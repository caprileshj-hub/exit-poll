# Exit Poll Venezuela

> Read this document in English: [README.md](./README.md)

Plataforma integral de exit poll para elecciones venezolanas. Reemplaza un flujo manual (planillas de papel → llamadas telefónicas → base de datos Access → Excel) con un sistema automatizado construido alrededor de la recolección de datos por SMS — el único canal confiable en las condiciones de baja conectividad del campo venezolano. Los resultados fluyen desde el campo hacia un heatmap ponderado en tiempo real y un dashboard de tendencias. Un analista IA determinístico embebido en la vista en vivo lee los datos entrantes y ofrece interpretaciones en lenguaje natural de la tendencia nacional, los estados individuales y la posición de cada candidato — con guardrails explícitos contra declaraciones prematuras de ganador.

---

## El problema

Hacer un exit poll en Venezuela implica tres desafíos que se acumulan:

1. **Sin datos móviles en campo.** Los encuestadores trabajan en centros de votación sin internet confiable. La recolección tradicional por app falla.
2. **Datos electorales oficiales inconsistentes.** Antes de cada elección, el CNE entrega a los partidos registrados una *Tabla de Mesa* (TM) — un documento técnico que lista cada código de mesa, su ubicación dentro de cada centro y el número de electores asignados. La TM es el insumo fundacional para el diseño de muestra y el cálculo de pesos. El problema: su formato, estructura de columnas, nombres de hojas y encoding cambian con cada ciclo electoral. Un parser rígido construido para una elección se rompe en la siguiente.
3. **La agregación manual es lenta y propensa a errores.** El flujo legacy requería un coordinador recibiendo llamadas del campo, transcribiendo votos a Access y procesando resultados ponderados en Excel — introduciendo demoras y errores de transcripción en cada paso.

Este proyecto automatiza el pipeline completo: desde la recolección en campo hasta la visualización de resultados ponderados.

---

## Arquitectura

```
[APK Android] → SMS → [Gateway Android] → HTTP POST → [Backend FastAPI] → [BD SQLite] → [Dashboard HTML]
```

**¿Por qué SMS?** En los estados rurales venezolanos, la cobertura de datos móviles en los centros de votación es poco confiable o inexistente. El SMS es el único canal que funciona consistentemente en todo el alcance geográfico de una elección nacional. Todo encuestador tiene capacidad SMS sin importar la cobertura de datos.

Cada SMS lleva un registro de voto completo en ~28 caracteres:

```
C1234;V2;T1932;L09a7F3b
```

| Campo | Descripción |
|-------|-------------|
| `C`   | Código CNE del centro de votación |
| `V`   | ID del candidato (V0 = voto nulo) |
| `T`   | Timestamp local (HHMM) |
| `L`   | Coordenadas GPS como Geohash (~38 m de precisión, 6 chars) |

El número de teléfono del encuestador es su ID — nunca viaja en el payload del SMS.

---

## Estado actual

El proyecto está en desarrollo activo. **La Fase 7 está en curso:**

