import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.token import LoginRequest, RefreshTokenRequest, RefreshTokenResponse, TokenResponse
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import get_user_by_email, get_user_by_id

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo")

    access_token = create_access_token(subject=user.id, role=user.role.value)
    refresh_token = create_refresh_token(subject=user.id, role=user.role.value)
    
    return TokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        user=UserRead.model_validate(user)
    )

@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de atualização inválido ou expirado",
    )
    try:
        payload = jwt.decode(request.refreshToken, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_id(db, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise credentials_exception

    access_token = create_access_token(subject=user.id, role=user.role.value)
    refresh_token = create_refresh_token(subject=user.id, role=user.role.value)

    return RefreshTokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token
    )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: RefreshTokenRequest, current_user: User = Depends(get_current_active_user)):
    # Apenas confirmamos a rota e o formato da requisição para seguir o contrato.
    return None

@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")

    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user