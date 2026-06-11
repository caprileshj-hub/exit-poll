# -*- coding: utf-8 -*-
"""
Regresion B2: la carga diferencial de TM solo puede desactivar centros
dentro de los estados presentes en el CSV. Un TM parcial (una eleccion
regional, p. ej.) no debe desactivar los centros del resto del pais.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

import backend.cargador_tm as cargador_tm

BASE_DIR = Path(__file__).resolve().parent

TM_COLUMNAS = [
    "codigo_centro", "nombre_centro", "direccion",
    "cod_estado", "estado", "cod_municipio", "municipio",
    "cod_parroquia", "parroquia", "numero_mesa", "electores",
]


def _init_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "exitpoll_test.db"
    schema = (BASE_DIR / "backend" / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(cargador_tm, "DB_PATH", str(db_path))
    return db_path


def _seed_dos_estados(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO estados (id, codigo_cne, nombre) VALUES (1, '01', 'DISTRITO CAPITAL')")
    conn.execute("INSERT INTO estados (id, codigo_cne, nombre) VALUES (2, '05', 'ARAGUA')")
    conn.execute("INSERT INTO municipios (id, id_estado, codigo_cne, nombre) VALUES (1, 1, '01', 'LIBERTADOR')")
    conn.execute("INSERT INTO municipios (id, id_estado, codigo_cne, nombre) VALUES (2, 2, '01', 'GIRARDOT')")
    conn.execute("INSERT INTO parroquias (id, id_municipio, codigo_cne, nombre) VALUES (1, 1, '01', 'ALTAGRACIA')")
    conn.execute("INSERT INTO parroquias (id, id_municipio, codigo_cne, nombre) VALUES (2, 2, '01', 'LAS DELICIAS')")
    centros = [
        # (codigo, id_parroquia, id_municipio, id_estado)
        ("010101001", 1, 1, 1),
        ("010101002", 1, 1, 1),
        ("050101001", 2, 2, 2),
        ("050101002", 2, 2, 2),
    ]
    for codigo, id_p, id_m, id_e in centros:
        conn.execute(
            """INSERT INTO centros (
                   codigo_cne, nombre, id_parroquia, id_municipio, id_estado,
                   num_mesas, num_electores, activo
               ) VALUES (?, ?, ?, ?, ?, 2, 800, 1)""",
            (codigo, f"Centro {codigo}", id_p, id_m, id_e),
        )
    conn.commit()


def _escribir_tm_parcial(path: Path) -> None:
    """TM solo del estado 01: trae 010101001 (actualizado) pero ya no 010101002."""
    filas = [
        {
            "codigo_centro": "010101001", "nombre_centro": "CENTRO 010101001",
            "direccion": "CALLE 1", "cod_estado": "01", "estado": "DISTRITO CAPITAL",
            "cod_municipio": "01", "municipio": "LIBERTADOR",
            "cod_parroquia": "01", "parroquia": "ALTAGRACIA",
            "numero_mesa": str(mesa), "electores": "450",
        }
        for mesa in (1, 2, 3)
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=TM_COLUMNAS)
        writer.writeheader()
        writer.writerows(filas)


def test_tm_parcial_no_desactiva_otros_estados(tmp_path, monkeypatch):
    db_path = _init_db(tmp_path, monkeypatch)
    conn = sqlite3.connect(db_path)
    try:
        _seed_dos_estados(conn)
    finally:
        conn.close()

    csv_path = tmp_path / "tm_parcial_dc.csv"
    _escribir_tm_parcial(csv_path)
    cargador_tm.cargar_tm(str(csv_path))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        activos = {
            r["codigo_cne"]: r["activo"]
            for r in conn.execute("SELECT codigo_cne, activo FROM centros")
        }
        # El centro presente en el TM sigue activo y actualizado
        assert activos["010101001"] == 1
        actualizado = conn.execute(
            "SELECT num_mesas, num_electores FROM centros WHERE codigo_cne='010101001'"
        ).fetchone()
        assert actualizado["num_mesas"] == 3
        assert actualizado["num_electores"] == 1350
        # El centro del mismo estado que desaparecio del TM se desactiva
        assert activos["010101002"] == 0
        # Los centros de OTRO estado no se tocan (antes del fix quedaban en 0)
        assert activos["050101001"] == 1
        assert activos["050101002"] == 1
    finally:
        conn.close()


def test_dry_run_no_escribe(tmp_path, monkeypatch):
    db_path = _init_db(tmp_path, monkeypatch)
    conn = sqlite3.connect(db_path)
    try:
        _seed_dos_estados(conn)
    finally:
        conn.close()

    csv_path = tmp_path / "tm_parcial_dc.csv"
    _escribir_tm_parcial(csv_path)
    cargador_tm.cargar_tm(str(csv_path), dry_run=True)

    conn = sqlite3.connect(db_path)
    try:
        activos = conn.execute("SELECT COUNT(*) FROM centros WHERE activo=1").fetchone()[0]
        assert activos == 4
        mesas = conn.execute(
            "SELECT num_mesas FROM centros WHERE codigo_cne='010101001'"
        ).fetchone()[0]
        assert mesas == 2
    finally:
        conn.close()
