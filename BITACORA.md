# BITACORA.md — Exit Poll Venezuela

> Historial narrativo de desarrollo, sesión por sesión. Más antiguo arriba.
> Encabezados de sesión: `## AAAA-MM-DD — Tema`.

---

## Fases 1–5 — Registro inicial de cambios

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

## 2026-04-30 — Deploy Azure (resuelto)

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

## 2026-04-30 — SSE Live Dashboard y agente IA multi-proveedor

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

## 2026-05-01 — Candidatos por ambito, guardrails de suficiencia y test de flujo

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

## 2026-05-01 — Ingestion AI multi-formato para Tabla de Mesa

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

## 2026-05-01 — Seguridad, Azure y carga AI TM

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

## 2026-05-01 — Correcciones criticas TM AI y simulador

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

## 2026-05-07 — Sincronizacion local, pytest dev y documentacion multi-equipo

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

## 2026-05-07 — Hardening modulo AI de reportes v2.3

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

## 2026-05-08 — Live dashboard alineado con visualizacion

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

## 2026-05-18 — Historicos unificados en Azure

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

## 2026-05-18 — Estudio historico Asamblea Nacional 2010

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

## 2026-05-18 — Resultado oficial Presidencial 2018

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

---

## 2026-05-19 — Coleccion historica Gobernadores 2012

### Contexto
- Se agrego el estudio historico `2012-gobernadores` al modulo de historicos.
- A diferencia de 2008, el archivo fuente es unico:
  - `backend/data/2012/gobernadores/CORE4.xlsx`
- El workbook contiene una hoja maestra `Entrada`, hojas auxiliares (`Hector`, `Alejandro`) y 23 hojas por estado/codigo (`AM`, `AN`, `AP`, etc.).
- El layout 2012 no coincide con 2008: las hojas estatales estan agregadas por municipio/segmento y turnos 1..18, no por `Entidad / Centro / Turno / Cand...`.

### Cambio
- Se agrego `backend/import_2012_gobernadores.py`.
- El importador crea 23 estudios paralelos por estado, mas una fila `NACIONAL` de metadato de coleccion.
- Se cargan:
  - `historico_estudios` con `eleccion_ref='2012-gobernadores'`.
  - `historico_oficial` con resultados oficiales Wikipedia/CNE 2012.
  - `historico_estudios_turnos` con `ambito=slug_estado` para cada serie acumulada por turno.
- Se agregaron rutas especiales antes de la ruta generica `/historicos/estudios/{ref}`:
  - `/historicos/estudios/2012-gobernadores`
  - `/historicos/estudios/2012-gobernadores/{estado_slug}`
- Se agregaron templates:
  - `backend/templates/gobernadores_2012.html`
  - `backend/templates/gobernador_2012_detalle.html`
- `_historicos_unificados()` ahora marca `2012-gobernadores` como coleccion multi-estudio con badge `23 exit polls`.
- Se regenero `backend/data/historico_estudios_seed.json`; no se versiona `backend/exitpoll.db`.

### Criterio metodologico
- Cada estado es un estudio independiente y paralelo.
- La fila `NACIONAL` es solo metadato de coleccion; no representa un promedio nacional.
- En 2012 la categoria de oposicion se toma como MUD/plataforma opositora.
- Las hojas 2012 no exponen centros CNE crudos en el mismo layout de 2008; para las vistas se usa el conteo de municipios/segmentos reportados como `num_centros` operativo.

### Validacion
- `D:\Test\.venv\Scripts\python.exe import_2012_gobernadores.py --reset`: OK.
  - 23 estados parseados.
  - 24 filas en `historico_estudios` incluyendo `NACIONAL`.
  - 23 filas en `historico_oficial`.
  - 407 filas en `historico_estudios_turnos`.
- `D:\Test\.venv\Scripts\python.exe -c "from app import app; print('OK')"`: OK.
- `D:\Test\.venv\Scripts\pytest.exe -q`: 15 passed.
- `TestClient`:
  - `/historicos`: 200.
  - `/historicos/estudios/2012-gobernadores`: 200.
  - `/historicos/estudios/2012-gobernadores/miranda`: 200.
- Uvicorn local:
  - `http://127.0.0.1:8000/historicos/estudios/2012-gobernadores/miranda`: 200.

---

## 2026-05-20 — Coleccion historica Municipales 2013

### Contexto
- Se agrego la eleccion municipal 2013 al modulo `/historicos`.
- Los insumos locales estan en `backend/data/2013/municipales/`:
  - `auditoria4.xlsx`
  - `PESO CENTROS DIC 2013.xlsx`
- La pagina CNE original esta caida; el importador queda preparado para leer resultados oficiales desde archive.org:
  - `https://web.archive.org/web/20190812031057/http://www.cne.gob.ve/resultado_municipal_2013/r/1/reg_000000.html`

### Cambio
- Se agrego `backend/import_2013_municipales.py`.
- El importador crea una coleccion `2013-municipales` con 52 estudios municipales y fila `NACIONAL` de metadatos.
- Se cargan:
  - `historico_estudios` con `eleccion_ref='2013-municipales'`.
  - `historico_estudios_turnos` con `ambito=slug_municipio`.
  - `historico_oficial` cuando archive.org/CNE responde y se logra leer el municipio.
- Se agregaron rutas especiales:
  - `/historicos/estudios/2013-municipales`
  - `/historicos/estudios/2013-municipales/{municipio_slug}`
- Se agregaron templates:
  - `backend/templates/municipales_2013.html`
  - `backend/templates/municipal_2013_detalle.html`
- `_historicos_unificados()` marca `2013-municipales` como coleccion multi-estudio con badge `52 exit polls`.
- Se regenero `backend/data/historico_estudios_seed.json`; no se versiona `backend/exitpoll.db`.

### Semaforo de informacion confiable
- `auditoria4.xlsx` usa las hojas `Pantalla1` a `Pantalla4` como tablero operativo por centro y turno.
- Cada fila consolida el total recibido por centro en un corte. El semaforo separa:
  - centros que transmiten informacion util/correcta;
  - centros con informacion errada o atipica, por totales desproporcionados o inconsistentes;
  - centros sin transmision, cuando no aparece informacion posterior al corte base.
- Para la publicacion historica no se muestran datos crudos por centro; se documenta el resumen de auditoria por municipio:
  - centros esperados;
  - centros que transmitieron;
  - centros sin transmision;
  - cortes con total atipico.
- La ponderacion publicada usa `PESO CENTROS DIC 2013.xlsx` y agrupa candidato 1 como gobierno, candidato 2 como oposicion y el resto como otros, igual que el core historico.

### Validacion
- `C:\Users\capri\AppData\Local\Python\pythoncore-3.14-64\python.exe backend\import_2013_municipales.py --no-official --write-seed`: OK.
  - 53 filas en `historico_estudios`.
  - 279 filas en `historico_estudios_turnos`.
  - `historico_oficial` quedo en 0 en esta corrida porque archive.org rechazo conexiones de forma intermitente; el scraper queda implementado para completar esa capa cuando responda estable.
- `C:\Users\capri\AppData\Local\Python\pythoncore-3.14-64\python.exe backend\seed_historico_estudios.py`: OK, 201 estudios, 149 oficiales, 1134 turnos.
- `C:\Users\capri\AppData\Local\Python\pythoncore-3.14-64\python.exe -m py_compile backend\app.py backend\import_2013_municipales.py backend\seed_historico_estudios.py`: OK.
- `TestClient`:
  - `/historicos`: 200.
  - `/historicos/debug-json`: 200.
  - `/historicos/estudios/2013-municipales`: 200.
  - `/historicos/estudios/2013-municipales/monagas-maturin`: 200.
