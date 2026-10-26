from datetime import datetime
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import exigir_permissao, obter_usuario_ativo_atual
from app.core.database import get_db
from app.models.user import Usuario
from app.schemas.climate import AgregadoClimatico
from app.schemas.dashboard import (
    AlertaTermico,
    LeituraClimatica,
    PrevisaoColheita,
    ResumoPainel,
    Talhao,
)
from app.schemas.station import CulturaId
from app.services.dashboard_service import (
    obter_agregados_climaticos,
    obter_alerta_termico_ativo,
    obter_leituras_climaticas,
    obter_previsao_colheita,
    obter_resumo_painel,
    obter_talhoes,
)

router = APIRouter(tags=["dashboard"])


@router.get(
    "/climate/readings",
    response_model=List[LeituraClimatica],
    dependencies=[Depends(exigir_permissao("climate:read"))],
)
async def listar_leituras_climaticas(
    range: str = Query("today", description="Intervalo de filtragem: today, 24h, 7d, 30d, all"),
    data_inicial: Optional[datetime] = Query(None, alias="from", description="Início (ISO 8601); tem precedência sobre range"),
    data_final: Optional[datetime] = Query(None, alias="to", description="Fim (ISO 8601)"),
    stationId: Optional[str] = Query(None, description="Filtra pela estação (ex.: ESP-PTR-01)"),
    maxPoints: Optional[int] = Query(None, ge=2, le=2000, description="Reduz a série a no máximo N pontos (média por janela de tempo)"),
    db: AsyncSession = Depends(get_db),
):
    """Retorna as leituras reais de telemetria climática em ordem cronológica."""
    return await obter_leituras_climaticas(
        db=db,
        filtro_periodo=range,
        data_inicial=data_inicial,
        data_final=data_final,
        id_estacao=stationId,
        max_pontos=maxPoints,
    )


@router.get(
    "/climate/aggregates",
    response_model=List[AgregadoClimatico],
    dependencies=[Depends(exigir_permissao("climate:read"))],
)
async def listar_agregados_climaticos(
    bucket: Literal["day", "hour"] = Query("day", description="Agrupamento: day (por dia) ou hour (por hora)"),
    days: int = Query(14, ge=1, le=31, description="Dias corridos, incluindo hoje (horário do Vale, UTC-3)"),
    db: AsyncSession = Depends(get_db),
):
    """Mínima, média e máxima de temperatura e umidade do ar por dia ou hora, com horas de estresse térmico."""
    return await obter_agregados_climaticos(db=db, agrupamento=bucket, dias=days)


@router.get(
    "/dashboard/summary",
    response_model=ResumoPainel,
    dependencies=[Depends(exigir_permissao("dashboard:read"))],
)
async def consultar_resumo_painel(db: AsyncSession = Depends(get_db)):
    """Retorna o sumário executivo do painel climático e de safra."""
    return await obter_resumo_painel(db)


@router.get(
    "/forecasts/harvest",
    response_model=PrevisaoColheita,
    dependencies=[Depends(exigir_permissao("forecast:read"))],
)
async def consultar_previsao_colheita(
    cropId: CulturaId = Query("UVA_SUGRAONE", description="Cultura: UVA_SUGRAONE, MANGA_PALMER, UVA_ARRA, GOIABA_PALUMA"),
    db: AsyncSession = Depends(get_db),
):
    """Retorna a série de produção e temperatura (referência e medida) da cultura informada."""
    return await obter_previsao_colheita(id_cultura=cropId, db=db)


@router.get(
    "/plots",
    response_model=List[Talhao],
    dependencies=[Depends(exigir_permissao("dashboard:read"))],
)
async def listar_talhoes(
    status: str = Query("ACTIVE", description="Filtro de status dos talhões (ACTIVE, ALL)"),
):
    """Retorna a listagem de lotes/talhões monitorados."""
    return await obter_talhoes(filtro_status=status)


@router.get(
    "/alerts/active",
    response_model=Optional[AlertaTermico],
)
async def consultar_alerta_ativo(
    usuario_atual: Usuario = Depends(obter_usuario_ativo_atual),
    db: AsyncSession = Depends(get_db),
):
    """Retorna o alerta térmico ativo (ou null) para qualquer usuário autenticado."""
    return await obter_alerta_termico_ativo(db)
