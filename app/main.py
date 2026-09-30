import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import List
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.core.database import Base, engine, get_db
from app.models.climate import ClimateData
from app.schemas.climate import ClimateDataResponse
from app.routers import ingestion
from app.services.scheduler import ingestion_loop


logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if os.getenv("INGEST_ENABLED", "true").lower() == "true":
        interval = int(os.getenv("INGEST_INTERVAL_SECONDS", "60"))
        task = asyncio.create_task(ingestion_loop(interval))
    yield
    if task:
        task.cancel()

app = FastAPI(
    title="Dashboard Climático e Logístico API",
    description="API para ingestão e monitoramento de dados de exportação de frutas",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(ingestion.router)

@app.get("/")
def read_root():
    return {"message": "API online e conectada ao banco de dados."}

@app.get("/api/climate", response_model=List[ClimateDataResponse])
def get_climate_records(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    records = db.query(ClimateData).order_by(ClimateData.recorded_at.desc()).offset(skip).limit(limit).all()
    return records