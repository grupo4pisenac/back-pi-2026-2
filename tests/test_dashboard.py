import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import obter_usuario_ativo_atual
from app.core.database import get_db
from app.models.user import PerfilUsuario, Usuario
from app.models.climate import DadosClimaticos


def _usuario(perfil: PerfilUsuario) -> Usuario:
    return Usuario(
        id=uuid.uuid4(),
        nome="Usuário Teste",
        email="teste@agro.com",
        ativo=True,
        perfil=perfil,
        criado_em=datetime.now(timezone.utc),
    )


def _sessao_com_leituras(leituras: list[DadosClimaticos]) -> AsyncMock:
    sessao = AsyncMock()
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = leituras
    resultado.scalars.return_value.first.return_value = None
    sessao.execute.return_value = resultado
    return sessao


def _leitura(id_: int, temperatura: float, minutos_atras: int) -> DadosClimaticos:
    agora = datetime.now(timezone.utc)
    return DadosClimaticos(
        id=id_,
        id_entrada=id_,
        temperatura=temperatura,
        umidade=40.0,
        umidade_solo=48.0,
        chuva=0.5,
        registrado_em=agora - timedelta(minutes=minutos_atras),
        criado_em=agora,
    )


@pytest.fixture
def cliente():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_rotas_publicas(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert resposta.json() == {"message": "API online."}


def test_autenticacao_e_painel_nao_autorizado(cliente):
    assert cliente.get("/auth/me").status_code == 401
    assert cliente.get("/api/auth/me").status_code == 401
    assert cliente.get("/api/dashboard/summary").status_code == 401
    assert cliente.get("/api/forecasts/harvest").status_code == 401
    assert cliente.get("/api/plots").status_code == 401
    assert cliente.get("/api/climate/readings").status_code == 401
    assert cliente.get("/api/alerts/active").status_code == 401


def test_endpoints_painel_com_usuario_mock(cliente):
    leituras = [_leitura(1, 30.0, 120), _leitura(2, 36.2, 60)]

    async def sobrescrever_db():
        yield _sessao_com_leituras(leituras)

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.PRODUTOR)
    app.dependency_overrides[get_db] = sobrescrever_db

    # 1. Resumo do Painel (contrato DashboardSummary)
    res_resumo = cliente.get("/api/dashboard/summary")
    assert res_resumo.status_code == 200
    resumo = res_resumo.json()
    assert set(resumo) == {
        "projectedProductionT", "productionChangePct", "avgTemperatureC", "temperatureDeltaC",
        "airHumidityPct", "soilMoisturePct", "rainfall7dMm", "lastReadingAt",
    }
    assert resumo["avgTemperatureC"] == 33.1
    assert resumo["airHumidityPct"] == 40.0
    assert resumo["rainfall7dMm"] == 1.0

    # 2. Previsão de Colheita (contrato HarvestForecast)
    res_previsao = cliente.get("/api/forecasts/harvest?cropId=MANGA_PALMER")
    assert res_previsao.status_code == 200
    previsao = res_previsao.json()
    assert previsao["cropId"] == "MANGA_PALMER"
    assert len(previsao["points"]) == 12
    assert set(previsao["points"][0]) == {"period", "productionT", "avgTemperatureC", "measuredTemperatureC", "projected"}
    assert cliente.get("/api/forecasts/harvest?cropId=invalida").status_code == 422

    # 3. Talhões (contrato Plot)
    res_talhoes = cliente.get("/api/plots?status=ACTIVE")
    assert res_talhoes.status_code == 200
    talhoes = res_talhoes.json()
    assert len(talhoes) == 4
    assert set(talhoes[0]) == {"id", "name", "code", "cropId", "areaHa", "daysToHarvest", "progress"}

    # 4. Alerta térmico (pico ≥ 35 °C → atencao)
    res_alerta = cliente.get("/api/alerts/active")
    assert res_alerta.status_code == 200
    alerta = res_alerta.json()
    assert alerta["severity"] == "atencao"
    assert set(alerta) == {"id", "title", "message", "severity"}


def test_alerta_nulo_sem_pico_termico(cliente):
    async def sobrescrever_db():
        yield _sessao_com_leituras([_leitura(1, 29.0, 30)])

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.PRODUTOR)
    app.dependency_overrides[get_db] = sobrescrever_db

    res_alerta = cliente.get("/api/alerts/active")
    assert res_alerta.status_code == 200
    assert res_alerta.json() is None


def test_consulta_leituras_climaticas(cliente):
    async def sobrescrever_db():
        yield _sessao_com_leituras([_leitura(999, 28.5, 10)])

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.ANALISTA)
    app.dependency_overrides[get_db] = sobrescrever_db

    res_clima = cliente.get("/api/climate/readings?range=today")
    assert res_clima.status_code == 200
    leituras = res_clima.json()
    assert len(leituras) == 1
    assert leituras[0]["id"] == "999"
    assert leituras[0]["temperature"] == 28.5
    assert leituras[0]["airHumidity"] == 40.0
    assert leituras[0]["soilMoisture"] == 48.0
    assert set(leituras[0]) == {"id", "stationId", "timestamp", "temperature", "soilMoisture", "airHumidity", "rainfall"}