### Completado
- **Base de datos** — SQLite en modo WAL, foreign keys, registro permanente de centros de votación, elegibilidad por elección, tablas de auditoría y modelo de acceso para clientes
- **Pipeline de ingesta TM** — Mantiene el cargador diferencial legacy Excel/CSV para los formatos conocidos 2015/2018 y agrega un flujo de ingesta multi-formato asistido por IA para archivos CNE nuevos; las coordenadas GPS y calificaciones de riesgo ingresadas manualmente nunca se sobrescriben
- **Diseño de muestra** — Laboratorio asistido para seleccionar centros desde el universo activo e histórico; combina score de utilidad, confianza del dato, tendencia por centro, trazabilidad de fuentes y propuesta automática editable. Usa resultados por centro/mesa agregados de 2004, 2006, 2007, 2009, 2012, 2013, 2018 y 2024 cuando están disponibles.
- **Calculador de pesos jerárquico** — Ponderación de cuatro niveles (parroquia → municipio → estado → nacional) con reglas de excepción geográfica para Distrito Capital, La Guaira y Miranda-Caracas
- **Generador de heatmap** — Choropleth con Folium a nivel estado (ADM1) y municipio (ADM2); lookup espacial cacheado para 332 municipios
- **Dashboard HTML autónomo** — Salida de un solo archivo: mapa Folium (58%) + gráficos de tendencia Plotly (42%); clic en el polígono de un estado muestra su tendencia local; paleta simétrica azul-blanco-rojo con umbral de empate técnico ±3%
- **Dashboard de configuración FastAPI** — Gestiona elecciones, candidatos (con fotos y ámbito geográfico/circuito por elección), selección de muestra, edición de pesos, cargas TM legacy, cargas TM asistidas por IA y vista previa de visualización
- **Integración de datos CNE 2024** — Resultados electorales completos de 2024 (11.927 centros) ingeridos desde la fuente vzlapi en `resultados_historicos` para el scoring de representatividad. Requirió un conversor dedicado (`convertidor_cne2024.py`) porque el formato de la Tabla de Mesa 2024 difería estructuralmente de los conversores 2015 y 2018 ya existentes. Este es el caso concreto que motiva el componente de normalización con IA: cada ciclo electoral — o tipo de elección — llega con una estructura de TM distinta, y escribir un conversor nuevo cada vez no escala.
- **Módulo de Estudios Históricos** — Archivo de solo lectura para estudios históricos fijos y resultados oficiales. Incluye estudios presidenciales, legislativo 2010, colecciones de gobernadores 2008 y 2012, estudios municipales 2013 con notas de auditoría de confiabilidad por centro, páginas de detalle por estado, gráficos de tendencia por cortes y un seed versionado (`backend/data/historico_estudios_seed.json`) aplicado idempotentemente al arranque.
- **Ficha técnica** — Documento de metodología estilo CIS con margen de error calculado, imprimible desde el dashboard
- **Analista IA en vivo** — Panel de analista determinístico y chat respaldado por proveedor con guardrails. Rechaza análisis de tendencia prematuros con la frase exacta `datos insuficientes para establecer tendencias` hasta que existan mínimos de opiniones, cobertura y cortes comparables.

### Dataset historico RR 2004
- **Referendum Revocatorio 2004** - Dataset agregado por centro en `backend/resultados_rr2004.csv`, sembrado como `2004-revocatorio` en `resultados_historicos` mediante `backend/seed_resultados_historicos.py`. La fuente recuperable es Esdata/Wayback; no contiene cedulas, nombres de electores ni registros persona a persona.
- **Cobertura recuperada** - 6.265 centros, 8.956.463 votos validos y 12.980.497 electores REP 2004. La cobertura no es el 100% del universo oficial de centros habilitados; debe leerse como una recuperacion historica parcial para analisis de tendencias por centro. Aun asi, cubre mas de 90% del volumen nacional de votos/electores.
- **Convencion historica** - En el revocatorio, `NO` ratifica al gobierno y se guarda como `votos_gobierno`; `SI` revoca y se guarda como `votos_oposicion`. `codigo_centro` y `codigo_cne_nuevo` son el codigo CNE nuevo; `codigo_viejo` y `codigo_cne_viejo` preservan el identificador antiguo usado por Esdata.

### Dataset historico Referendum Constitucional 2007
- **Referendum Constitucional 2007** - Dataset agregado por centro en `backend/resultados_ref2007.csv`, sembrado como `2007-referendum` en `resultados_historicos` mediante `backend/seed_resultados_historicos.py`.
- **Cobertura recuperada** - 9.002 centros con resultados, 29.072 mesas fuente con resultado y 4.542 mesas fuente sin resultado. La cobertura registrada es 86,5% y debe leerse como recuperacion de primer boletin, no como universo oficial completo.
- **Convencion historica** - La fuente tiene bloques A y B. `SI` apoyaba la propuesta de reforma del gobierno y `NO` la rechazaba. La tendencia almacenada combina la relacion SI/NO de ambos bloques y preserva volumen aproximado de votantes promediando los votos validos entre bloques. El CSV versionado no contiene cedulas, nombres de electores ni registros persona a persona.

### Dataset historico Enmienda 2009
- **Enmienda Constitucional 2009** - Dataset agregado por centro en `backend/resultados_enmienda2009.csv`, sembrado como `2009-enmienda` en `resultados_historicos` mediante `backend/seed_resultados_historicos.py`.
- **Cobertura recuperada** - 11.233 centros, 34.250 mesas exportadas en agregados por centro, 11.504.321 votos validos y 16.684.405 electores. La fuente es el archivo Esdata/Wayback `ENMIENDA2009_2boletin` y debe tratarse como recuperacion historica de alta cobertura, pero de segundo boletin.
- **Convencion historica** - En la enmienda 2009, `SI` apoyaba la propuesta del gobierno y se almacena como `votos_gobierno`; `NO` se almacena como `votos_oposicion`. El CSV versionado no contiene cedulas, nombres de electores ni registros persona a persona.

