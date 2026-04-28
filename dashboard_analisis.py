# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import procesador_csv_2024
import os

# Configuración de la página
st.set_page_config(page_title="Exit Poll - Análisis de Muestra", layout="wide")

st.title("🗳️ Tablero de Selección de Muestra (Data 2024)")
st.markdown("""
Este dashboard analiza los resultados históricos por centro para determinar 
cuáles son los puntos estratégicos para el despliegue del Exit Poll.
""")

# --- 1. Carga de Datos ---
base_dir = os.path.dirname(os.path.abspath(__file__))
default_path = os.path.join(base_dir, "RESULTADOS_2024_CSV_V3.csv")
ruta_archivo = st.text_input("Ruta del archivo CSV 2024:", value=default_path)

@st.cache_data
def cargar_datos(ruta):
    return procesador_csv_2024.cargar_data_electoral_2024(ruta)

if st.button("Cargar y Analizar"):
    df = cargar_datos(ruta_archivo)
    
    if df is not None:
        st.success(f"✅ Data cargada exitosamente: {len(df)} centros procesados.")
        
        # --- 2. Filtros Laterales ---
        st.sidebar.header("Filtros de Selección")
        
        estados = sorted(df['ESTADO'].unique())
        estado_sel = st.sidebar.selectbox("Filtrar por Estado:", ["TODOS"] + estados)
        
        categorias = sorted(df['CATEGORIA'].unique())
        cat_sel = st.sidebar.multiselect("Categoría del Centro:", categorias, default=categorias)
        
        min_mesas = st.sidebar.slider("Mínimo de Mesas:", 1, int(df['MESA'].max()), 1)

        # Aplicar filtros
        df_filtrado = df.copy()
        if estado_sel != "TODOS":
            df_filtrado = df_filtrado[df_filtrado['ESTADO'] == estado_sel]
        
        if cat_sel:
            df_filtrado = df_filtrado[df_filtrado['CATEGORIA'].isin(cat_sel)]
            
        df_filtrado = df_filtrado[df_filtrado['MESA'] >= min_mesas]

        # --- 3. KPIs Principales ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Centros Seleccionados", len(df_filtrado))
        col2.metric("Votos Totales (Muestra)", f"{df_filtrado['TOTAL_VOTOS'].sum():,}")
        prom_eg = df_filtrado['PCT_EG'].mean()
        prom_nm = df_filtrado['PCT_NM'].mean()
        col3.metric("Promedio Histórico EG", f"{prom_eg:.1f}%")
        col4.metric("Promedio Histórico NM", f"{prom_nm:.1f}%")

        # --- 4. Visualización ---
        
        # Gráfico de Dispersión: Tamaño del Centro vs Polarización
        st.subheader("Mapa de Dispersión: Tamaño vs. Sesgo Político")
        fig_scatter = px.scatter(
            df_filtrado, 
            x="PCT_EG", 
            y="TOTAL_VOTOS",
            color="CATEGORIA",
            size="MESA",
            hover_data=['CENTRO', 'ESTADO', 'PAR'],
            title="Distribución de Centros (Eje X: % Voto Oposición)",
            labels={"PCT_EG": "% Votos EG", "TOTAL_VOTOS": "Total Votos Válidos"}
        )
        # Línea de 50%
        fig_scatter.add_vline(x=50, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_scatter, use_container_width=True)

        # --- 5. Tabla de Datos ---
        st.subheader("Detalle de Centros Seleccionados")
        st.dataframe(
            df_filtrado[['CENTRO', 'ESTADO', 'PAR', 'MESA', 'TOTAL_VOTOS', 'PCT_EG', 'PCT_NM', 'CATEGORIA']]
            .sort_values(by='TOTAL_VOTOS', ascending=False),
            use_container_width=True
        )
        
        # Botón de descarga
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Descargar Muestra Filtrada (CSV)",
            csv,
            "muestra_exit_poll.csv",
            "text/csv",
            key='download-csv'
        )

    else:
        st.error("No se pudo cargar el archivo. Verifica la ruta y el formato.")
