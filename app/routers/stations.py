from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import RoleChecker
from app.core.database import get_db
from app.models.station import Station
from app.models.user import PerfilUsuario
from app.schemas.station import NetworkHealth, StationInput, Station as StationSchema

router = APIRouter(prefix="/stations", tags=["stations"])

# Permissões RBAC
permissao_leitura_estacoes = RoleChecker([PerfilUsuario.ANALISTA, PerfilUsuario.ADMIN])
permissao_admin = RoleChecker([PerfilUsuario.ADMIN])


@router.get(
    "",
    response_model=List[StationSchema],
    dependencies=[Depends(permissao_leitura_estacoes)],
)
async def listar_estacoes(db: AsyncSession = Depends(get_db)):
    """Lista todas as estações/sensores cadastrados."""
    resultado = await db.execute(select(Station).order_by(Station.id.asc()))
    return resultado.scalars().all()


@router.get(
    "/health",
    response_model=NetworkHealth,
    dependencies=[Depends(permissao_leitura_estacoes)],
)
async def consultar_saude_rede(db: AsyncSession = Depends(get_db)):
    """Retorna métricas de saúde e conectividade da rede de estações."""
    resultado = await db.execute(select(Station))
    estacoes = resultado.scalars().all()

    total = len(estacoes)
    ativas = sum(1 for e in estacoes if e.status_ativo)
    inativas = total - ativas

    estado_rede = "HEALTHY"
    if total > 0 and inativas > ativas:
        estado_rede = "DEGRADED"
    elif total == 0:
        estado_rede = "ONLINE"

    return NetworkHealth(
        status=estado_rede,
        total_stations=total,
        active_stations=ativas,
        inactive_stations=inativas,
        average_latency_ms=38.4,
        packet_loss_rate=0.005,
        last_sync=datetime.now(timezone.utc),
    )


@router.post(
    "",
    response_model=StationSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(permissao_admin)],
)
async def criar_estacao(dados: StationInput, db: AsyncSession = Depends(get_db)):
    """Cadastra uma nova estação meteorológica/sensor (Apenas Administrador)."""
    nova_estacao = Station(
        nome=dados.nome,
        localizacao=dados.localizacao,
        status_ativo=dados.status_ativo,
        created_at=datetime.now(timezone.utc),
    )
    db.add(nova_estacao)
    await db.commit()
    await db.refresh(nova_estacao)
    return nova_estacao


@router.put(
    "/{id}",
    response_model=StationSchema,
    dependencies=[Depends(permissao_admin)],
)
async def atualizar_estacao(id: int, dados: StationInput, db: AsyncSession = Depends(get_db)):
    """Atualiza os dados de uma estação existente (Apenas Administrador)."""
    resultado = await db.execute(select(Station).where(Station.id == id))
    estacao = resultado.scalars().first()

    if not estacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estação não encontrada",
        )

    estacao.nome = dados.nome
    estacao.localizacao = dados.localizacao
    estacao.status_ativo = dados.status_ativo

    await db.commit()
    await db.refresh(estacao)
    return estacao


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(permissao_admin)],
)
async def remover_estacao(id: int, db: AsyncSession = Depends(get_db)):
    """Remove uma estação cadastrada (Apenas Administrador)."""
    resultado = await db.execute(select(Station).where(Station.id == id))
    estacao = resultado.scalars().first()

    if not estacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estação não encontrada",
        )

    await db.delete(estacao)
    await db.commit()
    return None
