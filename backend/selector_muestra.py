"""Selector productivo de muestra.

V1 usa seleccion aleatoria estratificada. Los historicos quedan fuera de la
decision productiva: no rankean, filtran, corrigen ni redibujan centros.
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from datetime import datetime, timezone
from typing import Any


METODO_PRODUCTIVO = "stratified_random"
ALGORITHM_VERSION = "stratified_random_v1"
DEFAULT_SAMPLE_SIZE = 120
DEFAULT_RESERVE_SIZE = 180
DEFAULT_SEED = 2026
DOMESTIC_STATE_IDS = set(range(1, 25))


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def ensure_selector_schema(conn: sqlite3.Connection) -> None:
    """Crea contratos aditivos para reproducibilidad y auditoria manual."""
    cols_muestra = {r[1] for r in conn.execute("PRAGMA table_info(muestra)")}
    for col, ddl in {
        "rol_muestra": "ALTER TABLE muestra ADD COLUMN rol_muestra TEXT DEFAULT 'titular'",
        "generacion_id": "ALTER TABLE muestra ADD COLUMN generacion_id INTEGER",
    }.items():
        if col not in cols_muestra:
            conn.execute(ddl)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS muestra_generaciones (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            id_eleccion         INTEGER NOT NULL REFERENCES elecciones(id),
            tm_hash             TEXT NOT NULL,
            metodo              TEXT NOT NULL,
            sample_size         INTEGER NOT NULL,
            reserve_size        INTEGER NOT NULL DEFAULT 0,
            seed                INTEGER NOT NULL,
            cuotas_json         TEXT NOT NULL,
            frame_count         INTEGER NOT NULL,
            frame_electores     INTEGER NOT NULL,
            algorithm_version   TEXT NOT NULL,
            created_at          TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS muestra_sustituciones (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            id_eleccion         INTEGER NOT NULL REFERENCES elecciones(id),
            centro_removido     TEXT NOT NULL REFERENCES centros(codigo_cne),
            centro_sustituto    TEXT NOT NULL REFERENCES centros(codigo_cne),
            motivo              TEXT NOT NULL,
            usuario             TEXT,
            created_at          TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def _has_election_frame(conn: sqlite3.Connection, id_eleccion: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM election_centers WHERE eleccion_id=? AND eligible=1 LIMIT 1",
        (id_eleccion,),
    ).fetchone() is not None


def build_frame(conn: sqlite3.Connection, id_eleccion: int | None = None) -> list[dict[str, Any]]:
    """Universo preelectoral: Tabla Mesa si existe; si no, centros activos."""
    params: dict[str, Any] = {}
    eligible_join = ""
    eligible_where = "c.activo = 1"
    frame_source_expr = "'centros_activos'"

    if id_eleccion and _has_election_frame(conn, id_eleccion):
        eligible_join = """
            JOIN election_centers ec
              ON ec.centro_id = c.codigo_cne
             AND ec.eleccion_id = :id_eleccion
             AND ec.eligible = 1
        """
        eligible_where = "1 = 1"
        frame_source_expr = "'election_centers'"
        params["id_eleccion"] = id_eleccion

    rows = conn.execute(
        f"""
        SELECT
            c.codigo_cne,
            c.nombre,
            c.num_electores,
            c.num_mesas,
            e.id AS id_estado,
            e.nombre AS estado,
            mu.nombre AS municipio,
            p.nombre AS parroquia,
            {frame_source_expr} AS frame_source
        FROM centros c
        {eligible_join}
        JOIN estados e ON c.id_estado = e.id
        LEFT JOIN municipios mu ON c.id_municipio = mu.id
        LEFT JOIN parroquias p ON c.id_parroquia = p.id
        WHERE {eligible_where}
          AND COALESCE(c.num_electores, 0) > 0
          AND e.id IN ({",".join(str(i) for i in sorted(DOMESTIC_STATE_IDS))})
        ORDER BY e.nombre, c.codigo_cne
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def frame_hash(frame: list[dict[str, Any]]) -> str:
    payload = [
        {
            "codigo_cne": row["codigo_cne"],
            "id_estado": row["id_estado"],
            "num_electores": int(row.get("num_electores") or 0),
            "num_mesas": int(row.get("num_mesas") or 0),
        }
        for row in sorted(frame, key=lambda r: r["codigo_cne"])
    ]
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def allocate_state_quotas(frame: list[dict[str, Any]], sample_size: int) -> dict[int, int]:
    """Cuotas proporcionales a electores.

    Regla: se toma el piso de la cuota exacta; si el tamano alcanza para todos
    los estados, se garantiza minimo 1. Los remanentes se asignan por mayor
    fraccion, luego mayor peso electoral y luego nombre de estado.
    """
    if sample_size <= 0 or not frame:
        return {}

    states: dict[int, dict[str, Any]] = {}
    for row in frame:
        state = int(row["id_estado"])
        bucket = states.setdefault(
            state,
            {"weight": 0.0, "capacity": 0, "estado": row["estado"]},
        )
        bucket["weight"] += float(row.get("num_electores") or 1)
        bucket["capacity"] += 1

    requested = min(sample_size, len(frame))
    total_weight = sum(v["weight"] for v in states.values()) or float(len(frame))
    quotas: dict[int, int] = {}
    fractions = []
    for state, data in states.items():
        exact = requested * data["weight"] / total_weight
        quota = int(exact // 1)
        if requested >= len(states):
            quota = max(1, quota)
        quota = min(quota, data["capacity"])
        quotas[state] = quota
        fractions.append((exact - int(exact // 1), data["weight"], str(data["estado"]), state))

    while sum(quotas.values()) > requested:
        candidates = [
            (quotas[state], fraction, weight, name, state)
            for fraction, weight, name, state in fractions
            if quotas[state] > (1 if requested >= len(states) else 0)
        ]
        if not candidates:
            break
        _, _, _, _, state = sorted(candidates, key=lambda x: (-x[0], x[1], x[3]))[0]
        quotas[state] -= 1

    while sum(quotas.values()) < requested:
        candidates = [
            (fraction, weight, name, state)
            for fraction, weight, name, state in fractions
            if quotas[state] < states[state]["capacity"]
        ]
        if not candidates:
            break
        _, _, _, state = sorted(candidates, key=lambda x: (-x[0], -x[1], x[2]))[0]
        quotas[state] += 1

    return {state: quota for state, quota in sorted(quotas.items()) if quota > 0}


def _sample_by_state(
    frame: list[dict[str, Any]],
    quotas: dict[int, int],
    seed: int,
    excluded: set[str] | None = None,
) -> list[dict[str, Any]]:
    excluded = excluded or set()
    rng = random.Random(seed)
    by_state: dict[int, list[dict[str, Any]]] = {}
    for row in frame:
        if row["codigo_cne"] in excluded:
            continue
        by_state.setdefault(int(row["id_estado"]), []).append(row)

    selected: list[dict[str, Any]] = []
    for state, quota in sorted(quotas.items()):
        population = sorted(by_state.get(state, []), key=lambda r: r["codigo_cne"])
        picked = rng.sample(population, min(quota, len(population)))
        selected.extend(sorted(picked, key=lambda r: r["codigo_cne"]))
    return selected


def generar_muestra_estratificada(
    conn: sqlite3.Connection,
    id_eleccion: int,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    reserve_size: int = DEFAULT_RESERVE_SIZE,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Genera titulares y reservas sin consultar resultados historicos."""
    frame = build_frame(conn, id_eleccion=id_eleccion)
    titular_quotas = allocate_state_quotas(frame, sample_size)
    titulares = _sample_by_state(frame, titular_quotas, seed)
    titular_codes = {row["codigo_cne"] for row in titulares}

    reserve_frame = [row for row in frame if row["codigo_cne"] not in titular_codes]
    reserve_quotas = allocate_state_quotas(reserve_frame, reserve_size)
    reservas = _sample_by_state(frame, reserve_quotas, seed + 1, excluded=titular_codes)

    for row in titulares:
        row["rol_muestra"] = "titular"
        row["unidad_geo"] = row["estado"]
        row["nivel_seleccion"] = "estado"
    for row in reservas:
        row["rol_muestra"] = "reserva"
        row["unidad_geo"] = row["estado"]
        row["nivel_seleccion"] = "estado"

    for rows in (titulares, reservas):
        by_state: dict[int, int] = {}
        for row in sorted(rows, key=lambda r: (r["id_estado"], r["codigo_cne"])):
            state = int(row["id_estado"])
            by_state[state] = by_state.get(state, 0) + 1
            row["rank"] = by_state[state]

    return {
        "id_eleccion": id_eleccion,
        "metodo": METODO_PRODUCTIVO,
        "sample_size": sample_size,
        "reserve_size": reserve_size,
        "seed": seed,
        "cuotas": titular_quotas,
        "cuotas_reserva": reserve_quotas,
        "frame_hash": frame_hash(frame),
        "frame_count": len(frame),
        "frame_electores": sum(int(row.get("num_electores") or 0) for row in frame),
        "frame_source": frame[0]["frame_source"] if frame else "sin_frame",
        "algorithm_version": ALGORITHM_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "titulares": titulares,
        "reservas": reservas,
    }


def aplicar_muestra_estratificada(
    conn: sqlite3.Connection,
    id_eleccion: int,
    titulares: list[str],
    reservas: list[str],
    metadata: dict[str, Any],
) -> int:
    """Guarda muestra productiva y metadatos de reproducibilidad."""
    ensure_selector_schema(conn)
    frame = build_frame(conn, id_eleccion=id_eleccion)
    frame_codes = {row["codigo_cne"] for row in frame}
    titular_codes = []
    for code in titulares:
        if code in frame_codes and code not in titular_codes:
            titular_codes.append(code)
    titular_set = set(titular_codes)
    reserva_codes = []
    for code in reservas:
        if code in frame_codes and code not in titular_set and code not in reserva_codes:
            reserva_codes.append(code)

    generation = conn.execute(
        """
        INSERT INTO muestra_generaciones (
            id_eleccion, tm_hash, metodo, sample_size, reserve_size, seed,
            cuotas_json, frame_count, frame_electores, algorithm_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id_eleccion,
            metadata["frame_hash"],
            METODO_PRODUCTIVO,
            int(metadata["sample_size"]),
            int(metadata.get("reserve_size") or 0),
            int(metadata["seed"]),
            _json_dumps(
                {
                    "titulares": metadata.get("cuotas", {}),
                    "reservas": metadata.get("cuotas_reserva", {}),
                }
            ),
            int(metadata.get("frame_count") or len(frame)),
            int(metadata.get("frame_electores") or 0),
            ALGORITHM_VERSION,
        ),
    )
    generation_id = generation.lastrowid

    conn.execute(
        """
        DELETE FROM pesos
        WHERE id_muestra IN (
            SELECT id FROM muestra WHERE id_eleccion = ?
        )
        """,
        (id_eleccion,),
    )
    conn.execute("DELETE FROM muestra WHERE id_eleccion = ?", (id_eleccion,))
    for role, codes in (("titular", titular_codes), ("reserva", reserva_codes)):
        for code in codes:
            conn.execute(
                """
                INSERT INTO muestra (
                    id_eleccion, codigo_centro, tipo_centro, activo, motivo,
                    agregado_por, rol_muestra, generacion_id
                ) VALUES (?, ?, 'estandar', ?, ?, 'selector_productivo', ?, ?)
                """,
                (
                    id_eleccion,
                    code,
                    1 if role == "titular" else 0,
                    f"{METODO_PRODUCTIVO}; seed={metadata['seed']}; role={role}",
                    role,
                    generation_id,
                ),
            )
    conn.commit()
    return len(titular_codes)


def sustituir_por_reserva(
    conn: sqlite3.Connection,
    id_eleccion: int,
    centro_removido: str,
    centro_sustituto: str,
    motivo: str,
    usuario: str = "local",
) -> bool:
    """Promueve una reserva a titular y deja rastro auditable."""
    ensure_selector_schema(conn)
    titular = conn.execute(
        """
        SELECT 1 FROM muestra
        WHERE id_eleccion=? AND codigo_centro=? AND activo=1
          AND COALESCE(rol_muestra, 'titular')='titular'
        """,
        (id_eleccion, centro_removido),
    ).fetchone()
    reserva = conn.execute(
        """
        SELECT 1 FROM muestra
        WHERE id_eleccion=? AND codigo_centro=?
          AND COALESCE(rol_muestra, 'titular')='reserva'
        """,
        (id_eleccion, centro_sustituto),
    ).fetchone()
    if not titular or not reserva:
        return False

    conn.execute(
        "UPDATE muestra SET rol_muestra='removido', activo=0 WHERE id_eleccion=? AND codigo_centro=?",
        (id_eleccion, centro_removido),
    )
    conn.execute(
        "UPDATE muestra SET rol_muestra='titular', activo=1, motivo=? WHERE id_eleccion=? AND codigo_centro=?",
        (f"Sustituto de {centro_removido}: {motivo}", id_eleccion, centro_sustituto),
    )
    conn.execute(
        """
        INSERT INTO muestra_sustituciones (
            id_eleccion, centro_removido, centro_sustituto, motivo, usuario
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (id_eleccion, centro_removido, centro_sustituto, motivo, usuario),
    )
    conn.commit()
    return True


def generar_candidatos(
    conn: sqlite3.Connection,
    id_eleccion: int | None = None,
    eleccion_ref: str = "",
    candidatos_por_unidad: int = 5,
    umbral_pct: float = 10.0,
) -> list[dict[str, Any]]:
    """Compatibilidad legacy: devuelve titulares del selector productivo."""
    if id_eleccion is None:
        return []
    propuesta = generar_muestra_estratificada(
        conn,
        id_eleccion=id_eleccion,
        sample_size=DEFAULT_SAMPLE_SIZE,
        reserve_size=0,
        seed=DEFAULT_SEED,
    )
    return propuesta["titulares"]


def aplicar_muestra(
    conn: sqlite3.Connection,
    id_eleccion: int,
    codigos_centros: list[str],
    tipo_centro: str = "estandar",
) -> int:
    metadata = generar_muestra_estratificada(
        conn,
        id_eleccion=id_eleccion,
        sample_size=len(codigos_centros),
        reserve_size=0,
        seed=DEFAULT_SEED,
    )
    metadata["sample_size"] = len(codigos_centros)
    return aplicar_muestra_estratificada(conn, id_eleccion, codigos_centros, [], metadata)
