# Falsificacion longitudinal antes de decidir selector

Este documento es generado por `backend/backtest_legacy_nacional.py --only falsification`. Usa exclusivamente fuentes versionadas del repositorio y no modifica el selector productivo moderno.

## Objetivo

Evaluar si los datos actuales contienen evidencia adversa suficiente para descartar `historical_mae` como candidato principal del sucesor legacy frente a `recent_distance`.

## Pruebas

- `within-state persistence`: calcula persistencia de residuales centro-estado dentro de cada estado para 2006->2012, 2012->2013, 2013->2018 y 2018->2024.
- `oracle headroom`: seleccion imposible que ordena por `abs(residual_target)`; usa leakage intencional y se marca `diagnostic_only = true`.
- `survivorship`: describe si `historical_mae` depende de centros antiguos/estables mediante `n_hist`, cohortes de historia larga/corta y tasas de linking.
- `turnout`: mide persistencia de residuales de participacion y su relacion con residuales politicos, sin crear selector de turnout.

## Tabla de decision

| prueba | resultado | favorece historical_mae | amenaza seria | comentario |
| --- | --- | --- | --- | --- |
| within-state persistence | persistencia positiva dentro de estados en la mayoria de transiciones | si | no | contrasta la correlacion pooled dentro del territorio real de seleccion |
| oracle headroom | el techo oracle deja margen amplio o inestable | no | no | oracle usa outcome futuro y queda marcado como diagnostic_only |
| survivorship | la historia larga no aparece peor que la historia corta en promedio | si | no | describe poblacion por n_hist sin cambiar reglas de seleccion |
| turnout | diagnostico parcial; 2024 no tiene votantes comparables | neutral | no | no se construye selector de participacion |

## Headroom contra oracle

| target | recent_mae | historical_mae | oracle_mae | gain_hist | total_headroom | fraction_headroom |
| --- | --- | --- | --- | --- | --- | --- |
| 2013 | 1.28 | 1.80 | 0.48 | -0.52 | 0.80 | -0.65 |
| 2018 | 3.94 | 2.37 | 0.43 | 1.58 | 3.51 | 0.45 |
| 2024 | 3.39 | 2.89 | 0.38 | 0.49 | 3.00 | 0.16 |

## Persistencia within-state

| from_year | to_year | n_estados | median_pearson_state | p25_pearson_state | p75_pearson_state | median_r2_state | n_states_pearson_positive | n_states_pearson_gt_0_5 | n_states_r2_gt_0_25 | n_states_r2_gt_0_50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2006 | 2012 | 24 | 0.85 | 0.79 | 0.88 | 0.72 | 24 | 23 | 23 | 22 |
| 2012 | 2013 | 24 | 0.98 | 0.97 | 0.98 | 0.95 | 24 | 24 | 24 | 24 |
| 2013 | 2018 | 24 | 0.66 | 0.55 | 0.75 | 0.43 | 24 | 20 | 20 | 8 |
| 2018 | 2024 | 24 | 0.70 | 0.63 | 0.77 | 0.49 | 24 | 21 | 21 | 11 |

Resultado: la persistencia pooled no desaparece al calcularla dentro de estados, aunque se debilita en transiciones de shock, especialmente desde 2013.

## Oracle benchmark

| target | selector | mae | rmse | medae | pct_dentro_2pp | pct_dentro_5pp | pct_dentro_10pp | max_error_abs | diagnostic_only | leakage_outcome_used |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | recent_distance | 1.28 | 1.71 | 0.97 | 0.83 | 0.96 | 1 | 5.49 | 0 | 0 |
| 2013 | historical_mae | 1.80 | 2.33 | 1.57 | 0.67 | 0.96 | 1 | 8.02 | 0 | 0 |
| 2013 | oracle | 0.48 | 0.63 | 0.32 | 1 | 1 | 1 | 1.43 | 1 | 1 |
| 2018 | recent_distance | 3.94 | 4.97 | 3.39 | 0.21 | 0.75 | 0.92 | 12.26 | 0 | 0 |
| 2018 | historical_mae | 2.37 | 3.48 | 1.76 | 0.58 | 0.92 | 1 | 9.73 | 0 | 0 |
| 2018 | oracle | 0.43 | 0.53 | 0.40 | 1 | 1 | 1 | 1.39 | 1 | 1 |
| 2024 | recent_distance | 3.39 | 4.21 | 2.93 | 0.33 | 0.71 | 1 | 9.91 | 0 | 0 |
| 2024 | historical_mae | 2.89 | 3.56 | 2.63 | 0.38 | 0.88 | 1 | 9.10 | 0 | 0 |
| 2024 | oracle | 0.38 | 0.53 | 0.32 | 1 | 1 | 1 | 1.44 | 1 | 1 |

