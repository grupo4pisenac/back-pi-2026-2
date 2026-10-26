from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import List, Optional
from sqlalchemy import extract, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.climate import DadosClimaticos
from app.models.station import Station
from app.schemas.climate import AgregadoClimatico, EstatisticaSerie, LeituraClimatica
from app.schemas.dashboard import (
    AlertaTermico,
    PontoPrevisaoColheita,
    PrevisaoColheita,
    ResumoPainel,
    Talhao,
)

# Limiares do alerta térmico (°C)
LIMIAR_ATENCAO_C = 35.0
LIMIAR_CRITICO_C = 38.0

# Petrolina/Juazeiro: UTC-3 o ano todo (sem horário de verão desde 2019)
FUSO_LOCAL = timezone(timedelta(hours=-3), "BRT")


def _meia_noite_local(agora: datetime) -> datetime:
    return agora.astimezone(FUSO_LOCAL).replace(hour=0, minute=0, second=0, microsecond=0)


def _inicio_periodo(filtro_periodo: str, agora: datetime) -> Optional[datetime]:
    periodo = (filtro_periodo or "today").strip().lower()
    if periodo in ("24h", "1d"):
        return agora - timedelta(hours=24)
    if periodo in ("7d", "week"):
        return agora - timedelta(days=7)
    if periodo in ("30d", "month"):
        return agora - timedelta(days=30)
    if periodo == "all":
        return None
    # "today" (default) e valores desconhecidos: desde a meia-noite no horário do Vale
    return _meia_noite_local(agora)


async def _id_estacao_ingestao(db: AsyncSession) -> str:
    """Estação vinculada ao canal ThingSpeak ingerido; sem cadastro, usa o próprio canal como identificador."""
    if settings.THINGSPEAK_CHANNEL_ID:
        resultado = await db.execute(
            select(Station.id).where(Station.canal_thingspeak == settings.THINGSPEAK_CHANNEL_ID)
        )
        id_estacao = resultado.scalars().first()
        if id_estacao:
            return id_estacao
    return settings.THINGSPEAK_CHANNEL_ID or "THINGSPEAK"


async def _consultar_dados(db: AsyncSession, desde: Optional[datetime], ate: Optional[datetime] = None) -> List[DadosClimaticos]:
    consulta = select(DadosClimaticos)
    if desde is not None:
        consulta = consulta.where(DadosClimaticos.registrado_em >= desde)
    if ate is not None:
        consulta = consulta.where(DadosClimaticos.registrado_em <= ate)
    resultado = await db.execute(consulta.order_by(DadosClimaticos.registrado_em.asc()))
    return list(resultado.scalars().all())


def _media(valores: List[Optional[float]], casas: int = 1) -> Optional[float]:
    presentes = [v for v in valores if v is not None]
    return round(mean(presentes), casas) if presentes else None


def _reduzir_pontos(registros: List[DadosClimaticos], max_pontos: int, id_estacao: str) -> List[LeituraClimatica]:
    """
    Agrupa as leituras em `max_pontos` janelas de tempo iguais e devolve a média de cada janela
    (chuva é somada). Mantém o gráfico leve em períodos longos sem perder a forma da série.
    """
    inicio = registros[0].registrado_em.timestamp()
    duracao = registros[-1].registrado_em.timestamp() - inicio
    largura = duracao / max_pontos or 1.0

    janelas: dict[int, List[DadosClimaticos]] = {}
    for r in registros:
        indice = min(int((r.registrado_em.timestamp() - inicio) / largura), max_pontos - 1)
        janelas.setdefault(indice, []).append(r)

    pontos = []
    for grupo in janelas.values():
        chuvas = [r.chuva for r in grupo if r.chuva is not None]
        pontos.append(
            LeituraClimatica(
                id=str(grupo[-1].id),
                id_estacao=id_estacao,
                # Instante médio da janela
                registrado_em=datetime.fromtimestamp(mean(r.registrado_em.timestamp() for r in grupo), tz=timezone.utc),
                temperatura=_media([r.temperatura for r in grupo], 2),
                umidade_solo=_media([r.umidade_solo for r in grupo], 2),
                umidade_ar=_media([r.umidade for r in grupo], 2),
                chuva=round(sum(chuvas), 2) if chuvas else None,
            )
        )
    return pontos


async def obter_leituras_climaticas(
    db: AsyncSession,
    filtro_periodo: str = "today",
    data_inicial: Optional[datetime] = None,
    data_final: Optional[datetime] = None,
    id_estacao: Optional[str] = None,
    max_pontos: Optional[int] = None,
) -> List[LeituraClimatica]:
    """
    Leituras reais da tabela dados_climaticos em ordem cronológica crescente.
    `from`/`to` têm precedência sobre `range` (today, 24h, 7d, 30d, all).
    Com `max_pontos`, séries maiores são reduzidas por média em janelas de tempo.
    """
    agora = datetime.now(timezone.utc)
    desde = data_inicial if (data_inicial or data_final) else _inicio_periodo(filtro_periodo, agora)

    estacao = await _id_estacao_ingestao(db)
    if id_estacao and id_estacao != estacao:
        return []

    registros = await _consultar_dados(db, desde, data_final)
    if max_pontos and len(registros) > max_pontos:
        return _reduzir_pontos(registros, max_pontos, estacao)

    return [
        LeituraClimatica(
            id=str(r.id),
            id_estacao=estacao,
            registrado_em=r.registrado_em,
            temperatura=r.temperatura,
            umidade_solo=r.umidade_solo,
            umidade_ar=r.umidade,
            chuva=r.chuva,
        )
        for r in registros
    ]


