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
    select_legacy,
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
