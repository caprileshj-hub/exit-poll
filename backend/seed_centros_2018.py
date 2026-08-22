"""Carga el marco electoral 2018 por centro en centro_snapshot.

Fuente: Directorio de Centros de Votacion Elecciones 2018 (CNE, Junta Nacional
Electoral / ONIE), recuperado via Wayback Machine y parseado por
parse_centros_2018.py a centros_cne_2018.csv.

IMPORTANTE: 2018 aporta MARCO (electores y mesas por centro), no resultados.
No se inserta nada en resultados_historicos porque el CNE nunca publico el
desglose territorial de esa eleccion.

Uso:
    python seed_centros_2018.py [--db exitpoll.db] [--csv centros_cne_2018.csv]
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

ELECCION_REF = "2018-presidencial"
FUENTE = "cne_directorio_2018"


def cargar(db_path: Path, csv_path: Path, *, dry_run: bool = False) -> dict:
    filas = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        previas = conn.execute(
            "SELECT COUNT(*) FROM centro_snapshot WHERE eleccion_ref=?", (ELECCION_REF,)
        ).fetchone()[0]

        conocidos = {
            r[0] for r in conn.execute("SELECT DISTINCT codigo_cne FROM centro_snapshot")
        }
        activos = {r[0] for r in conn.execute("SELECT codigo_cne FROM centros")}

        if not dry_run:
            conn.execute("DELETE FROM centro_snapshot WHERE eleccion_ref=?", (ELECCION_REF,))
            conn.executemany(
                """
                INSERT INTO centro_snapshot
                    (codigo_cne, eleccion_ref, nombre_centro, num_mesas, num_electores, fuente)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo_cne, eleccion_ref) DO UPDATE SET
                    nombre_centro=COALESCE(excluded.nombre_centro, centro_snapshot.nombre_centro),
                    num_mesas=excluded.num_mesas,
                    num_electores=excluded.num_electores,
                    fuente=excluded.fuente
                """,
                [
                    (
                        f["centro_cne_id"],
                        ELECCION_REF,
                        f["nombre_centro"] or None,
                        int(f["mesas"]),
                        int(f["electores"]),
                        FUENTE,
                    )
                    for f in filas
                ],
            )
            conn.commit()

        codigos = {f["centro_cne_id"] for f in filas}
        return {
            "filas_csv": len(filas),
            "snapshot_previo": previas,
            "electores": sum(int(f["electores"]) for f in filas),
            "mesas": sum(int(f["mesas"]) for f in filas),
            "nuevos_para_la_bd": len(codigos - conocidos - activos),
            "ya_en_snapshot": len(codigos & conocidos),
            "en_centros_activos": len(codigos & activos),
        }
    finally:
        conn.close()


def main() -> None:
    base = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=base / "exitpoll.db", type=Path)
    ap.add_argument("--csv", default=base / "centros_cne_2018.csv", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stats = cargar(args.db, args.csv, dry_run=args.dry_run)
    print(f"{'DRY-RUN' if args.dry_run else 'CARGADO'}: {ELECCION_REF} <- {args.csv.name}")
    for k, v in stats.items():
        print(f"  {k:22s} {v:>10,d}")


if __name__ == "__main__":
    main()
