# DECISIONES.md — Registro de Decisiones Arquitectónicas

> El "qué" está en el código. Este archivo documenta el "por qué".
> Formato ADR simplificado: Decisión · Contexto · Consecuencias · Estado.
> Las decisiones aquí son las que más se han cuestionado o cuya motivación no es obvia desde el código.

---

## ADR-001 — SMS como canal de campo

**Decisión**: El canal de datos entre encuestadores y backend es exclusivamente SMS.

**Contexto**: En las elecciones venezolanas, la señal de datos celular en los centros de votación en campo es mala o inexistente. Las redes 2G/SMS son mucho más confiables que datos móviles en zonas rurales y periurbanas durante jornadas electorales (picos de uso).

**Consecuencias**:
- Payload máximo ≤ 40 chars para evitar fragmentación de SMS.
- APK Android nativa obligatoria — las PWA no tienen acceso a envío de SMS en background.
- Gateway Android dedicado en sala de totalización (WiFi estable + energía continua).
- El número de teléfono del encuestador es su ID: no viaja en el SMS para ahorrar caracteres.
- Modo offline en la APK: encola votos y envía en lote al recuperar señal.

**Estado**: Fija. No cambiar sin evidencia de que la conectividad en campo cambió estructuralmente.

---

## ADR-002 — GPS como requerimiento duro (antifraude primario)

**Decisión**: Votos cuyas coordenadas GPS caigan fuera del radio registrado del centro se almacenan con `valid=false` y no totalizan.

**Contexto**: El riesgo de fraude principal en un exit poll es que un encuestador reporte votos desde su casa u otro lugar. El GPS del teléfono Android es la defensa más efectiva disponible sin infraestructura adicional.

**Consecuencias**:
- Radio configurable por centro (default 300m) en `centros.radio_m`.
- Algoritmo: distancia Haversine entre Geohash decodificado del SMS y `centros.lat`/`centros.lon`.
- `lat`/`lon` son datos operativos verificados en campo — nunca vienen de un archivo CNE.
- El voto se guarda igualmente en `sms_raw` (para auditoría), pero `valid=false` lo excluye de totales.

**Estado**: Fija.

---

## ADR-003 — Geohash 6 chars en SMS (vs. lat/lon decimal)

**Decisión**: Las coordenadas GPS viajan en el SMS como Geohash de 6 caracteres.

**Contexto**: El límite de 40 chars del SMS es estricto. Lat/lon decimal requeriría ≥ 20 chars solo para coordenadas (`-10.48123,-66.90234`). Geohash de 6 chars = ~38m de precisión en 6 caracteres.

**Consecuencias**:
- El backend decodifica el Geohash a lat/lon para el cálculo Haversine.
- Precisión ~38m es suficiente — los centros de votación son edificios, no puntos de 1m².
- El campo `L` en el SMS ocupa exactamente 6 chars, predecible para el parser.

**Estado**: Fija.

---

## ADR-004 — SQLite con WAL (vs. PostgreSQL)

**Decisión**: Motor de base de datos es SQLite en modo WAL con foreign keys activos.

**Contexto**: El sistema opera en Azure App Service B1 (1 core, 1.75 GB). El día de elección tiene SMS entrantes concurrentes pero el volumen es manejable para SQLite WAL (varios cientos de escrituras/hora, no miles/segundo). PostgreSQL añadiría complejidad de gestión de servidor y costo en el plan de estudiante.

**Consecuencias**:
- Archivo único `backend/exitpoll.db` — fácil de respaldar y transportar.
- WAL permite lecturas concurrentes mientras se escribe.
- FK activos garantizan integridad referencial.
- Criterio de escalación: si el piloto en producción muestra errores `database is locked` sostenidos durante la jornada, migrar a PostgreSQL.

**Estado**: Activa. Revisar después del primer piloto en jornada real.

---

## ADR-005 — IA centralizada en /config (sin endpoints separados por módulo)

**Decisión**: Todos los módulos que necesitan IA usan el mismo proveedor configurado en `/config` y la misma tabla SQLite `config`.

**Contexto**: Tener múltiples superficies de API keys (una por módulo — una para el analista, otra para la ingesta TM, otra para el chat) es un vector de seguridad y un problema de gestión. Un operador configura una vez el proveedor para toda la app.

**Consecuencias**:
- `backend/agent.py` es la única abstracción de proveedores IA.
- Cambiar de proveedor (OpenAI → Gemini) se hace en un solo lugar.
- No crear nuevos imports de SDKs IA fuera de `agent.py`.

**Estado**: Fija.

---

## ADR-006 — Propósito del exit poll (impacto en diseño del analista y la muestra)

**Decisión**: El exit poll sirve para informar movilización política durante la jornada, no para predecir el ganador.

