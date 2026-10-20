import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import obter_usuario_ativo_atual
from app.core.database import get_db
from app.models.station import Station
from app.models.user import PerfilUsuario, Usuario


@pytest.fixture
def cliente():
    return TestClient(app)


def test_estacoes_e_usuarios_sem_autenticacao(cliente):
    # Sem autenticação deve retornar 401
    assert cliente.get("/api/stations").status_code == 401
    assert cliente.get("/api/stations/health").status_code == 401
    assert cliente.post("/api/stations", json={"name": "E1", "location": "Talhão A"}).status_code == 401
    assert cliente.get("/api/users").status_code == 401
    assert cliente.get("/api/users/stats").status_code == 401
    assert cliente.post("/api/users", json={"email": "u@agro.com", "password": "password123"}).status_code == 401


def test_rbac_estacoes(cliente):
    usuario_produtor = Usuario(id=uuid.uuid4(), email="p@agro.com", ativo=True, perfil=PerfilUsuario.PRODUTOR)
    usuario_analista = Usuario(id=uuid.uuid4(), email="a@agro.com", ativo=True, perfil=PerfilUsuario.ANALISTA)
    usuario_admin = Usuario(id=uuid.uuid4(), email="adm@agro.com", ativo=True, perfil=PerfilUsuario.ADMIN)

    sessao_mock = AsyncMock()
    resultado_mock = MagicMock()
    resultado_mock.scalars.return_value.all.return_value = []
    sessao_mock.execute.return_value = resultado_mock

    async def mock_refresh(instance):
        if hasattr(instance, "id") and instance.id is None:
            instance.id = 1
        if hasattr(instance, "created_at") and instance.created_at is None:
            instance.created_at = datetime.now(timezone.utc)

    sessao_mock.refresh.side_effect = mock_refresh

    async def sobrescrever_db():
        yield sessao_mock

    app.dependency_overrides[get_db] = sobrescrever_db

    # Produtor não pode ler nem alterar estações (403)
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: usuario_produtor
    assert cliente.get("/api/stations").status_code == 403
    assert cliente.get("/api/stations/health").status_code == 403
    assert cliente.post("/api/stations", json={"name": "E1", "location": "Talhão A"}).status_code == 403

    # Analista pode ler estações e saúde da rede (200), mas não pode criar (403)
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: usuario_analista
    assert cliente.get("/api/stations").status_code == 200
    assert cliente.get("/api/stations/health").status_code == 200
    assert cliente.post("/api/stations", json={"name": "E1", "location": "Talhão A"}).status_code == 403

    # Admin pode criar estações (201)
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: usuario_admin
    res_post = cliente.post("/api/stations", json={"name": "Estação 01", "location": "Talhão A1", "status_ativo": True})
    assert res_post.status_code == 201
    dados_estacao = res_post.json()
    assert dados_estacao["id"] == 1
    assert dados_estacao.get("name") == "Estação 01" or dados_estacao.get("nome") == "Estação 01"

    app.dependency_overrides.clear()


def test_crud_usuarios_rbac_e_duplicidade(cliente):
    usuario_analista = Usuario(id=uuid.uuid4(), email="a@agro.com", ativo=True, perfil=PerfilUsuario.ANALISTA)
    usuario_admin = Usuario(id=uuid.uuid4(), email="adm@agro.com", ativo=True, perfil=PerfilUsuario.ADMIN)

    # Analista não tem permissão para gerenciar usuários (403)
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: usuario_analista
    assert cliente.get("/api/users").status_code == 403
    assert cliente.get("/api/users/stats").status_code == 403
    assert cliente.post("/api/users", json={"email": "novo@agro.com", "password": "password123"}).status_code == 403

    # Admin tem permissão total
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: usuario_admin

    # Mock de banco com usuário existente para testar 409 de email duplicado
    usuario_existente = Usuario(id=uuid.uuid4(), email="duplicado@agro.com", senha_hash="hash", ativo=True, perfil=PerfilUsuario.PRODUTOR)

    sessao_mock = AsyncMock()
    resultado_busca = MagicMock()
    resultado_busca.scalars.return_value.first.return_value = usuario_existente
    resultado_busca.scalars.return_value.all.return_value = [usuario_existente, usuario_admin]
    sessao_mock.execute.return_value = resultado_busca

    async def sobrescrever_db():
        yield sessao_mock

    app.dependency_overrides[get_db] = sobrescrever_db

    # POST com email duplicado deve retornar 409
    res_dup = cliente.post("/api/users", json={"email": "duplicado@agro.com", "password": "password123"})
    assert res_dup.status_code == 409
    assert res_dup.json()["detail"] == "Email já cadastrado"

    # GET /users e GET /users/stats retornam 200 com admin
    res_list = cliente.get("/api/users")
    assert res_list.status_code == 200

    res_stats = cliente.get("/api/users/stats")
    assert res_stats.status_code == 200
    assert "total_users" in res_stats.json() or "totalUsers" in res_stats.json()

    app.dependency_overrides.clear()
