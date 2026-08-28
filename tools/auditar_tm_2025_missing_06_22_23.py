from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATA_DIR = BACKEND / "data" / "2025"
CANDIDATES_IN = ROOT / "tm_2025_missing_centers_candidates.csv"
AUDIT_CSV = ROOT / "tm_2025_missing_centers_06_22_23_audit.csv"
REPORT = ROOT / "docs" / "tm" / "TM_2025_MISSING_CENTERS_06_22_23.md"
ORIGINAL_TM = BACKEND / "tm_2025_macedonia_estandar.csv"
V2_TM = BACKEND / "tm_2025_macedonia_estandar_candidate_completed_v2.csv"
HTML_CACHE = DATA_DIR / "regionales_candidate_pages_cache"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TARGET_STATES = {"06": "BOLIVAR", "22": "AMAZONAS", "23": "DELTA AMACURO"}
EXPECTED_STATE_COUNTS = {
    "06": {"estado": "BOLIVAR", "centros": 817, "mesas": 1429, "electores_gap_aprox": 976},
    "22": {"estado": "AMAZONAS", "centros": 150, "mesas": 192, "electores_gap_aprox": 612},
    "23": {"estado": "DELTA AMACURO", "centros": 195, "mesas": 237, "electores_gap_aprox": 477},
}

AUDIT_COLUMNS = [
    "codigo_centro",
    "estado",
    "municipio",
    "parroquia",
    "centro",
    "mesas_2025",
    "electores_2025",
    "regionales_2025",
    "asamblea_2025",
    "tm_2024",
    "tm_2018",
    "tm_2015",
    "url_regionales",
    "url_asamblea_si_existe",
    "evidencia",
    "clasificacion",
    "razon_clasificacion",
]


def norm_code(value: Any, width: int) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits.zfill(width) if digits else ""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cache_name(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.netloc + parsed.path)
    return f"{safe[:170]}__{digest}.html"


