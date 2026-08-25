# Backtest longitudinal de representatividad historica por centro

Este experimento evalua si la posicion historica relativa de un centro frente a su estado aporta informacion para seleccionar centros, manteniendo fijo el procedimiento legacy de cuotas y prioridad por tamano.

## Definicion

`residual_i,t = pct_gobierno_centro_i,t - pct_gobierno_estado_s,t`. Un residual positivo indica que el centro fue mas gobierno que su estado en esa eleccion.

Features por centro antes de cada target:

- `recent_distance`: valor absoluto del residual de la eleccion presidencial inmediatamente anterior.
- `historical_mae`: promedio historico de `abs(residual)` antes del target.
- `historical_rmse`: raiz del promedio de residual al cuadrado antes del target.
- `historical_volatility`: desviacion estandar poblacional de los residuales previos; queda NULL con menos de 2 observaciones.
- `historical_bias`: promedio firmado de residuales previos; se reporta como diagnostico, no como selector principal.

## Elecciones y linking

- Target 2013 usa features 2006 y 2012.
- Target 2018 usa features 2006, 2012 y 2013.
- Target 2024 usa features 2006, 2012, 2013 y 2018.
- El enlace entre procesos usa el codigo CNE nuevo normalizado a 9 digitos que ya emplean `seed_resultados_historicos.py` y los CSV/XLSX versionados. No se inventan mappings adicionales.
- Para 2013 se usa el archivo oficial 2013 como marco de codigo/electores/estado; sus votos se revelan solo en evaluacion.
- Para 2018 se usa `tm_2018_estandar.csv` y Distrito Capital se completa desde VENPRES-A 2018 solo como marco.

## Cohortes

- `common`: todos los selectores compiten sobre centros con historial suficiente para calcular tambien volatilidad (`n_hist >= 2`).
- `operational`: cada selector usa el universo que naturalmente puede calcular; `recent_distance`, MAE y RMSE requieren al menos 1 historico, volatilidad requiere 2.

## Resumen principal

| target | cohort | selector | mae | rmse | medae | pct_dentro_2pp | pct_dentro_5pp | pct_dentro_10pp | max_error_abs | max_error_estado | centros_comunes_cuatro_selectores |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013.00 | common | historical_mae | 1.49 | 1.65 | 1.48 | 0.67 | 1.00 | 1.00 | 2.94 | Bolivar | 8.00 |
| 2013.00 | common | historical_rmse | 1.28 | 1.50 | 1.36 | 0.75 | 1.00 | 1.00 | 3.06 | Bolivar | 8.00 |
| 2013.00 | common | historical_volatility | 6.47 | 8.85 | 5.66 | 0.12 | 0.46 | 0.88 | 29.39 | Miranda | 8.00 |
| 2013.00 | common | recent_distance | 1.79 | 3.83 | 0.97 | 0.83 | 0.96 | 0.96 | 17.68 | Delta Amacuro | 8.00 |
| 2013.00 | operational | historical_mae | 1.80 | 2.33 | 1.57 | 0.67 | 0.96 | 1.00 | 8.02 | Delta Amacuro | 8.00 |
| 2013.00 | operational | historical_rmse | 1.59 | 2.22 | 1.49 | 0.67 | 0.96 | 1.00 | 8.02 | Delta Amacuro | 8.00 |
| 2013.00 | operational | historical_volatility | 6.47 | 8.85 | 5.66 | 0.12 | 0.46 | 0.88 | 29.39 | Miranda | 8.00 |
| 2013.00 | operational | recent_distance | 1.28 | 1.71 | 0.97 | 0.83 | 0.96 | 1.00 | 5.49 | Delta Amacuro | 8.00 |
| 2018.00 | common | historical_mae | 2.37 | 3.48 | 1.76 | 0.58 | 0.92 | 1.00 | 9.73 | Yaracuy | 2.00 |
| 2018.00 | common | historical_rmse | 2.94 | 3.34 | 2.84 | 0.29 | 0.88 | 1.00 | 6.02 | Merida | 2.00 |
| 2018.00 | common | historical_volatility | 2.73 | 3.84 | 1.64 | 0.54 | 0.83 | 0.96 | 10.85 | Miranda | 2.00 |
| 2018.00 | common | recent_distance | 3.94 | 4.97 | 3.39 | 0.21 | 0.75 | 0.92 | 12.26 | Delta Amacuro | 2.00 |
| 2018.00 | operational | historical_mae | 2.37 | 3.48 | 1.76 | 0.58 | 0.92 | 1.00 | 9.73 | Yaracuy | 2.00 |
| 2018.00 | operational | historical_rmse | 2.94 | 3.34 | 2.84 | 0.29 | 0.88 | 1.00 | 6.02 | Merida | 2.00 |
| 2018.00 | operational | historical_volatility | 2.73 | 3.84 | 1.64 | 0.54 | 0.83 | 0.96 | 10.85 | Miranda | 2.00 |
| 2018.00 | operational | recent_distance | 3.94 | 4.97 | 3.39 | 0.21 | 0.75 | 0.92 | 12.26 | Delta Amacuro | 2.00 |
| 2024.00 | common | historical_mae | 3.09 | 3.82 | 2.78 | 0.33 | 0.92 | 1.00 | 9.63 | Amazonas | 7.00 |
| 2024.00 | common | historical_rmse | 3.16 | 3.85 | 2.89 | 0.42 | 0.79 | 1.00 | 7.30 | Sucre | 7.00 |
| 2024.00 | common | historical_volatility | 3.68 | 4.59 | 2.93 | 0.33 | 0.67 | 1.00 | 9.98 | Sucre | 7.00 |
| 2024.00 | common | recent_distance | 3.39 | 4.21 | 2.93 | 0.33 | 0.71 | 1.00 | 9.91 | Barinas | 7.00 |
| 2024.00 | operational | historical_mae | 2.89 | 3.56 | 2.63 | 0.38 | 0.88 | 1.00 | 9.10 | Sucre | 6.00 |
| 2024.00 | operational | historical_rmse | 3.15 | 3.88 | 2.89 | 0.42 | 0.83 | 1.00 | 7.62 | Amazonas | 6.00 |
| 2024.00 | operational | historical_volatility | 3.68 | 4.59 | 2.93 | 0.33 | 0.67 | 1.00 | 9.98 | Sucre | 6.00 |
| 2024.00 | operational | recent_distance | 3.39 | 4.21 | 2.93 | 0.33 | 0.71 | 1.00 | 9.91 | Barinas | 6.00 |

