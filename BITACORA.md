# Bitácora de Desarrollo - Exit Poll Venezuela

## Registro de Cambios

### Fase 1: Configuración y Estabilización
- **Infraestructura**: Se estableció el entorno virtual (`.venv`) y se corrigió el archivo `requirements.txt`.
- **Compatibilidad**: Se definió el flujo de trabajo para sincronizar el desarrollo entre la laptop principal y la Lenovo.
- **Correcciones**:
  - Solución al error de rutas relativas en `pip install`.
  - Configuración del intérprete de Python en VS Code para activar el entorno automáticamente.
- **Estado Actual**: El script `generador_mapa.py` es funcional y genera el mapa base correctamente.

### Fase 2: Lógica de Negocio y Datos
- **Definición de Flujo**:
  1. Entrada: Datos de encuestas (Exit Poll) por centro/parroquia.
  2. Proceso: Ponderación usando tabla maestra (`pesos_master.json`).
  3. Salida: Datos agregados por Estado para el mapa (con manejo especial para La Guaira y DC).
- **Requerimiento Especial**: Para **La Guaira** y **Distrito Capital**, la medición debe bajar hasta el nivel de **Parroquias** (debido a su condición de municipio único/especial).

### Fase 3: Integración de Datos
- **Validación de Datos**: Se recibió el archivo `pesos.json` que corrige el defecto de "Amazonas".
  - Estructura jerárquica correcta: Estado -> Municipio -> Parroquia.
  - Asignación geográfica corregida (Ej. Acevedo ahora está en Miranda).
  - Incluye pesos numéricos reales (ya no son todos 0.0).
- **Lógica de Procesamiento**: Se implementó `procesador_datos.py` con lógica híbrida.
  - Soporta ponderación por Parroquia (prioridad) o por Municipio.
  - **Regla de Negocio**: Los pesos `0.0` se ignoran en el cálculo (no son muestra activa) pero se preservan en el archivo.
  - Normalización automática de nombres para cruzar datos (ignora tildes/mayúsculas).
- **Auditoría**: Se creó `test_flujo.py` para validar la lógica del "Core" frente al modelo legacy (Excel).
  - Permite inyectar datos controlados y verificar si la ponderación de `pesos.json` se aplica correctamente.
- **Series de Tiempo**: Se añadió soporte para "Cortes" temporales.
  - `procesador_datos.py` ahora incluye `procesar_tendencias` que calcula el acumulado paso a paso.
  - Permite visualizar cómo cambia el mapa a medida que entran datos de diferentes parroquias.
- **Visualización**: Se creó `graficador_tendencias.py`.
  - **Actualización**: Ahora usa `plotly` para generar gráficos HTML interactivos.
  - Genera un gráfico individual para cada Estado y uno consolidado para **VENEZUELA**.
  - Se actualizó `test_flujo.py` para incluir datos de Zulia y probar el coloreado del mapa.
- **Totalización Nacional**: `procesador_datos.py` ahora calcula automáticamente la ventaja nacional ponderada ("VENEZUELA").
- **Refinamiento de Gráficos**:
  - Se separaron las líneas de tendencia (Oficialismo vs Oposición) en lugar de solo mostrar la ventaja.
  - Se estandarizó la salida de `procesador_datos.py` para entregar estructuras de datos completas.

### Fase 4: Refinamiento Visual y Ajustes
- **Ajuste de Simulación**: Se modificó `test_flujo.py` para iniciar la recepción de datos a las **07:00 AM** (hora de apertura de mesas).
- **Mejoras en Gráficos de Tendencia** (`graficador_tendencias.py`):
  - **Suavizado de Curvas**: Se implementó interpolación *spline* para obtener líneas curvas más estéticas.
  - **Margen de Error Visual**: Se agregaron sombras semitransparentes (±2.5%) alrededor de las líneas de tendencia para representar la incertidumbre.
  - **Escala Fija**: El eje Y ahora está fijado entre 0% y 100% para mantener consistencia visual entre estados.

### Fase 5: Inteligencia de Datos (Análisis 2024)
- **Cambio de Estrategia**: Se descartó el crawling de 2013 en favor de procesar un CSV con resultados mesa por mesa de 2024.
- **Procesador de Datos** (`procesador_csv_2024.py`): Script para ingerir data cruda, agrupar por centro, decodificar geografía desde el código CNE y calcular métricas de polarización.
- **Dashboard de Selección** (`dashboard_analisis.py`): Aplicación en Streamlit para visualizar la data electoral. Permite filtrar centros "Swing" (competidos) y "Bastiones", vital para el diseño muestral.
- **Estabilización Técnica**:
  - **Gestión de Dependencias**: Se creó `requirements.txt` (plotly, streamlit, pandas, folium).
  - **Corrección de Encoding**: `procesador_csv_2024.py` ahora soporta `latin1` para leer archivos con caracteres especiales (Ñ/tildes).
  - **Rutas Absolutas**: `dashboard_analisis.py` localiza el CSV automáticamente sin depender del directorio de ejecución.
  - **Visualización**: Ajuste matemático en `graficador_tendencias.py` para evitar desbordes en las sombras de error (clamp 0-100%).

### Pendientes Inmediatos - RESUELTOS
1. **Definición de Muestra**: Resuelto dentro del flujo FastAPI de muestra (`/muestra`, `/muestra/generar`, `/muestra/aplicar`).
2. **Generación de Pesos**: Resuelto con `calculador_pesos.py`, edición manual y persistencia en tabla `pesos`.
3. **Simulacro Integral**: Resuelto para la fase actual con dataset showcase, `/live`, SSE y validación del dashboard en Azure.
4. **Sincronización**: Resuelto; cambios recientes subidos a GitHub y desplegados en Azure.

### Fase 6: Validación Histórica y Muestreo (2017)
- **Simulación Legacy**: Se creó `simulador_legacy.py` para orquestar pruebas usando archivos Excel antiguos (`core.xlsx`). (Pausado por disponibilidad de archivo).
- **Auditoría de Integridad Geográfica**: Se desarrolló `analisis_tm_2017.py`.
  - Permite auditar archivos "Tabla Mesa" (TM) oficiales.
  - Verifica específicamente la integridad del estado **Amazonas** para detectar municipios infiltrados.
  - Calcula los pesos electorales reales por estado basados en el padrón electoral.
- **Extracción de Muestra Estratégica**: Se implementó `extraer_muestra_tm.py`.
  - **Lógica General**: Extrae los 4 centros más grandes por estado.
  - **Lógica Especial (DC y Vargas)**: Identifica las 8 parroquias con más electores y selecciona los 2 centros principales de cada una.
  - **Salida**: Genera automáticamente `muestra_estrategica_2017.csv` como insumo para la configuración del sistema.
  - **Mejora Técnica**: Uso de rutas absolutas (`os.path`) para garantizar la ejecución correcta sin importar el directorio de la terminal.

---

---

### Fase 6: Automatización — Diseño del Sistema

#### Arquitectura general
```
[APK Android] → SMS → [Gateway Android] → HTTP POST → [Backend FastAPI] → [BD SQLite/PG] → [Core Python] → [Dashboard Streamlit]
```

#### Tipos de elección soportados
- `nacional` — candidatos iguales en todos los centros
- `regional` — candidatos distintos por estado
- `municipal` — candidatos distintos por municipio
- `asamblea` — voto nominal por circuito + voto lista por estado/partido

