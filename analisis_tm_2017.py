# -*- coding: utf-8 -*-
import pandas as pd
import os
import unicodedata

# --- Configuración ---
base_dir = os.path.dirname(os.path.abspath(__file__))
RUTA_TM = os.path.join(base_dir, 'legacy', 'TM2017.xlsx')
HOJA_TM = 'TM'

def normalizar(texto):
    """Normaliza texto para comparaciones (Mayúsculas, sin tildes)."""
    if not isinstance(texto, str):
        return str(texto)
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').upper().strip()

def main():
    print(f"🔍 Iniciando auditoría de archivo: {RUTA_TM}")
    
    if not os.path.exists(RUTA_TM):
        print(f"❌ ERROR: No se encontró el archivo en: {RUTA_TM}")
        return

    try:
        # 1. Carga preliminar para detectar columnas
        print("   Leyendo cabeceras...")
        df_preview = pd.read_excel(RUTA_TM, sheet_name=HOJA_TM, nrows=5)
        
        # Búsqueda inteligente de columnas
        cols = df_preview.columns
        col_estado = next((c for c in cols if 'ESTADO' in c.upper() and 'COD' not in c.upper()), None)
        col_municipio = next((c for c in cols if 'MUNICIPIO' in c.upper() and 'COD' not in c.upper()), None)
        col_electores = next((c for c in cols if 'ELECTORES' in c.upper() or 'VOTANTES' in c.upper()), None)

        if not (col_estado and col_municipio and col_electores):
            print("⚠️  No se pudieron identificar automáticamente las columnas clave.")
            print(f"   Columnas disponibles: {list(cols)}")
            return

        print(f"✅ Columnas identificadas: Estado='{col_estado}', Municipio='{col_municipio}', Electores='{col_electores}'")

        # 2. Carga de datos
        print("⏳ Cargando dataset completo (esto puede tomar unos segundos)...")
        df = pd.read_excel(RUTA_TM, sheet_name=HOJA_TM, usecols=[col_estado, col_municipio, col_electores])
        
        # Normalización
        df['ESTADO_NORM'] = df[col_estado].apply(normalizar)
        df['MUNICIPIO_NORM'] = df[col_municipio].apply(normalizar)

        # 3. Auditoría Específica: Caso AMAZONAS
        print("\n--- 🕵️  Auditoría de Integridad: AMAZONAS ---")
        amazonas_df = df[df['ESTADO_NORM'] == 'AMAZONAS']
        
        if amazonas_df.empty:
            print("⚠️  ALERTA: No se encontraron registros para el estado 'AMAZONAS'.")
        else:
            muns_amazonas = sorted(amazonas_df['MUNICIPIO_NORM'].unique())
            print(f"   Municipios detectados en AMAZONAS ({len(muns_amazonas)}):")
            
            muns_correctos = {'ATURES', 'AUTANA', 'MANAPIARE', 'MAROA', 'RIO NEGRO', 'ALTO ORINOCO', 'ATABAPO'}
            muns_encontrados = set(muns_amazonas)
            
            infiltrados = muns_encontrados - muns_correctos
            faltantes = muns_correctos - muns_encontrados

            for m in muns_amazonas:
                mark = "❌ INTRUSO" if m in infiltrados else "✅"
                print(f"   - {m} {mark}")
            
            if not infiltrados and not faltantes:
                print("   ✅ La geografía de Amazonas parece CORRECTA.")
            elif infiltrados:
                print(f"   ❌ ALERTA: Hay municipios infiltrados de otros estados: {infiltrados}")

        # 4. Generación de Tabla de Pesos Reales (2017)
        print("\n--- ⚖️  Distribución de Pesos Reales (Base Electores 2017) ---")
        total_pais = df[col_electores].sum()
        agrupado = df.groupby('ESTADO_NORM')[col_electores].sum().reset_index()
        agrupado['PESO_REAL'] = (agrupado[col_electores] / total_pais) * 100
        agrupado = agrupado.sort_values('PESO_REAL', ascending=False)

        print(f"{'ESTADO':<20} | {'ELECTORES':>12} | {'PESO %':>8}")
        print("-" * 46)
        for _, row in agrupado.iterrows():
            print(f"{row['ESTADO_NORM']:<20} | {row[col_electores]:>12,.0f} | {row['PESO_REAL']:>7.4f}%")

    except Exception as e:
        print(f"❌ Error procesando el archivo: {e}")

if __name__ == "__main__":
    main()