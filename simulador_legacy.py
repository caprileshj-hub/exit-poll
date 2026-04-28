# -*- coding: utf-8 -*-
import pandas as pd
import os
import procesador_datos
import generador_mapa
import shutil

# --- Configuración ---
RUTA_EXCEL = os.path.join('legacy', 'core.xlsx')
SHEET_DATOS = 'Resultados' # Asumo que la hoja con datos de encuestas se llama así
SHEET_PESOS = 'Pesos'       # Asumo que la hoja con los pesos se llama así
CARPETA_SALIDA = 'simulacion_legacy_output'

def crear_tabla_pesos_desde_excel(df_pesos):
    """
    Transforma un DataFrame plano de pesos en la estructura anidada
    que espera el procesador_datos.py.
    
    Asume un DataFrame con columnas: ESTADO, MUNICIPIO, PARROQUIA, PESO
    """
    tabla_pesos = {}
    df_pesos['ESTADO'] = df_pesos['ESTADO'].apply(procesador_datos.normalizar_texto)
    df_pesos['MUNICIPIO'] = df_pesos['MUNICIPIO'].apply(procesador_datos.normalizar_texto)
    df_pesos['PARROQUIA'] = df_pesos['PARROQUIA'].apply(procesador_datos.normalizar_texto)

    for _, row in df_pesos.iterrows():
        est, mun, par, peso = row['ESTADO'], row['MUNICIPIO'], row['PARROQUIA'], row['PESO']
        
        if not est or not mun:
            continue

        if est not in tabla_pesos:
            tabla_pesos[est] = {}
        
        if mun not in tabla_pesos[est]:
            tabla_pesos[est][mun] = {'municipio': 0.0, 'parroquias': {}}

        # Si la parroquia está definida y no es un NaN, es un peso parroquial
        if par and pd.notna(row['PARROQUIA']):
            tabla_pesos[est][mun]['parroquias'][par] = peso
        else: # Si no, es un peso a nivel de municipio
            tabla_pesos[est][mun]['municipio'] = peso
            
    return tabla_pesos

def main():
    """
    Orquesta la simulación completa:
    1. Lee datos y pesos del Excel legacy.
    2. Procesa las tendencias por cortes de tiempo.
    3. Genera un mapa HTML para cada corte.
    """
    print("🚀 Iniciando simulacro desde archivo Excel legacy...")

    # 1. Validar y leer el archivo Excel
    if not os.path.exists(RUTA_EXCEL):
        print(f"❌ ERROR: No se encontró el archivo de simulación en '{RUTA_EXCEL}'.")
        print("   Por favor, asegúrate de que 'core.xlsx' exista en la carpeta 'legacy'.")
        return

    try:
        df_datos = pd.read_excel(RUTA_EXCEL, sheet_name=SHEET_DATOS)
        df_pesos = pd.read_excel(RUTA_EXCEL, sheet_name=SHEET_PESOS)
        print(f"✅ Archivo '{RUTA_EXCEL}' cargado correctamente.")
    except Exception as e:
        print(f"❌ ERROR: No se pudo leer el archivo Excel. Causa: {e}")
        print(f"   Verifica que el archivo contenga las hojas '{SHEET_DATOS}' y '{SHEET_PESOS}'.")
        return

    # 2. Preparar datos para el procesamiento
    print("🔧 Transformando datos para el procesador...")
    
    # Crear la tabla de pesos desde el DataFrame
    tabla_pesos = crear_tabla_pesos_desde_excel(df_pesos)
    
    # Renombrar columnas del Excel a las esperadas por el procesador
    # y convertir a formato de lista de diccionarios.
    try:
        df_datos = df_datos.rename(columns={
            'HORA': 'hora',
            'ESTADO': 'estado',
            'MUNICIPIO': 'municipio',
            'PARROQUIA': 'parroquia',
            'VOTOS_ROJO': 'rojo',
            'VOTOS_AZUL': 'azul'
        })
        # Asegurarse que la hora sea un string en formato HH:MM
        df_datos['hora'] = pd.to_datetime(df_datos['hora'], format='%H:%M:%S').dt.strftime('%H:%M')
        
        datos_entrada = df_datos[['hora', 'estado', 'municipio', 'parroquia', 'rojo', 'azul']].to_dict('records')
    except KeyError as e:
        print(f"❌ ERROR: Falta una columna esperada en la hoja '{SHEET_DATOS}': {e}")
        print("   Las columnas esperadas son: HORA, ESTADO, MUNICIPIO, PARROQUIA, VOTOS_ROJO, VOTOS_AZUL.")
        return

    # 3. Procesar las tendencias
    print("📊 Calculando tendencias por cortes de tiempo...")
    tendencias = procesador_datos.procesar_tendencias(datos_entrada, tabla_pesos)
    
    if not tendencias:
        print("⚠️ No se generaron tendencias. Revisa los datos de entrada y los pesos.")
        return

    # 4. Generar los mapas para cada corte
    print(f"🗺️  Generando mapas en la carpeta '{CARPETA_SALIDA}'...")
    if os.path.exists(CARPETA_SALIDA):
        shutil.rmtree(CARPETA_SALIDA) # Limpiar carpeta de resultados anteriores
    os.makedirs(CARPETA_SALIDA)

    for corte, resultados_corte in tendencias.items():
        datos_ventaja = {estado: data.get('ventaja', 0.0) for estado, data in resultados_corte.items() if estado != 'VENEZUELA'}
        nombre_archivo = f"mapa_{corte.replace(':', '')}.html"
        ruta_salida = os.path.join(CARPETA_SALIDA, nombre_archivo)
        print(f"   -> Generando mapa para el corte de las {corte}...")
        generador_mapa.crear_mapa_resultados(datos_ventaja, ruta_salida=ruta_salida)

    print("\n✅ ¡Simulacro completado!")
    print(f"   Los mapas se han guardado en la carpeta '{CARPETA_SALIDA}'.")
    print("   Abre los archivos .html en tu navegador para ver los resultados de cada corte.")

if __name__ == "__main__":
    main()