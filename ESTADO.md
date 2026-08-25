# ESTADO.md — Exit Poll Venezuela

> Estado actual del proyecto: qué funciona, qué está pendiente, qué bugs hay abiertos.
> Actualizar al cierre de cada sesión de trabajo significativa.
> Última actualización: 2026-08-25 (selector longitudinal experimental)

---

## Resumen ejecutivo

Sistema de exit poll electoral venezolano en producción activa en Azure. Fases 1–6 completas. Fase 7 en curso: hardening ingesta IA TM, APK Android (repo separado), cobertura de tests, auditoría interna. Módulo de Históricos opera con resultados normalizados por centro/mesa desde 2004 e incorpora VENPRES-A 2018 como dataset granular provisional.

---

## Sistema en producción

| Parámetro | Valor |
|-----------|-------|
| URL | `https://exit-poll-ve-hqfch0gvfzekeqck.eastus-01.azurewebsites.net` |
| Dominio | `estacomp.systems` |
| Plan Azure | B1 Basic (1 core / 1.75 GB RAM), Always On activo |
| Startup | `python /home/site/wwwroot/startup.py` → `uvicorn app:app` |
| BD | SQLite WAL · `backend/exitpoll.db` |
| Deploy | GitHub Actions en push a `main` (`.github/workflows/master_exit-poll-ve.yml`): empaqueta `backend/` como raíz, instala deps en `.python_packages` y despliega con publish profile |
| Versión desplegada | `GET /version` → `commit` + `built_at`, y badge en el navbar |

### Verificaciones última sesión de rendimiento (2026-08-23)

Medido contra producción tras desplegar los arreglos de rendimiento:

| Ruta | Antes | Después |
|------|-------|---------|
| `GET /` con un `/live` en vuelo | 9.0 s | **0.33 s** |
| `/live` | 6.3-6.6 s | **0.86 s** |
| `/pesos` | 1.14 s | **0.28 s** |
| `/config` | 500 a los ~5 s | **200**, 0.2-0.9 s |
| `/muestra` | 500 a los ~5 s | **200** (lento, ver Pendiente) |
| `/` (control) | 0.16 s | 0.17 s |

- `/config` verificado 14 veces seguidas durante deploy y reinicio, incluida la ventana del seed: todas 200, cero `database is locked` en el log.
- `/version` devuelve `commit` y `built_at`; el sha coincide con el del commit desplegado.
- `pytest -q` → 24 tests en verde.

---

## Completado (Fases 1–7 parcial)

### Infraestructura y datos
- [x] BD SQLite completa: WAL, FK, 19+ tablas en 8 bloques funcionales
- [x] Migración incremental en `init_db.py` (sin `--reset` necesario para nuevas tablas)
- [x] Integración CNE 2024: 11.927 centros en `resultados_historicos`
- [x] Normalización histórica 2004+: campos aditivos para electores, votantes, válidos, nulos, exterior, fuente/corte y mesas cubiertas sin romper el contrato legado
- [x] VENPRES-A 2018: 14.400 centros, 33.716 mesas y trazabilidad DOI `10.7910/DVN/NO1XJ2` en `resultados_historicos`
- [x] Seed histórico 2006: 11.118 centros, 33.002 mesas, 580 reportes de campo

### Pipeline de ingesta TM
- [x] Convertidor determinístico para formatos 2015/2018 (`convertidor_tm.py`)
- [x] Cargador diferencial (`cargador_tm.py`): actualiza mesas/electores, nunca sobrescribe GPS/riesgo
- [x] Ingesta IA multi-formato (`/tm` AI path): PDF, XLSX, XLS, XLSM, CSV, DOCX, TXT
- [x] Fuzzy matching centros: `difflib` · MATCHED ≥ 0.88 · AMBIGUOUS 0.72–0.88 · NEW < 0.72
- [x] Confirmación de carga con transacción `BEGIN IMMEDIATE`
- [x] Chunking 15k chars, `response_format=json_object`, `asyncio.to_thread` para no bloquear event loop

### Lógica de negocio
- [x] Selector de muestra con elegibilidad por elección (`selector_muestra.py`)
- [x] Metodologia productiva V1 documentada: seleccion aleatoria estratificada
  por estado, reproducible por seed, sin uso de historicos para inclusion
  (decision metodologica; implementacion productiva en cambio separado)
