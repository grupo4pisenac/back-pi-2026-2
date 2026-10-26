import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import obter_usuario_ativo_atual
from app.core.database import get_db
from app.models.user import PerfilUsuario, Usuario

ESTACAO_VALIDA = {
    "id": "ESP-PTR-04",
    "name": "Fazenda Nova",
    "municipality": "PETROLINA",
    "productId": "UVA_SUGRAONE",
    "thingSpeakChannelId": "2481040",
}
USUARIO_VALIDO = {
    "name": "Novo Usuário",
    "email": "novo@agro.com",
    "role": "ANALISTA_DADOS",
    "status": "ATIVO",
    "password": "password123",
}


def _usuario(perfil: PerfilUsuario, email: str = "u@agro.com") -> Usuario:
    return Usuario(
        id=uuid.uuid4(),
        nome="Usuário Teste",
        email=email,
        senha_hash="hash",
        ativo=True,
        perfil=perfil,
        criado_em=datetime.now(timezone.utc),
    )


def _sessao_mock(primeiro=None, todos=None) -> AsyncMock:
    sessao = AsyncMock()
    sessao.add = MagicMock()
    resultado = MagicMock()
    resultado.scalars.return_value.first.return_value = primeiro
    resultado.scalars.return_value.all.return_value = todos or []
    sessao.execute.return_value = resultado
    return sessao


@pytest.fixture
def cliente():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_estacoes_e_usuarios_sem_autenticacao(cliente):
    # Sem autenticação deve retornar 401 com erro padronizado {"message": ...}
    resposta = cliente.get("/api/stations")
    assert resposta.status_code == 401
    assert "message" in resposta.json()
    assert cliente.get("/api/stations/health").status_code == 401
    assert cliente.post("/api/stations", json=ESTACAO_VALIDA).status_code == 401
    assert cliente.get("/api/users").status_code == 401
    assert cliente.get("/api/users/stats").status_code == 401
    assert cliente.post("/api/users", json=USUARIO_VALIDO).status_code == 401


def test_rbac_estacoes(cliente):
    sessao = _sessao_mock()

    async def mock_refresh(instancia):
        if getattr(instancia, "created_at", None) is None:
            instancia.created_at = datetime.now(timezone.utc)

    sessao.refresh.side_effect = mock_refresh

    async def sobrescrever_db():
        yield sessao

    app.dependency_overrides[get_db] = sobrescrever_db

    # Todos os perfis leem estações (sensors:read), mas só ADMIN escreve (sensors:write)
    for perfil in (PerfilUsuario.PRODUTOR, PerfilUsuario.ANALISTA):
        app.dependency_overrides[obter_usuario_ativo_atual] = lambda p=perfil: _usuario(p)
        assert cliente.get("/api/stations").status_code == 200
        saude = cliente.get("/api/stations/health")
        assert saude.status_code == 200
        assert set(saude.json()) == {"total", "online", "active", "attention", "inactive", "lastSyncAt"}
        assert cliente.post("/api/stations", json=ESTACAO_VALIDA).status_code == 403

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.ADMIN)
    res_post = cliente.post("/api/stations", json=ESTACAO_VALIDA)
    assert res_post.status_code == 201
    estacao = res_post.json()
    assert estacao["id"] == "ESP-PTR-04"
    assert estacao["name"] == "Fazenda Nova"
    assert estacao["status"] == "INATIVO"
    assert estacao["statusReason"] == "Aguardando 1ª leitura"
    assert 0 <= estacao["position"]["x"] <= 100 and 0 <= estacao["position"]["y"] <= 100

    # Validação de formato do ID → 422 com mensagem legível
    invalida = cliente.post("/api/stations", json={**ESTACAO_VALIDA, "id": "XYZ"})
    assert invalida.status_code == 422
    assert "message" in invalida.json()


def test_crud_usuarios_rbac_e_duplicidade(cliente):
    usuario_existente = _usuario(PerfilUsuario.PRODUTOR, email="duplicado@agro.com")
    usuario_admin = _usuario(PerfilUsuario.ADMIN, email="adm@agro.com")
    sessao = _sessao_mock(primeiro=usuario_existente, todos=[usuario_existente, usuario_admin])

    async def sobrescrever_db():
        yield sessao

    app.dependency_overrides[get_db] = sobrescrever_db

    # Analista lê usuários (users:read), mas não escreve (users:write)
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.ANALISTA)
    assert cliente.get("/api/users").status_code == 200
    assert cliente.get("/api/users/stats").status_code == 200
    assert cliente.post("/api/users", json=USUARIO_VALIDO).status_code == 403

    # Produtor não acessa usuários
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: _usuario(PerfilUsuario.PRODUTOR)
    assert cliente.get("/api/users").status_code == 403

    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: usuario_admin

    # POST com email duplicado deve retornar 409 com "message"
    res_dup = cliente.post("/api/users", json={**USUARIO_VALIDO, "email": "duplicado@agro.com"})
    assert res_dup.status_code == 409
    assert res_dup.json()["message"] == "Email já cadastrado"

    res_list = cliente.get("/api/users")
    assert res_list.status_code == 200
    usuario = res_list.json()[0]
    assert set(usuario) == {"id", "name", "email", "role", "status", "lastAccessAt", "createdAt"}
    assert usuario["role"] == "PRODUTOR_EXPORTADOR"
    assert usuario["status"] == "ATIVO"

    res_stats = cliente.get("/api/users/stats")
    assert res_stats.status_code == 200
    assert res_stats.json() == {"total": 2, "addedThisMonth": 2, "active": 2, "admins": 1}


def test_admin_nao_perde_o_proprio_acesso(cliente):
    usuario_admin = _usuario(PerfilUsuario.ADMIN, email="adm@agro.com")
    sessao = _sessao_mock(primeiro=usuario_admin)

    async def sobrescrever_db():
        yield sessao

    app.dependency_overrides[get_db] = sobrescrever_db
    app.dependency_overrides[obter_usuario_ativo_atual] = lambda: usuario_admin
    rota = f"/api/users/{usuario_admin.id}"
    dados = {"name": "Admin", "email": "adm@agro.com", "role": "ADMIN", "status": "ATIVO"}

    assert cliente.delete(rota).status_code == 400
    assert cliente.put(rota, json={**dados, "status": "INATIVO"}).status_code == 400
    assert cliente.put(rota, json={**dados, "role": "ANALISTA_DADOS"}).status_code == 400
    assert cliente.put(rota, json=dados).status_code == 200
