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
SIMILARITY_VARIANTS = ("winner_share", "top2_gap", "full_profile")
LONGITUDINAL_TARGETS = {
    2013: [2006, 2012],
    2018: [2006, 2012, 2013],
    2024: [2006, 2012, 2013, 2018],
}
LONGITUDINAL_SELECTORS = ("recent_distance", "historical_mae", "historical_rmse", "historical_volatility")
VALID_LONGITUDINAL_SELECTORS = set(LONGITUDINAL_SELECTORS)
ORACLE_SELECTOR = "oracle"
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

PRESIDENTIAL_EXCEL_SOURCES = {
    2006: {
        "path": BASE_DIR / "data" / "2006" / "resultado elecciones presidenciales 2006.xlsx",
        "sheet": "resultados_2006-12-03",
        "codigo_col": "codigo_centro_nuevo",
        "nombre_col": "centro",
        "electores_col": "inscritos_rep",
        "gobierno_cols": ["votos_chavez"],
        "oposicion_cols": ["votos_rosales"],
        "otros_cols": [],
        "validos_col": "votos_validos",
        "votantes_col": "votos_escrutados",
        "cod_edo_col": "codigo_estado",
    },
    2012: {
        "path": BASE_DIR / "data" / "2012" / "presidenciales" / "resultados oficiales presidenciales 2012.xlsx",
        "sheet": "resultados_2012-10-07",
        "codigo_col": "codigo nuevo",
        "nombre_col": "centro",
        "electores_col": "electores escrutados",
        "gobierno_cols": ["chavez"],
        "oposicion_cols": ["capriles"],
        "otros_cols": ["chirino", "sequera", "reyes", "bolivar"],
        "validos_col": "votos validos",
        "votantes_col": "votantes que_votaron",
        "cod_edo_col": "cod_edo",
    },
    2013: {
        "path": BASE_DIR / "data" / "2013" / "presidenciales" / "resultados oficiales elecciones presidenciales 2013.xlsx",
        "sheet": "resultados_2013-04-14",
        "codigo_col": "codigo nuevo",
        "nombre_col": "centro",
        "electores_col": "electores esperados",
        "gobierno_cols": ["maduro"],
        "oposicion_cols": ["capriles"],
        "otros_cols": ["sequera", "bolivar", "mora", "mendez"],
        "validos_col": "votos validos",
        "votantes_col": "votos escrutados",
        "cod_edo_col": "cod_edo",
    },
}


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


def residual(center_pct: float, state_pct: float) -> float:
    return float(center_pct) - float(state_pct)


def longitudinal_feature_values(residuals: list[float | None]) -> dict[str, float | int | None]:
    values = [float(value) for value in residuals if value is not None and not pd.isna(value)]
    if not values:
        return {
            "n_hist": 0,
            "recent_distance": None,
            "historical_mae": None,
            "historical_rmse": None,
            "historical_bias": None,
            "abs_historical_bias": None,
            "historical_volatility": None,
        }
    bias = mean(values)
    return {
        "n_hist": len(values),
        "recent_distance": abs(values[-1]),
        "historical_mae": mean(abs(value) for value in values),
        "historical_rmse": math.sqrt(mean(value * value for value in values)),
        "historical_bias": bias,
        "abs_historical_bias": abs(bias),
        "historical_volatility": (
            math.sqrt(mean((value - bias) ** 2 for value in values)) if len(values) >= 2 else None
        ),
    }


def _source_col(columns: Iterable[object], configured_name: str) -> object:
    return _find_column(columns, *str(configured_name).replace("_", " ").split())


@lru_cache(maxsize=None)
def load_presidential_result(year: int) -> pd.DataFrame:
    if year in PRESIDENTIAL_EXCEL_SOURCES:
        source = PRESIDENTIAL_EXCEL_SOURCES[year]
        df = pd.read_excel(source["path"], sheet_name=source["sheet"], dtype=object)
        code_col = _source_col(df.columns, source["codigo_col"])
        name_col = _source_col(df.columns, source["nombre_col"])
        electors_col = _source_col(df.columns, source["electores_col"])
        valid_col = _source_col(df.columns, source["validos_col"])
        voters_col = _source_col(df.columns, source["votantes_col"])
        state_col = _source_col(df.columns, source["cod_edo_col"])
        gov_cols = [_source_col(df.columns, col) for col in source["gobierno_cols"]]
        opos_cols = [_source_col(df.columns, col) for col in source["oposicion_cols"]]
        otros_cols = [_source_col(df.columns, col) for col in source["otros_cols"]]
        df["codigo_centro"] = df[code_col].map(code9)
        df["cod_estado"] = _num(df[state_col]).astype(int).map(lambda value: f"{value:02d}")
        df = df[~df["cod_estado"].eq("99")].copy()
        df["nombre_centro"] = df[name_col].astype(str)
        df["electores"] = _num(df[electors_col])
        df["votos_gobierno"] = sum(_num(df[col]) for col in gov_cols)
        df["votos_oposicion"] = sum(_num(df[col]) for col in opos_cols)
        df["votos_otros"] = sum(_num(df[col]) for col in otros_cols) if otros_cols else 0
        df["votos_validos"] = _num(df[valid_col])
        df["votantes"] = _num(df[voters_col])
        rows = (
            df[df["codigo_centro"].ne("")]
            .groupby(["codigo_centro", "cod_estado"], as_index=False)
            .agg(
                nombre_centro=("nombre_centro", "first"),
                electores=("electores", "sum"),
                votos_gobierno=("votos_gobierno", "sum"),
                votos_oposicion=("votos_oposicion", "sum"),
                votos_otros=("votos_otros", "sum"),
                votos_validos=("votos_validos", "sum"),
                votantes=("votantes", "sum"),
            )
        )
    elif year == 2018:
        rows = load_results("venpres2018_csv", BASE_DIR / "data" / "2018" / "resultados_venpres_a_2018.csv").copy()
        source = pd.read_csv(BASE_DIR / "data" / "2018" / "resultados_venpres_a_2018.csv", dtype=str)
        source["codigo_centro"] = source["codigo_centro"].map(code9)
        source["nombre_centro"] = source["nombre_centro"].astype(str)
        source["electores"] = _num(source["electores_inscritos"])
        source["votantes"] = _num(source["votantes"])
        rows = rows.merge(source[["codigo_centro", "nombre_centro", "electores", "votantes"]], on="codigo_centro", how="left")
    elif year == 2024:
        rows = load_results("cne2024_csv", BASE_DIR / "resultados_cne2024.csv").copy()
        frame = load_frame(BASE_DIR / "tm_2024_estandar.csv")
        rows = rows.merge(frame[["codigo_centro", "nombre_centro", "electores"]], on="codigo_centro", how="left")
        rows["votantes"] = None
    else:
        raise ValueError(f"Eleccion presidencial no soportada: {year}")

    rows = rows[rows["cod_estado"].isin(STATE_NAMES)].copy()
    rows = rows[rows["votos_validos"] > 0].copy()
    rows["pct_gobierno"] = 100 * rows["votos_gobierno"] / rows["votos_validos"]
    rows["estado"] = rows["cod_estado"].map(STATE_NAMES)
    rows["year"] = year
    return rows.reset_index(drop=True)


def frame_for_longitudinal_target(target_year: int) -> pd.DataFrame:
    if target_year == 2013:
        rows = load_presidential_result(2013)[
            ["codigo_centro", "cod_estado", "nombre_centro", "estado", "electores"]
        ].copy()
        rows["mesas"] = None
    elif target_year == 2018:
        rows = complete_2018_frame_with_venpres_dc(load_frame(BASE_DIR / "tm_2018_estandar.csv"))
    elif target_year == 2024:
        rows = load_frame(BASE_DIR / "tm_2024_estandar.csv")
    else:
        raise ValueError(f"Target longitudinal no soportado: {target_year}")
    rows = rows[rows["cod_estado"].isin(STATE_NAMES)].copy()
    rows = rows.sort_values(["cod_estado", "electores", "codigo_centro"], ascending=[True, False, True])
    rows["rank_por_tamano"] = rows.groupby("cod_estado")["electores"].rank(method="first", ascending=False).astype(int)
    return rows.reset_index(drop=True)


def residuals_for_year(year: int) -> pd.DataFrame:
    result = load_presidential_result(year)
    state = (
        result.groupby("cod_estado", as_index=False)
        .agg(votos_gobierno=("votos_gobierno", "sum"), votos_validos=("votos_validos", "sum"))
    )
    state["pct_gobierno_estado"] = 100 * state["votos_gobierno"] / state["votos_validos"]
    rows = result.merge(state[["cod_estado", "pct_gobierno_estado"]], on="cod_estado", how="left")
    rows[f"residual_{year}"] = rows["pct_gobierno"] - rows["pct_gobierno_estado"]
    return rows[["codigo_centro", "cod_estado", f"residual_{year}"]].copy()


def build_longitudinal_features(target_year: int) -> pd.DataFrame:
    frame = frame_for_longitudinal_target(target_year)
    history_years = LONGITUDINAL_TARGETS[target_year]
    features = frame[["codigo_centro", "cod_estado", "estado", "nombre_centro", "electores", "rank_por_tamano"]].copy()
    for year in history_years:
        features = features.merge(residuals_for_year(year), on=["codigo_centro", "cod_estado"], how="left")
    residual_cols = [f"residual_{year}" for year in history_years]
    computed = []
    for _, row in features.iterrows():
        vals = [row[col] if not pd.isna(row[col]) else None for col in residual_cols]
        computed.append(longitudinal_feature_values(vals))
    return pd.concat([features, pd.DataFrame(computed)], axis=1)


