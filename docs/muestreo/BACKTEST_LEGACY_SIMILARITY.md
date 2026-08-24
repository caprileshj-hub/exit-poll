# Comparacion de formalizaciones de similitud legacy

Este ejercicio mantiene fijo el procedimiento legacy de 120 centros y cambia solo la definicion matematica de `se parece` usada contra la presidencial inmediatamente anterior.

## Formulas

- `winner_share`: distancia absoluta entre el porcentaje del candidato ganador estatal historico y ese mismo candidato en el centro.
- `top2_gap`: distancia absoluta entre el gap firmado de los dos candidatos principales estatales y el gap firmado de esos mismos candidatos en el centro.
- `full_profile`: Total Variation Distance en puntos porcentuales, `0.5 * sum(abs(p_cj - p_sj))`, sobre todos los candidatos comparables dentro de la eleccion historica.

La escalera comun es `[2, 4, 6, 8, 10, 15, 20, inf]` pp y `min_electores=300`. No se optimiza por variante.

## Fuentes y tratamiento de candidatos

- `2013_2018`: marco `backend/tm_2018_estandar.csv`, Distrito Capital completado desde VENPRES-A 2018 solo como marco, similitud desde `resultados oficiales elecciones presidenciales 2013.xlsx`, outcome desde VENPRES-A 2018.
- Perfil 2013: Maduro, Capriles, Sequera, Bolivar, Mora y Mendez; porcentajes sobre votos validos agregados por centro/estado.
- `2018_2024`: marco `backend/tm_2024_estandar.csv`, similitud desde VENPRES-A 2018, outcome desde `backend/resultados_cne2024.csv`.
- Perfil 2018: Maduro, Falcon y Bertucci+Quijada. VENPRES-A conserva Falcon separado como oposicion y Bertucci+Quijada como bloque `otros`; no se separa Quijada porque el CSV normalizado del repo no lo expone aparte.

La implementacion legacy previa usa porcentaje de Maduro/gobierno contra el porcentaje estatal historico. Es equivalente a `winner_share` solo en estados donde Maduro fue el ganador estatal historico; si gana otro candidato, `winner_share` compara contra ese ganador estatal y no contra Maduro.

## Resumen nacional

| transicion | similarity | mae | rmse | medae | pct_dentro_2pp | pct_dentro_5pp | pct_dentro_10pp | max_error_abs | max_error_estado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013_2018 | full_profile | 4.64 | 7.25 | 3.57 | 0.21 | 0.75 | 0.92 | 28.59 | Delta Amacuro |
| 2013_2018 | top2_gap | 3.90 | 5.99 | 3.38 | 0.25 | 0.83 | 0.96 | 24.37 | Delta Amacuro |
| 2013_2018 | winner_share | 4.07 | 5.20 | 3.39 | 0.25 | 0.71 | 0.88 | 12.26 | Delta Amacuro |
| 2018_2024 | full_profile | 3.38 | 4.04 | 2.81 | 0.33 | 0.75 | 1.00 | 8.91 | Barinas |
| 2018_2024 | top2_gap | 4.10 | 4.71 | 4.12 | 0.25 | 0.67 | 1.00 | 9.84 | Barinas |
| 2018_2024 | winner_share | 3.39 | 4.21 | 2.93 | 0.33 | 0.71 | 1.00 | 9.91 | Barinas |

## Estabilidad comparativa

| transicion | menor_mae_similarity | menor_mae | menor_rmse_similarity | menor_rmse | menor_outlier_similarity | menor_max_error_abs | menor_ampliacion_similarity | pasada_maxima | distancia_max_sel | centros_comunes_tres_variantes | pct_comun_sobre_120 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013_2018 | top2_gap | 3.90 | winner_share | 5.20 | winner_share | 12.26 | top2_gap | 1.00 | 1.98 | 72.00 | 60.00 |
| 2018_2024 | full_profile | 3.38 | full_profile | 4.04 | full_profile | 8.91 | winner_share | 1.00 | 1.97 | 25.00 | 20.83 |

## Resultados estatales

