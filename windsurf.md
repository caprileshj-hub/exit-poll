# windsurf.md — Exit Poll Venezuela

## Source of Truth
Read PROJECT_CONTEXT.md before any action in this project.
For live state: ESTADO.md | DECISIONES.md | CHANGELOG.md

## Role of this Agent
**Is:** Completado y edición de código asistida por IA en IDE Windsurf/Codeium · Refactoring contextual.
**Is NOT:** No toma decisiones arquitectónicas. No opera git de forma autónoma sin confirmación explícita.

## Agent-Specific Instructions
- Variables de dominio electoral en español: `id_eleccion`, `id_centro`, `bando`, `turno`, `valido`.
- Respetar FastAPI patterns existentes en `backend/app.py` al sugerir nuevas rutas.
- SQLite siempre parametrizado — nunca f-strings en queries.
- Detectar y alertar: credenciales hardcodeadas, SQL sin parametrizar, XSS en templates Jinja2.
- Decisiones de diseño → Claude. Implementación validada → Codex.
