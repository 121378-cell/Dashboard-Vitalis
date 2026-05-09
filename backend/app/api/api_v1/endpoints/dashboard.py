from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.api.deps import get_db, get_current_user_id
from app.models.workout import Workout
from app.models.biometrics import Biometrics
from app.models.training_plan import PersonalRecord
from datetime import date, timedelta, datetime
import json
import logging

router = APIRouter()
logger = logging.getLogger("app.api.dashboard")


@router.get("/kpis")
def get_dashboard_kpis(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()

    workouts_30d = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.date >= thirty_days_ago,
    ).all()

    activities_30d = len(workouts_30d)
    calories_30d = sum(w.calories or 0 for w in workouts_30d)
    training_minutes_30d = sum((w.duration or 0) for w in workouts_30d) // 60

    weekly_sessions_avg = round(activities_30d / 4.3, 1) if activities_30d else 0

    bios = db.query(Biometrics).filter(
        Biometrics.user_id == user_id,
        Biometrics.date >= thirty_days_ago,
    ).all()

    rhr_values = []
    sleep_values = []
    stress_values = []
    bb_values = []
    steps_values = []
    readiness_values = []

    for b in bios:
        try:
            data = json.loads(b.data) if b.data else {}
        except Exception:
            continue
        if data.get("lastSevenDaysAvgRHR"):
            rhr_values.append(data["lastSevenDaysAvgRHR"])
        if data.get("sleep"):
            sleep_values.append(data["sleep"])
        if data.get("stress") is not None:
            stress_values.append(data["stress"])
        if b.body_battery is not None:
            bb_values.append(b.body_battery)
        if data.get("steps"):
            steps_values.append(data["steps"])
        if b.training_readiness is not None:
            readiness_values.append(b.training_readiness)

    avg_rhr = round(sum(rhr_values) / len(rhr_values), 1) if rhr_values else None
    avg_sleep = round(sum(sleep_values) / len(sleep_values), 1) if sleep_values else None
    avg_stress = round(sum(stress_values) / len(stress_values), 1) if stress_values else None
    avg_bb = round(sum(bb_values) / len(bb_values), 1) if bb_values else None
    avg_steps = round(sum(steps_values) / len(steps_values)) if steps_values else None
    avg_readiness = round(sum(readiness_values) / len(readiness_values)) if readiness_values else None

    if not avg_readiness and bios:
        from app.services.daily_loop_service import DailyLoopService
        try:
            status = DailyLoopService.get_status(db, user_id)
            avg_readiness = status.get("readiness_score")
        except Exception:
            pass

    prev_30_start = (date.today() - timedelta(days=60)).isoformat()
    prev_workouts = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.date >= prev_30_start,
        Workout.date < thirty_days_ago,
    ).count()

    activity_change = round((activities_30d - prev_workouts) / max(prev_workouts, 1) * 100) if prev_workouts else None

    total_workouts = db.query(Workout).filter(Workout.user_id == user_id).count()

    strength_count = sum(1 for w in workouts_30d if w.name and "fuerza" in w.name.lower())
    cardio_count = sum(1 for w in workouts_30d if w.name and any(k in w.name.lower() for k in ["carrera", "running", "trail", "caminar", "walk"]))

    return {
        "activities_30d": activities_30d,
        "calories_30d": calories_30d,
        "training_minutes_30d": training_minutes_30d,
        "weekly_sessions_avg": weekly_sessions_avg,
        "avg_rhr": avg_rhr,
        "avg_sleep": avg_sleep,
        "avg_stress": avg_stress,
        "avg_bb": avg_bb,
        "avg_steps": avg_steps,
        "avg_readiness": avg_readiness,
        "activity_change_pct": activity_change,
        "total_workouts": total_workouts,
        "strength_30d": strength_count,
        "cardio_30d": cardio_count,
        "biometrics_days_30d": len(bios),
    }


