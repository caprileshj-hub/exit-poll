# METODOLOGIA_ESTADISTICA.md — Exit Poll Venezuela

> Metodología estadística del módulo de Estudios Históricos y el Analista IA.
> Documento vivo: registra el rigor metodológico implementado, las particularidades encontradas
> en cada tipo de elección, y los hallazgos y resoluciones surgidos durante el desarrollo.
> Actualizar cada vez que se agregue un nuevo estudio o se extienda el marco analítico.
> Última actualización: 2026-05-19

---

## 1. Marco estadístico general

### 1.1 Métricas de acertividad

Todas las tarjetas de estudios históricos calculan las siguientes métricas en tiempo de respuesta
(sin almacenar, siempre recalculadas desde los datos crudos):

#### MAE Mosteller M3 (métrica principal)
La Medida 3 de Mosteller —promedio del error absoluto entre las partes— es el estándar de la
literatura de exit polls desde los años 90.

```
MAE_M3 = mean( |est_gov - ofc_gov|, |est_opos - ofc_opos| [, |est_otros - ofc_otros|] )
```

Se incluye `otros` en el promedio **solo cuando `ofc_otros > 0`**, es decir, cuando existe
resultado oficial de una tercera opción. Incluir `otros=0` inflaría artificialmente la precisión.
El número de opciones usadas se registra como `mae_n_opciones` y se muestra en la tarjeta.

**Umbrales de calidad:**
| Rango | Categoría |
|-------|-----------|
| ≤ 1.0 pp | Leve |
| 1.0–2.5 pp | Moderado |
| 2.5–5.0 pp | Severo |
| > 5.0 pp | Crítico |

#### Error de brecha (spread error)
La diferencia entre la ventaja estimada y la ventaja oficial:
```
Error_brecha = (est_gov − est_opos) − (ofc_gov − ofc_opos)
```
Un `error_brecha` grande con MAE pequeño indica que el estudio
sobre/subestimó la magnitud de la ventaja aunque las cifras individuales fueran razonables.
Umbral: ≤ 2 pp leve, 2–5 pp moderado, > 5 pp severo.

#### Sesgo estructural (errores de signo opuesto)
Si `delta_gov` y `delta_opos` tienen signos contrarios, el error no es ruido aleatorio:
```
sesgo_estructural = True  iff  delta_gov × delta_opos < 0
```
Signo contrario implica que el estudio desplazó porcentaje de un bando al otro de forma
sistemática. Patrón compatible con sesgo de no-respuesta diferencial (espiral del silencio)
o con fallo de estratificación, no con varianza de muestreo aleatoria.

#### Ganador correcto
```
acierto_ganador = (est_gov > est_opos) == (ofc_gov > ofc_opos)
```
Booleano simple; para el caso Lara 2008 (ambigüedad PPT) se registra como `None` y se muestra `?`.

---

### 1.2 Efecto de diseño (DEFF) y error de muestreo

La muestra del exit poll es por conglomerados (centros de votación), no aleatoria simple.
El error de muestreo simple subestima el intervalo real. Se corrige con la fórmula de Kish (1965):

```
DEFF = 1 + (m̄ − 1) × ρ
```
Donde:
- `m̄ = n_respondentes / n_centros` (tamaño medio de conglomerado)
- `ρ = ICC_REF = 0.04` (correlación intracluster de referencia; rango típico 0.02–0.08 en Venezuela)

```
MoE_srs     = 1.96 × √(0.25 / n) × 100          # varianza máxima p=0.5
MoE_ajustado = 1.96 × √(DEFF × 0.25 / n) × 100
```

**Implicación práctica:** Un estado con 2 centros y 1.232 respondentes (m̄ = 616)
tiene DEFF ≈ 25.6×, lo que convierte un MoE teórico de ±0.9 pp en un MoE real de ±4.5 pp.
El dashboard lo muestra como alerta naranja/roja cuando DEFF > 5 o DEFF > 10.

---

### 1.3 Varianza territorial (RMSE y σ del sesgo)

Para estudios con datos estadales (múltiples estados cubiertos en el mismo estudio):

```
RMSE_estados = √( mean( (delta_gov_i)² ) )   # RMSE del error de gobierno entre estados
bias_std     = std( delta_gov_i )             # desviación estándar del sesgo estadal
pct_gov_neg  = % de estados donde delta_gov < -0.5  # subestimación de gobierno
```

Si ≥ 65% de estados muestran subestimación de gobierno, el patrón se clasifica como
"sesgo consistente" — evidencia de espiral del silencio estructural, no error de afijación puntual.
Umbral mínimo: 3 estados con datos para calcular RMSE.

