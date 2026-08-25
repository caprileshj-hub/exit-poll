"""Laboratorio asistido para seleccion de muestra.

Calcula catalogo, score y confianza desde datos agregados por centro.
No usa datos personales ni toca las tablas de votos en vivo.
"""

from __future__ import annotations

import math
import re
import sqlite3
import statistics
import unicodedata
from collections import Counter, defaultdict
from typing import Any

try:
    from historico_normalizacion import ensure_historico_normalizado_schema
except ImportError:  # pragma: no cover - package import path
    from .historico_normalizacion import ensure_historico_normalizado_schema


FUENTE_FACTOR = {
    "cne_oficial": 1.0,
    "cne_recuperado": 0.85,
    "actas_cvzla": 0.78,
    "esdata_wayback": 0.80,
    "estudio_exitpoll": 0.60,
    "otro": 0.50,
}

GRANULARIDAD_FACTOR = {
    "mesa": 1.0,
    "centro": 1.0,
    "parroquia": 0.60,
    "municipio": 0.50,
    "estado": 0.30,
    "nacional": 0.15,
}

RECENCY_DECAY = 0.85
SHRINKAGE_K = 1.5
MIN_STRONG_N_EFF = 2.5
UTILITY_WEIGHTS = {
    "representatividad": 0.50,
    "estabilidad": 0.30,
    "volumen": 0.20,
}

ESTADO_LABELS = {
    "AMAZONAS": "Amazonas",
    "ANZOATEGUI": "Anzoategui",
    "APURE": "Apure",
    "ARAGUA": "Aragua",
    "BARINAS": "Barinas",
    "BOLIVAR": "Bolivar",
    "CARABOBO": "Carabobo",
    "COJEDES": "Cojedes",
    "DELTA AMAC": "Delta Amacuro",
    "DELTA AMACURO": "Delta Amacuro",
    "DISTRITO CAPITAL": "Distrito Capital",
    "FALCON": "Falcon",
    "GUARICO": "Guarico",
    "LARA": "Lara",
    "MERIDA": "Merida",
    "MIRANDA": "Miranda",
    "MONAGAS": "Monagas",
    "NUEVA ESPARTA": "Nueva Esparta",
    "PORTUGUESA": "Portuguesa",
    "SUCRE": "Sucre",
    "TACHIRA": "Tachira",
    "TRUJILLO": "Trujillo",
    "VARGAS": "Vargas/La Guaira",
    "LA GUAIRA": "Vargas/La Guaira",
    "YARACUY": "Yaracuy",
    "ZULIA": "Zulia",
    "EXTERIOR": "Exterior",
}
CONVERGENCE_BONUS_MAX = 8.0
CONVERGENCE_FULL_PP = 8.0


