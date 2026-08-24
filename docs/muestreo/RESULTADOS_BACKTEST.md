# Resultados de backtest y diagnosticos

Fecha de consolidacion: 2026-08-24.
Fecha de ejecucion local verificada: 2026-08-24.
Commit local verificado: `9c71f16fb2c9f96c366e4612e48a36b5a6343aec`.
Base local: `backend/exitpoll.db`.
Tamano DB: `64589824` bytes.
SHA256 DB corto: `e4cc0e5a5cb8`.
Python: `3.12.0`.
Harness principal: `backend/backtest_muestra.py`.
Sample size: `180`.
Random runs: `100`.
Modo SQLite: read-only; diagnosticos compactos reejecutados con URI
`mode=ro&immutable=1`.

Estos resultados son experimentales y read-only. No definen comportamiento
productivo.

## Fuentes historicas disponibles

| Eleccion | Fuente | Granularidad | Cobertura | Centros | Mesas | Validos |
|---|---:|---:|---:|---:|---:|---:|
| 2004-revocatorio | esdata_wayback | centro | 91.4 | 6265 | 0 | 8956463 |
| 2006-presidencial | cne_recuperado | mesa | 100.0 | 10936 | 32788 | 11569233 |
| 2007-referendum | esdata_wayback | mesa | 86.5 | 9002 | 30505 | 8870584 |
| 2009-enmienda | esdata_wayback | mesa | 99.0 | 11233 | 34250 | 11504321 |
| 2012-presidencial | cne_recuperado | mesa | 100.0 | 13818 | 39299 | 14864226 |
| 2013-presidencial | cne_recuperado | mesa | 100.0 | 13850 | 39360 | 14988563 |
| 2018-presidencial | venpres_a | centro | 98.37 | 14400 | 33716 | 9203220 |
| 2024-presidencial | actas_cvzla | centro | 81.0 | 11925 | 0 | 9615399 |

Huella de fuentes en `seed_state`: `6c9facf8f0459dbdbe48bd2550cc925d4c9bd34e66b8a2bd7e91572bf99320a0`.

## Backtest CLI

Parametros:

- script: `backend/backtest_muestra.py`;
- `--sample-size 180`;
- `--random-runs 100`;
- targets: 2012, 2013 y 2018;
- training refs: solo elecciones anteriores al target.

Comando:

```powershell
python backend/backtest_muestra.py --sample-size 180 --random-runs 100
```

| Target | Frame | Training refs | Historical error nacional pp | Historical MAE estatal pp | Random mediana pp | Random p10-p90 pp |
|---|---:|---|---:|---:|---:|---:|
| 2012-presidencial | 13680 | 2004, 2006, 2007, 2009 | 4.79 | 5.90 | 3.82 | 0.68-7.24 |
| 2013-presidencial | 13700 | 2004, 2006, 2007, 2009, 2012 | 3.41 | 3.95 | 3.35 | 0.62-6.73 |
| 2018-presidencial | 14357 | 2004, 2006, 2007, 2009, 2012, 2013 | 1.20 | 5.91 | 1.40 | 0.23-2.99 |

Lectura: `historical_rmse_state` no gana robustamente. Su mejor caso nacional
es 2018, pero eso no basta para promoverlo a produccion.

## Cobertura del score historico en la muestra greedy

| Target | Score completo | Evidencia limitada | Fallback | Exposicion |
|---|---:|---:|---:|---:|
| 2012-presidencial | 161 | 18 | 1 | 99.4% |
| 2013-presidencial | 174 | 6 | 0 | 100.0% |
| 2018-presidencial | 129 | 51 | 0 | 100.0% |

Para 2024 no hay backtest equivalente con `centro_snapshot` target completo en
el arnes actual. El diagnostico 2024 usa frame vigente `centros_activos` y
resultados observados 2024 solo para medir, no para seleccionar.

## Persistencia de RMSE

| Target | n RMSE | Spearman | Pearson | Parcial log electores | Top20/mediana | Lift |
|---|---:|---:|---:|---:|---:|---:|
| 2012-presidencial | 10635 | 0.819 | 0.860 | 0.813 | 56.0 | 2.80 |
| 2013-presidencial | 11181 | 0.865 | 0.892 | 0.856 | 60.9 | 3.04 |
| 2018-presidencial | 13256 | 0.367 | 0.390 | 0.299 | 30.5 | 1.52 |
| 2024-presidencial | 10081 | 0.523 | 0.584 | 0.491 | 32.9 | 1.65 |

El RMSE historico tiene senal real, pero no estable en la magnitud necesaria
para convertirlo en selector automatico.

## Profundidad historica del frame

| Target | n>=4 | n=3 | n=2 | n=1 | n=0 |
|---|---:|---:|---:|---:|---:|
| 2012-presidencial | 5383 | 3971 | 1281 | 530 | 2515 |
| 2013-presidencial | 9358 | 1291 | 532 | 2514 | 5 |
| 2018-presidencial | 10373 | 475 | 2408 | 6 | 1095 |
| 2024-presidencial | 11057 | 1765 | 163 | 808 | 1117 |

## Profundidad en centros con target observado

| Target | n>=4 | n=3 | n=2 | n=1 |
|---|---:|---:|---:|---:|
| 2012-presidencial | 5383 | 3971 | 1281 | 530 |
| 2013-presidencial | 9358 | 1291 | 532 | 2514 |
| 2018-presidencial | 10373 | 475 | 2408 | 6 |
| 2024-presidencial | 8480 | 1592 | 9 | 731 |

