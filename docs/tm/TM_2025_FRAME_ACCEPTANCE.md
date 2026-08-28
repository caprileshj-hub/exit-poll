# TM 2025 Frame Acceptance

## Status

**ACCEPTED - BEST AVAILABLE OPERATIONAL FRAME**

El archivo operativo aceptado para carga manual es:

`backend/tm_2025_macedonia_estandar.csv`

Este frame se acepta para uso operacional porque es la mejor reconstruccion
disponible, pero no se etiqueta como Tabla Mesa oficial CNE ni como
reconstruccion completa al 100%.

## Source

Fuente primaria de reconstruccion:

`https://asamblea.macedoniadelnorte.com`

La fuente es un espejo independiente de terceros. La reconstruccion se hizo con
scraping de HTML/RSC/API/endpoints, paginas cacheadas, hashes y provenance. No
se encontro un dump oficial CNE reutilizable para el TM 2025.

Etiqueta recomendada:

**TM 2025 - Macedonia Asamblea reconstructed frame - Best Available Operational Frame**

## Observed Frame

| Metrica | Valor observado |
| --- | ---: |
| Centros | 15,728 |
| Mesas | 27,705 |
| Electores | 21,286,719 |

## Comparable Benchmark

El benchmark correcto para Asamblea es el universo fisico comparable de 24
estados, solo venezolanos, excluyendo Guayana Esequiba.

| Concepto | Valor |
| --- | ---: |
| Venezolanos 2025 incluyendo Guayana Esequiba | 21,310,028 |
| Venezolanos Guayana Esequiba | 21,183 |
| Universo fisico comparable Asamblea | 21,288,845 |
| Centros operacionales esperados | 15,736 |
| Mesas operacionales esperadas | 27,713 |

El total `21,507,072` corresponde a `21,310,028 venezolanos + 197,044
extranjeros`. Al restar `21,403` de Guayana Esequiba se obtiene `21,485,669`,
que es el total venezolanos + extranjeros excluyendo Guayana Esequiba. Ese
numero no debe usarse como benchmark del electorado parlamentario de Asamblea.

La cifra `21,507,162` detectada en documentacion previa era un typo
aritmetico/transcripcional y fue corregida a `21,507,072`.

## Known Coverage Gap

| Metrica | Gap conocido |
| --- | ---: |
| Centros | 8 |
| Mesas | 8 |
| Electores comparables | 2,126 |

El gap comparable de electores es:

`21,288,845 - 21,286,719 = 2,126`

Esto equivale aproximadamente a `0.010%` del electorado comparable.

## Geographic Localization

| Estado | Referencia centros | TM centros | Deficit centros | Referencia mesas | TM mesas | Deficit mesas | Deficit electores aprox. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BOLIVAR | 817 | 812 | 5 | 1,429 | 1,424 | 5 | 976 |
| AMAZONAS | 150 | 148 | 2 | 192 | 190 | 2 | 612 |
| DELTA AMACURO | 195 | 194 | 1 | 237 | 236 | 1 | 477 |

Los otros 21 estados coinciden en centros y mesas.

Los deficits estatales aproximados suman `2,065` electores, contra un residuo
nacional comparable exacto de `2,126`. La diferencia residual de 61 electores
queda abierta porque las cifras estatales usadas en esa comparacion son
secundarias/aproximadas.

## Resolution

Los missing units se preservan. No se imputan centros ni mesas.

La reconciliacion agregada demuestra que los 8 missing units son necesariamente
8 centros de una mesa cada uno:

- Bolivar: 5 centros / 5 mesas.
- Amazonas: 2 centros / 2 mesas.
- Delta Amacuro: 1 centro / 1 mesa.

Esto no identifica documentalmente cuales son los 8 centros individuales.

## Operational Materiality

La materialidad operativa disponible parece baja por magnitud nacional:

- 8 centros sobre 15,736 esperados.
- 8 mesas sobre 27,713 esperadas.
- 2,126 electores sobre 21,288,845 comparables.

No se declara materialidad cero. Tampoco se afirma que todos los missing units
queden fuera del universo elegible por piso de 800 electores.

## Known Falsifier

`060701010` - ESCUELA NACIONAL SAN MARTIN DE TURUNBAN

- Estado: Bolivar.
- Municipio: Sifontes.
- Parroquia: CM. Tumeremo.
- Regionales 2025: 889 electores.
- Clasificacion: INDETERMINADO.
- `cantidadMesas=0`.

