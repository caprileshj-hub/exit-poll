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

### Pendientes Inmediatos
1. **Definición de Muestra**: Utilizar el dashboard ya funcional para filtrar los centros y exportar el CSV de muestra.
2. **Generación de Pesos**: Crear el archivo `pesos_finales.json` a partir de la muestra exportada.
3. **Simulacro Integral**: Ejecutar `test_flujo.py` utilizando los nuevos pesos reales.
4. **Sincronización**: Cambios recientes subidos a GitHub (Fase 5 Estabilizada).

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

#### Pendientes de Fase 6
- [ ] Backend FastAPI: parser SMS, validación GPS, lógica de turnos, alertas
- [ ] App Android: UI votante, generación SMS, modo offline/lote
- [ ] Gateway Android: lector SMS → HTTP POST
- [ ] Dashboard de auditoría interna: semáforo de centros, panel de encuestadores, alertas
- [ ] Gráficos torta/barras en el panel cliente
- [ ] Contraste con datos de exit poll anterior para validar modelo

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
