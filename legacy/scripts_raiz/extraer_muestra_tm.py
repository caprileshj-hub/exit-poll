# -*- coding: utf-8 -*-
import pandas as pd
import os
import unicodedata

# --- Configuración ---
base_dir = os.path.dirname(os.path.abspath(__file__))
RUTA_TM = os.path.join(base_dir, 'legacy', 'TM2017.xlsx')
HOJA_TM = 'TM'
ARCHIVO_SALIDA = os.path.join(base_dir, 'muestra_estrategica_2017.csv')

def normalizar(texto):
    """Normaliza texto (Mayúsculas, sin tildes) para comparaciones."""
    if not isinstance(texto, str):
        return str(texto)
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').upper().strip()

def main():
    print(f"🚀 Iniciando extracción de muestra estratégica desde: {RUTA_TM}")

    if not os.path.exists(RUTA_TM):
        print(f"❌ ERROR: No se encontró el archivo {RUTA_TM}")
        return

    try:
        # 1. Carga preliminar para detectar columnas
        print("   Leyendo cabeceras para identificar columnas...")
        df_preview = pd.read_excel(RUTA_TM, sheet_name=HOJA_TM, nrows=5)
        cols = df_preview.columns
        
        # Detección inteligente de columnas
        col_estado = next((c for c in cols if 'ESTADO' in c.upper() and 'COD' not in c.upper()), None)
        col_municipio = next((c for c in cols if 'MUNICIPIO' in c.upper() and 'COD' not in c.upper()), None)
        col_parroquia = next((c for c in cols if 'PARROQUIA' in c.upper() and 'COD' not in c.upper()), None)
        # Buscamos 'NOMBRE_CENTRO', 'CENTRO' o 'NOMBRE'
        col_centro = next((c for c in cols if ('NOMBRE' in c.upper() and 'CENTRO' in c.upper()) or c.upper() == 'CENTRO'), None)
        if not col_centro: # Intento fallback
            col_centro = next((c for c in cols if 'NOMBRE' in c.upper() and 'ESTADO' not in c.upper() and 'MUN' not in c.upper() and 'PAR' not in c.upper()), None)
            
        col_electores = next((c for c in cols if 'ELECTORES' in c.upper() or 'VOTANTES' in c.upper()), None)

        if not (col_estado and col_parroquia and col_centro and col_electores):
            print("❌ No se pudieron identificar todas las columnas necesarias.")
            print(f"   Detectadas: Est={col_estado}, Par={col_parroquia}, Cen={col_centro}, Ele={col_electores}")
            return

        print(f"✅ Columnas: {col_estado} | {col_parroquia} | {col_centro} | {col_electores}")

        # 2. Carga de datos completa
        print("⏳ Cargando datos (esto puede tardar unos segundos)...")
        df = pd.read_excel(RUTA_TM, sheet_name=HOJA_TM, usecols=[col_estado, col_municipio, col_parroquia, col_centro, col_electores])
        
        # Normalización de nombres clave
        df['ESTADO_NORM'] = df[col_estado].apply(normalizar)
        df['PARROQUIA_NORM'] = df[col_parroquia].apply(normalizar)
        
        # 3. Agrupación por Centro (Sumar mesas)
        # Un centro tiene varias mesas, necesitamos el total de electores del centro.
        print("   Agrupando mesas por centro...")
        df_centros = df.groupby(['ESTADO_NORM', col_municipio, 'PARROQUIA_NORM', col_centro])[col_electores].sum().reset_index()
        df_centros.rename(columns={col_electores: 'TOTAL_ELECTORES', col_centro: 'NOMBRE_CENTRO', col_municipio: 'MUNICIPIO'}, inplace=True)

        muestra_final = []

        # Obtener lista de estados
        estados = df_centros['ESTADO_NORM'].unique()

        print("\n🏭 Procesando selección por Estado:")
        
        for estado in estados:
            df_estado = df_centros[df_centros['ESTADO_NORM'] == estado]
            
            # --- CASO ESPECIAL: DISTRITO CAPITAL y VARGAS ---
            if estado in ['DISTRITO CAPITAL', 'VARGAS', 'LA GUAIRA']:
                print(f"   🔹 {estado}: Aplicando lógica especial (Top 8 Parroquias -> Top 2 Centros)")
                
                # 1. Ranking de Parroquias por población electoral
                parroquias_rank = df_estado.groupby('PARROQUIA_NORM')['TOTAL_ELECTORES'].sum().reset_index()
                parroquias_rank = parroquias_rank.sort_values('TOTAL_ELECTORES', ascending=False)
                
                top_8_parroquias = parroquias_rank.head(8)['PARROQUIA_NORM'].tolist()
                
                for parr in top_8_parroquias:
                    # 2. En cada parroquia, Top 2 Centros
                    df_parr = df_estado[df_estado['PARROQUIA_NORM'] == parr]
                    top_centros = df_parr.sort_values('TOTAL_ELECTORES', ascending=False).head(2)
                    
                    for _, row in top_centros.iterrows():
                        row_dict = row.to_dict()
                        row_dict['CRITERIO'] = f"Top 2 en Parroquia Top 8 ({parr})"
                        muestra_final.append(row_dict)

            # --- CASO GENERAL: RESTO DEL PAÍS ---
            else:
                # Top 4 Centros del Estado
                top_centros = df_estado.sort_values('TOTAL_ELECTORES', ascending=False).head(4)
                for _, row in top_centros.iterrows():
                    row_dict = row.to_dict()
                    row_dict['CRITERIO'] = "Top 4 del Estado"
                    muestra_final.append(row_dict)

        # 4. Exportar Resultados
        df_muestra = pd.DataFrame(muestra_final)
        
        # Reordenar columnas para que se vea bonito
        cols_orden = ['ESTADO_NORM', 'MUNICIPIO', 'PARROQUIA_NORM', 'NOMBRE_CENTRO', 'TOTAL_ELECTORES', 'CRITERIO']
        df_muestra = df_muestra[cols_orden]
        
        df_muestra.to_csv(ARCHIVO_SALIDA, index=False, encoding='utf-8')
        
        print("\n✅ ¡Extracción completada!")
        print(f"   Archivo guardado en: {ARCHIVO_SALIDA}")
        print(f"   Total de centros seleccionados: {len(df_muestra)}")
        
        # Mostrar un preview en consola
        print("\n👀 Vista previa de la muestra:")
        print("-" * 80)
        print(f"{'ESTADO':<15} | {'PARROQUIA':<20} | {'CENTRO':<30} | {'ELECTORES'}")
        print("-" * 80)
        
        # Mostrar algunos ejemplos (DC y uno del interior)
        ejemplos = pd.concat([
            df_muestra[df_muestra['ESTADO_NORM'] == 'DISTRITO CAPITAL'].head(4),
            df_muestra[df_muestra['ESTADO_NORM'] == 'ZULIA'].head(2)
        ])
        
        for _, row in ejemplos.iterrows():
            cen = (row['NOMBRE_CENTRO'][:28] + '..') if len(row['NOMBRE_CENTRO']) > 28 else row['NOMBRE_CENTRO']
            par = (row['PARROQUIA_NORM'][:18] + '..') if len(row['PARROQUIA_NORM']) > 18 else row['PARROQUIA_NORM']
            print(f"{row['ESTADO_NORM']:<15} | {par:<20} | {cen:<30} | {row['TOTAL_ELECTORES']}")

    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()