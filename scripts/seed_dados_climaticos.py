import math
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.climate import DadosClimaticos


# Configuração do histórico
DIAS_HISTORICO = 365
INTERVALO_MINUTOS = 15

# Faixa reservada para IDs dos registros simulados
ID_SEED_INICIAL = 1_000_000_000

# Semente fixa para gerar sempre os mesmos valores
GERADOR = random.Random(42)


def gerar_leitura(data: datetime, indice: int) -> dict:
    """Gera uma leitura climática simulada."""

    hora = data.hour + data.minute / 60

    # Variação diária de temperatura
    temperatura = (
        25
        + 5 * math.sin((hora - 9) * 2 * math.pi / 24)
        + GERADOR.uniform(-1.5, 1.5)
    )

    # Variação de umidade do ar
    umidade = (
        65
        - 12 * math.sin((hora - 9) * 2 * math.pi / 24)
        + GERADOR.uniform(-5, 5)
    )

    # Umidade do solo
    umidade_solo = 55 + GERADOR.uniform(-8, 8)

    # Chuva ocasional
    chuva = 0.0
    if GERADOR.random() < 0.025:
        chuva = round(GERADOR.uniform(0.5, 12.0), 2)
        umidade_solo += GERADOR.uniform(2, 8)

    return {
        "id_entrada": ID_SEED_INICIAL + indice,
        "temperatura": round(max(15, min(42, temperatura)), 2),
        "umidade": round(max(25, min(100, umidade)), 2),
        "umidade_solo": round(max(10, min(100, umidade_solo)), 2),
        "chuva": chuva,
        "registrado_em": data,
    }


def executar_seed():
    total_registros = DIAS_HISTORICO * 24 * 60 // INTERVALO_MINUTOS

    with SessionLocal() as db:
        # Impede uma segunda execução
        ultimo_id_seed = ID_SEED_INICIAL + total_registros - 1

        registros_existentes = db.scalar(
            select(func.count())
            .select_from(DadosClimaticos)
            .where(
                DadosClimaticos.id_entrada.between(
                    ID_SEED_INICIAL,
                    ultimo_id_seed,
                )
            )
        )

        if registros_existentes:
            raise RuntimeError(
                "Já existem registros na faixa reservada ao seed. "
                "Nenhum dado foi inserido."
            )

        # Localiza a primeira leitura real
        primeira_leitura = db.scalar(
            select(func.min(DadosClimaticos.registrado_em))
        )

        if primeira_leitura is None:
            raise RuntimeError(
                "Não existem leituras reais no banco. "
                "Execute o seed somente depois da primeira leitura ThingSpeak."
            )

        # Último registro simulado será 15 minutos antes da primeira leitura real
        fim = primeira_leitura - timedelta(minutes=INTERVALO_MINUTOS)

        # Início de um ano antes
        inicio = fim - timedelta(days=DIAS_HISTORICO) + timedelta(
            minutes=INTERVALO_MINUTOS
        )

        leituras = []

        for indice in range(total_registros):
            data = inicio + timedelta(
                minutes=indice * INTERVALO_MINUTOS
            )

            leituras.append(
                DadosClimaticos(**gerar_leitura(data, indice))
            )

        # Insere tudo em uma única transação
        try:
            db.add_all(leituras)
            db.commit()
        except Exception:
            db.rollback()
            raise

        print(f"Seed concluído: {len(leituras)} registros inseridos.")
        print(f"Primeiro registro: {inicio.isoformat()}")
        print(f"Último registro: {fim.isoformat()}")
        print(f"Primeira leitura real: {primeira_leitura.isoformat()}")


if __name__ == "__main__":
    executar_seed()
