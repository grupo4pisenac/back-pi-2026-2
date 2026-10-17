import uuid
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


# Aliases para compatibilidade entre módulos
UserBase = UsuarioBase
UserCreate = UsuarioCriar
UserRead = UsuarioLeitura