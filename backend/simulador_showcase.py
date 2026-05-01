"""
simulador_showcase.py
Simula el día de elección insertando votos turno a turno en la BD.

Uso:
    python simulador_showcase.py [--delay 5] [--reset] [--sesgo 0.52] [--datos 2024]

Flags:
    --delay N      Segundos entre turnos (default: 5)
    --reset        Limpia votos y sms_raw antes de empezar
    --sesgo F      Fracción de votos para oposición, 0.0–1.0 (default: 0.52)
    --datos 2024   Usa porcentajes reales CNE 2024 por centro (ignora --sesgo)
                   Simula reporte gradual: los centros se incorporan turno a turno
                   para mostrar cómo evoluciona la confianza estadística.
"""

import argparse
import csv
import math
import os
import random
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'exitpoll.db')
CSV_2024 = os.path.join(BASE_DIR, 'resultados_cne2024.csv')

VOTOS_MIN_TURNO = 8
VOTOS_MAX_TURNO = 25
MUESTRA_MINIMA  = 385   # n mínimo para error ≤ ±5% con 95% de confianza (z=1.96, p=0.5)


# ──────────────────────────────────────────────
# Conexión
# ──────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    return conn


# ──────────────────────────────────────────────
# Carga de datos desde la BD
# ──────────────────────────────────────────────

def cargar_eleccion_activa(conn) -> dict:
    row = conn.execute('SELECT * FROM elecciones WHERE activa = 1').fetchone()
    if not row:
        raise SystemExit(
            'No hay ninguna elección activa (activa=1).\n'
            'Configura una en el dashboard antes de correr la simulación.'
        )
    return dict(row)


def cargar_muestra(conn, id_eleccion: int) -> list[dict]:
    rows = conn.execute('''
        SELECT
            m.id            AS id_muestra,
            m.codigo_centro,
            m.tipo_centro,
            p.peso_parroquia,
            p.peso_municipio,
            p.peso_estado,
            p.peso_nacion,
            c.nombre        AS centro_nombre,
            c.num_electores,
            c.id_estado,
            c.id_municipio,
            c.id_parroquia,
            c.lat,
            c.lon,
            e.nombre        AS estado_nombre,
            mu.nombre       AS municipio_nombre
        FROM muestra m
        JOIN centros  c ON c.codigo_cne  = m.codigo_centro
        JOIN estados  e ON e.id          = c.id_estado
        LEFT JOIN municipios mu ON mu.id  = c.id_municipio
        LEFT JOIN pesos p ON p.id_muestra = m.id
        WHERE m.id_eleccion = ? AND m.activo = 1 AND c.activo = 1
    ''', (id_eleccion,)).fetchall()

    if not rows:
        raise SystemExit(
            'La muestra está vacía para esta elección.\n'
            'Carga centros y genera la muestra en el dashboard primero.'
        )
    return [dict(r) for r in rows]


def cargar_candidatos(conn, id_eleccion: int) -> list[dict]:
    rows = conn.execute(
        'SELECT * FROM candidatos WHERE id_eleccion = ? ORDER BY orden',
        (id_eleccion,)
    ).fetchall()
    if not rows:
        raise SystemExit(
            'No hay candidatos para esta elección.\n'
            'Configúralos en el dashboard primero.'
        )
    return [dict(r) for r in rows]


def cargar_centros_candidatos(conn, codigos_centro: list[str]) -> dict[str, list[int]]:
    """Devuelve {codigo_centro: [id_candidato, ...]} desde centros_candidatos."""
    placeholders = ','.join('?' * len(codigos_centro))
    rows = conn.execute(
        f'SELECT codigo_centro, id_candidato FROM centros_candidatos WHERE codigo_centro IN ({placeholders})',
        codigos_centro
    ).fetchall()
    mapa: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        mapa[r['codigo_centro']].append(r['id_candidato'])
    return dict(mapa)


# ──────────────────────────────────────────────
# Encuestadores ficticios
# ──────────────────────────────────────────────

