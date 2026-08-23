"""Normaliza e importa Presidencial 2018 desde VENPRES-A.

Fuente primaria de esta normalizacion:
    The Venezuelan Presidential Election Archive (VENPRES-A)
    DOI: 10.7910/DVN/NO1XJ2

El XLSX fuente `Elecciones_Centros_2006_2021.xlsx` contiene una fila agregada
por centro para 2018. La columna `mesas` es cantidad de mesas del centro, no
identificador de mesa.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path

import pandas as pd

try:
    from historico_normalizacion import ensure_historico_normalizado_schema
except ImportError:  # pragma: no cover - package import path
    from .historico_normalizacion import ensure_historico_normalizado_schema


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "exitpoll.db"
DEFAULT_SOURCE = BASE_DIR / "data" / "2018" / "Elecciones_Centros_2006_2021.xlsx"
DEFAULT_OUTPUT = BASE_DIR / "data" / "2018" / "resultados_venpres_a_2018.csv"
ELECCION_REF = "2018-presidencial"
FUENTE = "venpres_a"
DOI = "10.7910/DVN/NO1XJ2"


def _int(value: object) -> int:
    try:
        if pd.isna(value):
            return 0
    except TypeError:
        pass
    if value in (None, ""):
        return 0
    return int(float(str(value).strip()))


def _code9(value: object) -> str:
    digits = "".join(ch for ch in str(value or "").strip().split(".")[0] if ch.isdigit())
    return digits.zfill(9) if digits else ""


def build_normalized_rows(source_path: Path) -> list[dict[str, object]]:
    if not source_path.exists():
        raise FileNotFoundError(f"No existe fuente VENPRES-A: {source_path}")
    if source_path.suffix.lower() in {".csv", ".tab", ".tsv"}:
        df = pd.read_csv(source_path, sep="\t" if source_path.suffix.lower() in {".tab", ".tsv"} else ",")
        if "year" in df.columns:
            df = df[df["year"].astype(str).str[:4] == "2018"].copy()
            df = df.rename(columns={"validos": "voto_c", "nulos": "nulo_c", "mesa": "mesas"})
            # El TAB publico ya trae Falcon agregado dentro de otro_c; no permite
            # separar oposicion 2018 sin el XLSX fuente.
            if "ppt_c" not in df.columns:
                raise ValueError("Use el XLSX VENPRES-A para 2018; el TAB no separa Falcon de Bertucci+Quijada.")
    else:
        df = pd.read_excel(source_path)
        df = df[df["eleccion"].astype(str).eq("201801")].copy()

    rows: list[dict[str, object]] = []
    for _, row in df.iterrows():
        codigo = _code9(row.get("centro"))
        if not codigo:
            continue
        gobierno = _int(row.get("of_c"))
        oposicion = _int(row.get("ppt_c"))
        otros = _int(row.get("ot_c"))
        nulos = _int(row.get("nulo_c"))
        validos = gobierno + oposicion + otros
        electores = _int(row.get("rep_c"))
        votantes = _int(row.get("voto_c")) or (validos + nulos if validos or nulos else _int(row.get("totales_c")))
        mesas = _int(row.get("mesas"))
        if validos <= 0:
            continue
        detalle = {"falcon": oposicion, "bertucci_quijada": otros}
        rows.append(
            {
                "codigo_centro": codigo,
                "codigo_cne_original": str(row.get("centro") or "").split(".")[0],
                "nombre_centro": str(row.get("nombre_centro") or "").strip(),
                "estado": str(row.get("estado") or "").strip(),
                "municipio": str(row.get("Municipio") or row.get("municipio") or "").strip(),
                "parroquia": str(row.get("Parroquia") or row.get("parroquia") or "").strip(),
                "num_mesas": mesas,
                "electores_inscritos": electores,
                "votantes": votantes,
                "votos_validos": validos,
                "votos_nulos": nulos,
                "votos_gobierno": gobierno,
                "votos_oposicion": oposicion,
                "votos_otros": otros,
                "votos_falcon": oposicion,
                "votos_bertucci_quijada": otros,
                "pct_gobierno": round(100 * gobierno / validos, 6),
                "pct_oposicion": round(100 * oposicion / validos, 6),
                "pct_otros": round(100 * otros / validos, 6),
                "participacion": round(100 * votantes / electores, 6) if electores else "",
                "detalle_otros_json": json.dumps(detalle, sort_keys=True, separators=(",", ":")),
                "fuente": FUENTE,
                "doi": DOI,
                "corte_fuente": "VENPRES-A v1.1; voto_c tratado como votantes y validos recalculados desde candidatos",
            }
        )
    rows.sort(key=lambda r: str(r["codigo_centro"]))
    return rows


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def import_csv(db_path: Path, csv_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_historico_normalizado_schema(conn)
        conn.execute("DELETE FROM resultados_historicos WHERE eleccion_ref=?", (ELECCION_REF,))
        conn.execute("DELETE FROM centro_snapshot WHERE eleccion_ref=?", (ELECCION_REF,))
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        for row in rows:
            validos = _int(row["votos_validos"])
            gobierno = _int(row["votos_gobierno"])
            oposicion = _int(row["votos_oposicion"])
            otros = _int(row["votos_otros"])
            nulos = _int(row["votos_nulos"])
            electores = _int(row["electores_inscritos"])
            votantes = _int(row["votantes"])
            conn.execute(
                """
                INSERT INTO resultados_historicos
                    (codigo_centro, eleccion_ref, votos_validos, votos_gobierno,
                     votos_oposicion, votos_otros, electores_inscritos, votantes,
                     votos_nulos, pct_gobierno, pct_oposicion, pct_otros,
                     participacion, incluye_exterior, granularidad, fuente,
                     corte_fuente, notas, num_mesas, detalle_otros_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'centro', ?, ?, ?, ?, ?)
                ON CONFLICT(codigo_centro, eleccion_ref) DO UPDATE SET
                    votos_validos=excluded.votos_validos,
                    votos_gobierno=excluded.votos_gobierno,
                    votos_oposicion=excluded.votos_oposicion,
                    votos_otros=excluded.votos_otros,
                    electores_inscritos=excluded.electores_inscritos,
                    votantes=excluded.votantes,
                    votos_nulos=excluded.votos_nulos,
                    pct_gobierno=excluded.pct_gobierno,
                    pct_oposicion=excluded.pct_oposicion,
                    pct_otros=excluded.pct_otros,
                    participacion=excluded.participacion,
                    incluye_exterior=excluded.incluye_exterior,
                    granularidad=excluded.granularidad,
                    fuente=excluded.fuente,
                    corte_fuente=excluded.corte_fuente,
                    notas=excluded.notas,
                    num_mesas=excluded.num_mesas,
                    detalle_otros_json=excluded.detalle_otros_json
                """,
                (
                    row["codigo_centro"],
                    ELECCION_REF,
                    validos,
                    gobierno,
                    oposicion,
                    otros,
                    electores,
                    votantes,
                    nulos,
                    float(row["pct_gobierno"]),
                    float(row["pct_oposicion"]),
                    float(row["pct_otros"]),
                    float(row["participacion"]) if row["participacion"] else None,
                    FUENTE,
                    row["corte_fuente"],
                f"DOI {DOI}; Falcon se conserva como oposicion; Bertucci+Quijada como otros; votos_validos recalculados desde candidatos.",
                    _int(row["num_mesas"]),
                    row["detalle_otros_json"],
                ),
            )
            conn.execute(
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
                (
                    row["codigo_centro"],
                    ELECCION_REF,
                    row["nombre_centro"] or None,
                    _int(row["num_mesas"]),
                    electores,
                    FUENTE,
                ),
            )
        totals = {
            "centros": len(rows),
            "mesas": sum(_int(r["num_mesas"]) for r in rows),
            "electores": sum(_int(r["electores_inscritos"]) for r in rows),
            "votantes": sum(_int(r["votantes"]) for r in rows),
            "validos": sum(_int(r["votos_validos"]) for r in rows),
            "nulos": sum(_int(r["votos_nulos"]) for r in rows),
            "gobierno": sum(_int(r["votos_gobierno"]) for r in rows),
            "oposicion": sum(_int(r["votos_oposicion"]) for r in rows),
            "otros": sum(_int(r["votos_otros"]) for r in rows),
        }
        conn.execute(
            """
            INSERT INTO historico_fuentes
                (eleccion_ref, fuente, granularidad, cobertura_pct, comparabilidad,
                 notas, incluye_exterior, corte_fuente, centros_cubiertos,
                 mesas_cubiertas, electores_inscritos, votantes, votos_validos,
                 votos_nulos, votos_gobierno, votos_oposicion, votos_otros)
            VALUES (?, ?, 'centro', 98.37, 'provisional_arqueologica', ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(eleccion_ref) DO UPDATE SET
                fuente=excluded.fuente,
                granularidad=excluded.granularidad,
                cobertura_pct=excluded.cobertura_pct,
                comparabilidad=excluded.comparabilidad,
                notas=excluded.notas,
                incluye_exterior=excluded.incluye_exterior,
                corte_fuente=excluded.corte_fuente,
                centros_cubiertos=excluded.centros_cubiertos,
                mesas_cubiertas=excluded.mesas_cubiertas,
                electores_inscritos=excluded.electores_inscritos,
                votantes=excluded.votantes,
                votos_validos=excluded.votos_validos,
                votos_nulos=excluded.votos_nulos,
                votos_gobierno=excluded.votos_gobierno,
                votos_oposicion=excluded.votos_oposicion,
                votos_otros=excluded.votos_otros,
                updated_at=datetime('now')
            """,
            (
                ELECCION_REF,
                FUENTE,
                f"DOI {DOI}; cobertura domestica por centro; no incluye exterior.",
                "VENPRES-A v1.1; 14.400 centros domesticos agregados",
                totals["centros"],
                totals["mesas"],
                totals["electores"],
                totals["votantes"],
                totals["validos"],
                totals["nulos"],
                totals["gobierno"],
                totals["oposicion"],
                totals["otros"],
            ),
        )
        conn.commit()
        return totals
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("--import-db", action="store_true")
    args = ap.parse_args()

    rows = build_normalized_rows(args.source)
    write_csv(rows, args.output)
    print(f"CSV normalizado: {args.output} ({len(rows):,} centros)")
    totals = {
        "mesas": sum(_int(r["num_mesas"]) for r in rows),
        "electores": sum(_int(r["electores_inscritos"]) for r in rows),
        "votantes": sum(_int(r["votantes"]) for r in rows),
        "validos": sum(_int(r["votos_validos"]) for r in rows),
        "nulos": sum(_int(r["votos_nulos"]) for r in rows),
        "gobierno": sum(_int(r["votos_gobierno"]) for r in rows),
        "oposicion": sum(_int(r["votos_oposicion"]) for r in rows),
        "otros": sum(_int(r["votos_otros"]) for r in rows),
    }
    for key, value in totals.items():
        print(f"  {key:12s} {value:>12,}")
    if args.import_db:
        imported = import_csv(args.db, args.output)
        print("Importado en DB:")
        for key, value in imported.items():
            print(f"  {key:12s} {value:>12,}")


if __name__ == "__main__":
    main()
