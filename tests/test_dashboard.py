import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import obter_usuario_ativo_atual
from app.core.database import get_db
from app.models.user import PerfilUsuario, Usuario
from app.models.climate import DadosClimaticos


@pytest.fixture
def cliente():
    return TestClient(app)


def test_rotas_publicas(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert resposta.json() == {"message": "API online."}


def test_autenticacao_e_painel_nao_autorizado(cliente):
    assert cliente.get("/auth/me").status_code == 401
    assert cliente.get("/api/dashboard/summary").status_code == 401
    assert cliente.get("/api/forecasts/harvest").status_code == 401
    assert cliente.get("/api/plots").status_code == 401
    assert cliente.get("/api/climate/readings").status_code == 401
    assert cliente.get("/api/alerts/active").status_code == 401


def test_endpoints_painel_com_usuario_mock(cliente):
    usuario_mock = Usuario(
        id=uuid.uuid4(),
        email="produtor@agro.com",
        ativo=True,
        perfil=PerfilUsuario.PRODUTOR,
    )
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: usuario_mock

    # 1. Resumo do Painel
    res_resumo = cliente.get("/api/dashboard/summary")
    assert res_resumo.status_code == 200
    dados_resumo = res_resumo.json()
    assert "averageTemperature" in dados_resumo
    assert "harvestWindowStatus" in dados_resumo
    assert "exportDemandIndex" not in dados_resumo
    assert dados_resumo["harvestWindowStatus"] == "IDEAL"

    # 2. Previsão de Colheita
    res_previsao = cliente.get("/api/forecasts/harvest?cropId=manga-palmer")
    assert res_previsao.status_code == 200
    dados_previsao = res_previsao.json()
    assert dados_previsao["cropId"] == "manga-palmer"
    assert "idealWindowStart" in dados_previsao
    assert "optimalLogisticsRoute" not in dados_previsao
    assert len(dados_previsao["dailyProjections"]) == 7

    # 3. Talhões (Plots)
    res_talhoes = cliente.get("/api/plots?status=ACTIVE")
    assert res_talhoes.status_code == 200
    dados_talhoes = res_talhoes.json()
    assert isinstance(dados_talhoes, list)
    assert len(dados_talhoes) == 4
    assert dados_talhoes[0]["status"] == "ACTIVE"

    # 4. Alertas Ativos
    res_alertas = cliente.get("/api/alerts/active")
    assert res_alertas.status_code == 200
    dados_alerta = res_alertas.json()
    assert dados_alerta["active"] is True
    assert dados_alerta["type"] == "IDEAL_HARVEST_WINDOW"

    app.dependency_overrides.clear()


def test_consulta_leituras_climaticas(cliente):
    usuario_mock = Usuario(
        id=uuid.uuid4(),
        email="analista@agro.com",
        ativo=True,
        perfil=PerfilUsuario.ANALISTA,
    )
    leitura_mock = DadosClimaticos(
        id=1,
        id_entrada=999,
        temperatura=28.5,
        umidade=60.0,
        registrado_em=datetime.now(timezone.utc),
        criado_em=datetime.now(timezone.utc),
    )

    sessao_mock = AsyncMock()
    resultado_mock = MagicMock()
    resultado_mock.scalars.return_value.all.return_value = [leitura_mock]
    sessao_mock.execute.return_value = resultado_mock

    async def sobrescrever_db():
        yield sessao_mock

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: usuario_mock
    app.dependency_overrides[get_db] = sobrescrever_db

    res_clima = cliente.get("/api/climate/readings?range=today")
    assert res_clima.status_code == 200
    leituras = res_clima.json()
    assert len(leituras) == 1
    assert leituras[0]["temperature"] == 28.5
    assert leituras[0]["entry_id"] == 999

    app.dependency_overrides.clear()