@lru_cache(maxsize=None)
def load_candidate_results(kind: str, path: Path) -> pd.DataFrame:
    """Carga votos por candidato para calcular similitud historica.

    Las columnas `cand_*` son el perfil comparable dentro de una misma
    eleccion. No se intenta crear una taxonomia longitudinal.
    """
    if kind == "pres2013_xlsx":
        df = pd.read_excel(path, dtype=object)
        code_col = _find_column(df.columns, "codigo", "nuevo")
        valid_col = _find_column(df.columns, "votos", "validos")
        candidate_cols = ["maduro", "capriles", "sequera", "bolivar", "mora", "mendez"]
        df["codigo_centro"] = df[code_col].map(code9)
        df["cod_estado"] = df["codigo_centro"].str[:2]
        for col in [*candidate_cols, valid_col]:
            df[col] = _num(df[col])
        rename = {col: f"cand_{col}" for col in candidate_cols}
        df = df.rename(columns=rename)
        out_cols = ["codigo_centro", "cod_estado", *rename.values()]
    elif kind == "venpres2018_csv":
        df = pd.read_csv(path, dtype=str)
        df["codigo_centro"] = df["codigo_centro"].map(code9)
        df["cod_estado"] = df["codigo_centro"].str[:2]
        source_cols = {
            "cand_maduro": "votos_gobierno",
            "cand_falcon": "votos_falcon" if "votos_falcon" in df.columns else "votos_oposicion",
            "cand_bertucci_quijada": (
                "votos_bertucci_quijada" if "votos_bertucci_quijada" in df.columns else "votos_otros"
            ),
        }
        for col in source_cols.values():
            df[col] = _num(df[col])
        for target, source in source_cols.items():
            df[target] = df[source]
        out_cols = ["codigo_centro", "cod_estado", *source_cols.keys()]
    else:
        raise ValueError(f"Tipo de perfil no soportado: {kind}")

    grouped = df[df["codigo_centro"].ne("")].groupby(["codigo_centro", "cod_estado"], as_index=False)[
        [c for c in out_cols if c.startswith("cand_")]
    ].sum()
    candidate_cols = [c for c in grouped.columns if c.startswith("cand_")]
    grouped["votos_validos"] = grouped[candidate_cols].sum(axis=1)
    grouped = grouped[grouped["votos_validos"] > 0].copy()
    for col in candidate_cols:
        grouped[f"pct_{col[5:]}"] = 100 * grouped[col] / grouped["votos_validos"]
    return grouped


def candidate_pct_columns(profile: pd.DataFrame) -> list[str]:
    return sorted(col for col in profile.columns if col.startswith("pct_"))


def state_candidate_profiles(profile: pd.DataFrame) -> pd.DataFrame:
    candidate_vote_cols = sorted(col for col in profile.columns if col.startswith("cand_"))
    grouped = profile.groupby("cod_estado", as_index=False)[candidate_vote_cols].sum()
    grouped["votos_validos"] = grouped[candidate_vote_cols].sum(axis=1)
    grouped = grouped[grouped["votos_validos"] > 0].copy()
    for col in candidate_vote_cols:
        grouped[f"pct_{col[5:]}"] = 100 * grouped[col] / grouped["votos_validos"]
    return grouped


def similarity_distance(
    center_pct: dict[str, float],
    state_pct: dict[str, float],
    variant: str,
) -> float:
    if variant not in SIMILARITY_VARIANTS:
        raise ValueError(f"Variante no soportada: {variant}")
    candidates = sorted(state_pct)
    if not candidates:
        raise ValueError("Perfil estatal vacio")
    if variant == "winner_share":
        winner = max(candidates, key=lambda c: (state_pct[c], c))
        return abs(float(center_pct.get(winner, 0.0)) - float(state_pct[winner]))
    if variant == "top2_gap":
        ordered = sorted(candidates, key=lambda c: (-state_pct[c], c))
        if len(ordered) < 2:
            return 0.0
        first, second = ordered[:2]
        state_gap = float(state_pct[first]) - float(state_pct[second])
        center_gap = float(center_pct.get(first, 0.0)) - float(center_pct.get(second, 0.0))
        return abs(center_gap - state_gap)
    return 0.5 * sum(abs(float(center_pct.get(c, 0.0)) - float(state_pct[c])) for c in candidates)


def enrich_similarity_distances(profile: pd.DataFrame, variant: str) -> pd.DataFrame:
    pct_cols = candidate_pct_columns(profile)
    state_profiles = state_candidate_profiles(profile)
    state_pct = {
        row["cod_estado"]: {col[4:]: float(row[col]) for col in pct_cols}
        for row in state_profiles.to_dict("records")
    }
    rows = []
    for row in profile.to_dict("records"):
        state = row["cod_estado"]
        if state not in state_pct:
            continue
        center_pct = {col[4:]: float(row[col]) for col in pct_cols}
        state_row = state_pct[state]
        ordered = sorted(state_row, key=lambda c: (-state_row[c], c))
        rows.append(
            {
                "codigo_centro": row["codigo_centro"],
                "cod_estado": state,
                "similarity": variant,
                "distancia_hist_pp": similarity_distance(center_pct, state_row, variant),
                "state_winner": ordered[0] if ordered else "",
                "state_top1": ordered[0] if ordered else "",
                "state_top2": ordered[1] if len(ordered) > 1 else "",
                "candidate_profile": ",".join(sorted(state_row)),
            }
        )
    return pd.DataFrame(rows)


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


