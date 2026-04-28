# Formato Estándar de Tabla de Mesa (TM)

## Descripción
CSV interno que normaliza los archivos de Tabla de Mesa del CNE.
Una fila por MESA (no por centro). El cargador agrupa por centro al importar.

## Formato

Archivo: `tm_YYYY_descripcion.csv`
Encoding: UTF-8
Separador: `,`
Cabecera: obligatoria (primera fila)

## Columnas

| # | Columna | Tipo | Obligatorio | Descripción |
|---|---------|------|-------------|-------------|
| 1 | `codigo_centro` | TEXT | ✅ | Código permanente del CNE (CTRO_PROP). Ej: `10101027` |
| 2 | `nombre_centro` | TEXT | ✅ | Nombre del centro electoral |
| 3 | `direccion` | TEXT | | Dirección del centro |
| 4 | `cod_estado` | TEXT | ✅ | Código del estado. Ej: `01` (DC), `23` (Zulia) |
| 5 | `estado` | TEXT | ✅ | Nombre del estado. Ej: `DTTO. CAPITAL` |
| 6 | `cod_municipio` | TEXT | ✅ | Código del municipio dentro del estado. Ej: `01` |
| 7 | `municipio` | TEXT | ✅ | Nombre del municipio |
| 8 | `cod_parroquia` | TEXT | ✅ | Código de la parroquia dentro del municipio. Ej: `01` |
| 9 | `parroquia` | TEXT | ✅ | Nombre de la parroquia |
| 10 | `numero_mesa` | INTEGER | ✅ | Número de mesa dentro del centro |
| 11 | `electores` | INTEGER | ✅ | Electores inscritos en esta mesa |
| 12 | `circuito_an` | INTEGER | | Circuito de Asamblea Nacional. NULL si no aplica |
| 13 | `lat` | REAL | | Latitud del centro. Ej: `10.460018` |
| 14 | `lon` | REAL | | Longitud del centro. Ej: `-66.987559` |
| 15 | `riesgo` | INTEGER | | Nivel de riesgo: 1=bajo, 2=medio, 3=alto. Default: 1 |

## Ejemplo

```csv
codigo_centro,nombre_centro,direccion,cod_estado,estado,cod_municipio,municipio,cod_parroquia,parroquia,numero_mesa,electores,circuito_an,lat,lon,riesgo
10101027,UNIDAD EDUCATIVA ANTONIO ORNES,BARRIO SAN JOSE COTIZA,01,DTTO. CAPITAL,01,MP. LIBERTADOR,01,PQ. ALTAGRACIA,1,485,,10.460018,-66.987559,1
10101027,UNIDAD EDUCATIVA ANTONIO ORNES,BARRIO SAN JOSE COTIZA,01,DTTO. CAPITAL,01,MP. LIBERTADOR,01,PQ. ALTAGRACIA,2,488,,10.460018,-66.987559,1
10101027,UNIDAD EDUCATIVA ANTONIO ORNES,BARRIO SAN JOSE COTIZA,01,DTTO. CAPITAL,01,MP. LIBERTADOR,01,PQ. ALTAGRACIA,3,467,,10.460018,-66.987559,1
```

## Notas

- `lat` y `lon` son opcionales en el archivo TM. Se pueden enriquecer después desde
  una fuente GPS separada (como la Hoja2 del archivo 2018).
- `riesgo` es opcional. Si no viene en el TM del CNE se asigna 1 (bajo) por defecto.
- `circuito_an` solo aplica para elecciones de Asamblea Nacional.
- El cargador agrupa las mesas por `codigo_centro` para calcular
  `num_mesas` y `num_electores` al insertar en la tabla `centros`.