| transicion | similarity | estado | cuota | error_outcome_pp | distancia_media_sel | pasada_maxima | tolerancia_maxima | n_difiere_otras_variantes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013_2018 | full_profile | Amazonas | 2.00 | -5.25 | 0.85 | 1.00 | 2.00 | 0.00 |
| 2013_2018 | full_profile | Anzoategui | 6.00 | -3.86 | 1.13 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | full_profile | Apure | 3.00 | -0.44 | 0.99 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Aragua | 7.00 | -4.11 | 0.86 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Barinas | 4.00 | -3.43 | 0.64 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Bolivar | 6.00 | -6.10 | 0.78 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Carabobo | 8.00 | -2.27 | 1.05 | 1.00 | 2.00 | 4.00 |
| 2013_2018 | full_profile | Cojedes | 2.00 | 0.96 | 0.92 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Delta Amacuro | 2.00 | 28.59 | 0.83 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Distrito Capital | 9.00 | -2.22 | 1.12 | 1.00 | 2.00 | 5.00 |
| 2013_2018 | full_profile | Falcon | 4.00 | -3.70 | 1.56 | 1.00 | 2.00 | 4.00 |
| 2013_2018 | full_profile | Guarico | 4.00 | -6.35 | 0.92 | 1.00 | 2.00 | 2.00 |
| 2013_2018 | full_profile | La Guaira | 3.00 | 0.53 | 0.87 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Lara | 7.00 | -4.98 | 0.95 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | full_profile | Merida | 4.00 | 2.02 | 1.29 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | full_profile | Miranda | 10.00 | -2.73 | 0.96 | 1.00 | 2.00 | 5.00 |
| 2013_2018 | full_profile | Monagas | 4.00 | -4.41 | 0.56 | 1.00 | 2.00 | 0.00 |
| 2013_2018 | full_profile | Nueva Esparta | 3.00 | 1.73 | 0.96 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Portuguesa | 4.00 | 2.55 | 0.89 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Sucre | 4.00 | -0.23 | 0.48 | 1.00 | 2.00 | 0.00 |
| 2013_2018 | full_profile | Tachira | 5.00 | -7.52 | 1.16 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | full_profile | Trujillo | 4.00 | 3.86 | 0.71 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | full_profile | Yaracuy | 3.00 | -11.42 | 1.31 | 1.00 | 2.00 | 2.00 |
| 2013_2018 | full_profile | Zulia | 12.00 | -2.04 | 0.73 | 1.00 | 2.00 | 4.00 |
| 2013_2018 | top2_gap | Amazonas | 2.00 | -5.25 | 1.57 | 1.00 | 2.00 | 0.00 |
| 2013_2018 | top2_gap | Anzoategui | 6.00 | -3.62 | 1.28 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | top2_gap | Apure | 3.00 | 4.91 | 0.78 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Aragua | 7.00 | -3.76 | 1.02 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Barinas | 4.00 | -2.37 | 0.75 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Bolivar | 6.00 | -4.14 | 1.04 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Carabobo | 8.00 | -2.48 | 0.81 | 1.00 | 2.00 | 4.00 |
| 2013_2018 | top2_gap | Cojedes | 2.00 | 0.58 | 0.79 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Delta Amacuro | 2.00 | 24.37 | 0.94 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Distrito Capital | 9.00 | -2.44 | 1.31 | 1.00 | 2.00 | 5.00 |
| 2013_2018 | top2_gap | Falcon | 4.00 | -3.14 | 1.25 | 1.00 | 2.00 | 4.00 |
| 2013_2018 | top2_gap | Guarico | 4.00 | -5.23 | 0.78 | 1.00 | 2.00 | 2.00 |
| 2013_2018 | top2_gap | La Guaira | 3.00 | 1.08 | 0.70 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Lara | 7.00 | -5.38 | 0.86 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | top2_gap | Merida | 4.00 | 2.41 | 1.28 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | top2_gap | Miranda | 10.00 | -4.09 | 0.87 | 1.00 | 2.00 | 5.00 |
| 2013_2018 | top2_gap | Monagas | 4.00 | -4.41 | 0.97 | 1.00 | 2.00 | 0.00 |
| 2013_2018 | top2_gap | Nueva Esparta | 3.00 | -2.43 | 1.14 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Portuguesa | 4.00 | 1.96 | 1.16 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Sucre | 4.00 | -0.23 | 0.80 | 1.00 | 2.00 | 0.00 |
| 2013_2018 | top2_gap | Tachira | 5.00 | -4.09 | 0.97 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | top2_gap | Trujillo | 4.00 | 1.20 | 0.63 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | top2_gap | Yaracuy | 3.00 | -4.03 | 0.96 | 1.00 | 2.00 | 2.00 |
| 2013_2018 | top2_gap | Zulia | 12.00 | 0.11 | 0.66 | 1.00 | 2.00 | 4.00 |
| 2013_2018 | winner_share | Amazonas | 2.00 | -5.25 | 0.80 | 1.00 | 2.00 | 0.00 |
| 2013_2018 | winner_share | Anzoategui | 6.00 | -3.86 | 1.07 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | winner_share | Apure | 3.00 | -0.44 | 0.96 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Aragua | 7.00 | -4.11 | 0.72 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Barinas | 4.00 | -3.43 | 0.55 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Bolivar | 6.00 | -6.10 | 0.74 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Carabobo | 8.00 | -2.27 | 0.99 | 1.00 | 2.00 | 4.00 |
| 2013_2018 | winner_share | Cojedes | 2.00 | 0.96 | 0.85 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Delta Amacuro | 2.00 | 12.26 | 1.06 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Distrito Capital | 9.00 | -2.22 | 1.02 | 1.00 | 2.00 | 5.00 |
| 2013_2018 | winner_share | Falcon | 4.00 | -3.34 | 1.57 | 1.00 | 2.00 | 4.00 |
| 2013_2018 | winner_share | Guarico | 4.00 | -6.35 | 0.86 | 1.00 | 2.00 | 2.00 |
| 2013_2018 | winner_share | La Guaira | 3.00 | 0.53 | 0.84 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Lara | 7.00 | -5.31 | 0.94 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | winner_share | Merida | 4.00 | 1.34 | 1.41 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | winner_share | Miranda | 10.00 | -3.21 | 1.03 | 1.00 | 2.00 | 5.00 |
| 2013_2018 | winner_share | Monagas | 4.00 | -4.41 | 0.52 | 1.00 | 2.00 | 0.00 |
| 2013_2018 | winner_share | Nueva Esparta | 3.00 | 1.73 | 0.87 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Portuguesa | 4.00 | 2.55 | 0.80 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Sucre | 4.00 | -0.23 | 0.41 | 1.00 | 2.00 | 0.00 |
| 2013_2018 | winner_share | Tachira | 5.00 | -10.47 | 1.13 | 1.00 | 2.00 | 3.00 |
| 2013_2018 | winner_share | Trujillo | 4.00 | 3.86 | 0.64 | 1.00 | 2.00 | 1.00 |
| 2013_2018 | winner_share | Yaracuy | 3.00 | -11.42 | 1.25 | 1.00 | 2.00 | 2.00 |
| 2013_2018 | winner_share | Zulia | 12.00 | -2.04 | 0.67 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | full_profile | Amazonas | 2.00 | 0.63 | 1.06 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | full_profile | Anzoategui | 7.00 | -2.83 | 1.51 | 1.00 | 2.00 | 6.00 |
| 2018_2024 | full_profile | Apure | 3.00 | 4.54 | 1.06 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | full_profile | Aragua | 7.00 | -1.76 | 1.51 | 1.00 | 2.00 | 6.00 |
| 2018_2024 | full_profile | Barinas | 4.00 | -8.91 | 1.19 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | full_profile | Bolivar | 5.00 | -3.45 | 1.17 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | full_profile | Carabobo | 7.00 | -0.61 | 1.21 | 1.00 | 2.00 | 7.00 |
| 2018_2024 | full_profile | Cojedes | 3.00 | -6.86 | 1.16 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | full_profile | Delta Amacuro | 2.00 | -2.73 | 1.34 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | full_profile | Distrito Capital | 7.00 | 2.80 | 1.38 | 1.00 | 2.00 | 6.00 |
| 2018_2024 | full_profile | Falcon | 5.00 | -4.50 | 1.24 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | full_profile | Guarico | 4.00 | -4.20 | 1.02 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | full_profile | La Guaira | 3.00 | -0.86 | 1.23 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | full_profile | Lara | 6.00 | -5.82 | 1.65 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | full_profile | Merida | 4.00 | -2.75 | 1.21 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | full_profile | Miranda | 9.00 | 1.00 | 1.29 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | full_profile | Monagas | 4.00 | -2.57 | 1.47 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | full_profile | Nueva Esparta | 3.00 | -1.46 | 1.27 | 1.00 | 2.00 | 3.00 |
| 2018_2024 | full_profile | Portuguesa | 5.00 | 2.97 | 1.45 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | full_profile | Sucre | 5.00 | 0.26 | 1.56 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | full_profile | Tachira | 6.00 | -5.72 | 1.49 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | full_profile | Trujillo | 4.00 | -6.56 | 1.41 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | full_profile | Yaracuy | 4.00 | -5.24 | 1.17 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | full_profile | Zulia | 11.00 | -1.97 | 1.08 | 1.00 | 2.00 | 10.00 |
| 2018_2024 | top2_gap | Amazonas | 2.00 | 4.16 | 1.41 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | top2_gap | Anzoategui | 7.00 | 0.65 | 1.04 | 1.00 | 2.00 | 6.00 |
| 2018_2024 | top2_gap | Apure | 3.00 | 1.70 | 0.76 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | top2_gap | Aragua | 7.00 | -2.41 | 1.12 | 1.00 | 2.00 | 6.00 |
| 2018_2024 | top2_gap | Barinas | 4.00 | -9.84 | 1.11 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | top2_gap | Bolivar | 5.00 | -5.60 | 1.02 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | top2_gap | Carabobo | 7.00 | -4.64 | 1.37 | 1.00 | 2.00 | 7.00 |
| 2018_2024 | top2_gap | Cojedes | 3.00 | -3.56 | 1.09 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | top2_gap | Delta Amacuro | 2.00 | -1.49 | 0.21 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | top2_gap | Distrito Capital | 7.00 | 1.93 | 1.19 | 1.00 | 2.00 | 6.00 |
| 2018_2024 | top2_gap | Falcon | 5.00 | -5.28 | 0.92 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | top2_gap | Guarico | 4.00 | -4.40 | 1.02 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | top2_gap | La Guaira | 3.00 | -1.77 | 0.55 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | top2_gap | Lara | 6.00 | -7.20 | 0.70 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | top2_gap | Merida | 4.00 | -2.11 | 1.12 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | top2_gap | Miranda | 9.00 | 4.09 | 0.70 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | top2_gap | Monagas | 4.00 | -0.62 | 1.12 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | top2_gap | Nueva Esparta | 3.00 | -2.87 | 1.02 | 1.00 | 2.00 | 3.00 |
| 2018_2024 | top2_gap | Portuguesa | 5.00 | -3.65 | 1.29 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | top2_gap | Sucre | 5.00 | -7.82 | 0.75 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | top2_gap | Tachira | 6.00 | -4.88 | 0.99 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | top2_gap | Trujillo | 4.00 | -5.07 | 0.63 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | top2_gap | Yaracuy | 4.00 | -5.71 | 1.02 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | top2_gap | Zulia | 11.00 | -6.95 | 0.80 | 1.00 | 2.00 | 10.00 |
| 2018_2024 | winner_share | Amazonas | 2.00 | 4.16 | 0.70 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | winner_share | Anzoategui | 7.00 | -1.77 | 1.06 | 1.00 | 2.00 | 6.00 |
| 2018_2024 | winner_share | Apure | 3.00 | 0.14 | 0.78 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | winner_share | Aragua | 7.00 | -4.28 | 1.06 | 1.00 | 2.00 | 6.00 |
| 2018_2024 | winner_share | Barinas | 4.00 | -9.91 | 0.27 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | winner_share | Bolivar | 5.00 | -2.21 | 1.31 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | winner_share | Carabobo | 7.00 | -0.79 | 0.99 | 1.00 | 2.00 | 7.00 |
| 2018_2024 | winner_share | Cojedes | 3.00 | -6.86 | 0.61 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | winner_share | Delta Amacuro | 2.00 | -2.73 | 0.38 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | winner_share | Distrito Capital | 7.00 | 2.24 | 1.20 | 1.00 | 2.00 | 6.00 |
| 2018_2024 | winner_share | Falcon | 5.00 | -3.61 | 0.89 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | winner_share | Guarico | 4.00 | -1.25 | 1.70 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | winner_share | La Guaira | 3.00 | -0.86 | 0.76 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | winner_share | Lara | 6.00 | -5.04 | 0.78 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | winner_share | Merida | 4.00 | -1.53 | 0.65 | 1.00 | 2.00 | 2.00 |
| 2018_2024 | winner_share | Miranda | 9.00 | 3.13 | 0.82 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | winner_share | Monagas | 4.00 | 0.24 | 0.97 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | winner_share | Nueva Esparta | 3.00 | 0.08 | 1.20 | 1.00 | 2.00 | 3.00 |
| 2018_2024 | winner_share | Portuguesa | 5.00 | -5.61 | 1.23 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | winner_share | Sucre | 5.00 | -6.79 | 0.74 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | winner_share | Tachira | 6.00 | -3.92 | 0.84 | 1.00 | 2.00 | 5.00 |
| 2018_2024 | winner_share | Trujillo | 4.00 | -5.07 | 0.64 | 1.00 | 2.00 | 1.00 |
| 2018_2024 | winner_share | Yaracuy | 4.00 | -2.22 | 0.76 | 1.00 | 2.00 | 4.00 |
| 2018_2024 | winner_share | Zulia | 11.00 | -6.82 | 1.07 | 1.00 | 2.00 | 10.00 |

## Archivos reproducibles

- `backtest_legacy_similarity_summary.csv`
- `backtest_legacy_similarity_estados.csv`
- `backtest_legacy_similarity_centros.csv`

## Limitaciones

- Este no es un nuevo selector productivo ni una optimizacion moderna; solo formaliza el componente `se parece`.
- No se agregan fuentes externas ni se modifican datasets originales.
- Las metricas de swing se conservan en los CSV como diagnostico secundario.
- Diferencias pequenas entre variantes no se interpretan automaticamente como victoria metodologica.
