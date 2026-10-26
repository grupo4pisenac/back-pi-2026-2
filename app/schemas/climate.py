from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DadosClimaticosBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    temperatura: float = Field(..., alias="temperature")
    umidade: float = Field(..., alias="humidity")
    umidade_solo: float | None = Field(default=None, alias="soil_moisture")
    chuva: float | None = Field(default=None, alias="rainfall")
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
    """Contrato ClimateReading do front-end."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    id_estacao: str = Field(..., alias="stationId")
    registrado_em: datetime = Field(..., alias="timestamp")
    temperatura: float = Field(..., alias="temperature")
    # null quando o canal não publica o campo (field3/field4)
    umidade_solo: float | None = Field(None, alias="soilMoisture")
    umidade_ar: float = Field(..., alias="airHumidity")
    chuva: float | None = Field(None, alias="rainfall")


# Aliases para compatibilidade entre módulos
ClimateDataBase = DadosClimaticosBase
ClimateDataCreate = DadosClimaticosCriar
ClimateDataResponse = DadosClimaticosResposta
ClimateReading = LeituraClimatica

class EstatisticaSerie(BaseModel):
    """Mínimo, média e máximo de uma grandeza dentro do intervalo agregado."""
    minimo: float = Field(..., alias="min")
    media: float = Field(..., alias="avg")
    maximo: float = Field(..., alias="max")

    model_config = ConfigDict(populate_by_name=True)


class AgregadoClimatico(BaseModel):
    """Contrato ClimateAggregate do front-end (um dia ou uma hora, no fuso do Vale)."""
    model_config = ConfigDict(populate_by_name=True)

    inicio: datetime = Field(..., alias="start", description="Início do intervalo (ISO 8601, fuso -03:00)")
    leituras: int = Field(..., alias="readings")
    temperatura: EstatisticaSerie = Field(..., alias="temperature")
    umidade_ar: EstatisticaSerie = Field(..., alias="airHumidity")
    horas_estresse_termico: float = Field(..., alias="heatStressHours", description="Horas com temperatura ≥ 35 °C")


ClimateAggregate = AgregadoClimatico
