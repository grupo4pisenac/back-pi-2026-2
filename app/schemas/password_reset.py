from pydantic import BaseModel, EmailStr, Field


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., pattern=r"^\d{6}$", description="Código numérico de 6 dígitos")


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., pattern=r"^\d{6}$", description="Código numérico de 6 dígitos")
    # Mesmas regras de força de senha do cadastro (app/schemas/user.py)
    new_password: str = Field(..., min_length=8, max_length=72)


class MessageResponse(BaseModel):
    message: str
