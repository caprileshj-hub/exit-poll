"""Selector longitudinal experimental de muestra presidencial.

Este modulo no reemplaza el selector productivo. Usa el frame vigente de la
eleccion objetivo y resultados presidenciales historicos normalizados para
ordenar centros grandes que hayan permanecido cerca de su estado.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Iterable

try:
    from selector_muestra import build_frame, frame_hash
except ImportError:  # pragma: no cover - package import path
    from .selector_muestra import build_frame, frame_hash


METHOD = "longitudinal_mae"
ALGORITHM_VERSION = "longitudinal_mae_v1"
SAMPLE_SIZE = 120
BASE_PER_STATE = 2
EXTRAS_DHONDT = 72
TOLERANCE_LADDER_PP = [2, 4, 6, 8, 10, 15, 20, math.inf]
PRESIDENTIAL_STATE_IDS = set(range(1, 25))


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _year_from_ref(eleccion_ref: str) -> int | None:
    prefix = str(eleccion_ref or "").split("-", 1)[0]
    return int(prefix) if prefix.isdigit() else None


def _target_year(conn: sqlite3.Connection, id_eleccion: int) -> int:
    row = conn.execute("SELECT fecha, tipo FROM elecciones WHERE id=?", (id_eleccion,)).fetchone()
    if row is None:
        raise ValueError(f"Eleccion no encontrada: {id_eleccion}")
    fecha = row["fecha"] if isinstance(row, sqlite3.Row) else row[0]
    tipo = row["tipo"] if isinstance(row, sqlite3.Row) else row[1]
    if tipo != "nacional":
        raise ValueError("longitudinal_mae_v1 solo soporta elecciones nacionales presidenciales")
    return int(str(fecha)[:4])


def residual(center_pct: float, state_pct: float) -> float:
    return float(center_pct) - float(state_pct)


def longitudinal_feature_values(residuals: list[float | None]) -> dict[str, float | int | None]:
    values = [float(value) for value in residuals if value is not None]
    if not values:
        return {
            "n_hist": 0,
            "recent_distance": None,
            "historical_mae": None,
            "historical_rmse": None,
            "historical_bias": None,
            "abs_historical_bias": None,
            "historical_volatility": None,
            "selector_score": None,
            "score_source": "no_history",
        }
    bias = mean(values)
    historical_mae = mean(abs(value) for value in values)
    recent_distance = abs(values[-1])
    out = {
        "n_hist": len(values),
        "recent_distance": recent_distance,
        "historical_mae": historical_mae,
        "historical_rmse": math.sqrt(mean(value * value for value in values)),
        "historical_bias": bias,
        "abs_historical_bias": abs(bias),
        "historical_volatility": math.sqrt(mean((value - bias) ** 2 for value in values)) if len(values) >= 2 else None,
    }
    if len(values) >= 2:
        out["selector_score"] = historical_mae
        out["score_source"] = "longitudinal"
    else:
        out["selector_score"] = recent_distance
        out["score_source"] = "recent_fallback"
    return out


def allocate_longitudinal_dhondt_quotas(
    frame: list[dict[str, Any]],
    sample_size: int = SAMPLE_SIZE,
    base_per_state: int = BASE_PER_STATE,
) -> dict[int, int]:
    states: dict[int, dict[str, Any]] = {}
    for row in frame:
        state = int(row["id_estado"])
        bucket = states.setdefault(state, {"weight": 0.0, "estado": row["estado"]})
        bucket["weight"] += float(row.get("num_electores") or 0)
    if not states:
        return {}
    quotas = {state: base_per_state for state in states}
    extras_to_allocate = sample_size - (base_per_state * len(states))
    if extras_to_allocate < 0:
        raise ValueError("El minimo territorial excede el tamano de muestra")
    scores = []
    for state, data in states.items():
        weight = float(data["weight"])
        for divisor in range(1, extras_to_allocate + 1):
            scores.append((weight / divisor, weight, str(data["estado"]), state, divisor))
    for _, _, _, state, _ in sorted(scores, key=lambda item: (-item[0], -item[1], item[2], item[3]))[:extras_to_allocate]:
        quotas[state] += 1
    if sum(quotas.values()) != sample_size:
        raise AssertionError("La cuota longitudinal final no suma el tamano solicitado")
    return dict(sorted(quotas.items()))


def presidential_frame(frame: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in frame if int(row["id_estado"]) in PRESIDENTIAL_STATE_IDS]


def historical_election_refs(conn: sqlite3.Connection, target_year: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT eleccion_ref
        FROM resultados_historicos
        WHERE eleccion_ref LIKE '%-presidencial'
        ORDER BY eleccion_ref
        """
    ).fetchall()
    refs = []
    for row in rows:
        ref = row["eleccion_ref"] if isinstance(row, sqlite3.Row) else row[0]
        year = _year_from_ref(ref)
        if year is not None and year < target_year:
            refs.append(ref)
    return refs