- **Contrato normalizado 2004+** - `resultados_historicos` conserva el contrato legado y agrega campos normalizados: `electores_inscritos`, `votantes`, `votos_validos`, `votos_nulos`, `votos_gobierno`, `votos_oposicion`, `votos_otros`, porcentajes sobre votos validos, `participacion`, `incluye_exterior`, `granularidad`, `fuente`, `corte_fuente`, notas y mesas cubiertas cuando existen. Los nulos no se mezclan con `votos_otros`.

### Fuente historica Presidencial 2018
- **Presidencial 2018** - `2018-presidencial` ahora tiene dataset granular provisional por centro en `backend/data/2018/resultados_venpres_a_2018.csv`, generado desde VENPRES-A (`10.7910/DVN/NO1XJ2`) con `backend/import_2018_venpres_a.py`.
- **Cobertura VENPRES-A** - 14.400 centros, 33.716 mesas, 20.517.997 electores, 9.360.318 votantes, 9.203.220 votos validos, 157.098 nulos. Maduro se almacena como gobierno (6.227.663), Falcon como oposicion (1.924.469) y Bertucci+Quijada como otros (1.051.088).
- **Transformacion documentada** - En el XLSX fuente, `mesas` es cantidad de mesas por centro. La columna `voto_c` se trata como votantes; `votos_validos` se recalcula desde candidatos para mantener `votantes = votos_validos + votos_nulos`.
- **Evidencia CNE archivada** - `backend/data/2018/cne_archivado_nacional.json` registra la pista publica de subdominios y las capturas de Wayback para `www4.cne.gob.ve/ResultadosElecciones2018/`. La pagina CNE archivada conserva valores de ficha tecnica nacional y porcentajes por candidato a traves de `grafico_participacion.php`.
- **Mejora estadal provisional** - `backend/data/2018/resultados_estadales_provisional.csv` conserva la mejor evidencia disponible por estado. La participacion suma contra el total nacional final, pero los votos por candidato no reconcilian completamente (brecha material en Bertucci), por lo que se etiqueta como `provisional_no_reconciliado`.
- **Limite conocido** - VENPRES-A queda aceptado provisionalmente como arqueologia granular historica, pero no reemplaza una segunda fuente publica centro por centro ni el resultado nacional final CNE. La diferencia contra el corte nacional final queda documentada por fuente/cobertura.

### En desarrollo (Fase 7)
- Completar el archivo histórico de investigación: recuperar los estudios integrales de exit poll PLM de 2007 y 2009, obtener resultados electorales trazables por mesa o centro para 2015 y buscar una segunda fuente pública granular 2018. Los agregados Esdata 2007/2009 y VENPRES-A 2018 no cierran la normalización de estudios históricos.
- Hardening de producción para la normalización TM con IA: UX para archivos grandes, mejores flujos de resolución manual, manejo de rate limits de proveedores y fuzzy matching más fuerte
- Parser SMS y validación GPS en el backend FastAPI
- APK Android (UI del encuestador + envío SMS + cola offline)
- Gateway Android (lector SMS → HTTP POST)
- Dashboard de auditoría interna (semáforo de centros, panel de encuestadores, alertas de fraude)
- Gráficos para clientes (torta/barras)

---

## Componente IA: normalización dinámica de TM

La *Tabla de Mesa* del CNE es el insumo fundacional de cada elección. Contiene el registro completo de centros de votación, mesas, conteos de electores y códigos geográficos — pero **el formato cambia con cada ciclo electoral**. Los nombres de columnas se mueven, el encoding varía, las hojas se renombran y aparecen (o desaparecen) entidades geográficas nuevas.

El sistema tiene dos caminos de ingesta TM:

1. **Camino determinístico legacy** — `convertidor_tm.py` más `cargador_tm.py` maneja los formatos Excel/CSV conocidos y escribe a través del cargador diferencial establecido.
2. **Camino multi-formato asistido por IA** — `/tm` puede procesar archivos `.pdf`, `.xlsx`, `.xls`, `.xlsm`, `.csv`, `.docx` y `.txt`. Extrae texto del lado del cliente cuando es posible (SheetJS, mammoth.js, pdf.js) y cae a extracción del lado del servidor (`openpyxl`, `python-docx`, `pdfplumber`) cuando hace falta.

