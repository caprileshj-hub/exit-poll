# GitHub Copilot — Exit Poll Venezuela

## Source of Truth
Read PROJECT_CONTEXT.md before any action in this project.
For live state: ESTADO.md | DECISIONES.md | CHANGELOG.md

## Role of this Agent
**Is:** Completado de código inline en GitHub · Sugerencias contextuales durante revisión de PRs.
**Is NOT:** No toma decisiones arquitectónicas. No opera git de forma autónoma.

## Agent-Specific Instructions
- Respetar convenciones: variables de dominio en español, FastAPI patterns existentes, SQLite parametrizado.
- Nunca sugerir sobrescribir `lat`, `lon`, `riesgo`, `radio_m` desde un archivo CNE.
- Nunca sugerir nueva superficie de API key fuera de `backend/agent.py`.
- Nunca sugerir exponer rutas de auditoría interna en el dashboard de clientes.
- HTTPS Only, TLS ≥ 1.2, App Settings correctos en sugerencias de configuración Azure.
