# CHANGELOG.md — Exit Poll Venezuela

> Historial de cambios por sesión, mantenido por los agentes al cierre de cada sesión de implementación.
> Orden: más reciente arriba. `[Unreleased]` agrupa lo pendiente de commit.
> Tipos: `feat` · `fix` · `refactor` · `test` · `docs` · `deploy` · `security`

---

## [Unreleased]

### docs - Metodologia de muestreo consolidada
- `docs/muestreo/METODOLOGIA_MUESTREO.md`: documenta la decision metodologica V1 como seleccion aleatoria estratificada por estado, reproducible por seed y sin uso de historicos para inclusion.
- `docs/muestreo/HISTORIAL_EXPERIMENTAL.md`, `RESULTADOS_BACKTEST.md` y `DECISIONES_MUESTREO.md`: consolidan la evolucion experimental, resultados verificados localmente y decisiones especificas de muestreo.
- `DECISIONES.md`: agrega ADR-016 y deja `historical_greedy` como estrategia experimental no promovida a produccion.
- Cambio documental solamente; no modifica comportamiento productivo ni cierra la implementacion productiva en este commit.

### fix — 500 "database is locked" en /config y /muestra
- `backend/seed_resultados_historicos.py`: el seed se salta si las fuentes no cambiaron. La huella cubre tamaño y mtime de cada fichero más los metadatos declarados en `DATASETS`/`EXCEL_DATASETS`, y se guarda en la nueva tabla `seed_state`. Tocar un CSV o editar un dataset vuelve a disparar el seed completo, así que un deploy con datos nuevos los sigue aplicando. Medido: 34.6 s → 0.0 s con los mismos 91.429 registros en 8 refs.
- `backend/app.py` · `ensure_config_table` y `backend/muestra_lab.py` · `construir_laboratorio`: dejan de escribir en cada petición GET. El trabajo idempotente se hace una vez por BD, con guard por ruta de fichero (no booleano) porque los tests intercambian `DB_PATH` dentro del mismo proceso.
- `backend/app.py`: ese bootstrap se ejecuta en el evento de startup, síncrono y antes de lanzar el seed pesado, para que ninguna petición llegue compitiendo por el lock de escritura.
- `get_db()` usa `timeout=30` en vez del default de 5 s como red de seguridad.
- Causa raíz: el seed mantenía una transacción de escritura abierta ~34 s mientras dos rutas GET necesitaban el lock para servirse; a los 5 s exactos sqlite abandonaba con `OperationalError`.

### refactor — Event loop desbloqueado y dashboard /live cacheado
- 50 rutas declaradas `async def` que solo hacen I/O síncrono pasan a `def`, para que FastAPI las corra en el threadpool. Con un worker sobre el core del B1, una petición pesada congelaba toda la app: `GET /` pasaba de 0.16 s a 9.0 s con un solo `/live` en vuelo; ahora 0.33 s.
- `/stream/dashboard`: el generador SSE ejecuta su consulta con `asyncio.to_thread`; antes bloqueaba el loop cada 60 s por cada pestaña abierta.
- `/live` cachea el HTML generado por huella de contenido: 6.3-6.6 s → 0.86 s en producción.
- `_tendencia_simulada` usa un RNG sembrado con los datos de entrada. Con `random` global la serie cambiaba en cada petición, lo que impedía cachear y hacía saltar la línea en cada recarga sin que el dato hubiera cambiado.
- Cache del mapa base gris de `_html_sin_datos` y de la lectura de los geojson (1.25 MB ADM1 / 3.2 MB ADM2), que en Azure viven en un share de Azure Files.
- Se eliminan el `sys.path.insert(0, BASE_DIR)` por petición (hacía crecer `sys.path` sin límite) y los `importlib.reload` de los generadores.
- Las 56 conexiones sqlite quedan en `try/finally`; varias rutas hacían `return` antes del `close()` y filtraban la conexión.

### fix — Compresión gzip y su nivel
- `GZipMiddleware` para respuestas > 1 KB, con el SSE excluido vía `Content-Encoding: identity` para que no bufferee los eventos. `/pesos` baja de 248 KB a 16.5 KB.
- `compresslevel=5` en vez del 9 por defecto de Starlette: medido en producción, con nivel 9 `/live` tardaba 2.04-2.17 s contra 0.95-1.01 s sin comprimir, porque comprimir 1.49 MB cuesta ~1.2 s en ese core. El nivel 5 comprime 6x más rápido por un 2% más de bytes.

### fix — /version y el badge del navbar nunca mostraron el commit
- `.github/workflows/master_exit-poll-ve.yml` escribe `deploy_root/VERSION` con el sha y la fecha de build al empaquetar; es la única fuente fiable en Azure porque el `.git` no se despliega.
- `backend/app.py` · `_detect_app_version` lee ese fichero primero y saca `WEBSITE_DEPLOYMENT_ID` de la lista de fuentes: en App Service vale el nombre del sitio, no un sha, y cortocircuitaba la detección desde `f6fe39c`.
- `/version` devuelve ahora `commit` y `built_at`; el badge de `base.html` muestra el sha corto y lleva la fecha de build en el `title`.

