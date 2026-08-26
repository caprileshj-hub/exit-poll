-- =============================================================
-- EXIT POLL VENEZUELA - Schema de Base de Datos
-- SQLite
-- =============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- =============================================================
-- BLOQUE 1: GEOGRAFIA
-- Fuente: archivo TM del CNE (se recarga por eleccion)
-- =============================================================

CREATE TABLE IF NOT EXISTS estados (
    id              INTEGER PRIMARY KEY,
    codigo_cne      TEXT NOT NULL UNIQUE,   -- "01"=DC, "23"=Zulia
    nombre          TEXT NOT NULL,
    es_excepcion    INTEGER DEFAULT 0       -- 1: DC, La Guaira, Miranda-Caracas
                                            -- seleccion por parroquia en vez de estado
);

CREATE TABLE IF NOT EXISTS municipios (
    id              INTEGER PRIMARY KEY,
    id_estado       INTEGER NOT NULL REFERENCES estados(id),
    codigo_cne      TEXT NOT NULL,          -- "01" dentro del estado
    nombre          TEXT NOT NULL,
    es_excepcion    INTEGER DEFAULT 0,      -- 1: Chacao, Baruta, El Hatillo, Sucre (Miranda-Caracas)
                                            -- pesos calculados por parroquia, no por municipio
    UNIQUE(id_estado, codigo_cne)
);

CREATE TABLE IF NOT EXISTS parroquias (
    id              INTEGER PRIMARY KEY,
    id_municipio    INTEGER NOT NULL REFERENCES municipios(id),
    codigo_cne      TEXT NOT NULL,          -- "01" dentro del municipio
    nombre          TEXT NOT NULL,
    UNIQUE(id_municipio, codigo_cne)
);

CREATE TABLE IF NOT EXISTS circuitos (
    id              INTEGER PRIMARY KEY,
    id_estado       INTEGER NOT NULL REFERENCES estados(id),
    numero          INTEGER NOT NULL,       -- numero de circuito AN
    nombre          TEXT,
    UNIQUE(id_estado, numero)
);

CREATE TABLE IF NOT EXISTS circunscripciones_indigenas (
    id              INTEGER PRIMARY KEY,
    nombre          TEXT NOT NULL UNIQUE    -- OCCIDENTE, SUR, ORIENTE
);


-- =============================================================
-- BLOQUE 2: CENTROS ELECTORALES
-- Fuente: archivo TM del CNE
-- Se actualiza con cada nueva tabla de mesa
-- =============================================================