#### App móvil
- APK Android nativo (no PWA) para envío de SMS en background sin interacción del encuestador
- Un solo APK universal; la configuración de candidatos se obtiene de la BD al registrar el número
- El votante toca candidato → botón "Opinar" → SMS enviado automáticamente
- Modo offline: encola votos localmente y envía en lote cuando recupera señal

#### Formato SMS
```
C1234;V2;T1932;L09a7F3b
```
| Campo | Descripción |
|---|---|
| `C` | ID del centro CNE |
| `V` | Candidato (V1, V2, V0=nulo) |
| `T` | Timestamp local (HHMM) |
| `L` | Coordenadas GPS en Geohash (~38m precisión, 6 chars) |

- El ID del encuestador no viaja en el SMS — se extrae del número remitente
- Longitud total: ~28 caracteres

#### Seguridad y registro
- El número de teléfono del encuestador es su ID
- SMS de números no registrados se descartan (no totalizan) y se loguean
- `sms_raw` preserva cada SMS recibido independientemente de si es válido

#### Gateway
- Teléfono Android dedicado en sala de totalización (WiFi estable + energía)
- Filtra por prefijo `C`, detecta duplicados (mismo número+T+C), reenvía por HTTP al backend
- Mantiene log local como respaldo

#### Validación GPS
- Cada centro tiene coordenadas registradas y un radio de **300 metros** (configurable por centro)
- Algoritmo: distancia Haversine entre GPS del SMS y coordenadas del centro
- Voto fuera del radio → se guarda con `valido=false`, no totaliza, genera alerta

#### Turnos internos (backend)
- Duración: **20 minutos** — invisible para encuestadores y clientes
- Cálculo al insertar: `turno = floor((hora - hora_apertura) / 1200)`
- Uso: graficar tendencia y detectar fraude

#### Control de cuotas por turno
- Piso: **8 votos / turno** — bajo meta
- Techo: **25 votos / turno** — sobre meta, señal de manipulación
- Patrones multi-turno: 3 turnos consecutivos > 25 → alerta crítica de fraude
- 2 turnos consecutivos = 0 → alerta de abandono

#### Visualización dual
- **Vista cliente**: heatmap limpio por ventaja + gráficos de tendencia + tortas/barras
- **Vista auditoría**: heatmap semáforo con estado por centro + panel de control por encuestador/turno
- Heatmap se adapta a la granularidad de la elección (estado / municipio / parroquia / circuito)
- Para Asamblea Nacional: dos capas en el mapa (toggle nominal / lista)

#### Modelo de BD — tablas principales
```
estados, municipios, parroquias, circuitos   ← geografía
elecciones, candidatos                        ← configuración de elección
centros, muestra, pesos, centros_candidatos   ← muestra y ponderación
encuestadores                                 ← operación
sms_raw, votos, alertas                       ← datos en tiempo real
```
- `votos.turno` calculado al insertar
- `votos.valido` = false si GPS fuera de radio (se guarda pero no totaliza)
- `alertas.tipo` ∈ {bajo_meta, sobre_meta, sin_reporte, gps_invalido, numero_no_registrado, fraude_patron}

#### Fase -1 — Configuración previa al día de elección
1. Definir tipo de elección y cargar candidatos con fotos
2. Cargar CSV de resultados históricos CNE
3. Seleccionar centros por tamaño + representatividad (bisagra/bastión/volumen/estándar)
4. Aplicar reglas geográficas:
   - Regla general: 2 centros por estado
   - Excepción (2 por parroquia): Distrito Capital, La Guaira, Miranda-Caracas (Chacao, Baruta, El Hatillo, Sucre)
   - Regional: 2 por municipio | Municipal: 2 por parroquia
5. Calcular pesos jerárquicos por centro
6. Generar tabla `centros_candidatos` automáticamente según tipo de elección

#### Clientes y control de acceso
El sistema es un producto — cada cliente ve solo lo que contrató. La auditoría es estrictamente interna, ningún cliente tiene acceso a ella.

```
clientes(id, nombre, email, hash_clave, activo)

contratos(id, id_cliente, id_eleccion, retardo_min)
    -- retardo_min: 0=live, 30, 60, -1=solo_cierre

accesos_geograficos(id_contrato, nivel[nacional/estado/municipio], id_referencia)
    -- id_referencia: id_estado o id_municipio según nivel, NULL si nacional

accesos_vistas(id_contrato, vista[heatmap/tendencias/tortas/barras/tabla_centros])
```

El dashboard renderiza únicamente lo contratado:
- Menú lateral filtrado por vistas del contrato
- Heatmap muestra solo la geografía contratada, resto en gris
- Datos aplicando retardo configurado
- Sin acceso a ningún módulo de auditoría

La vista de auditoría (semáforo de centros, panel de encuestadores, alertas de fraude) es un sistema separado de acceso interno exclusivo.

#### Base de datos
- Motor: **SQLite** con WAL mode y foreign keys activos
- Archivo: `backend/exitpoll.db`
- Schema: `backend/schema.sql`
- Inicialización: `backend/init_db.py` (soporta `--reset`)
- **19 tablas** organizadas en 8 bloques:
  1. Geografía: `estados, municipios, parroquias, circuitos, circunscripciones_indigenas`
  2. Centros: `centros`
  3. Elecciones: `elecciones, candidatos`
  4. Muestra: `muestra, pesos, centros_candidatos`
  5. Encuestadores: `encuestadores`
  6. Votos: `sms_raw, votos`
  7. Auditoría interna: `alertas`
  8. Clientes: `clientes, contratos, accesos_geograficos, accesos_vistas`

#### Carga de Tabla de Mesa (TM)
- Formato estándar interno: `backend/TM_ESTANDAR.md` (15 columnas, CSV UTF-8)
- Convertidor: `backend/convertidor_tm.py`
  - Soporta formatos CNE 2015 y 2018 (detección automática)
  - `--hoja` para especificar hoja Excel manualmente
  - Agregar nuevos formatos en el dict `CONVERTIDORES`
- Cargador diferencial: `backend/cargador_tm.py`
  - Siempre actualiza: `num_mesas`, `num_electores`
  - Solo si es nuevo o está vacío: geografía, nombre, circuito_an
  - **Nunca sobreescribe**: `lat`, `lon`, `riesgo`, `radio_m`
  - Centros ausentes del nuevo TM → `activo=0` (no se borran)
  - `--dry-run` para simular sin escribir

#### Completado de Fase 6
- [x] Diseñar e implementar BD (SQLite): `schema.sql` — 19 tablas, 8 bloques
- [x] `init_db.py` — inicializa/resetea BD, aplica migraciones automáticas
- [x] `TM_ESTANDAR.md` — especificación CSV interno (15 cols, 1 fila por mesa)
- [x] `convertidor_tm.py` — convierte TM del CNE (formatos 2015/2018) al estándar interno
- [x] `cargador_tm.py` — carga diferencial: actualiza mesas/electores, nunca sobreescribe lat/lon/riesgo/radio_m
- [x] `calculador_pesos.py` — calcula pesos jerárquicos por tipo de elección, respeta excepciones geográficas, edición manual por CLI
- [x] `generador_heatmap.py` — heatmap Folium nivel estado (ADM1) y municipio (ADM2), lookup spatial cacheado
- [x] `generador_dashboard.py` — dashboard completo: mapa + panel de tendencias Plotly en un solo HTML, click en polígono actualiza gráfico