- `C:\Users\capri\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest -q`: 15 passed.

---

## 2026-05-20 — Reorganizacion de data historica 2012/2013

### Contexto
- En 2012 y 2013 hay mas de un tipo de eleccion historica cargada.
- Para evitar ambiguedad, los insumos Excel quedaron separados por tipo:
  - `backend/data/2012/presidenciales/`
  - `backend/data/2012/gobernadores/`
  - `backend/data/2013/presidenciales/`
  - `backend/data/2013/municipales/`

### Cambio
- `backend/import_2012_2013.py` ahora lee los archivos presidenciales desde las subcarpetas `presidenciales/`.
- El mismo importador se actualizo para insertar turnos presidenciales con `ambito='NACIONAL'`, compatible con el esquema actual de `historico_estudios_turnos`.
- `backend/import_2012_gobernadores.py` ya apuntaba a `backend/data/2012/gobernadores/`.
- `backend/import_2013_municipales.py` ya apuntaba a `backend/data/2013/municipales/`.
- Los archivos que antes estaban en la raiz del anio deben tratarse como movidos, no como eliminados:
  - `backend/data/2012/Core (2).xlsx` -> `backend/data/2012/presidenciales/Core (2).xlsx`
  - `backend/data/2012/resultados oficiales presidenciales 2012.xlsx` -> `backend/data/2012/presidenciales/resultados oficiales presidenciales 2012.xlsx`
  - `backend/data/2013/CoreMA2.xlsx` -> `backend/data/2013/presidenciales/CoreMA2.xlsx`
  - `backend/data/2013/resultados oficiales elecciones presidenciales 2013.xlsx` -> `backend/data/2013/presidenciales/resultados oficiales elecciones presidenciales 2013.xlsx`

### Validacion
- `D:\Test\.venv\Scripts\python.exe -m py_compile backend\import_2012_2013.py backend\import_2012_gobernadores.py backend\import_2013_municipales.py`: OK.
- `D:\Test\.venv\Scripts\python.exe import_2012_2013.py` desde `backend/`: OK.
  - `2012-presidencial`: 25 filas de estudio, 25 oficiales, 13 turnos.
  - `2013-presidencial`: 25 filas de estudio, 25 oficiales, 18 turnos.

---

## 2026-05-20 — Scraper archive.org municipal 2013

### Contexto
- Se corrio el scraper oficial de `2013-municipales` contra archive.org con pausas entre solicitudes para no saturar el snapshot.
- El primer mapeo de codigos CNE estaba desplazado en varios estados; se corrigio usando los indices estadales archivados del CNE.
- El parser ahora toma solo el primer bloque `ALCALDESA O ALCALDE` de cada pagina, evitando sumar concejales u otros cargos.

### Resultado
- `backend/data/historico_estudios_seed.json` queda con:
  - 53 filas de estudio para `2013-municipales`.
  - 279 filas de turnos.
  - 52 filas oficiales: 51 municipios mas `NACIONAL`.
- Se cargaron fichas tecnicas manuales provistas desde CNE/archive para municipios donde archive.org no devolvia pagina usable:
  - Barinas, Barinas.
  - San Fernando, Apure.
  - Maturin, Monagas.
  - Paez, Portuguesa.
  - Sucre, Sucre.
- San Fernando, Apure:
  - Ofelia Padron: 65,27%.
  - Yadala Abouhadour: 32,19%.
  - Otros: 2,54%.
  - Votos validos: 52.279.
- Barinas, Maturin, Paez y Sucre-Sucre se cargaron con sus porcentajes oficiales manuales, manteniendo la convencion local de candidato gobierno/oposicion.
- Falta oficial por pagina no disponible o snapshot roto en archive.org:
  - `guarico-juan-german-roscio`
- No se cargo el bloque de `Municipio Roscio del estado Bolivar` porque no corresponde al estudio pendiente `Juan German Roscio, Guarico`.

### Validacion
- `D:\Test\.venv\Scripts\python.exe backend\import_2013_municipales.py --write-seed --delay-seconds 4 --retries 3`: OK, con faltantes documentados.
- `D:\Test\.venv\Scripts\python.exe backend\seed_historico_estudios.py`: OK.
  - 201 estudios.
  - 201 oficiales.
  - 1134 turnos.

---

## 2026-05-20 — Graficos acumulativos municipales 2013

### Cambio
- `backend/import_2013_municipales.py` ahora calcula cada corte con las opiniones acumuladas hasta ese turno (`turno <= corte`).
- El resultado final del estudio municipal tambien sale del acumulado completo, no solo de las filas del ultimo turno.
- Se regenero `backend/data/historico_estudios_seed.json` preservando los oficiales ya obtenidos por archive.org y las fichas tecnicas manuales.

### Validacion
- `D:\Test\.venv\Scripts\python.exe backend\seed_historico_estudios.py`: OK.
  - 201 estudios.
  - 201 oficiales.
  - 1134 turnos.
- Rutas verificadas:
  - `/historicos/estudios/2013-municipales`
  - `/historicos/estudios/2013-municipales/barinas-barinas`
  - `/historicos/estudios/2013-municipales/zulia-maracaibo`
- `D:\Test\.venv\Scripts\pytest.exe -q`: 15 passed.

---

## 2026-06-10 — Limpieza del repo, barrido de bugs y normalización de documentación

### Contexto
- Sesión con Claude Code: revisión completa del proyecto a pedido del usuario — ordenar carpetas, limpiar git, barrer la app en busca de bugs y normalizar la documentación.
- El repo paraguas `D:\Test` también se ordenó: cada proyecto con repo git propio quedó ignorado en el `.gitignore` del padre; `SOMBRA.FP5` y carpetas huérfanas movidas a `D:\Test\legacy\`.

### Limpieza del repositorio
- `legacy/scripts_raiz/`: los 9 scripts pre-backend de las fases 1–6 (pipeline CSV 2024, crawler CNE 2013, dashboards Streamlit, graficadores) con sus datos.
- `legacy/ai_configs/`: instrucciones por herramienta (aider, chatgpt, copilot, cursor, gemini, grok, perplexity, windsurf); quedan activos `AGENTS.md`, `CLAUDE.md` y `.github/copilot-instructions.md`.
- `legacy/outputs/`: HTML de prueba, `graficos_test/`, logs `server_*.txt` y dos BD vacías huérfanas (`backend/exit_poll.db` y `exitpoll.db` de la raíz, ambas 0 bytes).
- `.gitignore`: agrega `server_*.txt`, elimina la entrada obsoleta `/exit poll/`.

### Bugs encontrados y resueltos
1. **Dashboard de referencia mezclaba elecciones** (crítico): las funciones de ventaja y el total de referencia sumaban todas las `eleccion_ref` de `resultados_historicos`. Con 2006 + 2024 cargadas, `/live` mostraba ventaja nacional −3.7 pp cuando la ref 2024 sola da −36.8 pp. Nuevo helper `_eleccion_ref_referencia()` y filtro en las 5 funciones; los LEFT JOIN de muestra además duplicaban filas.
2. **Carga TM parcial desactivaba todo el país** (crítico latente): `cargador_tm` marcaba `activo=0` a todo centro ausente del CSV sin importar el estado. Ahora la desactivación se acota a los estados del CSV, como el path IA.
3. **Pesos excluían centros sin municipio**: el INNER JOIN dejaba fuera del cálculo a los centros creados por ingesta IA con `id_municipio NULL`. LEFT JOIN con aviso; sin geografía el centro agrupa como unidad propia.
4. **Geografía duplicada entre ingestas**: la ingesta IA no encontraba los municipios con nombre crudo CNE ("MP. ZAMORA") y creaba duplicados `AI##`. Nuevo `_geo_match_name()` canoniza nombres entre fuentes. La BD de producción no tenía duplicados.
5. **Menores**: `diff_nac` de 0.0 se convertía en 999 en `selector_muestra`; refs `'2024-presidencial'` hardcodeadas en `/muestra`; `test_flujo` dependía del directorio de ejecución.
- Falsa alarma descartada: el streaming de `/chat` con generador síncrono no bloquea el event loop — Starlette lo itera en threadpool.

