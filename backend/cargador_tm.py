"""
Carga el CSV estándar de Tabla de Mesa a la BD.
Hace carga DIFERENCIAL: solo actualiza lo que cambia entre elecciones.

Lo que SIEMPRE se actualiza:
    - num_mesas, num_electores (cambian por eleccion)

Lo que se actualiza SOLO si el centro es nuevo o el campo está vacío:
    - nombre, direccion, jerarquia geografica (estado/municipio/parroquia)
    - id_circuito (puede cambiar por gerrymandering AN)

Lo que NUNCA se sobreescribe si ya tiene valor:
    - lat, lon      (coordenadas fisicas del edificio)
    - riesgo        (evaluacion de seguridad)
    - radio_m       (configuracion operativa)

Centros que desaparecen del nuevo TM se marcan activo=0, no se borran.

Uso:
    python cargador_tm.py <tm_estandar.csv> [--dry-run]
"""

import sqlite3
import pandas as pd
import argparse
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'exitpoll.db')


# ------------------------------------------------------------------
# Helpers geograficos
# ------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """Normaliza texto para comparacion: mayusculas, sin espacios extra."""
    if not texto or str(texto).strip().upper() in ('', 'NAN', 'NONE'):
        return ''
    return str(texto).strip().upper()


def obtener_o_crear(conn, tabla, campos_busqueda: dict, campos_extra: dict = None) -> int:
    """Obtiene el id de un registro o lo crea si no existe."""
    where  = ' AND '.join(f'{k} = ?' for k in campos_busqueda)
    valores = list(campos_busqueda.values())
    row = conn.execute(f'SELECT id FROM {tabla} WHERE {where}', valores).fetchone()
    if row:
        return row[0]
    todos = {**campos_busqueda, **(campos_extra or {})}
    cols  = ', '.join(todos.keys())
    placeholders = ', '.join('?' for _ in todos)
    conn.execute(f'INSERT INTO {tabla} ({cols}) VALUES ({placeholders})', list(todos.values()))
    return conn.execute(f'SELECT id FROM {tabla} WHERE {where}', valores).fetchone()[0]


# ------------------------------------------------------------------
# Carga principal
# ------------------------------------------------------------------