**Contexto**: Los clientes son actores políticos que necesitan saber si están ganando o perdiendo en ciertos estados/municipios para mover recursos humanos durante el día. El trabajo real termina a las 11am. Comparar la proyección contra el resultado CNE (publicado a las 6pm) no es una métrica válida de precisión del sistema.

**Consecuencias**:
- El analista IA enfatiza tendencias e información accionable, no declaraciones de ganador.
- El guardrail existe porque declarar ganador con 30 opiniones es contraproducente para el cliente.
- El diseño muestral prioriza centros "swing" y "bisagra" — los que dan información de movilización.
- El dashboard muestra tendencias en tiempo real, no proyección final.

**Estado**: Fija. Define la filosofía del analista y el diseño muestral.

---

## ADR-007 — TM sin sobrescritura de datos operativos

**Decisión**: Al cargar una nueva Tabla de Mesa del CNE, los campos `lat`, `lon`, `riesgo`, `radio_m` de `centros` jamás se sobrescriben.

**Contexto**: El CNE provee coordenadas oficiales, pero las coordenadas operativas son las verificadas en campo por el equipo (más precisas para validación GPS). `riesgo` y `radio_m` son asignaciones operativas que no existen en los archivos CNE.

**Consecuencias**:
- `cargador_tm.py` usa `COALESCE` para estos campos.
- `_upsert_ai_center()` en `/api/tm/confirm` respeta la misma regla.
- Centros ausentes en un TM nuevo no se eliminan: simplemente no tienen fila en `election_centers` para esa elección.
- Si se carga un TM que incluye coordenadas CNE incorrectas, el sistema las ignora silenciosamente.

**Estado**: Fija.

---

## ADR-008 — difflib vs. RapidFuzz para fuzzy matching de centros (provisional)

**Decisión inicial**: `difflib.SequenceMatcher` de stdlib para el primer piloto.

**Contexto**: RapidFuzz tiene mejor rendimiento y precisión pero requiere compilación (extensión C). difflib está en stdlib, cero dependencias extra, y Azure B1 no garantiza compilación de extensiones C en todos los escenarios de deploy.

**Consecuencias**:
- Umbrales actuales: MATCHED ≥ 0.88 · AMBIGUOUS 0.72–0.88 · NEW < 0.72 · CONFLICT si exact + fuzzy apuntan a centros distintos.
- Si con carga real (11k+ centros) la calidad o el tiempo son insuficientes, migrar a RapidFuzz como dependencia explícita.

**Estado**: Provisional. Revisar después del primer piloto con TM completa real.

---

## ADR-009 — APK Android nativa (no PWA)

**Decisión**: La aplicación móvil del encuestador es una APK Android nativa, no una Progressive Web App.

**Contexto**: Las PWA en Android no tienen acceso a la API de envío de SMS en background. El SMS requiere permisos `SEND_SMS` y capacidad de envío sin que el usuario interactúe con la app en cada envío. Esto es posible solo en una APK nativa (Kotlin/Java).

**Consecuencias**:
- Requiere un repo separado para el desarrollo Android.
- El encuestador toca candidato → toca "Opinar" → el SMS se envía automáticamente sin confirmación adicional.
- Modo offline: la APK encola votos localmente y envía en lote al recuperar señal.
- Distribución: sideload directo (APK firmada) — no requiere Play Store.

**Estado**: Fija. Desarrollo Android pendiente (fuera de scope del repo web actual).

---

## ADR-010 — Seed de datos históricos en startup.py (no solo en evento FastAPI)

**Decisión**: `startup.py` llama `seed_historico_estudios.py` explícitamente en cada arranque, antes de iniciar uvicorn.

**Contexto**: Los datos históricos viven en `data/historico_estudios_seed.json` (versionado en git) y se escriben en `exitpoll.db` (persistente en Azure, no versionado). Cuando se regenera el seed localmente y se hace push, Azure tiene el código nuevo pero la BD contiene los datos viejos. El `@app.on_event("startup")` que existía como mecanismo de sync fallaba silenciosamente por el bloque `try/except` — Azure servía datos desactualizados sin ningún aviso en los logs.

**Consecuencias**:
- `startup.py` ejecuta `seed_historico_estudios.py` incondicionalmente en cada deploy/restart.
- El seed usa `ON CONFLICT DO UPDATE` en todas las tablas historicas — es idempotente y seguro.
- Si el seed falla, `subprocess.check_call` lanza excepción y el arranque aborta visiblemente (en lugar de continuar con datos viejos).
- El evento `@app.on_event("startup")` en `app.py` queda como fallback redundante pero ya no es el mecanismo primario.
- **Regla operativa**: cada vez que se modifica `historico_estudios_seed.json` localmente, el commit y push al repo es suficiente para que Azure sincronice en el próximo restart. No se necesita intervención manual en la BD.

**Estado**: Fija.