---

### 1.4 Componentes TSE (Total Survey Error)

El módulo `auditor_sesgo.py` identifica y puntúa cuatro fuentes de error:

| ID | Condición de disparo | Probabilidad asignada |
|----|---------------------|-----------------------|
| `sesgo_no_respuesta_diferencial` | `delta_gov < −1.5` y `delta_opos > 1.5` | Alta |
| `sesgo_cobertura_asimetrico` | `delta_gov × delta_opos < 0` (signos contrarios) | Confirmada (si suma < 1.5 pp) / Alta |
| `error_afijacion_muestra_reducida` | `n_centros < 20` | Moderada |
| `tasa_no_respuesta_ausente` | `tasa_no_respuesta = None` | Sin datos |

El nivel de riesgo global se compone con una escala 1–4 (bajo/moderado/alto/crítico).
Si el patrón estadal es consistente (≥ 65% estados subestiman gobierno), se sube un nivel.

---

### 1.5 Centros sin reporte y sesgo del encuestador

Dos fuentes de error que los indicadores de acertividad post-hoc no capturan directamente,
pero que se manifiestan en los residuales del estudio.

#### Centros sin reporte (unit non-response a nivel de centro)

En condiciones de campo reales, algunos centros de votación no reportan sus datos al equipo
de totalización. Esto ocurre por:
- Problemas de comunicación (ausencia de señal, coordinador no contactable)
- Incidentes en el centro (cierre forzado, violencia, lentitud extrema)
- Centro excluido por decisión del coordinador en campo

**Implicación estadística:** Si los centros sin reporte no son aleatorios (y raramente lo son),
su ausencia introduce sesgo de cobertura. En Venezuela, los centros urbanos de oposición y
los rurales muy chavistas tienen las tasas de reporte más bajas por razones distintas
(acceso a comunicaciones y disposición del coordinador, respectivamente), lo que puede cancelar
parcialmente el sesgo pero no eliminarlo.

**En los datos históricos:** la columna `num_centros` en `historico_estudios` registra cuántos
centros reportaron, no cuántos estaban en la muestra original. La diferencia
`(centros_muestra − num_centros_reportados)` es la tasa de no-reporte a nivel de centro,
que actualmente no está registrada en el schema por falta de datos de muestra planificada.

**TSE mapping:** corresponde al componente `error_afijacion_muestra_reducida` (n_centros < 20)
en `auditor_sesgo.py`, pero este umbral solo detecta casos extremos. El problema general de
centros no-reportados es más sutil y requeriría la muestra planificada original como denominador.

**Pendiente:** registrar en `notas` JSON la columna `centros_planificados` para habilitar
el cálculo de tasa de no-reporte por estudio.

#### Sesgo del encuestador (interviewer bias)

Distinto de la espiral del silencio (que es sesgo del respondente), el sesgo del encuestador
es un error sistemático introducido por quien aplica el instrumento:

| Tipo | Descripción | Manifestación en los datos |
|------|-------------|---------------------------|
| **Redondeo selectivo** | El encuestador anota la marca más próxima en lugar del porcentaje exacto | Acumulación de valores en múltiplos de 5 en `pct_gov` por turno |
| **Efecto de proximidad** | El encuestador registra el voto de quien está más cerca, sesgando hacia el candidato dominante en el entorno inmediato | Amplificación del candidato local |
| **Sesgo de omisión** | Se omiten respuestas de electores con voto "inconveniente" para simplificar la hoja de campo | Subregistro sistemático de un bando |
| **Sesgo de conformidad** | El coordinador ajusta los totales del turno para que cuadren con la expectativa previa | Serie de turnos excesivamente suave, sin variación natural |

**Detección posible con datos actuales:**
- Redondeo: histograma de los valores de `pct_gov` por turno — si hay picos en 0, 5, 10, 25, 50
- Sesgo de conformidad: autocorrelación alta en la serie de turnos; RMSE inter-turno < 0.2 pp
  (señal demasiado limpia para datos de campo)

**Nota sobre la operación:** en el exit poll venezolano, el encuestador aplica el cuestionario
en papel y lo transmite por teléfono al coordinador de estado, quien hace el conteo. La fuente
de sesgo de encuestador más probable es el coordinador de estado (no el encuestador en campo),
porque él totaliza y decide qué reportar al Centro de Operaciones. Este rol de "buffer" entre
campo y totalización es una característica operativa del modelo SMS/teléfono que no existe en
exit polls donde se captura digitalmente en el centro.

