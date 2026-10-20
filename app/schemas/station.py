from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class StationInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome: str = Field(..., alias="name", description="Nome ou identificador da estação meteorológica/sensor")
    localizacao: str = Field(..., alias="location", description="Localização física ou talhão de instalação")
    status_ativo: bool = Field(default=True, alias="is_active", description="Indica se a estação está ativa")

    @property
    def name(self) -> str:
        return self.nome

    @property
    def location(self) -> str:
        return self.localizacao

    @property
    def is_active(self) -> bool:
        return self.status_ativo


class Station(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    nome: str = Field(..., alias="name")
    localizacao: str = Field(..., alias="location")
    status_ativo: bool = Field(..., alias="is_active")
    created_at: datetime

    @property
    def name(self) -> str:
        return self.nome

    @property
    def location(self) -> str:
        return self.localizacao

    @property
    def is_active(self) -> bool:
        return self.status_ativo


class NetworkHealth(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="HEALTHY", description="Status da conectividade da rede de sensores")
    total_stations: int = Field(default=0, alias="totalStations", description="Total de estações cadastradas")
    active_stations: int = Field(default=0, alias="activeStations", description="Estações transmitindo ativamente")
    inactive_stations: int = Field(default=0, alias="inactiveStations", description="Estações inativas ou sem sinal")
    average_latency_ms: float = Field(default=45.2, alias="averageLatencyMs", description="Latência média dos pacotes (ms)")
    packet_loss_rate: float = Field(default=0.008, alias="packetLossRate", description="Taxa de perda de pacotes")
    last_sync: datetime = Field(default_factory=_agora_utc, alias="lastSync", description="Data/hora da última verificação")


# Aliases em português
EstacaoInput = StationInput
Estacao = Station
SaudeRede = NetworkHealth
