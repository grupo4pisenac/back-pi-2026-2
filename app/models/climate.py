from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer
from app.core.database import Base

class ClimateData(Base):
    __tablename__ = "climate_data"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, unique=True, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False)        # Registro Sensor/Thingspeak
    created_at = Column(DateTime, default=datetime.utcnow) # Registro da APi