**En el analista IA:** actualmente no se flagea el sesgo del encuestador. El flag
`SESGO_NO_RESPUESTA_NO_CUANTIFICADO` cubre el riesgo de espiral del silencio pero no este.
Se propone agregar en futuras versiones del prompt un flag `SESGO_ENCUESTADOR_POSIBLE` cuando
la serie de turnos muestra autocorrelación anormalmente alta.

---

### 1.6 Laboratorio de muestra y columnas diagnosticas

El laboratorio de centros es una vista de auditoria operativa, no el selector
productivo de la muestra. La tabla principal debe mostrar solo columnas que
ayudan a decidir o revisar rapido:

- centro y geografia;
- estatus seleccionable;
- uso recomendado como aptitud operativa;
- electores actuales;
- cobertura historica disponible;
- desvio relativo.

Las columnas con valor diagnostico pero menor uso en la primera lectura no se
eliminan del metodo; se mueven a la ficha expandida del centro. Este grupo
incluye GPS, mesas, `n_eff`, presencia 2024, ruptura 2024, confianza documental,
score del laboratorio, estabilidad relativa, convergencia, estabilidad de
brecha, perfil historico, fuente, granularidad y cobertura de cada historico.

`Uso` no es una clase politica del centro. La etiqueta `ancla` queda reservada a
centros fuertes para revision: dato 2024, confianza A, historico efectivo
suficiente, score de laboratorio >= 70, desvio <= 8 pp, estabilidad <= 6 pp y
sin ruptura 2024. Los demas centros con informacion util quedan como
`condicional`, `condicional_sin_2024`, `no_ancla` o `sin_score`.

El antiguo `Tipo` se conserva solo como `perfil historico` en la ficha expandida.
Es una etiqueta descriptiva heredada del barometro (`bastion`, `representativo`,
`cambiante`, `bisagra`, `volumen`, `estandar`, `sin_historico`) y no debe leerse
como decision de seleccion.

El flujo operativo queda:

1. Revisar el laboratorio, que contiene todos los centros de la base y la ficha
   diagnostica completa por centro.
2. Usar `Seleccion automatica` dentro de la pestana `Muestra actual` para
   generar la muestra candidata reproducible con `longitudinal_mae_v1`. En
   estudios domesticos se excluye `Exterior` del frame productivo.
3. Revisar en esa misma pestana los 120 centros titulares seleccionados, la
   lista de centros y el resumen por estado.
4. Gestionar los pesos desde la pestana `Pesos` dentro de `Muestra`, no como una
   pagina principal separada.

Esta separacion evita confundir tres capas:

- `longitudinal_mae_v1`: selector de seleccion automatica vigente para
  presidenciales nacionales. Usa 48 plazas fijas territoriales (2 por entidad)
  y 72 adicionales asignadas por D'Hondt sobre electores. El frame automatico
  es domestico y aplica un piso operativo de 800 electores inscritos por centro.
- Score del laboratorio: barometro exploratorio para ordenar y auditar centros;
  combina representatividad relativa, estabilidad robusta, volumen y un bonus
  capado de convergencia temporal.
- `stratified_random_v1`: selector legacy/fallback compatible para metadata
  anterior; no es el flujo visible de seleccion automatica.

---

## 2. Tipos de estudio: particularidades y hallazgos

### 2.1 Presidencial (2006, 2012, 2013)

**Estructura estándar:** un candidato gobierno (chavismo) contra un candidato opositor principal.
Se agrega una categoría `otros` cuando hay candidatos adicionales con votación relevante.

**Datos disponibles:**
- Estudio por estado: `pct_gov`, `pct_opos` por cada uno de los 22–24 estados
- Estudio nacional (NACIONAL): agregado ponderado por peso electoral
- Turno intradiario: hasta 18 turnos, con porcentajes acumulados
- Resultados oficiales: CNE por mesa o por estado

**Hallazgo — "Otros" en presidenciales:**
En 2012 y 2013, la suma estudio + oficiales no da 100% solo con gov/opos, porque participaron
candidatos minoritarios (Chirino, Sequera, Bolívar, Mora, etc.).
**Resolución:** el campo `pct_otros` se incluye en la importación y en el MAE M3 cuando
`ofc_otros > 0`. Si el estudio no registró `otros` pero el oficial sí, el MAE se calcula con 2 opciones
y se anota `mae_n_opciones = 2`.

**Hallazgo — Turnos incrementales vs. acumulados (2013):**
El Excel de 2013 registraba datos incrementales por turno (votos de ese turno, no totales),
a diferencia de 2006 y 2012 que tenían acumulados.
**Resolución:** `import_2012_2013.py` suma cumulativamente el Excel 2013 antes de calcular porcentajes.
La lógica de detección es por archivo, no por formato genérico.