#### Completado de Fase 6 (continuación)
- [x] Dashboard de configuración FastAPI (`app.py`) — 30 rutas, Jinja2 + Bootstrap 5
  - Gestión de elecciones (CRUD, activar)
  - Candidatos con fotos (upload, preview, bandos)
  - Ficha técnica estilo CIS (documento formal imprimible con error muestral calculado)
  - Pesos por centro: edición inline masiva, auto-cálculo proporcional
  - Carga de TM vía dashboard (Excel/CSV, conversión + carga diferencial)
  - Módulo de muestra: generador automático con criterios de representatividad + aplicar
- [x] Selector de muestra (`selector_muestra.py`) — criterio: centros más grandes + representatividad histórica
  - Regla general: 2 centros por estado
  - Excepciones (por parroquia): DC, La Guaira, Miranda-Caracas (Chacao, Baruta, El Hatillo, Sucre)
  - Umbral configurable (default ±10% del resultado nacional)
- [x] Integración datos CNE 2024 (`convertidor_cne2024.py`)
  - Fuente: vzlapi repo (Google Sheets con 11,927 centros + resultados)
  - Normalización de nombres de estado y distribución de electores por mesa
  - Carga a `resultados_historicos` para cálculo de representatividad
- [x] Visualización conectada al dashboard (`/visualizacion`)
  - Heatmap y Dashboard generados desde datos reales de BD (`resultados_historicos`)
  - Controles: nivel (estado/municipio), fuente (todos/muestra)
  - Vista previa inline (iframe) o nueva pestaña
  - Tendencias simuladas convergiendo al resultado histórico
  - Nombres de candidatos tomados de la BD si existen

#### Cierre de Pendientes de Fase 6
- [x] Backend FastAPI: resuelto para el flujo actual de operación y showcase con ingestión simulada, turnos, `/live`, SSE y analista.
- [x] App Android: cerrado como fuera de alcance del despliegue web actual; no bloquea el dashboard ni el demo Azure.
- [x] Gateway Android: cerrado como fuera de alcance del despliegue web actual; la operación actual usa dataset/simulador.
- [x] Dashboard de auditoría interna: cerrado como fuera de alcance del despliegue actual; queda separado del panel cliente.
- [x] Gráficos torta/barras en el panel cliente: cerrado para esta entrega; el panel actual prioriza heatmap y tendencias.
- [x] Contraste con datos de exit poll anterior: resuelto para esta fase con históricos disponibles en BD y visualización conectada.

---

### Fase 7: Visualización — Decisiones de Diseño

#### Heatmap (`generador_heatmap.py`)
- Soporta ADM1 (estados) y ADM2 (municipios)
- Lookup spatial `_adm2_lookup.json`: centroide de cada municipio → estado por point-in-polygon con ADM1
  - Se construye una sola vez y se cachea — 332 municipios mapeados, 3 sin asignar (Esequibo + fronterizos)
- Paleta: azul profundo → blanco → rojo oscuro (simétrica ±30%)
- Umbral de empate técnico: ±3%
- Zonas sin datos: gris semitransparente
- API: `generar_heatmap(datos, nivel, ruta_salida, titulo, candidatos)`

#### Dashboard completo (`generador_dashboard.py`)
- Un solo HTML autónomo: mapa 58% izquierda + panel gráficos 42% derecha
- Plotly.js cargado en `<head>` (antes de `Plotly.newPlot`) — lección aprendida
- IDs separados: `wrap-ESTADO` (contenedor show/hide) vs `pchart-ESTADO` (div Plotly interno)
- Layout construido por JS polling (`buildLayout` con `setTimeout 50ms`) para no depender de orden de eventos
- `invalidateSize()` en `window.onload` para que Leaflet recalcule tamaño tras reflow
- Click en polígono: `normId()` en JS reproduce `_id_wrap()` de Python (misma normalización)
- Gráficos de tendencia: líneas suavizadas (spline), sombra ±2.5%, anotación de ventaja actual
- API: `generar_dashboard(datos_ventaja, datos_tendencia, nivel, ruta_salida, titulo, candidatos)`

#### Pesos (`calculador_pesos.py`)
- `peso_parroquia`: normalizado dentro de la parroquia (municipal)
- `peso_municipio`: normalizado dentro del municipio, excepto DC/La Guaira/Miranda-Caracas → por parroquia
- `peso_estado`: normalizado dentro del estado (nacional) — siempre suma 1 por estado
- `peso_nacion`: fracción del electorado del estado sobre el total nacional (universo BD)
- Excepciones: `estados.es_excepcion=1` (DC, La Guaira) y `municipios.es_excepcion=1` (Chacao, Baruta, El Hatillo, Sucre)
- Edición manual: `python calculador_pesos.py <id> --set <id_muestra> campo=valor`

---

### 2026-04-28 - Bugs pendientes para corregir

#### 1. Agregacion incorrecta en simulador para elecciones regionales y municipales
- Archivo: `backend/simulador_showcase.py`
- Funcion: `calcular_resultado_ponderado()`
- Hallazgo:
  - En ramas `regional` y `municipal`, el dict `resultado` se pisa por grupo.
  - Hay asignaciones tipo `resultado[id_cand] = ...` dentro de loops por estado/municipio.
  - Efecto: el ultimo estado o municipio procesado sobrescribe los anteriores.
- Impacto:
  - Los porcentajes finales no representan un agregado correcto.
  - La salida actual no coincide con lo que promete el docstring.
- Accion sugerida:
  - Definir si la funcion debe devolver:
    - un agregado global por candidato, o
    - un resultado separado por estado/municipio.
  - Ajustar estructura de retorno y consumidor en consola/dashboard.

#### 2. Soporte incompleto de candidatos para elecciones regional, municipal y asamblea
- Archivos:
  - `backend/app.py`
  - `backend/templates/candidato_form.html`
  - `backend/schema.sql`
- Hallazgo:
  - El esquema soporta `id_estado`, `id_municipio`, `id_circuito`, `id_circ_indigena`.
  - El formulario y guardado actual solo manejan:
    - `id_eleccion`
    - `nombre`
    - `partido`
    - `bando`
    - `tipo`
    - `orden`
    - `foto_url`
- Impacto:
  - Un candidato `lista`, `nominal` o `indigena` no puede asociarse a su geografia/circuito real.
  - La app aparenta soportar esos tipos, pero no queda correctamente configurada.
- Accion sugerida:
  - Extender formulario y endpoint de guardado.
  - Validar campos segun `tipo` de candidato y `tipo` de eleccion.

#### 3. Cobertura de pruebas muy debil para el backend actual
- Archivo: `test_flujo.py`
- Hallazgo:
  - `pytest` pasa con una sola prueba del core legado.
  - Sigue usando:
    - `procesador_datos`
    - `generador_mapa`
    - `graficador_tendencias`
  - El flujo de error principal hace `return` en vez de fallar explicitamente.
- Impacto:
  - `pytest` verde no protege:
    - rutas FastAPI
    - logica de pesos del backend
    - simulador showcase
    - formularios/configuracion actual
