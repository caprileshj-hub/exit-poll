from __future__ import annotations

import sqlite3
from pathlib import Path

from backend import selector_muestra as sm


BASE_DIR = Path(__file__).resolve().parent


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    schema = (BASE_DIR / "backend" / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    sm.ensure_selector_schema(conn)
    for state_id, name in [(1, "Estado A"), (2, "Estado B"), (3, "Estado C")]:
        conn.execute(
            "INSERT INTO estados (id, codigo_cne, nombre) VALUES (?, ?, ?)",
            (state_id, f"{state_id:02d}", name),
        )
    conn.execute(
        "INSERT INTO estados (id, codigo_cne, nombre) VALUES (25, '99', 'Exterior')"
    )
    conn.execute(
        """INSERT INTO elecciones
           (id, nombre, tipo, fecha, hora_apertura, hora_cierre, activa)
           VALUES (1, 'Prueba presidencial', 'nacional', '2026-01-01', '07:00', '18:00', 1)"""
    )
    idx = 1
    for state_id, base in [(1, 1000), (2, 600), (3, 200)]:
        for local in range(8):
            code = f"{state_id:02d}{local:06d}"
            conn.execute(
                """INSERT INTO centros
                   (codigo_cne, nombre, id_estado, num_mesas, num_electores, activo)
                   VALUES (?, ?, ?, 1, ?, 1)""",
                (code, f"Centro {idx}", state_id, base + local),
            )
            if local < 6:
                conn.execute(
                    "INSERT INTO election_centers (eleccion_id, centro_id, eligible) VALUES (1, ?, 1)",
                    (code,),
                )
            idx += 1
    for local in range(3):
        code = f"99{local:06d}"
        conn.execute(
            """INSERT INTO centros
               (codigo_cne, nombre, id_estado, num_mesas, num_electores, activo)
               VALUES (?, ?, 25, 1, 900, 1)""",
            (code, f"Exterior {local}"),
        )
        conn.execute(
            "INSERT INTO election_centers (eleccion_id, centro_id, eligible) VALUES (1, ?, 1)",
            (code,),
        )
    conn.execute(
        """INSERT INTO resultados_historicos
           (codigo_centro, eleccion_ref, votos_validos, votos_gobierno, votos_oposicion,
            pct_gobierno, pct_oposicion)
           VALUES ('01000000', '2024-presidencial', 100, 40, 60, 40, 60)"""
    )
    conn.commit()
    return conn


def _codes(rows: list[dict]) -> list[str]:
    return [r["codigo_cne"] for r in rows]


def test_reproducibilidad_misma_entrada_y_seed():
    conn = _conn()
    one = sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=6, seed=77)
    two = sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=6, seed=77)
    assert _codes(one["titulares"]) == _codes(two["titulares"])
    assert _codes(one["reservas"]) == _codes(two["reservas"])
    assert one["frame_hash"] == two["frame_hash"]


def test_distinta_seed_puede_producir_muestra_diferente():
    conn = _conn()
    one = sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=0, seed=77)
    two = sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=0, seed=78)
    assert _codes(one["titulares"]) != _codes(two["titulares"])


def test_cuotas_suman_n_y_respetan_minimos_redondeo():
    conn = _conn()
    frame = sm.build_frame(conn, 1)
    cuotas = sm.allocate_state_quotas(frame, 9)
    assert sum(cuotas.values()) == 9
    assert set(cuotas) == {1, 2, 3}
    assert all(v >= 1 for v in cuotas.values())


def test_titulares_reservas_no_solapan_y_pertenecen_al_frame_tm():
    conn = _conn()
    propuesta = sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=6, seed=12)
    frame_codes = {r["codigo_cne"] for r in sm.build_frame(conn, 1)}
    titulares = set(_codes(propuesta["titulares"]))
    reservas = set(_codes(propuesta["reservas"]))
    assert len(titulares) == len(propuesta["titulares"])
    assert len(reservas) == len(propuesta["reservas"])
    assert titulares <= frame_codes
    assert reservas <= frame_codes
    assert not (titulares & reservas)
    assert "01000006" not in titulares | reservas


def test_selector_productivo_excluye_exterior_domestico():
    conn = _conn()
    frame = sm.build_frame(conn, 1)
    assert frame
    assert {int(r["id_estado"]) for r in frame} == {1, 2, 3}
    propuesta = sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=6, seed=12)
    seleccionados = propuesta["titulares"] + propuesta["reservas"]
    assert all(int(r["id_estado"]) != 25 for r in seleccionados)


def test_seleccion_no_consulta_resultados_historicos():
    conn = _conn()
    sql_seen: list[str] = []
    conn.set_trace_callback(sql_seen.append)
    sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=6, seed=12)
    assert not any("resultados_historicos" in sql.lower() for sql in sql_seen)


def test_aplicar_guarda_metadatos_roles_y_sustitucion_auditable():
    conn = _conn()
    propuesta = sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=6, seed=12)
    n = sm.aplicar_muestra_estratificada(
        conn,
        1,
        _codes(propuesta["titulares"]),
        _codes(propuesta["reservas"]),
        propuesta,
    )
    assert n == 9
    roles = dict(
        conn.execute(
            "SELECT rol_muestra, COUNT(*) c FROM muestra GROUP BY rol_muestra"
        ).fetchall()
    )
    assert roles["titular"] == 9
    assert roles["reserva"] == 6
    meta = conn.execute("SELECT * FROM muestra_generaciones").fetchone()
    assert meta["metodo"] == sm.METODO_PRODUCTIVO
    assert meta["seed"] == 12
    assert meta["tm_hash"] == propuesta["frame_hash"]

    titular = propuesta["titulares"][0]["codigo_cne"]
    reserva = propuesta["reservas"][0]["codigo_cne"]
    assert sm.sustituir_por_reserva(conn, 1, titular, reserva, "Centro inaccesible", usuario="tester")
    row = conn.execute(
        "SELECT centro_removido, centro_sustituto, motivo, usuario FROM muestra_sustituciones"
    ).fetchone()
    assert dict(row) == {
        "centro_removido": titular,
        "centro_sustituto": reserva,
        "motivo": "Centro inaccesible",
        "usuario": "tester",
    }
    promoted = conn.execute(
        "SELECT rol_muestra, activo FROM muestra WHERE codigo_centro=?", (reserva,)
    ).fetchone()
    assert promoted["rol_muestra"] == "titular"
    assert promoted["activo"] == 1


def test_aplicar_reemplaza_muestra_con_pesos_existentes():
    conn = _conn()
    propuesta = sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=6, seed=12)
    sm.aplicar_muestra_estratificada(
        conn,
        1,
        _codes(propuesta["titulares"]),
        _codes(propuesta["reservas"]),
        propuesta,
    )
    first_id = conn.execute("SELECT id FROM muestra LIMIT 1").fetchone()["id"]
    conn.execute(
        """INSERT INTO pesos
           (id_muestra, peso_parroquia, peso_municipio, peso_estado, peso_nacion)
           VALUES (?, 1, 1, 1, 1)""",
        (first_id,),
    )
    conn.commit()

    nueva = sm.generar_muestra_estratificada(conn, 1, sample_size=9, reserve_size=6, seed=13)
    assert sm.aplicar_muestra_estratificada(
        conn,
        1,
        _codes(nueva["titulares"]),
        _codes(nueva["reservas"]),
        nueva,
    ) == 9
    assert conn.execute("SELECT COUNT(*) c FROM pesos").fetchone()["c"] == 0