**Métricas verificadas:**
| Estudio | MAE M3 | Δ Brecha | Sesgo estructural | Ganador |
|---------|--------|----------|-------------------|---------|
| Presidencial 2006 | 1.59 pp | +0.31 pp | No | Correcto |
| Presidencial 2012 | 2.82 pp | −7.52 pp | Sí | Correcto |
| Presidencial 2013 | 4.53 pp | +11.71 pp | Sí | Correcto |

---

### 2.2 Asamblea Nacional 2010 — doble componente lista + nominal

**Particularidad crítica:** la Asamblea Nacional venezolana combina un sistema proporcional
(voto lista, 96 escaños) y un sistema nominal/mayoritario por circuitos (104 escaños nominales +
3 indígenas). El exit poll captura ambos votos pero **lo que importa son los escaños, no los porcentajes de voto**.

**Dos capas de análisis:**

#### Capa 1 — Estimación del voto popular (lista)
Error en el porcentaje de voto lista entre el estudio y el oficial.
MAE M3 estándar aplicado al voto lista:
```
MAE_lista = mean( |est_gov_lista − ofc_gov_lista|, |est_opos_lista − ofc_opos_lista| )
```

#### Capa 2 — Conversión votos → escaños (algoritmo electoral)
El sistema electoral no es proporcional puro. Un error en el voto lista se **amplifica**
al convertirse en escaños por el efecto D'Hondt + circuitos plurinominales + componente nominal.

```
err_esc_real         = |est_escanos_gov − ofc_escanos_gov|
err_esc_proporcional = round( err_lista_pp × total_escanos / 100 )   # si fuese proporcional puro
err_esc_algoritmo    = err_esc_real − err_esc_proporcional           # error inducido por el sistema
factor_amplificacion = err_esc_real / err_esc_proporcional
pct_error_algoritmo  = err_esc_algoritmo / err_esc_real × 100
```

**Hallazgo:** En 2010, el factor de amplificación fue **1.80×**: cada punto porcentual de error en
voto lista se convirtió en 1.8 veces ese error en participación de escaños. El 44.4% del error total
en escaños fue inducido por el sistema electoral, no por el exit poll.

**Umbral de decisión:** la mayoría absoluta (83+ escaños de 165) es el KPI operativo, no el porcentaje.
La Capa 2 muestra si el estudio predijo correctamente cuál bloque tendría mayoría.

**Hallazgo — Sin tendencia intradiaria:**
El Excel de 2010 no tenía hojas de turnos. La tarjeta muestra "Sin tendencia intradiaria" y
deshabilita el gráfico Plotly.
**Resolución:** El campo `sin_tendencia` en `notas_json` controla el render. El gráfico no se
muestra si no hay datos de turnos, en lugar de un gráfico vacío.

**Hallazgo — "tipo": "asamblea" como discriminador:**
El análisis de Capa 1+2 se activa solo cuando `notas_json.tipo == "asamblea"`. Esto permite que
el mismo template `historico_estudio_detalle.html` sirva para presidenciales y legislativas sin
lógica de URL diferenciada.
**Resolución:** el campo `tipo` en el JSON de notas es el discriminador; se propaga desde
`import_2010.py` en tiempo de importación.

---

### 2.3 Regionales 2008 — 25 exit polls paralelos simultáneos

**Particularidad crítica:** no es un solo estudio nacional. Son **25 estudios independientes**,
cada uno con candidatos, centros y metodología propios. No existe un porcentaje de gobierno nacional
significativo porque los candidatos son distintos en cada estado.

#### Unidades de análisis

| Tipo | Cargo | Referencia |
|------|-------|------------|
| 22 gobernaciones | Gobernación | Elección regional |
| Alcaldía Mayor de Caracas | Alcaldía Mayor | Cargo especial (capital) |
| Alcaldía Municipal Libertador | Alcaldía Municipal | Municipio Caracas |
| Alcaldía Municipal Maracaibo | Alcaldía Municipal | Municipio Maracaibo |

Las dos alcaldías municipales se incluyeron porque el cliente tenía cobertura de campo en esos
municipios. Su naturaleza jurídica es distinta a la de la Alcaldía Mayor, pero metodológicamente
se tratan igual que una gobernación en el análisis.

#### Categorización política

Con candidatos distintos en cada estado, se establece una categoría uniforme para poder comparar:

| Categoría | Partidos incluidos |
|-----------|--------------------|
| Gobierno (Chavismo) | MVR, PSUV, PPT (como aliado) |
| Oposición | PJ, AD, COPEI, UNT — al menos 2 de estos en la boleta |
| Otros | Candidatos extra-bloque sin filiación chavista ni opositora clara |