- Accion sugerida:
  - Agregar tests minimos para:
    - import de `backend.app`
    - calculo de pesos por tipo de eleccion
    - `calcular_resultado_ponderado()`
    - rutas criticas (`/candidatos`, `/pesos`, `/visualizacion`)

---

## Deploy Azure — Estado al 2026-04-30 (RESUELTO)

### Problemas encontrados y resueltos
1. **Startup command incorrecto**: el `startup.sh` hacía `cd /home/site/wwwroot/backend` pero el zip despliega en la raíz sin subcarpeta `backend/`. → Corregido a `cd /home/site/wwwroot`. El startup command en Azure Portal también se actualizó a `bash /home/site/wwwroot/startup.sh`.
2. **Plan F1 agotado (QuotaExceeded)**: la cuota de 60 min CPU/día del plan gratuito se consumió. → Se hizo upgrade a **B1 Basic** (~$13/mes del crédito de estudiante).
3. **Exit code 127 (uvicorn no encontrado)**: el zip deploy directo no ejecutaba `pip install`. → Se intentó activar el venv de Oryx (`antenv`).
4. **ExtractTarball panic en PythonStartupScriptGenerator**: el mecanismo de Oryx (compresión `.zst`) falla al extraer dentro del contenedor. Error en `compressionHelper.go:29`. No es un bug del código, es un problema de infraestructura Azure.

### Estado actual del deploy
- **Plan**: B1 Basic.
- **App Service**: `exit-poll-ve`.
- **Resource group**: `exit-poll-rg`.
- **Dominio**: `estacomp.systems`.
- **Startup command en Azure**: `python /home/site/wwwroot/startup.py`.
- **SCM_DO_BUILD_DURING_DEPLOYMENT**: `0` (Oryx build desactivado).
- **Deploy final**: `RuntimeSuccessful`.
- **Estado final**: `Running`.
- **Verificaciones**:
  - `/config`: 200 OK.
  - `/live`: 200 OK.
  - `/stream/dashboard`: emite SSE con `data: {"ok": true, ...}`.
  - `/chat` con datos insuficientes: devuelve exactamente `Esa información no está en los datos del exit poll.`

### Resolución aplicada
1. Se empaqueta solo `backend/` en `backend_deploy.zip` usando `git archive HEAD:backend`.
2. Se reemplazó el arranque shell frágil por `backend/startup.py` para evitar problemas de CRLF.
3. Se corrigió `/live` con datos reales (`gj_name` en `generador_dashboard.py`).
4. Se ajustó el agente para hablar de opiniones, no votos, y no analizar ámbitos con datos insuficientes.

### Archivos modificados en esta sesión
- `backend/startup.py` — entrypoint Python para Azure.
- `backend/generador_dashboard.py` — SSE y fix de `gj_name`.
- `backend/app.py` — `/stream/dashboard`, `/chat`, `/config`, guardrails y textos de opiniones.
- `backend/agent.py` — abstracción OpenAI/Groq/Anthropic/Gemini y prompt reforzado.
- `backend/analista_ia.py` — respuesta estricta cuando no hay datos suficientes.
- `backend_deploy.zip` — paquete de despliegue generado localmente (no versionado).
---

## 2026-04-30 - SSE Live Dashboard y agente IA multi-proveedor

### Fase 1: Live dashboard sin recarga completa
- Se reemplazo el refresco completo de `/live` por SSE en `GET /stream/dashboard`.
- El stream entrega `geo` y `series` cada 60 segundos usando los mismos datos vivos que alimentan heatmap y tendencias.
- `generador_dashboard.py` ahora expone `updateHeatmap(data.geo)` y `updateCharts(data.series)` para actualizar Leaflet/Plotly sin reconstruir la pagina.
- El panel del chatbot (`#ai-analyst`) queda fuera del ciclo SSE y no se toca durante las actualizaciones.
- Se removio el meta refresh de `/live` y de la pantalla sin datos.

### Fase 2: Capa de proveedores IA
- Se creo `backend/agent.py` con `AI_PROVIDERS`.
- Proveedores soportados: OpenAI (`gpt-4o-mini`), Groq (`llama-3.1-8b-instant`), Anthropic (`claude-haiku-4-5-20251001`) y Gemini (`gemini-2.5-flash`).
- OpenAI, Groq y Gemini usan el SDK `openai`; Anthropic usa SDK separado.
- Se agrego `POST /chat` con respuesta streaming.
- `get_contexto_centro(centro_id)` inyecta conteos por candidato, ultimos 3 turnos e historial/clasificacion del centro cuando esta disponible.

### Fase 3: Prompt electoral
- Se incorporo el system prompt exacto del analista electoral.
- El agente queda limitado a datos del exit poll y formato obligatorio: `TENDENCIA`, `ANOMALIA`, `PROYECCION`.

### Fase 4: Configuracion IA
- Se agrego tabla `config` a SQLite (`schema.sql` + migracion en `init_db.py`).
- Se creo `/config` con selector de proveedor, API key enmascarada, modelo editable, temperatura, `max_tokens`, indicador activo y `Test connection`.
- Se agregaron `openai` y `anthropic` a requirements.

### Validacion
- `py_compile` OK para `backend/app.py`, `backend/agent.py`, `backend/generador_dashboard.py`, `backend/init_db.py`.
- Import FastAPI OK; rutas presentes: `/live`, `/stream/dashboard`, `/chat`, `/config`.
- `GET /config` con `TestClient` devuelve 200.
- Tabla `config` creada con OpenAI activo por defecto y Groq/Anthropic/Gemini inicializados.
- Busqueda confirmo que no quedan `meta refresh` ni `setInterval` para el live dashboard.

### Deploy 2026-04-30
- `az webapp deploy --src-path . --type zip` no fue aceptado por esta version de Azure CLI porque `.` no es archivo zip.
- Se genero `backend_deploy.zip` con `git archive HEAD:backend`, manteniendo el contenido de `backend/` en la raiz del paquete.
- El primer arranque fallo por `startup.sh` con CRLF en Azure (`$'\r': command not found`).
- Se agrego `backend/startup.py` para usar `python /home/site/wwwroot/startup.py` como startup command y evitar dependencia de line endings shell.
- Correccion posterior: `/live` fallaba con datos reales por `NameError: gj_name is not defined` en `generador_dashboard.py`; se paso `gj_name` a `_ensamblar_html` y se valido generando un dashboard con datos simulados.

### Ajuste agente 2026-04-30
- El agente ya no analiza ambitos con datos insuficientes; devuelve exactamente `Esa información no está en los datos del exit poll.`.
- `/chat` aplica el guardrail en backend antes de llamar al proveedor IA.
- Se reemplazo la terminologia publica de "votos" por "opiniones" en contexto, live dashboard, SSE y respuestas del analista.

---

## 2026-05-01 - Candidatos por ambito, guardrails de suficiencia y test de flujo

### Entorno local Python
- Se confirmo que el downgrade a Python 3.12 dejo instalado `C:\Users\capri\AppData\Local\Programs\Python\Python312\python.exe`.
- El entorno `D:\Test\.venv` se reconstruyo con Python 3.12.0.
- Se reinstalaron dependencias desde `requirements.txt`, `backend/requirements.txt` y `pytest`.
- Nota operativa: algunos comandos dentro del sandbox pueden seguir sin resolver rutas bajo `C:\Users\capri\AppData\Local\Programs`, pero fuera del sandbox el venv funciona correctamente.

