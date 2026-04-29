from datetime import datetime, timedelta
from sqlalchemy import func
from typing import List, Dict, Optional
from app.models.community import Challenge, ChallengeParticipant, UserPublicProfile
from app.db.session import BaseSession

class CommunityService:
    def __init__(self, session: BaseSession):
        self.session = session
    
    def get_leaderboard(self, metric: str, period: str = "weekly") -> List[Dict]:
        """Get leaderboard data for specified metric and period"""
        period_timedelta = {
            "weekly": timedelta(days=7),
            "monthly": timedelta(days=30),
            "all_time": None
        }[period]
        
        # Calculate start date for periodic challenges
        start_date = datetime.utcnow() - period_timedelta if period_timedelta else None
        
        # Get active challenges for this period
        active_challenges = self._get_active_challenges(start_date)
        
        # Calculate leaderboard rankings
        leaderboard_data = []
        for challenge in active_challenges:
            # Get participants and their metrics
            participants = self.session.query(ChallengeParticipant).filter(
                ChallengeParticipant.challenge_id.in_([c.id for c in active_challenges])
            ).all()
            
            # Calculate scores based on metric type
            scored_participants = []
            for participant in participants:
                score = self._calculate_score(participant, metric)
                scored_participants.append({
                    "user_id": participant.user_id,
                    "score": score,
                    "rank": self._get_rank(participants, score),
                    "display_name": participant.user.public_profile.display_name if participant.user else "Anonymous"
                })
            
            # Sort by score descending and limit to top 50
            scored_participants.sort(key=lambda x: x["score"], reverse=True)
            leaderboard_data.append({
                "challenge_id": challenge.id,
                "title": challenge.title,
                "leaderboard": scored_participants[:50]
            })
        
        return leaderboard_data
    
    def _calculate_score(self, participant: ChallengeParticipant, metric: str) -> float:
        """Calculate score based on metric type"""
        if metric == "workouts":
            return participant.current_value or 0
        elif metric == "volume":
            return participant.current_value or 0
        elif metric == "readiness":
            return participant.current_value or 0
        return participant.current_value or 0
    
    def _get_rank(self, participants: List[ChallengeParticipant], score: float) -> int:
        """Get rank of participant based on score"""
        ranked = sorted(participants, key=lambda p: self._calculate_score(p, "workouts"), reverse=True)
        return sum(1 for p in ranked if self._calculate_score(p, "workouts") > score) + 1
    
    def _get_active_challenges(self, start_date: Optional[datetime] = None) -> List[Challenge]:
        """Get challenges active for the current period"""
        # Get challenges starting within the period or ongoing
        query = self.session.query(Challenge)
        if start_date:
            query = query.filter(Challenge.start_date >= start_date)
        return query.filter(Challenge.end_date < datetime.utcnow() + timedelta(days=1)).all()
    
    def get_active_challenges(self) -> List[Dict]:
        """Get active challenges for display in frontend"""
        challenges = self._get_active_challenges()
        return [{
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "type": c.type.value,
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat(),
            "prize_xp": c.prize_xp
        } for c in challenges]
    
    def join_challenge(self, challenge_id: int, user_id: str) -> bool:
        """Join a challenge as participant"""
        # Check if user is ATLAS Pro
        user = self.session.query(UserPublicProfile).filter(
            UserPublicProfile.user_id == user_id
        ).first()
        if not user or not user.is_pro:
            return False
        
        # Create participant entry
        participant = ChallengeParticipant(
            challenge_id=challenge_id,
            user_id=user_id,
            current_value=0
        )
        self.session.add(participant)
        self.session.commit()
        return True
    
    def get_public_profile(self, user_id: str) -> Optional[Dict]:
        """Get public profile data for a user"""
        user = self.session.query(UserPublicProfile).filter(
            UserPublicProfile.user_id == user_id
        ).first()
        return {
            "display_name": user.display_name if user else "Anonymous",
            "avatar_url": user.avatar_url if user else None,
            "is_public": user.is_public,
            "statistics": {
                "total_workouts": user.total_workouts,
                "best_readiness": user.best_readiness,
                "current_level": user.current_level
            } if user else {}
        }