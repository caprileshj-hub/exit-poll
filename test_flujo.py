# -*- coding: utf-8 -*-
import procesador_datos
import generador_mapa
import graficador_tendencias
import json
from datetime import datetime, timedelta
import random

def test_core():
    print("🔬 INICIANDO AUDITORÍA DEL NÚCLEO (PYTHON CORE)")
    print("=============================================")

    # 1. Cargar Pesos
    print("\n1. Cargando Matriz de Pesos (pesos.json)...")
    pesos = procesador_datos.cargar_pesos()
    if not pesos:
        print("❌ Error CRÍTICO: No se pudo cargar la tabla de pesos.")
        return

    # 2. Generar Datos de Prueba con TIEMPO (Simulando transmisión cada 20 min hasta las 11am)
    print("\n2. Generando simulación temporal (06:00 - 11:00, cada 20 min)...")
    datos_encuesta = []
    
    start_time = datetime.strptime("07:00", "%H:%M")
    end_time = datetime.strptime("11:00", "%H:%M")
    delta = timedelta(minutes=20)
    
    current_time = start_time
    while current_time <= end_time:
        hora_str = current_time.strftime("%H:%M")
        
        # Generar datos aleatorios para cada estado disponible en pesos
        for estado, data_estado in pesos.items():
            if not isinstance(data_estado, dict): continue
            
            # Seleccionar un municipio aleatorio del estado para simular entrada de datos
            municipios_keys = list(data_estado.keys())
            if not municipios_keys: continue
            mun = random.choice(municipios_keys)
            
            # Intentar obtener una parroquia válida si existe en los pesos
            node_mun = data_estado[mun]
            parroquias_dict = node_mun.get('parroquias', {})
            parroquia_elegida = random.choice(list(parroquias_dict.keys())) if parroquias_dict else "CAPITAL"
            
            datos_encuesta.append({
                'estado': estado,
                'municipio': mun,
                'parroquia': parroquia_elegida,
                'rojo': random.randint(50, 500), # Votos aleatorios
                'azul': random.randint(50, 500),
                'hora': hora_str
            })
            
        current_time += delta

    print(f"   -> Se inyectaron {len(datos_encuesta)} encuestas distribuidas en el tiempo.")

    # 3. Ejecutar el Procesador de Tendencias
    print("\n3. Calculando TENDENCIAS (Corte a Corte)...")
    tendencias = procesador_datos.procesar_tendencias(datos_encuesta, pesos)
    
    print("\n📊 EVOLUCIÓN DE RESULTADOS:")
    print("-" * 30)
    for hora, resultados in tendencias.items():
        for estado, data in resultados.items():
            ventaja = data['ventaja']
            rojo = data['rojo']
            azul = data['azul']
            if ventaja != 0:
                barra = "🟦" * int(abs(ventaja)/2) if ventaja < 0 else "🟥" * int(abs(ventaja)/2)
                print(f"   ⏰ {hora} | {estado:10}: R {rojo:5.1f}% vs A {azul:5.1f}% | Ventaja: {ventaja:6.2f}% {barra}")
    print("-" * 30)

    # 4. Generar Mapa Visual
    print("\n4. Generando mapa con el ÚLTIMO CORTE (mapa_test.html)...")
    ultimo_corte = list(tendencias.keys())[-1]
    
    # Adaptador: El mapa espera {Estado: VentajaFloat}, convertimos el dict complejo
    datos_para_mapa = {k: v['ventaja'] for k, v in tendencias[ultimo_corte].items()}
    generador_mapa.crear_mapa_resultados(datos_para_mapa, "mapa_test.html")
    
    # 5. Generar Gráficos Interactivos
    print("\n5. Generando gráficos interactivos (HTML)...")
    graficador_tendencias.generar_graficos_interactivos(tendencias, "graficos_test")
    print("✅ Prueba finalizada. Revisa 'mapa_test.html' y la carpeta 'graficos_test/'.")

if __name__ == "__main__":
    test_core()