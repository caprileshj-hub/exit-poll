# -*- coding: utf-8 -*-
import plotly.graph_objects as go
import os

def generar_graficos_interactivos(tendencias, output_dir="graficos"):
    """
    Genera gráficos HTML interactivos para cada entidad (Estados y Nacional).
    Args:
        tendencias (dict): { "HH:MM": { "ESTADO": ventaja, ... } }
        output_dir (str): Carpeta donde se guardarán los HTML.
    """
    if not tendencias:
        print("⚠️ No hay datos de tendencias para graficar.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    horas = sorted(tendencias.keys())
    
    # 1. Organizar datos por entidad (Estado/País)
    # entidad -> { 'x': [horas], 'y': [ventajas] }
    datos_por_entidad = {}
    
    # Obtener lista completa de entidades que aparecen en algún momento
    todas_entidades = set()
    for h in horas:
        todas_entidades.update(tendencias[h].keys())
    
    for entidad in todas_entidades:
        x_vals = []
        y_rojo = []
        y_azul = []
        for h in horas:
            if entidad in tendencias[h]:
                data = tendencias[h][entidad]
                x_vals.append(h)
                y_rojo.append(data.get('rojo', 0.0))
                y_azul.append(data.get('azul', 0.0))
        datos_por_entidad[entidad] = {'x': x_vals, 'rojo': y_rojo, 'azul': y_azul}

    # 2. Generar un gráfico por cada entidad
    count = 0
    MARGEN_ERROR = 2.5  # Margen de error visual fijo (2.5%)

    for entidad, data in datos_por_entidad.items():
        fig = go.Figure()
        
        # --- Oficialismo (Rojo) ---
        # Sombra Margen de Error
        fig.add_trace(go.Scatter(
            x=data['x'] + data['x'][::-1],
            y=[min(y + MARGEN_ERROR, 100) for y in data['rojo']] + [max(y - MARGEN_ERROR, 0) for y in data['rojo']][::-1],
            fill='toself',
            fillcolor='rgba(255, 0, 0, 0.15)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=False
        ))
        # Línea Principal
        fig.add_trace(go.Scatter(
            x=data['x'], y=data['rojo'],
            mode='lines+markers',
            name='Oficialismo',
            line=dict(color='red', width=3, shape='spline', smoothing=1.3),
            hovertemplate='<b>%{x}</b><br>Oficialismo: %{y:.2f}%<extra></extra>'
        ))

        # --- Oposición (Azul) ---
        # Sombra Margen de Error
        fig.add_trace(go.Scatter(
            x=data['x'] + data['x'][::-1],
            y=[min(y + MARGEN_ERROR, 100) for y in data['azul']] + [max(y - MARGEN_ERROR, 0) for y in data['azul']][::-1],
            fill='toself',
            fillcolor='rgba(0, 0, 255, 0.15)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=False
        ))
        # Línea Principal
        fig.add_trace(go.Scatter(
            x=data['x'], y=data['azul'],
            mode='lines+markers',
            name='Oposición',
            line=dict(color='blue', width=3, shape='spline', smoothing=1.3),
            hovertemplate='<b>%{x}</b><br>Oposición: %{y:.2f}%<extra></extra>'
        ))

        fig.update_layout(
            title=f"Tendencia Electoral: {entidad}",
            xaxis_title="Hora del Reporte",
            yaxis_title="Porcentaje de Votos (%)",
            yaxis=dict(
                zeroline=True, 
                zerolinewidth=2, 
                zerolinecolor='black',
                range=[0, 100] # Fijar escala 0-100 para consistencia visual
            ),
            hovermode="x unified"
        )

        # Guardar archivo HTML
        filename = f"{entidad.replace(' ', '_')}.html"
        filepath = os.path.join(output_dir, filename)
        fig.write_html(filepath)
        count += 1
    
    print(f"✅ Se generaron {count} gráficos interactivos en la carpeta '{output_dir}/'.")