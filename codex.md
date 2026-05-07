# codex.md — Exit Poll Venezuela

> Contexto operativo para Codex. Integra reglas del proyecto, rol de ejecución, y estado activo de implementación.
> Si el usuario dice que subió cambios o pide revisar lo último: `git pull --ff-only origin main` antes de analizar.

---

## Capa 1 — Reglas del Proyecto

> Reglas invariantes comunes a todos los agentes. No cambiar sin consenso.

### Entorno
- Repo: `https://github.com/caprileshj-hub/exit-poll.git` · Rama: `main`
- Local (Windows 11, PowerShell): `D:\Test\exit_poll` (no confundir con `D:\Test` — hay varios proyectos hermanos)
- venv: `D:\Test\.venv` — Python 3.12 (si falla, reconstruir con `python3.12 -m venv`; nunca 3.14)
- Deploy: Azure App Service B1, eastus

### Comandos esenciales
```powershell
& 'D:\Test\.venv\Scripts\pytest.exe' -q
& 'D:\Test\.venv\Scripts\python.exe' backend\seed_2006.py --dry-run
& 'D:\Test\.venv\Scripts\pip.exe' install -r requirements.txt -r backend\requirements.txt pytest
```

### Arquitectura SMS (decisión fija)
```
[APK Android] → SMS → [Gateway Android] → HTTP POST → [FastAPI] → [SQLite WAL] → [Dashboard]
```
Formato: `C1234;V2;T1932;L09a7F3b` · `C`=CNE · `V`=candidato · `T`=HHMM · `L`=Geohash 6 chars

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

## Capa 2 — Rol de Codex

**Codex = Implementación autónoma + Git + Tests + Deploy + CHANGELOG**

### Responsabilidades exclusivas de Codex
- Implementar features y fixes definidos por Claude o el usuario.
- Correr validaciones antes de commitear: `pytest -q` + `python -m py_compile` sobre archivos modificados.
- Gestionar git: stage → commit (mensaje en español, descriptivo) → push.
- **Mantener `CHANGELOG.md` actualizado en cada commit** con fecha, tipo y archivos afectados.
- Operaciones de deploy Azure (empaquetar `backend/` con `git archive HEAD:backend`, `az webapp deploy`).
- No tomar decisiones arquitectónicas por cuenta propia — escalar a Claude si hay duda de diseño.

### Flujo estándar
1. `git pull --ff-only origin main` si el usuario menciona cambios recientes.
2. Implementar el cambio solicitado.
3. Validar: `pytest -q` + `py_compile` de los archivos modificados.
4. Para cambios de BD/seed: `--dry-run` primero, luego aplicar.
5. `git diff --check && git status --short --branch` antes de commitear.
6. Commitear + pushear.
7. Registrar en `CHANGELOG.md`.
8. Si quedan bugs → registrar en `ESTADO.md` sección Pendientes.

### Directivas operativas
- "arréglalo" o "dale" → proceder sin otra ronda de permiso.
- "súbelo" → commitear y pushear después de validar.
- Responder y documentar en **español**.
- `test_flujo.py` es smoke test legacy — pytest verde no garantiza funcionalidad FastAPI completa.
- No commitear `.env`, `*.db`, `*.sqlite` — están en `.gitignore`.
- Antes de editar archivos sensibles, leer contexto cercano.

---

## Capa 3 — Contexto Activo (Codex)

> Estado completo del sistema → `ESTADO.md`

**Fase activa**: Fase 7

**Pendientes de implementación asignados a Codex**:
- [ ] Parser SMS en `backend/app.py`: recibir POST del gateway, parsear `C;V;T;L`, validar Haversine < `radio_m`, insertar `sms_raw` + `votos` con `valid` y `turno`
- [ ] Dashboard auditoría interna: semáforo centros, panel encuestadores, alertas fraude (rutas internas, sin acceso cliente)
- [ ] Gráficos torta/barras para clientes
- [ ] Tests FastAPI: rutas `/candidatos`, `/pesos`, `/visualizacion`, `/tm`
- [ ] Tests `calcular_resultado_ponderado()` en `simulador_showcase.py` para elecciones regionales/municipales
- [ ] Tests calculador pesos por tipo de elección

**Bugs conocidos**:
1. `backend/simulador_showcase.py` · `calcular_resultado_ponderado()` — pisa resultados por estado/municipio en loop (ver BUG-001 en `ESTADO.md`)
2. `backend/templates/candidato_form.html` — lógica JS show/hide de campos por tipo candidato × tipo elección puede tener casos no cubiertos (ver BUG-002 en `ESTADO.md`)

**Último estado validado** (2026-05-02):
- `pytest -q` → 1 passed
- `GET /config` → 200 · `GET /live` → 200 · SSE `/stream/dashboard` → `{"ok": true}`
- Deploy Azure → RuntimeSuccessful, Running

**Estructura deploy Azure**:
- Solo `backend/` como raíz del artefacto: `git archive HEAD:backend > backend_deploy.zip`
- Startup: `python /home/site/wwwroot/startup.py` (no `startup.sh` — CRLF issues)
- `OPENAI_API_KEY` en Azure App Settings, no en código
- `SCM_DO_BUILD_DURING_DEPLOYMENT=0` (Oryx desactivado)
