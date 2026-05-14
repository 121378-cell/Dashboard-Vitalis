import logging
import re
import threading
import time
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from openai import OpenAI
from app.core.config import settings
from app.services.memory_service import MemoryService

logger = logging.getLogger("app.services.ai_service")


class ThreadSafeCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            self._cache[key] = value

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

MASTER_SYSTEM_PROMPT = """Eres ATLAS, el Director Deportivo de IA de {athlete_name}. NO eres un asistente pasivo.

IDENTIDAD CORE:
- Eres el guardián del PROYECTO 31/07: {athlete_name} debe llegar al 31 de Julio en su mejor forma histórica.
- Tono: Directo, basado en datos, exigente pero leal. Si los datos sugieren descanso, lo dictas como orden profesional, no como sugerencia.
- Edad del atleta: {athlete_age} años — ajusta recuperación y volumen en consecuencia. Un atleta de 47 años NO recupera como uno de 25.
- PROACTIVIDAD: Analiza los datos de Garmin proporcionados. Si {athlete_name} no llega a sus {step_target} pasos, comunícalo con firmeza. Si su HRV es excelente, empújale a sesión de fuerza de alta intensidad.

REGLAS ABSOLUTAS:
1. NUNCA respondas "Como modelo de lenguaje..." o "No tengo acceso a...". Si no tienes un dato, di qué dato falta y qué decisión tomarías al respecto.
2. NUNCA des respuestas genéricas sin datos del atleta. Cada recomendación debe estar anclada a métricas reales.
3. MÁXIMO 150 PALABRAS por respuesta. Sé quirúrgico. Emojis funcionales solo (📊🟢🟡🔴⚡🛡️).
4. Cuando generes un entrenamiento, USA SIEMPRE los marcadores 'json_session_start' y 'json_session_end' con JSON editable por filas.
5. Usa ÚNICAMENTE nombres de ejercicios de la lista HEVY para que el usuario pueda registrarlos sin problemas.

GUARDIA BIOMÉTRICA (OBLIGATORIO):
- Readiness < 55 o HRV bajo baseline → ABORTAR fuerza, dictar Recuperación Activa o Descanso.
- Alerta de lesión activa → EVITAR zonas lesionadas, proponer alternativas.
- Dolor agudo reportado (≥8) → CONSULTA MÉDICA inmediata. ATLAS no diagnostica.
- Lesiones son PERMANENTES en memoria — nunca las ignores.

METODOLOGÍA:
- Sobrecarga Progresiva como motor principal.
- Protocolos McGill para salud espinal y recuperación.
- Intensidad Stoppani para periodización.
- NEAT: {step_target} pasos/día como motor de composición corporal.
- Hitos: Banca 50kg / Prensa 100kg.

MODO DE CONVERSACIÓN ACTUAL: {conversation_mode}
{mode_instructions}

CONTEXTO REAL DE HOY ({today_date}):
{biometrics_context}
{injury_context}
{readiness_context}
{acwr_context}
{workouts_context}
{plan_context}
{memory_context}

PERFIL DEL ATLETA:
{profile_context}

BIBLIA DE EJERCICIOS HEVY:
{exercise_context}
ORDEN: Usa ÚNICAMENTE nombres de ejercicios de la lista HEVY.

PROTOCOLO DE ADAPTABILIDAD CONTINUA:
1. ALINEACIÓN: Cada sesión debe ser un peldaño hacia el Proyecto 31/07.
2. GUARDIA BIOMÉTRICA: Si el Readiness Score es < 55 o el HRV está por debajo de su baseline, DEBES abortar el plan de fuerza.
3. ESCUCHA ACTIVA: Si {athlete_name} menciona cansancio o dolor, ajusta la rutina de inmediato.
4. FORMATO: Entrenamientos SIEMPRE con 'json_session_start' y 'json_session_end'.

DISEÑO DE SESIÓN: Diseña rutinas con sobrecarga progresiva, 100% coherentes con el estado físico real de hoy."""

MODE_INSTRUCTIONS = {
    "analysis": """INSTRUCCIÓN DE MODO: {athlete_name} quiere un ANÁLISIS de sus datos.
- Desglosa métricas clave con comparación a baseline.
- Señala tendencias (mejorando/estable/empeorando).
- Concluye con 1-2 acciones concretas basadas en los datos.
- Usa formato: métrica → interpretación → acción.""",

    "planning": """INSTRUCCIÓN DE MODO: {athlete_name} quiere un PLAN o ENTRENAMIENTO.
- Diseña la sesión basándote en: readiness actual, lesiones activas, ACWR, y objetivo 31/07.
- Si readiness < 55 → dicta recuperación activa (McGill, movilidad, caminata).
- Si readiness ≥ 70 → sesión de fuerza con sobrecarga progresiva.
- INCLUYE siempre: ejercicios, series, reps, RPE objetivo, duración estimada.
- Usa marcadores json_session_start / json_session_end.""",

    "motivation": """INSTRUCCIÓN DE MODO: {athlete_name} necesita MOTIVACIÓN.
- Reconoce su esfuerzo con datos reales (rachas, PRs, volumen).
- Conecta el día a día con la visión del 31 de Julio.
- Sé intenso pero no vacío — cita métricas, no frases hechas.
- 3-4 frases máximo. Impacto sobre cantidad.""",

    "alert": """INSTRUCCIÓN DE MODO: ALERTA ACTIVA — datos biométricos en zona de riesgo.
- Comunica el problema con urgencia profesional, no alarma innecesaria.
- Especifica qué métrica está fuera de rango y cuánto.
- Dicta la acción (descanso, recuperación activa, consulta médica si dolor ≥8).
- NO propongas entrenamiento de fuerza bajo ninguna circunstancia.""",

    "celebration": """INSTRUCCIÓN DE MODO: {athlete_name} ha logrado algo destacable.
- Celebra con datos concretos (PR, racha, readiness alto, HRV excepcional).
- Conecta el logro con la trayectoria hacia el 31/07.
- Sugiere cómo capitalizar este estado (ej: hoy es día de intensidad máxima).
- 2-3 frases. Contundente.""",
}