def registrar_encuestadores(conn, centros: list[dict], id_eleccion: int) -> dict[str, str]:
    """
    Garantiza que cada centro tenga al menos un encuestador activo.
    Devuelve {codigo_centro: telefono}.
    """
    telefonos: dict[str, str] = {}

    # Primero reusa los existentes
    rows = conn.execute(
        'SELECT codigo_centro, telefono FROM encuestadores WHERE id_eleccion = ? AND activo = 1',
        (id_eleccion,)
    ).fetchall()
    for r in rows:
        if r['codigo_centro'] not in telefonos:
            telefonos[r['codigo_centro']] = r['telefono']

    # Crea los que faltan
    conn.execute('BEGIN')
    for centro in centros:
        codigo = centro['codigo_centro']
        if codigo in telefonos:
            continue
        # Teléfono determinista basado en el código del centro
        sufijo = abs(hash(codigo)) % 10_000_000
        tel = f'+5804140{sufijo:07d}'
        conn.execute('''
            INSERT OR IGNORE INTO encuestadores
                (telefono, nombre, codigo_centro, id_eleccion, activo)
            VALUES (?, ?, ?, ?, 1)
        ''', (tel, f'Simulador-{codigo}', codigo, id_eleccion))
        telefonos[codigo] = tel
    conn.commit()

    return telefonos


# ──────────────────────────────────────────────
# Lógica de simulación
# ──────────────────────────────────────────────

