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
U = min(100, 100 * (0.50*R + 0.30*E + 0.20*V) + Bc)

R = representatividad relativa
    max(0, 1 - desvio_shrunk / 15pp)

E = estabilidad relativa robusta
    max(0, 1 - MAD_shrunk / 10pp)

V = volumen log-normalizado dentro del estado
    log(electores) / log(max_electores_estado)

Bc = bonus capado de convergencia temporal
     0 a 8 puntos si el desvio relativo baja con el tiempo
```

- `desvio_shrunk` y `MAD_shrunk` usan shrinkage empirico adaptativo hacia el estrato geografico con `k=1.5`: el encogimiento pesa con series cortas y se apaga cuando `n_eff >= 2.5`. Esto reduce ruido sin aplastar centros con historia suficiente.
- La estabilidad relativa se mide contra la brecha nacional de cada eleccion, no contra la brecha cruda del centro. Una eleccion atipica que mueve todo el pais no convierte automaticamente a un centro estable en `cambiante`.
- La estabilidad robusta usa MAD de los desvios relativos, no desviacion estandar, para reducir sensibilidad a outliers con series de 3 a 5 puntos.
- La convergencia temporal requiere al menos 3 historicos comparables. Ajusta una pendiente sobre el desvio relativo ordenado en el tiempo; si el desvio baja, agrega hasta 8 puntos al score. Si el desvio sube, no resta puntos adicionales porque esa perdida ya se refleja en representatividad y estabilidad.
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

---

## ADR-013 - Contrato normalizado de resultados electorales historicos

**Decision**: Para elecciones operativas desde 2004, `resultados_historicos` mantiene sus columnas legadas y agrega campos normalizados aditivos: `electores_inscritos`, `votantes`, `votos_validos`, `votos_nulos`, `votos_gobierno`, `votos_oposicion`, `votos_otros`, porcentajes politicos sobre validos, `participacion`, `incluye_exterior`, `granularidad`, `fuente`, `corte_fuente`, notas, mesas y detalle JSON cuando hace falta conservar subgrupos.

**Contexto**: Las fuentes historicas mezclan cortes, coberturas y denominadores. Algunos importadores antiguos excluian exterior o sumaban nulos dentro de otros. Para arqueologia electoral, la fuente original se conserva, pero los derivados deben tener la misma semantica entre anos.

**Reglas**:
- `votos_otros` contiene candidatos distintos de gobierno/oposicion; no contiene nulos.
- Porcentajes de gobierno/oposicion/otros se calculan sobre `votos_validos`.
- Participacion se calcula como `votantes / electores_inscritos`.
- `NULL` significa desconocido/no disponible; cero significa cero real.
- `incluye_exterior` debe explicitar si el corte nacional conserva exterior.
- 1998 y 2000 quedan como antecedentes; no se fuerzan equivalencias con codigos CNE modernos en esta fase.

**VENPRES-A 2018**:
- Se acepta provisionalmente `2018-presidencial` desde VENPRES-A (`10.7910/DVN/NO1XJ2`) como dataset granular historico por centro.
- En el XLSX fuente, `mesas` representa cantidad de mesas por centro.
- `voto_c` se trata como votantes y `votos_validos` se recalcula desde candidatos.
- Maduro se almacena como gobierno, Falcon como oposicion y Bertucci+Quijada como otros; el detalle se conserva en `detalle_otros_json`.

**Consecuencias**:
- La UI actual sigue leyendo el contrato legado.
- Las validaciones y futuras fichas deben usar los campos normalizados.
- Las discrepancias arqueologicas se reportan con deltas; no se corrigen silenciosamente.

**Estado**: Implementada para resultados electorales; pendiente normalizacion de estudios historicos y fichas.

---

## ADR-014 - Rutas sincronas y prohibicion de escribir desde un GET

**Decision**: Los handlers de FastAPI que hacen I/O sincrono se declaran `def`, no `async def`. Ninguna ruta GET escribe en la BD.

**Contexto**: Las 59 rutas estaban declaradas `async def` pero llamaban `get_db()` (sqlite3 sincrono), leian ficheros y generaban graficos con folium/plotly. Eso bloquea el event loop. Con un solo worker de uvicorn sobre el core del plan B1, la app quedaba estrictamente serializada: `GET /` pasaba de 0.16 s a 9.0 s mientras una peticion a `/live` estaba en vuelo.

En paralelo, dos rutas GET hacian trabajo de escritura en cada peticion (`ensure_config_table` con `CREATE TABLE` + INSERTs, y `construir_laboratorio` con `ensure_muestra_lab_tables` y `seed_default_historical_metadata`). Como el seed de arranque mantiene una transaccion de escritura abierta durante decenas de segundos, esas lecturas competian por un lock que no deberian necesitar y devolvian 500 con `database is locked`.

**Reglas**:
- Una ruta que hace I/O sincrono se declara `def`. FastAPI la corre en el threadpool y el event loop queda libre.
- Una ruta se declara `async def` solo si su cuerpo usa `await`. Si necesita leer el body (`await request.form()`) y ademas hacer trabajo bloqueante, el trabajo bloqueante va en `asyncio.to_thread`.
- Los generadores de SSE nunca ejecutan sqlite inline: usan `asyncio.to_thread`.
- Un GET no crea tablas, no siembra filas y no hace `commit`. El trabajo idempotente de bootstrap se hace una vez, en el evento de startup.
- Los guards de "una vez por BD" se llavean por ruta de fichero de la BD, no con un booleano de modulo: los tests intercambian `DB_PATH` dentro del mismo proceso.

**Consecuencias**:
- Cualquier ruta nueva debe elegir conscientemente `def` vs `async def`; el default correcto en este proyecto es `def`.
- Quedan 9 rutas POST en `async def` con trabajo bloqueante tras el `await` del body, registradas como pendiente en ESTADO.md.
- Metodo de diagnostico que sirvio y conviene repetir: lanzar la peticion pesada en segundo plano y cronometrar una ruta trivial en paralelo. Si la trivial se degrada, el cuello es el event loop y no la capacidad del plan.

**Estado**: Fija.

---

## ADR-015 - Seed de resultados historicos idempotente por huella de fuentes

**Decision**: `seed_resultados_historicos` calcula una huella de sus ficheros de origen y se salta el trabajo si no cambio nada desde la ultima siembra. La huella se guarda en la tabla `seed_state`.

**Contexto**: El seed corria completo en cada arranque, reprocesando todos los CSV y XLSX: 34.6 s medidos en SSD local y bastante mas sobre Azure Files. Durante todo ese tiempo mantenia una transaccion de escritura abierta, y cualquier otra escritura concurrente moria a los 5 s con `database is locked`. La ventana se reabria en cada deploy y en cada reinicio.

**Alcance**: Esta ADR afecta unicamente a `seed_resultados_historicos` (los CSV/XLSX de resultados electorales). **No modifica ADR-010**, que sigue vigente tal cual: `seed_historico_estudios` se sigue ejecutando incondicionalmente en cada arranque desde `startup.py`. Ese seed tarda 0.0 s medidos, asi que no aporta el problema y conserva su garantia de sincronizacion.

**Reglas**:
- La huella cubre tamano y `mtime` de cada fichero de `DATASETS` y `EXCEL_DATASETS`, mas los metadatos declarados de cada dataset. Editar un CSV o cambiar la definicion de un dataset vuelve a disparar el seed completo.
- El skip exige ademas que `resultados_historicos` tenga filas, para no saltarse la siembra sobre una BD vacia o reseteada cuya huella quedo escrita.
- Un deploy reescribe los ficheros y cambia sus `mtime`, asi que la regla operativa de ADR-010 se mantiene: commit y push bastan para que Azure aplique datos nuevos.

**Consecuencias**:
- El arranque deja de pagar ~34 s de reproceso cuando no hay nada nuevo que sembrar.
- Si alguna vez se necesita forzar una resiembra sin tocar las fuentes, basta con borrar la fila de `seed_state`.

**Estado**: Fija.

---

## ADR-016 - Seleccion productiva de muestra V1 aleatoria estratificada

**Decision**: La seleccion productiva de muestra usa `stratified_random`: cuotas
por estado proporcionales a electores inscritos del frame de la eleccion
corriente y seleccion aleatoria reproducible por `seed` dentro de cada estado.

**Contexto**: Los backtests y diagnosticos historicos muestran que RMSE, `mu` y
`sigma` contienen senal real, pero no una victoria robusta ni preregistrada que
justifique usarlos para rankear, filtrar, corregir o redibujar centros en
produccion. Usar resultados anteriores como correccion operativa tambien
cambia la naturaleza del sistema: deja de ser una medicion pura de la eleccion
corriente.

**Reglas**:
- El universo metodologico es la Tabla Mesa de la eleccion corriente.
- Para presidencial V1, el estrato es el estado.
- Las cuotas se asignan proporcionalmente a electores inscritos, con minimos y
  redondeo deterministicos.
- La muestra genera titulares y reservas sin solapamiento.
- Cada generacion registra eleccion, hash/version de Tabla Mesa, metodo,
  tamano, seed, cuotas, timestamp y version de algoritmo.
- RMSE, score, `mu`, `sigma`, recency, factores de fuente y ranking historico
  quedan fuera de la seleccion productiva.
- `historical_greedy` y backtests quedan como estrategias experimentales no
  promovidas a produccion.

**Consecuencias**:
- ADR-011 y ADR-012 siguen documentando el laboratorio historico, pero no
  definen el selector productivo V1.
- El estimador productivo no cambia: mantiene pesos preelectorales,
  actualmente electores inscritos.
- El experimento oracle con votos validos target queda como investigacion, no
  como comportamiento productivo.

**Documentacion permanente**:
- `docs/muestreo/METODOLOGIA_MUESTREO.md`
- `docs/muestreo/HISTORIAL_EXPERIMENTAL.md`
- `docs/muestreo/RESULTADOS_BACKTEST.md`
- `docs/muestreo/DECISIONES_MUESTREO.md`

**Estado**: Fija para V1.

---

## ADR-017 - Selector longitudinal experimental sucesor del legacy

**Decision**: Se implementa `longitudinal_mae_v1` como metodo experimental
separado para muestras presidenciales nacionales futuras. Su score principal
es `historical_mae` cuando el centro tiene al menos dos historicos
presidenciales comparables, con fallback a `recent_distance` cuando tiene uno
y `NULL` cuando no tiene historial.

**Contexto**: La reconstruccion del legacy mostro que el criterio operativo era
centros grandes dentro del estado, filtrados por semejanza con elecciones
previas. Los backtests longitudinales 2013, 2018 y 2024 y la ronda de
falsificacion no encontraron evidencia suficiente para descartar
`historical_mae` como candidato principal, pero tambien mostraron cautelas de
survivorship y margen frente al oracle. Por eso el metodo se implementa como
sucesor experimental, no como selector productivo por defecto.

**Reglas**:
- El universo lo define el frame vigente de la eleccion objetivo.
- V1 se limita a presidencial -> presidencial.
- La asignacion nacional es 2 centros por cada una de 24 entidades mas 72
  adicionales por D'Hondt sobre electores, para N=120.
- La seleccion dentro del estado conserva la logica legacy: score historico
  como aptitud, prioridad por electores y ladder `[2,4,6,8,10,15,20,inf]`.
- No hay score compuesto, alfa, minimax, PPS, random baseline ni reglas
  especiales derivadas de 2013/2018/2024.
- `stratified_random_v1` sigue siendo `METODO_PRODUCTIVO`.

**Consecuencias**:
- `backend/selector_longitudinal.py` puede invocarse deliberadamente para
  estudios futuros y comparaciones de laboratorio.
- El legacy y sus backtests permanecen como reconstruccion/comparacion.
- Los resultados retrospectivos son evidencia documental, no reglas
  operacionales futuras.

**Documentacion permanente**:
- `docs/muestreo/METODO_LONGITUDINAL_V1.md`
- `docs/muestreo/BACKTEST_LONGITUDINAL.md`
- `docs/muestreo/BACKTEST_LONGITUDINAL_FALSIFICATION.md`

**Estado**: Experimental. No productivo.

---

## ADR-018 - Marco muestral 2024 desde el REP del CNE y derivacion de mesas

**Decision**: El marco muestral 2024 se construye desde el Registro Electoral
2024 publicado por el CNE a nivel de CENTRO (15.962 centros), no desde el dump
de actas de resultadosconvzla. El numero de mesas por centro, que el CNE nunca
publico para 2024, se deriva por formula y queda marcado en el CSV con la
columna `origen_mesas`.

**Contexto**: El marco 2024 en uso venia del dump de actas y cubria 11.927
centros con 17.502.516 electores, es decir el 75% de los centros y el 82% del
padron. Los centros sin acta digitalizada simplemente no existian para el
selector. No hay ninguna TM oficial del CNE por mesa para 2024: igual que en
2018, el organismo no publico ni el desagregado de resultados ni el directorio
de centros y mesas de ese ciclo, y `cne.gob.ve` ya no resuelve DNS.

**Fuente**: hoja `15.962 centros_cne` del spreadsheet de `ipince/vzlapi`
(https://docs.google.com/spreadsheets/d/1l6ThiQQZXog_8fBw3z5RwqThG7QAy0AqF4wPYpvGUWA/),
datos del CNE. Copiada al repo como `backend/centros_cne_2024_rep.csv`.

**Validaciones que dieron exacto contra cifras oficiales**:
- 21.392.464 electores venezolanos, la cifra oficial del REP presidencial 2024.
- 228.144 electores extranjeros.
- Estado `99 EXTERIOR`: 106 centros y 69.211 electores, la cifra oficial del
  voto en el exterior.
- Cero mojibake en el fichero, a diferencia del TM anterior.

**Reglas**:
- `electores` de la TM usa `electores_venezolanos`. Los extranjeros estan en el
  REP pero no votan presidenciales; asi el total cuadra con la cifra oficial.
- El numero de mesas usa `electores_total` (venezolanos + extranjeros), porque
  el cuaderno del centro con el que se arman las mesas si los incluye.
- `CAP_MESA = 1000`. Calibrado por barrido contra las 22.197 mesas conocidas
  por acta: 11.177 centros con coincidencia exacta (94%), 23 centros donde el
  acta muestra mas mesas que la formula (0,19%), y 30.459 mesas nacionales
  contra las ~30.027 oficiales (24.532 mesas transmitidas = 81,7% segun
  resultadosconvzla). Capacidades entre 550 y 950 no producen ninguna
  violacion pero se alejan del total nacional; por encima de 1010 las
  violaciones se disparan.
- `origen_mesas` distingue las dos vias: `acta` para los 11.200 centros donde
  manda la mesa de mayor numero vista en las actas, `derivado` para los 4.762
  restantes.

**Consecuencias**:
- `centros.num_mesas` en BD queda poblado con valores derivados para el 30% de
  los centros. No es dato duro. La distincion vive solo en
  `backend/tm_2024_estandar_v2.csv`; recuperarla en BD requiere agregar la
  columna a `centros`, que no se hizo por no ser necesario hoy.
- El marco activo pasa de 14.910 a 15.962 centros y de 18.740.203 a 21.392.464
  electores. 906 centros que existian en marcos viejos y no estan en el REP
  2024 quedan `activo=0`.
- El frame elegible del selector longitudinal (piso de 800 electores, estados
  1-24) pasa de 7.142 a 8.314 centros. 1.316 de esos centros ya existian pero
  estaban bajo el piso con el padron desactualizado.

**Reproducible con**:
```
python backend/generar_tm_2024.py
python backend/cargador_tm.py backend/tm_2024_estandar_v2.csv --dry-run
python backend/cargador_tm.py backend/tm_2024_estandar_v2.csv
```

**Estado**: Productivo.