_prompt_cache = ThreadSafeCache()
_coach_context_cache = ThreadSafeCache()
_welcome_cache = ThreadSafeCache()


def _cache_key(user_id: str) -> str:
    return f"atlas_prompt_{user_id}"


FALLBACK_SYSTEM_PROMPT = """Eres ATLAS, el Director Deportivo de IA de Sergi. NO eres un asistente pasivo.

IDENTIDAD CORE:
- Eres el guardián del PROYECTO 31/07: Sergi debe llegar al 31 de Julio en su mejor forma histórica.
- Tono: Directo, basado en datos, exigente pero leal.
- Edad del atleta: 47 años — ajusta recuperación y volumen en consecuencia.
- ATENCIÓN: Sergi usa un Forerunner 245 que NO mide HRV. NUNCA menciones HRV como dato disponible.

LIMITACIONES HONESTAS:
- NUNCA menciones HRV como métrica disponible — el dispositivo del atleta (FR245) no lo mide.
- Usa Body Battery y FC Reposo como indicadores de recuperación.
- Si no tienes un dato, di qué dato falta y qué decisión tomarías.

REGLAS ABSOLUTAS:
1. NUNCA respondas "Como modelo de lenguaje..." o "No tengo acceso a...". Si no tienes un dato, di qué dato falta y qué decisión tomarías al respecto.
2. NUNCA des respuestas genéricas sin datos del atleta. Cada recomendación debe estar anclada a métricas reales.
3. MÁXIMO 150 PALABRAS por respuesta. Sé quirúrgico. Emojis funcionales solo (📊🟢🟡🔴⚡🛡️).
4. Cuando generes un entrenamiento, USA SIEMPRE los marcadores 'json_session_start' y 'json_session_end' con JSON editable por filas.
5. Usa ÚNICAMENTE nombres de ejercicios de la lista HEVY para que el usuario pueda registrarlos sin problemas.

PERFIL DEL ATLETA: Sergi, 47 años. FC Reposo: 45.5bpm. Sueño crónico: 6.15h. Body Battery medio: 70.5. 560 actividades registradas. Deporte principal: strength_training. Objetivo: Proyecto 31/07."""


