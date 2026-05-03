# CLAUDE.md — Exit Poll Venezuela

Archivo de contexto para Claude Code. Cubre el dominio operativo, decisiones de arquitectura, estado actual y preferencias de colaboración. El `README.md` es documentación pública; este archivo es la memoria de trabajo.

---

## Repo y entorno

- Repo activo: `D:\Test\exit_poll` (no confundir con `D:\Test`, que tiene varios proyectos hermanos).
- Rama principal: `main`. Remoto: `https://github.com/caprileshj-hub/exit-poll.git`.
- Shell: PowerShell en Windows 11. Entorno virtual en `D:\Test\.venv` (Python 3.12 — evitar 3.14).
- Comandos clave:

```powershell
# Tests
& 'D:\Test\.venv\Scripts\pytest.exe' -q

# Dry-run del seed histórico
& 'D:\Test\.venv\Scripts\python.exe' backend\seed_2006.py --dry-run

# Levantar backend local
& 'D:\Test\.venv\Scripts\uvicorn.exe' app:app --reload --app-dir backend
```

- Dependencias: hay `requirements.txt` en la raíz y otro en `backend/`. Instalar ambos al reconstruir el venv.

---

## Flujo operativo original (dominio)

El sistema reemplaza un proceso manual de exit poll electoral venezolano:

1. **Selección de muestra** — 2 centros por estado. Excepciones con granularidad de parroquia: Distrito Capital, La Guaira, y 4 municipios de Miranda que forman parte de Caracas (Chacao, Baruta, El Hatillo, Sucre).
2. **Campo** — Encuestador en el centro. Votante selecciona candidato. Mínimo 15 encuestas cada 30 min. Encuestador totaliza y llama al centro de totalización cada turno.
3. **Transcripción** — Antes: papeleta → Access. Ahora: SMS → gateway Android → FastAPI.
4. **Core** — Antes: Excel con pesos y jerarquía. Ahora: `calculador_pesos.py` + `procesador_datos.py`.
5. **Visualización** — Heatmap + gráficos de tendencia + dashboard para clientes.

**Propósito real del exit poll:** NO es predecir el ganador. Es dar información a los actores políticos para movilizar maquinaria durante la jornada. El trabajo real termina a las 11am. Se continúa hasta las 4-5pm por los clientes. Comparar con el resultado CNE (a las 6pm) no es una métrica válida de precisión.

---

## Arquitectura SMS (decisión fija)

La señal de datos celular en Venezuela es mala en campo. SMS es el único canal confiable.

```
[APK Android] → SMS → [Gateway Android dedicado] → HTTP POST → [FastAPI] → [SQLite] → [Dashboard]
```

### Formato SMS (< 40 chars)

```
C1234;V2;T1932;L09a7F3b
```

| Campo | Descripción |
|-------|-------------|
| `C`   | Código CNE del centro |
| `V`   | Candidato (V0 = nulo) |
| `T`   | Timestamp local HHMM |
| `L`   | GPS como Geohash (~38m, 6 chars) |

El número del teléfono del encuestador es su ID — nunca viaja en el SMS.

### Parámetros operativos (no cambiar sin consenso)

- Techo de votos por turno: **25** (fraude si se supera)
- Piso de votos por turno: **8** (alerta de inactividad)
- Duración del turno: **20 minutos** (interno, invisible para encuestadores y clientes)
- Radio GPS de validez: **300 metros** por defecto, configurable por centro

### Anti-fraude GPS

Si las coordenadas del SMS caen fuera del radio del centro → `valid=false`, no agrega. El votante no puede reportar desde su casa.

---

## Tabla de Mesa (TM) — reglas de ingesta

La TM es el insumo fundacional (centros, mesas, electores, geografía). El CNE la cambia de formato en cada ciclo. Hay dos caminos:

1. **Determinístico legacy** (`convertidor_tm.py` + `cargador_tm.py`) — formatos conocidos 2015/2018.
2. **Asistido por IA** (`/tm` en la app) — multi-formato; usa el proveedor configurado en `/config`.

**Reglas invariables en TM:**
- Nunca sobrescribir `lat`, `lon`, `riesgo`, ni `radio_m` desde un archivo CNE.
- Centros ausentes en una nueva TM no se borran ni se marcan inactivos.
- Filas ambiguas o con conflicto bloquean la confirmación hasta resolverse.
- La IA usa el proveedor de `/config`; no crear superficie separada de API keys.

---

## Arquitectura actual

### Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12, FastAPI, Jinja2 |
| BD | SQLite (WAL mode, foreign keys) |
| Visualización | Folium, Plotly, Bootstrap 5 |
| Procesamiento | pandas, openpyxl, pdfplumber, python-docx |
| IA | Abstracción multi-proveedor (`agent.py`) — OpenAI, Anthropic, Groq, Gemini |
| Móvil (pendiente) | APK Android nativo (no PWA — SMS en background) |
| Deploy | Azure App Service B1, eastus |

### Archivos clave

