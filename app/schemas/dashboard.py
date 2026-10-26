from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.climate import ClimateReading, LeituraClimatica
from app.schemas.station import CulturaId


class ResumoPainel(BaseModel):
    """Contrato DashboardSummary do front-end."""
    model_config = ConfigDict(populate_by_name=True)

    producao_projetada_t: float = Field(..., alias="projectedProductionT", description="Produção projetada (t)")
    variacao_producao_pct: float = Field(..., alias="productionChangePct", description="Variação % vs. ciclo anterior")
    # Campos climáticos são null quando não há leitura (ou o sensor não mede a grandeza)
    temperatura_media_c: Optional[float] = Field(None, alias="avgTemperatureC", description="Temperatura média das últimas 24 h (°C)")
    delta_temperatura_c: Optional[float] = Field(None, alias="temperatureDeltaC", description="Diferença vs. média de 30 dias (°C)")
    umidade_ar_pct: Optional[float] = Field(None, alias="airHumidityPct", description="Umidade do ar média das últimas 24 h (%)")
    umidade_solo_pct: Optional[float] = Field(None, alias="soilMoisturePct", description="Umidade média do solo (%)")
    chuva_7d_mm: Optional[float] = Field(None, alias="rainfall7dMm", description="Chuva acumulada em 7 dias (mm)")
    ultima_leitura_em: Optional[datetime] = Field(None, alias="lastReadingAt", description="Data/hora da última leitura")


class PontoPrevisaoColheita(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    periodo: str = Field(..., alias="period", description="Rótulo curto do período (ex.: Jan)")
    producao_t: float = Field(..., alias="productionT", description="Produção (t)")
    temperatura_media_c: float = Field(..., alias="avgTemperatureC", description="Temperatura média climatológica (°C)")
    temperatura_medida_c: Optional[float] = Field(None, alias="measuredTemperatureC", description="Média medida pela estação no mês (°C); null sem leituras")
    projetado: bool = Field(..., alias="projected", description="true para pontos projetados (futuro)")


class PrevisaoColheita(BaseModel):
    """Contrato HarvestForecast do front-end."""
    model_config = ConfigDict(populate_by_name=True)

    id_cultura: CulturaId = Field(..., alias="cropId")
    pontos: List[PontoPrevisaoColheita] = Field(default_factory=list, alias="points")


class Talhao(BaseModel):
    """Contrato Plot do front-end."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    nome: str = Field(..., alias="name")
    codigo: str = Field(..., alias="code")
    id_cultura: CulturaId = Field(..., alias="cropId")
    area_ha: float = Field(..., alias="areaHa")
    dias_para_colheita: int = Field(..., alias="daysToHarvest")
    progresso: int = Field(..., alias="progress", description="0–100 — avanço do ciclo fenológico")


class AlertaTermico(BaseModel):
    """Contrato ThermalAlert do front-end."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    titulo: str = Field(..., alias="title")
    mensagem: str = Field(..., alias="message")
    severidade: Literal["atencao", "critico"] = Field(..., alias="severity")


# Aliases para compatibilidade entre módulos
DashboardSummary = ResumoPainel
HarvestForecastPoint = PontoPrevisaoColheita
HarvestForecast = PrevisaoColheita
Plot = Talhao
ThermalAlert = AlertaTermico

__all__ = [
    "LeituraClimatica",
    "ResumoPainel",
    "PontoPrevisaoColheita",
    "PrevisaoColheita",
    "Talhao",
    "AlertaTermico",
    "ClimateReading",
    "DashboardSummary",
    "HarvestForecastPoint",
    "HarvestForecast",
    "Plot",
    "ThermalAlert",
]
