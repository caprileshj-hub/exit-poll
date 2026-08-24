from __future__ import annotations

import sqlite3
from pathlib import Path

from backend import backtest_muestra as bt


BASE_DIR = Path(__file__).resolve().parent


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    schema = (BASE_DIR / "backend" / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.execute("INSERT INTO estados (id, codigo_cne, nombre) VALUES (1, '01', 'Estado A')")
    conn.execute("INSERT INTO estados (id, codigo_cne, nombre) VALUES (2, '02', 'Estado B')")
    for code, state, electors in [
        ("A", 1, 1000),
        ("B", 1, 900),
        ("C", 1, 800),
        ("D", 2, 700),
        ("E", 2, 600),
    ]:
        conn.execute(
            """INSERT INTO centros
               (codigo_cne, nombre, id_estado, num_mesas, num_electores, activo)
               VALUES (?, ?, ?, 1, ?, 1)""",
            (code, f"Centro {code}", state, electors),
        )
    for ref in ["2006-presidencial", "2009-enmienda", "2012-presidencial"]:
        for code, _, electors in [
            ("A", 1, 1000),
            ("B", 1, 900),
            ("C", 1, 800),
            ("D", 2, 700),
            ("E", 2, 600),
        ]:
            conn.execute(
                """INSERT INTO centro_snapshot
                   (codigo_cne, eleccion_ref, nombre_centro, num_mesas, num_electores, fuente)
                   VALUES (?, ?, ?, 1, ?, 'fixture')""",
                (code, ref, f"Centro {code}", electors),
            )
    _insert_result(conn, "A", "2006-presidencial", 50, 50)
    _insert_result(conn, "A", "2009-enmienda", 55, 45)
    _insert_result(conn, "B", "2006-presidencial", 70, 30)
    _insert_result(conn, "B", "2009-enmienda", 75, 25)
    _insert_result(conn, "D", "2006-presidencial", 40, 60)
    _insert_result(conn, "D", "2009-enmienda", 42, 58)
    _insert_result(conn, "E", "2006-presidencial", 60, 40)

    for code, gov, opo in [
        ("A", 48, 52),
        ("B", 68, 32),
        ("C", 50, 50),
        ("D", 41, 59),
        ("E", 61, 39),
    ]:
        _insert_result(conn, code, "2012-presidencial", gov, opo)
    conn.commit()
    return conn


def _insert_result(conn: sqlite3.Connection, code: str, ref: str, gov: float, opo: float) -> None:
    conn.execute(
        """INSERT INTO resultados_historicos
           (codigo_centro, eleccion_ref, votos_validos, votos_gobierno, votos_oposicion,
            pct_gobierno, pct_oposicion, electores_inscritos)
           VALUES (?, ?, 100, ?, ?, ?, ?, 100)""",
        (code, ref, int(gov), int(opo), gov, opo),
    )


def test_training_refs_excluye_target_y_posteriores():
    conn = _conn()
    conn.execute("INSERT INTO resultados_historicos (codigo_centro, eleccion_ref) VALUES ('A', '2024-presidencial')")
    refs = bt.training_refs_before(conn, "2012-presidencial")
    assert "2012-presidencial" not in refs
    assert "2024-presidencial" not in refs
    assert refs == ["2006-presidencial", "2009-enmienda"]


def test_frame_no_expone_resultados_objetivo_y_solo_centros_target():
    conn = _conn()
    frame = bt.build_historical_frame(conn, "2012-presidencial")
    assert {r["codigo_centro"] for r in frame} == {"A", "B", "C", "D", "E"}
    assert all("pct_gobierno" not in r and "pct_oposicion" not in r for r in frame)
    assert all("votos_validos" not in r for r in frame)


def test_random_seed_reproducible_y_cuota_total():
    conn = _conn()
    frame = bt.build_historical_frame(conn, "2012-presidencial")
    one = bt.select_stratified_random(frame, sample_size=4, seed=7)
    two = bt.select_stratified_random(frame, sample_size=4, seed=7)
    assert [r["codigo_centro"] for r in one["selected"]] == [r["codigo_centro"] for r in two["selected"]]
    assert one["sample_size_actual"] == 4
    assert sum(one["quotas"].values()) == 4


def test_historical_rmse_respeta_n_y_null_no_es_cero():
    conn = _conn()
    conn.execute(
        """INSERT INTO resultados_historicos
           (codigo_centro, eleccion_ref, votos_validos, votos_gobierno, votos_oposicion,
            pct_gobierno, pct_oposicion)
           VALUES ('C', '2006-presidencial', 100, 0, 0, NULL, NULL)"""
    )
    frame = bt.build_historical_frame(conn, "2012-presidencial")
    history = bt.build_training_history(conn, ["2006-presidencial", "2009-enmienda"], frame)
    assert history["A"]["n"] == 2
    assert history["A"]["evidencia_limitada"] is True
    assert history["A"]["rmse"] is not None
    assert history["E"]["n"] == 1
    assert history["E"]["rmse"] is None
    assert "C" not in history


def test_historical_selection_no_elige_centro_inexistente_en_target():
    conn = _conn()
    conn.execute(
        "INSERT INTO centros (codigo_cne, nombre, id_estado, num_electores) VALUES ('Z', 'Centro Z', 1, 500)"
    )
    _insert_result(conn, "Z", "2006-presidencial", 50, 50)
    _insert_result(conn, "Z", "2009-enmienda", 51, 49)
    frame = bt.build_historical_frame(conn, "2012-presidencial")
    history = bt.build_training_history(conn, ["2006-presidencial", "2009-enmienda"], frame)
    selected = bt.select_historical_rmse(frame, history, sample_size=4, seed=1)
    codes = {r["codigo_centro"] for r in selected["selected"]}
    assert "Z" not in codes
    assert codes <= {r["codigo_centro"] for r in frame}


def test_evaluacion_ocurre_despues_de_seleccion_y_metricas_conocidas():
    conn = _conn()
    frame = bt.build_historical_frame(conn, "2012-presidencial")
    training_refs = ["2006-presidencial", "2009-enmienda"]
    history = bt.build_training_history(conn, training_refs, frame)
    selected = bt.select_historical_rmse(frame, history, sample_size=2, seed=3)
    assert all("pct_gobierno" not in r for r in selected["selected"])

    result = bt.evaluate_backtest(conn, "2012-presidencial", "historical_rmse_state", selected, frame, training_refs)
    assert result["label"] == "selection_only_estimate"
    assert result["target_ref"] == "2012-presidencial"
    assert result["sample_size_actual"] == 2
    assert result["absolute_error_pp"] is not None
    assert result["state_MAE_pp"] is not None


def test_walk_forward_skipped_si_no_hay_frame():
    conn = _conn()
    result = bt.run_walk_forward(conn, target_refs=["2013-presidencial"], sample_size=2, random_seeds=[1, 2])
    assert result["targets"][0]["status"] == "SKIPPED"
    assert "frame" in result["targets"][0]["reason"]