def build_coach_context(db, user_id: str = "default_user") -> Dict[str, Any]:
    """
    Build comprehensive coach context from ALL services on EVERY chat message.
    Each data block in independent try/except — never breaks chat if any service fails.
    Falls back to FALLBACK_SYSTEM_PROMPT if ALL services fail.
    Returns dict with: prompt, readiness_score, athlete_name, athlete_age, step_target,
                       bio_summary, injury_summary, context_meta (for frontend indicator).
    """
    today_str = date.today().isoformat()
    now = datetime.now()
    athlete_name = "Sergi"
    athlete_age = "47"
    step_target = "20.000"
    readiness_score = None
    bio_summary = ""
    injury_summary = "clear"
    context_blocks = {}
    context_meta = {"data_freshness": None, "plan_active": False, "plan_progress": None,
                    "unread_insights": 0, "readiness_score": None, "readiness_color": "gray"}

    # ── Block 1: Athletic Intelligence Profile (30min cache) ──
    profile_context = ""
    profile_data = {}
    try:
        from app.services.athletic_intelligence_service import AthleticIntelligenceService
        ai_cache_key = f"atlas_profile_{user_id}"
        ai_cached = _coach_context_cache.get(ai_cache_key)
        if ai_cached and (now - ai_cached["ts"]).total_seconds() < 1800:
            profile_data = ai_cached["result"]
        else:
            profile_data = AthleticIntelligenceService.get_full_athletic_profile(db, user_id)
            _coach_context_cache.set(ai_cache_key, {"result": profile_data, "ts": now})

        identity = profile_data.get("athlete_identity", {})
        athlete_name = identity.get("name", "Sergi")
        age_val = identity.get("age")
        if age_val:
            athlete_age = str(age_val)

        coach_summary = profile_data.get("coach_context_summary", "")
        if coach_summary:
            profile_context = f"--- PERFIL DEL ATLETA ---\n{coach_summary}"
    except Exception as e:
        logger.warning(f"build_coach_context: AthleticIntelligence failed: {e}")

    # ── Block 2: Daily Loop (readiness + today status) ──
    readiness_context = ""
    daily_data = {}
    try:
        from app.services.daily_loop_service import DailyLoopService
        daily_data = DailyLoopService.run_daily_loop(db, user_id)
        if not daily_data.get("error"):
            readiness_score = daily_data.get("readiness_score", 50)
            category = daily_data.get("readiness_category", "moderate")
            color = daily_data.get("readiness_color", "yellow")
            components = daily_data.get("components", {})
            session_data = daily_data.get("today_session")

            bb_val = components.get("body_battery", {}).get("value")
            rhr_val = components.get("resting_hr", {}).get("value")
            sleep_val = components.get("sleep", {}).get("value")
            stress_val = components.get("stress", {}).get("value")
            bio_source = daily_data.get("biometrics_source", "partial")

            readiness_context = f"""--- READINESS ({today_str}) ---
Puntuación: {readiness_score}/100 — Estado: {category.upper()}
Body Battery: {bb_val if bb_val is not None else 'N/A'} | FC Reposo: {rhr_val if rhr_val is not None else 'N/A'}bpm | Sueño: {sleep_val if sleep_val is not None else 'N/A'}h | Estrés: {stress_val if stress_val is not None else 'N/A'}/100
Fuente de datos: {bio_source}"""

            if session_data and session_data.get("planned"):
                sp = session_data["planned"]
                adapt = session_data.get("adaptation", {})
                readiness_context += f"\nSesión planificada: {sp.get('title', 'N/A')} ({sp.get('duration_minutes', '?')}min, intensidad {sp.get('intensity', '?')})"
                if adapt.get("suggestion") != "mantener":
                    readiness_context += f"\n⚡ Adaptación: {adapt.get('note', '')}"

            context_meta["readiness_score"] = readiness_score
            context_meta["readiness_color"] = color
            context_meta["data_freshness"] = f"{bio_source} {now.strftime('%H:%M')}"

            if bb_val is not None and rhr_val is not None:
                bio_summary = f"BB:{bb_val} FCR:{rhr_val}"
    except Exception as e:
        logger.warning(f"build_coach_context: DailyLoop failed: {e}")

    # ── Block 3: Training Plan ──
    plan_context = ""
    try:
        from app.services.training_plan_service import TrainingPlanService
        current_plan = TrainingPlanService.get_current_plan(db, user_id)
        if current_plan:
            progress = current_plan.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 7)
            week_obj = current_plan.get("week_start", "")
            goal = current_plan.get("plan_data", {}).get("weekly_goal", "N/A")
            plan_context = f"""--- PLAN DE ENTRENAMIENTO ACTIVO ---
Semana: {week_obj}
Objetivo: {goal}
Progreso: {completed}/{total} sesiones completadas"""

            today_session = None
            for s in current_plan.get("plan_data", {}).get("sessions", []):
                if s.get("date") == today_str:
                    today_session = s
                    break
            if today_session:
                plan_context += f"\nHoy: {today_session.get('title', 'N/A')} ({today_session.get('session_type', '?')}, {today_session.get('duration_minutes', '?')}min)"
                completed_today = today_session.get("completed", False)
                plan_context += f" — {'✅ Completada' if completed_today else '⏳ Pendiente'}"

            context_meta["plan_active"] = True
            context_meta["plan_progress"] = f"{completed}/{total}"
        else:
            plan_context = "No hay plan de entrenamiento activo para esta semana."
    except Exception as e:
        logger.warning(f"build_coach_context: TrainingPlan failed: {e}")

    # ── Block 4: Recent 5 Activities ──
    workouts_context = ""
    try:
        from app.models.workout import Workout
        recent_workouts = db.query(Workout).filter(
            Workout.user_id == user_id
        ).order_by(Workout.date.desc()).limit(5).all()

        if recent_workouts:
            w_lines = ["--- ENTRENAMIENTOS RECIENTES ---"]
            for w in recent_workouts:
                try:
                    metrics = json.loads(w.description) if w.description else {}
                    sport = metrics.get("sport", "actividad").replace("_", " ")
                    info = f"- {w.date.strftime('%d/%m') if hasattr(w.date, 'strftime') else w.date}: {w.name} ({sport})"
                    dist = metrics.get("distance", 0)
                    if dist:
                        info += f" {round(dist/1000, 2)}km"
                    dur = w.duration
                    if dur:
                        info += f" {round(dur/60, 0)}min"
                    cal = w.calories
                    if cal:
                        info += f" {cal}kcal"
                    w_lines.append(info)
                except Exception as e:
                    logger.debug(f"build_coach_context: Workout parse failed for '{w.name}': {e}")
                    w_lines.append(f"- {w.name}")
            workouts_context = "\n".join(w_lines)
        else:
            workouts_context = "No se han registrado entrenamientos recientes."
    except Exception as e:
        logger.warning(f"build_coach_context: Recent workouts failed: {e}")

    # ── Block 5: Unread Notifications (limit 3) ──
    insights_context = ""
    try:
        from app.services.notification_service import NotificationService
        unread = NotificationService.get_unread(db, limit=3)
        if unread:
            i_lines = ["--- INSIGHTS PENDIENTES ---"]
            for n in unread:
                emoji = "🔴" if n.get("priority") == "urgent" else "🟡" if n.get("priority") == "high" else "📊"
                i_lines.append(f"{emoji} {n['title']}: {n['message'][:100]}")
            insights_context = "\n".join(i_lines)
            context_meta["unread_insights"] = len(unread)
    except Exception as e:
        logger.warning(f"build_coach_context: Notifications failed: {e}")

    # ── Block 6: Injury Prevention ──
    injury_context = ""
    try:
        from app.services.injury_prevention_service import InjuryPreventionService
        injury_status = InjuryPreventionService.get_current_status(db, user_id)
        injury_dict = injury_status.to_dict() if hasattr(injury_status, "to_dict") else {}
        alert_level = injury_dict.get("alert_level", "optimal")
        active_injuries = injury_dict.get("active_injuries", [])
        zones_to_avoid = injury_dict.get("zones_to_avoid", [])
        alerts = injury_dict.get("alerts", [])

        if active_injuries or alert_level != "optimal":
            parts = [f"--- ALERTA DE LESIÓN: {alert_level.upper()} ---"]
            for a in alerts:
                parts.append(f"{'🔴' if a['level'] == 'stop' else '🟡' if a['level'] == 'caution' else '🟠'} {a['reason']} → {a['action_required']}")
            for inj in active_injuries:
                parts.append(f"🩹 Lesión activa: {inj.get('zone', 'N/A')} — {inj.get('content', '')}")
            if zones_to_avoid:
                parts.append(f"Zonas a evitar: {', '.join(zones_to_avoid)}")
            injury_context = "\n".join(parts)
            injury_summary = "active_injury"
        else:
            injury_context = "Sin lesiones activas. Estado de prevención: ÓPTIMO 🟢"
    except Exception as e:
        logger.warning(f"build_coach_context: InjuryPrevention failed: {e}")

    # ── Block 7: ACWR ──
    acwr_context = ""
    try:
        from app.services.analytics_service import AnalyticsService
        acwr = AnalyticsService.calculate_acwr(db, user_id)
        acwr_context = f"""--- CARGA DE ENTRENAMIENTO (ACWR) ---
Ratio: {acwr.get('ratio', 1.0)} — Estado: {acwr.get('status', 'mantenimiento').upper()}
{acwr.get('message', '')}"""
    except Exception as e:
        logger.warning(f"build_coach_context: ACWR failed: {e}")

    # ── Block 8: Memory ──
    memory_context = ""
    try:
        memory_context = MemoryService.get_memory_context_string(db, user_id, max_tokens=1500)
    except Exception as e:
        logger.warning(f"build_coach_context: Memory failed: {e}")

    # ── Block 9: Exercise list ──
    exercise_context = ""
    try:
        from app.services.exercise_service import ExerciseService
        exercise_context = ExerciseService.get_context_summary()
    except Exception as e:
        logger.warning(f"build_coach_context: Exercise list failed: {e}")

    # ── Assemble full prompt ──
    all_blocks = [readiness_context, injury_context, acwr_context, workouts_context,
                  plan_context, insights_context, memory_context]
    has_any_data = any(block.strip() for block in all_blocks)

    if not has_any_data and not profile_context:
        prompt = FALLBACK_SYSTEM_PROMPT
    else:
        mode_inst_placeholder = "{mode_instructions}"
        prompt = MASTER_SYSTEM_PROMPT.format(
            athlete_name=athlete_name,
            athlete_age=athlete_age,
            step_target=step_target,
            conversation_mode="{conversation_mode}",
            mode_instructions=mode_inst_placeholder,
            today_date=today_str,
            biometrics_context=readiness_context if readiness_context else "Datos biométricos no disponibles para hoy.",
            injury_context=injury_context if injury_context else "Sin datos de lesión.",
            readiness_context="",
            acwr_context=acwr_context if acwr_context else "Datos ACWR no disponibles.",
            workouts_context=workouts_context if workouts_context else "Sin entrenamientos recientes.",
            plan_context=plan_context if plan_context else "",
            memory_context=memory_context if memory_context else "",
            profile_context=profile_context if profile_context else f"Atleta: {athlete_name}, {athlete_age} años. Objetivo: Proyecto 31/07.",
            exercise_context=exercise_context if exercise_context else "",
        )

    if readiness_score is None:
        readiness_score = 50

    return {
        "prompt": prompt,
        "athlete_name": athlete_name,
        "athlete_age": athlete_age,
        "step_target": step_target,
        "readiness_score": readiness_score,
        "bio_summary": bio_summary,
        "injury_summary": injury_summary,
        "context_meta": context_meta,
    }


