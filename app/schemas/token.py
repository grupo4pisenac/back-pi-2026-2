import uuid
from pydantic import BaseModel
from app.schemas.user import UserRead

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refreshToken: str

class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    user: UserRead

class RefreshTokenResponse(BaseModel):
    accessToken: str
    refreshToken: str

class TokenPayload(BaseModel):
    sub: uuid.UUID | None = None
    role: str | None = None
    exp: int | None = None
    type: str | None = None