### Tests
- Suite pasó de 15 a 20 tests: regresión de mezcla de refs (`test_flujo`), TM parcial y dry-run (`test_cargador_tm`), pesos sin municipio y matching de geografía (`test_geo_pesos`).
- `pytest -q`: 20 passed.

### Documentación
- CHANGELOG reordenado a cronología inversa estricta con `[Unreleased]` arriba; backfill de las sesiones 2026-05-18 a 2026-05-20 (AN 2010, oficial 2018, Gobernadores 2012, Municipales 2013) que solo estaban en esta bitácora.
- Encabezados de sesión de esta bitácora unificados al formato `## AAAA-MM-DD — Tema`.
- README en inglés (portfolio) + `README.es.md` en español, enlazados; SECURITY conserva inglés con estructura estándar; AI_MODULE_REVIEW con acentos.
- ESTADO actualizado: bugs de hoy en resueltos, BUG-002 nuevo (error muestral de /ficha usa electores en vez de entrevistas — pendiente decisión de n).

---

## 2026-08-13 - Dataset historico Referendum Revocatorio 2004

### Contexto
- Se incorporo una recuperacion agregada por centro desde Esdata/Wayback para alimentar `resultados_historicos` con la referencia `2004-revocatorio`.
- La recuperacion evita datos personales: no se descargan ni se versionan cedulas, nombres de electores ni registros elector-persona.

### Cambio
- Se agrego `backend/resultados_rr2004.csv` con 6.265 centros agregados.
- Se agrego `backend/seed_resultados_historicos.py` para sembrar datasets historicos versionados:
  - `2024-presidencial` desde `backend/resultados_cne2024.csv`.
  - `2004-revocatorio` desde `backend/resultados_rr2004.csv`.
- `backend/app.py`, `backend/startup.py`, `backend/startup.sh` e `backend/init_showcase.py` cargan el seed de resultados historicos por centro de forma idempotente.
- Se agregaron importadores reproducibles:
  - `backend/import_2004_esdata.ps1`
  - `backend/import_2004_esdata.py`
- En `resultados_rr2004.csv`, `codigo_centro` y `codigo_cne_nuevo` son el codigo CNE nuevo; `codigo_viejo` y `codigo_cne_viejo` preservan el identificador viejo de Esdata.

### Criterio metodologico
- En el RR 2004, `NO` ratifica al gobierno y se almacena como `votos_gobierno`.
- `SI` revoca al presidente y se almacena como `votos_oposicion`.
- La cobertura recuperada no es el 100% del universo oficial de centros habilitados; debe tratarse como una recuperacion historica parcial para analisis de tendencias por centro. Es una base de alta cobertura por volumen:
  - 6.265 centros.
  - 8.956.463 votos validos.
  - 12.980.497 electores REP 2004.

### Validacion
- `D:\Test\.venv\Scripts\python.exe backend\seed_resultados_historicos.py`: OK.
  - `2024-presidencial`: 11.925 centros.
  - `2004-revocatorio`: 6.265 centros.
- Rutas verificadas:
  - `/historicos`: 200.
  - `/historicos/2004-revocatorio`: 200.
  - `/historicos/debug-json`: 200.

---

## 2026-08-13 - Decision de diseno para laboratorio de muestra

### Contexto
- Se reviso el proximo rediseno de la pestana `Muestra` para seleccionar centros de una nueva eleccion usando TM/REP disponible, registro permanente e historicos heterogeneos.
- La premisa metodologica queda documentada: el selector automatico actual debe pasar a ser un sugeridor editable, no el mecanismo unico de decision.

### Decision
- Se agrego `ADR-011` en `DECISIONES.md`.
- La muestra se redisenara como laboratorio asistido:
  - lista maestra de centros activos, historicos, nuevos e inciertos;
  - ficha por centro con linaje de datos, tendencia y advertencias;
  - separacion estricta entre `score_utilidad` y `confianza_dato`;
  - comparacion viva de muestra vs universo;
  - backcast y metricas Mosteller/DEFF cuando existan datos suficientes.
- Los historicos agregados por territorio se usaran como contexto o prior, no como sustituto directo del comportamiento por centro.

### Alcance inicial
- Implementacion futura en fases: primero contratos de datos aditivos y pantalla exploratoria; despues sugerencias por estrato; optimizador automatico solo cuando la herramienta manual este validada.

---

## 2026-08-13 - Implementacion v1 laboratorio de muestra

### Cambio
- Se implemento `backend/muestra_lab.py` como capa de calculo para catalogo maestro, score, confianza, clasificacion y resumen muestra-vs-universo.
- `/muestra` ahora muestra:
  - KPIs del universo conocido y muestra actual;
  - filtros por busqueda, estado, municipio, parroquia, estatus y clasificacion;
  - tabla de centros con estatus, tipo, historicos disponibles, desvio, estabilidad, confianza y score;
  - ordenamiento client-side por columnas manteniendo la ficha desplegable asociada al centro;
  - ficha desplegable con resultados historicos por centro y linaje de fuente/granularidad/cobertura;
  - accion manual para agregar centros sin borrar la muestra vigente.
- `/muestra/generar` queda como propuesta automatica editable.

### Datos
- Se agregaron contratos aditivos:
  - `historico_fuentes`
  - `centro_codigos`
  - `centro_snapshot`
  - columnas de trazabilidad en `muestra`: `motivo`, `agregado_por`, `score_snapshot`, `confianza_snapshot`, `created_at`.
- `seed_resultados_historicos.py` ahora puebla metadatos de fuente, snapshots disponibles y los mapeos viejo/nuevo del RR 2004.
- Correccion de alcance: los archivos oficiales por mesa ya versionados en `backend/data` para 2006, 2012 y 2013 tambien alimentan `resultados_historicos` agregados por centro:
  - `2006-presidencial`: 10.936 centros.
  - `2012-presidencial`: 13.818 centros.
  - `2013-presidencial`: 13.850 centros.
- Esos tres historicos se registran como `cne_recuperado` con granularidad `mesa`; el laboratorio los usa para tendencia, estabilidad, confianza y snapshots por eleccion.

### Validacion
- `D:\Test\.venv\Scripts\python.exe -m py_compile backend\app.py backend\muestra_lab.py backend\seed_resultados_historicos.py backend\init_db.py`: OK.
- `D:\Test\.venv\Scripts\python.exe backend\seed_resultados_historicos.py`: OK.
- Conteos limpios en `resultados_historicos`: 2004=6.265, 2006=10.936, 2012=13.818, 2013=13.850, 2024=11.925 centros.
- `D:\Test\.venv\Scripts\pytest.exe -q`: 20 passed.
- Uvicorn local: `/muestra` responde 200 y renderiza `Laboratorio de centros`.
- Ajuste de dominio de datos: `/muestra` responde 200 con filtros de municipio/parroquia y tabla ordenable.
- Ajuste de ficha/orden:
  - la columna Centro ordena por nombre del centro antes que por codigo CNE;
  - la ficha muestra todos los historicos disponibles del centro, no solo los 4 mas recientes;
  - los nombres visibles prefieren el snapshot historico mas completo cuando `centros.nombre` viene truncado;
  - se reemplazaron separadores propensos a mojibake por guiones ASCII.
