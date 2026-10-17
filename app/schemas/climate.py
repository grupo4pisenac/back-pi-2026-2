from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DadosClimaticosBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    temperatura: float = Field(..., alias="temperature")
    umidade: float = Field(..., alias="humidity")
    registrado_em: datetime = Field(..., alias="recorded_at")
    id_entrada: int = Field(..., alias="entry_id")

    @property
    def temperature(self) -> float:
        return self.temperatura

    @property
    def humidity(self) -> float:
        return self.umidade

    @property
    def recorded_at(self) -> datetime:
        return self.registrado_em

    @property
    def entry_id(self) -> int:
        return self.id_entrada


class DadosClimaticosCriar(DadosClimaticosBase):
    pass


class DadosClimaticosResposta(DadosClimaticosBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    criado_em: datetime = Field(..., alias="created_at")

    @property
    def created_at(self) -> datetime:
        return self.criado_em


class LeituraClimatica(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    id_entrada: int = Field(..., alias="entry_id")
    temperatura: float = Field(..., alias="temperature")
    umidade: float = Field(..., alias="humidity")
    registrado_em: datetime = Field(..., alias="recorded_at")
    criado_em: Optional[datetime] = Field(default=None, alias="created_at")

    @property
    def entry_id(self) -> int:
        return self.id_entrada

    @property
    def temperature(self) -> float:
        return self.temperatura

    @property
    def humidity(self) -> float:
        return self.umidade

    @property
    def recorded_at(self) -> datetime:
        return self.registrado_em

    @property
    def created_at(self) -> Optional[datetime]:
        return self.criado_em


# Aliases para compatibilidade entre módulos
ClimateDataBase = DadosClimaticosBase
ClimateDataCreate = DadosClimaticosCriar
ClimateDataResponse = DadosClimaticosResposta
ClimateReading = LeituraClimatica