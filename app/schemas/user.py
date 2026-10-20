import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.user import PerfilUsuario


class UsuarioBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr


class UsuarioCriar(UsuarioBase):
    senha: str = Field(..., min_length=8, max_length=72, alias="password")
    perfil: PerfilUsuario = Field(default=PerfilUsuario.PRODUTOR, alias="role")

    @property
    def password(self) -> str:
        return self.senha

    @property
    def role(self) -> PerfilUsuario:
        return self.perfil


class UsuarioInput(UsuarioBase):
    """Schema para criação e atualização de usuários."""
    model_config = ConfigDict(populate_by_name=True)

    senha: Optional[str] = Field(None, min_length=8, max_length=72, alias="password")
    perfil: PerfilUsuario = Field(default=PerfilUsuario.PRODUTOR, alias="role")
    ativo: bool = Field(default=True, alias="is_active")

    @property
    def password(self) -> Optional[str]:
        return self.senha

    @property
    def role(self) -> PerfilUsuario:
        return self.perfil

    @property
    def is_active(self) -> bool:
        return self.ativo


class UsuarioLeitura(UsuarioBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    ativo: bool = Field(..., alias="is_active")
    perfil: PerfilUsuario = Field(..., alias="role")

    @property
    def is_active(self) -> bool:
        return self.ativo

    @property
    def role(self) -> PerfilUsuario:
        return self.perfil


class UsuarioEstatisticas(BaseModel):
    """Estatísticas de usuários cadastrados no sistema."""
    model_config = ConfigDict(populate_by_name=True)

    total_users: int = Field(..., alias="totalUsers", description="Total de usuários cadastrados")
    active_users: int = Field(..., alias="activeUsers", description="Total de usuários ativos")
    inactive_users: int = Field(..., alias="inactiveUsers", description="Total de usuários inativos")
    by_role: Optional[dict[str, int]] = Field(default=None, alias="byRole", description="Distribuição por perfil")


# Aliases para compatibilidade entre módulos e nomenclatura solicitada
UserBase = UsuarioBase
UserCreate = UsuarioCriar
UserInput = UsuarioInput
UserRead = UsuarioLeitura
UserStats = UsuarioEstatisticas