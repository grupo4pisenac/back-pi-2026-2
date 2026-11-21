import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.rate_limit import forgot_password_rate_limiter, reset_password_rate_limiter
from app.core.security import gerar_hash_senha
from app.main import app
from app.models.password_reset import PasswordResetToken
from app.models.user import PerfilUsuario, Usuario
from app.services.password_reset_service import (
    MAX_RESET_CODE_ATTEMPTS,
    consume_code_and_reset_password,
    create_password_reset_code,
    hash_reset_code,
)


@compiles(PG_UUID, "sqlite")
def _compile_pg_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def db_env(tmp_path, monkeypatch):
    """Cria um banco SQLite assíncrono isolado por teste com FK ativa e rate limit desligado."""
    db_file = tmp_path / "test_reset.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    sync_conn,
                    tables=[Usuario.__table__, PasswordResetToken.__table__],
                )
            )

    _run(_init())

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    forgot_password_rate_limiter.reset()
    reset_password_rate_limiter.reset()

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    yield engine, session_factory

    app.dependency_overrides.clear()
    forgot_password_rate_limiter.reset()
    reset_password_rate_limiter.reset()
    _run(engine.dispose())


def _criar_usuario(session_factory, email="produtor@barto.io", senha="SenhaAntiga123", ativo=True) -> Usuario:
    async def _insert():
        async with session_factory() as db:
            usuario = Usuario(
                id=uuid.uuid4(),
                nome="Produtor Teste",
                email=email,
                senha_hash=gerar_hash_senha(senha),
                ativo=ativo,
                perfil=PerfilUsuario.PRODUTOR,
                criado_em=datetime.now(timezone.utc),
            )
            db.add(usuario)
            await db.commit()
            await db.refresh(usuario)
            return usuario

    return _run(_insert())


def test_fluxo_feliz_codigo_6_digitos_verify_reset_e_login(db_env, monkeypatch):
    _, session_factory = db_env
    usuario = _criar_usuario(session_factory, email="feliz@barto.io", senha="SenhaAntiga123")

    enviados: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_email",
        lambda to_email, code: enviados.append((to_email, code)),
    )

    client = TestClient(app)

    # 1. Solicita recuperação (valida também /api/auth/...)
    res_forgot = client.post("/api/auth/forgot-password", json={"email": usuario.email})
    assert res_forgot.status_code == 200
    assert len(enviados) == 1
    destino, codigo = enviados[0]
    assert destino == usuario.email
    assert len(codigo) == 6 and codigo.isdigit()

    # Garante que no banco existe apenas o hash SHA-256, nunca o código puro
    async def _check_db():
        async with session_factory() as db:
            row = (await db.execute(select(PasswordResetToken))).scalar_one()
            assert row.token_hash == hash_reset_code(usuario.id, codigo)
            assert row.token_hash != codigo
            assert row.used_at is None
            assert row.attempts == 0

    _run(_check_db())

    # 2. Valida o código na rota intermediária (não consome o código)
    res_verify = client.post(
        "/auth/verify-reset-code",
        json={"email": usuario.email, "code": codigo},
    )
    assert res_verify.status_code == 200

    # 3. Redefine a senha com o mesmo código
    res_reset = client.post(
        "/auth/reset-password",
        json={"email": usuario.email, "code": codigo, "new_password": "NovaSenhaForte456"},
    )
    assert res_reset.status_code == 200

    # 4. Senha antiga não loga mais
    res_login_antigo = client.post(
        "/auth/login",
        json={"email": usuario.email, "password": "SenhaAntiga123"},
    )
    assert res_login_antigo.status_code == 401

    # 5. Nova senha loga com sucesso
    res_login_novo = client.post(
        "/auth/login",
        json={"email": usuario.email, "password": "NovaSenhaForte456"},
    )
    assert res_login_novo.status_code == 200
    assert "accessToken" in res_login_novo.json()


def test_email_inexistente_retorna_mesma_resposta_e_nao_envia_email(db_env, monkeypatch):
    _, session_factory = db_env
    _criar_usuario(session_factory, email="existe@barto.io")

    enviados: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_email",
        lambda to_email, code: enviados.append((to_email, code)),
    )

    client = TestClient(app)
    res_existe = client.post("/auth/forgot-password", json={"email": "existe@barto.io"})
    res_inexistente = client.post("/auth/forgot-password", json={"email": "naoexiste@barto.io"})

    assert res_existe.status_code == 200
    assert res_inexistente.status_code == 200
    assert res_existe.json() == res_inexistente.json()
    assert len(enviados) == 1
    assert enviados[0][0] == "existe@barto.io"


