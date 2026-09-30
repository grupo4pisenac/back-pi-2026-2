from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer
from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ClimateData(Base):
    __tablename__ = "climate_data"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, unique=True, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)        # Registro Sensor/Thingspeak
    created_at = Column(DateTime(timezone=True), default=_utcnow)        # Registro da API