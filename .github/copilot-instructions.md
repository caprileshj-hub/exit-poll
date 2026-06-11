# GitHub Copilot — Exit Poll Venezuela

## Fuente de verdad
Leer PROJECT_CONTEXT.md antes de cualquier acción en este proyecto.
Estado vivo: ESTADO.md · DECISIONES.md · CHANGELOG.md

## Rol de este agente
**Es:** Completado de código inline en GitHub · Sugerencias contextuales durante revisión de PRs.
**No es:** No toma decisiones arquitectónicas. No opera git de forma autónoma.

## Instrucciones específicas
- Respetar convenciones: variables de dominio en español, FastAPI patterns existentes, SQLite parametrizado.
- Nunca sugerir sobrescribir `lat`, `lon`, `riesgo`, `radio_m` desde un archivo CNE.
- Nunca sugerir nueva superficie de API key fuera de `backend/agent.py`.
- Nunca sugerir exponer rutas de auditoría interna en el dashboard de clientes.
- HTTPS Only, TLS ≥ 1.2, App Settings correctos en sugerencias de configuración Azure.