@router.get("/activity-heatmap")
def get_activity_heatmap(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    weeks: int = Query(52, ge=1, le=104),
):
    days = weeks * 7
    start_date = (date.today() - timedelta(days=days)).isoformat()

    workouts = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.date >= start_date,
    ).all()

    from collections import defaultdict
    weekly_data = defaultdict(lambda: {"count": 0, "minutes": 0, "calories": 0})

    for w in workouts:
        if w.date:
            w_date = w.date if isinstance(w.date, datetime) else datetime.strptime(str(w.date)[:10], "%Y-%m-%d")
            week_num = (w_date - timedelta(days=w_date.weekday())).strftime("%Y-W%W")
            weekly_data[week_num]["count"] += 1
            weekly_data[week_num]["minutes"] += (w.duration or 0) // 60
            weekly_data[week_num]["calories"] += w.calories or 0

    result = []
    for i in range(weeks):
        week_start = date.today() - timedelta(days=(weeks - 1 - i) * 7)
        week_key = (week_start - timedelta(days=week_start.weekday())).strftime("%Y-W%W")
        label = f"S{i + 1}"
        d = weekly_data.get(week_key, {"count": 0, "minutes": 0, "calories": 0})
        result.append({
            "week": label,
            "weekStart": week_start.isoformat(),
            "value": d["count"],
            "minutes": d["minutes"],
            "calories": d["calories"],
        })

    return result


@router.get("/training-distribution")
def get_training_distribution(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    days: int = Query(90, ge=7, le=365),
):
    start_date = (date.today() - timedelta(days=days)).isoformat()

    workouts = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.date >= start_date,
    ).all()

    categories = {
        "Strength": 0,
        "Cardio": 0,
        "HIIT": 0,
        "Mobility": 0,
        "Recovery": 0,
    }

    strength_keywords = ["fuerza", "strength", "weight", "pesas", "gym", "press", "squat", "deadlift", "row"]
    cardio_keywords = ["carrera", "running", "trail", "caminar", "walk", "bike", "ciclismo", "natacion", "swim"]
    hiit_keywords = ["hiit", "interval", "crossfit", "tabata"]
    mobility_keywords = ["pilates", "yoga", "stretch", "mobility", "flexibilidad"]
    recovery_keywords = ["recovery", "recuperacion", "rest", "descanso"]

    for w in workouts:
        name = (w.name or "").lower()
        matched = False
        for kw in hiit_keywords:
            if kw in name:
                categories["HIIT"] += 1
                matched = True
                break
        if matched:
            continue
        for kw in strength_keywords:
            if kw in name:
                categories["Strength"] += 1
                matched = True
                break
        if matched:
            continue
        for kw in cardio_keywords:
            if kw in name:
                categories["Cardio"] += 1
                matched = True
                break
        if matched:
            continue
        for kw in mobility_keywords:
            if kw in name:
                categories["Mobility"] += 1
                matched = True
                break
        if matched:
            continue
        for kw in recovery_keywords:
            if kw in name:
                categories["Recovery"] += 1
                matched = True
                break
        if not matched:
            categories["Strength"] += 1

    total = sum(categories.values()) or 1
    colors = {
        "Strength": "#E8FF47",
        "Cardio": "#60A5FA",
        "HIIT": "#FB923C",
        "Mobility": "#4ADE80",
        "Recovery": "#6B6B8A",
    }

    return [
        {
            "type": k,
            "value": v,
            "percentage": round(v / total * 100, 1),
            "color": colors[k],
        }
        for k, v in categories.items()
        if v > 0
    ]


