import zlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.climate import DadosClimaticos
from app.models.station import Station
from app.schemas.station import LeituraEstacao, NetworkHealth, PosicaoMapa, Station as StationSchema

# Regras de negócio do status da estação (README do front, seção 9)
BATERIA_BAIXA = 20
LIMITE_SEM_LEITURA = timedelta(minutes=30)
LIMITE_SEM_SINAL = timedelta(hours=24)

# Área de cada município no mapa SVG do front (x/y iniciais e amplitude, 0–100)
AREA_MUNICIPIO: dict[str, Tuple[float, float]] = {
    "PETROLINA": (18.0, 48.0),
    "JUAZEIRO": (68.0, 28.0),
}
AMPLITUDE_X, AMPLITUDE_Y = 16.0, 20.0


def calcular_posicao(id_estacao: str, municipio: str) -> Tuple[float, float]:
    """Posiciona o pin dentro da área do município de forma determinística (mesmo id → mesma posição)."""
    base_x, base_y = AREA_MUNICIPIO.get(municipio, (42.0, 40.0))
    semente = zlib.crc32(id_estacao.encode())
    deslocamento_x = (semente % 1000) / 1000 * AMPLITUDE_X
    deslocamento_y = ((semente // 1000) % 1000) / 1000 * AMPLITUDE_Y
    return round(base_x + deslocamento_x, 1), round(base_y + deslocamento_y, 1)


def calcular_status(
    bateria: int, ultima_leitura_em: Optional[datetime], agora: datetime
) -> Tuple[str, Optional[str]]:
    """Retorna (status, motivo) conforme bateria e atraso da última leitura."""
    if ultima_leitura_em is None:
        return "INATIVO", "Aguardando 1ª leitura"
    atraso = agora - ultima_leitura_em
    if atraso > LIMITE_SEM_SINAL:
        return "INATIVO", "Sem sinal"
    if bateria < BATERIA_BAIXA:
        return "ATENCAO", "Checar bateria"
    if atraso > LIMITE_SEM_LEITURA:
        return "ATENCAO", f"Sem leitura há {int(atraso.total_seconds() // 60)} min"
    return "ATIVO", None


async def obter_ultima_leitura(db: AsyncSession) -> Optional[DadosClimaticos]:
    resultado = await db.execute(
        select(DadosClimaticos).order_by(DadosClimaticos.registrado_em.desc()).limit(1)
    )
    return resultado.scalars().first()


def montar_estacao(
    estacao: Station, ultima_leitura: Optional[DadosClimaticos], agora: datetime
) -> StationSchema:
    """
    Converte o modelo no contrato Station do front-end.
    A ingestão lê um único canal (THINGSPEAK_CHANNEL_ID); só a estação desse canal recebe leituras.
    """
    leitura = ultima_leitura if estacao.canal_thingspeak == settings.THINGSPEAK_CHANNEL_ID else None
    leitura_em = leitura.registrado_em if leitura else None
    status, motivo = calcular_status(estacao.bateria, leitura_em, agora)

    return StationSchema(
        id=estacao.id,
        nome=estacao.nome,
        municipio=estacao.municipio,
        posicao=PosicaoMapa(x=estacao.posicao_x, y=estacao.posicao_y),
        status=status,
        motivo_status=motivo,
        bateria=estacao.bateria,
        ultima_leitura_em=leitura_em,
        ultima_leitura=(
            LeituraEstacao(
                temperatura=leitura.temperatura,
                umidade_solo=leitura.umidade_solo,
                umidade_ar=leitura.umidade,
            )
            if leitura
            else None
        ),
        produto_id=estacao.produto_id,
        canal_thingspeak=estacao.canal_thingspeak,
    )


async def listar_estacoes(db: AsyncSession) -> List[StationSchema]:
    resultado = await db.execute(select(Station).order_by(Station.id.asc()))
    estacoes = resultado.scalars().all()
    ultima_leitura = await obter_ultima_leitura(db)
    agora = datetime.now(timezone.utc)
    return [montar_estacao(e, ultima_leitura, agora) for e in estacoes]


async def calcular_saude_rede(db: AsyncSession) -> NetworkHealth:
    estacoes = await listar_estacoes(db)
    ativas = sum(1 for e in estacoes if e.status == "ATIVO")
    atencao = sum(1 for e in estacoes if e.status == "ATENCAO")
    ultima_leitura = await obter_ultima_leitura(db)

    return NetworkHealth(
        total=len(estacoes),
        online=ativas + atencao,
        ativas=ativas,
        atencao=atencao,
        inativas=len(estacoes) - ativas - atencao,
        ultima_sincronizacao=(
            ultima_leitura.criado_em or ultima_leitura.registrado_em
            if ultima_leitura
            else datetime.now(timezone.utc)
        ),
    )


# Aliases para compatibilidade entre módulos
list_stations = listar_estacoes
get_network_health = calcular_saude_rede
build_station = montar_estacao
