"""Build aggregated 2009 constitutional amendment results from Esdata/Wayback.

The source file is a table-level election result archive. This importer writes
only voting-center aggregates and drops all columns not needed for historical
trend analysis.
"""

from __future__ import annotations

import argparse
import csv
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUT_PATH = BASE_DIR / "resultados_enmienda2009.csv"
SOURCE_URL = (
    "https://web.archive.org/web/20101006061251id_/"
    "http://esdata.info/resultados/ENMIENDA2009_2boletin.xls.zip"
)

FORBIDDEN_OUTPUT_COLUMNS = {
    "cedula",
    "ci",
    "nacionalidad",
    "nombre",
    "nombres",
    "apellido",
    "apellidos",
    "telefono",
    "direccion_habitacion",
    "fecha_nacimiento",
    "elector",
}


def _download(url: str, out_path: Path) -> None:
    req = Request(url, headers={"User-Agent": "exit-poll-historical-import/1.0"})
    with urlopen(req, timeout=90) as resp, out_path.open("wb") as fh:
        fh.write(resp.read())


def _number(value: object) -> float:
    if value is None:
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
    except TypeError:
        pass
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return 0.0


def _code9(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits.zfill(9) if digits else ""


def _code_raw(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return "".join(ch for ch in text if ch.isdigit())


def _source_xls_from_zip(zip_path: Path, work_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path) as zf:
        members = [
            name for name in zf.namelist()
            if name.lower().endswith(".xls") and not name.startswith("__MACOSX/")
        ]
        if not members:
            raise RuntimeError(f"{zip_path.name} no contiene un .xls util.")
        return Path(zf.extract(members[0], work_dir))


def _load_source(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = [str(col).strip() for col in df.columns]
    required = {
        "cod_centro_nuevo",
        "cod_centro_viejo",
        "centro",
        "mesa",
        "electores",
        "votos_si",
        "votos_no",
        "votos_nulos_cne",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Faltan columnas esperadas: {', '.join(missing)}")
    return df


def build_dataset(out_path: Path, source_zip: Path | None = None) -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="exitpoll_enmienda2009_") as tmp_name:
        tmp = Path(tmp_name)
        zip_path = source_zip or (tmp / "ENMIENDA2009_2boletin.xls.zip")
        if source_zip is None:
            _download(SOURCE_URL, zip_path)
        xls_path = _source_xls_from_zip(zip_path, tmp)
        df = _load_source(xls_path)

        by_center: dict[str, dict[str, object]] = {}
        rows_with_votes = 0
        for _, row in df.iterrows():
            codigo = _code9(row.get("cod_centro_nuevo"))
            if not codigo:
                continue
            votos_si = int(_number(row.get("votos_si")))
            votos_no = int(_number(row.get("votos_no")))
            votos_nulos = int(_number(row.get("votos_nulos_cne")))
            if votos_si or votos_no:
                rows_with_votes += 1

            item = by_center.setdefault(
                codigo,
                {
                    "codigo_centro": codigo,
                    "codigo_cne_nuevo": codigo,
                    "codigo_viejo": "",
                    "codigo_cne_viejo": "",
                    "nombre_centro": "",
                    "num_electores": 0,
                    "num_mesas": set(),
                    "votos_gobierno": 0,
                    "votos_oposicion": 0,
                    "votos_nulos": 0,
                },
            )
            codigo_viejo = _code_raw(row.get("cod_centro_viejo"))
            if codigo_viejo and not item["codigo_viejo"]:
                item["codigo_viejo"] = codigo_viejo
                item["codigo_cne_viejo"] = codigo_viejo
            if not item["nombre_centro"]:
                item["nombre_centro"] = str(row.get("centro") or "").strip()
            mesa = _code_raw(row.get("mesa"))
            if mesa:
                item["num_mesas"].add(mesa)
            item["num_electores"] = int(item["num_electores"]) + int(_number(row.get("electores")))
            # En la enmienda 2009, SI apoyaba la propuesta del gobierno; NO era oposicion.
            item["votos_gobierno"] = int(item["votos_gobierno"]) + votos_si
            item["votos_oposicion"] = int(item["votos_oposicion"]) + votos_no
            item["votos_nulos"] = int(item["votos_nulos"]) + votos_nulos

        fieldnames = [
            "codigo_centro",
            "codigo_cne_nuevo",
            "codigo_viejo",
            "codigo_cne_viejo",
            "nombre_centro",
            "num_electores",
            "num_mesas",
            "votos_validos",
            "votos_gobierno",
            "votos_oposicion",
            "votos_otros",
            "votos_nulos",
            "total_votos",
            "pct_gobierno",
            "pct_oposicion",
            "participacion",
            "fuente_url",
        ]
        pii = sorted(set(fieldnames) & FORBIDDEN_OUTPUT_COLUMNS)
        if pii:
            raise ValueError(f"Columnas PII no permitidas en salida: {', '.join(pii)}")

        out_rows: list[dict[str, object]] = []
        for item in by_center.values():
            gobierno = int(item["votos_gobierno"])
            oposicion = int(item["votos_oposicion"])
            validos = gobierno + oposicion
            if validos <= 0:
                continue
            nulos = int(item["votos_nulos"])
            electores = int(item["num_electores"])
            total = validos + nulos
            out_rows.append({
                "codigo_centro": item["codigo_centro"],
                "codigo_cne_nuevo": item["codigo_cne_nuevo"],
                "codigo_viejo": item["codigo_viejo"],
                "codigo_cne_viejo": item["codigo_cne_viejo"],
                "nombre_centro": item["nombre_centro"],
                "num_electores": electores,
                "num_mesas": len(item["num_mesas"]),
                "votos_validos": validos,
                "votos_gobierno": gobierno,
                "votos_oposicion": oposicion,
                "votos_otros": 0,
                "votos_nulos": nulos,
                "total_votos": total,
                "pct_gobierno": round(100 * gobierno / validos, 2),
                "pct_oposicion": round(100 * oposicion / validos, 2),
                "participacion": round(100 * total / electores, 2) if electores else 0,
                "fuente_url": SOURCE_URL,
            })

        out_rows.sort(key=lambda r: str(r["codigo_centro"]))
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(out_rows)

        return {
            "filas_mesa_fuente": len(df),
            "mesas_con_votos": rows_with_votes,
            "centros_fuente": len(by_center),
            "centros_exportados": len(out_rows),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT_PATH))
    parser.add_argument("--source-zip", default="")
    args = parser.parse_args()

    stats = build_dataset(
        Path(args.out),
        source_zip=Path(args.source_zip) if args.source_zip else None,
    )
    print("Import 2009 Esdata:", stats)


if __name__ == "__main__":
    main()