def generate_welcome_message(db, user_id: str = "default_user") -> Dict[str, Any]:
    """Generate a personalized welcome message from ATLAS. Cached 15min."""
    now = datetime.now()
    cache_key = f"welcome_{user_id}"
    cached = _welcome_cache.get(cache_key)
    if cached and (now - cached["ts"]).total_seconds() < 900:
        return cached["result"]

    try:
        context_result = build_coach_context(db, user_id)
        meta = context_result.get("context_meta", {})
        readiness = meta.get("readiness_score")
        plan_active = meta.get("plan_active", False)
        plan_progress = meta.get("plan_progress")

        hour = now.hour
        if hour < 12:
            greeting = "Buenos días"
        elif hour < 18:
            greeting = "Buenas tardes"
        else:
            greeting = "Buenas noches"

        parts = [f"{greeting}, {context_result['athlete_name']}."]

        if readiness is not None:
            if readiness >= 70:
                parts.append(f"Readiness {readiness}/100 🟢 — estás listo para entrenar con intensidad.")
            elif readiness >= 50:
                parts.append(f"Readiness {readiness}/100 🟡 — sesión moderada recomendada.")
            else:
                parts.append(f"Readiness {readiness}/100 🔴 — prioriza recuperación hoy.")

        if plan_active and plan_progress:
            parts.append(f"Plan activo: {plan_progress} ✓")

        unread = meta.get("unread_insights", 0)
        if unread > 0:
            parts.append(f"Tienes {unread} insight{'s' if unread > 1 else ''} sin revisar.")

        parts.append("¿En qué te puedo ayudar?")

        welcome_msg = " ".join(parts)
    except Exception as e:
        logger.warning(f"generate_welcome_message failed, using fallback: {e}")
        welcome_msg = "Hola, Sergi. Soy ATLAS, tu Director Deportivo. ¿En qué te puedo ayudar?"

    result = {"message": welcome_msg, "generated_at": now.isoformat()}
    _welcome_cache.set(cache_key, {"result": result, "ts": now})
    return result


