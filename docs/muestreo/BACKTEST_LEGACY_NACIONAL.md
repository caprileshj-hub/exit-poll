# Backtest legacy nacional de seleccion de centros

Este documento es generado por `backend/backtest_legacy_nacional.py`. Evalua solo la seleccion base de 120 centros: no simula campo, sobremuestreo, reemplazos discrecionales, ponderacion ni proyeccion de ganador.

## Reglas implementadas

- Tamano base nacional: 120 centros.
- Cobertura territorial: 2 centros iniciales por cada una de las 24 entidades, para 48 fijos.
- D'Hondt asigna solo los 72 centros adicionales sobre electores del marco vigente; los 2 garantizados no cuentan como escanos previos.
- Elegibilidad: centro con codigo CNE normalizado presente en la eleccion presidencial inmediatamente anterior.
- Orden interno: centros elegibles por estado de mayor a menor electores, reiniciando desde el mayor en cada tolerancia.
- Variable comun: porcentaje de Maduro sobre votos validos, calculado desde votos agregados.
- Baseline primaria de formalizacion moderna: tolerancias `[2, 4, 6, 8, 10, 15, 20, inf]` pp y `min_electores=300`.
- Comparador `size_only`: misma cuota estatal y mismo requisito de historico, pero toma los centros elegibles mas grandes.

## Fuentes locales

- 2018 usando 2013: `backend/tm_2018_estandar.csv`, `backend/data/2013/presidenciales/resultados oficiales elecciones presidenciales 2013.xlsx`, `backend/data/2018/resultados_venpres_a_2018.csv`.
- 2024 usando 2018: `backend/tm_2024_estandar.csv`, `backend/data/2018/resultados_venpres_a_2018.csv`, `backend/resultados_cne2024.csv`.

Para `2013_2018`, `tm_2018_estandar.csv` no trae Distrito Capital. Se completo el marco de esa entidad desde VENPRES-A 2018 usando solo columnas de marco (`codigo_centro`, nombre, electores y mesas); los votos de 2018 siguen cerrados hasta la fase de evaluacion.

No se sustituyo cobertura parcial con fuentes web.

## Verificacion de cuotas

| transicion | suma_extras_dhondt | suma_cuotas_finales |
| --- | --- | --- |
| 2013_2018 | 72.00 | 120.00 |
| 2018_2024 | 72.00 | 120.00 |

## Metricas nacionales

| transicion | metodo | estados_evaluados | mae_error_outcome_pp | rmse_error_outcome_pp | mae_swing_error_pp | rmse_swing_error_pp | prop_dentro_5pp | centros_con_outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013_2018 | legacy | 24.00 | 3.94 | 4.97 | 3.91 | 4.78 | 0.75 | 120.00 |
| 2013_2018 | size_only | 24.00 | 5.76 | 7.47 | 5.27 | 6.56 | 0.50 | 120.00 |
| 2018_2024 | legacy | 24.00 | 3.39 | 4.21 | 3.41 | 4.30 | 0.71 | 120.00 |
| 2018_2024 | size_only | 24.00 | 7.45 | 8.59 | 3.64 | 4.09 | 0.29 | 120.00 |

## Cobertura de outcomes en muestra primaria

| transicion | metodo | centros_seleccionados | centros_con_outcome | cobertura_pct |
| --- | --- | --- | --- | --- |
| 2013_2018 | legacy | 120.00 | 120.00 | 100.00 |
| 2013_2018 | size_only | 120.00 | 120.00 | 100.00 |
| 2018_2024 | legacy | 120.00 | 120.00 | 100.00 |
| 2018_2024 | size_only | 120.00 | 120.00 | 100.00 |

## Sensibilidad

El grid cruza tres escaleras de tolerancia y tres valores de `min_electores`. Los resultados completos estan en `backtest_legacy_sensibilidad.csv`; estas cifras son una operacionalizacion moderna del juicio legacy, no umbrales historicos reconstruidos.

