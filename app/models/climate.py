from datetime import datetime, timezone
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint)
from sqlalchemy.orm import synonym
from app.core.database import Base


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class DadosClimaticos(Base):
    __tablename__ = "dados_climaticos"
    __table_args__ = (
    UniqueConstraint("station_id", "id_entrada", name="uq_dados_climaticos_station_entry"),)

    id = Column(Integer, primary_key=True, index=True)
    id_entrada = Column(Integer, index=True)
    temperatura = Column(Float, nullable=False)
    umidade = Column(Float, nullable=False)  # Umidade do ar (field2)
    umidade_solo = Column(Float, nullable=True)  # Opcional (field3)
    chuva = Column(Float, nullable=True)  # Opcional, mm (field4)
    registrado_em = Column(DateTime(timezone=True), nullable=False)  # Registro Sensor/ThingSpeak
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)  # Registro da API
    station_id = Column(String, ForeignKey("stations.id"), nullable=False, index=True)

    # Sinônimos para compatibilidade com contratos de API e queries legadas
    entry_id = synonym("id_entrada")
    temperature = synonym("temperatura")
    humidity = synonym("umidade")
    soil_moisture = synonym("umidade_solo")
    rainfall = synonym("chuva")
    recorded_at = synonym("registrado_em")
    created_at = synonym("criado_em")


# Alias para compatibilidade entre módulos
ClimateData = DadosClimaticos