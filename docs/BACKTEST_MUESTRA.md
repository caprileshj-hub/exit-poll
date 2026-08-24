# Backtest de seleccion de muestra

Este arnes experimental evalua si una seleccion asistida por historicos habria
representado mejor el resultado agregado que una seleccion aleatoria
estratificada.

Este backtest evalua error de seleccion usando resultados conocidos de centros
como oracle. No simula error de campo de un exit poll.

Nota productiva: `historical_rmse_state` queda como estrategia experimental y
no fue promovida al selector de produccion V1. La seleccion productiva usa
`stratified_random` sobre la Tabla Mesa corriente.

## Que mide

- Error nacional de brecha gobierno-oposicion producido por centros
  seleccionados.
- Error por estado y metricas agregadas estatales.
- Comparacion por eleccion historica entre `historical_rmse_state` y la
  distribucion de `stratified_random`.

## Que no mide

- No respuesta, rechazo, encuestadores ni error de entrevistas.
- Fraude, hipotesis politicas, ponderaciones de campo ni dinamica temporal.
- Error total de un exit poll.

## Regla antileakage

Para el target historico, el frame de seleccion usa solo `centro_snapshot`,
`centros` y `estados`: codigo del centro, nombre, estado, mesas y electores.
No incluye votos, porcentajes, participacion ni resultados del target.

Los resultados de `target_ref` se cargan despues de seleccionar centros, dentro
de la evaluacion `selection_only_estimate`.

## Tablas usadas

- `centro_snapshot`: frame historico por `eleccion_ref`, con electores y mesas.
- `centros`: geografia vigente del centro y enlace a estado.
- `estados`: nombre del estado para estratificar y reportar.
- `resultados_historicos`: resultados agregados por centro para entrenar con
  elecciones anteriores y evaluar el target despues de seleccionar.
- `historico_fuentes`: no se modifica; queda disponible para auditoria externa
  de fuentes.

El modulo es read-only respecto a SQLite: no inserta, actualiza ni elimina filas.

## Estrategias v1

`stratified_random` asigna el tamano muestral por estado de forma proporcional a
electores del frame. El algoritmo toma el piso de la cuota exacta, garantiza un
centro por estado cuando el tamano alcanza para todos, y reparte remanentes por
mayor fraccion, mayor peso electoral y nombre de estado. La semilla es
obligatoria y se registra.

`historical_rmse_state` calcula, para cada eleccion anterior al target, el
residual del centro contra la brecha de su estado:

```text
residual = (pct_gobierno_centro - pct_oposicion_centro)
         - (pct_gobierno_estado - pct_oposicion_estado)
RMSE = sqrt(mean(residual^2))
score = max(0, 100 - 5 * RMSE)
```

Con `n >= 3` el centro es candidato normal. Con `n = 2` se calcula RMSE y se
marca `evidencia_limitada`. Con `n <= 1` no hay score. No usa shrinkage,
factores de fuente, cobertura, granularidad, recencia, volumen ni convergencia.

## Estimador v1

`selection_only_estimate` estima la brecha dentro de cada estado usando solo los
centros seleccionados con resultados target ya abiertos para evaluacion. Los
centros se ponderan por electores del frame; luego los estados se combinan con
el peso electoral del frame. No usa votos validos del target como peso.

## Ejecucion

```powershell
python backend/backtest_muestra.py
python backend/backtest_muestra.py --sample-size 180 --random-runs 100
python backend/backtest_muestra.py --json
```

La CLI abre `backend/exitpoll.db` en modo read-only y muestra un resumen humano.
Con `--json` imprime el dict completo.

## Limitaciones

- La geografia de entrenamiento se toma desde `centros`, porque
  `centro_snapshot` no guarda estado historico.
- Si un target no tiene `centro_snapshot` o resultados agregados por centro, se
  reporta `SKIPPED` con razon explicita.
- No declara un ganador global; solo reporta resultados por eleccion y
  estrategia.
