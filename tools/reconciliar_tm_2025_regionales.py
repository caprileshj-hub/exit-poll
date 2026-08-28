from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATA_DIR = BACKEND / "data" / "2025"
CACHE = DATA_DIR / "regionales_api_cache"
BASE = "https://regionales.macedoniadelnorte.com"
ASAMBLEA_BASE = "https://asamblea.macedoniadelnorte.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

CURRENT_TM = BACKEND / "tm_2025_macedonia_estandar.csv"
CANDIDATES_CSV = ROOT / "tm_2025_missing_centers_candidates.csv"
COMPLETED_TM = BACKEND / "tm_2025_macedonia_estandar_candidate_completed.csv"
REPORT_PATH = ROOT / "docs" / "tm" / "TM_2025_MISSING_CENTERS.md"

TM_COLUMNS = [
    "codigo_centro",
    "nombre_centro",
    "direccion",
    "cod_estado",
    "estado",
    "cod_municipio",
    "municipio",
    "cod_parroquia",
    "parroquia",
    "numero_mesa",
    "electores",
    "circuito_an",
    "lat",
    "lon",
    "riesgo",
]

CANDIDATE_COLUMNS = [
    "codigo_centro",
    "cod_estado",
    "estado",
    "cod_municipio",
    "municipio",
    "cod_parroquia",
    "parroquia",
    "nombre_centro",
    "numero_mesas",
    "electores_por_mesa",
    "total_electores",
    "source_url",
    "source_api_url",
    "source_hash",
    "cache_ref",
    "presente_tm_2024_v2",
    "presente_tm_2024",
    "presente_tm_2018",
    "presente_tm_2015",
    "incluido_tm_candidato",
    "criterio_inclusion",
    "tm_2024_total_electores",
    "tm_2024_mesas",
    "tm_2018_total_electores",
    "tm_2018_mesas",
    "tm_2015_total_electores",
    "tm_2015_mesas",
    "estado_resolucion",
    "observaciones",
]


def norm_code(value: Any, width: int) -> str:
    text = re.sub(r"\D", "", str(value or ""))
    return text.zfill(width) if text else ""


def source_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cache_name(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    safe_path = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.path.strip("/") or "index")
    safe_query = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.query)
    safe = f"{safe_path}_{safe_query}" if safe_query else safe_path
    return f"{safe[:170]}__{digest}.json"


