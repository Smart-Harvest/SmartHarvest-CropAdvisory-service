import uuid
from sqlalchemy import Column, String, Float, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.database import Base


class AdvisoryHistory(Base):
    __tablename__ = "advisory_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    location = Column(String(255), nullable=False)
    soil_type = Column(String(100), nullable=False)
    weather_data = Column(JSON, nullable=True)
    recommended_crops = Column(JSON, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AdvisoryHistory(id={self.id}, user_id={self.user_id})>"