**Hallazgo — Henri Falcón (Lara, PPT, 2008):**
Falcón se candidateó como PPT, partido en ese momento aliado al chavismo, y ganó la gobernación
de Lara como "disidente". En el instrumento de campo fue clasificado en la columna gobierno.
El CNE lo registra como ganador independiente. La categorización es genuinamente ambigua.

**Resolución:** Se almacena un flag `lara_nota` en el campo `notas` JSON del registro de Lara.
El template muestra badge `?` en la colección y un cuadro de alerta metodológica en el detalle.
El campo `ganador_ok` para Lara es `None` (no `True`/`False`). No se imputa ninguna decisión.

#### Esquema de datos: el problema de `ambito`

El modelo original de `historico_estudios_turnos` tenía `UNIQUE(eleccion_ref, turno)`,
válido para un estudio con una sola serie de turno. Con 25 estudios paralelos bajo el mismo
`eleccion_ref = '2008-gobernadores'`, se necesita una dimensión adicional.

**Resolución:** Se agregó columna `ambito TEXT NOT NULL DEFAULT 'NACIONAL'` a la tabla y se cambió
el constraint a `UNIQUE(eleccion_ref, ambito, turno)`. Los 43 turnos pre-existentes (estudios
presidenciales) se migraron automáticamente con `ambito = 'NACIONAL'`.
Script de migración: `backend/migrate_turnos_ambito.py` (idempotente, usa RENAME + CREATE + INSERT + DROP).

#### Registro nacional = metadatos de la colección

La fila NACIONAL en `historico_estudios` para `2008-gobernadores` no contiene porcentajes
significativos. Se usa como contenedor de metadatos de colección en el campo `notas` JSON:

```json
{
  "tipo": "coleccion_gobernadores",
  "n_estudios": 25,
  "n_centros_total": 613,
  "n_respondentes_total": 140069,
  "icc_referencia": 0.04,
  "gov_wins_estudio": 18,
  "opos_wins_estudio": 7,
  "fuente_oficial": "Wikipedia/CNE + PDF resultados municipales 2008"
}
```

`pct_gov = 0` se almacena como placeholder (documentado). El listado `/historicos` detecta
`eleccion_ref == '2008-gobernadores'` y reemplaza la tarjeta estándar por una tarjeta
tipo `coleccion` con enlace directo a la colección, para evitar mostrar "0% gobierno".

#### Fuentes de datos oficiales

- Wikipedia (`Anexo:Resultados de las elecciones regionales de Venezuela de 2008`):
  cubre 22 gobernaciones y Alcaldía Mayor.
- PDF `resultados-de-las-elecciones-municipales-2004-y-2008.pdf`: aporta los datos
  de Alcaldía Municipal Libertador (gov 53.59% / opos 41.39%) y Maracaibo
  (gov 39.71% / opos 59.90%), ausentes de la tabla de Wikipedia.
  Leído con `pdfplumber`.

#### DEFF variable por estado

Con 25 estudios de tamaños muy distintos, el DEFF varía enormemente:

| Estado | Centros | Respondentes | m̄ | DEFF estimado |
|--------|---------|-------------|---|--------------|
| Delta Amacuro | 3 | ~1.800 | 600 | ~24.9× |
| Trujillo | 2 | ~1.230 | 615 | ~25.6× |
| Carabobo | 49 | ~9.000 | 184 | ~8.3× |
| Aragua | 35 | ~5.500 | 157 | ~7.3× |
| Apure | 8 | ~500 | 63 | ~3.5× |

Estados con DEFF > 10 (pocos centros, muchos respondentes por centro) muestran alerta roja
en la tarjeta de detalle. DEFF < 5 no genera alerta. El rango 5–10 genera alerta naranja.

#### Acertividad global

20 de 24 ganadores correctamente identificados (83.3%). Lara = ambiguo (excluido del denominador).
4 proyecciones incorrectas:

| Estado | Estudio proyectó | Ganador real |
|--------|-----------------|--------------|
| Miranda | Gobierno (Cabello) | Oposición (Capriles) |
| Mérida | Gobierno (Dávila) | Oposición (Díaz Orellana) |
| Zulia | Gobierno (Di Martino) | Oposición (Pablo Pérez) |
| Municipio Libertador | Gobierno (Stalin Rondón) | Gobierno (Jorge Rodríguez) |

Libertador es el único caso en que ambos candidatos eran de gobierno; el error fue
proyectar al candidato gobierno equivocado, no proyectar el bando equivocado.