### feat — Normalización histórica oficial y VENPRES-A 2018
- `resultados_historicos` conserva su contrato legado y agrega campos normalizados para electores, votantes, votos válidos, nulos, exterior, fuente/corte, notas y mesas.
- `backend/import_2018_venpres_a.py` genera `backend/data/2018/resultados_venpres_a_2018.csv` desde VENPRES-A (`10.7910/DVN/NO1XJ2`) y preserva Falcon como oposición y Bertucci+Quijada como otros.
- `backend/seed_resultados_historicos.py` siembra 2018 como `venpres_a`, granularidad `centro`, cobertura `98.37`, sin exterior, y recalcula porcentajes políticos sobre votos válidos.
- `backend/validar_historico_normalizado.py` reporta la tabla comparativa 2006/2012/2013/2018 y deltas de identidad.
- Tests nuevos en `test_historico_normalizacion.py`.

### docs — Pendientes de recuperación histórica
- Se documenta que 2007 y 2009 tienen resultados electorales agregados en el sistema, pero siguen pendientes los estudios de exit poll completos y verificables.
- Se mantienen pendientes los resultados electorales desglosados por mesa o centro de 2015 y 2018; el registro nacional fijo de 2018 no sustituye ese detalle.
- Los archivos operativos de prueba localizados para 2009 no deben importarse como observaciones reales.

### fix — Arranque Azure no bloqueado por semillas históricas
- El workflow empaqueta dependencias en `deploy_root/.python_packages/lib/site-packages`; el contenedor deja de depender de PyPI durante cada reinicio.
- `backend/startup.py` y `backend/startup.sh` dejan de ejecutar las semillas históricas antes de iniciar Uvicorn.
- `backend/app.py` programa una única actualización histórica en un hilo de fondo, evitando que la lectura de Excel/CSV y la escritura SQLite excedan el tiempo de arranque de App Service.
- Se conserva `init_showcase.py` para inicializar una base completamente vacía antes de servir tráfico.
- `test_startup.py` verifica que FastAPI completa su evento de arranque sin esperar a que termine una semilla lenta.

### fix — Dominio visual y disponibilidad GPS en laboratorio de muestra
- `backend/templates/muestra.html`: la tabla del laboratorio usa anchos de columna estables y desplazamiento horizontal para evitar que las métricas salgan de la pantalla o pierdan alineación con sus cabeceras.
- Se agrega la columna sortable `GPS`, que indica únicamente si el centro tiene latitud y longitud disponibles para una futura gestión de geocerca.
- `backend/muestra_lab.py`: expone `tiene_gps` y el radio configurado del centro sin mostrar ni alterar sus coordenadas en la tabla.

### feat — Convergencia temporal en score de muestra
- `backend/muestra_lab.py`: agrega componente `C` de convergencia temporal. Con 3+ historicos comparables, mide si el desvio relativo del centro contra el resultado nacional baja con el tiempo.
- El score conserva la base 50% representatividad, 30% estabilidad y 20% volumen, y suma un bonus capado de hasta 8 puntos por convergencia; si el centro se aleja, no hay castigo adicional.
- `backend/templates/muestra.html`: nueva columna sortable `Conv.` y badges/tooltip en la ficha del centro.
- `DECISIONES.md`: ADR-012 actualizada con la formula del bonus de convergencia.

### feat — Datasets históricos Referéndum 2007 y Enmienda 2009
- `backend/import_2007_esdata.py`: importador reproducible desde Esdata/Wayback `resultados_elecc_2007.xls.zip`; procesa hojas de mesas con resultado y sin resultado.
- `backend/import_2009_esdata.py`: importador reproducible desde Esdata/Wayback `ENMIENDA2009_2boletin.xls.zip`; descarga temporal, extrae el XLS y exporta solo agregados por centro.
- `backend/resultados_ref2007.csv`: 9.002 centros con resultado, 29.072 mesas fuente con resultado y 4.542 mesas fuente sin resultado; cobertura parcial de primer boletín.
- `backend/resultados_enmienda2009.csv`: 11.233 centros, 34.250 mesas exportadas, 11.504.321 votos válidos y 16.684.405 electores; sin datos personales.
- `backend/seed_resultados_historicos.py`: siembra `2007-referendum` y `2009-enmienda` en `resultados_historicos`, `centro_snapshot`, `historico_fuentes` y mapeos de códigos alternos.
- `backend/muestra_lab.py`: `seed_default_historical_metadata()` ahora completa metadatos faltantes sin sobrescribir la fuente ya sembrada; conserva `esdata_wayback/mesa` para 2007/2009 y `cne_recuperado/mesa` para 2006/2012/2013.
- Convención metodológica 2007: `SI` se almacena como gobierno y `NO` como oposición; bloques A/B se combinan por ratio SI/NO preservando volumen aproximado de votantes.
- Convención metodológica: en la enmienda 2009, `SI` se almacena como gobierno y `NO` como oposición; fuente `esdata_wayback`, granularidad `mesa`, cobertura 99%, segundo boletín CNE.