- Correccion metodologica de clasificacion:
  - `bastion_rojo`/`bastion_azul` se calcula por persistencia de la brecha propia del centro;
  - la estabilidad visible usa desviacion estandar de la brecha del centro;
  - el desvio contra el resultado nacional queda como indicador separado de representatividad, no como criterio para llamar cambiante a un bastion estable.
- Ajuste de interfaz en `/muestra`:
  - se separo la pantalla en subpestanas `Laboratorio` y `Muestra actual` para reducir ruido visual;
  - se agregaron ayudas contextuales `(?)` en metricas y cabeceras: mesas, confianza, score, desvio, estabilidad de brecha, brecha, estatus, tipo, electores e historicos.
- Ajuste de score:
  - la confianza visible ahora representa confianza de tendencia, no solo calidad de fuente;
  - se agrego un factor de suficiencia historica: 1 historico queda penalizado, 2 historicos quedan parcialmente penalizados, 3 historicos casi completos y 4+ historicos completos;
  - el score final tambien se multiplica por esa suficiencia para impedir que un centro con un unico dato historico aparezca como maximo candidato.
- Ajuste de clasificacion de estabilidad:
  - `cambiante` ya no se determina por cambio de signo de la brecha cruda, porque una eleccion nacional atipica puede mover todo el pais;
  - se agrego estabilidad relativa contra la brecha nacional de cada eleccion y esa metrica alimenta `representativo`, `cambiante`, score y ordenamiento;
  - la tabla muestra `Estab. rel.` como metrica principal y conserva `Estab. brecha` cruda dentro de la ficha desplegable.
- Aclaratoria de ponderacion:
  - el tooltip de `Tipo` explica cada categoria visible;
  - el tooltip de `Score` muestra la ponderacion vigente en la app;
  - se deja documentado que volumen no domina el score para evitar sesgo hacia centros grandes; debe operar junto con estratos y pesos, no como unico criterio de ranking.
- Implementacion dictamen comite tecnico - score v2:
  - se adopto `ADR-012`: utilidad separada de confianza;
  - el score deja de sumar confianza y deja de aplicar penalizacion externa por suficiencia historica;
  - la utilidad barometro queda en 50% representatividad relativa, 30% estabilidad relativa robusta y 20% volumen;
  - la confianza A-D queda como eje paralelo con fuente, granularidad, cobertura, recencia y `n_eff`;
  - se reemplazo sigma por MAD para estabilidad relativa y se agrego shrinkage adaptativo hacia el estrato con `k=1.5`, apagandolo cuando `n_eff >= 2.5`;
  - 2024 queda marcado como `actas_cvzla`, cobertura 81%, y se agrega bandera `ruptura_2024` cuando el desvio relativo reciente se aparta mas de 8pp del promedio previo;
  - la app muestra una nota metodologica de score v2 y tooltips actualizados.
- Ajuste de seleccion operativa:
  - se agrego `Uso` como regla paralela al score: `ancla`, `condicional_sin_2024`, `condicional`, `no_ancla` o `sin_score`;
  - el orden inicial del laboratorio prioriza `Uso` y luego `Score`; ordenar por `Score` sigue disponible para ver utilidad pura;
  - un centro sin dato 2024 no debe anclar si hay alternativa similar con 2024 y confianza A/B.
- Pendientes aceptados:
  - boton de seleccion automatica bajo score v2 como preseleccion editable;
  - fase logistica posterior a la seleccion metodologica: accesibilidad, seguridad, cobertura de encuestadores, zonas rurales/fronterizas y sustitutos;
  - recalibrar tendencias cuando se incorporen nuevos resultados historicos previos.

---

### Pendiente
- BUG-002 (error muestral de la ficha técnica) requiere definir el n correcto.
- Deploy a Azure para activar los fixes en producción.

---

## 2026-08-15 - Datasets historicos Referendum 2007 y Enmienda 2009

### Contexto
- Se incorporo la recuperacion de Esdata/Wayback para el referendum constitucional nacional 2007.
- Se incorporo la recuperacion de Esdata/Wayback para el referendum nacional de enmienda constitucional 2009.
- La fuente 2007 es `resultados_elecc_2007.xls.zip`, con hojas de mesas con resultado y mesas sin resultado. El binario no se versiona; el proyecto conserva solo el CSV agregado por centro.
- La fuente recuperada es `ENMIENDA2009_2boletin.xls.zip`, con resultados por mesa. El binario no se versiona; el proyecto conserva solo el CSV agregado por centro.

### Cambio
- Se agrego `backend/import_2007_esdata.py` como importador reproducible.
- Se agrego `backend/import_2009_esdata.py` como importador reproducible.
- Se agrego `backend/resultados_ref2007.csv` con 9.002 centros agregados con resultado.
- Se agrego `backend/resultados_enmienda2009.csv` con 11.233 centros agregados.
- `backend/seed_resultados_historicos.py` ahora siembra `2007-referendum` y `2009-enmienda` en:
  - `resultados_historicos`
  - `centro_snapshot`
  - `historico_fuentes`
  - `centro_codigos` cuando aplica codigo viejo/nuevo.
- `backend/muestra_lab.py` ahora completa metadatos faltantes sin sobrescribir los sembrados por `seed_resultados_historicos.py`; esto evita degradar 2007/2009 a fuente `otro` al abrir `/muestra`.
- Se actualizaron `README.md`, `README.es.md` y `CHANGELOG.md`.

### Criterio metodologico
- En el referendum constitucional 2007, `SI` apoyaba la propuesta de reforma del gobierno y se almacena como `votos_gobierno`.
- `NO` se almacena como `votos_oposicion`.
- Como 2007 tuvo bloques A/B, la tendencia por centro combina la relacion SI/NO de ambos bloques y preserva volumen aproximado de votantes promediando votos validos entre bloques.
- Fuente `esdata_wayback`, granularidad `mesa`, cobertura registrada `86.5`, notas de primer boletin CNE y recuperacion parcial.
- En la enmienda 2009, `SI` apoyaba la propuesta del gobierno y se almacena como `votos_gobierno`.
- `NO` se almacena como `votos_oposicion`.
- Fuente `esdata_wayback`, granularidad `mesa`, cobertura registrada `99.0`, notas de segundo boletin CNE.
- El CSV versionado no contiene cedulas, nombres de electores ni registros persona a persona.

### Validacion
- `D:\Test\.venv\Scripts\python.exe backend\import_2007_esdata.py`: OK.
  - 29.072 mesas fuente con resultado.
  - 4.542 mesas fuente sin resultado.
  - 11.132 centros fuente.
  - 9.002 centros exportados.
- `D:\Test\.venv\Scripts\python.exe backend\import_2009_esdata.py`: OK.
  - 34.541 filas de mesa en fuente.
  - 34.185 mesas con votos SI/NO.
  - 11.422 centros fuente.
  - 11.233 centros exportados.
- `D:\Test\.venv\Scripts\python.exe -m py_compile backend\import_2007_esdata.py backend\import_2009_esdata.py backend\seed_resultados_historicos.py`: OK.
- `D:\Test\.venv\Scripts\python.exe backend\seed_resultados_historicos.py`: OK.
  - `2007-referendum`: 9.002 centros.
  - `2009-enmienda`: 11.233 centros.
  - Totales 2007 sembrados: 8.870.584 votos validos aproximados, 4.357.243 gobierno, 4.513.341 oposicion.
  - Totales sembrados: 11.504.321 votos validos, 6.310.482 gobierno, 5.193.839 oposicion.
