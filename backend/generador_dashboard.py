"""
Dashboard electoral: mapa Folium + gráficos de tendencia Plotly en un solo HTML.

Click en un estado/municipio del mapa → muestra su gráfico de tendencia.

API:
    generar_dashboard(datos_ventaja, datos_tendencia, nivel, ruta_salida,
                      titulo, candidatos)

    datos_ventaja:
        nivel='estado'    → { nombre_estado: ventaja_float }
        nivel='municipio' → { (nombre_estado, nombre_municipio): ventaja_float }
        ventaja > 0 = gobierno, < 0 = oposición

    datos_tendencia:
        {
            "VENEZUELA": [{"hora": "07:00", "gob": 48.5, "opo": 49.2}, ...],
            "ZULIA":     [...],
            ...
        }
        clave "VENEZUELA" = resumen nacional (se muestra al inicio)

Demo:
    python generador_dashboard.py [--nivel estado|municipio]
"""

import json
import os
import random
import argparse
import unicodedata
import tempfile

import folium
import plotly.graph_objects as go
from branca.colormap import LinearColormap
from branca.element import Element
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
GEOJSON_ADM2 = os.path.join(BASE_DIR, 'geoBoundaries-VEN-ADM2_simplified.geojson')
LOOKUP_ADM2  = os.path.join(BASE_DIR, '_adm2_lookup.json')

UMBRAL_EMPATE = 3.0
VMIN, VMAX    = -30, 30
MARGEN_ERROR  = 2.5


# ------------------------------------------------------------------
# Normalización (igual que en generador_heatmap)
# ------------------------------------------------------------------

def _norm(texto: str) -> str:
    if not texto:
        return ''
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return nfkd.encode('ASCII', 'ignore').decode('utf-8').strip().upper()


def _id_chart(nombre: str) -> str:
    """ID del div Plotly (interno)."""
    return 'pchart-' + _norm(nombre).replace(' ', '_').replace('.', '')


def _id_wrap(nombre: str) -> str:
    """ID del div contenedor (para mostrar/ocultar)."""
    return 'wrap-' + _norm(nombre).replace(' ', '_').replace('.', '')


# ------------------------------------------------------------------
# Geometría (misma lógica que generador_heatmap)
# ------------------------------------------------------------------

