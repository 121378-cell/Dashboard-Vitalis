import json
import logging
from datetime import date
from sqlalchemy.orm import Session
from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.services.analytics_service import AnalyticsService

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
        
        full_context = [
            "Actúa como ATLAS, un Coach de Salud de IA experto.",
            "A continuación tienes los datos REALES del usuario sincronizados desde su Garmin.",
            "Usa esta información para dar consejos personalizados, ajustar su entrenamiento y detectar fatiga.",
            "",
            biometrics_narrative,
            "",
            acwr_narrative,
            "",
            workouts_narrative,
            "",
            "Prioriza SIEMPRE la salud y longevidad del atleta. Si los datos sugieren fatiga, no dudes en recomendar un día de descanso total o actividad muy ligera (Z1)."
        ]
        
        return "\n".join(full_context)
