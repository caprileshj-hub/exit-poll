# -*- coding: utf-8 -*-
"""
Prueba de flujo: simula un dia de eleccion con llegada progresiva de
opiniones desde centros de la muestra y verifica el guardrail del analista.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.analista_ia as analista_ia
import backend.app as app_backend


INSUFICIENTE = "datos insuficientes para establecer tendencias"


def _init_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "exitpoll_test.db"
    schema = Path("backend/schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(app_backend, "DB_PATH", db_path)
    return db_path


def _seed_eleccion(conn: sqlite3.Connection) -> dict[str, int]:
    conn.execute(
        "INSERT INTO estados (id, codigo_cne, nombre) VALUES (1, '01', 'Distrito Capital')"
    )
    conn.execute(
        "INSERT INTO municipios (id, id_estado, codigo_cne, nombre) VALUES (1, 1, '01', 'Libertador')"
    )
    conn.execute(
        "INSERT INTO parroquias (id, id_municipio, codigo_cne, nombre) VALUES (1, 1, '01', 'Altagracia')"
    )
    for idx in range(1, 5):
        codigo = f"010100{idx:03d}"
        conn.execute(
            """INSERT INTO centros (
                   codigo_cne, nombre, id_parroquia, id_municipio, id_estado,
                   num_mesas, num_electores, activo
               ) VALUES (?, ?, 1, 1, 1, 1, 500, 1)""",
            (codigo, f"Centro {idx}"),
        )
    conn.execute(
        """INSERT INTO elecciones (
               id, nombre, tipo, fecha, hora_apertura, hora_cierre, activa
           ) VALUES (1, 'Simulacion nacional', 'nacional', '2026-05-01', '07:00', '18:00', 1)"""
    )
    conn.execute(
        """INSERT INTO candidatos (id, id_eleccion, nombre, partido, bando, tipo, orden)
           VALUES (1, 1, 'Candidata Gobierno', 'GOB', 'gobierno', 'unico', 1)"""
    )
    conn.execute(
        """INSERT INTO candidatos (id, id_eleccion, nombre, partido, bando, tipo, orden)
           VALUES (2, 1, 'Candidato Oposicion', 'OPO', 'oposicion', 'unico', 2)"""
    )
    for idx in range(1, 5):
        codigo = f"010100{idx:03d}"
        telefono = f"+58414000{idx:04d}"
        conn.execute(
            "INSERT INTO muestra (id, id_eleccion, codigo_centro, tipo_centro, activo) VALUES (?, 1, ?, 'estandar', 1)",
            (idx, codigo),
        )
        conn.execute(
            "INSERT INTO encuestadores (telefono, nombre, codigo_centro, id_eleccion, activo) VALUES (?, ?, ?, 1, 1)",
            (telefono, f"Encuestador {idx}", codigo),
        )
    conn.commit()
    return {"eleccion_id": 1}


def _inyectar_opiniones(conn: sqlite3.Connection, inicio: int, cantidad: int, turno: int) -> None:
    centros = [f"010100{idx:03d}" for idx in range(1, 5)]
    telefonos = [f"+58414000{idx:04d}" for idx in range(1, 5)]
    for offset in range(cantidad):
        n = inicio + offset
        centro_idx = n % len(centros)
        # La oposicion arranca competitiva y luego consolida una ventaja moderada.
        id_candidato = 2 if (n % 10) < 6 else 1
        hora = f"2026-05-01T{7 + turno:02d}:{(n % 6) * 10:02d}:00"
        conn.execute(
            "INSERT INTO sms_raw (id, from_number, contenido, procesado) VALUES (?, ?, ?, 1)",
            (n, telefonos[centro_idx], f"C{centros[centro_idx]};V{id_candidato};T{turno}",),
        )
        conn.execute(
            """INSERT INTO votos (
                   id_sms, codigo_centro, id_candidato, telefono, hora, turno, valido
               ) VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (n, centros[centro_idx], id_candidato, telefonos[centro_idx], hora, turno),
        )
    conn.commit()


def _inyectar_resultados_historicos(conn: sqlite3.Connection) -> None:
    for idx in range(1, 5):
        codigo = f"010100{idx:03d}"
        conn.execute(
            """INSERT INTO resultados_historicos (
                   codigo_centro, eleccion_ref, votos_validos,
                   votos_gobierno, votos_oposicion, pct_gobierno, pct_oposicion
               ) VALUES (?, 'referencia-test', 100, 40, 60, 40.0, 60.0)""",
            (codigo,),
        )
    conn.commit()


def _analisis(conn: sqlite3.Connection) -> dict:
    eleccion = conn.execute("SELECT * FROM elecciones WHERE activa=1").fetchone()
    candidatos = app_backend._nombres_candidatos(conn, eleccion["id"])
    contexto = app_backend._contexto_analista(conn, eleccion, candidatos)
    return analista_ia.analizar_contexto(contexto, "como va evolucionando la tendencia nacional")


def test_simula_dia_electoral_y_guardrail_ia(tmp_path, monkeypatch):
    db_path = _init_db(tmp_path, monkeypatch)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _seed_eleccion(conn)

        _inyectar_opiniones(conn, inicio=1, cantidad=40, turno=0)
        _inyectar_opiniones(conn, inicio=41, cantidad=40, turno=1)
        temprano = _analisis(conn)
        assert temprano["estado"] == "insuficiente"
        assert temprano["resumen"] == INSUFICIENTE

        _inyectar_opiniones(conn, inicio=81, cantidad=40, turno=2)
        consolidado = _analisis(conn)
        assert consolidado["estado"] != "insuficiente"
        assert consolidado["resumen"] != INSUFICIENTE
        assert consolidado["metricas"]["total_opiniones"] == 120
        assert consolidado["metricas"]["ventaja_actual"] < 0
    finally:
        conn.close()


def test_live_usa_dashboard_referencia_si_no_hay_votos(tmp_path, monkeypatch):
    db_path = _init_db(tmp_path, monkeypatch)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _seed_eleccion(conn)
        _inyectar_resultados_historicos(conn)

        payload = app_backend._dashboard_stream_payload(conn)
        assert payload["fuente_datos"] == "dashboard_referencia"
        assert payload["total_opiniones"] == 400
        assert payload["geo"]
        assert payload["series"]["VENEZUELA"]

        contexto = app_backend._contexto_analista(
            conn,
            conn.execute("SELECT * FROM elecciones WHERE activa=1").fetchone(),
            app_backend._nombres_candidatos(conn, 1),
        )
        assert contexto["fuente_datos"] == "dashboard_referencia"
        assert contexto["total_opiniones"] == 400
        assert contexto["suficiencia"]["estados"]["Distrito Capital"]["datos_suficientes"] is True
        lectura_estado = analista_ia.analizar_contexto(contexto, "como va Distrito Capital")
        assert lectura_estado["estado"] == "dato_disponible"
        assert "data de referencia que muestra el dashboard" in lectura_estado["resumen"]
        lectura_sin_estado = analista_ia.analizar_contexto(contexto, "como va Carabobo")
        assert lectura_sin_estado["estado"] == "sin_datos"
        assert lectura_sin_estado["resumen"] == INSUFICIENTE
    finally:
        conn.close()

    client = TestClient(app_backend.app)
    response = client.get("/live")
    assert response.status_code == 200
    assert "Corre: python backend/simulador_showcase.py --reset" not in response.text
    assert "AI Electoral Analyst" in response.text
    assert "ep-live-source" in response.text
    assert "Datos de referencia del dashboard" in response.text
