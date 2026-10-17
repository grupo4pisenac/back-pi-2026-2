import enum
import uuid
from sqlalchemy import Boolean, Column, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import synonym
from app.core.database import Base


class PerfilUsuario(str, enum.Enum):
    PRODUTOR = "PRODUTOR"
    ANALISTA = "ANALISTA"
    ADMIN = "ADMIN"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    perfil = Column(
        Enum(PerfilUsuario, name="perfil_usuario"),
        default=PerfilUsuario.PRODUTOR,
        nullable=False,
    )

    # Sinônimos para compatibilidade com contratos de API e schemas existentes
    hashed_password = synonym("senha_hash")
    is_active = synonym("ativo")
    role = synonym("perfil")


# Aliases para compatibilidade entre módulos
UserRole = PerfilUsuario
User = Usuario