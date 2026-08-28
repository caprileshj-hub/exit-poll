# Comparacion TM 2024 -> TM 2025 Macedonia
Analisis independiente. No se importo el TM 2025 a la aplicacion ni se modifico SQLite.

Status metodologico 2025: **ACCEPTED - BEST AVAILABLE OPERATIONAL FRAME**.
El archivo `backend/tm_2025_macedonia_estandar.csv` es un frame reconstruido desde
un espejo independiente de terceros (`asamblea.macedoniadelnorte.com`). No es un
dump oficial CNE ni una Tabla Mesa CNE completa.
## Metodo
- Fuente: https://asamblea.macedoniadelnorte.com/. Se inspeccionaron HTML/JS, `/api/estados`, `/api/buscar`, `/api/participacion`, `/api/verificacion` y endpoints de resultados. No se encontro dump RE/CSV/JSON completo; la reconstruccion usa HTML/RSC cacheado.
- Las paginas de estado no enlazan municipios; se usaron codigos territoriales del marco REP 2024 vigente como semillas de parroquia, y cada URL 2025 se valido por HTTP. Los centros 2025 se descubrieron desde enlaces publicados en cada parroquia.
## Totales nacionales
| Metrica | 2024 | 2025 | Delta | Delta % |
| --- | ---: | ---: | ---: | ---: |
| Centros | 15,856 | 15,728 | -128 | -0.81% |
| Mesas | 30,308 | 27,705 | -2,603 | -8.59% |
| Electores | 21,323,253 | 21,286,719 | -36,534 | -0.17% |

Exterior separado: 2024 = 69,211 electores; 2025 = `not_applicable` para el
frame territorial del 25-M. Cualquier cero tecnico en artefactos estructurados
debe leerse como N/A, no como cero observado ni como missing electoral.

Advertencia sobre mesas: la comparacion bruta `30,308 -> 27,705` no debe
interpretarse automaticamente como una consolidacion real de mesas. En el TM
2024 hay mesas derivadas mediante `CAP_MESA=1000` para aproximadamente 4,762
centros segun ADR-018. La comparacion de centros puede usarse con cautela; la
comparacion de mesas esta contaminada por generacion derivada en 2024.

## Benchmarks 2025
- Extraido Macedonia nacional: 15,728 centros, 27,705 mesas, 21,286,719 electores.
- Benchmark operacional CNE: 15,736 centros; 27,713 mesas.
- Benchmark parlamentario comparable de 24 estados fisicos: 21,288,845 venezolanos.
- Delta comparable: centros -8; mesas -8; electores -2,126.
- La cifra `21,507,162` usada en una version anterior de este documento queda corregida como typo: `21,310,028 venezolanos + 197,044 extranjeros = 21,507,072`.
- `21,507,072 - 21,403 Guayana Esequiba = 21,485,669`. Ese valor corresponde al total venezolanos + extranjeros excluyendo Guayana Esequiba; no es el benchmark parlamentario comparable de Asamblea.
- Endpoint `/api/participacion`: total_mesas=27,018, total_electores=20,832,010, re_total_voters=21,485,669. Se conserva como evidencia de endpoint, no como benchmark del electorado parlamentario.

## Brecha territorial conocida
| Estado | Referencia centros | TM centros | Deficit centros | Referencia mesas | TM mesas | Deficit mesas | Referencia electores | TM electores | Deficit electores aprox. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BOLIVAR | 817 | 812 | 5 | 1,429 | 1,424 | 5 | 1,086,202 | 1,085,226 | 976 |
| AMAZONAS | 150 | 148 | 2 | 192 | 190 | 2 | 121,553 | 120,941 | 612 |
| DELTA AMACURO | 195 | 194 | 1 | 237 | 236 | 1 | 133,979 | 133,502 | 477 |

Los otros 21 estados coinciden en centros y mesas. Como cada deficit estatal
tiene igual numero de centros y mesas, los missing units corresponden
deterministicamente a 8 centros de una mesa cada uno: 5 en Bolivar, 2 en
Amazonas y 1 en Delta Amacuro. Esta es una conclusion agregada, no una
identificacion individual de candidatos.

