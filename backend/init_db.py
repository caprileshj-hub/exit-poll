"""
Inicializa la base de datos del Exit Poll a partir del schema.sql
Uso: python init_db.py [--reset]
"""

import sqlite3
import argparse
import os

try:
    from historico_normalizacion import ensure_historico_normalizado_schema
except ImportError:  # pragma: no cover - package import path
    from .historico_normalizacion import ensure_historico_normalizado_schema

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'exitpoll.db')
SQL_PATH = os.path.join(BASE_DIR, 'schema.sql')


def init_db(reset: bool = False) -> sqlite3.Connection:
    if reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f'[!] BD eliminada: {DB_PATH}')

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')

    with open(SQL_PATH, 'r', encoding='utf-8') as f:
        sql = f.read()

    conn.executescript(sql)
    conn.commit()
    print(f'[+] BD inicializada: {DB_PATH}')
    return conn


def migrar(conn: sqlite3.Connection):
    """Aplica migraciones incrementales sobre una BD existente."""
    cols_estados = {r[1] for r in conn.execute('PRAGMA table_info(estados)')}
    if 'codigo_cne' not in cols_estados:
        conn.execute('ALTER TABLE estados ADD COLUMN codigo_cne TEXT')
        conn.execute("UPDATE estados SET codigo_cne = printf('%02d', id) WHERE codigo_cne IS NULL OR TRIM(codigo_cne) = ''")
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_estados_codigo_cne ON estados(codigo_cne)')
        conn.commit()
        print('[~] Migracion: estados.codigo_cne anadida')
    cols = {r[1] for r in conn.execute('PRAGMA table_info(municipios)')}
    if 'es_excepcion' not in cols:
        conn.execute('ALTER TABLE municipios ADD COLUMN es_excepcion INTEGER DEFAULT 0')
        conn.commit()
        print('[~] Migración: municipios.es_excepcion añadida')
    cols_elecciones = {r[1] for r in conn.execute('PRAGMA table_info(elecciones)')}
    if 'notas' not in cols_elecciones:
        conn.execute('ALTER TABLE elecciones ADD COLUMN notas TEXT')
        conn.commit()
        print('[~] Migracion: elecciones.notas anadida')
    cols_muestra = {r[1] for r in conn.execute('PRAGMA table_info(muestra)')}
    for col, ddl in {
        'motivo': 'ALTER TABLE muestra ADD COLUMN motivo TEXT',
        'agregado_por': 'ALTER TABLE muestra ADD COLUMN agregado_por TEXT',
        'score_snapshot': 'ALTER TABLE muestra ADD COLUMN score_snapshot REAL',
        'confianza_snapshot': 'ALTER TABLE muestra ADD COLUMN confianza_snapshot REAL',
        'created_at': "ALTER TABLE muestra ADD COLUMN created_at TEXT",
    }.items():
        if col not in cols_muestra:
            conn.execute(ddl)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_fuentes (
            eleccion_ref    TEXT PRIMARY KEY,
            fuente          TEXT NOT NULL,
            granularidad    TEXT NOT NULL,
            cobertura_pct   REAL,
            comparabilidad  TEXT NOT NULL DEFAULT 'directa',
            notas           TEXT,
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS centro_codigos (
            codigo_cne      TEXT NOT NULL,
            codigo_alterno  TEXT NOT NULL,
            tipo_codigo     TEXT NOT NULL,
            fuente          TEXT NOT NULL,
            confianza_match REAL NOT NULL DEFAULT 1.0,
            created_at      TEXT DEFAULT (datetime('now')),
            PRIMARY KEY(codigo_cne, codigo_alterno, tipo_codigo)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cc_alt ON centro_codigos(codigo_alterno)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS centro_snapshot (
            codigo_cne      TEXT NOT NULL,
            eleccion_ref    TEXT NOT NULL,
            nombre_centro   TEXT,
            num_mesas       INTEGER DEFAULT 0,
            num_electores   INTEGER DEFAULT 0,
            fuente          TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            PRIMARY KEY(codigo_cne, eleccion_ref)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cs_ref ON centro_snapshot(eleccion_ref)")
    ensure_historico_normalizado_schema(conn)
    conn.commit()
    conn.execute("""
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
        )
    """)
    conn.execute("""
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
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ec_eleccion ON election_centers(eleccion_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ec_centro ON election_centers(centro_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tm_ingestion_logs (
            id                  INTEGER PRIMARY KEY,
            eleccion_id          INTEGER NOT NULL REFERENCES elecciones(id),
            source_files         TEXT NOT NULL,
            detected_columns     TEXT,
            field_notes          TEXT,
            match_stats          TEXT,
            user                 TEXT,
            created_at           TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
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
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rm_eleccion ON resultados_mesa(id_eleccion)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rm_centro ON resultados_mesa(codigo_cne)")
    conn.execute("""
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
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rc_eleccion ON reportes_campo(id_eleccion)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rc_centro ON reportes_campo(codigo_cne)")
    # Bloque 9: estudios históricos
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_estudios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            eleccion_ref    TEXT NOT NULL,
            ambito          TEXT NOT NULL,
            nombre          TEXT NOT NULL,
            nombre_eleccion TEXT,
            fecha_eleccion  TEXT,
            pct_gov         REAL NOT NULL DEFAULT 0,
            pct_opos        REAL NOT NULL DEFAULT 0,
            pct_otros       REAL NOT NULL DEFAULT 0,
            num_centros     INTEGER NOT NULL DEFAULT 0,
            fuente          TEXT,
            notas           TEXT,
            updated_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(eleccion_ref, ambito)
        )
    """)
    conn.execute("""
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
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_estudios_turnos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            eleccion_ref    TEXT NOT NULL,
            ambito          TEXT NOT NULL DEFAULT 'NACIONAL',
            turno           INTEGER NOT NULL,
            hora_label      TEXT,
            pct_gov         REAL NOT NULL DEFAULT 0,
            pct_opos        REAL NOT NULL DEFAULT 0,
            pct_otros       REAL NOT NULL DEFAULT 0,
            num_centros     INTEGER NOT NULL DEFAULT 0,
            updated_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(eleccion_ref, ambito, turno)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_he_ref  ON historico_estudios(eleccion_ref)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ho_ref  ON historico_oficial(eleccion_ref)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_het_ref ON historico_estudios_turnos(eleccion_ref)")
    conn.commit()
    print('[~] Migración: tablas historico_estudios, historico_oficial, historico_estudios_turnos añadidas')
    conn.execute("""
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
                           AND c2.id_eleccion   = campo.id_eleccion
    """)
    conn.execute("""
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
        LEFT JOIN cne_centro  cc ON cc.id_eleccion=m.id_eleccion AND cc.codigo_cne=m.codigo_centro
    """)
    conn.commit()


def verificar_tablas(conn: sqlite3.Connection):
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tablas = [row[0] for row in cursor.fetchall()]
    print(f'\n[+] Tablas creadas ({len(tablas)}):')
    for t in tablas:
        count = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        print(f'    {t:<30} {count:>6} filas')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inicializa la BD del Exit Poll')
    parser.add_argument('--reset', action='store_true',
                        help='Elimina y recrea la BD desde cero')
    args = parser.parse_args()

    conn = init_db(reset=args.reset)
    if not args.reset:
        migrar(conn)
    verificar_tablas(conn)
    conn.close()
