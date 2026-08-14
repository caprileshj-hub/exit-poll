# ESTADO.md — Exit Poll Venezuela

> Estado actual del proyecto: qué funciona, qué está pendiente, qué bugs hay abiertos.
> Actualizar al cierre de cada sesión de trabajo significativa.
> Última actualización: 2026-08-14

---

## Resumen ejecutivo

Sistema de exit poll electoral venezolano en producción activa en Azure. Fases 1–6 completas. Fase 7 en curso: hardening ingesta IA TM, APK Android (repo separado), cobertura de tests, auditoría interna. Módulo de Estudios Históricos implementado con primer dataset cargado (Presidencial 2006). Nuevo: Laboratorio asistido de selección de muestra (`/muestra`) con score v2, en fase de auditoría — un bug de correctitud detectado y pendiente de fix (ver BUG-003).

---

## Sistema en producción

| Parámetro | Valor |
|-----------|-------|
| URL | `https://exit-poll-ve-hqfch0gvfzekeqck.eastus-01.azurewebsites.net` |
| Dominio | `estacomp.systems` |
| Plan Azure | B1 Basic (1 core / 1.75 GB RAM), Always On activo |
| Startup | `python /home/site/wwwroot/startup.py` → `uvicorn app:app` |
| BD | SQLite WAL · `backend/exitpoll.db` |
| Deploy | `git archive HEAD:backend` → `backend_deploy.zip` → `az webapp deploy` |

### Verificaciones última sesión (2026-05-02)
- `GET /config` → 200 OK
- `GET /live` → 200 OK
- SSE `/stream/dashboard` → `{"ok": true, ...}`
- `/chat` con datos insuficientes → `Esa información no está en los datos del exit poll.`
- `POST /config/test` → `{"ok": true, "provider": "openai"}`

---

## Completado (Fases 1–7 parcial)

### Infraestructura y datos
- [x] BD SQLite completa: WAL, FK, 19+ tablas en 8 bloques funcionales
- [x] Migración incremental en `init_db.py` (sin `--reset` necesario para nuevas tablas)
- [x] Integración CNE 2024: 11.927 centros en `resultados_historicos`
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

### Laboratorio de selección de muestra (2026-08-13)
- [x] `backend/muestra_lab.py`: catálogo maestro, score de utilidad, confianza A–D y clasificación de centros (ADR-011, ADR-012)
- [x] `/muestra` rediseñada: subpestañas Laboratorio / Muestra actual, filtros, tabla ordenable con ficha desplegable por centro, tooltips metodológicos
- [x] Contratos aditivos: `historico_fuentes`, `centro_codigos`, `centro_snapshot`, columnas de trazabilidad en `muestra`
- [x] Históricos por centro incorporados desde datos por mesa ya versionados: 2006 (10.936 centros), 2012 (13.818), 2013 (13.850); más 2004-revocatorio (6.265) y 2024 (11.925)
- [x] Score v2: utilidad (50% representatividad relativa + 30% estabilidad relativa robusta MAD + 20% volumen) separada de confianza; shrinkage adaptativo hacia el estrato (`k=1.5`, apagado con `n_eff >= 2.5`)
- [ ] Botón de selección automática bajo score v2 como preselección editable
- [ ] Fase logística posterior a la selección metodológica (accesibilidad, seguridad, cobertura de encuestadores, zonas rurales/fronterizas, sustitutos)
- [ ] Recalibrar tendencias cuando se incorporen nuevos resultados históricos previos
- Detalle: `BITACORA.md` (2026-08-13), `DECISIONES.md` ADR-011/ADR-012

### Dashboard de configuración FastAPI
- [x] Gestión de elecciones y candidatos (con fotos, ámbito geográfico, circuitos)
- [x] Muestra: generador automático + aplicar
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

### BUG-003: Score v2 del laboratorio de muestra trata 0.0 como "sin dato"
- **Archivo**: `backend/muestra_lab.py` · función `construir_laboratorio` (cálculo de `r_score`/`e_score`, líneas ~544-545)
- **Síntoma**: `c["desvio_pp"] or 15.0` y `c["estabilidad_relativa_pp"] or 5.0` tratan `0.0` como valor faltante (falsy en Python), no solo `None`. Mismo patrón que el bug ya corregido en `selector_muestra.py` (`diff_nac` → 999, ver fix 2026-06-10).
- **Impacto**: Un centro perfectamente representativo (`desvio_pp = 0.0`) recibe `r_score = 0.0` (el peor posible en vez del mejor); un centro perfectamente estable (`estabilidad_relativa_pp = 0.0`) recibe `e_score = 0.5` en vez de `1.0`. Verificado con reproducción directa de las expresiones.
- **Acción**: Reemplazar el fallback `or` por chequeo explícito `is None`. En `r_score` el `is not None` externo ya cubre el caso `None`, así que basta usar `c["desvio_pp"]` directo.

## Bugs resueltos

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