async def obter_resumo_painel(db: AsyncSession) -> ResumoPainel:
    """
    KPIs do painel. Clima vem das leituras reais (últimas 24 h vs. média de 30 dias) e fica null
    quando não há leitura ou o sensor não mede a grandeza. Produção ainda é estimativa estratégica.
    """
    agora = datetime.now(timezone.utc)
    leituras_30d = await _consultar_dados(db, agora - timedelta(days=30))
    leituras_24h = [r for r in leituras_30d if r.registrado_em >= agora - timedelta(hours=24)]
    leituras_7d = [r for r in leituras_30d if r.registrado_em >= agora - timedelta(days=7)]

    ultima = leituras_30d[-1] if leituras_30d else await _ultima_leitura(db)
    media_24h = _media([r.temperatura for r in leituras_24h])
    media_30d = _media([r.temperatura for r in leituras_30d])
    chuvas_7d = [r.chuva for r in leituras_7d if r.chuva is not None]

    return ResumoPainel(
        producao_projetada_t=1248,
        variacao_producao_pct=8.2,
        temperatura_media_c=media_24h,
        delta_temperatura_c=round(media_24h - media_30d, 1) if media_24h is not None and media_30d is not None else None,
        umidade_ar_pct=_media([r.umidade for r in leituras_24h]),
        umidade_solo_pct=_media([r.umidade_solo for r in leituras_24h]),
        chuva_7d_mm=round(sum(chuvas_7d), 1) if chuvas_7d else None,
        ultima_leitura_em=ultima.registrado_em if ultima else None,
    )


async def _ultima_leitura(db: AsyncSession) -> Optional[DadosClimaticos]:
    resultado = await db.execute(select(DadosClimaticos).order_by(DadosClimaticos.registrado_em.desc()).limit(1))
    return resultado.scalars().first()


MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
TEMPERATURAS_MENSAIS = [30.2, 29.8, 29.1, 28.4, 27.2, 26.1, 25.9, 27.0, 29.3, 31.0, 31.8, 31.2]
PRODUCAO_MENSAL: dict[str, List[float]] = {
    "UVA_SUGRAONE": [62, 70, 78, 84, 92, 88, 96, 108, 118, 126, 134, 140],
    "MANGA_PALMER": [120, 110, 96, 84, 80, 92, 104, 128, 152, 170, 186, 178],
    "UVA_ARRA": [44, 50, 56, 60, 66, 63, 70, 78, 86, 92, 98, 101],
    "GOIABA_PALUMA": [30, 32, 35, 38, 36, 34, 37, 41, 45, 48, 52, 50],
}


async def _temperatura_media_por_mes(db: AsyncSession, inicio_ano: datetime) -> dict[int, float]:
    """Média mensal medida pela estação no ano corrente (mês 1–12, no horário do Vale)."""
    mes_local = extract("month", func.timezone("America/Recife", DadosClimaticos.registrado_em))
    resultado = await db.execute(
        select(mes_local, func.avg(DadosClimaticos.temperatura))
        .where(DadosClimaticos.registrado_em >= inicio_ano)
        .group_by(mes_local)
    )
    return {int(mes): round(float(media), 1) for mes, media in resultado.all() if media is not None}


async def obter_previsao_colheita(id_cultura: str = "UVA_SUGRAONE", db: Optional[AsyncSession] = None) -> PrevisaoColheita:
    """
    Série mensal de produção e temperatura da cultura; meses após o atual são projetados (RF06).
    A temperatura climatológica de referência vem acompanhada da média real medida pela estação.
    """
    agora_local = datetime.now(timezone.utc).astimezone(FUSO_LOCAL)
    mes_atual = agora_local.month - 1
    inicio_ano = agora_local.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    medidas = await _temperatura_media_por_mes(db, inicio_ano) if db is not None else {}
    return PrevisaoColheita(
        id_cultura=id_cultura,
        pontos=[
            PontoPrevisaoColheita(
                periodo=periodo,
                producao_t=PRODUCAO_MENSAL[id_cultura][i],
                temperatura_media_c=TEMPERATURAS_MENSAIS[i],
                temperatura_medida_c=medidas.get(i + 1) if i <= mes_atual else None,
                projetado=i > mes_atual,
            )
            for i, periodo in enumerate(MESES)
        ],
    )