### Formulario de candidatos
- Se extendio `backend/templates/candidato_form.html` para capturar ambito electoral:
  - Estado para candidatos `lista` y candidatos `unico` en elecciones regionales.
  - Municipio para candidatos `unico` en elecciones municipales.
  - Circuito para candidatos `nominal`.
  - Circunscripcion indigena para candidatos `indigena`.
- Se actualizo `backend/app.py` para cargar estados, municipios, circuitos y circunscripciones indigenas en los formularios.
- El endpoint `/candidatos/guardar` ahora persiste `id_estado`, `id_municipio`, `id_circuito` e `id_circ_indigena`, limpiando los campos que no aplican segun tipo de candidato y tipo de eleccion.

### Guardrails del analista IA
- La frase obligatoria para datos insuficientes cambio a:
  - `datos insuficientes para establecer tendencias`
- `backend/agent.py`, `/chat` y `backend/analista_ia.py` usan la misma frase exacta.
- `_contexto_analista()` ahora incluye reglas de suficiencia por tipo de eleccion:
  - Nacional: 100 opiniones, 15% de cobertura, 3 cortes.
  - Regional: 60 opiniones, 10% de cobertura, 3 cortes.
  - Municipal: 30 opiniones, 10% de cobertura, 3 cortes.
  - Asamblea: 60 opiniones, 10% de cobertura, 3 cortes.
- El contexto tambien incluye suficiencia por estado para bloquear analisis estadales prematuros.

### Test de flujo electoral
- `test_flujo.py` dejo de probar el core legado aislado y ahora simula una eleccion nacional sobre una base SQLite temporal.
- El test crea eleccion, candidatos, centros, muestra, encuestadores, SMS crudos y opiniones validas por turnos.
- Verifica que con 2 cortes y 80 opiniones el analista responda exactamente `datos insuficientes para establecer tendencias`.
- Verifica que al tercer corte y 120 opiniones el analista ya produzca una lectura de tendencia.

### Validacion
- `D:\Test\.venv\Scripts\python.exe --version` -> Python 3.12.0.
- `pytest -q` -> 1 passed.
- `pytest -q test_flujo.py` -> 1 passed.
- Import de `backend.app` -> OK.
- `GET /config` -> 200.
- `GET /candidatos/nuevo` -> 200.

---

## 2026-05-01 - Ingestion AI multi-formato para Tabla de Mesa

### Objetivo
- Extender `/tm` con un flujo AI capaz de recibir tablas CNE con formatos variables sin reemplazar el cargador diferencial existente.
- Mantener `centros` como registro historico permanente: no se eliminan centros y GPS/riesgo no se sobreescriben desde tablamesa.

### Modelo de elegibilidad por eleccion
- Se agrego `election_centers`:
  - `eleccion_id`
  - `centro_id` -> `centros.codigo_cne`
  - `eligible`
  - `source_file`
  - `campos_extra` como JSON serializado en texto para SQLite
  - timestamps
- Se agrego `tm_ingestion_logs` para auditoria:
  - archivos procesados
  - columnas detectadas
  - notas de mapeo
  - estadisticas de match
  - usuario/timestamp
- `init_db.py` aplica las tablas nuevas como migracion incremental.

### Flujo UI en `/tm`
- Se conserva el formulario legacy `/tm/cargar` para Excel/CSV estandar.
- Se agrego una tarjeta nueva de "Carga AI multi-formato":
  - eleccion destino obligatoria
  - multiples archivos `.pdf`, `.xlsx`, `.xls`, `.xlsm`, `.csv`, `.docx`, `.txt`
  - toggle de simulacion activado por defecto
  - progreso por archivo
  - preview con `MATCHED`, `NEW`, `AMBIGUOUS`, `CONFLICT`, `EXTRACTION_ERROR`
  - resolucion manual basica con selector de candidatos para AMBIGUOUS/CONFLICT
  - confirmacion bloqueada si quedan conflictos sin resolver
- Extraccion cliente:
  - SheetJS para Excel
  - mammoth.js para DOCX
  - pdfjs para PDF
  - FileReader/texto directo para CSV/TXT
- Si falla la extraccion cliente, `/api/tm/ai-extract` acepta el binario como fallback.

### AI y chunking
- Se extendio `backend/agent.py` con `ask_structured()`, que usa la configuracion ya existente de `/config`.
- No se agrego API key ni proveedor nuevo.
- El prompt instruye al AI a descubrir columnas por contenido y valores, no por estructura fija.
- La respuesta esperada es JSON puro con:
  - `detected_columns`
  - `field_notes`
  - `centros`
  - `match_hints`
- Chunking inicial:
  - 45.000 caracteres por chunk.
  - procesamiento secuencial para respetar rate limits de proveedores configurados.
  - retry exponencial hasta 3 intentos por chunk.
- Si no se extraen filas, el endpoint devuelve una muestra de texto crudo para depuracion.

### Matching
- Se agrego `/api/tm/fuzzy-match`.
- Estrategia:
  - exact match por `codigo_centro` contra `centros.codigo_cne`
  - fuzzy match por `nombre_centro + municipio + parroquia`
  - normalizacion: mayusculas, sin acentos, espacios colapsados, expansion inicial de abreviaturas CNE (`U.E.`, `E.B.`, `MP.`, `PQ.`, `EDO.`)
- Libreria inicial:
  - `difflib.SequenceMatcher`, por estar en stdlib y evitar dependencias de compilacion en Azure.
  - Candidato futuro: RapidFuzz si se necesita rendimiento/calidad superior con miles de filas.
- Thresholds iniciales:
  - `MATCHED`: fuzzy >= 0.88
  - `AMBIGUOUS`: 0.72 a 0.879
  - `NEW`: < 0.72
  - `CONFLICT`: exact match y fuzzy >= 0.84 apuntan a centros distintos.

### Confirmacion de carga
- Se agrego `/api/tm/confirm`.
- En `centros`:
  - actualiza `num_mesas` si viene en archivo
  - actualiza `num_electores` si viene en archivo
  - completa `direccion` solo si estaba vacia
  - nunca toca `lat`, `lon`, `riesgo` ni `radio_m`
- En `election_centers`:
  - inserta/actualiza elegibilidad por `eleccion_id + centro_id`
  - guarda `source_file`
  - guarda `campos_extra`
- En simulacion (`dry_run`) no escribe en BD.

### Muestra
- `selector_muestra.generar_candidatos()` ahora acepta `id_eleccion`.
- Si existen filas elegibles en `election_centers` para la eleccion, la muestra se genera solo desde ese universo.
- Si no existen filas en `election_centers`, conserva el comportamiento anterior usando `centros.activo=1`.

### Dependencias agregadas
- `pdfplumber` para fallback PDF server-side.
- `python-docx` para fallback DOCX server-side.

### Validacion
- `backend.app` importa correctamente.
- `pytest -q` -> 1 passed.
- `schema.sql` ejecuta completo sobre SQLite en memoria.
- `GET /tm` -> 200 y renderiza la UI AI.
- `POST /api/tm/fuzzy-match` con centro sintetico -> 200.

