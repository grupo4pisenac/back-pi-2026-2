from datetime import date, datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.climate import ClimateReading, LeituraClimatica


class ResumoPainel(BaseModel):
    """Schema de sumário executivo do painel de monitoramento climático e safra."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    temperatura_media: float = Field(..., alias="averageTemperature", description="Temperatura média atual (°C)")
    umidade_media: float = Field(..., alias="averageHumidity", description="Umidade relativa média atual (%)")
    umidade_solo: float = Field(..., alias="soilMoisture", description="Umidade média do solo (%)")
    total_talhoes_ativos: int = Field(..., alias="activePlotsCount", description="Quantidade de talhões ativos")
    total_talhoes: int = Field(..., alias="totalPlotsCount", description="Total de talhões cadastrados")
    total_alertas_ativos: int = Field(..., alias="activeAlertsCount", description="Quantidade de alertas ativos")
    status_janela_colheita: str = Field(..., alias="harvestWindowStatus", description="Status da janela de colheita (IDEAL, WARNING, CRITICAL)")
    producao_estimada_ton: float = Field(..., alias="estimatedYieldTons", description="Estimativa de volume de safra (toneladas)")
    ultima_atualizacao: datetime = Field(..., alias="lastUpdated", description="Data e hora da última atualização dos indicadores")


class PontoPrevisaoDiaria(BaseModel):
    """Projeção diária para o gráfico preditivo de safra e clima."""
    model_config = ConfigDict(populate_by_name=True)

    data: date = Field(..., alias="date")
    temperatura_prevista: float = Field(..., alias="predictedTemperature")
    umidade_prevista: float = Field(..., alias="predictedHumidity")
    indice_maturacao: float = Field(..., alias="maturationIndex")


class PrevisaoColheita(BaseModel):
    """Schema de previsão da janela ideal de colheita da safra (RF06)."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id_cultura: str = Field(..., alias="cropId", description="Identificador da cultura agrícola")
    nome_cultura: str = Field(..., alias="cropName", description="Nome comercial da fruta/cultura")
    inicio_janela_ideal: date = Field(..., alias="idealWindowStart", description="Data inicial da janela ideal de colheita")
    fim_janela_ideal: date = Field(..., alias="idealWindowEnd", description="Data final da janela ideal de colheita")
    indice_confianca: float = Field(..., alias="confidenceScore", description="Índice de confiança do modelo preditivo (0 a 1)")
    recomendacao: str = Field(..., alias="recommendation", description="Recomendação técnica para manejo e colheita")
    nivel_risco: str = Field(..., alias="riskLevel", description="Nível de risco climático (LOW, MEDIUM, HIGH)")
    temperatura_media_prevista: float = Field(..., alias="predictedTemperatureAvg", description="Temperatura média prevista no período (°C)")
    umidade_media_prevista: float = Field(..., alias="predictedHumidityAvg", description="Umidade relativa média prevista no período (%)")
    projecoes_diarias: List[PontoPrevisaoDiaria] = Field(default_factory=list, alias="dailyProjections", description="Série temporal preditiva")


class LocalizacaoTalhao(BaseModel):
    """Coordenadas GPS e localização do talhão."""
    model_config = ConfigDict(populate_by_name=True)

    latitude: float
    longitude: float
    municipio: str = Field(..., alias="municipality")


class Talhao(BaseModel):
    """Schema de lote/talhão monitorado na região de Petrolina/Juazeiro."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(..., description="Identificador único do talhão")
    nome: str = Field(..., alias="name", description="Nome/código do talhão")
    cultura: str = Field(..., alias="crop", description="Cultura cultivada")
    variedade: str = Field(..., alias="variety", description="Variedade da fruta cultivada")
    area_hectares: float = Field(..., alias="areaHectares", description="Área plantada em hectares")
    status: str = Field(..., description="Status operacional do talhão (ACTIVE, HARVESTING, RESTING, INACTIVE)")
    temperatura_atual: float = Field(..., alias="currentTemperature", description="Última temperatura registrada no talhão (°C)")
    umidade_atual: float = Field(..., alias="currentHumidity", description="Última umidade registrada no talhão (%)")
    umidade_solo: float = Field(..., alias="soilMoisture", description="Umidade do solo registrada (%)")
    estagio_maturacao: str = Field(..., alias="maturationStage", description="Estágio atual de maturação da safra")
    localizacao: LocalizacaoTalhao = Field(..., alias="location", description="Localização geográfica GPS do lote")
    data_estimada_colheita: date = Field(..., alias="estimatedHarvestDate", description="Data estimada para início da colheita")


class AlertaTermico(BaseModel):
    """Schema de alerta térmico e climático para tomada de decisão (RF09)."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(..., description="Identificador único do alerta")
    severidade: str = Field(..., alias="severity", description="Severidade (INFO, WARNING, CRITICAL)")
    tipo: str = Field(..., alias="type", description="Categoria do alerta (HEAT_WAVE, LOW_HUMIDITY, IDEAL_HARVEST_WINDOW)")
    titulo: str = Field(..., alias="title", description="Título resumido do alerta")
    mensagem: str = Field(..., alias="message", description="Descrição detalhada e orientação operacional")
    id_talhao: str = Field(..., alias="plotId", description="ID do talhão afetado")
    nome_talhao: str = Field(..., alias="plotName", description="Nome do talhão afetado")
    temperatura_registrada: float = Field(..., alias="recordedTemperature", description="Temperatura registrada no evento (°C)")
    temperatura_limite: float = Field(..., alias="thresholdTemperature", description="Limite térmico configurado (°C)")
    umidade_registrada: float = Field(..., alias="recordedHumidity", description="Umidade registrada no evento (%)")
    disparado_em: datetime = Field(..., alias="triggeredAt", description="Timestamp de disparo do alerta")
    ativo: bool = Field(default=True, alias="active", description="Indica se o alerta permanece ativo")


# Aliases para compatibilidade entre módulos
DashboardSummary = ResumoPainel
ForecastDayPoint = PontoPrevisaoDiaria
HarvestForecast = PrevisaoColheita
PlotLocation = LocalizacaoTalhao
Plot = Talhao
ThermalAlert = AlertaTermico

__all__ = [
    "LeituraClimatica",
    "ResumoPainel",
    "PontoPrevisaoDiaria",
    "PrevisaoColheita",
    "LocalizacaoTalhao",
    "Talhao",
    "AlertaTermico",
    "ClimateReading",
    "DashboardSummary",
    "ForecastDayPoint",
    "HarvestForecast",
    "Plot",
    "PlotLocation",
    "ThermalAlert",
]