CREATE TABLE IF NOT EXISTS centros (
    codigo_cne      TEXT PRIMARY KEY,       -- codigo CTRO_PROP del CNE (8-9 digitos)
    nombre          TEXT NOT NULL,
    direccion       TEXT,
    id_parroquia    INTEGER REFERENCES parroquias(id),
    id_municipio    INTEGER REFERENCES municipios(id),
    id_estado       INTEGER NOT NULL REFERENCES estados(id),
    id_circuito     INTEGER REFERENCES circuitos(id),           -- solo elecciones AN
    id_circ_indigena INTEGER REFERENCES circunscripciones_indigenas(id), -- solo indigena
    num_mesas       INTEGER DEFAULT 0,
    num_electores   INTEGER DEFAULT 0,
    lat             REAL,
    lon             REAL,
    riesgo          INTEGER DEFAULT 1,      -- 1=bajo, 2=medio, 3=alto
    radio_m         INTEGER DEFAULT 300,    -- radio GPS valido en metros
    activo          INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_centros_estado ON centros(id_estado);
CREATE INDEX IF NOT EXISTS idx_centros_municipio ON centros(id_municipio);

CREATE TABLE IF NOT EXISTS election_centers (
    eleccion_id     INTEGER NOT NULL REFERENCES elecciones(id),
    centro_id       TEXT NOT NULL REFERENCES centros(codigo_cne),
    eligible        INTEGER NOT NULL DEFAULT 1,
    source_file     TEXT,
    campos_extra    TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    PRIMARY KEY(eleccion_id, centro_id),
    CHECK(eligible IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_ec_eleccion ON election_centers(eleccion_id);
CREATE INDEX IF NOT EXISTS idx_ec_centro ON election_centers(centro_id);

CREATE TABLE IF NOT EXISTS tm_ingestion_logs (
    id                  INTEGER PRIMARY KEY,
    eleccion_id          INTEGER NOT NULL REFERENCES elecciones(id),
    source_files         TEXT NOT NULL,
    detected_columns     TEXT,
    field_notes          TEXT,
    match_stats          TEXT,
    user                 TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tm_cargas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    eleccion_id          INTEGER REFERENCES elecciones(id),
    periodo_tm           TEXT NOT NULL,
    fecha_tm             TEXT NOT NULL,
    filename             TEXT NOT NULL,
    file_hash            TEXT,
    file_size            INTEGER,
    mime_type            TEXT,
    detected_format      TEXT,
    parser_mode          TEXT,
    loaded_at            TEXT DEFAULT (datetime('now')),
    frame_before_hash    TEXT,
    frame_after_hash     TEXT,
    centros_before       INTEGER NOT NULL DEFAULT 0,
    centros_after        INTEGER NOT NULL DEFAULT 0,
    electores_before     INTEGER NOT NULL DEFAULT 0,
    electores_after      INTEGER NOT NULL DEFAULT 0,
    mesas_before         INTEGER NOT NULL DEFAULT 0,
    mesas_after          INTEGER NOT NULL DEFAULT 0,
    report_json          TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'completed'
);

CREATE INDEX IF NOT EXISTS idx_tm_cargas_eleccion ON tm_cargas(eleccion_id);
CREATE INDEX IF NOT EXISTS idx_tm_cargas_loaded ON tm_cargas(loaded_at);

CREATE TABLE IF NOT EXISTS tm_carga_cambios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    carga_id         INTEGER NOT NULL REFERENCES tm_cargas(id),
    codigo_centro    TEXT NOT NULL,
    tipo_cambio      TEXT NOT NULL,
    before_json      TEXT,
    after_json       TEXT
);

CREATE INDEX IF NOT EXISTS idx_tm_cambios_carga ON tm_carga_cambios(carga_id);
CREATE INDEX IF NOT EXISTS idx_tm_cambios_tipo ON tm_carga_cambios(tipo_cambio);


-- =============================================================
-- BLOQUE 3: ELECCIONES Y CANDIDATOS
-- =============================================================

CREATE TABLE IF NOT EXISTS elecciones (
    id              INTEGER PRIMARY KEY,
    nombre          TEXT NOT NULL,
    tipo            TEXT NOT NULL CHECK(tipo IN ('nacional','regional','municipal','asamblea')),
    fecha           TEXT NOT NULL,          -- ISO: 2024-07-28
    hora_apertura   TEXT NOT NULL DEFAULT '07:00',
    hora_cierre     TEXT NOT NULL DEFAULT '18:00',
    activa          INTEGER DEFAULT 0,      -- solo una activa a la vez
    notas           TEXT,
    CHECK(activa IN (0,1))
);

CREATE TABLE IF NOT EXISTS candidatos (
    id              INTEGER PRIMARY KEY,
    id_eleccion     INTEGER NOT NULL REFERENCES elecciones(id),
    nombre          TEXT NOT NULL,
    foto_url        TEXT,
    partido         TEXT,
    bando           TEXT CHECK(bando IN ('gobierno','oposicion','otro')),
    tipo            TEXT NOT NULL CHECK(tipo IN ('nominal','lista','indigena','unico')),
    id_estado       INTEGER REFERENCES estados(id),         -- regional/lista AN
    id_municipio    INTEGER REFERENCES municipios(id),      -- municipal
    id_circuito     INTEGER REFERENCES circuitos(id),       -- nominal AN
    id_circ_indigena INTEGER REFERENCES circunscripciones_indigenas(id),
    orden           INTEGER DEFAULT 1       -- orden en pantalla de la app
);


-- =============================================================
-- BLOQUE 4: MUESTRA Y PESOS
-- Generados en Fase -1
-- =============================================================

CREATE TABLE IF NOT EXISTS muestra (
    id              INTEGER PRIMARY KEY,
    id_eleccion     INTEGER NOT NULL REFERENCES elecciones(id),
    codigo_centro   TEXT NOT NULL REFERENCES centros(codigo_cne),
    tipo_centro     TEXT CHECK(tipo_centro IN ('bisagra','bastion','volumen','estandar')),
    activo          INTEGER DEFAULT 1,
    motivo          TEXT,
    agregado_por    TEXT,
    score_snapshot  REAL,
    confianza_snapshot REAL,
    rol_muestra     TEXT DEFAULT 'titular' CHECK(rol_muestra IN ('titular','reserva','removido')),
    generacion_id   INTEGER,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(id_eleccion, codigo_centro)
);

CREATE TABLE IF NOT EXISTS muestra_generaciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_eleccion         INTEGER NOT NULL REFERENCES elecciones(id),
    tm_hash             TEXT NOT NULL,
    metodo              TEXT NOT NULL,
    sample_size         INTEGER NOT NULL,
    reserve_size        INTEGER NOT NULL DEFAULT 0,
    seed                INTEGER NOT NULL,
    cuotas_json         TEXT NOT NULL,
    frame_count         INTEGER NOT NULL,
    frame_electores     INTEGER NOT NULL,
    algorithm_version   TEXT NOT NULL,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS muestra_sustituciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_eleccion         INTEGER NOT NULL REFERENCES elecciones(id),
    centro_removido     TEXT NOT NULL REFERENCES centros(codigo_cne),
    centro_sustituto    TEXT NOT NULL REFERENCES centros(codigo_cne),
    motivo              TEXT NOT NULL,
    usuario             TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pesos (
    id_muestra      INTEGER PRIMARY KEY REFERENCES muestra(id),
    peso_parroquia  REAL DEFAULT 0,
    peso_municipio  REAL DEFAULT 0,
    peso_estado     REAL DEFAULT 0,
    peso_nacion     REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS centros_candidatos (
    codigo_centro   TEXT NOT NULL REFERENCES centros(codigo_cne),
    id_candidato    INTEGER NOT NULL REFERENCES candidatos(id),
    PRIMARY KEY(codigo_centro, id_candidato)
    -- generada automaticamente en Fase -1 segun tipo de eleccion y circuito
);


-- =============================================================
-- BLOQUE 5: OPERACION - ENCUESTADORES
-- =============================================================

CREATE TABLE IF NOT EXISTS encuestadores (
    telefono        TEXT PRIMARY KEY,       -- +58414XXXXXXX (es el ID)
    nombre          TEXT NOT NULL,
    codigo_centro   TEXT NOT NULL REFERENCES centros(codigo_cne),
    id_eleccion     INTEGER NOT NULL REFERENCES elecciones(id),
    activo          INTEGER DEFAULT 1,
    registrado_at   TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_enc_eleccion ON encuestadores(id_eleccion);
CREATE INDEX IF NOT EXISTS idx_enc_centro ON encuestadores(codigo_centro);


-- =============================================================
-- BLOQUE 6: OPERACION - VOTOS EN TIEMPO REAL
-- =============================================================

CREATE TABLE IF NOT EXISTS sms_raw (
    id              INTEGER PRIMARY KEY,
    from_number     TEXT NOT NULL,          -- numero remitente
    contenido       TEXT NOT NULL,          -- SMS crudo recibido
    recibido_at     TEXT NOT NULL DEFAULT (datetime('now')),
    procesado       INTEGER DEFAULT 0,
    error           TEXT,                   -- NULL si procesado ok
    CHECK(procesado IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_sms_numero ON sms_raw(from_number);
CREATE INDEX IF NOT EXISTS idx_sms_procesado ON sms_raw(procesado);

CREATE TABLE IF NOT EXISTS votos (
    id              INTEGER PRIMARY KEY,
    id_sms          INTEGER NOT NULL REFERENCES sms_raw(id),
    codigo_centro   TEXT NOT NULL REFERENCES centros(codigo_cne),
    id_candidato    INTEGER NOT NULL REFERENCES candidatos(id),
    telefono        TEXT NOT NULL REFERENCES encuestadores(telefono),
    hora            TEXT NOT NULL,          -- timestamp real del SMS (ISO)
    turno           INTEGER NOT NULL,       -- calculado: floor((hora-apertura)/1200)
    lat             REAL,
    lon             REAL,
    distancia_m     INTEGER,                -- distancia al centro de votacion
    valido          INTEGER DEFAULT 1,      -- 0 si GPS fuera de radio
    CHECK(valido IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_votos_centro ON votos(codigo_centro);
CREATE INDEX IF NOT EXISTS idx_votos_turno ON votos(turno);
CREATE INDEX IF NOT EXISTS idx_votos_telefono ON votos(telefono);
CREATE INDEX IF NOT EXISTS idx_votos_valido ON votos(valido);


-- =============================================================
-- BLOQUE 7: AUDITORIA INTERNA
-- Solo visible para operadores, nunca para clientes
-- =============================================================

CREATE TABLE IF NOT EXISTS alertas (
    id              INTEGER PRIMARY KEY,
    tipo            TEXT NOT NULL CHECK(tipo IN (
                        'bajo_meta',
                        'sobre_meta',
                        'sin_reporte',
                        'gps_invalido',
                        'numero_no_registrado',
                        'fraude_patron'
                    )),
    codigo_centro   TEXT REFERENCES centros(codigo_cne),
    telefono        TEXT,
    turno           INTEGER,
    detalle         TEXT,
    creado_at       TEXT DEFAULT (datetime('now')),
    atendido        INTEGER DEFAULT 0,
    CHECK(atendido IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_alertas_atendido ON alertas(atendido);
CREATE INDEX IF NOT EXISTS idx_alertas_centro ON alertas(codigo_centro);


-- =============================================================
-- BLOQUE 7B: RESULTADOS HISTORICOS
-- Para calcular representatividad de centros al seleccionar muestra
-- =============================================================

CREATE TABLE IF NOT EXISTS resultados_historicos (
    id              INTEGER PRIMARY KEY,
    codigo_centro   TEXT NOT NULL,              -- codigo CNE del centro
    eleccion_ref    TEXT NOT NULL,              -- nombre referencia (ej: "2024-presidencial")
    votos_validos   INTEGER NOT NULL DEFAULT 0,
    votos_gobierno  INTEGER NOT NULL DEFAULT 0, -- total bando gobierno
    votos_oposicion INTEGER NOT NULL DEFAULT 0, -- total bando oposicion
    votos_otros     INTEGER NOT NULL DEFAULT 0,
    electores_inscritos INTEGER,
    votantes        INTEGER,
    votos_nulos     INTEGER,
    pct_gobierno    REAL,                       -- % gobierno en este centro
    pct_oposicion   REAL,                       -- % oposicion en este centro
    pct_otros       REAL,
    participacion   REAL,
    incluye_exterior INTEGER,
    granularidad    TEXT,
    fuente          TEXT,
    corte_fuente    TEXT,
    notas           TEXT,
    num_mesas       INTEGER,
    detalle_otros_json TEXT,
    UNIQUE(codigo_centro, eleccion_ref)
);

CREATE INDEX IF NOT EXISTS idx_rh_centro ON resultados_historicos(codigo_centro);
CREATE INDEX IF NOT EXISTS idx_rh_eleccion ON resultados_historicos(eleccion_ref);

CREATE TABLE IF NOT EXISTS historico_fuentes (
    eleccion_ref    TEXT PRIMARY KEY,
    fuente          TEXT NOT NULL,
    granularidad    TEXT NOT NULL,
    cobertura_pct   REAL,
    comparabilidad  TEXT NOT NULL DEFAULT 'directa',
    notas           TEXT,
    incluye_exterior INTEGER,
    corte_fuente    TEXT,
    centros_cubiertos INTEGER,
    mesas_cubiertas INTEGER,
    electores_inscritos INTEGER,
    votantes        INTEGER,
    votos_validos   INTEGER,
    votos_nulos     INTEGER,
    votos_gobierno  INTEGER,
    votos_oposicion INTEGER,
    votos_otros     INTEGER,
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS centro_codigos (
    codigo_cne      TEXT NOT NULL,
    codigo_alterno  TEXT NOT NULL,
    tipo_codigo     TEXT NOT NULL,
    fuente          TEXT NOT NULL,
    confianza_match REAL NOT NULL DEFAULT 1.0,
    created_at      TEXT DEFAULT (datetime('now')),
    PRIMARY KEY(codigo_cne, codigo_alterno, tipo_codigo)
);

CREATE INDEX IF NOT EXISTS idx_cc_alt ON centro_codigos(codigo_alterno);

CREATE TABLE IF NOT EXISTS centro_snapshot (
    codigo_cne      TEXT NOT NULL,
    eleccion_ref    TEXT NOT NULL,
    nombre_centro   TEXT,
    num_mesas       INTEGER DEFAULT 0,
    num_electores   INTEGER DEFAULT 0,
    fuente          TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    PRIMARY KEY(codigo_cne, eleccion_ref)
);

CREATE INDEX IF NOT EXISTS idx_cs_ref ON centro_snapshot(eleccion_ref);

-- =============================================================
-- BLOQUE 7C: ESTUDIOS HISTORICOS Y RESULTADOS OFICIALES
-- Resultados por mesa y reportes de campo acumulados por turno.
-- =============================================================

CREATE TABLE IF NOT EXISTS resultados_mesa (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    id_eleccion     INTEGER NOT NULL REFERENCES elecciones(id),
    codigo_cne      TEXT    NOT NULL REFERENCES centros(codigo_cne),
    numero_mesa     INTEGER NOT NULL,
    votos_gov       INTEGER NOT NULL DEFAULT 0,
    votos_opos      INTEGER NOT NULL DEFAULT 0,
    votos_otros     INTEGER NOT NULL DEFAULT 0,
    votos_nulos     INTEGER NOT NULL DEFAULT 0,
    votos_validos   INTEGER NOT NULL DEFAULT 0,
    inscritos       INTEGER NOT NULL DEFAULT 0,
    fuente          TEXT,
    UNIQUE(id_eleccion, codigo_cne, numero_mesa)
);

CREATE INDEX IF NOT EXISTS idx_rm_eleccion ON resultados_mesa(id_eleccion);
CREATE INDEX IF NOT EXISTS idx_rm_centro ON resultados_mesa(codigo_cne);

CREATE TABLE IF NOT EXISTS reportes_campo (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    id_eleccion     INTEGER NOT NULL REFERENCES elecciones(id),
    codigo_cne      TEXT    NOT NULL REFERENCES centros(codigo_cne),
    turno           INTEGER NOT NULL,
    timestamp_rx    DATETIME DEFAULT CURRENT_TIMESTAMP,
    votos_gov       INTEGER NOT NULL DEFAULT 0,
    votos_opos      INTEGER NOT NULL DEFAULT 0,
    votos_otros     INTEGER NOT NULL DEFAULT 0,
    votos_nulos     INTEGER NOT NULL DEFAULT 0,
    UNIQUE(id_eleccion, codigo_cne, turno) ON CONFLICT REPLACE
);

CREATE INDEX IF NOT EXISTS idx_rc_eleccion ON reportes_campo(id_eleccion);
CREATE INDEX IF NOT EXISTS idx_rc_centro ON reportes_campo(codigo_cne);

CREATE VIEW IF NOT EXISTS v_proyeccion AS
WITH ultimo AS (
    SELECT id_eleccion, codigo_cne, MAX(turno) AS t
    FROM reportes_campo GROUP BY id_eleccion, codigo_cne
),
campo AS (
    SELECT rc.* FROM reportes_campo rc
    JOIN ultimo u ON rc.id_eleccion=u.id_eleccion
                 AND rc.codigo_cne=u.codigo_cne
                 AND rc.turno=u.t
)
SELECT
    c2.id_eleccion,
    ct.id_estado,
    ct.nombre                  AS centro,
    ct.num_electores           AS peso,
    campo.votos_gov,
    campo.votos_opos,
    campo.votos_otros,
    campo.turno                AS ultimo_turno,
    ROUND(campo.votos_gov  * 100.0 /
          NULLIF(campo.votos_gov+campo.votos_opos+campo.votos_otros,0),2) AS pct_gov,
    ROUND(campo.votos_opos * 100.0 /
          NULLIF(campo.votos_gov+campo.votos_opos+campo.votos_otros,0),2) AS pct_opos
FROM campo
JOIN centros ct     ON ct.codigo_cne   = campo.codigo_cne
JOIN muestra c2     ON c2.codigo_centro = campo.codigo_cne
                   AND c2.id_eleccion   = campo.id_eleccion;

CREATE VIEW IF NOT EXISTS v_evaluacion AS
WITH campo_final AS (
    SELECT rc.* FROM reportes_campo rc
    JOIN (SELECT id_eleccion, codigo_cne, MAX(turno) t
          FROM reportes_campo GROUP BY id_eleccion, codigo_cne) u
      ON rc.id_eleccion=u.id_eleccion AND rc.codigo_cne=u.codigo_cne AND rc.turno=u.t
),
cne_centro AS (
    SELECT id_eleccion, codigo_cne,
           SUM(votos_gov)     AS votos_gov,
           SUM(votos_opos)    AS votos_opos,
           SUM(votos_validos) AS votos_validos
    FROM resultados_mesa GROUP BY id_eleccion, codigo_cne
)
SELECT
    m.id_eleccion,
    ct.nombre   AS centro,
    ct.id_estado,
    ROUND(cf.votos_gov  *100.0/NULLIF(cf.votos_gov+cf.votos_opos+cf.votos_otros,0),2)
                AS campo_pct_gov,
    ROUND(cf.votos_opos *100.0/NULLIF(cf.votos_gov+cf.votos_opos+cf.votos_otros,0),2)
                AS campo_pct_opos,
    ROUND(cc.votos_gov  *100.0/NULLIF(cc.votos_validos,0),2)  AS cne_pct_gov,
    ROUND(cc.votos_opos *100.0/NULLIF(cc.votos_validos,0),2)  AS cne_pct_opos,
    ROUND(
        (cf.votos_gov *100.0/NULLIF(cf.votos_gov+cf.votos_opos+cf.votos_otros,0)) -
        (cc.votos_gov *100.0/NULLIF(cc.votos_validos,0))
    ,2) AS delta_gov_pp
FROM muestra m
JOIN centros ct ON ct.codigo_cne = m.codigo_centro
LEFT JOIN campo_final cf ON cf.id_eleccion=m.id_eleccion AND cf.codigo_cne=m.codigo_centro
LEFT JOIN cne_centro  cc ON cc.id_eleccion=m.id_eleccion AND cc.codigo_cne=m.codigo_centro;

-- =============================================================
-- BLOQUE 7D: CONFIGURACION DE IA
-- Proveedores remotos ligeros; sin modelos locales.
-- =============================================================

CREATE TABLE IF NOT EXISTS config (
    provider      TEXT PRIMARY KEY,
    api_key       TEXT,
    model         TEXT NOT NULL,
    temperature   REAL NOT NULL DEFAULT 0.3,
    max_tokens    INTEGER NOT NULL DEFAULT 300,
    active        INTEGER NOT NULL DEFAULT 0,
    updated_at    TEXT DEFAULT (datetime('now')),
    CHECK(provider IN ('openai','groq','anthropic','gemini')),
    CHECK(active IN (0,1))
);


-- =============================================================
-- BLOQUE 8: CLIENTES Y ACCESOS
-- Sistema de producto - cada cliente ve solo lo que pago
-- La auditoria es exclusivamente interna, nunca para clientes
-- =============================================================

CREATE TABLE IF NOT EXISTS clientes (
    id              INTEGER PRIMARY KEY,
    nombre          TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    hash_clave      TEXT NOT NULL,
    activo          INTEGER DEFAULT 1,
    creado_at       TEXT DEFAULT (datetime('now')),
    CHECK(activo IN (0,1))
);

CREATE TABLE IF NOT EXISTS contratos (
    id              INTEGER PRIMARY KEY,
    id_cliente      INTEGER NOT NULL REFERENCES clientes(id),
    id_eleccion     INTEGER NOT NULL REFERENCES elecciones(id),
    retardo_min     INTEGER DEFAULT 0,      -- 0=live, 30, 60, -1=solo al cierre
    UNIQUE(id_cliente, id_eleccion)
);

CREATE TABLE IF NOT EXISTS accesos_geograficos (
    id              INTEGER PRIMARY KEY,
    id_contrato     INTEGER NOT NULL REFERENCES contratos(id),
    nivel           TEXT NOT NULL CHECK(nivel IN ('nacional','estado','municipio')),
    id_referencia   INTEGER                 -- id_estado o id_municipio, NULL si nacional
);

CREATE TABLE IF NOT EXISTS accesos_vistas (
    id              INTEGER PRIMARY KEY,
    id_contrato     INTEGER NOT NULL REFERENCES contratos(id),
    vista           TEXT NOT NULL CHECK(vista IN (
                        'heatmap',
                        'tendencias',
                        'tortas',
                        'barras',
                        'tabla_centros'
                    ))
);


-- =============================================================
-- BLOQUE 9: ESTUDIOS HISTÓRICOS — comparación exit poll vs oficial
-- Carga manual por ámbito. No depende de centros ni FK geográficas.
-- =============================================================

CREATE TABLE IF NOT EXISTS historico_estudios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    eleccion_ref    TEXT NOT NULL,
    ambito          TEXT NOT NULL,          -- 'NACIONAL' o codigo_cne del estado
    nombre          TEXT NOT NULL,          -- 'Nacional' / 'Zulia' / etc.
    nombre_eleccion TEXT,                   -- solo en ambito='NACIONAL'
    fecha_eleccion  TEXT,                   -- solo en ambito='NACIONAL'
    pct_gov         REAL NOT NULL DEFAULT 0,
    pct_opos        REAL NOT NULL DEFAULT 0,
    pct_otros       REAL NOT NULL DEFAULT 0,
    num_centros     INTEGER NOT NULL DEFAULT 0,
    fuente          TEXT,
    notas           TEXT,
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(eleccion_ref, ambito)
);

CREATE TABLE IF NOT EXISTS historico_oficial (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    eleccion_ref    TEXT NOT NULL,
    ambito          TEXT NOT NULL,
    nombre          TEXT NOT NULL,
    nombre_eleccion TEXT,
    fecha_eleccion  TEXT,
    pct_gov         REAL NOT NULL DEFAULT 0,
    pct_opos        REAL NOT NULL DEFAULT 0,
    pct_otros       REAL NOT NULL DEFAULT 0,
    total_votos     INTEGER NOT NULL DEFAULT 0,
    fuente          TEXT,
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(eleccion_ref, ambito)
);

CREATE TABLE IF NOT EXISTS historico_estudios_turnos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    eleccion_ref    TEXT NOT NULL,
    ambito          TEXT NOT NULL DEFAULT 'NACIONAL',
    turno           INTEGER NOT NULL,
    hora_label      TEXT,                   -- ej: '08:00–09:30'
    pct_gov         REAL NOT NULL DEFAULT 0,
    pct_opos        REAL NOT NULL DEFAULT 0,
    pct_otros       REAL NOT NULL DEFAULT 0,
    num_centros     INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(eleccion_ref, ambito, turno)
);

CREATE INDEX IF NOT EXISTS idx_he_ref   ON historico_estudios(eleccion_ref);
CREATE INDEX IF NOT EXISTS idx_ho_ref   ON historico_oficial(eleccion_ref);
CREATE INDEX IF NOT EXISTS idx_het_ref  ON historico_estudios_turnos(eleccion_ref);