def _pct_gobierno(row: sqlite3.Row) -> float | None:
    pct = row["pct_gobierno"]
    if pct is not None:
        return float(pct)
    validos = float(row["votos_validos"] or 0)
    if validos <= 0:
        return None
    return 100 * float(row["votos_gobierno"] or 0) / validos


def load_presidential_residuals(
    conn: sqlite3.Connection,
    target_year: int,
    frame_codes: set[str],
) -> dict[str, list[tuple[str, float]]]:
    refs = historical_election_refs(conn, target_year)
    if not refs:
        return {}
    placeholders = ",".join("?" for _ in refs)
    rows = conn.execute(
        f"""
        SELECT codigo_centro, eleccion_ref, votos_validos, votos_gobierno, pct_gobierno
        FROM resultados_historicos
        WHERE eleccion_ref IN ({placeholders})
          AND votos_validos > 0
          AND substr(codigo_centro, 1, 2) BETWEEN '01' AND '24'
        """,
        refs,
    ).fetchall()
    by_ref_state: dict[tuple[str, int], dict[str, float]] = defaultdict(lambda: {"gov": 0.0, "valid": 0.0})
    center_rows = []
    for row in rows:
        code = str(row["codigo_centro"])
        state = int(code[:2])
        valid = float(row["votos_validos"] or 0)
        gov = float(row["votos_gobierno"] or 0)
        by_ref_state[(row["eleccion_ref"], state)]["gov"] += gov
        by_ref_state[(row["eleccion_ref"], state)]["valid"] += valid
        if code in frame_codes:
            pct = _pct_gobierno(row)
            if pct is not None:
                center_rows.append((code, row["eleccion_ref"], state, pct))

    state_pct = {
        key: 100 * data["gov"] / data["valid"]
        for key, data in by_ref_state.items()
        if data["valid"] > 0
    }
    by_code: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for code, ref, state, pct in center_rows:
        state_value = state_pct.get((ref, state))
        if state_value is not None:
            by_code[code].append((ref, residual(pct, state_value)))
    return {code: sorted(values, key=lambda item: _year_from_ref(item[0]) or 0) for code, values in by_code.items()}


