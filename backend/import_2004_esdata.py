"""Build aggregated 2004 recall referendum results from archived Esdata pages.

This importer reads only aggregated voting-center pages from Wayback:
    http://www.esdata.info/centro/<codigo_viejo>

It explicitly ignores elector/person routes and writes a center-level CSV with
no personal data.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
OUT_PATH = BASE_DIR / "resultados_rr2004.csv"
CDX_URL = (
    "https://web.archive.org/cdx/search/cdx?"
    "url=esdata.info/centro/*&output=json&fl=timestamp,original,statuscode,mimetype,length"
    "&filter=statuscode:200&collapse=urlkey&limit=30000"
)

CENTER_RE = re.compile(r"https?://(?:www\.)?esdata\.info(?::80)?/centro/(\d+)/?$", re.I)


def fetch_text(url: str, timeout: int = 30, retries: int = 4, retry_sleep: float = 15.0) -> str:
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "exit-poll-historical-import/1.0"},
            )
            resp.raise_for_status()
            resp.encoding = resp.encoding or "utf-8"
            return resp.text
        except Exception as exc:
            last_exc = exc
            if attempt >= retries:
                break
            print(f"[warn] intento {attempt}/{retries} fallo para {url}: {exc}")
            time.sleep(retry_sleep * attempt)
    raise RuntimeError(f"No se pudo descargar {url}") from last_exc


def archived_url(timestamp: str, original: str) -> str:
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def parse_center_page(page: str) -> dict[str, object] | None:
    if "Refer" not in page or "Revocatorio" not in page:
        return None

    title_match = re.search(r"<span class=\"currentpage\">(.*?)</span>", page, re.S)
    centro_nombre = clean_text(title_match.group(1)) if title_match else ""

    viejo = re.search(r"C[oó]digo Viejo CNE:</strong>\s*([0-9]+)", page, re.I)
    nuevo = re.search(r"C[oó]digo Nuevo CNE:</strong>\s*([0-9]+)", page, re.I)
    if not viejo:
        viejo = re.search(r"C.{0,4}digo Viejo CNE:</strong>\s*([0-9]+)", page, re.I)
    if not nuevo:
        nuevo = re.search(r"C.{0,4}digo Nuevo CNE:</strong>\s*([0-9]+)", page, re.I)
    if not viejo or not nuevo:
        return None

    rr_block = re.search(
        r"Refer.*?Revocatorio Presidencial agosto 2004</h2>(.*?)</table>",
        page,
        re.S | re.I,
    )
    if not rr_block:
        return None

    block = rr_block.group(1)

    def row_int(label: str) -> int:
        m = re.search(rf"{label}</th>\s*<td[^>]*>([0-9.,]+)</td>", block, re.S | re.I)
        return int(float(m.group(1).replace(".", "").replace(",", "."))) if m else 0

    votos_si = row_int("Total Votos SI")
    votos_no = row_int("Total Votos NO")
    votos_nulos = row_int("Total Votos Nulos")
    total_votos = row_int("Total Votos")
    if total_votos <= 0:
        total_votos = votos_si + votos_no + votos_nulos

    rep_2004 = 0
    rep_match = re.search(
        r"<td>2004-07-01</td>\s*<td>Referendo Revocatorio</td>\s*"
        r"<td>([0-9]+)</td>\s*<td>([0-9]*)</td>\s*<td>([0-9]+)</td>",
        page,
        re.S,
    )
    if rep_match:
        rep_2004 = int(rep_match.group(3))

    tipo = ""
    tipo_match = re.search(r"Tipo de Centro</th>\s*<td colspan=\"2\">([^<]+)</td>", block, re.S | re.I)
    if tipo_match:
        tipo = clean_text(tipo_match.group(1))

    fuente_url = ""
    old_code = viejo.group(1)
    return {
        "codigo_centro": nuevo.group(1).zfill(9),
        "codigo_cne_nuevo": nuevo.group(1).zfill(9),
        "codigo_viejo": old_code,
        "codigo_cne_viejo": old_code,
        "nombre_centro": centro_nombre,
        "rep_2004": rep_2004,
        "votos_validos": votos_si + votos_no,
        "votos_gobierno": votos_no,
        "votos_oposicion": votos_si,
        "votos_otros": 0,
        "votos_nulos": votos_nulos,
        "total_votos": total_votos,
        "pct_gobierno": round(100 * votos_no / (votos_si + votos_no), 2) if (votos_si + votos_no) else 0,
        "pct_oposicion": round(100 * votos_si / (votos_si + votos_no), 2) if (votos_si + votos_no) else 0,
        "participacion": round(100 * total_votos / rep_2004, 2) if rep_2004 else 0,
        "tipo_centro": tipo,
        "fuente_url": fuente_url,
    }


def list_center_captures() -> list[tuple[str, str, str]]:
    data = json.loads(fetch_text(CDX_URL, timeout=60))
    captures = []
    for row in data[1:]:
        timestamp, original, status, mimetype, length = row
        m = CENTER_RE.match(original)
        if not m:
            continue
        captures.append((m.group(1), timestamp, original))
    captures.sort(key=lambda x: int(x[0]))
    return captures


def build_dataset(out_path: Path, limit: int | None = None, sleep_s: float = 0.05) -> dict[str, int]:
    captures = list_center_captures()
    if not captures:
        raise RuntimeError("Wayback no devolvio capturas de /centro/*. No se escribio el CSV.")
    if limit:
        captures = captures[:limit]

    rows: list[dict[str, object]] = []
    errors = 0
    for idx, (_old, timestamp, original) in enumerate(captures, 1):
        url = archived_url(timestamp, original)
        try:
            page = fetch_text(url)
            parsed = parse_center_page(page)
            if parsed:
                parsed["fuente_url"] = url
                rows.append(parsed)
        except Exception as exc:
            errors += 1
            print(f"[warn] {original}: {exc}")
        if idx % 250 == 0:
            print(f"[{idx}/{len(captures)}] centros leidos, {len(rows)} con RR2004")
        if sleep_s:
            time.sleep(sleep_s)

    if not rows:
        raise RuntimeError("No se parseo ningun centro RR2004. No se escribio el CSV.")

    fieldnames = [
        "codigo_centro", "codigo_cne_nuevo", "codigo_viejo", "codigo_cne_viejo",
        "nombre_centro", "rep_2004",
        "votos_validos", "votos_gobierno", "votos_oposicion", "votos_otros",
        "votos_nulos", "total_votos", "pct_gobierno", "pct_oposicion",
        "participacion", "tipo_centro", "fuente_url",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return {"capturas": len(captures), "filas": len(rows), "errores": errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT_PATH))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.05)
    args = parser.parse_args()

    stats = build_dataset(Path(args.out), limit=args.limit, sleep_s=args.sleep)
    print("Import 2004 Esdata:", stats)


if __name__ == "__main__":
    main()
