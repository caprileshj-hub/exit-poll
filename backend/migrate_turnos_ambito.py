"""
Migración: agrega columna ambito a historico_estudios_turnos.
Cambia UNIQUE(eleccion_ref, turno) → UNIQUE(eleccion_ref, ambito, turno).
Filas existentes (presidenciales) quedan con ambito='NACIONAL'.
"""
import sqlite3

DB = "exitpoll.db"
conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = OFF")
conn.execute("PRAGMA journal_mode = WAL")

try:
    conn.execute("BEGIN")

    # Verificar si ya fue migrada
    cols = [r[1] for r in conn.execute("PRAGMA table_info(historico_estudios_turnos)").fetchall()]
    if "ambito" in cols:
        print("Ya tiene columna ambito — nada que hacer.")
        conn.rollback()
    else:
        conn.execute("ALTER TABLE historico_estudios_turnos RENAME TO _turnos_old")
        conn.execute("""
            CREATE TABLE historico_estudios_turnos (
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
        conn.execute("""
            INSERT INTO historico_estudios_turnos
                (id, eleccion_ref, ambito, turno, hora_label,
                 pct_gov, pct_opos, pct_otros, num_centros, updated_at)
            SELECT id, eleccion_ref, 'NACIONAL', turno, hora_label,
                   pct_gov, pct_opos, pct_otros, num_centros, updated_at
            FROM _turnos_old
        """)
        conn.execute("DROP TABLE _turnos_old")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_het_ref ON historico_estudios_turnos(eleccion_ref)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_het_amb ON historico_estudios_turnos(eleccion_ref, ambito)")
        conn.commit()
        n = conn.execute("SELECT COUNT(*) FROM historico_estudios_turnos").fetchone()[0]
        print(f"Migración completada. {n} filas existentes preservadas con ambito='NACIONAL'.")
finally:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
