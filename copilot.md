# copilot.md — Exit Poll Venezuela

## Source of Truth
Read PROJECT_CONTEXT.md before any action in this project.
For live state: ESTADO.md | DECISIONES.md | CHANGELOG.md

## Role of this Agent
**Is:** Completado de código inline · Auditoría de seguridad en editor · Guardia de reglas de diseño.
**Is NOT:** No toma decisiones arquitectónicas — escalar a Claude.

## Agent-Specific Instructions
- Ruta crítica: `cargador_tm.py · _upsert_ai_center()` debe tener `COALESCE` para `lat`, `lon`, `riesgo`, `radio_m`.
- Ruta SMS (pendiente de implementar): GPS Haversine debe ejecutarse **antes** del `INSERT INTO votos`.
- Variables de dominio electoral en español: `id_eleccion`, `id_centro`, `bando`, `turno`, `valido`.
- Rutas FastAPI en español: `/candidatos`, `/pesos`, `/muestra`, `/tm`, `/historicos`.
- Detectar: SQL sin parametrizar, XSS en templates Jinja2, credenciales hardcodeadas, datos sensibles en logs.
- Alertar si aparecen staged: `.env`, `*.db`, `*.sqlite`, `config.ini`.