def ensure_muestra_lab_tables(conn) -> None:
    """Crea contratos aditivos requeridos por el laboratorio."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(muestra)")}
    for col, ddl in {
        "motivo": "ALTER TABLE muestra ADD COLUMN motivo TEXT",
        "agregado_por": "ALTER TABLE muestra ADD COLUMN agregado_por TEXT",
        "score_snapshot": "ALTER TABLE muestra ADD COLUMN score_snapshot REAL",
        "confianza_snapshot": "ALTER TABLE muestra ADD COLUMN confianza_snapshot REAL",
        "created_at": "ALTER TABLE muestra ADD COLUMN created_at TEXT",
    }.items():
        if col not in cols:
            conn.execute(ddl)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_fuentes (
            eleccion_ref    TEXT PRIMARY KEY,
            fuente          TEXT NOT NULL,
            granularidad    TEXT NOT NULL,
            cobertura_pct   REAL,
            comparabilidad  TEXT NOT NULL DEFAULT 'directa',
            notas           TEXT,
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS centro_codigos (
            codigo_cne      TEXT NOT NULL,
            codigo_alterno  TEXT NOT NULL,
            tipo_codigo     TEXT NOT NULL,
            fuente          TEXT NOT NULL,
            confianza_match REAL NOT NULL DEFAULT 1.0,
            created_at      TEXT DEFAULT (datetime('now')),
            PRIMARY KEY(codigo_cne, codigo_alterno, tipo_codigo)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cc_alt ON centro_codigos(codigo_alterno)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS centro_snapshot (
            codigo_cne      TEXT NOT NULL,
            eleccion_ref    TEXT NOT NULL,
            nombre_centro   TEXT,
            num_mesas       INTEGER DEFAULT 0,
            num_electores   INTEGER DEFAULT 0,
            fuente          TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            PRIMARY KEY(codigo_cne, eleccion_ref)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cs_ref ON centro_snapshot(eleccion_ref)")
    ensure_historico_normalizado_schema(conn)
    conn.commit()


def seed_default_historical_metadata(conn) -> None:
    """Completa metadatos minimos si existen resultados sin fuente registrada."""
    refs = [r["eleccion_ref"] for r in conn.execute(
        "SELECT DISTINCT eleccion_ref FROM resultados_historicos"
    ).fetchall()]
    for ref in refs:
        if ref == "2004-revocatorio":
            meta = (
                ref,
                "esdata_wayback",
                "centro",
                91.4,
                "directa",
                "Recuperacion parcial por centro desde Esdata/Wayback; no cubre el 100% de centros habilitados.",
            )
        elif ref == "2007-referendum":
            meta = (
                ref,
                "esdata_wayback",
                "mesa",
                86.5,
                "directa",
                "Referendum constitucional 2007, primer boletin CNE recuperado desde Esdata/Wayback; combina bloques A/B en una tendencia por centro.",
            )
        elif ref == "2009-enmienda":
            meta = (
                ref,
                "esdata_wayback",
                "mesa",
                99.0,
                "directa",
                "Enmienda constitucional 2009, segundo boletin CNE recuperado desde Esdata/Wayback; SI se almacena como gobierno y NO como oposicion.",
            )
        elif ref in {"2006-presidencial", "2012-presidencial", "2013-presidencial"}:
            meta = (
                ref,
                "cne_recuperado",
                "mesa",
                100.0,
                "directa",
                "Resultado oficial por mesa desde archivo historico Esdata/CNE.",
            )
        elif ref == "2024-presidencial":
            meta = (
                ref,
                "actas_cvzla",
                "centro",
                81.0,
                "directa",
                "Actas agregadas por centro desde ComandoConVzla; cobertura parcial y no aleatoria.",
            )
        else:
            meta = (
                ref,
                "otro",
                "centro",
                None,
                "directa",
                "Fuente historica sin metadatos detallados.",
            )
        conn.execute("""
            INSERT INTO historico_fuentes
                (eleccion_ref, fuente, granularidad, cobertura_pct, comparabilidad, notas)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(eleccion_ref) DO NOTHING
        """, meta)
    conn.commit()


def _year(ref: str) -> int:
    try:
        return int(str(ref)[:4])
    except (TypeError, ValueError):
        return 0


def _row_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _gap(pct_gob: float | None, pct_opo: float | None) -> float:
    return float(pct_gob or 0) - float(pct_opo or 0)


def _legacy_tipo(clasificacion: str) -> str:
    if clasificacion == "bisagra":
        return "bisagra"
    if clasificacion in {"bastion_rojo", "bastion_azul"}:
        return "bastion"
    if clasificacion == "volumen":
        return "volumen"
    return "estandar"


def _confidence(dato: dict[str, Any], ref_rank: dict[str, int]) -> float:
    fuente = FUENTE_FACTOR.get(dato.get("fuente") or "otro", 0.50)
    granularidad = GRANULARIDAD_FACTOR.get(dato.get("granularidad") or "centro", 0.50)
    coverage = dato.get("cobertura_pct")
    coverage_factor = max(0.0, min(1.0, float(coverage) / 100.0)) if coverage is not None else 0.70
    recency = RECENCY_DECAY ** ref_rank.get(dato.get("eleccion_ref", ""), 0)
    return max(0.0, min(1.0, fuente * granularidad * coverage_factor * recency))


def _combined_confidence(values: list[float]) -> float:
    if not values:
        return 0.0
    product = 1.0
    for value in values:
        product *= 1.0 - max(0.0, min(1.0, value))
    return max(0.0, min(1.0, 1.0 - product))


def _history_depth_factor(n_hist: int) -> float:
    """Penaliza series cortas: una fuente buena no equivale a tendencia robusta."""
    if n_hist <= 0:
        return 0.0
    if n_hist == 1:
        return 0.35
    if n_hist == 2:
        return 0.70
    if n_hist == 3:
        return 0.90
    return 1.0


def _sufficiency_factor(n_eff: float) -> float:
    return max(0.0, min(1.0, n_eff / MIN_STRONG_N_EFF))


def _weighted_mean(values: list[float], weights: list[float]) -> float | None:
    pairs = [(float(v), float(w)) for v, w in zip(values, weights) if w > 0]
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total if total else None


def _temporal_convergence(histories: list[dict[str, Any]]) -> tuple[float | None, float]:
    """Mide si el desvio relativo baja con el tiempo.

    Devuelve mejora estimada en puntos porcentuales y score 0-1. Requiere al
    menos tres historicos con brecha nacional comparable; si la pendiente
    empeora, el bonus es cero para evitar doble castigo.
    """
    points = [
        h for h in histories
        if h.get("desvio") is not None and h.get("brecha_ref") is not None
    ]
    if len(points) < 3:
        return None, 0.0
    points.sort(key=lambda h: (_year(str(h.get("eleccion_ref") or "")), str(h.get("eleccion_ref") or "")))
    xs = [float(i) for i, _ in enumerate(points)]
    ys = [float(h["desvio"]) for h in points]
    weights = [max(0.10, float(h.get("confianza_dato") or 0.0)) for h in points]
    w_total = sum(weights)
    if w_total <= 0:
        return None, 0.0
    x_bar = sum(x * w for x, w in zip(xs, weights)) / w_total
    y_bar = sum(y * w for y, w in zip(ys, weights)) / w_total
    denom = sum(w * (x - x_bar) ** 2 for x, w in zip(xs, weights))
    if denom <= 0:
        return None, 0.0
    slope = sum(w * (x - x_bar) * (y - y_bar) for x, y, w in zip(xs, ys, weights)) / denom
    improvement_pp = -slope * (len(points) - 1)
    score = max(0.0, min(1.0, improvement_pp / CONVERGENCE_FULL_PP))
    return improvement_pp, score


def _median(values: list[float]) -> float | None:
    clean = sorted(float(v) for v in values)
    if not clean:
        return None
    mid = len(clean) // 2
    if len(clean) % 2:
        return clean[mid]
    return (clean[mid - 1] + clean[mid]) / 2


def _mad(values: list[float]) -> float | None:
    med = _median(values)
    if med is None:
        return None
    return _median([abs(float(v) - med) for v in values])


def _shrink(observed: float | None, stratum_prior: float | None, n_eff: float, k: float = SHRINKAGE_K) -> float | None:
    if observed is None and stratum_prior is None:
        return None
    if observed is None:
        return stratum_prior
    if stratum_prior is None:
        return observed
    effective_k = k * max(0.0, 1.0 - (n_eff / MIN_STRONG_N_EFF))
    if effective_k <= 0:
        return observed
    return ((n_eff * observed) + (effective_k * stratum_prior)) / (n_eff + effective_k)


def _stratum_key(row: dict[str, Any]) -> str:
    estado = row.get("estado_filtro") or row.get("estado") or "Nacional"
    municipio = row.get("municipio") or ""
    return f"{estado}|{municipio}" if municipio else estado


def _plain_key(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper().replace(".", " ")
    text = re.sub(r"\bEDO\b", " ", text)
    text = re.sub(r"\bDTTO\b", "DISTRITO", text)
    text = re.sub(r"\bNVA\b", "NUEVA", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _estado_display(value: str | None) -> str | None:
    key = _plain_key(value)
    if not key or key == "HISTORICO":
        return None
    if "VARGAS" in key or "GUAIRA" in key:
        return "Vargas/La Guaira"
    if key in {"DISTRITO CAPITAL", "CAPITAL"}:
        return "Distrito Capital"
    if key in {"NUEVA ESPARTA", "NUEVAESPARTA"}:
        return "Nueva Esparta"
    return ESTADO_LABELS.get(key, str(value or "").strip().title() or None)


def _apply_estado_display(row: dict[str, Any], inferred: bool = False) -> None:
    display = _estado_display(row.get("estado"))
    row["estado_raw"] = row.get("estado")
    row["estado_display"] = display
    row["estado_filtro"] = display
    row["geo_inferida"] = bool(inferred and display)
    row["geo_incompleta"] = display is None
    row["estatus_display"] = "historico" if row.get("estatus") == "solo_historico" else row.get("estatus")


def _estado_maps(conn) -> tuple[dict[str, str], dict[str, int]]:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(estados)").fetchall()}
    if "codigo_cne" in cols:
        rows = conn.execute("SELECT id, codigo_cne, nombre FROM estados").fetchall()
        return (
            {str(r["codigo_cne"]).zfill(2): r["nombre"] for r in rows},
            {str(r["codigo_cne"]).zfill(2): r["id"] for r in rows},
        )
    rows = conn.execute("SELECT id, nombre FROM estados").fetchall()
    return (
        {str(r["id"]).zfill(2): r["nombre"] for r in rows},
        {str(r["id"]).zfill(2): r["id"] for r in rows},
    )


def _municipios_by_codigo(conn, estado_ids_by_codigo: dict[str, int]) -> dict[tuple[str, str], str]:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(municipios)").fetchall()}
    if "codigo_cne" not in cols:
        return {}
    estado_codigo_by_id = {estado_id: codigo for codigo, estado_id in estado_ids_by_codigo.items()}
    rows = conn.execute("SELECT id_estado, codigo_cne, nombre FROM municipios").fetchall()
    return {
        (estado_codigo_by_id[r["id_estado"]], str(r["codigo_cne"]).zfill(2)): r["nombre"]
        for r in rows
        if r["id_estado"] in estado_codigo_by_id
    }


def _infer_geo_from_codigo(
    codigo: str,
    estados_by_codigo: dict[str, str],
    municipios_by_codigo: dict[tuple[str, str], str],
) -> tuple[str | None, str | None, bool]:
    codigo = str(codigo or "").strip()
    candidates: list[tuple[str, str | None]] = []
    if len(codigo) >= 4:
        candidates.append((codigo[:2], codigo[2:4]))
    if codigo.startswith("98") and len(codigo) >= 6:
        candidates.insert(0, (codigo[2:4], codigo[4:6]))
    for estado_codigo, municipio_codigo in candidates:
        estado = estados_by_codigo.get(estado_codigo)
        if estado:
            municipio = municipios_by_codigo.get((estado_codigo, municipio_codigo or ""))
            return estado, municipio, True
    return None, None, False


def _uso_recomendado(row: dict[str, Any]) -> tuple[str, int]:
    if row.get("score") is None:
        return "sin_score", 0
    if row.get("semaforo") == "D":
        return "no_ancla", 1
    if not row.get("tiene_2024"):
        return "condicional_sin_2024", 2
    if row.get("semaforo") == "C" or row.get("ruptura_2024"):
        return "condicional", 3
    if (
        row.get("semaforo") == "A"
        and float(row.get("n_eff") or 0.0) >= MIN_STRONG_N_EFF
        and float(row.get("score") or 0.0) >= 70.0
        and row.get("desvio_pp") is not None
        and float(row.get("desvio_pp") or 0.0) <= 8.0
        and row.get("estabilidad_relativa_pp") is not None
        and float(row.get("estabilidad_relativa_pp") or 0.0) <= 6.0
    ):
        return "ancla", 4
    return "condicional", 3


def _semaforo(confianza: float) -> str:
    if confianza >= 0.75:
        return "A"
    if confianza >= 0.55:
        return "B"
    if confianza >= 0.30:
        return "C"
    return "D"


def _clasificar(row: dict[str, Any], histories: list[dict[str, Any]], p90_electores: int) -> str:
    if not histories:
        return "sin_historico"
    latest = histories[0]
    latest_gap = latest["brecha"]
    gaps = [h["brecha"] for h in histories]
    estabilidad_relativa = row.get("estabilidad_relativa_pp")
    n_eff = float(row.get("n_eff") or 0.0)

    # Bastion is about the center's own persistent political gap, not about
    # how far it deviates from the national result in changing elections.
    min_persistent = 2 if len(gaps) >= 2 else 1
    if latest_gap >= 30 and sum(1 for gap in gaps if gap >= 30) >= min_persistent:
        return "bastion_rojo"
    if latest_gap <= -30 and sum(1 for gap in gaps if gap <= -30) >= min_persistent:
        return "bastion_azul"

    if (
        n_eff >= 2.0
        and row["desvio_pp"] is not None
        and row["desvio_pp"] <= 5
        and (estabilidad_relativa or 0) <= 6
    ):
        return "representativo"
    if (n_eff >= MIN_STRONG_N_EFF and estabilidad_relativa is not None and estabilidad_relativa > 12) or row.get("ruptura_2024"):
        return "cambiante"
    if abs(latest_gap) <= 10:
        return "bisagra"
    if int(row.get("num_electores") or 0) >= p90_electores and p90_electores > 0:
        return "volumen"
    return "estandar"



# ---------------------------------------------------------------------------
# Guard de trabajo idempotente por BD
# ---------------------------------------------------------------------------
# ensure_muestra_lab_tables y seed_default_historical_metadata solo escriben la
# primera vez, pero construir_laboratorio las invocaba en cada GET /muestra.
# Eso convertia una ruta de lectura en escritora: tomaba el lock y, mientras el
# seed de arranque tenia la BD, moria con "database is locked". Se cachea por
# ruta de fichero de la BD (no un booleano) porque los tests intercambian la BD
# dentro del mismo proceso.
_BOOTSTRAP_HECHO: set = set()


def _db_key(conn) -> str:
    try:
        for _, nombre, fichero in conn.execute("PRAGMA database_list"):
            if nombre == "main":
                return fichero or "<memoria>"
    except sqlite3.Error:
        pass
    return "<desconocida>"


def _bootstrap_una_vez(conn) -> None:
    clave = _db_key(conn)
    if clave in _BOOTSTRAP_HECHO:
        return
    ensure_muestra_lab_tables(conn)
    seed_default_historical_metadata(conn)
    _BOOTSTRAP_HECHO.add(clave)


def construir_laboratorio(
    conn,
    eleccion: dict[str, Any] | None,
    q: str = "",
    estado: str = "",
    municipio: str = "",
    parroquia: str = "",
    estatus: str = "",
    clasificacion: str = "",
    limit: int = 300,
    offset: int = 0,
) -> dict[str, Any]:
    """Devuelve datos para la pantalla laboratorio de muestra."""
    _bootstrap_una_vez(conn)

    ref_totals = {
        r["eleccion_ref"]: _row_dict(r)
        for r in conn.execute("""
            SELECT eleccion_ref,
                   SUM(votos_validos) AS validos,
                   SUM(votos_gobierno) AS gobierno,
                   SUM(votos_oposicion) AS oposicion
            FROM resultados_historicos
            GROUP BY eleccion_ref
        """).fetchall()
    }
    ref_gap = {}
    for ref, total in ref_totals.items():
        validos = total.get("validos") or 0
        if validos:
            ref_gap[ref] = 100.0 * (total["gobierno"] - total["oposicion"]) / validos

    meta = {
        r["eleccion_ref"]: _row_dict(r)
        for r in conn.execute("SELECT * FROM historico_fuentes").fetchall()
    }
    ordered_refs = sorted(ref_totals.keys(), key=lambda ref: (_year(ref), ref), reverse=True)
    ref_rank = {ref: idx for idx, ref in enumerate(ordered_refs)}

    histories_by_center: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in conn.execute("""
        SELECT rh.*, hf.fuente, hf.granularidad, hf.cobertura_pct, hf.comparabilidad
        FROM resultados_historicos rh
        LEFT JOIN historico_fuentes hf ON hf.eleccion_ref = rh.eleccion_ref
        ORDER BY rh.eleccion_ref DESC
    """).fetchall():
        h = _row_dict(r)
        h["brecha"] = _gap(h.get("pct_gobierno"), h.get("pct_oposicion"))
        h["brecha_ref"] = ref_gap.get(h["eleccion_ref"])
        h["desvio"] = abs(h["brecha"] - h["brecha_ref"]) if h["brecha_ref"] is not None else None
        h["recency_weight"] = RECENCY_DECAY ** ref_rank.get(h.get("eleccion_ref", ""), 0)
        h["confianza_dato"] = _confidence(h, ref_rank)
        histories_by_center[h["codigo_centro"]].append(h)

    active_current: set[str] = set()
    has_ec = False
    if eleccion:
        has_ec = bool(conn.execute(
            "SELECT COUNT(*) c FROM sqlite_master WHERE type='table' AND name='election_centers'"
        ).fetchone()["c"])
        if has_ec:
            rows = conn.execute(
                "SELECT centro_id FROM election_centers WHERE eleccion_id=? AND eligible=1",
                (eleccion["id"],),
            ).fetchall()
            active_current = {r["centro_id"] for r in rows}

    centers: dict[str, dict[str, Any]] = {}
    for r in conn.execute("""
        SELECT c.codigo_cne, c.nombre, c.num_electores, c.num_mesas, c.activo,
               c.lat, c.lon, c.radio_m,
               e.nombre AS estado, mu.nombre AS municipio, p.nombre AS parroquia
        FROM centros c
        JOIN estados e ON e.id = c.id_estado
        LEFT JOIN municipios mu ON mu.id = c.id_municipio
        LEFT JOIN parroquias p ON p.id = c.id_parroquia
    """).fetchall():
        c = _row_dict(r)
        codigo = c["codigo_cne"]
        activo_actual = bool(c.get("activo")) or (eleccion and has_ec and codigo in active_current)
        c["estatus"] = "activo" if activo_actual else "incierto"
        c["tiene_gps"] = c.get("lat") is not None and c.get("lon") is not None
        c["geocerca_radio_m"] = int(c.get("radio_m") or 300)
        _apply_estado_display(c)
        centers[codigo] = c

    estados_by_codigo, estado_ids_by_codigo = _estado_maps(conn)
    municipios_by_codigo = _municipios_by_codigo(conn, estado_ids_by_codigo)
    for codigo in histories_by_center:
        if codigo not in centers:
            snap = conn.execute("""
                SELECT nombre_centro, num_electores, num_mesas
                FROM centro_snapshot
                WHERE codigo_cne=?
                ORDER BY eleccion_ref DESC LIMIT 1
            """, (codigo,)).fetchone()
            codigo_str = str(codigo or "").strip()
            estado_inferido, municipio_inferido, inferred = _infer_geo_from_codigo(
                codigo_str,
                estados_by_codigo,
                municipios_by_codigo,
            )
            centers[codigo] = {
                "codigo_cne": codigo,
                "nombre": snap["nombre_centro"] if snap and snap["nombre_centro"] else "Centro historico sin registro activo",
                "num_electores": snap["num_electores"] if snap else 0,
                "num_mesas": snap["num_mesas"] if snap else 0,
                "activo": 0,
                "estado": estado_inferido,
                "municipio": municipio_inferido,
                "parroquia": None,
                "lat": None,
                "lon": None,
                "radio_m": None,
                "tiene_gps": False,
                "geocerca_radio_m": 300,
                "estatus": "solo_historico",
            }
            _apply_estado_display(centers[codigo], inferred=inferred)

    snapshot_names: dict[str, str] = {}
    for r in conn.execute("""
        SELECT codigo_cne, nombre_centro
        FROM centro_snapshot
        WHERE nombre_centro IS NOT NULL AND TRIM(nombre_centro) != ''
    """).fetchall():
        current = snapshot_names.get(r["codigo_cne"], "")
        candidate = str(r["nombre_centro"] or "").strip()
        if len(candidate) > len(current):
            snapshot_names[r["codigo_cne"]] = candidate

    for codigo, nombre in snapshot_names.items():
        if codigo in centers and len(nombre) > len(str(centers[codigo].get("nombre") or "")):
            centers[codigo]["nombre"] = nombre

    in_sample = set()
    sample_rows = []
    if eleccion:
        sample_rows = conn.execute(
            "SELECT * FROM muestra WHERE id_eleccion=? AND activo=1",
            (eleccion["id"],),
        ).fetchall()
        in_sample = {r["codigo_centro"] for r in sample_rows}

    electores_by_estado: dict[str, list[int]] = defaultdict(list)
    for c in centers.values():
        electores_by_estado[c.get("estado_filtro") or ""].append(int(c.get("num_electores") or 0))
    p90_by_estado = {}
    for edo, vals in electores_by_estado.items():
        vals = sorted(v for v in vals if v > 0)
        idx = int(len(vals) * 0.90) if vals else 0
        p90_by_estado[edo] = vals[min(idx, len(vals) - 1)] if vals else 0
    max_by_estado = {
        edo: max(vals) if vals else 1
        for edo, vals in electores_by_estado.items()
    }

    raw_catalog = []
    stratum_desvios: dict[str, list[tuple[float, float]]] = defaultdict(list)
    stratum_estabilidades: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for codigo, c in centers.items():
        histories = sorted(histories_by_center.get(codigo, []), key=lambda x: x["eleccion_ref"], reverse=True)
        n_hist = len(histories)
        n_eff = sum(float(h.get("recency_weight") or 0.0) for h in histories)
        conf_base = _combined_confidence([h["confianza_dato"] for h in histories])
        conf = conf_base * _sufficiency_factor(n_eff)
        desvio_values = [h["desvio"] for h in histories if h["desvio"] is not None]
        desvio_weights = [float(h.get("recency_weight") or 0.0) for h in histories if h["desvio"] is not None]
        residuales = [
            h["brecha"] - h["brecha_ref"]
            for h in histories
            if h.get("brecha_ref") is not None
        ]
        brechas = [h["brecha"] for h in histories]
        residual_weights = [float(h.get("recency_weight") or 0.0) for h in histories if h.get("brecha_ref") is not None]
        desvio_obs = _weighted_mean(desvio_values, desvio_weights)
        estabilidad_obs = _mad(residuales) if len(residuales) >= 2 else None
        convergencia_pp, convergencia_score = _temporal_convergence(histories)
        c["desvio_obs_pp"] = round(desvio_obs, 2) if desvio_obs is not None else None
        c["estabilidad_obs_pp"] = round(estabilidad_obs, 2) if estabilidad_obs is not None else None
        c["desvio_pp"] = c["desvio_obs_pp"]
        c["estabilidad_pp"] = round(statistics.pstdev(desvio_values), 2) if len(desvio_values) >= 2 else None
        c["estabilidad_relativa_pp"] = c["estabilidad_obs_pp"]
        c["brecha_estabilidad_pp"] = round(statistics.pstdev(brechas), 2) if len(brechas) >= 2 else None
        c["convergencia_pp"] = round(convergencia_pp, 2) if convergencia_pp is not None else None
        c["convergencia_score"] = round(convergencia_score, 3)
        c["n_eff"] = round(n_eff, 2)
        c["tiene_2024"] = any(h.get("eleccion_ref") == "2024-presidencial" for h in histories)
        c["confianza"] = round(conf, 3)
        c["semaforo"] = _semaforo(conf)
        c["n_historicos"] = n_hist
        c["histories"] = histories
        c["en_muestra"] = codigo in in_sample
        c["ruptura_2024"] = False
        residual_2024 = next(
            (h["brecha"] - h["brecha_ref"] for h in histories if h.get("eleccion_ref") == "2024-presidencial" and h.get("brecha_ref") is not None),
            None,
        )
        prev_residuales = [
            h["brecha"] - h["brecha_ref"]
            for h in histories
            if h.get("eleccion_ref") != "2024-presidencial" and h.get("brecha_ref") is not None
        ]
        prev_mean = _weighted_mean(
            prev_residuales,
            [float(h.get("recency_weight") or 0.0) for h in histories if h.get("eleccion_ref") != "2024-presidencial" and h.get("brecha_ref") is not None],
        )
        if residual_2024 is not None and prev_mean is not None:
            c["ruptura_2024"] = abs(residual_2024 - prev_mean) > 8.0

        if c["estatus"] != "solo_historico" and n_hist == 0:
            c["estatus"] = "nuevo"
            c["estatus_display"] = "nuevo"

        stratum = _stratum_key(c)
        if desvio_obs is not None:
            stratum_desvios[stratum].append((desvio_obs, max(0.1, n_eff)))
        if estabilidad_obs is not None:
            stratum_estabilidades[stratum].append((estabilidad_obs, max(0.1, n_eff)))
        raw_catalog.append(c)

    stratum_desvio_prior = {
        key: _weighted_mean([v for v, _ in vals], [w for _, w in vals])
        for key, vals in stratum_desvios.items()
    }
    stratum_estabilidad_prior = {
        key: _weighted_mean([v for v, _ in vals], [w for _, w in vals])
        for key, vals in stratum_estabilidades.items()
    }
    all_desvio_prior = _weighted_mean(
        [v for vals in stratum_desvios.values() for v, _ in vals],
        [w for vals in stratum_desvios.values() for _, w in vals],
    )
    all_estabilidad_prior = _weighted_mean(
        [v for vals in stratum_estabilidades.values() for v, _ in vals],
        [w for vals in stratum_estabilidades.values() for _, w in vals],
    )

    catalog = []
    for c in raw_catalog:
        stratum = _stratum_key(c)
        n_eff = float(c.get("n_eff") or 0.0)
        desvio_shrunk = _shrink(
            c.get("desvio_obs_pp"),
            stratum_desvio_prior.get(stratum, all_desvio_prior),
            n_eff,
        )
        estabilidad_shrunk = _shrink(
            c.get("estabilidad_obs_pp"),
            stratum_estabilidad_prior.get(stratum, all_estabilidad_prior),
            n_eff,
        )
        c["desvio_pp"] = round(desvio_shrunk, 2) if desvio_shrunk is not None else None
        c["estabilidad_relativa_pp"] = round(estabilidad_shrunk, 2) if estabilidad_shrunk is not None else None
        c["clasificacion"] = _clasificar(c, c["histories"], p90_by_estado.get(c.get("estado_filtro") or "", 0))
        c["tipo_legacy"] = _legacy_tipo(c["clasificacion"])

        max_e = max(1, max_by_estado.get(c.get("estado_filtro") or "", 1))
        electores = max(0, int(c.get("num_electores") or 0))
        volumen = math.log(max(2, electores)) / math.log(max(2, max_e)) if electores else 0.0
        r_score = max(0.0, 1.0 - ((c["desvio_pp"] or 15.0) / 15.0)) if c["desvio_pp"] is not None else 0.0
        e_score = max(0.0, 1.0 - ((c["estabilidad_relativa_pp"] or 5.0) / 10.0)) if c["n_historicos"] >= 2 else 0.0
        c["volumen_score"] = round(volumen, 3)
        c["score_componentes"] = {
            "R": round(r_score, 3),
            "E": round(e_score, 3),
            "V": round(volumen, 3),
            "C": round(float(c.get("convergencia_score") or 0.0), 3),
        }
        if c["n_historicos"] == 0 or c["desvio_pp"] is None:
            c["score"] = None
        else:
            raw_score = (
                UTILITY_WEIGHTS["representatividad"] * r_score
                + UTILITY_WEIGHTS["estabilidad"] * e_score
                + UTILITY_WEIGHTS["volumen"] * volumen
            )
            convergence_bonus = CONVERGENCE_BONUS_MAX * float(c.get("convergencia_score") or 0.0)
            c["score"] = round(min(100.0, (100.0 * raw_score) + convergence_bonus), 1)
        c["uso_recomendado"], c["uso_prioridad"] = _uso_recomendado(c)
        catalog.append(c)

    query = (q or "").strip().lower()
    if query:
        catalog = [
            c for c in catalog
            if query in str(c["codigo_cne"]).lower()
            or query in str(c.get("nombre") or "").lower()
            or query in str(c.get("municipio") or "").lower()
            or query in str(c.get("parroquia") or "").lower()
        ]
    if estado:
        catalog = [c for c in catalog if c.get("estado_filtro") == estado]
    if municipio:
        catalog = [c for c in catalog if c.get("municipio") == municipio]
    if parroquia:
        catalog = [c for c in catalog if c.get("parroquia") == parroquia]
    if estatus:
        catalog = [c for c in catalog if c.get("estatus") == estatus]
    if clasificacion:
        catalog = [c for c in catalog if c.get("clasificacion") == clasificacion]

    catalog.sort(key=lambda c: (c["score"] is None, -c.get("uso_prioridad", 0), -(c["score"] or 0), -(c.get("num_electores") or 0)))
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 300
    limit = max(1, min(limit, 1000))
    try:
        offset = int(offset)
    except (TypeError, ValueError):
        offset = 0
    offset = max(0, offset)
    total_filtrados = len(catalog)
    if total_filtrados and offset >= total_filtrados:
        offset = ((total_filtrados - 1) // limit) * limit
    limited = catalog[offset:offset + limit]
    inicio = offset + 1 if total_filtrados else 0
    fin = min(offset + len(limited), total_filtrados)
    paginas = math.ceil(total_filtrados / limit) if total_filtrados else 0
    paginacion = {
        "limit": limit,
        "offset": offset,
        "inicio": inicio,
        "fin": fin,
        "total": total_filtrados,
        "pagina": (offset // limit) + 1 if total_filtrados else 0,
        "paginas": paginas,
        "hay_anterior": offset > 0,
        "hay_siguiente": offset + limit < total_filtrados,
        "offset_anterior": max(0, offset - limit),
        "offset_siguiente": offset + limit,
    }

    sample_codes = {r["codigo_centro"] for r in sample_rows}
    sample_catalog = [c for c in centers.values() if c["codigo_cne"] in sample_codes]
    sample_detail = [c for c in catalog if c["codigo_cne"] in sample_codes]
    if not sample_detail:
        sample_detail = [c for c in limited if c["codigo_cne"] in sample_codes]

    resumen = {
        "universo": len(centers),
        "filtrados": len(catalog),
        "mostrados": len(limited),
        "en_muestra": len(sample_codes),
        "electores_muestra": sum(int(c.get("num_electores") or 0) for c in sample_catalog),
        "estatus": Counter(c["estatus"] for c in centers.values()),
        "uso": Counter(c.get("uso_recomendado") for c in centers.values()),
        "clasificaciones_muestra": Counter(c.get("clasificacion") for c in sample_detail),
        "confianza_muestra": Counter(c.get("semaforo") for c in sample_detail),
    }

    return {
        "centros": limited,
        "resumen": resumen,
        "paginacion": paginacion,
        "refs": sorted(ref_totals.keys(), reverse=True),
        "fuentes": meta,
        "estados": sorted({c.get("estado_filtro") for c in centers.values() if c.get("estado_filtro")}),
        "municipios": sorted({
            c.get("municipio") for c in centers.values()
            if c.get("municipio") and (not estado or c.get("estado_filtro") == estado)
        }),
        "parroquias": sorted({
            c.get("parroquia") for c in centers.values()
            if c.get("parroquia")
            and (not estado or c.get("estado_filtro") == estado)
            and (not municipio or c.get("municipio") == municipio)
        }),
        "clasificaciones": sorted({c.get("clasificacion") for c in centers.values() if c.get("clasificacion")}),
    }


def agregar_centro(conn, id_eleccion: int, codigo_centro: str, motivo: str = "", usuario: str = "local") -> bool:
    ensure_muestra_lab_tables(conn)
    row = conn.execute("SELECT 1 FROM centros WHERE codigo_cne=?", (codigo_centro,)).fetchone()
    if not row:
        return False
    eleccion = conn.execute("SELECT * FROM elecciones WHERE id=?", (id_eleccion,)).fetchone()
    lab = construir_laboratorio(conn, dict(eleccion) if eleccion else None, q=codigo_centro, limit=1)
    centro = next((c for c in lab["centros"] if c["codigo_cne"] == codigo_centro), None)
    tipo = _legacy_tipo(centro["clasificacion"]) if centro else "estandar"
    score = centro.get("score") if centro else None
    confianza = centro.get("confianza") if centro else None
    conn.execute("""
        INSERT INTO muestra
            (id_eleccion, codigo_centro, tipo_centro, activo, motivo,
             agregado_por, score_snapshot, confianza_snapshot)
        VALUES (?, ?, ?, 1, ?, ?, ?, ?)
        ON CONFLICT(id_eleccion, codigo_centro) DO UPDATE SET
            activo=1,
            tipo_centro=excluded.tipo_centro,
            motivo=excluded.motivo,
            agregado_por=excluded.agregado_por,
            score_snapshot=excluded.score_snapshot,
            confianza_snapshot=excluded.confianza_snapshot
    """, (id_eleccion, codigo_centro, tipo, motivo, usuario, score, confianza))
    conn.commit()
    return True
