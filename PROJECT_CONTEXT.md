# PROJECT_CONTEXT.md — Exit Poll Venezuela

> Fuente de verdad para todos los agentes de IA que trabajan en este proyecto.
> Leer este archivo **antes de cualquier acción** en el repositorio.
> Estado vivo: ESTADO.md · Decisiones con rationale: DECISIONES.md · Historial de commits: CHANGELOG.md

---

## Entorno

| Parámetro | Valor |
|-----------|-------|
| Repo | `https://github.com/caprileshj-hub/exit-poll.git` · Rama principal: `main` |
| Local | Windows 11 / PowerShell. Pavilion: proyectos en `D:\Test`. Lenovo: proyectos en `C:\Proyects`. |
| venv | Python 3.12. Nunca 3.14. Pavilion: `D:\Test\.venv`. Lenovo: `C:\Proyects\exit-poll\venv`. |
| Deploy | Azure App Service B1 (1 core / 1.75 GB RAM), eastus · Always On activo |
| BD | SQLite WAL · `backend/exitpoll.db` |
| URL producción | `https://exit-poll-ve-hqfch0gvfzekeqck.eastus-01.azurewebsites.net` |

### Comandos esenciales

```powershell
# Tests
& 'D:\Test\.venv\Scripts\pytest.exe' -q

# Instalar dependencias (ambos requirements.txt)
& 'D:\Test\.venv\Scripts\pip.exe' install -r requirements.txt -r backend\requirements.txt pytest

# Dry-run seed histórico
& 'D:\Test\.venv\Scripts\python.exe' backend\seed_2006.py --dry-run

# Backend local
& 'D:\Test\.venv\Scripts\uvicorn.exe' app:app --reload --app-dir backend
```

---

## Flujo operativo del dominio

1. **Selección de muestra** — 2 centros por estado. Excepciones con granularidad de parroquia: Distrito Capital, La Guaira, 4 municipios de Miranda que forman Caracas (Chacao, Baruta, El Hatillo, Sucre).
2. **Campo** — Encuestador en centro. Votante selecciona candidato. Mínimo 15 encuestas / 30 min. Encuestador totaliza y llama al centro cada turno.
3. **Transcripción** — SMS → gateway Android → FastAPI.
4. **Core** — `calculador_pesos.py` + `procesador_datos.py`.
5. **Visualización** — Heatmap + gráficos de tendencia + dashboard para clientes.

**Propósito real**: Informar movilización política durante la jornada, NO predecir el ganador. El trabajo real termina a las 11am. Comparar contra resultado CNE no es métrica válida de precisión.

---

## Arquitectura SMS (decisión fija)

```
[APK Android] → SMS → [Gateway Android] → HTTP POST → [FastAPI] → [SQLite WAL] → [Dashboard]
```

**Formato SMS** (< 40 chars): `C1234;V2;T1932;L09a7F3b`

| Campo | Descripción |
|-------|-------------|
| `C` | Código CNE del centro |
| `V` | Candidato (V0 = nulo) |
| `T` | Timestamp local HHMM |
| `L` | GPS como Geohash 6 chars (~38m de precisión) |

El número de teléfono del encuestador es su ID — no viaja en el SMS.

### Parámetros operativos (no cambiar sin consenso)

| Parámetro | Valor |
|-----------|-------|
| Techo votos/turno | 25 (fraude si supera) |
| Piso votos/turno | 8 (alerta inactividad) |
| Duración turno | 20 min (interno, invisible para encuestadores y clientes) |
| Radio GPS validez | 300m defecto, configurable por centro (`centros.radio_m`) |

---

## Reglas de diseño no negociables

1. **TM sin sobrescritura**: `lat`, `lon`, `riesgo`, `radio_m` en `centros` son datos operativos verificados en campo. Jamás se sobrescriben desde un archivo CNE. Usar `COALESCE` en todos los upserts.
2. **Guardrail analista** — frase exacta si datos insuficientes: `datos insuficientes para establecer tendencias`. No parafrasear, no suavizar.
3. **IA centralizada**: único proveedor configurado en `/config` · tabla SQLite `config`. Sin endpoints ni API keys separadas por módulo.
4. **APK nativa, no PWA**: SMS en background requiere Android nativo (Kotlin/Java). Las PWA no tienen acceso a `SEND_SMS` en background.
5. **GPS requerimiento duro**: distancia Haversine entre Geohash decodificado del SMS y `centros.lat/lon` debe ser < `radio_m`. Si no → `valid=false`. El voto se guarda en `sms_raw` para auditoría pero no totaliza.
6. **Centros ausentes en TM no se eliminan**: sin fila en `election_centers` para esa elección, pero el registro en `centros` permanece.
7. **Clientes no ven auditoría**: semáforo de centros, panel encuestadores, alertas de fraude son acceso interno exclusivo — nunca en el dashboard de clientes.
8. **Sin credenciales en código**: API keys solo en Azure App Settings o tabla SQLite `config`. `.env`, `*.db`, `*.sqlite`, `config.ini` en `.gitignore`. Nunca en respuestas JSON al navegador.

