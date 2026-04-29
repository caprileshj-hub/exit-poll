"""
Genera el heatmap electoral en HTML (Folium).
Soporta nivel estado (ADM1) y municipio (ADM2).

Para ADM2, resuelve la ambigüedad de nombres repetidos en distintos estados
mediante un lookup spatial pre-calculado (_adm2_lookup.json).
El lookup se genera automáticamente la primera vez y se reutiliza después.

API principal:
    generar_heatmap(datos, nivel, ruta_salida, titulo, candidatos)

    datos:
        nivel='estado'    → { nombre_estado: ventaja_float }
        nivel='municipio' → { (nombre_estado, nombre_municipio): ventaja_float }
        ventaja > 0 → gobierno gana, < 0 → oposición gana (en %)

    candidatos (dict opcional):
        { 'gobierno': 'Maduro', 'oposicion': 'Edmundo' }

Demo:
    python generador_heatmap.py [--nivel estado|municipio]
"""

import json
import os
import random
import argparse
import unicodedata

import folium
from branca.colormap import LinearColormap
from folium.features import DivIcon


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

GEOJSON_ADM1_STATIC = os.path.join(BASE_DIR, 'static', 'geoBoundaries-VEN-ADM1_simplified.geojson')
GEOJSON_ADM1_BASE = os.path.join(BASE_DIR, 'geoBoundaries-VEN-ADM1_simplified.geojson')
GEOJSON_ADM1_REPO = os.path.join(ROOT_DIR, 'geoBoundaries-VEN-ADM1_simplified.geojson')
GEOJSON_ADM1 = next(
    (path for path in (GEOJSON_ADM1_STATIC, GEOJSON_ADM1_BASE, GEOJSON_ADM1_REPO) if os.path.exists(path)),
    GEOJSON_ADM1_REPO,
)
GEOJSON_ADM2 = os.path.join(ROOT_DIR, 'legacy', 'geoBoundaries-VEN-ADM2_simplified.geojson')
LOOKUP_ADM2  = os.path.join(BASE_DIR, '_adm2_lookup.json')

UMBRAL_EMPATE = 3.0
VMIN, VMAX    = -30, 30


# ------------------------------------------------------------------
# Normalización
# ------------------------------------------------------------------

def _norm(texto: str) -> str:
    """Sin acentos, mayúsculas, sin espacios extra."""
    if not texto:
        return ''
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return nfkd.encode('ASCII', 'ignore').decode('utf-8').strip().upper()


# ------------------------------------------------------------------
# Geometría: centroide y point-in-polygon (sin dependencias externas)
# ------------------------------------------------------------------

