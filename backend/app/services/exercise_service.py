import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ExerciseService:
    _exercises = []
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    CSV_PATH = PROJECT_ROOT / "knowledge_base" / "HEVY APP exercises.csv"
    EXPECTED_HEVY_EXERCISES = 434

    @classmethod
    def load_exercises(cls):
        if cls._exercises:
            return cls._exercises

        exercises = []
        try:
            if not cls.CSV_PATH.exists():
                logger.error(f"CSV de ejercicios no encontrado en {cls.CSV_PATH}")
                return []

            with cls.CSV_PATH.open(mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    exercises.append(
                        {
                            "title": row["title"],
                            "muscle": row["primary_muscle_group"],
                            "equipment": row["equipment"],
                        }
                    )

            cls._exercises = exercises
            logger.info(f"Cargados {len(exercises)} ejercicios de la biblia HEVY.")
            if len(exercises) < cls.EXPECTED_HEVY_EXERCISES:
                logger.warning(
                    "La biblia HEVY tiene %s ejercicios, por debajo del objetivo de %s.",
                    len(exercises),
                    cls.EXPECTED_HEVY_EXERCISES,
                )
        except Exception as e:
            logger.error(f"Error cargando CSV de ejercicios: {e}")

        return cls._exercises

    @classmethod
    def get_context_summary(cls):
        """Genera un resumen corto de los ejercicios disponibles para el prompt de la IA."""
        exs = cls.load_exercises()
        muscles = sorted(list(set(e["muscle"] for e in exs)))
        return f"Tienes {len(exs)} ejercicios disponibles en la biblia HEVY. Grupos: {', '.join(muscles)}."
