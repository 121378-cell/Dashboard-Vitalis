import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.adaptive_training_plan import AdaptivePlannedSession
from app.models.workout import Workout
from app.models.training_plan import PersonalRecord

logger = logging.getLogger("app.services.exercise_progression_service")


def _parse_reps_range(reps_str: str) -> tuple[int, int]:
    try:
        if "-" in reps_str:
            parts = reps_str.split("-")
            return int(parts[0].strip()), int(parts[1].strip())
        return int(reps_str), int(reps_str)
    except (ValueError, AttributeError):
        return 0, 0


def _find_exercise_in_workout_description(description: str, exercise_name: str) -> Optional[dict]:
    if not description:
        return None
    try:
        data = json.loads(description)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(data, dict):
        sport = data.get("sport", "")
        if sport and exercise_name.lower() in sport.lower():
            return data
    return None


def get_progression_suggestion(db: Session, user_id: str, exercise_name: str) -> dict:
    now = datetime.now(timezone.utc)
    four_weeks_ago = now - timedelta(weeks=4)
    today = date.today()

    last_session = None
    sessions = (
        db.query(AdaptivePlannedSession)
        .filter(
            AdaptivePlannedSession.user_id == user_id
            if hasattr(AdaptivePlannedSession, "user_id")
            else AdaptivePlannedSession.plan_id.isnot(None),
            AdaptivePlannedSession.completed == True,
        )
        .order_by(AdaptivePlannedSession.session_date.desc())
        .all()
    )

    for session in sessions:
        if not session.exercises_json:
            continue
        try:
            exercises = json.loads(session.exercises_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(exercises, list):
            continue
        for ex in exercises:
            if isinstance(ex, dict) and ex.get("name", "").lower() == exercise_name.lower():
                last_session = {
                    "date": str(session.session_date) if session.session_date else None,
                    "weight": ex.get("weight_kg"),
                    "reps": ex.get("reps"),
                    "sets": ex.get("sets"),
                }
                break
        if last_session:
            break

    workouts = (
        db.query(Workout)
        .filter(
            Workout.user_id == user_id,
            Workout.date >= four_weeks_ago,
        )
        .all()
    )

    max_weight_last_4_weeks: Optional[float] = None
    for w in workouts:
        found = _find_exercise_in_workout_description(w.description, exercise_name)
        if found:
            metrics = found.get("metrics", found)
            weight_val = None
            if isinstance(metrics, dict):
                weight_val = metrics.get("weight_kg") or metrics.get("weight")
            if weight_val is not None:
                try:
                    w_val = float(weight_val)
                    if max_weight_last_4_weeks is None or w_val > max_weight_last_4_weeks:
                        max_weight_last_4_weeks = w_val
                except (ValueError, TypeError):
                    pass

    pr_record = (
        db.query(PersonalRecord)
        .filter(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_name.ilike(exercise_name),
        )
        .order_by(PersonalRecord.weight.desc())
        .first()
    )
    pr_current = float(pr_record.weight) if pr_record else None

    last_weight = last_session.get("weight") if last_session else max_weight_last_4_weeks
    last_reps_str = last_session.get("reps") if last_session else None

    if last_weight is None and max_weight_last_4_weeks is not None:
        last_weight = max_weight_last_4_weeks

    if last_weight is None:
        return {
            "exercise_name": exercise_name,
            "last_session": None,
            "suggested_weight": None,
            "suggested_reps": None,
            "progression_note": "No historical data found for this exercise.",
            "pr_potential": False,
            "pr_current": pr_current,
        }

    reps_min, reps_max = _parse_reps_range(last_reps_str) if last_reps_str else (0, 0)
    target_reps = reps_max if reps_max > 0 else reps_min

    completed_reps_per_set = target_reps

    suggested_weight = last_weight
    suggested_reps = last_reps_str or str(target_reps)
    progression_note = "Maintain current load."

    if target_reps > 0:
        completion_ratio = completed_reps_per_set / target_reps if target_reps else 0

        if completion_ratio >= 1.0:
            suggested_weight = last_weight + 2.5
            suggested_reps = last_reps_str or str(target_reps)
            progression_note = "All target reps completed. Increase weight by +2.5 kg."
        elif completion_ratio >= 0.9:
            suggested_weight = last_weight
            new_target = target_reps + 1
            if last_reps_str and "-" in last_reps_str:
                suggested_reps = f"{reps_min}-{new_target}"
            else:
                suggested_reps = str(new_target)
            progression_note = "90%+ reps completed. Same weight, attempt +1 rep."
        else:
            suggested_weight = max(0, last_weight - 2.5)
            suggested_reps = last_reps_str or str(target_reps)
            progression_note = "Less than 90% reps completed. Reduce weight by -2.5 kg or maintain."

    pr_potential = False
    if suggested_weight and pr_current is not None:
        pr_potential = suggested_weight > pr_current
    elif suggested_weight and pr_current is None:
        pr_potential = True

    if not pr_potential and suggested_weight and pr_current is not None:
        pr_potential = suggested_weight >= pr_current

    return {
        "exercise_name": exercise_name,
        "last_session": last_session,
        "suggested_weight": suggested_weight,
        "suggested_reps": suggested_reps,
        "progression_note": progression_note,
        "pr_potential": pr_potential,
        "pr_current": pr_current,
    }


def get_progressions_for_session(db: Session, user_id: str, session_id: int) -> list[dict]:
    session = db.query(AdaptivePlannedSession).filter(AdaptivePlannedSession.id == session_id).first()
    if not session:
        logger.warning(f"Session {session_id} not found for progression lookup.")
        return []

    if not session.exercises_json:
        logger.info(f"Session {session_id} has no exercises_json.")
        return []

    try:
        exercises = json.loads(session.exercises_json)
    except (json.JSONDecodeError, TypeError):
        logger.error(f"Failed to parse exercises_json for session {session_id}.")
        return []

    if not isinstance(exercises, list):
        logger.warning(f"exercises_json for session {session_id} is not a list.")
        return []

    progressions = []
    for ex in exercises:
        if not isinstance(ex, dict):
            continue
        name = ex.get("name")
        if not name:
            continue
        try:
            suggestion = get_progression_suggestion(db, user_id, name)
            progressions.append(suggestion)
        except Exception as e:
            logger.error(f"Error getting progression for '{name}' in session {session_id}: {e}")

    return progressions
