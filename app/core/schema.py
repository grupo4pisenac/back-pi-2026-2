"""
Atualização leve do schema para bancos criados por versões anteriores da API.
`Base.metadata.create_all` só cria tabelas novas; aqui adicionamos as colunas que faltam.
Idempotente: pode rodar a cada inicialização.
"""
import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.core.database import Base

logger = logging.getLogger(__name__)

# tabela -> {coluna: DDL usado no ADD COLUMN}
COLUNAS_NOVAS: dict[str, dict[str, str]] = {
    "usuarios": {
        "nome": "VARCHAR NOT NULL DEFAULT ''",
        "ultimo_acesso_em": "TIMESTAMP WITH TIME ZONE",
        "criado_em": "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
    },
    "dados_climaticos": {
        "umidade_solo": "DOUBLE PRECISION",
        "chuva": "DOUBLE PRECISION",
    },
}


def _recriar_stations_legada(conexao: Connection) -> None:
    """A tabela antiga usava id inteiro e localizacao; o contrato atual usa o ID do ESP32 (texto)."""
    inspetor = inspect(conexao)
    if "stations" not in inspetor.get_table_names():
        return
    colunas = {c["name"]: c for c in inspetor.get_columns("stations")}
    if "canal_thingspeak" in colunas:
        return
    total = conexao.execute(text("SELECT count(*) FROM stations")).scalar_one()
    if total:
        logger.error(
            "Tabela 'stations' está no formato antigo e possui %s registro(s). "
            "Migre ou apague os dados manualmente e reinicie a API.",
            total,
        )
        return
    logger.warning("Recriando a tabela 'stations' (formato antigo e vazia).")
    conexao.execute(text("DROP TABLE stations"))
    Base.metadata.tables["stations"].create(conexao)


def atualizar_schema(conexao: Connection) -> None:
    if conexao.dialect.name != "postgresql":
        return
    _recriar_stations_legada(conexao)
    inspetor = inspect(conexao)
    tabelas = set(inspetor.get_table_names())
    for tabela, colunas in COLUNAS_NOVAS.items():
        if tabela not in tabelas:
            continue
        existentes = {c["name"] for c in inspetor.get_columns(tabela)}
        for coluna, ddl in colunas.items():
            if coluna not in existentes:
                logger.warning("Adicionando coluna %s.%s", tabela, coluna)
                conexao.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {ddl}"))