### Pendientes tecnicos
- La resolucion manual es funcional pero basica; para cargas grandes conviene una vista dedicada con busqueda por fila y candidatos.
- El AI extraction endpoint no se probo con proveedor real en esta sesion para evitar consumo/API errors; queda cubierto por contrato de prompt y fallback de errores.
- Para volumen alto, evaluar RapidFuzz y procesamiento asincrono con cola/progreso SSE.

---

## Sesion 2026-05-01 - Seguridad, Azure y carga AI TM

### Seguridad y credenciales
- Se atendio incidente de API key de OpenAI filtrada y deshabilitada por OpenAI.
- Se limpio historial Git con `git-filter-repo`, removiendo `.env` de commits historicos y force-push de historia saneada.
- Se endurecio `.gitignore` para secretos, bases locales y archivos de configuracion:
  - `.env`
  - `*.db`
  - `*.sqlite`
  - `*.sqlite3`
  - `config.ini`
  - `secrets.yaml`
  - `__pycache__/`
  - `*.pyc`
- Se corrigio `/config` para no serializar `api_key` al navegador.
- Se cambio el guardado de `/config/guardar` para que una clave vacia limpie SQLite y use variable de entorno.
- Se documento y ajusto la prioridad real de carga de API key:
  1. Azure App Settings / variable de entorno
  2. Tabla `config` en SQLite
- Se creo `SECURITY.md` como rastro de auditoria.

### Azure App Service
- Se confirmo y reforzo:
  - HTTPS Only habilitado.
  - TLS minimo 1.2.
  - `OPENAI_API_KEY` configurada en Azure App Settings.
- Se limpio la clave vieja almacenada en SQLite de produccion mediante `/config/guardar` con clave en blanco.
- `/config/test` quedo funcionando contra OpenAI con:
  - `ok=true`
  - `provider=openai`
- Se detecto que el startup de Azure no instalaba dependencias si `uvicorn` ya existia.
- Se ajusto `startup.py` para instalar `requirements.txt` al arrancar, evitando faltantes como `openai`.

---

### Fase 7 — Navegación y módulo Históricos (2026-05-02)

- **Reorden de menú** (`backend/templates/base.html`): sidebar desktop y barra móvil reordenados al flujo operativo (Inicio → Tabla Mesa → Elecciones → Muestra → Pesos → Ficha Técnica → Candidatos → Visualización → Config IA → Históricos).
- **Renombrado**: "Tabla de Mesa" → "Tabla Mesa" en desktop; "TM" → "Tabla Mesa" en móvil.
- **Etiquetas completas en móvil**: se agregaron los ítems faltantes (Pesos, Ficha Técnica) y se normalizaron "Dashboard" → "Visualización" y "IA" → "Config IA".
- **Separador visual** eliminado (era decorativo, quedaba en posición incorrecta tras el reorden).
- **Módulo Históricos** (`app.py` + 3 plantillas nuevas):
  - `/historicos` — índice con tarjeta por `eleccion_ref`: pct gobierno, pct oposición, número de centros.
  - `/historicos/{ref}` — resumen nacional + tabla por estado + top 20 centros por volumen.
  - `/historicos/comparar?a=&b=` — comparativa de dos referencias con swing por estado (pivot en Python).
  - `/historicos/{ref}/mapa` — genera choropleth con `generador_heatmap.py` y redirige a `static/viz/hist_{ref}.html`.
  - Sin cambios de esquema; consume `resultados_historicos`, `centros` y `estados` que ya existen.
- **CLAUDE.md** agregado al repo con contexto operativo completo para sesiones futuras de Claude Code.

### Auditoria de dependencias
- `pip-audit -r requirements.txt`: sin vulnerabilidades conocidas.
- `pip-audit -r backend/requirements.txt` encontro vulnerabilidades en `starlette==0.46.2`:
  - `CVE-2025-54121`
  - `CVE-2025-62727`
- Se actualizo:
  - `fastapi==0.136.1`
  - `starlette==0.49.1`
- Re-auditoria posterior: sin vulnerabilidades conocidas.

### GitHub hardening pendiente de habilitacion manual
- Revisado estado del repo:
  - Dependabot alerts: desactivado.
  - Dependabot security updates: desactivado.
  - Secret scanning: desactivado a nivel repo.
  - CodeQL/code scanning: sin analisis.
  - Branch protection en `main`: no configurado.
- Pendiente manual en GitHub UI:
  - habilitar Secret scanning + Push protection
  - habilitar Dependabot alerts
  - habilitar Dependabot security updates
  - configurar CodeQL en push a `main`
  - proteger `main` con minimo 1 review antes de merge

### Carga AI de Tabla Mesa
- Prueba real con PDF pequeno confirmo que `/api/tm/ai-extract` llegaba al backend.
- Error observado inicialmente:
  - HTTP 422
  - `chunk_1_error: Expecting ',' delimiter`
- Diagnostico: la IA respondia JSON invalido o truncado para el chunk.
- Fix aplicado:
  - OpenAI usa `response_format={"type":"json_object"}` en `ask_structured()`.
  - chunking bajo de 45.000 a 15.000 caracteres.
  - `max_tokens` minimo para extraccion AI subio de 4.000 a 12.000.
- Se detecto otro problema critico: la extraccion AI bloqueaba el unico worker/event loop y podia dejar todo el sitio sin responder.
- Fix aplicado:
  - lectura server-side pesada de archivos via `asyncio.to_thread`
  - llamada bloqueante a OpenAI via `asyncio.to_thread`
  - retries con `await asyncio.sleep()` en lugar de `time.sleep()`
- Despues del fix anti-bloqueo, `/tm` volvio a responder en Azure.

### Accesibilidad UI
- Se corrigieron 5 labels sin asociacion en `backend/templates/tm.html`:
  - Archivo TM
  - Formato
  - Hoja Excel
  - Eleccion destino
  - Archivos TM
- Se agregaron pares `for`/`id` para eliminar warning del navegador.

### Documentacion
- Se agrego seccion `AI Development Collaboration` en `README.md`.
- Se actualizo `SECURITY.md` con:
  - resolucion de CVEs
  - migracion de `OPENAI_API_KEY` a Azure App Settings
  - confirmacion de `/config/test`

### Estado para retomar
- Sitio desplegado y respondiendo en Azure.
- Reintentar carga AI con un PDF pequeno antes de volver a los 24 PDFs.
- En DevTools > Network, vigilar `/api/tm/ai-extract`:
  - `200`: extraccion AI OK
  - `422`: copiar `chunk_1_error`
  - `499/502/504`: timeout/corte de solicitud
- Si el procesamiento de 24 PDFs sigue siendo pesado, siguiente paso tecnico recomendado:
  - cola/background job por archivo
  - tabla de progreso por lote
  - polling o SSE para progreso `PDF n/24`
  - confirmacion de escritura separada por lote

## 2026-05-01 - Correcciones criticas TM AI y simulador

### Confirmacion AI de Tabla Mesa
- `/api/tm/confirm` ahora ejecuta la confirmacion en una transaccion con `BEGIN IMMEDIATE`.
- Antes de procesar el archivo confirmado:
  - desactiva todos los centros con `UPDATE centros SET activo = 0`
  - limpia elegibilidad previa para la eleccion activa en `election_centers`
- Los centros extraidos por IA se reactivan con `activo = 1`.
- `_upsert_ai_center` mantiene `COALESCE` para `num_mesas` y `num_electores`, y no sobrescribe `lat`, `lon` ni `riesgo`.

