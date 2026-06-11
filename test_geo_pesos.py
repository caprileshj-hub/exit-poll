# -*- coding: utf-8 -*-
"""
Regresion B4/B5:
  - B4: el calculo de pesos no debe excluir centros con id_municipio NULL
    (los crea la ingesta IA cuando el archivo no trae municipio).
  - B5: la ingesta IA debe reusar la geografia creada por cargador_tm
    ("MP. ZAMORA" y "Zamora" son el mismo municipio), no duplicarla.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import backend.app as app_backend
import backend.calculador_pesos as calculador_pesos

BASE_DIR = Path(__file__).resolve().parent


def _crear_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "exitpoll_test.db"
    schema = (BASE_DIR / "backend" / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.commit()
    conn.close()
    return db_path


def test_pesos_incluye_centros_sin_municipio(tmp_path, monkeypatch):
    db_path = _crear_db(tmp_path)
    monkeypatch.setattr(calculador_pesos, "DB_PATH", str(db_path))

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO estados (id, codigo_cne, nombre, es_excepcion) VALUES (1, '05', 'ARAGUA', 0)")
        conn.execute("INSERT INTO municipios (id, id_estado, codigo_cne, nombre) VALUES (1, 1, '01', 'GIRARDOT')")
        conn.execute(
            """INSERT INTO centros (codigo_cne, nombre, id_municipio, id_estado, num_mesas, num_electores, activo)
               VALUES ('050101001', 'Centro con municipio', 1, 1, 2, 1000, 1)"""
        )
        # Centro creado por ingesta IA sin municipio asignado
        conn.execute(
            """INSERT INTO centros (codigo_cne, nombre, id_municipio, id_estado, num_mesas, num_electores, activo)
               VALUES ('AI_1_abc123', 'Centro IA sin municipio', NULL, 1, 1, 400, 1)"""
        )
        conn.execute(
            """INSERT INTO elecciones (id, nombre, tipo, fecha, hora_apertura, hora_cierre, activa)
               VALUES (1, 'Regional Aragua', 'regional', '2026-11-01', '07:00', '18:00', 1)"""
        )
        conn.execute("INSERT INTO muestra (id, id_eleccion, codigo_centro, tipo_centro, activo) VALUES (1, 1, '050101001', 'estandar', 1)")
        conn.execute("INSERT INTO muestra (id, id_eleccion, codigo_centro, tipo_centro, activo) VALUES (2, 1, 'AI_1_abc123', 'estandar', 1)")
        conn.commit()
    finally:
        conn.close()

    calculador_pesos.calcular(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        pesos = {r["id_muestra"]: dict(r) for r in conn.execute("SELECT * FROM pesos")}
        # Antes del fix el INNER JOIN dejaba fuera al centro sin municipio
        assert set(pesos) == {1, 2}
        # Cada uno es unico en su grupo municipal: peso 1
        assert pesos[1]["peso_municipio"] == pytest.approx(1.0)
        assert pesos[2]["peso_municipio"] == pytest.approx(1.0)
        assert pesos[2]["peso_nacion"] > 0
    finally:
        conn.close()


def test_ingesta_ia_reusa_geografia_de_cargador_tm(tmp_path):
    db_path = _crear_db(tmp_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # Geografia tal como la guarda cargador_tm (nombres crudos CNE)
        conn.execute("INSERT INTO estados (id, codigo_cne, nombre) VALUES (1, '05', 'EDO. ARAGUA')")
        conn.execute("INSERT INTO municipios (id, id_estado, codigo_cne, nombre) VALUES (1, 1, '08', 'MP. ZAMORA')")
        conn.execute("INSERT INTO parroquias (id, id_municipio, codigo_cne, nombre) VALUES (1, 1, '01', 'CM. VILLA DE CURA')")
        conn.commit()

        # La ingesta IA llega con nombres "limpios"
        id_estado, id_municipio, id_parroquia = app_backend._obtener_o_crear_geo(
            conn, "Aragua", "Zamora", "Villa de Cura", cod_estado="05"
        )
        assert id_estado == 1
        assert id_municipio == 1   # antes del fix creaba un municipio AI## duplicado
        assert id_parroquia == 1
        assert conn.execute("SELECT COUNT(*) FROM municipios").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM parroquias").fetchone()[0] == 1

        # Un municipio realmente nuevo si se crea
        _, id_mun_nuevo, _ = app_backend._obtener_o_crear_geo(
            conn, "Aragua", "Sucre", None, cod_estado="05"
        )
        assert id_mun_nuevo != 1
        assert conn.execute("SELECT COUNT(*) FROM municipios").fetchone()[0] == 2
    finally:
        conn.close()
