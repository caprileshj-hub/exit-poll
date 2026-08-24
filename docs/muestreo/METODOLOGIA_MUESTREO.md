# Metodologia productiva de muestreo

Estado de decision metodologica: V1 adoptada.
Estado de implementacion: separado de este documento y de este commit.
Metodo: `stratified_random`.
Version algoritmo: `stratified_random_v1`.

## Decision

La seleccion productiva de centros para la muestra debe ser aleatoria
estratificada.
Los resultados historicos no se usan para rankear, filtrar, corregir ni
redibujar centros en V1.

Los historicos pueden informar analisis, auditorias y backtests, pero no
determinan la inclusion de centros ni corrigen los resultados observados de la
eleccion corriente.

## Universo

El universo es la Tabla Mesa de la eleccion corriente.

En el sistema, el frame operativo se toma de `election_centers` para el
`id_eleccion` cuando existe. Si todavia no hay Tabla Mesa cargada para esa
eleccion, el selector conserva el fallback operativo a `centros.activo = 1`.
Ese fallback debe considerarse transitorio y debe quedar visible en la metadata
de la generacion.

No entran centros nulos, duplicados ni centros fuera del frame usado por el
selector.

## Estratificacion

Para elecciones presidenciales V1, el estrato es el estado.

Cada centro pertenece a un unico estado del frame. La cuota estatal se calcula
sobre electores inscritos del frame, no sobre votos historicos ni votos target.

## Tamano

El tamano de la muestra lo define la ficha tecnica.

Mientras la ficha no tenga un campo operativo definitivo para tamano de muestra,
el default experimental actual es `180`.

## Asignacion de cuotas

La asignacion por estado es proporcional a electores inscritos del frame.

Regla deterministica de minimos y redondeo:

1. Calcular la cuota exacta del estado: `n * electores_estado / electores_frame`.
2. Tomar el piso de cada cuota.
3. Si el tamano alcanza para todos los estados con centros elegibles, garantizar
   minimo 1 centro por estado.
4. Repartir remanentes por mayor fraccion decimal.
5. En empates, ordenar por mayor peso electoral y luego por nombre de estado.
6. Nunca asignar mas centros que la capacidad real del estado en el frame.

Las cuotas resultantes deben sumar el tamano solicitado, salvo que el frame
tenga menos centros elegibles que `sample_size`; en ese caso la muestra no puede
exceder la capacidad real del frame.

## Seleccion dentro del estrato

Dentro de cada estado, la seleccion es aleatoria reproducible mediante `seed`.
El algoritmo ordena los centros por codigo antes de aplicar el generador
deterministico, de modo que la misma eleccion, frame, ficha y semilla produzcan
exactamente la misma muestra.

La generacion produce:

- titulares;
- reservas.

Titulares y reservas no se solapan.

## Reproducibilidad

Cada generacion debe guardar o asociar:

- `id_eleccion`;
- version o hash de la Tabla Mesa (`tm_hash`);
- `metodo = stratified_random`;
- `sample_size`;
- `reserve_size`;
- `seed`;
- cuotas resultantes;
- timestamp;
- version del algoritmo;
- conteo de centros y electores del frame.

Contrato: la misma eleccion, el mismo frame, la misma ficha y la misma semilla
deben producir exactamente la misma muestra.

## Estimador

Esta decision no cambia el estimador productivo.

Los pesos productivos siguen basados en variables disponibles antes de la
eleccion, actualmente electores inscritos, salvo que exista una medida
operacional independiente de participacion disponible antes del operativo.

El experimento oracle con votos validos target se documenta como hallazgo de
investigacion. No es comportamiento productivo.

## Historicos fuera del selector

No se usan para inclusion:

- RMSE;
- score;
- `mu`;
- `sigma`;
- recency;
- factores de fuente;
- rankings historicos;
- correcciones con resultados anteriores;
- ponderacion por votos oficiales target.

Los experimentos historicos existentes permanecen disponibles para auditoria y
metodologia, pero no son estrategia productiva V1.

## Cambios manuales

Se permite sustituir un titular por una reserva.

Toda sustitucion debe registrar:

- centro removido;
- centro sustituto;
- motivo;
- fecha;
- usuario.

No se permiten sustituciones silenciosas.

## UI minima

La vista productiva de muestra debe mostrar como minimo:

- centro;
- estado;
- municipio;
- electores;
- rol: titular o reserva.

Tambien debe mostrar metadata:

- metodo;
- tamano;
- semilla;
- version o hash de Tabla Mesa.

`Score` no debe presentarse como criterio productivo.

## Limites

La seleccion aleatoria estratificada no optimiza error historico ni busca una
cartera con offsets balanceados. Esa renuncia es deliberada: mantiene separada
la medicion de la eleccion corriente de la correccion con resultados previos.