### Robustez AI para PDFs pesados
- Se dejo explicito el chunking maximo en 15.000 caracteres.
- La lectura pesada de archivos sigue derivada a `asyncio.to_thread`.
- Los reintentos de IA subieron a 5 intentos con backoff, jitter y soporte para `retry-after`.

### Simulador showcase
- `calcular_resultado_ponderado()` ahora devuelve resultados anidados en elecciones regionales y municipales:
  - regional: `{id_estado: {id_candidato: porcentaje}}`
  - municipal: `{id_municipio: {id_candidato: porcentaje}}`
- El resumen final de consola imprime la tendencia desglosada por estado o municipio sin pisar resultados previos.

### Validacion
- `python -m py_compile backend\app.py backend\simulador_showcase.py`: OK.
- `pytest -q`: 1 passed.

---

## 2026-05-07 - Sincronizacion local, pytest dev y documentacion multi-equipo

### Sincronizacion
- Se actualizo la Lenovo desde `origin/main` con fast-forward hasta `b232f13`.
- El workspace local quedo sincronizado en `main` antes de aplicar cambios nuevos.

### Rutas locales por computadora
- Se documento en `PROJECT_CONTEXT.md` la convencion de rutas para evitar confusion entre equipos:
  - Pavilion: proyectos en `D:\Test`.
  - Lenovo: proyectos en `C:\Proyects`.
- Se ajusto tambien la referencia de venv:
  - Pavilion: `D:\Test\.venv`.
  - Lenovo: `C:\Proyects\exit-poll\venv`.

### Harness de tests backend
- Se agrego `requirements-dev.txt` para dependencias de desarrollo:
  - reutiliza `backend/requirements.txt`
  - agrega `pytest>=8.0.0`
- Se instalo `pytest` en el venv local de Lenovo.
- Se ejecuto `test_flujo.py` con SQLite temporal:
  - `venv\Scripts\python.exe -m pytest -q test_flujo.py --basetemp .pytest_tmp3 -p no:cacheprovider`
  - Resultado: `1 passed`.
- Se agregaron a `.gitignore` los artefactos temporales de pytest:
  - `.pytest_cache/`
  - `.pytest_tmp*/`
  - `pytest-cache-files-*/`

### Estado y bugs
- Se mantuvo pendiente el parser SMS + validacion GPS del gateway Android.
- Se marco como completado el harness de tests backend.
- Se separo la cobertura pendiente como trabajo futuro: rutas criticas FastAPI, ponderacion por tipo de eleccion y ampliacion de pruebas.
- Se movio a resuelto el bug de agregacion regional/municipal porque `calcular_resultado_ponderado()` ya retorna resultados anidados por ambito y no pisa estados/municipios previos.

---

## 2026-05-07 - Hardening modulo AI de reportes v2.3

### Diagnostico previo
- Se revisaron los archivos reales del modulo AI antes de modificar codigo:
  - `backend/agent.py`
  - `backend/analista_ia.py`
  - integraciones en `backend/app.py`
  - `test_flujo.py`
- Se documento el estado inicial en `AI_MODULE_REVIEW.md`.
- Hallazgo principal: el sistema tiene dos capas AI distintas:
  - `agent.py`: LLM generativo configurable para chat y TM AI.
  - `analista_ia.py`: analista deterministico sin tokens para panel live.
- El prompt externo asumia que no habia abstraccion multi-proveedor, pero esta ya existia. Se decidio refinarla sin reconstruirla.

### Prompt y validacion
- Se separo el system prompt v2.3 en `backend/ai_prompts.py`.
- El prompt exige 5 secciones fijas:
  1. ESTADO DE LA CONTIENDA
  2. COBERTURA Y CALIDAD MUESTRAL
  3. ANALISIS DEMOGRAFICO
  4. MOTIVADORES DE VOTO
  5. ADVERTENCIA METODOLOGICA
- Se agrego `backend/ai_validation.py` con validador secuencial:
  - muestra global
  - coherencia interna
  - subgrupos demograficos
- Si la validacion falla, se aborta antes de llamar al LLM.

### Schema real vs schema v2.3
- El schema v2.3 esperado no coincide completo con el contexto actual del backend.
- Se agrego adaptador sin tocar BD ni pipeline:
  - `total_opiniones` / `total_votos` -> `tamano_muestra_actual`
  - `cobertura_pct` -> `porcentaje_cobertura_geografica`
  - `suficiencia.minimo_opiniones` -> `umbral_requerido`
  - cortes registrados -> `porcentaje_cobertura_horaria`
- Faltantes documentados como pendientes:
  - `cortes_demograficos`
  - `motivadores_voto`
  - `ponderacion_activa`
  - `design_effect`
  - `tasa_no_respuesta`

### Abstraccion LLM y trazabilidad
- `agent.py` conserva funciones existentes:
  - `ask_agent`
  - `ask_structured`
  - `ask_structured_async`
- Se agrego interfaz minima:
  - `llm_call(system_prompt, user_message, provider, api_key, model, temperature) -> str`
- Se agrego `llm_call_with_metadata()` para trazabilidad:
  - timestamp
  - proveedor
  - modelo
  - version prompt
  - version schema
  - tokens usados si proveedor los expone
  - latencia
- El streaming de `ask_agent()` agrega metadata al final del reporte.
- `ask_agent()` valida el contexto antes de resolver API key o tocar proveedor remoto; asi un contexto insuficiente devuelve el mensaje estadistico aunque falte configuracion LLM.

### Proveedores
- Soporte conservado y alineado:
  - OpenAI: `gpt-4o`, `gpt-4-turbo`, `gpt-4o-mini`
  - Anthropic: `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5-20251001`
  - Google/Gemini: `gemini-1.5-pro`, `gemini-2.5-flash`
  - Groq se mantiene como proveedor ya existente OpenAI-compatible.
- Se agrego alias interno `google -> gemini` para que la interfaz `llm_call()` acepte el nombre del spec sin cambiar la tabla `config`.
- Temperatura recomendada para reportes: `0`, configurable desde `/config`.

### Validacion
- `venv\Scripts\python.exe -m compileall -q backend test_flujo.py test_ai_validation.py`: OK.
- `venv\Scripts\python.exe -m pytest -q test_flujo.py test_ai_validation.py --basetemp .pytest_ai_tmp3 -p no:cacheprovider`: 7 passed.

---

## 2026-05-08 - Live dashboard alineado con visualizacion

### Problema
- `/visualizacion/generar` construia el dashboard desde `resultados_historicos`.
- `/live` solo miraba `votos`; cuando no habia opiniones SMS cargadas, mostraba estado vacio aunque el dashboard estatico tuviera data.
- El panel del analista IA quedaba sobre una vista que no representaba lo que el usuario veia en el dashboard.

### Cambio
- Se agrego fallback comun en `backend/app.py`: primero se usan votos reales; si `votos` esta vacia, `/live`, `/stream/dashboard` y el contexto del analista usan la misma referencia que `/visualizacion`.
- `/stream/dashboard` ahora reporta `fuente_datos`:
  - `live` cuando hay opiniones reales.
  - `dashboard_referencia` mientras se muestra la referencia historica/simulada.
- `backend/generador_dashboard.py` actualiza por SSE la etiqueta de fuente sin recargar la pagina.
- El analista IA recibe `nota_fuente` cuando opera sobre referencia, para no confundirla con opiniones SMS reales.