- `/muestra`: 200; metadata verificada despues de cargar la ruta:
  - `2007-referendum`: `esdata_wayback`, `mesa`, cobertura 86.5.
  - `2009-enmienda`: `esdata_wayback`, `mesa`, cobertura 99.0.

---

## 2026-08-15 - Convergencia temporal en score de muestra

### Contexto
- Se agrego la hipotesis metodologica de que un centro gana valor barometrico si su distancia contra el resultado nacional disminuye con el tiempo.
- La metrica no reemplaza confianza A-D ni la representatividad actual; actua como senal adicional de calibracion historica.

### Cambio
- `backend/muestra_lab.py` agrega `_temporal_convergence()`.
- Requiere al menos 3 historicos comparables con brecha nacional.
- Calcula una pendiente ponderada del `desvio` relativo en el tiempo.
- Si el desvio baja, agrega un bonus capado de 0 a 8 puntos al score.
- Si el desvio sube, el bonus queda en 0 y no se castiga adicionalmente para evitar doble penalizacion.
- `backend/templates/muestra.html` agrega la columna sortable `Conv.` y badges explicativos en la ficha del centro.
- `DECISIONES.md` actualiza ADR-012 con la formula:
  - `U = min(100, 100*(0.50*R + 0.30*E + 0.20*V) + Bc)`.

### Validacion
- `/muestra`: 200.
- `D:\Test\.venv\Scripts\python.exe -m py_compile backend\muestra_lab.py backend\app.py`: OK.
- Se verificaron ejemplos del top del laboratorio con componente `C` en `score_componentes`.

---

## 2026-08-15 - Ajuste visual y disponibilidad GPS en laboratorio

### Cambio
- La tabla del laboratorio queda contenida en un área con desplazamiento horizontal, con anchos de columna estables y cabeceras alineadas con sus datos.
- Se agrega la columna sortable `GPS` como indicador binario de disponibilidad de latitud y longitud por centro.
- La ficha del centro informa si existen coordenadas y muestra el radio de geocerca configurado; la tabla no expone los valores de latitud o longitud.
- `backend/muestra_lab.py` entrega `tiene_gps` y `geocerca_radio_m`, usando 300 metros como valor por defecto cuando no existe un radio específico.

### Validacion
- La suite completa responde `20 passed`.
- `python -m py_compile` valida `backend/muestra_lab.py`, `backend/seed_resultados_historicos.py` y ambos importadores históricos.

---

## 2026-08-15 - Recuperacion de Azure tras 503 de arranque

### Diagnostico
- `estacomp.systems` y el hostname interno de App Service devolvian `503 Application Error`.
- DNS y TLS del dominio raiz eran correctos: ambos hostnames resolvian al mismo App Service.
- GitHub Actions completo correctamente build y OneDeploy para `6e03990`; la falla ocurria despues del despliegue, durante el arranque del proceso.
- `startup.py` sembraba todos los historicos de forma sincronica y FastAPI repetia la misma operacion en su evento `startup`. La semilla procesa cuatro CSV y tres Excel y tardo aproximadamente 32 segundos en el entorno local, con riesgo de superar el limite de arranque en el plan B1.

### Cambio
- GitHub Actions instala las dependencias dentro de `.python_packages/lib/site-packages` como parte del artefacto OneDeploy.
- `startup.py` y `startup.sh` eliminan `pip install` del runtime, configuran `PYTHONPATH` al paquete desplegado e inician Uvicorn con `python -m uvicorn`.
- `startup.py` y `startup.sh` inician Uvicorn sin repetir la semilla historica.
- FastAPI conserva la actualizacion idempotente, pero la ejecuta una sola vez mediante `asyncio.to_thread()` y una tarea de fondo guardada en `app.state.historicos_seed_task`.
- Una base completamente vacia sigue pasando por `init_showcase.py` antes de iniciar Uvicorn.
- Se agrego `test_startup.py` para impedir que una semilla lenta vuelva a bloquear el evento de arranque.

### Validacion
- Suite completa: `21 passed`.
- Prueba local de Uvicorn: `/` respondio 200 en aproximadamente 1,4 segundos mientras la semilla seguia en segundo plano.

---

## 2026-08-16 - Pendientes de recuperacion historica 2007, 2009, 2015 y 2018

### Alcance ya cubierto
- `2007-referendum` y `2009-enmienda` ya cuentan con resultados electorales agregados por centro recuperados de Esdata/Wayback. Este pendiente no cuestiona esos datasets.
- `2018-presidencial` ya aparece en `/historicos` como resultado oficial nacional fijo, pero no dispone del desglose requerido por mesa o centro.

### Estudios de exit poll pendientes
- **2007:** Gmail conserva el reporte agregado de PLM y una hoja con 251 capturas de 131 codigos internos de centro. Falta el estudio completo, la correspondencia entre esos codigos y los centros CNE, y el detalle verificable de ambos bloques A/B.
- **2009:** Gmail conserva el reporte final agregado y una muestra operativa con nombres de centros. No se encontro la base final de capturas por centro.
- Las bases `BD3`, `BD6` y `BD9` localizadas para 2009 son versiones anteriores a la votacion o contienen datos de prueba. No deben importarse como resultados reales del estudio.

### Resultados electorales pendientes
- **2015:** conseguir una fuente trazable con resultados desglosados por mesa o, como minimo, por centro de votacion.
- **2018:** sustituir o complementar el resultado nacional fijo con una fuente trazable desglosada por mesa o centro.

### Criterio de cierre
- Un proceso solo deja de estar pendiente cuando existe un archivo fuente preservable, procedencia documentada, identificadores conciliables con el registro de centros y una auditoria de cobertura.
- Los reportes agregados, graficos finales y archivos de prueba sirven como evidencia metodologica, pero no sustituyen el dataset granular requerido por el laboratorio de muestra.

---

## 2026-08-21 - Evidencia CNE archivada para Presidencial 2018

### Hallazgo
- La enumeracion publica de subdominios de `cne.gob.ve` muestra hosts historicamente relevantes para resultados: `resultados.cne.gob.ve`, `resultados2024.cne.gob.ve`, `resultados2021.cne.gob.ve`, `resultadosanreg2025.cne.gob.ve` y `www4.cne.gob.ve`.
- `www4.cne.gob.ve/ResultadosElecciones2018/` tiene capturas de Wayback con la pantalla nacional 2018 y endpoints AJAX archivados.
- La captura nacional conserva ficha tecnica y porcentajes por candidato via `grafico_participacion.php`.

### Cambio
- Se agrego `backend/data/2018/cne_archivado_nacional.json` como evidencia versionada de la fuente CNE/Wayback 2018.
- Se actualizo `backend/historico_1998_2024.csv` para registrar 2012/2013 como copia publica CNE scrapeable y 2018 como fuente CNE archivada solo nacional.
- Se actualizo la fuente de `2018-presidencial` en `backend/data/historico_estudios_seed.json` a `Wikipedia/CNE agregado nacional + CNE 2018 archivado en Wayback`.
- README y README.es documentan que 2018 sigue siendo una tarjeta oficial nacional, no un dataset granular para el laboratorio de muestra.

### Pendiente
- Los endpoints territoriales archivados probados para 2018 devolvieron `Esperando Totalizacion de Datos`; no hay todavia resultados por mesa o centro.
- El pendiente 2018 solo se cierra si aparece una fuente trazable y preservable con granularidad por mesa o centro y auditoria de cobertura.

---

## 2026-08-21 - Resultados estadales provisionales Presidencial 2018

