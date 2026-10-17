from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer
from sqlalchemy.orm import synonym
from app.core.database import Base


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class DadosClimaticos(Base):
    __tablename__ = "dados_climaticos"

    id = Column(Integer, primary_key=True, index=True)
    id_entrada = Column(Integer, unique=True, index=True)
    temperatura = Column(Float, nullable=False)
    umidade = Column(Float, nullable=False)
    registrado_em = Column(DateTime(timezone=True), nullable=False)  # Registro Sensor/ThingSpeak
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)  # Registro da API

    # Sinônimos para compatibilidade com contratos de API e queries legadas
    entry_id = synonym("id_entrada")
    temperature = synonym("temperatura")
    humidity = synonym("umidade")
    recorded_at = synonym("registrado_em")
    created_at = synonym("criado_em")


# Alias para compatibilidade entre módulos
ClimateData = DadosClimaticos