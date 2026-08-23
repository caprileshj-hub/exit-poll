from pathlib import Path
import sqlite3

from backend.historico_normalizacion import ensure_historico_normalizado_schema
from backend.import_2018_venpres_a import import_csv
from backend.validar_historico_normalizado import validate


BASE_DIR = Path(__file__).resolve().parent


def test_schema_historico_normalizado_es_aditivo(tmp_path):
    db_path = tmp_path / "hist.db"
    conn = sqlite3.connect(db_path)
    schema = (BASE_DIR / "backend" / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    ensure_historico_normalizado_schema(conn)

    rh_cols = {r[1] for r in conn.execute("PRAGMA table_info(resultados_historicos)")}
    hf_cols = {r[1] for r in conn.execute("PRAGMA table_info(historico_fuentes)")}
    assert {"votantes", "votos_nulos", "incluye_exterior", "corte_fuente"} <= rh_cols
    assert {"mesas_cubiertas", "votos_nulos", "incluye_exterior"} <= hf_cols
    conn.close()


def test_import_2018_venpres_a_no_mezcla_nulos_en_otros(tmp_path):
    db_path = tmp_path / "hist.db"
    conn = sqlite3.connect(db_path)
    schema = (BASE_DIR / "backend" / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.close()

    csv_path = BASE_DIR / "backend" / "data" / "2018" / "resultados_venpres_a_2018.csv"
    totals = import_csv(db_path, csv_path)

    assert totals["centros"] == 14400
    assert totals["mesas"] == 33716
    assert totals["electores"] == 20517997
    assert totals["votantes"] == 9360318
    assert totals["validos"] == 9203220
    assert totals["nulos"] == 157098
    assert totals["gobierno"] == 6227663
    assert totals["oposicion"] == 1924469
    assert totals["otros"] == 1051088

    row = validate(db_path, ("2018-presidencial",))[0]
    assert row["delta_validos"] == 0
    assert row["delta_votantes"] == 0
    assert row["fuente"] == "venpres_a"
    assert row["granularidad"] == "centro"
    assert row["incluye_exterior"] is False
