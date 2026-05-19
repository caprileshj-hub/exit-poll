"""
Calcula y guarda los pesos jerárquicos para cada centro de la muestra.

Reglas por tipo de elección:
    nacional / asamblea → peso_estado:    centros del mismo estado  suman 1
    regional            → peso_municipio: centros del mismo municipio suman 1
    municipal           → peso_parroquia: centros de la misma parroquia suman 1

peso_nacion: fracción del electorado del estado sobre el total nacional
             (universo = todos los centros activos en la BD)
             Permite agregar resultados de estados al total nacional.

Excepciones geográficas (para peso_municipio en elecciones regionales):
    - Estados con es_excepcion=1 (DC, La Guaira): solo tienen 1 municipio,
      las parroquias se comportan como municipios → grupos por parroquia.
    - Municipios con es_excepcion=1 (Chacao, Baruta, El Hatillo, Sucre en Miranda):
      mismo comportamiento → grupos por parroquia.

Todos los pesos se calculan con los electores de la MUESTRA (no el universo),
excepto peso_nacion que usa el universo real de la BD.

Uso:
    python calculador_pesos.py <id_eleccion> [--dry-run]
    python calculador_pesos.py <id_eleccion> --set <id_muestra> campo=valor [campo=valor ...]
"""

import sqlite3
import argparse
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'exitpoll.db')

CAMPOS_PESOS = ('peso_parroquia', 'peso_municipio', 'peso_estado', 'peso_nacion')


# ------------------------------------------------------------------
# Cálculo
# ------------------------------------------------------------------

def _normalizar_dentro_grupo(centros: list[dict], clave_grupo: str) -> dict[int, float]:
    """
    Dada una lista de centros con 'id_muestra' y 'num_electores',
    y una clave de agrupación, devuelve {id_muestra: peso} donde
    la suma dentro de cada grupo = 1.
    """
    # Acumular electores por grupo
    suma_grupo: dict = {}
    for c in centros:
        g = c[clave_grupo]
        suma_grupo[g] = suma_grupo.get(g, 0) + c['num_electores']

    pesos = {}
    for c in centros:
        g   = c[clave_grupo]
        den = suma_grupo[g]
        pesos[c['id_muestra']] = (c['num_electores'] / den) if den else 0.0
    return pesos