def _centroide(geometry):
    if geometry['type'] == 'Polygon':
        coords = geometry['coordinates'][0]
    else:
        coords = max(geometry['coordinates'], key=lambda p: len(p[0]))[0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return sum(lons) / len(lons), sum(lats) / len(lats)


def _pip(px, py, poly):
    inside = False
    j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _en_feature(px, py, feat):
    g = feat['geometry']
    polys = ([g['coordinates'][0]] if g['type'] == 'Polygon'
             else [p[0] for p in g['coordinates']])
    return any(_pip(px, py, p) for p in polys)


def _lookup_adm2():
    if os.path.exists(LOOKUP_ADM2):
        with open(LOOKUP_ADM2, encoding='utf-8') as f:
            return json.load(f)
    # Construir si no existe (delegamos a generador_heatmap)
    from generador_heatmap import _construir_lookup
    return _construir_lookup()


# ------------------------------------------------------------------
# Gráficos de tendencia (Plotly)
# ------------------------------------------------------------------

def _grafico_tendencia(nombre: str, puntos: list, cand_gob: str, cand_opo: str) -> str:
    """
    Genera un div Plotly con la tendencia de gobierno vs oposición.
    puntos: [{"hora": "HH:MM", "gob": float, "opo": float}, ...]
    Retorna HTML del div (sin <html>, sin plotly.js — se incluye una sola vez).
    """
    if not puntos:
        return f'<div style="padding:20px;color:#aaa;font-family:sans-serif;">Sin datos para {nombre}</div>'

    horas  = [p['hora'] for p in puntos]
    y_gob  = [p['gob']  for p in puntos]
    y_opo  = [p['opo']  for p in puntos]

    fig = go.Figure()

    # --- Sombra margen de error ---
    for y_vals, color_fill, _ in [
        (y_gob, 'rgba(183,28,28,0.12)',  'gob'),
        (y_opo, 'rgba(21,101,192,0.12)', 'opo'),
    ]:
        fig.add_trace(go.Scatter(
            x=horas + horas[::-1],
            y=[min(v + MARGEN_ERROR, 100) for v in y_vals] +
              [max(v - MARGEN_ERROR, 0)   for v in y_vals[::-1]],
            fill='toself', fillcolor=color_fill,
            line=dict(color='rgba(0,0,0,0)'),
            hoverinfo='skip', showlegend=False,
        ))

    # --- Líneas principales ---
    ultimo_gob = y_gob[-1] if y_gob else 0
    ultimo_opo = y_opo[-1] if y_opo else 0

    fig.add_trace(go.Scatter(
        x=horas, y=y_gob,
        mode='lines+markers',
        name=cand_gob,
        line=dict(color='#B71C1C', width=2.5, shape='spline', smoothing=1.2),
        marker=dict(size=5, color='#B71C1C'),
        hovertemplate='<b>%{x}</b><br>' + cand_gob + ': %{y:.1f}%<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=horas, y=y_opo,
        mode='lines+markers',
        name=cand_opo,
        line=dict(color='#1565C0', width=2.5, shape='spline', smoothing=1.2),
        marker=dict(size=5, color='#1565C0'),
        hovertemplate='<b>%{x}</b><br>' + cand_opo + ': %{y:.1f}%<extra></extra>',
    ))

    # --- Anotación del último valor ---
    if y_gob and y_opo:
        ventaja = ultimo_gob - ultimo_opo
        adelante = cand_gob if ventaja > 0 else cand_opo
        color_adel = '#B71C1C' if ventaja > 0 else '#1565C0'
        subtitulo = (f'Empate técnico ({abs(ventaja):.1f}%)'
                     if abs(ventaja) < UMBRAL_EMPATE
                     else f'{adelante} +{abs(ventaja):.1f}%')
        fig.add_annotation(
            xref='paper', yref='paper', x=1, y=1.05,
            text=f'<b style="color:{color_adel}">{subtitulo}</b>',
            showarrow=False, xanchor='right',
            font=dict(size=12), align='right',
        )

    fig.update_layout(
        title=dict(text=nombre, font=dict(size=14, color='#333'), x=0),
        margin=dict(l=40, r=20, t=50, b=40),
        height=320,
        paper_bgcolor='white',
        plot_bgcolor='#FAFAFA',
        xaxis=dict(
            title='Hora', tickangle=-30, tickfont=dict(size=10),
            gridcolor='#EEEEEE', showgrid=True,
        ),
        yaxis=dict(
            title='%', range=[0, 100], tickfont=dict(size=10),
            gridcolor='#EEEEEE', showgrid=True, zeroline=False,
        ),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02,
            xanchor='right', x=1, font=dict(size=11),
        ),
        hovermode='x unified',
    )

    # div_id = ID del contenedor Plotly (distinto del wrapper externo)
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       div_id=_id_chart(nombre))



# ------------------------------------------------------------------
# Mapa Folium
# ------------------------------------------------------------------

