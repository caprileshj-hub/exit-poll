# AGENTS.md — Exit Poll Venezuela

## Fuente de verdad
Leer PROJECT_CONTEXT.md antes de cualquier acción en este proyecto.
Estado vivo: ESTADO.md · DECISIONES.md · CHANGELOG.md

## Rol de este agente
**Es:** Implementación autónoma · Git · Tests · Deploy · Mantenimiento de CHANGELOG.
**No es:** No toma decisiones arquitectónicas. Escala a Claude si hay duda de diseño.

## Instrucciones específicas
- Si el usuario menciona cambios recientes: `git pull --ff-only origin main` antes de analizar.
- Flujo estándar: pull → implementar → `pytest -q` + `py_compile` → dry-run si BD → commit → push → CHANGELOG.
- Validar antes de commitear: `git diff --check && git status --short --branch`.
- No commitear `.env`, `*.db`, `*.sqlite` — están en `.gitignore`.
- Mensajes de commit en español, descriptivos.
- Bugs que quedan pendientes → registrar en `ESTADO.md` sección Pendientes.