El camino IA usa el proveedor configurado en `/config`; no introduce una API key separada ni un vendor hardcodeado. La IA recibe el texto extraído, descubre el esquema del archivo desde los encabezados y valores reales, devuelve JSON y preserva los campos específicos de la elección en `campos_extra`.

Para cada fila extraída, el backend:
- Intenta matching exacto por identificador probable de centro (`codigo_centro` o hints de la IA)
- Corre fuzzy matching contra el registro histórico usando `nombre_centro + municipio + parroquia` normalizados
- Clasifica las filas como `MATCHED`, `NEW`, `AMBIGUOUS`, `CONFLICT` o `EXTRACTION_ERROR`
- Bloquea la confirmación hasta que las filas ambiguas/en conflicto se resuelvan
- Respeta el modo simulación: sin escrituras a BD cuando está activo

Al confirmar:
- `centros.num_mesas` y `centros.num_electores` se actualizan cuando vienen presentes
- `centros.direccion` se llena solo cuando está vacía
- `lat`, `lon`, `riesgo` y `radio_m` nunca se sobrescriben desde una Tabla de Mesa
- `election_centers` vincula cada centro del archivo a la elección destino y guarda `source_file` más `campos_extra`
- Los centros ausentes de una TM nueva no se eliminan ni se marcan inactivos; simplemente no tienen fila en `election_centers` para esa elección

---

## Tipos de elección soportados

| Tipo | Descripción |
|------|-------------|
| `nacional` | Mismos candidatos en todos los centros |
| `regional` | Candidatos distintos por estado |
| `municipal` | Candidatos distintos por municipio |
| `asamblea` | Voto nominal por circuito + voto lista por estado/partido |

---

## Detección de fraude

El backend aplica detección de anomalías basada en reglas durante la ingesta en tiempo real:

- **Alerta de piso:** < 8 votos por intervalo de 20 minutos (encuestador posiblemente inactivo)
- **Alerta de techo:** > 25 votos por intervalo de 20 minutos (por encima del objetivo estadístico)
- **Patrón crítico:** 3 intervalos consecutivos sobre el techo → alerta escalada
- **Validación GPS:** distancia Haversine entre el GPS del voto y las coordenadas registradas del centro; los votos fuera del radio configurado (300 m por defecto, configurable por centro) se guardan con `valid=false` y no totalizan
- **Números no registrados:** los SMS de teléfonos desconocidos se registran pero nunca se cuentan

Todas las alertas son visibles solo en la vista de auditoría interna. Los dashboards de clientes muestran resultados únicamente, sin acceso a datos operativos.

---

## Modelo de acceso de clientes

El sistema es un producto comercial. Cada cliente ve solo lo que contrató:

- **Retraso de datos configurable:** en vivo (0 min), 30 min, 60 min, o solo resultados al cierre
- **Ámbito geográfico:** nacional, por estado o por municipio
- **Permisos de vistas:** heatmap, gráficos de tendencia, tortas, barras, tabla de centros
- **Vistas de auditoría:** solo operadores internos — nunca expuestas a clientes

---

## Estructura de la base de datos

Tablas principales organizadas por bloque funcional:

| Bloque | Tablas |
|--------|--------|
| Geografía | `estados`, `municipios`, `parroquias`, `circuitos`, `circunscripciones_indigenas` |
| Centros de votación | `centros`, `election_centers`, `tm_ingestion_logs` |
| Elecciones | `elecciones`, `candidatos` |
| Diseño de muestra | `muestra`, `pesos`, `centros_candidatos` |
| Encuestadores | `encuestadores` |
| Votos | `sms_raw`, `votos` |
| Auditoría interna | `alertas` |
| Acceso de clientes | `clientes`, `contratos`, `accesos_geograficos`, `accesos_vistas` |

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.x, FastAPI, Jinja2 |
| Base de datos | SQLite (modo WAL, foreign keys) |
| Visualización | Folium, Plotly, Bootstrap 5 |
| Procesamiento de datos | pandas, openpyxl, pdfplumber, python-docx |
| Proveedores IA | Clientes OpenAI-compatible más Anthropic, vía el proveedor configurado en `/config` |
| Móvil (planificado) | Android nativo |
| Deploy | Azure (Student) |

---

## Reglas del diseño de muestra

**Regla general:** 2 centros de votación por estado

