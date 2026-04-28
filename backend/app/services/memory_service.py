"""
ATLAS Long-Term Memory Engine v2
=================================

Advanced memory management with pattern detection, deduplication,
and automatic pruning. Enables truly personalized AI coaching by
building a persistent profile of the athlete over time.

Memory types:
- injury: Physical injuries, aches, restrictions (always included in context)
- achievement: PRs, milestones, breakthroughs
- pattern: Recurring behavioral patterns (late sleeper, weekend warrior)
- preference: Explicit athlete preferences
- milestone: Body composition, strength goals reached
- health_alert: Critical health alerts (HRV anomalies, overtraining signs)

Autor: ATLAS Team
Version: 2.0.0
"""

import json
import logging
import statistics
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.memory import AtlasMemory
from app.models.biometrics import Biometrics
from app.models.workout import Workout

logger = logging.getLogger("app.services.memory")


class MemoryService:
    """
    Advanced service for managing ATLAS Long-Term Memory.
    
    Features:
    - Pattern detection from biometrics data
    - Deduplication to prevent duplicate entries
    - Automatic pruning (max 50 memories per user)
    - Smart context injection prioritizing injuries and high importance
    - Notification triggers for critical memories (importance >= 8)
    """

    # Configuration
    IMPORTANCE_THRESHOLD = 5  # Min importance for context injection
    MAX_CONTEXT_MEMORIES = 15  # Max memories in AI context window
    MAX_TOTAL_MEMORIES = 50  # Max memories per user (auto-pruning)
    CRITICAL_IMPORTANCE = 8  # Trigger notifications
    
    # Type-specific settings
    INJURY_ALWAYS_INCLUDE = True  # Injuries always in context regardless of date
    INJURY_IMPORTANCE_MIN = 7  # Minimum importance for injury memories

    @staticmethod
    def get_memory_summary(
        db: Session,
        user_id: str,
        days: int = 90,
        types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get structured summary of memories grouped by type.
        
        Returns:
            Dict with memories grouped by type and metadata
        """
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
        ).all()

        # Group by type
        grouped = {}
        for m in memories:
            if m.type not in grouped:
                grouped[m.type] = []
            grouped[m.type].append({
                "id": m.id,
                "type": m.type,
                "content": m.content,
                "date": m.date,
                "importance": m.importance,
                "tags": m.tags or [],
                "source": m.source,
            })

        return {
            "grouped_memories": grouped,
            "memories": [
                {
                    "id": m.id,
                    "type": m.type,
                    "content": m.content,
                    "date": m.date,
                    "importance": m.importance,
                    "tags": m.tags or [],
                    "source": m.source,
                }
                for m in memories
            ],
            "count": len(memories),
            "period_days": days,
            "type_counts": {t: len(items) for t, items in grouped.items()}
        }

    @staticmethod
    def get_memory_context_string(db: Session, user_id: str, max_tokens: int = 2000) -> str:
        """
        Generate compact context string for AI injection.
        
        Prioritizes:
        1. All injury memories (regardless of date)
        2. High importance (>= 8) recent memories
        3. Recent high importance (5-7) memories
        
        Args:
            max_tokens: Approximate token limit for context
            
        Returns:
            Formatted string ready for system prompt injection
        """
        lines = ["\n--- ATLAS ATHLETE MEMORY ---"]
        total_chars = 0
        max_chars = max_tokens * 4  # Approximate chars per token
        
        # Step 1: Always include injuries (critical for safety)
        if MemoryService.INJURY_ALWAYS_INCLUDE:
            injuries = db.query(AtlasMemory).filter(
                AtlasMemory.user_id == user_id,
                AtlasMemory.type == "injury"
            ).order_by(AtlasMemory.importance.desc(), AtlasMemory.date.desc()).all()
            
            if injuries:
                lines.append("\n🚨 ACTIVE INJURIES/RESTRICTIONS:")
                for m in injuries[:5]:  # Max 5 injuries
                    line = f"  • [{m.date}] {m.content}"
                    if total_chars + len(line) < max_chars:
                        lines.append(line)
                        total_chars += len(line)
        
        # Step 2: High importance recent memories (>= 8)
        high_importance = db.query(AtlasMemory).filter(
            AtlasMemory.user_id == user_id,
            AtlasMemory.importance >= MemoryService.CRITICAL_IMPORTANCE,
            AtlasMemory.type != "injury"  # Already included above
        ).order_by(AtlasMemory.date.desc()).limit(5).all()
        
        if high_importance:
            lines.append("\n🏆 KEY ACHIEVEMENTS/ALERTS:")
            for m in high_importance:
                emoji = {"achievement": "🏆", "health_alert": "⚠️", "milestone": "🎯"}.get(m.type, "📝")
                line = f"  {emoji} [{m.date}] {m.content}"
                if total_chars + len(line) < max_chars:
                    lines.append(line)
                    total_chars += len(line)
        
        # Step 3: Recent patterns and preferences
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        patterns = db.query(AtlasMemory).filter(
            AtlasMemory.user_id == user_id,
            AtlasMemory.type.in_(["pattern", "preference"]),
            AtlasMemory.date >= cutoff,
            AtlasMemory.importance >= MemoryService.IMPORTANCE_THRESHOLD
        ).order_by(AtlasMemory.importance.desc()).limit(5).all()
        
        if patterns:
            lines.append("\n📊 OBSERVED PATTERNS:")
            for m in patterns:
                line = f"  • [{m.date}] {m.content}"
                if total_chars + len(line) < max_chars:
                    lines.append(line)
                    total_chars += len(line)
        
        if len(lines) == 1:  # Only header
            return ""
            
        lines.append("--- END MEMORY ---\n")
        return "\n".join(lines)

    @staticmethod
    def check_duplicate(
        db: Session,
        user_id: str,
        memory_type: str,
        content: str,
        date_str: str,
        similarity_threshold: float = 0.8
    ) -> bool:
        """
        Check if a similar memory already exists for this user on this date.
        
        Uses simple string similarity (substring match) for now.
        Can be enhanced with embeddings in the future.
        """
        # Check for exact same content on same date
        existing = db.query(AtlasMemory).filter(
            AtlasMemory.user_id == user_id,
            AtlasMemory.type == memory_type,
            AtlasMemory.date == date_str,
            AtlasMemory.content == content
        ).first()
        
        if existing:
            return True
            
        # Check for similar content (simplified - checks if content is substring)
        similar = db.query(AtlasMemory).filter(
            AtlasMemory.user_id == user_id,
            AtlasMemory.date == date_str,
            AtlasMemory.content.ilike(f"%{content[:50]}%")
        ).first()
        
        return similar is not None

    @staticmethod
    def prune_old_memories(db: Session, user_id: str):
        """
        Prune old memories to maintain MAX_TOTAL_MEMORIES limit.
        Removes oldest memories with lowest importance first.
        Preserves all injury memories regardless of date.
        """
        total_count = db.query(AtlasMemory).filter(
            AtlasMemory.user_id == user_id
        ).count()
        
        if total_count <= MemoryService.MAX_TOTAL_MEMORIES:
            return 0
        
        # Calculate how many to delete
        to_delete = total_count - MemoryService.MAX_TOTAL_MEMORIES
        
        # Get candidates for deletion (exclude injuries, order by importance asc, date asc)
        candidates = db.query(AtlasMemory).filter(
            AtlasMemory.user_id == user_id,
            AtlasMemory.type != "injury"  # Never delete injuries
        ).order_by(
            AtlasMemory.importance.asc(),
            AtlasMemory.date.asc()
        ).limit(to_delete).all()
        
        deleted_count = 0
        for memory in candidates:
            db.delete(memory)
            deleted_count += 1
        
        db.commit()
        if deleted_count > 0:
            logger.info(f"Pruned {deleted_count} old memories for user {user_id}")
        return deleted_count

    @staticmethod
    def add_memory(
        db: Session,
        user_id: str,
        memory_type: str,
        content: str,
        importance: int = 5,
        memory_date: Optional[str] = None,
        source: str = "auto",
        tags: Optional[List[str]] = None,
        skip_duplicates: bool = True
    ) -> Optional[AtlasMemory]:
        """
        Add a new memory entry with deduplication and pruning.
        
        Args:
            skip_duplicates: If True, skips if similar memory exists
            
        Returns:
            Created memory or None if skipped/duplicate
        """
        target_date = memory_date or date.today().isoformat()
        
        # Check for duplicates
        if skip_duplicates:
            is_duplicate = MemoryService.check_duplicate(
                db, user_id, memory_type, content, target_date
            )
            if is_duplicate:
                logger.debug(f"Skipping duplicate memory for {user_id}: {content[:50]}...")
                return None
        
        # Create entry
        entry = AtlasMemory(
            user_id=user_id,
            type=memory_type,
            content=content,
            date=target_date,
            importance=max(1, min(10, importance)),
            source=source,
            tags=tags or []
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        
        logger.info(f"Memory added for {user_id}: [{memory_type}] {content[:60]}...")
        
        # Prune old memories if needed
        MemoryService.prune_old_memories(db, user_id)
        
        # Trigger notification for critical memories
        if entry.importance >= MemoryService.CRITICAL_IMPORTANCE:
            MemoryService._notify_critical_memory(entry)
        
        return entry

    @staticmethod
    def delete_memory(db: Session, user_id: str, memory_id: int) -> bool:
        """Delete a specific memory by ID."""
        memory = db.query(AtlasMemory).filter(
            AtlasMemory.id == memory_id,
            AtlasMemory.user_id == user_id
        ).first()
        
        if not memory:
            return False
        
        db.delete(memory)
        db.commit()
        logger.info(f"Memory {memory_id} deleted for user {user_id}")
        return True

    @staticmethod
    def _notify_critical_memory(memory: AtlasMemory):
        """
        Trigger notification for critical memories (importance >= 8).
        These appear in the daily briefing.
        """
        # This would integrate with a notification service
        # For now, just log it
        logger.info(f"CRITICAL MEMORY created: [{memory.type}] {memory.content}")
        
        # TODO: Integrate with notification system to include in daily briefing
        # notification_service.add_to_briefing(memory)

    @staticmethod
    def detect_hrv_anomaly(
        recent_biometrics: List[Biometrics]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect HRV anomalies (>2 std dev from 30-day baseline).
        
        Returns:
            Memory entry dict if anomaly detected, None otherwise
        """
        hrv_values = []
        for b in recent_biometrics:
            try:
                data = json.loads(b.data) if b.data else {}
                hrv = data.get("hrv")
                if hrv and hrv > 0:
                    hrv_values.append(float(hrv))
            except (json.JSONDecodeError, ValueError):
                continue
        
        if len(hrv_values) < 7:
            return None
        
        # Calculate baseline (last 30 days or all available)
        baseline_window = hrv_values[-30:] if len(hrv_values) >= 30 else hrv_values
        baseline = statistics.mean(baseline_window)
        
        # Calculate std dev of recent week
        recent_week = hrv_values[-7:]
        if len(recent_week) < 2:
            return None
            
        std = statistics.stdev(recent_week)
        current = hrv_values[-1]
        
        # Check for critically low HRV (overtraining indicator)
        if current < baseline - 2 * std:
            return {
                "type": "health_alert",
                "content": f"HRV críticamente bajo: {current:.0f}ms vs baseline {baseline:.0f}ms. Posible sobreentrenamiento.",
                "importance": 9,
                "tags": ["hrv", "overtraining", "recovery"]
            }
        
        # Check for exceptionally high HRV (great recovery)
        if current > baseline + 2 * std and current > 70:
            return {
                "type": "achievement",
                "content": f"HRV excepcional: {current:.0f}ms - recuperación óptima",
                "importance": 7,
                "tags": ["hrv", "recovery", "peak"]
            }
        
        return None

    @staticmethod
    def detect_training_streak(
        workouts: List[Workout],
        min_days: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Detect consecutive training days streak."""
        if len(workouts) < min_days:
            return None
        
        # Sort by date
        sorted_workouts = sorted(workouts, key=lambda w: w.date, reverse=True)
        
        # Check for consecutive days
        consecutive = 1
        for i in range(1, len(sorted_workouts)):
            curr_date = sorted_workouts[i-1].date
            prev_date = sorted_workouts[i].date
            if curr_date and prev_date:
                diff = (curr_date - prev_date).days
                if diff == 1:
                    consecutive += 1
                else:
                    break
        
        if consecutive >= min_days:
            return {
                "type": "achievement",
                "content": f"Racha de {consecutive} días consecutivos de entrenamiento",
                "importance": 7 if consecutive >= 7 else 6,
                "tags": ["streak", "consistency", "training"]
            }
        
        return None

    @staticmethod
    def detect_volume_record(
        workouts: List[Workout],
        days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """Detect week with highest training volume."""
        if len(workouts) < 3:
            return None
        
        # Calculate total duration for recent week
        cutoff = date.today() - timedelta(days=days)
        recent_workouts = [w for w in workouts if w.date and w.date.date() >= cutoff]
        
        if len(recent_workouts) < 2:
            return None
        
        total_minutes = sum(w.duration or 0 for w in recent_workouts) // 60
        
        # Check if this is a record (simplified - in production would compare with history)
        if total_minutes > 300:  # > 5 hours in a week
            return {
                "type": "achievement",
                "content": f"Semana de alto volumen: {total_minutes} minutos de entrenamiento",
                "importance": 7,
                "tags": ["volume", "week_record", "training_load"]
            }
        
        return None

    @staticmethod
    def detect_sleep_pattern(
        recent_biometrics: List[Biometrics]
    ) -> Optional[Dict[str, Any]]:
        """Detect poor sleep pattern (>3 days with < 6h sleep)."""
        bad_sleep_days = 0
        
        for b in recent_biometrics[-7:]:  # Check last 7 days
            try:
                data = json.loads(b.data) if b.data else {}
                sleep = data.get("sleep")
                if sleep and sleep < 6.0:
                    bad_sleep_days += 1
            except (json.JSONDecodeError, ValueError):
                continue
        
        if bad_sleep_days >= 3:
            return {
                "type": "pattern",
                "content": f"Patrón de sueño deficiente: {bad_sleep_days} días esta semana con < 6h de sueño",
                "importance": 7,
                "tags": ["sleep", "recovery", "pattern"]
            }
        
        return None

    @staticmethod
    def auto_generate_from_sync(
        db: Session,
        user_id: str,
        biometrics_data: Optional[Dict] = None,
        workouts_data: Optional[List] = None,
        recent_biometrics: Optional[List[Biometrics]] = None
    ) -> List[AtlasMemory]:
        """
        Automatically generate memories from sync data.
        
        Called after successful Garmin sync to detect patterns,
        anomalies, and achievements.
        """
        created = []
        today = date.today().isoformat()
        
        # 1. HRV Anomaly Detection
        if recent_biometrics:
            hrv_memory = MemoryService.detect_hrv_anomaly(recent_biometrics)
            if hrv_memory:
                m = MemoryService.add_memory(
                    db, user_id,
                    hrv_memory["type"],
                    hrv_memory["content"],
                    importance=hrv_memory["importance"],
                    source="garmin_sync",
                    tags=hrv_memory.get("tags", [])
                )
                if m:
                    created.append(m)
        
        # 2. Basic biometrics achievements
        if biometrics_data:
            steps = biometrics_data.get("steps")
            if steps and steps > 25000:
                m = MemoryService.add_memory(
                    db, user_id, "achievement",
                    f"Día de actividad extrema: {steps} pasos",
                    importance=7, source="garmin_sync",
                    tags=["steps", "activity", "record"]
                )
                if m:
                    created.append(m)
            elif steps and steps > 15000:
                m = MemoryService.add_memory(
                    db, user_id, "achievement",
                    f"Alta actividad: {steps} pasos",
                    importance=5, source="garmin_sync",
                    tags=["steps", "activity"]
                )
                if m:
                    created.append(m)
            
            sleep = biometrics_data.get("sleep")
            if sleep is not None:
                if sleep < 5.0:
                    m = MemoryService.add_memory(
                        db, user_id, "pattern",
                        f"Noche con muy poco sueño: {sleep:.1f}h",
                        importance=6, source="garmin_sync",
                        tags=["sleep", "recovery", "alert"]
                    )
                    if m:
                        created.append(m)
                elif sleep > 9.0:
                    m = MemoryService.add_memory(
                        db, user_id, "pattern",
                        f"Recuperación profunda: {sleep:.1f}h de sueño",
                        importance=5, source="garmin_sync",
                        tags=["sleep", "recovery"]
                    )
                    if m:
                        created.append(m)
            
            hrv = biometrics_data.get("hrv")
            if hrv and hrv > 80:
                m = MemoryService.add_memory(
                    db, user_id, "achievement",
                    f"Lectura HRV excepcional: {hrv}ms",
                    importance=8, source="garmin_sync",
                    tags=["hrv", "recovery", "peak"]
                )
                if m:
                    created.append(m)
        
        # 3. Workout achievements
        if workouts_data:
            # Training streak detection
            streak = MemoryService.detect_training_streak(workouts_data)
            if streak:
                m = MemoryService.add_memory(
                    db, user_id, streak["type"],
                    streak["content"],
                    importance=streak["importance"],
                    source="garmin_sync",
                    tags=streak.get("tags", [])
                )
                if m:
                    created.append(m)
            
            # Volume records
            volume = MemoryService.detect_volume_record(workouts_data)
            if volume:
                m = MemoryService.add_memory(
                    db, user_id, volume["type"],
                    volume["content"],
                    importance=volume["importance"],
                    source="garmin_sync",
                    tags=volume.get("tags", [])
                )
                if m:
                    created.append(m)
            
            # Individual workout achievements
            for w in workouts_data[-3:]:  # Last 3 workouts
                duration = w.get("duration", 0)
                calories = w.get("calories", 0)
                
                if duration > 7200:  # > 2h
                    m = MemoryService.add_memory(
                        db, user_id, "achievement",
                        f"Entrenamiento largo completado: {duration // 60}min",
                        importance=6, source="garmin_sync",
                        tags=["duration", "long_workout"]
                    )
                    if m:
                        created.append(m)
                
                if calories > 1500:
                    m = MemoryService.add_memory(
                        db, user_id, "achievement",
                        f"Alto gasto calórico: {calories}kcal",
                        importance=6, source="garmin_sync",
                        tags=["calories", "intensity"]
                    )
                    if m:
                        created.append(m)
        
        logger.info(f"Auto-generated {len(created)} memories for user {user_id}")
        return created
