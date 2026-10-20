from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import synonym
from app.core.database import Base


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String, nullable=False)
    localizacao = Column(String, nullable=False)
    status_ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

    # Sinônimos para flexibilidade e compatibilidade
    name = synonym("nome")
    location = synonym("localizacao")
    is_active = synonym("status_ativo")
    criado_em = synonym("created_at")


# Alias em português
Estacao = Station
