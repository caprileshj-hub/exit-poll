"""
Carga un dataset completo de demostración usando los resultados CNE 2024.
Inserta votos para todos los turnos de una vez — dashboard listo para mostrar
en cualquier momento sin necesidad de correr la simulación en tiempo real.

Uso:
    python demo_loader.py [--reset]

Flags:
    --reset    Elimina votos y sms_raw previos antes de cargar
"""

import argparse
import csv
import os
import random
import sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'exitpoll.db')
CSV_2024 = os.path.join(BASE_DIR, 'resultados_cne2024.csv')

CANDIDATOS_DEMO = [
    {'nombre': 'Nicolás Maduro',   'partido': 'PSUV', 'bando': 'gobierno',  'tipo': 'unico', 'orden': 1},
    {'nombre': 'Edmundo González', 'partido': 'PUD',  'bando': 'oposicion', 'tipo': 'unico', 'orden': 2},
]
VOTOS_POR_CENTRO_POR_TURNO = 3


def cargar_pct_2024() -> dict[str, tuple[float, float]]:
    """Devuelve {codigo_cne: (p_gobierno, p_oposicion)} desde el CSV real del CNE 2024."""
    pct: dict[str, tuple[float, float]] = {}
    with open(CSV_2024, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            p_g = float(row['pct_gobierno']) / 100
            p_o = float(row['pct_oposicion']) / 100
            pct[row['centro_cne_id']] = (p_g, p_o)
    return pct


def asegurar_candidatos(conn: sqlite3.Connection, id_eleccion: int) -> dict[str, int]:
    """Crea candidatos demo si no existen. Devuelve {bando: id_candidato}."""
    rows = conn.execute(
        'SELECT id, bando FROM candidatos WHERE id_eleccion=?', (id_eleccion,)
    ).fetchall()
    if rows:
        return {r['bando']: r['id'] for r in rows}
    for c in CANDIDATOS_DEMO:
        conn.execute(
            'INSERT INTO candidatos (id_eleccion, nombre, partido, bando, tipo, orden) '
            'VALUES (?,?,?,?,?,?)',
            (id_eleccion, c['nombre'], c['partido'], c['bando'], c['tipo'], c['orden'])
        )
    conn.commit()
    return {r['bando']: r['id'] for r in conn.execute(
        'SELECT id, bando FROM candidatos WHERE id_eleccion=?', (id_eleccion,)
    )}


def main() -> None:
    parser = argparse.ArgumentParser(description='Carga dataset demo 2024 en la BD')
    parser.add_argument('--reset', action='store_true',
                        help='Elimina votos y sms_raw previos antes de cargar')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    elec = conn.execute('SELECT * FROM elecciones WHERE activa=1').fetchone()
    if not elec:
        conn.close()
        raise SystemExit('No hay elección activa. Crea una desde el dashboard.')
    print(f'[+] Elección: "{elec["nombre"]}"  (ID={elec["id"]}, tipo={elec["tipo"]})')

    cands = asegurar_candidatos(conn, elec['id'])
    print(f'[+] Candidatos: {", ".join(cands.keys())}')

    centros = conn.execute('''
        SELECT m.id AS id_muestra, m.codigo_centro, c.num_electores, c.lat, c.lon
        FROM muestra m
        JOIN centros c ON c.codigo_cne = m.codigo_centro
        WHERE m.id_eleccion=? AND m.activo=1 AND c.activo=1
    ''', (elec['id'],)).fetchall()
    print(f'[+] Centros-muestra: {len(centros)}')

    pct = cargar_pct_2024()
    matches = sum(1 for c in centros if c['codigo_centro'] in pct)
    print(f'[+] Centros con datos CNE 2024: {matches}/{len(centros)}')

    if args.reset:
        conn.execute('DELETE FROM votos')
        conn.execute('DELETE FROM sms_raw')
        conn.commit()
        print('[reset] Datos previos eliminados')

    # Encuestadores demo (uno por centro)
    for c in centros:
        tel = f'+58414{c["id_muestra"]:07d}'
        conn.execute(
            'INSERT OR IGNORE INTO encuestadores (telefono, nombre, codigo_centro, id_eleccion) '
            'VALUES (?,?,?,?)',
            (tel, f'Demo-{c["id_muestra"]}', c['codigo_centro'], elec['id'])
        )
    conn.commit()

    # Generar turnos (cada 20 min entre apertura y cierre)
    t      = datetime.strptime(elec['hora_apertura'], '%H:%M')
    cierre = datetime.strptime(elec['hora_cierre'],   '%H:%M')
    turnos: list[str] = []
    while t <= cierre:
        turnos.append(t.strftime('%H:%M'))
        t += timedelta(minutes=20)

    total = 0
    conn.execute('BEGIN')
    for idx, hora_str in enumerate(turnos):
        turno_num = idx + 1
        hora_iso  = f'{elec["fecha"]}T{hora_str}:00'

        for c in centros:
            cod  = c['codigo_centro']
            p_g, p_o = pct.get(cod, (0.5, 0.5))
            p_tot = p_g + p_o
            tel  = f'+58414{c["id_muestra"]:07d}'
            lat  = c['lat']  or (10.5  + random.uniform(-2, 2))
            lon  = c['lon']  or (-66.9 + random.uniform(-3, 3))

            for _ in range(VOTOS_POR_CENTRO_POR_TURNO):
                id_cand = (cands['gobierno']
                           if random.random() < (p_g / p_tot)
                           else cands['oposicion'])
                cur = conn.execute(
                    'INSERT INTO sms_raw (from_number, contenido, recibido_at, procesado) '
                    'VALUES (?,?,?,1)',
                    (tel, f'DEMO T{turno_num}', hora_iso)
                )
                conn.execute('''
                    INSERT INTO votos
                        (id_sms, codigo_centro, id_candidato, telefono,
                         hora, turno, lat, lon, distancia_m, valido)
                    VALUES (?,?,?,?,?,?,?,?,?,1)
                ''', (cur.lastrowid, cod, id_cand, tel,
                      hora_iso, turno_num, lat, lon, random.randint(30, 280)))
                total += 1
    conn.commit()
    conn.close()

    print(f'[+] Votos insertados: {total:,}  '
          f'({len(turnos)} turnos × {len(centros)} centros × {VOTOS_POR_CENTRO_POR_TURNO})')
    print('[✓] Dataset demo listo — abre el dashboard para ver los resultados.')


if __name__ == '__main__':
    main()