def _crear_mapa(datos_ventaja, nivel, candidatos):
    cand_gob = candidatos.get('gobierno',  'Gobierno')
    cand_opo = candidatos.get('oposicion', 'Oposicion')

    if nivel == 'municipio':
        geojson_path = GEOJSON_ADM2
        lookup = _lookup_adm2()
        datos_id = {}
        labels_id = {}
        for (est, mun), v in datos_ventaja.items():
            key = f'{_norm(est)}|{_norm(mun)}'
            sid = lookup.get(key)
            if sid:
                datos_id[sid] = v
                labels_id[sid] = f'{est} - {mun}'
        get_clave  = lambda feat: feat['properties']['shapeID']
        get_nombre = lambda feat: labels_id.get(feat['properties']['shapeID'], feat['properties']['shapeName'])
    else:
        geojson_path = GEOJSON_ADM1
        datos_id   = {_norm(k): v for k, v in datos_ventaja.items()}
        get_clave  = lambda feat: _norm(feat['properties']['shapeName'])
        get_nombre = lambda feat: feat['properties']['shapeName']

    with open(geojson_path, encoding='utf-8') as f:
        geojson = json.load(f)

    m = folium.Map(
        location=[7.8, -66.0], zoom_start=6,
        tiles=None, min_zoom=5, max_bounds=True,
    )

    colormap = LinearColormap(
        colors=['#1565C0', '#5E92C8', '#FFFFFF', '#E07070', '#B71C1C'],
        vmin=VMIN, vmax=VMAX,
    )

    for feat in geojson['features']:
        clave   = get_clave(feat)
        nombre  = get_nombre(feat)
        ventaja = datos_id.get(clave)
        feat['properties']['VENTAJA']    = ventaja if ventaja is not None else 0.0
        feat['properties']['TIENE_DATO'] = ventaja is not None
        feat['properties']['CHART_NAME'] = nombre
        feat['properties']['WRAP_ID']    = _id_wrap(nombre)

        if ventaja is None:
            tt = f'<b>{nombre}</b><br><i style="color:#aaa">Sin datos</i>'
        elif abs(ventaja) < UMBRAL_EMPATE:
            tt = f'<b>{nombre}</b><br>Empate tecnico ({ventaja:+.1f}%)'
        elif ventaja > 0:
            tt = (f'<b>{nombre}</b><br>'
                  f'<span style="color:#B71C1C">&#9650; {cand_gob} +{ventaja:.1f}%</span>')
        else:
            tt = (f'<b>{nombre}</b><br>'
                  f'<span style="color:#1565C0">&#9650; {cand_opo} +{abs(ventaja):.1f}%</span>')
        feat['properties']['TT'] = tt

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

    gj = folium.GeoJson(
        geojson,
        style_function=lambda feat: {
            'fillColor':   (colormap(feat['properties']['VENTAJA'])
                            if feat['properties']['TIENE_DATO'] else '#CCCCCC'),
            'color':       '#333',
            'weight':      0.5 if nivel == 'municipio' else 0.9,
            'fillOpacity': 0.82 if feat['properties']['TIENE_DATO'] else 0.3,
        },
        highlight_function=lambda feat: {
            'weight': 2.5,
            'color': '#FFD600',
            'fillOpacity': 0.95,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['TT'], aliases=[''],
            localize=True, sticky=True,
            style=('background:white;color:#111;font-family:sans-serif;'
                   'font-size:12px;padding:8px;border-radius:4px;'
                   'box-shadow:1px 1px 4px rgba(0,0,0,.2);'),
        ),
    )
    gj.add_to(m)
    colormap.add_to(m)

    return m, gj


# ------------------------------------------------------------------
# Ensamblado del HTML final
# ------------------------------------------------------------------

_LAYOUT_CSS = """
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<style>
  :root { --ep-top-offset: 0px; }
  html, body { margin:0; padding:0; height:100%; overflow:hidden; }
  #ep-outer { display:flex; height:calc(100vh - var(--ep-top-offset)); width:100vw; }
  #ep-map   { flex: 0 0 58%; height:calc(100vh - var(--ep-top-offset)); position:relative; overflow:hidden; }
  #ep-panel { flex: 0 0 42%; height:calc(100vh - var(--ep-top-offset)); min-height:0; display:flex; flex-direction:column;
              background:#F5F5F5; font-family:sans-serif; }
  #ep-panel-header {
      padding:10px 14px 8px;
      background:white;
      border-bottom:1px solid #DDD;
      display:flex; align-items:center; gap:10px;
  }
  #ep-panel-header h2 { margin:0; font-size:15px; color:#333; flex:1; }
  #ep-zone-name { font-size:12px; color:#888; }
  #ep-charts-scroll { flex:1; min-height:0; overflow-y:auto; padding:10px 10px 28px; }
  .ep-chart-block { background:white; border-radius:6px; padding:8px;
                    box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:10px; overflow:visible; }
  .ep-chart-block .plotly-graph-div { width:100% !important; max-width:100% !important; }
  .ep-hint { font-size:11px; color:#AAA; text-align:center;
             padding:6px 0; border-top:1px solid #EEE; margin-top:4px; }
  @media (max-width: 760px) {
    html, body { overflow:auto; }
    #ep-outer { flex-direction:column; height:auto; min-height:calc(100vh - var(--ep-top-offset)); }
    #ep-map { flex:0 0 48vh; height:48vh; width:100vw; }
    #ep-panel { flex:0 0 auto; width:100vw; height:auto; min-height:52vh; }
    #ep-charts-scroll { max-height:none; overflow:visible; padding-bottom:96px; }
  }
</style>
"""

