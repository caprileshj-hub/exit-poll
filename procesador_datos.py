# -*- coding: utf-8 -*-
import json
import unicodedata

def normalizar_texto(texto):
    """Normaliza texto a mayúsculas sin tildes para coincidir con las claves del JSON."""
    if not isinstance(texto, str):
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').upper().strip()

def cargar_pesos(ruta="pesos.json"):
    """Carga la tabla maestra de pesos."""
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error cargando {ruta}: {e}")
        return {}

def procesar_encuesta(datos_entrada, tabla_pesos):
    """
    Procesa los datos crudos de encuestas y calcula la ventaja ponderada por Estado.
    
    Args:
        datos_entrada (list): Lista de diccionarios con votos crudos.
                              Ej: [{'estado': 'ZULIA', 'municipio': 'MARACAIBO', 'parroquia': '...', 'rojo': 50, 'azul': 40}, ...]
        tabla_pesos (dict): Estructura cargada de pesos.json
        
    Returns:
        dict: Diccionario con la ventaja porcentual por estado.
              Ej: {'ZULIA': 5.2, 'MIRANDA': -3.1} (Positivo=Rojo, Negativo=Azul)
    """
    # 1. Agrupar datos crudos en un árbol para acceso rápido
    # Estructura: data_tree[estado][municipio][parroquia] = {rojo: X, azul: Y, total: Z}
    data_tree = {}
    
    for entrada in datos_entrada:
        est = normalizar_texto(entrada.get('estado'))
        mun = normalizar_texto(entrada.get('municipio'))
        par = normalizar_texto(entrada.get('parroquia'))
        
        if est not in data_tree: data_tree[est] = {}
        if mun not in data_tree[est]: data_tree[est][mun] = {}
        if par not in data_tree[est][mun]: data_tree[est][mun][par] = {'rojo': 0, 'azul': 0, 'total': 0}
        
        r = entrada.get('rojo', 0)
        a = entrada.get('azul', 0)
        data_tree[est][mun][par]['rojo'] += r
        data_tree[est][mun][par]['azul'] += a
        data_tree[est][mun][par]['total'] += (r + a)

    # 2. Calcular resultados ponderados
    resultados_estados = {}
    
    # Acumuladores para el Total Nacional (VENEZUELA)
    nacional_rojo_score = 0.0
    nacional_azul_score = 0.0
    nacional_peso_total = 0.0
    
    for est, municipios_data in data_tree.items():
        peso_estado_node = tabla_pesos.get(est)
        if not peso_estado_node:
            continue # Estado no existe en tabla de pesos
            
        score_rojo_est = 0.0
        score_azul_est = 0.0
        peso_acumulado_est = 0.0
        
        for mun, parroquias_data in municipios_data.items():
            peso_muni_node = peso_estado_node.get(mun)
            if not peso_muni_node:
                continue # Municipio no encontrado en pesos
                
            peso_municipio_global = peso_muni_node.get('municipio', 0.0)
            pesos_parroquias_dict = peso_muni_node.get('parroquias', {})
            
            # LÓGICA DE NEGOCIO:
            # Si hay pesos definidos a nivel de parroquia (ej. La Guaira), usamos esos.
            # Si no, usamos el peso del municipio (ej. Anzoátegui).
            # Si el peso es 0.0, se ignora (no es parte de la muestra estadística actual).
            
            usa_peso_parroquial = any(p > 0 for p in pesos_parroquias_dict.values())
            
            if usa_peso_parroquial:
                # Estrategia: Suma ponderada de parroquias
                for par, votos in parroquias_data.items():
                    peso_par = pesos_parroquias_dict.get(par, 0.0)
                    if peso_par > 0 and votos['total'] > 0:
                        pct_rojo = votos['rojo'] / votos['total']
                        pct_azul = votos['azul'] / votos['total']
                        
                        score_rojo_est += pct_rojo * peso_par
                        score_azul_est += pct_azul * peso_par
                        peso_acumulado_est += peso_par
            
            elif peso_municipio_global > 0:
                # Estrategia: Suma simple del municipio * Peso Municipio
                total_mun = sum(v['total'] for v in parroquias_data.values())
                rojo_mun = sum(v['rojo'] for v in parroquias_data.values())
                azul_mun = sum(v['azul'] for v in parroquias_data.values())
                
                if total_mun > 0:
                    pct_rojo = rojo_mun / total_mun
                    pct_azul = azul_mun / total_mun
                    
                    score_rojo_est += pct_rojo * peso_municipio_global
                    score_azul_est += pct_azul * peso_municipio_global
                    peso_acumulado_est += peso_municipio_global

        # Sumar al acumulado nacional
        nacional_rojo_score += score_rojo_est
        nacional_azul_score += score_azul_est
        nacional_peso_total += peso_acumulado_est

        # 3. Normalización final por Estado
        if peso_acumulado_est > 0:
            # Proyectamos al 100% basado en la muestra recogida
            final_rojo = (score_rojo_est / peso_acumulado_est) * 100
            final_azul = (score_azul_est / peso_acumulado_est) * 100
            resultados_estados[est] = {
                'rojo': final_rojo,
                'azul': final_azul,
                'ventaja': final_rojo - final_azul
            }
        else:
            resultados_estados[est] = {'rojo': 0.0, 'azul': 0.0, 'ventaja': 0.0}
            
    # 4. Calcular Resultado Nacional (VENEZUELA)
    if nacional_peso_total > 0:
        nac_rojo = (nacional_rojo_score / nacional_peso_total) * 100
        nac_azul = (nacional_azul_score / nacional_peso_total) * 100
        resultados_estados['VENEZUELA'] = {
            'rojo': nac_rojo,
            'azul': nac_azul,
            'ventaja': nac_rojo - nac_azul
        }
    elif resultados_estados: # Si hay estados procesados pero peso 0 (caso borde)
        resultados_estados['VENEZUELA'] = {'rojo': 0.0, 'azul': 0.0, 'ventaja': 0.0}
            
    return resultados_estados

def procesar_tendencias(datos_entrada, tabla_pesos):
    """
    Calcula la evolución de los resultados acumulados por corte de tiempo.
    Simula el comportamiento de 'Cortes' cada 30 min.
    
    Args:
        datos_entrada (list): Lista de votos con campo 'hora' (HH:MM).
        tabla_pesos (dict): Tabla maestra de pesos.
        
    Returns:
        dict: Diccionario { "HH:MM": { "ESTADO": ventaja, ... } } ordenado cronológicamente.
    """
    # 1. Identificar cortes de tiempo únicos y ordenarlos
    cortes = sorted(list(set(d.get('hora', '00:00') for d in datos_entrada)))
    
    tendencias = {}
    datos_acumulados = []
    
    for corte in cortes:
        # Obtener datos de este bloque de tiempo específico
        bloque = [d for d in datos_entrada if d.get('hora') == corte]
        
        # En un Exit Poll, el resultado de las 8:00 incluye lo de las 7:30 (Acumulado)
        datos_acumulados.extend(bloque)
        
        # Procesar la "foto" acumulada hasta este momento
        resultado_corte = procesar_encuesta(datos_acumulados, tabla_pesos)
        tendencias[corte] = resultado_corte
        
    return tendencias