| Archivo | Rol |
|---------|-----|
| `backend/app.py` | FastAPI: dashboard config, live view, endpoints TM/IA |
| `backend/schema.sql` | Esquema SQLite |
| `backend/init_db.py` | Init y migraciones ligeras |
| `backend/agent.py` | Abstracción proveedores IA |
| `backend/analista_ia.py` | Analista determinístico con guardrails |
| `backend/calculador_pesos.py` | Ponderación jerárquica 4 niveles |
| `backend/selector_muestra.py` | Selección de muestra con filtro de elegibilidad |
| `backend/cargador_tm.py` | Cargador diferencial TM |
| `backend/convertidor_tm.py` | Conversor determinístico 2015/2018 |
| `backend/generador_heatmap.py` | Choropleth Folium ADM1/ADM2 |
| `backend/generador_dashboard.py` | HTML autónomo: mapa + tendencias |
| `backend/seed_2006.py` | Carga histórica presidencial 2006 |
| `backend/TM_ESTANDAR.md` | Spec del CSV interno (15 columnas) |
| `BITACORA.md` | Historial de fases y pendientes |

### BD — grupos de tablas

| Grupo | Tablas |
|-------|--------|
| Geografía | `estados`, `municipios`, `parroquias`, `circuitos`, `circunscripciones_indigenas` |
| Centros | `centros`, `election_centers`, `tm_ingestion_logs` |
| Elecciones | `elecciones`, `candidatos` |
| Muestra | `muestra`, `pesos`, `centros_candidatos` |
| Encuestadores | `encuestadores` |
| Votos | `sms_raw`, `votos` |
| Histórico | `resultados_historicos`, `resultados_mesa`, `reportes_campo` |
| Auditoría | `alertas` |
| Clientes | `clientes`, `contratos`, `accesos_geograficos`, `accesos_vistas` |

---

## Estado actual (al 2026-05-02)

App en producción: `https://exit-poll-ve-hqfch0gvfzekeqck.eastus-01.azurewebsites.net`

**Azure:** Plan B1 (1 core / 1.75 GB RAM). Always On activado. Solo `backend/` se empaqueta como raíz del artefacto. Startup: `bash /home/site/wwwroot/startup.sh`.

### Completado (Fases 1–7 parcial)

- BD SQLite completa con WAL, foreign keys, modelo de clientes y auditoría
- Pipeline de ingesta TM: determinístico (2015/2018) + IA multi-formato
- Selector de muestra con elegibilidad por elección
- Calculador de pesos jerárquico 4 niveles con excepciones DC/La Guaira/Miranda-Caracas
- Generador de heatmap Folium ADM1/ADM2
- Dashboard HTML autónomo (mapa 58% + tendencias Plotly 42%)
- Dashboard FastAPI de configuración (elecciones, candidatos, muestra, pesos, TM, demo, live view)
- Integración datos CNE 2024 (11.927 centros en `resultados_historicos`)
- Analista IA determinístico con guardrails; frase exacta requerida: `datos insuficientes para establecer tendencias`
- Seed histórico 2006 (11.118 centros, 33.002 mesas, 580 reportes de campo)

### Pendiente (Fase 7)

- Hardening de ingesta IA de TM: UX para archivos grandes, rate limits, resolución manual, fuzzy matching
- Parser SMS + validación GPS en FastAPI
- APK Android (UI encuestador + SMS + cola offline)
- Gateway Android (lector SMS → HTTP POST)
- Dashboard de auditoría interna (estado de centros, panel encuestadores, alertas de fraude)
- Gráficos para clientes (torta, barras)
- Ampliar cobertura de tests: rutas FastAPI, carga TM, muestra, pesos, analista

---

## Reglas de diseño (no negociables)

- **TM sin sobrescritura de campo:** `lat`, `lon`, `riesgo`, `radio_m` son datos operativos; nunca vienen de un archivo CNE.
- **Analista con guardrails:** hasta no tener mínimo de opiniones, cobertura y cortes comparables, la frase de bloqueo es exactamente `datos insuficientes para establecer tendencias`.
- **IA centralizada:** un único proveedor configurado en `/config`; no crear endpoints ni claves separadas por módulo.
- **APK nativa, no PWA:** el SMS en background requiere Android nativo (Kotlin/Java). Las PWA no tienen acceso a SMS.
- **GPS como requerimiento duro:** no es opcional; es la principal defensa antifraude operativa.
- **Centros ausentes en TM no se eliminan.**
- **Clientes no ven datos de auditoría:** las vistas internas (encuestadores, alertas, centros) no se exponen al cliente.

---

## Deploy en Azure

- Artefacto: solo `backend/` como raíz (`wwwroot`).
- Oryx detecta `requirements.txt` en wwwroot e instala.
- Startup: `bash /home/site/wwwroot/startup.sh` → `uvicorn app:app`.
- Si hay cold start: verificar que Always On esté activo (Portal → Configuration → General settings).
- Si `startup.sh` detecta 0 centros al arrancar, ejecuta `init_showcase.py` automáticamente.
- Geojson ADM1 y ADM2 están en `backend/` (no en la raíz) para que se incluyan en el artefacto.

---

## Preferencias de colaboración

- Responder y documentar en **español** para este repo.
- Si el usuario dice "arréglalo" o "dale", proceder sin pedir otra ronda de permiso.
- Si dice "súbelo", commitear y pushear después de validar.
- Si quedan bugs pendientes, anotarlos en `BITACORA.md`.
- Si se cambia comportamiento importante, sincronizar `README.md`.
- Antes de hacer `git pull`, verificar que no haya cambios locales sin commitear.
- El test `test_flujo.py` es un smoke test legacy; no confiar en un pytest verde como garantía de funcionalidad real de FastAPI.
- Para cambios de esquema o seed: correr `--dry-run` primero.