### Reglas de ingesta TM

- Dos caminos: determinístico legacy (`convertidor_tm.py` + `cargador_tm.py`) para formatos 2015/2018; asistido por IA (`/tm`) para formatos nuevos o variables.
- Filas ambiguas o con CONFLICT bloquean confirmación hasta resolverse manualmente.
- Fuzzy matching: MATCHED ≥ 0.88 · AMBIGUOUS 0.72–0.88 · NEW < 0.72.
- Nunca sobrescribir, nunca eliminar centros — solo actualizar mesas/electores.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12, FastAPI, Jinja2 |
| BD | SQLite (WAL + FK) · `backend/exitpoll.db` |
| Visualización | Folium, Plotly, Bootstrap 5 |
| Procesamiento | pandas, openpyxl, pdfplumber, python-docx |
| IA | `backend/agent.py` — OpenAI, Anthropic, Groq, Gemini |
| Móvil (pendiente) | APK Android nativa (repo separado) |
| Deploy | Azure App Service B1, eastus |

### Archivos clave del backend

| Archivo | Rol |
|---------|-----|
| `backend/app.py` | FastAPI: dashboard config, live view, endpoints TM/IA |
| `backend/schema.sql` | Esquema SQLite |
| `backend/init_db.py` | Init y migraciones ligeras |
| `backend/agent.py` | Abstracción proveedores IA |
| `backend/analista_ia.py` | Analista determinístico con guardrails |
| `backend/calculador_pesos.py` | Ponderación jerárquica 4 niveles |
| `backend/selector_muestra.py` | Selección de muestra con filtro elegibilidad |
| `backend/cargador_tm.py` | Cargador diferencial TM |
| `backend/convertidor_tm.py` | Conversor determinístico 2015/2018 |
| `backend/generador_heatmap.py` | Choropleth Folium ADM1/ADM2 |
| `backend/generador_dashboard.py` | HTML autónomo: mapa + tendencias |
| `backend/seed_2006.py` | Carga histórica presidencial 2006 |
| `backend/TM_ESTANDAR.md` | Spec del CSV interno (15 columnas) |

---

## Deploy en Azure

- Artefacto: solo `backend/` como raíz → `git archive HEAD:backend > backend_deploy.zip`
- Startup: `python /home/site/wwwroot/startup.py` → `uvicorn app:app` (no `startup.sh` — CRLF issues)
- `OPENAI_API_KEY` en Azure App Settings (no en código)
- `SCM_DO_BUILD_DURING_DEPLOYMENT=0` (Oryx desactivado)
- Si 0 centros al arrancar → `init_showcase.py` se ejecuta automáticamente
- Si cold start: verificar Always On activo en Portal → Configuration → General settings
- Geojson ADM1/ADM2 en `backend/` (no en raíz) para que estén en el artefacto

---

## Preferencias de colaboración

- Documentar y responder en **español** para este repo.
- "arréglalo" / "dale" → proceder sin otra ronda de permiso.
- "súbelo" → commitear y pushear después de validar.
- Bugs pendientes → anotar en `ESTADO.md` sección Pendientes.
- Comportamiento cambiado importante → sincronizar `README.md`.
- Antes de `git pull`: verificar que no haya cambios sin commitear.
- Suite de tests: `test_flujo.py`, `test_ai_validation.py`, `test_cargador_tm.py`, `test_geo_pesos.py` (20 tests al 2026-06-10). Correr pytest desde la raíz del proyecto. Verde no garantiza funcionalidad FastAPI completa.
- Para cambios de esquema o seed: `--dry-run` primero.

---

## Estado vivo del proyecto

| Documento | Contenido |
|-----------|-----------|
| `ESTADO.md` | Qué funciona, qué está pendiente, bugs conocidos |
| `DECISIONES.md` | Decisiones arquitectónicas con rationale (ADRs) |
| `CHANGELOG.md` | Historial de cambios por sesión (más reciente arriba) |
| `BITACORA.md` | Historial narrativo de desarrollo; los agentes pueden agregar sesiones con formato `## AAAA-MM-DD — Tema` |
| `METODOLOGIA_ESTADISTICA.md` | Marco estadístico de estudios históricos y analista IA |
| `SECURITY.md` | Auditoría de seguridad 2026-05-01 y riesgos aceptados (en inglés) |
| `README.md` / `README.es.md` | Cara pública del repo (inglés/español, enlazados) |
