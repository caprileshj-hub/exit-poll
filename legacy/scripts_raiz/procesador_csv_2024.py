# -*- coding: utf-8 -*-
import pandas as pd
import os

# Mapa de códigos de estado CNE (Primeros 2 dígitos del código de centro)
CODIGOS_ESTADO = {
    '01': 'DISTRITO CAPITAL', '02': 'AMAZONAS', '03': 'ANZOATEGUI', '04': 'APURE',
    '05': 'ARAGUA', '06': 'BARINAS', '07': 'BOLIVAR', '08': 'CARABOBO',
    '09': 'COJEDES', '10': 'DELTA AMACURO', '11': 'FALCON', '12': 'GUARICO',
    '13': 'LARA', '14': 'MERIDA', '15': 'MIRANDA', '16': 'MONAGAS',
    '17': 'NUEVA ESPARTA', '18': 'PORTUGUESA', '19': 'SUCRE', '20': 'TACHIRA',
    '21': 'TRUJILLO', '22': 'YARACUY', '23': 'ZULIA', '24': 'LA GUAIRA'
}

def cargar_data_electoral_2024(ruta_csv):
    """
    Carga y procesa el CSV de resultados 2024.
    Retorna un DataFrame enriquecido con métricas y clasificación.
    """
    if not os.path.exists(ruta_csv):
        print(f"⚠️ No se encontró el archivo: {ruta_csv}")
        return None

    try:
        # Cargar CSV asumiendo separador coma (ajustar si es punto y coma)
        # Forzamos CENTRO como string para no perder ceros a la izquierda
        # Intentamos primero con utf-8, si falla, probamos latin1 (común en español)
        try:
            df = pd.read_csv(ruta_csv, dtype={'CENTRO': str, 'MESA': str}, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(ruta_csv, dtype={'CENTRO': str, 'MESA': str}, encoding='latin1')
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        return None

    # Estandarización de nombres de columnas (por si varían ligeramente)
    df.columns = [c.upper().strip() for c in df.columns]
    
    # Validar columnas críticas
    required = ['CENTRO', 'EG', 'NM']
    if not all(col in df.columns for col in required):
        print(f"❌ El CSV debe tener las columnas: {required}")
        return None

    # 1. Agrupación por Centro (Roll-up de Mesas)
    # Si el archivo tiene una fila por mesa, sumamos para obtener el centro completo
    agg_dict = {
        'EG': 'sum',
        'NM': 'sum',
        'MESA': 'count' # Contamos filas como número de mesas
    }
    
    # Si existe columna PAR (Parroquia), la incluimos en la agrupación para no perderla
    group_cols = ['CENTRO']
    if 'PAR' in df.columns:
        group_cols.append('PAR')
        agg_dict['PAR'] = 'first' # Mantener el nombre

    df_centros = df.groupby('CENTRO').agg(agg_dict).reset_index()

    # 2. Enriquecimiento Geográfico (Decodificar Código CNE)
    def obtener_estado(codigo):
        prefijo = codigo[:2]
        return CODIGOS_ESTADO.get(prefijo, 'DESCONOCIDO')

    df_centros['ESTADO'] = df_centros['CENTRO'].apply(obtener_estado)

    # 3. Cálculo de Métricas Electorales
    df_centros['TOTAL_VOTOS'] = df_centros['EG'] + df_centros['NM']
    
    # Evitar división por cero
    df_centros = df_centros[df_centros['TOTAL_VOTOS'] > 0].copy()

    df_centros['PCT_EG'] = (df_centros['EG'] / df_centros['TOTAL_VOTOS']) * 100
    df_centros['PCT_NM'] = (df_centros['NM'] / df_centros['TOTAL_VOTOS']) * 100
    df_centros['DIFERENCIA'] = (df_centros['PCT_EG'] - df_centros['PCT_NM']).abs()

    # 4. Clasificación de Centros (Lógica de Negocio)
    def clasificar_centro(row):
        # Centros Swing: Diferencia menor al 5%
        if row['DIFERENCIA'] <= 5.0:
            return "SWING (Competido)"
        # Bastiones: Ganador con > 70%
        elif row['PCT_EG'] >= 70.0:
            return "BASTION OPOSICION"
        elif row['PCT_NM'] >= 70.0:
            return "BASTION OFICIALISMO"
        # Alto Volumen (si no es lo anterior, pero es grande)
        elif row['MESA'] >= 5:
            return "ALTO VOLUMEN"
        else:
            return "ESTANDAR"

    df_centros['CATEGORIA'] = df_centros.apply(clasificar_centro, axis=1)

    return df_centros
