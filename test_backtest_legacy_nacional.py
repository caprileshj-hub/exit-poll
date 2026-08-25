import math
from inspect import signature

import pandas as pd

import backend.backtest_legacy_nacional as bln
from backend.backtest_legacy_nacional import (
    BASE_PER_STATE,
    EXTRAS_DHONDT,
    N_BASE,
    ORACLE_SELECTOR,
    aggregate_pct,
    allocate_dhondt_quotas,
    code9,
    evaluate_selection,
    longitudinal_feature_values,
    LONGITUDINAL_TARGETS,
    residual,
    select_oracle_diagnostic,
    select_longitudinal_feature,
    select_legacy_similarity,
    select_legacy,
    similarity_distance,
    turnout_residuals_for_year,
)


def _frame_24_states() -> pd.DataFrame:
    rows = []
    for state in range(1, 25):
        for idx in range(1, 4):
            rows.append(
                {
                    "codigo_centro": f"{state:02d}0000{idx:03d}",
                    "cod_estado": f"{state:02d}",
                    "nombre_centro": f"C {state}-{idx}",
                    "estado": f"E{state:02d}",
                    "electores": 1000 * state + idx,
                    "mesas": 1,
                    "rank_por_tamano": idx,
                }
            )
    return pd.DataFrame(rows)


def test_dhondt_allocates_72_extras_and_final_120_with_minimum_two():
    quotas = allocate_dhondt_quotas(_frame_24_states())

    assert sum(q - BASE_PER_STATE for q in quotas.values()) == EXTRAS_DHONDT
    assert sum(quotas.values()) == N_BASE
    assert min(quotas.values()) >= 2


def test_legacy_orders_by_size_restarts_on_wider_tolerance_and_excludes_missing_history():
    frame = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "nombre_centro": "grande lejos", "estado": "DC", "electores": 3000, "mesas": 1, "rank_por_tamano": 1},
            {"codigo_centro": "010000002", "cod_estado": "01", "nombre_centro": "medio cerca", "estado": "DC", "electores": 2000, "mesas": 1, "rank_por_tamano": 2},
            {"codigo_centro": "010000003", "cod_estado": "01", "nombre_centro": "chico cerca", "estado": "DC", "electores": 1000, "mesas": 1, "rank_por_tamano": 3},
            {"codigo_centro": "010000004", "cod_estado": "01", "nombre_centro": "sin historico", "estado": "DC", "electores": 4000, "mesas": 1, "rank_por_tamano": 0},
        ]
    )
    historical = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "votos_gobierno": 70, "votos_validos": 100, "votos_oposicion": 30, "votos_otros": 0, "pct_maduro": 70.0},
            {"codigo_centro": "010000002", "cod_estado": "01", "votos_gobierno": 5000, "votos_validos": 10000, "votos_oposicion": 5000, "votos_otros": 0, "pct_maduro": 50.0},
            {"codigo_centro": "010000003", "cod_estado": "01", "votos_gobierno": 5000, "votos_validos": 10000, "votos_oposicion": 5000, "votos_otros": 0, "pct_maduro": 50.0},
        ]
    )

    selected, incomplete = select_legacy(frame, historical, {"01": 3}, [2, 25, math.inf], min_electores=0)

    assert incomplete.empty
    assert list(selected["codigo_centro"]) == ["010000002", "010000003", "010000001"]
    assert list(selected["pasada"]) == [1, 1, 2]
    assert "010000004" not in set(selected["codigo_centro"])


def test_selection_function_cannot_receive_outcome_argument():
    params = set(signature(select_legacy).parameters)

    assert "outcome" not in params
    assert "target" not in params


