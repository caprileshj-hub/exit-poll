# Decisiones de muestreo

Este registro resume decisiones especificas de metodologia de muestra. Las ADR
generales siguen en `DECISIONES.md`.

## MD-001 - Selector productivo aleatorio estratificado

Estado: aceptada.

La seleccion productiva V1 usa `stratified_random`: cuotas por estado
proporcionales a electores inscritos y seleccion aleatoria reproducible dentro
de cada estado.

## MD-002 - Frame de eleccion corriente

Estado: aceptada.

El universo metodologico es la Tabla Mesa de la eleccion corriente. El sistema
usa `election_centers` cuando existe para `id_eleccion` y conserva un fallback
operativo a centros activos si la Tabla Mesa todavia no esta cargada.

## MD-003 - Historicos fuera del selector V1

Estado: aceptada.

RMSE, score, `mu`, `sigma`, recency, factores de fuente y rankings historicos no
participan en inclusion productiva.

## MD-004 - Experimentos conservados

Estado: aceptada.

No se eliminan `backend/backtest_muestra.py`, diagnosticos ni documentacion
experimental. Quedan como auditoria e investigacion.

## MD-005 - `historical_greedy` no promovido

Estado: rechazada como produccion.

La estrategia historica greedy puede ser evaluada, pero no selecciona centros
productivos V1. La evidencia local no muestra victoria robusta contra la
distribucion aleatoria estratificada.

## MD-006 - Sin `portfolio_balanced` en V1

Estado: fuera de alcance.

No se agrega cartera balanceada por offsets, nuevo score, tuning historico,
recency, shrinkage ni correccion con resultados anteriores.

## MD-007 - Pesos productivos preelectorales

Estado: aceptada.

El estimador productivo mantiene pesos basados en variables disponibles antes de
la eleccion, actualmente electores inscritos. Votos validos target solo pueden
usarse como experimento oracle.

## MD-008 - Reproducibilidad por semilla

Estado: aceptada.

La misma eleccion, frame, ficha y seed debe producir la misma muestra. La
generacion registra `id_eleccion`, `tm_hash`, metodo, tamano, reservas, seed,
cuotas, timestamp y version de algoritmo.

## MD-009 - Reservas y sustituciones auditables

Estado: aceptada.

La muestra incluye titulares y reservas. Una sustitucion valida promueve una
reserva y registra centro removido, sustituto, motivo, fecha y usuario. No hay
sustituciones silenciosas.

## MD-010 - UI productiva sin score como criterio

Estado: aceptada.

La UI productiva debe mostrar centro, estado, municipio, electores, rol,
metodo, tamano, semilla y version de Tabla Mesa. `Score` no debe verse como
criterio productivo.

## MD-011 - Diagnosticos de offsets como auditoria

Estado: hallazgo.

La identidad `Error = B + I` es una prueba dura de definiciones y pesos. El
balance `sum(a_c mu_c)` es diagnostico poblacional o experimental, no sumando
adicional del error ni criterio productivo V1.

## MD-012 - Robustez de carteras extremas

Estado: hallazgo.

Una cartera puede cumplir una restriccion escalar de balance usando centros con
offsets extremos que se cancelan. Si se estudian carteras experimentales, debe
 reportarse dispersion de `mu` y mayor contribucion absoluta `|a_c mu_c|`.