def _ensamblar_html(map_html, charts_panel_html, click_js, titulo, cand_gob, cand_opo, gj_name):
    """
    Inyecta panel de gráficos y JS de interacción en el HTML de Folium.

    Folium pone sus scripts de Leaflet DESPUÉS de </body>, así que:
    - Plotly.js va en <head> (antes que cualquier Plotly.newPlot)
    - El panel de gráficos y el JS van antes de </body>
    - El click handler usa window.onload para garantizar que Leaflet ya cargó
    """
    # Plotly.js en el <head>, antes de que se ejecuten los scripts de los charts
    inject_head = _LAYOUT_CSS   # ya incluye el <script src="plotly...">

    # Panel + JS de layout/click van antes de </body>
    inject_body = f"""
{charts_panel_html}

<script>
// -------------------------------------------------------
// Layout: reorganizar en flexbox
// -------------------------------------------------------
(function buildLayout() {{
  var mapEl = document.querySelector('[id^="map_"]');
  if (!mapEl) {{ setTimeout(buildLayout, 50); return; }}

  var outer   = document.createElement('div');
  outer.id    = 'ep-outer';
  var mapWrap = document.createElement('div');
  mapWrap.id  = 'ep-map';

  mapEl.style.width  = '100%';
  mapEl.style.height = '100%';
  mapEl.parentNode.insertBefore(outer, mapEl);
  mapWrap.appendChild(mapEl);
  outer.appendChild(mapWrap);

  var panel = document.getElementById('ep-panel');
  if (panel) outer.appendChild(panel);
}})();

// -------------------------------------------------------
// Mostrar gráfico al hacer click
// -------------------------------------------------------
function epShowChart(nombre, wrapId) {{
  document.querySelectorAll('.ep-chart-block').forEach(function(d) {{
    d.style.display = 'none';
  }});
  var el = document.getElementById(wrapId);
  if (!el) el = document.getElementById('{_id_wrap("VENEZUELA")}');
  if (el)  el.style.display = 'block';
  if (window.Plotly && el) {{
    el.querySelectorAll('.plotly-graph-div').forEach(function(g) {{
      try {{ Plotly.Plots.resize(g); }} catch(e) {{}}
    }});
  }}
  var zn = document.getElementById('ep-zone-name');
  if (zn) zn.textContent = nombre;
}}

// -------------------------------------------------------
// Click en GeoJSON → enganchado con window.onload
// para garantizar que Leaflet ya terminó de inicializarse
// -------------------------------------------------------
// -------------------------------------------------------
// Actualizacion en vivo por SSE. No toca #ai-analyst.
// -------------------------------------------------------
function epNorm(s) {{
  return String(s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')
    .trim().toUpperCase();
}}
function epChartId(nombre) {{
  return 'pchart-' + epNorm(nombre).replace(/\\s+/g, '_').replace(/\\./g, '');
}}
function epColor(ventaja) {{
  if (ventaja === null || ventaja === undefined || isNaN(Number(ventaja))) return '#CCCCCC';
  var v = Math.max(-30, Math.min(30, Number(ventaja)));
  if (v < -3) return '#1565C0';
  if (v < 0) return '#5E92C8';
  if (v <= 3) return '#FFFFFF';
  if (v <= 15) return '#E07070';
  return '#B71C1C';
}}
window.updateHeatmap = function(geo) {{
  geo = geo || {{}};
  try {{
    {gj_name}.eachLayer(function(layer) {{
      if (!layer.feature || !layer.feature.properties) return;
      var props = layer.feature.properties;
      var nombre = props.CHART_NAME || props.shapeName || '';
      var key = epNorm(nombre);
      var ventaja = geo[nombre];
      if (ventaja === undefined) ventaja = geo[key];
      if (ventaja === undefined) ventaja = geo[nombre.toUpperCase()];
      var tieneDato = ventaja !== undefined && ventaja !== null;
      props.VENTAJA = tieneDato ? Number(ventaja) : 0;
      props.TIENE_DATO = tieneDato;
      if (layer.setStyle) {{
        layer.setStyle({{
          fillColor: tieneDato ? epColor(ventaja) : '#CCCCCC',
          fillOpacity: tieneDato ? 0.82 : 0.3
        }});
      }}
    }});
  }} catch(err) {{
    console.warn('[exit-poll] updateHeatmap:', err);
  }}
}};
window.updateCharts = function(series) {{
  series = series || {{}};
  Object.keys(series).forEach(function(nombre) {{
    var puntos = series[nombre] || [];
    var chart = document.getElementById(epChartId(nombre));
    if (!chart || !window.Plotly || !puntos.length) return;
    var horas = puntos.map(function(p) {{ return p.hora; }});
    var gob = puntos.map(function(p) {{ return p.gob; }});
    var opo = puntos.map(function(p) {{ return p.opo; }});
    try {{
      Plotly.restyle(chart, {{x: [horas], y: [gob]}}, [2]);
      Plotly.restyle(chart, {{x: [horas], y: [opo]}}, [3]);
    }} catch(err) {{
      console.warn('[exit-poll] updateCharts:', err);
    }}
  }});
}};
if (window.EventSource) {{
  var epDashboardStream = new EventSource('/stream/dashboard');
  epDashboardStream.onmessage = function(event) {{
    try {{
      var data = JSON.parse(event.data || '{{}}');
      updateHeatmap(data.geo);
      updateCharts(data.series);
      var liveTotal = document.getElementById('ep-live-total');
      if (liveTotal && data.total_votos !== undefined) {{
        liveTotal.textContent = Number(data.total_votos || 0).toLocaleString() + ' votos procesados';
      }}
    }} catch(err) {{
      console.warn('[exit-poll] SSE:', err);
    }}
  }};
}}

{click_js}
</script>
"""

    html = map_html.replace('</head>', inject_head + '</head>', 1)
    html = html.replace('</body>', inject_body + '</body>', 1)
    return html


