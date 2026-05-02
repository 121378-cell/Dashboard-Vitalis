"""
ATLAS Injury Prevention & Recovery Service
==========================================

Early warning system for overtraining and injury risk based on:
- HRV deviation from baseline
- Resting heart rate elevation
- Training streak detection
- Sleep debt accumulation
- Readiness score decline
- Weekly volume spikes

Integrates with MemoryService for injury tracking and pattern detection.
Uses McGill methodology for recovery session design.

Autor: ATLAS Team
Version: 1.0.0
"""

import json
import logging
import statistics
from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.models.memory import AtlasMemory
from app.services.memory_service import MemoryService

logger = logging.getLogger("app.services.injury_prevention")


class AlertLevel(str, Enum):
    GREEN = "optimal"
    YELLOW = "caution"
    ORANGE = "warning"
    RED = "stop"


@dataclass
class RecoverySession:
    session_type: str
    duration_min: int
    exercises: Optional[List[str]] = None
    message: Optional[str] = None
    optional: Optional[List[str]] = None
    alert_level: AlertLevel = AlertLevel.GREEN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.session_type,
            "duration_min": self.duration_min,
            "exercises": self.exercises or [],
            "message": self.message,
            "optional": self.optional or [],
            "alert_level": self.alert_level.value,
        }


@dataclass
class Alert:
    level: AlertLevel
    reason: str
    indicator: str
    value: Any = None
    threshold: Any = None
    action_required: str = ""


@dataclass
class RecoveryStatus:
    alert_level: AlertLevel
    alerts: List[Alert]
    readiness_penalty: float
    active_injuries: List[Dict]
    zones_to_avoid: List[str]
    recommendations: List[str]
    forecast_risk: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_level": self.alert_level.value,
            "alerts": [
                {
                    "level": a.level.value,
                    "reason": a.reason,
                    "indicator": a.indicator,
                    "value": a.value,
                    "threshold": a.threshold,
                    "action_required": a.action_required,
                }
                for a in self.alerts
            ],
            "readiness_penalty": self.readiness_penalty,
            "active_injuries": self.active_injuries,
            "zones_to_avoid": self.zones_to_avoid,
            "recommendations": self.recommendations,
            "forecast_risk": self.forecast_risk,
        }


BODY_ZONES = {
    "neck": ["trapezius", "levator_scapulae", "sternocleidomastoid"],
    "shoulder_left": ["anterior_delt", "lateral_delt", "posterior_delt", "rotator_cuff"],
    "shoulder_right": ["anterior_delt", "lateral_delt", "posterior_delt", "rotator_cuff"],
    "upper_back": ["rhomboid", "mid_trapezius", "latissimus"],
    "lower_back": ["erector_spinae", "quadratus_lumborum", "multifidus"],
    "elbow_left": ["bicep_tendon", "tricep_tendon", "lateral_epicondyle", "medial_epicondyle"],
    "elbow_right": ["bicep_tendon", "tricep_tendon", "lateral_epicondyle", "medial_epicondyle"],
    "wrist_left": ["carpal", "forearm_flexor", "forearm_extensor"],
    "wrist_right": ["carpal", "forearm_flexor", "forearm_extensor"],
    "chest": ["pectoralis_major", "pec_minor", "intercostals"],
    "core": ["rectus_abdominis", "obliques", "transverse_abdominis"],
    "hip_left": ["hip_flexor", "glute_med", "piriformis", "adductor"],
    "hip_right": ["hip_flexor", "glute_med", "piriformis", "adductor"],
    "knee_left": ["patellar_tendon", "quadriceps", "hamstring", "it_band"],
    "knee_right": ["patellar_tendon", "quadriceps", "hamstring", "it_band"],
    "ankle_left": ["achilles", "calf", "peroneal", "ankle_joint"],
    "ankle_right": ["achilles", "calf", "peroneal", "ankle_joint"],
    "hand_left": ["grip", "forearm_flexor"],
    "hand_right": ["grip", "forearm_flexor"],
}