Resultado: el oracle no es viable operacionalmente; solo estima techo empirico dentro de la misma arquitectura de 120 centros y cuotas estatales.

## Survivorship y linking

| target | history_group | n_centros | pct_frame | electores_median | electores_mean | abs_residual_target_mean | abs_residual_target_median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2013 | short_history | 3142 | 22.97 | 324 | 485.85 | 20.02 | 18.81 |
| 2013 | long_history | 10539 | 77.03 | 1195 | 1638.70 | 14.43 | 12.21 |
| 2018 | short_history | 1079 | 7.47 | 304 | 458.87 | 13.43 | 12.77 |
| 2018 | long_history | 13371 | 92.53 | 935 | 1443.53 | 9.06 | 6.77 |
| 2024 | short_history | 1844 | 15.46 | 339 | 583.51 | 17.97 | 16.21 |
| 2024 | long_history | 10083 | 84.54 | 1221 | 1629.13 | 10.68 | 8.11 |

Resultado: existe sesgo de supervivencia potencial porque los centros con mas historia son una subpoblacion identificable, pero esta prueba no muestra por si sola que esa subpoblacion explique negativamente la ventaja longitudinal.

## Turnout

| from_year | to_year | n_centros | pearson | spearman | r2 | mae_delta_turnout_residual |
| --- | --- | --- | --- | --- | --- | --- |
| 2006 | 2012 | 10540 | 0.68 | 0.74 | 0.46 | 0.05 |
| 2012 | 2013 | 13656 | 0.90 | 0.93 | 0.80 | 0.02 |
| 2013 | 2018 | 13260 | 0.23 | 0.19 | 0.05 | 0.12 |

| relation | from_year | to_year | n_centros | pearson | spearman | r2 |
| --- | --- | --- | --- | --- | --- | --- |
| abs_prev_turnout_vs_abs_next_vote | 2006 | 2012 | 10540 | 0.17 | 0.16 | 0.03 |
| delta_turnout_vs_delta_vote | 2006 | 2012 | 10540 | 0.03 | 0.02 | 0.00 |
| abs_prev_turnout_vs_abs_next_vote | 2012 | 2013 | 13656 | 0.19 | 0.19 | 0.04 |
| delta_turnout_vs_delta_vote | 2012 | 2013 | 13656 | -0.09 | -0.13 | 0.01 |
| abs_prev_turnout_vs_abs_next_vote | 2013 | 2018 | 13260 | 0.23 | 0.20 | 0.05 |
| delta_turnout_vs_delta_vote | 2013 | 2018 | 13260 | -0.67 | -0.67 | 0.44 |

| from_year | to_year | skip_reason |
| --- | --- | --- |
| 2018 | 2024 | faltan votantes/electores comparables en al menos un ano |

Resultado: turnout aporta contexto sobre shocks, pero 2024 no trae votantes comparables en el CSV local; por restriccion de no imputar, 2018->2024 queda omitido.

## Falsificaciones encontradas

- No aparece una falsificacion directa de la persistencia territorial.
- El oracle confirma que queda margen empirico, pero no desaconseja `historical_mae`; solo muestra que ningun selector valido agota el techo.
- Survivorship obliga a cautela interpretativa: `historical_mae` depende de centros con historial enlazado, no de todo el frame.
- Turnout no puede resolver 2018->2024 con los datos actuales porque falta `votantes` comparable para 2024.

## Implicaciones para historical_mae

`historical_mae` sigue siendo defendible como candidato experimental principal del sucesor legacy. La evidencia adversa mas importante es de limites y cobertura, no una refutacion empirica fuerte.

## Limitaciones

- No se agregaron fuentes, mappings ni datasets.
- Missing historico y turnout faltante permanecen `NULL`/omitidos.
- El oracle tiene leakage deliberado y no puede seleccionarse como metodo productivo.
- No se crea score compuesto, PPS, minimax, random baseline ni optimizacion de pesos.
- La conclusion no recomienda cambios productivos todavia.

## Conclusion final

no aparece falsificacion suficiente para descartar historical_mae

## Archivos reproducibles

- `backtest_longitudinal_within_state.csv`
- `backtest_longitudinal_oracle.csv`
- `backtest_longitudinal_survivorship.csv`
- `backtest_longitudinal_turnout.csv`