## Ganadores por MAE

| target | cohort | menor_mae_selector | menor_mae |
| --- | --- | --- | --- |
| 2013.00 | common | historical_rmse | 1.28 |
| 2013.00 | operational | recent_distance | 1.28 |
| 2018.00 | common | historical_mae | 2.37 |
| 2018.00 | operational | historical_mae | 2.37 |
| 2024.00 | common | historical_mae | 3.09 |
| 2024.00 | operational | historical_mae | 2.89 |

## Ranking por MAE

| target | cohort | rank_mae | selector | mae |
| --- | --- | --- | --- | --- |
| 2013.00 | common | 1.00 | historical_rmse | 1.28 |
| 2013.00 | common | 2.00 | historical_mae | 1.49 |
| 2013.00 | common | 3.00 | recent_distance | 1.79 |
| 2013.00 | common | 4.00 | historical_volatility | 6.47 |
| 2013.00 | operational | 1.00 | recent_distance | 1.28 |
| 2013.00 | operational | 2.00 | historical_rmse | 1.59 |
| 2013.00 | operational | 3.00 | historical_mae | 1.80 |
| 2013.00 | operational | 4.00 | historical_volatility | 6.47 |
| 2018.00 | common | 1.00 | historical_mae | 2.37 |
| 2018.00 | common | 2.00 | historical_volatility | 2.73 |
| 2018.00 | common | 3.00 | historical_rmse | 2.94 |
| 2018.00 | common | 4.00 | recent_distance | 3.94 |
| 2018.00 | operational | 1.00 | historical_mae | 2.37 |
| 2018.00 | operational | 2.00 | historical_volatility | 2.73 |
| 2018.00 | operational | 3.00 | historical_rmse | 2.94 |
| 2018.00 | operational | 4.00 | recent_distance | 3.94 |
| 2024.00 | common | 1.00 | historical_mae | 3.09 |
| 2024.00 | common | 2.00 | historical_rmse | 3.16 |
| 2024.00 | common | 3.00 | recent_distance | 3.39 |
| 2024.00 | common | 4.00 | historical_volatility | 3.68 |
| 2024.00 | operational | 1.00 | historical_mae | 2.89 |
| 2024.00 | operational | 2.00 | historical_rmse | 3.15 |
| 2024.00 | operational | 3.00 | recent_distance | 3.39 |
| 2024.00 | operational | 4.00 | historical_volatility | 3.68 |

