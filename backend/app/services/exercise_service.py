import csv
import os
import logging

logger = logging.getLogger(__name__)

class ExerciseService:
    _exercises = []
    CSV_PATH = "C:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/knowledge_base/HEVY APP exercises.csv"

    @classmethod
    def load_exercises(cls):
        if cls._exercises:
            return cls._exercises
        
        exercises = []
        try:
            if not os.path.exists(cls.CSV_PATH):
                logger.error(f"CSV de ejercicios no encontrado en {cls.CSV_PATH}")
                return []
                
            with open(cls.CSV_PATH, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    exercises.append({
                        "title": row["title"],
                        "muscle": row["primary_muscle_group"],
                        "equipment": row["equipment"]
                    })
            cls._exercises = exercises
            logger.info(f"Cargados {len(exercises)} ejercicios de la biblia HEVY.")
        except Exception as e:
            logger.error(f"Error cargando CSV de ejercicios: {e}")
            
        return cls._exercises

    @classmethod
    def get_context_summary(cls):
        """Genera un resumen corto de los ejercicios disponibles para el prompt de la IA."""
        exs = cls.load_exercises()
        # Solo enviamos una muestra o los grupos principales para no saturar el prompt
        muscles = sorted(list(set(e["muscle"] for e in exs)))
        return f"Tienes {len(exs)} ejercicios disponibles en la biblia HEVY. Grupos: {', '.join(muscles)}."
