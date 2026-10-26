from datetime import datetime, timezone

from app.services.thingspeak import analisar_leitura


def test_analisa_feed_do_canal_com_temperatura_e_umidade():
    # Formato real do feeds.json: valores chegam como string, sem field3/field4
    registro = analisar_leitura(
        {"created_at": "2026-10-23T14:30:15Z", "entry_id": 7, "field1": "31.40", "field2": "38.00"}
    )
    assert registro is not None
    assert registro.id_entrada == 7
    assert registro.temperatura == 31.4
    assert registro.umidade == 38.0
    assert registro.umidade_solo is None
    assert registro.chuva is None
    assert registro.registrado_em == datetime(2026, 10, 23, 14, 30, 15, tzinfo=timezone.utc)


def test_descarta_leituras_invalidas_do_sensor():
    base = {"created_at": "2026-10-23T14:30:15Z", "entry_id": 8}
    # DHT desconectado costuma publicar "nan" ou campo vazio
    assert analisar_leitura({**base, "field1": "nan", "field2": "40"}) is None
    assert analisar_leitura({**base, "field1": None, "field2": "40"}) is None
    assert analisar_leitura({**base, "field1": "150", "field2": "40"}) is None
    assert analisar_leitura({**base, "field1": "30", "field2": "120"}) is None
