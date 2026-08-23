"""Valida totales normalizados de resultados_historicos."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

try:
    from historico_normalizacion import ensure_historico_normalizado_schema
except ImportError:  # pragma: no cover - package import path
    from .historico_normalizacion import ensure_historico_normalizado_schema


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "exitpoll.db"
DEFAULT_REFS = ("2006-presidencial", "2012-presidencial", "2013-presidencial", "2018-presidencial")


def _pct(num: int | None, den: int | None) -> float | None:
    return round(100 * num / den, 4) if num is not None and den else None


def validate(db_path: Path = DB_PATH, refs: tuple[str, ...] = DEFAULT_REFS) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_historico_normalizado_schema(conn)
        out = []
        for ref in refs:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS centros,
                    SUM(num_mesas) AS mesas,
                    SUM(electores_inscritos) AS electores,
                    SUM(votantes) AS votantes,
                    SUM(votos_validos) AS validos,
                    SUM(votos_nulos) AS nulos,
                    SUM(votos_gobierno) AS gobierno,
                    SUM(votos_oposicion) AS oposicion,
                    SUM(votos_otros) AS otros,
                    MAX(incluye_exterior) AS incluye_exterior
                FROM resultados_historicos
                WHERE eleccion_ref=?
                """,
                (ref,),
            ).fetchone()
            meta = conn.execute(
                "SELECT fuente, granularidad, cobertura_pct, corte_fuente FROM historico_fuentes WHERE eleccion_ref=?",
                (ref,),
            ).fetchone()
            validos = row["validos"]
            votantes = row["votantes"]
            electores = row["electores"]
            item = {
                "eleccion_ref": ref,
                "centros": row["centros"] or 0,
                "mesas": row["mesas"],
                "electores": electores,
                "votantes": votantes,
                "validos": validos,
                "nulos": row["nulos"],
                "gobierno": row["gobierno"],
                "oposicion": row["oposicion"],
                "otros": row["otros"],
                "pct_gobierno": _pct(row["gobierno"], validos),
                "pct_oposicion": _pct(row["oposicion"], validos),
                "pct_otros": _pct(row["otros"], validos),
                "participacion": _pct(votantes, electores),
                "incluye_exterior": bool(row["incluye_exterior"]),
                "cobertura_pct": meta["cobertura_pct"] if meta else None,
                "fuente": meta["fuente"] if meta else None,
                "granularidad": meta["granularidad"] if meta else None,
                "corte_fuente": meta["corte_fuente"] if meta else None,
                "delta_validos": (row["gobierno"] or 0) + (row["oposicion"] or 0) + (row["otros"] or 0) - (validos or 0),
                "delta_votantes": (validos or 0) + (row["nulos"] or 0) - (votantes or 0),
            }
            out.append(item)
        return out
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("refs", nargs="*", default=list(DEFAULT_REFS))
    args = ap.parse_args()

    rows = validate(args.db, tuple(args.refs))
    headers = [
        "ref", "centros", "mesas", "electores", "votantes", "validos", "nulos",
        "gob", "opo", "otros", "%gob", "%opo", "%otros", "part", "ext",
        "cob", "fuente", "delta_validos", "delta_votantes",
    ]
    print("\t".join(headers))
    for r in rows:
        print("\t".join(str(v) for v in [
            r["eleccion_ref"],
            r["centros"],
            r["mesas"],
            r["electores"],
            r["votantes"],
            r["validos"],
            r["nulos"],
            r["gobierno"],
            r["oposicion"],
            r["otros"],
            r["pct_gobierno"],
            r["pct_oposicion"],
            r["pct_otros"],
            r["participacion"],
            "si" if r["incluye_exterior"] else "no",
            r["cobertura_pct"],
            r["fuente"],
            r["delta_validos"],
            r["delta_votantes"],
        ]))


if __name__ == "__main__":
    main()
