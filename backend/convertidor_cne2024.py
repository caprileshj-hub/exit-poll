"""
Convierte el spreadsheet de Centros CNE 2024 (vzlapi) al formato TM estándar.

Fuente: https://docs.google.com/spreadsheets/d/1l6ThiQQZXog_8fBw3z5RwqThG7QAy0AqF4wPYpvGUWA/

Columnas de entrada:
    acta_id, centro_cne_id, mesa, estado, municipio, parroquia, centro,
    electores_centro, electores_mesa, votos_maduro, ..., votos_gonzalez, ...

Problemas a resolver:
    - Nombres de estado inconsistentes (algunos sin prefijo EDO./DTTO.)
    - No tiene cod_estado/cod_municipio/cod_parroquia explícitos
    - Los códigos se extraen del centro_cne_id (9 dígitos: EEMMPP+centro)
    - "EDO. VARGAS" pasó a "EDO. LA GUAIRA" en 2024
"""

import pandas as pd
import sys
import os

# Mapeo de nombres no estándar a nombres CNE oficiales
ESTADO_NORMALIZE = {
    'CAPITAL': 'DTTO. CAPITAL',
    'ANZOATEGUI': 'EDO. ANZOATEGUI',
    'APURE': 'EDO. APURE',
    'BARINAS': 'EDO. BARINAS',
    'BOLIVAR': 'EDO. BOLIVAR',
    'DELTA AMACURO': 'EDO. DELTA AMAC',
    'MERIDA': 'EDO. MERIDA',
    'MIRANDA': 'EDO. MIRANDA',
    'SUCRE': 'EDO. SUCRE',
    'ZULIA': 'EDO. ZULIA',
}


def convertir_cne2024(csv_path: str, salida_tm: str, salida_resultados: str = None):
    print(f'[+] Leyendo: {csv_path}')
    df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
    print(f'[+] Filas: {len(df):,}')

    # Normalizar nombres de estado
    df['estado'] = df['estado'].str.strip()
    df['estado'] = df['estado'].replace(ESTADO_NORMALIZE)

    # Normalizar código de centro a 9 dígitos
    df['centro_cne_id'] = df['centro_cne_id'].astype(str).str.strip().str.zfill(9)

    # Extraer códigos geográficos del centro_cne_id
    # Formato CNE: EEMMPPSSS (9 dígitos)
    # EE = estado, MM = municipio, PP = parroquia, SSS = secuencial
    df['cod_estado'] = df['centro_cne_id'].str[:2]
    df['cod_municipio'] = df['centro_cne_id'].str[2:4]
    df['cod_parroquia'] = df['centro_cne_id'].str[4:6]

    # Limpiar strings
    for col in ['municipio', 'parroquia', 'centro']:
        df[col] = df[col].astype(str).str.strip().str.upper()

    # Electores por mesa
    df['electores_mesa'] = pd.to_numeric(df['electores_mesa'], errors='coerce')
    df['electores_centro'] = pd.to_numeric(df['electores_centro'], errors='coerce').fillna(0).astype(int)

    # Si electores_mesa está vacío, distribuir electores_centro entre las mesas
    mesas_por_centro = df.groupby('centro_cne_id')['mesa'].transform('count')
    df['electores_calc'] = df['electores_mesa'].fillna(
        (df['electores_centro'] / mesas_por_centro).round()
    ).astype(int)

    # === Generar TM estándar ===
    tm = pd.DataFrame({
        'codigo_centro': df['centro_cne_id'],
        'nombre_centro': df['centro'],
        'direccion': '',
        'cod_estado': df['cod_estado'],
        'estado': df['estado'],
        'cod_municipio': df['cod_municipio'],
        'municipio': df['municipio'],
        'cod_parroquia': df['cod_parroquia'],
        'parroquia': df['parroquia'],
        'numero_mesa': pd.to_numeric(df['mesa'], errors='coerce').fillna(1).astype(int),
        'electores': df['electores_calc'],
        'circuito_an': None,
        'lat': None,
        'lon': None,
        'riesgo': 1,
    })

    # Limpiar: solo filas con código y electores válidos
    tm = tm[tm['codigo_centro'].str.len() >= 8]
    tm = tm[tm['estado'].str.startswith(('EDO.', 'DTTO.'))]

    centros = tm['codigo_centro'].nunique()
    electores = tm.groupby('codigo_centro')['electores'].max().sum()
    print(f'[+] TM generado: {len(tm):,} mesas, {centros:,} centros, {electores:,.0f} electores')
    print(f'[+] Estados: {tm["estado"].nunique()}')

    tm.to_csv(salida_tm, index=False, encoding='utf-8-sig')
    print(f'[+] Guardado TM: {salida_tm}')

    # === Generar resultados por centro ===
    if salida_resultados:
        votos_cols = ['votos_maduro', 'votos_gonzalez', 'votos_martinez', 'votos_bertucci',
                      'votos_brito', 'votos_ecarri', 'votos_fermin', 'votos_ceballos',
                      'votos_marquez', 'votos_rausseo']
        for col in votos_cols:
            df[col] = pd.to_numeric(df.get(col, pd.Series(dtype=float)), errors='coerce').fillna(0)
        df['total_validos'] = pd.to_numeric(df['total_validos'], errors='coerce').fillna(0)

        gc = df.groupby('centro_cne_id').agg(
            votos_gobierno=('votos_maduro', 'sum'),
            votos_oposicion=('votos_gonzalez', 'sum'),
            votos_validos=('total_validos', 'sum'),
        ).reset_index()
        gc['votos_otros'] = gc['votos_validos'] - gc['votos_gobierno'] - gc['votos_oposicion']
        gc.loc[gc['votos_validos'] > 0, 'pct_gobierno'] = (
            100 * gc['votos_gobierno'] / gc['votos_validos']).round(2)
        gc.loc[gc['votos_validos'] > 0, 'pct_oposicion'] = (
            100 * gc['votos_oposicion'] / gc['votos_validos']).round(2)

        # Solo centros con votos
        gc = gc[gc['votos_validos'] > 0]
        gc.to_csv(salida_resultados, index=False, encoding='utf-8-sig')
        print(f'[+] Guardado resultados: {salida_resultados} ({len(gc):,} centros con votos)')

    return tm


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python convertidor_cne2024.py <centros_cne_2024.csv> [salida_tm.csv] [salida_resultados.csv]')
        sys.exit(1)

    entrada = sys.argv[1]
    salida_tm = sys.argv[2] if len(sys.argv) > 2 else 'tm_2024_estandar.csv'
    salida_res = sys.argv[3] if len(sys.argv) > 3 else 'resultados_cne2024.csv'
    convertir_cne2024(entrada, salida_tm, salida_res)