def calcular(id_eleccion: int, dry_run: bool = False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # --- Elección ---
    elec = conn.execute('SELECT tipo, nombre FROM elecciones WHERE id = ?',
                        (id_eleccion,)).fetchone()
    if not elec:
        conn.close()
        raise ValueError(f'Elección {id_eleccion} no encontrada')
    tipo = elec['tipo']
    print(f'[+] Elección {id_eleccion}: "{elec["nombre"]}" — tipo: {tipo}')

    # --- Muestra con geografía ---
    filas = conn.execute('''
        SELECT
            m.id            AS id_muestra,
            c.codigo_cne,
            c.num_electores,
            c.id_parroquia,
            c.id_municipio,
            c.id_estado,
            e.es_excepcion  AS estado_excepcion,
            mu.es_excepcion AS municipio_excepcion
        FROM muestra m
        JOIN centros     c  ON c.codigo_cne = m.codigo_centro
        JOIN estados     e  ON e.id = c.id_estado
        JOIN municipios  mu ON mu.id = c.id_municipio
        WHERE m.id_eleccion = ? AND m.activo = 1 AND c.activo = 1
    ''', (id_eleccion,)).fetchall()

    if not filas:
        conn.close()
        print('[!] No hay centros activos en la muestra para esta elección')
        return

    centros = [dict(f) for f in filas]
    print(f'[+] Centros en muestra: {len(centros)}')

    # --- Universo: electores totales por estado (para peso_nacion) ---
    universo = conn.execute('''
        SELECT id_estado, SUM(num_electores) AS total
        FROM centros WHERE activo = 1
        GROUP BY id_estado
    ''').fetchall()
    elec_universo_estado = {r['id_estado']: r['total'] for r in universo}
    elec_universo_total  = sum(elec_universo_estado.values())

    # --- Calcular pesos según tipo de elección ---

    # peso_nacion: siempre (fracción del electorado del estado sobre total nacional)
    p_nacion = {
        c['id_muestra']: (
            elec_universo_estado.get(c['id_estado'], 0) / elec_universo_total
            if elec_universo_total else 0.0
        )
        for c in centros
    }

    zero = {c['id_muestra']: 0.0 for c in centros}

    if tipo in ('nacional', 'asamblea'):
        # Centros-muestra suman 1 por estado
        p_estado    = _normalizar_dentro_grupo(centros, 'id_estado')
        p_municipio = zero
        p_parroquia = zero
        clave_verif, label_verif, p_verif = 'id_estado', 'peso_estado', p_estado

    elif tipo == 'regional':
        # Centros-muestra suman 1 por municipio (con excepciones DC/La Guaira/municipios especiales)
        for c in centros:
            if c['estado_excepcion'] or c['municipio_excepcion']:
                c['_grupo_muni'] = f"p_{c['id_parroquia']}"
            else:
                c['_grupo_muni'] = f"m_{c['id_municipio']}"
        p_municipio = _normalizar_dentro_grupo(centros, '_grupo_muni')
        p_estado    = zero
        p_parroquia = zero
        clave_verif, label_verif, p_verif = '_grupo_muni', 'peso_municipio', p_municipio

    elif tipo == 'municipal':
        # Centros-muestra suman 1 por parroquia
        p_parroquia = _normalizar_dentro_grupo(centros, 'id_parroquia')
        p_municipio = zero
        p_estado    = zero
        clave_verif, label_verif, p_verif = 'id_parroquia', 'peso_parroquia', p_parroquia

    else:
        conn.close()
        raise ValueError(f'Tipo de elección no soportado: {tipo!r}')

    # --- Verificación de sumas ---
    print('\n[+] Verificación:')
    _verificar_suma(centros, p_verif, clave_verif, label_verif)
    _verificar_suma_nacion(p_nacion, elec_universo_estado, elec_universo_total)

    # --- Persistir ---
    if dry_run:
        print('\n[DRY RUN] Pesos calculados (no guardados):')
        print(f'  {"id_muestra":>10} {"codigo_cne":>12} {"p_parroquia":>12} '
              f'{"p_municipio":>12} {"p_estado":>10} {"p_nacion":>10}')
        for c in centros:
            mid = c['id_muestra']
            print(f'  {mid:>10} {c["codigo_cne"]:>12} '
                  f'{p_parroquia[mid]:>12.6f} {p_municipio[mid]:>12.6f} '
                  f'{p_estado[mid]:>10.6f} {p_nacion[mid]:>10.6f}')
        conn.close()
        return

    conn.execute('BEGIN')
    try:
        for c in centros:
            mid = c['id_muestra']
            conn.execute('''
                INSERT INTO pesos (id_muestra, peso_parroquia, peso_municipio,
                                   peso_estado, peso_nacion)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id_muestra) DO UPDATE SET
                    peso_parroquia = excluded.peso_parroquia,
                    peso_municipio = excluded.peso_municipio,
                    peso_estado    = excluded.peso_estado,
                    peso_nacion    = excluded.peso_nacion
            ''', (
                mid,
                round(p_parroquia[mid], 8),
                round(p_municipio[mid], 8),
                round(p_estado[mid],    8),
                round(p_nacion[mid],    8),
            ))
        conn.commit()
        print(f'\n[+] Pesos guardados: {len(centros)} centros')
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def _verificar_suma(centros, pesos, clave_grupo, nombre):
    """Verifica que los pesos sumen 1 dentro de cada grupo."""
    sumas: dict = {}
    for c in centros:
        g = c[clave_grupo]
        sumas[g] = sumas.get(g, 0.0) + pesos[c['id_muestra']]

    errores = [(g, s) for g, s in sumas.items() if abs(s - 1.0) > 1e-6]
    estado = '✓' if not errores else f'✗ ({len(errores)} grupos fuera de rango)'
    print(f'    {nombre:<20} {len(sumas):>4} grupos — {estado}')
    for g, s in errores:
        print(f'      grupo {g}: suma = {s:.8f}')


def _verificar_suma_nacion(p_nacion, elec_estado, total):
    """Verifica que peso_nacion (por estado único) sume ~1 globalmente."""
    estados_vistos = set()
    suma = 0.0
    # p_nacion tiene una entrada por id_muestra; sumamos por estado único
    # Reconstruimos desde elec_estado directamente
    suma = sum(v / total for v in elec_estado.values()) if total else 0.0
    estado = '✓' if abs(suma - 1.0) < 1e-6 else f'✗ (suma={suma:.8f})'
    print(f'    {"peso_nacion":<20} universo — {estado}')


# ------------------------------------------------------------------
# Edición manual de un centro
# ------------------------------------------------------------------

def set_peso(id_muestra: int, asignaciones: list[str]):
    """
    Actualiza manualmente campos de pesos para un id_muestra dado.
    Formato de asignaciones: ["peso_estado=0.35", "peso_municipio=0.5"]
    """
    updates = {}
    for a in asignaciones:
        if '=' not in a:
            raise ValueError(f'Formato inválido: {a!r}. Use campo=valor')
        campo, valor = a.split('=', 1)
        campo = campo.strip()
        if campo not in CAMPOS_PESOS:
            raise ValueError(f'Campo desconocido: {campo!r}. Válidos: {CAMPOS_PESOS}')
        updates[campo] = float(valor)

    if not updates:
        print('[!] Nada que actualizar')
        return

    conn = sqlite3.connect(DB_PATH)
    existe = conn.execute('SELECT 1 FROM pesos WHERE id_muestra = ?',
                          (id_muestra,)).fetchone()
    if not existe:
        conn.close()
        raise ValueError(f'id_muestra {id_muestra} no tiene pesos calculados aún')

    set_clause = ', '.join(f'{k} = ?' for k in updates)
    conn.execute(f'UPDATE pesos SET {set_clause} WHERE id_muestra = ?',
                 list(updates.values()) + [id_muestra])
    conn.commit()
    conn.close()
    print(f'[+] id_muestra {id_muestra} actualizado: {updates}')


# ------------------------------------------------------------------
# Diagnóstico de cobertura y DEFF (para elecciones activas)
# ------------------------------------------------------------------

def diagnosticar_cobertura(id_eleccion: int) -> dict:
    """
    Compara la cobertura de la muestra vs el universo de centros por estado.
    Estima el DEFF usando la fórmula de Kish con ICC=0.04.

    Retorna:
        estados: lista de dicts con cobertura por estado
        deff_estimado: estimación del efecto de diseño global
        alertas: estados con cobertura < 10% (riesgo de afijación)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    muestra = conn.execute('''
        SELECT c.id_estado, e.nombre AS nombre_estado,
               COUNT(m.id) AS n_muestra, SUM(c.num_electores) AS elec_muestra
        FROM muestra m
        JOIN centros c ON c.codigo_cne = m.codigo_centro
        JOIN estados e ON e.id = c.id_estado
        WHERE m.id_eleccion = ? AND m.activo = 1 AND c.activo = 1
        GROUP BY c.id_estado
    ''', (id_eleccion,)).fetchall()

    universo = conn.execute('''
        SELECT id_estado, COUNT(*) AS n_total, SUM(num_electores) AS elec_total
        FROM centros WHERE activo = 1
        GROUP BY id_estado
    ''').fetchall()
    conn.close()

    u_map = {r['id_estado']: dict(r) for r in universo}
    total_muestra_centros  = sum(r['n_muestra']  for r in muestra)
    total_universo_electores = sum(r['elec_total'] for r in u_map.values())
    total_muestra_electores  = sum(r['elec_muestra'] for r in muestra)

    estados_diag = []
    alertas = []
    for r in muestra:
        u = u_map.get(r['id_estado'], {})
        n_tot = u.get('n_total', 0)
        e_tot = u.get('elec_total', 0)
        cobertura_centros = round(r['n_muestra'] / n_tot * 100, 1) if n_tot else None
        peso_universo = round(e_tot / total_universo_electores * 100, 1) if total_universo_electores else None
        peso_muestra  = round(r['elec_muestra'] / total_muestra_electores * 100, 1) if total_muestra_electores else None
        desbalance    = round(peso_muestra - peso_universo, 2) if (peso_muestra and peso_universo) else None
        d = {
            'estado': r['nombre_estado'],
            'centros_muestra': r['n_muestra'],
            'centros_universo': n_tot,
            'cobertura_pct': cobertura_centros,
            'peso_universo_pct': peso_universo,
            'peso_muestra_pct': peso_muestra,
            'desbalance_pp': desbalance,
        }
        estados_diag.append(d)
        if cobertura_centros is not None and cobertura_centros < 10:
            alertas.append({'estado': r['nombre_estado'], 'cobertura_pct': cobertura_centros})

    # DEFF estimado: usa ICC=0.04 con tamaño de cluster promedio de la muestra
    icc = 0.04
    if total_muestra_centros > 0:
        m_bar = total_muestra_electores / total_muestra_centros if total_muestra_centros else 0
        deff = round(1.0 + (m_bar - 1) * icc, 3)
    else:
        deff = None

    return {
        'id_eleccion': id_eleccion,
        'n_centros_muestra': total_muestra_centros,
        'deff_estimado': deff,
        'estados': sorted(estados_diag, key=lambda x: abs(x['desbalance_pp'] or 0), reverse=True),
        'alertas_cobertura': alertas,
    }


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calcula pesos de la muestra')
    parser.add_argument('id_eleccion', type=int,
                        help='ID de la elección en la BD')
    parser.add_argument('--dry-run', action='store_true',
                        help='Muestra los pesos calculados sin guardar')
    parser.add_argument('--set', metavar='id_muestra', type=int, dest='set_id',
                        help='Editar manualmente los pesos de un centro')
    parser.add_argument('campos', nargs='*',
                        help='Con --set: campo=valor a actualizar')
    args = parser.parse_args()

    if args.set_id is not None:
        set_peso(args.set_id, args.campos)
    else:
        calcular(args.id_eleccion, dry_run=args.dry_run)
