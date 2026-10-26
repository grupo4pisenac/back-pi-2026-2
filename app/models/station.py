from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import synonym
from app.core.database import Base


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class Station(Base):
    __tablename__ = "stations"

    # Identificador do dispositivo ESP32 (ex.: ESP-PTR-01)
    id = Column(String, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    municipio = Column(String, nullable=False)  # PETROLINA | JUAZEIRO
    produto_id = Column(String, nullable=False)  # CropId (UVA_SUGRAONE, MANGA_PALMER, ...)
    canal_thingspeak = Column(String, nullable=False)
    # Coordenadas do pin no mapa SVG do front (0–100)
    posicao_x = Column(Float, nullable=False, default=50.0)
    posicao_y = Column(Float, nullable=False, default=50.0)
    bateria = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

    # Sinônimos para flexibilidade e compatibilidade
    name = synonym("nome")
    municipality = synonym("municipio")
    product_id = synonym("produto_id")
    thingspeak_channel_id = synonym("canal_thingspeak")
    battery = synonym("bateria")
    criado_em = synonym("created_at")


# Alias em português
Estacao = Station
