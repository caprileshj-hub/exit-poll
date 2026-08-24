"""Backtesting historico read-only para seleccion de centros.

Este modulo mide error de seleccion: primero arma un frame sin resultados del
target, luego abre los resultados objetivo solo para evaluar.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable


DEFAULT_TARGET_REFS = ("2012-presidencial", "2013-presidencial", "2018-presidencial")
DEFAULT_SAMPLE_SIZE = 180
DEFAULT_RANDOM_SEEDS = tuple(range(100))


def _year(ref: str) -> int:
    try:
        return int(str(ref)[:4])
    except (TypeError, ValueError):
        return 0


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _gap(row: dict[str, Any]) -> float | None:
    if row.get("pct_gobierno") is None or row.get("pct_oposicion") is None:
        return None
    return float(row["pct_gobierno"]) - float(row["pct_oposicion"])


def _weighted_mean(values: Iterable[tuple[float, float]]) -> float | None:
    pairs = [(float(v), float(w)) for v, w in values if v is not None and w is not None and w > 0]
    if not pairs:
        return None
    total_weight = sum(w for _, w in pairs)
    if total_weight <= 0:
        return None
    return sum(v * w for v, w in pairs) / total_weight


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * pct
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def available_refs(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT eleccion_ref FROM resultados_historicos ORDER BY eleccion_ref"
    ).fetchall()
    return [r["eleccion_ref"] for r in rows]


def training_refs_before(conn: sqlite3.Connection, target_ref: str) -> list[str]:
    target_year = _year(target_ref)
    refs = []
    for ref in available_refs(conn):
        ref_year = _year(ref)
        if ref != target_ref and ref_year and target_year and ref_year < target_year:
            refs.append(ref)
    return refs


def build_historical_frame(conn: sqlite3.Connection, target_ref: str) -> list[dict[str, Any]]:
    """Devuelve el universo elegible del target sin columnas de resultado objetivo."""
    rows = conn.execute(
        """
        SELECT
            cs.codigo_cne AS codigo_centro,
            COALESCE(cs.nombre_centro, c.nombre) AS nombre_centro,
            e.id AS state_id,
            e.nombre AS state,
            COALESCE(NULLIF(cs.num_electores, 0), NULLIF(c.num_electores, 0), 1) AS electores,
            COALESCE(NULLIF(cs.num_mesas, 0), NULLIF(c.num_mesas, 0), 0) AS mesas
        FROM centro_snapshot cs
        JOIN centros c ON c.codigo_cne = cs.codigo_cne
        JOIN estados e ON e.id = c.id_estado
        WHERE cs.eleccion_ref = ?
          AND COALESCE(NULLIF(cs.num_electores, 0), NULLIF(c.num_electores, 0), 0) > 0
        ORDER BY e.nombre, cs.codigo_cne
        """,
        (target_ref,),
    ).fetchall()
    return [_row_dict(r) for r in rows]


def build_training_history(
    conn: sqlite3.Connection, training_refs: list[str], frame: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Calcula residuales historicos por centro contra su estado."""
    if not training_refs or not frame:
        return {}

    frame_by_code = {r["codigo_centro"]: r for r in frame}
    codes = set(frame_by_code)
    placeholders = ",".join("?" for _ in training_refs)
    rows = conn.execute(
        f"""
        SELECT
            rh.codigo_centro,
            rh.eleccion_ref,
            rh.pct_gobierno,
            rh.pct_oposicion,
            COALESCE(NULLIF(rh.votos_validos, 0), NULLIF(rh.electores_inscritos, 0), 1) AS weight
        FROM resultados_historicos rh
        WHERE rh.eleccion_ref IN ({placeholders})
          AND rh.pct_gobierno IS NOT NULL
          AND rh.pct_oposicion IS NOT NULL
        """,
        tuple(training_refs),
    ).fetchall()

    by_ref_state: dict[tuple[str, Any], list[tuple[float, float]]] = defaultdict(list)
    center_rows: list[dict[str, Any]] = []
    for row in rows:
        item = _row_dict(row)
        frame_row = frame_by_code.get(item["codigo_centro"])
        if not frame_row:
            continue
        gap = _gap(item)
        if gap is None:
            continue
        item["gap"] = gap
        item["state_id"] = frame_row["state_id"]
        center_rows.append(item)
        by_ref_state[(item["eleccion_ref"], item["state_id"])].append((gap, item["weight"] or 1))

    state_gap = {key: _weighted_mean(values) for key, values in by_ref_state.items()}
    residuals: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in center_rows:
        baseline = state_gap.get((item["eleccion_ref"], item["state_id"]))
        if baseline is None:
            continue
        residuals[item["codigo_centro"]].append(
            {
                "eleccion_ref": item["eleccion_ref"],
                "residual": item["gap"] - baseline,
            }
        )

    history = {}
    for code, values in residuals.items():
        n = len(values)
        if n <= 1:
            history[code] = {
                "n": n,
                "rmse": None,
                "score": None,
                "evidencia_limitada": False,
                "residuals": values,
            }
            continue
        rmse = math.sqrt(mean(v["residual"] ** 2 for v in values))
        history[code] = {
            "n": n,
            "rmse": rmse,
            "score": max(0.0, 100.0 - 5.0 * rmse),
            "evidencia_limitada": n == 2,
            "residuals": values,
        }
    return history


