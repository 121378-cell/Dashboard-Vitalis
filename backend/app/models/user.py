from sqlalchemy import Column, String, DateTime, Date
from sqlalchemy.sql import func
from app.db.session import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    birth_date = Column(Date, nullable=True)  # Fecha de nacimiento del atleta
    
    # Relationships
    challenge_participations = relationship("ChallengeParticipant", back_populates="user")
    public_profile = relationship("UserPublicProfile", back_populates="user", uselist=False)
    
    @property
    def age(self):
        """Calcula la edad actual basada en la fecha de nacimiento."""
        if not self.birth_date:
            return None
        
        from datetime import date
        today = date.today()
        
        # Calcular edad considerando si ya pasó el cumpleaños este año
        age = today.year - self.birth_date.year
        
        # Restar 1 si el cumpleaños aún no ha pasado este año
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            age -= 1
        
        return age