def cargar_tm(csv_path: str, dry_run: bool = False):
    print(f'[+] Leyendo: {csv_path}')
    df = pd.read_csv(csv_path, encoding='utf-8-sig', dtype=str)

    # Limpiar y tipar
    df['electores']   = pd.to_numeric(df['electores'],   errors='coerce').fillna(0).astype(int)
    df['numero_mesa'] = pd.to_numeric(df['numero_mesa'], errors='coerce').fillna(0).astype(int)
    df['circuito_an'] = pd.to_numeric(df.get('circuito_an', pd.Series(dtype=str)),
                                      errors='coerce')
    df['lat']  = pd.to_numeric(df.get('lat',  pd.Series(dtype=str)), errors='coerce')
    df['lon']  = pd.to_numeric(df.get('lon',  pd.Series(dtype=str)), errors='coerce')
    df['riesgo'] = pd.to_numeric(df.get('riesgo', pd.Series(dtype=str)),
                                 errors='coerce').fillna(1).astype(int)

    # Agrupar por centro: sumar mesas y electores
    centros_nuevos = (
        df.groupby('codigo_centro')
          .agg(
              nombre_centro  = ('nombre_centro',  'first'),
              direccion      = ('direccion',       'first'),
              cod_estado     = ('cod_estado',      'first'),
              estado         = ('estado',          'first'),
              cod_municipio  = ('cod_municipio',   'first'),
              municipio      = ('municipio',       'first'),
              cod_parroquia  = ('cod_parroquia',   'first'),
              parroquia      = ('parroquia',       'first'),
              num_mesas      = ('numero_mesa',     'count'),
              num_electores  = ('electores',       'sum'),
              circuito_an    = ('circuito_an',     'first'),
              lat            = ('lat',             'first'),
              lon            = ('lon',             'first'),
              riesgo         = ('riesgo',          'first'),
          )
          .reset_index()
    )

    total_csv = len(centros_nuevos)
    print(f'[+] Centros en CSV: {total_csv:,}')
    print(f'[+] Electores totales: {df["electores"].sum():,}')

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')

    stats = {'nuevos': 0, 'actualizados': 0, 'sin_cambio': 0, 'desactivados': 0}

    try:
        for _, row in centros_nuevos.iterrows():
            codigo = str(row['codigo_centro']).strip()

            # --- Geografía: obtener o crear estado/municipio/parroquia ---
            id_estado = obtener_o_crear(
                conn, 'estados',
                {'codigo_cne': str(row['cod_estado']).zfill(2)},
                {'nombre': normalizar(row['estado']), 'es_excepcion': 0}
            )

            id_municipio = obtener_o_crear(
                conn, 'municipios',
                {'id_estado': id_estado,
                 'codigo_cne': str(row['cod_municipio']).zfill(2)},
                {'nombre': normalizar(row['municipio'])}
            )

            id_parroquia = obtener_o_crear(
                conn, 'parroquias',
                {'id_municipio': id_municipio,
                 'codigo_cne': str(row['cod_parroquia']).zfill(2)},
                {'nombre': normalizar(row['parroquia'])}
            )

            # Circuito AN (puede ser None)
            id_circuito = None
            if pd.notna(row.get('circuito_an')):
                id_circuito = obtener_o_crear(
                    conn, 'circuitos',
                    {'id_estado': id_estado,
                     'numero': int(row['circuito_an'])},
                )

            # --- Verificar si el centro ya existe ---
            existente = conn.execute(
                'SELECT num_mesas, num_electores, lat, lon, riesgo, radio_m, activo '
                'FROM centros WHERE codigo_cne = ?', (codigo,)
            ).fetchone()

            lat_csv = row['lat'] if pd.notna(row.get('lat')) else None
            lon_csv = row['lon'] if pd.notna(row.get('lon')) else None

            if existente is None:
                # Centro nuevo
                if not dry_run:
                    conn.execute('''
                        INSERT INTO centros
                            (codigo_cne, nombre, direccion,
                             id_parroquia, id_municipio, id_estado, id_circuito,
                             num_mesas, num_electores,
                             lat, lon, riesgo, radio_m, activo)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,300,1)
                    ''', (
                        codigo,
                        normalizar(row['nombre_centro']),
                        normalizar(row['direccion']),
                        id_parroquia, id_municipio, id_estado, id_circuito,
                        int(row['num_mesas']), int(row['num_electores']),
                        lat_csv, lon_csv, int(row['riesgo'])
                    ))
                stats['nuevos'] += 1

            else:
                ex_mesas, ex_electores, ex_lat, ex_lon, ex_riesgo, ex_radio, ex_activo = existente

                # Detectar cambios en lo que SI se actualiza
                mesas_cambio     = int(row['num_mesas'])     != ex_mesas
                electores_cambio = int(row['num_electores']) != ex_electores
                circuito_cambio  = False  # solo actualizar si es AN y cambio

                if not (mesas_cambio or electores_cambio) and ex_activo == 1:
                    stats['sin_cambio'] += 1
                    continue

                if not dry_run:
                    conn.execute('''
                        UPDATE centros SET
                            num_mesas     = ?,
                            num_electores = ?,
                            id_circuito   = COALESCE(?, id_circuito),
                            -- lat/lon/riesgo/radio_m NO se tocan si ya tienen valor
                            lat    = CASE WHEN lat IS NULL THEN ? ELSE lat END,
                            lon    = CASE WHEN lon IS NULL THEN ? ELSE lon END,
                            activo = 1
                        WHERE codigo_cne = ?
                    ''', (
                        int(row['num_mesas']),
                        int(row['num_electores']),
                        id_circuito,
                        lat_csv, lon_csv,
                        codigo
                    ))
                stats['actualizados'] += 1

        # --- Marcar como inactivos los centros que no están en el nuevo TM ---
        codigos_csv = set(centros_nuevos['codigo_centro'].astype(str))
        codigos_bd  = {r[0] for r in conn.execute('SELECT codigo_cne FROM centros WHERE activo=1')}
        desaparecidos = codigos_bd - codigos_csv

        if desaparecidos and not dry_run:
            conn.executemany(
                'UPDATE centros SET activo = 0 WHERE codigo_cne = ?',
                [(c,) for c in desaparecidos]
            )
        stats['desactivados'] = len(desaparecidos)

        if not dry_run:
            conn.commit()

    except Exception as e:
        conn.rollback()
        print(f'[!] Error: {e}')
        raise
    finally:
        conn.close()

    # --- Reporte ---
    modo = '[DRY RUN] ' if dry_run else ''
    print(f'\n{modo}Resultado:')
    print(f'    Centros nuevos:       {stats["nuevos"]:>6,}')
    print(f'    Centros actualizados: {stats["actualizados"]:>6,}  (mesas/electores)')
    print(f'    Sin cambios:          {stats["sin_cambio"]:>6,}')
    print(f'    Desactivados:         {stats["desactivados"]:>6,}  (no están en nuevo TM)')
    if dry_run:
        print('\n[!] Dry run: no se escribió nada en la BD')


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Carga TM estándar a la BD (diferencial)')
    parser.add_argument('csv', help='Archivo CSV estándar generado por convertidor_tm.py')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula la carga sin escribir en la BD')
    args = parser.parse_args()
    cargar_tm(args.csv, dry_run=args.dry_run)
