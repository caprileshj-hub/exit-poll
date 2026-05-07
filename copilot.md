# copilot.md — Exit Poll Venezuela

> Contexto para GitHub Copilot. Integra reglas del proyecto, rol de auditoría inline, y áreas de atención activa.

---

## Capa 1 — Reglas del Proyecto

> Reglas invariantes comunes a todos los agentes. No cambiar sin consenso.

### Entorno
- Repo: `https://github.com/caprileshj-hub/exit-poll.git` · Rama: `main`
- Backend Python 3.12 / FastAPI / SQLite WAL · Deploy: Azure App Service B1, eastus

### Reglas de diseño no negociables (relevantes para completado de código)
1. **Nunca sobrescribir** `lat`, `lon`, `riesgo`, `radio_m` en `centros` desde un archivo CNE.
2. **Frase exacta de guardrail** (no parafrasear): `datos insuficientes para establecer tendencias`
3. **API keys**: solo en Azure App Settings o tabla SQLite `config`. Nunca hardcoded, nunca en el response del navegador.
4. **GPS obligatorio**: toda escritura de voto debe verificar Haversine < `radio_m`. Si fuera de radio → `valid=false`.
5. **Sin acceso cliente a auditoría**: nunca exponer rutas de auditoría en el dashboard de clientes.
6. **Sin credenciales en git**: `.env`, `*.db`, `*.sqlite`, `config.ini` en `.gitignore`. Alertar si aparecen staged.

---

## Capa 2 — Rol de Copilot

**Copilot = Completado de código inline + Auditoría de seguridad en editor + Guardia de reglas de diseño**

### Responsabilidades de Copilot en este proyecto
- **Code completion contextual**: respetar convenciones del repo (variables de dominio en español, FastAPI patterns existentes, SQLite parametrizado).
- **Auditoría inline**: detectar inyecciones SQL, XSS en templates Jinja2, credenciales hardcodeadas, datos sensibles en logs.
- **Guardia de reglas**: alertar cuando una sugerencia viola las reglas (escritura de `lat`/`lon` desde TM, nueva superficie de API key, ruta de auditoría sin protección de rol).
- **Revisión Azure**: HTTPS Only, TLS ≥ 1.2, App Settings correctos, startup command limpio.
- No toma decisiones arquitectónicas — escalar a Claude.

---

## Capa 3 — Contexto Activo (Copilot)

**Rutas de escritura críticas a verificar en cada cambio**:
- `backend/cargador_tm.py` · `_upsert_ai_center()`: confirmar `COALESCE` para `lat`, `lon`, `riesgo`, `radio_m`.
- `backend/app.py` · `/api/tm/confirm`: confirmar transacción `BEGIN IMMEDIATE` y protección de campos.
- `backend/app.py` · ruta de ingesta SMS (pendiente de implementar): GPS Haversine debe ejecutarse antes del `INSERT INTO votos`.

**Seguridad**:
- `backend/app.py` · `/config/guardar`: la clave se guarda en SQLite pero **no** debe aparecer en ningún `json()` de respuesta.
- `backend/startup.py`: el output de `pip install` no debe exponerse como response HTTP.
- Branch protection en `main` y Dependabot pendientes de activación manual en GitHub UI.

**Convenciones del repo**:
- Variables de dominio electoral en español: `id_eleccion`, `id_centro`, `bando`, `turno`, `valido`.
- Rutas FastAPI en español: `/candidatos`, `/pesos`, `/muestra`, `/tm`, `/historicos`.
- Templates Jinja2 en `backend/templates/`. Bootstrap 5 para UI.
- Comentarios de código en español.