---

## 2026-06-10

### fix — Dashboard de referencia filtra por la eleccion_ref más reciente
- Las funciones de ventaja (`_datos_ventaja_por_estado`, `_datos_ventaja_por_municipio` y variantes de muestra) y `_total_referencia_dashboard` sumaban **todas** las `eleccion_ref` de `resultados_historicos`; al importar el seed 2006 el dashboard `/live`, `/visualizacion` y el contexto del analista mezclaban 2006 con 2024 (ventaja nacional −3.7 pp en vez de −36.8 pp)
- Los `LEFT JOIN` de muestra además duplicaban filas por centro con dos refs
- Nuevo helper `_eleccion_ref_referencia()` resuelve la ref vigente (la más reciente); `/muestra` y `/muestra/generar` la usan en vez de `'2024-presidencial'` hardcodeado
- Archivos: `backend/app.py`, `test_flujo.py`
- Tests: regresión con dos refs cargadas; suite completa verde
- Deploy: requiere redeploy

### fix — Carga TM diferencial acotada a los estados presentes en el CSV
- `cargador_tm.cargar_tm` marcaba `activo=0` a todo centro de la BD ausente del CSV, sin importar el estado: un TM parcial (una regional) desactivaba los ~13.000 centros del resto del país
- La desactivación ahora se limita a los estados que el CSV cubre, igual que el path de ingesta IA (`_deactivate_tm_scope`)
- Archivos: `backend/cargador_tm.py`, `test_cargador_tm.py`
- Tests: TM parcial no toca otros estados; dry-run no escribe
- Deploy: requiere redeploy

### fix — Pesos con centros sin municipio y geografía compartida entre ingestas
- `calculador_pesos`: el `INNER JOIN` a municipios excluía en silencio del cálculo a los centros con `id_municipio NULL` (los crea la ingesta IA). Ahora `LEFT JOIN` con aviso; sin geografía asignada el centro agrupa como unidad propia (peso 1)
- `_obtener_o_crear_geo`: buscaba municipios/parroquias por igualdad exacta del nombre normalizado, que no coincide con los nombres crudos CNE de `cargador_tm` ("MP. ZAMORA" vs "Zamora") y creaba duplicados `AI##`. Nuevo `_geo_match_name()` compara nombres canónicos entre ambas fuentes
- Archivos: `backend/calculador_pesos.py`, `backend/app.py`, `test_geo_pesos.py`
- Tests: 20 passed (suite completa)
- Deploy: requiere redeploy

### fix — Menores del barrido de bugs
- `selector_muestra`: `diff_nac` de 0.0 (centro perfectamente representativo) se convertía en 999 por usar `or` como fallback de `None`
- `test_flujo`: resuelve `schema.sql` relativo al archivo; pytest funciona desde cualquier directorio
- Archivos: `backend/selector_muestra.py`, `backend/app.py`, `test_flujo.py`

### refactor — Limpieza del repositorio: legacy/
- `legacy/scripts_raiz/`: los 9 scripts pre-backend de las fases 1–6 (pipeline CSV 2024, crawler CNE 2013, dashboards Streamlit, graficadores) con sus datos
- `legacy/ai_configs/`: instrucciones por herramienta (aider, cursor, gemini, grok, etc.); quedan activos `AGENTS.md`, `CLAUDE.md` y `.github/copilot-instructions.md`
- `legacy/outputs/`: HTML generados, logs `server_*.txt` y dos BD vacías huérfanas
- `.gitignore`: ignora `server_*.txt`, elimina entrada obsoleta `/exit poll/`
- Archivos: `.gitignore`, `legacy/`
- Deploy: no requiere redeploy

---

## 2026-05-20

### feat — Municipales 2013: colección de 52 exit polls
- `backend/import_2013_municipales.py`: colección `2013-municipales` con 52 estudios municipales + fila `NACIONAL` de metadatos, desde `auditoria4.xlsx` y `PESO CENTROS DIC 2013.xlsx`
- Rutas `/historicos/estudios/2013-municipales` y `/{municipio_slug}`; templates `municipales_2013.html` y `municipal_2013_detalle.html`
- Semáforo de información confiable por municipio: centros esperados / que transmitieron / sin transmisión / cortes atípicos
- Detalle: BITACORA.md (2026-05-20)

