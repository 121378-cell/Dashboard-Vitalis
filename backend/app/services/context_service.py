import json
import logging
from datetime import date
from sqlalchemy.orm import Session
from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.services.analytics_service import AnalyticsService
from app.services.athlete_profile_service import AthleteProfileService
from app.services.exercise_service import ExerciseService

logger = logging.getLogger("app.services.context_service")

class ContextService:
    @staticmethod
    def translate_biometrics(data: dict, readiness: dict) -> str:
        """Translates raw biometric numbers into a narrative for the AI."""
        hr = data.get("heartRate", 0)
        hrv = data.get("hrv") or 0
        sleep = data.get("sleep", 0)
        steps = data.get("steps", 0)
        stress = data.get("stress", 0)
        
        status = readiness.get("status", "unknown")
        score = readiness.get("score", 0)
        
        narrative = [
            f"--- ESTADO FÍSICO ACTUAL ({date.today().isoformat()}) ---",
            f"Puntuación de Preparación (Readiness): {score}/100 - Estado: {status.upper()}.",
            f"Sueño: {round(sleep, 1)} horas.",
            f"Frecuencia Cardíaca en Reposo: {hr} ppm (Base: {readiness.get('rhr_baseline', 0)} ppm).",
            f"Variabilidad de la FC (HRV): {hrv} ms (Base: {readiness.get('hrv_baseline', 0)} ms).",
            f"Estrés diario: {stress}/100.",
            f"Actividad: {steps} pasos hoy."
        ]
        
        # Add insights based on deviations
        if hrv > 0 and readiness.get('hrv_baseline', 0) > 0:
            diff = hrv - readiness['hrv_baseline']
            if diff < -10:
                narrative.append("AVISO IA: El HRV está significativamente por debajo de la línea base. Posible fatiga o inicio de enfermedad.")
            elif diff > 10:
                narrative.append("NOTA IA: Recuperación excelente. El HRV está por encima de la media.")
                
        return "\n".join(narrative)

    @staticmethod
    def translate_recent_workouts(workouts: list) -> str:
        """Summarizes recent activities for the AI context."""
        if not workouts:
            return "No se han registrado entrenamientos recientes."
            
        summary = ["--- ENTRENAMIENTOS RECIENTES ---"]
        for w in workouts[:3]: # Last 3
            try:
                metrics = json.loads(w.description) if w.description else {}
                dist = metrics.get("distance", 0)
                sport = metrics.get("sport", "actividad").replace("_", " ")
                
                info = f"- {w.date.strftime('%d/%m')}: {w.name} ({sport}). "
                if dist: info += f"Distancia: {round(dist/1000, 2)}km. "
                info += f"Duración: {round(w.duration/60, 1)} min. Calorías: {w.calories}."
                summary.append(info)
            except:
                summary.append(f"- {w.date.strftime('%d/%m')}: {w.name}. Duración: {w.duration}s.")
                
        return "\n".join(summary)

    @staticmethod
    def translate_acwr(acwr: dict) -> str:
        """Translates ACWR data into a narrative."""
        ratio = acwr.get("ratio", 1.0)
        status = acwr.get("status", "mantenimiento")
        message = acwr.get("message", "")
        
        narrative = [
            "--- ANÁLISIS DE CARGA DE ENTRENAMIENTO (ACWR) ---",
            f"Ratio Aguda/Crónica: {ratio} - Estado: {status.upper()}.",
            f"Interpretación: {message}"
        ]
        
        if status == "peligro":
            narrative.append("AVISO CRÍTICO IA: El usuario está en riesgo inminente de lesión por sobreesfuerzo agudo.")
        
        return "\n".join(narrative)

    @staticmethod
    def get_full_coach_context(db: Session, user_id: str) -> str:
        """Generates the complete context string for the LLM prompt."""
        today_str = date.today().isoformat()
        today_bio = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date == today_str
        ).first()
        
        # Get Readiness and ACWR
        readiness = AnalyticsService.get_readiness_score(db, user_id)
        acwr = AnalyticsService.calculate_acwr(db, user_id)
        
        biometrics_narrative = ""
        if today_bio:
            data = json.loads(today_bio.data)
            biometrics_narrative = ContextService.translate_biometrics(data, readiness)
        else:
            biometrics_narrative = "No hay datos biométricos disponibles para hoy. Usa los baselines históricos si están disponibles."

        acwr_narrative = ContextService.translate_acwr(acwr)

        recent_workouts = db.query(Workout).filter(
            Workout.user_id == user_id
        ).order_by(Workout.date.desc()).limit(5).all()
        
        workouts_narrative = ContextService.translate_recent_workouts(recent_workouts)
        
        # Perfil de atleta
        profile_summary = AthleteProfileService.get_profile_summary(user_id, db)
        
        # --- CEREBRO VITALIS (PROYECTO 31/07 & BIBLIOTECA ACADÉMICA) ---
        wisdom_context = [
            "--- METODOLOGÍA Y FILOSOFÍA (PROYECTO 31/07) ---",
            "- OBJETIVO: Definición estética y salud funcional para el 31 de Julio.",
            "- PRINCIPIOS: Sobrecarga Progresiva, Stoppani (Intensidad), McGill (Salud Espinal).",
            "- MOTOR: NEAT de 20.000 pasos/día.",
            "- HITOS: Banca 50kg / Prensa 100kg.",
            "",
            "--- BIBLIOTECA DE REFERENCIA (ERES EXPERTO EN ESTAS FUENTES) ---",
            "INSTRUCCIÓN DE PERSONALIDAD: Eres el Director Deportivo de Sergi. NO eres un asistente pasivo. Tu misión es que Sergi llegue al 31 de Julio en su mejor forma histórica.",
            "PROACTIVIDAD: Analiza los datos de Garmin que se te proporcionan. Si detectas que Sergi no está llegando a sus 20.000 pasos, dáselo a conocer con firmeza. Si ves que su HRV es excelente, empújale a realizar una sesión de fuerza de alta intensidad. No esperes a que él empiece la conversación; toma la iniciativa en tus recomendaciones.",
            "TONO: Directo, basado en datos, exigente pero leal al atleta. Si los datos sugieren que debe descansar, dicta el descanso como una orden profesional, no como una sugerencia."
        ]

        full_context = [
            "Actúa como ATLAS, el Coach de Salud de IA experto para Sergi.",
            "Eres el guardián del 'PROYECTO 31/07'. Tu tono es técnico, motivador y directo.",
            "\n".join(wisdom_context),
            "",
            "A continuación tienes los datos REALES de hoy sincronizados desde Garmin/Health Connect:",
            "",
            f"--- PERFIL DEL ATLETA ---",
            profile_summary,
            "",
            biometrics_narrative,
            "",
            acwr_narrative,
            "",
            workouts_narrative,
            "",
            f"--- BIBLIA DE EJERCICIOS HEVY ---",
            ExerciseService.get_context_summary(),
            "ORDEN: Usa ÚNICAMENTE nombres de ejercicios de la lista HEVY para que el usuario pueda registrarlos sin problemas.",
            "",
            "DISEÑO DE SESIÓN: Si el usuario pide un entreno, básate estrictamente en sus hitos (Banca 50kg, Prensa 100kg) y aplica sobrecarga progresiva."
        ]
        
        return "\n".join(full_context)
