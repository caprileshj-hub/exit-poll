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

---

## ADR-011 - Pestana Muestra como laboratorio asistido de seleccion

**Decision**: La pestana `Muestra` debe evolucionar de un generador automatico de centros a un laboratorio asistido de seleccion. El selector automatico actual seguira existiendo como boton de propuesta inicial, pero la decision final debe ser visible, editable y defendible por un operador humano.

**Contexto**: Para construir una muestra de exit poll, el insumo ideal es doble: la Tabla Mesa o REP de la eleccion objetivo y el resultado de la eleccion inmediatamente anterior desglosado por mesa o centro. En Venezuela esos insumos son dificiles de conseguir y pueden estar incompletos. El sistema ya tiene historicos heterogeneos: resultados por centro, estudios de exit poll agregados, resultados oficiales nacionales o territoriales, y recuperaciones parciales como el Referendum Revocatorio 2004. Es metodologicamente incorrecto colapsar todo eso en un unico score sin mostrar linaje, granularidad y confianza.

**Consecuencias**:
- La lista maestra de centros debe unir registro permanente, TM/REP de la eleccion activa e historicos conocidos. Ninguna fuente debe filtrar destructivamente el universo.
- Cada centro debe tener un estado de vida derivado: `activo`, `solo_historico`, `nuevo` o `incierto`.
- El laboratorio debe separar `score_utilidad` de `confianza_dato`. El score ordena candidatos; la confianza dice cuanto puede creerse ese score.
- No se debe promediar una serie por centro con una serie territorial sin etiquetarlo. Los estudios agregados sirven como contexto territorial, prior para centros sin dato propio o validacion cruzada, pero no sustituyen el comportamiento historico del centro.
- La estabilidad historica solo se calcula con datos por mesa o centro agregables a centro.
- La representatividad debe comparar brechas (`pct_gobierno - pct_oposicion`) contra el ambito relevante de la eleccion objetivo, no solo porcentajes de un bando contra el nacional.
- El ambito de referencia depende de la eleccion: presidencial nacional; gobernadores estado; alcaldes municipio; legislativas circuito/estado cuando exista.
- Centros con baja confianza o sin historico suficiente no deben mostrar falsa precision. En vez de un score numerico deben mostrar `dato insuficiente` o semaforo bajo.
- La muestra publicada debe conservar trazabilidad: quien agrego el centro, cuando, score/confianza al momento y motivo.

**Contratos de datos propuestos para v1**:
- `centro_codigos`: mapeos entre codigo CNE actual y codigos alternos/historicos, con `tipo_codigo`, `fuente` y `confianza_match`. No limitarlo a 2004; debe soportar futuros codigos alternos, renombres o vinculos manuales.
- `centro_snapshot`: historial de mesas/electores por `codigo_cne` y `eleccion_ref`, con `fuente`.
- Metadatos de historicos: preferir una tabla aditiva tipo `resultados_historicos_meta` o `historico_fuentes` antes de modificar agresivamente `resultados_historicos`, para no romper `/historicos`, heatmaps ni visualizaciones existentes.
- `muestra` debe ganar trazabilidad (`motivo`, `agregado_por`, `score_snapshot`, `confianza_snapshot`, `created_at`) o una tabla asociada equivalente.
- Las clasificaciones multiples deben modelarse como tags o chips derivados; evitar que un unico `CHECK` de `tipo_centro` bloquee casos como `volumen` + `bastion_azul` + `alta_confianza`.

**Formula inicial explicable**:

```text
Score = 100 * (0.35*R + 0.20*E + 0.20*V + 0.25*C)

R = representatividad = max(0, 1 - desvio_pp / 15)
E = estabilidad       = max(0, 1 - estabilidad_pp / 10)
V = volumen           = log(electores) / log(electores_max_del_estrato)
C = confianza_dato
```

Los pesos deben ser configurables en la UI. El score compite dentro del estrato geografico aplicable; la cobertura geografica se garantiza por cuotas, no por inflar el score.

**Metricas de control de la muestra**:
- Cobertura geografica: estados, municipios y parroquias representados contra el universo disponible.
- Composicion: centros por clasificacion, nivel de confianza, fuente y granularidad.
- Distribucion de brecha: histograma de la muestra contra el universo disponible.
- Backcast: que habria proyectado esta muestra en elecciones historicas disponibles por centro, reportando error de brecha y metricas Mosteller/DEFF cuando apliquen.
- Alertas: exceso de bastiones, exceso de centros sin historico, subrepresentacion territorial, muestra demasiado sesgada contra el universo historico.

**Alcance v1**:
- Lista maestra filtrable.
- Ficha de centro con linaje de datos, elecciones disponibles, tendencia rojo/azul, desviacion contra ambito y advertencias.
- Agregar/quitar centros manualmente.
- Panel vivo muestra vs universo.
- Boton `proponer candidatos` reutilizando el selector actual como precarga editable.