### Criterio pragmatico
- Dado que la Gaceta Electoral 2018 no se ha podido descargar desde una fuente primaria y el portal CNE archivado depende de respuestas POST que Wayback no reproduce, se incorpora el mejor desglose disponible por estado como insumo provisional.
- El archivo no se trata como cierre del pendiente granular: mejora el nivel nacional a nivel estadal, pero no reemplaza una fuente oficial por municipio, centro o mesa.

### Cambio
- Se agrego `backend/data/2018/resultados_estadales_provisional.csv` con 24 filas estadales de electores, participacion y votos de Maduro, Falcon, Bertucci y Quijada.
- Se agrego `backend/data/2018/resultados_estadales_provisional.json` con procedencia, fuentes consultadas, sumas y deltas contra los totales nacionales CNE finales.
- `backend/data/2018/cne_archivado_nacional.json`, `backend/historico_1998_2024.csv`, README y README.es documentan la nueva evidencia y su estatus `provisional_no_reconciliado`.

### Validacion
- Participacion estadal suma 9.389.056, igual al total nacional final citado.
- Los votos por candidato no reconcilian completamente: Maduro -86, Falcon -117, Bertucci -19.259 y Quijada +186 contra el total nacional final. La brecha de Bertucci es material y mantiene la fuente en estado provisional.
- `josebhuerta.com/historico_electoral.php` devolvio 503 durante la verificacion; queda como pista para intentar municipio en otra pasada.

---

## 2026-08-23 - Normalizacion historica oficial y VENPRES-A 2018

### Cambio
- Se agrego un contrato aditivo normalizado para `resultados_historicos`: electores, votantes, validos, nulos, gobierno, oposicion, otros, porcentajes sobre validos, participacion, exterior, granularidad, fuente, corte, notas, mesas y detalle JSON de otros.
- Se agrego `backend/historico_normalizacion.py` y se conecto a `schema.sql`, `init_db.py`, `muestra_lab.py` y `seed_resultados_historicos.py`.
- Se incorporo `backend/import_2018_venpres_a.py` para generar `backend/data/2018/resultados_venpres_a_2018.csv` desde VENPRES-A (`10.7910/DVN/NO1XJ2`).
- `2018-presidencial` se siembra ahora en `resultados_historicos`, `centro_snapshot` y `historico_fuentes` como `venpres_a`, granularidad `centro`, cobertura `98.37`, sin exterior.

### Criterio metodologico
- En VENPRES-A 2018, `mesas` se conserva como cantidad de mesas del centro, no como identificador de mesa.
- `voto_c` en el XLSX fuente se trata como `votantes`; `votos_validos` se recalcula desde candidatos para que los nulos no entren en `votos_otros`.
- Maduro se almacena como gobierno, Falcon como oposicion y Bertucci+Quijada como otros. El detalle agregado se conserva en `detalle_otros_json`.
- 1998 y 2000 quedan como antecedentes y no se fuerzan a codigos CNE modernos en esta normalizacion.

### Validacion
- `backend/validar_historico_normalizado.py` genera la comparativa normalizada.
- Totales validados:
  - 2006: 10.936 centros, 32.788 mesas, 15.868.348 electores, 11.728.599 votantes, 11.569.233 validos, 159.366 nulos, exterior incluido.
  - 2012: 13.818 centros, 39.299 mesas, 18.836.157 electores, 15.171.358 votantes fuente, 14.864.226 validos, 287.267 nulos, exterior incluido.
  - 2013: 13.850 centros, 39.360 mesas, 18.895.335 electores, 15.055.498 votantes, 14.988.563 validos, 66.935 nulos, exterior incluido.
  - 2018: 14.400 centros, 33.716 mesas, 20.517.997 electores, 9.360.318 votantes, 9.203.220 validos, 157.098 nulos, exterior no incluido.
- Identidades:
  - `votos_validos = gobierno + oposicion + otros` cierra en 2006, 2012, 2013 y 2018.
  - `votantes = votos_validos + votos_nulos` cierra en 2006, 2013 y 2018.
  - 2012 queda con delta abierto de -19.865 entre `validos+nulos` y la columna fuente de votantes; no se corrige silenciosamente.

### Pendiente
- Normalizar fichas de estudios historicos en una fase posterior; por ahora se mantiene la UI funcional.
- Buscar fuente granular trazable 2015 y una segunda fuente publica centro por centro para contrastar VENPRES-A 2018.

---

## 2026-08-23 - Rendimiento en Azure: event loop, cache de /live y 500 por lock de BD

### Sintoma reportado
"El Azure esta lento". Sin mas detalle.

### Diagnostico
La medicion que aislo el problema fue lanzar una peticion pesada en segundo plano y cronometrar una ruta trivial en paralelo:

```
5x GET /  secuencial:            0.16 s cada una
5x GET /  con un /live en vuelo: 9.0 s cada una
```

La app no era lenta: se serializaba. Las 59 rutas estaban declaradas `async def` pero hacian I/O sincrono (sqlite3, ficheros, folium/plotly), asi que bloqueaban el event loop. Con un solo worker de uvicorn sobre el core del plan B1, una peticion pesada congelaba todo lo demas.

`/live` era el bloqueador dominante: en **cada** request hacia `importlib.reload(generador_dashboard)`, parseaba el geojson desde disco, regeneraba el dashboard completo a un fichero temporal y lo releia. 6.3-6.6 s medidos, y la pagina se auto-refresca.

### Cambios de rendimiento
- 50 rutas `async def` -> `def` para que FastAPI las corra en el threadpool. Se clasificaron con AST, no por texto: 9 usan `await` y se quedaron async.
- El generador SSE de `/stream/dashboard` ejecuta su consulta con `asyncio.to_thread`; antes bloqueaba el loop cada 60 s por cada pestana abierta.
- `/live` cachea el HTML por huella de contenido.
- `_tendencia_simulada` usa un RNG sembrado con los datos de entrada. Con `random` global la serie cambiaba en cada request: el cache nunca podia pegar y la linea saltaba en cada recarga sin que el dato hubiera cambiado.
- Cache del mapa base gris y de la lectura de los geojson (1.25 MB ADM1 / 3.2 MB ADM2), que sobre Azure Files son un share de red.
- Se eliminan el `sys.path.insert(0, BASE_DIR)` por request (hacia crecer `sys.path` sin limite) y los `importlib.reload` de los generadores.
- `GZipMiddleware` con el SSE excluido via `Content-Encoding: identity`.

### Nota sobre gzip: el nivel por defecto era un retroceso
Con el `compresslevel=9` por defecto de Starlette, `/live` empeoro: 2.04-2.17 s totales contra 0.95-1.01 s sin comprimir. Comprimir 1.49 MB a nivel 9 cuesta ~1.2 s en ese core, mas de lo que ahorra en transferencia. Se bajo a nivel 5, que comprime 6x mas rapido por un 2% mas de bytes (424 KB vs 415 KB sobre 1.48 MB).

Sin medir en produccion, ese cambio habria empeorado la pagina creyendo mejorarla.

### Los 500 de /config y /muestra
Ambas devolvian 500 tras exactamente ~5 s. Reproducido en local, el traceback fue directo: `sqlite3.OperationalError: database is locked`, y los 5 s eran el timeout por defecto de sqlite3.

Cadena completa:
1. `seed_resultados_historicos` corre en cada arranque y reprocesa todos los CSV: **34.6 s en SSD local**, bastante mas sobre Azure Files, con una transaccion de escritura abierta todo ese tiempo.
2. Dos rutas GET escribian en cada peticion: `ensure_config_table` hacia `CREATE TABLE` + INSERTs, y `construir_laboratorio` llamaba a `ensure_muestra_lab_tables` y `seed_default_historical_metadata`.
3. Necesitaban el lock que el seed tenia tomado, esperaban 5 s y morian.