| transicion | metodo | tolerance_ladder | min_electores | mae_error_outcome_pp | rmse_error_outcome_pp | mae_swing_error_pp | centros_con_outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2013_2018 | legacy | baseline | 0.00 | 3.94 | 4.97 | 3.91 | 120.00 |
| 2013_2018 | size_only | baseline | 0.00 | 5.76 | 7.47 | 5.27 | 120.00 |
| 2013_2018 | legacy | baseline | 300.00 | 3.94 | 4.97 | 3.91 | 120.00 |
| 2013_2018 | size_only | baseline | 300.00 | 5.76 | 7.47 | 5.27 | 120.00 |
| 2013_2018 | legacy | baseline | 600.00 | 3.94 | 4.97 | 3.91 | 120.00 |
| 2013_2018 | size_only | baseline | 600.00 | 5.76 | 7.47 | 5.27 | 120.00 |
| 2013_2018 | legacy | estricta | 0.00 | 3.75 | 5.91 | 3.73 | 120.00 |
| 2013_2018 | size_only | estricta | 0.00 | 5.76 | 7.47 | 5.27 | 120.00 |
| 2013_2018 | legacy | estricta | 300.00 | 3.75 | 5.91 | 3.73 | 120.00 |
| 2013_2018 | size_only | estricta | 300.00 | 5.76 | 7.47 | 5.27 | 120.00 |
| 2013_2018 | legacy | estricta | 600.00 | 3.25 | 4.06 | 3.17 | 120.00 |
| 2013_2018 | size_only | estricta | 600.00 | 5.76 | 7.47 | 5.27 | 120.00 |
| 2013_2018 | legacy | amplia | 0.00 | 3.61 | 4.29 | 3.64 | 120.00 |
| 2013_2018 | size_only | amplia | 0.00 | 5.76 | 7.47 | 5.27 | 120.00 |
| 2013_2018 | legacy | amplia | 300.00 | 3.61 | 4.29 | 3.64 | 120.00 |
| 2013_2018 | size_only | amplia | 300.00 | 5.76 | 7.47 | 5.27 | 120.00 |
| 2013_2018 | legacy | amplia | 600.00 | 3.61 | 4.29 | 3.64 | 120.00 |
| 2013_2018 | size_only | amplia | 600.00 | 5.76 | 7.47 | 5.27 | 120.00 |
| 2018_2024 | legacy | baseline | 0.00 | 3.39 | 4.21 | 3.41 | 120.00 |
| 2018_2024 | size_only | baseline | 0.00 | 7.45 | 8.59 | 3.64 | 120.00 |
| 2018_2024 | legacy | baseline | 300.00 | 3.39 | 4.21 | 3.41 | 120.00 |
| 2018_2024 | size_only | baseline | 300.00 | 7.45 | 8.59 | 3.64 | 120.00 |
| 2018_2024 | legacy | baseline | 600.00 | 3.39 | 4.21 | 3.41 | 120.00 |
| 2018_2024 | size_only | baseline | 600.00 | 7.45 | 8.59 | 3.64 | 120.00 |
| 2018_2024 | legacy | estricta | 0.00 | 4.39 | 5.08 | 4.44 | 120.00 |
| 2018_2024 | size_only | estricta | 0.00 | 7.45 | 8.59 | 3.64 | 120.00 |
| 2018_2024 | legacy | estricta | 300.00 | 4.39 | 5.08 | 4.44 | 120.00 |
| 2018_2024 | size_only | estricta | 300.00 | 7.45 | 8.59 | 3.64 | 120.00 |
| 2018_2024 | legacy | estricta | 600.00 | 4.39 | 5.08 | 4.44 | 120.00 |
| 2018_2024 | size_only | estricta | 600.00 | 7.45 | 8.59 | 3.64 | 120.00 |
| 2018_2024 | legacy | amplia | 0.00 | 3.36 | 4.57 | 3.45 | 120.00 |
| 2018_2024 | size_only | amplia | 0.00 | 7.45 | 8.59 | 3.64 | 120.00 |
| 2018_2024 | legacy | amplia | 300.00 | 3.36 | 4.57 | 3.45 | 120.00 |
| 2018_2024 | size_only | amplia | 300.00 | 7.45 | 8.59 | 3.64 | 120.00 |
| 2018_2024 | legacy | amplia | 600.00 | 3.36 | 4.57 | 3.45 | 120.00 |
| 2018_2024 | size_only | amplia | 600.00 | 7.45 | 8.59 | 3.64 | 120.00 |

## Archivos generados

- `backtest_legacy_2013_2018_estados.csv`
- `backtest_legacy_2018_2024_estados.csv`
- `backtest_legacy_centros.csv`
- `backtest_legacy_sensibilidad.csv`
- `backtest_legacy_cuotas.csv`
- `backtest_legacy_exclusiones.csv`

## Limitaciones

- VENPRES-A 2018 y CNE 2024 se tratan segun la cobertura disponible en repo.
- Si un centro seleccionado no tiene outcome, queda en el denominador de seleccion y fuera del calculo de outcome; no se reemplaza post hoc.
- Las dos transiciones son stress tests electorales. No se ajustaron parametros con conocimiento del outcome.
- El resultado no valida ni invalida el exit poll completo; solo compara reglas de seleccion de centros.