Los deficits estatales aproximados suman 2,065 electores; el residuo nacional
comparable exacto es 2,126. La diferencia de 61 electores no se fuerza ni se
elimina: las cifras estatales de electores son secundarias/aproximadas.

## Exterior y estructuras especiales
- Exterior no aplica al frame territorial parlamentario/regional 25-M. No es un
  missing, no representa una caida de electores respecto de 2024 y no debe
  reconciliarse contra 2024.
- `/api/estados` lista GUAYANA (`cod_estado=26`), pero el arbol usado no produjo centros unicos con codigo 26.
- Busqueda puntual `q=GUAYANA` muestra el codigo `060703003` tambien etiquetado como GUAYANA; al abrir `/guayana/0607/060703/060703003`, el HTML del centro conserva parroquia SAN ISIDRO, municipio SIFONTES, estado BOLIVAR. Por tanto no se duplica ni se reasigna.
- Guayana Esequiba no explica los 5 faltantes de Bolivar: los 12 centros / 25
  mesas asociados a esa circunscripcion administrativa ya aparecen bajo su
  geografia fisica de Bolivar. Su patron estructural (`25 / 12 = 2.08` mesas
  por centro) tampoco corresponde al deficit de Bolivar (`5 / 5 = 1`).

## Frame operativo >=800
- Piso importado: 800 electores por centro.
- 2024: 8,314 centros (52.43%), 18,435,500 electores (86.46%).
- 2025: 8,293 centros (52.73%), 18,406,684 electores (86.47%).
- Cruzan <800 -> >=800: 16; cruzan >=800 -> <800: 23; nuevos >=800: 18; desaparecidos >=800: 32.

No queda demostrado que los 8 missing units tengan todos menos de 800 electores.
La mayoria de los candidatos observados en Bolivar/Amazonas/Delta tiene
electorados inferiores a 800, pero `060701010` (ESCUELA NACIONAL SAN MARTIN DE
TURUNBAN, Bolivar / Sifontes / CM. Tumeremo) reporta 889 electores en
Regionales y queda INDETERMINADO con `cantidadMesas=0`. Ese codigo es el
falsador nominado de la hipotesis absoluta "todos <800". La materialidad
operativa parece baja con la evidencia disponible, pero no se declara cero.

## Drift de centros
- Comunes: 15,693; nuevos: 35; desaparecidos: 163.
- Cambios territoriales por codigo municipio/parroquia en comunes: 0; posibles renombres con mismo codigo: 1,099.
- Distribucion delta electores comunes: min=-187, p25=-7, mediana=-2, p75=1, max=3,315.

Mayores aumentos:
- 130203016 CASA DE LA CULTURA (MIRANDA): 320 -> 3,635 (+3,315)
- 131301017 UNIDAD EDUCATIVA LUIS EDUARDO EGUI (MIRANDA): 6,381 -> 9,493 (+3,112)
- 130301039 INSTITUTO UNIVERSITARIO TECNICO DE ADMINISTRACION IUTA (MIRANDA): 2,912 -> 5,720 (+2,808)
- 180101022 UNIDAD EDUCATIVA SAGRADO CORAZÓN DE JESÚS (TACHIRA): 673 -> 3,011 (+2,338)
- 021601001 ESCUELA BASICA PEDRO CELESTINO MUNOZ (ANZOATEGUI): 2,494 -> 4,443 (+1,949)
- 150601050 UNIDAD EDUCATIVA MUNICIPAL CARMEN HAYDEE VALDIVIESO (NUEVA ESPARTA): 2,498 -> 4,285 (+1,787)
- 130901119 BIBLIOTECA PUBLICA PAUL HARRIS (MIRANDA): 1,153 -> 2,806 (+1,653)
- 240104025 UNIVERSIDAD MARITIMA DEL CARIBE (LA GUAIRA): 3,521 -> 5,105 (+1,584)
- 150601010 UNIDAD EDUCATIVA MUNICIPAL MAESTRO GREGORIO ROMERO (NUEVA ESPARTA): 2,101 -> 3,567 (+1,466)
- 240111002 UNIDAD EDUCATIVA NACIONAL BOLIVARIANA MARE ABAJO (LA GUAIRA): 2,122 -> 3,289 (+1,167)

