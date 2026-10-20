import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import RoleChecker
from app.core.database import get_db
from app.core.security import gerar_hash_senha
from app.models.user import PerfilUsuario, Usuario
from app.schemas.user import UserInput, UserRead, UserStats
from app.services.user_service import obter_usuario_por_email, obter_usuario_por_id

router = APIRouter(prefix="/users", tags=["users"])

# Todas as rotas de gerenciamento de usuários exigem perfil ADMIN
permissao_admin = RoleChecker([PerfilUsuario.ADMIN])


@router.get(
    "",
    response_model=List[UserRead],
    dependencies=[Depends(permissao_admin)],
)
async def listar_usuarios(db: AsyncSession = Depends(get_db)):
    """Lista todos os usuários cadastrados no sistema (Apenas Administrador)."""
    resultado = await db.execute(select(Usuario).order_by(Usuario.email.asc()))
    return resultado.scalars().all()


@router.get(
    "/stats",
    response_model=UserStats,
    dependencies=[Depends(permissao_admin)],
)
async def obter_estatisticas_usuarios(db: AsyncSession = Depends(get_db)):
    """Retorna métricas consolidadas dos usuários: total, ativos, inativos e por perfil."""
    resultado = await db.execute(select(Usuario))
    usuarios = resultado.scalars().all()

    total = len(usuarios)
    ativos = sum(1 for u in usuarios if u.ativo)
    inativos = total - ativos

    distribuicao_perfil: dict[str, int] = {}
    for u in usuarios:
        chave_perfil = u.perfil.value if hasattr(u.perfil, "value") else str(u.perfil)
        distribuicao_perfil[chave_perfil] = distribuicao_perfil.get(chave_perfil, 0) + 1

    return UserStats(
        total_users=total,
        active_users=ativos,
        inactive_users=inativos,
        by_role=distribuicao_perfil,
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(permissao_admin)],
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
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.senha),
        ativo=dados.ativo,
        perfil=dados.perfil,
    )
    db.add(novo_usuario)
    await db.commit()
    await db.refresh(novo_usuario)
    return novo_usuario


@router.put(
    "/{id}",
    response_model=UserRead,
    dependencies=[Depends(permissao_admin)],
)
async def atualizar_usuario(id: uuid.UUID, dados: UserInput, db: AsyncSession = Depends(get_db)):
    """Atualiza dados de um usuário existente (email, perfil, status, senha opcional)."""
    usuario = await obter_usuario_por_id(db, id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
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

    usuario.perfil = dados.perfil
    usuario.ativo = dados.ativo

    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(permissao_admin)],
)
async def remover_usuario(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Remove um usuário cadastrado (Apenas Administrador)."""
    usuario = await obter_usuario_por_id(db, id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    await db.delete(usuario)
    await db.commit()
    return None