ZONE_TO_EXERCISES = {
    "neck": ["chin_tucks", "neck_rotation", "shoulder_shrugs"],
    "shoulder_left": ["external_rotation_left", "face_pull", "band_pull_apart", "y Raises"],
    "shoulder_right": ["external_rotation_right", "face_pull", "band_pull_apart", "y_raises"],
    "upper_back": ["face_pull", "band_pull_apart", "scapular_retraction", "rows"],
    "lower_back": ["bird_dog", "dead_bug", "McGill_big_3", "plank", "bridge"],
    "elbow_left": ["wrist_curl_left", "reverse_wrist_curl_left", "grip_squeeze_left"],
    "elbow_right": ["wrist_curl_right", "reverse_wrist_curl_right", "grip_squeeze_right"],
    "wrist_left": ["wrist_circles", "wrist_curls_left", "grip_squeeze_left"],
    "wrist_right": ["wrist_circles", "wrist_curls_right", "grip_squeeze_right"],
    "chest": ["pec_stretch", "wall_pec_stretch", "doorway_stretch"],
    "core": ["McGill_big_3", "dead_bug", "bird_dog", "plank"],
    "hip_left": ["hip_circles_left", "90_90_stretch_left", "pigeon_stretch_left", "glute_bridge"],
    "hip_right": ["hip_circles_right", "90_90_stretch_right", "pigeon_stretch_right", "glute_bridge"],
    "knee_left": ["leg_extension_left", "terminal_knee_extension_left", "straight_leg_raise_left"],
    "knee_right": ["leg_extension_right", "terminal_knee_extension_right", "straight_leg_raise_right"],
    "ankle_left": ["ankle_circles_left", "calf_stretch_left", "alphabet_ankle_left"],
    "ankle_right": ["ankle_circles_right", "calf_stretch_right", "alphabet_ankle_right"],
}


