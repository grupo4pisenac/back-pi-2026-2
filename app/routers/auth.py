import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import VerificadorPerfil, obter_usuario_ativo_atual
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import forgot_password_rate_limiter, reset_password_rate_limiter
from app.core.security import criar_token_acesso, criar_token_atualizacao, gerar_hash_senha, verificar_senha
from app.models.user import PerfilUsuario, Usuario
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    VerifyResetCodeRequest,
)
from app.schemas.token import (
    RequisicaoLogin,
    RequisicaoRefreshToken,
    RespostaRefreshToken,
    RespostaToken,
)
from app.schemas.user import UsuarioCriar, UsuarioLeitura
from app.services.email_service import send_password_reset_email
from app.services.password_reset_service import (
    consume_code_and_reset_password,
    create_password_reset_code,
    verify_password_reset_code,
)
from app.services.user_service import obter_usuario_por_email, obter_usuario_por_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=RespostaToken)
async def autenticar_usuario(requisicao: RequisicaoLogin, db: AsyncSession = Depends(get_db)):
    usuario = await obter_usuario_por_email(db, requisicao.email)
    if not usuario or not verificar_senha(requisicao.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )
    if not usuario.ativo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo")

    usuario.ultimo_acesso_em = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(usuario)

    token_acesso = criar_token_acesso(assunto=usuario.id, perfil=usuario.perfil.value)
    token_atualizacao = criar_token_atualizacao(assunto=usuario.id, perfil=usuario.perfil.value)

    return RespostaToken(
        token_acesso=token_acesso,
        token_atualizacao=token_atualizacao,
        usuario=UsuarioLeitura.model_validate(usuario),
    )


@router.post("/refresh", response_model=RespostaRefreshToken)
async def atualizar_token(requisicao: RequisicaoRefreshToken, db: AsyncSession = Depends(get_db)):
    excecao_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de atualização inválido ou expirado",
    )
    try:
        payload = jwt.decode(
            requisicao.token_atualizacao,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        id_usuario = payload.get("sub")
        tipo_token = payload.get("type")
        if id_usuario is None or tipo_token != "refresh":
            raise excecao_credenciais
    except JWTError:
        raise excecao_credenciais

    usuario = await obter_usuario_por_id(db, uuid.UUID(id_usuario))
    if not usuario or not usuario.ativo:
        raise excecao_credenciais

    token_acesso = criar_token_acesso(assunto=usuario.id, perfil=usuario.perfil.value)
    token_atualizacao = criar_token_atualizacao(assunto=usuario.id, perfil=usuario.perfil.value)

    return RespostaRefreshToken(
        token_acesso=token_acesso,
        token_atualizacao=token_atualizacao,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def encerrar_sessao(
    requisicao: RequisicaoRefreshToken,
    usuario_atual: Usuario = Depends(obter_usuario_ativo_atual),
):
    return None


@router.get("/me", response_model=UsuarioLeitura)
async def obter_perfil_logado(usuario_atual: Usuario = Depends(obter_usuario_ativo_atual)):
    return usuario_atual


@router.post(
    "/register",
    response_model=UsuarioLeitura,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(VerificadorPerfil([PerfilUsuario.ADMIN]))],
)
async def cadastrar_usuario(dados_usuario: UsuarioCriar, db: AsyncSession = Depends(get_db)):
    usuario_existente = await obter_usuario_por_email(db, dados_usuario.email)
    if usuario_existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")

    novo_usuario = Usuario(
        nome=dados_usuario.nome,
        email=dados_usuario.email,
        senha_hash=gerar_hash_senha(dados_usuario.senha),
        perfil=dados_usuario.perfil,
    )
    db.add(novo_usuario)
    await db.commit()
    await db.refresh(novo_usuario)
    return novo_usuario


FORGOT_PASSWORD_GENERIC_MESSAGE = (
    "Se o e-mail estiver cadastrado, enviaremos instruções para redefinir sua senha."
)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(forgot_password_rate_limiter)],
)
async def solicitar_redefinicao_senha(
    requisicao: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Solicita redefinição de senha por código de 6 dígitos. Sempre retorna 200 genérico."""
    usuario = await obter_usuario_por_email(db, requisicao.email)
    if usuario and usuario.ativo:
        codigo = await create_password_reset_code(db, usuario)
        background_tasks.add_task(send_password_reset_email, usuario.email, codigo)
    return MessageResponse(message=FORGOT_PASSWORD_GENERIC_MESSAGE)


@router.post(
    "/verify-reset-code",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(reset_password_rate_limiter)],
)
async def verificar_codigo_redefinicao(
    requisicao: VerifyResetCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Valida se o código de 6 dígitos é válido para o e-mail (sem consumi-lo)."""
    valido = await verify_password_reset_code(
        db=db,
        email=requisicao.email,
        code=requisicao.code,
    )
    if not valido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado",
        )
    return MessageResponse(message="Código validado com sucesso.")


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(reset_password_rate_limiter)],
)
async def redefinir_senha(
    requisicao: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Consome atomicamente o código de 6 dígitos e atualiza a senha do usuário."""
    sucesso = await consume_code_and_reset_password(
        db=db,
        email=requisicao.email,
        code=requisicao.code,
        new_password=requisicao.new_password,
    )
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado",
        )
    return MessageResponse(message="Senha redefinida com sucesso.")