# -*- coding: utf-8 -*-
import json
import folium
from folium.features import GeoJsonTooltip
from branca.colormap import LinearColormap
import os
import unicodedata

# Configuración de Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_FILE = os.path.join(BASE_DIR, "geoBoundaries-VEN-ADM1_simplified.geojson")

def normalizar_texto(texto):
    """Elimina acentos y convierte a mayúsculas para asegurar el cruce de datos."""
    if not isinstance(texto, str): return str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto.upper().strip()

def crear_mapa_ventaja(datos_ventaja):
    """
    Genera un objeto mapa de Folium basado en un diccionario de ventajas.
    
    Args:
        datos_ventaja (dict): Diccionario { "NombreEstado": valor_float }
                              Ej: {"ZULIA": -0.15, "BARINAS": 0.05}
                              - Valor Negativo: Ventaja Candidato Azul (ej. -0.15 = 15%)
                              - Valor Positivo: Ventaja Candidato Rojo (ej. 0.05 = 5%)
                              - 0: Empate técnico (Blanco)
    Returns:
        folium.Map: Objeto mapa listo para renderizar en Streamlit o guardar como HTML.
    """
    
    # 1. Cargar GeoJSON (Solo si existe)
    if not os.path.exists(GEOJSON_FILE):
        print(f"Error: No se encuentra el archivo GeoJSON en: {GEOJSON_FILE}")
        return folium.Map(location=[7.5, -66], zoom_start=6)

    with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    # 2. Configurar el Mapa Base (Limpio, sin tiles pesados)
    m = folium.Map(location=[7.5, -66], zoom_start=6, tiles="CartoDB positron")

    # 3. Inyectar datos en el GeoJSON para el Tooltip
    # Esto evita depender de pandas para el cruce
    for feature in geojson_data["features"]:
        nombre_original = feature["properties"]["shapeName"]
        nombre_estado = normalizar_texto(nombre_original)
        
        # Obtener ventaja (default 0 si no hay datos)
        ventaja = datos_ventaja.get(nombre_estado, 0.0)
        
        feature["properties"]["VENTAJA_VAL"] = ventaja
        
        # Formato texto para tooltip
        candidato = "Empate"
        if ventaja > 0: candidato = "Rojo"
        elif ventaja < 0: candidato = "Azul"
        
        feature["properties"]["TOOLTIP_TXT"] = f"{candidato} ({abs(ventaja)*100:.1f}%)"

    # 4. Crear Escala de Colores Divergente (Azul <-> Blanco <-> Rojo)
    # Rango fijo de -30% a +30% para que los colores sean consistentes
    colormap = LinearColormap(
        colors=['blue', 'white', 'red'],
        vmin=-0.30, vmax=0.30,
        caption='Ventaja Porcentual (Azul vs Rojo)'
    )
    m.add_child(colormap)

    # 5. Añadir Capa GeoJSON
    folium.GeoJson(
        geojson_data,
        style_function=lambda feature: {
            'fillColor': colormap(feature["properties"]["VENTAJA_VAL"]),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        },
        tooltip=GeoJsonTooltip(
            fields=['shapeName', 'TOOLTIP_TXT'],
            aliases=['Estado:', 'Tendencia:'],
            localize=True
        )
    ).add_to(m)

    return m

# ---------------------------------------------------------
# Bloque de Prueba (Solo corre si ejecutas este script directamente)
# ---------------------------------------------------------
if __name__ == "__main__":
    import random
    print("Generando mapa de prueba con datos aleatorios...")
    
    # Simular datos de DB
    estados_demo = ["ZULIA", "MIRANDA", "CARABOBO", "LARA", "ARAGUA", "BOLIVAR", "TACHIRA", "MERIDA"]
    datos_mock = {est: random.uniform(-0.4, 0.4) for est in estados_demo}
    
    mapa = crear_mapa_ventaja(datos_mock)
    mapa.save("mapa_test_memoria.html")
    print("✅ Mapa guardado como 'mapa_test_memoria.html'")
