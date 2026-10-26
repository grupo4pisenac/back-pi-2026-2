from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

Municipio = Literal["PETROLINA", "JUAZEIRO"]
StatusEstacao = Literal["ATIVO", "ATENCAO", "INATIVO"]
CulturaId = Literal["UVA_SUGRAONE", "MANGA_PALMER", "UVA_ARRA", "GOIABA_PALUMA"]


class StationInput(BaseModel):
    """Contrato StationInput do front-end."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., pattern=r"^ESP-[A-Z]{3}-\d{2}$", description="Identificador do dispositivo (ex.: ESP-PTR-04)")
    nome: str = Field(..., min_length=3, alias="name", description="Nome da estação meteorológica")
    municipio: Municipio = Field(..., alias="municipality")
    produto_id: CulturaId = Field(..., alias="productId", description="Cultura associada à estação")
    canal_thingspeak: str = Field(..., pattern=r"^\d{5,8}$", alias="thingSpeakChannelId")


class PosicaoMapa(BaseModel):
    """Coordenadas do pin no mapa SVG do front (0–100)."""
    x: float
    y: float


class LeituraEstacao(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    temperatura: float = Field(..., alias="temperature")
    umidade_solo: Optional[float] = Field(None, alias="soilMoisture")
    umidade_ar: float = Field(..., alias="airHumidity")


class Station(BaseModel):
    """Contrato Station do front-end."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    nome: str = Field(..., alias="name")
    municipio: Municipio = Field(..., alias="municipality")
    posicao: PosicaoMapa = Field(..., alias="position")
    status: StatusEstacao
    motivo_status: Optional[str] = Field(None, alias="statusReason")
    bateria: int = Field(..., alias="battery")
    ultima_leitura_em: Optional[datetime] = Field(None, alias="lastReadingAt")
    ultima_leitura: Optional[LeituraEstacao] = Field(None, alias="lastReading")
    produto_id: CulturaId = Field(..., alias="productId")
    canal_thingspeak: str = Field(..., alias="thingSpeakChannelId")


class NetworkHealth(BaseModel):
    """Contrato NetworkHealth do front-end (online = active + attention)."""
    model_config = ConfigDict(populate_by_name=True)

    total: int
    online: int
    ativas: int = Field(..., alias="active")
    atencao: int = Field(..., alias="attention")
    inativas: int = Field(..., alias="inactive")
    ultima_sincronizacao: datetime = Field(..., alias="lastSyncAt")


# Aliases em português
EstacaoInput = StationInput
Estacao = Station
SaudeRede = NetworkHealth