# Intervalo máximo atribuído a uma leitura; acima disso considera-se falha de transmissão
INTERVALO_MAXIMO_LEITURA = timedelta(minutes=30)


def _inicio_intervalo(instante: datetime, agrupamento: str) -> datetime:
    local = instante.astimezone(FUSO_LOCAL)
    if agrupamento == "hour":
        return local.replace(minute=0, second=0, microsecond=0)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def _estatistica(valores: List[float]) -> EstatisticaSerie:
    return EstatisticaSerie(minimo=round(min(valores), 1), media=round(mean(valores), 1), maximo=round(max(valores), 1))


async def obter_agregados_climaticos(db: AsyncSession, agrupamento: str = "day", dias: int = 14) -> List[AgregadoClimatico]:
    """
    Agrega as leituras por dia ou por hora (horário do Vale) dos últimos `dias` dias corridos,
    incluindo hoje. Só devolve intervalos com leitura.
    Horas de estresse térmico: tempo coberto por leituras ≥ 35 °C (cada leitura vale até a
    próxima, limitado a 30 min para não contar falhas de transmissão).
    """
    agora = datetime.now(timezone.utc)
    desde = _meia_noite_local(agora) - timedelta(days=dias - 1)
    registros = await _consultar_dados(db, desde)

    grupos: dict[datetime, List[DadosClimaticos]] = {}
    estresse: dict[datetime, float] = {}
    for i, r in enumerate(registros):
        chave = _inicio_intervalo(r.registrado_em, agrupamento)
        grupos.setdefault(chave, []).append(r)
        if r.temperatura >= LIMIAR_ATENCAO_C:
            proximo = registros[i + 1].registrado_em if i + 1 < len(registros) else agora
            duracao = min(proximo - r.registrado_em, INTERVALO_MAXIMO_LEITURA)
            estresse[chave] = estresse.get(chave, 0.0) + duracao.total_seconds() / 3600

    return [
        AgregadoClimatico(
            inicio=inicio,
            leituras=len(grupo),
            temperatura=_estatistica([r.temperatura for r in grupo]),
            umidade_ar=_estatistica([r.umidade for r in grupo]),
            horas_estresse_termico=round(estresse.get(inicio, 0.0), 2),
        )
        for inicio, grupo in sorted(grupos.items())
    ]


TALHOES = [
    Talhao(id="p1", nome="Sugraone Norte", codigo="T-04", id_cultura="UVA_SUGRAONE", area_ha=12, dias_para_colheita=18, progresso=82),
    Talhao(id="p2", nome="Manga Palmer Leste", codigo="T-07", id_cultura="MANGA_PALMER", area_ha=20, dias_para_colheita=34, progresso=64),
    Talhao(id="p3", nome="Arra 15 Encosta", codigo="T-11", id_cultura="UVA_ARRA", area_ha=8, dias_para_colheita=46, progresso=51),
    Talhao(id="p4", nome="Goiaba Paluma Sul", codigo="T-02", id_cultura="GOIABA_PALUMA", area_ha=6, dias_para_colheita=61, progresso=37),
]


async def obter_talhoes(filtro_status: str = "ACTIVE") -> List[Talhao]:
    """Talhões monitorados (cadastro estratégico — todos em ciclo ativo)."""
    status_normalizado = (filtro_status or "ACTIVE").strip().upper()
    if status_normalizado in ("ACTIVE", "ALL"):
        return list(TALHOES)
    return []


async def obter_alerta_termico_ativo(db: AsyncSession) -> Optional[AlertaTermico]:
    """Alerta térmico a partir do pico de temperatura das últimas 24 h (RF09); None se dentro do limite."""
    agora = datetime.now(timezone.utc)
    leituras = await _consultar_dados(db, agora - timedelta(hours=24))
    if not leituras:
        return None

    pico = max(leituras, key=lambda r: r.temperatura)
    if pico.temperatura < LIMIAR_ATENCAO_C:
        return None

    critico = pico.temperatura >= LIMIAR_CRITICO_C
    horario = pico.registrado_em.astimezone(FUSO_LOCAL).strftime("%Hh%M")
    temperatura = f"{pico.temperatura:.1f}".replace(".", ",")  # decimal em pt-BR
    return AlertaTermico(
        id=f"alt_{pico.id}",
        titulo="Alerta térmico crítico" if critico else "Alerta térmico",
        mensagem=(
            f"Pico de {temperatura} °C registrado às {horario} nas últimas 24 h. "
            + (
                "Risco alto de estresse hídrico — reforce a irrigação no início da manhã."
                if critico
                else "Acompanhe a demanda de irrigação nas horas mais quentes."
            )
        ),
        severidade="critico" if critico else "atencao",
    )


# Aliases para compatibilidade entre módulos
get_climate_readings = obter_leituras_climaticas
get_dashboard_summary = obter_resumo_painel
get_harvest_forecast = obter_previsao_colheita
get_plots = obter_talhoes
get_active_thermal_alert = obter_alerta_termico_ativo