## Recent vs longitudinal

| target | cohort | selector | mae | rmse | medae |
| --- | --- | --- | --- | --- | --- |
| 2013.00 | common | historical_mae | 1.49 | 1.65 | 1.48 |
| 2013.00 | common | historical_rmse | 1.28 | 1.50 | 1.36 |
| 2013.00 | common | recent_distance | 1.79 | 3.83 | 0.97 |
| 2013.00 | operational | historical_mae | 1.80 | 2.33 | 1.57 |
| 2013.00 | operational | historical_rmse | 1.59 | 2.22 | 1.49 |
| 2013.00 | operational | recent_distance | 1.28 | 1.71 | 0.97 |
| 2018.00 | common | historical_mae | 2.37 | 3.48 | 1.76 |
| 2018.00 | common | historical_rmse | 2.94 | 3.34 | 2.84 |
| 2018.00 | common | recent_distance | 3.94 | 4.97 | 3.39 |
| 2018.00 | operational | historical_mae | 2.37 | 3.48 | 1.76 |
| 2018.00 | operational | historical_rmse | 2.94 | 3.34 | 2.84 |
| 2018.00 | operational | recent_distance | 3.94 | 4.97 | 3.39 |
| 2024.00 | common | historical_mae | 3.09 | 3.82 | 2.78 |
| 2024.00 | common | historical_rmse | 3.16 | 3.85 | 2.89 |
| 2024.00 | common | recent_distance | 3.39 | 4.21 | 2.93 |
| 2024.00 | operational | historical_mae | 2.89 | 3.56 | 2.63 |
| 2024.00 | operational | historical_rmse | 3.15 | 3.88 | 2.89 |
| 2024.00 | operational | recent_distance | 3.39 | 4.21 | 2.93 |

## Persistencia de residuales

| from_year | to_year | n_centros | pearson | spearman | ols_slope | r2 | mae_delta_residual |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2006.00 | 2012.00 | 10540.00 | 0.87 | 0.84 | 0.95 | 0.75 | 6.21 |
| 2012.00 | 2013.00 | 13684.00 | 0.98 | 0.98 | 0.99 | 0.96 | 2.44 |
| 2013.00 | 2018.00 | 13260.00 | 0.60 | 0.62 | 0.41 | 0.37 | 12.33 |
| 2018.00 | 2024.00 | 10775.00 | 0.66 | 0.66 | 0.79 | 0.44 | 8.37 |

## Diagnostico por cuantiles