### feat — Scraper archive.org para oficiales municipales 2013
- Scraper contra snapshots archive.org del CNE con pausas y reintentos; corrige mapeo de códigos CNE desplazado y toma solo el bloque `ALCALDESA O ALCALDE`
- 52 filas oficiales (51 municipios + NACIONAL); fichas técnicas manuales para Barinas, San Fernando, Maturín, Páez y Sucre-Sucre
- Pendiente por snapshot roto: `guarico-juan-german-roscio`
- Detalle: BITACORA.md (2026-05-20)

### fix — Municipales 2013: gráficos acumulativos y porcentajes sin ponderar
- Cada corte se calcula con las opiniones acumuladas hasta ese turno (`turno <= corte`); el resultado final sale del acumulado completo
- Porcentajes sin ponderar, nombres de candidatos y categoría Otros consistentes con Gobernadores 2012
- Archivos: `backend/import_2013_municipales.py`, `backend/data/historico_estudios_seed.json`

### refactor — Reorganización de data histórica 2012/2013
- Insumos Excel separados por tipo de elección: `backend/data/2012/{presidenciales,gobernadores}/` y `backend/data/2013/{presidenciales,municipales}/`
- `import_2012_2013.py` actualizado a las subcarpetas e inserta turnos con `ambito='NACIONAL'`

### fix — Seed histórico también en startup.py (sync Azure)
- `startup.py` ejecuta `seed_historico_estudios.py` en cada arranque para garantizar que los cambios del seed JSON lleguen a Azure en cada deploy (ver ADR-010)
- Archivos: `backend/startup.py`

---

## 2026-05-19

### feat — Auditoría estadística rigurosa en tarjetas de estudios históricos

Implementa análisis metodológico completo dentro de cada tarjeta de estudio histórico individual (no un resumen cruzado). Cubre los 4 estudios disponibles: Presidencial 2006, 2012, 2013 y Asamblea Nacional 2010.

#### Nuevo módulo `backend/auditor_sesgo.py`
- Diagnóstico TSE (Total Survey Error) por estudio: no-respuesta diferencial (espiral del silencio), sesgo asimétrico estructural (errores de signo opuesto), DEFF estimado (Kish 1965: ICC=0.04)
- MoE SRSWOR vs MoE ajustado por DEFF por estudio
- Detección automática de patrón histórico esperado (gov subestimado)
- Nivel de riesgo metodológico: bajo / moderado / severo / crítico con puntaje compuesto
- Recomendaciones accionables según nivel de error y disponibilidad de datos

#### `backend/app.py` — ruta `GET /historicos/estudios/{ref}`
- `analisis` enriquecido: `delta_gov`, `delta_opos`, `delta_brecha`, `mae_mosteller` (Medida 3 Mosteller), `errores_opuestos` (flag de sesgo estructural), `rmse_estados`, `bias_std`, `pct_estados_gov_neg`, `ganador_estudio`, `ganador_oficial`, `acierto_ganador`, `magnitud`
- `analisis_leg` para legislativas: `delta_gov_esc`, `delta_opos_esc`, `acierto_mayoria`, `mae_voto_lista`, `capa2` (descomposición Capa 1 + Capa 2)
- Capa 2 (2010): `err_esc_proporcional`, `err_esc_algoritmo`, `factor_amplificacion`, `pct_error_por_algoritmo`
- Badge de sesgo en listado `/historicos`: nivel crítico/alto/moderado por desviación de gov

#### `backend/templates/historico_estudio_detalle.html`
- Panel "Diagnóstico de Sesgo Sistémico (TSE)" con componentes coloreados por probabilidad
- **Presidenciales**: tabla comparativa Proyectado vs Oficial vs Desviación (gov, opos, otros, brecha), KPIs MAE M3 Mosteller + error de brecha + ganador correcto + sesgo estructural, RMSE±σ estadal, % estados con gov subestimado, texto de conclusiones técnico
- **Asamblea 2010**: visualización escaños, tabla voto lista vs oficial, alerta Capa 2 con factor de amplificación del algoritmo electoral, conclusiones Capa 1/Capa 2 diferenciadas

#### `backend/templates/historicos.html`
- Badge de nivel de sesgo (crítico/alto/moderado) en tarjetas con estudio, solo si `sesgo_nivel != 'bajo'`

#### `backend/ai_prompts.py` y `backend/ai_validation.py` — versión 2.4
- Prompt v2.4: cláusula obligatoria de espiral del silencio cuando `SESGO_NO_RESPUESTA_NO_CUANTIFICADO`; cláusula DEFF cuando `MOE_AJUSTADO_POR_DEFF`; prohibición de ajustar porcentajes por sesgo (solo advertir)
- Validación v2.4: flag `SESGO_NO_RESPUESTA_NO_CUANTIFICADO` cuando `tasa_no_respuesta=None`; corrección de MoE con DEFF cuando `design_effect_estimado > 1.0`

