# Selector productivo de muestra

Decision V1: la seleccion productiva es aleatoria estratificada.

Los resultados historicos no se usan para rankear, filtrar, corregir ni
redibujar centros. RMSE, score, mu, sigma, recency, source factors y rankings
historicos quedan disponibles solo para analisis y auditoria experimental.

## Universo

El universo es la Tabla Mesa de la eleccion corriente, representada por
`election_centers` cuando existe para `id_eleccion`.

Si una eleccion todavia no tiene filas elegibles en `election_centers`, el
selector conserva el fallback operativo a `centros.activo=1`.

## Estratificacion

Para elecciones presidenciales V1, el estrato es el estado.

## Tamano

El tamano viene de la ficha tecnica cuando exista un campo operativo para ello.
Mientras ese campo no existe, la pantalla usa el default experimental `180`.

## Cuotas

La asignacion estatal es proporcional a electores inscritos del frame.

Regla deterministica:

1. calcular cuota exacta por estado;
2. tomar el piso;
3. si el tamano alcanza para todos los estados, garantizar minimo 1;
4. repartir remanentes por mayor fraccion, mayor peso electoral y nombre de
   estado;
5. nunca exceder la capacidad real del estado en el frame.

## Aleatoriedad

Dentro de cada estado, los centros se ordenan por codigo y se seleccionan con
`random.Random(seed)`. La misma eleccion, frame, tamano, reservas y seed produce
la misma muestra.

La muestra genera titulares y reservas. Las reservas quedan registradas pero
inactivas hasta ser promovidas.

## Reproducibilidad

Cada aplicacion registra en `muestra_generaciones`:

- `id_eleccion`;
- `tm_hash`;
- `metodo = stratified_random`;
- `sample_size`;
- `reserve_size`;
- `seed`;
- `cuotas_json`;
- `frame_count`;
- `frame_electores`;
- `algorithm_version`;
- `created_at`.

El hash de Tabla Mesa se calcula sobre codigo de centro, estado, electores y
mesas del frame usado por el selector.

## Sustituciones

Una sustitucion valida promueve una reserva a titular y desactiva el titular
removido. Toda sustitucion se registra en `muestra_sustituciones` con centro
removido, centro sustituto, motivo, usuario y timestamp.

No se hacen sustituciones silenciosas.

## Estimador

No se cambia el estimador productivo en esta decision. Los pesos siguen basados
en variables disponibles antes de la eleccion, actualmente electores inscritos.

El experimento oracle con votos validos target queda como hallazgo de
investigacion, no como comportamiento productivo.