def detect_conversation_mode(message: str, biometrics_context: str, injury_context: str, readiness_score: Optional[int] = None) -> str:
    msg = message.lower()

    if injury_context and ("dolor" in msg or "lesion" in msg or "duele" in msg or "molestia" in msg):
        return "alert"
    if readiness_score is not None and readiness_score < 40:
        return "alert"
    if "🔴" in biometrics_context or "alerta" in biometrics_context.lower() or "crítico" in biometrics_context.lower():
        return "alert"

    celebration_keywords = ["récord", "record", "pr", "pr personal", "logr", "conseguí", "consegui", "llegué a", "llegue a", "supera", "mejor marca", "hit"]
    if any(kw in msg for kw in celebration_keywords):
        return "celebration"

    planning_keywords = ["entreno", "sesión", "workout", "entrena", "ejercicio hoy", "rutina", "plan", "programa", "hacer hoy", "gym", "entrenar", "fuerza hoy", "cardio hoy"]
    if any(kw in msg for kw in planning_keywords):
        return "planning"

    analysis_keywords = ["análisis", "analisis", "cómo estoy", "como estoy", "datos", "métricas", "metricas", "readiness", "hrv", "carga", "acwr", "progreso", "tendencia", "estado"]
    if any(kw in msg for kw in analysis_keywords):
        return "analysis"

    motivation_keywords = ["motiv", "ánimo", "animo", "cansado", "perezoso", "no puedo", "difícil", "costó", "perez", "vago", "quiero dejar", "no tengo ganas"]
    if any(kw in msg for kw in motivation_keywords):
        return "motivation"

    if readiness_score is not None and readiness_score >= 80:
        return "planning"

    if readiness_score is not None and readiness_score < 55:
        return "analysis"

    return "analysis"


