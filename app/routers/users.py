import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import exigir_permissao
from app.core.database import get_db
from app.core.security import gerar_hash_senha
from app.models.user import PerfilUsuario, Usuario
from app.schemas.user import UserInput, UserRead, UserStats
from app.services.user_service import obter_usuario_por_email, obter_usuario_por_id

router = APIRouter(prefix="/users", tags=["users"])

# Leitura: ADMIN e ANALISTA_DADOS · Escrita: apenas ADMIN
permissao_leitura = exigir_permissao("users:read")
permissao_escrita = exigir_permissao("users:write")


@router.get(
    "",
    response_model=List[UserRead],
    dependencies=[Depends(permissao_leitura)],
)
async def listar_usuarios(db: AsyncSession = Depends(get_db)):
    """Lista todos os usuários cadastrados no sistema."""
    resultado = await db.execute(select(Usuario).order_by(Usuario.nome.asc()))
    return resultado.scalars().all()


@router.get(
    "/stats",
    response_model=UserStats,
    dependencies=[Depends(permissao_leitura)],
)
async def obter_estatisticas_usuarios(db: AsyncSession = Depends(get_db)):
    """Retorna métricas consolidadas dos usuários: total, novos no mês, ativos e administradores."""
    resultado = await db.execute(select(Usuario))
    usuarios = resultado.scalars().all()

    agora = datetime.now(timezone.utc)
    adicionados_mes = sum(
        1
        for u in usuarios
        if u.criado_em and u.criado_em.year == agora.year and u.criado_em.month == agora.month
    )

    return UserStats(
        total=len(usuarios),
        adicionados_mes=adicionados_mes,
        ativos=sum(1 for u in usuarios if u.ativo),
        administradores=sum(1 for u in usuarios if u.perfil == PerfilUsuario.ADMIN),
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(permissao_escrita)],
)
async def criar_usuario(dados: UserInput, db: AsyncSession = Depends(get_db)):
    """Cadastra um novo usuário no sistema. Retorna 409 se o email já estiver registrado."""
    usuario_existente = await obter_usuario_por_email(db, dados.email)
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado",
        )

    if not dados.senha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha é obrigatória para cadastro de novo usuário",
        )

    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.senha),
        ativo=dados.ativo,
        perfil=dados.perfil,
        criado_em=datetime.now(timezone.utc),
    )
    db.add(novo_usuario)
    await db.commit()
    await db.refresh(novo_usuario)
    return novo_usuario


@router.put(
    "/{id}",
    response_model=UserRead,
)
async def atualizar_usuario(
    id: uuid.UUID,
    dados: UserInput,
    db: AsyncSession = Depends(get_db),
    usuario_atual: Usuario = Depends(permissao_escrita),
):
    """Atualiza dados de um usuário existente (nome, email, perfil, status, senha opcional)."""
    usuario = await obter_usuario_por_id(db, id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    # Evita que o administrador perca o próprio acesso
    if usuario.id == usuario_atual.id and (not dados.ativo or dados.perfil != PerfilUsuario.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode desativar nem alterar o perfil da própria conta",
        )

    # Se o email foi alterado, verifica se já pertence a outro usuário
    if dados.email != usuario.email:
        outro_com_mesmo_email = await obter_usuario_por_email(db, dados.email)
        if outro_com_mesmo_email and outro_com_mesmo_email.id != id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado para outro usuário",
            )
        usuario.email = dados.email

    if dados.senha:
        usuario.senha_hash = gerar_hash_senha(dados.senha)

    usuario.nome = dados.nome
    usuario.perfil = dados.perfil
    usuario.ativo = dados.ativo

    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remover_usuario(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario_atual: Usuario = Depends(permissao_escrita),
):
    """Remove um usuário cadastrado (Apenas Administrador)."""
    usuario = await obter_usuario_por_id(db, id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    if usuario.id == usuario_atual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode excluir a própria conta",
        )

    await db.delete(usuario)
    await db.commit()
    return None
