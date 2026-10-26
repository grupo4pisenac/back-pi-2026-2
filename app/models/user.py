import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import synonym
from app.core.database import Base


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class PerfilUsuario(str, enum.Enum):
    # O banco persiste o NOME do membro (PRODUTOR/ANALISTA/ADMIN);
    # o VALOR é o contrato exposto ao front-end (types/rbac.ts).
    PRODUTOR = "PRODUTOR_EXPORTADOR"
    ANALISTA = "ANALISTA_DADOS"
    ADMIN = "ADMIN"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nome = Column(String, nullable=False, default="")
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    perfil = Column(
        Enum(PerfilUsuario, name="perfil_usuario"),
        default=PerfilUsuario.PRODUTOR,
        nullable=False,
    )
    ultimo_acesso_em = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

    # Sinônimos para compatibilidade com contratos de API e schemas existentes
    name = synonym("nome")
    hashed_password = synonym("senha_hash")
    is_active = synonym("ativo")
    role = synonym("perfil")
    last_access_at = synonym("ultimo_acesso_em")
    created_at = synonym("criado_em")


# Aliases para compatibilidade entre módulos
UserRole = PerfilUsuario
User = Usuario