def cargar_pct_2024() -> dict[str, tuple[float, float]]:
    """Devuelve {codigo_cne: (p_gobierno, p_oposicion)} desde el CSV CNE 2024."""
    pct: dict[str, tuple[float, float]] = {}
    with open(CSV_2024, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            p_g = float(row['pct_gobierno']) / 100
            p_o = float(row['pct_oposicion']) / 100
            pct[row['centro_cne_id']] = (p_g, p_o)
    return pct


def calcular_confianza(n: int, z: float = 1.96) -> tuple[float, float]:
    """
    Devuelve (confianza_pct, error_pct) para n muestras.
    Usa p=0.5 (peor caso) para el error máximo posible.
    Con n=385: error ≈ ±5.0% a 95% de confianza.
    """
    if n == 0:
        return 95.0, float('inf')
    error = z * math.sqrt(0.25 / n) * 100
    return 95.0, error


def generar_turnos(hora_apertura: str, hora_cierre: str) -> list[str]:
    t      = datetime.strptime(hora_apertura, '%H:%M')
    cierre = datetime.strptime(hora_cierre,   '%H:%M')
    turnos = []
    while t <= cierre:
        turnos.append(t.strftime('%H:%M'))
        t += timedelta(minutes=20)
    return turnos


def calcular_num_turno(hora_str: str, apertura_str: str) -> int:
    h = datetime.strptime(hora_str,   '%H:%M')
    a = datetime.strptime(apertura_str, '%H:%M')
    return max(0, int((h - a).total_seconds() // 1200))


def pesos_por_candidato(candidatos: list[dict], sesgo_oposicion: float) -> dict[int, float]:
    """
    Distribuye la probabilidad de voto entre candidatos.
    sesgo_oposicion: fracción total para candidatos de bando 'oposicion'.
    El resto se reparte uniformemente entre los demás bandos.
    """
    opos = [c for c in candidatos if c['bando'] == 'oposicion']
    otros = [c for c in candidatos if c['bando'] != 'oposicion']

    pesos: dict[int, float] = {}

    if opos and otros:
        p_opos  = sesgo_oposicion / len(opos)
        p_otros = (1.0 - sesgo_oposicion) / len(otros)
        for c in opos:  pesos[c['id']] = p_opos
        for c in otros: pesos[c['id']] = p_otros
    else:
        # Un solo bando o sin bando asignado: distribución uniforme
        for c in candidatos:
            pesos[c['id']] = 1.0 / len(candidatos)

    return pesos


def votos_para_turno(num_electores: int) -> int:
    """Votos a generar en un turno. Escala con electores, acotado al rango 8–25."""
    base = max(VOTOS_MIN_TURNO, min(VOTOS_MAX_TURNO, num_electores // 400))
    return base + random.randint(-1, 3)


def insertar_voto_bd(conn, codigo_centro: str, id_candidato: int,
                     telefono: str, hora_iso: str, turno: int,
                     lat: float, lon: float) -> None:
    hora_hhmm = hora_iso[11:16].replace(':', '')
    geohash   = f'{abs(hash(codigo_centro + hora_iso)) % 16_777_216:06x}'
    contenido = f'C{codigo_centro};V{id_candidato};T{hora_hhmm};L{geohash}'

    cur = conn.execute('''
        INSERT INTO sms_raw (from_number, contenido, recibido_at, procesado)
        VALUES (?, ?, ?, 1)
    ''', (telefono, contenido, hora_iso))
    id_sms = cur.lastrowid

    distancia = random.randint(30, 280)
    conn.execute('''
        INSERT INTO votos
            (id_sms, codigo_centro, id_candidato, telefono,
             hora, turno, lat, lon, distancia_m, valido)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    ''', (id_sms, codigo_centro, id_candidato, telefono,
          hora_iso, turno, lat, lon, distancia))


# ──────────────────────────────────────────────
# Resultado ponderado
# ──────────────────────────────────────────────

def calcular_resultado_ponderado(conn, id_eleccion: int, tipo: str,
                                  centros: list[dict],
                                  candidatos: list[dict]) -> dict[int, float] | dict[int, dict[int, float]]:
    """
    Devuelve el resultado según el tipo de elección:
      nacional/asamblea → {id_candidato: pct}
      regional          → {id_estado: {id_candidato: pct}}
      municipal         → {id_municipio: {id_candidato: pct}}
    """
    rows = conn.execute('''
        SELECT v.codigo_centro, v.id_candidato, COUNT(*) AS n
        FROM votos v
        JOIN muestra m ON m.codigo_centro = v.codigo_centro
        WHERE m.id_eleccion = ? AND v.valido = 1
        GROUP BY v.codigo_centro, v.id_candidato
    ''', (id_eleccion,)).fetchall()

    votos_centro: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        votos_centro[r['codigo_centro']][r['id_candidato']] = r['n']

    peso_map = {c['codigo_centro']: c for c in centros}
    resultado: dict[int, float] = defaultdict(float)

    if tipo in ('nacional', 'asamblea'):
        # Primer nivel: peso_estado → resultado por estado
        # Segundo nivel: peso_nacion → agrega estados al total nacional
        pn_estado: dict[int, float] = {}
        for c in centros:
            eid = c['id_estado']
            if eid not in pn_estado and c.get('peso_nacion') is not None:
                pn_estado[eid] = c['peso_nacion']

        por_estado: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        for codigo, vc in votos_centro.items():
            centro = peso_map.get(codigo)
            if not centro:
                continue
            total_v = sum(vc.values())
            if not total_v:
                continue
            pe = centro.get('peso_estado') or 0.0
            for id_cand, n in vc.items():
                por_estado[centro['id_estado']][id_cand] += (n / total_v) * pe

        for id_estado, por_cand in por_estado.items():
            pn = pn_estado.get(id_estado, 0.0)
            for id_cand, val in por_cand.items():
                resultado[id_cand] += val * pn

    elif tipo == 'regional':
        # Primer nivel: peso_municipio → resultado por municipio
        # Segundo nivel: universo real municipio/estado → agrega municipios al estado
        uni_muni = {r['id_municipio']: r['total'] for r in conn.execute(
            'SELECT id_municipio, SUM(num_electores) AS total FROM centros WHERE activo=1 GROUP BY id_municipio'
        ).fetchall()}
        uni_estado = {r['id_estado']: r['total'] for r in conn.execute(
            'SELECT id_estado, SUM(num_electores) AS total FROM centros WHERE activo=1 GROUP BY id_estado'
        ).fetchall()}

        por_estado_r: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        for codigo, vc in votos_centro.items():
            centro = peso_map.get(codigo)
            if not centro:
                continue
            total_v = sum(vc.values())
            if not total_v:
                continue
            pm  = centro.get('peso_municipio') or 0.0
            den = uni_estado.get(centro['id_estado'], 0)
            w2  = (uni_muni.get(centro['id_municipio'], 0) / den) if den else 0.0
            for id_cand, n in vc.items():
                por_estado_r[centro['id_estado']][id_cand] += (n / total_v) * pm * w2

        for id_estado, por_cand in por_estado_r.items():
            total_e = sum(por_cand.values())
            if total_e > 0:
                resultado[id_estado] = {
                    id_cand: val / total_e * 100
                    for id_cand, val in por_cand.items()
                }
        return dict(resultado) if resultado else _fallback_conteos_por_ambito(
            votos_centro, peso_map, 'id_estado'
        )

    elif tipo == 'municipal':
        # Primer nivel: peso_parroquia → resultado por parroquia
        # Segundo nivel: universo real parroquia/municipio → agrega parroquias al municipio
        uni_parr = {r['id_parroquia']: r['total'] for r in conn.execute(
            'SELECT id_parroquia, SUM(num_electores) AS total FROM centros WHERE activo=1 GROUP BY id_parroquia'
        ).fetchall()}
        uni_muni_m = {r['id_municipio']: r['total'] for r in conn.execute(
            'SELECT id_municipio, SUM(num_electores) AS total FROM centros WHERE activo=1 GROUP BY id_municipio'
        ).fetchall()}

        por_muni_m: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        for codigo, vc in votos_centro.items():
            centro = peso_map.get(codigo)
            if not centro:
                continue
            total_v = sum(vc.values())
            if not total_v:
                continue
            pp  = centro.get('peso_parroquia') or 0.0
            den = uni_muni_m.get(centro['id_municipio'], 0)
            w2  = (uni_parr.get(centro['id_parroquia'], 0) / den) if den else 0.0
            for id_cand, n in vc.items():
                por_muni_m[centro['id_municipio']][id_cand] += (n / total_v) * pp * w2

        for id_muni, por_cand in por_muni_m.items():
            total_m = sum(por_cand.values())
            if total_m > 0:
                resultado[id_muni] = {
                    id_cand: val / total_m * 100
                    for id_cand, val in por_cand.items()
                }
        return dict(resultado) if resultado else _fallback_conteos_por_ambito(
            votos_centro, peso_map, 'id_municipio'
        )

    # nacional/asamblea: normalizar a 100
    total = sum(resultado.values())
    if total > 0:
        return {k: v / total * 100 for k, v in resultado.items()}
    return _fallback_conteos(votos_centro)


def _fallback_conteos(votos_centro: dict) -> dict[int, float]:
    conteos: dict[int, int] = defaultdict(int)
    for vc in votos_centro.values():
        for id_cand, n in vc.items():
            conteos[id_cand] += n
    total_v = sum(conteos.values())
    return {k: v / total_v * 100 for k, v in conteos.items()} if total_v else {}


def _fallback_conteos_por_ambito(votos_centro: dict, peso_map: dict, scope_field: str) -> dict[int, dict[int, float]]:
    conteos_scope: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for codigo, vc in votos_centro.items():
        centro = peso_map.get(codigo)
        scope_id = centro.get(scope_field) if centro else None
        if scope_id is None:
            continue
        for id_cand, n in vc.items():
            conteos_scope[scope_id][id_cand] += n

    resultado_scope: dict[int, dict[int, float]] = {}
    for scope_id, conteos in conteos_scope.items():
        total_v = sum(conteos.values())
        if total_v:
            resultado_scope[scope_id] = {
                id_cand: n / total_v * 100
                for id_cand, n in conteos.items()
            }
    return resultado_scope


def _resultado_es_anidado(resultado: dict) -> bool:
    return any(isinstance(v, dict) for v in resultado.values())


def _print_resultado_plano(resultado: dict[int, float], candidatos: list[dict], indent: str = '  ') -> None:
    for cand in candidatos:
        pct = resultado.get(cand['id'], 0.0)
        bar = '█' * int(pct / 2)
        print(f'{indent}{cand["nombre"]:<30}  {pct:4.1f}%  {bar}')


def _print_resultado_anidado(resultado: dict[int, dict[int, float]],
                             candidatos: list[dict],
                             labels: dict[int, str],
                             fallback_prefix: str) -> None:
    for scope_id in sorted(resultado):
        label = labels.get(scope_id) or f'{fallback_prefix} {scope_id}'
        print(f'  {label}:')
        _print_resultado_plano(resultado[scope_id], candidatos, indent='    ')


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Simula el día de elección — inyecta votos turno a turno en la BD'
    )
    parser.add_argument('--delay', type=float, default=5.0,
                        help='Segundos entre turnos (default: 5)')
    parser.add_argument('--reset', action='store_true',
                        help='Limpia votos y sms_raw antes de empezar')
    parser.add_argument('--sesgo', type=float, default=0.52,
                        help='Fracción de votos para oposición 0.0–1.0 (default: 0.52)')
    parser.add_argument('--datos', choices=['2024'], default=None,
                        help='Usa porcentajes reales CNE 2024 por centro (ignora --sesgo)')
    args = parser.parse_args()

    if not 0.0 <= args.sesgo <= 1.0:
        raise SystemExit('--sesgo debe estar entre 0.0 y 1.0')

    pct_2024: dict[str, tuple[float, float]] = {}
    if args.datos == '2024':
        pct_2024 = cargar_pct_2024()
        print(f'[+] Usando datos reales CNE 2024 ({len(pct_2024):,} centros cargados)')

    conn = get_conn()

    try:
        # ── Cargar datos ──────────────────────────────────
        eleccion   = cargar_eleccion_activa(conn)
        centros    = cargar_muestra(conn, eleccion['id'])
        candidatos = cargar_candidatos(conn, eleccion['id'])

        codigos = [c['codigo_centro'] for c in centros]
        cc_map  = cargar_centros_candidatos(conn, codigos)

        # Para centros sin centros_candidatos, usar todos los candidatos
        cands_id_todos = [c['id'] for c in candidatos]
        cands_por_centro: dict[str, list[dict]] = {}
        for c in centros:
            ids = cc_map.get(c['codigo_centro'], cands_id_todos)
            cands_por_centro[c['codigo_centro']] = [x for x in candidatos if x['id'] in ids]

        print(f'\n{"═"*60}')
        print(f'  EXIT POLL — SIMULADOR SHOWCASE')
        print(f'{"═"*60}')
        print(f'  Elección : {eleccion["nombre"]}')
        print(f'  Tipo     : {eleccion["tipo"]}')
        print(f'  Fecha    : {eleccion["fecha"]}')
        print(f'  Horario  : {eleccion["hora_apertura"]} → {eleccion["hora_cierre"]}')
        print(f'  Centros  : {len(centros)}')
        print(f'  Candidatos:')
        for c in candidatos:
            print(f'    [{c["id"]:2d}] {c["nombre"]:<30} ({c["bando"] or "—"})')
        modo_datos = f'CNE 2024 por centro' if args.datos == '2024' else f'sesgo fijo {args.sesgo:.0%}'
        print(f'  Modo datos      : {modo_datos}')
        print(f'  Delay por turno : {args.delay}s')
        print(f'  Muestra mínima  : {MUESTRA_MINIMA} votos (error ≤ ±5% con 95% confianza)')
        print(f'{"─"*60}')

        # ── Reset opcional ────────────────────────────────
        if args.reset:
            conn.execute('DELETE FROM votos')
            conn.execute('DELETE FROM sms_raw')
            conn.commit()
            print('  [reset] votos y sms_raw limpiados\n')

        # ── Encuestadores ─────────────────────────────────
        telefonos = registrar_encuestadores(conn, centros, eleccion['id'])

        # ── Asignar turno de inicio por centro (solo modo 2024) ──────────
        # Simula que los encuestadores no reportan todos al mismo tiempo:
        # los primeros turnos tienen pocos centros, el reporte se va completando
        # gradualmente — igual que en campo real. Esto hace que la muestra crezca
        # despacio al principio y el error sea alto hasta cruzar la muestra mínima.
        if args.datos == '2024':
            turno_inicio = {c['codigo_centro']: random.randint(1, 6) for c in centros}
        else:
            turno_inicio = {c['codigo_centro']: 1 for c in centros}

        # ── Simular turnos ────────────────────────────────
        turnos = generar_turnos(eleccion['hora_apertura'], eleccion['hora_cierre'])
        print(f'  Turnos a simular: {len(turnos)}')
        print(f'{"─"*60}')

        conteo_total: dict[int, int] = defaultdict(int)
        muestra_alcanzada = False

        for idx, hora_str in enumerate(turnos):
            turno_num = calcular_num_turno(hora_str, eleccion['hora_apertura'])
            hora_iso  = f'{eleccion["fecha"]}T{hora_str}:00'

            votos_turno: dict[int, int] = defaultdict(int)
            centros_activos = 0

            conn.execute('BEGIN')
            for centro in centros:
                codigo = centro['codigo_centro']

                # En modo 2024: el centro no reporta hasta su turno de inicio
                if turno_num < turno_inicio.get(codigo, 1):
                    continue

                cands  = cands_por_centro[codigo]
                if not cands:
                    continue
                centros_activos += 1

                tel = telefonos[codigo]
                lat = centro.get('lat') or 10.5 + random.uniform(-2, 2)
                lon = centro.get('lon') or -66.9 + random.uniform(-3, 3)

                if args.datos == '2024' and codigo in pct_2024:
                    # Probabilidades reales por centro
                    p_g, p_o = pct_2024[codigo]
                    p_tot = p_g + p_o
                    cand_gob = next((c for c in cands if c['bando'] == 'gobierno'), None)
                    cand_op  = next((c for c in cands if c['bando'] == 'oposicion'), None)
                    n = votos_para_turno(centro['num_electores'])
                    for _ in range(n):
                        if cand_gob and cand_op and p_tot > 0:
                            id_cand = cand_gob['id'] if random.random() < (p_g / p_tot) else cand_op['id']
                        else:
                            id_cand = random.choice(cands)['id']
                        insertar_voto_bd(conn, codigo, id_cand, tel, hora_iso, turno_num, lat, lon)
                        votos_turno[id_cand]  += 1
                        conteo_total[id_cand] += 1
                else:
                    pesos  = pesos_por_candidato(cands, args.sesgo)
                    n      = votos_para_turno(centro['num_electores'])
                    ids_cands = list(pesos.keys())
                    probs     = [pesos[cid] for cid in ids_cands]
                    for _ in range(n):
                        id_cand = random.choices(ids_cands, weights=probs, k=1)[0]
                        insertar_voto_bd(conn, codigo, id_cand, tel, hora_iso, turno_num, lat, lon)
                        votos_turno[id_cand]  += 1
                        conteo_total[id_cand] += 1
            conn.commit()

            # ── Estadísticas del turno ────────────────────
            total_turno  = sum(votos_turno.values())
            n_acum       = sum(conteo_total.values())
            _, error_pct = calcular_confianza(n_acum)

            detalle = '  '.join(
                f'{next(c["nombre"] for c in candidatos if c["id"] == cid)}: {v}'
                for cid, v in sorted(votos_turno.items())
            )
            print(f'  Turno {turno_num:2d}  {hora_str}  │  +{total_turno:4d} votos  │  {detalle}')
            print(f'         {"":8}  │  Muestra acum: {n_acum:5d}  │  '
                  f'Centros reportando: {centros_activos}/{len(centros)}  │  '
                  f'Error: ±{error_pct:.1f}%', end='')

            if n_acum >= MUESTRA_MINIMA:
                if not muestra_alcanzada:
                    print(f'  ← [✓ MUESTRA MÍNIMA ALCANZADA — tendencia confiable]')
                    muestra_alcanzada = True
                else:
                    print()
            else:
                faltan = MUESTRA_MINIMA - n_acum
                print(f'  [⚠ muestra insuficiente — faltan {faltan} datos]')

            if args.delay > 0 and idx < len(turnos) - 1:
                time.sleep(args.delay)

        # ── Resumen final ─────────────────────────────────
        total_votos = sum(conteo_total.values())
        print(f'\n{"═"*60}')
        print(f'  RESUMEN FINAL')
        print(f'{"─"*60}')
        print(f'  Total votos insertados: {total_votos}')
        print()
        for cand in candidatos:
            n   = conteo_total.get(cand['id'], 0)
            pct = n / total_votos * 100 if total_votos else 0
            bar = '█' * int(pct / 2)
            print(f'  {cand["nombre"]:<30}  {n:5d}  ({pct:4.1f}%)  {bar}')

        _formula = {
            'nacional':  'peso_estado × peso_nacion',
            'asamblea':  'peso_estado × peso_nacion',
            'regional':  'peso_municipio × universo_municipio/estado',
            'municipal': 'peso_parroquia × universo_parroquia/municipio',
        }.get(eleccion['tipo'], 'ponderado')
        print(f'\n  Resultado ponderado ({_formula}):')
        resultado = calcular_resultado_ponderado(conn, eleccion['id'], eleccion['tipo'], centros, candidatos)
        if resultado:
            if _resultado_es_anidado(resultado):
                if eleccion['tipo'] == 'regional':
                    labels = {
                        c['id_estado']: c.get('estado_nombre') or f'Estado {c["id_estado"]}'
                        for c in centros
                    }
                    _print_resultado_anidado(resultado, candidatos, labels, 'Estado')
                else:
                    labels = {
                        c['id_municipio']: c.get('municipio_nombre') or f'Municipio {c["id_municipio"]}'
                        for c in centros
                        if c.get('id_municipio') is not None
                    }
                    _print_resultado_anidado(resultado, candidatos, labels, 'Municipio')
            else:
                for cand in candidatos:
                    pct = resultado.get(cand['id'], 0.0)
                    bar = '█' * int(pct / 2)
                    print(f'  {cand["nombre"]:<30}  {pct:4.1f}%  {bar}')
        else:
            print('  [sin pesos calculados — se muestran conteos directos]')

        print(f'\n{"═"*60}')
        print(f'  Simulación completada.')
        print(f'{"═"*60}\n')

    finally:
        conn.close()


if __name__ == '__main__':
    main()
