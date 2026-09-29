from datetime import datetime
from pydantic import BaseModel

class ClimateDataBase(BaseModel):
    temperature: float
    humidity: float
    recorded_at: datetime
    entry_id: int

class ClimateDataCreate(ClimateDataBase):
    pass

class ClimateDataResponse(ClimateDataBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True