- [x] Calculador pesos jerárquico 4 niveles con excepciones DC/La Guaira/Miranda-Caracas
- [x] Analista IA determinístico con guardrails (`analista_ia.py`)
- [x] Abstracción multi-proveedor: OpenAI, Anthropic, Groq, Gemini (`agent.py`)
- [x] Suficiencia por tipo de elección: Nacional (100 op/15%/3 cortes), Regional (60/10%/3), Municipal (30/10%/3)
- [x] Hardening AI reportes v2.3: prompt separado, validación estadística previa, metadata de trazabilidad y adaptador de schema legado

### Visualización
- [x] Heatmap Folium ADM1/ADM2 (`generador_heatmap.py`)
- [x] Dashboard HTML autónomo: mapa 58% + tendencias Plotly 42% (`generador_dashboard.py`)
- [x] SSE live dashboard (`/stream/dashboard`) — sin meta refresh; `/live` usa votos reales cuando existen y cae a la misma referencia del dashboard mientras no haya opiniones SMS
- [x] Módulo Históricos: `/historicos`, `/historicos/{ref}`, `/historicos/comparar`, `/historicos/{ref}/mapa`
- [x] Módulo Estudios Históricos: `/historicos/estudios`, detalle con Plotly, edición manual, análisis acertividad
  - Tablas: `historico_estudios`, `historico_oficial`, `historico_estudios_turnos` (bloque 9 schema)
  - Importador `import_2006.py`: Presidencial 2006 — 22 estados, 12 turnos, 24 estados oficial
  - Error nacional −1.04 pp (Chávez 61.06% vs 62.10% oficial); ganador correcto
  - **Auditoría estadística por tarjeta** (2026-05-19): MAE Mosteller M3, error de brecha, sesgo estructural, RMSE±σ estadal, panel TSE, Capa 1+2 para legislativo 2010
  - `auditor_sesgo.py`: DEFF (Kish ICC=0.04), espiral del silencio, nivel de riesgo metodológico
  - AI v2.4: `SESGO_NO_RESPUESTA_NO_CUANTIFICADO`, corrección MoE por DEFF, prompt con cláusulas de sesgo

### Dashboard de configuración FastAPI
- [x] Gestión de elecciones y candidatos (con fotos, ámbito geográfico, circuitos)
- [x] Muestra: generador automático + aplicar
- [x] Documentacion consolidada de muestreo en `docs/muestreo/`: metodologia
  productiva, historial experimental, resultados de backtest y decisiones
- [x] Backtest legacy nacional aislado (`2013_2018` y `2018_2024`) con D'Hondt
  de 72 adicionales, comparador size-only, sensibilidad parametrica y
  artefactos reproducibles en `docs/muestreo/`
- [x] Comparacion reproducible de similitudes legacy (`winner_share`, `top2_gap`,
  `full_profile`) sin modificar el selector productivo ni las cuotas legacy
- [x] Backtest longitudinal de representatividad historica por centro con
  residuales centro-estado, cohortes common/operational y persistencia entre
  presidenciales 2006, 2012, 2013, 2018 y 2024
- [x] Ronda final de falsificacion longitudinal documentada: persistencia
  within-state, oracle diagnostico, survivorship/linking y turnout, sin cambiar
  el selector productivo moderno
- [x] Selector longitudinal experimental `longitudinal_mae_v1` implementado en
  modulo separado para presidencial nacional futura, con N=120, 2 por entidad +
  72 D'Hondt, sin modificar `METODO_PRODUCTIVO`
- [x] Pesos: edición inline masiva
- [x] TM: carga legacy + carga IA multi-formato con preview MATCHED/NEW/AMBIGUOUS/CONFLICT
- [x] Ficha técnica estilo CIS (imprimible, error muestral calculado)
- [x] Configuración proveedor IA con test de conexión

### Seguridad y deploy
- [x] CVEs starlette resueltos: `fastapi==0.136.1`, `starlette==0.49.1`
- [x] Historia Git saneada (API key OpenAI removida con `git-filter-repo`)
- [x] `OPENAI_API_KEY` en Azure App Settings (no en código)
- [x] HTTPS Only + TLS 1.2 mínimo en Azure

