"""
Popula o banco com dados iniciais para desenvolvimento e integração com o front-end.
Idempotente: registros já existentes (mesmo email / mesmo ID de estação) são mantidos.

Uso:  python -m app.seed
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, async_engine
from app.core.schema import atualizar_schema
from app.core.security import gerar_hash_senha
from app.models.climate import DadosClimaticos  # noqa: F401 — registra no Base.metadata
from app.models.station import Station
from app.models.user import PerfilUsuario, Usuario
from app.services.station_service import calcular_posicao

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed")

SENHA_PADRAO = os.getenv("SEED_PASSWORD", "barto@2026")

USUARIOS = [
    ("Administrador Bartô", "admin@barto.io", PerfilUsuario.ADMIN),
    ("Analista de Dados", "analista@barto.io", PerfilUsuario.ANALISTA),
    ("Produtor Exportador", "produtor@barto.io", PerfilUsuario.PRODUTOR),
]

ESTACOES = [
    ("ESP-PTR-01", "Fazenda Santa Clara", "PETROLINA", "UVA_SUGRAONE", "2481035"),
    ("ESP-PTR-02", "Sítio Boa Esperança", "PETROLINA", "MANGA_PALMER", "2481036"),
    ("ESP-PTR-03", "Projeto Senador Nilo Coelho", "PETROLINA", "UVA_ARRA", "2481037"),
    ("ESP-JZR-01", "Fazenda Mandacaru", "JUAZEIRO", "MANGA_PALMER", "2481038"),
    ("ESP-JZR-02", "Vale do Salitre", "JUAZEIRO", "GOIABA_PALUMA", "2481039"),
]

# Estação que recebe as leituras do canal real configurado em THINGSPEAK_CHANNEL_ID
ESTACAO_CANAL_REAL = "ESP-PTR-01"


async def _vincular_canal_real(db) -> None:
    """Garante que o canal ingerido (THINGSPEAK_CHANNEL_ID) apareça no mapa, ligado à ESTACAO_CANAL_REAL."""
    canal = settings.THINGSPEAK_CHANNEL_ID
    if not canal:
        return
    vinculada = await db.execute(select(Station).where(Station.canal_thingspeak == canal))
    if vinculada.scalars().first():
        logger.info("Canal %s já vinculado a uma estação", canal)
        return
    estacao = await db.get(Station, ESTACAO_CANAL_REAL)
    if estacao:
        estacao.canal_thingspeak = canal
        logger.info("Estação %s vinculada ao canal ThingSpeak %s", ESTACAO_CANAL_REAL, canal)


async def popular() -> None:
    async with async_engine.begin() as conexao:
        await conexao.run_sync(Base.metadata.create_all)
        await conexao.run_sync(atualizar_schema)

    agora = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        for nome, email, perfil in USUARIOS:
            existente = await db.execute(select(Usuario).where(Usuario.email == email))
            if existente.scalars().first():
                logger.info("Usuário já existe: %s", email)
                continue
            db.add(
                Usuario(
                    nome=nome,
                    email=email,
                    senha_hash=gerar_hash_senha(SENHA_PADRAO),
                    perfil=perfil,
                    ativo=True,
                    criado_em=agora,
                )
            )
            logger.info("Usuário criado: %s (%s)", email, perfil.value)

        for id_estacao, nome, municipio, produto, canal in ESTACOES:
            if await db.get(Station, id_estacao):
                logger.info("Estação já existe: %s", id_estacao)
                continue
            posicao_x, posicao_y = calcular_posicao(id_estacao, municipio)
            db.add(
                Station(
                    id=id_estacao,
                    nome=nome,
                    municipio=municipio,
                    produto_id=produto,
                    canal_thingspeak=canal,
                    posicao_x=posicao_x,
                    posicao_y=posicao_y,
                    bateria=100,
                    created_at=agora,
                )
            )
            logger.info("Estação criada: %s", id_estacao)

        await db.flush()
        await _vincular_canal_real(db)
        await db.commit()

    await async_engine.dispose()
    logger.info("Seed concluído. Senha dos usuários: %s", SENHA_PADRAO)


if __name__ == "__main__":
    asyncio.run(popular())
