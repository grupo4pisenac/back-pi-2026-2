import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field
from app.models.user import PerfilUsuario

StatusUsuario = Literal["ATIVO", "INATIVO"]


class UsuarioBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr


class UsuarioCriar(UsuarioBase):
    nome: str = Field(default="", alias="name")
    senha: str = Field(..., min_length=8, max_length=72, alias="password")
    perfil: PerfilUsuario = Field(default=PerfilUsuario.PRODUTOR, alias="role")

    @property
    def password(self) -> str:
        return self.senha

    @property
    def role(self) -> PerfilUsuario:
        return self.perfil


class UsuarioInput(UsuarioBase):
    """Schema para criação e atualização de usuários (contrato UserInput do front-end)."""
    model_config = ConfigDict(populate_by_name=True)

    nome: str = Field(..., min_length=1, alias="name")
    senha: Optional[str] = Field(None, min_length=8, max_length=72, alias="password")
    perfil: PerfilUsuario = Field(default=PerfilUsuario.PRODUTOR, alias="role")
    status: StatusUsuario = Field(default="ATIVO")

    @property
    def ativo(self) -> bool:
        return self.status == "ATIVO"

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
    """Contrato User do front-end."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    nome: str = Field(..., alias="name")
    perfil: PerfilUsuario = Field(..., alias="role")
    ativo: bool = Field(..., exclude=True)
    ultimo_acesso_em: Optional[datetime] = Field(None, alias="lastAccessAt")
    criado_em: datetime = Field(..., alias="createdAt")

    @computed_field
    @property
    def status(self) -> StatusUsuario:
        return "ATIVO" if self.ativo else "INATIVO"

    @property
    def is_active(self) -> bool:
        return self.ativo

    @property
    def role(self) -> PerfilUsuario:
        return self.perfil


class UsuarioEstatisticas(BaseModel):
    """Estatísticas de usuários cadastrados no sistema (contrato UsersStats do front-end)."""
    model_config = ConfigDict(populate_by_name=True)

    total: int = Field(..., description="Total de usuários cadastrados")
    adicionados_mes: int = Field(..., alias="addedThisMonth", description="Usuários criados no mês corrente")
    ativos: int = Field(..., alias="active", description="Total de usuários ativos")
    administradores: int = Field(..., alias="admins", description="Total de administradores")


# Aliases para compatibilidade entre módulos e nomenclatura solicitada
UserBase = UsuarioBase
UserCreate = UsuarioCriar
UserInput = UsuarioInput
UserRead = UsuarioLeitura
UserStats = UsuarioEstatisticas
