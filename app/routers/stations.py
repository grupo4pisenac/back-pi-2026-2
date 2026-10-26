from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import exigir_permissao
from app.core.database import get_db
from app.models.station import Station
from app.schemas.station import NetworkHealth, StationInput, Station as StationSchema
from app.services.station_service import (
    calcular_posicao,
    calcular_saude_rede,
    listar_estacoes,
    montar_estacao,
    obter_ultima_leitura,
)

router = APIRouter(prefix="/stations", tags=["stations"])

# Permissões RBAC (matriz do front-end): leitura para todos os perfis, escrita apenas ADMIN
permissao_leitura_estacoes = exigir_permissao("sensors:read")
permissao_escrita_estacoes = exigir_permissao("sensors:write")


async def _responder(db: AsyncSession, estacao: Station) -> StationSchema:
    ultima_leitura = await obter_ultima_leitura(db)
    return montar_estacao(estacao, ultima_leitura, datetime.now(timezone.utc))


@router.get(
    "",
    response_model=List[StationSchema],
    dependencies=[Depends(permissao_leitura_estacoes)],
)
async def consultar_estacoes(db: AsyncSession = Depends(get_db)):
    """Lista todas as estações/sensores cadastrados com status calculado."""
    return await listar_estacoes(db)


@router.get(
    "/health",
    response_model=NetworkHealth,
    dependencies=[Depends(permissao_leitura_estacoes)],
)
async def consultar_saude_rede(db: AsyncSession = Depends(get_db)):
    """Retorna métricas de saúde da rede de estações (online = active + attention)."""
    return await calcular_saude_rede(db)


@router.post(
    "",
    response_model=StationSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(permissao_escrita_estacoes)],
)
async def criar_estacao(dados: StationInput, db: AsyncSession = Depends(get_db)):
    """Cadastra uma nova estação meteorológica/sensor (Apenas Administrador)."""
    existente = await db.execute(select(Station).where(Station.id == dados.id))
    if existente.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma estação com este ID",
        )

    posicao_x, posicao_y = calcular_posicao(dados.id, dados.municipio)
    nova_estacao = Station(
        id=dados.id,
        nome=dados.nome,
        municipio=dados.municipio,
        produto_id=dados.produto_id,
        canal_thingspeak=dados.canal_thingspeak,
        posicao_x=posicao_x,
        posicao_y=posicao_y,
        bateria=100,
        created_at=datetime.now(timezone.utc),
    )
    db.add(nova_estacao)
    await db.commit()
    await db.refresh(nova_estacao)
    return await _responder(db, nova_estacao)


@router.put(
    "/{id}",
    response_model=StationSchema,
    dependencies=[Depends(permissao_escrita_estacoes)],
)
async def atualizar_estacao(id: str, dados: StationInput, db: AsyncSession = Depends(get_db)):
    """Atualiza os dados de uma estação existente (Apenas Administrador). O ID do dispositivo é imutável."""
    resultado = await db.execute(select(Station).where(Station.id == id))
    estacao = resultado.scalars().first()

    if not estacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estação não encontrada",
        )

    if estacao.municipio != dados.municipio:
        estacao.posicao_x, estacao.posicao_y = calcular_posicao(estacao.id, dados.municipio)
    estacao.nome = dados.nome
    estacao.municipio = dados.municipio
    estacao.produto_id = dados.produto_id
    estacao.canal_thingspeak = dados.canal_thingspeak

    await db.commit()
    await db.refresh(estacao)
    return await _responder(db, estacao)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(permissao_escrita_estacoes)],
)
async def remover_estacao(id: str, db: AsyncSession = Depends(get_db)):
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