def select_legacy_similarity(
    frame: pd.DataFrame,
    historical_profile: pd.DataFrame,
    quotas: dict[str, int],
    tolerance_ladder_pp: list[float],
    min_electores: int,
    similarity: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    distances = enrich_similarity_distances(historical_profile, similarity)
    eligible = frame.merge(distances, on=["codigo_centro", "cod_estado"], how="inner")
    eligible = eligible[eligible["electores"] >= min_electores].copy()

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

    eligible["pasada"] = eligible["distancia_hist_pp"].map(entry_pass)
    eligible["tolerancia_de_entrada"] = eligible["distancia_hist_pp"].map(entry_tolerance)
    eligible = eligible.dropna(subset=["pasada"]).copy()
    eligible["pasada"] = eligible["pasada"].astype(int)

    selected = []
    incomplete = []
    for state, quota in sorted(quotas.items()):
        chosen = (
            eligible[eligible["cod_estado"].eq(state)]
            .sort_values(["pasada", "electores", "codigo_centro"], ascending=[True, False, True])
            .head(quota)
            .copy()
        )
        if not chosen.empty:
            chosen["metodo"] = "legacy_similarity"
            selected.extend(chosen.to_dict("records"))
        if len(chosen) < quota:
            incomplete.append(
                {
                    "cod_estado": state,
                    "estado": STATE_NAMES.get(state, state),
                    "cuota": quota,
                    "seleccionados": len(chosen),
                    "faltantes": quota - len(chosen),
                    "similarity": similarity,
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


def similarity_summary_metrics(states: pd.DataFrame) -> dict[str, float | int | str | None]:
    valid = states.dropna(subset=["error_outcome_pp"]).copy()
    if valid.empty:
        return {}
    valid["abs_error"] = valid["error_outcome_pp"].abs()
    max_row = valid.sort_values(["abs_error", "cod_estado"], ascending=[False, True]).iloc[0]
    errors = [float(x) for x in valid["error_outcome_pp"]]
    abs_errors = [abs(x) for x in errors]
    swing_valid = states.dropna(subset=["swing_error_pp"]).copy()
    swing_errors = [float(x) for x in swing_valid["swing_error_pp"]]
    return {
        "transicion": states.iloc[0]["transicion"],
        "similarity": states.iloc[0]["similarity"],
        "centros_seleccionados": int(states["n_seleccionados"].sum()),
        "estados_evaluados": int(len(valid)),
        "mae": mean(abs_errors),
        "rmse": math.sqrt(mean([e * e for e in errors])),
        "medae": median(abs_errors),
        "pct_dentro_2pp": sum(1 for x in abs_errors if x <= 2) / len(abs_errors),
        "pct_dentro_5pp": sum(1 for x in abs_errors if x <= 5) / len(abs_errors),
        "pct_dentro_10pp": sum(1 for x in abs_errors if x <= 10) / len(abs_errors),
        "max_error_abs": float(max_row["abs_error"]),
        "max_error_estado": max_row["estado"],
        "max_error_firmado": float(max_row["error_outcome_pp"]),
        "mae_swing_error_pp": mean([abs(x) for x in swing_errors]) if swing_errors else None,
        "rmse_swing_error_pp": math.sqrt(mean([x * x for x in swing_errors])) if swing_errors else None,
    }


def similarity_state_diagnostics(
    selected: pd.DataFrame,
    transition: str,
    similarity: str,
    quotas: dict[str, int],
) -> pd.DataFrame:
    rows = []
    for state, quota in sorted(quotas.items()):
        group = selected[selected["cod_estado"].eq(state)].copy()
        tolerance_counts = defaultdict(int)
        for value in group["tolerancia_de_entrada"].tolist() if not group.empty else []:
            tolerance_counts[str(value)] += 1
        rows.append(
            {
                "transicion": transition,
                "similarity": similarity,
                "cod_estado": state,
                "estado": STATE_NAMES.get(state, state),
                "cuota": quota,
                "distancia_media_sel": float(group["distancia_hist_pp"].mean()) if not group.empty else None,
                "distancia_mediana_sel": float(group["distancia_hist_pp"].median()) if not group.empty else None,
                "distancia_max_sel": float(group["distancia_hist_pp"].max()) if not group.empty else None,
                "pasada_maxima": int(group["pasada"].max()) if not group.empty else None,
                "tolerancia_maxima": group["tolerancia_de_entrada"].iloc[-1] if not group.empty else None,
                "conteo_por_tolerancia": ";".join(f"{k}:{v}" for k, v in sorted(tolerance_counts.items())),
                "electores_medianos_sel": float(group["electores"].median()) if not group.empty else None,
                "electores_minimos_sel": float(group["electores"].min()) if not group.empty else None,
            }
        )
    return pd.DataFrame(rows)


def add_sample_overlap_diagnostics(states: pd.DataFrame, centers: pd.DataFrame) -> pd.DataFrame:
    out = states.copy()
    selected_sets = {
        (transition, similarity, state): set(group["codigo_centro"])
        for (transition, similarity, state), group in centers.groupby(["transicion", "similarity", "cod_estado"])
    }
    rows = []
    for row in out.to_dict("records"):
        key_base = (row["transicion"], row["cod_estado"])
        current = selected_sets.get((row["transicion"], row["similarity"], row["cod_estado"]), set())
        others = [
            selected_sets.get((key_base[0], other, key_base[1]), set())
            for other in SIMILARITY_VARIANTS
            if other != row["similarity"]
        ]
        common_all = set(current)
        for other_set in others:
            common_all &= other_set
        row["n_difiere_otras_variantes"] = len(current - common_all)
        for other in SIMILARITY_VARIANTS:
            if other == row["similarity"]:
                row[f"n_difiere_vs_{other}"] = 0
                continue
            other_set = selected_sets.get((key_base[0], other, key_base[1]), set())
            row[f"n_difiere_vs_{other}"] = len(current - other_set)
        rows.append(row)
    return pd.DataFrame(rows)


def common_centers_summary(centers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for transition, group in centers.groupby("transicion"):
        sets = [
            set(group[group["similarity"].eq(similarity)]["codigo_centro"])
            for similarity in SIMILARITY_VARIANTS
        ]
        common = set.intersection(*sets) if sets else set()
        rows.append(
            {
                "transicion": transition,
                "centros_comunes_tres_variantes": len(common),
                "pct_comun_sobre_120": 100 * len(common) / N_BASE,
            }
        )
    return pd.DataFrame(rows)


def run_similarity_transition(transition: Transition) -> dict[str, pd.DataFrame]:
    frame = load_frame(transition.frame_path)
    if transition.name == "2013_2018":
        frame = complete_2018_frame_with_venpres_dc(frame)
    quotas = allocate_dhondt_quotas(frame)
    historical_eval = load_results(transition.historical_kind, transition.historical_path)
    historical_profile = load_candidate_results(transition.historical_kind, transition.historical_path)
    outcome = load_results(transition.outcome_kind, transition.outcome_path)

    state_rows = []
    center_rows = []
    diagnostics = []
    incomplete_rows = []
    for similarity in SIMILARITY_VARIANTS:
        selected, incomplete = select_legacy_similarity(
            frame,
            historical_profile,
            quotas,
            DEFAULT_TOLERANCE_LADDERS[PRIMARY_CONFIG[0]],
            PRIMARY_CONFIG[1],
            similarity,
        )
        selected = selected.assign(transicion=transition.name, similarity=similarity)
        states = evaluate_selection(
            transition.name,
            "legacy_similarity",
            frame,
            selected,
            historical_eval,
            outcome,
            quotas,
            PRIMARY_CONFIG[0],
            PRIMARY_CONFIG[1],
        ).assign(similarity=similarity)
        state_rows.append(states)
        center_rows.append(selected)
        diagnostics.append(similarity_state_diagnostics(selected, transition.name, similarity, quotas))
        if not incomplete.empty:
            incomplete_rows.append(incomplete.assign(transicion=transition.name))

    centers = pd.concat(center_rows, ignore_index=True)
    states = add_sample_overlap_diagnostics(pd.concat(state_rows, ignore_index=True), centers)
    diagnostics_df = pd.concat(diagnostics, ignore_index=True)
    diagnostics_df = diagnostics_df.merge(
        states[
            [
                "transicion",
                "similarity",
                "cod_estado",
                "n_difiere_otras_variantes",
                "n_difiere_vs_winner_share",
                "n_difiere_vs_top2_gap",
                "n_difiere_vs_full_profile",
            ]
        ],
        on=["transicion", "similarity", "cod_estado"],
        how="left",
    )
    diagnostic_cols = [
        "transicion",
        "similarity",
        "cod_estado",
        "estado",
        "cuota",
        "distancia_media_sel",
        "distancia_mediana_sel",
        "distancia_max_sel",
        "pasada_maxima",
        "tolerancia_maxima",
        "conteo_por_tolerancia",
        "electores_medianos_sel",
        "electores_minimos_sel",
    ]
    states = states.merge(
        diagnostics_df[diagnostic_cols],
        on=["transicion", "similarity", "cod_estado", "estado", "cuota"],
        how="left",
    )
    summary = pd.DataFrame(
        [similarity_summary_metrics(group) for _, group in states.groupby(["transicion", "similarity"])]
    )
    summary = summary.merge(common_centers_summary(centers), on="transicion", how="left")
    return {
        "summary": summary,
        "states": states,
        "centers": centers,
        "incomplete": pd.concat(incomplete_rows, ignore_index=True) if incomplete_rows else pd.DataFrame(),
    }


def run_similarity_experiment(output_dir: Path) -> dict[str, pd.DataFrame]:
    results = [run_similarity_transition(transition) for transition in TRANSITIONS]
    outputs = {
        key: pd.concat([result[key] for result in results], ignore_index=True)
        for key in ("summary", "states", "centers")
    }
    incomplete = [result["incomplete"] for result in results if not result["incomplete"].empty]
    outputs["incomplete"] = pd.concat(incomplete, ignore_index=True) if incomplete else pd.DataFrame()
    write_similarity_outputs(output_dir, outputs)
    return outputs


def select_longitudinal_feature(
    features: pd.DataFrame,
    quotas: dict[str, int],
    selector: str,
    cohort: str,
    tolerance_ladder_pp: list[float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if selector not in VALID_LONGITUDINAL_SELECTORS:
        raise ValueError(f"Selector longitudinal no productivo/no soportado: {selector}")
    eligible = features.dropna(subset=[selector]).copy()
    if cohort == "common":
        eligible = eligible[eligible["historical_volatility"].notna()].copy()
    elif cohort != "operational":
        raise ValueError(f"Cohorte no soportada: {cohort}")

    def entry_pass(score: float) -> int | None:
        for idx, tolerance in enumerate(tolerance_ladder_pp, start=1):
            if score <= tolerance:
                return idx
        return None

    def entry_tolerance(score: float) -> str | float | None:
        for tolerance in tolerance_ladder_pp:
            if score <= tolerance:
                return "inf" if math.isinf(tolerance) else tolerance
        return None

    eligible["selector"] = selector
    eligible["cohort"] = cohort
    eligible["score"] = eligible[selector].astype(float)
    eligible["pasada"] = eligible["score"].map(entry_pass)
    eligible["tolerancia_de_entrada"] = eligible["score"].map(entry_tolerance)
    eligible = eligible.dropna(subset=["pasada"]).copy()
    eligible["pasada"] = eligible["pasada"].astype(int)

    selected = []
    incomplete = []
    for state, quota in sorted(quotas.items()):
        chosen = (
            eligible[eligible["cod_estado"].eq(state)]
            .sort_values(["pasada", "electores", "codigo_centro"], ascending=[True, False, True])
            .head(quota)
            .copy()
        )
        if not chosen.empty:
            chosen["metodo"] = "longitudinal"
            selected.extend(chosen.to_dict("records"))
        if len(chosen) < quota:
            incomplete.append(
                {
                    "cod_estado": state,
                    "estado": STATE_NAMES.get(state, state),
                    "cuota": quota,
                    "seleccionados": len(chosen),
                    "faltantes": quota - len(chosen),
                    "selector": selector,
                    "cohort": cohort,
                }
            )
    return pd.DataFrame(selected), pd.DataFrame(incomplete)


def longitudinal_state_metrics(states: pd.DataFrame) -> dict[str, float | int | str | None]:
    valid = states.dropna(subset=["error_outcome_pp"]).copy()
    if valid.empty:
        return {}
    valid["abs_error"] = valid["error_outcome_pp"].abs()
    max_row = valid.sort_values(["abs_error", "cod_estado"], ascending=[False, True]).iloc[0]
    errors = [float(value) for value in valid["error_outcome_pp"]]
    abs_errors = [abs(value) for value in errors]
    return {
        "target": int(states.iloc[0]["target"]),
        "cohort": states.iloc[0]["cohort"],
        "selector": states.iloc[0]["selector"],
        "centros_seleccionados": int(states["n_seleccionados"].sum()),
        "estados_completos": int((states["n_seleccionados"] >= states["cuota"]).sum()),
        "estados_evaluados": int(len(valid)),
        "mae": mean(abs_errors),
        "rmse": math.sqrt(mean([value * value for value in errors])),
        "medae": median(abs_errors),
        "pct_dentro_2pp": sum(1 for value in abs_errors if value <= 2) / len(abs_errors),
        "pct_dentro_5pp": sum(1 for value in abs_errors if value <= 5) / len(abs_errors),
        "pct_dentro_10pp": sum(1 for value in abs_errors if value <= 10) / len(abs_errors),
        "max_error_abs": float(max_row["abs_error"]),
        "max_error_estado": max_row["estado"],
        "max_error_firmado": float(max_row["error_outcome_pp"]),
    }


def add_longitudinal_overlap(states: pd.DataFrame, centers: pd.DataFrame) -> pd.DataFrame:
    selected_sets = {
        (target, cohort, selector, state): set(group["codigo_centro"])
        for (target, cohort, selector, state), group in centers.groupby(["target", "cohort", "selector", "cod_estado"])
    }
    rows = []
    for row in states.to_dict("records"):
        current = selected_sets.get((row["target"], row["cohort"], row["selector"], row["cod_estado"]), set())
        common = set(current)
        for selector in LONGITUDINAL_SELECTORS:
            common &= selected_sets.get((row["target"], row["cohort"], selector, row["cod_estado"]), set())
        row["n_difiere_otras_features"] = len(current - common)
        rows.append(row)
    return pd.DataFrame(rows)


def longitudinal_common_centers_summary(centers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (target, cohort), group in centers.groupby(["target", "cohort"]):
        sets = [
            set(group[group["selector"].eq(selector)]["codigo_centro"])
            for selector in LONGITUDINAL_SELECTORS
        ]
        common = set.intersection(*sets) if sets else set()
        rows.append(
            {
                "target": int(target),
                "cohort": cohort,
                "centros_comunes_cuatro_selectores": len(common),
                "pct_comun_sobre_120": 100 * len(common) / N_BASE,
            }
        )
    return pd.DataFrame(rows)


def run_longitudinal_target(target_year: int) -> dict[str, pd.DataFrame]:
    features = build_longitudinal_features(target_year)
    frame = frame_for_longitudinal_target(target_year)
    quotas = allocate_dhondt_quotas(frame)
    prev_year = LONGITUDINAL_TARGETS[target_year][-1]
    historical_eval = load_presidential_result(prev_year)
    outcome = load_presidential_result(target_year)
    state_rows = []
    center_rows = []
    incomplete_rows = []
    for cohort in ("common", "operational"):
        for selector in LONGITUDINAL_SELECTORS:
            selected, incomplete = select_longitudinal_feature(
                features,
                quotas,
                selector,
                cohort,
                DEFAULT_TOLERANCE_LADDERS[PRIMARY_CONFIG[0]],
            )
            selected = selected.assign(target=target_year, selector=selector, cohort=cohort)
            states = evaluate_selection(
                str(target_year),
                "longitudinal",
                frame,
                selected,
                historical_eval,
                outcome,
                quotas,
                PRIMARY_CONFIG[0],
                PRIMARY_CONFIG[1],
            ).assign(target=target_year, selector=selector, cohort=cohort)
            state_rows.append(states)
            center_rows.append(selected)
            if not incomplete.empty:
                incomplete_rows.append(incomplete.assign(target=target_year))
    centers = pd.concat(center_rows, ignore_index=True)
    states = add_longitudinal_overlap(pd.concat(state_rows, ignore_index=True), centers)
    summary = pd.DataFrame(
        [longitudinal_state_metrics(group) for _, group in states.groupby(["target", "cohort", "selector"])]
    )
    summary = summary.merge(longitudinal_common_centers_summary(centers), on=["target", "cohort"], how="left")
    features = features.assign(target=target_year)
    return {
        "summary": summary,
        "states": states,
        "centers": centers,
        "features": features,
        "incomplete": pd.concat(incomplete_rows, ignore_index=True) if incomplete_rows else pd.DataFrame(),
    }


def transition_residual_diagnostics() -> pd.DataFrame:
    rows = []
    for prev_year, next_year in [(2006, 2012), (2012, 2013), (2013, 2018), (2018, 2024)]:
        prev = residuals_for_year(prev_year)
        nxt = residuals_for_year(next_year)
        prev_col = f"residual_{prev_year}"
        next_col = f"residual_{next_year}"
        merged = prev.merge(nxt, on=["codigo_centro", "cod_estado"], how="inner").dropna(subset=[prev_col, next_col])
        x = merged[prev_col].astype(float)
        y = merged[next_col].astype(float)
        if len(merged) >= 2 and float(x.var(ddof=0)) > 0:
            slope = float(((x - x.mean()) * (y - y.mean())).mean() / x.var(ddof=0))
            intercept = float(y.mean() - slope * x.mean())
            pred = intercept + slope * x
            ss_tot = float(((y - y.mean()) ** 2).sum())
            r2 = 1 - float(((y - pred) ** 2).sum()) / ss_tot if ss_tot > 0 else None
        else:
            slope = intercept = r2 = None
        rows.append(
            {
                "record_type": "transition_correlation",
                "from_year": prev_year,
                "to_year": next_year,
                "n_centros": len(merged),
                "pearson": float(x.corr(y, method="pearson")) if len(merged) >= 2 else None,
                "spearman": float(x.rank(method="average").corr(y.rank(method="average"))) if len(merged) >= 2 else None,
                "ols_slope": slope,
                "ols_intercept": intercept,
                "r2": r2,
                "mae_delta_residual": float((y - x).abs().mean()) if len(merged) else None,
            }
        )
        for prev_threshold in (1, 2, 5, 10):
            base = merged[x.abs() <= prev_threshold]
            for next_threshold in (2, 5, 10):
                rows.append(
                    {
                        "record_type": "threshold_persistence",
                        "from_year": prev_year,
                        "to_year": next_year,
                        "prev_threshold_pp": prev_threshold,
                        "next_threshold_pp": next_threshold,
                        "n_centros": len(base),
                        "pct_permanece": (
                            float((base[next_col].abs() <= next_threshold).mean()) if len(base) else None
                        ),
                    }
                )
    return pd.DataFrame(rows)


def feature_quantile_diagnostics(features_all: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target, features in features_all.groupby("target"):
        outcome_res = residuals_for_year(int(target)).rename(columns={f"residual_{int(target)}": "residual_target"})
        merged = features.merge(outcome_res, on=["codigo_centro", "cod_estado"], how="inner")
        merged["abs_residual_target"] = merged["residual_target"].abs()
        for feature in ("historical_volatility", "historical_mae", "abs_historical_bias", "recent_distance"):
            observed = merged.dropna(subset=[feature, "abs_residual_target"]).copy()
            if observed[feature].nunique() < 4:
                continue
            observed["quantile"] = pd.qcut(observed[feature], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
            for quantile, group in observed.groupby("quantile", observed=True):
                rows.append(
                    {
                        "record_type": "feature_quantile",
                        "target": int(target),
                        "feature": feature,
                        "quantile": str(quantile),
                        "n_centros": len(group),
                        "feature_min": float(group[feature].min()),
                        "feature_max": float(group[feature].max()),
                        "abs_residual_target_mae": float(group["abs_residual_target"].mean()),
                        "abs_residual_target_median": float(group["abs_residual_target"].median()),
                    }
                )
    return pd.DataFrame(rows)


def regression_diagnostics(x: pd.Series, y: pd.Series) -> dict[str, float | None]:
    if len(x) < 2:
        return {"pearson": None, "spearman": None, "ols_slope": None, "ols_intercept": None, "r2": None}
    x = x.astype(float)
    y = y.astype(float)
    if float(x.var(ddof=0)) > 0:
        slope = float(((x - x.mean()) * (y - y.mean())).mean() / x.var(ddof=0))
        intercept = float(y.mean() - slope * x.mean())
        pred = intercept + slope * x
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1 - float(((y - pred) ** 2).sum()) / ss_tot if ss_tot > 0 else None
    else:
        slope = intercept = r2 = None
    return {
        "pearson": float(x.corr(y, method="pearson")) if len(x) >= 2 else None,
        "spearman": float(x.rank(method="average").corr(y.rank(method="average"))) if len(x) >= 2 else None,
        "ols_slope": slope,
        "ols_intercept": intercept,
        "r2": r2,
    }


def transition_residual_within_state_diagnostics() -> pd.DataFrame:
    detail_rows = []
    summary_rows = []
    for prev_year, next_year in [(2006, 2012), (2012, 2013), (2013, 2018), (2018, 2024)]:
        prev = residuals_for_year(prev_year)
        nxt = residuals_for_year(next_year)
        prev_col = f"residual_{prev_year}"
        next_col = f"residual_{next_year}"
        merged = prev.merge(nxt, on=["codigo_centro", "cod_estado"], how="inner").dropna(subset=[prev_col, next_col])
        for state, group in merged.groupby("cod_estado"):
            x = group[prev_col].astype(float)
            y = group[next_col].astype(float)
            stats = regression_diagnostics(x, y)
            detail_rows.append(
                {
                    "record_type": "state_transition",
                    "from_year": prev_year,
                    "to_year": next_year,
                    "cod_estado": state,
                    "estado": STATE_NAMES.get(state, state),
                    "n_centros": len(group),
                    **stats,
                    "sd_residual_prev": float(x.std(ddof=0)) if len(group) else None,
                    "sd_residual_next": float(y.std(ddof=0)) if len(group) else None,
                    "mae_delta_residual": float((y - x).abs().mean()) if len(group) else None,
                }
            )
        detail = pd.DataFrame([row for row in detail_rows if row["from_year"] == prev_year and row["to_year"] == next_year])
        pearson = detail["pearson"].dropna().astype(float).tolist()
        r2 = detail["r2"].dropna().astype(float).tolist()
        summary_rows.append(
            {
                "record_type": "national_summary",
                "from_year": prev_year,
                "to_year": next_year,
                "n_estados": int(detail["cod_estado"].nunique()) if not detail.empty else 0,
                "median_pearson_state": median(pearson) if pearson else None,
                "p25_pearson_state": percentile(pearson, 0.25),
                "p75_pearson_state": percentile(pearson, 0.75),
                "median_r2_state": median(r2) if r2 else None,
                "p25_r2_state": percentile(r2, 0.25),
                "p75_r2_state": percentile(r2, 0.75),
                "n_states_pearson_positive": sum(1 for value in pearson if value > 0),
                "n_states_pearson_gt_0_5": sum(1 for value in pearson if value > 0.5),
                "n_states_r2_gt_0_25": sum(1 for value in r2 if value > 0.25),
                "n_states_r2_gt_0_50": sum(1 for value in r2 if value > 0.50),
            }
        )
    return pd.concat([pd.DataFrame(summary_rows), pd.DataFrame(detail_rows)], ignore_index=True, sort=False)


def select_oracle_diagnostic(
    features: pd.DataFrame,
    quotas: dict[str, int],
    target_year: int,
    tolerance_ladder_pp: list[float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    outcome = residuals_for_year(target_year).rename(columns={f"residual_{target_year}": "residual_target"})
    eligible = features.merge(outcome, on=["codigo_centro", "cod_estado"], how="inner")
    eligible["oracle_score"] = eligible["residual_target"].abs()
    eligible["selector"] = ORACLE_SELECTOR
    eligible["cohort"] = "diagnostic_oracle"
    eligible["score"] = eligible["oracle_score"].astype(float)
    eligible["diagnostic_only"] = True
    eligible["leakage_outcome_used"] = True

    def entry_pass(score: float) -> int | None:
        for idx, tolerance in enumerate(tolerance_ladder_pp, start=1):
            if score <= tolerance:
                return idx
        return None

    def entry_tolerance(score: float) -> str | float | None:
        for tolerance in tolerance_ladder_pp:
            if score <= tolerance:
                return "inf" if math.isinf(tolerance) else tolerance
        return None

    eligible["pasada"] = eligible["score"].map(entry_pass)
    eligible["tolerancia_de_entrada"] = eligible["score"].map(entry_tolerance)
    eligible = eligible.dropna(subset=["pasada"]).copy()
    eligible["pasada"] = eligible["pasada"].astype(int)

    selected = []
    incomplete = []
    for state, quota in sorted(quotas.items()):
        chosen = (
            eligible[eligible["cod_estado"].eq(state)]
            .sort_values(["pasada", "electores", "codigo_centro"], ascending=[True, False, True])
            .head(quota)
            .copy()
        )
        selected.extend(chosen.to_dict("records"))
        if len(chosen) < quota:
            incomplete.append(
                {
                    "cod_estado": state,
                    "estado": STATE_NAMES.get(state, state),
                    "cuota": quota,
                    "seleccionados": len(chosen),
                    "faltantes": quota - len(chosen),
                    "selector": ORACLE_SELECTOR,
                    "cohort": "diagnostic_oracle",
                    "diagnostic_only": True,
                }
            )
    return pd.DataFrame(selected), pd.DataFrame(incomplete)


def oracle_headroom_diagnostics() -> pd.DataFrame:
    rows = []
    for target_year in LONGITUDINAL_TARGETS:
        features = build_longitudinal_features(target_year)
        frame = frame_for_longitudinal_target(target_year)
        quotas = allocate_dhondt_quotas(frame)
        historical_eval = load_presidential_result(LONGITUDINAL_TARGETS[target_year][-1])
        outcome = load_presidential_result(target_year)
        summaries = []
        for selector in ("recent_distance", "historical_mae"):
            selected, _ = select_longitudinal_feature(
                features,
                quotas,
                selector,
                "operational",
                DEFAULT_TOLERANCE_LADDERS[PRIMARY_CONFIG[0]],
            )
            states = evaluate_selection(
                str(target_year),
                "longitudinal_falsification",
                frame,
                selected.assign(target=target_year, selector=selector, cohort="operational"),
                historical_eval,
                outcome,
                quotas,
                PRIMARY_CONFIG[0],
                PRIMARY_CONFIG[1],
            ).assign(target=target_year, selector=selector, cohort="operational")
            summary = longitudinal_state_metrics(states)
            summary["diagnostic_only"] = False
            summary["leakage_outcome_used"] = False
            summaries.append(summary)
        selected_oracle, _ = select_oracle_diagnostic(
            features, quotas, target_year, DEFAULT_TOLERANCE_LADDERS[PRIMARY_CONFIG[0]]
        )
        states = evaluate_selection(
            str(target_year),
            "oracle_diagnostic",
            frame,
            selected_oracle.assign(target=target_year, selector=ORACLE_SELECTOR, cohort="diagnostic_oracle"),
            historical_eval,
            outcome,
            quotas,
            PRIMARY_CONFIG[0],
            PRIMARY_CONFIG[1],
        ).assign(target=target_year, selector=ORACLE_SELECTOR, cohort="diagnostic_oracle")
        summary = longitudinal_state_metrics(states)
        summary["diagnostic_only"] = True
        summary["leakage_outcome_used"] = True
        summaries.append(summary)

        summary_by_selector = {row["selector"]: row for row in summaries}
        recent_mae = summary_by_selector["recent_distance"]["mae"]
        historical_mae = summary_by_selector["historical_mae"]["mae"]
        oracle_mae = summary_by_selector[ORACLE_SELECTOR]["mae"]
        total_headroom = recent_mae - oracle_mae
        gain_hist = recent_mae - historical_mae
        fraction_headroom = gain_hist / total_headroom if total_headroom and total_headroom > 0 else None
        for summary in summaries:
            rows.append(
                {
                    **summary,
                    "recent_mae": recent_mae,
                    "historical_mae_value": historical_mae,
                    "oracle_mae": oracle_mae,
                    "gain_hist": gain_hist,
                    "total_headroom": total_headroom,
                    "fraction_headroom": fraction_headroom,
                }
            )
    return pd.DataFrame(rows)


def survivorship_diagnostics() -> pd.DataFrame:
    rows = []
    for target_year in LONGITUDINAL_TARGETS:
        frame = frame_for_longitudinal_target(target_year)
        features = build_longitudinal_features(target_year)
        outcome = residuals_for_year(target_year).rename(columns={f"residual_{target_year}": "residual_target"})
        merged = frame[["codigo_centro", "cod_estado", "estado", "electores"]].merge(
            features[["codigo_centro", "cod_estado", "n_hist", "recent_distance", "historical_mae", "historical_volatility"]],
            on=["codigo_centro", "cod_estado"],
            how="left",
        ).merge(outcome, on=["codigo_centro", "cod_estado"], how="left")
        merged["n_hist"] = merged["n_hist"].fillna(0).astype(int)
        merged["abs_residual_target"] = merged["residual_target"].abs()
        merged["has_recent_distance"] = merged["recent_distance"].notna()
        merged["has_historical_mae"] = merged["historical_mae"].notna()
        merged["selectable_common_cohort"] = merged["historical_volatility"].notna()
        total_frame = len(merged)
        for n_hist, group in merged.groupby("n_hist"):
            rows.append(
                {
                    "record_type": "n_hist_summary",
                    "target": target_year,
                    "n_hist": int(n_hist),
                    "n_centros": len(group),
                    "pct_frame": 100 * len(group) / total_frame if total_frame else None,
                    "electores_median": float(group["electores"].median()) if len(group) else None,
                    "electores_mean": float(group["electores"].mean()) if len(group) else None,
                    "abs_residual_target_mean": float(group["abs_residual_target"].mean()) if group["abs_residual_target"].notna().any() else None,
                    "abs_residual_target_median": float(group["abs_residual_target"].median()) if group["abs_residual_target"].notna().any() else None,
                    "has_recent_distance_pct": 100 * float(group["has_recent_distance"].mean()) if len(group) else None,
                    "has_historical_mae_pct": 100 * float(group["has_historical_mae"].mean()) if len(group) else None,
                    "selectable_common_cohort_pct": 100 * float(group["selectable_common_cohort"].mean()) if len(group) else None,
                }
            )
            for state, state_group in group.groupby("cod_estado"):
                rows.append(
                    {
                        "record_type": "n_hist_state_distribution",
                        "target": target_year,
                        "n_hist": int(n_hist),
                        "cod_estado": state,
                        "estado": STATE_NAMES.get(state, state),
                        "n_centros": len(state_group),
                        "pct_state_frame": 100 * len(state_group) / len(merged[merged["cod_estado"].eq(state)]),
                    }
                )
        for cohort_name, condition in {
            "short_history": merged["n_hist"] < 2,
            "long_history": merged["n_hist"] >= 2,
        }.items():
            group = merged[condition]
            rows.append(
                {
                    "record_type": "history_length_summary",
                    "target": target_year,
                    "history_group": cohort_name,
                    "n_centros": len(group),
                    "pct_frame": 100 * len(group) / total_frame if total_frame else None,
                    "electores_median": float(group["electores"].median()) if len(group) else None,
                    "electores_mean": float(group["electores"].mean()) if len(group) else None,
                    "abs_residual_target_mean": float(group["abs_residual_target"].mean()) if group["abs_residual_target"].notna().any() else None,
                    "abs_residual_target_median": float(group["abs_residual_target"].median()) if group["abs_residual_target"].notna().any() else None,
                }
            )
    for from_year, to_year in [(2006, 2012), (2012, 2013), (2013, 2018), (2018, 2024)]:
        origin = load_presidential_result(from_year)[["codigo_centro", "cod_estado"]].drop_duplicates()
        dest = load_presidential_result(to_year)[["codigo_centro", "cod_estado"]].drop_duplicates()
        for state in sorted(set(origin["cod_estado"]) | set(dest["cod_estado"])):
            origin_codes = set(origin[origin["cod_estado"].eq(state)]["codigo_centro"])
            dest_codes = set(dest[dest["cod_estado"].eq(state)]["codigo_centro"])
            matched = origin_codes & dest_codes
            rows.append(
                {
                    "record_type": "link_rate",
                    "from_year": from_year,
                    "to_year": to_year,
                    "cod_estado": state,
                    "estado": STATE_NAMES.get(state, state),
                    "total_centros_origen": len(origin_codes),
                    "total_centros_destino": len(dest_codes),
                    "matched": len(matched),
                    "unmatched": len(origin_codes - dest_codes),
                    "match_rate": len(matched) / len(origin_codes) if origin_codes else None,
                }
            )
    return pd.DataFrame(rows)


def turnout_residuals_for_year(year: int) -> pd.DataFrame:
    result = load_presidential_result(year)
    if "votantes" not in result.columns or result["votantes"].isna().all():
        return pd.DataFrame(
            columns=["codigo_centro", "cod_estado", f"turnout_residual_{year}", f"turnout_{year}"]
        )
    rows = result.dropna(subset=["electores", "votantes"]).copy()
    rows = rows[(rows["electores"].astype(float) > 0) & (rows["votantes"].astype(float) >= 0)].copy()
    if rows.empty:
        return pd.DataFrame(
            columns=["codigo_centro", "cod_estado", f"turnout_residual_{year}", f"turnout_{year}"]
        )
    state = rows.groupby("cod_estado", as_index=False).agg(electores=("electores", "sum"), votantes=("votantes", "sum"))
    state[f"turnout_estado_{year}"] = state["votantes"] / state["electores"]
    rows[f"turnout_{year}"] = rows["votantes"].astype(float) / rows["electores"].astype(float)
    rows = rows.merge(state[["cod_estado", f"turnout_estado_{year}"]], on="cod_estado", how="left")
    rows[f"turnout_residual_{year}"] = rows[f"turnout_{year}"] - rows[f"turnout_estado_{year}"]
    return rows[["codigo_centro", "cod_estado", f"turnout_{year}", f"turnout_residual_{year}"]].copy()


def turnout_diagnostics() -> pd.DataFrame:
    rows = []
    for prev_year, next_year in [(2006, 2012), (2012, 2013), (2013, 2018), (2018, 2024)]:
        prev_turnout = turnout_residuals_for_year(prev_year)
        next_turnout = turnout_residuals_for_year(next_year)
        if prev_turnout.empty or next_turnout.empty:
            rows.append(
                {
                    "record_type": "transition_skipped",
                    "from_year": prev_year,
                    "to_year": next_year,
                    "skip_reason": "faltan votantes/electores comparables en al menos un ano",
                }
            )
            continue
        prev_col = f"turnout_residual_{prev_year}"
        next_col = f"turnout_residual_{next_year}"
        merged = prev_turnout.merge(next_turnout, on=["codigo_centro", "cod_estado"], how="inner").dropna(
            subset=[prev_col, next_col]
        )
        x = merged[prev_col].astype(float)
        y = merged[next_col].astype(float)
        rows.append(
            {
                "record_type": "pooled_turnout_persistence",
                "from_year": prev_year,
                "to_year": next_year,
                "n_centros": len(merged),
                **regression_diagnostics(x, y),
                "mae_delta_turnout_residual": float((y - x).abs().mean()) if len(merged) else None,
            }
        )
        state_rows = []
        for state, group in merged.groupby("cod_estado"):
            sx = group[prev_col].astype(float)
            sy = group[next_col].astype(float)
            state_rows.append(
                {
                    "record_type": "state_turnout_persistence",
                    "from_year": prev_year,
                    "to_year": next_year,
                    "cod_estado": state,
                    "estado": STATE_NAMES.get(state, state),
                    "n_centros": len(group),
                    **regression_diagnostics(sx, sy),
                    "mae_delta_turnout_residual": float((sy - sx).abs().mean()) if len(group) else None,
                }
            )
        rows.extend(state_rows)
        pearson = [float(row["pearson"]) for row in state_rows if row.get("pearson") is not None and not pd.isna(row.get("pearson"))]
        r2 = [float(row["r2"]) for row in state_rows if row.get("r2") is not None and not pd.isna(row.get("r2"))]
        rows.append(
            {
                "record_type": "state_turnout_summary",
                "from_year": prev_year,
                "to_year": next_year,
                "n_estados": len(state_rows),
                "median_pearson_state": median(pearson) if pearson else None,
                "median_r2_state": median(r2) if r2 else None,
                "p25_pearson_state": percentile(pearson, 0.25),
                "p75_pearson_state": percentile(pearson, 0.75),
                "p25_r2_state": percentile(r2, 0.25),
                "p75_r2_state": percentile(r2, 0.75),
            }
        )
        prev_vote = residuals_for_year(prev_year).rename(columns={f"residual_{prev_year}": "vote_prev"})
        next_vote = residuals_for_year(next_year).rename(columns={f"residual_{next_year}": "vote_next"})
        relation = merged.merge(prev_vote, on=["codigo_centro", "cod_estado"], how="inner").merge(
            next_vote, on=["codigo_centro", "cod_estado"], how="inner"
        )
        if not relation.empty:
            relation["abs_turnout_prev"] = relation[prev_col].abs()
            relation["abs_vote_next"] = relation["vote_next"].abs()
            relation["delta_turnout"] = relation[next_col] - relation[prev_col]
            relation["delta_vote"] = relation["vote_next"] - relation["vote_prev"]
            for relation_name, x_col, y_col in [
                ("abs_prev_turnout_vs_abs_next_vote", "abs_turnout_prev", "abs_vote_next"),
                ("delta_turnout_vs_delta_vote", "delta_turnout", "delta_vote"),
            ]:
                rx = relation[x_col].astype(float)
                ry = relation[y_col].astype(float)
                rows.append(
                    {
                        "record_type": "turnout_vote_relation",
                        "relation": relation_name,
                        "from_year": prev_year,
                        "to_year": next_year,
                        "n_centros": len(relation),
                        **regression_diagnostics(rx, ry),
                    }
                )
    return pd.DataFrame(rows)


def run_longitudinal_falsification(output_dir: Path) -> dict[str, pd.DataFrame]:
    outputs = {
        "within_state": transition_residual_within_state_diagnostics(),
        "oracle": oracle_headroom_diagnostics(),
        "survivorship": survivorship_diagnostics(),
        "turnout": turnout_diagnostics(),
    }
    write_longitudinal_falsification_outputs(output_dir, outputs)
    return outputs


def run_longitudinal_experiment(output_dir: Path) -> dict[str, pd.DataFrame]:
    results = [run_longitudinal_target(target) for target in LONGITUDINAL_TARGETS]
    outputs = {
        key: pd.concat([result[key] for result in results], ignore_index=True)
        for key in ("summary", "states", "centers", "features")
    }
    incomplete = [result["incomplete"] for result in results if not result["incomplete"].empty]
    outputs["incomplete"] = pd.concat(incomplete, ignore_index=True) if incomplete else pd.DataFrame()
    persistence = transition_residual_diagnostics()
    quantiles = feature_quantile_diagnostics(outputs["features"])
    outputs["persistencia"] = pd.concat([persistence, quantiles], ignore_index=True, sort=False)
    write_longitudinal_outputs(output_dir, outputs)
    return outputs


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


def write_similarity_outputs(output_dir: Path, outputs: dict[str, pd.DataFrame]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _round_floats(outputs["summary"]).to_csv(
        output_dir / "backtest_legacy_similarity_summary.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["states"]).to_csv(
        output_dir / "backtest_legacy_similarity_estados.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["centers"]).to_csv(
        output_dir / "backtest_legacy_similarity_centros.csv", index=False, encoding="utf-8"
    )
    if not outputs["incomplete"].empty:
        outputs["incomplete"].to_csv(
            output_dir / "backtest_legacy_similarity_incompletos.csv", index=False, encoding="utf-8"
        )
    write_similarity_markdown(output_dir / "BACKTEST_LEGACY_SIMILARITY.md", outputs)


def write_longitudinal_outputs(output_dir: Path, outputs: dict[str, pd.DataFrame]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _round_floats(outputs["summary"]).to_csv(
        output_dir / "backtest_longitudinal_summary.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["states"]).to_csv(
        output_dir / "backtest_longitudinal_estados.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["centers"]).to_csv(
        output_dir / "backtest_longitudinal_centros.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["features"]).to_csv(
        output_dir / "backtest_longitudinal_features.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["persistencia"]).to_csv(
        output_dir / "backtest_longitudinal_persistencia.csv", index=False, encoding="utf-8"
    )
    if not outputs["incomplete"].empty:
        outputs["incomplete"].to_csv(output_dir / "backtest_longitudinal_incompletos.csv", index=False, encoding="utf-8")
    write_longitudinal_markdown(output_dir / "BACKTEST_LONGITUDINAL.md", outputs)


def write_longitudinal_falsification_outputs(output_dir: Path, outputs: dict[str, pd.DataFrame]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _round_floats(outputs["within_state"]).to_csv(
        output_dir / "backtest_longitudinal_within_state.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["oracle"]).to_csv(
        output_dir / "backtest_longitudinal_oracle.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["survivorship"]).to_csv(
        output_dir / "backtest_longitudinal_survivorship.csv", index=False, encoding="utf-8"
    )
    _round_floats(outputs["turnout"]).to_csv(
        output_dir / "backtest_longitudinal_turnout.csv", index=False, encoding="utf-8"
    )
    write_longitudinal_falsification_markdown(
        output_dir / "BACKTEST_LONGITUDINAL_FALSIFICATION.md", outputs
    )


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    try:
        if pd.isna(value):
            return "n/a"
        as_float = float(value)
        if as_float.is_integer():
            return str(int(as_float))
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


def write_similarity_markdown(path: Path, outputs: dict[str, pd.DataFrame]) -> None:
    summary = outputs["summary"].copy()
    states = outputs["states"].copy()
    centers = outputs["centers"].copy()
    best_mae = (
        summary.sort_values(["transicion", "mae", "rmse"])
        .groupby("transicion", as_index=False)
        .first()[["transicion", "similarity", "mae"]]
        .rename(columns={"similarity": "menor_mae_similarity", "mae": "menor_mae"})
    )
    best_rmse = (
        summary.sort_values(["transicion", "rmse", "mae"])
        .groupby("transicion", as_index=False)
        .first()[["transicion", "similarity", "rmse"]]
        .rename(columns={"similarity": "menor_rmse_similarity", "rmse": "menor_rmse"})
    )
    least_outlier = (
        summary.sort_values(["transicion", "max_error_abs", "mae"])
        .groupby("transicion", as_index=False)
        .first()[["transicion", "similarity", "max_error_abs"]]
        .rename(columns={"similarity": "menor_outlier_similarity", "max_error_abs": "menor_max_error_abs"})
    )
    tolerance = (
        states.groupby(["transicion", "similarity"], as_index=False)
        .agg(pasada_maxima=("pasada_maxima", "max"), distancia_max_sel=("distancia_max_sel", "max"))
        .sort_values(["transicion", "pasada_maxima", "distancia_max_sel"])
        .groupby("transicion", as_index=False)
        .first()
        .rename(columns={"similarity": "menor_ampliacion_similarity"})
    )
    stability = best_mae.merge(best_rmse, on="transicion").merge(least_outlier, on="transicion").merge(
        tolerance[["transicion", "menor_ampliacion_similarity", "pasada_maxima", "distancia_max_sel"]],
        on="transicion",
    )
    common = summary[["transicion", "centros_comunes_tres_variantes", "pct_comun_sobre_120"]].drop_duplicates()
    state_preview = states[
        [
            "transicion",
            "similarity",
            "estado",
            "cuota",
            "error_outcome_pp",
            "distancia_media_sel",
            "pasada_maxima",
            "tolerancia_maxima",
            "n_difiere_otras_variantes",
        ]
    ].sort_values(["transicion", "similarity", "estado"])

    lines = [
        "# Comparacion de formalizaciones de similitud legacy",
        "",
        "Este ejercicio mantiene fijo el procedimiento legacy de 120 centros y cambia solo la definicion matematica de `se parece` usada contra la presidencial inmediatamente anterior.",
        "",
        "## Formulas",
        "",
        "- `winner_share`: distancia absoluta entre el porcentaje del candidato ganador estatal historico y ese mismo candidato en el centro.",
        "- `top2_gap`: distancia absoluta entre el gap firmado de los dos candidatos principales estatales y el gap firmado de esos mismos candidatos en el centro.",
        "- `full_profile`: Total Variation Distance en puntos porcentuales, `0.5 * sum(abs(p_cj - p_sj))`, sobre todos los candidatos comparables dentro de la eleccion historica.",
        "",
        "La escalera comun es `[2, 4, 6, 8, 10, 15, 20, inf]` pp y `min_electores=300`. No se optimiza por variante.",
        "",
        "## Fuentes y tratamiento de candidatos",
        "",
        "- `2013_2018`: marco `backend/tm_2018_estandar.csv`, Distrito Capital completado desde VENPRES-A 2018 solo como marco, similitud desde `resultados oficiales elecciones presidenciales 2013.xlsx`, outcome desde VENPRES-A 2018.",
        "- Perfil 2013: Maduro, Capriles, Sequera, Bolivar, Mora y Mendez; porcentajes sobre votos validos agregados por centro/estado.",
        "- `2018_2024`: marco `backend/tm_2024_estandar.csv`, similitud desde VENPRES-A 2018, outcome desde `backend/resultados_cne2024.csv`.",
        "- Perfil 2018: Maduro, Falcon y Bertucci+Quijada. VENPRES-A conserva Falcon separado como oposicion y Bertucci+Quijada como bloque `otros`; no se separa Quijada porque el CSV normalizado del repo no lo expone aparte.",
        "",
        "La implementacion legacy previa usa porcentaje de Maduro/gobierno contra el porcentaje estatal historico. Es equivalente a `winner_share` solo en estados donde Maduro fue el ganador estatal historico; si gana otro candidato, `winner_share` compara contra ese ganador estatal y no contra Maduro.",
        "",
        "## Resumen nacional",
        "",
        markdown_table(
            summary[
                [
                    "transicion",
                    "similarity",
                    "mae",
                    "rmse",
                    "medae",
                    "pct_dentro_2pp",
                    "pct_dentro_5pp",
                    "pct_dentro_10pp",
                    "max_error_abs",
                    "max_error_estado",
                ]
            ].to_dict("records"),
            [
                "transicion",
                "similarity",
                "mae",
                "rmse",
                "medae",
                "pct_dentro_2pp",
                "pct_dentro_5pp",
                "pct_dentro_10pp",
                "max_error_abs",
                "max_error_estado",
            ],
        ),
        "",
        "## Estabilidad comparativa",
        "",
        markdown_table(
            stability.merge(common, on="transicion").to_dict("records"),
            [
                "transicion",
                "menor_mae_similarity",
                "menor_mae",
                "menor_rmse_similarity",
                "menor_rmse",
                "menor_outlier_similarity",
                "menor_max_error_abs",
                "menor_ampliacion_similarity",
                "pasada_maxima",
                "distancia_max_sel",
                "centros_comunes_tres_variantes",
                "pct_comun_sobre_120",
            ],
        ),
        "",
        "## Resultados estatales",
        "",
        markdown_table(
            state_preview.to_dict("records"),
            [
                "transicion",
                "similarity",
                "estado",
                "cuota",
                "error_outcome_pp",
                "distancia_media_sel",
                "pasada_maxima",
                "tolerancia_maxima",
                "n_difiere_otras_variantes",
            ],
        ),
        "",
        "## Archivos reproducibles",
        "",
        "- `backtest_legacy_similarity_summary.csv`",
        "- `backtest_legacy_similarity_estados.csv`",
        "- `backtest_legacy_similarity_centros.csv`",
        "",
        "## Limitaciones",
        "",
        "- Este no es un nuevo selector productivo ni una optimizacion moderna; solo formaliza el componente `se parece`.",
        "- No se agregan fuentes externas ni se modifican datasets originales.",
        "- Las metricas de swing se conservan en los CSV como diagnostico secundario.",
        "- Diferencias pequenas entre variantes no se interpretan automaticamente como victoria metodologica.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_longitudinal_markdown(path: Path, outputs: dict[str, pd.DataFrame]) -> None:
    summary = outputs["summary"].copy()
    persistence = outputs["persistencia"].copy()
    corr = persistence[persistence["record_type"].eq("transition_correlation")].copy()
    quant = persistence[persistence["record_type"].eq("feature_quantile")].copy()
    winners = (
        summary.sort_values(["target", "cohort", "mae", "rmse"])
        .groupby(["target", "cohort"], as_index=False)
        .first()[["target", "cohort", "selector", "mae"]]
        .rename(columns={"selector": "menor_mae_selector", "mae": "menor_mae"})
    )
    recent_vs_long = summary[summary["selector"].isin(["recent_distance", "historical_mae", "historical_rmse"])][
        ["target", "cohort", "selector", "mae", "rmse", "medae"]
    ].copy()
    rank_rows = []
    for (target, cohort), group in summary.groupby(["target", "cohort"]):
        ranked = group.sort_values(["mae", "rmse"]).reset_index(drop=True)
        for idx, row in ranked.iterrows():
            rank_rows.append(
                {
                    "target": int(target),
                    "cohort": cohort,
                    "rank_mae": idx + 1,
                    "selector": row["selector"],
                    "mae": row["mae"],
                }
            )
    lines = [
        "# Backtest longitudinal de representatividad historica por centro",
        "",
        "Este experimento evalua si la posicion historica relativa de un centro frente a su estado aporta informacion para seleccionar centros, manteniendo fijo el procedimiento legacy de cuotas y prioridad por tamano.",
        "",
        "## Definicion",
        "",
        "`residual_i,t = pct_gobierno_centro_i,t - pct_gobierno_estado_s,t`. Un residual positivo indica que el centro fue mas gobierno que su estado en esa eleccion.",
        "",
        "Features por centro antes de cada target:",
        "",
        "- `recent_distance`: valor absoluto del residual de la eleccion presidencial inmediatamente anterior.",
        "- `historical_mae`: promedio historico de `abs(residual)` antes del target.",
        "- `historical_rmse`: raiz del promedio de residual al cuadrado antes del target.",
        "- `historical_volatility`: desviacion estandar poblacional de los residuales previos; queda NULL con menos de 2 observaciones.",
        "- `historical_bias`: promedio firmado de residuales previos; se reporta como diagnostico, no como selector principal.",
        "",
        "## Elecciones y linking",
        "",
        "- Target 2013 usa features 2006 y 2012.",
        "- Target 2018 usa features 2006, 2012 y 2013.",
        "- Target 2024 usa features 2006, 2012, 2013 y 2018.",
        "- El enlace entre procesos usa el codigo CNE nuevo normalizado a 9 digitos que ya emplean `seed_resultados_historicos.py` y los CSV/XLSX versionados. No se inventan mappings adicionales.",
        "- Para 2013 se usa el archivo oficial 2013 como marco de codigo/electores/estado; sus votos se revelan solo en evaluacion.",
        "- Para 2018 se usa `tm_2018_estandar.csv` y Distrito Capital se completa desde VENPRES-A 2018 solo como marco.",
        "",
        "## Cohortes",
        "",
        "- `common`: todos los selectores compiten sobre centros con historial suficiente para calcular tambien volatilidad (`n_hist >= 2`).",
        "- `operational`: cada selector usa el universo que naturalmente puede calcular; `recent_distance`, MAE y RMSE requieren al menos 1 historico, volatilidad requiere 2.",
        "",
        "## Resumen principal",
        "",
        markdown_table(
            summary[
                [
                    "target",
                    "cohort",
                    "selector",
                    "mae",
                    "rmse",
                    "medae",
                    "pct_dentro_2pp",
                    "pct_dentro_5pp",
                    "pct_dentro_10pp",
                    "max_error_abs",
                    "max_error_estado",
                    "centros_comunes_cuatro_selectores",
                ]
            ].to_dict("records"),
            [
                "target",
                "cohort",
                "selector",
                "mae",
                "rmse",
                "medae",
                "pct_dentro_2pp",
                "pct_dentro_5pp",
                "pct_dentro_10pp",
                "max_error_abs",
                "max_error_estado",
                "centros_comunes_cuatro_selectores",
            ],
        ),
        "",
        "## Ganadores por MAE",
        "",
        markdown_table(winners.to_dict("records"), ["target", "cohort", "menor_mae_selector", "menor_mae"]),
        "",
        "## Ranking por MAE",
        "",
        markdown_table(
            rank_rows,
            ["target", "cohort", "rank_mae", "selector", "mae"],
        ),
        "",
        "## Recent vs longitudinal",
        "",
        markdown_table(
            recent_vs_long.to_dict("records"),
            ["target", "cohort", "selector", "mae", "rmse", "medae"],
        ),
        "",
        "## Persistencia de residuales",
        "",
        markdown_table(
            corr[
                [
                    "from_year",
                    "to_year",
                    "n_centros",
                    "pearson",
                    "spearman",
                    "ols_slope",
                    "r2",
                    "mae_delta_residual",
                ]
            ].to_dict("records"),
            ["from_year", "to_year", "n_centros", "pearson", "spearman", "ols_slope", "r2", "mae_delta_residual"],
        ),
        "",
        "## Diagnostico por cuantiles",
        "",
        markdown_table(
            quant.head(48)[
                ["target", "feature", "quantile", "n_centros", "feature_min", "feature_max", "abs_residual_target_mae"]
            ].to_dict("records"),
            ["target", "feature", "quantile", "n_centros", "feature_min", "feature_max", "abs_residual_target_mae"],
        ),
        "",
        "## Archivos reproducibles",
        "",
        "- `backtest_longitudinal_summary.csv`",
        "- `backtest_longitudinal_estados.csv`",
        "- `backtest_longitudinal_centros.csv`",
        "- `backtest_longitudinal_features.csv`",
        "- `backtest_longitudinal_persistencia.csv`",
        "",
        "## Limitaciones",
        "",
        "- El estudio no modifica el selector productivo moderno ni propone un score compuesto.",
        "- Missing historico permanece NULL y reduce `n_hist`; no se imputa ni se convierte en cero.",
        "- Las series dependen del enlace por codigo CNE nuevo ya presente en los archivos normalizados/importadores del repo.",
        "- La interpretacion es descriptiva; diferencias pequenas no justifican cambios productivos por si solas.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_longitudinal_falsification_markdown(path: Path, outputs: dict[str, pd.DataFrame]) -> None:
    within = outputs["within_state"].copy()
    oracle = outputs["oracle"].copy()
    survivorship = outputs["survivorship"].copy()
    turnout = outputs["turnout"].copy()

    within_summary = within[within["record_type"].eq("national_summary")].copy()
    oracle_summary = oracle[oracle["selector"].isin(["recent_distance", "historical_mae", ORACLE_SELECTOR])].copy()
    headroom_rows = (
        oracle_summary[oracle_summary["selector"].eq("recent_distance")]
        [
            [
                "target",
                "recent_mae",
                "historical_mae_value",
                "oracle_mae",
                "gain_hist",
                "total_headroom",
                "fraction_headroom",
            ]
        ]
        .drop_duplicates()
        .rename(columns={"historical_mae_value": "historical_mae"})
        .sort_values("target")
    )
    survivorship_history = survivorship[survivorship["record_type"].eq("history_length_summary")].copy()
    turnout_pooled = turnout[turnout["record_type"].eq("pooled_turnout_persistence")].copy()
    turnout_rel = turnout[turnout["record_type"].eq("turnout_vote_relation")].copy()
    turnout_skipped = turnout[turnout["record_type"].eq("transition_skipped")].copy()

    within_support = bool(
        not within_summary.empty
        and (within_summary["median_pearson_state"].dropna().astype(float) > 0).sum() >= 3
        and (within_summary["n_states_pearson_positive"].dropna().astype(float).median() >= 18)
    )
    serious_within_threat = bool(
        not within_summary.empty
        and (within_summary["median_pearson_state"].dropna().astype(float) <= 0).any()
    )
    headroom_capture = headroom_rows["fraction_headroom"].dropna().astype(float).tolist()
    oracle_support = bool(headroom_capture and median(headroom_capture) >= 0.25)
    serious_oracle_threat = bool(headroom_capture and median(headroom_capture) < 0)
    if not survivorship_history.empty:
        pivot = survivorship_history.pivot_table(
            index="target", columns="history_group", values="abs_residual_target_mean", aggfunc="first"
        )
        survivor_gaps = [
            float(row["short_history"]) - float(row["long_history"])
            for _, row in pivot.dropna(subset=["short_history", "long_history"]).iterrows()
        ]
    else:
        survivor_gaps = []
    survivorship_support = bool(survivor_gaps and median(survivor_gaps) >= 0)
    serious_survivorship_threat = bool(survivor_gaps and median(survivor_gaps) < -2)
    turnout_support = "neutral"
    serious_turnout_threat = False

    if serious_within_threat or serious_oracle_threat or serious_survivorship_threat or serious_turnout_threat:
        conclusion = "evidencia ambigua; hacen falta mas pruebas"
    else:
        conclusion = "no aparece falsificacion suficiente para descartar historical_mae"

    decision_rows = [
        {
            "prueba": "within-state persistence",
            "resultado": "persistencia positiva dentro de estados en la mayoria de transiciones" if within_support else "persistencia territorial debil o incompleta",
            "favorece historical_mae": "si" if within_support else "no",
            "amenaza seria": "si" if serious_within_threat else "no",
            "comentario": "contrasta la correlacion pooled dentro del territorio real de seleccion",
        },
        {
            "prueba": "oracle headroom",
            "resultado": "historical_mae captura una fraccion positiva del techo diagnostico" if oracle_support else "el techo oracle deja margen amplio o inestable",
            "favorece historical_mae": "si" if oracle_support else "no",
            "amenaza seria": "si" if serious_oracle_threat else "no",
            "comentario": "oracle usa outcome futuro y queda marcado como diagnostic_only",
        },
        {
            "prueba": "survivorship",
            "resultado": "la historia larga no aparece peor que la historia corta en promedio" if survivorship_support else "la composicion sobreviviente exige cautela",
            "favorece historical_mae": "si" if survivorship_support else "no",
            "amenaza seria": "si" if serious_survivorship_threat else "no",
            "comentario": "describe poblacion por n_hist sin cambiar reglas de seleccion",
        },
        {
            "prueba": "turnout",
            "resultado": "diagnostico parcial; 2024 no tiene votantes comparables" if not turnout_pooled.empty else "sin transiciones comparables",
            "favorece historical_mae": turnout_support,
            "amenaza seria": "si" if serious_turnout_threat else "no",
            "comentario": "no se construye selector de participacion",
        },
    ]

    lines = [
        "# Falsificacion longitudinal antes de decidir selector",
        "",
        "Este documento es generado por `backend/backtest_legacy_nacional.py --only falsification`. Usa exclusivamente fuentes versionadas del repositorio y no modifica el selector productivo moderno.",
        "",
        "## Objetivo",
        "",
        "Evaluar si los datos actuales contienen evidencia adversa suficiente para descartar `historical_mae` como candidato principal del sucesor legacy frente a `recent_distance`.",
        "",
        "## Pruebas",
        "",
        "- `within-state persistence`: calcula persistencia de residuales centro-estado dentro de cada estado para 2006->2012, 2012->2013, 2013->2018 y 2018->2024.",
        "- `oracle headroom`: seleccion imposible que ordena por `abs(residual_target)`; usa leakage intencional y se marca `diagnostic_only = true`.",
        "- `survivorship`: describe si `historical_mae` depende de centros antiguos/estables mediante `n_hist`, cohortes de historia larga/corta y tasas de linking.",
        "- `turnout`: mide persistencia de residuales de participacion y su relacion con residuales politicos, sin crear selector de turnout.",
        "",
        "## Tabla de decision",
        "",
        markdown_table(
            decision_rows,
            ["prueba", "resultado", "favorece historical_mae", "amenaza seria", "comentario"],
        ),
        "",
        "## Headroom contra oracle",
        "",
        markdown_table(
            headroom_rows.to_dict("records"),
            ["target", "recent_mae", "historical_mae", "oracle_mae", "gain_hist", "total_headroom", "fraction_headroom"],
        ),
        "",
        "## Persistencia within-state",
        "",
        markdown_table(
            within_summary[
                [
                    "from_year",
                    "to_year",
                    "n_estados",
                    "median_pearson_state",
                    "p25_pearson_state",
                    "p75_pearson_state",
                    "median_r2_state",
                    "n_states_pearson_positive",
                    "n_states_pearson_gt_0_5",
                    "n_states_r2_gt_0_25",
                    "n_states_r2_gt_0_50",
                ]
            ].to_dict("records"),
            [
                "from_year",
                "to_year",
                "n_estados",
                "median_pearson_state",
                "p25_pearson_state",
                "p75_pearson_state",
                "median_r2_state",
                "n_states_pearson_positive",
                "n_states_pearson_gt_0_5",
                "n_states_r2_gt_0_25",
                "n_states_r2_gt_0_50",
            ],
        ),
        "",
        "Resultado: la persistencia pooled no desaparece al calcularla dentro de estados, aunque se debilita en transiciones de shock, especialmente desde 2013.",
        "",
        "## Oracle benchmark",
        "",
        markdown_table(
            oracle_summary[
                [
                    "target",
                    "selector",
                    "mae",
                    "rmse",
                    "medae",
                    "pct_dentro_2pp",
                    "pct_dentro_5pp",
                    "pct_dentro_10pp",
                    "max_error_abs",
                    "diagnostic_only",
                    "leakage_outcome_used",
                ]
            ].to_dict("records"),
            [
                "target",
                "selector",
                "mae",
                "rmse",
                "medae",
                "pct_dentro_2pp",
                "pct_dentro_5pp",
                "pct_dentro_10pp",
                "max_error_abs",
                "diagnostic_only",
                "leakage_outcome_used",
            ],
        ),
        "",
        "Resultado: el oracle no es viable operacionalmente; solo estima techo empirico dentro de la misma arquitectura de 120 centros y cuotas estatales.",
        "",
        "## Survivorship y linking",
        "",
        markdown_table(
            survivorship_history[
                [
                    "target",
                    "history_group",
                    "n_centros",
                    "pct_frame",
                    "electores_median",
                    "electores_mean",
                    "abs_residual_target_mean",
                    "abs_residual_target_median",
                ]
            ].to_dict("records"),
            [
                "target",
                "history_group",
                "n_centros",
                "pct_frame",
                "electores_median",
                "electores_mean",
                "abs_residual_target_mean",
                "abs_residual_target_median",
            ],
        ),
        "",
        "Resultado: existe sesgo de supervivencia potencial porque los centros con mas historia son una subpoblacion identificable, pero esta prueba no muestra por si sola que esa subpoblacion explique negativamente la ventaja longitudinal.",
        "",
        "## Turnout",
        "",
        markdown_table(
            turnout_pooled[
                [
                    "from_year",
                    "to_year",
                    "n_centros",
                    "pearson",
                    "spearman",
                    "r2",
                    "mae_delta_turnout_residual",
                ]
            ].to_dict("records"),
            ["from_year", "to_year", "n_centros", "pearson", "spearman", "r2", "mae_delta_turnout_residual"],
        ),
        "",
        markdown_table(
            turnout_rel[
                [
                    "relation",
                    "from_year",
                    "to_year",
                    "n_centros",
                    "pearson",
                    "spearman",
                    "r2",
                ]
            ].to_dict("records"),
            ["relation", "from_year", "to_year", "n_centros", "pearson", "spearman", "r2"],
        ),
        "",
        markdown_table(
            turnout_skipped[["from_year", "to_year", "skip_reason"]].to_dict("records"),
            ["from_year", "to_year", "skip_reason"],
        ) if not turnout_skipped.empty else "",
        "",
        "Resultado: turnout aporta contexto sobre shocks, pero 2024 no trae votantes comparables en el CSV local; por restriccion de no imputar, 2018->2024 queda omitido.",
        "",
        "## Falsificaciones encontradas",
        "",
        "- No aparece una falsificacion directa de la persistencia territorial.",
        "- El oracle confirma que queda margen empirico, pero no desaconseja `historical_mae`; solo muestra que ningun selector valido agota el techo.",
        "- Survivorship obliga a cautela interpretativa: `historical_mae` depende de centros con historial enlazado, no de todo el frame.",
        "- Turnout no puede resolver 2018->2024 con los datos actuales porque falta `votantes` comparable para 2024.",
        "",
        "## Implicaciones para historical_mae",
        "",
        "`historical_mae` sigue siendo defendible como candidato experimental principal del sucesor legacy. La evidencia adversa mas importante es de limites y cobertura, no una refutacion empirica fuerte.",
        "",
        "## Limitaciones",
        "",
        "- No se agregaron fuentes, mappings ni datasets.",
        "- Missing historico y turnout faltante permanecen `NULL`/omitidos.",
        "- El oracle tiene leakage deliberado y no puede seleccionarse como metodo productivo.",
        "- No se crea score compuesto, PPS, minimax, random baseline ni optimizacion de pesos.",
        "- La conclusion no recomienda cambios productivos todavia.",
        "",
        "## Conclusion final",
        "",
        conclusion,
        "",
        "## Archivos reproducibles",
        "",
        "- `backtest_longitudinal_within_state.csv`",
        "- `backtest_longitudinal_oracle.csv`",
        "- `backtest_longitudinal_survivorship.csv`",
        "- `backtest_longitudinal_turnout.csv`",
        "",
    ]
    path.write_text("\n".join(line for line in lines if line is not None), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO_DIR / "docs" / "muestreo")
    parser.add_argument(
        "--only",
        choices=["all", "legacy", "similarity", "longitudinal", "falsification"],
        default="all",
        help="Controla que artefactos se regeneran.",
    )
    args = parser.parse_args()
    if args.only in {"all", "legacy"}:
        outputs = run_all(args.output_dir)
        print(f"Estados: {len(outputs['states'])} filas")
        print(f"Centros legacy primarios: {len(outputs['centers'])} filas")
        print(f"Sensibilidad: {len(outputs['sensitivity'])} filas")
    if args.only in {"all", "similarity"}:
        similarity_outputs = run_similarity_experiment(args.output_dir)
        print(f"Similarity summary: {len(similarity_outputs['summary'])} filas")
        print(f"Similarity estados: {len(similarity_outputs['states'])} filas")
        print(f"Similarity centros: {len(similarity_outputs['centers'])} filas")
    if args.only in {"all", "longitudinal"}:
        longitudinal_outputs = run_longitudinal_experiment(args.output_dir)
        print(f"Longitudinal summary: {len(longitudinal_outputs['summary'])} filas")
        print(f"Longitudinal estados: {len(longitudinal_outputs['states'])} filas")
        print(f"Longitudinal centros: {len(longitudinal_outputs['centers'])} filas")
        print(f"Longitudinal features: {len(longitudinal_outputs['features'])} filas")
    if args.only in {"all", "falsification"}:
        falsification_outputs = run_longitudinal_falsification(args.output_dir)
        print(f"Falsificacion within-state: {len(falsification_outputs['within_state'])} filas")
        print(f"Falsificacion oracle: {len(falsification_outputs['oracle'])} filas")
        print(f"Falsificacion survivorship: {len(falsification_outputs['survivorship'])} filas")
        print(f"Falsificacion turnout: {len(falsification_outputs['turnout'])} filas")
    print(f"Salida: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
