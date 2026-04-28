"""
ATLAS Long-Term Memory Engine
==============================

Manages persistent athlete memory entries that are injected
into every AI chat request for personalized coaching context.

Memory types:
- injury: Physical injuries, aches, restrictions
- achievement: PRs, milestones, breakthroughs
- pattern: Recurring behavioral patterns (late sleeper, weekend warrior, etc.)
- preference: Explicit athlete preferences (equipment, exercises, schedule)
- milestone: Body composition, strength goals reached

Autor: ATLAS Team
"""

import json
import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.memory import AtlasMemory
from app.models.biometrics import Biometrics
from app.models.workout import Workout

logger = logging.getLogger("app.services.memory")


class MemoryService:
    """Service for managing ATLAS Long-Term Memory."""

    IMPORTANCE_THRESHOLD = 5  # Only memories >= this are injected into context
    MAX_CONTEXT_MEMORIES = 15  # Hard limit for context window size

    @staticmethod
    def get_memory_summary(
        db: Session,
        user_id: str,
        days: int = 90,
        types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Return a summary of memories for context injection."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        query = db.query(AtlasMemory).filter(
            AtlasMemory.user_id == user_id,
            AtlasMemory.date >= cutoff,
            AtlasMemory.importance >= MemoryService.IMPORTANCE_THRESHOLD
        )

        if types:
            query = query.filter(AtlasMemory.type.in_(types))

        memories = query.order_by(
            AtlasMemory.importance.desc(),
            AtlasMemory.date.desc()
        ).limit(MemoryService.MAX_CONTEXT_MEMORIES).all()

        return {
            "memories": [
                {
                    "type": m.type,
                    "content": m.content,
                    "date": m.date,
                    "importance": m.importance,
                    "source": m.source,
                }
                for m in memories
            ],
            "count": len(memories),
            "period_days": days
        }

    @staticmethod
    def get_memory_context_string(db: Session, user_id: str) -> str:
        """Return a formatted string ready for AI context injection."""
        summary = MemoryService.get_memory_summary(db, user_id)

        if not summary["memories"]:
            return ""

        lines = ["\n--- ATLAS ATHLETE MEMORY ---"]
        for m in summary["memories"]:
            emoji = {
                "injury": "🩹",
                "achievement": "🏆",
                "pattern": "📊",
                "preference": "⚙️",
                "milestone": "🎯"
            }.get(m["type"], "📝")
            lines.append(f"{emoji} [{m['date']}] {m['content']} (importance: {m['importance']}/10)")

        lines.append("--- END MEMORY ---\n")
        return "\n".join(lines)

    @staticmethod
    def add_memory(
        db: Session,
        user_id: str,
        memory_type: str,
        content: str,
        importance: int = 5,
        memory_date: Optional[str] = None,
        source: str = "auto"
    ) -> AtlasMemory:
        """Add a new memory entry."""
        entry = AtlasMemory(
            user_id=user_id,
            type=memory_type,
            content=content,
            date=memory_date or date.today().isoformat(),
            importance=max(1, min(10, importance)),
            source=source
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(f"Memory added for {user_id}: [{memory_type}] {content[:60]}...")
        return entry

    @staticmethod
    def generate_memories_from_sync(
        db: Session,
        user_id: str,
        biometrics_data: Optional[Dict] = None,
        workouts_data: Optional[List] = None
    ) -> List[AtlasMemory]:
        """Auto-generate memory entries from a sync batch."""
        created = []
        today = date.today().isoformat()

        # Pattern detection from biometrics
        if biometrics_data:
            steps = biometrics_data.get("steps")
            if steps and steps > 25000:
                created.append(MemoryService.add_memory(
                    db, user_id, "achievement",
                    f"Extremely high activity day: {steps} steps",
                    importance=7, source="garmin_sync"
                ))

            sleep = biometrics_data.get("sleep")
            if sleep is not None:
                if sleep < 5.0:
                    created.append(MemoryService.add_memory(
                        db, user_id, "pattern",
                        f"Very low sleep night: {sleep:.1f}h",
                        importance=6, source="garmin_sync"
                    ))
                elif sleep > 9.0:
                    created.append(MemoryService.add_memory(
                        db, user_id, "pattern",
                        f"High recovery sleep: {sleep:.1f}h",
                        importance=5, source="garmin_sync"
                    ))

            hrv = biometrics_data.get("hrv")
            if hrv and hrv > 80:
                created.append(MemoryService.add_memory(
                    db, user_id, "achievement",
                    f"Exceptional HRV reading: {hrv}ms",
                    importance=8, source="garmin_sync"
                ))

        # Workout achievements
        if workouts_data:
            for w in workouts_data:
                duration = w.get("duration", 0)
                calories = w.get("calories", 0)
                if duration > 7200:  # > 2h
                    created.append(MemoryService.add_memory(
                        db, user_id, "achievement",
                        f"Long workout completed: {duration // 60}min",
                        importance=6, source="garmin_sync"
                    ))
                if calories > 1500:
                    created.append(MemoryService.add_memory(
                        db, user_id, "achievement",
                        f"High calorie burn workout: {calories}kcal",
                        importance=6, source="garmin_sync"
                    ))

        return [m for m in created if m is not None]