Mayores disminuciones:
- 060306009 UNIDAD EDUCATIVA ELEAZAR LOPEZ CONTRERAS (BOLIVAR): 943 -> 756 (-187)
- 181001001 CENTRO PENITENCIARIO DE OCCIDENTE (TACHIRA): 1,731 -> 1,606 (-125)
- 020601020 COLEGIO SAN TOME (ANZOATEGUI): 4,794 -> 4,676 (-118)
- 130501008 GRUPO ESCOLAR ALBERTO SMITH (MIRANDA): 5,451 -> 5,355 (-96)
- 040304001 UNIDAD EDUCATIVA NACIONAL LUIS AUGUSTO MACHADO (ARAGUA): 5,659 -> 5,566 (-93)
- 131401002 JARDIN DE INFANCIA CARLOS HERNANDEZ BAEZ (MIRANDA): 2,383 -> 2,292 (-91)
- 131201007 UNIDAD EDUCATIVA NACIONAL CECILIO ACOSTA (MIRANDA): 7,012 -> 6,926 (-86)
- 050401034 ESCUELA BASICA NACIONAL EL RIO (BARINAS): 436 -> 354 (-82)
- 070908021 ESCUELA ITACA (CARABOBO): 6,603 -> 6,523 (-80)
- 130601003 GRUPO ESCOLAR RAFAEL AREVALO GONZALEZ (MIRANDA): 2,761 -> 2,682 (-79)

## Cuotas D'Hondt diagnosticas
N=120; 2 garantizados por 24 entidades nacionales + 72 adicionales D'Hondt. Exterior excluido.
| Estado | Cuota 2024 | Cuota 2025 | Delta |
| --- | ---: | ---: | ---: |
| DTTO. CAPITAL | 8 | 8 | +0 |
| ANZOATEGUI | 6 | 6 | +0 |
| APURE | 3 | 3 | +0 |
| ARAGUA | 7 | 7 | +0 |
| BARINAS | 4 | 4 | +0 |
| BOLIVAR | 6 | 6 | +0 |
| CARABOBO | 8 | 8 | +0 |
| COJEDES | 3 | 3 | +0 |
| FALCON | 4 | 4 | +0 |
| GUARICO | 4 | 4 | +0 |
| LARA | 7 | 7 | +0 |
| MERIDA | 4 | 4 | +0 |
| MIRANDA | 10 | 10 | +0 |
| MONAGAS | 4 | 4 | +0 |
| NUEVA ESPARTA | 3 | 3 | +0 |
| PORTUGUESA | 4 | 4 | +0 |
| SUCRE | 4 | 4 | +0 |
| TACHIRA | 5 | 5 | +0 |
| TRUJILLO | 4 | 4 | +0 |
| YARACUY | 3 | 3 | +0 |
| ZULIA | 12 | 12 | +0 |
| AMAZONAS | 2 | 2 | +0 |
| DELTA AMACURO | 2 | 2 | +0 |
| LA GUAIRA | 3 | 3 | +0 |

Conclusion estrecha: la discrepancia conocida no ha demostrado alterar la
asignacion territorial D'Hondt del diseno legacy. Esto habla de robustez de
asignacion estatal. No demuestra robustez de seleccion intraestatal ni permite
afirmar cuales centros especificos resultarian seleccionados dentro de Bolivar,
Amazonas o Delta Amacuro.

## Simulacion de muestra 2025
No ejecutada: hacerlo con el selector longitudinal actual requiere frame de aplicacion/SQLite; se mantiene read-only y se limita el analisis al frame.