Por eso fallaban siempre a los ~5-7 s y se "curaban solas" al terminar el seed. Cada deploy y cada reinicio reabria la ventana.

Resolucion:
- El seed se salta si las fuentes no cambiaron, por huella de tamano y mtime de cada fichero mas los metadatos de `DATASETS`/`EXCEL_DATASETS`, guardada en la tabla `seed_state`. Medido: 34.6 s -> 0.0 s con los mismos 91.429 registros en 8 refs. Verificado que tocar un CSV lo vuelve a disparar entero.
- `ensure_config_table` y el bootstrap de `muestra_lab` se ejecutan una vez por BD, no por peticion. El guard va por ruta de fichero y no por booleano porque los tests intercambian `DB_PATH` dentro del mismo proceso.
- Ese bootstrap se movio al evento de startup, sincrono y antes de lanzar el seed pesado. App Service no enruta peticiones hasta que termina el startup, asi que ninguna llega compitiendo por el lock.
- `get_db()` usa `timeout=30` en vez del default de 5 s como red de seguridad. En WAL los lectores no se bloquean.

### /version nunca mostro un commit
`_detect_app_version` nacio en `f6fe39c` leyendo `APP_COMMIT_SHA`, `GITHUB_SHA`, `COMMIT_SHA` y `WEBSITE_DEPLOYMENT_ID`. El workflow nunca puso ninguna de las tres primeras; la cuarta si existe en App Service pero vale el nombre del sitio (`exit-poll-ve`), no un sha, y al estar en la lista cortocircuitaba la deteccion. El fallback a `git rev-parse` tampoco podia salvarlo porque el `.git` no se despliega.

Ahora el workflow escribe `deploy_root/VERSION` con el sha y la fecha de build, y `app.py` lo lee. `WEBSITE_DEPLOYMENT_ID` sale de la lista.

### Resultados medidos en produccion

| Ruta | Antes | Despues |
|------|-------|---------|
| `GET /` con un `/live` en vuelo | 9.0 s | **0.33 s** |
| `/live` | 6.3-6.6 s | **0.86 s** |
| `/pesos` | 1.14 s | **0.28 s** |
| `/config` | 500 a los ~5 s | **200**, 0.2-0.9 s |
| `/muestra` | 500 a los ~5 s | **200** (pero lento, ver Pendiente) |
| `/` (control) | 0.16 s | 0.17 s |

`/config` verificado 14 veces seguidas durante el deploy y el reinicio, incluida la ventana del seed: todas 200, cero `database is locked` en el log.

### Pendiente
- `/muestra` responde 200 pero tarda 23-27 s en Azure (~4 s en SSD local). Perfilado con cProfile: de los ~4 s locales, 2.65 s son `statistics._ss` (29.646 llamadas). El modulo `statistics` de la stdlib usa `Fraction` para aritmetica exacta, asi que el perfil lo dominan `fractions.py` y 946.338 llamadas a `math.gcd`, recalculando sobre las 91.429 filas de `resultados_historicos` en cada peticion. No hace falta precision exacta para desviaciones tipicas de porcentajes electorales.
- Quedan 9 rutas POST en `async def` (`/muestra/aplicar`, `/chat`, `/api/tm/*`, `/historicos/estudios/guardar`). Todas hacen `await request.form()` y despues trabajo bloqueante, asi que no se convierten con un cambio de firma: hay que mover el cuerpo a un hilo una por una. Siguen pudiendo congelar la app mientras corren, pero son rutas de operador (un click humano cada tanto), no el dashboard que auto-refresca.

---

## 2026-08-25 - Marco electoral 2024 completo, normalizacion de estados y limpieza de /tm

### De donde salio el marco 2024
El TM 2024 en uso venia del dump de actas de resultadosconvzla: 11.927 centros,
22.197 mesas, 17.502.516 electores. Los centros sin acta digitalizada no
existian para el selector.

Se busco una TM oficial del CNE por mesa para 2024 y no existe. Igual que en
2018, el CNE no publico ni el desagregado de resultados ni el directorio de
centros y mesas del ciclo, y `cne.gob.ve` ya no resuelve DNS. En Wayback bajo
`registro_electoral/centros/2024/` solo quedo `PUNTOS_RE_PRESIDENCIAL_2024.pdf`,
que son puntos de inscripcion.

Lo que si existe y estaba a mano es el REP 2024 por CENTRO, en la hoja
`15.962 centros_cne` del spreadsheet de `ipince/vzlapi`. Copiado al repo como
`backend/centros_cne_2024_rep.csv`. Cuadra exacto con tres cifras oficiales:
21.392.464 electores venezolanos, 228.144 extranjeros, y 106 centros con 69.211
electores en el exterior. Sin mojibake, a diferencia del TM anterior, que traia
nombres truncados (`EDO. DELTA AMAC`, `MP. JUAN GERMAN ROSC`) y danados
(`FERMIN TORO` como `FERM?N TORO`).

Ver ADR-018 para la calibracion de `CAP_MESA = 1000` y el reparto de electores
entre mesas. Genera `backend/generar_tm_2024.py`.

### Carga
Carga diferencial con `cargador_tm.py`: 813 centros nuevos, 11.916 actualizados,
3.233 sin cambio, 906 desactivados. El marco activo queda en 15.962 centros /
30.459 mesas / 21.392.464 electores.

Efecto colateral que hay que tener presente: 16 de los 120 centros de la muestra
de `Presidenciales 2025` (y 5 de la eleccion 2) quedaron `activo=0` porque no
estan en el REP 2024. La muestra se regenero despues desde la app.

### Renombre de estados y un bug que estaba vivo
La BD arrastraba tres nombres del CNE viejo: `EDO. VARGAS` (el estado es La
Guaira desde 2019), `EDO.NVA.ESPARTA` y `EDO. DELTA AMAC`. El cargador matchea
estados por `codigo_cne` y no renombra los existentes, asi que la carga 2024 no
los toco.

Antes de renombrar se verifico que la seleccion no dependiera de esos nombres:
- `selector_muestra.py` y `selector_longitudinal.py` agrupan por `id_estado`.
- `_estado_display` en `muestra_lab.py` ya colapsaba VARGAS y GUAIRA en la misma
  etiqueta.
- `resultados_historicos` linkea por `codigo_centro`, nunca por nombre.

Se capturo una huella del laboratorio (1.000 centros con `estado_display`,
`estado_filtro`, `score` y `estatus`) antes y despues de cada renombre. Ambas
salieron identicas.

El renombre destapo un bug real en `_norm_estado`, que traduce nombres del CNE a
los del GeoJSON para el heatmap:

- `EDO.NVA.ESPARTA` daba `Edo.Nva.Esparta`. El `.replace("EDO. ", "")` no
  matcheaba porque en BD no habia espacio tras `EDO.`, y `.replace("NVA. ESPARTA", ...)`
  tampoco porque en BD era `NVA.ESPARTA`. **Nueva Esparta no estaba pintando en
  el mapa.**
- Renombrar Delta Amacuro lo habria roto: `.replace("DELTA AMAC", "Delta Amacuro")`
  aplicado sobre `EDO. DELTA AMACURO` da `Delta Amacurouro`. Ese estado
  funcionaba precisamente porque el nombre estaba truncado.

Se endurecio `_norm_estado` (variantes largas antes que las cortas, y `EDO.` sin
espacio) y despues se renombro. Las seis grafias convergen y los 24 estados
domesticos matchean contra el GeoJSON ADM1.