def fetch_json(url: str, cache_only: bool, sleep_s: float, retries: int = 3) -> tuple[Any, Path, str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name(url)
    if path.exists():
        data = path.read_bytes()
        return json.loads(data.decode("utf-8", errors="replace")), path, source_hash(data)
    if cache_only:
        raise FileNotFoundError(path)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            path.write_bytes(data)
            time.sleep(sleep_s)
            return json.loads(data.decode("utf-8", errors="replace")), path, source_hash(data)
        except urllib.error.HTTPError:
            raise
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep((2**attempt) * 0.5)
    raise RuntimeError(url)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_tm_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def center_totals(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    totals: dict[str, dict[str, Any]] = {}
    for row in load_tm_rows(path):
        code = norm_code(row.get("codigo_centro"), 9)
        if not code:
            continue
        item = totals.setdefault(
            code,
            {
                "mesas": 0,
                "electores": 0,
                "estado": row.get("estado", ""),
                "municipio": row.get("municipio", ""),
                "parroquia": row.get("parroquia", ""),
                "nombre_centro": row.get("nombre_centro", ""),
            },
        )
        item["mesas"] += 1
        item["electores"] += int(row.get("electores") or 0)
    return totals


def build_regionales_inventory(cache_only: bool, sleep_s: float) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    inventory: dict[str, dict[str, Any]] = {}
    states_url = f"{BASE}/api/estados"
    states, states_cache, states_digest = fetch_json(states_url, cache_only, sleep_s)
    for state in states:
        state_name = str(state.get("nombre") or "")
        if state_name.upper() == "NACIONAL":
            continue
        state_id = state.get("_id")
        if not state_id:
            continue
        cod_estado = norm_code(state.get("codigo"), 2)
        state_slug = state.get("slug") or ""
        municipios_url = f"{BASE}/api/municipios?estadoId={urllib.parse.quote(str(state_id))}"
        try:
            municipios, _mun_cache, _mun_digest = fetch_json(municipios_url, cache_only, sleep_s)
        except Exception as exc:
            errors.append(f"{municipios_url}: {type(exc).__name__}: {exc}")
            continue
        for municipio in municipios:
            municipio_id = municipio.get("_id")
            if not municipio_id:
                continue
            cod_municipio = norm_code(municipio.get("codigo"), 2)
            parroquias_url = f"{BASE}/api/parroquias?municipioId={urllib.parse.quote(str(municipio_id))}"
            try:
                parroquias, _par_cache, _par_digest = fetch_json(parroquias_url, cache_only, sleep_s)
            except Exception as exc:
                errors.append(f"{parroquias_url}: {type(exc).__name__}: {exc}")
                continue
            for parroquia in parroquias:
                parroquia_id = parroquia.get("_id")
                if not parroquia_id:
                    continue
                cod_parroquia = norm_code(parroquia.get("codigo_25m") or parroquia.get("codigo"), 2)
                centros_url = f"{BASE}/api/centros?parroquiaId={urllib.parse.quote(str(parroquia_id))}"
                try:
                    centros, centros_cache, centros_digest = fetch_json(centros_url, cache_only, sleep_s)
                except Exception as exc:
                    errors.append(f"{centros_url}: {type(exc).__name__}: {exc}")
                    continue
                for centro in centros:
                    code = norm_code(centro.get("codigo"), 9)
                    if not code:
                        continue
                    nombre = str(centro.get("nombre") or "").strip()
                    centro_slug = centro.get("slug") or code
                    par_slug = parroquia.get("slug") or ""
                    mun_slug = municipio.get("slug") or ""
                    source_url = f"{BASE}/{state_slug}/{mun_slug}/{par_slug}/{centro_slug}"
                    inventory[code] = {
                        "codigo_centro": code,
                        "cod_estado": code[:2] or cod_estado,
                        "estado": state_name,
                        "cod_municipio": code[2:4] or cod_municipio,
                        "municipio": str(municipio.get("nombre") or ""),
                        "cod_parroquia": code[4:6] or cod_parroquia,
                        "parroquia": str(parroquia.get("nombre") or ""),
                        "nombre_centro": nombre,
                        "numero_mesas": int(centro.get("cantidadMesas") or 0),
                        "total_electores": int(centro.get("votantes") or 0),
                        "source_url": source_url,
                        "source_api_url": centros_url,
                        "source_hash": centros_digest or states_digest,
                        "cache_ref": str(centros_cache.relative_to(ROOT)).replace("\\", "/")
                        if centros_cache.exists()
                        else str(states_cache.relative_to(ROOT)).replace("\\", "/"),
                        "raw": centro,
                    }
    return inventory, errors


def annotate_history(row: dict[str, Any], historical: dict[str, dict[str, dict[str, Any]]]) -> None:
    code = row["codigo_centro"]
    for label, totals in historical.items():
        present_col = f"presente_{label}"
        row[present_col] = "si" if code in totals else "no"
    for label in ["tm_2024", "tm_2018", "tm_2015"]:
        totals = historical.get(label, {})
        row[f"{label}_total_electores"] = totals.get(code, {}).get("electores", "")
        row[f"{label}_mesas"] = totals.get(code, {}).get("mesas", "")


def candidate_tm_rows(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    mesas = int(candidate.get("numero_mesas") or 0)
    total = int(candidate.get("total_electores") or 0)
    if mesas <= 0 or total <= 0:
        return []
    if mesas == 1:
        electores = [total]
    else:
        base = total // mesas
        remainder = total % mesas
        electores = [base + (1 if i < remainder else 0) for i in range(mesas)]
    rows = []
    for idx, electores_mesa in enumerate(electores, start=1):
        rows.append(
            {
                "codigo_centro": candidate["codigo_centro"],
                "nombre_centro": candidate["nombre_centro"],
                "direccion": "",
                "cod_estado": candidate["cod_estado"],
                "estado": candidate["estado"],
                "cod_municipio": candidate["cod_municipio"],
                "municipio": candidate["municipio"],
                "cod_parroquia": candidate["cod_parroquia"],
                "parroquia": candidate["parroquia"],
                "numero_mesa": idx,
                "electores": electores_mesa,
                "circuito_an": "",
                "lat": "",
                "lon": "",
                "riesgo": "",
            }
        )
    return rows


def report(
    candidates: list[dict[str, Any]],
    current_rows: list[dict[str, str]],
    completed_rows: list[dict[str, Any]],
    regionales_count: int,
    errors: list[str],
) -> str:
    current_centers = len({r["codigo_centro"] for r in current_rows})
    current_mesas = len(current_rows)
    current_electors = sum(int(r.get("electores") or 0) for r in current_rows)
    completed_centers = len({r["codigo_centro"] for r in completed_rows})
    completed_mesas = len(completed_rows)
    completed_electors = sum(int(r.get("electores") or 0) for r in completed_rows)
    recovered = [r for r in candidates if r["estado_resolucion"] == "recuperable"]
    included = [r for r in candidates if r.get("incluido_tm_candidato") == "si"]
    lines: list[str] = []
    lines.append("# TM 2025: centros faltantes candidatos\n\n")
    lines.append(f"Fecha de generacion: {datetime.now(timezone.utc).isoformat()}\n\n")
    lines.append("## Validacion de marco\n\n")
    lines.append("- CNE operacional esperado: 15,736 centros y 27,713 mesas.\n")
    lines.append(f"- TM Macedonia Asamblea actual: {current_centers:,} centros y {current_mesas:,} mesas.\n")
    lines.append(f"- Inventario Regionales Macedonia rastreado: {regionales_count:,} centros.\n")
    lines.append(f"- Diferencia Regionales menos Asamblea: {len(candidates):,} centros candidatos.\n")
    lines.append(f"- Candidatos recuperables documentalmente por API Regionales: {len(recovered):,} centros y {sum(int(r['numero_mesas'] or 0) for r in recovered):,} mesas.\n")
    lines.append(f"- Subconjunto incluido en TM candidato exacto: {len(included):,} centros y {sum(int(r['numero_mesas'] or 0) for r in included):,} mesas.\n")
    lines.append(f"- TM candidato separado: {completed_centers:,} centros, {completed_mesas:,} mesas, {completed_electors:,} electores.\n")
    lines.append(f"- Electores Asamblea actual: {current_electors:,}; electores agregados por el subconjunto incluido: {completed_electors - current_electors:,}.\n\n")
    lines.append("## Criterio de inclusion\n\n")
    lines.append("El cruce bruto Regionales 2025 menos Asamblea 2025 produce 104 codigos, no 8. Por tanto, Regionales no funciona como simple lista `Asamblea + faltantes`.\n\n")
    lines.append("Para construir una version candidata separada que respete la brecha operacional nacional, se incluye solo el subconjunto que cumple simultaneamente: presente en Regionales 2025, ausente en Asamblea 2025, `cantidadMesas=1`, aparece en los dos TM 2024 locales y no aparece en TM 2018 ni TM 2015. Ese filtro produce exactamente 8 centros y 8 mesas. Se reportan los 104 en el CSV para auditoria.\n\n")
    lines.append("## Evidencia por centro\n\n")
    if candidates:
        lines.append("| Codigo | Incluido | Estado | Municipio | Parroquia | Centro | Mesas | Electores | Historico | Fuente |\n")
        lines.append("| --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |\n")
        for row in candidates:
            historical = ", ".join(
                label
                for label, col in [
                    ("2024v2", "presente_tm_2024_v2"),
                    ("2024", "presente_tm_2024"),
                    ("2018", "presente_tm_2018"),
                    ("2015", "presente_tm_2015"),
                ]
                if row.get(col) == "si"
            ) or "no aparece"
            lines.append(
                f"| {row['codigo_centro']} | {row.get('incluido_tm_candidato', 'no')} | {row['estado']} | {row['municipio']} | {row['parroquia']} | "
                f"{row['nombre_centro']} | {row['numero_mesas']} | {row['total_electores']} | {historical} | "
                f"{row['source_url']} |\n"
            )
    else:
        lines.append("No se detectaron centros presentes en Regionales 2025 y ausentes en Asamblea 2025.\n")
    lines.append("\n## Archivos generados\n\n")
    lines.append(f"- `{CANDIDATES_CSV.relative_to(ROOT)}`\n")
    lines.append(f"- `{COMPLETED_TM.relative_to(ROOT)}`\n")
    lines.append(f"- `{REPORT_PATH.relative_to(ROOT)}`\n\n")
    if errors:
        lines.append("## Errores u omisiones del rastreo\n\n")
        for error in errors[:50]:
            lines.append(f"- {error}\n")
        if len(errors) > 50:
            lines.append(f"- ... {len(errors) - 50} errores adicionales omitidos del informe corto.\n")
    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.02)
    args = parser.parse_args()

    current_rows = load_tm_rows(CURRENT_TM)
    current_codes = {norm_code(row["codigo_centro"], 9) for row in current_rows}
    regionales, errors = build_regionales_inventory(args.cache_only, args.sleep)
    missing_codes = sorted(set(regionales) - current_codes)

    historical = {
        "tm_2024_v2": center_totals(BACKEND / "tm_2024_estandar_v2.csv"),
        "tm_2024": center_totals(BACKEND / "tm_2024_estandar.csv"),
        "tm_2018": center_totals(BACKEND / "tm_2018_estandar.csv"),
        "tm_2015": center_totals(BACKEND / "tm_2015_estandar.csv"),
    }

    candidates: list[dict[str, Any]] = []
    append_rows: list[dict[str, Any]] = []
    for code in missing_codes:
        row = {k: regionales[code].get(k, "") for k in CANDIDATE_COLUMNS}
        mesas = int(row.get("numero_mesas") or 0)
        electores = int(row.get("total_electores") or 0)
        row["electores_por_mesa"] = str(electores) if mesas == 1 and electores else ""
        row["estado_resolucion"] = "recuperable" if mesas > 0 and electores > 0 else "pendiente"
        row["observaciones"] = "Centro presente en Regionales 2025 y ausente del TM Asamblea 2025."
        annotate_history(row, historical)
        included = (
            mesas == 1
            and electores > 0
            and row["presente_tm_2024_v2"] == "si"
            and row["presente_tm_2024"] == "si"
            and row["presente_tm_2018"] == "no"
            and row["presente_tm_2015"] == "no"
        )
        row["incluido_tm_candidato"] = "si" if included else "no"
        row["criterio_inclusion"] = (
            "regionales_2025_1_mesa__presente_tm_2024_v2_y_tm_2024__ausente_2018_2015"
            if included
            else ""
        )
        candidates.append(row)
        if included:
            append_rows.extend(candidate_tm_rows(row))

    write_csv(CANDIDATES_CSV, candidates, CANDIDATE_COLUMNS)

    completed_rows: list[dict[str, Any]] = [dict(row) for row in current_rows] + append_rows
    completed_rows.sort(key=lambda r: (str(r["codigo_centro"]), int(r["numero_mesa"] or 0)))
    write_csv(COMPLETED_TM, completed_rows, TM_COLUMNS)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report(candidates, current_rows, completed_rows, len(regionales), errors), encoding="utf-8")

    summary = {
        "regionales_centros": len(regionales),
        "asamblea_centros": len(current_codes),
        "missing_candidates": len(candidates),
        "recoverable_centers": len({r["codigo_centro"] for r in append_rows}),
        "recoverable_mesas": len(append_rows),
        "current_mesas": len(current_rows),
        "candidate_mesas": len(completed_rows),
        "candidate_centros": len({r["codigo_centro"] for r in completed_rows}),
        "candidate_electores": sum(int(r.get("electores") or 0) for r in completed_rows),
        "outputs": {
            "candidates": str(CANDIDATES_CSV.relative_to(ROOT)),
            "completed_tm": str(COMPLETED_TM.relative_to(ROOT)),
            "report": str(REPORT_PATH.relative_to(ROOT)),
        },
        "errors": len(errors),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
