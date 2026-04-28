"""
Inicializa la BD con datos mínimos para la demo Showcase.

Flujo:
  1. BD limpia (init_db --reset)
  2. Carga TM 2018 con GPS
  3. Carga resultados_cne2024.csv → resultados_historicos
  4. Crea elección "Presidenciales 2006" + candidatos Chávez / Rosales
  5. Selecciona muestra (1 centro por unidad geográfica)
  6. Popula centros_candidatos
  7. Calcula pesos
  8. Corre simulador_showcase.py --reset --delay 0 --sesgo 0.55

Uso: python init_showcase.py
"""

import csv
import os
import sqlite3
import subprocess
import sys

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(BASE_DIR, 'exitpoll.db')
TM_PATH      = os.path.join(BASE_DIR, 'tm_2018_con_gps.csv')
CNE2024_PATH = os.path.join(BASE_DIR, 'resultados_cne2024.csv')
SIM_PATH     = os.path.join(BASE_DIR, 'simulador_showcase.py')

sys.path.insert(0, BASE_DIR)
import calculador_pesos
import cargador_tm
import init_db
import selector_muestra

ELECCION_REF = '2024-presidencial'


def _cargar_historicos(csv_path: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    count = 0
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                conn.execute(
                    '''
                    INSERT INTO resultados_historicos
                        (codigo_centro, eleccion_ref,
                         votos_validos, votos_gobierno, votos_oposicion,
                         votos_otros, pct_gobierno, pct_oposicion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(codigo_centro, eleccion_ref) DO UPDATE SET
                        votos_validos   = excluded.votos_validos,
                        votos_gobierno  = excluded.votos_gobierno,
                        votos_oposicion = excluded.votos_oposicion,
                        votos_otros     = excluded.votos_otros,
                        pct_gobierno    = excluded.pct_gobierno,
                        pct_oposicion   = excluded.pct_oposicion
                    ''',
                    (
                        row['centro_cne_id'],
                        ELECCION_REF,
                        int(float(row.get('votos_validos') or 0)),
                        int(float(row.get('votos_gobierno') or 0)),
                        int(float(row.get('votos_oposicion') or 0)),
                        int(float(row.get('votos_otros') or 0)),
                        float(row.get('pct_gobierno') or 0),
                        float(row.get('pct_oposicion') or 0),
                    ),
                )
                count += 1
            except (ValueError, KeyError) as e:
                print(f'[!] Fila omitida: {e}')
    conn.commit()
    conn.close()
    print(f'[+] resultados_historicos: {count} centros (ref={ELECCION_REF})')


def main():
    # 1. BD limpia
    print('\n=== Paso 1: Inicializar BD ===')
    conn = init_db.init_db(reset=True)
    conn.close()

    # 2. TM con GPS
    print('\n=== Paso 2: Cargar TM 2018 ===')
    cargador_tm.cargar_tm(TM_PATH)

    # 3. Resultados históricos (requeridos por selector_muestra)
    print('\n=== Paso 3: Cargar resultados CNE 2024 ===')
    _cargar_historicos(CNE2024_PATH)

    # 4. Elección y candidatos
    print('\n=== Paso 4: Crear elección y candidatos ===')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')

    cur = conn.execute(
        '''INSERT INTO elecciones
               (nombre, tipo, fecha, hora_apertura, hora_cierre, activa)
           VALUES ('Presidenciales 2006', 'nacional', '2006-12-03', '07:00', '18:00', 1)'''
    )
    id_eleccion = cur.lastrowid
    print(f'[+] Elección id={id_eleccion}: Presidenciales 2006')

    cur = conn.execute(
        "INSERT INTO candidatos (id_eleccion, nombre, bando, tipo, orden) VALUES (?, ?, 'gobierno', 'unico', 1)",
        (id_eleccion, 'Hugo Chávez Frías'),
    )
    id_chavez = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO candidatos (id_eleccion, nombre, bando, tipo, orden) VALUES (?, ?, 'oposicion', 'unico', 2)",
        (id_eleccion, 'Manuel Rosales'),
    )
    id_rosales = cur.lastrowid
    conn.commit()
    print(f'[+] Candidatos: Chávez id={id_chavez}, Rosales id={id_rosales}')

    # 5. Selección de muestra
    print('\n=== Paso 5: Seleccionar muestra ===')
    candidatos_muestra = selector_muestra.generar_candidatos(
        conn, eleccion_ref=ELECCION_REF, candidatos_por_unidad=2
    )
    if not candidatos_muestra:
        conn.close()
        sys.exit('[!] selector_muestra retornó lista vacía — verificar resultados_historicos')

    codigos = [c['codigo_cne'] for c in candidatos_muestra if c['rank'] == 1]
    print(f'[+] Centros seleccionados: {len(codigos)}')
    selector_muestra.aplicar_muestra(conn, id_eleccion, codigos)

    # 6. centros_candidatos (todos los centros × ambos candidatos)
    print('\n=== Paso 6: centros_candidatos ===')
    for codigo in codigos:
        conn.execute(
            'INSERT OR IGNORE INTO centros_candidatos (codigo_centro, id_candidato) VALUES (?, ?)',
            (codigo, id_chavez),
        )
        conn.execute(
            'INSERT OR IGNORE INTO centros_candidatos (codigo_centro, id_candidato) VALUES (?, ?)',
            (codigo, id_rosales),
        )
    conn.commit()
    conn.close()
    print(f'[+] centros_candidatos: {len(codigos) * 2} filas')

    # 7. Pesos
    print('\n=== Paso 7: Calcular pesos ===')
    calculador_pesos.calcular(id_eleccion)

    # 8. Simulador
    print('\n=== Paso 8: Simular jornada electoral ===')
    subprocess.run(
        [sys.executable, SIM_PATH, '--reset', '--delay', '0', '--sesgo', '0.55'],
        check=True,
    )
    print('\n[OK] Showcase listo. Servidor: uvicorn app:app --reload')


if __name__ == '__main__':
    main()
