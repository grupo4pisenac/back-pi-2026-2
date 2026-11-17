import pytest
from fastapi.testclient import TestClient

from app.main import app

VERCEL_DEPLOY = "https://front-pi-2026-2-frmjlecdz-vitorrsantoss.vercel.app"


@pytest.fixture
def cliente():
    return TestClient(app)


def _preflight(cliente: TestClient, origem: str):
    return cliente.options(
        "/api/auth/login",
        headers={
            "Origin": origem,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )


@pytest.mark.parametrize(
    "origem",
    [
        "http://localhost:5173",
        VERCEL_DEPLOY,
        # Deploys futuros da Vercel mudam o código do meio do endereço
        "https://front-pi-2026-2-abc123xyz-vitorrsantoss.vercel.app",
        "https://front-pi-2026-2-git-main-vitorrsantoss.vercel.app",
        "https://front-pi-2026-2.vercel.app",
    ],
)
def test_origens_do_front_liberadas(cliente, origem):
    resposta = _preflight(cliente, origem)
    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == origem


@pytest.mark.parametrize(
    "origem",
    [
        "https://evil.example.com",
        "https://front-pi-2026-2-abc123-outro-time.vercel.app",
        "https://front-pi-2026-2-vitorrsantoss.vercel.app.evil.com",
        "http://front-pi-2026-2-abc123-vitorrsantoss.vercel.app",
    ],
)
def test_origens_desconhecidas_bloqueadas(cliente, origem):
    resposta = _preflight(cliente, origem)
    assert resposta.status_code == 400
    assert "access-control-allow-origin" not in resposta.headers
