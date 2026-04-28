# Exit Poll Venezuela

Automated electoral survey platform for Venezuelan elections. Replaces a manual workflow (paper forms → phone calls → Access database → Excel processing) with an end-to-end automated system built around SMS-based data collection — the only reliable channel in Venezuela's low-connectivity field conditions.

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

The project is in active development. **Phase 6 is complete:**

### ✅ Completed
- **Database** — SQLite with WAL mode, 19 tables across 8 functional blocks (geography, voting centers, elections, sample design, surveyors, votes, audit, client access)
- **TM Ingestion Pipeline** — Converts CNE electoral registry files (Excel/CSV, formats 2015 and 2018) to internal standard format; differential loader never overwrites manually-entered GPS coordinates or risk ratings
- **Sample Design** — Automatic selection of representative voting centers using historical CNE results (11,927 centers from 2024); classifies centers as *swing*, *bastion*, *volume*, or *standard*
- **Hierarchical Weight Calculator** — Four-level weighting (precinct → municipality → state → national) with geographic exception rules for Distrito Capital, La Guaira, and Miranda-Caracas
- **Heatmap Generator** — Folium-based choropleth at state (ADM1) and municipality (ADM2) level; spatial lookup cached for 332 municipalities
- **Standalone HTML Dashboard** — Single-file output: Folium map (58%) + Plotly trend charts (42%); click on state polygon to see local trend; blue-white-red symmetric palette with ±3% technical tie threshold
- **FastAPI Configuration Dashboard** — 30 routes; manages elections, candidates (with photos), sample selection, weight editing, TM uploads, and visualization preview
- **CNE 2024 Data Integration** — Ingested complete 2024 electoral results (11,927 centers) from the vzlapi source into `resultados_historicos` for representativeness scoring. Required writing a dedicated converter (`convertidor_cne2024.py`) because the 2024 Tabla de Mesa format differed structurally from both the 2015 and 2018 converters already in the system. This is the concrete case motivating the AI normalization component: each new electoral cycle — or election type — arrives with a different TM structure, and writing a new converter each time does not scale.
- **Technical specification document** — CIS-style methodology card with calculated margin of error, printable from the dashboard

### 🔄 In Development (Phase 7)
- AI-powered TM normalization (see section below)
- SMS parser and GPS validation in FastAPI backend
- Android APK (surveyor UI + SMS sending + offline queue)
- Android Gateway (SMS reader → HTTP POST)
- Internal audit dashboard (center status board, surveyor panel, fraud alerts)
- Client-facing charts (pie/bar views)

---

## AI Component: Dynamic TM Normalization

The CNE's *Tabla de Mesa* is the foundational input for every election. It contains the complete registry of voting centers, precincts, voter counts, and geographic codes — but **the format changes with every electoral cycle**. Column names shift, encoding varies, sheets are renamed, and new geographic entities appear (or disappear).

The current implementation handles formats 2015 and 2018 via explicit converter mappings (`convertidor_tm.py`). Every new election requires manually writing a new converter.

The AI component under development replaces this with a **dynamic normalization layer** that:
- Receives a raw TM file (any format, any year)
- Infers column mappings, encoding, and structure without hard-coded rules
- Identifies geographic changes (new centers, merged precincts, reclassified municipalities)
- Flags structural anomalies for human review before loading
- Outputs a validated CSV conforming to the 15-column internal standard (`TM_ESTANDAR.md`)

This makes the system resilient to CNE format changes without code modifications between electoral cycles.

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

19 tables organized in 8 blocks:

| Block | Tables |
|-------|--------|
| Geography | `estados`, `municipios`, `parroquias`, `circuitos`, `circunscripciones_indigenas` |
| Voting Centers | `centros` |
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
| Data Processing | pandas, openpyxl |
| Mobile (planned) | Android native |
| Deploy | Azure (Student) |

---

## Sample Design Rules

**General rule:** 2 voting centers per state

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
exit poll/
├── backend/
│   ├── app.py                  # FastAPI dashboard (30 routes)
│   ├── schema.sql              # Database schema (19 tables)
│   ├── init_db.py              # DB initialization / reset
│   ├── convertidor_tm.py       # CNE TM converter (2015/2018 formats)
│   ├── convertidor_cne2024.py  # CNE 2024 results ingestion (11,927 centers)
│   ├── cargador_tm.py          # Differential TM loader
│   ├── calculador_pesos.py     # Hierarchical weight calculator
│   ├── selector_muestra.py     # Automatic sample selector
│   ├── generador_heatmap.py    # Folium choropleth generator
│   ├── generador_dashboard.py  # Standalone HTML dashboard generator
│   ├── TM_ESTANDAR.md          # Internal CSV spec (15 columns)
│   └── exitpoll.db             # SQLite database
└── legacy/
    └── Core.xlsx               # Original Excel model (reference)
```

---

## Development Log

See [BITACORA.md](./BITACORA.md) for the full development history across all phases.

---

*Solo project. Active development since 2024. Built as part of independent consulting work in electoral technology.*