def test_resumo_sem_leituras_retorna_nulos(cliente):
    # Canal ainda sem dados: nada de valores inventados no painel
    async def sobrescrever_db():
        yield _sessao_com_leituras([])

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.PRODUTOR)
    app.dependency_overrides[get_db] = sobrescrever_db

    resumo = cliente.get("/api/dashboard/summary").json()
    for campo in ("avgTemperatureC", "temperatureDeltaC", "airHumidityPct", "soilMoisturePct", "rainfall7dMm", "lastReadingAt"):
        assert resumo[campo] is None, campo
    assert cliente.get("/api/climate/readings?range=24h").json() == []


def test_leituras_sem_campos_opcionais_e_reducao_de_pontos(cliente):
    # Canal real publica só field1/field2: solo e chuva vêm null, não 0
    leituras = []
    for i in range(120):
        leitura = _leitura(i + 1, 25.0 + (i % 10), 120 - i)
        leitura.umidade_solo = None
        leitura.chuva = None
        leituras.append(leitura)

    async def sobrescrever_db():
        yield _sessao_com_leituras(leituras)

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.PRODUTOR)
    app.dependency_overrides[get_db] = sobrescrever_db

    completas = cliente.get("/api/climate/readings?range=24h").json()
    assert len(completas) == 120
    assert completas[0]["soilMoisture"] is None and completas[0]["rainfall"] is None

    reduzidas = cliente.get("/api/climate/readings?range=24h&maxPoints=24").json()
    assert 1 < len(reduzidas) <= 24
    timestamps = [p["timestamp"] for p in reduzidas]
    assert timestamps == sorted(timestamps)
    assert all(25.0 <= p["temperature"] <= 34.0 for p in reduzidas)
    assert reduzidas[0]["soilMoisture"] is None
    assert cliente.get("/api/climate/readings?maxPoints=1").status_code == 422


def test_ingestao_manual_exige_admin(cliente):
    assert cliente.post("/api/ingestion/run").status_code == 401
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.ANALISTA)
    assert cliente.post("/api/ingestion/run").status_code == 403


def test_agregados_por_dia_e_hora_com_estresse_termico(cliente):
    # Leituras a cada 10 min: 6 acima de 35 °C → 1 h de estresse térmico
    leituras = [_leitura(i + 1, 36.0 if i < 6 else 30.0, 200 - i * 10) for i in range(12)]

    async def sobrescrever_db():
        yield _sessao_com_leituras(leituras)

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.PRODUTOR)
    app.dependency_overrides[get_db] = sobrescrever_db

    dias = cliente.get("/api/climate/aggregates?bucket=day&days=7").json()
    assert sum(d["readings"] for d in dias) == 12
    assert set(dias[0]) == {"start", "readings", "temperature", "airHumidity", "heatStressHours"}
    assert set(dias[0]["temperature"]) == {"min", "avg", "max"}
    assert dias[0]["start"].endswith("-03:00")
    assert max(d["temperature"]["max"] for d in dias) == 36.0
    assert min(d["temperature"]["min"] for d in dias) == 30.0
    assert abs(sum(d["heatStressHours"] for d in dias) - 1.0) < 0.01

    horas = cliente.get("/api/climate/aggregates?bucket=hour&days=1").json()
    assert sum(h["readings"] for h in horas) == 12
    assert all(h["start"][14:19] == "00:00" for h in horas)

    assert cliente.get("/api/climate/aggregates?bucket=week").status_code == 422
    assert cliente.get("/api/climate/aggregates?days=90").status_code == 422


def test_hoje_comeca_a_meia_noite_do_vale():
    from app.services.dashboard_service import FUSO_LOCAL, _inicio_periodo

    # 01:30 UTC = 22:30 do dia anterior em Petrolina
    agora = datetime(2026, 10, 23, 1, 30, tzinfo=timezone.utc)
    inicio = _inicio_periodo("today", agora)
    assert inicio == datetime(2026, 10, 22, 0, 0, tzinfo=FUSO_LOCAL)


def test_previsao_traz_temperatura_medida_nos_meses_com_leitura(cliente):
    sessao = AsyncMock()
    resultado = MagicMock()
    resultado.all.return_value = [(1, 29.44), (12, 40.0)]
    sessao.execute.return_value = resultado

    async def sobrescrever_db():
        yield sessao

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.PRODUTOR)
    app.dependency_overrides[get_db] = sobrescrever_db

    pontos = cliente.get("/api/forecasts/harvest?cropId=UVA_ARRA").json()["points"]
    assert pontos[0]["measuredTemperatureC"] == 29.4
    # Mês futuro (projetado) nunca traz valor medido
    assert all(p["measuredTemperatureC"] is None for p in pontos if p["projected"])