def _centroide(geometry: dict) -> tuple:
    if geometry['type'] == 'Polygon':
        coords = geometry['coordinates'][0]
    else:  # MultiPolygon — usar el polígono con más vértices
        coords = max(geometry['coordinates'], key=lambda p: len(p[0]))[0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return sum(lons) / len(lons), sum(lats) / len(lats)


def _pip(px: float, py: float, poly: list) -> bool:
    """Ray-casting point-in-polygon."""
    inside = False
    j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _en_feature(px: float, py: float, feat: dict) -> bool:
    g = feat['geometry']
    polys = ([g['coordinates'][0]] if g['type'] == 'Polygon'
             else [p[0] for p in g['coordinates']])
    return any(_pip(px, py, p) for p in polys)


# ------------------------------------------------------------------
# Lookup ADM2: norm(estado)|norm(municipio) → shapeID
# ------------------------------------------------------------------

def _construir_lookup() -> dict:
    """
    Spatial join: asigna cada municipio ADM2 al estado ADM1 que contiene su centroide.
    Resultado guardado en _adm2_lookup.json para no recalcular.
    """
    print('[heatmap] Construyendo lookup ADM2 (solo la primera vez)...')
    with open(GEOJSON_ADM1, encoding='utf-8') as f:
        adm1 = json.load(f)
    with open(GEOJSON_ADM2, encoding='utf-8') as f:
        adm2 = json.load(f)

    lookup = {}
    sin_match = []
    for feat2 in adm2['features']:
        cx, cy  = _centroide(feat2['geometry'])
        estado  = next((f['properties']['shapeName']
                        for f in adm1['features'] if _en_feature(cx, cy, f)), None)
        muni    = feat2['properties']['shapeName']
        shp_id  = feat2['properties']['shapeID']
        if estado:
            lookup[f'{_norm(estado)}|{_norm(muni)}'] = shp_id
        else:
            sin_match.append(muni)

    if sin_match:
        print(f'[heatmap] WARN Sin estado asignado ({len(sin_match)}): {sin_match}')

    with open(LOOKUP_ADM2, 'w', encoding='utf-8') as f:
        json.dump(lookup, f, ensure_ascii=False, indent=2)
    print(f'[heatmap] Lookup guardado: {len(lookup)} municipios -> {LOOKUP_ADM2}')
    return lookup


def _lookup_adm2() -> dict:
    if os.path.exists(LOOKUP_ADM2):
        with open(LOOKUP_ADM2, encoding='utf-8') as f:
            return json.load(f)
    return _construir_lookup()


# ------------------------------------------------------------------
# Generador de heatmap
# ------------------------------------------------------------------

def generar_heatmap(
    datos: dict,
    nivel: str = 'estado',          # 'estado' | 'municipio'
    ruta_salida: str = 'heatmap.html',
    titulo: str = 'Exit Poll Venezuela',
    candidatos: dict = None,        # {'gobierno': 'Nombre', 'oposicion': 'Nombre'}
) -> bool:
    """
    Genera el heatmap HTML del exit poll.

    datos:
        nivel='estado'    → { nombre_estado: ventaja }
        nivel='municipio' → { (nombre_estado, nombre_municipio): ventaja }
        ventaja > 0 = gobierno gana   ventaja < 0 = oposición gana
    """
    cand = candidatos or {}
    cand_gob = cand.get('gobierno',  'Gobierno')
    cand_opo = cand.get('oposicion', 'Oposición')

    # --- Resolver datos a {shapeID_o_nombre_norm: ventaja} ---
    if nivel == 'municipio':
        geojson_path = GEOJSON_ADM2
        lookup       = _lookup_adm2()
        datos_id: dict = {}
        for (est, mun), v in datos.items():
            key = f'{_norm(est)}|{_norm(mun)}'
            sid = lookup.get(key)
            if sid:
                datos_id[sid] = v
            else:
                print(f'[heatmap] WARN Sin lookup: {key!r}')
        get_clave = lambda feat: feat['properties']['shapeID']
    else:  # estado
        geojson_path = GEOJSON_ADM1
        datos_id     = {_norm(k): v for k, v in datos.items()}
        get_clave    = lambda feat: _norm(feat['properties']['shapeName'])

    if not os.path.exists(geojson_path):
        print(f'[heatmap] ERROR GeoJSON no encontrado: {geojson_path}')
        return False

    with open(geojson_path, encoding='utf-8') as f:
        geojson = json.load(f)

    # --- Mapa base ---
    m = folium.Map(
        location=[7.8, -66.0], zoom_start=6,
        tiles=None, min_zoom=5, max_bounds=True
    )

    colormap = LinearColormap(
        colors=['#1565C0', '#5E92C8', '#FFFFFF', '#E07070', '#B71C1C'],
        vmin=VMIN, vmax=VMAX,
    )

    # --- Enriquecer features ---
    for feat in geojson['features']:
        clave   = get_clave(feat)
        ventaja = datos_id.get(clave)
        nombre  = feat['properties']['shapeName']

        feat['properties']['VENTAJA']    = ventaja if ventaja is not None else 0.0
        feat['properties']['TIENE_DATO'] = ventaja is not None

        if ventaja is None:
            tt = f'<b>{nombre}</b><br><i style="color:#aaa">Sin datos</i>'
        elif abs(ventaja) < UMBRAL_EMPATE:
            tt = f'<b>{nombre}</b><br>Empate técnico ({ventaja:+.1f}%)'
        elif ventaja > 0:
            tt = f'<b>{nombre}</b><br>▲ <b style="color:#B71C1C">{cand_gob}</b> +{ventaja:.1f}%'
        else:
            tt = f'<b>{nombre}</b><br>▲ <b style="color:#1565C0">{cand_opo}</b> +{abs(ventaja):.1f}%'
        feat['properties']['TT'] = tt

        # Etiquetas de nombre solo para nivel estado
        if nivel == 'estado':
            cx, cy = _centroide(feat['geometry'])
            label  = nombre if len(nombre) <= 11 else nombre[:9] + '.'
            folium.Marker(
                location=[cy, cx],
                icon=DivIcon(
                    icon_size=(120, 18), icon_anchor=(60, 9),
                    html=(f'<div style="font-size:7pt;font-weight:bold;color:#222;'
                          f'text-shadow:1px 1px 0 #fff,-1px -1px 0 #fff;'
                          f'text-align:center;pointer-events:none;white-space:nowrap;">'
                          f'{label}</div>')
                )
            ).add_to(m)

    # --- Capa GeoJSON ---
    folium.GeoJson(
        geojson,
        style_function=lambda feat: {
            'fillColor':   (colormap(feat['properties']['VENTAJA'])
                            if feat['properties']['TIENE_DATO'] else '#CCCCCC'),
            'color':       '#333333',
            'weight':      0.5 if nivel == 'municipio' else 0.9,
            'fillOpacity': 0.82 if feat['properties']['TIENE_DATO'] else 0.3,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['TT'], aliases=[''],
            localize=True, sticky=True,
            style=('background-color:white;color:#111;font-family:sans-serif;'
                   'font-size:12px;padding:8px;border-radius:4px;'
                   'box-shadow:1px 1px 4px rgba(0,0,0,.2);')
        )
    ).add_to(m)

    colormap.add_to(m)

    # --- Leyenda ---
    leyenda = f"""
    <div style="position:fixed;bottom:30px;left:30px;width:250px;
                background:white;z-index:9999;font-family:sans-serif;
                border:1px solid #ccc;border-radius:8px;padding:12px;
                box-shadow:2px 2px 6px rgba(0,0,0,.2);">
        <div style="font-weight:bold;font-size:13px;margin-bottom:8px;
                    border-bottom:1px solid #eee;padding-bottom:6px;">{titulo}</div>
        <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;">
            <span style="color:#1565C0;font-weight:bold;">◀ {cand_opo}</span>
            <span style="color:#888;font-size:10px;">Empate ±{UMBRAL_EMPATE}%</span>
            <span style="color:#B71C1C;font-weight:bold;">{cand_gob} ▶</span>
        </div>
        <div style="background:linear-gradient(to right,#1565C0,#5E92C8,#fff,#E07070,#B71C1C);
                    height:10px;border-radius:4px;"></div>
        <div style="display:flex;justify-content:space-between;
                    font-size:10px;color:#777;margin-top:3px;">
            <span>{VMIN}%</span><span>0</span><span>+{VMAX}%</span>
        </div>
        <div style="font-size:10px;color:#bbb;margin-top:8px;">
            ▪ Gris = sin datos en la muestra
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(leyenda))

    m.save(ruta_salida)
    cobertura = sum(1 for v in datos_id.values() if v is not None)
    print(f'[heatmap] OK {nivel.capitalize()} - {cobertura} zonas con datos -> {ruta_salida}')
    return True


# ------------------------------------------------------------------
# Demo
# ------------------------------------------------------------------

def _demo_estado():
    estados = [
        'Amazonas', 'Anzoátegui', 'Apure', 'Aragua', 'Barinas', 'Bolívar',
        'Carabobo', 'Cojedes', 'Delta Amacuro', 'Distrito Capital', 'Falcón',
        'Guárico', 'Lara', 'Mérida', 'Miranda', 'Monagas', 'Nueva Esparta',
        'Portuguesa', 'Sucre', 'Táchira', 'Trujillo', 'La Guaira', 'Yaracuy', 'Zulia',
    ]
    return {e: round(random.uniform(-25, 25), 1) for e in estados}


def _demo_municipio():
    """Carga nombres del GeoJSON ADM2 y el lookup para generar datos demo."""
    lookup = _lookup_adm2()
    datos = {}
    for key in lookup:
        est, mun = key.split('|', 1)
        # Solo subset aleatorio (60%) para simular cobertura parcial
        if random.random() > 0.4:
            datos[(est, mun)] = round(random.uniform(-25, 25), 1)
    return datos


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Demo del heatmap electoral')
    parser.add_argument('--nivel', choices=['estado', 'municipio'], default='estado')
    parser.add_argument('--salida', default=None)
    args = parser.parse_args()

    salida = args.salida or f'demo_heatmap_{args.nivel}.html'

    candidatos = {'gobierno': 'Candidato A', 'oposicion': 'Candidato B'}
    titulo = f'Exit Poll — Demo ({args.nivel.capitalize()})'

    if args.nivel == 'municipio':
        datos = _demo_municipio()
    else:
        datos = _demo_estado()

    generar_heatmap(datos, nivel=args.nivel, ruta_salida=salida,
                    titulo=titulo, candidatos=candidatos)
