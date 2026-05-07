# cursor.md — Exit Poll Venezuela

## Source of Truth
Read PROJECT_CONTEXT.md before any action in this project.
For live state: ESTADO.md | DECISIONES.md | CHANGELOG.md

## Role of this Agent
**Is:** Edición de código asistida por IA en IDE · Refactoring multi-archivo · Navegación contextual del codebase.
**Is NOT:** No toma decisiones arquitectónicas. No opera git de forma autónoma sin confirmación explícita.

## Agent-Specific Instructions
- Variables de dominio electoral en español: `id_eleccion`, `id_centro`, `bando`, `turno`, `valido`.
- Respetar FastAPI patterns existentes en `backend/app.py` al sugerir nuevas rutas.
- SQLite siempre parametrizado — nunca f-strings en queries.
- Para cambios de esquema: coordinar con Claude antes de implementar.
- No modificar `BITACORA.md`, `ESTADO.md`, `DECISIONES.md`, `CHANGELOG.md` directamente.
