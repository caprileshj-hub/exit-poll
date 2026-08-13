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

import os
import sqlite3
import sys

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(BASE_DIR, 'exitpoll.db')
TM_PATH      = os.path.join(BASE_DIR, 'tm_2018_con_gps.csv')

sys.path.insert(0, BASE_DIR)
import calculador_pesos
import cargador_tm
import init_db
import seed_resultados_historicos
import selector_muestra

ELECCION_REF = '2024-presidencial'


def main():
    # 1. BD limpia
    print('\n=== Paso 1: Inicializar BD ===')
    conn = init_db.init_db(reset=True)
    conn.close()

    # 2. TM con GPS
    print('\n=== Paso 2: Cargar TM 2018 ===')
    cargador_tm.cargar_tm(TM_PATH)

    # 3. Resultados históricos (requeridos por selector_muestra)
    print('\n=== Paso 3: Cargar resultados historicos por centro ===')
    stats = seed_resultados_historicos.seed_resultados_historicos(DB_PATH)
    print(f'[+] resultados_historicos: {stats}')

    # 4. Elección y candidatos
    print('\n=== Paso 4: Crear elección y candidatos ===')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')

    cur = conn.execute(
        '''INSERT INTO elecciones
               (nombre, tipo, fecha, hora_apertura, hora_cierre, activa)
           VALUES ('Presidenciales 2024', 'nacional', '2024-07-28', '07:00', '18:00', 1)'''
    )
    id_eleccion = cur.lastrowid
    print(f'[+] Elección id={id_eleccion}: Presidenciales 2024')

    cur = conn.execute(
        "INSERT INTO candidatos (id_eleccion, nombre, partido, bando, tipo, orden) VALUES (?, ?, 'PSUV', 'gobierno', 'unico', 1)",
        (id_eleccion, 'Nicolás Maduro'),
    )
    id_maduro = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO candidatos (id_eleccion, nombre, partido, bando, tipo, orden) VALUES (?, ?, 'PUD', 'oposicion', 'unico', 2)",
        (id_eleccion, 'Edmundo González'),
    )
    id_gonzalez = cur.lastrowid
    conn.commit()
    print(f'[+] Candidatos: Maduro id={id_maduro}, González id={id_gonzalez}')

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
            (codigo, id_maduro),
        )
        conn.execute(
            'INSERT OR IGNORE INTO centros_candidatos (codigo_centro, id_candidato) VALUES (?, ?)',
            (codigo, id_gonzalez),
        )
    conn.commit()
    conn.close()
    print(f'[+] centros_candidatos: {len(codigos) * 2} filas')

    # 7. Pesos
    print('\n=== Paso 7: Calcular pesos ===')
    calculador_pesos.calcular(id_eleccion)

    print('\n[OK] BD sembrada. Usa "Test Total" en el dashboard para cargar los votos demo.')


if __name__ == '__main__':
    main()
