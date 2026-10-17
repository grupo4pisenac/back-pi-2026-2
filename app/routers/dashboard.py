from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import exigir_permissao, obter_usuario_ativo_atual
from app.core.database import get_db
from app.models.user import Usuario
from app.schemas.dashboard import (
    AlertaTermico,
    LeituraClimatica,
    PrevisaoColheita,
    ResumoPainel,
    Talhao,
)
from app.services.dashboard_service import (
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
    db: AsyncSession = Depends(get_db),
):
    """Retorna as leituras reais de telemetria climática da tabela dados_climaticos filtradas por período."""
    return await obter_leituras_climaticas(db=db, filtro_periodo=range)


@router.get(
    "/dashboard/summary",
    response_model=ResumoPainel,
    dependencies=[Depends(exigir_permissao("dashboard:read"))],
)
async def consultar_resumo_painel():
    """Retorna o sumário executivo do painel climático e de safra."""
    return await obter_resumo_painel()


@router.get(
    "/forecasts/harvest",
    response_model=PrevisaoColheita,
    dependencies=[Depends(exigir_permissao("forecast:read"))],
)
async def consultar_previsao_colheita(
    cropId: Optional[str] = Query(None, description="Identificador da cultura agrícola (ex: manga-palmer, uva-vitoria)"),
):
    """Retorna a previsão da janela ideal de colheita para a cultura informada."""
    return await obter_previsao_colheita(id_cultura=cropId)


@router.get(
    "/plots",
    response_model=List[Talhao],
    dependencies=[Depends(exigir_permissao("dashboard:read"))],
)
async def listar_talhoes(
    status: str = Query("ACTIVE", description="Filtro de status dos talhões (ACTIVE, RESTING, ALL)"),
):
    """Retorna a listagem de lotes/talhões monitorados."""
    return await obter_talhoes(filtro_status=status)


@router.get(
    "/alerts/active",
    response_model=Optional[AlertaTermico],
)
async def consultar_alerta_ativo(
    usuario_atual: Usuario = Depends(obter_usuario_ativo_atual),
):
    """Retorna o alerta térmico ativo no momento para qualquer usuário autenticado."""
    return await obter_alerta_termico_ativo()