| target | feature | quantile | n_centros | feature_min | feature_max | abs_residual_target_mae |
| --- | --- | --- | --- | --- | --- | --- |
| 2013.00 | historical_volatility | Q1 | 2635.00 | 0.00 | 1.11 | 13.48 |
| 2013.00 | historical_volatility | Q2 | 2635.00 | 1.11 | 2.36 | 13.76 |
| 2013.00 | historical_volatility | Q3 | 2634.00 | 2.36 | 4.22 | 13.74 |
| 2013.00 | historical_volatility | Q4 | 2635.00 | 4.22 | 54.23 | 16.74 |
| 2013.00 | historical_mae | Q1 | 3419.00 | 0.03 | 6.76 | 4.64 |
| 2013.00 | historical_mae | Q2 | 3418.00 | 6.77 | 12.95 | 10.17 |
| 2013.00 | historical_mae | Q3 | 3418.00 | 12.95 | 21.03 | 17.58 |
| 2013.00 | historical_mae | Q4 | 3419.00 | 21.04 | 124.17 | 30.47 |
| 2013.00 | abs_historical_bias | Q1 | 3419.00 | 0.00 | 6.16 | 4.98 |
| 2013.00 | abs_historical_bias | Q2 | 3418.00 | 6.16 | 12.77 | 9.92 |
| 2013.00 | abs_historical_bias | Q3 | 3418.00 | 12.77 | 21.01 | 17.48 |
| 2013.00 | abs_historical_bias | Q4 | 3419.00 | 21.01 | 124.17 | 30.47 |
| 2013.00 | recent_distance | Q1 | 3419.00 | 0.01 | 6.60 | 3.85 |
| 2013.00 | recent_distance | Q2 | 3418.00 | 6.60 | 13.65 | 9.98 |
| 2013.00 | recent_distance | Q3 | 3418.00 | 13.65 | 22.56 | 17.88 |
| 2013.00 | recent_distance | Q4 | 3419.00 | 22.56 | 124.17 | 31.14 |
| 2018.00 | historical_volatility | Q1 | 3305.00 | 0.00 | 1.14 | 7.33 |
| 2018.00 | historical_volatility | Q2 | 3304.00 | 1.14 | 2.21 | 8.13 |
| 2018.00 | historical_volatility | Q3 | 3304.00 | 2.21 | 3.90 | 9.08 |
| 2018.00 | historical_volatility | Q4 | 3304.00 | 3.90 | 52.43 | 11.68 |
| 2018.00 | historical_mae | Q1 | 3307.00 | 0.11 | 6.73 | 6.55 |
| 2018.00 | historical_mae | Q2 | 3306.00 | 6.73 | 13.04 | 7.52 |
| 2018.00 | historical_mae | Q3 | 3306.00 | 13.04 | 21.50 | 8.56 |
| 2018.00 | historical_mae | Q4 | 3306.00 | 21.50 | 77.13 | 13.60 |
| 2018.00 | abs_historical_bias | Q1 | 3307.00 | 0.00 | 6.10 | 6.92 |
| 2018.00 | abs_historical_bias | Q2 | 3306.00 | 6.10 | 12.91 | 7.27 |
| 2018.00 | abs_historical_bias | Q3 | 3306.00 | 12.92 | 21.46 | 8.44 |
| 2018.00 | abs_historical_bias | Q4 | 3306.00 | 21.46 | 77.13 | 13.58 |
| 2018.00 | recent_distance | Q1 | 3307.00 | 0.01 | 6.46 | 6.58 |
| 2018.00 | recent_distance | Q2 | 3306.00 | 6.46 | 13.50 | 7.08 |
| 2018.00 | recent_distance | Q3 | 3306.00 | 13.50 | 22.82 | 8.40 |
| 2018.00 | recent_distance | Q4 | 3306.00 | 22.82 | 55.44 | 14.16 |
| 2024.00 | historical_volatility | Q1 | 2521.00 | 0.07 | 3.33 | 8.32 |
| 2024.00 | historical_volatility | Q2 | 2520.00 | 3.33 | 5.40 | 10.01 |
| 2024.00 | historical_volatility | Q3 | 2520.00 | 5.40 | 8.10 | 11.40 |
| 2024.00 | historical_volatility | Q4 | 2520.00 | 8.10 | 50.60 | 13.01 |
| 2024.00 | historical_mae | Q1 | 2703.00 | 0.14 | 6.27 | 5.94 |
| 2024.00 | historical_mae | Q2 | 2703.00 | 6.27 | 10.99 | 7.44 |
| 2024.00 | historical_mae | Q3 | 2703.00 | 10.99 | 17.35 | 11.25 |
| 2024.00 | historical_mae | Q4 | 2703.00 | 17.35 | 53.84 | 19.56 |
| 2024.00 | abs_historical_bias | Q1 | 2703.00 | 0.00 | 4.59 | 6.07 |
| 2024.00 | abs_historical_bias | Q2 | 2703.00 | 4.59 | 9.91 | 7.26 |
| 2024.00 | abs_historical_bias | Q3 | 2703.00 | 9.91 | 16.86 | 11.07 |
| 2024.00 | abs_historical_bias | Q4 | 2703.00 | 16.87 | 53.84 | 19.79 |
| 2024.00 | recent_distance | Q1 | 2703.00 | 0.00 | 3.13 | 6.71 |
| 2024.00 | recent_distance | Q2 | 2703.00 | 3.13 | 6.86 | 8.07 |
| 2024.00 | recent_distance | Q3 | 2703.00 | 6.87 | 12.76 | 11.15 |
| 2024.00 | recent_distance | Q4 | 2703.00 | 12.76 | 56.93 | 18.26 |

## Archivos reproducibles

- `backtest_longitudinal_summary.csv`
- `backtest_longitudinal_estados.csv`
- `backtest_longitudinal_centros.csv`
- `backtest_longitudinal_features.csv`
- `backtest_longitudinal_persistencia.csv`

## Limitaciones

- El estudio no modifica el selector productivo moderno ni propone un score compuesto.
- Missing historico permanece NULL y reduce `n_hist`; no se imputa ni se convierte en cero.
- Las series dependen del enlace por codigo CNE nuevo ya presente en los archivos normalizados/importadores del repo.
- La interpretacion es descriptiva; diferencias pequenas no justifican cambios productivos por si solas.