---

## 3. Hallazgos técnicos y resoluciones

### H-01: Filtro de hojas gráficas en Excel 2008 excluía estados

**Problema:** La lógica de detección de hojas "gráficas" (no de datos) usaba
`not sheet.startswith('C') and not sheet.startswith('G')` para excluir hojas
de gráficos. Esto eliminaba incorrectamente Carabobo (`C`), Cojedes (`C`) y Guarico (`G`).

**Resolución:** Función `is_graphic_sheet(name, all_names)` que verifica si el nombre
es exactamente `'G' + otro_nombre` o `'C' + otro_nombre` existente en el archivo.
Así `'GCarabobo'` es hoja gráfica pero `'Carabobo'` es hoja de datos.

```python
def is_graphic_sheet(name: str, all_names: list[str]) -> bool:
    for prefix in ('G', 'C'):
        if name.startswith(prefix):
            rest = name[1:]
            if rest in all_names:
                return True
    return False
```

**Impacto:** Sin esta corrección, 3 de 25 estados hubieran faltado en la importación.

---

### H-02: NOT NULL constraint en fila NACIONAL sin porcentajes

**Problema:** Al insertar la fila NACIONAL de `2008-gobernadores` en `historico_estudios`,
los campos `pct_gov` y `pct_opos` eran `None` (sin agregado nacional válido).
SQLite rechazó el INSERT por `NOT NULL constraint failed: historico_estudios.pct_gov`.

**Resolución:** Se almacena `pct_gov = 0, pct_opos = 0` como placeholder deliberado.
El campo `notas` JSON documenta que la fila NACIONAL es metadato de colección, no un
porcentaje válido. El template de listado detecta el caso especialmente.

---

### H-03: NOT NULL constraint en oficial de Lara (ambigüedad PPT)

**Problema:** El registro oficial de Lara tenía `o_gov = None` porque la categorización
de Falcón/PPT era ambigua. El INSERT fallaba por NOT NULL.

**Resolución:** `o_gov or 0, o_opos or 0, o_otros or 0` al momento del INSERT,
con `ganador_gov = None` en el diccionario `OFICIALES`. El flag `lara_nota` en notas JSON
permite distinguir "sin datos" de "dato ambiguo".

---

### H-04: Deduplicación de turnos con filas repetidas

**Problema:** Algunos centros aparecían múltiples veces en el mismo turno en los Excels
(reentradas de datos por los coordinadores). Sumar las filas duplicadas inflaría los votos.

**Resolución:** Estrategia "último gana" con dict keyed por `(centro, turno)`:
```python
datos[(centro, turno)] = votos_gov  # sobrescribe si ya existía
```
Para la serie acumulativa, cada turno T usa el último reporte disponible de cada centro
donde `turno_i ≤ T`, lo que genera una serie monotónica creciente de centros cubiertos.

---

### H-05: UnicodeEncodeError en consola Windows (✓/✗)

**Problema:** Windows PowerShell usa encoding CP1252. Los caracteres ✓ y ✗ (U+2713, U+2717)
no son representables en CP1252 y lanzaban `UnicodeEncodeError` al ejecutar el script.

**Resolución:** Reemplazar por `'OK'` y `'XX'` en las salidas de consola del script,
usando solo ASCII. Los templates HTML usan la entidad `&#x2713;`/`&#x2717;` directamente
y no tienen este problema.

---

### H-06: Colisión de rutas FastAPI — 2008-gobernadores vs. {ref}

**Problema:** La ruta `GET /historicos/estudios/{ref}` capturaba cualquier path segment,
incluyendo `2008-gobernadores`, antes de que llegara a la ruta de la colección.

**Resolución:** Las dos rutas nuevas (`/historicos/estudios/2008-gobernadores` y
`/historicos/estudios/2008-gobernadores/{estado_slug}`) se registraron **antes** de
`/historicos/estudios/{ref}` en `app.py`. FastAPI resuelve rutas en orden de registro,
por lo que las rutas literales tienen prioridad sobre los path params.

---

### H-07: Tarjeta principal mostraba "0% gobierno" para la colección

**Problema:** La consulta de `_historicos_unificados()` devuelve `e_gov = 0` para el
registro NACIONAL de `2008-gobernadores`, y la tarjeta estándar mostraba "Estudio: 0% / 0%".

**Resolución:** Detección por `eleccion_ref == '2008-gobernadores'` en el post-procesamiento
de `_historicos_unificados()`. El tipo se cambia a `'coleccion'` y se agrega `coleccion_url`.
El template `historicos.html` tiene un bloque `{% if e.tipo == 'coleccion' %}` antes del bloque
`con_estudio`, que muestra una tarjeta en violeta con enlace directo a la colección.