Si una elección tiene filas en `election_centers`, el selector de muestra solo considera centros marcados elegibles para esa elección. Si todavía no existen filas de elegibilidad, cae al comportamiento histórico y muestrea desde los centros activos del registro permanente.

**Excepciones geográficas** (2 centros por parroquia en vez de por estado):
- Distrito Capital
- La Guaira
- Miranda-Caracas: municipios Chacao, Baruta, El Hatillo y Sucre

**Clasificación de centros** (según resultados históricos):
- **Bisagra (swing):** centros competitivos dentro de ±10% del resultado nacional
- **Bastión:** centros con > 70% de dominio de un bando
- **Volumen:** alto número de electores, sin importar competitividad
- **Estándar:** todos los demás

---

## Antecedentes

Este sistema evolucionó de una operación manual de exit poll usada en elecciones venezolanas. El flujo original requería:
- Encuestadores de campo llamando resultados por teléfono a una sala de coordinación
- Transcripción manual a una base de datos Access
- Cálculo de pesos y agregación en Excel

El proyecto de automatización comenzó replicando el core de Excel en Python, validado contra el modelo legacy, y luego reemplazó progresivamente cada paso manual con componentes automatizados.

La carpeta `legacy/` contiene `Core.xlsx` — el modelo Excel original que este sistema vino a reemplazar.

---

## Estructura del repositorio

```
exit_poll/
├── backend/
│   ├── app.py                  # Dashboard FastAPI, vista live, endpoints TM/IA
│   ├── schema.sql              # Esquema de la base de datos
│   ├── init_db.py              # Inicialización / reset de BD
│   ├── convertidor_tm.py       # Conversor TM CNE (formatos 2015/2018)
│   ├── convertidor_cne2024.py  # Ingesta resultados CNE 2024 (11.927 centros)
│   ├── import_2007_esdata.py   # Importador agregado Referendum 2007 Esdata/Wayback
│   ├── import_2009_esdata.py   # Importador agregado Enmienda 2009 Esdata/Wayback
│   ├── import_2018_venpres_a.py # Normalizador VENPRES-A 2018 por centro
│   ├── import_2012_gobernadores.py # Colección histórica Gobernadores 2012
│   ├── cargador_tm.py          # Cargador diferencial de TM
│   ├── agent.py                # Abstracción de proveedores IA y llamadas estructuradas
│   ├── analista_ia.py          # Analista en vivo determinístico
│   ├── calculador_pesos.py     # Calculador de pesos jerárquico
│   ├── selector_muestra.py     # Selector automático de muestra con filtro de elegibilidad
│   ├── generador_heatmap.py    # Generador de choropleth Folium
│   ├── generador_dashboard.py  # Generador de dashboard HTML autónomo
│   ├── TM_ESTANDAR.md          # Spec del CSV interno (15 columnas)
│   └── exitpoll.db             # Base de datos SQLite
├── test_flujo.py               # Tests de jornada electoral + guardrail IA
├── test_ai_validation.py       # Tests de validación estadística
├── test_cargador_tm.py         # Tests del cargador diferencial TM
├── test_geo_pesos.py           # Tests de pesos + matching de geografía
└── legacy/
    ├── Core.xlsx               # Modelo Excel original (referencia)
    ├── scripts_raiz/           # Scripts pre-backend (fases 1-6)
    ├── ai_configs/             # Instrucciones IA por herramienta (archivadas)
    └── outputs/                # Artefactos generados (archivados)
```

---

## Registro de desarrollo

Ver [BITACORA.md](./BITACORA.md) para la historia completa de desarrollo en todas las fases.

---

## Colaboración con IA en el desarrollo

Este proyecto fue desarrollado con la asistencia de múltiples agentes de IA
trabajando en roles complementarios:

- **GitHub Copilot** — autocompletado de código y auditoría de seguridad del codebase y la configuración de Azure
- **OpenAI Codex** — implementación autónoma, reescritura de historia git, auditoría de dependencias y deploy en Azure
- **Google Gemini** — revisión de arquitectura y análisis de superficie de vulnerabilidades públicas
- **Anthropic Claude** — decisiones técnicas, prompt engineering y estrategia de orquestación multi-agente

Cada agente aportó capacidades distintas, reflejando un flujo de desarrollo
multi-agente real donde ningún modelo lo hizo todo.

---

*Proyecto individual. Desarrollo activo desde 2024. Construido como parte de trabajo de consultoría independiente en tecnología electoral.*
