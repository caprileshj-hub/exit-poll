# Exit Poll Venezuela

> Lee este documento en español: [README.es.md](./README.es.md)

End-to-end exit poll platform for Venezuelan elections. Replaces a manual workflow (paper forms → phone calls → Access database → Excel) with an automated system built around SMS-based data collection — the only reliable channel in Venezuela's low-connectivity field conditions. Results flow from the field into a weighted, real-time heatmap and trend dashboard. A deterministic AI analyst embedded in the live view reads incoming data and provides plain-language interpretations of the national trend, individual states, and each candidate's position — with explicit guardrails against premature winner declarations.

---

## The Problem

Running an exit poll in Venezuela involves three compounding challenges:

1. **No mobile data in the field.** Surveyors work at voting centers with no reliable internet. Traditional app-based data collection fails.
2. **Inconsistent official electoral data.** Before each election, the CNE (Venezuela's electoral authority) delivers to registered political parties a *Tabla de Mesa* (TM) — a technical document listing every voting table code, its location within each voting center, and the number of voters assigned to it. The TM is the foundational input for sample design and weight calculation. The problem: its format, column structure, sheet names, and encoding change with every electoral cycle. A rigid parser built for one election breaks on the next.
3. **Manual aggregation is slow and error-prone.** The legacy workflow required a coordinator to receive calls from the field, transcribe votes into Access, and process weighted results in Excel — introducing delays and transcription errors at every step.

This project automates the full pipeline: from field data collection to weighted results visualization.

---

## Architecture

```
[Android APK] → SMS → [Android Gateway] → HTTP POST → [FastAPI Backend] → [SQLite DB] → [HTML Dashboard]
```

**Why SMS?** In rural Venezuelan states, mobile data coverage at voting centers is unreliable or absent. SMS is the only channel that works consistently across the full geographic scope of a national election. Every surveyor has SMS capability regardless of data coverage.

Each SMS carries a complete vote record in ~28 characters:

```
C1234;V2;T1932;L09a7F3b
```

| Field | Description |
|-------|-------------|
| `C`   | CNE voting center code |
| `V`   | Candidate ID (V0 = null vote) |
| `T`   | Local timestamp (HHMM) |
| `L`   | GPS coordinates as Geohash (~38m precision, 6 chars) |

The surveyor's phone number serves as their ID — it never travels in the SMS payload.

---

## Current Status

The project is in active development. **Phase 7 is underway:**

### Completed
- **Database** — SQLite with WAL mode, foreign keys, permanent voting-center registry, election-specific eligibility, audit tables, and client access model
- **TM Ingestion Pipeline** — Keeps the legacy Excel/CSV differential loader for known 2015/2018 formats and adds an AI-assisted multi-format ingestion flow for new CNE files; manually-entered GPS coordinates and risk ratings are never overwritten
- **Sample Design** — Assisted laboratory for selecting centers from the active and historical universe; combines utility score, data confidence, center-level trend, source lineage, and an editable automatic proposal. Uses center/table-level aggregates from 2004, 2006, 2007, 2009, 2012, 2013, and 2024 when available.
- **Hierarchical Weight Calculator** — Four-level weighting (precinct → municipality → state → national) with geographic exception rules for Distrito Capital, La Guaira, and Miranda-Caracas
- **Heatmap Generator** — Folium-based choropleth at state (ADM1) and municipality (ADM2) level; spatial lookup cached for 332 municipalities
- **Standalone HTML Dashboard** — Single-file output: Folium map (58%) + Plotly trend charts (42%); click on state polygon to see local trend; blue-white-red symmetric palette with ±3% technical tie threshold
- **FastAPI Configuration Dashboard** — Manages elections, candidates (with photos and election-specific geography/circuit scope), sample selection, weight editing, legacy TM uploads, AI-assisted TM uploads, and visualization preview
- **CNE 2024 Data Integration** — Ingested complete 2024 electoral results (11,927 centers) from the vzlapi source into `resultados_historicos` for representativeness scoring. Required writing a dedicated converter (`convertidor_cne2024.py`) because the 2024 Tabla de Mesa format differed structurally from both the 2015 and 2018 converters already in the system. This is the concrete case motivating the AI normalization component: each new electoral cycle — or election type — arrives with a different TM structure, and writing a new converter each time does not scale.
- **Historical Studies Module** — Read-only archive for fixed historical studies and official results. Includes presidential studies, legislative 2010, regional governor collections for 2008 and 2012, municipal 2013 studies with center-level reliability audit notes, per-state/detail pages, turnout-cut trend charts, and a versioned seed (`backend/data/historico_estudios_seed.json`) applied idempotently on startup.
- **Technical specification document** — CIS-style methodology card with calculated margin of error, printable from the dashboard
- **Live AI analyst** — Deterministic analyst panel and provider-backed chat with guardrails. It refuses premature trend analysis with the exact phrase `datos insuficientes para establecer tendencias` until minimum opinions, coverage, and comparable cuts are available.

### Historical Dataset RR 2004
- **2004 Recall Referendum** - Center-level aggregate dataset in `backend/resultados_rr2004.csv`, seeded as `2004-revocatorio` into `resultados_historicos` through `backend/seed_resultados_historicos.py`. The recoverable source is Esdata/Wayback; it contains no voter names, ID numbers, or person-level records.
- **Recovered coverage** - 6,265 centers, 8,956,463 valid votes, and 12,980,497 REP 2004 electors. Coverage is not 100% of the official enabled-center universe; it should be read as a partial historical recovery for center-level trend analysis. Even so, it covers more than 90% of national vote/elector volume.
- **Historical convention** - In the recall referendum, `NO` ratifies the government and is stored as `votos_gobierno`; `SI` recalls the president and is stored as `votos_oposicion`. `codigo_centro` and `codigo_cne_nuevo` are the new CNE code; `codigo_viejo` and `codigo_cne_viejo` preserve the old Esdata identifier.

### Historical Dataset 2007 Constitutional Referendum
- **2007 Constitutional Referendum** - Center-level aggregate dataset in `backend/resultados_ref2007.csv`, seeded as `2007-referendum` into `resultados_historicos` through `backend/seed_resultados_historicos.py`.
- **Recovered coverage** - 9,002 centers with results, 29,072 source tables with results and 4,542 source tables without results. Coverage is registered as 86.5% and must be read as a first-bulletin recovery, not a complete official universe.
- **Historical convention** - The source has blocks A and B. `SI` supported the government reform proposal and `NO` opposed it. The stored center trend combines the SI/NO ratio across both blocks while preserving approximate voter volume by averaging valid votes across blocks. The versioned CSV contains no voter names, ID numbers, or person-level records.

### Historical Dataset 2009 Constitutional Amendment
- **2009 Constitutional Amendment** - Center-level aggregate dataset in `backend/resultados_enmienda2009.csv`, seeded as `2009-enmienda` into `resultados_historicos` through `backend/seed_resultados_historicos.py`.
- **Recovered coverage** - 11,233 centers, 34,250 tables with exported center aggregates, 11,504,321 valid votes, and 16,684,405 electors. The source is Esdata/Wayback's `ENMIENDA2009_2boletin` file and is treated as high-coverage but second-bulletin historical recovery.
- **Historical convention** - In the 2009 amendment referendum, `SI` supported the government proposal and is stored as `votos_gobierno`; `NO` is stored as `votos_oposicion`. The versioned CSV contains no voter names, ID numbers, or person-level records.

### Historical Source 2018 Presidential
- **2018 Presidential** - `2018-presidencial` remains a national-only official historical card, not a center-level dataset for sample scoring.
- **Archived CNE evidence** - `backend/data/2018/cne_archivado_nacional.json` records the public subdomain trail and Wayback captures for `www4.cne.gob.ve/ResultadosElecciones2018/`. The archived CNE page preserves national technical-sheet values and candidate percentages through `grafico_participacion.php`.
- **Provisional state-level improvement** - `backend/data/2018/resultados_estadales_provisional.csv` preserves the best available state-level evidence. Turnout reconciles to the final national total, but candidate votes do not reconcile completely (material Bertucci gap), so it is labeled `provisional_no_reconciliado`.
- **Known limitation** - The tested archived territorial AJAX endpoints did not return usable municipality, center, or table results; they returned the CNE placeholder `Esperando Totalizacion de Datos` or empty selectors. The 2018 granular-result recovery remains open until a primary traceable municipality-, table-, or center-level source is found.

### In Development (Phase 7)
- Complete the historical research archive: recover the full PLM exit-poll studies for 2007 and 2009, and obtain traceable table- or center-level election results for 2015 and 2018. The existing 2007/2009 Esdata aggregates and the national-only 2018 historical card do not close these research gaps.
- Production hardening for AI-powered TM normalization: larger-file UX, better manual-resolution workflows, provider rate-limit handling, and stronger fuzzy matching
- SMS parser and GPS validation in FastAPI backend
- Android APK (surveyor UI + SMS sending + offline queue)
- Android Gateway (SMS reader → HTTP POST)
- Internal audit dashboard (center status board, surveyor panel, fraud alerts)
- Client-facing charts (pie/bar views)

---

## AI Component: Dynamic TM Normalization

The CNE's *Tabla de Mesa* is the foundational input for every election. It contains the complete registry of voting centers, precincts, voter counts, and geographic codes — but **the format changes with every electoral cycle**. Column names shift, encoding varies, sheets are renamed, and new geographic entities appear (or disappear).

The system now has two TM ingestion paths:

1. **Legacy deterministic path** — `convertidor_tm.py` plus `cargador_tm.py` handles known Excel/CSV formats and writes through the established differential loader.
2. **AI-assisted multi-format path** — `/tm` can process `.pdf`, `.xlsx`, `.xls`, `.xlsm`, `.csv`, `.docx`, and `.txt` files. It extracts text client-side when possible (SheetJS, mammoth.js, pdf.js) and falls back to server-side extraction (`openpyxl`, `python-docx`, `pdfplumber`) when needed.

The AI path uses the provider configured in `/config`; it does not introduce a separate API key or hard-coded vendor. The AI receives extracted text, discovers the file schema from actual headers and values, returns JSON, and preserves election-specific fields in `campos_extra`.

For each extracted row, the backend:
- Attempts exact matching by likely center identifier (`codigo_centro` or AI-provided match hints)
- Runs fuzzy matching against the historical registry using normalized `nombre_centro + municipio + parroquia`
- Classifies rows as `MATCHED`, `NEW`, `AMBIGUOUS`, `CONFLICT`, or `EXTRACTION_ERROR`
- Blocks confirmation until ambiguous/conflicting rows are resolved
- Respects simulation mode: no database writes when enabled

On confirmation:
- `centros.num_mesas` and `centros.num_electores` are updated when present
- `centros.direccion` is filled only when currently empty
- `lat`, `lon`, `riesgo`, and `radio_m` are never overwritten from a Tabla de Mesa
- `election_centers` links every center in the file to the target election and stores `source_file` plus `campos_extra`
- Centers absent from a new TM are not deleted and are not marked inactive; they simply have no `election_centers` row for that election

---

## Election Types Supported

| Type | Description |
|------|-------------|
| `nacional` | Same candidates at all voting centers |
| `regional` | Different candidates per state |
| `municipal` | Different candidates per municipality |
| `asamblea` | Nominal vote by circuit + list vote by state/party |

---

## Fraud Detection

The backend applies rule-based anomaly detection during real-time ingestion:

- **Floor alert:** < 8 votes per 20-minute interval (surveyor may be inactive)
- **Ceiling alert:** > 25 votes per 20-minute interval (above statistical target)
- **Critical pattern:** 3 consecutive intervals exceeding ceiling → escalated alert
- **GPS validation:** Haversine distance between vote GPS and registered center coordinates; votes outside the configured radius (default 300m, configurable per center) are stored with `valid=false` and do not aggregate
- **Unregistered numbers:** SMS from unknown phones are logged but never counted

All alerts are visible only in the internal audit view. Client dashboards show results only, with no access to operational data.

---

## Client Access Model

The system is a commercial product. Each client sees only what they contracted:

- **Configurable data delay:** Live (0 min), 30 min, 60 min, or results-only at close
- **Geographic scope:** National, state-level, or municipality-level
- **View permissions:** Heatmap, trend charts, pie charts, bar charts, center table
- **Audit views:** Internal operators only — never exposed to clients

---

## Database Structure

Core tables organized by functional block:

| Block | Tables |
|-------|--------|
| Geography | `estados`, `municipios`, `parroquias`, `circuitos`, `circunscripciones_indigenas` |
| Voting Centers | `centros`, `election_centers`, `tm_ingestion_logs` |
| Elections | `elecciones`, `candidatos` |
| Sample Design | `muestra`, `pesos`, `centros_candidatos` |
| Surveyors | `encuestadores` |
| Votes | `sms_raw`, `votos` |
| Internal Audit | `alertas` |
| Client Access | `clientes`, `contratos`, `accesos_geograficos`, `accesos_vistas` |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.x, FastAPI, Jinja2 |
| Database | SQLite (WAL mode, foreign keys) |
| Visualization | Folium, Plotly, Bootstrap 5 |
| Data Processing | pandas, openpyxl, pdfplumber, python-docx |
| AI Providers | OpenAI-compatible clients plus Anthropic through the configured `/config` provider |
| Mobile (planned) | Android native |
| Deploy | Azure (Student) |

---

## Sample Design Rules

**General rule:** 2 voting centers per state

If an election has rows in `election_centers`, the sample selector only considers centers marked eligible for that election. If no eligibility rows exist yet, it falls back to the historical behavior and samples from active centers in the permanent registry.

**Geographic exceptions** (2 centers per precinct instead of per state):
- Distrito Capital
- La Guaira
- Miranda-Caracas: Chacao, Baruta, El Hatillo, Sucre municipalities

**Center classification** (based on historical results):
- **Swing (bisagra):** Competitive centers within ±10% of national result
- **Bastion:** Centers with > 70% dominance by one side
- **Volume:** High voter count, regardless of competitiveness
- **Standard:** All others

---

## Background

This system evolved from a manual exit poll operation used in Venezuelan elections. The original workflow required:
- Field surveyors calling results by phone to a coordination room
- Manual transcription into an Access database
- Weight calculation and aggregation in Excel

The automation project began by replicating the Excel core in Python, validated against the legacy model, then progressively replaced each manual step with automated components.

The `legacy/` folder contains `Core.xlsx` — the original Excel model that this system was built to replace.

---

## Repository Structure

```
exit_poll/
├── backend/
│   ├── app.py                  # FastAPI dashboard, live view, AI TM endpoints
│   ├── schema.sql              # Database schema
│   ├── init_db.py              # DB initialization / reset
│   ├── convertidor_tm.py       # CNE TM converter (2015/2018 formats)
│   ├── convertidor_cne2024.py  # CNE 2024 results ingestion (11,927 centers)
│   ├── import_2007_esdata.py   # Esdata/Wayback 2007 referendum aggregate importer
│   ├── import_2009_esdata.py   # Esdata/Wayback 2009 amendment aggregate importer
│   ├── import_2012_gobernadores.py # Regionales 2012 historical governor collection
│   ├── cargador_tm.py          # Differential TM loader
│   ├── agent.py                # AI provider abstraction and structured calls
│   ├── analista_ia.py          # Deterministic live analyst
│   ├── calculador_pesos.py     # Hierarchical weight calculator
│   ├── selector_muestra.py     # Automatic sample selector with election eligibility filter
│   ├── generador_heatmap.py    # Folium choropleth generator
│   ├── generador_dashboard.py  # Standalone HTML dashboard generator
│   ├── TM_ESTANDAR.md          # Internal CSV spec (15 columns)
│   └── exitpoll.db             # SQLite database
├── test_flujo.py               # Election-day flow + AI guardrail tests
├── test_ai_validation.py       # Statistical validation tests
├── test_cargador_tm.py         # Differential TM loader tests
├── test_geo_pesos.py           # Weights + geography matching tests
└── legacy/
    ├── Core.xlsx               # Original Excel model (reference)
    ├── scripts_raiz/           # Pre-backend scripts (phases 1-6)
    ├── ai_configs/             # Per-tool AI instructions (archived)
    └── outputs/                # Generated artifacts (archived)
```

---

## Development Log

See [BITACORA.md](./BITACORA.md) for the full development history across all phases.

---

## AI Development Collaboration

This project was developed with the assistance of multiple AI agents
working in complementary roles:

- **GitHub Copilot** — code completion and security audit across the codebase and Azure configuration
- **OpenAI Codex** — autonomous implementation, git history rewriting, dependency auditing, and Azure deployment
- **Google Gemini** — architecture review and public vulnerability surface analysis
- **Anthropic Claude** — technical decision-making, prompt engineering, and multi-agent orchestration strategy

Each agent contributed distinct capabilities, reflecting a real-world
multi-agent development workflow where no single model handled everything.

---

*Solo project. Active development since 2024. Built as part of independent consulting work in electoral technology.*