Nota 2024: el frame diagnostico tiene 14910 centros activos; el resultado
observado tiene 11925 centros con datos en `actas_cvzla`.

## RMSE historico por quintiles

Cada celda muestra mediana de RMSE historico y mediana de error target del mismo
quintil, en puntos porcentuales.

| Target | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---:|---:|---:|---:|---:|
| 2012 | 7.512 -> 8.410 | 15.617 -> 15.248 | 24.345 -> 25.131 | 35.159 -> 36.227 | 53.141 -> 54.932 |
| 2013 | 8.469 -> 7.497 | 16.347 -> 15.290 | 25.056 -> 25.642 | 36.230 -> 37.874 | 55.084 -> 59.172 |
| 2018 | 8.843 -> 8.106 | 17.416 -> 9.288 | 27.114 -> 10.281 | 39.182 -> 13.972 | 60.098 -> 25.032 |
| 2024 | 8.988 -> 9.781 | 16.252 -> 11.324 | 24.124 -> 14.880 | 34.350 -> 21.472 | 51.638 -> 36.252 |

## Offset `mu` e innovacion `sigma`

| Target | n mu | Spearman mu | Pearson mu | b | R2 | n sigma | Spearman sigma-innov |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2012 | 10635 | 0.918 | 0.931 | 1.015 | 0.867 | 9354 | 0.232 |
| 2013 | 11181 | 0.939 | 0.945 | 1.035 | 0.892 | 10649 | 0.503 |
| 2018 | 13256 | 0.636 | 0.610 | 0.403 | 0.372 | 10848 | 0.053 |
| 2024 | 10081 | 0.777 | 0.759 | 0.749 | 0.576 | 10072 | 0.312 |

La re-ejecucion local corrigio valores de la sintesis previa: por ejemplo,
2018 usa `mu` Spearman 0.636 y no 0.653 bajo residual estatal ponderado
consistentemente por votos.

## `sigma` por quintiles de innovacion absoluta

Valores: mediana de innovacion absoluta target por quintil de `sigma`.

| Target | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---:|---:|---:|---:|---:|
| 2012 | 5.703 | 6.040 | 7.122 | 7.405 | 9.285 |
| 2013 | 3.693 | 5.309 | 7.106 | 8.617 | 13.342 |
| 2018 | 17.259 | 18.123 | 18.953 | 20.805 | 20.623 |
| 2024 | 8.405 | 11.734 | 13.869 | 16.699 | 18.449 |

La sintesis pegada contenia valores de `sigma` ligeramente distintos. Se
conservan aqui los de la re-ejecucion local reproducible.

## Split-half de `mu`

Solo se reporta para centros con al menos 4 elecciones historicas.

| Target | n | Spearman | Pearson | b | R2 |
|---|---:|---:|---:|---:|---:|
| 2012 | 5383 | 0.915 | 0.931 | 0.971 | 0.867 |
| 2013 | 9358 | 0.901 | 0.921 | 0.967 | 0.848 |
| 2018 | 10373 | 0.903 | 0.920 | 0.996 | 0.846 |
| 2024 | 11057 | 0.892 | 0.906 | 0.823 | 0.820 |

Con `n=3`, el split-half seria 1 contra 2 y queda descartado como prueba
primaria.

## Extremos de `mu` y `sigma`

| Target | mu p05 | mu mediana | mu p95 | sigma p05 | sigma mediana | sigma p95 |
|---|---:|---:|---:|---:|---:|---:|
| 2012 | -44.532 | 13.706 | 58.486 | 1.825 | 6.273 | 19.708 |
| 2013 | -44.510 | 13.922 | 60.392 | 2.495 | 7.256 | 20.828 |
| 2018 | -41.138 | 17.995 | 67.234 | 2.626 | 7.279 | 19.803 |
| 2024 | -39.688 | 12.207 | 54.016 | 4.026 | 11.591 | 27.541 |

## Descomposicion greedy B + I

| Target | B | I | Error | Cierre | Percentil B | Percentil I | Percentil error |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2012 | -0.04 | -4.86 | -4.79 | 0.114 | 0 | 77 | 68 |
| 2013 | -0.07 | -3.34 | -3.41 | ~0 | 0 | 65 | 52 |
| 2018 | 0.16 | -1.37 | -1.20 | ~0 | 1 | 5 | 44 |

El cierre 2012 no es cero por un fallback sin `mu` usable. La identidad
`Error = B + I` es una prueba dura cuando definiciones y pesos coinciden.

## Descomposicion aleatoria B + I

| Target | B mediana | I mediana | Error absoluto mediana | Error p10-p90 |
|---|---:|---:|---:|---:|
| 2012 | 4.21 | -3.99 | 3.82 | 0.68-7.24 |
| 2013 | 3.87 | -3.08 | 3.35 | 0.62-6.73 |
| 2018 | 5.41 | -5.30 | 1.40 | 0.23-2.99 |

## Diagnostico 2024

La fuente 2024 es `actas_cvzla`, granularidad centro, cobertura declarada 81%.
No hay `centro_snapshot` completo de 2024 para el arnes leave-one-out, por lo
que el diagnostico usa centros activos como frame y solo observa target donde
hay actas.

Cobertura baja por electores: Lara 65.1, Amazonas 69.9, Distrito Capital 72.1,
Carabobo 75.2, Miranda 75.6.

Cobertura alta por electores: Merida 95.0, Trujillo 94.0, Guarico 94.0,
Yaracuy 93.1, Portuguesa 93.0.

`EXTERIOR` no tiene referencia territorial usable para este diagnostico.
