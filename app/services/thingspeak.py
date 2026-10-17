import os
from datetime import datetime
from typing import Optional
import httpx
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.climate import DadosClimaticos
from app.schemas.climate import DadosClimaticosCriar

load_dotenv()

URL_BASE = "https://api.thingspeak.com"
FAIXA_TEMPERATURA = (-40.0, 100.0)
FAIXA_UMIDADE = (0.0, 100.0)


def buscar_leituras(quantidade: int = 10) -> list[dict]:
    """Busca as últimas leituras do canal do ThingSpeak."""
    id_canal = os.getenv("THINGSPEAK_CHANNEL_ID")
    chave_leitura = os.getenv("THINGSPEAK_READ_KEY")
    if not id_canal or not chave_leitura:
        raise RuntimeError("THINGSPEAK_CHANNEL_ID e THINGSPEAK_READ_KEY devem estar configurados no .env")

    resposta = httpx.get(
        f"{URL_BASE}/channels/{id_canal}/feeds.json",
        params={"api_key": chave_leitura, "results": quantidade},
        timeout=10.0,
    )
    resposta.raise_for_status()
    return resposta.json().get("feeds", [])


def analisar_leitura(leitura_bruta: dict) -> Optional[DadosClimaticosCriar]:
    try:
        id_entrada = int(leitura_bruta.get("entry_id"))
        temperatura = float(leitura_bruta.get("field1"))
        umidade = float(leitura_bruta.get("field2"))
        registrado_em = datetime.fromisoformat(leitura_bruta.get("created_at").replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None

    if not (FAIXA_TEMPERATURA[0] <= temperatura <= FAIXA_TEMPERATURA[1]):
        return None
    if not (FAIXA_UMIDADE[0] <= umidade <= FAIXA_UMIDADE[1]):
        return None

    return DadosClimaticosCriar(
        id_entrada=id_entrada,
        temperatura=temperatura,
        umidade=umidade,
        registrado_em=registrado_em,
    )


def salvar_novas_leituras(db: Session, registros: list[DadosClimaticosCriar]) -> tuple[int, int]:
    if not registros:
        return 0, 0

    ids = [registro.id_entrada for registro in registros]
    existentes = set(
        db.scalars(select(DadosClimaticos.id_entrada).where(DadosClimaticos.id_entrada.in_(ids)))
    )

    novas_linhas = [
        DadosClimaticos(
            id_entrada=registro.id_entrada,
            temperatura=registro.temperatura,
            umidade=registro.umidade,
            registrado_em=registro.registrado_em,
        )
        for registro in registros
        if registro.id_entrada not in existentes
    ]

    db.add_all(novas_linhas)
    db.commit()
    return len(novas_linhas), len(registros) - len(novas_linhas)


def processar_leituras(db: Session, leituras_brutas: list[dict]) -> dict:
    registros = []
    descartados = 0
    for leitura in leituras_brutas:
        registro = analisar_leitura(leitura)
        if registro is None:
            descartados += 1
        else:
            registros.append(registro)

    salvos, duplicados = salvar_novas_leituras(db, registros)
    return {
        "fetched": len(leituras_brutas),
        "saved": salvos,
        "duplicates": duplicados,
        "discarded": descartados,
    }


# Aliases para compatibilidade entre módulos
BASE_URL = URL_BASE
TEMPERATURE_RANGE = FAIXA_TEMPERATURA
HUMIDITY_RANGE = FAIXA_UMIDADE
fetch_feeds = buscar_leituras
parse_feed = analisar_leitura
save_new = salvar_novas_leituras
process_feeds = processar_leituras