def test_missing_outcome_is_not_replaced_post_hoc():
    frame = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "nombre_centro": "A", "estado": "DC", "electores": 1000, "mesas": 1, "rank_por_tamano": 1},
            {"codigo_centro": "010000002", "cod_estado": "01", "nombre_centro": "B", "estado": "DC", "electores": 900, "mesas": 1, "rank_por_tamano": 2},
        ]
    )
    selected = frame.copy()
    historical = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "votos_gobierno": 50, "votos_validos": 100, "votos_oposicion": 50, "votos_otros": 0, "pct_maduro": 50.0},
            {"codigo_centro": "010000002", "cod_estado": "01", "votos_gobierno": 50, "votos_validos": 100, "votos_oposicion": 50, "votos_otros": 0, "pct_maduro": 50.0},
        ]
    )
    outcome = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "votos_gobierno": 60, "votos_validos": 100, "votos_oposicion": 40, "votos_otros": 0, "pct_maduro": 60.0},
        ]
    )

    states = evaluate_selection("x", "legacy", frame, selected, historical, outcome, {"01": 2}, "baseline", 0)

    assert states.loc[0, "n_seleccionados"] == 2
    assert states.loc[0, "n_con_outcome"] == 1
    assert states.loc[0, "pct_cobertura_muestra"] == 50.0


def test_vote_aggregate_is_not_simple_average():
    rows = pd.DataFrame(
        [
            {"votos_gobierno": 10, "votos_validos": 100},
            {"votos_gobierno": 900, "votos_validos": 1000},
        ]
    )

    assert round(aggregate_pct(rows), 6) == round(100 * 910 / 1100, 6)


def test_code9_normalizes_xlsx_and_csv_codes_consistently():
    assert code9(10110032) == "010110032"
    assert code9("010110032") == "010110032"
    assert code9("10110032.0") == "010110032"


def test_winner_share_zero_when_center_matches_state_winner_share():
    state = {"maduro": 55.0, "capriles": 45.0}
    center = {"maduro": 55.0, "capriles": 45.0}

    assert similarity_distance(center, state, "winner_share") == 0.0


def test_top2_gap_zero_when_signed_gaps_match():
    state = {"maduro": 52.0, "capriles": 48.0, "otros": 0.0}
    center = {"maduro": 51.0, "capriles": 47.0, "otros": 2.0}

    assert similarity_distance(center, state, "top2_gap") == 0.0


def test_top2_gap_penalizes_candidate_order_inversion():
    state = {"maduro": 60.0, "capriles": 40.0}
    center = {"maduro": 40.0, "capriles": 60.0}

    assert similarity_distance(center, state, "top2_gap") == 40.0


def test_full_profile_total_variation_distance_and_identity():
    state = {"a": 50.0, "b": 45.0, "c": 5.0}
    center = {"a": 52.0, "b": 42.0, "c": 6.0}

    assert similarity_distance(center, state, "full_profile") == 3.0
    assert similarity_distance(state, state, "full_profile") == 0.0


def test_similarity_distances_are_non_negative():
    state = {"a": 70.0, "b": 20.0, "c": 10.0}
    center = {"a": 10.0, "b": 80.0, "c": 10.0}

    assert similarity_distance(center, state, "winner_share") >= 0
    assert similarity_distance(center, state, "top2_gap") >= 0
    assert similarity_distance(center, state, "full_profile") >= 0


def test_similarity_variant_is_only_selection_component_that_changes():
    frame = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "nombre_centro": "A", "estado": "DC", "electores": 3000, "mesas": 1, "rank_por_tamano": 1},
            {"codigo_centro": "010000002", "cod_estado": "01", "nombre_centro": "B", "estado": "DC", "electores": 2000, "mesas": 1, "rank_por_tamano": 2},
            {"codigo_centro": "010000003", "cod_estado": "01", "nombre_centro": "C", "estado": "DC", "electores": 1000, "mesas": 1, "rank_por_tamano": 3},
        ]
    )
    profile = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "cand_maduro": 80, "cand_capriles": 10, "cand_otros": 10, "votos_validos": 100, "pct_maduro": 80.0, "pct_capriles": 10.0, "pct_otros": 10.0},
            {"codigo_centro": "010000002", "cod_estado": "01", "cand_maduro": 50, "cand_capriles": 45, "cand_otros": 5, "votos_validos": 100, "pct_maduro": 50.0, "pct_capriles": 45.0, "pct_otros": 5.0},
            {"codigo_centro": "010000003", "cod_estado": "01", "cand_maduro": 20, "cand_capriles": 75, "cand_otros": 5, "votos_validos": 100, "pct_maduro": 20.0, "pct_capriles": 75.0, "pct_otros": 5.0},
        ]
    )
    common_kwargs = {
        "frame": frame,
        "historical_profile": profile,
        "quotas": {"01": 2},
        "tolerance_ladder_pp": [10, 40, math.inf],
        "min_electores": 0,
    }

    winner, _ = select_legacy_similarity(similarity="winner_share", **common_kwargs)
    gap, _ = select_legacy_similarity(similarity="top2_gap", **common_kwargs)

    assert len(winner) == len(gap) == 2
    assert set(common_kwargs) == {"frame", "historical_profile", "quotas", "tolerance_ladder_pp", "min_electores"}