def build_atlas_system_prompt(db, user_id: str) -> Dict[str, Any]:
    from app.services.injury_prevention_service import InjuryPreventionService
    from app.services.readiness_service import ReadinessService
    from app.services.analytics_service import AnalyticsService
    from app.services.athlete_profile_service import AthleteProfileService
    from app.services.exercise_service import ExerciseService
    from app.models.biometrics import Biometrics
    from app.models.workout import Workout
    from app.models.session import TrainingSession
    import json

    key = _cache_key(user_id)
    cached = _prompt_cache.get(key)
    if cached and (datetime.now() - cached["ts"]).total_seconds() < 300:
        return cached["result"]

    today_str = date.today().isoformat()

    athlete_name = "Sergi"
    athlete_age = "47"
    step_target = "20.000"

    try:
        from app.models.user import User
        user_obj = db.query(User).filter(User.id == user_id).first()
        if user_obj and user_obj.name:
            athlete_name = user_obj.name
    except Exception as e:
        logger.debug(f"build_atlas_system_prompt: User lookup failed: {e}")

    try:
        profile_summary = AthleteProfileService.get_profile_summary(user_id, db)
        if profile_summary and "Perfil no disponible" not in profile_summary:
            import re as _re
            age_match = _re.search(r'(\d+)\s*años', profile_summary)
            if age_match:
                athlete_age = age_match.group(1)
            steps_match = _re.search(r'([\d.,]+)\s*pasos/día', profile_summary)
            if steps_match:
                step_target = steps_match.group(1).replace(",", ".")
    except Exception as e:
        logger.debug(f"build_atlas_system_prompt: AthleteProfileService failed: {e}")

    readiness_result = ReadinessService.calculate(db, user_id)
    readiness_score = readiness_result.get("score") or 50
    readiness_status = readiness_result.get("status", "moderate")
    readiness_rec = readiness_result.get("recommendation", "")
    baseline = readiness_result.get("baseline", {})

    readiness_context = f"""--- READINESS ({today_str}) ---
Puntuación: {readiness_score}/100 — Estado: {readiness_status.upper()}
Recomendación: {readiness_rec}
Baseline personal: HRV {baseline.get('hrv_mean', 'N/A')}ms | FCR {baseline.get('rhr_mean', 'N/A')}bpm | Sueño {baseline.get('sleep_mean', 'N/A')}h"""

    today_bio = db.query(Biometrics).filter(
        Biometrics.user_id == user_id, Biometrics.date == today_str
    ).first()

    if today_bio and today_bio.data:
        bio_data = json.loads(today_bio.data)
        hr = bio_data.get("heartRate", 0)
        hrv = bio_data.get("hrv", 0)
        sleep = bio_data.get("sleep", 0)
        steps = bio_data.get("steps", 0)
        stress = bio_data.get("stress", 0)

        hrv_baseline_val = baseline.get("hrv_mean") or 0
        rhr_baseline_val = baseline.get("rhr_mean") or 0

        biometrics_context = f"""--- BIOMÉTRICOS DE HOY ({today_str}) ---
FC Reposo: {hr} ppm (Baseline: {rhr_baseline_val} ppm)
HRV: {hrv} ms (Baseline: {hrv_baseline_val} ms)
Sueño: {sleep}h | Estrés: {stress}/100 | Pasos: {steps}"""

        if hrv_baseline_val > 0 and hrv > 0:
            diff = hrv - hrv_baseline_val
            if diff < -10:
                biometrics_context += "\n🔴 AVISO: HRV significativamente bajo — posible fatiga o inicio de enfermedad."
            elif diff > 10:
                biometrics_context += "\n🟢 HRV por encima de la media — recuperación excelente."
    else:
        biometrics_context = "No hay datos biométricos disponibles para hoy. Usa baselines históricos si están disponibles."

    injury_status = InjuryPreventionService.get_current_status(db, user_id)
    injury_dict = injury_status.to_dict() if hasattr(injury_status, "to_dict") else {}
    alert_level = injury_dict.get("alert_level", "optimal")
    active_injuries = injury_dict.get("active_injuries", [])
    zones_to_avoid = injury_dict.get("zones_to_avoid", [])
    alerts = injury_dict.get("alerts", [])

    if active_injuries or alert_level != "optimal":
        parts = [f"--- ALERTA DE LESIÓN: {alert_level.upper()} ---"]
        for a in alerts:
            parts.append(f"{'🔴' if a['level'] == 'stop' else '🟡' if a['level'] == 'caution' else '🟠'} {a['reason']} → {a['action_required']}")
        if active_injuries:
            for inj in active_injuries:
                parts.append(f"🩹 Lesión activa: {inj.get('zone', 'N/A')} — {inj.get('content', '')}")
        if zones_to_avoid:
            parts.append(f"Zonas a evitar: {', '.join(zones_to_avoid)}")
        injury_context = "\n".join(parts)
    else:
        injury_context = "Sin lesiones activas. Estado de prevención: ÓPTIMO 🟢"

    acwr = AnalyticsService.calculate_acwr(db, user_id)
    acwr_context = f"""--- CARGA DE ENTRENAMIENTO (ACWR) ---
Ratio: {acwr.get('ratio', 1.0)} — Estado: {acwr.get('status', 'mantenimiento').upper()}
{acwr.get('message', '')}"""

    recent_workouts = db.query(Workout).filter(
        Workout.user_id == user_id
    ).order_by(Workout.date.desc()).limit(5).all()

    if recent_workouts:
        w_lines = ["--- ENTRENAMIENTOS RECIENTES ---"]
        for w in recent_workouts[:3]:
            try:
                metrics = json.loads(w.description) if w.description else {}
                dist = metrics.get("distance", 0)
                sport = metrics.get("sport", "actividad").replace("_", " ")
                info = f"- {w.date.strftime('%d/%m') if hasattr(w.date, 'strftime') else w.date}: {w.name} ({sport}). "
                if dist:
                    info += f"Dist: {round(dist/1000, 2)}km. "
                info += f"Dur: {round(w.duration/60, 1)}min. Cal: {w.calories}."
                w_lines.append(info)
            except Exception as e:
                logger.debug(f"build_atlas_system_prompt: Workout parse failed for '{w.name}': {e}")
                w_lines.append(f"- {w.name}. Dur: {w.duration}s.")
        workouts_context = "\n".join(w_lines)
    else:
        workouts_context = "No se han registrado entrenamientos recientes."

    plan_context = ""
    try:
        today_session = db.query(TrainingSession).filter(
            TrainingSession.user_id == user_id,
            TrainingSession.date == today_str,
            TrainingSession.status.in_(["planned", "active"])
        ).first()
        if today_session and today_session.plan_json:
            plan = json.loads(today_session.plan_json)
            plan_context = f"""--- SESIÓN PLANIFICADA HOY ---
Nombre: {plan.get('session_name', 'N/A')}
Duración: {plan.get('estimated_duration_min', 0)}min
Ejercicios: {len(plan.get('exercises', []))}"""
    except Exception as e:
        logger.debug(f"build_atlas_system_prompt: Training session lookup failed: {e}")

    memory_context = MemoryService.get_memory_context_string(db, user_id, max_tokens=1500)

    try:
        profile_context = AthleteProfileService.get_profile_summary(user_id, db)
    except Exception as e:
        logger.debug(f"build_atlas_system_prompt: Profile summary failed: {e}")
        profile_context = f"Atleta: {athlete_name}, {athlete_age} años. Objetivo: Proyecto 31/07."

    exercise_context = ExerciseService.get_context_summary()

    conversation_mode = "analysis"

    mode_inst = MODE_INSTRUCTIONS.get(conversation_mode, "").format(athlete_name=athlete_name)

    prompt = MASTER_SYSTEM_PROMPT.format(
        athlete_name=athlete_name,
        athlete_age=athlete_age,
        step_target=step_target,
        conversation_mode=conversation_mode.upper(),
        mode_instructions=mode_inst,
        today_date=today_str,
        biometrics_context=biometrics_context,
        injury_context=injury_context,
        readiness_context=readiness_context,
        acwr_context=acwr_context,
        workouts_context=workouts_context,
        plan_context=plan_context,
        memory_context=memory_context,
        profile_context=profile_context,
        exercise_context=exercise_context,
    )

    bio_summary = ""
    if today_bio and today_bio.data:
        try:
            bd = json.loads(today_bio.data)
            bio_summary = f"HRV:{bd.get('hrv', 0)} FCR:{bd.get('heartRate', 0)}"
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"build_atlas_system_prompt: Bio data parse failed: {e}")
    injury_summary = "active_injury" if active_injuries else "clear"

    _prompt_cache.set(key, {
        "result": {
            "prompt": prompt,
            "athlete_name": athlete_name,
            "athlete_age": athlete_age,
            "step_target": step_target,
            "readiness_score": readiness_score,
            "bio_summary": bio_summary,
            "injury_summary": injury_summary,
        },
        "ts": datetime.now(),
    })

    cached = _prompt_cache.get(key)
    return cached["result"] if cached else {"prompt": prompt, "athlete_name": athlete_name, "athlete_age": athlete_age, "step_target": step_target, "readiness_score": readiness_score, "bio_summary": bio_summary, "injury_summary": injury_summary}