def allocate_state_quotas(frame: list[dict[str, Any]], sample_size: int) -> dict[Any, int]:
    """Cuotas proporcionales a electores: piso, minimo 1 si alcanza, remanente por fraccion."""
    states: dict[Any, dict[str, Any]] = {}
    for row in frame:
        state = row["state_id"]
        bucket = states.setdefault(state, {"weight": 0.0, "capacity": 0, "state": row["state"]})
        bucket["weight"] += float(row.get("electores") or 1)
        bucket["capacity"] += 1

    if not states or sample_size <= 0:
        return {}

    requested = min(sample_size, len(frame))
    total_weight = sum(v["weight"] for v in states.values()) or float(len(frame))
    quotas = {}
    fractions = []
    for state, data in states.items():
        exact = requested * data["weight"] / total_weight
        quota = math.floor(exact)
        if requested >= len(states):
            quota = max(1, quota)
        quota = min(quota, data["capacity"])
        quotas[state] = quota
        fractions.append((exact - math.floor(exact), data["weight"], str(data["state"]), state))

    while sum(quotas.values()) > requested:
        candidates = [
            (quotas[state], frac, weight, name, state)
            for frac, weight, name, state in fractions
            if quotas[state] > (1 if requested >= len(states) else 0)
        ]
        _, _, _, _, state = sorted(candidates, key=lambda x: (-x[0], x[1], x[3]))[0]
        quotas[state] -= 1

    while sum(quotas.values()) < requested:
        candidates = [
            (frac, weight, name, state)
            for frac, weight, name, state in fractions
            if quotas[state] < states[state]["capacity"]
        ]
        if not candidates:
            break
        _, _, _, state = sorted(candidates, key=lambda x: (-x[0], -x[1], x[2]))[0]
        quotas[state] += 1

    return quotas


def select_stratified_random(
    frame: list[dict[str, Any]], sample_size: int = DEFAULT_SAMPLE_SIZE, seed: int = 2026
) -> dict[str, Any]:
    quotas = allocate_state_quotas(frame, sample_size)
    rng = random.Random(seed)
    by_state: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in frame:
        by_state[row["state_id"]].append(row)

    selected = []
    for state, quota in sorted(quotas.items(), key=lambda kv: str(kv[0])):
        population = sorted(by_state[state], key=lambda r: r["codigo_centro"])
        picked = rng.sample(population, min(quota, len(population)))
        for row in sorted(picked, key=lambda r: r["codigo_centro"]):
            selected.append({**row, "selection_reason": "stratified_random"})

    return {
        "strategy": "stratified_random",
        "sample_size_requested": sample_size,
        "sample_size_actual": len(selected),
        "seed": seed,
        "quotas": quotas,
        "selected": selected,
    }


def select_historical_rmse(
    frame: list[dict[str, Any]],
    history: dict[str, dict[str, Any]],
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = 2026,
) -> dict[str, Any]:
    quotas = allocate_state_quotas(frame, sample_size)
    rng = random.Random(seed)
    by_state: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in frame:
        by_state[row["state_id"]].append(row)

    selected = []
    for state, quota in sorted(quotas.items(), key=lambda kv: str(kv[0])):
        population = by_state[state]
        ranked = []
        fallback = []
        for row in population:
            h = history.get(row["codigo_centro"], {"n": 0, "rmse": None, "score": None})
            enriched = {**row, **{f"historical_{k}": v for k, v in h.items() if k != "residuals"}}
            if h.get("rmse") is None:
                fallback.append(enriched)
            else:
                ranked.append(enriched)
        ranked.sort(
            key=lambda r: (
                r["historical_rmse"],
                r["historical_n"] == 2,
                -float(r.get("electores") or 0),
                r["codigo_centro"],
            )
        )
        chosen = []
        for row in ranked[:quota]:
            reason = "historical_rmse_limited" if row.get("historical_evidencia_limitada") else "historical_rmse"
            chosen.append({**row, "selection_reason": reason})
        if len(chosen) < quota:
            remaining_codes = {r["codigo_centro"] for r in chosen}
            remaining = [r for r in ranked[quota:] + fallback if r["codigo_centro"] not in remaining_codes]
            remaining.sort(key=lambda r: r["codigo_centro"])
            rng.shuffle(remaining)
            for row in remaining[: quota - len(chosen)]:
                chosen.append({**row, "selection_reason": "fallback_no_sufficient_history"})
        selected.extend(sorted(chosen, key=lambda r: (r["state"], r["codigo_centro"])))

    return {
        "strategy": "historical_rmse_state",
        "sample_size_requested": sample_size,
        "sample_size_actual": len(selected),
        "seed": seed,
        "quotas": quotas,
        "selected": selected,
    }


