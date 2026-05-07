# CLAUDE.md — Exit Poll Venezuela

> Contexto para Claude Code. Integra reglas del proyecto (comunes a todos los agentes), el rol específico de Claude, y el contexto activo de la sesión.
> El `README.md` es documentación pública. Este archivo es la memoria de trabajo de Claude.

---

## Capa 1 — Reglas del Proyecto

> Reglas invariantes comunes a todos los agentes. No cambiar sin consenso explícito.

### Entorno
- Repo: `https://github.com/caprileshj-hub/exit-poll.git` · Rama: `main`
- Local (Windows 11, PowerShell): `D:\Test\exit_poll` (no confundir con `D:\Test` — hay varios proyectos hermanos)
- venv: `D:\Test\.venv` — Python 3.12 (nunca 3.14)
- Deploy: Azure App Service B1, eastus

### Comandos esenciales
```powershell
& 'D:\Test\.venv\Scripts\pytest.exe' -q
& 'D:\Test\.venv\Scripts\python.exe' backend\seed_2006.py --dry-run
& 'D:\Test\.venv\Scripts\uvicorn.exe' app:app --reload --app-dir backend
```

### Arquitectura SMS (decisión fija)
```
[APK Android] → SMS → [Gateway Android] → HTTP POST → [FastAPI] → [SQLite WAL] → [Dashboard]
```
Formato: `C1234;V2;T1932;L09a7F3b` (~28 chars)
`C`=código CNE · `V`=candidato (V0=nulo) · `T`=HHMM · `L`=Geohash 6 chars (~38m)
El número de teléfono del encuestador es su ID — no viaja en el SMS.

### Parámetros operativos (no cambiar sin consenso)
| Parámetro | Valor |
|-----------|-------|
| Techo votos/turno | 25 (fraude si supera) |
| Piso votos/turno | 8 (alerta inactividad) |
| Duración turno | 20 min (interno, invisible) |
| Radio GPS validez | 300m defecto, configurable por centro |

### Reglas de diseño no negociables
1. **TM sin sobrescritura**: `lat`, `lon`, `riesgo`, `radio_m` son datos operativos. Jamás se sobrescriben desde un archivo CNE.
2. **Guardrail analista**: frase exacta si no hay suficientes datos: `datos insuficientes para establecer tendencias`
3. **IA centralizada**: único proveedor en `/config`. Sin endpoints ni API keys separadas por módulo.
4. **APK nativa**: SMS en background requiere Android nativo (Kotlin/Java). No PWA.
5. **GPS requerimiento duro**: Haversine < `radio_m`; si no, `valid=false`, no totaliza.
6. **Centros ausentes en TM no se eliminan**: sin `election_centers` para esa elección, pero el centro permanece.
7. **Clientes no ven auditoría**: semáforo de centros, panel encuestadores, alertas de fraude — acceso interno exclusivo.
8. **Propósito del exit poll**: informar movilización política durante la jornada. No predecir ganador. El trabajo real termina a las 11am. Comparar contra resultado CNE no es métrica válida de precisión.

### Stack
| Capa | Tech |
|------|------|
| Backend | Python 3.12, FastAPI, Jinja2 |
| BD | SQLite (WAL + FK) · `backend/exitpoll.db` |
| Visualización | Folium, Plotly, Bootstrap 5 |
| Procesamiento | pandas, openpyxl, pdfplumber, python-docx |
| IA | `backend/agent.py` — OpenAI, Anthropic, Groq, Gemini |
| Deploy | Azure App Service B1, eastus |

---

## Capa 2 — Rol de Claude en el Stack Multi-Agente

**Claude = Arquitectura + Auditoría técnica + Orquestación**

En este proyecto operan cuatro agentes con roles complementarios:
- **Claude** (este archivo): decisiones arquitectónicas, auditoría, prompt engineering, orquestación del resto.
- **Codex** (`codex.md`): implementación autónoma, git, tests, deploy, CHANGELOG.
- **Gemini** (`gemini.md`): revisión de arquitectura pública, análisis de superficie de vulnerabilidades.
- **Copilot** (`copilot.md`): completado de código inline, auditoría de seguridad en editor, Azure config.

### Responsabilidades exclusivas de Claude
- Definir contratos entre módulos y evaluar trade-offs arquitectónicos.
- Revisar y aprobar cambios de esquema antes de que Codex los implemente.
- Diseñar y refinar prompts del analista IA y del flujo de ingesta TM.
- Mantener `CLAUDE.md`, `ESTADO.md` y `DECISIONES.md` sincronizados.
- **No ejecuta git directamente** — eso es responsabilidad de Codex.

### Directivas operativas
- Responder y documentar en **español**.
- "arréglalo" o "dale" → proceder sin otra ronda de permiso.
- "súbelo" → coordinar con Codex para commitear y pushear.
- Bugs pendientes → anotar en `ESTADO.md` sección Pendientes.
- Comportamiento cambiado → sincronizar `README.md`.
- Antes de `git pull`: verificar que no haya cambios sin commitear.
- `test_flujo.py` es smoke test legacy; un pytest verde no garantiza funcionalidad FastAPI real.
- Para cambios de esquema o seed: `--dry-run` primero.

---

## Capa 3 — Contexto Activo

> Actualizar al inicio y cierre de cada sesión significativa.
> Estado completo → `ESTADO.md` · Decisiones con rationale → `DECISIONES.md` · Changelog → `CHANGELOG.md`

**Fase activa**: Fase 7 — Hardening ingesta IA TM, APK Android, auditoría interna, cobertura tests.

**Últimas decisiones implementadas relevantes para Claude**:
- Guardrail `datos insuficientes para establecer tendencias` activo en `analista_ia.py`, `agent.py`, `/chat`.
- Ingesta IA TM: chunking 15k chars, `response_format=json_object`, `asyncio.to_thread` aplicado.
- Matching: `difflib.SequenceMatcher` · MATCHED ≥ 0.88 · AMBIGUOUS 0.72–0.88 · NEW < 0.72.
- CVEs starlette resueltos: `fastapi==0.136.1`, `starlette==0.49.1`.
- Formulario candidatos extendido: `id_estado`, `id_municipio`, `id_circuito`, `id_circ_indigena`.
- Módulo Históricos: `/historicos`, `/historicos/{ref}`, `/historicos/comparar`, `/historicos/{ref}/mapa`.

**Pendiente de decisión arquitectónica (Claude debe resolver)**:
- [ ] Cola/background jobs para ingesta de múltiples PDFs — Celery vs. asyncio Queue vs. thread pool.
- [ ] RapidFuzz vs. difflib cuando el volumen escale — costo de dependencia vs. calidad de matching.
- [ ] Diseño de vista de auditoría interna: semáforo centros, panel encuestadores, alertas fraude.
- [ ] Estrategia distribución APK Android (sideload directo, Play Store interno, MDM).
- [ ] SQLite WAL bajo carga del día de elección — ¿suficiente o migrar a PostgreSQL?