# ------------------------------------------------------------------
# Función principal
# ------------------------------------------------------------------

def generar_dashboard(
    datos_ventaja: dict,
    datos_tendencia: dict,
    nivel: str = 'estado',
    ruta_salida: str = 'dashboard.html',
    titulo: str = 'Exit Poll Venezuela',
    candidatos: dict = None,
) -> bool:
    cand = candidatos or {}
    cand_gob = cand.get('gobierno',  'Gobierno')
    cand_opo = cand.get('oposicion', 'Oposicion')

    print(f'[dashboard] Generando mapa ({nivel})...')
    m, gj = _crear_mapa(datos_ventaja, nivel, cand)
    map_name = m.get_name()
    gj_name  = gj.get_name()

    # --- Gráficos de tendencia ---
    print(f'[dashboard] Generando graficos ({len(datos_tendencia)} entidades)...')
    bloques_charts = []
    primera = True
    for nombre, puntos in datos_tendencia.items():
        chart_div  = _grafico_tendencia(nombre, puntos, cand_gob, cand_opo)
        estilo     = '' if primera else ' style="display:none"'
        primera    = False
        # _id_wrap  = wrapper externo (show/hide)
        # _id_chart = div interno de Plotly (IDs separados para evitar duplicados)
        bloques_charts.append(
            f'<div id="{_id_wrap(nombre)}" class="ep-chart-block"{estilo}>'
            f'{chart_div}</div>'
        )

    panel_html = f"""
<div id="ep-panel">
  <div id="ep-panel-header">
    <h2>{titulo}</h2>
    <span id="ep-zone-name">VENEZUELA</span>
  </div>
  <div id="ep-charts-scroll">
    {''.join(bloques_charts)}
    <div class="ep-hint">Haz click en el mapa para ver la tendencia de cada zona</div>
  </div>
</div>
"""

    # --- Click handler JS ---
    # normId() debe producir IDs de tipo wrap-* (igual que _id_wrap en Python)
    click_js = f"""
window.addEventListener('load', function() {{
  function normId(s) {{
    return 'wrap-' + s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'')
                       .toUpperCase().replace(/\\s+/g,'_').replace(/[^A-Z0-9_]/g,'');
  }}
  // Invalidar tamaño del mapa ahora que el layout está reorganizado
  setTimeout(function() {{
    for (var k in window) {{
      try {{
        if (window[k] && typeof window[k].invalidateSize === 'function') {{
          window[k].invalidateSize();
        }}
      }} catch(e) {{}}
    }}
  }}, 200);
  try {{
    {gj_name}.eachLayer(function(layer) {{
      layer.on('click', function(e) {{
        var nombre = e.target.feature.properties.CHART_NAME || e.target.feature.properties.shapeName || '';
        var id     = e.target.feature.properties.WRAP_ID || normId(nombre);
        epShowChart(nombre, id);
      }});
    }});
  }} catch(err) {{
    console.warn('[exit-poll] click handler:', err);
  }}
}});
"""

    # --- Guardar mapa a string ---
    tmp = tempfile.mktemp(suffix='.html')
    m.save(tmp)
    with open(tmp, encoding='utf-8') as f:
        map_html = f.read()
    os.unlink(tmp)

    # --- Ensamblar ---
    final_html = _ensamblar_html(map_html, panel_html, click_js, titulo, cand_gob, cand_opo, gj_name)

    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(final_html)

    print(f'[dashboard] Guardado -> {ruta_salida}')
    return True