def test_residual_center_minus_state_and_zero_identity():
    assert residual(57.0, 55.0) == 2.0
    assert residual(55.0, 55.0) == 0.0


def test_longitudinal_features_preserve_missing_and_bias_sign():
    values = longitudinal_feature_values([2.0, None, -4.0])

    assert values["n_hist"] == 2
    assert values["recent_distance"] == 4.0
    assert values["historical_mae"] == 3.0
    assert round(values["historical_rmse"], 6) == round(math.sqrt(10), 6)
    assert values["historical_bias"] == -1.0
    assert values["abs_historical_bias"] == 1.0
    assert values["historical_volatility"] == 3.0


def test_longitudinal_volatility_null_with_less_than_two_observations():
    values = longitudinal_feature_values([2.0, None])

    assert values["n_hist"] == 1
    assert values["historical_volatility"] is None


def test_longitudinal_target_windows_do_not_include_target_or_future():
    assert LONGITUDINAL_TARGETS[2013] == [2006, 2012]
    assert LONGITUDINAL_TARGETS[2018] == [2006, 2012, 2013]
    assert LONGITUDINAL_TARGETS[2024] == [2006, 2012, 2013, 2018]
    for target, years in LONGITUDINAL_TARGETS.items():
        assert all(year < target for year in years)


def test_longitudinal_selector_changes_only_feature_column():
    features = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "estado": "DC", "nombre_centro": "A", "electores": 3000, "rank_por_tamano": 1, "n_hist": 2, "recent_distance": 8.0, "historical_mae": 1.0, "historical_rmse": 1.0, "historical_volatility": 1.0},
            {"codigo_centro": "010000002", "cod_estado": "01", "estado": "DC", "nombre_centro": "B", "electores": 2000, "rank_por_tamano": 2, "n_hist": 2, "recent_distance": 1.0, "historical_mae": 8.0, "historical_rmse": 8.0, "historical_volatility": 8.0},
            {"codigo_centro": "010000003", "cod_estado": "01", "estado": "DC", "nombre_centro": "C", "electores": 1000, "rank_por_tamano": 3, "n_hist": 2, "recent_distance": 1.0, "historical_mae": 1.0, "historical_rmse": 1.0, "historical_volatility": 1.0},
        ]
    )
    kwargs = {
        "features": features,
        "quotas": {"01": 2},
        "cohort": "common",
        "tolerance_ladder_pp": [2, 10, math.inf],
    }

    recent, _ = select_longitudinal_feature(selector="recent_distance", **kwargs)
    mae, _ = select_longitudinal_feature(selector="historical_mae", **kwargs)

    assert list(recent["codigo_centro"]) == ["010000002", "010000003"]
    assert list(mae["codigo_centro"]) == ["010000001", "010000003"]
    assert set(kwargs) == {"features", "quotas", "cohort", "tolerance_ladder_pp"}


