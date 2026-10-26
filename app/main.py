import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import List
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import Base, async_engine, get_db
from app.core.schema import atualizar_schema
from app.models.climate import DadosClimaticos
from app.models.station import Station  # Garante registro no Base.metadata
from app.models.user import Usuario    # Garante registro no Base.metadata
from app.schemas.climate import DadosClimaticosResposta
from app.routers import auth, dashboard, ingestion, stations, users
from app.services.scheduler import loop_ingestao

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    # Inicializa as tabelas de forma assíncrona se o banco de dados estiver acessível
    try:
        async with async_engine.begin() as conexao:
            await conexao.run_sync(Base.metadata.create_all)
            await conexao.run_sync(atualizar_schema)
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
    description="API para ingestão e monitoramento climático e administrativo",
    version="1.0.0",
    lifespan=ciclo_vida,
)

# CORS para o front-end (Vite em dev); em produção ajuste CORS_ORIGINS no .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Erro padronizado: o front exibe o campo "message"; "detail" é mantido por compatibilidade
@app.exception_handler(StarletteHTTPException)
async def tratar_erro_http(request: Request, exc: StarletteHTTPException):
    mensagem = exc.detail if isinstance(exc.detail, str) else "Erro na requisição"
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": mensagem, "detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def tratar_erro_validacao(request: Request, exc: RequestValidationError):
    erros = exc.errors()
    primeiro = erros[0] if erros else {}
    campo = ".".join(str(p) for p in primeiro.get("loc", []) if p not in ("body", "query", "path"))
    mensagem = f"Dados inválidos: {campo} — {primeiro.get('msg', '')}" if campo else "Dados inválidos"
    return JSONResponse(
        status_code=422,
        content={"message": mensagem, "detail": jsonable_encoder(erros)},
    )


# Registro dos roteadores sob /api e na raiz para compatibilidade com o front-end
app.include_router(auth.router)
app.include_router(auth.router, prefix="/api", include_in_schema=False)
app.include_router(dashboard.router, prefix="/api")
app.include_router(dashboard.router, include_in_schema=False)
app.include_router(stations.router, prefix="/api")
app.include_router(stations.router, include_in_schema=False)
app.include_router(users.router, prefix="/api")
app.include_router(users.router, include_in_schema=False)
app.include_router(ingestion.router, prefix="/api")


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