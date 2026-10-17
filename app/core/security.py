from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

contexto_senha = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verificar_senha(senha_texto: str, senha_hash: str) -> bool:
    return contexto_senha.verify(senha_texto, senha_hash)


def gerar_hash_senha(senha: str) -> str:
    return contexto_senha.hash(senha)


def criar_token_acesso(assunto: str, perfil: str, delta_expiracao: timedelta | None = None) -> str:
    expira_em = datetime.now(timezone.utc) + (
        delta_expiracao or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    dados_codificar = {"sub": str(assunto), "role": perfil, "exp": expira_em, "type": "access"}
    return jwt.encode(dados_codificar, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def criar_token_atualizacao(assunto: str, perfil: str, delta_expiracao: timedelta | None = None) -> str:
    expira_em = datetime.now(timezone.utc) + (
        delta_expiracao or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    dados_codificar = {"sub": str(assunto), "role": perfil, "exp": expira_em, "type": "refresh"}
    return jwt.encode(dados_codificar, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# Aliases para compatibilidade entre módulos
pwd_context = contexto_senha
verify_password = verificar_senha
get_password_hash = gerar_hash_senha
create_access_token = criar_token_acesso
create_refresh_token = criar_token_atualizacao