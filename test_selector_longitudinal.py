from __future__ import annotations

import math
import sqlite3
from pathlib import Path

from backend import selector_longitudinal as sl
from backend import selector_muestra as sm


BASE_DIR = Path(__file__).resolve().parent


def _conn_24_states() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    schema = (BASE_DIR / "backend" / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    for state in range(1, 25):
        conn.execute(
            "INSERT INTO estados (id, codigo_cne, nombre) VALUES (?, ?, ?)",
            (state, f"{state:02d}", f"Estado {state:02d}"),
        )
    conn.execute(
        """INSERT INTO elecciones
           (id, nombre, tipo, fecha, hora_apertura, hora_cierre, activa)
           VALUES (1, 'Presidencial futura', 'nacional', '2026-12-06', '07:00', '18:00', 1)"""
    )
    for state in range(1, 25):
        for idx in range(1, 13):
            code = f"{state:02d}{idx:07d}"
            conn.execute(
                """INSERT INTO centros
                   (codigo_cne, nombre, id_estado, num_mesas, num_electores, activo)
                   VALUES (?, ?, ?, 1, ?, 1)""",
                (code, f"Centro {state}-{idx}", state, 1000 * state + idx),
            )
            conn.execute(
                "INSERT INTO election_centers (eleccion_id, centro_id, eligible) VALUES (1, ?, 1)",
                (code,),
            )
    conn.commit()
    return conn


def _insert_historical(conn: sqlite3.Connection, ref: str, code: str, pct_gov: float) -> None:
    gov = int(round(pct_gov))
    conn.execute(
        """INSERT INTO resultados_historicos
           (codigo_centro, eleccion_ref, votos_validos, votos_gobierno, votos_oposicion,
            pct_gobierno, pct_oposicion, granularidad)
           VALUES (?, ?, 100, ?, ?, ?, ?, 'centro')""",
        (code, ref, gov, 100 - gov, pct_gov, 100 - pct_gov),
    )


def test_feature_values_apply_v1_fallback_and_preserve_missing():
    none = sl.longitudinal_feature_values([])
    one = sl.longitudinal_feature_values([None, -4.0])
    two = sl.longitudinal_feature_values([2.0, -4.0])

    assert none["n_hist"] == 0
    assert none["selector_score"] is None
    assert none["score_source"] == "no_history"
    assert one["selector_score"] == 4.0
    assert one["score_source"] == "recent_fallback"
    assert two["historical_mae"] == 3.0
    assert round(two["historical_rmse"], 6) == round(math.sqrt(10), 6)
    assert two["historical_bias"] == -1.0
    assert two["selector_score"] == 3.0
    assert two["score_source"] == "longitudinal"


def test_residual_is_center_minus_state():
    assert sl.residual(57.5, 55.0) == 2.5
    assert sl.residual(40.0, 55.0) == -15.0


def test_dhondt_quotas_keep_48_base_72_extras_total_120_and_are_deterministic():
    conn = _conn_24_states()
    frame = sm.build_frame(conn, 1)
    quotas_one = sl.allocate_longitudinal_dhondt_quotas(frame)
    quotas_two = sl.allocate_longitudinal_dhondt_quotas(frame)

    assert quotas_one == quotas_two
    assert len(quotas_one) == 24
    assert sum(quotas_one.values()) == 120
    assert sum(value - sl.BASE_PER_STATE for value in quotas_one.values()) == sl.EXTRAS_DHONDT
    assert min(quotas_one.values()) >= 2


def test_dhondt_extras_start_with_divisor_one_independent_of_base_minimum():
    frame = [
        {"id_estado": 1, "estado": "A", "num_electores": 100},
        {"id_estado": 2, "estado": "B", "num_electores": 99},
    ]

    quotas = sl.allocate_longitudinal_dhondt_quotas(frame, sample_size=5, base_per_state=2)

    assert quotas == {1: 3, 2: 2}


def test_presidential_frame_excludes_non_24_entities():
    frame = [
        {"id_estado": 1, "estado": "A", "num_electores": 100, "codigo_cne": "010000001"},
        {"id_estado": 24, "estado": "X", "num_electores": 100, "codigo_cne": "240000001"},
        {"id_estado": 25, "estado": "Exterior", "num_electores": 100, "codigo_cne": "250000001"},
    ]

    assert [row["id_estado"] for row in sl.presidential_frame(frame)] == [1, 24]


def test_build_features_uses_only_history_before_target_and_normalized_tables():
    conn = _conn_24_states()
    code = "010000001"
    other = "010000002"
    _insert_historical(conn, "2006-presidencial", code, 52.0)
    _insert_historical(conn, "2006-presidencial", other, 48.0)
    _insert_historical(conn, "2012-presidencial", code, 54.0)
    _insert_historical(conn, "2012-presidencial", other, 46.0)
    _insert_historical(conn, "2026-presidencial", code, 99.0)
    _insert_historical(conn, "2028-presidencial", code, 1.0)
    conn.commit()

    features = sl.build_longitudinal_features(conn, 1)
    row = next(item for item in features if item["codigo_cne"] == code)

    assert row["historical_elections_used"] == ["2006-presidencial", "2012-presidencial"]
    assert row["n_hist"] == 2
    assert row["historical_mae"] == 3.0
    assert row["recent_distance"] == 4.0
    assert row["selector_score"] == 3.0
    assert row["score_source"] == "longitudinal"


def test_selection_orders_by_size_restarts_ladder_excludes_null_and_has_no_duplicates():
    features = [
        {"codigo_cne": "010000001", "id_estado": 1, "estado": "A", "num_electores": 3000, "selector_score": 3.0, "score_source": "longitudinal", "n_hist": 2, "recent_distance": 3.0, "historical_mae": 3.0, "historical_rmse": 3.0, "historical_bias": 3.0, "historical_volatility": 0.0, "historical_elections_used": ["2006"], "rank_tamano_estado": 1},
        {"codigo_cne": "010000002", "id_estado": 1, "estado": "A", "num_electores": 2000, "selector_score": 1.0, "score_source": "longitudinal", "n_hist": 2, "recent_distance": 1.0, "historical_mae": 1.0, "historical_rmse": 1.0, "historical_bias": 1.0, "historical_volatility": 0.0, "historical_elections_used": ["2006"], "rank_tamano_estado": 2},
        {"codigo_cne": "010000003", "id_estado": 1, "estado": "A", "num_electores": 1000, "selector_score": 1.0, "score_source": "longitudinal", "n_hist": 2, "recent_distance": 1.0, "historical_mae": 1.0, "historical_rmse": 1.0, "historical_bias": 1.0, "historical_volatility": 0.0, "historical_elections_used": ["2006"], "rank_tamano_estado": 3},
        {"codigo_cne": "010000004", "id_estado": 1, "estado": "A", "num_electores": 900, "selector_score": None, "score_source": "no_history", "n_hist": 0, "recent_distance": None, "historical_mae": None, "historical_rmse": None, "historical_bias": None, "historical_volatility": None, "historical_elections_used": [], "rank_tamano_estado": 4},
    ]

    selected = sl.select_centers_by_longitudinal_score(features, {1: 3})

    assert [row["codigo_cne"] for row in selected] == ["010000002", "010000003", "010000001"]
    assert selected[-1]["pasada_seleccion"] == 2
    assert selected[-1]["tolerancia_seleccion"] == 4
    assert len({row["codigo_cne"] for row in selected}) == len(selected)
    assert "010000004" not in {row["codigo_cne"] for row in selected}


def test_generate_longitudinal_is_deterministic_and_uses_only_frame_centers():
    conn = _conn_24_states()
    for state in range(1, 25):
        for idx in range(1, 13):
            code = f"{state:02d}{idx:07d}"
            # Cada estado queda centrado en 50; idx 1 y 2 son los mas cercanos.
            _insert_historical(conn, "2006-presidencial", code, 50 + idx)
            _insert_historical(conn, "2012-presidencial", code, 50 - idx)
    _insert_historical(conn, "2006-presidencial", "019999999", 50.0)
    conn.commit()

    one = sl.generar_muestra_longitudinal(conn, 1)
    two = sl.generar_muestra_longitudinal(conn, 1)
    frame_codes = {row["codigo_cne"] for row in sm.build_frame(conn, 1)}

    assert [row["codigo_cne"] for row in one["titulares"]] == [row["codigo_cne"] for row in two["titulares"]]
    assert len(one["titulares"]) == 120
    assert {row["codigo_cne"] for row in one["titulares"]} <= frame_codes
    assert one["method"] == sl.METHOD
    assert one["algorithm_version"] == sl.ALGORITHM_VERSION
    assert one["history_coverage"]["n_hist_ge_2"] == 288


def test_productive_selector_remains_stratified_random_and_unchanged():
    assert sm.METODO_PRODUCTIVO == "stratified_random"
    assert sm.ALGORITHM_VERSION == "stratified_random_v1"

    conn = _conn_24_states()
    propuesta = sm.generar_muestra_estratificada(conn, 1, sample_size=24, reserve_size=0, seed=7)

    assert propuesta["metodo"] == "stratified_random"
    assert propuesta["algorithm_version"] == "stratified_random_v1"