---

### H-08: Ambito 'NACIONAL' vs. slug en turno series

**Problema:** Antes de la migración, todos los turnos usaban `ambito='NACIONAL'` implícitamente.
Con los 25 estados de 2008-gobernadores, cada estado tiene su propia serie de turnos con
`ambito = slug_estado`. Si el INSERT no especificaba `ambito`, el DEFAULT='NACIONAL'
mezclaba series de estados distintos.

**Resolución:** Todos los INSERT de turnos (en `app.py`, `seed_historico_estudios.py`,
`import_2008.py`) incluyen `ambito` explícitamente. Las consultas de lectura filtran
`AND ambito = ?` con el valor correcto. El seed legacy usa `.setdefault("ambito", "NACIONAL")`
para mantener compatibilidad con datos anteriores.

---

### H-09: PDF como fuente alternativa para datos municipales

**Problema:** Los resultados de Alcaldía Municipal Libertador y Maracaibo no aparecen en
el tabla de Wikipedia para elecciones regionales 2008 (que es una tabla de gobernaciones).

**Resolución:** El PDF `resultados-de-las-elecciones-municipales-2004-y-2008.pdf`
(presente en `backend/data/2008/`) fue leído con `pdfplumber`. Extrajo los datos de 2008:
- Libertador: gov 53.59% / opos 41.39%
- Maracaibo: gov 39.71% / opos 59.90%

Estos valores se codificaron directamente en el diccionario `OFICIALES` de `import_2008.py`.

---

## 4. Analista IA — rigor metodológico

### 4.1 Arquitectura de la cadena de validación

Antes de invocar al LLM, el backend ejecuta `ai_validation.py` en secuencia:

```
datos_campo → validar_suficiencia() → normalizar_schema() → LLM (si OK) → respuesta
```

Si `validar_suficiencia()` retorna `ok=False`, el backend devuelve el mensaje estándar
`"datos insuficientes para establecer tendencias"` sin tocar la API del proveedor IA.
Esto evita consumo de tokens y previene alucinaciones sobre datos insuficientes.

### 4.2 Umbrales de suficiencia por tipo de elección

| Tipo | Opiniones mínimas | Cobertura mínima | Cortes mínimos |
|------|------------------|-----------------|----------------|
| Nacional | 100 | 15% | 3 |
| Regional | 60 | 10% | 3 |
| Municipal | 30 | 10% | 3 |

"Cortes" = número de centros distintos que han reportado.

### 4.3 Flags de contexto metodológico

El backend inyecta flags en el JSON enviado al LLM según el estado de los datos:

| Flag | Condición | Efecto en el prompt |
|------|-----------|---------------------|
| `SESGO_NO_RESPUESTA_NO_CUANTIFICADO` | `tasa_no_respuesta = None` | Advertencia obligatoria de espiral del silencio |
| `MOE_AJUSTADO_POR_DEFF` | `design_effect > 1.0` y aplicado al MoE | El LLM usa MoE ajustado sin nota adicional |
| `ALTA_NO_RESPUESTA` | `tasa_no_respuesta > 15%` | Nota de riesgo obligatoria en el reporte |

### 4.4 Restricciones del prompt v2.4

El prompt `ai_prompts.py` v2.4 define restricciones que no pueden violarse:

1. **Prohibición de ajuste:** el LLM no puede corregir ni ajustar los porcentajes por sesgo.
   Solo puede advertir el riesgo.
2. **Prohibición de declarar ganador:** incluso con ventaja clara, el analista no declara
   quién ganará. Reporta "ventaja estadísticamente observable", nunca "ganará".
3. **Prohibición de inventar datos:** si una sección del JSON no existe, se omite con
   nota estándar. No se infiere ni completa.
4. **Temperatura 0:** todos los reportes son determinísticos. El mismo JSON debe producir
   el mismo reporte en cualquier proveedor.

### 4.5 Clasificación de ventaja estadística

El LLM opera con el MoE del estudio (ajustado por DEFF cuando está disponible):

| Condición | Clasificación |
|-----------|--------------|
| `diferencia ≤ MoE` | Empate técnico |
| `MoE < diferencia ≤ MoE×2` | Ventaja marginal no concluyente |
| `diferencia > MoE×2` | Ventaja estadísticamente observable |

Si el MoE por subgrupo (`moe_subgrupo`) existe, se usa ese en lugar del MoE global,
con nota de que es una aproximación de subgrupo.

### 4.6 DEFF en el analista IA

