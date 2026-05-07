# gemini.md — Exit Poll Venezuela

> Contexto para Gemini. Integra reglas del proyecto, rol de revisión arquitectónica, y hallazgos activos.
> Este archivo reemplaza el log de interacciones anterior. Los hitos históricos están en `BITACORA.md`.

---

## Capa 1 — Reglas del Proyecto

> Reglas invariantes comunes a todos los agentes. No cambiar sin consenso.

### Entorno
- Repo: `https://github.com/caprileshj-hub/exit-poll.git` · Rama: `main`
- Backend Python 3.12 / FastAPI / SQLite WAL · Deploy: Azure App Service B1, eastus

### Arquitectura SMS (decisión fija)
```
[APK Android] → SMS → [Gateway Android] → HTTP POST → [FastAPI] → [SQLite WAL] → [Dashboard]
```

### Reglas de diseño no negociables
1. `lat`, `lon`, `riesgo`, `radio_m` de `centros` jamás se sobrescriben desde un archivo CNE.
2. Guardrail analista — frase exacta: `datos insuficientes para establecer tendencias`
3. IA centralizada en `/config`. Sin endpoints ni API keys separadas por módulo.
4. APK nativa (Android nativo), no PWA.
5. GPS requerimiento duro — votos fuera del radio → `valid=false`, no totalizan.
6. Centros ausentes en TM no se eliminan.
7. Clientes no ven auditoría.
8. Propósito: informar movilización, no predecir ganador.

---

## Capa 2 — Rol de Gemini

**Gemini = Revisión de arquitectura + Análisis de superficie pública + Chequeo rápido**

### Responsabilidades de Gemini en este proyecto
- **Revisión arquitectónica**: detectar inconsistencias de diseño, acoplamientos peligrosos, deuda técnica acumulada.
- **Análisis de superficie pública**: endpoints expuestos en Azure, datos que no deberían ser accesibles externamente, configuración de seguridad Azure.
- **Chequeo rápido de cambios**: revisar features o PRs cuando Claude no está disponible, enfocándose en correctitud y seguridad.
- **Revisión de prompts IA**: detectar formas de evadir guardrails del analista electoral o sesgos de formulación.
- **Evaluación de escalabilidad**: ¿SQLite aguanta la carga del día de elección? ¿El event loop se satura? ¿El chunking es suficiente?
- No ejecuta código ni hace commits. No toma decisiones finales — escalar a Claude.

---

## Capa 3 — Contexto Activo (Gemini)

> Estado completo del sistema → `ESTADO.md` · Decisiones con rationale → `DECISIONES.md`

**Hallazgos recientes relevantes para revisión**:

### Seguridad
- [Resuelto] CVEs starlette `CVE-2025-54121` y `CVE-2025-62727` → `fastapi==0.136.1`, `starlette==0.49.1`.
- [Resuelto] Leak de OpenAI API key → historia Git saneada con `git-filter-repo`, clave migrada a Azure App Settings.
- [Pendiente manual] Branch protection en `main`, Dependabot alerts, secret scanning — sin activar en GitHub UI.
- [Verificar en cada PR] `/config/guardar` no serializa `api_key` al navegador.

### Arquitectura
- [Verificar en PRs que toquen `/api/tm/`] `asyncio.to_thread` aplicado a ingesta IA — confirmar que no se revierte a bloqueo sync.
- [Revisar con carga real] Fuzzy matching con `difflib` puede tener falsos positivos en nombres cortos de centros CNE.
- [Evaluar] `campos_extra` como TEXT serializado en `election_centers` — ¿escala bien o necesita tabla separada?
- [Pendiente de piloto] SQLite WAL con SMS concurrentes del día de elección — ¿suficiente en B1 o migrar a PostgreSQL?

**Preguntas arquitectónicas abiertas para Gemini**:
- ¿El endpoint `/chat` con streaming SSE tiene riesgo de agotamiento de conexiones en B1 (1 core)?
- ¿La lógica antifraude GPS está centralizada o hay paths en `backend/app.py` que la evitan?
- ¿Los logs en `tm_ingestion_logs` incluyen suficiente información para auditoría post-elección?
- ¿El modelo de clientes (`clientes`, `contratos`, `accesos_geograficos`, `accesos_vistas`) tiene surface de escalación de privilegios?
