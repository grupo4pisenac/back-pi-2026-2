import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UsuarioLeitura


class RequisicaoLogin(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    senha: str = Field(..., alias="password")

    @property
    def password(self) -> str:
        return self.senha


class RequisicaoRefreshToken(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    token_atualizacao: str = Field(..., alias="refreshToken")

    @property
    def refreshToken(self) -> str:
        return self.token_atualizacao


class RespostaToken(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    token_acesso: str = Field(..., alias="accessToken")
    token_atualizacao: str = Field(..., alias="refreshToken")
    usuario: UsuarioLeitura = Field(..., alias="user")

    @property
    def accessToken(self) -> str:
        return self.token_acesso

    @property
    def refreshToken(self) -> str:
        return self.token_atualizacao

    @property
    def user(self) -> UsuarioLeitura:
        return self.usuario


class RespostaRefreshToken(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    token_acesso: str = Field(..., alias="accessToken")
    token_atualizacao: str = Field(..., alias="refreshToken")

    @property
    def accessToken(self) -> str:
        return self.token_acesso

    @property
    def refreshToken(self) -> str:
        return self.token_atualizacao


class PayloadToken(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sub: uuid.UUID | None = None
    perfil: str | None = Field(default=None, alias="role")
    exp: int | None = None
    tipo: str | None = Field(default=None, alias="type")

    @property
    def role(self) -> str | None:
        return self.perfil

    @property
    def type(self) -> str | None:
        return self.tipo


# Aliases para compatibilidade entre módulos
LoginRequest = RequisicaoLogin
RefreshTokenRequest = RequisicaoRefreshToken
TokenResponse = RespostaToken
RefreshTokenResponse = RespostaRefreshToken
TokenPayload = PayloadToken