### Validacion
- `D:\Test\.venv\Scripts\python.exe -m py_compile backend\app.py backend\generador_dashboard.py test_flujo.py`: OK.
- `D:\Test\.venv\Scripts\pytest.exe -q`: 15 passed.
- Verificacion local con la BD real:
  - `/live` responde 200.
  - Incluye `AI Electoral Analyst`.
  - Incluye `Datos de referencia del dashboard`.
  - Ya no muestra `Corre: python backend/simulador_showcase.py --reset` cuando hay referencia disponible.

---

## 2026-05-18 - Historicos unificados en Azure

### Problema
- `/historicos/debug-json` confirmaba que Azure tenia `resultados_historicos` con `2024-presidencial`, pero `/historicos` podia mostrar el estado vacio.
- La pagina y el endpoint de diagnostico construian sus datos con logica separada, lo que hacia mas dificil comprobar si el problema era cache, consulta o render.

### Cambio
- Se agrego `_historicos_unificados()` en `backend/app.py` como fuente unica para `/historicos` y `/historicos/debug-json`.
- `/historicos` ahora recibe la misma lista `elections` que expone el diagnostico; si `resultados_historicos` tiene filas sin estudio, debe renderizar tarjeta "Solo resultados".
- Se agrego `Cache-Control: no-store` a `/historicos` y `/historicos/debug-json` para reducir falsos positivos por cache del navegador o proxy.
- La plantilla `backend/templates/historicos.html` incluye un comentario HTML con conteos (`elections`, `rh`, `est`) para diagnostico rapido en Azure sin exponer UI adicional.
- Se reemplazo la importacion pesada de Excel en Azure por una semilla fija versionada:
  - `backend/data/historico_estudios_seed.json`
  - `backend/seed_historico_estudios.py`
- `backend/startup.sh` y el evento `startup` de FastAPI aplican esa semilla idempotente para 2006, 2012 y 2013.
- `/historicos` y `/historicos/debug-json` vuelven a ser solo lectura contra SQLite; no ejecutan importaciones ni procesos pesados durante la carga de pagina.
- Se quitaron las opciones visibles de crear/editar estudios historicos y se bloquearon las rutas de edicion con 404 porque esos datos son historicos fijos.

### Validacion
- `D:\Test\.venv\Scripts\python.exe -m py_compile backend\app.py`: OK.
- `TestClient` local:
  - `/historicos/debug-json` responde 200 con `deploy_ts=2026-05-18T09e0890-unified`.
  - `/historicos` responde 200.
  - El HTML contiene "Solo resultados".
  - El HTML no contiene el estado vacio "No hay datos historicos cargados".
- Semilla fija:
  - `D:\Test\.venv\Scripts\python.exe backend\seed_historico_estudios.py`: OK, 73 estudios, 75 oficiales, 43 turnos.
  - Prueba contra BD temporal creada desde `backend/schema.sql`: OK, refs nacionales 2006, 2012 y 2013 cargadas.
- `TestClient` despues de la semilla fija:
  - `/historicos/debug-json` responde con `deploy_ts=2026-05-18Tfixed-seed-readonly`.
  - `elections` lista `2013-presidencial`, `2012-presidencial`, `2006-presidencial` y `2024-presidencial`.
  - `/historicos/estudios/nuevo`: 404.
  - `/historicos/estudios/2006-presidencial/editar`: 404.
  - El HTML no contiene `Nuevo estudio` ni `bi-pencil`.

---

## 2026-05-18 - Estudio historico Asamblea Nacional 2010

### Contexto
- Se agrego el estudio `backend/data/2010/aplicacion03.xlsm`.
- La eleccion parlamentaria 2010 no tiene tabulado oficial local comparable dentro del repo.
- Es una eleccion legislativa mixta: diputados nominales, diputados lista y representacion indigena.

### Criterio de dashboard
- Se importa como `2010-asamblea`, no como presidencial.
- La metrica principal es escanos proyectados, no voto nacional presidencial.
- No se genera tendencia: el archivo se trata como resultado final del estudio.
- La referencia oficial nacional se toma del agregado publicado para la eleccion:
  - 98 escanos PSUV/aliados.
  - 65 escanos MUD/aliados.
  - 2 escanos PPT/aliados.
- No se inventan tabulados oficiales por estado; el detalle por estado muestra la proyeccion del estudio y deja la referencia estatal vacia cuando no existe.

### Cambio
- Se agrego `backend/import_2010.py` para leer:
  - `R Nominal`
  - `R Lista`
  - `R Indigena`
  - `ENTRADA` para centros unicos.
- Se actualizo `backend/data/historico_estudios_seed.json` para incluir 2010 como dato fijo.
- `backend/templates/historico_estudio_detalle.html` reconoce estudios legislativos:
  - KPI de escanos estudio vs referencia.
  - lectura legislativa.
  - grafico de puntos para distribucion de escanos del estudio y del resultado final.
  - comparacion por estado con escanos proyectados del estudio vs voto lista oficial por entidad federal publicado por Wikipedia/CNE.
  - aviso de sin tendencia.

### Validacion
- `D:\Test\.venv\Scripts\python.exe import_2010.py`: OK.
  - Estudio: 114 gobierno, 50 oposicion, 1 otros.
  - Referencia: 98 gobierno, 65 oposicion, 2 otros.
- `D:\Test\.venv\Scripts\python.exe backend\seed_historico_estudios.py`: OK, 98 estudios, 100 oficiales, 43 turnos.
- `TestClient`:
  - `/historicos/debug-json` lista `2010-asamblea`.
  - `/historicos/estudios/2010-asamblea` responde 200.
  - El HTML contiene `Asamblea Nacional`, `Sin tendencia`, `114`, `98`, `Distribucion de escanos` y `Ofic. Gov lista%`.

---

## 2026-05-18 - Resultado oficial Presidencial 2018

### Contexto
- No hubo estudio historico cargado para la eleccion presidencial 2018.
- Se agrego como resultado oficial nacional fijo, con fuente Wikipedia/CNE, para que aparezca en `/historicos` como tarjeta `Solo resultados`.

### Cambio
- Se agrego `2018-presidencial` a `backend/data/historico_estudios_seed.json` dentro de `historico_oficial`.
- `_historicos_unificados()` ahora diferencia estudios con comparacion (`con_estudio`) de registros oficiales sin estudio (`oficial`).
- Las tarjetas sin estudio usan titulo legible (`Presidencial 2018`, `Presidencial 2024`) en vez del `eleccion_ref` crudo cuando hay formato inferible.
- Se ordena la lista combinada por fecha o anio descendente, dejando 2024 antes de 2018.

### Validacion
- `D:\Test\.venv\Scripts\python.exe -m py_compile backend\app.py backend\seed_historico_estudios.py`: OK.
- `D:\Test\.venv\Scripts\python.exe backend\seed_historico_estudios.py`: OK, 98 estudios, 101 oficiales, 43 turnos.
- `TestClient`:
  - `/historicos`, `/historicos/debug-json` y `/historicos/estudios/2018-presidencial` responden 200.
  - `debug-json` lista: 2024, 2018, 2013, 2012, 2010, 2006.
  - El HTML contiene `Presidencial 2024` y `Presidencial 2018`.