**Fuera de alcance v1**:
- Optimizador automatico que minimice error de backcast.
- Reemplazar pesos o calculos de totalizacion.
- Mezclar datos personales de electores. Todo debe operar con agregados por centro, mesa o territorio.

**Estado**: Aprobada para diseno. Implementar en fases, empezando por contratos de datos aditivos y pantalla exploratoria; no convertir todavia el selector en optimizador automatico.

---

## ADR-012 - Score v2 de centros: utilidad separada de confianza

**Decision**: El laboratorio de `Muestra` adopta un score de utilidad separado del semaforo de confianza. El score no suma confianza ni aplica una penalizacion externa por suficiencia historica; la confianza queda como eje paralelo para habilitar, limitar o condicionar el uso del centro.

**Contexto**: El dictamen del comite tecnico senalo cuatro riesgos del score v1: doble penalizacion por suficiencia historica, mezcla entre utilidad y confianza, sesgo mecanico hacia centros grandes y dependencia excesiva de niveles en vez de comportamiento relativo. En exit polls politicos, especialmente en Venezuela, la disponibilidad historica es incompleta y la eleccion 2024 debe tratarse como dato reciente valioso pero con fuente y cobertura visibles.

**Metodologia implementada**:
- El score visible es un score de rol `barometro`:

```text
U = 100 * (0.50*R + 0.30*E + 0.20*V)

R = representatividad relativa
    max(0, 1 - desvio_shrunk / 15pp)

E = estabilidad relativa robusta
    max(0, 1 - MAD_shrunk / 10pp)

V = volumen log-normalizado dentro del estado
    log(electores) / log(max_electores_estado)
```

- `desvio_shrunk` y `MAD_shrunk` usan shrinkage empirico adaptativo hacia el estrato geografico con `k=1.5`: el encogimiento pesa con series cortas y se apaga cuando `n_eff >= 2.5`. Esto reduce ruido sin aplastar centros con historia suficiente.
- La estabilidad relativa se mide contra la brecha nacional de cada eleccion, no contra la brecha cruda del centro. Una eleccion atipica que mueve todo el pais no convierte automaticamente a un centro estable en `cambiante`.
- La estabilidad robusta usa MAD de los desvios relativos, no desviacion estandar, para reducir sensibilidad a outliers con series de 3 a 5 puntos.
- La confianza A-D se calcula aparte con fuente, granularidad, cobertura, recencia y `n_eff`.
- `n_eff` pondera historicos por recencia: 2024 pesa 1.0 y cada ciclo historico hacia atras pesa 0.85 del anterior.
- 2024 se incorpora como historico normal en el marco relativo, pero la fuente queda marcada como `actas_cvzla`, cobertura 81%, y se muestra bandera `ruptura_2024` si el desvio relativo 2024 se aparta mas de 8pp del promedio previo del centro.

**Reglas practicas**:
- La confianza no debe compensar mala utilidad. Un centro muy documentado pero poco representativo no debe subir artificialmente por el semaforo.
- Clase A/B puede anclar estratos; clase C es candidato condicional si no hay mejores opciones o si cumple un rol especifico; clase D no debe anclar.
- Para anclar una muestra futura se exige dato reciente 2024 cuando exista alternativa comparable. Un centro sin 2024 puede conservar alto score de utilidad historica, pero queda como `condicional_sin_2024` y se ordena debajo de `ancla`.
- El volumen queda en 20% porque es eficiencia operativa, no representatividad estadistica. El peso electoral final se maneja con estratos y pesos, no eligiendo solo centros grandes.
- La clasificacion `cambiante` se basa en variacion relativa alta o ruptura 2024, no solo en cambio de signo de la brecha cruda.
- Los bastiones siguen siendo utiles como controles de sesgo de campo y no deben descartarse por no ser barometros nacionales.

**Pendiente metodologico**:
- Implementar backtesting leave-one-election-out para comparar score v2 contra PPS estratificado, centros mas grandes y score v1.
- Agregar scores por rol (`seguidor_swing`, `volumen`, `bastion_control`, `bisagra`) antes de construir un optimizador automatico de portafolio.
- Implementar un boton de seleccion automatica que use estos criterios como preseleccion tecnica editable, no como muestra definitiva.
- Separar formalmente la seleccion metodologica de la seleccion logistica: accesibilidad, seguridad, disponibilidad de encuestadores, continuidad operativa y sustitutos del mismo estrato/rol pueden descartar un centro aun si tiene el mejor score.
- Cuando se incorporen nuevos resultados previos, el algoritmo debe suavizar y recalibrar la tendencia de uso de cada centro, no congelar decisiones anteriores.
- Evaluar incorporacion de historicos 1998 y 2000 si se recuperan localmente con contrato verificable.

**Estado**: Implementada como v2 explicable en el laboratorio; pendiente validacion por backtesting antes de automatizar la seleccion final.
