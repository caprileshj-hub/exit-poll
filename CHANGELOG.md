# CHANGELOG.md — Exit Poll Venezuela

> Mantenido por Codex en cada sesión de implementación. No editar manualmente.
> Tipos: `feat` · `fix` · `refactor` · `test` · `docs` · `deploy` · `security`

---

## [Unreleased]

<!-- Codex: agregar aquí los cambios del próximo commit antes de pushear -->

### refactor — Hardening modulo AI de reportes
- Documentado estado inicial del modulo en `AI_MODULE_REVIEW.md` antes de tocar implementacion
- Separado prompt v2.3 en `backend/ai_prompts.py`
- Agregado validador estadistico secuencial y adaptador de schema en `backend/ai_validation.py`
- `backend/agent.py` mantiene compatibilidad con `ask_agent`/`ask_structured` y agrega `llm_call(...)` + metadata de trazabilidad
- `ask_agent()` valida suficiencia estadistica antes de resolver API key o tocar proveedor remoto
- Alias `google` agregado para reutilizar la configuracion Gemini sin cambiar la tabla `config`
- Defaults AI alineados a reportes deterministas (`temperature=0`) y modelos requeridos por proveedor
- Tests nuevos para validacion estadistica y schema legado
- Archivos: `AI_MODULE_REVIEW.md`, `backend/ai_prompts.py`, `backend/ai_validation.py`, `backend/agent.py`, `backend/app.py`, `backend/templates/config.html`, `test_ai_validation.py`, `.gitignore`
- Tests: `venv\Scripts\python.exe -m pytest -q test_flujo.py test_ai_validation.py --basetemp .pytest_ai_tmp3 -p no:cacheprovider` → 7 passed
- Deploy: requiere redeploy para activar cambios AI en Azure

### test — Dependencias de desarrollo para pytest
- Agregado `requirements-dev.txt` con dependencias backend + `pytest`
- Documentado el harness de tests backend en `ESTADO.md`
- `BUG-001` de agregación regional/municipal movido a resuelto tras verificar la implementación actual
- Archivos: `requirements-dev.txt`, `ESTADO.md`, `CHANGELOG.md`
- Tests: `venv\Scripts\python.exe -m pytest -q test_flujo.py --basetemp .pytest_tmp3 -p no:cacheprovider` → 1 passed
- Deploy: no requiere redeploy

---

## 2026-05-07

### docs — Restructuración documentación de agentes
- Separadas 3 capas en `CLAUDE.md`, `codex.md`, `gemini.md`, `copilot.md`: Project Rules / Role Definition / Active Context
- Creados: `ESTADO.md` (estado vivo), `DECISIONES.md` (ADR), `CHANGELOG.md` (este archivo)
- Archivos: `CLAUDE.md`, `codex.md`, `gemini.md`, `copilot.md`, `ESTADO.md`, `DECISIONES.md`, `CHANGELOG.md`
- Tests: sin cambio (smoke test pasa)
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
PLANTILLA PARA NUEVAS ENTRADAS (Codex: copiar, rellenar y mover a [Unreleased] antes del commit)

## YYYY-MM-DD

### [tipo] — [descripción breve en español]
- [detalle del cambio]
- Archivos: [lista separada por comas]
- Tests: [pytest verde / nuevo test / sin cambio]
- Deploy: [sí / no aplica / requiere redeploy]
-->
