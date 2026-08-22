"""Repara nombres y direcciones con doble-encoding UTF-8 en la base.

El dano tipico es texto UTF-8 que fue leido como cp1252/latin-1 en alguna
importacion previa: "SIMON BOLIVAR" quedo guardado como "SIMÃ“N BOLÃVAR".
Eso rompe la busqueda por nombre en el laboratorio de muestra.

Tres estrategias, en orden:
  1. Re-encode determinista, caracter a caracter (ver _a_bytes).
  2. Respaldo desde centros_cne_2018.csv (Directorio de Centros de Votacion
     del CNE, con los nombres y direcciones limpios) cuando el byte original
     se perdio y el re-encode ya no puede recuperarlo.
  3. Correccion del dano posterior de un upper() sobre el texto ya danado,
     que deja acentos graves y Ê donde iban agudos (ver reparar_post_upper).

Es idempotente: volver a correrlo sobre una base limpia no cambia nada.

Uso:
    python reparar_encoding.py --dry-run
    python reparar_encoding.py
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from pathlib import Path

MOJIBAKE = re.compile(r"Ã.|Â.|â€")

# (tabla, columna_texto, columna_clave, campo_respaldo_en_csv_2018)
OBJETIVOS = [
    ("centros", "nombre", "codigo_cne", "nombre_centro"),
    ("centros", "direccion", "codigo_cne", "direccion"),
    ("centro_snapshot", "nombre_centro", "codigo_cne", "nombre_centro"),
    ("parroquias", "nombre", "id", None),
    ("municipios", "nombre", "id", None),
]


def tiene_mojibake(texto: str | None) -> bool:
    return bool(texto) and bool(MOJIBAKE.search(texto))


def _a_bytes(texto: str) -> bytes | None:
    """Recupera los bytes originales caracter a caracter.

    Una sola tabla no basta: cp1252 no puede codificar 0x81/0x8D (huecos) y
    latin-1 no tiene los caracteres tipograficos de cp1252 (U+201C, U+2018...).
    Un mismo texto danado suele mezclar ambos, asi que se elige por caracter.
    """
    salida = bytearray()
    for ch in texto:
        for codec in ("cp1252", "latin-1"):
            try:
                salida.extend(ch.encode(codec))
                break
            except UnicodeEncodeError:
                continue
        else:
            return None
    return bytes(salida)


def reparar_texto(texto: str) -> str | None:
    """Revierte el doble-encoding. Devuelve None si no es recuperable."""
    crudo = _a_bytes(texto)
    if crudo is None:
        return None
    try:
        candidato = crudo.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # el mojibake siempre expande bytes: la reparacion no puede crecer
    if tiene_mojibake(candidato) or len(candidato) > len(texto):
        return None
    return candidato


def cargar_respaldo(csv_path: Path) -> dict[str, dict[str, str]]:
    if not csv_path.exists():
        return {}
    return {
        f["centro_cne_id"]: f
        for f in csv.DictReader(csv_path.open(encoding="utf-8"))
    }


def reparar_post_upper(conn, respaldo: dict[str, dict[str, str]], *, dry_run: bool) -> dict:
    """Corrige el dano de un upper() aplicado sobre texto ya danado.

    En cp1252 las vocales acentuadas altas viajaban como minusculas: U+009A
    ('s' caron) para Ú y U+009C ('oe') para Ü. Al pasar el texto por upper()
    se volvieron U+008A y U+008C, que al decodificar dan Ê y Ì. Resultado:
    "JESÚS" quedo como "JESÊS" y "GÜIRIA" como "GÌIRIA".

    Ê -> Ú es determinista (Ê no se usa en espanol). Lo mismo vale para las
    vocales con acento grave (À È Ì Ò Ù): el espanol no las usa nunca, siempre
    son el agudo correspondiente ("RAMÒN" por RAMÓN, "ELÌAS" por ELÍAS).

    El unico caso genuinamente ambiguo es Ì, que ademas puede venir de Ü
    (AGÜERO, GÜIRIA). Por eso se consulta primero el Directorio de Centros 2018:
    si tiene el nombre oficial limpio se usa ese, y solo si no esta se aplica
    la regla.
    """
    graves = {"Ê": "Ú", "À": "Á", "È": "É", "Ì": "Í", "Ò": "Ó", "Ù": "Ú"}
    stats = {"por_regla": 0, "por_csv2018": 0, "pendientes": 0}
    objetivos = [
        ("centros", "nombre", "codigo_cne", "nombre_centro"),
        ("centros", "direccion", "codigo_cne", "direccion"),
        ("centro_snapshot", "nombre_centro", "codigo_cne", "nombre_centro"),
        ("parroquias", "nombre", "id", None),
        ("municipios", "nombre", "id", None),
    ]
    for tabla, col, clave, campo_csv in objetivos:
        cambios = []
        filas = conn.execute(
            f'SELECT rowid AS rid, "{clave}" AS clave, "{col}" AS valor FROM "{tabla}"'
        ).fetchall()
        for f in filas:
            valor = f["valor"] or ""
            if not any(ch in valor for ch in graves):
                continue
            oficial = (respaldo.get(str(f["clave"])) or {}).get(campo_csv) if campo_csv else None
            if oficial and not any(ch in oficial for ch in graves):
                if oficial != valor:
                    cambios.append((oficial, f["rid"]))
                    stats["por_csv2018"] += 1
                continue
            nuevo = valor
            for danado, limpio in graves.items():
                nuevo = nuevo.replace(danado, limpio)
            if nuevo != valor:
                cambios.append((nuevo, f["rid"]))
                stats["por_regla"] += 1
            else:
                stats["pendientes"] += 1
        if cambios and not dry_run:
            conn.executemany(f'UPDATE "{tabla}" SET "{col}"=? WHERE rowid=?', cambios)
            conn.commit()
    return stats


def procesar(db_path: Path, csv_path: Path, *, dry_run: bool) -> None:
    respaldo = cargar_respaldo(csv_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    total = {"reencode": 0, "csv2018": 0, "irreparable": 0}

    try:
        for tabla, col, clave, campo_csv in OBJETIVOS:
            filas = conn.execute(
                f'SELECT rowid AS rid, "{clave}" AS clave, "{col}" AS valor FROM "{tabla}"'
            ).fetchall()
            danadas = [f for f in filas if tiene_mojibake(f["valor"])]
            if not danadas:
                continue

            cambios, por_csv, irreparables = [], 0, []
            for f in danadas:
                nuevo = reparar_texto(f["valor"])
                if nuevo is None and campo_csv and respaldo:
                    alterno = (respaldo.get(str(f["clave"])) or {}).get(campo_csv)
                    if alterno and not tiene_mojibake(alterno):
                        nuevo, por_csv = alterno, por_csv + 1
                if nuevo is None:
                    irreparables.append(f["valor"])
                else:
                    cambios.append((nuevo, f["rid"]))

            if not dry_run and cambios:
                conn.executemany(
                    f'UPDATE "{tabla}" SET "{col}"=? WHERE rowid=?', cambios
                )
                conn.commit()

            total["reencode"] += len(cambios) - por_csv
            total["csv2018"] += por_csv
            total["irreparable"] += len(irreparables)
            print(
                f'  {tabla}.{col:14s} danadas {len(danadas):>6,d} | '
                f'reparadas {len(cambios):>6,d} (re-encode {len(cambios)-por_csv:,}, '
                f'csv2018 {por_csv:,}) | sin arreglo {len(irreparables):,}'
            )
            for texto in irreparables[:3]:
                print(f"      ! {texto[:70]}")

        post = reparar_post_upper(conn, respaldo, dry_run=dry_run)
        print(f'  post-upper: por regla {post["por_regla"]:,} | '
              f'por csv2018 {post["por_csv2018"]:,} | '
              f'pendientes {post["pendientes"]:,}')
    finally:
        conn.close()

    print()
    print(f"{'DRY-RUN (no se escribio)' if dry_run else 'APLICADO'}: "
          f"re-encode {total['reencode']:,} | csv2018 {total['csv2018']:,} | "
          f"irreparables {total['irreparable']:,}")


def main() -> None:
    base = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=base / "exitpoll.db", type=Path)
    ap.add_argument("--csv", default=base / "centros_cne_2018.csv", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    procesar(args.db, args.csv, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
