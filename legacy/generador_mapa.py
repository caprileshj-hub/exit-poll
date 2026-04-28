# -*- coding: utf-8 -*-
from branca.colormap import LinearColormap
import folium
import json
import os
import unicodedata
import random

# --- Helpers ---

def normalizar_nombre_estado(texto):
    """
    Elimina acentos y convierte a mayúsculas para un cruce de datos robusto.
    Ej: "Mérida" -> "MERIDA"
    """
    if not isinstance(texto, str):
        return ""
    # La normalización NFKD separa los caracteres combinados en caracteres base y diacríticos
    nfkd_form = unicodedata.normalize('NFKD', texto)
    # Codificar a ASCII ignorando errores y luego decodificar de nuevo a utf-8
    # elimina eficazmente todos los diacríticos.
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    return only_ascii.upper().strip()

# --- Función Principal de Generación de Mapa ---

def crear_mapa_resultados(datos_ventaja, ruta_salida="mapa_resultados.html"):
    """
    Genera un mapa de Venezuela con Folium, coloreando los estados según la ventaja.

    Args:
        datos_ventaja (dict): Un diccionario donde las claves son los nombres de los estados
                              (en mayúsculas y sin acentos) y los valores son la ventaja
                              numérica (positiva para Rojo, negativa para Azul).
                              Ej: {"ZULIA": -15.5, "BARINAS": 5.2}
        ruta_salida (str): La ruta del archivo HTML donde se guardará el mapa.

    Returns:
        bool: True si el mapa se generó correctamente, False en caso de error.
    """
    # --- 1. Configuración y Validación de Archivos ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    geojson_path = os.path.join(base_dir, "geoBoundaries-VEN-ADM1_simplified.geojson")

    if not os.path.exists(geojson_path):
        print(f"❌ ERROR: No se encontró el archivo GeoJSON en la ruta:")
        print(f"   {geojson_path}")
        print("   Asegúrate de que el archivo 'geoBoundaries-VEN-ADM1_simplified.geojson' esté en la misma carpeta que este script.")
        return False

    with open(geojson_path, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    # --- 2. Creación del Mapa Base ---
    m = folium.Map(location=[7.5, -66], zoom_start=5.5, tiles="CartoDB positron")

    # --- 3. Preparación de Datos para el Mapa ---
    for feature in geojson_data["features"]:
        nombre_estado_normalizado = normalizar_nombre_estado(feature["properties"]["shapeName"])
        
        ventaja = datos_ventaja.get(nombre_estado_normalizado, 0.0)
        
        feature["properties"]["VENTAJA"] = ventaja
        
        if ventaja > 0:
            candidato = "Candidato A (Rojo)"
            tooltip_text = f"<b>{candidato}</b><br>Ventaja: {abs(ventaja):.1f}%"
        elif ventaja < 0:
            candidato = "Candidato B (Azul)"
            tooltip_text = f"<b>{candidato}</b><br>Ventaja: {abs(ventaja):.1f}%"
        else:
            candidato = "Empate Técnico"
            tooltip_text = f"<b>{candidato}</b>"
            
        feature["properties"]["TOOLTIP"] = tooltip_text

    # --- 4. Configuración de la Escala de Colores ---
    colormap = LinearColormap(
        colors=['#0000FF', '#FFFFFF', '#FF0000'],  # Azul, Blanco, Rojo
        vmin=-30,  # Ventaja máxima para el azul
        vmax=30,   # Ventaja máxima para el rojo
        caption='Ventaja Porcentual (%)'
    )
    m.add_child(colormap)

    # --- 5. Creación de la Capa GeoJSON ---
    folium.GeoJson(
        geojson_data,
        style_function=lambda feature: {
            'fillColor': colormap(feature["properties"]["VENTAJA"]),
            'color': 'black',
            'weight': 0.7,
            'fillOpacity': 0.8,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["shapeName", "TOOLTIP"],
            aliases=["Estado:", "Tendencia:"],
            localize=True,
            sticky=True,
            style=("background-color: white; color: black; font-family: sans-serif; font-size: 12px; padding: 10px;")
        )
    ).add_to(m)

    # --- 6. Guardado del Archivo ---
    m.save(ruta_salida)
    print(f"✅ Mapa generado exitosamente en: {ruta_salida}")
    return True

# --- Bloque de Ejecución Principal ---
if __name__ == "__main__":
    print("Iniciando la generación del mapa base...")
    ESTADOS = ["AMAZONAS", "ANZOATEGUI", "APURE", "ARAGUA", "BARINAS", "BOLIVAR", "CARABOBO", "COJEDES", "DELTA AMACURO", "DISTRITO CAPITAL", "FALCON", "GUARICO", "LARA", "MERIDA", "MIRANDA", "MONAGAS", "NUEVA ESPARTA", "PORTUGUESA", "SUCRE", "TACHIRA", "TRUJILLO", "LA GUAIRA", "YARACUY", "ZULIA"]
    datos_mock = {estado: random.uniform(-30, 30) for estado in ESTADOS}
    crear_mapa_resultados(datos_mock, "mapa_venezuela.html")