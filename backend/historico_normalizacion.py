"""Contratos aditivos para resultados historicos normalizados."""

from __future__ import annotations

import sqlite3


RESULTADOS_HISTORICOS_COLUMNS = {
    "electores_inscritos": "ALTER TABLE resultados_historicos ADD COLUMN electores_inscritos INTEGER",
    "votantes": "ALTER TABLE resultados_historicos ADD COLUMN votantes INTEGER",
    "votos_nulos": "ALTER TABLE resultados_historicos ADD COLUMN votos_nulos INTEGER",
    "pct_otros": "ALTER TABLE resultados_historicos ADD COLUMN pct_otros REAL",
    "participacion": "ALTER TABLE resultados_historicos ADD COLUMN participacion REAL",
    "incluye_exterior": "ALTER TABLE resultados_historicos ADD COLUMN incluye_exterior INTEGER",
    "granularidad": "ALTER TABLE resultados_historicos ADD COLUMN granularidad TEXT",
    "fuente": "ALTER TABLE resultados_historicos ADD COLUMN fuente TEXT",
    "corte_fuente": "ALTER TABLE resultados_historicos ADD COLUMN corte_fuente TEXT",
    "notas": "ALTER TABLE resultados_historicos ADD COLUMN notas TEXT",
    "num_mesas": "ALTER TABLE resultados_historicos ADD COLUMN num_mesas INTEGER",
    "detalle_otros_json": "ALTER TABLE resultados_historicos ADD COLUMN detalle_otros_json TEXT",
}

HISTORICO_FUENTES_COLUMNS = {
    "incluye_exterior": "ALTER TABLE historico_fuentes ADD COLUMN incluye_exterior INTEGER",
    "corte_fuente": "ALTER TABLE historico_fuentes ADD COLUMN corte_fuente TEXT",
    "centros_cubiertos": "ALTER TABLE historico_fuentes ADD COLUMN centros_cubiertos INTEGER",
    "mesas_cubiertas": "ALTER TABLE historico_fuentes ADD COLUMN mesas_cubiertas INTEGER",
    "electores_inscritos": "ALTER TABLE historico_fuentes ADD COLUMN electores_inscritos INTEGER",
    "votantes": "ALTER TABLE historico_fuentes ADD COLUMN votantes INTEGER",
    "votos_validos": "ALTER TABLE historico_fuentes ADD COLUMN votos_validos INTEGER",
    "votos_nulos": "ALTER TABLE historico_fuentes ADD COLUMN votos_nulos INTEGER",
    "votos_gobierno": "ALTER TABLE historico_fuentes ADD COLUMN votos_gobierno INTEGER",
    "votos_oposicion": "ALTER TABLE historico_fuentes ADD COLUMN votos_oposicion INTEGER",
    "votos_otros": "ALTER TABLE historico_fuentes ADD COLUMN votos_otros INTEGER",
}


def ensure_historico_normalizado_schema(conn: sqlite3.Connection) -> None:
    """Agrega columnas normalizadas sin alterar el contrato legado."""
    rh_cols = {r[1] for r in conn.execute("PRAGMA table_info(resultados_historicos)")}
    for col, ddl in RESULTADOS_HISTORICOS_COLUMNS.items():
        if col not in rh_cols:
            conn.execute(ddl)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_fuentes (
            eleccion_ref    TEXT PRIMARY KEY,
            fuente          TEXT NOT NULL,
            granularidad    TEXT NOT NULL,
            cobertura_pct   REAL,
            comparabilidad  TEXT NOT NULL DEFAULT 'directa',
            notas           TEXT,
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)
    hf_cols = {r[1] for r in conn.execute("PRAGMA table_info(historico_fuentes)")}
    for col, ddl in HISTORICO_FUENTES_COLUMNS.items():
        if col not in hf_cols:
            conn.execute(ddl)
