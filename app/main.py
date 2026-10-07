import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import List
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, engine, get_db
from app.models.climate import ClimateData
from app.schemas.climate import ClimateDataResponse
from app.routers import ingestion
from app.routers import auth
from app.services.scheduler import ingestion_loop

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

app.include_router(auth.router)
app.include_router(ingestion.router)

@app.get("/")
async def read_root():
    return {"message": "API online."}

@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Banco de dados indisponível")
    return {"status": "ok", "database": "connected"}

@app.get("/api/climate", response_model=List[ClimateDataResponse])
async def get_climate_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ClimateData).order_by(ClimateData.recorded_at.desc()).offset(skip).limit(limit))
    records = result.scalars().all()
    return records