class AIService:
    def __init__(self):
        self.groq_client = None
        if settings.GROQ_API_KEY:
            self.groq_client = OpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
        
        self.gemini_client = None
        if settings.GEMINI_API_KEY:
            self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
        self.ollama_client = OpenAI(
            api_key="ollama",
            base_url=f"{settings.OLLAMA_BASE_URL}/v1"
        )

    @staticmethod
    def chat(messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Class method for direct chat with provider fallback."""
        service = AIService()
        content = service._generate_chat_response(messages, system_prompt)
        return content

    def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Simple prompt-based generation."""
        messages = [{"role": "user", "content": prompt}]
        res = self._generate_chat_response(messages, system_instruction)
        return res["content"]

    def _generate_chat_response(self, messages: List[Dict[str, str]], system_instruction: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # 1. Groq (llama-3.3-70b-versatile) — fastest, 10s timeout
        if self.groq_client:
            try:
                logger.info("Trying Groq AI provider...")
                content = self._generate_openai_compatible(
                    self.groq_client, "llama-3.3-70b-versatile", messages, system_instruction, timeout=10
                )
                logger.info(f"Groq responded in {time.time() - start_time:.1f}s")
                return {"content": content, "provider": "Groq"}
            except Exception as e:
                logger.warning(f"Groq failed: {e}")

        # 2. Gemini (gemini-2.0-flash) — fallback, 10s timeout
        if self.gemini_client:
            try:
                logger.info("Trying Gemini AI provider...")
                content = self._generate_gemini(messages, system_instruction)
                logger.info(f"Gemini responded in {time.time() - start_time:.1f}s")
                return {"content": content, "provider": "Gemini"}
            except Exception as e:
                logger.error(f"Gemini failed: {e}")

        # 3. Ollama local — offline fallback, 10s timeout
        if self._check_ollama_available():
            try:
                logger.info("Trying Ollama (local) AI provider...")
                content = self._generate_openai_compatible(
                    self.ollama_client, "llama3", messages, system_instruction, timeout=10
                )
                logger.info(f"Ollama responded in {time.time() - start_time:.1f}s")
                return {"content": content, "provider": "Ollama (Local)"}
            except Exception as e:
                logger.warning(f"Ollama failed: {e}")
        
        elapsed = time.time() - start_time
        logger.error(f"All AI providers failed after {elapsed:.1f}s")
        raise Exception("All AI providers failed. Please check your API keys or try again later.")

    def _check_ollama_available(self) -> bool:
        """Quick 2s check if Ollama is running."""
        try:
            import requests
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False

    def _generate_openai_compatible(self, client: OpenAI, model: str, messages: List[Dict], system_instruction: str = None, timeout: int = 30) -> str:
        full_messages = []
        if system_instruction:
            full_messages.append({"role": "system", "content": system_instruction})
        full_messages.extend(messages)
        
        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
            stream=False,
            timeout=timeout
        )
        return response.choices[0].message.content

    def _generate_gemini(self, messages: List[Dict], system_instruction: str = None) -> str:
        # Convert messages to Gemini format
        contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

        config = types.GenerateContentConfig(system_instruction=system_instruction)
        response = self.gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=config
        )
        return response.text

    @staticmethod
    def inject_memory_context(
        db: Session,
        user_id: str,
        base_system_prompt: str,
        max_tokens: int = 2000
    ) -> str:
        """
        Inject memory context into system prompt for personalized AI responses.
        
        This method retrieves the athlete's historical memories and adds them
        to the system prompt, enabling the AI to provide contextually-aware
        coaching that considers the athlete's history, injuries, patterns,
        and achievements.
        
        Args:
            db: Database session
            user_id: Athlete user ID
            base_system_prompt: Original system prompt without memory context
            max_tokens: Maximum tokens for memory context
            
        Returns:
            Enhanced system prompt with memory context injected
        """
        try:
            # Get memory context string
            memory_context = MemoryService.get_memory_context_string(
                db, user_id, max_tokens=max_tokens
            )
            
            if not memory_context:
                return base_system_prompt

            return base_system_prompt + memory_context
        except Exception as e:
            logger.error(f"Error injecting memory context: {e}")
            return base_system_prompt

    async def generate_morning_briefing(
        self, 
        db: Session, 
        user_id: str,
        readiness_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a morning briefing for a user.
        
        Args:
            db: Database session
            user_id: User ID
            readiness_result: Optional readiness result from readiness_service
            
        Returns:
            Dict containing briefing content with readiness_score and recommendation
        """
        try:
            # Get user's readiness score (use provided result or calculate)
            from app.services.readiness_service import ReadinessService
            if readiness_result is None:
                readiness_result = ReadinessService.calculate(db, user_id)
            
            # Get user's recent memories for context
            from app.services.memory_service import MemoryService
            memories = MemoryService.get_memory_context_string(
                db, user_id, max_tokens=1000
            )
            
            # Prepare prompt for AI
            system_prompt = """Eres un entrenador personal experto que proporciona un briefing matutino personalizado basado en los datos biométricos y el historial del atleta."""
            
            user_prompt = f"""
            Genera un briefing matutino personalizado para el atleta basado en:
            
            Puntuación de readiness: {readiness_result.get('score', 'N/A')}/100
            Estado: {readiness_result.get('status', 'N/A')}
            Componentes: {readiness_result.get('components', {})}
            
            Historial y contexto del atleta:
            {memories if memories else 'No hay datos históricos disponibles'}
            
            El briefing debe incluir:
            1. Una evaluación del estado físico y mental del día
            2. Una recomendación de entrenamiento específica
            3. Un mensaje motivacional
            
            Formato de respuesta como JSON con:
            {{
                "readiness_score": número (0-100),
                "status": string (excellent, good, moderate, poor, rest),
                "recommendation": string (recomendación de entrenamiento),
                "summary": string (resumen breve del briefing),
                "motivational_message": string (mensaje motivacional)
            }}
            """
            
            # Generate response using AI
            messages = [{"role": "user", "content": user_prompt}]
            response = self._generate_chat_response(messages, system_prompt)
            
            # Parse JSON response
            import json
            try:
                briefing_content = json.loads(response["content"])
            except json.JSONDecodeError:
                # Fallback if AI doesn't return valid JSON
                briefing_content = {
                    "readiness_score": readiness_result.get('score', 50),
                    "status": readiness_result.get('status', 'moderate'),
                    "recommendation": readiness_result.get('recommendation', 'Entrenamiento moderado recomendado'),
                    "summary": f"Tu readiness hoy es {readiness_result.get('score', 'N/A')}/100. Estado: {readiness_result.get('status', 'N/A')}.",
                    "motivational_message": "¡Que tengas un gran día!"
                }
            
            return briefing_content
            
        except Exception as e:
            logger.error(f"Error generating morning briefing for user {user_id}: {e}", exc_info=True)
            # Return fallback briefing
            return {
                "readiness_score": 50,
                "status": "moderate",
                "recommendation": "Entrenamiento moderado recomendado",
                "summary": "Error generando briefing. Por favor intenta de nuevo más tarde.",
                "motivational_message": "¡Confía en el proceso!"
            }

    async def generate_weekly_report(
        self, 
        db: Session, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate a weekly report for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dict containing report content with summary and stats
        """
        try:
            from datetime import date, timedelta
            from app.models.biometrics import Biometrics
            from app.models.workout import Workout
            
            # Get data for the last 7 days
            cutoff = (date.today() - timedelta(days=7)).isoformat()
            
            # Get biometrics
            biometrics = db.query(Biometrics).filter(
                Biometrics.user_id == user_id,
                Biometrics.date >= cutoff
            ).all()
            
            # Get workouts
            workouts = db.query(Workout).filter(
                Workout.user_id == user_id,
                Workout.date >= cutoff
            ).all()
            
            # Calculate stats
            total_workouts = len(workouts)
            total_duration = sum(w.duration or 0 for w in workouts)  # in minutes
            total_calories = sum(w.calories or 0 for w in workouts)
            
            # Calculate average readiness
            readiness_scores = []
            for bio in biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        readiness_scores.append(70) # placeholder
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.debug(f"Skipping biometric record with invalid data: {e}")
            
            avg_readiness = sum(readiness_scores) / len(readiness_scores) if readiness_scores else 70
            
            # Prepare prompt for AI
            system_prompt = """Eres un entrenador personal experto que proporciona un informe semanal personalizado basado en los datos de entrenamiento y biométricos del atleta."""
            
            user_prompt = f"""
            Genera un informe semanal personalizado para el atleta basado en:
            
            Entrenamientos totales: {total_workouts}
            Duración total: {total_duration} minutos
            Calorías totales quemadas: {total_calories} kcal
            Readiness promedio estimado: {avg_readiness:.1f}/100
            
            El informe debe incluir:
            1. Resumen de la semana de entrenamiento
            2. Logros y progresos destacados
            3. Áreas de mejora para la próxima semana
            4. Recomendaciones generales
            
            Formato de respuesta como JSON con:
            {{
                "summary": string (resumen ejecutivo del informe semanal),
                "total_workouts": número,
                "total_duration_minutes": número,
                "total_calories": número,
                "avg_readiness": número,
                "achievements": array de strings (logros destacados),
                "recommendations": array de strings (recomendaciones para próxima semana)
            }}
            """
            
            # Generate response using AI
            messages = [{"role": "user", "content": user_prompt}]
            response = self._generate_chat_response(messages, system_prompt)
            
            # Parse JSON response
            import json
            try:
                report_content = json.loads(response["content"])
            except json.JSONDecodeError:
                # Fallback if AI doesn't return valid JSON
                report_content = {
                    "summary": f"Semana con {total_workouts} entrenamientos, {total_duration} minutos de actividad y {total_calories} kcal quemadas.",
                    "total_workouts": total_workouts,
                    "total_duration_minutes": total_duration,
                    "total_calories": total_calories,
                    "avg_readiness": round(avg_readiness, 1),
                    "achievements": ["Completaste todos tus entrenamientos programados"] if total_workouts > 0 else ["Mantuviste tu rutina"],
                    "recommendations": ["Continúa con tu plan de entrenamiento", "Presta atención a tu recuperación"]
                }
            
            return report_content
            
        except Exception as e:
            logger.error(f"Error generating weekly report for user {user_id}: {e}", exc_info=True)
            # Return fallback report
            return {
                "summary": "Error generando informe semanal. Por favor intenta de nuevo más tarde.",
                "total_workouts": 0,
                "total_duration_minutes": 0,
                "total_calories": 0,
                "avg_readiness": 50,
                "achievements": [],
                "recommendations": ["Verifica tu conexión y vuelve a intentar"]
            }
            