### Limpieza de /tm
Las tarjetas "Estados" y "Mun. / Parr." mostraban `COUNT(*)` pelado sobre las
tablas de geografia, sin filtrar por `activo` ni por centros vivos, mientras el
resto de las tarjetas si filtra. De ahi salia `430 / 1278`. La descomposicion
real: 335 municipios y 1.141 parroquias de Venezuela con centro activo, mas 86 y
106 del exterior (el CNE modela paises como municipios y consulados como
parroquias), mas 9 y 31 que solo tenian centros ya desactivados. Los 335 cuadran
exacto con la cifra oficial.

Se quitaron las dos tarjetas y sus consultas. El estudio es domestico y esos
numeros solo hacian ruido. Las cuatro que quedan pasaron a `col-md-3`.

Tambien se corrigio que La Guaira apareciera sin prefijo en la tabla por estado:
el override de `app.py` forzaba `"LA GUAIRA"` para fusionar filas VARGAS y
LA GUAIRA, y de paso comia el prefijo. Ahora fuerza `"EDO. LA GUAIRA"`.

### Comparacion Azure vs local
Azure corre `ceaa6830` con el marco viejo. Diferencias medidas:

| | Azure | Local |
|---|---|---|
| Centros activos | 14.910 | 15.962 |
| Electores | 18.740.203 | 21.392.464 |

Los 25 estados ganaron electores. Seis perdieron centros (Tachira -48, Aragua
-18, Merida -12, Exterior -12, Barinas -9, Sucre -2): es consolidacion, no
perdida de votantes, Tachira pierde 48 centros y suma 60.828 electores.

Muestra de 120 contra muestra de 120: 89 se mantienen, 31 rotan. De los 31 que
salen, 16 ya no existen en el marco 2024 y 15 los desplazo la cuota. Cambios de
cuota: Miranda +1, Bolivar +1, Portuguesa +1, Distrito Capital -1, Aragua -1,
Zulia -1.

Lo menos evidente: **de los 89 centros que se mantienen, 81 cambiaron su numero
de electores**, algunos mas de 2.000 en ambas direcciones. Sus pesos de
expansion cambiaron aunque el centro sea el mismo.

### El frame de 8.314
La generacion 3 registro `frame_count=8314` / `frame_electores=18435500`. No
tiene que ver con disponibilidad de historico: es el piso
`MIN_ELECTORES_CENTRO = 800` de `selector_longitudinal.py` sobre los estados
1-24. Verificado, los dos numeros dan exacto.

El piso descarta el 47,6% de los centros pero solo el 13,5% del electorado; los
7.542 excluidos promedian 383 electores.

El REP 2024 ensancho ese frame mas que el universo. Universo +7,2%, frame
+16,4% (7.142 -> 8.314):

```
cruzaron el piso hacia arriba (<800 -> >=800)   +1,316
cayeron por debajo del piso  (>=800 -> <800)       -94
centros nuevos que ya entran elegibles            +396
centros que desaparecieron del marco              -446
```

1.316 centros que antes eran invisibles para el selector ahora compiten. Eso
reencuadra las rotaciones de la muestra: muchos de los 15 desplazamientos "por
cuota" son centros que perdieron su puesto contra competidores que antes ni
participaban del sorteo.

### Pendiente
- La BD no se versiona, asi que el marco 2024 y los tres renombres de estado no
  viajan con este commit. Hay que repetir la carga en Azure. El codigo si es
  seguro de desplegar tal cual: `_norm_estado` acepta las grafias viejas y
  nuevas, y el override de La Guaira funciona con `EDO. VARGAS` en BD.
- Los renombres de estado se aplicaron a mano:
  `UPDATE estados SET nombre='EDO. LA GUAIRA' WHERE codigo_cne='24'` y
  equivalentes para `15 -> EDO. NUEVA ESPARTA` y `23 -> EDO. DELTA AMACURO`.
  Si se repiten a menudo conviene un script idempotente.
- `app.py` tiene dos bloques (lineas ~2247 y ~2279) que repiten la
  normalizacion de `_norm_estado` a mano, con los mismos errores que se
  arreglaron. Es codigo muerto: calculan una variable `nombre` que nunca se usa
  porque la linea siguiente llama a `_norm_estado`. Borrarlos.
- `centros_2024_hoja0/1/2.csv` en `backend/` son HTML de error de Google Docs,
  no CSVs. Quedaron de una descarga fallida.

## 2026-08-27 - Dashboard operativo, pruebas por fuente y cierre TM 2025

### Dashboard vs Live
`/live` queda como vitrina de seguimiento automatico: refresco por SSE, barra EN VIVO
y panel de analista IA. `/visualizacion` pasa a ser el dashboard operativo para
revision analitica sin auto-refresco ni analista.

La nueva vista usa la misma data viva ponderada que alimenta el stream:
- heatmap/tendencia territorial via `/visualizacion/mapa`;
- gauge de margen nacional;
- barras crudo vs ponderado con `Gobierno`, `Oposicion` y `Otros`;
- tendencia nacional;
- selector de estado con opiniones, cobertura, ventaja, desvio nacional y
  porcentajes Gob/Opo/Otros;
- tabla por estado con busqueda y ordenamiento;
- resumen de muestra, cobertura y pesos.

Se corrigio un problema previo de consistencia: `_datos_vivos` ya no cuenta todos
los votos crudos como si fueran el resultado operativo, sino que filtra muestra
activa titular y aplica `peso_nacion`/`peso_estado`. La ventaja por estado usa
denominador ponderado y el dashboard conserva `Otros` aunque su peso sea cero.

### Datos de prueba
Los botones de Inicio dejan de estar fijos a 2024 y a dos bandos. Ahora aceptan
una fuente:
- `random`, con pequena fraccion de `otros`;
- cualquier `eleccion_ref` historica disponible y compatible con el tipo de
  eleccion activa.

Cuando una referencia historica trae `votos_otros`, el test crea o reutiliza un
candidato de bando `otro` para que el dashboard muestre ese bloque. Esto aplica
igual a `Test Total` y `Test Data Entry`. `Reset` mantiene el comportamiento de
borrar `votos` y `sms_raw`.

### Tabla Mesa y Exterior
Queda documentada y reflejada en auditoria la separacion conceptual: el Tabla
Mesa debe comportarse como inventario completo del pais, incluyendo Exterior. Las
restricciones de elegibilidad domestica pertenecen al proceso electoral/muestra,
no a la carga de TM.

### Publicacion excepcional de base local
La politica normal sigue siendo no versionar `backend/exitpoll.db`. En este
cierre se incluye excepcionalmente por instruccion explicita del usuario, para
transportar la carga local actual junto con el codigo y los artefactos TM 2025.

## 2026-08-28 - Pendiente: auditoria legacy y auditoria nueva

Queda como pendiente separar dos planos de evaluacion historica que hoy pueden
mezclarse en las tarjetas:

- Auditoria legacy: el semaforo historico existia operacionalmente y dependia de
  numeracion interna por estudio mas tablas de conversion hacia centros CNE. La
  auditoria por centro solo debe activarse donde ese mapping este recuperado,
  trazado y sea confiable.
- Auditoria nueva: debe evaluar cobertura efectiva de campo, recepcion por
  centro/turno, estados inhospitos con informacion insuficiente y suficiencia
  minima antes de calcular metricas estadisticas o diagnosticos territoriales.

Si falta la conversion interna-CNE o la recepcion es insuficiente, el estudio se
mantiene como evidencia agregada o parcial. No se debe interpretar la ausencia
de mapping como falla del selector legacy ni reconstruir semaforos individuales
sin evidencia documental.
