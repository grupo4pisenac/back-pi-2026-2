import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import VerificadorPerfil, obter_usuario_ativo_atual
from app.core.config import settings
from app.core.database import get_db
from app.core.security import criar_token_acesso, criar_token_atualizacao, gerar_hash_senha, verificar_senha
from app.models.user import PerfilUsuario, Usuario
from app.schemas.token import (
    RequisicaoLogin,
    RequisicaoRefreshToken,
    RespostaRefreshToken,
    RespostaToken,
)
from app.schemas.user import UsuarioCriar, UsuarioLeitura
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