"""
Inicializa la base de datos del Exit Poll a partir del schema.sql
Uso: python init_db.py [--reset]
"""

import sqlite3
import argparse
import os

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
    cols = {r[1] for r in conn.execute('PRAGMA table_info(municipios)')}
    if 'es_excepcion' not in cols:
        conn.execute('ALTER TABLE municipios ADD COLUMN es_excepcion INTEGER DEFAULT 0')
        conn.commit()
        print('[~] Migración: municipios.es_excepcion añadida')


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
