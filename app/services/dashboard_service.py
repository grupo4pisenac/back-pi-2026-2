from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.climate import DadosClimaticos
from app.schemas.dashboard import (
    AlertaTermico,
    LocalizacaoTalhao,
    PontoPrevisaoDiaria,
    PrevisaoColheita,
    ResumoPainel,
    Talhao,
)


async def obter_leituras_climaticas(db: AsyncSession, filtro_periodo: str = "today") -> List[DadosClimaticos]:
    """
    Consulta real assíncrona na tabela dados_climaticos filtrando pelo intervalo solicitado.
    Suporta: 'today' (default), '24h', '7d', '30d', 'all'.
    """
    agora = datetime.now(timezone.utc)
    periodo_normalizado = (filtro_periodo or "today").strip().lower()

    consulta = select(DadosClimaticos)

    if periodo_normalizado == "today":
        data_inicial = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        consulta = consulta.where(DadosClimaticos.registrado_em >= data_inicial)
    elif periodo_normalizado in ("24h", "1d"):
        data_inicial = agora - timedelta(hours=24)
        consulta = consulta.where(DadosClimaticos.registrado_em >= data_inicial)
    elif periodo_normalizado in ("7d", "week"):
        data_inicial = agora - timedelta(days=7)
        consulta = consulta.where(DadosClimaticos.registrado_em >= data_inicial)
    elif periodo_normalizado in ("30d", "month"):
        data_inicial = agora - timedelta(days=30)
        consulta = consulta.where(DadosClimaticos.registrado_em >= data_inicial)
    elif periodo_normalizado == "all":
        pass
    else:
        data_inicial = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        consulta = consulta.where(DadosClimaticos.registrado_em >= data_inicial)

    consulta = consulta.order_by(DadosClimaticos.registrado_em.desc())
    resultado = await db.execute(consulta)
    return list(resultado.scalars().all())


async def obter_resumo_painel() -> ResumoPainel:
    """Retorna os indicadores consolidados do painel (Mock Estratégico - Petrolina/Juazeiro)."""
    agora = datetime.now(timezone.utc)
    return ResumoPainel(
        temperatura_media=29.4,
        umidade_media=54.2,
        umidade_solo=68.5,
        total_talhoes_ativos=4,
        total_talhoes=5,
        total_alertas_ativos=1,
        status_janela_colheita="IDEAL",
        producao_estimada_ton=420.0,
        ultima_atualizacao=agora,
    )


async def obter_previsao_colheita(id_cultura: Optional[str] = None) -> PrevisaoColheita:
    """Retorna a previsão da janela ideal de colheita da safra (Mock Estratégico - RF06)."""
    hoje = date.today()
    cultura_resolvida = id_cultura or "manga-palmer"

    catalogo_culturas = {
        "manga-palmer": "Manga Palmer",
        "manga-tommy": "Manga Tommy Atkins",
        "uva-vitoria": "Uva Vitória Sem Semente",
        "uva-arra15": "Uva Arra 15",
    }
    nome_cultura = catalogo_culturas.get(cultura_resolvida.lower(), f"Cultura ({cultura_resolvida})")

    projecoes_diarias = [
        PontoPrevisaoDiaria(
            data=hoje + timedelta(days=i),
            temperatura_prevista=round(28.5 + (i * 0.3), 1),
            umidade_prevista=round(56.0 - (i * 0.8), 1),
            indice_maturacao=round(min(100.0, 82.0 + (i * 2.5)), 1),
        )
        for i in range(7)
    ]

    return PrevisaoColheita(
        id_cultura=cultura_resolvida,
        nome_cultura=nome_cultura,
        inicio_janela_ideal=hoje + timedelta(days=3),
        fim_janela_ideal=hoje + timedelta(days=10),
        indice_confianca=0.93,
        recomendacao=(
            "Condições termohigrométricas estáveis no Vale do São Francisco. "
            "Recomenda-se iniciar a colheita no 3º dia da janela ideal nas primeiras horas da manhã."
        ),
        nivel_risco="LOW",
        temperatura_media_prevista=29.8,
        umidade_media_prevista=52.5,
        projecoes_diarias=projecoes_diarias,
    )


