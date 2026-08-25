# Metodo longitudinal V1

`longitudinal_mae_v1` es un selector experimental para muestras presidenciales
nacionales futuras. No reemplaza el selector productivo actual
`stratified_random_v1` y debe invocarse de forma deliberada desde
`backend/selector_longitudinal.py`.

## Origen

El metodo deriva de la reconstruccion del criterio legacy: centros grandes que
"se parecen" territorialmente a su estado. La diferencia es que el juicio
humano se sustituye por una medida longitudinal reproducible calculada con
resultados historicos presidenciales ya normalizados en el repositorio.

Los backtests 2013, 2018 y 2024 fueron evidencia retrospectiva para evaluar la
regla. No crean excepciones por ano, pesos aprendidos, reglas de shock ni
optimizacion post hoc.

## Formula

Para cada centro `i`, eleccion presidencial historica `t` y estado `s`:

```text
r_i,t = p_i,t - p_s,t
```

Donde:

- `p_i,t` es el porcentaje de gobierno/bloque de referencia en el centro.
- `p_s,t` es el porcentaje del mismo bloque agregado en el estado.
- `r_i,t` es el residual territorial centro-estado.

Para un estudio futuro `T`, solo se usan elecciones presidenciales anteriores a
`T`:

```text
HistoricalMAE_i = mean(abs(r_i,t)) para t < T
RecentDistance_i = abs(r_i,t-1)
```

## Fallback

La regla efectiva de score es:

| condicion | selector_score | score_source |
| --- | --- | --- |
| `n_hist >= 2` | `historical_mae` | `longitudinal` |
| `n_hist == 1` | `recent_distance` | `recent_fallback` |
| `n_hist == 0` | `NULL` | `no_history` |

Los valores faltantes permanecen `NULL`; no se imputan, no se transforman en
cero y no reciben penalizaciones artificiales.

## Variables diagnosticas

Aunque solo `historical_mae` o el fallback reciente deciden la seleccion, cada
centro conserva:

- `n_hist`
- `recent_distance`
- `historical_mae`
- `historical_rmse`
- `historical_bias`
- `abs_historical_bias`
- `historical_volatility`
- residuales historicos disponibles
- `historical_elections_used`

Estas variables no entran en una formula compuesta.

## Asignacion territorial

La arquitectura presidencial nacional reconstruida queda fija:

```text
24 entidades
2 centros minimos por entidad = 48
72 centros adicionales por D'Hondt sobre electores
48 + 72 = 120
```

Los 2 minimos territoriales no cuentan como plazas previas de D'Hondt. D'Hondt
solo determina cuota por estado; no selecciona centros.

En una corrida local read-only sobre la BD de desarrollo (`Presidenciales 2025`,
frame de centros activos), las cuotas fueron:

| estado | cuota |
| --- | --- |
| 1 | 9 |
| 2 | 6 |
| 3 | 3 |
| 4 | 7 |
| 5 | 4 |
| 6 | 5 |
| 7 | 8 |
| 8 | 3 |
| 9 | 4 |
| 10 | 4 |
| 11 | 7 |
| 12 | 4 |
| 13 | 10 |
| 14 | 4 |
| 15 | 3 |
| 16 | 4 |
| 17 | 4 |
| 18 | 5 |
| 19 | 4 |
| 20 | 3 |
| 21 | 12 |
| 22 | 2 |
| 23 | 2 |
| 24 | 3 |

Suma: 120.

## Seleccion dentro del estado

El frame operativo lo define la Tabla Mesa o `election_centers` vigente de la
eleccion objetivo. Si no existe frame por eleccion, se usa el fallback ya
existente de centros activos. En ambos casos, V1 presidencial filtra a las 24
entidades nacionales.

Dentro de cada estado:

1. Excluir centros con `selector_score = NULL`.
2. Ordenar por electores actuales descendente.
3. Recorrer desde el centro mas grande con tolerancia inicial de 2 pp.
4. Seleccionar si `selector_score <= tolerance`.
5. Si no se llena la cuota, ampliar la tolerancia con:

```text
[2, 4, 6, 8, 10, 15, 20, inf]
```

Cada vez que se amplia la tolerancia, se vuelve a recorrer desde el centro mas
grande. El score historico determina aptitud; el tamano determina prioridad
operacional.

## Salida auditable

Cada titular incluye:

- `codigo_cne`
- `estado`
- `num_electores`
- `cuota_estado`
- `selector_score`
- `score_source`
- `n_hist`
- `recent_distance`
- `historical_mae`
- `historical_rmse`
- `historical_bias`
- `historical_volatility`
- `tolerancia_seleccion`
- `pasada_seleccion`
- `rank_tamano_estado`
- `metodo = longitudinal_mae`
- `algorithm_version = longitudinal_mae_v1`
- `historical_elections_used`

La generacion conserva metadata deterministica: `frame_hash`,
`historical_data_hash`, `generated_at`, cuotas, conteo de frame y cobertura
historica.

## Evidencia experimental

Los backtests longitudinales previos muestran:

| target | recent_mae | historical_mae |
| --- | --- | --- |
| 2013 operational | 1.28 | 1.80 |
| 2018 operational | 3.94 | 2.37 |
| 2024 operational | 3.39 | 2.89 |

La falsificacion posterior encontro persistencia within-state en las cuatro
transiciones presidenciales, no descarto `historical_mae`, pero documento dos
cautelas:

- `historical_mae` depende de centros con historial enlazado, una subpoblacion
  mas antigua y estructuralmente distinta.
- La prueba de turnout es parcial porque 2024 no tiene `votantes` comparable en
  el CSV local.

## Alcance

V1 aplica solo a:

- elecciones nacionales presidenciales;
- historicos presidenciales normalizados;
- dimension politica `pct_gobierno`/bloque de referencia equivalente.

Fuera de alcance:

- gobernadores;
- alcaldes;
- circuitos legislativos;
- referendos;
- `winner_share`, `top2_gap` o `full_profile`;
- score compuesto, alfa, minimax, PPS o random baseline;
- reglas especiales por ano o tipo de shock.

## Estado operativo

`longitudinal_mae_v1` queda como metodo sucesor experimental. El selector
productivo por defecto sigue siendo `stratified_random_v1`.
