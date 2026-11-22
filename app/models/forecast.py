from datetime import datetime, timezone
from sqlalchemy import JSON, Column, DateTime, String
from app.core.database import Base


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class ParametroPrevisao(Base):
    """
    Parâmetros editáveis da previsão de colheita: a produção mensal (t) de cada cultura.
    Sem linha para a cultura, a API usa os valores padrão de PRODUCAO_MENSAL.
    """

    __tablename__ = "parametros_previsao"

    id_cultura = Column(String, primary_key=True)  # CropId (UVA_SUGRAONE, MANGA_PALMER, ...)
    producao_mensal = Column(JSON, nullable=False)  # lista com 12 valores (Jan..Dez), em toneladas
    atualizado_em = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc, nullable=False)
    atualizado_por = Column(String, nullable=True)  # e-mail de quem fez a última alteração (trilha de auditoria)