def load_target_results(conn: sqlite3.Connection, target_ref: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT codigo_centro, pct_gobierno, pct_oposicion, votos_validos
        FROM resultados_historicos
        WHERE eleccion_ref = ?
          AND pct_gobierno IS NOT NULL
          AND pct_oposicion IS NOT NULL
        """,
        (target_ref,),
    ).fetchall()
    return {r["codigo_centro"]: _row_dict(r) for r in rows}


def estimate_from_selected_centers(
    frame: list[dict[str, Any]], selected: list[dict[str, Any]], target_results: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    frame_by_code = {r["codigo_centro"]: r for r in frame}
    selected_codes = {r["codigo_centro"] for r in selected}
    by_state_frame: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    by_state_selected: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in frame:
        by_state_frame[row["state_id"]].append(row)
        if row["codigo_centro"] in selected_codes:
            by_state_selected[row["state_id"]].append(row)

    state_rows = []
    for state_id, rows in by_state_frame.items():
        state_name = rows[0]["state"]
        actual_values = []
        for row in rows:
            result = target_results.get(row["codigo_centro"])
            if result:
                gap = _gap(result)
                if gap is not None:
                    actual_values.append((gap, row.get("electores") or 1))
        selected_values = []
        for row in by_state_selected.get(state_id, []):
            result = target_results.get(row["codigo_centro"])
            if result:
                gap = _gap(result)
                if gap is not None:
                    selected_values.append((gap, row.get("electores") or 1))
        actual = _weighted_mean(actual_values)
        estimated = _weighted_mean(selected_values)
        state_rows.append(
            {
                "state_id": state_id,
                "state": state_name,
                "n_frame": len(rows),
                "n_selected": len(by_state_selected.get(state_id, [])),
                "estimated_gap": estimated,
                "actual_gap": actual,
                "absolute_error_pp": abs(estimated - actual) if estimated is not None and actual is not None else None,
                "weight": sum(float(r.get("electores") or 1) for r in rows),
            }
        )

    estimated_national = _weighted_mean(
        (r["estimated_gap"], r["weight"]) for r in state_rows if r["estimated_gap"] is not None
    )
    actual_national = _weighted_mean(
        (r["actual_gap"], r["weight"]) for r in state_rows if r["actual_gap"] is not None
    )
    state_errors = [r["absolute_error_pp"] for r in state_rows if r["absolute_error_pp"] is not None]
    return {
        "label": "selection_only_estimate",
        "estimated_gap": estimated_national,
        "actual_gap": actual_national,
        "absolute_error_pp": (
            abs(estimated_national - actual_national)
            if estimated_national is not None and actual_national is not None
            else None
        ),
        "states": [{k: v for k, v in r.items() if k != "weight"} for r in state_rows],
        "state_MAE_pp": mean(state_errors) if state_errors else None,
        "state_RMSE_pp": math.sqrt(mean(e * e for e in state_errors)) if state_errors else None,
        "max_state_error_pp": max(state_errors) if state_errors else None,
        "n_selected_with_target": sum(1 for code in selected_codes if code in target_results and code in frame_by_code),
    }


def evaluate_backtest(
    conn: sqlite3.Connection,
    target_ref: str,
    strategy: str,
    selected_payload: dict[str, Any],
    frame: list[dict[str, Any]],
    training_refs: list[str],
) -> dict[str, Any]:
    target_results = load_target_results(conn, target_ref)
    estimate = estimate_from_selected_centers(frame, selected_payload["selected"], target_results)
    n_history = 0
    if training_refs:
        frame_codes = {r["codigo_centro"] for r in frame}
        placeholders = ",".join("?" for _ in training_refs)
        history_codes = {
            r["codigo_centro"]
            for r in conn.execute(
                f"""
                SELECT DISTINCT codigo_centro
                FROM resultados_historicos
                WHERE eleccion_ref IN ({placeholders})
                  AND pct_gobierno IS NOT NULL
                  AND pct_oposicion IS NOT NULL
                """,
                tuple(training_refs),
            ).fetchall()
        }
        n_history = len(frame_codes & history_codes)
    return {
        "target_ref": target_ref,
        "strategy": strategy,
        "sample_size_requested": selected_payload["sample_size_requested"],
        "sample_size_actual": selected_payload["sample_size_actual"],
        "seed": selected_payload.get("seed"),
        "training_refs": training_refs,
        "n_states": len({r["state_id"] for r in frame}),
        "n_centers_frame": len(frame),
        "n_centers_with_history": n_history,
        **{k: v for k, v in estimate.items() if k != "states"},
        "states": estimate["states"],
    }


def summarize_random_runs(results: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [r["absolute_error_pp"] for r in results if r.get("absolute_error_pp") is not None]
    return {
        "runs": len(results),
        "mean_absolute_error": mean(errors) if errors else None,
        "median_absolute_error": median(errors) if errors else None,
        "p10": _percentile(errors, 0.10),
        "p90": _percentile(errors, 0.90),
        "best": min(errors) if errors else None,
        "worst": max(errors) if errors else None,
    }


def run_walk_forward(
    conn: sqlite3.Connection,
    target_refs: Iterable[str] = DEFAULT_TARGET_REFS,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    random_seeds: Iterable[int] = DEFAULT_RANDOM_SEEDS,
    historical_seed: int = 2026,
) -> dict[str, Any]:
    output = {"sample_size": sample_size, "targets": []}
    for target_ref in target_refs:
        frame = build_historical_frame(conn, target_ref)
        training_refs = training_refs_before(conn, target_ref)
        if not frame:
            output["targets"].append({"target_ref": target_ref, "status": "SKIPPED", "reason": "sin centro_snapshot/frame"})
            continue
        if not training_refs:
            output["targets"].append({"target_ref": target_ref, "status": "SKIPPED", "reason": "sin elecciones anteriores"})
            continue
        target_results_count = conn.execute(
            "SELECT COUNT(*) FROM resultados_historicos WHERE eleccion_ref=?", (target_ref,)
        ).fetchone()[0]
        if target_results_count == 0:
            output["targets"].append({"target_ref": target_ref, "status": "SKIPPED", "reason": "sin resultados target para evaluacion"})
            continue

        history = build_training_history(conn, training_refs, frame)
        historical_selection = select_historical_rmse(frame, history, sample_size, historical_seed)
        historical_result = evaluate_backtest(
            conn, target_ref, "historical_rmse_state", historical_selection, frame, training_refs
        )

        random_results = []
        for seed in random_seeds:
            selection = select_stratified_random(frame, sample_size, int(seed))
            random_results.append(
                evaluate_backtest(conn, target_ref, "stratified_random", selection, frame, training_refs)
            )

        output["targets"].append(
            {
                "target_ref": target_ref,
                "status": "OK",
                "frame": {"n_centers": len(frame), "n_states": len({r["state_id"] for r in frame})},
                "training_refs": training_refs,
                "historical_rmse_state": historical_result,
                "stratified_random": {
                    "summary": summarize_random_runs(random_results),
                    "runs": random_results,
                },
            }
        )
    return output


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _format_pp(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f} pp"


def print_human_summary(result: dict[str, Any]) -> None:
    for target in result["targets"]:
        print(target["target_ref"])
        if target["status"] != "OK":
            print(f"  SKIPPED: {target['reason']}")
            continue
        print(f"  frame: {target['frame']['n_centers']} centros")
        print(f"  training: {target['training_refs']}")
        hist = target["historical_rmse_state"]
        print("  historical RMSE:")
        print(f"    national error: {_format_pp(hist['absolute_error_pp'])}")
        print(f"    state MAE: {_format_pp(hist['state_MAE_pp'])}")
        rnd = target["stratified_random"]["summary"]
        print(f"  stratified random ({rnd['runs']} runs):")
        print(f"    median national error: {_format_pp(rnd['median_absolute_error'])}")
        print(f"    p10-p90: {_format_pp(rnd['p10'])} - {_format_pp(rnd['p90'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest read-only de seleccion de centros.")
    parser.add_argument("--db", default=str(Path(__file__).with_name("exitpoll.db")))
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--random-runs", type=int, default=100)
    parser.add_argument("--json", action="store_true", help="Imprime JSON completo.")
    args = parser.parse_args()

    conn = _connect_readonly(Path(args.db))
    try:
        result = run_walk_forward(
            conn,
            sample_size=args.sample_size,
            random_seeds=range(args.random_runs),
        )
    finally:
        conn.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
