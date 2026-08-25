# Metodologia productiva de muestreo

Estado de decision metodologica: selector longitudinal adoptado para seleccion
automatica.
Metodo: `longitudinal_mae`.
Version algoritmo: `longitudinal_mae_v1`.

## Decision

La seleccion automatica de centros para la muestra presidencial nacional usa
representatividad longitudinal centro-estado (`historical_mae`) dentro del frame
domestico vigente.

Los historicos rankean centros dentro del estado, pero no corrigen los
resultados observados de la eleccion corriente.

## Universo

El universo es la Tabla Mesa de la eleccion corriente.

En el sistema, el frame operativo se toma de `election_centers` para el
`id_eleccion` cuando existe. Si todavia no hay Tabla Mesa cargada para esa
eleccion, el selector conserva el fallback operativo a `centros.activo = 1`.
Ese fallback debe considerarse transitorio y debe quedar visible en la metadata
de la generacion.

No entran centros nulos, duplicados ni centros fuera del frame usado por el
selector.

Para la seleccion automatica presidencial, el frame operativo es domestico y
aplica un piso de `800` electores inscritos por centro. Centros por debajo de
ese umbral permanecen visibles en el laboratorio para auditoria o decisiones
manuales, pero no entran al calculo de cuotas, ranking ni propuesta automatica.

## Estratificacion

Para elecciones presidenciales V1, el estrato es el estado.

Cada centro pertenece a un unico estado del frame. La cuota estatal se calcula
sobre electores inscritos del frame, no sobre votos historicos ni votos target.

## Tamano

El tamano de la muestra lo define la ficha tecnica.

El default operativo actual es `120` titulares.

## Asignacion de cuotas

La asignacion por estado usa 48 plazas fijas territoriales (2 por entidad) y 72
plazas adicionales por D'Hondt sobre electores inscritos del frame.

## Seleccion dentro del estrato

Dentro de cada estado, la seleccion ordena centros grandes por tamano y los
acepta si su `selector_score` longitudinal cae dentro de una escalera de
tolerancia reproducible. No usa semilla ni aleatoriedad.

La generacion produce:

- titulares;
- reservas.

Titulares y reservas no se solapan. Para el estudio domestico, el frame
productivo excluye `Exterior`; la seleccion automatica por defecto genera 120
titulares.

## Reproducibilidad

Cada generacion debe guardar o asociar:

- `id_eleccion`;
- version o hash de la Tabla Mesa (`tm_hash`);
- `metodo = longitudinal_mae`;
- `sample_size`;
- `reserve_size`;
- hash de datos historicos usados;
- cobertura historica;
- cuotas resultantes;
- timestamp;
- version del algoritmo;
- conteo de centros y electores del frame.

Contrato: la misma eleccion, el mismo frame, la misma ficha y los mismos
historicos normalizados deben producir exactamente la misma muestra.

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