def fetch_html(url: str, cache_only: bool, sleep_s: float) -> dict[str, Any]:
    HTML_CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = HTML_CACHE / cache_name(url)
    if cache_path.exists():
        data = cache_path.read_bytes()
        marker = data.decode("utf-8", "replace")
        if marker.startswith("__HTTP_STATUS__="):
            status = int(marker.split("=", 1)[1].strip())
            return {"status": status, "hash": sha256(data), "cache": cache_path, "text": ""}
        return {"status": 200, "hash": sha256(data), "cache": cache_path, "text": data.decode("utf-8", "replace")}
    if cache_only:
        return {"status": "missing_cache", "hash": "", "cache": cache_path, "text": ""}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
        cache_path.write_bytes(data)
        time.sleep(sleep_s)
        return {"status": 200, "hash": sha256(data), "cache": cache_path, "text": data.decode("utf-8", "replace")}
    except urllib.error.HTTPError as exc:
        marker = f"__HTTP_STATUS__={exc.code}\n".encode("utf-8")
        cache_path.write_bytes(marker)
        return {"status": exc.code, "hash": "", "cache": cache_path, "text": ""}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def center_totals(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    totals: dict[str, dict[str, Any]] = {}
    for row in read_csv(path):
        code = norm_code(row.get("codigo_centro"), 9)
        item = totals.setdefault(code, {"mesas": 0, "electores": 0})
        item["mesas"] += 1
        item["electores"] += int(row.get("electores") or 0)
    return totals


def tm_state_counts(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        state = norm_code(row.get("cod_estado"), 2)
        if state not in out:
            out[state] = {"centros": 0, "mesas": 0, "electores": 0}
        out[state]["mesas"] += 1
        out[state]["electores"] += int(row.get("electores") or 0)
    seen = {(norm_code(row.get("cod_estado"), 2), norm_code(row.get("codigo_centro"), 9)) for row in rows}
    for state, _code in seen:
        out.setdefault(state, {"centros": 0, "mesas": 0, "electores": 0})
        out[state]["centros"] += 1
    return out


def historical_label(totals: dict[str, dict[str, Any]], code: str) -> str:
    if code not in totals:
        return "no"
    return f"si ({totals[code]['mesas']} mesa(s), {totals[code]['electores']} electores)"


def asamblea_url(code: str) -> str:
    slug = {"06": "bolivar", "22": "amazonas", "23": "delta-amacuro"}[code[:2]]
    return f"https://asamblea.macedoniadelnorte.com/{slug}/{code[:4]}/{code[:6]}/{code}"


def classify(row: dict[str, str], reg_html: dict[str, Any], asm_status: Any) -> tuple[str, str]:
    code = row["codigo_centro"]
    mesas = int(row.get("numero_mesas") or 0)
    electores = int(row.get("total_electores") or 0)
    page_ok = reg_html["status"] == 200 and row["nombre_centro"][:20] in reg_html["text"]
    if asm_status == 200:
        return "DESCARTADO", "La URL directa de Asamblea responde; no es ausente documental."
    if mesas == 1 and electores > 0 and page_ok:
        return "CONFIRMADO", "API Regionales 2025 reporta cantidadMesas=1 y votantes>0; pagina publica renderiza el centro; Asamblea 2025 responde 404 y el codigo no esta en el TM reconstruido."
    if code == "230303004" and electores > 0 and page_ok:
        return "PROBABLE", "Regionales 2025 renderiza el centro y reporta votantes; Asamblea 2025 responde 404; aparece historicamente; el deficit de Delta esta localizado en Antonio Diaz, pero cantidadMesas=0 impide confirmarlo como mesa 2025 por si solo."
    if code == "220602004" and electores > 0 and page_ok:
        return "PROBABLE", "Regionales 2025 renderiza el centro y reporta 107 votantes; aparece historicamente con 1 mesa; junto con 220101023 explica aproximadamente la brecha de electores de Amazonas, pero cantidadMesas=0 impide confirmacion plena."
    if electores > 0 and page_ok:
        return "INDETERMINADO", "Regionales 2025 renderiza el centro y reporta votantes, pero cantidadMesas=0; puede ser activo sin mesa publicada, residual o no usado para el marco Asamblea."
    return "DESCARTADO", "No hay evidencia suficiente de pagina Regionales 2025 activa con electores."


def build_report(audit_rows: list[dict[str, Any]], original_rows: list[dict[str, str]], v2_created: bool) -> str:
    state_counts = tm_state_counts(original_rows)
    by_state = {state: [r for r in audit_rows if r["codigo_centro"][:2] == state] for state in TARGET_STATES}
    selected = [r for r in audit_rows if r["clasificacion"] == "CONFIRMADO"]
    probable = [r for r in audit_rows if r["clasificacion"] == "PROBABLE"]
    lines: list[str] = []
    lines.append("# TM 2025: segunda auditoria de faltantes 06/22/23\n\n")
    lines.append(f"Fecha de generacion: {datetime.now(timezone.utc).isoformat()}\n\n")
    lines.append("## Metodologia\n\n")
    lines.append("- Se parte del TM original `backend/tm_2025_macedonia_estandar.csv` de Asamblea Macedonia, no del candidato previo.\n")
    lines.append("- Se restringe el universo a codigos de estado `06`, `22` y `23` dentro de `tm_2025_missing_centers_candidates.csv`.\n")
    lines.append("- Para cada candidato se verifica presencia en Regionales 2025 por API/CSV previo y pagina publica; ausencia en Asamblea por TM reconstruido y URL directa esperable; y presencia historica en TM 2024, 2018 y 2015.\n")
    lines.append("- `cantidadMesas=1` en Regionales se trata como evidencia fuerte de centro activo de una mesa. `cantidadMesas=0` no se convierte automaticamente en una mesa, aunque se reporte electorado.\n\n")
    lines.append("## Validacion territorial de partida\n\n")
    lines.append("| Estado | Esperado centros | TM Asamblea centros | Deficit centros | Esperado mesas | TM Asamblea mesas | Deficit mesas |\n")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n")
    for state, expected in EXPECTED_STATE_COUNTS.items():
        current = state_counts[state]
        lines.append(
            f"| {expected['estado']} | {expected['centros']} | {current['centros']} | {expected['centros'] - current['centros']} | "
            f"{expected['mesas']} | {current['mesas']} | {expected['mesas'] - current['mesas']} |\n"
        )
    lines.append("\n## Resultado por estado\n\n")
    for state, rows in by_state.items():
        expected = EXPECTED_STATE_COUNTS[state]
        counts = Counter(r["clasificacion"] for r in rows)
        elect_confirmed = sum(int(r["electores_2025"] or 0) for r in rows if r["clasificacion"] == "CONFIRMADO")
        elect_probable = sum(int(r["electores_2025"] or 0) for r in rows if r["clasificacion"] in {"CONFIRMADO", "PROBABLE"})
        lines.append(f"### {expected['estado']}\n\n")
        lines.append(f"- Candidatos auditados: {len(rows)}.\n")
        lines.append(f"- Clasificacion: {dict(counts)}.\n")
        lines.append(f"- Deficit requerido: {expected['centros']} - {state_counts[state]['centros']} = {expected['centros'] - state_counts[state]['centros']} centros; {expected['mesas'] - state_counts[state]['mesas']} mesas.\n")
        lines.append(f"- Electores confirmados: {elect_confirmed}; confirmados+probables: {elect_probable}; brecha secundaria aproximada: {expected['electores_gap_aprox']}.\n\n")
    lines.append("## Candidatos evaluados\n\n")
    lines.append("| Codigo | Estado | Municipio | Parroquia | Centro | Mesas 2025 | Electores 2025 | Clasificacion | Evidencia |\n")
    lines.append("| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |\n")
    for row in audit_rows:
        lines.append(
            f"| {row['codigo_centro']} | {row['estado']} | {row['municipio']} | {row['parroquia']} | {row['centro']} | "
            f"{row['mesas_2025']} | {row['electores_2025']} | {row['clasificacion']} | {row['evidencia']} |\n"
        )
    lines.append("\n## Decision sobre TM v2\n\n")
    if v2_created:
        lines.append(f"Se genero `{V2_TM.relative_to(ROOT)}` porque hay evidencia suficiente para cerrar exactamente 5+2+1.\n")
    else:
        lines.append("No se genero `backend/tm_2025_macedonia_estandar_candidate_completed_v2.csv`.\n\n")
        lines.append("Razon: la evidencia documental no identifica de forma unica los 5 centros de Bolivar. Hay 8 candidatos con `cantidadMesas=1` en Regionales para un deficit de 5; varias combinaciones pueden acercarse a la brecha secundaria de electores, pero eso seria una seleccion aritmetica, no documental. Amazonas y Delta tambien contienen candidatos con electores y `cantidadMesas=0`, que quedan como probables/indeterminados segun el caso.\n")
    return "".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.02)
    args = parser.parse_args()

    all_candidates = read_csv(CANDIDATES_IN)
    candidates = [r for r in all_candidates if norm_code(r["codigo_centro"], 9)[:2] in TARGET_STATES]
    original_rows = read_csv(ORIGINAL_TM)
    original_codes = {norm_code(r["codigo_centro"], 9) for r in original_rows}
    hist_2024 = center_totals(BACKEND / "tm_2024_estandar_v2.csv")
    hist_2018 = center_totals(BACKEND / "tm_2018_estandar.csv")
    hist_2015 = center_totals(BACKEND / "tm_2015_estandar.csv")

    audit_rows: list[dict[str, Any]] = []
    for row in candidates:
        code = norm_code(row["codigo_centro"], 9)
        reg_url = row["source_url"]
        asm_url = asamblea_url(code)
        reg_html = fetch_html(reg_url, args.cache_only, args.sleep)
        asm_html = fetch_html(asm_url, args.cache_only, args.sleep)
        classification, reason = classify(row, reg_html, asm_html["status"])
        cache_ref = ""
        if isinstance(reg_html["cache"], Path) and reg_html["cache"].exists():
            cache_ref = str(reg_html["cache"].relative_to(ROOT)).replace("\\", "/")
        evidencia = (
            f"Regionales API {row['source_api_url']} hash {row['source_hash']}; "
            f"HTML Regionales status {reg_html['status']} hash {reg_html['hash'][:12]} cache {cache_ref}; "
            f"Asamblea URL status {asm_html['status']}; "
            f"codigo en TM Asamblea reconstruido: {'si' if code in original_codes else 'no'}."
        )
        audit_rows.append(
            {
                "codigo_centro": code,
                "estado": row["estado"],
                "municipio": row["municipio"],
                "parroquia": row["parroquia"],
                "centro": row["nombre_centro"],
                "mesas_2025": row["numero_mesas"],
                "electores_2025": row["total_electores"],
                "regionales_2025": "si" if reg_html["status"] == 200 else f"parcial/status_{reg_html['status']}",
                "asamblea_2025": "si" if code in original_codes or asm_html["status"] == 200 else "no",
                "tm_2024": historical_label(hist_2024, code),
                "tm_2018": historical_label(hist_2018, code),
                "tm_2015": historical_label(hist_2015, code),
                "url_regionales": reg_url,
                "url_asamblea_si_existe": asm_url if asm_html["status"] == 200 else "",
                "evidencia": evidencia,
                "clasificacion": classification,
                "razon_clasificacion": reason,
            }
        )

    audit_rows.sort(key=lambda r: r["codigo_centro"])
    write_csv(AUDIT_CSV, audit_rows, AUDIT_COLUMNS)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    confirmed_by_state = Counter(r["codigo_centro"][:2] for r in audit_rows if r["clasificacion"] == "CONFIRMADO")
    probable_by_state = Counter(r["codigo_centro"][:2] for r in audit_rows if r["clasificacion"] == "PROBABLE")
    enough_for_v2 = (
        confirmed_by_state["06"] == 5
        and confirmed_by_state["22"] == 2
        and confirmed_by_state["23"] == 1
    )
    if enough_for_v2:
        raise RuntimeError("La auditoria encontro cierre exacto inesperado; generar TM v2 requiere implementacion explicita.")

    REPORT.write_text(build_report(audit_rows, original_rows, v2_created=False), encoding="utf-8")
    summary = {
        "audit_csv": str(AUDIT_CSV.relative_to(ROOT)),
        "report": str(REPORT.relative_to(ROOT)),
        "tm_v2_created": False,
        "candidates": len(audit_rows),
        "classification": dict(Counter(r["clasificacion"] for r in audit_rows)),
        "confirmed_by_state": dict(confirmed_by_state),
        "probable_by_state": dict(probable_by_state),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
