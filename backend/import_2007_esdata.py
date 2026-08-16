"""Build aggregated 2007 constitutional referendum results from Esdata/Wayback.

The 2007 referendum had two blocks (A and B). The source includes table-level
results for both blocks plus a sheet of tables missing from the CNE first
bulletin. This importer stores one center-level trend record by averaging the
two block valid-vote volumes and using the combined SI/NO ratio across blocks.
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
OUT_PATH = BASE_DIR / "resultados_ref2007.csv"
SOURCE_URL = (
    "https://web.archive.org/web/20101006101346id_/"
    "http://esdata.info/resultados/resultados_elecc_2007.xls.zip"
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


def _header_row(path: Path, sheet: str) -> int:
    raw = pd.read_excel(path, sheet_name=sheet, header=None, nrows=12)
    for idx, row in raw.iterrows():
        values = {str(v).strip() for v in row.tolist() if pd.notna(v)}
        if "cod_estado" in values and "mesa" in values:
            return int(idx)
    raise ValueError(f"No se encontro encabezado en hoja {sheet}.")


def _load_sheet(path: Path, sheet: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet, header=_header_row(path, sheet))
    df.columns = [str(col).strip() for col in df.columns]
    return df.dropna(how="all")


def _center_item(by_center: dict[str, dict[str, object]], row: pd.Series) -> dict[str, object] | None:
    codigo = _code9(row.get("cod_centro_nuevo"))
    if not codigo:
        return None
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
            "num_mesas_escrutadas": set(),
            "num_mesas_sin_resultado": set(),
            "a_si": 0,
            "a_no": 0,
            "b_si": 0,
            "b_no": 0,
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
    return item


def build_dataset(out_path: Path, source_zip: Path | None = None) -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="exitpoll_ref2007_") as tmp_name:
        tmp = Path(tmp_name)
        zip_path = source_zip or (tmp / "resultados_elecc_2007.xls.zip")
        if source_zip is None:
            _download(SOURCE_URL, zip_path)
        xls_path = _source_xls_from_zip(zip_path, tmp)

        con_resultado = _load_sheet(xls_path, "Mesas con Resultado")
        sin_resultado = _load_sheet(xls_path, "Mesas sin Resultado")

        by_center: dict[str, dict[str, object]] = {}
        for _, row in con_resultado.iterrows():
            item = _center_item(by_center, row)
            if item is None:
                continue
            mesa = _code_raw(row.get("mesa"))
            if mesa:
                item["num_mesas_escrutadas"].add(mesa)
            item["a_si"] = int(item["a_si"]) + int(_number(row.get("votos_A_si")))
            item["a_no"] = int(item["a_no"]) + int(_number(row.get("votos_A_no")))
            item["b_si"] = int(item["b_si"]) + int(_number(row.get("votos_B_si")))
            item["b_no"] = int(item["b_no"]) + int(_number(row.get("votos_B_no")))

        for _, row in sin_resultado.iterrows():
            item = _center_item(by_center, row)
            if item is None:
                continue
            mesa = _code_raw(row.get("mesa"))
            if mesa:
                item["num_mesas_sin_resultado"].add(mesa)

        fieldnames = [
            "codigo_centro",
            "codigo_cne_nuevo",
            "codigo_viejo",
            "codigo_cne_viejo",
            "nombre_centro",
            "num_electores",
            "num_mesas",
            "num_mesas_escrutadas",
            "num_mesas_sin_resultado",
            "votos_validos",
            "votos_gobierno",
            "votos_oposicion",
            "votos_otros",
            "votos_bloques_validos",
            "votos_A_si",
            "votos_A_no",
            "votos_B_si",
            "votos_B_no",
            "pct_gobierno",
            "pct_oposicion",
            "fuente_url",
        ]
        pii = sorted(set(fieldnames) & FORBIDDEN_OUTPUT_COLUMNS)
        if pii:
            raise ValueError(f"Columnas PII no permitidas en salida: {', '.join(pii)}")

        out_rows: list[dict[str, object]] = []
        for item in by_center.values():
            a_si = int(item["a_si"])
            a_no = int(item["a_no"])
            b_si = int(item["b_si"])
            b_no = int(item["b_no"])
            bloques_validos = a_si + a_no + b_si + b_no
            if bloques_validos <= 0:
                continue
            pct_gob = (a_si + b_si) / bloques_validos
            validos_a = a_si + a_no
            validos_b = b_si + b_no
            validos = int(round((validos_a + validos_b) / 2))
            gobierno = int(round(validos * pct_gob))
            oposicion = max(0, validos - gobierno)
            out_rows.append({
                "codigo_centro": item["codigo_centro"],
                "codigo_cne_nuevo": item["codigo_cne_nuevo"],
                "codigo_viejo": item["codigo_viejo"],
                "codigo_cne_viejo": item["codigo_cne_viejo"],
                "nombre_centro": item["nombre_centro"],
                "num_electores": int(item["num_electores"]),
                "num_mesas": len(item["num_mesas"]),
                "num_mesas_escrutadas": len(item["num_mesas_escrutadas"]),
                "num_mesas_sin_resultado": len(item["num_mesas_sin_resultado"]),
                "votos_validos": validos,
                "votos_gobierno": gobierno,
                "votos_oposicion": oposicion,
                "votos_otros": 0,
                "votos_bloques_validos": bloques_validos,
                "votos_A_si": a_si,
                "votos_A_no": a_no,
                "votos_B_si": b_si,
                "votos_B_no": b_no,
                "pct_gobierno": round(100 * gobierno / validos, 2) if validos else 0,
                "pct_oposicion": round(100 * oposicion / validos, 2) if validos else 0,
                "fuente_url": SOURCE_URL,
            })

        out_rows.sort(key=lambda r: str(r["codigo_centro"]))
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(out_rows)

        return {
            "mesas_con_resultado": len(con_resultado),
            "mesas_sin_resultado": len(sin_resultado),
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
    print("Import 2007 Esdata:", stats)


if __name__ == "__main__":
    main()
