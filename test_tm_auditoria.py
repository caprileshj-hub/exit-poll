from __future__ import annotations

import sqlite3
from pathlib import Path

from backend import tm_auditoria


BASE_DIR = Path(__file__).resolve().parent


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    schema = (BASE_DIR / "backend" / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.execute("INSERT INTO estados (id, codigo_cne, nombre) VALUES (1, '01', 'DTTO. CAPITAL')")
    conn.execute("INSERT INTO estados (id, codigo_cne, nombre) VALUES (25, '99', 'EXTERIOR')")
    conn.execute(
        """INSERT INTO centros
           (codigo_cne, nombre, id_estado, num_mesas, num_electores, activo)
           VALUES ('010101001', 'Centro nacional', 1, 2, 1500, 1)"""
    )
    conn.execute(
        """INSERT INTO centros
           (codigo_cne, nombre, id_estado, num_mesas, num_electores, activo)
           VALUES ('990101001', 'Consulado', 25, 1, 1200, 1)"""
    )
    conn.commit()
    return conn


def test_snapshot_tm_incluye_exterior_y_elegibilidad_es_domestica():
    conn = _conn()

    snapshot = tm_auditoria.snapshot_frame(conn)

    assert snapshot["nacional"]["centros"] == 2
    assert snapshot["nacional"]["mesas"] == 3
    assert snapshot["nacional"]["electores"] == 2700
    assert snapshot["domestico"]["centros"] == 1
    assert snapshot["exterior"]["centros"] == 1
    assert snapshot["elegibilidad"]["centros_ge_piso"] == 1
