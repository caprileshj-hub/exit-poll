# -*- coding: utf-8 -*-
from branca.colormap import LinearColormap
from folium.features import DivIcon
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

def calcular_centroide(geometry):
    """Calcula un centroide aproximado para colocar la etiqueta del estado."""
    coords = []
    if geometry['type'] == 'Polygon':
        coords = geometry['coordinates'][0]
    elif geometry['type'] == 'MultiPolygon':
        # Tomamos el polígono más grande o simplemente el primero para simplificar
        coords = geometry['coordinates'][0][0]
    
    if not coords:
        return [7.5, -66.0] # Fallback centro de Vzla
        
    lons = [p[0] for p in coords]
    lats = [p[1] for p in coords]
    return [sum(lats)/len(lats), sum(lons)/len(lons)]

# --- Función Principal de Generación de Mapa ---

def crear_mapa_resultados(datos_ventaja, ruta_salida="mapa_resultados.html", tipo_eleccion="NACIONAL", info_candidatos=None):
    """
    Genera un mapa de Venezuela con Folium, coloreando los estados según la ventaja.

    Args:
        datos_ventaja (dict): Un diccionario donde las claves son los nombres de los estados
                              (en mayúsculas y sin acentos) y los valores son la ventaja
                              numérica (positiva para Rojo, negativa para Azul).
                              Ej: {"ZULIA": -15.5, "BARINAS": 5.2}
        tipo_eleccion (str): "NACIONAL" o "REGIONAL".
        info_candidatos (dict): Diccionario con nombres de candidatos.
                                Si NACIONAL: {"ROJO": "NombreA", "AZUL": "NombreB"}
                                Si REGIONAL: {"ZULIA": {"ROJO": "CandZ1", "AZUL": "CandZ2"}, ...}
        ruta_salida (str): La ruta del archivo HTML donde se guardará el mapa.

    Returns:
        bool: True si el mapa se generó correctamente, False en caso de error.
    """
    # --- 0. Configuración de Negocio ---
    UMBRAL_EMPATE = 3.0  # Diferencia menor a 3% se considera empate técnico

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
    # tiles=None elimina el mapa mundi de fondo (países vecinos), dejando solo Venezuela flotando.
    m = folium.Map(
        location=[7.8, -66.0], 
        zoom_start=6, 
        tiles=None,
        min_zoom=6,
        max_bounds=True
    )

    # --- 3. Preparación de Datos para el Mapa ---
    for feature in geojson_data["features"]:
        nombre_estado_normalizado = normalizar_nombre_estado(feature["properties"]["shapeName"])
        
        ventaja = datos_ventaja.get(nombre_estado_normalizado, 0.0)
        
        feature["properties"]["VENTAJA"] = ventaja
        
        # --- Lógica de Nombres de Candidatos ---
        candidato_rojo = "Oficialismo"
        candidato_azul = "Oposición"
        
        if tipo_eleccion == "NACIONAL" and info_candidatos:
            candidato_rojo = info_candidatos.get("ROJO", candidato_rojo)
            candidato_azul = info_candidatos.get("AZUL", candidato_azul)
        elif tipo_eleccion == "REGIONAL" and info_candidatos:
            # Buscar candidatos específicos del estado
            local_cands = info_candidatos.get(nombre_estado_normalizado, {})
            candidato_rojo = local_cands.get("ROJO", candidato_rojo)
            candidato_azul = local_cands.get("AZUL", candidato_azul)

        # Lógica de Empate Técnico y Tooltips
        if abs(ventaja) < UMBRAL_EMPATE:
            header = "Empate Técnico"
            body = f"Diferencia: {abs(ventaja):.1f}%<br>(Margen < {UMBRAL_EMPATE}%)"
        elif ventaja > 0:
            header = f"Ganando: {candidato_rojo}"
            body = f"Ventaja: {abs(ventaja):.1f}%"
        else:
            header = f"Ganando: {candidato_azul}"
            body = f"Ventaja: {abs(ventaja):.1f}%"
            
        tooltip_text = f"<b>{feature['properties']['shapeName']}</b><br>{header}<br>{body}"
        feature["properties"]["TOOLTIP"] = tooltip_text

        # --- 3.1 Agregar Etiquetas de Nombres de Estados ---
        centro = calcular_centroide(feature['geometry'])
        
        # Crear Popup con Gráfica (Simulada)
        # En un entorno real, 'graph_url' apuntaría a una imagen generada o un endpoint de API
        graph_url = f"https://placehold.co/300x150/EEE/31343C?text=Tendencia+{feature['properties']['shapeName']}&font=roboto"
        
        popup_html = f"""
        <div style="font-family:sans-serif; width:300px;">
            <h4 style="margin-bottom:5px; border-bottom:1px solid #ccc;">{feature['properties']['shapeName']}</h4>
            <div style="margin-bottom:10px; font-size:12px;">
                <span style="color:red;">&#9632;</span> <b>{candidato_rojo}</b><br>
                <span style="color:blue;">&#9632;</span> <b>{candidato_azul}</b>
            </div>
            <div style="text-align:center;">
                <img src="{graph_url}" style="width:100%; border:1px solid #ccc; border-radius:4px;">
            </div>
            <p style="font-size:10px; color:grey; text-align:center; margin-top:5px;">
                Click para ver detalles históricos
            </p>
        </div>
        """

        folium.Marker(
            location=centro,
            icon=DivIcon(
                icon_size=(100, 20),
                icon_anchor=(50, 10),
                html=f'<div style="font-size: 8pt; font-weight: bold; color: #333; text-shadow: 1px 1px 0 #fff; text-align: center; cursor: pointer;">{feature["properties"]["shapeName"]}</div>'
            ),
            popup=folium.Popup(popup_html, max_width=320)
        ).add_to(m)

    # --- 4. Configuración de la Escala de Colores ---
    colormap = LinearColormap(
        colors=['#0000FF', '#FFFFFF', '#FF0000'],  # Azul, Blanco, Rojo
        vmin=-30,  # Ventaja máxima para el azul
        vmax=30,   # Ventaja máxima para el rojo
        caption='Ventaja Porcentual (%)'
    )
    # No añadimos colormap estándar al mapa, usaremos la leyenda personalizada abajo
    # m.add_child(colormap) 

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

    # --- 5.1 Leyenda Personalizada con Fotos ---
    # Puedes reemplazar las URLs de las imágenes por las reales de los candidatos
    legend_html = """
    <div style="
        position: fixed; 
        bottom: 30px; left: 30px; width: 320px; height: 155px; 
        background-color: white; z-index:9999; font-size:14px;
        border:2px solid #ccc; border-radius: 10px; padding: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    ">
        <h4 style="text-align:center; margin: 0 0 10px 0; font-family: sans-serif;">Tendencia Electoral</h4>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <div style="text-align: center;">
                <img src="https://placehold.co/50x50/0000FF/FFFFFF?text=Azul" style="width:50px; height:50px; border-radius:50%; border: 3px solid blue;"><br>
                <span style="color: blue; font-weight: bold; font-size: 12px;">Oposición</span>
            </div>
            <div style="text-align: center;">
                <img src="https://placehold.co/50x50/FF0000/FFFFFF?text=Rojo" style="width:50px; height:50px; border-radius:50%; border: 3px solid red;"><br>
                <span style="color: red; font-weight: bold; font-size: 12px;">Oficialismo</span>
            </div>
        </div>
        <div style="background: linear-gradient(to right, blue, white, red); height: 15px; width: 100%; border-radius: 5px; border: 1px solid #999;"></div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #555; margin-top: 2px; font-weight: bold;">
            <span>-30%</span>
            <span>0% (Empate)</span>
            <span>+30%</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # --- 6. Guardado del Archivo ---
    m.save(ruta_salida)
    print(f"✅ Mapa generado exitosamente en: {ruta_salida}")
    return True

# --- Bloque de Ejecución Principal ---
if __name__ == "__main__":
    print("Iniciando la generación del mapa base...")
    ESTADOS = ["AMAZONAS", "ANZOATEGUI", "APURE", "ARAGUA", "BARINAS", "BOLIVAR", "CARABOBO", "COJEDES", "DELTA AMACURO", "DISTRITO CAPITAL", "FALCON", "GUARICO", "LARA", "MERIDA", "MIRANDA", "MONAGAS", "NUEVA ESPARTA", "PORTUGUESA", "SUCRE", "TACHIRA", "TRUJILLO", "LA GUAIRA", "YARACUY", "ZULIA"]
    datos_mock = {estado: random.uniform(-30, 30) for estado in ESTADOS}
    
    # Ejemplo de Configuración para Elección Regional
    candidatos_mock = {
        "ZULIA": {"ROJO": "Maduro", "AZUL": "Rosales"},
        "MIRANDA": {"ROJO": "Hector R.", "AZUL": "Ocariz"},
        "CARABOBO": {"ROJO": "Lacava", "AZUL": "Scarano"},
        # ... resto de estados con valores por defecto
    }
    
    crear_mapa_resultados(
        datos_mock, 
        "mapa_venezuela.html", 
        tipo_eleccion="REGIONAL", 
        info_candidatos=candidatos_mock
    )