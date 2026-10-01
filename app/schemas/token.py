import uuid
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: uuid.UUID | None = None
    role: str | None = None
    exp: int | None = None