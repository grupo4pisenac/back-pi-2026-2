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

from app.core.database import Base, async_engine, get_db
from app.models.climate import DadosClimaticos
from app.schemas.climate import DadosClimaticosResposta
from app.routers import auth, dashboard, ingestion
from app.services.scheduler import loop_ingestao

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    # Inicializa as tabelas de forma assíncrona se o banco de dados estiver acessível
    try:
        async with async_engine.begin() as conexao:
            await conexao.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logging.warning("Aviso: Não foi possível conectar ao banco para create_all na inicialização: %s", exc)

    tarefa = None
    if os.getenv("INGEST_ENABLED", "true").lower() == "true":
        intervalo = int(os.getenv("INGEST_INTERVAL_SECONDS", "60"))
        tarefa = asyncio.create_task(loop_ingestao(intervalo))
    yield
    if tarefa:
        tarefa.cancel()


app = FastAPI(
    title="Dashboard de Monitoramento Climático e Safra API",
    description="API para ingestão e monitoramento climático e preditivo de colheita",
    version="1.0.0",
    lifespan=ciclo_vida,
)

# Registro dos roteadores sob /api e também na raiz para compatibilidade total com o front-end
app.include_router(auth.router)
app.include_router(auth.router, prefix="/api", include_in_schema=False)
app.include_router(dashboard.router, prefix="/api")
app.include_router(dashboard.router, include_in_schema=False)
app.include_router(ingestion.router)


@app.get("/")
async def raiz():
    return {"message": "API online."}


@app.get("/health")
async def verificar_saude(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Banco de dados indisponível")
    return {"status": "ok", "database": "connected"}


@app.get("/api/climate", response_model=List[DadosClimaticosResposta])
async def listar_registros_climaticos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    resultado = await db.execute(
        select(DadosClimaticos).order_by(DadosClimaticos.registrado_em.desc()).offset(skip).limit(limit)
    )
    registros = resultado.scalars().all()
    return registros