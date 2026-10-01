import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.user import UserRole

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=72)
    role: UserRole = UserRole.PRODUTOR

class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    role: UserRole