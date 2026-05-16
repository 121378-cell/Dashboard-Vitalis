"""
ATLAS Daily Intelligence Loop Service
======================================

Ejecuta el loop diario de inteligencia que:
1. Fetch biométricos de hoy/anoche
2. Calcula Readiness Score (0-100) SIN HRV (FR245)
3. Adapta sesión del día según readiness
4. Genera insights proactivos
5. Guarda en SQLite (daily_readiness)
6. Retorna resultado completo

Autor: ATLAS Team
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text, and_

from app.models.biometrics import Biometrics
from app.models.adaptive_training_plan import AdaptiveTrainingPlan, AdaptivePlannedSession, AdaptivePlanAdjustment
from app.services.athletic_intelligence_service import AthleticIntelligenceService
from app.services.training_plan_service import TrainingPlanService
from app.core.exceptions import BiometricDataNotFoundError

logger = logging.getLogger("app.services.daily_loop_service")

RHR_BASELINE = 45.5


class DailyLoopService:

    @staticmethod
    def run_daily_loop(db: Session, user_id: str = "default_user") -> Dict[str, Any]:
        try:
            today = date.today()
            yesterday = today - timedelta(days=1)

            bb_value, rhr_value, sleep_hours, stress_value, biometrics_source = DailyLoopService._fetch_biometrics(
                db, user_id, today, yesterday
            )

            readiness_score, bb_score, rhr_score, sleep_score, stress_score_val, bb_clean, rhr_delta = DailyLoopService._calculate_readiness(
                bb_value, rhr_value, sleep_hours, stress_value
            )

            category, color = DailyLoopService._categorize_readiness(readiness_score)

            session_data = DailyLoopService._adapt_session(
                db, user_id, today, readiness_score, bb_clean
            )

            insights = DailyLoopService._generate_insights(
                db, user_id, readiness_score, bb_clean, rhr_value,
                rhr_delta, sleep_hours, stress_value
            )

            DailyLoopService._save_readiness(
                db, user_id, today, readiness_score, category,
                bb_clean, rhr_value, sleep_hours, stress_value,
                bb_score, rhr_score, sleep_score, stress_score_val,
                session_data, insights, biometrics_source
            )

            summary_message = DailyLoopService._build_summary_message(
                readiness_score, category, session_data
            )

            result = {
                "date": today.isoformat(),
                "readiness_score": readiness_score,
                "readiness_category": category,
                "readiness_color": color,
                "components": {
                    "body_battery": {
                        "value": bb_clean,
                        "score": round(bb_score, 1),
                        "weight": "35%"
                    },
                    "resting_hr": {
                        "value": rhr_value,
                        "score": round(rhr_score, 1),
                        "weight": "30%",
                        "vs_baseline": round(rhr_delta, 1) if rhr_value else None
                    },
                    "sleep": {
                        "value": sleep_hours,
                        "score": round(sleep_score, 1),
                        "weight": "25%"
                    },
                    "stress": {
                        "value": stress_value,
                        "score": round(stress_score_val, 1),
                        "weight": "10%"
                    }
                },
                "biometrics_source": biometrics_source,
                "today_session": session_data,
                "insights": insights,
                "summary_message": summary_message
            }

            logger.info(f"Daily loop completado. Readiness: {readiness_score}/100 ({category})")

            try:
                from app.services.notification_service import NotificationService
                NotificationService.send_daily_briefing(result, db=db)
                for insight in insights:
                    if insight.get("priority") in ("high", "medium"):
                        NotificationService.send_insight(insight, db=db)
            except Exception as notif_err:
                logger.warning(f"Error enviando notificaciones: {notif_err}")

            # ── Living ATLAS: emitir evento y actualizar estado ──
            try:
                from app.services.event_bus_service import emit
                emit(
                    user_id=user_id,
                    event_type="daily_loop_completed",
                    payload={
                        "readiness_score": readiness_score,
                        "readiness_category": category,
                        "insights_count": len(insights),
                        "adaptation_made": (
                            session_data.get("adaptation", {}).get("suggestion") != "mantener"
                            if session_data else False
                        ),
                    },
                    source="daily_loop"
                )
            except Exception as ev_err:
                logger.warning(f"Error emitiendo evento daily_loop: {ev_err}")

            try:
                from app.services.athlete_state_service import AthleteStateService
                AthleteStateService.compute_state(user_id)
            except Exception as state_err:
                logger.warning(f"Error computando estado del atleta: {state_err}")

            return result

        except Exception as e:
            logger.error(f"Error en daily loop: {e}", exc_info=True)
            return {"error": True, "message": str(e)}

    @staticmethod
    def _fetch_biometrics(
        db: Session, user_id: str, today: date, yesterday: date
    ) -> tuple:
        bb_value = None
        rhr_value = None
        sleep_hours = None
        stress_value = None
        biometrics_source = "partial"

        today_str = today.isoformat()
        yesterday_str = yesterday.isoformat()

        for check_date_str, source_label in [(today_str, "today"), (yesterday_str, "yesterday")]:
            row = db.execute(
                text("SELECT data FROM biometrics WHERE user_id = :uid AND date = :d ORDER BY timestamp DESC LIMIT 1"),
                {"uid": user_id, "d": check_date_str}
            ).first()

            if not row or not row[0]:
                continue

            try:
                raw = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error parseando data JSON de biometrics ({check_date_str}): {e}")
                continue

            body_battery = raw.get("bodyBattery") or raw.get("bodyBatteryMostRecentValue")
            if body_battery is not None:
                if body_battery > 100:
                    logger.warning(f"Body Battery corrupto filtrado: {body_battery}")
                    body_battery = None
                else:
                    bb_value = body_battery

            rhr_raw = raw.get("heartRate") or raw.get("lastSevenDaysAvgRHR")
            if rhr_raw and rhr_raw > 0:
                rhr_value = rhr_raw

            sleep_raw = raw.get("sleep")
            if sleep_raw and sleep_raw > 0:
                sleep_hours = sleep_raw if sleep_raw < 24 else sleep_raw / 3600
            if not sleep_hours:
                sleep_from_stats = raw.get("sleepFromStats")
                if sleep_from_stats and sleep_from_stats > 0:
                    sleep_hours = sleep_from_stats
                    logger.info(f"Sleep from sleepFromStats fallback: {sleep_hours}h")

            stress_raw = raw.get("stress")
            if stress_raw is not None:
                stress_value = stress_raw

            biometrics_source = source_label
            if source_label == "yesterday":
                logger.warning(f"No hay datos de hoy, usando datos de ayer para user {user_id}")
            break

        else:
            logger.warning(f"No hay datos biométricos recientes para user {user_id}")
            raise BiometricDataNotFoundError(
                detail={"user_id": user_id, "dates_checked": [today_str, yesterday_str]}
            )

        return bb_value, rhr_value, sleep_hours, stress_value, biometrics_source

    @staticmethod
    def _calculate_readiness(
        bb_value: Optional[float],
        rhr_value: Optional[float],
        sleep_hours: Optional[float],
        stress_value: Optional[float]
    ) -> tuple:
        bb_clean = min(bb_value, 100) if bb_value is not None else None
        bb_score = (bb_clean / 100) * 35 if bb_clean is not None else 17.5

        rhr_baseline = RHR_BASELINE
        try:
            from app.db.session import SessionLocal
            _db = SessionLocal()
            profile = AthleticIntelligenceService.analyze_fitness_baseline(_db, "default_user")
            if profile.get("resting_hr_avg"):
                rhr_baseline = profile["resting_hr_avg"]
            _db.close()
        except Exception:
            pass

        if rhr_value is not None:
            rhr_delta = rhr_value - rhr_baseline
            if rhr_delta <= 0:
                rhr_score = 30
            elif rhr_delta <= 2:
                rhr_score = 24
            elif rhr_delta <= 4:
                rhr_score = 18
            elif rhr_delta <= 6:
                rhr_score = 12
            else:
                rhr_score = 6
        else:
            rhr_score = 18
            rhr_delta = 0

        if sleep_hours is not None:
            if sleep_hours >= 8:
                sleep_score = 25
            elif sleep_hours >= 7:
                sleep_score = 20
            elif sleep_hours >= 6:
                sleep_score = 14
            elif sleep_hours >= 5:
                sleep_score = 8
            else:
                sleep_score = 3
        else:
            sleep_score = 10

        if stress_value is not None:
            stress_score = ((100 - min(stress_value, 100)) / 100) * 10
        else:
            stress_score = 7

        readiness_score = round(bb_score + rhr_score + sleep_score + stress_score)
        readiness_score = max(0, min(100, readiness_score))

        bb_clean_val = bb_clean if bb_clean is not None else 0
        return readiness_score, bb_score, rhr_score, sleep_score, stress_score, bb_clean_val, rhr_delta

    @staticmethod
    def _categorize_readiness(score: int) -> tuple:
        if score >= 80:
            return "ÓPTIMO", "green"
        elif score >= 65:
            return "BUENO", "blue"
        elif score >= 45:
            return "MODERADO", "yellow"
        else:
            return "BAJO", "red"

    @staticmethod
    def _adapt_session(
        db: Session, user_id: str, today: date, readiness_score: int, bb_clean: float
    ) -> Optional[Dict[str, Any]]:
        try:
            current_plan = TrainingPlanService.get_current_plan(db, user_id)
            if not current_plan:
                return None

            today_str = today.isoformat()
            today_session = None
            today_session_id = None

            for session in current_plan.get("plan", {}).get("sessions", []):
                if session.get("date") == today_str and not session.get("completed", False):
                    today_session = session
                    today_session_id = session.get("id")
                    break

            if not today_session:
                return None

            intensity = today_session.get("intensity", "medium")
            suggestion = "mantener"
            adaptation_note = None

            if readiness_score >= 80 and intensity == "medium":
                suggestion = "subir_intensidad"
                adaptation_note = "Tu readiness es óptimo. Considera añadir series extra o subir peso."
            elif readiness_score < 45 and intensity == "high":
                suggestion = "bajar_intensidad"
                adaptation_note = "Readiness bajo. Se recomienda bajar intensidad o cambiar a active_recovery."

                if today_session_id:
                    session_obj = db.query(AdaptivePlannedSession).filter(
                        AdaptivePlannedSession.id == today_session_id
                    ).first()
                    if session_obj:
                        original_intensity = session_obj.intensity
                        original_session_data = {
                            "intensity": original_intensity,
                            "title": session_obj.title,
                            "duration_minutes": session_obj.duration_minutes
                        }
                        session_obj.intensity = "low"
                        session_obj.adaptation_reason = adaptation_note

                        biometrics_json = json.dumps({
                            "readiness_score": readiness_score,
                            "body_battery": bb_clean,
                            "date": today.isoformat()
                        })
                        adjustment = AdaptivePlanAdjustment(
                            plan_id=current_plan["plan_id"],
                            session_id=today_session_id,
                            reason=adaptation_note,
                            original_session_json=json.dumps(original_session_data),
                            adapted_session_json=json.dumps({"intensity": "low"}),
                            biometrics_json=biometrics_json
                        )
                        db.add(adjustment)
                        db.commit()

            elif readiness_score < 30:
                suggestion = "descanso_recomendado"
                adaptation_note = "Readiness muy bajo. Tu cuerpo necesita recuperación hoy."

            return {
                "planned": {
                    "session_type": today_session.get("session_type"),
                    "title": today_session.get("title"),
                    "duration_minutes": today_session.get("duration_minutes"),
                    "intensity": today_session.get("intensity")
                },
                "adaptation": {
                    "suggestion": suggestion,
                    "note": adaptation_note or "Sin cambios necesarios."
                }
            }

        except Exception as e:
            logger.error(f"Error adaptando sesión: {e}", exc_info=True)
            return None

    @staticmethod
    def _generate_insights(
        db: Session, user_id: str,
        readiness_score: int, bb_clean: float,
        rhr_value: Optional[float], rhr_delta: float,
        sleep_hours: Optional[float], stress_value: Optional[float]
    ) -> List[Dict[str, Any]]:
        insights = []

        try:
            sleep_analysis = AthleticIntelligenceService.analyze_sleep_patterns(db, user_id)
            sleep_debt_7d = sleep_analysis.get("sleep_debt_7d_hours")
            sleep_avg = sleep_analysis.get("sleep_avg_recent_4w")

            overreaching = AthleticIntelligenceService.detect_overreaching_risk(db, user_id)
            acwr_ratio = overreaching.get("acwr_ratio")
        except Exception as e:
            logger.warning(f"Error obteniendo datos de AthleticIntelligenceService: {e}")
            sleep_debt_7d = None
            sleep_avg = None
            acwr_ratio = None

        consecutive_good_days = DailyLoopService._count_consecutive_good_days(db, user_id)

        if sleep_debt_7d is not None and sleep_debt_7d > 3.0:
            insights.append({
                "id": "sleep_debt",
                "priority": "high",
                "title": "\u26a0\ufe0f Deuda de sueño acumulada",
                "message": f"Llevas una deuda de {sleep_debt_7d:.1f}h de sueño esta semana. La síntesis proteica y recuperación muscular están comprometidas."
            })

        if sleep_hours is not None and sleep_hours < 6.5:
            avg_display = f"{sleep_avg:.1f}h" if sleep_avg else "tu media"
            insights.append({
                "id": "sleep_last_night",
                "priority": "medium",
                "title": "\U0001f634 Sueño corto anoche",
                "message": f"Dormiste {sleep_hours:.1f}h. Tu media es {avg_display}. Prioriza descanso esta noche."
            })

        if readiness_score >= 80 and bb_clean >= 70:
            insights.append({
                "id": "good_recovery",
                "priority": "low",
                "title": "\u2705 Recuperación excelente",
                "message": f"Body Battery {bb_clean:.0f}% y readiness {readiness_score}/100. Día óptimo para entrenar fuerte."
            })

        if rhr_value is not None and rhr_value > RHR_BASELINE + 5:
            delta = rhr_value - RHR_BASELINE
            insights.append({
                "id": "rhr_elevated",
                "priority": "high",
                "title": "\u2764\ufe0f FC elevada",
                "message": f"FC reposo {rhr_value:.0f} bpm (+{delta:.0f} sobre tu media). Señal de fatiga o estrés acumulado. Considera bajar carga hoy."
            })

        if acwr_ratio is not None and acwr_ratio > 1.3:
            insights.append({
                "id": "overreaching_risk",
                "priority": "high",
                "title": "\U0001f534 Riesgo de sobreentrenamiento",
                "message": f"Carga semanal {acwr_ratio:.2f}x superior a tu media crónica. Incorpora descanso activo."
            })

        if acwr_ratio is not None and acwr_ratio < 0.7:
            insights.append({
                "id": "low_load",
                "priority": "medium",
                "title": "\U0001f4c9 Carga baja esta semana",
                "message": "Tu carga de entrenamiento está por debajo de tu media. Puedes aumentar volumen o intensidad de forma segura."
            })

        if consecutive_good_days >= 5:
            insights.append({
                "id": "streak_positive",
                "priority": "low",
                "title": "\U0001f525 Racha de buena recuperación",
                "message": f"Llevas {consecutive_good_days} días consecutivos con buena recuperación. Momento óptimo para semana de carga progresiva."
            })

        return insights

    @staticmethod
    def _count_consecutive_good_days(db: Session, user_id: str) -> int:
        try:
            result = db.execute(text(
                "SELECT readiness_score FROM daily_readiness "
                "WHERE date <= :today AND readiness_score IS NOT NULL "
                "ORDER BY date DESC LIMIT 30"
            ), {"today": date.today().isoformat()}).fetchall()

            count = 0
            for row in result:
                if row[0] is not None and row[0] >= 70:
                    count += 1
                else:
                    break
            return count
        except Exception:
            return 0

    @staticmethod
    def _save_readiness(
        db: Session, user_id: str, today: date,
        readiness_score: int, category: str,
        bb_clean: float, rhr_value: Optional[float],
        sleep_hours: Optional[float], stress_value: Optional[float],
        bb_score: float, rhr_score: float,
        sleep_score: float, stress_score_val: float,
        session_data: Optional[Dict], insights: List[Dict],
        biometrics_source: str
    ):
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_readiness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    readiness_score INTEGER,
                    readiness_category TEXT,
                    body_battery REAL,
                    resting_heart_rate REAL,
                    sleep_hours REAL,
                    stress_level REAL,
                    bb_score REAL,
                    rhr_score REAL,
                    sleep_score REAL,
                    stress_score REAL,
                    adaptation_made BOOLEAN DEFAULT 0,
                    adaptation_suggestion TEXT,
                    adaptation_note TEXT,
                    insights_json TEXT,
                    biometrics_source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            adaptation_made = 0
            adaptation_suggestion = None
            adaptation_note = None
            if session_data and session_data.get("adaptation", {}).get("suggestion") != "mantener":
                adaptation_made = 1
                adaptation_suggestion = session_data["adaptation"]["suggestion"]
                adaptation_note = session_data["adaptation"]["note"]

            insights_json = json.dumps(insights, ensure_ascii=False)

            db.execute(text("""
                INSERT OR REPLACE INTO daily_readiness (
                    date, readiness_score, readiness_category,
                    body_battery, resting_heart_rate, sleep_hours, stress_level,
                    bb_score, rhr_score, sleep_score, stress_score,
                    adaptation_made, adaptation_suggestion, adaptation_note,
                    insights_json, biometrics_source
                ) VALUES (
                    :date, :readiness_score, :readiness_category,
                    :body_battery, :resting_heart_rate, :sleep_hours, :stress_level,
                    :bb_score, :rhr_score, :sleep_score, :stress_score,
                    :adaptation_made, :adaptation_suggestion, :adaptation_note,
                    :insights_json, :biometrics_source
                )
            """), {
                "date": today.isoformat(),
                "readiness_score": readiness_score,
                "readiness_category": category,
                "body_battery": bb_clean if bb_clean else None,
                "resting_heart_rate": rhr_value,
                "sleep_hours": sleep_hours,
                "stress_level": stress_value,
                "bb_score": bb_score,
                "rhr_score": rhr_score,
                "sleep_score": sleep_score,
                "stress_score": stress_score_val,
                "adaptation_made": adaptation_made,
                "adaptation_suggestion": adaptation_suggestion,
                "adaptation_note": adaptation_note,
                "insights_json": insights_json,
                "biometrics_source": biometrics_source
            })

            db.commit()
            logger.info(f"Readiness guardado para {today.isoformat()}: {readiness_score}/100")

        except Exception as e:
            logger.error(f"Error guardando readiness: {e}", exc_info=True)
            db.rollback()

    @staticmethod
    def _build_summary_message(
        readiness_score: int, category: str,
        session_data: Optional[Dict]
    ) -> str:
        parts = [f"Readiness {readiness_score}/100 — {category}."]

        if readiness_score >= 65:
            parts.append("Buena recuperación.")
        elif readiness_score >= 45:
            parts.append("Recuperación moderada.")
        else:
            parts.append("Recuperación baja.")

        if session_data:
            title = session_data.get("planned", {}).get("title")
            suggestion = session_data.get("adaptation", {}).get("suggestion")
            if title:
                if suggestion == "mantener":
                    parts.append(f"Tu sesión de {title} está en verde.")
                elif suggestion == "subir_intensidad":
                    parts.append(f"Tu sesión de {title} puede subir de intensidad hoy.")
                elif suggestion in ("bajar_intensidad", "descanso_recomendado"):
                    parts.append(f"Considera adaptar tu sesión de {title}.")
        else:
            parts.append("Sin sesión planificada para hoy.")

        return " ".join(parts)

    @staticmethod
    def get_status(db: Session, user_id: str = "default_user") -> Optional[Dict[str, Any]]:
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_readiness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    readiness_score INTEGER,
                    readiness_category TEXT,
                    body_battery REAL,
                    resting_heart_rate REAL,
                    sleep_hours REAL,
                    stress_level REAL,
                    bb_score REAL,
                    rhr_score REAL,
                    sleep_score REAL,
                    stress_score REAL,
                    adaptation_made BOOLEAN DEFAULT 0,
                    adaptation_suggestion TEXT,
                    adaptation_note TEXT,
                    insights_json TEXT,
                    biometrics_source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            row = db.execute(text(
                "SELECT * FROM daily_readiness WHERE date = :today ORDER BY created_at DESC LIMIT 1"
            ), {"today": date.today().isoformat()}).fetchone()

            if not row:
                return {"has_data": False}

            keys = [
                "id", "date", "readiness_score", "readiness_category",
                "body_battery", "resting_heart_rate", "sleep_hours", "stress_level",
                "bb_score", "rhr_score", "sleep_score", "stress_score",
                "adaptation_made", "adaptation_suggestion", "adaptation_note",
                "insights_json", "biometrics_source", "created_at"
            ]
            record = dict(zip(keys, row))

            score = record.get("readiness_score", 0)
            category, color = DailyLoopService._categorize_readiness(score)

            insights = []
            if record.get("insights_json"):
                try:
                    insights = json.loads(record["insights_json"])
                except (json.JSONDecodeError, TypeError):
                    pass

            return {
                "has_data": True,
                "date": record.get("date"),
                "readiness_score": score,
                "readiness_category": record.get("readiness_category", category),
                "readiness_color": color,
                "components": {
                    "body_battery": {
                        "value": record.get("body_battery"),
                        "score": record.get("bb_score"),
                        "weight": "35%"
                    },
                    "resting_hr": {
                        "value": record.get("resting_heart_rate"),
                        "score": record.get("rhr_score"),
                        "weight": "30%",
                        "vs_baseline": round(record.get("resting_heart_rate", 0) - RHR_BASELINE, 1) if record.get("resting_heart_rate") else None
                    },
                    "sleep": {
                        "value": record.get("sleep_hours"),
                        "score": record.get("sleep_score"),
                        "weight": "25%"
                    },
                    "stress": {
                        "value": record.get("stress_level"),
                        "score": record.get("stress_score"),
                        "weight": "10%"
                    }
                },
                "biometrics_source": record.get("biometrics_source"),
                "adaptation": {
                    "made": bool(record.get("adaptation_made")),
                    "suggestion": record.get("adaptation_suggestion"),
                    "note": record.get("adaptation_note")
                },
                "insights": insights,
                "summary_message": DailyLoopService._build_summary_message(
                    score, record.get("readiness_category", category), None
                ),
                "created_at": str(record.get("created_at", ""))
            }

        except Exception as e:
            logger.error(f"Error obteniendo status de daily readiness: {e}", exc_info=True)
            return {"has_data": False, "error": str(e)}

    @staticmethod
    def get_history(db: Session, user_id: str = "default_user", days: int = 30) -> List[Dict[str, Any]]:
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_readiness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    readiness_score INTEGER,
                    readiness_category TEXT,
                    body_battery REAL,
                    resting_heart_rate REAL,
                    sleep_hours REAL,
                    stress_level REAL,
                    bb_score REAL,
                    rhr_score REAL,
                    sleep_score REAL,
                    stress_score REAL,
                    adaptation_made BOOLEAN DEFAULT 0,
                    adaptation_suggestion TEXT,
                    adaptation_note TEXT,
                    insights_json TEXT,
                    biometrics_source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            rows = db.execute(text(
                "SELECT date, readiness_score, readiness_category, body_battery, "
                "resting_heart_rate, sleep_hours, stress_level, "
                "bb_score, rhr_score, sleep_score, stress_score, "
                "adaptation_made, adaptation_suggestion, adaptation_note, "
                "insights_json, biometrics_source, created_at "
                "FROM daily_readiness ORDER BY date DESC LIMIT :days"
            ), {"days": days}).fetchall()

            result = []
            for row in rows:
                insights = []
                if row[14]:
                    try:
                        insights = json.loads(row[14])
                    except (json.JSONDecodeError, TypeError):
                        pass

                score = row[1] or 0
                _, color = DailyLoopService._categorize_readiness(score)

                result.append({
                    "date": str(row[0]),
                    "readiness_score": score,
                    "readiness_category": row[2],
                    "readiness_color": color,
                    "body_battery": row[3],
                    "resting_heart_rate": row[4],
                    "sleep_hours": row[5],
                    "stress_level": row[6],
                    "components": {
                        "bb_score": row[7],
                        "rhr_score": row[8],
                        "sleep_score": row[9],
                        "stress_score": row[10]
                    },
                    "adaptation_made": bool(row[11]),
                    "adaptation_suggestion": row[12],
                    "adaptation_note": row[13],
                    "insights": insights,
                    "biometrics_source": row[15],
                    "created_at": str(row[16] or "")
                })

            return result

        except Exception as e:
            logger.error(f"Error obteniendo historial de readiness: {e}", exc_info=True)
            return []
