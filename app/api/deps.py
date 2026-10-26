import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import PerfilUsuario, Usuario
from app.schemas.token import PayloadToken
from app.services.user_service import obter_usuario_por_id

esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

_TODOS_PERFIS = [PerfilUsuario.PRODUTOR, PerfilUsuario.ANALISTA, PerfilUsuario.ADMIN]

# Mapeamento granular de permissões (escopos) para perfis de acesso (RBAC - RF08).
# Mantenha sincronizado com a matriz do front-end (barto-io/src/lib/rbac.ts).
MAPA_PERMISSOES_PERFIL: dict[str, list[PerfilUsuario]] = {
    "dashboard:read": _TODOS_PERFIS,
    "forecast:read": _TODOS_PERFIS,
    "climate:read": _TODOS_PERFIS,
    "irrigation:read": _TODOS_PERFIS,
    "reports:read": _TODOS_PERFIS,
    "sensors:read": _TODOS_PERFIS,
    "analytics:read": [PerfilUsuario.ANALISTA, PerfilUsuario.ADMIN],
    "users:read": [PerfilUsuario.ANALISTA, PerfilUsuario.ADMIN],
    "forecast:write": [PerfilUsuario.ANALISTA, PerfilUsuario.ADMIN],
    "sensors:write": [PerfilUsuario.ADMIN],
    "users:write": [PerfilUsuario.ADMIN],
    "users:manage": [PerfilUsuario.ADMIN],
}


async def obter_usuario_atual(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(esquema_oauth2),
) -> Usuario:
    excecao_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        id_usuario = payload.get("sub")
        tipo_token = payload.get("type")
        if id_usuario is None or tipo_token != "access":
            raise excecao_credenciais
        dados_token = PayloadToken(sub=uuid.UUID(id_usuario), perfil=payload.get("role"), tipo=tipo_token)
    except (JWTError, ValueError):
        raise excecao_credenciais

    usuario = await obter_usuario_por_id(db, dados_token.sub)
    if usuario is None:
        raise excecao_credenciais
    return usuario


async def obter_usuario_ativo_atual(usuario_atual: Usuario = Depends(obter_usuario_atual)) -> Usuario:
    if not usuario_atual.ativo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo")
    return usuario_atual


class VerificadorPerfil:
    def __init__(self, perfis_permitidos: list[PerfilUsuario]):
        self.perfis_permitidos = perfis_permitidos

    async def __call__(self, usuario_atual: Usuario = Depends(obter_usuario_ativo_atual)) -> Usuario:
        if usuario_atual.perfil not in self.perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão suficiente para esta operação",
            )
        return usuario_atual


def exigir_permissao(permissao: str) -> VerificadorPerfil:
    """Retorna uma instância de VerificadorPerfil mapeada a partir da permissão granular."""
    perfis_permitidos = MAPA_PERMISSOES_PERFIL.get(permissao, [PerfilUsuario.ADMIN])
    return VerificadorPerfil(perfis_permitidos)


# Aliases para compatibilidade entre módulos
oauth2_scheme = esquema_oauth2
PERMISSION_ROLES_MAP = MAPA_PERMISSOES_PERFIL
get_current_user = obter_usuario_atual
get_current_active_user = obter_usuario_ativo_atual
RoleChecker = VerificadorPerfil
require_permission = exigir_permissao