---

## Pendiente (Fase 7)

### Alta prioridad
- [ ] **Parser SMS + validación GPS** en `backend/app.py`
  - Recibir POST del gateway Android
  - Parsear formato `C;V;T;L`
  - Validar Haversine < `radio_m` del centro registrado
  - Insertar en `sms_raw` y `votos` con `valid` y `turno` calculado
- [x] **Harness de tests backend**
  - Dependencias de desarrollo documentadas en `requirements-dev.txt`
  - `test_flujo.py` ejecutable con pytest sobre SQLite temporal
- [ ] **Ampliar cobertura de tests backend** (20 tests al 2026-06-10: `test_flujo`, `test_ai_validation`, `test_cargador_tm`, `test_geo_pesos`)
  - Rutas FastAPI críticas: `/candidatos`, `/pesos`, `/visualizacion`, `/tm`
  - `calcular_resultado_ponderado()` en `simulador_showcase.py`
  - Calculador pesos por tipo de elección (asamblea pendiente; regional cubierto en `test_geo_pesos`)
- [ ] **Normalizar estudios históricos y fichas** contra la nueva referencia oficial estandarizada
  - Distinguir NULL/no disponible de cero
  - Recalcular fichas contra `resultados_historicos` normalizado
  - Mantener estudios de exit poll separados de resultados electorales oficiales

- [ ] **`/muestra` tarda 23-27 s en Azure** (~4 s en SSD local)
  - Perfilado con cProfile: 2.65 s de los ~4 s locales son `statistics._ss` (29.646 llamadas)
  - El módulo `statistics` usa `Fraction` para aritmética exacta; el perfil lo dominan `fractions.py` y 946.338 llamadas a `math.gcd`
  - Recalcula sobre las 91.429 filas de `resultados_historicos` en cada petición
  - Acción: sustituir por cálculo en float (o pandas, ya es dependencia) y cachear los agregados por centro
- [ ] **9 rutas POST siguen en `async def` con trabajo bloqueante** (`/muestra/aplicar`, `/chat`, `/api/tm/*`, `/historicos/estudios/guardar`)
  - Hacen `await request.form()` y después trabajo síncrono, así que no se convierten con un cambio de firma
  - Acción: mover el cuerpo a `asyncio.to_thread` una por una (ver ADR-014)
  - Impacto acotado: son rutas de operador, no el dashboard que auto-refresca

### Media prioridad
- [ ] **Dashboard auditoría interna**: semáforo centros, panel encuestadores, alertas fraude (acceso interno exclusivo)
- [ ] **Gráficos torta/barras** para clientes
- [ ] **Cola/background jobs** para ingesta de múltiples PDFs grandes
- [ ] **Hardening UX ingesta IA TM**: resolución manual para cargas grandes, progreso SSE por lote
- [ ] **Schema AI v2.3 completo desde backend**: hoy el adaptador cubre faltantes; falta emitir nativamente `cortes_demograficos`, `motivadores_voto`, `ponderacion_activa`, `design_effect` y `tasa_no_respuesta`

### Fuera de scope web actual (repos separados)
- [ ] APK Android (repo a crear)
- [ ] Gateway Android (repo a crear)

### Pendiente manual en GitHub UI
- [ ] Activar branch protection en `main` (mínimo 1 review antes de merge)
- [ ] Activar Dependabot alerts
- [ ] Activar secret scanning + push protection
- [ ] Configurar CodeQL en push a `main`

---

## Bugs conocidos

### BUG-001: UI candidatos — show/hide de campos por tipo no cubre todos los casos
- **Archivos**: `backend/templates/candidato_form.html`, `backend/app.py`
- **Síntoma**: El formulario persiste `id_estado`, `id_municipio`, `id_circuito`, `id_circ_indigena` correctamente, pero la lógica JS de show/hide puede no cubrir todas las combinaciones tipo_candidato × tipo_eleccion.
- **Impacto**: Candidatos `lista`, `nominal`, `indigena` pueden quedar sin su geografía correctamente asociada.
- **Acción**: Revisar JS del formulario; agregar validación server-side por combinación.