async def obter_talhoes(filtro_status: str = "ACTIVE") -> List[Talhao]:
    """Retorna a listagem de lotes/talhões monitorados filtrada por status (Mock Estratégico)."""
    hoje = date.today()
    todos_talhoes = [
        Talhao(
            id="plot-vsf-01",
            nome="Talhão A1 - Fazenda São Francisco",
            cultura="Manga",
            variedade="Palmer",
            area_hectares=45.0,
            status="ACTIVE",
            temperatura_atual=29.2,
            umidade_atual=55.0,
            umidade_solo=71.0,
            estagio_maturacao="Maturação Fisiológica (88%)",
            localizacao=LocalizacaoTalhao(
                latitude=-9.3891,
                longitude=-40.5030,
                municipio="Petrolina - PE",
            ),
            data_estimada_colheita=hoje + timedelta(days=4),
        ),
        Talhao(
            id="plot-vsf-02",
            nome="Talhão A2 - Fazenda São Francisco",
            cultura="Manga",
            variedade="Tommy Atkins",
            area_hectares=62.5,
            status="ACTIVE",
            temperatura_atual=30.1,
            umidade_atual=51.4,
            umidade_solo=66.2,
            estagio_maturacao="Enchimento de Fruto (75%)",
            localizacao=LocalizacaoTalhao(
                latitude=-9.3945,
                longitude=-40.4982,
                municipio="Petrolina - PE",
            ),
            data_estimada_colheita=hoje + timedelta(days=12),
        ),
        Talhao(
            id="plot-vsf-03",
            nome="Talhão B1 - Vale do Salitre",
            cultura="Uva",
            variedade="Vitória (Sem Semente)",
            area_hectares=28.0,
            status="ACTIVE",
            temperatura_atual=28.7,
            umidade_atual=58.3,
            umidade_solo=74.5,
            estagio_maturacao="Brix Ideal para Colheita (94%)",
            localizacao=LocalizacaoTalhao(
                latitude=-9.4385,
                longitude=-40.5052,
                municipio="Juazeiro - BA",
            ),
            data_estimada_colheita=hoje + timedelta(days=2),
        ),
        Talhao(
            id="plot-vsf-04",
            nome="Talhão B2 - Projeto Nilo Coelho",
            cultura="Uva",
            variedade="Arra 15",
            area_hectares=34.0,
            status="ACTIVE",
            temperatura_atual=29.6,
            umidade_atual=53.0,
            umidade_solo=69.0,
            estagio_maturacao="Maturação Inicial (65%)",
            localizacao=LocalizacaoTalhao(
                latitude=-9.3210,
                longitude=-40.5612,
                municipio="Petrolina - PE",
            ),
            data_estimada_colheita=hoje + timedelta(days=18),
        ),
        Talhao(
            id="plot-vsf-05",
            nome="Talhão C1 - Mandacaru",
            cultura="Manga",
            variedade="Keitt",
            area_hectares=50.0,
            status="RESTING",
            temperatura_atual=31.0,
            umidade_atual=47.5,
            umidade_solo=52.0,
            estagio_maturacao="Pós-Colheita / Poda",
            localizacao=LocalizacaoTalhao(
                latitude=-9.4012,
                longitude=-40.4510,
                municipio="Juazeiro - BA",
            ),
            data_estimada_colheita=hoje + timedelta(days=90),
        ),
    ]

    status_normalizado = (filtro_status or "ACTIVE").strip().upper()
    if status_normalizado == "ALL":
        return todos_talhoes

    return [talhao for talhao in todos_talhoes if talhao.status.upper() == status_normalizado]


async def obter_alerta_termico_ativo() -> Optional[AlertaTermico]:
    """Retorna o alerta térmico/operacional ativo (Mock Estratégico - RF09)."""
    agora = datetime.now(timezone.utc)
    return AlertaTermico(
        id="alert-therm-2026-01",
        severidade="WARNING",
        tipo="IDEAL_HARVEST_WINDOW",
        titulo="Janela Ideal de Colheita e Alerta Térmico Vespertino",
        mensagem=(
            "O Talhão B1 (Uva Vitória) atingiu índice Brix ideal com baixa umidade prevista para as próximas 48h. "
            "Temperatura acima de 30°C detectada no Talhão A2 — ajuste a lâmina de irrigação."
        ),
        id_talhao="plot-vsf-03",
        nome_talhao="Talhão B1 - Vale do Salitre",
        temperatura_registrada=30.8,
        temperatura_limite=30.0,
        umidade_registrada=49.5,
        disparado_em=agora - timedelta(minutes=25),
        ativo=True,
    )


# Aliases para compatibilidade entre módulos
get_climate_readings = obter_leituras_climaticas
get_dashboard_summary = obter_resumo_painel
get_harvest_forecast = obter_previsao_colheita
get_plots = obter_talhoes
get_active_thermal_alert = obter_alerta_termico_ativo
