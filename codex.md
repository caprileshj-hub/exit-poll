# codex.md — Exit Poll Venezuela

## Source of Truth
Read PROJECT_CONTEXT.md before any action in this project.
For live state: ESTADO.md | DECISIONES.md | CHANGELOG.md

## Role of this Agent
**Is:** Implementación autónoma · Git · Tests · Deploy · Mantenimiento de CHANGELOG.
**Is NOT:** No toma decisiones arquitectónicas. Escala a Claude si hay duda de diseño.

## Agent-Specific Instructions
- Si el usuario menciona cambios recientes: `git pull --ff-only origin main` antes de analizar.
- Flujo estándar: pull → implementar → `pytest -q` + `py_compile` → dry-run si BD → commit → push → CHANGELOG.
- Validar antes de commitear: `git diff --check && git status --short --branch`.
- No commitear `.env`, `*.db`, `*.sqlite` — están en `.gitignore`.
- Mensajes de commit en español, descriptivos.
- Bugs que quedan pendientes → registrar en `ESTADO.md` sección Pendientes.