### BUG-002: Error muestral de /ficha usa electores en vez de entrevistas
- **Archivo**: `backend/app.py` · ruta `/ficha`
- **Síntoma**: La fórmula del margen de error usa como *n* los electores de los centros de la muestra (~cientos de miles), no las entrevistas esperadas.
- **Impacto**: La ficha técnica estilo CIS muestra un MoE irrealmente pequeño.
- **Acción**: Decidir el *n* correcto (¿entrevistas planificadas por centro × centros? ¿campo configurable?) antes de corregir la fórmula.

## Bugs resueltos

### RESUELTO (2026-08-23): App serializada — una petición pesada congelaba todo
- **Archivos**: `backend/app.py`, `backend/generador_dashboard.py`, `backend/generador_heatmap.py`
- **Síntoma**: `GET /` pasaba de 0.16 s a 9.0 s mientras una sola petición a `/live` estaba en vuelo.
- **Resolución**: 50 rutas `async def` que solo hacen I/O síncrono pasan a `def` (threadpool); el generador SSE usa `asyncio.to_thread`; `/live` cachea su HTML por huella de contenido. Ver ADR-014.

### RESUELTO (2026-08-23): 500 "database is locked" en /config y /muestra
- **Archivos**: `backend/seed_resultados_historicos.py`, `backend/app.py`, `backend/muestra_lab.py`
- **Síntoma**: Ambas rutas devolvían 500 tras exactamente ~5 s (timeout por defecto de sqlite3), y se "curaban solas" pasado un rato.
- **Resolución**: El seed histórico mantenía una transacción de escritura abierta ~34 s en cada arranque mientras dos rutas GET necesitaban el lock para servirse. El seed ahora se salta si las fuentes no cambiaron, y el trabajo idempotente de bootstrap se hace una vez en el startup en lugar de en cada GET. Ver ADR-015.

### RESUELTO (2026-08-23): /version y el badge mostraban el nombre del sitio, no el commit
- **Archivos**: `.github/workflows/master_exit-poll-ve.yml`, `backend/app.py`, `backend/templates/base.html`
- **Síntoma**: El badge del navbar mostraba `exit-poll-ve` desde `f6fe39c`; nunca llegó a mostrar un sha.
- **Resolución**: `WEBSITE_DEPLOYMENT_ID` vale el nombre del sitio y cortocircuitaba la detección; el workflow nunca puso las otras env vars y el `.git` no se despliega. Ahora el workflow escribe `deploy_root/VERSION` con el sha y la fecha de build.


### RESUELTO (2026-06-10): Dashboard de referencia mezclaba elecciones distintas
- **Archivos**: `backend/app.py` · funciones de ventaja y `_total_referencia_dashboard`
- **Resolución**: Nuevo helper `_eleccion_ref_referencia()`; todas las funciones de referencia filtran por la `eleccion_ref` más reciente. Antes sumaban 2006 + 2024 (ventaja nacional −3.7 pp en vez de −36.8 pp) y los LEFT JOIN duplicaban filas por centro con dos refs.

### RESUELTO (2026-06-10): Carga TM parcial desactivaba centros de todo el país
- **Archivo**: `backend/cargador_tm.py`
- **Resolución**: La desactivación de centros ausentes del CSV se acota a los estados que el CSV cubre, igual que el path de ingesta IA.

### RESUELTO (2026-06-10): Pesos excluían centros sin municipio; geografía duplicada entre ingestas
- **Archivos**: `backend/calculador_pesos.py`, `backend/app.py`
- **Resolución**: LEFT JOIN a municipios con aviso (centros sin geografía agrupan como unidad propia); `_geo_match_name()` unifica el matching de nombres CNE crudos vs nombres de la ingesta IA.

### RESUELTO: Agregación incorrecta en simulador regional/municipal
- **Archivo**: `backend/simulador_showcase.py` · función `calcular_resultado_ponderado()`
- **Resolución**: Las ramas `regional` y `municipal` ahora retornan resultados anidados por ámbito (`id_estado` o `id_municipio`) y evitan sobrescribir resultados de ámbitos anteriores.

---

## Referencias
- Historial narrativo de desarrollo → `BITACORA.md`
- Decisiones arquitectónicas con rationale → `DECISIONES.md`
- Changelog de commits → `CHANGELOG.md`