#### `backend/calculador_pesos.py`
- Nueva función `diagnosticar_cobertura(id_eleccion)`: compara cobertura muestral vs universo por estado, estima DEFF desde tamaños de clúster, señala estados < 10% como alertas

#### Métricas verificadas para los 4 estudios
| Estudio | MAE M3 | Δ Brecha | Sesgo estructural |
|---|---|---|---|
| Presidencial 2006 | 1.59 pp | +0.31 pp | No |
| Presidencial 2012 | 2.82 pp | −7.52 pp | Sí (errores opuestos) |
| Presidencial 2013 | 4.53 pp | +11.71 pp | Sí (errores opuestos) |
| Asamblea 2010 | MAE voto lista 3.40 pp | — | Capa 2: factor ×1.80, 44.4 % por algoritmo |

### feat — Regionales 2008: colección de 25 exit polls simultáneos

Implementación completa del módulo de Elecciones Regionales 2008 (gobernaciones, Alcaldía Mayor de Caracas, Municipio Libertador, Municipio Maracaibo).

#### Migración de esquema
- `backend/migrate_turnos_ambito.py`: recrea `historico_estudios_turnos` con columna `ambito TEXT NOT NULL DEFAULT 'NACIONAL'`; cambia UNIQUE de `(eleccion_ref, turno)` a `(eleccion_ref, ambito, turno)`; preserva los 43 turnos existentes con `ambito='NACIONAL'`
- `backend/schema.sql` e `backend/init_db.py` actualizados con el mismo cambio
- `backend/seed_historico_estudios.py` y la ruta de guardado en `app.py` actualizados para incluir `ambito` en todos los INSERT de turnos

#### Importación de datos (`backend/import_2008.py`)
- Lee 7 archivos Excel (`*.xlsx`) en `backend/data/2008/`: cada uno contiene múltiples hojas de estados
- `is_graphic_sheet()`: discrimina hojas de datos vs hojas gráficas (`G*`, `C*`) sin filtrar por inicial (fix para Carabobo, Cojedes, Guarico)
- `parse_state_sheet()`: extrae candidatos, centros únicos, conteos acumulados por `(centro, turno)`
- `build_turno_series()`: construye serie cumulativa por turno usando el último reporte disponible por centro (deduplication)
- Categorización política: Chavismo=MVR/PSUV, Oposición=PJ/AD/COPEI/UNT(≥2), Otros=extra-bloque
- Henri Falcón (Lara/PPT): tratado como ambiguo, marcado con `lara_nota` en notas JSON
- OFICIALES: datos Wikipedia/CNE + PDF `resultados-de-las-elecciones-municipales-2004-y-2008.pdf` (Libertador 53.59%/41.39%, Maracaibo 39.71%/59.90%)
- Resultado: 26 filas en `historico_estudios` (25 estados + NACIONAL), 25 en `historico_oficial`, 405 en `historico_estudios_turnos`
- Acertividad: 20/24 ganadores correctos (83.3%); Lara=ambiguo; 4 incorrectos (Miranda, Mérida, Zulia, Libertador)

#### Nuevas rutas (`backend/app.py`)
- `GET /historicos/estudios/2008-gobernadores` → `gobernadores_2008_collection()`: grilla regional de 25 tarjetas + KPIs (613 centros, 140K respondentes, acertividad global), organizadas en 7 regiones
- `GET /historicos/estudios/2008-gobernadores/{estado_slug}` → `gobernadores_2008_detalle()`: candidatos, KPIs, gráfico Plotly de tendencia acumulativa (Plotly dual-axis: % + centros reportados vs turno), DEFF/MoE, análisis de acertividad MAE M3 Mosteller, nota de ambigüedad Lara
- `_historicos_unificados()`: inyección de tarjeta tipo `coleccion` para 2008-gobernadores (evita mostrar `e_gov=0%` en listado principal)