class InjuryPreventionService:
    """
    Early warning system for injury prevention and recovery protocols.

    Monitors: HRV, resting HR, training streaks, sleep debt, readiness decline,
    volume spikes. Generates McGill-based recovery sessions when needed.
    """

    HRV_YELLOW_THRESHOLD = 0.20
    HRV_RED_THRESHOLD = 0.30
    RESTING_HR_THRESHOLD_BPM = 8
    TRAINING_STREAK_THRESHOLD = 6
    SLEEP_DEBT_DAYS = 3
    SLEEP_HOURS_MIN = 6.0
    READINESS_YELLOW_THRESHOLD = 50
    READINESS_RED_THRESHOLD = 35
    VOLUME_SPIKE_THRESHOLD = 1.30

    @staticmethod
    def _parse_biometrics(data: Dict) -> Dict:
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return data or {}

    @staticmethod
    def _get_biometrics_window(
        db: Session, user_id: str, days: int
    ) -> List[Biometrics]:
        cutoff = date.today() - timedelta(days=days)
        return (
            db.query(Biometrics)
            .filter(
                Biometrics.user_id == user_id,
                Biometrics.date >= cutoff.isoformat(),
            )
            .order_by(Biometrics.date.desc())
            .all()
        )

    @staticmethod
    def _get_workouts_window(
        db: Session, user_id: str, days: int
    ) -> List[Workout]:
        cutoff = date.today() - timedelta(days=days)
        return (
            db.query(Workout)
            .filter(
                Workout.user_id == user_id,
                Workout.date >= cutoff.isoformat(),
            )
            .order_by(Workout.date.desc())
            .all()
        )

    @staticmethod
    def _calculate_hrv_baseline(
        biometrics: List[Biometrics]
    ) -> Optional[float]:
        hrv_values = []
        for b in biometrics:
            data = InjuryPreventionService._parse_biometrics(b.data)
            hrv = data.get("hrv")
            if hrv and hrv > 0:
                hrv_values.append(float(hrv))
        if len(hrv_values) < 7:
            return None
        return statistics.mean(hrv_values[-30:] if len(hrv_values) >= 30 else hrv_values)

    @staticmethod
    def _evaluate_hrv_alert(
        current_hrv: Optional[float], baseline: Optional[float]
    ) -> Optional[Alert]:
        if current_hrv is None or baseline is None or baseline <= 0:
            return None
        deviation = (baseline - current_hrv) / baseline
        if deviation >= InjuryPreventionService.HRV_RED_THRESHOLD:
            return Alert(
                level=AlertLevel.RED,
                reason=f"HRV crítico: {current_hrv:.0f}ms vs baseline {baseline:.0f}ms ({deviation*100:.0f}% bajo)",
                indicator="hrv",
                value=current_hrv,
                threshold=f"-{deviation*100:.0f}% vs baseline",
                action_required="Descanso total obligatorio. No entrenes hoy.",
            )
        if deviation >= InjuryPreventionService.HRV_YELLOW_THRESHOLD:
            return Alert(
                level=AlertLevel.YELLOW,
                reason=f"HRV bajo: {current_hrv:.0f}ms vs baseline {baseline:.0f}ms ({deviation*100:.0f}% bajo)",
                indicator="hrv",
                value=current_hrv,
                threshold=f"-{deviation*100:.0f}% vs baseline",
                action_required="Reducir intensidad hoy. Prioriza recuperación.",
            )
        return None

    @staticmethod
    def _evaluate_resting_hr_alert(
        current_rhr: Optional[float], baseline: Optional[float]
    ) -> Optional[Alert]:
        if current_rhr is None or baseline is None:
            return None
        elevation = current_rhr - baseline
        if elevation >= InjuryPreventionService.RESTING_HR_THRESHOLD_BPM:
            return Alert(
                level=AlertLevel.YELLOW,
                reason=f"FC reposo elevada: {current_rhr:.0f} bpm (+{elevation:.0f} vs baseline {baseline:.0f})",
                indicator="resting_hr",
                value=current_rhr,
                threshold=f"+{elevation:.0f} bpm vs baseline {baseline:.0f}",
                action_required="Posible enfermedad o sobreentrenamiento. Reduce volumen.",
            )
        return None

    @staticmethod
    def _evaluate_training_streak(workouts: List[Workout]) -> Optional[Alert]:
        if not workouts:
            return None
        sorted_workouts = sorted(
            (w for w in workouts if w.date), key=lambda w: w.date, reverse=True
        )
        consecutive = 1
        for i in range(1, len(sorted_workouts)):
            diff = (sorted_workouts[i - 1].date - sorted_workouts[i].date).days
            if diff == 1:
                consecutive += 1
            else:
                break
        if consecutive >= InjuryPreventionService.TRAINING_STREAK_THRESHOLD:
            return Alert(
                level=AlertLevel.YELLOW,
                reason=f"{consecutive} días consecutivos entrenando",
                indicator="training_streak",
                value=consecutive,
                threshold=f">= {InjuryPreventionService.TRAINING_STREAK_THRESHOLD} días",
                action_required="Inserta al menos 1 día de descanso esta semana.",
            )
        return None

    @staticmethod
    def _evaluate_sleep_debt(biometrics: List[Biometrics]) -> Optional[Alert]:
        bad_days = 0
        for b in biometrics[: InjuryPreventionService.SLEEP_DEBT_DAYS]:
            data = InjuryPreventionService._parse_biometrics(b.data)
            sleep = data.get("sleep")
            if sleep and sleep < InjuryPreventionService.SLEEP_HOURS_MIN:
                bad_days += 1
        if bad_days >= InjuryPreventionService.SLEEP_DEBT_DAYS:
            return Alert(
                level=AlertLevel.YELLOW,
                reason=f"{bad_days} días seguidos con < {InjuryPreventionService.SLEEP_HOURS_MIN}h de sueño",
                indicator="sleep_debt",
                value=bad_days,
                threshold=f"{InjuryPreventionService.SLEEP_DEBT_DAYS}+ días < {InjuryPreventionService.SLEEP_HOURS_MIN}h",
                action_required="Prioriza sueño sobre entrenamiento. El sueño es tu mayor herramienta de recuperación.",
            )
        return None

    @staticmethod
    def _evaluate_readiness_decline(
        readiness_scores: List[float],
    ) -> Optional[Alert]:
        if len(readiness_scores) < 2:
            if readiness_scores and readiness_scores[0] < InjuryPreventionService.READINESS_RED_THRESHOLD:
                return Alert(
                    level=AlertLevel.ORANGE,
                    reason=f"Readiness crítico: {readiness_scores[0]:.0f}",
                    indicator="readiness_decline",
                    value=readiness_scores[0],
                    threshold=f"< {InjuryPreventionService.READINESS_RED_THRESHOLD}",
                    action_required="Protocolo de recuperación activa. Descansa hoy.",
                )
            return None
        recent_avg = statistics.mean(readiness_scores[:2])
        if recent_avg < InjuryPreventionService.READINESS_RED_THRESHOLD:
            return Alert(
                level=AlertLevel.ORANGE,
                reason=f"Readiness en declive: {recent_avg:.0f} (promedio últimos 2 días)",
                indicator="readiness_decline",
                value=recent_avg,
                threshold=f"< {InjuryPreventionService.READINESS_RED_THRESHOLD} por 2 días",
                action_required="Protocolo de recuperación activa. Solo movilidad y McGill.",
            )
        if recent_avg < InjuryPreventionService.READINESS_YELLOW_THRESHOLD:
            return Alert(
                level=AlertLevel.YELLOW,
                reason=f"Readiness bajo: {recent_avg:.0f} (promedio últimos 2 días)",
                indicator="readiness_decline",
                value=recent_avg,
                threshold=f"< {InjuryPreventionService.READINESS_YELLOW_THRESHOLD}",
                action_required="Reduce intensidad. Solo ejercicios de recuperación si es necesario.",
            )
        return None

    @staticmethod
    def _evaluate_volume_spike(
        current_week_workouts: List[Workout],
        previous_week_workouts: List[Workout],
    ) -> Optional[Alert]:
        def total_volume(workouts: List[Workout]) -> float:
            return sum(
                (w.duration or 0) + (w.calories or 0) * 0.1
                for w in workouts
            )

        current = total_volume(current_week_workouts)
        previous = total_volume(previous_week_workouts)
        if previous <= 0 or current <= 0:
            return None
        ratio = current / previous
        if ratio >= InjuryPreventionService.VOLUME_SPIKE_THRESHOLD:
            return Alert(
                level=AlertLevel.ORANGE,
                reason=f"Volumen semanal {ratio*100:.0f}% vs semana anterior",
                indicator="volume_spike",
                value=ratio,
                threshold=f">= {InjuryPreventionService.VOLUME_SPIKE_THRESHOLD * 100:.0f}%",
                action_required="Reducir volumen esta semana. No incrementes más.",
            )
        return None

    @staticmethod
    def _calculate_rhr_baseline(biometrics: List[Biometrics]) -> Optional[float]:
        rhr_values = []
        for b in biometrics:
            data = InjuryPreventionService._parse_biometrics(b.data)
            rhr = data.get("resting_hr") or data.get("heartRate")
            if rhr and rhr > 0:
                rhr_values.append(float(rhr))
        if len(rhr_values) < 7:
            return None
        return statistics.mean(rhr_values[-30:] if len(rhr_values) >= 30 else rhr_values)

    @classmethod
    def get_current_status(cls, db: Session, user_id: str) -> RecoveryStatus:
        alerts: List[Alert] = []
        biometrics_7 = cls._get_biometrics_window(db, user_id, 7)
        biometrics_30 = cls._get_biometrics_window(db, user_id, 30)
        workouts_7 = cls._get_workouts_window(db, user_id, 7)
        workouts_14 = cls._get_workouts_window(db, user_id, 14)

        today_bio = biometrics_7[0] if biometrics_7 else None
        today_data = cls._parse_biometrics(today_bio.data) if today_bio else {}

        current_hrv = today_data.get("hrv")
        current_rhr = today_data.get("resting_hr")
        baseline_hrv = cls._calculate_hrv_baseline(biometrics_30)
        baseline_rhr = cls._calculate_rhr_baseline(biometrics_30)

        hrv_alert = cls._evaluate_hrv_alert(current_hrv, baseline_hrv)
        if hrv_alert:
            alerts.append(hrv_alert)

        rhr_alert = cls._evaluate_resting_hr_alert(current_rhr, baseline_rhr)
        if rhr_alert:
            alerts.append(rhr_alert)

        streak_alert = cls._evaluate_training_streak(workouts_14)
        if streak_alert:
            alerts.append(streak_alert)

        sleep_alert = cls._evaluate_sleep_debt(biometrics_7)
        if sleep_alert:
            alerts.append(sleep_alert)

        readiness_scores = []
        for b in biometrics_7[:2]:
            bdata = cls._parse_biometrics(b.data)
            rs = bdata.get("readiness_score")
            if rs is not None:
                readiness_scores.append(float(rs))
        if not readiness_scores:
            readiness_scores = [today_data.get("readiness_score", 50)]
        readiness_alert = cls._evaluate_readiness_decline(readiness_scores)
        if readiness_alert:
            alerts.append(readiness_alert)

        current_week = [w for w in workouts_7 if w.date and w.date >= date.today() - timedelta(days=7)]
        prev_week = [
            w for w in workouts_14
            if w.date
            and w.date < date.today() - timedelta(days=7)
            and w.date >= date.today() - timedelta(days=14)
        ]
        volume_alert = cls._evaluate_volume_spike(current_week, prev_week)
        if volume_alert:
            alerts.append(volume_alert)

        active_injuries = cls.get_injury_history(db, user_id, active_only=True)
        zones_to_avoid = []
        for injury in active_injuries:
            zone = injury.get("zone")
            if zone and zone not in zones_to_avoid:
                zones_to_avoid.append(zone)

        overall_level = AlertLevel.GREEN
        for alert in alerts:
            if alert.level == AlertLevel.RED:
                overall_level = AlertLevel.RED
                break
            elif alert.level == AlertLevel.ORANGE and overall_level != AlertLevel.RED:
                overall_level = AlertLevel.ORANGE
            elif alert.level == AlertLevel.YELLOW and overall_level == AlertLevel.GREEN:
                overall_level = AlertLevel.YELLOW

        for injury in active_injuries:
            pain = injury.get("pain_level", 0)
            if pain >= 7:
                overall_level = AlertLevel.RED
                break
            elif pain >= 5 and overall_level in [AlertLevel.GREEN, AlertLevel.YELLOW]:
                overall_level = AlertLevel.ORANGE

        readiness_penalty = 0.0
        if overall_level == AlertLevel.YELLOW:
            readiness_penalty = 15.0
        elif overall_level == AlertLevel.ORANGE:
            readiness_penalty = 30.0
        elif overall_level == AlertLevel.RED:
            readiness_penalty = 50.0

        recommendations = cls._generate_recommendations(alerts, active_injuries, overall_level)
        forecast_risk = cls._forecast_risk(alerts, active_injuries)

        return RecoveryStatus(
            alert_level=overall_level,
            alerts=alerts,
            readiness_penalty=readiness_penalty,
            active_injuries=active_injuries,
            zones_to_avoid=zones_to_avoid,
            recommendations=recommendations,
            forecast_risk=forecast_risk,
        )

    @staticmethod
    def _generate_recommendations(
        alerts: List[Alert],
        active_injuries: List[Dict],
        overall_level: AlertLevel,
    ) -> List[str]:
        recs = []
        for alert in alerts:
            recs.append(alert.action_required)
        if overall_level in [AlertLevel.ORANGE, AlertLevel.RED]:
            recs.append("Sesión de recuperación activa recomendada.")
        if active_injuries:
            zones = [i.get("zone") for i in active_injuries if i.get("zone")]
            if zones:
                recs.append(f"Zonas activas a evitar: {', '.join(zones)}")
        return recs

    @staticmethod
    def _forecast_risk(alerts: List[Alert], active_injuries: List[Dict]) -> float:
        score = 0.0
        for alert in alerts:
            if alert.level == AlertLevel.YELLOW:
                score += 0.15
            elif alert.level == AlertLevel.ORANGE:
                score += 0.30
            elif alert.level == AlertLevel.RED:
                score += 0.50
        for injury in active_injuries:
            pain = injury.get("pain_level", 0)
            score += (pain / 10.0) * 0.4
        return min(1.0, score)

    @staticmethod
    def generate_recovery_session(
        alert_level: AlertLevel,
        injury_history: Optional[List[Dict]] = None,
    ) -> RecoverySession:
        if alert_level == AlertLevel.GREEN:
            return RecoverySession(
                session_type="no_recovery_needed",
                duration_min=0,
                message="Sin alertas activas. Continúa con tu plan normal.",
                exercises=[],
                alert_level=AlertLevel.GREEN,
            )

        if alert_level == AlertLevel.YELLOW:
            exercises = [
                "McGill Big 3 (Bird Dog, Dead Bug, Side Plank) — 2×10",
                "Foam rolling cuerpo completo — 15min",
                "Movilidad de cadera — 5min",
                "Caminata suave — 10min",
            ]
            return RecoverySession(
                session_type="active_recovery",
                duration_min=30,
                exercises=exercises,
                message="Recuperación activa. Movimiento suave Only.",
                alert_level=AlertLevel.YELLOW,
            )

        if alert_level == AlertLevel.ORANGE:
            exercises = [
                "McGill Big 3 (Bird Dog, Dead Bug, Side Plank) — 2×8",
                "Foam rolling zonas tensionadas — 10min",
                "Movilidad articular general — 10min",
                "Estiramientos estáticos suaves — 10min",
            ]
            return RecoverySession(
                session_type="active_recovery",
                duration_min=30,
                exercises=exercises,
                message="Recuperación activa. Nada de carga. Solo movilidad y McGill.",
                alert_level=AlertLevel.ORANGE,
            )

        return RecoverySession(
            session_type="complete_rest",
            duration_min=0,
            message="Descanso total. Hidratación, sueño y nutrición son tu entrenamiento hoy.",
            optional=[
                "Baño frío 10min",
                "Sauna 15min si disponible",
                "Masaje suave",
            ],
            alert_level=AlertLevel.RED,
        )

    @staticmethod
    def report_pain(
        db: Session,
        user_id: str,
        zone: str,
        pain_level: int,
        pain_type: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        if pain_level >= 8:
            message = (
                f"Dolor agudo ({pain_level}/10) en {zone}. "
                "Consulta a un profesional médico antes de continuar entrenando."
            )
        else:
            message = (
                f"Dolor reportado: {pain_type} {pain_level}/10 en {zone}. "
                "ATLAS ajustará tu plan para evitar esta zona."
            )

        content = f"{pain_type.title()} en {zone.replace('_', ' ')}, nivel {pain_level}/10"
        if notes:
            content += f". Notas: {notes}"

        zone_lower = zone.lower()
        affected_muscles = BODY_ZONES.get(zone_lower, [])

        memory = MemoryService.add_memory(
            db,
            user_id,
            memory_type="injury",
            content=content,
            importance=max(7, min(10, pain_level)),
            source="user_report",
            tags=["injury", zone_lower, pain_type, f"pain_level_{pain_level}"] + affected_muscles,
            skip_duplicates=False,
        )

        injury_data = {
            "zone": zone_lower,
            "pain_level": pain_level,
            "pain_type": pain_type,
            "notes": notes,
            "date": date.today().isoformat(),
            "memory_id": memory.id if memory else None,
        }

        InjuryPreventionService._schedule_followup_reminders(db, user_id, zone_lower, memory)

        return {
            "status": "saved",
            "injury": injury_data,
            "message": message,
            "zones_to_avoid": [zone_lower] + affected_muscles[:3],
        }

    @staticmethod
    def _schedule_followup_reminders(
        db: Session, user_id: str, zone: str, memory
    ):
        if memory:
            for days in [7, 14, 30]:
                follow_date = (date.today() + timedelta(days=days)).isoformat()
                MemoryService.add_memory(
                    db,
                    user_id,
                    memory_type="injury_followup",
                    content=f"Seguimiento de lesión en {zone.replace('_', ' ')} - día {days}",
                    importance=5,
                    memory_date=follow_date,
                    source="auto",
                    tags=["injury_followup", zone],
                    skip_duplicates=True,
                )

    @staticmethod
    def get_injury_history(
        db: Session, user_id: str, active_only: bool = False
    ) -> List[Dict]:
        query = (
            db.query(AtlasMemory)
            .filter(
                AtlasMemory.user_id == user_id,
                AtlasMemory.type.in_(["injury", "injury_followup"]),
            )
            .order_by(AtlasMemory.date.desc())
        )

        injuries = []
        for m in query.all():
            pain_level = 0
            for tag in (m.tags or []):
                if tag.startswith("pain_level_"):
                    try:
                        pain_level = int(tag.split("_")[-1])
                    except ValueError:
                        pass

            zone = None
            for z in BODY_ZONES:
                if z in (m.tags or []):
                    zone = z

            is_active = (
                pain_level >= 5
                and m.type == "injury"
                and (
                    date.today() - date.fromisoformat(m.date)
                ).days <= 30
            )

            if active_only and not is_active:
                continue

            injuries.append(
                {
                    "id": m.id,
                    "date": m.date,
                    "zone": zone,
                    "content": m.content,
                    "pain_level": pain_level,
                    "type": m.type,
                    "importance": m.importance,
                    "tags": m.tags or [],
                    "is_active": is_active,
                }
            )

        return injuries

    @staticmethod
    def get_zone_exercises(zone: str) -> List[str]:
        return ZONE_TO_EXERCISES.get(zone.lower(), [])

    @staticmethod
    def resolve_body_zone(pain_description: str) -> Optional[str]:
        desc = pain_description.lower()
        zone_mapping = {
            "cuello": "neck",
            "neck": "neck",
            "hombro": "shoulder_right",
            "shoulder": "shoulder_right",
            "hombro izquierdo": "shoulder_left",
            "left shoulder": "shoulder_left",
            "right shoulder": "shoulder_right",
            "espalda alta": "upper_back",
            "upper back": "upper_back",
            "espalda baja": "lower_back",
            "lower back": "lower_back",
            "lumbar": "lower_back",
            "codo": "elbow_right",
            "elbow": "elbow_right",
            "codo izquierdo": "elbow_left",
            "left elbow": "elbow_left",
            "right elbow": "elbow_right",
            "muñeca": "wrist_right",
            "wrist": "wrist_right",
            "muñeca izquierda": "wrist_left",
            "left wrist": "wrist_left",
            "right wrist": "wrist_right",
            "pecho": "chest",
            "chest": "chest",
            "abdomen": "core",
            "core": "core",
            "cadera": "hip_right",
            "hip": "hip_right",
            "cadera izquierda": "hip_left",
            "left hip": "hip_left",
            "right hip": "hip_right",
            "rodilla": "knee_right",
            "knee": "knee_right",
            "rodilla izquierda": "knee_left",
            "left knee": "knee_left",
            "right knee": "knee_right",
            "tobillo": "ankle_right",
            "ankle": "ankle_right",
            "tobillo izquierdo": "ankle_left",
            "left ankle": "ankle_left",
            "right ankle": "ankle_right",
            "mano": "hand_right",
            "hand": "hand_right",
            "left hand": "hand_left",
            "right hand": "hand_right",
        }
        return zone_mapping.get(desc, None)

    @staticmethod
    def apply_recovery_mode(weekly_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a weekly plan structure to recovery-only mode.
        Used by the planner when alert level is ORANGE or RED.
        """
        recovery_sessions = []
        for session in weekly_structure.get("sessions", []):
            recovery_sessions.append({
                "day": session.get("day", 0),
                "name": "RECUPERACIÓN ACTIVA",
                "focus": "recovery",
                "is_recovery": True,
                "exercises": [
                    {"name": "McGill Big 3 (Bird Dog)", "sets": 2, "reps": "10", "side": "alternating"},
                    {"name": "McGill Big 3 (Dead Bug)", "sets": 2, "reps": "10", "side": "alternating"},
                    {"name": "McGill Big 3 (Side Plank)", "sets": 2, "duration": "30s", "side": "each"},
                    {"name": "Foam Rolling", "sets": 1, "duration": "10min"},
                    {"name": "Movilidad Articular", "sets": 1, "duration": "10min"},
                    {"name": "Caminata Suave", "sets": 1, "duration": "10-15min"},
                ],
            })
        return {
            "name": "Recovery Week",
            "sessions": recovery_sessions,
            "note": "Modo recuperación activa por alerta de sobreentrenamiento/lesión",
        }