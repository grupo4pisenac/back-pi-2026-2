import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import Usuario


async def obter_usuario_por_email(db: AsyncSession, email: str) -> Usuario | None:
    resultado = await db.execute(select(Usuario).filter(Usuario.email == email))
    return resultado.scalars().first()


async def obter_usuario_por_id(db: AsyncSession, id_usuario: uuid.UUID) -> Usuario | None:
    resultado = await db.execute(select(Usuario).filter(Usuario.id == id_usuario))
    return resultado.scalars().first()


# Aliases para compatibilidade entre módulos
get_user_by_email = obter_usuario_por_email
get_user_by_id = obter_usuario_por_id