def test_within_state_persistence_never_mixes_states(monkeypatch):
    def fake_residuals_for_year(year):
        values = {
            2006: {"010000001": 1.0, "010000002": 2.0, "020000001": 50.0, "020000002": 60.0},
            2012: {"010000001": 2.0, "010000002": 4.0, "020000001": 100.0, "020000002": 120.0},
            2013: {"010000001": 3.0, "010000002": 6.0, "020000001": 150.0, "020000002": 180.0},
            2018: {"010000001": 4.0, "010000002": 8.0, "020000001": 200.0, "020000002": 240.0},
            2024: {"010000001": 5.0, "010000002": 10.0, "020000001": 250.0, "020000002": 300.0},
        }[year]
        return pd.DataFrame(
            [
                {"codigo_centro": code, "cod_estado": code[:2], f"residual_{year}": value}
                for code, value in values.items()
            ]
        )

    monkeypatch.setattr(bln, "residuals_for_year", fake_residuals_for_year)

    diagnostics = bln.transition_residual_within_state_diagnostics()
    states = diagnostics[diagnostics["record_type"].eq("state_transition")]

    assert set(states["cod_estado"]) == {"01", "02"}
    assert (states["n_centros"] == 2).all()


def test_oracle_is_diagnostic_leakage_and_not_productive_selector():
    features = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "estado": "DC", "nombre_centro": "A", "electores": 3000, "rank_por_tamano": 1, "n_hist": 1, "recent_distance": 8.0, "historical_mae": 8.0},
            {"codigo_centro": "010000002", "cod_estado": "01", "estado": "DC", "nombre_centro": "B", "electores": 2000, "rank_por_tamano": 2, "n_hist": 1, "recent_distance": 1.0, "historical_mae": 1.0},
        ]
    )

    try:
        select_longitudinal_feature(features, {"01": 1}, ORACLE_SELECTOR, "operational", [2, math.inf])
    except ValueError as exc:
        assert "no productivo" in str(exc)
    else:
        raise AssertionError("oracle no debe ser selector longitudinal valido")


def test_oracle_uses_outcome_only_inside_diagnostic_function(monkeypatch):
    features = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "estado": "DC", "nombre_centro": "A", "electores": 3000, "rank_por_tamano": 1},
            {"codigo_centro": "010000002", "cod_estado": "01", "estado": "DC", "nombre_centro": "B", "electores": 2000, "rank_por_tamano": 2},
        ]
    )
    outcome = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "residual_2099": 10.0},
            {"codigo_centro": "010000002", "cod_estado": "01", "residual_2099": 0.5},
        ]
    )
    monkeypatch.setattr(bln, "residuals_for_year", lambda year: outcome)

    selected, incomplete = select_oracle_diagnostic(features, {"01": 1}, 2099, [2, math.inf])

    assert incomplete.empty
    assert list(selected["codigo_centro"]) == ["010000002"]
    assert selected["diagnostic_only"].all()
    assert selected["leakage_outcome_used"].all()


def test_turnout_uses_voters_over_electors_and_center_minus_state(monkeypatch):
    source = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "electores": 100.0, "votantes": 50.0, "votos_validos": 50.0},
            {"codigo_centro": "010000002", "cod_estado": "01", "electores": 300.0, "votantes": 210.0, "votos_validos": 210.0},
        ]
    )
    monkeypatch.setattr(bln, "load_presidential_result", lambda year: source.copy())

    turnout = turnout_residuals_for_year(2099).sort_values("codigo_centro")

    assert list(turnout["turnout_2099"]) == [0.5, 0.7]
    assert round(turnout.iloc[0]["turnout_residual_2099"], 6) == round(0.5 - (260 / 400), 6)
    assert round(turnout.iloc[1]["turnout_residual_2099"], 6) == round(0.7 - (260 / 400), 6)


def test_turnout_missing_voters_returns_null_like_empty_frame(monkeypatch):
    source = pd.DataFrame(
        [
            {"codigo_centro": "010000001", "cod_estado": "01", "electores": 100.0, "votantes": None, "votos_validos": 50.0},
        ]
    )
    monkeypatch.setattr(bln, "load_presidential_result", lambda year: source.copy())

    turnout = turnout_residuals_for_year(2099)

    assert turnout.empty
    assert f"turnout_residual_2099" in turnout.columns


def test_recent_and_historical_selectors_have_no_target_or_outcome_arguments():
    params = set(signature(select_longitudinal_feature).parameters)

    assert "target_year" not in params
    assert "outcome" not in params
    assert "residual_target" not in params
