"""
Convertidor de Tabla de Mesa del CNE al formato estándar interno.

Uso:
    python convertidor_tm.py <archivo_entrada> <archivo_salida.csv> [--formato auto|2015|2018]

Formatos soportados:
    2015  - tablamesa-an_2015.xlsx  (COD_EDO, ESTADO, COD_MUN, MUNICIPIO, ...)
    2018  - TM elecciones 2018.xlsx (Nombre CV, Estado, Municipio, ...)
    auto  - detecta el formato automaticamente (default)
"""

import pandas as pd
import argparse
import os
import sys


# ------------------------------------------------------------------
# Deteccion de formato
# ------------------------------------------------------------------

def detectar_formato(df: pd.DataFrame) -> str:
    cols = [str(c).strip().upper() for c in df.columns]
    if 'COD_EDO' in cols and 'CTRO_PROP' in cols:
        return '2015'
    if 'NOMBRE CV' in cols or 'CÓDIGO CV' in cols or 'CODIGO CV' in cols:
        return '2018'
    raise ValueError(
        f'Formato no reconocido. Columnas encontradas: {cols}\n'
        'Agrega soporte manual con --formato o crea un nuevo convertidor.'
    )


# ------------------------------------------------------------------
# Convertidores por formato
# ------------------------------------------------------------------

def convertir_2015(df: pd.DataFrame) -> pd.DataFrame:
    """
    tablamesa-an_2015.xlsx
    Columnas: COD_EDO, ESTADO, COD_MUN, MUNICIPIO, COD_PAR, PARROQUIA,
              CTRO_ACT, CTRO_PROP, NOMBRE_CENTRO, DIRECCION, MESA,
              TOMO, DESDE, HASTA, ELECTORES, TECNOLOGIA, CIR_ASA, estatus
    """
    df.columns = [str(c).strip() for c in df.columns]

    resultado = pd.DataFrame({
        'codigo_centro': df['CTRO_PROP'].astype(str).str.strip().str.zfill(9),
        'nombre_centro': df['NOMBRE_CENTRO'].astype(str).str.strip(),
        'direccion':     df['DIRECCION'].astype(str).str.strip(),
        'cod_estado':    df['COD_EDO'].astype(str).str.zfill(2),
        'estado':        df['ESTADO'].astype(str).str.strip(),
        'cod_municipio': df['COD_MUN'].astype(str).str.zfill(2),
        'municipio':     df['MUNICIPIO'].astype(str).str.strip(),
        'cod_parroquia': df['COD_PAR'].astype(str).str.zfill(2),
        'parroquia':     df['PARROQUIA'].astype(str).str.strip(),
        'numero_mesa':   pd.to_numeric(df['MESA'], errors='coerce'),
        'electores':     pd.to_numeric(df['ELECTORES'], errors='coerce'),
        'circuito_an':   pd.to_numeric(df.get('CIR_ASA', pd.Series(dtype=float)),
                                       errors='coerce'),
        'lat':           None,
        'lon':           None,
        'riesgo':        1,
    })
    return resultado


def convertir_2018(df: pd.DataFrame) -> pd.DataFrame:
    """
    TM elecciones 2018.xlsx - hoja TM
    Columnas: Nombre CV, Dirección CV, N° ME, CI desde, CI hasta,
              Total Electores, Estado, Municipio, Parroquia, Código CV
    """
    df.columns = [str(c).strip() for c in df.columns]

    # Normalizar nombre de columnas con variaciones de encoding
    rename = {}
    for c in df.columns:
        cu = c.upper()
        if 'NOMBRE' in cu and 'CV' in cu:    rename[c] = 'NOMBRE_CV'
        if 'DIRECCI' in cu:                   rename[c] = 'DIRECCION'
        if 'N' in cu and 'ME' in cu:          rename[c] = 'MESA'
        if 'ELECTORES' in cu:                 rename[c] = 'ELECTORES'
        if 'ESTADO' in cu:                    rename[c] = 'ESTADO'
        if 'MUNICIPIO' in cu:                 rename[c] = 'MUNICIPIO'
        if 'PARROQUIA' in cu:                 rename[c] = 'PARROQUIA'
        if 'C' in cu and 'DIGO' in cu and 'CV' in cu: rename[c] = 'CODIGO_CV'
    df = df.rename(columns=rename)

    # El codigo CV en 2018 no tiene cod_estado/municipio/parroquia separados
    # Los extraemos del nombre (son prefijos del codigo)
    # Codigo: EEMMPPSSS (9 digitos) -> EE=estado, MM=municipio, PP=parroquia
    codigo = df['CODIGO_CV'].astype(str).str.strip().str.zfill(9)

    resultado = pd.DataFrame({
        'codigo_centro': codigo,
        'nombre_centro': df['NOMBRE_CV'].astype(str).str.strip(),
        'direccion':     df.get('DIRECCION', pd.Series(dtype=str)).astype(str).str.strip(),
        'cod_estado':    codigo.str[:2],
        'estado':        df['ESTADO'].astype(str).str.strip(),
        'cod_municipio': codigo.str[2:4],
        'municipio':     df['MUNICIPIO'].astype(str).str.strip(),
        'cod_parroquia': codigo.str[4:6],
        'parroquia':     df['PARROQUIA'].astype(str).str.strip(),
        'numero_mesa':   pd.to_numeric(df.get('MESA', pd.Series(dtype=float)),
                                       errors='coerce'),
        'electores':     pd.to_numeric(df['ELECTORES'], errors='coerce'),
        'circuito_an':   None,
        'lat':           None,
        'lon':           None,
        'riesgo':        1,
    })
    return resultado


