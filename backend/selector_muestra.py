"""
Selector automático de muestra para Exit Poll.

Criterio (elección nacional):
  - Estados normales: los N centros más grandes cuyo resultado histórico
    sea representativo del resultado nacional (diferencia ≤ umbral %).
  - Excepciones (DC, Vargas, municipios Caracas-Miranda):
    selección por PARROQUIA en vez de por estado.

Parámetros configurables:
  - centros_por_unidad:  cuántos centros seleccionar por unidad geográfica (default 2)
  - umbral_pct:          tolerancia máxima de diferencia con resultado nacional (default 10)
  - eleccion_ref:        nombre de la elección de referencia en resultados_historicos
  - candidatos_por_unidad: pre-seleccionar más candidatos para revisión manual (default 5)
"""

import sqlite3
from typing import Optional

BASE_QUERY_CANDIDATOS = """
    SELECT c.codigo_cne, c.nombre, c.num_electores, c.num_mesas,
           e.id as id_estado, e.nombre as estado, e.es_excepcion as estado_exc,
           mu.id as id_municipio, mu.nombre as municipio, mu.es_excepcion as mun_exc,
           p.id as id_parroquia, p.nombre as parroquia,
           rh.pct_oposicion, rh.pct_gobierno, rh.votos_validos as votos_hist,
           ABS(rh.pct_oposicion - :pct_nac_opo) as diff_nac
    FROM centros c
    JOIN estados e ON c.id_estado = e.id
    LEFT JOIN municipios mu ON c.id_municipio = mu.id
    LEFT JOIN parroquias p ON c.id_parroquia = p.id
    LEFT JOIN resultados_historicos rh
        ON rh.codigo_centro = c.codigo_cne AND rh.eleccion_ref = :eleccion_ref
    WHERE c.activo = 1 AND c.num_electores > 0
"""


def resultado_nacional(conn: sqlite3.Connection, eleccion_ref: str) -> dict:
    """Calcula el resultado nacional de referencia."""
    row = conn.execute("""
        SELECT SUM(votos_validos) v, SUM(votos_gobierno) g, SUM(votos_oposicion) o
        FROM resultados_historicos WHERE eleccion_ref = ?
    """, (eleccion_ref,)).fetchone()
    if not row or not row[0]:
        return {"validos": 0, "pct_gobierno": 0, "pct_oposicion": 0}
    return {
        "validos": row[0],
        "pct_gobierno": round(100 * row[1] / row[0], 2),
        "pct_oposicion": round(100 * row[2] / row[0], 2),
    }


def generar_candidatos(
    conn: sqlite3.Connection,
    eleccion_ref: str = "2024-presidencial",
    candidatos_por_unidad: int = 5,
    umbral_pct: float = 10.0,
) -> list[dict]:
    """
    Genera lista de centros candidatos a la muestra, agrupados por unidad geográfica.
    Retorna lista de dicts con info del centro + campo 'unidad_geo' y 'rank'.
    """
    nac = resultado_nacional(conn, eleccion_ref)
    if not nac["validos"]:
        return []

    pct_nac_opo = nac["pct_oposicion"]

    # Traer todos los centros activos con sus resultados
    query = BASE_QUERY_CANDIDATOS + " ORDER BY c.num_electores DESC"
    rows = conn.execute(query, {
        "pct_nac_opo": pct_nac_opo,
        "eleccion_ref": eleccion_ref,
    }).fetchall()

    # Agrupar por unidad geográfica
    # Regla: si el estado es excepción → agrupar por parroquia
    #         si el municipio es excepción → agrupar por parroquia
    #         sino → agrupar por estado
    unidades = {}  # key -> lista de centros
    for r in rows:
        r = dict(r)
        if r["estado_exc"] or r["mun_exc"]:
            # Excepción: agrupar por parroquia
            key = f"parr_{r['id_parroquia']}"
            r["unidad_geo"] = f"{r['estado']} / {r['municipio']} / {r['parroquia']}"
            r["nivel_seleccion"] = "parroquia"
        else:
            # Normal: agrupar por estado
            key = f"edo_{r['id_estado']}"
            r["unidad_geo"] = r["estado"]
            r["nivel_seleccion"] = "estado"

        if key not in unidades:
            unidades[key] = []
        unidades[key].append(r)

    # Para cada unidad, seleccionar los mejores candidatos
    resultado = []
    for key, centros in unidades.items():
        # Filtrar: solo los que tienen resultado histórico y están dentro del umbral
        con_resultado = [c for c in centros if c["pct_oposicion"] is not None]
        representativos = [c for c in con_resultado if c["diff_nac"] is not None and c["diff_nac"] <= umbral_pct]

        # Ordenar por tamaño (más electores primero)
        representativos.sort(key=lambda x: x["num_electores"], reverse=True)

        # Si no hay suficientes representativos, completar con los más grandes sin filtro
        if len(representativos) < candidatos_por_unidad:
            codigos_ya = {c["codigo_cne"] for c in representativos}
            for c in centros:
                if c["codigo_cne"] not in codigos_ya:
                    c["diff_nac"] = c.get("diff_nac") or 999
                    representativos.append(c)
                if len(representativos) >= candidatos_por_unidad:
                    break

        for rank, c in enumerate(representativos[:candidatos_por_unidad], 1):
            c["rank"] = rank
            c["representativo"] = (c.get("diff_nac") or 999) <= umbral_pct
            resultado.append(c)

    # Ordenar por unidad geográfica y rank
    resultado.sort(key=lambda x: (x["unidad_geo"], x["rank"]))
    return resultado


def aplicar_muestra(
    conn: sqlite3.Connection,
    id_eleccion: int,
    codigos_centros: list[str],
    tipo_centro: str = "estandar",
):
    """Inserta los centros seleccionados en la tabla muestra."""
    # Limpiar muestra previa de esta elección
    conn.execute("DELETE FROM muestra WHERE id_eleccion = ?", (id_eleccion,))
    conn.execute("DELETE FROM pesos WHERE id_muestra NOT IN (SELECT id FROM muestra)")

    for codigo in codigos_centros:
        conn.execute(
            "INSERT INTO muestra (id_eleccion, codigo_centro, tipo_centro, activo) VALUES (?,?,?,1)",
            (id_eleccion, codigo, tipo_centro),
        )
    conn.commit()
    return len(codigos_centros)
