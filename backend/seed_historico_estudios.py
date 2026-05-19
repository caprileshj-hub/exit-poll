"""Seed fixed historical-study aggregates into SQLite.

This is intentionally data-only and idempotent. It avoids re-reading the
large Excel cores during Azure requests or restarts.
"""

import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "exitpoll.db"
SEED_PATH = BASE_DIR / "data" / "historico_estudios_seed.json"


def _load_seed() -> dict:
    with SEED_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_historico_estudios(db_path: str | Path = DB_PATH) -> dict[str, int]:
    data = _load_seed()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        counts = {
            "historico_estudios": 0,
            "historico_oficial": 0,
            "historico_estudios_turnos": 0,
        }

        for row in data.get("historico_estudios", []):
            conn.execute("""
                INSERT INTO historico_estudios
                    (eleccion_ref, ambito, nombre, nombre_eleccion, fecha_eleccion,
                     pct_gov, pct_opos, pct_otros, num_centros, fuente, notas)
                VALUES (:eleccion_ref, :ambito, :nombre, :nombre_eleccion, :fecha_eleccion,
                        :pct_gov, :pct_opos, :pct_otros, :num_centros, :fuente, :notas)
                ON CONFLICT(eleccion_ref, ambito) DO UPDATE SET
                    nombre=excluded.nombre,
                    nombre_eleccion=excluded.nombre_eleccion,
                    fecha_eleccion=excluded.fecha_eleccion,
                    pct_gov=excluded.pct_gov,
                    pct_opos=excluded.pct_opos,
                    pct_otros=excluded.pct_otros,
                    num_centros=excluded.num_centros,
                    fuente=excluded.fuente,
                    notas=excluded.notas,
                    updated_at=datetime('now')
            """, row)
            counts["historico_estudios"] += 1

        for row in data.get("historico_oficial", []):
            conn.execute("""
                INSERT INTO historico_oficial
                    (eleccion_ref, ambito, nombre, nombre_eleccion, fecha_eleccion,
                     pct_gov, pct_opos, pct_otros, total_votos, fuente)
                VALUES (:eleccion_ref, :ambito, :nombre, :nombre_eleccion, :fecha_eleccion,
                        :pct_gov, :pct_opos, :pct_otros, :total_votos, :fuente)
                ON CONFLICT(eleccion_ref, ambito) DO UPDATE SET
                    nombre=excluded.nombre,
                    nombre_eleccion=excluded.nombre_eleccion,
                    fecha_eleccion=excluded.fecha_eleccion,
                    pct_gov=excluded.pct_gov,
                    pct_opos=excluded.pct_opos,
                    pct_otros=excluded.pct_otros,
                    total_votos=excluded.total_votos,
                    fuente=excluded.fuente,
                    updated_at=datetime('now')
            """, row)
            counts["historico_oficial"] += 1

        for row in data.get("historico_estudios_turnos", []):
            conn.execute("""
                INSERT INTO historico_estudios_turnos
                    (eleccion_ref, turno, hora_label, pct_gov, pct_opos, pct_otros, num_centros)
                VALUES (:eleccion_ref, :turno, :hora_label,
                        :pct_gov, :pct_opos, :pct_otros, :num_centros)
                ON CONFLICT(eleccion_ref, turno) DO UPDATE SET
                    hora_label=excluded.hora_label,
                    pct_gov=excluded.pct_gov,
                    pct_opos=excluded.pct_opos,
                    pct_otros=excluded.pct_otros,
                    num_centros=excluded.num_centros,
                    updated_at=datetime('now')
            """, row)
            counts["historico_estudios_turnos"] += 1

        conn.commit()
        return counts
    finally:
        conn.close()


if __name__ == "__main__":
    stats = seed_historico_estudios()
    print("Historico estudios seed:", stats)
