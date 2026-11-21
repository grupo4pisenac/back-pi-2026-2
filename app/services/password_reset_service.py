import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import gerar_hash_senha
from app.models.password_reset import PasswordResetToken
from app.models.user import Usuario
from app.services.user_service import obter_usuario_por_email

RESET_CODE_EXPIRE_MINUTES = 15
MAX_RESET_CODE_ATTEMPTS = 5


def hash_reset_code(user_id: uuid.UUID, code: str) -> str:
    """Retorna o hash SHA-256 (hex) vinculado ao user_id + código. Nunca salvamos o código puro."""
    return hashlib.sha256(f"{user_id}:{code}".encode("utf-8")).hexdigest()


async def create_password_reset_code(db: AsyncSession, usuario: Usuario) -> str:
    """
    Invalida códigos anteriores ainda não utilizados do usuário e cria um novo código
    numérico de 6 dígitos (uso único, validade de 15 minutos) na mesma transação.
    """
    agora = datetime.now(timezone.utc)

    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == usuario.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=agora)
    )

    codigo = f"{secrets.randbelow(1_000_000):06d}"
    novo_registro = PasswordResetToken(
        user_id=usuario.id,
        token_hash=hash_reset_code(usuario.id, codigo),
        attempts=0,
        expires_at=agora + timedelta(minutes=RESET_CODE_EXPIRE_MINUTES),
        created_at=agora,
    )
    db.add(novo_registro)
    await db.commit()
    return codigo


async def _registrar_tentativa_invalida(
    db: AsyncSession,
    user_id: uuid.UUID,
    agora: datetime,
) -> None:
    """Incrementa tentativas do código ativo e o invalida ao atingir MAX_RESET_CODE_ATTEMPTS."""
    novas_tentativas = PasswordResetToken.attempts + 1
    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > agora,
        )
        .values(
            attempts=novas_tentativas,
            used_at=case(
                (novas_tentativas >= MAX_RESET_CODE_ATTEMPTS, agora),
                else_=PasswordResetToken.used_at,
            ),
        )
    )
    await db.commit()


async def verify_password_reset_code(db: AsyncSession, email: str, code: str) -> bool:
    """
    Valida se o código de 6 dígitos está ativo para o e-mail informado (sem consumi-lo).
    Tentativas inválidas contam contra o limite de MAX_RESET_CODE_ATTEMPTS.
    """
    usuario = await obter_usuario_por_email(db, email)
    if usuario is None or not usuario.ativo:
        return False

    agora = datetime.now(timezone.utc)
    code_hash = hash_reset_code(usuario.id, code)

    stmt = select(PasswordResetToken.id).where(
        PasswordResetToken.user_id == usuario.id,
        PasswordResetToken.token_hash == code_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > agora,
        PasswordResetToken.attempts < MAX_RESET_CODE_ATTEMPTS,
    )
    registro_id = (await db.execute(stmt)).scalar_one_or_none()
    if registro_id is None:
        await _registrar_tentativa_invalida(db, usuario.id, agora)
        return False

    return True


async def consume_code_and_reset_password(
    db: AsyncSession,
    email: str,
    code: str,
    new_password: str,
) -> bool:
    """
    Consome o código atomicamente (UPDATE ... WHERE ... RETURNING user_id) e atualiza
    a senha do usuário na mesma transação (único commit).

    Nota de arquitetura: a autenticação da API é JWT stateless (sem tabela de sessões
    ou refresh tokens), portanto JWTs emitidos antes do reset seguem válidos até expirar.
    """
    usuario = await obter_usuario_por_email(db, email)
    if usuario is None or not usuario.ativo:
        return False

    agora = datetime.now(timezone.utc)
    code_hash = hash_reset_code(usuario.id, code)

    stmt = (
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == usuario.id,
            PasswordResetToken.token_hash == code_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > agora,
            PasswordResetToken.attempts < MAX_RESET_CODE_ATTEMPTS,
        )
        .values(used_at=agora)
        .returning(PasswordResetToken.user_id)
    )
    resultado = await db.execute(stmt)
    user_id = resultado.scalar_one_or_none()

    if user_id is None:
        await _registrar_tentativa_invalida(db, usuario.id, agora)
        return False

    usuario.senha_hash = gerar_hash_senha(new_password)
    await db.commit()
    return True