# ------------------------------------------------------------------
# Demo
# ------------------------------------------------------------------

def _demo_tendencia(nombres: list, n_puntos: int = 15) -> dict:
    """Genera datos de tendencia simulados."""
    import datetime
    start = datetime.datetime(2025, 1, 1, 7, 0)
    datos = {}
    for nombre in nombres:
        base_gob = random.uniform(35, 60)
        puntos = []
        gob, opo = base_gob, 100 - base_gob
        for i in range(n_puntos):
            hora = (start + datetime.timedelta(minutes=20 * i)).strftime('%H:%M')
            gob = max(5, min(95, gob + random.uniform(-2, 2)))
            opo = max(5, min(95, opo + random.uniform(-2, 2)))
            # Normalizar a 100
            total = gob + opo
            puntos.append({'hora': hora, 'gob': round(gob/total*100, 1),
                           'opo': round(opo/total*100, 1)})
            gob, opo = puntos[-1]['gob'], puntos[-1]['opo']
        datos[nombre] = puntos
    return datos


def _demo_estado():
    nombres = [
        'Amazonas', 'Anzoategui', 'Apure', 'Aragua', 'Barinas', 'Bolivar',
        'Carabobo', 'Cojedes', 'Delta Amacuro', 'Distrito Capital', 'Falcon',
        'Guarico', 'Lara', 'Merida', 'Miranda', 'Monagas', 'Nueva Esparta',
        'Portuguesa', 'Sucre', 'Tachira', 'Trujillo', 'La Guaira', 'Yaracuy', 'Zulia',
    ]
    ventajas = {n: round(random.uniform(-25, 25), 1) for n in nombres}
    tendencia_names = ['VENEZUELA'] + [n.upper() for n in nombres]
    tendencias = _demo_tendencia(tendencia_names)
    return ventajas, tendencias


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Demo del dashboard electoral')
    parser.add_argument('--nivel',  choices=['estado', 'municipio'], default='estado')
    parser.add_argument('--salida', default=None)
    args = parser.parse_args()

    salida = args.salida or f'demo_dashboard_{args.nivel}.html'
    candidatos = {'gobierno': 'Candidato A', 'oposicion': 'Candidato B'}
    titulo     = 'Exit Poll — Demo'

    if args.nivel == 'municipio':
        from generador_heatmap import _lookup_adm2
        lookup = _lookup_adm2()
        ventajas = {}
        nombres_muni = []
        for key in list(lookup.keys())[:120]:   # subset para demo
            est, mun = key.split('|', 1)
            ventajas[(est, mun)] = round(random.uniform(-25, 25), 1)
            nombres_muni.append(mun)
        tendencias = _demo_tendencia(['VENEZUELA'] + nombres_muni[:20])
    else:
        ventajas, tendencias = _demo_estado()

    generar_dashboard(ventajas, tendencias, nivel=args.nivel,
                      ruta_salida=salida, titulo=titulo, candidatos=candidatos)
