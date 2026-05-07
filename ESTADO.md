# ESTADO.md — Exit Poll Venezuela

> Estado actual del proyecto: qué funciona, qué está pendiente, qué bugs hay abiertos.
> Actualizar al cierre de cada sesión de trabajo significativa.
> Última actualización: 2026-05-07

---

## Resumen ejecutivo

Sistema de exit poll electoral venezolano en producción activa en Azure. Fases 1–6 completas. Fase 7 en curso: hardening ingesta IA TM, APK Android (repo separado), cobertura de tests, auditoría interna.

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

### Visualización
- [x] Heatmap Folium ADM1/ADM2 (`generador_heatmap.py`)
- [x] Dashboard HTML autónomo: mapa 58% + tendencias Plotly 42% (`generador_dashboard.py`)
- [x] SSE live dashboard (`/stream/dashboard`) — sin meta refresh
- [x] Módulo Históricos: `/historicos`, `/historicos/{ref}`, `/historicos/comparar`, `/historicos/{ref}/mapa`

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
- [ ] **Cobertura de tests backend**
  - Rutas FastAPI críticas: `/candidatos`, `/pesos`, `/visualizacion`, `/tm`
  - `calcular_resultado_ponderado()` en `simulador_showcase.py`
  - Calculador pesos por tipo de elección (regional, municipal, asamblea)

### Media prioridad
- [ ] **Dashboard auditoría interna**: semáforo centros, panel encuestadores, alertas fraude (acceso interno exclusivo)
- [ ] **Gráficos torta/barras** para clientes
- [ ] **Cola/background jobs** para ingesta de múltiples PDFs grandes
- [ ] **Hardening UX ingesta IA TM**: resolución manual para cargas grandes, progreso SSE por lote

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

### BUG-001: Agregación incorrecta en simulador regional/municipal
- **Archivo**: `backend/simulador_showcase.py` · función `calcular_resultado_ponderado()`
- **Síntoma**: En ramas `regional` y `municipal`, asignaciones tipo `resultado[id_cand] = ...` dentro de loops por estado/municipio. El último sobrescribe los anteriores.
- **Impacto**: Porcentajes finales incorrectos para elecciones no nacionales.
- **Acción**: Definir si retorna agregado global o desglosado por ámbito; ajustar estructura de retorno y su consumidor en consola/dashboard.

### BUG-002: UI candidatos — show/hide de campos por tipo no cubre todos los casos
- **Archivos**: `backend/templates/candidato_form.html`, `backend/app.py`
- **Síntoma**: El formulario persiste `id_estado`, `id_municipio`, `id_circuito`, `id_circ_indigena` correctamente, pero la lógica JS de show/hide puede no cubrir todas las combinaciones tipo_candidato × tipo_eleccion.
- **Impacto**: Candidatos `lista`, `nominal`, `indigena` pueden quedar sin su geografía correctamente asociada.
- **Acción**: Revisar JS del formulario; agregar validación server-side por combinación.

---

## Referencias
- Historial narrativo de desarrollo → `BITACORA.md`
- Decisiones arquitectónicas con rationale → `DECISIONES.md`
- Changelog de commits → `CHANGELOG.md`
