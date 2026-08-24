# Historial experimental de muestreo

Este documento consolida la evolucion metodologica previa a la decision V1.
Describe experimentos y hallazgos; no define comportamiento productivo.

## Resumen ejecutivo

La linea experimental partio de un laboratorio asistido por historicos, luego
probo ranking por RMSE, estabilidad de offsets, innovacion y descomposiciones
del error. El resultado practico fue no promover `historical_greedy` ni
`portfolio_balanced` a produccion.

La decision productiva V1 es aleatoria estratificada por estado con cuotas
proporcionales a electores inscritos.

## E0 - Laboratorio historico inicial

El laboratorio de muestra ordenaba centros con indicadores historicos de
representatividad, estabilidad y volumen. Esa linea era util para exploracion,
pero mezclaba informacion historica incompleta con decisiones que podian leerse
como seleccion productiva.

Estado: reemplazado como criterio productivo. Conservado como auditoria y
analisis.

## E1 - Score historico explicable

Se separo el score de utilidad de la confianza del dato. El score podia usar
representatividad relativa, estabilidad, volumen y convergencia temporal. La
confianza quedaba como semaforo paralelo.

Hallazgo: explicar el score no resuelve el problema de fondo si el historico
termina determinando inclusion productiva.

Estado: experimental.

## E2 - Backtest leave-one-election-out

Se implemento un arnes read-only para evaluar elecciones historicas como target
y entrenar solo con elecciones anteriores. La evaluacion mide error de seleccion
con resultados target conocidos como oracle; no simula no respuesta ni error de
campo.

Targets con backtest operacional local:

- 2012-presidencial;
- 2013-presidencial;
- 2018-presidencial.

Estado: herramienta experimental conservada.

## E3 - Ranking por RMSE estatal

La estrategia `historical_rmse_state` calcula el residual del centro contra su
estado en elecciones previas y usa el RMSE historico como criterio de seleccion.

Hallazgo: el ranking historico no gano de forma robusta contra la distribucion
aleatoria estratificada. En 2018 mejoro frente a la mediana aleatoria en error
nacional, pero no constituyo evidencia suficiente para promoverlo.

Estado: no promovido.

## E4 - Persistencia de RMSE

El RMSE historico predice el error futuro de centro con fuerza en 2012 y 2013,
pero pierde potencia en 2018 y queda en zona intermedia en 2024. Eso demuestra
que el historico contiene informacion real, pero no basta para convertirlo en
selector productivo.

Estado: hallazgo de investigacion.

## E5 - Offsets `mu`

Se estudio el offset promedio del centro contra su estado:

```text
mu_c = promedio historico de residual centro-estado
```

El offset historico es persistente, especialmente cuando hay varias elecciones
previas. Tambien puede quedar descentrado si el ponderador de evaluacion cambia
de votos validos a electores inscritos.

Estado: diagnostico poblacional, no criterio de inclusion.

## E6 - Innovacion `sigma`

Se estudio la dispersion historica del residual del centro como proxy de
innovacion. El resultado fue mas debil que `mu`: aporta diagnostico secundario,
pero no una regla confiable de seleccion V1.

Estado: diagnostico experimental.

## E7 - Descomposicion B + I

Para una muestra seleccionada, el error nacional puede escribirse como suma de:

```text
Error_S = B_S + I_S
```

donde `B_S` es el balance de offsets historicos de los centros seleccionados e
`I_S` es la innovacion target agregada. Si la identidad no cierra
numericamente, el problema es de definiciones o pesos.

Hallazgo: el balance de offsets puede verse razonable y aun asi depender de
pocos centros extremos. Por eso se recomienda reportar dispersion de `mu` y la
mayor contribucion absoluta `|a_c mu_c|` cuando se estudien carteras
experimentales.

Estado: diagnostico duro, no regla productiva.

## E8 - Portfolio balanced

Se considero una cartera historicamente balanceada bajo una banda blanda de
`sum(a_c mu_c)`. Antes de ejecutarla, la metodologia exigia preregistrar la
tolerancia, desempates y criterio de victoria para evitar tuning post hoc.

La decision de producto cerro esa linea para V1: no se agrega
`portfolio_balanced`, nuevo score, shrinkage, recency ni correccion historica.

Estado: fuera de alcance V1.

## Decision final V1

La seleccion productiva sera `stratified_random`.

Los experimentos historicos quedan documentados porque explican por que la
opcion aparentemente mas sofisticada no fue promovida. La razon central no es
que los historicos no tengan senal; es que usar resultados anteriores para
corregir o redibujar la muestra cambia la naturaleza del sistema. El exit poll
 debe medir la eleccion corriente.