def historical_data_hash(conn: sqlite3.Connection, target_year: int) -> str:
    refs = historical_election_refs(conn, target_year)
    if not refs:
        return hashlib.sha256(b"[]").hexdigest()
    placeholders = ",".join("?" for _ in refs)
    rows = conn.execute(
        f"""
        SELECT codigo_centro, eleccion_ref, votos_validos, votos_gobierno, pct_gobierno
        FROM resultados_historicos
        WHERE eleccion_ref IN ({placeholders})
        ORDER BY eleccion_ref, codigo_centro
        """,
        refs,
    ).fetchall()
    payload = [
        {
            "codigo_centro": row["codigo_centro"],
            "eleccion_ref": row["eleccion_ref"],
            "votos_validos": row["votos_validos"],
            "votos_gobierno": row["votos_gobierno"],
            "pct_gobierno": row["pct_gobierno"],
        }
        for row in rows
    ]
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def build_longitudinal_features(
    conn: sqlite3.Connection,
    id_eleccion: int,
    frame: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    frame = presidential_frame(frame if frame is not None else build_frame(conn, id_eleccion=id_eleccion))
    target_year = _target_year(conn, id_eleccion)
    frame_codes = {row["codigo_cne"] for row in frame}
    residuals_by_code = load_presidential_residuals(conn, target_year, frame_codes)
    features = []
    for row in frame:
        residual_pairs = residuals_by_code.get(row["codigo_cne"], [])
        residual_values = [value for _, value in residual_pairs]
        computed = longitudinal_feature_values(residual_values)
        feature = {
            **row,
            **computed,
            "historical_elections_used": [ref for ref, _ in residual_pairs],
            "historical_residuals": {ref: value for ref, value in residual_pairs},
            "rank_tamano_estado": None,
        }
        features.append(feature)

    by_state: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in features:
        by_state[int(row["id_estado"])].append(row)
    for rows in by_state.values():
        for rank, row in enumerate(
            sorted(rows, key=lambda item: (-(int(item.get("num_electores") or 0)), item["codigo_cne"])),
            start=1,
        ):
            row["rank_tamano_estado"] = rank
    return sorted(features, key=lambda item: (int(item["id_estado"]), int(item["rank_tamano_estado"])))


def _tolerance_label(value: float) -> str | float:
    return "inf" if math.isinf(value) else value


def select_centers_by_longitudinal_score(
    features: list[dict[str, Any]],
    quotas: dict[int, int],
    excluded: set[str] | None = None,
    role: str = "titular",
) -> list[dict[str, Any]]:
    excluded = excluded or set()
    selected: list[dict[str, Any]] = []
    selected_codes: set[str] = set()
    by_state: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in features:
        if row["codigo_cne"] not in excluded and row.get("selector_score") is not None:
            by_state[int(row["id_estado"])].append(row)

    for state, quota in sorted(quotas.items()):
        picked_for_state = 0
        for pass_number, tolerance in enumerate(TOLERANCE_LADDER_PP, start=1):
            candidates = sorted(
                by_state.get(state, []),
                key=lambda item: (-(int(item.get("num_electores") or 0)), item["codigo_cne"]),
            )
            for row in candidates:
                if picked_for_state >= quota:
                    break
                if row["codigo_cne"] in selected_codes:
                    continue
                if float(row["selector_score"]) <= tolerance:
                    selected.append(
                        {
                            "codigo_cne": row["codigo_cne"],
                            "estado": row["estado"],
                            "id_estado": int(row["id_estado"]),
                            "num_electores": int(row.get("num_electores") or 0),
                            "cuota_estado": int(quota),
                            "selector_score": float(row["selector_score"]),
                            "score_source": row["score_source"],
                            "n_hist": int(row["n_hist"]),
                            "recent_distance": row["recent_distance"],
                            "historical_mae": row["historical_mae"],
                            "historical_rmse": row["historical_rmse"],
                            "historical_bias": row["historical_bias"],
                            "historical_volatility": row["historical_volatility"],
                            "tolerancia_seleccion": _tolerance_label(tolerance),
                            "pasada_seleccion": pass_number,
                            "rank_tamano_estado": int(row["rank_tamano_estado"]),
                            "metodo": METHOD,
                            "algorithm_version": ALGORITHM_VERSION,
                            "historical_elections_used": list(row["historical_elections_used"]),
                            "rol_muestra": role,
                        }
                    )
                    selected_codes.add(row["codigo_cne"])
                    picked_for_state += 1
            if picked_for_state >= quota:
                break
    return selected


def coverage_by_history(features: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = {"n_hist_0": 0, "n_hist_1": 0, "n_hist_ge_2": 0}
    for row in features:
        n_hist = int(row.get("n_hist") or 0)
        if n_hist == 0:
            counts["n_hist_0"] += 1
        elif n_hist == 1:
            counts["n_hist_1"] += 1
        else:
            counts["n_hist_ge_2"] += 1
    return counts


def generar_muestra_longitudinal(
    conn: sqlite3.Connection,
    id_eleccion: int,
    sample_size: int = SAMPLE_SIZE,
    reserve_size: int = 0,
) -> dict[str, Any]:
    target_year = _target_year(conn, id_eleccion)
    frame = presidential_frame(build_frame(conn, id_eleccion=id_eleccion))
    quotas = allocate_longitudinal_dhondt_quotas(frame, sample_size=sample_size)
    features = build_longitudinal_features(conn, id_eleccion, frame=frame)
    titulares = select_centers_by_longitudinal_score(features, quotas, role="titular")
    titular_codes = {row["codigo_cne"] for row in titulares}
    reservas = []
    if reserve_size > 0:
        reserve_quotas = allocate_longitudinal_dhondt_quotas(
            [row for row in frame if row["codigo_cne"] not in titular_codes],
            sample_size=reserve_size,
        )
        reservas = select_centers_by_longitudinal_score(
            features,
            reserve_quotas,
            excluded=titular_codes,
            role="reserva",
        )
    else:
        reserve_quotas = {}

    return {
        "id_eleccion": id_eleccion,
        "method": METHOD,
        "metodo": METHOD,
        "algorithm_version": ALGORITHM_VERSION,
        "target_year": target_year,
        "sample_size": sample_size,
        "reserve_size": reserve_size,
        "cuotas": quotas,
        "cuotas_reserva": reserve_quotas,
        "frame_hash": frame_hash(frame),
        "historical_data_hash": historical_data_hash(conn, target_year),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "frame_count": len(frame),
        "frame_electores": sum(int(row.get("num_electores") or 0) for row in frame),
        "history_coverage": coverage_by_history(features),
        "titulares": titulares,
        "reservas": reservas,
        "features": features,
    }
