"""Backtest nacional aislado de la seleccion legacy de centros.

El modulo es deliberadamente file-based y read-only: no consulta la BD ni toca
el selector productivo moderno. La seleccion usa solo frame target + historico
previo; los resultados objetivo se cargan despues para evaluar.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean, median
from typing import Iterable

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent
N_BASE = 120
BASE_PER_STATE = 2
EXTRAS_DHONDT = 72
DEFAULT_TOLERANCE_LADDERS = {
    "baseline": [2, 4, 6, 8, 10, 15, 20, math.inf],
    "estricta": [1, 2, 4, 6, 8, 12, 16, math.inf],
    "amplia": [3, 6, 9, 12, 15, 20, 25, math.inf],
}
DEFAULT_MIN_ELECTORES = [0, 300, 600]
PRIMARY_CONFIG = ("baseline", 300)
STATE_NAMES = {
    "01": "Distrito Capital",
    "02": "Anzoategui",
    "03": "Apure",
    "04": "Aragua",
    "05": "Barinas",
    "06": "Bolivar",
    "07": "Carabobo",
    "08": "Cojedes",
    "09": "Falcon",
    "10": "Guarico",
    "11": "Lara",
    "12": "Merida",
    "13": "Miranda",
    "14": "Monagas",
    "15": "Nueva Esparta",
    "16": "Portuguesa",
    "17": "Sucre",
    "18": "Tachira",
    "19": "Trujillo",
    "20": "Yaracuy",
    "21": "Zulia",
    "22": "Amazonas",
    "23": "Delta Amacuro",
    "24": "La Guaira",
}


@dataclass(frozen=True)
class Transition:
    name: str
    frame_path: Path
    historical_kind: str
    historical_path: Path
    outcome_kind: str
    outcome_path: Path


TRANSITIONS = [
    Transition(
        name="2013_2018",
        frame_path=BASE_DIR / "tm_2018_estandar.csv",
        historical_kind="pres2013_xlsx",
        historical_path=BASE_DIR / "data" / "2013" / "presidenciales" / "resultados oficiales elecciones presidenciales 2013.xlsx",
        outcome_kind="venpres2018_csv",
        outcome_path=BASE_DIR / "data" / "2018" / "resultados_venpres_a_2018.csv",
    ),
    Transition(
        name="2018_2024",
        frame_path=BASE_DIR / "tm_2024_estandar.csv",
        historical_kind="venpres2018_csv",
        historical_path=BASE_DIR / "data" / "2018" / "resultados_venpres_a_2018.csv",
        outcome_kind="cne2024_csv",
        outcome_path=BASE_DIR / "resultados_cne2024.csv",
    ),
]


def code9(value: object) -> str:
    text = str(value or "").strip().split(".")[0]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits.zfill(9) if digits else ""


def state_code_from_center(code: str) -> str:
    return code9(code)[:2]


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _find_column(columns: Iterable[object], *needles: str) -> object:
    for column in columns:
        normalized = (
            str(column)
            .lower()
            .replace("\n", " ")
            .replace("�", "")
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )
        if all(needle.lower() in normalized for needle in needles):
            return column
    raise KeyError(f"No se encontro columna con: {needles}")


@lru_cache(maxsize=None)
def load_frame(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df["codigo_centro"] = df["codigo_centro"].map(code9)
    df["cod_estado"] = df["codigo_centro"].str[:2]
    df["electores"] = _num(df["electores"])
    grouped = (
        df.groupby(["codigo_centro", "cod_estado"], as_index=False)
        .agg(
            nombre_centro=("nombre_centro", "first"),
            estado=("estado", "first"),
            electores=("electores", "sum"),
            mesas=("numero_mesa", "count"),
        )
        .sort_values(["cod_estado", "electores", "codigo_centro"], ascending=[True, False, True])
    )
    grouped["estado"] = grouped["cod_estado"].map(STATE_NAMES).fillna(grouped["estado"])
    grouped["rank_por_tamano"] = grouped.groupby("cod_estado")["electores"].rank(
        method="first", ascending=False
    ).astype(int)
    return grouped.reset_index(drop=True)


@lru_cache(maxsize=None)
def load_venpres_frame_dc(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df["codigo_centro"] = df["codigo_centro"].map(code9)
    df = df[df["codigo_centro"].str.startswith("01")].copy()
    df["cod_estado"] = "01"
    df["electores"] = _num(df["electores_inscritos"])
    df["mesas"] = _num(df["num_mesas"])
    out = df[["codigo_centro", "cod_estado", "nombre_centro", "electores", "mesas"]].copy()
    out["estado"] = STATE_NAMES["01"]
    out = out.sort_values(["electores", "codigo_centro"], ascending=[False, True])
    out["rank_por_tamano"] = range(1, len(out) + 1)
    return out.reset_index(drop=True)


def complete_2018_frame_with_venpres_dc(frame: pd.DataFrame) -> pd.DataFrame:
    if "01" in set(frame["cod_estado"]):
        return frame
    dc = load_venpres_frame_dc(BASE_DIR / "data" / "2018" / "resultados_venpres_a_2018.csv")
    completed = pd.concat([frame, dc], ignore_index=True)
    completed = completed.sort_values(["cod_estado", "electores", "codigo_centro"], ascending=[True, False, True])
    completed["rank_por_tamano"] = completed.groupby("cod_estado")["electores"].rank(
        method="first", ascending=False
    ).astype(int)
    return completed.reset_index(drop=True)


@lru_cache(maxsize=None)
def load_results(kind: str, path: Path) -> pd.DataFrame:
    if kind == "pres2013_xlsx":
        df = pd.read_excel(path, dtype=object)
        code_col = _find_column(df.columns, "codigo", "nuevo")
        valid_col = _find_column(df.columns, "votos", "validos")
        df["codigo_centro"] = df[code_col].map(code9)
        df["cod_estado"] = df["codigo_centro"].str[:2]
        for col in ["maduro", "capriles", "sequera", "bolivar", "mora", "mendez", valid_col]:
            df[col] = _num(df[col])
        df["votos_gobierno"] = df["maduro"]
        df["votos_oposicion"] = df["capriles"]
        df["votos_otros"] = df[["sequera", "bolivar", "mora", "mendez"]].sum(axis=1)
        df["votos_validos"] = df[valid_col]
    elif kind == "venpres2018_csv":
        df = pd.read_csv(path, dtype=str)
        df["codigo_centro"] = df["codigo_centro"].map(code9)
        df["cod_estado"] = df["codigo_centro"].str[:2]
        for col in ["votos_gobierno", "votos_oposicion", "votos_otros", "votos_validos"]:
            df[col] = _num(df[col])
    elif kind == "cne2024_csv":
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        df["codigo_centro"] = df["centro_cne_id"].map(code9)
        df["cod_estado"] = df["codigo_centro"].str[:2]
        for col in ["votos_gobierno", "votos_oposicion", "votos_otros", "votos_validos"]:
            df[col] = _num(df[col])
    else:
        raise ValueError(f"Tipo de resultados no soportado: {kind}")

    out = (
        df[df["codigo_centro"].ne("")]
        .groupby(["codigo_centro", "cod_estado"], as_index=False)
        .agg(
            votos_gobierno=("votos_gobierno", "sum"),
            votos_oposicion=("votos_oposicion", "sum"),
            votos_otros=("votos_otros", "sum"),
            votos_validos=("votos_validos", "sum"),
        )
    )
    out = out[out["votos_validos"] > 0].copy()
    out["pct_maduro"] = 100 * out["votos_gobierno"] / out["votos_validos"]
    return out


def aggregate_pct(rows: pd.DataFrame) -> float | None:
    if rows.empty:
        return None
    validos = float(rows["votos_validos"].sum())
    if validos <= 0:
        return None
    return 100 * float(rows["votos_gobierno"].sum()) / validos


def state_results(results: pd.DataFrame) -> pd.DataFrame:
    by_state = (
        results.groupby("cod_estado", as_index=False)
        .agg(
            votos_gobierno=("votos_gobierno", "sum"),
            votos_oposicion=("votos_oposicion", "sum"),
            votos_otros=("votos_otros", "sum"),
            votos_validos=("votos_validos", "sum"),
            centros_con_resultado=("codigo_centro", "nunique"),
        )
    )
    by_state["pct_maduro"] = 100 * by_state["votos_gobierno"] / by_state["votos_validos"]
    by_state["estado"] = by_state["cod_estado"].map(STATE_NAMES)
    return by_state


def allocate_dhondt_quotas(frame: pd.DataFrame) -> dict[str, int]:
    electors = frame.groupby("cod_estado")["electores"].sum().to_dict()
    states = sorted(electors)
    quotas = {state: BASE_PER_STATE for state in states}
    extras_to_allocate = N_BASE - (BASE_PER_STATE * len(states))
    if extras_to_allocate < 0:
        raise AssertionError("El minimo territorial excede el tamano base")
    scores = []
    for state, weight in electors.items():
        for divisor in range(1, extras_to_allocate + 1):
            scores.append((float(weight) / divisor, float(weight), state, divisor))
    for _, _, state, _ in sorted(scores, key=lambda x: (-x[0], -x[1], x[2]))[:extras_to_allocate]:
        quotas[state] += 1
    if sum(quotas.values()) != N_BASE:
        raise AssertionError("La cuota final fija + D'Hondt no suma 120")
    return quotas


def select_legacy(
    frame: pd.DataFrame,
    historical: pd.DataFrame,
    quotas: dict[str, int],
    tolerance_ladder_pp: list[float],
    min_electores: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    state_hist = state_results(historical).set_index("cod_estado")
    selected = []
    incomplete = []

    hist_pct = historical[["codigo_centro", "pct_maduro"]].rename(columns={"pct_maduro": "hist_pct_maduro_centro"})
    eligible = frame.merge(hist_pct, on="codigo_centro", how="inner")
    eligible = eligible[eligible["electores"] >= min_electores].copy()
    state_targets = state_hist["pct_maduro"].to_dict()
    eligible["hist_pct_maduro_estado"] = eligible["cod_estado"].map(state_targets)
    eligible["hist_diff_abs_pp"] = (
        eligible["hist_pct_maduro_centro"].astype(float) - eligible["hist_pct_maduro_estado"].astype(float)
    ).abs()

    def entry_pass(diff: float) -> int | None:
        for idx, tolerance in enumerate(tolerance_ladder_pp, start=1):
            if diff <= tolerance:
                return idx
        return None

    def entry_tolerance(diff: float) -> str | float | None:
        for tolerance in tolerance_ladder_pp:
            if diff <= tolerance:
                return "inf" if math.isinf(tolerance) else tolerance
        return None

    eligible["pasada"] = eligible["hist_diff_abs_pp"].map(entry_pass)
    eligible["tolerancia_de_entrada"] = eligible["hist_diff_abs_pp"].map(entry_tolerance)
    eligible = eligible.dropna(subset=["pasada"]).copy()
    eligible["pasada"] = eligible["pasada"].astype(int)

    for state, quota in sorted(quotas.items()):
        chosen = (
            eligible[eligible["cod_estado"].eq(state)]
            .sort_values(["pasada", "electores", "codigo_centro"], ascending=[True, False, True])
            .head(quota)
            .copy()
        )
        if not chosen.empty:
            chosen["metodo"] = "legacy"
            selected.extend(chosen.to_dict("records"))
        if len(chosen) < quota:
            incomplete.append(
                {
                    "cod_estado": state,
                    "estado": STATE_NAMES.get(state, state),
                    "cuota": quota,
                    "seleccionados": len(chosen),
                    "faltantes": quota - len(chosen),
                }
            )
    return pd.DataFrame(selected), pd.DataFrame(incomplete)


def select_size_only(frame: pd.DataFrame, historical: pd.DataFrame, quotas: dict[str, int]) -> pd.DataFrame:
    eligible = frame[frame["codigo_centro"].isin(set(historical["codigo_centro"]))].copy()
    selected = []
    ordered = eligible.sort_values(["cod_estado", "electores", "codigo_centro"], ascending=[True, False, True])
    for state, group in ordered.groupby("cod_estado"):
        quota = quotas.get(state, 0)
        for row in group.head(quota).to_dict("records"):
            selected.append({**row, "metodo": "size_only", "pasada": "", "tolerancia_de_entrada": ""})
    return pd.DataFrame(selected)


def _err(sample_pct: float | None, state_pct: float | None) -> float | None:
    if sample_pct is None or state_pct is None:
        return None
    return sample_pct - state_pct


def evaluate_selection(
    transition: str,
    method: str,
    frame: pd.DataFrame,
    selected: pd.DataFrame,
    historical: pd.DataFrame,
    outcome: pd.DataFrame,
    quotas: dict[str, int],
    ladder_name: str,
    min_electores: int,
) -> pd.DataFrame:
    hist_state = state_results(historical).set_index("cod_estado")
    out_state = state_results(outcome).set_index("cod_estado")
    rows = []
    frame_counts = frame.groupby("cod_estado")["codigo_centro"].nunique().to_dict()
    frame_electors = frame.groupby("cod_estado")["electores"].sum().to_dict()
    frame_by_state = {
        state: set(group["codigo_centro"])
        for state, group in frame.groupby("cod_estado")
    }
    selected_by_state = {
        state: list(group["codigo_centro"])
        for state, group in selected.groupby("cod_estado")
    } if not selected.empty else {}
    hist_codes = set(historical["codigo_centro"])
    out_codes = set(outcome["codigo_centro"])
    hist_by_code = {
        row["codigo_centro"]: (
            float(row["votos_gobierno"]),
            float(row["votos_validos"]),
        )
        for row in historical.to_dict("records")
    }
    out_by_code = {
        row["codigo_centro"]: (
            float(row["votos_gobierno"]),
            float(row["votos_validos"]),
        )
        for row in outcome.to_dict("records")
    }

    def pct_for_codes(source: dict[str, tuple[float, float]], codes: Iterable[str]) -> float | None:
        gov = 0.0
        valid = 0.0
        for code in codes:
            values = source.get(code)
            if values is None:
                continue
            gov += values[0]
            valid += values[1]
        if valid <= 0:
            return None
        return 100 * gov / valid

    for state, quota in sorted(quotas.items()):
        frame_codes_state = frame_by_state.get(state, set())
        sel_codes = selected_by_state.get(state, [])
        hist_sel_codes = [code for code in sel_codes if code in hist_by_code]
        out_sel_codes = [code for code in sel_codes if code in out_by_code]
        comparable_codes = [code for code in sel_codes if code in hist_by_code and code in out_by_code]

        estado_hist = float(hist_state.loc[state, "pct_maduro"]) if state in hist_state.index else None
        estado_out = float(out_state.loc[state, "pct_maduro"]) if state in out_state.index else None
        muestra_hist = pct_for_codes(hist_by_code, hist_sel_codes)
        muestra_hist_comp = pct_for_codes(hist_by_code, comparable_codes)
        muestra_out = pct_for_codes(out_by_code, out_sel_codes)
        swing_estado = _err(estado_out, estado_hist)
        swing_muestra = _err(muestra_out, muestra_hist_comp)

        rows.append(
            {
                "transicion": transition,
                "metodo": method,
                "tolerance_ladder": ladder_name,
                "min_electores": min_electores,
                "cod_estado": state,
                "estado": STATE_NAMES.get(state, state),
                "cuota": quota,
                "n_frame": int(frame_counts.get(state, 0)),
                "n_con_historico_frame": int(len(frame_codes_state & hist_codes)),
                "n_con_outcome_frame": int(len(frame_codes_state & out_codes)),
                "n_seleccionados": int(len(sel_codes)),
                "n_con_outcome": int(len(out_sel_codes)),
                "pct_cobertura_muestra": round(100 * len(out_sel_codes) / len(sel_codes), 6) if sel_codes else None,
                "pct_cobertura_frame_outcome": round(100 * len(frame_codes_state & out_codes) / frame_counts.get(state, 1), 6),
                "pct_maduro_estado_hist": estado_hist,
                "pct_maduro_muestra_hist": muestra_hist,
                "error_hist_pp": _err(muestra_hist, estado_hist),
                "pct_maduro_muestra_hist_comparable": muestra_hist_comp,
                "pct_maduro_estado_outcome": estado_out,
                "pct_maduro_muestra_outcome": muestra_out,
                "error_outcome_pp": _err(muestra_out, estado_out),
                "swing_estado": swing_estado,
                "swing_muestra": swing_muestra,
                "swing_error_pp": _err(swing_muestra, swing_estado),
                "electores_estado": float(frame_electors.get(state, 0.0)),
            }
        )
    return pd.DataFrame(rows)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    pos = (len(values) - 1) * pct
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def national_metrics(states: pd.DataFrame) -> dict[str, float | int | str | None]:
    valid = states.dropna(subset=["error_outcome_pp"]).copy()
    swing_valid = states.dropna(subset=["swing_error_pp"]).copy()
    errors = [float(x) for x in valid["error_outcome_pp"]]
    abs_errors = [abs(x) for x in errors]
    swing_errors = [float(x) for x in swing_valid["swing_error_pp"]]
    weights = valid["electores_estado"].astype(float).tolist()
    total_weight = sum(weights)

    def weighted_abs(column: str) -> float | None:
        rows = states.dropna(subset=[column])
        denom = float(rows["electores_estado"].sum())
        if denom <= 0:
            return None
        return float((rows[column].abs() * rows["electores_estado"]).sum() / denom)

    def weighted_rmse(column: str) -> float | None:
        rows = states.dropna(subset=[column])
        denom = float(rows["electores_estado"].sum())
        if denom <= 0:
            return None
        return math.sqrt(float(((rows[column] ** 2) * rows["electores_estado"]).sum() / denom))

    return {
        "transicion": states.iloc[0]["transicion"] if not states.empty else "",
        "metodo": states.iloc[0]["metodo"] if not states.empty else "",
        "tolerance_ladder": states.iloc[0]["tolerance_ladder"] if not states.empty else "",
        "min_electores": int(states.iloc[0]["min_electores"]) if not states.empty else None,
        "estados_evaluados": len(valid),
        "mae_error_outcome_pp": mean(abs_errors) if abs_errors else None,
        "rmse_error_outcome_pp": math.sqrt(mean([e * e for e in errors])) if errors else None,
        "mediana_abs_error_outcome_pp": median(abs_errors) if abs_errors else None,
        "p90_abs_error_outcome_pp": percentile(abs_errors, 0.90),
        "mae_swing_error_pp": mean([abs(x) for x in swing_errors]) if swing_errors else None,
        "rmse_swing_error_pp": math.sqrt(mean([x * x for x in swing_errors])) if swing_errors else None,
        "prop_dentro_2pp": sum(1 for x in abs_errors if x <= 2) / len(abs_errors) if abs_errors else None,
        "prop_dentro_5pp": sum(1 for x in abs_errors if x <= 5) / len(abs_errors) if abs_errors else None,
        "prop_dentro_10pp": sum(1 for x in abs_errors if x <= 10) / len(abs_errors) if abs_errors else None,
        "mae_ponderado_electores_pp": weighted_abs("error_outcome_pp"),
        "rmse_ponderado_electores_pp": weighted_rmse("error_outcome_pp"),
        "mae_swing_ponderado_electores_pp": weighted_abs("swing_error_pp"),
        "rmse_swing_ponderado_electores_pp": weighted_rmse("swing_error_pp"),
        "electores_evaluados": total_weight,
        "centros_seleccionados": int(states["n_seleccionados"].sum()),
        "centros_con_outcome": int(states["n_con_outcome"].sum()),
    }


def run_transition(transition: Transition, ladder_name: str, min_electores: int) -> dict[str, pd.DataFrame]:
    frame = load_frame(transition.frame_path)
    if transition.name == "2013_2018":
        frame = complete_2018_frame_with_venpres_dc(frame)
    historical = load_results(transition.historical_kind, transition.historical_path)
    quotas = allocate_dhondt_quotas(frame)
    selected_legacy, incomplete = select_legacy(
        frame, historical, quotas, DEFAULT_TOLERANCE_LADDERS[ladder_name], min_electores
    )
    selected_size = select_size_only(frame, historical, quotas)
    outcome = load_results(transition.outcome_kind, transition.outcome_path)

    legacy_states = evaluate_selection(
        transition.name, "legacy", frame, selected_legacy, historical, outcome, quotas, ladder_name, min_electores
    )
    size_states = evaluate_selection(
        transition.name, "size_only", frame, selected_size, historical, outcome, quotas, ladder_name, min_electores
    )
    quota_rows = pd.DataFrame(
        [
            {
                "transicion": transition.name,
                "cod_estado": state,
                "estado": STATE_NAMES.get(state, state),
                "cuota_total": quota,
                "cuota_base": BASE_PER_STATE,
                "extras_dhondt": quota - BASE_PER_STATE,
                "electores_frame": float(frame[frame["cod_estado"].eq(state)]["electores"].sum()),
                "centros_frame": int(frame[frame["cod_estado"].eq(state)]["codigo_centro"].nunique()),
            }
            for state, quota in sorted(quotas.items())
        ]
    )
    return {
        "states": pd.concat([legacy_states, size_states], ignore_index=True),
        "centers": selected_legacy.assign(transicion=transition.name),
        "quotas": quota_rows,
        "incomplete": incomplete.assign(transicion=transition.name) if not incomplete.empty else incomplete,
        "excluded": exclusion_summary(frame, historical, transition.name),
    }


def exclusion_summary(frame: pd.DataFrame, historical: pd.DataFrame, transition: str) -> pd.DataFrame:
    hist_codes = set(historical["codigo_centro"])
    rows = []
    for state, group in frame.groupby("cod_estado"):
        missing = int((~group["codigo_centro"].isin(hist_codes)).sum())
        rows.append(
            {
                "transicion": transition,
                "cod_estado": state,
                "estado": STATE_NAMES.get(state, state),
                "centros_frame": int(len(group)),
                "centros_sin_historico": missing,
                "pct_sin_historico": round(100 * missing / len(group), 6) if len(group) else None,
            }
        )
    return pd.DataFrame(rows)


def run_all(
    output_dir: Path,
    tolerance_ladders: dict[str, list[float]] = DEFAULT_TOLERANCE_LADDERS,
    min_electores_values: Iterable[int] = DEFAULT_MIN_ELECTORES,
) -> dict[str, pd.DataFrame]:
    primary_states = []
    primary_centers = []
    quota_rows = []
    excluded_rows = []
    incomplete_rows = []
    sensitivity = []

    for transition in TRANSITIONS:
        for ladder_name in tolerance_ladders:
            for min_electores in min_electores_values:
                result = run_transition(transition, ladder_name, int(min_electores))
                metrics = [national_metrics(g) for _, g in result["states"].groupby(["transicion", "metodo"])]
                sensitivity.extend(metrics)
                if (ladder_name, int(min_electores)) == PRIMARY_CONFIG:
                    primary_states.append(result["states"])
                    primary_centers.append(result["centers"])
                    quota_rows.append(result["quotas"])
                    excluded_rows.append(result["excluded"])
                    if not result["incomplete"].empty:
                        incomplete_rows.append(result["incomplete"])

    outputs = {
        "states": pd.concat(primary_states, ignore_index=True),
        "centers": pd.concat(primary_centers, ignore_index=True),
        "quotas": pd.concat(quota_rows, ignore_index=True),
        "excluded": pd.concat(excluded_rows, ignore_index=True),
        "sensitivity": pd.DataFrame(sensitivity),
        "incomplete": pd.concat(incomplete_rows, ignore_index=True) if incomplete_rows else pd.DataFrame(),
    }
    write_outputs(output_dir, outputs)
    return outputs


def _round_floats(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.select_dtypes(include=["float"]).columns:
        out[col] = out[col].round(6)
    return out


def write_outputs(output_dir: Path, outputs: dict[str, pd.DataFrame]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    states = _round_floats(outputs["states"])
    states[states["transicion"].eq("2013_2018")].to_csv(
        output_dir / "backtest_legacy_2013_2018_estados.csv", index=False, encoding="utf-8"
    )
    states[states["transicion"].eq("2018_2024")].to_csv(
        output_dir / "backtest_legacy_2018_2024_estados.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["centers"]).to_csv(
        output_dir / "backtest_legacy_centros.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["sensitivity"]).to_csv(
        output_dir / "backtest_legacy_sensibilidad.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["quotas"]).to_csv(output_dir / "backtest_legacy_cuotas.csv", index=False, encoding="utf-8")
    _round_floats(outputs["excluded"]).to_csv(
        output_dir / "backtest_legacy_exclusiones.csv", index=False, encoding="utf-8"
    )
    if not outputs["incomplete"].empty:
        outputs["incomplete"].to_csv(output_dir / "backtest_legacy_incompletos.csv", index=False, encoding="utf-8")
    write_markdown(output_dir / "BACKTEST_LEGACY_NACIONAL.md", outputs)


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    try:
        if pd.isna(value):
            return "n/a"
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(_fmt(row.get(col)) for col in columns) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def write_markdown(path: Path, outputs: dict[str, pd.DataFrame]) -> None:
    metrics = outputs["sensitivity"]
    primary = metrics[
        metrics["tolerance_ladder"].eq(PRIMARY_CONFIG[0]) & metrics["min_electores"].eq(PRIMARY_CONFIG[1])
    ].copy()
    quota_check = (
        outputs["quotas"]
        .groupby("transicion", as_index=False)
        .agg(suma_cuotas_finales=("cuota_total", "sum"), suma_extras_dhondt=("extras_dhondt", "sum"))
    )
    coverage = (
        outputs["states"]
        .groupby(["transicion", "metodo"], as_index=False)
        .agg(centros_seleccionados=("n_seleccionados", "sum"), centros_con_outcome=("n_con_outcome", "sum"))
    )
    coverage["cobertura_pct"] = 100 * coverage["centros_con_outcome"] / coverage["centros_seleccionados"]

    lines = [
        "# Backtest legacy nacional de seleccion de centros",
        "",
        "Este documento es generado por `backend/backtest_legacy_nacional.py`. Evalua solo la seleccion base de 120 centros: no simula campo, sobremuestreo, reemplazos discrecionales, ponderacion ni proyeccion de ganador.",
        "",
        "## Reglas implementadas",
        "",
        "- Tamano base nacional: 120 centros.",
        "- Cobertura territorial: 2 centros iniciales por cada una de las 24 entidades, para 48 fijos.",
        "- D'Hondt asigna solo los 72 centros adicionales sobre electores del marco vigente; los 2 garantizados no cuentan como escanos previos.",
        "- Elegibilidad: centro con codigo CNE normalizado presente en la eleccion presidencial inmediatamente anterior.",
        "- Orden interno: centros elegibles por estado de mayor a menor electores, reiniciando desde el mayor en cada tolerancia.",
        "- Variable comun: porcentaje de Maduro sobre votos validos, calculado desde votos agregados.",
        "- Baseline primaria de formalizacion moderna: tolerancias `[2, 4, 6, 8, 10, 15, 20, inf]` pp y `min_electores=300`.",
        "- Comparador `size_only`: misma cuota estatal y mismo requisito de historico, pero toma los centros elegibles mas grandes.",
        "",
        "## Fuentes locales",
        "",
        "- 2018 usando 2013: `backend/tm_2018_estandar.csv`, `backend/data/2013/presidenciales/resultados oficiales elecciones presidenciales 2013.xlsx`, `backend/data/2018/resultados_venpres_a_2018.csv`.",
        "- 2024 usando 2018: `backend/tm_2024_estandar.csv`, `backend/data/2018/resultados_venpres_a_2018.csv`, `backend/resultados_cne2024.csv`.",
        "",
        "Para `2013_2018`, `tm_2018_estandar.csv` no trae Distrito Capital. Se completo el marco de esa entidad desde VENPRES-A 2018 usando solo columnas de marco (`codigo_centro`, nombre, electores y mesas); los votos de 2018 siguen cerrados hasta la fase de evaluacion.",
        "",
        "No se sustituyo cobertura parcial con fuentes web.",
        "",
        "## Verificacion de cuotas",
        "",
        markdown_table(
            quota_check.to_dict("records"),
            ["transicion", "suma_extras_dhondt", "suma_cuotas_finales"],
        ),
        "",
        "## Metricas nacionales",
        "",
        markdown_table(
            primary[
                [
                    "transicion",
                    "metodo",
                    "estados_evaluados",
                    "mae_error_outcome_pp",
                    "rmse_error_outcome_pp",
                    "mae_swing_error_pp",
                    "rmse_swing_error_pp",
                    "prop_dentro_5pp",
                    "centros_con_outcome",
                ]
            ].to_dict("records"),
            [
                "transicion",
                "metodo",
                "estados_evaluados",
                "mae_error_outcome_pp",
                "rmse_error_outcome_pp",
                "mae_swing_error_pp",
                "rmse_swing_error_pp",
                "prop_dentro_5pp",
                "centros_con_outcome",
            ],
        ),
        "",
        "## Cobertura de outcomes en muestra primaria",
        "",
        markdown_table(
            coverage.to_dict("records"),
            ["transicion", "metodo", "centros_seleccionados", "centros_con_outcome", "cobertura_pct"],
        ),
        "",
        "## Sensibilidad",
        "",
        "El grid cruza tres escaleras de tolerancia y tres valores de `min_electores`. Los resultados completos estan en `backtest_legacy_sensibilidad.csv`; estas cifras son una operacionalizacion moderna del juicio legacy, no umbrales historicos reconstruidos.",
        "",
        markdown_table(
            metrics[
                [
                    "transicion",
                    "metodo",
                    "tolerance_ladder",
                    "min_electores",
                    "mae_error_outcome_pp",
                    "rmse_error_outcome_pp",
                    "mae_swing_error_pp",
                    "centros_con_outcome",
                ]
            ].to_dict("records"),
            [
                "transicion",
                "metodo",
                "tolerance_ladder",
                "min_electores",
                "mae_error_outcome_pp",
                "rmse_error_outcome_pp",
                "mae_swing_error_pp",
                "centros_con_outcome",
            ],
        ),
        "",
        "## Archivos generados",
        "",
        "- `backtest_legacy_2013_2018_estados.csv`",
        "- `backtest_legacy_2018_2024_estados.csv`",
        "- `backtest_legacy_centros.csv`",
        "- `backtest_legacy_sensibilidad.csv`",
        "- `backtest_legacy_cuotas.csv`",
        "- `backtest_legacy_exclusiones.csv`",
        "",
        "## Limitaciones",
        "",
        "- VENPRES-A 2018 y CNE 2024 se tratan segun la cobertura disponible en repo.",
        "- Si un centro seleccionado no tiene outcome, queda en el denominador de seleccion y fuera del calculo de outcome; no se reemplaza post hoc.",
        "- Las dos transiciones son stress tests electorales. No se ajustaron parametros con conocimiento del outcome.",
        "- El resultado no valida ni invalida el exit poll completo; solo compara reglas de seleccion de centros.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "docs" / "muestreo")
    args = parser.parse_args()
    outputs = run_all(args.output_dir)
    print(f"Estados: {len(outputs['states'])} filas")
    print(f"Centros legacy primarios: {len(outputs['centers'])} filas")
    print(f"Sensibilidad: {len(outputs['sensitivity'])} filas")
    print(f"Salida: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
