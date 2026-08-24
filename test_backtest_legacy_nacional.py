import math
from inspect import signature

import pandas as pd

from backend.backtest_legacy_nacional import (
    BASE_PER_STATE,
    EXTRAS_DHONDT,
    N_BASE,
    aggregate_pct,
    allocate_dhondt_quotas,
    code9,
    evaluate_selection,
    select_legacy_similarity,
    select_legacy,
    similarity_distance,
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
