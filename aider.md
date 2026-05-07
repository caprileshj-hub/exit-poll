# aider.md — Exit Poll Venezuela

## Source of Truth
Read PROJECT_CONTEXT.md before any action in this project.
For live state: ESTADO.md | DECISIONES.md | CHANGELOG.md

## Role of this Agent
**Is:** Agente de coding en terminal · Edición multi-archivo asistida · Refactoring automatizado con git.
**Is NOT:** No toma decisiones arquitectónicas unilateralmente. No hace commits de cambios de esquema sin dry-run previo.

## Agent-Specific Instructions
- Iniciar sesión con `aider --read PROJECT_CONTEXT.md` para cargar el contexto del proyecto.
- Para cambios de BD o seed: ejecutar `--dry-run` primero, confirmar con el usuario antes de aplicar.
- No activar auto-commit en cambios de esquema o seed sin confirmación explícita.
- Mensajes de commit en español, descriptivos.
- Bugs que quedan pendientes → registrar en `ESTADO.md` sección Pendientes.
- No modificar `BITACORA.md`, `ESTADO.md`, `DECISIONES.md`, `CHANGELOG.md` directamente.