El `analista_ia.py` calcula el DEFF antes de construir el JSON para el LLM:
- Si hay datos de `n_respondentes` y `n_centros` en la muestra, calcula DEFF con ICC=0.04
- El MoE en el JSON ya viene ajustado (`margen_error_ajustado_por_deff = true`)
- El flag `MOE_AJUSTADO_POR_DEFF` le indica al LLM que el MoE reportado ya incorpora DEFF

Esto cierra el circuito: el módulo histórico diagnostica DEFF post-hoc (después del estudio),
y el analista IA lo aplica en tiempo real durante la jornada electoral.

---

## 5. Tabla resumen de estudios disponibles

| Referencia | Tipo | Fecha | Centros | Turnos | MAE M3 | Ganador |
|-----------|------|-------|---------|--------|--------|---------|
| `2006-presidencial` | Presidencial | 2006-12-03 | 225 | 12 | 1.59 pp | Correcto |
| `2010-asamblea` | Asamblea | 2010-09-26 | — | 0 | 3.40 pp lista | Mayoría sí |
| `2012-presidencial` | Presidencial | 2012-10-07 | — | 13 | 2.82 pp | Correcto |
| `2013-presidencial` | Presidencial | 2013-04-14 | — | 18 | 4.53 pp | Correcto |
| `2008-gobernadores` | Colección 25 estudios | 2008-11-23 | 613 total | 405 series | por estado | 20/24 (83.3%) |

---

## 6. Convenciones de naming y schema

### Nombres de campo
- `eleccion_ref`: slug de la elección (`2006-presidencial`, `2008-gobernadores`)
- `ambito`: `'NACIONAL'` para un estudio unitario; slug de estado para colecciones regionales
- `pct_gov` / `pct_opos` / `pct_otros`: porcentajes del estudio exit poll
- `o_gov` / `o_opos` / `o_otros`: porcentajes del resultado oficial CNE
- `delta_gov = pct_gov − o_gov` (positivo = sobreestimación de gobierno)
- `turno`: entero 1-N, orden de reporte durante la jornada
- `hora_label`: etiqueta legible del turno (ej. "10:00", "T3")

### Notas JSON por tipo de estudio
```json
// Presidencial / regional simple:
{ "cand_gov": "Nombre", "cand_opos": "Nombre", "region": "...", "n_respondentes": 0 }

// Asamblea:
{ "tipo": "asamblea", "estudio_escanos": {...}, "oficial_escanos": {...}, ... }

// Colección gobernadores (fila NACIONAL):
{ "tipo": "coleccion_gobernadores", "n_estudios": 25, "n_centros_total": 613, ... }

// Estado regional (fila de estado):
{ "region": "Capital", "tipo_cargo": "Gobernación", "cand_gov_nombre": "...",
  "cand_opos_nombre": "...", "n_respondentes": 0, "lara_nota": "..." }
```

---

## 7. Pendiente metodológico

- [ ] Importar datos de Parlamentarias 2015 y Presidencial 2018 (si hay cores)
- [ ] Calcular RMSE estadal para el estudio 2008-gobernadores (24 estados con datos oficiales)
- [ ] Registrar tasas de no-respuesta históricas para activar el flag `SESGO_NO_RESPUESTA_NO_CUANTIFICADO` en los estudios pasados
- [ ] Agregar columna `centros_planificados` en `notas` JSON de cada estudio para calcular tasa real de no-reporte a nivel de centro
- [ ] Recuperar la auditoria legacy por centro cuando exista evidencia:
  numeracion interna del estudio, tabla de conversion a `codigo_centro` CNE y
  trazabilidad de semaforo/cortes. Hasta entonces, no reconstruir semaforos por
  centro de forma artificial.
- [ ] Definir la auditoria nueva como capa separada: evaluar cobertura efectiva,
  suficiencia de campo, estados inhospitos con recepcion parcial y calidad de
  datos recibidos antes de calcular RMSE, DEFF, sesgo territorial o conclusiones
  por centro.
- [ ] Agregar flag `SESGO_ENCUESTADOR_POSIBLE` al analista IA cuando la autocorrelación de la serie de turnos supera umbral (serie demasiado suave para datos de campo)
- [ ] Análisis de redondeo: histograma de `pct_gov` por turno para detectar acumulación en múltiplos de 5 — indicador de redondeo selectivo por coordinador de estado
- [ ] Calibrar ICC_REF=0.04 con datos reales de la muestra (cuando estén disponibles encuestas con datos de varianza intraclúster)
- [ ] Calcular factor de amplificación Capa 2 para legislativo si se agregan datos de Parlamentarias 2015