CONVERTIDORES = {
    '2015': convertir_2015,
    '2018': convertir_2018,
}


# ------------------------------------------------------------------
# Carga del archivo fuente
# ------------------------------------------------------------------

def cargar_archivo(ruta: str, hoja: str = None) -> pd.DataFrame:
    ext = os.path.splitext(ruta)[1].lower()
    if ext in ('.xlsx', '.xlsm', '.xls'):
        xl = pd.ExcelFile(ruta)
        print(f'[+] Hojas disponibles: {xl.sheet_names}')

        # Si se especifica hoja, usarla directamente
        if hoja:
            df = pd.read_excel(ruta, sheet_name=hoja, header=0)
            print(f'[+] Usando hoja: {hoja} ({len(df)} filas)')
            return df

        # Heuristica: preferir hoja con mas filas que tenga columnas de centros
        candidatas = []
        for sh in xl.sheet_names:
            try:
                df = pd.read_excel(ruta, sheet_name=sh, header=0)
                cols = ' '.join(str(c).upper() for c in df.columns)
                score = 0
                if len(df) > 100:    score += len(df)
                if 'CENTRO' in cols: score += 50000
                if 'MESA'   in cols: score += 50000
                if 'ELECTOR' in cols: score += 50000
                if score > 0:
                    candidatas.append((score, sh, df))
            except Exception:
                continue

        if not candidatas:
            raise ValueError('No se encontró hoja con datos de centros')

        candidatas.sort(key=lambda x: x[0], reverse=True)
        score, sh, df = candidatas[0]
        print(f'[+] Usando hoja: {sh} ({len(df)} filas)')
        return df

    elif ext == '.csv':
        return pd.read_csv(ruta, encoding='utf-8-sig')
    else:
        raise ValueError(f'Formato de archivo no soportado: {ext}')


# ------------------------------------------------------------------
# Post-proceso: limpiar y validar
# ------------------------------------------------------------------

def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    # Eliminar filas sin codigo_centro o sin electores
    df = df.dropna(subset=['codigo_centro', 'electores'])
    df = df[df['codigo_centro'].astype(str).str.strip() != '']
    df = df[df['electores'] > 0]

    # Tipos correctos
    df['numero_mesa'] = df['numero_mesa'].fillna(0).astype(int)
    df['electores']   = df['electores'].astype(int)
    df['riesgo']      = df['riesgo'].fillna(1).astype(int)

    # Limpiar strings
    str_cols = ['nombre_centro', 'direccion', 'estado', 'municipio', 'parroquia']
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip().str.upper()
        df[col] = df[col].replace({'NAN': '', 'NONE': ''})

    return df.reset_index(drop=True)


def estadisticas(df: pd.DataFrame):
    centros  = df['codigo_centro'].nunique()
    estados  = df['estado'].nunique()
    electores = df['electores'].sum()
    mesas    = len(df)
    print(f'\n[+] Resumen:')
    print(f'    Mesas:     {mesas:>8,}')
    print(f'    Centros:   {centros:>8,}')
    print(f'    Estados:   {estados:>8,}')
    print(f'    Electores: {electores:>8,}')


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Convierte TM del CNE al formato estandar')
    parser.add_argument('entrada', help='Archivo fuente del CNE (.xlsx, .xlsm, .csv)')
    parser.add_argument('salida',  help='Archivo CSV de salida')
    parser.add_argument('--formato', default='auto',
                        choices=['auto', '2015', '2018'],
                        help='Formato del archivo fuente (default: auto)')
    parser.add_argument('--hoja', default=None,
                        help='Nombre de la hoja Excel a usar (opcional)')
    args = parser.parse_args()

    print(f'[+] Cargando: {args.entrada}')
    df_raw = cargar_archivo(args.entrada, hoja=args.hoja)

    fmt = args.formato
    if fmt == 'auto':
        fmt = detectar_formato(df_raw)
        print(f'[+] Formato detectado: {fmt}')

    if fmt not in CONVERTIDORES:
        print(f'[!] Formato "{fmt}" no soportado aun. Agrega el convertidor en este archivo.')
        sys.exit(1)

    print(f'[+] Convirtiendo con formato {fmt}...')
    df = CONVERTIDORES[fmt](df_raw)
    df = limpiar(df)

    estadisticas(df)

    df.to_csv(args.salida, index=False, encoding='utf-8-sig')
    print(f'\n[+] Guardado: {args.salida}')


if __name__ == '__main__':
    main()