@router.get("/readiness-trend-line")
def get_readiness_trend_line(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    days: int = Query(90, ge=7, le=365),
):
    start_date = (date.today() - timedelta(days=days)).isoformat()

    bios = db.query(Biometrics).filter(
        Biometrics.user_id == user_id,
        Biometrics.date >= start_date,
    ).order_by(Biometrics.date.asc()).all()

    result = []
    for i, b in enumerate(bios):
        try:
            data = json.loads(b.data) if b.data else {}
        except Exception:
            continue
        rhr = data.get("lastSevenDaysAvgRHR")
        sleep_h = data.get("sleep")
        stress = data.get("stress")
        steps = data.get("steps")

        score = 50
        if rhr and rhr < 60:
            score += 15
        elif rhr and rhr < 70:
            score += 5
        elif rhr and rhr >= 70:
            score -= 10

        if sleep_h and sleep_h >= 7:
            score += 15
        elif sleep_h and sleep_h >= 6:
            score += 5
        elif sleep_h and sleep_h < 5:
            score -= 15

        if stress is not None and stress < 30:
            score += 10
        elif stress is not None and stress > 60:
            score -= 10

        score = max(0, min(100, score))

        day_workouts = db.query(Workout).filter(
            Workout.user_id == user_id,
            func.date(Workout.date) == b.date,
        ).all()
        volume_min = sum((w.duration or 0) for w in day_workouts) // 60
        avg_hr = None
        hrs = []
        for w in day_workouts:
            try:
                desc = json.loads(w.description) if w.description else {}
                if desc.get("avgHR"):
                    hrs.append(desc["avgHR"])
            except Exception:
                pass
        if hrs:
            avg_hr = round(sum(hrs) / len(hrs))

        result.append({
            "day": i + 1,
            "date": b.date,
            "readiness": score,
            "volume": volume_min,
            "avgHr": avg_hr,
        })

    return result


@router.get("/muscle-volume")
def get_muscle_volume(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    weeks: int = Query(12, ge=4, le=52),
):
    days = weeks * 7
    start_date = (date.today() - timedelta(days=days)).isoformat()

    workouts = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.date >= start_date,
    ).all()

    from collections import defaultdict
    weekly_volume = defaultdict(lambda: defaultdict(int))

    muscle_keywords = {
        "Chest": ["chest", "press", "bench", "pecho", "push up", "dip"],
        "Back": ["back", "row", "pull", "lat", "espalda", "dominada", "chin up"],
        "Legs": ["leg", "squat", "deadlift", "lunge", "pierna", "sentadilla", "peso muerto"],
        "Shoulders": ["shoulder", "overhead", "military", "hombro", "lateral raise"],
        "Arms": ["arm", "bicep", "tricep", "curl", "brazo", "extension"],
        "Core": ["core", "abs", "plank", "crunch", "abdominal", "sit up"],
    }

    for w in workouts:
        if not w.date:
            continue
        w_date = w.date if isinstance(w.date, datetime) else datetime.strptime(str(w.date)[:10], "%Y-%m-%d")
        week_idx = (w_date - (date.today() - timedelta(days=days))).days // 7
        if week_idx < 0:
            week_idx = 0
        week_label = f"W{week_idx + 1}"

        name = (w.name or "").lower()
        desc = ""
        try:
            desc_data = json.loads(w.description) if w.description else {}
            desc = str(desc_data).lower()
        except Exception:
            pass

        text = f"{name} {desc}"
        matched = False
        for muscle, keywords in muscle_keywords.items():
            for kw in keywords:
                if kw in text:
                    weekly_volume[week_label][muscle] += (w.duration or 0) // 60
                    matched = True
                    break
            if matched:
                break
        if not matched:
            if "fuerza" in name or "strength" in name:
                weekly_volume[week_label]["Chest"] += (w.duration or 0) // 60 // 3
                weekly_volume[week_label]["Back"] += (w.duration or 0) // 60 // 3
                weekly_volume[week_label]["Legs"] += (w.duration or 0) // 60 // 3

    result = []
    for i in range(weeks):
        label = f"W{i + 1}"
        d = weekly_volume.get(label, {})
        result.append({
            "week": label,
            "Chest": d.get("Chest", 0),
            "Back": d.get("Back", 0),
            "Legs": d.get("Legs", 0),
            "Shoulders": d.get("Shoulders", 0),
            "Arms": d.get("Arms", 0),
            "Core": d.get("Core", 0),
        })

    return result