#### Nuevos templates
- `backend/templates/gobernadores_2008.html`: colección con 7 secciones regionales, tarjetas color-coded por ganador estudio (rojo=gov/azul=opos), badges de acierto, barras duales estudio vs oficial, delta badge, DEFF warning si >5
- `backend/templates/gobernador_2008_detalle.html`: candidatos con %, gráfico de tendencia prominente (eje dual %), alertas DEFF, tabla comparativa Estudio/Oficial/Δ, MAE M3, error de brecha, ganador, sesgo estructural, nota Lara cuando aplica
- `backend/templates/historicos.html`: nuevo tipo `coleccion` con tarjeta en violeta (#6f42c1) enlazando a la colección

#### Métricas 2008-gobernadores
| Estado | Est Gov% | Est Opos% | Ofic Gov% | Ofic Opos% | Ganador |
|---|---|---|---|---|---|
| Miranda | 43.0 | 45.0 | 52.7 | 47.3 | ✗ (Cabello→Capriles) |
| Mérida | 46.8 | 48.4 | 47.4 | 52.6 | ✗ (Dávila→Díaz Orellana) |
| Lara | 48.9 | 48.8 | — | — | ? (Falcón/PPT ambiguo) |
| Carabobo | 35.0 | 45.0 | 47.1 | 52.9 | ✓ |
| Capital | 40.8 | 49.0 | 44.1 | 55.9 | ✓ |

- Archivos: `backend/import_2008.py`, `backend/migrate_turnos_ambito.py`, `backend/schema.sql`, `backend/init_db.py`, `backend/seed_historico_estudios.py`, `backend/app.py`, `backend/templates/gobernadores_2008.html`, `backend/templates/gobernador_2008_detalle.html`, `backend/templates/historicos.html`

### feat — Gobernadores 2012: colección de 23 exit polls simultáneos
- `backend/import_2012_gobernadores.py`: 23 estudios paralelos por estado + fila `NACIONAL` de metadatos, desde `CORE4.xlsx` (hoja maestra `Entrada` + 23 hojas estatales agregadas por municipio/segmento, turnos 1–18)
- 24 filas en `historico_estudios`, 23 oficiales (Wikipedia/CNE 2012), 407 turnos con `ambito=slug_estado`
- Rutas `/historicos/estudios/2012-gobernadores` y `/{estado_slug}`; templates `gobernadores_2012.html` y `gobernador_2012_detalle.html`
- Detalle: BITACORA.md (2026-05-19)

---

## 2026-05-18

### feat — Importación Presidencial 2012 y 2013 desde cores Excel

- `import_2012_2013.py`: importa ambas elecciones en una sola ejecución
- 2012 (Chávez vs Capriles, 7-Oct):
  - Estudio: hoja R1 (resultados ponderados por estado, 24 estados) + hoja VZA (13 turnos de tendencia intra-jornada)
  - Oficial: xlsx mesa-a-mesa; gov=chavez, opos=capriles, otros=chirino+sequera+reyes+bolívar+nulos
  - Estudio nacional: Chávez 50.94% / Capriles 47.51% · Oficial: 54.02% / 43.49% · Error −3.08 pp
- 2013 (Maduro vs Capriles, 14-Abr):
  - Estudio: hoja R1 (conteos crudos por estado) + hoja Venezuela (18 turnos, valores incrementales)
  - Oficial: xlsx mesa-a-mesa; gov=maduro, opos=capriles, otros=sequera+bolívar+mora+méndez
  - Estudio nacional: Maduro 55.71% / Capriles 42.16% · Oficial: 50.62% / 49.12% · Error +5.09 pp
- Exterior (cod_edo=99) excluido de ambas importaciones para consistencia con 2006
- Archivos: `backend/import_2012_2013.py`, `backend/data/2012/`, `backend/data/2013/`
- Tests: totales de Entrada verificados contra Venezuela/CORE sheets; exterior depurado manualmente
- Deploy: requiere redeploy; datos sólo en BD local (no se suben archivos Excel a Azure)

### feat — Módulo Estudios Históricos con importación automática desde cores Excel

- Tres tablas nuevas (bloque 9 del schema): `historico_estudios`, `historico_oficial`, `historico_estudios_turnos`
  - `historico_estudios`: resultados finales del exit poll por `eleccion_ref` + `ambito` (NACIONAL o código estado)
  - `historico_oficial`: resultados CNE oficiales, mismo pivote; admite estados sin cobertura del estudio
  - `historico_estudios_turnos`: serie de tiempo intra-jornada (hasta 12 turnos) con % acumulados por turno
  - Upsert por `(eleccion_ref, ambito)` y `(eleccion_ref, turno)` para re-importaciones idempotentes
- Cinco rutas nuevas bajo `/historicos/estudios/*` (insertadas antes del wildcard `/historicos/{ref}` para evitar captura):
  - `GET /historicos/estudios` — índice de estudios con tarjetas de error ± pp
  - `GET /historicos/estudios/nuevo` — formulario de alta vacío
  - `GET /historicos/estudios/{ref}` — detalle con gráfico Plotly, análisis acertividad y tabla por estado
  - `GET /historicos/estudios/{ref}/editar` — formulario de edición con datos pre-poblados
  - `POST /historicos/estudios/guardar` — upsert; valida suma 99.5–100.5% server-side y client-side
- Helper `_estudios_pivot()` usa UNION ALL + GROUP BY (workaround FULL OUTER JOIN no disponible en SQLite)
- Análisis de acertividad calculado en tiempo de respuesta: delta_gov pp, acierto ganador, RMSE por estado
- Navegación: enlace "Estudios" agregado a sidebar desktop y barra móvil (`base.html`)
- Templates nuevos: `historico_estudios.html`, `historico_estudio_editar.html`, `historico_estudio_detalle.html`
- Script `import_2006.py`: carga Presidencial 2006 desde Excel core (`Presentacion Basica Copia5.xls`) y resultados oficiales por mesa (`resultado elecciones presidenciales 2006.xlsx`)
  - Estudio: agrega hoja Entrada (datos increméntales por turno y centro) → 22 estados + NACIONAL · 225 centros
  - Turnos: extrae 12 turnos desde hoja Cálculos con % acumulados
  - Oficial: agrega xlsx por estado → 24 estados + NACIONAL · 11.7M votos escrutados
  - Resultado: Chávez 61.06% (estudio) vs 62.10% (oficial) · error −1.04 pp · ganador correcto
- Archivos: `backend/schema.sql`, `backend/init_db.py`, `backend/app.py`, `backend/templates/base.html`, `backend/templates/historico_estudios.html`, `backend/templates/historico_estudio_editar.html`, `backend/templates/historico_estudio_detalle.html`, `backend/import_2006.py`
- Tests: smoke test pasa; datos verificados contra totales del core original (Entrada sum == Cálculos nacional: 9.074/5.194/306/287 votos)
- Deploy: requiere redeploy; la migración `init_db.py` crea las tablas automáticamente si no existen

### feat — Estudio histórico Asamblea Nacional 2010
- `backend/import_2010.py`: lee `R Nominal`, `R Lista`, `R Indigena` y `ENTRADA` de `aplicacion03.xlsm`; importa como `2010-asamblea` con métrica de escaños proyectados (114 gob / 50 opos / 1 otros vs referencia 98/65/2)
- Sin tendencia: el archivo se trata como resultado final del estudio; no se inventan tabulados oficiales por estado
- `historico_estudio_detalle.html` reconoce estudios legislativos: KPI de escaños, gráfico de distribución, comparación por estado vs voto lista oficial
- Detalle: BITACORA.md (2026-05-18)

### feat — Resultado oficial Presidencial 2018 (solo resultados)
- `2018-presidencial` agregado a `historico_estudios_seed.json` dentro de `historico_oficial` (fuente Wikipedia/CNE)
- `_historicos_unificados()` diferencia `con_estudio` de `oficial`; tarjetas sin estudio usan título legible y orden descendente por año
- Detalle: BITACORA.md (2026-05-18)

### fix — Históricos unificados en Azure + seed fijo versionado
- `_historicos_unificados()` como fuente única para `/historicos` y `/historicos/debug-json`; `Cache-Control: no-store`
- Importación pesada de Excel reemplazada por semilla fija versionada: `backend/data/historico_estudios_seed.json` + `backend/seed_historico_estudios.py` (idempotente)
- Rutas de creación/edición de estudios históricos bloqueadas con 404: son datos históricos fijos de solo lectura
- Detalle: BITACORA.md (2026-05-18)

---

## 2026-05-08

### fix — Live dashboard alineado con visualización
- `/live` ahora usa votos reales cuando existen y cae a la misma data de referencia que `/visualizacion` mientras no haya opiniones SMS en `votos`
- `/stream/dashboard` expone `fuente_datos` para distinguir `live` de `dashboard_referencia`
- El panel del analista IA usa el mismo contexto que la vista live, incluyendo nota de fuente cuando opera con referencia
- `generador_dashboard.py` actualiza por SSE la etiqueta de fuente sin recargar la página
- Agregado test para `votos=0` con datos históricos disponibles
- Archivos: `backend/app.py`, `backend/generador_dashboard.py`, `test_flujo.py`, `ESTADO.md`, `CHANGELOG.md`, `BITACORA.md`
- Tests: pytest verde
- Deploy: requiere redeploy

---

## 2026-05-07

### docs — Restructuración documentación de agentes
- Separadas 3 capas en `CLAUDE.md`, `codex.md`, `gemini.md`, `copilot.md`: Project Rules / Role Definition / Active Context
- Creados: `ESTADO.md` (estado vivo), `DECISIONES.md` (ADR), `CHANGELOG.md` (este archivo)
- Archivos: `CLAUDE.md`, `codex.md`, `gemini.md`, `copilot.md`, `ESTADO.md`, `DECISIONES.md`, `CHANGELOG.md`
- Tests: sin cambio (smoke test pasa)
- Deploy: no requiere redeploy

### refactor — Hardening módulo AI de reportes
- Documentado estado inicial del módulo en `AI_MODULE_REVIEW.md` antes de tocar implementación
- Separado prompt v2.3 en `backend/ai_prompts.py`
- Agregado validador estadístico secuencial y adaptador de schema en `backend/ai_validation.py`
- `backend/agent.py` mantiene compatibilidad con `ask_agent`/`ask_structured` y agrega `llm_call(...)` + metadata de trazabilidad
- `ask_agent()` valida suficiencia estadística antes de resolver API key o tocar proveedor remoto
- Alias `google` agregado para reutilizar la configuración Gemini sin cambiar la tabla `config`
- Defaults AI alineados a reportes deterministas (`temperature=0`) y modelos requeridos por proveedor
- Tests nuevos para validación estadística y schema legado
- Archivos: `AI_MODULE_REVIEW.md`, `backend/ai_prompts.py`, `backend/ai_validation.py`, `backend/agent.py`, `backend/app.py`, `backend/templates/config.html`, `test_ai_validation.py`, `.gitignore`
- Tests: pytest verde (7 passed)
- Deploy: requiere redeploy

### test — Dependencias de desarrollo para pytest
- Agregado `requirements-dev.txt` con dependencias backend + `pytest`
- Documentado el harness de tests backend en `ESTADO.md`
- `BUG-001` de agregación regional/municipal movido a resuelto tras verificar la implementación actual
- Archivos: `requirements-dev.txt`, `ESTADO.md`, `CHANGELOG.md`
- Tests: pytest verde
- Deploy: no requiere redeploy

---

## 2026-05-02

### feat — Módulo Históricos
- Rutas: `/historicos`, `/historicos/{ref}`, `/historicos/comparar`, `/historicos/{ref}/mapa`
- Consume `resultados_historicos`, `centros`, `estados` (sin cambio de esquema)
- Archivos: `backend/app.py`, `backend/templates/historicos_*.html`
- Tests: smoke test pasa
- Deploy: sí

### security — Resolución CVEs starlette
- `fastapi==0.136.1`, `starlette==0.49.1`
- Archivos: `backend/requirements.txt`
- Deploy: sí

### feat — Reorden menú y etiquetas móvil
- Sidebar desktop y barra móvil reordenados al flujo operativo
- Archivos: `backend/templates/base.html`
- Deploy: sí

---

## 2026-05-01

### feat — Ingesta IA multi-formato para Tabla de Mesa
- Rutas nuevas: `POST /api/tm/ai-extract`, `POST /api/tm/fuzzy-match`, `POST /api/tm/confirm`
- Extracción cliente: SheetJS, mammoth.js, pdf.js; fallback server-side: pdfplumber, python-docx
- Tablas nuevas: `election_centers`, `tm_ingestion_logs`
- Archivos: `backend/app.py`, `backend/agent.py`, `backend/schema.sql`, `backend/init_db.py`, `backend/templates/tm.html`
- Tests: smoke test pasa
- Deploy: sí

### feat — Guardrails analista con suficiencia por tipo de elección
- Nacional: 100 op/15%/3 cortes · Regional: 60/10%/3 · Municipal: 30/10%/3
- Frase exacta: `datos insuficientes para establecer tendencias`
- Archivos: `backend/analista_ia.py`, `backend/agent.py`, `backend/app.py`

### feat — Formulario candidatos con ámbito electoral completo
- Campos: `id_estado`, `id_municipio`, `id_circuito`, `id_circ_indigena` según tipo de candidato
- Archivos: `backend/templates/candidato_form.html`, `backend/app.py`

### test — Nuevo test_flujo.py sobre BD SQLite temporal
- Simula elección nacional completa con SMS, turnos y verificación de guardrail
- Archivos: `test_flujo.py`

### security — Saneamiento historia Git y hardening .gitignore
- Removido `.env` de commits históricos con `git-filter-repo`
- `OPENAI_API_KEY` migrada a Azure App Settings
- Archivos: `.gitignore`, `SECURITY.md`

---

## 2026-04-30

### feat — SSE live dashboard sin recarga
- `GET /stream/dashboard` emite `geo` + `series` cada 60s
- Removido `meta refresh` de `/live`
- Archivos: `backend/app.py`, `backend/generador_dashboard.py`

### feat — Multi-proveedor IA (agent.py)
- Proveedores: OpenAI, Groq, Anthropic, Gemini
- `POST /chat` con streaming
- Tabla `config` en SQLite
- Archivos: `backend/agent.py`, `backend/app.py`, `backend/schema.sql`

### deploy — Azure App Service B1 operativo
- Resuelto CRLF con `startup.py` en lugar de `startup.sh`
- `SCM_DO_BUILD_DURING_DEPLOYMENT=0`
- Archivos: `backend/startup.py`

---

## 2026-04-28 (estimado)

### feat — Seed histórico presidencial 2006
- 11.118 centros, 33.002 mesas, 580 reportes de campo
- Tablas nuevas: `resultados_mesa`, `reportes_campo`, vistas `v_proyeccion`, `v_evaluacion`
- Archivos: `backend/seed_2006.py`, `backend/schema.sql`, `backend/data/2006/`

---

<!--
PLANTILLA PARA NUEVAS ENTRADAS (copiar, rellenar y agregar bajo [Unreleased] antes del commit)

### [tipo] — [descripción breve en español]
- [detalle del cambio]
- Archivos: [lista separada por comas]
- Tests: [pytest verde / nuevo test / sin cambio]
- Deploy: [sí / no aplica / requiere redeploy]
-->