Este centro falsifica la afirmacion absoluta "todos los missing units tienen
menos de 800 electores". La formulacion valida es mas estrecha: la mayoria de
los candidatos observados en los tres estados tiene electorados inferiores a
800, pero no puede demostrarse que todos los missing units hubieran quedado
fuera del universo elegible.

## D'Hondt

El diseno legacy usa una muestra objetivo de 120 centros:

- 2 centros garantizados por cada una de 24 entidades: 48.
- 72 centros adicionales distribuidos por D'Hondt sobre electores.

La evidencia existente no ha demostrado que la discrepancia conocida altere la
asignacion territorial D'Hondt. Esa conclusion solo cubre la robustez de
asignacion estatal. No demuestra robustez de seleccion intraestatal ni permite
afirmar cuales centros especificos resultarian seleccionados dentro de Bolivar,
Amazonas o Delta Amacuro.

## Exterior

`not_applicable`

Exterior no forma parte del universo territorial aplicable al proceso
parlamentario/regional del 25-M 2025. No debe tratarse como missing, como cero
observado, ni como perdida de aproximadamente 69,000 electores respecto de 2024.
Si un artefacto estructurado requiere el valor numerico `0`, ese cero es tecnico
y debe leerse como N/A.

## Guayana Esequiba

Guayana Esequiba es una circunscripcion administrativa superpuesta, no una
duplicacion fisica del frame.

La circunscripcion identificada usa 12 centros y 25 mesas ubicados fisicamente
en Bolivar. Esos centros ya aparecen en el frame reconstruido bajo su geografia
fisica. No deben duplicarse ni reasignarse sin evidencia adicional.

Ademas, el patron `25 / 12 = 2.08` mesas por centro no corresponde al deficit
de Bolivar, que es `5 / 5 = 1` mesa por centro.

## Rejected Alternative

`backend/tm_2025_macedonia_estandar_candidate_completed.csv`

**REJECTED AUDIT ARTIFACT - DO NOT IMPORT**

Ese archivo fue generado en una pasada anterior mediante un filtro heuristico
que cuadraba el benchmark nacional:

- 15,736 centros.
- 27,713 mesas.

Pero los 8 centros agregados quedaron en Guarico, Lara, Merida, Miranda, Nueva
Esparta y Tachira, mientras los deficits reales estaban en Bolivar, Amazonas y
Delta Amacuro. Hacer coincidir el agregado nacional empeoro la reconciliacion
territorial. El archivo se conserva como evidencia de auditoria y como
justificacion de la decision de no imputar missing units.

## Candidate Audits

Artefactos de auditoria conservados:

- `tm_2025_missing_centers_candidates.csv`
- `docs/tm/TM_2025_MISSING_CENTERS.md`
- `tm_2025_missing_centers_06_22_23_audit.csv`
- `docs/tm/TM_2025_MISSING_CENTERS_06_22_23.md`

La segunda auditoria concluyo:

- Bolivar: 18 candidatos, 8 CONFIRMADO, 10 INDETERMINADO; se necesitan 5.
- Amazonas: 5 candidatos, 1 CONFIRMADO, 1 PROBABLE, 3 INDETERMINADO; se necesitan 2.
- Delta Amacuro: `230303004`, PROBABLE, 467 electores, `cantidadMesas=0`.

Conclusion: no existe correspondencia documental unica suficiente para
seleccionar 5+2+1 sin introducir una regla heuristica.

## 2024 Mesa Limitation

No debe interpretarse automaticamente `30,308 mesas 2024 -> 27,705 mesas 2025`
como una consolidacion electoral real de mesas. En el TM 2024 existen mesas
derivadas por `CAP_MESA=1000` para aproximadamente 4,762 centros segun ADR-018.

La comparacion de centros 2024 -> 2025 puede usarse con cautela. La comparacion
bruta de cantidad de mesas queda contaminada por generacion sintetica/derivada
en 2024.

## Provenance

Artefactos principales:

- `backend/tm_2025_macedonia_estandar.csv`
- `backend/data/2025/tm_2025_macedonia_provenance.csv`
- `backend/data/2025/tm_2025_macedonia_metadata.json`
- `backend/data/2025/tm_2025_macedonia_hashes.json`
- `docs/tm/TM_2024_2025_COMPARACION.md`
- `docs/tm/TM_2025_MISSING_CENTERS.md`
- `docs/tm/TM_2025_MISSING_CENTERS_06_22_23.md`

Hash SHA-256 del TM base aceptado:

`9f2ac8e0ed0d14aa73cb399b3f790d5a6ea57b88eaea77a98991114a57b72e30`
