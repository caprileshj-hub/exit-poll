"""
Genera el TM estandar 2024 COMPLETO (una fila por mesa) a partir de:

  1. centros_cne_2024_rep.csv  -> marco oficial del REP 2024 por CENTRO
                                  (15.962 centros, 21.392.464 electores
                                  venezolanos + 228.144 extranjeros).
                                  Fuente: hoja "15.962 centros_cne" del
                                  spreadsheet de ipince/vzlapi, datos del CNE.
  2. centros_cne_2024.csv      -> dump de actas de resultadosconvzla; da el
                                  numero de mesa REAL para los centros con acta.

El CNE nunca publico el marco 2024 desagregado por mesa, asi que el numero de
mesas por centro se resuelve en dos vias y queda marcado en `origen_mesas`:

  * `acta`     -> la mesa de mayor numero vista en las actas manda (dato duro).
  * `derivado` -> ceil(electores_total / CAP_MESA).

CAP_MESA=1000 se calibro por barrido contra las 22.197 mesas conocidas:
da 11.177 centros con coincidencia exacta (94%), solo 23 centros donde el acta
muestra mas mesas que la formula (0,19%), y ~30.4k mesas nacionales contra las
~30.027 oficiales (24.532 mesas transmitidas = 81,7% segun resultadosconvzla).

La columna `electores` usa electores_venezolanos: los extranjeros estan en el
REP pero no votan presidenciales, y asi el total del TM cuadra exacto con la
cifra oficial del REP presidencial 2024. Los extranjeros si cuentan para armar
las mesas, porque el cuaderno del centro los incluye.

El reparto de electores entre las mesas de un centro es uniforme (el CNE parte
el cuaderno alfabeticamente); el resto se reparte a las primeras mesas.

Uso:
    python generar_tm_2024.py [-o tm_2024_estandar_v2.csv]
"""

import argparse
import csv
import math
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REP_CSV   = os.path.join(BASE_DIR, 'centros_cne_2024_rep.csv')
ACTAS_CSV = os.path.join(BASE_DIR, 'centros_cne_2024.csv')

CAP_MESA = 1000

COLUMNAS = [
    'codigo_centro', 'nombre_centro', 'direccion',
    'cod_estado', 'estado', 'cod_municipio', 'municipio',
    'cod_parroquia', 'parroquia',
    'numero_mesa', 'electores',
    'circuito_an', 'lat', 'lon', 'riesgo',
    'origen_mesas',
]


def leer_mesas_de_actas(path: str) -> dict[str, int]:
    """Mesa de mayor numero vista en las actas, por centro."""
    maximo: dict[str, int] = defaultdict(int)
    with open(path, encoding='utf-8-sig') as f:
        for fila in csv.DictReader(f):
            centro = fila['centro_cne_id'].strip()
            try:
                mesa = int(fila['mesa'])
            except (TypeError, ValueError):
                continue
            if mesa > maximo[centro]:
                maximo[centro] = mesa
    return dict(maximo)


def repartir(total: int, n: int) -> list[int]:
    """Reparte `total` electores entre `n` mesas lo mas parejo posible."""
    base, resto = divmod(total, n)
    return [base + 1] * resto + [base] * (n - resto)


def generar(salida: str) -> None:
    mesas_acta = leer_mesas_de_actas(ACTAS_CSV)

    stats = {'centros': 0, 'mesas': 0, 'electores': 0,
             'origen_acta': 0, 'origen_derivado': 0, 'discrepancias': 0}

    with open(REP_CSV, encoding='utf-8') as f_in, \
         open(salida, 'w', newline='', encoding='utf-8') as f_out:

        writer = csv.DictWriter(f_out, fieldnames=COLUMNAS)
        writer.writeheader()

        for centro in csv.DictReader(f_in):
            codigo = centro['centro_cne_id'].strip()
            ven    = int(float(centro['electores_venezolanos'] or 0))
            total  = int(float(centro['electores_total'] or 0))

            derivado = max(1, math.ceil(total / CAP_MESA))
            visto    = mesas_acta.get(codigo, 0)

            if visto >= derivado and visto > 0:
                num_mesas, origen = visto, 'acta'
                stats['origen_acta'] += 1
                if visto > derivado:
                    stats['discrepancias'] += 1
            else:
                num_mesas, origen = derivado, 'derivado'
                stats['origen_derivado'] += 1

            base = {
                'codigo_centro': codigo,
                'nombre_centro': centro['centro'].strip(),
                'direccion':     '',
                'cod_estado':    centro['estado_cne_id'].strip().zfill(2),
                'estado':        centro['estado_largo'].strip(),
                'cod_municipio': centro['municipio_cne_id'].strip().zfill(2),
                'municipio':     'MP. ' + centro['municipio_corto'].strip(),
                'cod_parroquia': centro['parroquia_cne_id'].strip().zfill(2),
                'parroquia':     'PQ. ' + centro['parroquia_corto'].strip(),
                'circuito_an':   '',
                'lat':           '',
                'lon':           '',
                'riesgo':        1,
                'origen_mesas':  origen,
            }

            for i, electores in enumerate(repartir(ven, num_mesas), start=1):
                writer.writerow({**base, 'numero_mesa': i, 'electores': electores})

            stats['centros']   += 1
            stats['mesas']     += num_mesas
            stats['electores'] += ven

    print(f'[+] Escrito: {salida}')
    print(f'    centros           : {stats["centros"]:,}')
    print(f'    mesas             : {stats["mesas"]:,}')
    print(f'    electores          : {stats["electores"]:,}')
    print(f'    mesas por acta     : {stats["origen_acta"]:,} centros'
          f' ({stats["discrepancias"]:,} por encima de la formula)')
    print(f'    mesas derivadas    : {stats["origen_derivado"]:,} centros')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--salida', default=os.path.join(BASE_DIR, 'tm_2024_estandar_v2.csv'))
    args = ap.parse_args()
    generar(args.salida)
