from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.models.weekly_plan import WeeklyPlan, TrainingSession, PersonalRecord
from app.models.user import User
from app.services.planner_service import TrainingPlannerService
from app.services.readiness_service import ReadinessService
from app.services.athlete_profile_service import AthleteProfileService

router = APIRouter()


@router.post("/api/v1/planner/generate-week", response_model=dict)
async def generate_weekly_plan(
    db: Session = Depends(get_db),
    user_id: str = "default_user"  # In production, get from auth
):
    """
    Generate a comprehensive weekly training plan.
    
    Analyzes:
    - Athlete profile and goals
    - 30-day readiness history
    - 8-week workout history
    - Personal records
    - Memory context (injuries, patterns, achievements)
    - Readiness forecast for the week
    
    Returns:
        Complete weekly plan with all sessions and exercises
    """
    try:
        plan = await TrainingPlannerService.generate_weekly_plan(db, user_id)
        return {
            "status": "success",
            "data": plan,
            "message": "Weekly training plan generated successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating plan: {str(e)}"
        )


@router.get("/api/v1/planner/current-week", response_model=dict)
async def get_current_week(
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Get the currently active weekly plan.
    
    Returns:
        Active weekly plan with all sessions and their completion status
    """
    today = date.today().isoformat()
    
    plan = db.query(WeeklyPlan).filter(
        WeeklyPlan.user_id == user_id,
        WeeklyPlan.status == "active",
        WeeklyPlan.week_start <= today,
        WeeklyPlan.week_end >= today
    ).first()
    
    if not plan:
        # Try to find most recent plan
        plan = db.query(WeeklyPlan).filter(
            WeeklyPlan.user_id == user_id,
            WeeklyPlan.status == "archived"
        ).order_by(WeeklyPlan.week_end.desc()).first()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No training plan found. Generate one first."
            )
    
    sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan.id
    ).order_by(TrainingSession.day_index).all()
    
    sessions_data = []
    for s in sessions:
        sessions_data.append({
            "id": s.id,
            "day": s.day_index,
            "day_name": s.day_name,
            "scheduled_date": s.scheduled_date,
            "exercises": s.exercises_data,
            "completed": s.completed,
            "actual_data": s.actual_data,
            "skipped": s.skipped,
            "notes": s.notes
        })
    
    return {
        "status": "success",
        "data": {
            "id": plan.id,
            "user_id": plan.user_id,
            "week_start": plan.week_start,
            "week_end": plan.week_end,
            "generated_at": plan.generated_at.isoformat(),
            "status": plan.status,
            "objective": plan.objective,
            "sessions": sessions_data,
            "plan_data": plan.plan_data
        }
    }


@router.post("/api/v1/planner/complete-session", response_model=dict)
async def complete_session(
    session_id: int,
    actual_data: dict,
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Mark a training session as completed and record actual performance.
    
    Updates:
    - Session completion status
    - Actual weights/reps performed
    - Personal records if new PR achieved
    - Memory context with achievements
    
    Args:
        session_id: Training session ID
        actual_data: Dict with {"exercises": [{name, sets, reps, weight, rpe, ...}]}
    
    Returns:
        Updated session and any new personal records
    """
    session = db.query(TrainingSession).filter(
        TrainingSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found"
        )
    
    # Mark as completed
    session.completed = True
    session.completed_at = date.today()
    session.actual_data = actual_data
    
    new_prs = []
    
    # Check for new personal records
    for ex_actual in actual_data.get("exercises", []):
        ex_name = ex_actual.get("name", "").lower()
        weight = ex_actual.get("weight", 0)
        reps = ex_actual.get("reps", 0)
        rpe = ex_actual.get("rpe", 0)
        
        if weight <= 0 or reps <= 0:
            continue
        
        # Check existing PRs
        existing_pr = db.query(PersonalRecord).filter(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_name.ilike(ex_name)
        ).order_by(PersonalRecord.weight.desc(), PersonalRecord.reps.desc()).first()
        
        is_new_pr = False
        if existing_pr:
            # New PR: either more weight, or same weight with more reps
            if weight > existing_pr.weight or \
               (weight == existing_pr.weight and reps > existing_pr.reps):
                is_new_pr = True
                existing_pr.weight = weight
                existing_pr.reps = reps
                existing_pr.rpe = rpe
                existing_pr.date = date.today().isoformat()
                existing_pr.source = "workout"
                existing_pr.session_id = session_id
                new_prs.append({
                    "exercise": ex_name,
                    "weight": weight,
                    "reps": reps,
                    "previous_weight": existing_pr.weight,
                    "previous_reps": existing_pr.reps,
                    "type": "weight_increase" if weight > existing_pr.weight else "reps_increase"
                })
        else:
            # First PR for this exercise
            new_pr = PersonalRecord(
                user_id=user_id,
                exercise_name=ex_name,
                weight=weight,
                reps=reps,
                rpe=rpe,
                date=date.today().isoformat(),
                source="workout",
                session_id=session_id,
                notes="First recorded PR"
            )
            db.add(new_pr)
            db.flush()
            new_prs.append({
                "exercise": ex_name,
                "weight": weight,
                "reps": reps,
                "type": "first_pr"
            })
            is_new_pr = True
        
        # Add memory for new PR
        if is_new_pr:
            from app.services.memory_service import MemoryService
            MemoryService.add_memory(
                db, user_id,
                memory_type="achievement",
                content=f"Nuevo récord personal: {ex_name} - {weight}kg × {reps} reps",
                importance=9,
                source="workout",
                tags=["pr", "strength", ex_name]
            )
    
    db.commit()
    
    return {
        "status": "success",
        "data": {
            "session_id": session.id,
            "completed": True,
            "completed_at": session.completed_at.isoformat(),
            "new_personal_records": new_prs
        },
        "message": "Session completed successfully"
    }


@router.post("/api/v1/planner/skip-session", response_model=dict)
async def skip_session(
    session_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Skip a scheduled training session (e.g., due to low readiness).
    
    The session will be rescheduled to the next available day
    or regenerated in the next weekly plan.
    """
    session = db.query(TrainingSession).filter(
        TrainingSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found"
        )
    
    session.skipped = True
    session.notes = reason or "Skipped by user request"
    
    db.commit()
    
    return {
        "status": "success",
        "data": {
            "session_id": session.id,
            "skipped": True,
            "notes": session.notes
        },
        "message": "Session skipped"
    }


@router.get("/api/v1/planner/personal-records", response_model=dict)
async def get_personal_records(
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Get all personal records for the user.
    
    Returns:
        List of personal records grouped by exercise
    """
    prs = db.query(PersonalRecord).filter(
        PersonalRecord.user_id == user_id
    ).order_by(PersonalRecord.date.desc()).all()
    
    # Group by exercise
    grouped = {}
    for pr in prs:
        if pr.exercise_name not in grouped:
            grouped[pr.exercise_name] = []
        grouped[pr.exercise_name].append({
            "id": pr.id,
            "weight": pr.weight,
            "reps": pr.reps,
            "rpe": pr.rpe,
            "date": pr.date,
            "source": pr.source,
            "notes": pr.notes
        })
    
    # Keep only the latest PR per exercise
    current_prs = {}
    for ex_name, pr_list in grouped.items():
        current_prs[ex_name] = pr_list[0]
    
    return {
        "status": "success",
        "data": {
            "personal_records": current_prs,
            "total_exercises": len(current_prs),
            "all_records": grouped
        }
    }


@router.post("/api/v1/planner/update-pr", response_model=dict)
async def update_pr(
    exercise_name: str,
    weight: int,
    reps: int,
    rpe: Optional[int] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Manually update or add a personal record.
    
    Args:
        exercise_name: Name of the exercise
        weight: Weight in kg
        reps: Number of repetitions
        rpe: Rate of Perceived Exertion (optional)
        notes: Additional notes (optional)
    
    Returns:
        Updated personal record
    """
    existing_pr = db.query(PersonalRecord).filter(
        PersonalRecord.user_id == user_id,
        PersonalRecord.exercise_name.ilike(exercise_name)
    ).order_by(PersonalRecord.weight.desc(), PersonalRecord.reps.desc()).first()
    
    if existing_pr:
        existing_pr.weight = weight
        existing_pr.reps = reps
        existing_pr.rpe = rpe
        existing_pr.date = date.today().isoformat()
        existing_pr.source = "manual"
        existing_pr.notes = notes or existing_pr.notes
        pr = existing_pr
    else:
        pr = PersonalRecord(
            user_id=user_id,
            exercise_name=exercise_name,
            weight=weight,
            reps=reps,
            rpe=rpe,
            date=date.today().isoformat(),
            source="manual",
            notes=notes
        )
        db.add(pr)
    
    db.commit()
    db.refresh(pr)
    
    return {
        "status": "success",
        "data": {
            "id": pr.id,
            "exercise_name": pr.exercise_name,
            "weight": pr.weight,
            "reps": pr.reps,
            "rpe": pr.rpe,
            "date": pr.date,
            "source": pr.source,
            "notes": pr.notes
        },
        "message": "Personal record updated"
    }


@router.get("/api/v1/planner/weekly-stats", response_model=dict)
async def get_weekly_stats(
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Get weekly training statistics.
    
    Returns:
        Stats for the current week including sessions completed, total volume, etc.
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    sessions = db.query(TrainingSession).join(WeeklyPlan).filter(
        WeeklyPlan.user_id == user_id,
        TrainingSession.scheduled_date >= week_start.isoformat(),
        TrainingSession.scheduled_date <= week_end.isoformat()
    ).all()
    
    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s.completed)
    skipped_sessions = sum(1 for s in sessions if s.skipped)
    
    total_duration = 0
    total_exercises = 0
    for s in sessions:
        if s.actual_data:
            for ex in s.actual_data.get("exercises", []):
                total_exercises += 1
                # Estimate duration (3 min per set as rough estimate)
                sets = ex.get("sets", 3)
                total_duration += sets * 3
    
    return {
        "status": "success",
        "data": {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "skipped_sessions": skipped_sessions,
            "completion_rate": round(completed_sessions / total_sessions * 100, 1) if total_sessions > 0 else 0,
            "total_duration_minutes": total_duration,
            "total_exercises": total_exercises
        }
    }