def test_codigo_invalido_retorna_400_e_bloqueia_apos_limite_de_tentativas(db_env):
    _, session_factory = db_env
    usuario = _criar_usuario(session_factory, email="bloqueio@barto.io")

    async def _gerar() -> str:
        async with session_factory() as db:
            return await create_password_reset_code(db, usuario)

    codigo_valido = _run(_gerar())
    codigo_errado = "000000" if codigo_valido != "000000" else "999999"

    client = TestClient(app)

    # Erra MAX_RESET_CODE_ATTEMPTS vezes
    for _ in range(MAX_RESET_CODE_ATTEMPTS):
        res = client.post(
            "/auth/verify-reset-code",
            json={"email": usuario.email, "code": codigo_errado},
        )
        assert res.status_code == 400
        assert res.json()["message"] == "Código inválido ou expirado"

    # Agora até o código que era válido foi invalidado pelo limite de tentativas
    res_pos_bloqueio = client.post(
        "/auth/reset-password",
        json={"email": usuario.email, "code": codigo_valido, "new_password": "NovaSenhaForte456"},
    )
    assert res_pos_bloqueio.status_code == 400


def test_codigo_expirado_retorna_400(db_env):
    _, session_factory = db_env
    usuario = _criar_usuario(session_factory, email="expirado@barto.io")

    async def _inserir_expirado() -> str:
        codigo = "123456"
        agora = datetime.now(timezone.utc)
        async with session_factory() as db:
            db.add(
                PasswordResetToken(
                    user_id=usuario.id,
                    token_hash=hash_reset_code(usuario.id, codigo),
                    attempts=0,
                    expires_at=agora - timedelta(minutes=1),
                    created_at=agora - timedelta(minutes=16),
                )
            )
            await db.commit()
        return codigo

    codigo_expirado = _run(_inserir_expirado())
    client = TestClient(app)
    res = client.post(
        "/auth/reset-password",
        json={"email": usuario.email, "code": codigo_expirado, "new_password": "NovaSenhaForte456"},
    )
    assert res.status_code == 400
    assert res.json()["message"] == "Código inválido ou expirado"


def test_codigo_reutilizado_retorna_400_e_novo_codigo_invalida_anterior(db_env):
    _, session_factory = db_env
    usuario = _criar_usuario(session_factory, email="reuso@barto.io")

    async def _gerar_dois() -> tuple[str, str]:
        async with session_factory() as db:
            c1 = await create_password_reset_code(db, usuario)
            c2 = await create_password_reset_code(db, usuario)
            return c1, c2

    codigo_antigo, codigo_novo = _run(_gerar_dois())
    client = TestClient(app)

    # Código antigo foi invalidado ao gerar o novo (se por acaso não colidiu)
    if codigo_antigo != codigo_novo:
        res_antigo = client.post(
            "/auth/reset-password",
            json={"email": usuario.email, "code": codigo_antigo, "new_password": "NovaSenhaForte456"},
        )
        assert res_antigo.status_code == 400

    # Primeiro uso do código novo: sucesso
    res_primeiro = client.post(
        "/auth/reset-password",
        json={"email": usuario.email, "code": codigo_novo, "new_password": "NovaSenhaForte456"},
    )
    assert res_primeiro.status_code == 200

    # Segundo uso do mesmo código: 400
    res_segundo = client.post(
        "/auth/reset-password",
        json={"email": usuario.email, "code": codigo_novo, "new_password": "OutraSenhaForte789"},
    )
    assert res_segundo.status_code == 400


def test_consumo_concorrente_do_mesmo_codigo_so_um_sucesso(db_env):
    _, session_factory = db_env
    usuario = _criar_usuario(session_factory, email="concorrencia@barto.io")

    async def _executar_corrida() -> list[bool]:
        async with session_factory() as db:
            codigo = await create_password_reset_code(db, usuario)

        async def _tentar(nova_senha: str) -> bool:
            async with session_factory() as sessao_isolada:
                return await consume_code_and_reset_password(
                    sessao_isolada, usuario.email, codigo, nova_senha
                )

        resultados = await asyncio.gather(
            _tentar("SenhaCorridaA123"),
            _tentar("SenhaCorridaB456"),
        )
        return list(resultados)

    resultados = _run(_executar_corrida())
    assert resultados.count(True) == 1
    assert resultados.count(False) == 1


def test_rate_limit_forgot_e_reset_password(db_env, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "FORGOT_PASSWORD_RATE_LIMIT_MAX_REQUESTS", 2)
    monkeypatch.setattr(settings, "FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS", 60)
    forgot_password_rate_limiter.reset()
    reset_password_rate_limiter.reset()

    client = TestClient(app)
    assert client.post("/auth/forgot-password", json={"email": "a@barto.io"}).status_code == 200
    assert client.post("/auth/forgot-password", json={"email": "b@barto.io"}).status_code == 200
    assert client.post("/auth/forgot-password", json={"email": "c@barto.io"}).status_code == 429

    assert client.post("/auth/verify-reset-code", json={"email": "a@barto.io", "code": "123456"}).status_code == 400
    assert client.post("/auth/verify-reset-code", json={"email": "a@barto.io", "code": "123456"}).status_code == 400
    assert client.post("/auth/verify-reset-code", json={"email": "a@barto.io", "code": "123456"}).status_code == 429
