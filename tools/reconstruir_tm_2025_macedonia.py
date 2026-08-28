from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATA_DIR = BACKEND / "data" / "2025"
CACHE = DATA_DIR / "macedonia_cache"
BASE = "https://asamblea.macedoniadelnorte.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
NATIONAL_CODES = {f"{i:02d}" for i in range(1, 25)} | {"26"}


def norm_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def strip_tags(fragment: str) -> str:
    return norm_space(re.sub(r"<[^>]+>", " ", fragment.replace("<!-- -->", "")))


def number(value: str) -> int | None:
    value = re.sub(r"[^\d]", "", value or "")
    return int(value) if value else None


def source_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cache_name(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    suffix = Path(parsed.path).suffix or ".html"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.path.strip("/") or "index")
    return f"{safe[:150]}__{digest}{suffix}"


def fetch(url: str, cache_only: bool = False, sleep_s: float = 0.05, retries: int = 2) -> tuple[bytes | None, Path, str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name(url)
    if path.exists():
        data = path.read_bytes()
        return data, path, source_hash(data)
    if cache_only:
        return None, path, ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json,*/*"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
            path.write_bytes(data)
            time.sleep(sleep_s)
            return data, path, source_hash(data)
        except urllib.error.HTTPError:
            raise
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep((2**attempt) * 0.5)
    return None, path, ""


def read_json(url: str, cache_only: bool, sleep_s: float) -> tuple[object, Path, str]:
    data, path, digest = fetch(url, cache_only=cache_only, sleep_s=sleep_s)
    if data is None:
        raise FileNotFoundError(path)
    return json.loads(data.decode("utf-8", errors="replace")), path, digest


def extract_links(text: str, pattern: str) -> list[tuple[str, str]]:
    out = []
    for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text, flags=re.S):
        if re.match(pattern, href):
            out.append((href, strip_tags(label)))
    return out


def load_states(cache_only: bool, sleep_s: float) -> list[dict[str, str]]:
    states, _, _ = read_json(f"{BASE}/api/estados", cache_only, sleep_s)
    return list(states)


def parish_seed_from_2024(states: list[dict[str, str]]) -> list[tuple[str, str, str, str]]:
    slug_by_code = {s["cod_estado"].zfill(2): s["slug"] for s in states}
    path = BACKEND / "tm_2024_estandar_v2.csv"
    seeds: set[tuple[str, str, str, str]] = set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            cod_estado = row["cod_estado"].strip().zfill(2)
            if cod_estado not in slug_by_code:
                continue
            cod_mun = row["cod_municipio"].strip().zfill(2)
            cod_par = row["cod_parroquia"].strip().zfill(2)
            mun_full = f"{cod_estado}{cod_mun}"
            par_full = f"{mun_full}{cod_par}"
            seeds.add((slug_by_code[cod_estado], cod_estado, mun_full, par_full))
    return sorted(seeds)


def parse_parish_page(slug: str, mun_full: str, par_full: str, text: str) -> dict:
    pattern = rf"^/{re.escape(slug)}/{mun_full}/{par_full}/\d{{9}}$"
    centers = extract_links(text, pattern)
    names = {}
    for href, label in centers:
        match = re.search(r"Cod:\s*(\d{9})", label)
        code = match.group(1) if match else href.rsplit("/", 1)[-1]
        name = re.sub(r"\s*Cod:\s*\d{9}\s*$", "", label).strip()
        names[code] = name
    return {
        "centers": sorted(
            (code, name, f"/{slug}/{mun_full}/{par_full}/{code}") for code, name in names.items()
        )
    }


def parse_center_page(url: str, text: str, digest: str, cache_path: Path) -> tuple[list[dict], list[dict]]:
    code = url.rstrip("/").rsplit("/", 1)[-1]
    cod_estado, cod_municipio, cod_parroquia = code[:2], code[2:4], code[4:6]

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, flags=re.S)
    nombre = strip_tags(h1.group(1)) if h1 else ""
    geo_match = re.search(r'<p class="text-muted-foreground text-sm">(.*?)</p>', text, flags=re.S)
    geo_parts = [p.strip() for p in strip_tags(geo_match.group(1)).split(",")] if geo_match else []
    parroquia = geo_parts[0] if len(geo_parts) >= 1 else ""
    municipio = geo_parts[1] if len(geo_parts) >= 2 else ""
    estado = geo_parts[2] if len(geo_parts) >= 3 else ""

    total_reportado = None
    total_match = re.search(
        r'<div class="text-lg font-semibold">([^<]+)</div>\s*<div class="text-xs text-muted-foreground">Inscritos</div>',
        text,
        flags=re.S,
    )
    if total_match:
        total_reportado = number(total_match.group(1))

    mesa_matches = re.findall(
        r"Mesa\s*<!-- -->\s*(\d+).*?text-xs text-muted-foreground\">([^<]+)<!-- -->\s*de\s*<!-- -->\s*([^<]+)</div>",
        text,
        flags=re.S,
    )
    rows: list[dict] = []
    provenance: list[dict] = []
    sum_mesas = 0
    for mesa, _votantes, inscritos in mesa_matches:
        electores = number(inscritos)
        if electores is not None:
            sum_mesas += electores
        obs = ""
        row = {
            "codigo_centro": code,
            "nombre_centro": nombre,
            "direccion": "",
            "cod_estado": cod_estado,
            "estado": estado,
            "cod_municipio": cod_municipio,
            "municipio": municipio,
            "cod_parroquia": cod_parroquia,
            "parroquia": parroquia,
            "numero_mesa": int(mesa),
            "electores": electores if electores is not None else "",
            "circuito_an": "",
            "lat": "",
            "lon": "",
            "riesgo": "",
        }
        rows.append(row)
        provenance.append(
            {
                "codigo_centro": code,
                "numero_mesa": int(mesa),
                "source_url": url,
                "fetched_at": datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc).isoformat(),
                "source_hash": digest,
                "cache_ref": str(cache_path.relative_to(ROOT)).replace("\\", "/"),
                "electores_centro_reportado": total_reportado if total_reportado is not None else "",
                "electores_mesa": electores if electores is not None else "",
                "observaciones": obs,
            }
        )
    if total_reportado is not None and rows and total_reportado != sum_mesas:
        for p in provenance:
            p["observaciones"] = f"total_centro_reportado({total_reportado}) != suma_mesas({sum_mesas})"
    if not rows:
        provenance.append(
            {
                "codigo_centro": code,
                "numero_mesa": "",
                "source_url": url,
                "fetched_at": datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc).isoformat(),
                "source_hash": digest,
                "cache_ref": str(cache_path.relative_to(ROOT)).replace("\\", "/"),
                "electores_centro_reportado": total_reportado if total_reportado is not None else "",
                "electores_mesa": "",
                "observaciones": "centro_sin_mesas_parseables",
            }
        )
    return rows, provenance


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_tm(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def center_frame(rows: list[dict], domestic_only: bool = False) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in rows:
        code = str(row["codigo_centro"]).zfill(9)
        if domestic_only and code[:2] not in NATIONAL_CODES:
            continue
        rec = out.setdefault(
            code,
            {
                "codigo_centro": code,
                "cod_estado": row["cod_estado"].zfill(2),
                "estado": row["estado"],
                "cod_municipio": row["cod_municipio"].zfill(2),
                "municipio": row["municipio"],
                "cod_parroquia": row["cod_parroquia"].zfill(2),
                "parroquia": row["parroquia"],
                "nombre_centro": row["nombre_centro"],
                "mesas": 0,
                "electores": 0,
            },
        )
        rec["mesas"] += 1
        rec["electores"] += int(float(row["electores"] or 0))
    return out


def dhondt_quotas(frame: dict[str, dict], sample_size: int = 120, base_per_state: int = 2) -> dict[str, int]:
    weights = defaultdict(int)
    names = {}
    for rec in frame.values():
        state = rec["cod_estado"]
        weights[state] += rec["electores"]
        names[state] = rec["estado"]
    quotas = {state: base_per_state for state in weights}
    extras = sample_size - base_per_state * len(weights)
    scores = []
    for state, weight in weights.items():
        for divisor in range(1, extras + 1):
            scores.append((weight / divisor, weight, names[state], state))
    for *_rest, state in sorted(scores, key=lambda item: (-item[0], -item[1], item[2], item[3]))[:extras]:
        quotas[state] += 1
    return quotas


def percentile(values: list[int], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = (len(values) - 1) * p
    lo, hi = math.floor(idx), math.ceil(idx)
    if lo == hi:
        return float(values[lo])
    return values[lo] + (values[hi] - values[lo]) * (idx - lo)


def percent(part: int | float, total: int | float) -> float:
    return (float(part) / float(total) * 100) if total else 0.0


def compare(tm2025: Path, metadata: dict, min_electores: int) -> tuple[list[dict], str]:
    rows25 = load_tm(tm2025)
    rows24 = load_tm(BACKEND / "tm_2024_estandar_v2.csv")
    f25_all = center_frame(rows25)
    f24_all = center_frame(rows24)
    f25 = center_frame(rows25, domestic_only=True)
    f24 = center_frame(rows24, domestic_only=True)
    states = sorted({r["cod_estado"] for r in f24.values()} | {r["cod_estado"] for r in f25.values()})
    q24, q25 = dhondt_quotas(f24), dhondt_quotas(f25)

    estado_rows = []
    for state in states:
        c24 = [r for r in f24.values() if r["cod_estado"] == state]
        c25 = [r for r in f25.values() if r["cod_estado"] == state]
        name = (c25 or c24 or [{"estado": state}])[0]["estado"]
        row = {
            "cod_estado": state,
            "estado": name,
            "centros_2024": len(c24),
            "centros_2025": len(c25),
            "delta_centros": len(c25) - len(c24),
            "mesas_2024": sum(r["mesas"] for r in c24),
            "mesas_2025": sum(r["mesas"] for r in c25),
            "delta_mesas": sum(r["mesas"] for r in c25) - sum(r["mesas"] for r in c24),
            "electores_2024": sum(r["electores"] for r in c24),
            "electores_2025": sum(r["electores"] for r in c25),
            "delta_electores": sum(r["electores"] for r in c25) - sum(r["electores"] for r in c24),
            "cuota_2024": q24.get(state, 0),
            "cuota_2025": q25.get(state, 0),
            "delta_cuota": q25.get(state, 0) - q24.get(state, 0),
        }
        estado_rows.append(row)

    codes24, codes25 = set(f24), set(f25)
    comunes = codes24 & codes25
    nuevos = codes25 - codes24
    desaparecidos = codes24 - codes25
    eligible24 = {c for c, r in f24.items() if r["electores"] >= min_electores}
    eligible25 = {c for c, r in f25.items() if r["electores"] >= min_electores}
    crossed_up = {c for c in comunes if f24[c]["electores"] < min_electores <= f25[c]["electores"]}
    crossed_down = {c for c in comunes if f24[c]["electores"] >= min_electores > f25[c]["electores"]}
    deltas = [
        {
            "codigo_centro": c,
            "nombre_2024": f24[c]["nombre_centro"],
            "nombre_2025": f25[c]["nombre_centro"],
            "estado": f25[c]["estado"],
            "municipio_2024": f24[c]["municipio"],
            "municipio_2025": f25[c]["municipio"],
            "parroquia_2024": f24[c]["parroquia"],
            "parroquia_2025": f25[c]["parroquia"],
            "electores_2024": f24[c]["electores"],
            "electores_2025": f25[c]["electores"],
            "delta": f25[c]["electores"] - f24[c]["electores"],
        }
        for c in comunes
    ]
    changes = [d["delta"] for d in deltas]
    geo_changes = [
        d
        for d in deltas
        if f24[d["codigo_centro"]]["cod_municipio"] != f25[d["codigo_centro"]]["cod_municipio"]
        or f24[d["codigo_centro"]]["cod_parroquia"] != f25[d["codigo_centro"]]["cod_parroquia"]
    ]
    renames = [d for d in deltas if d["nombre_2024"] != d["nombre_2025"]]

    totals = {
        "centros_2024": len(f24),
        "centros_2025": len(f25),
        "mesas_2024": sum(r["mesas"] for r in f24.values()),
        "mesas_2025": sum(r["mesas"] for r in f25.values()),
        "electores_2024": sum(r["electores"] for r in f24.values()),
        "electores_2025": sum(r["electores"] for r in f25.values()),
        "exterior_2024": sum(r["electores"] for r in f24_all.values() if r["cod_estado"] == "99"),
        "exterior_2025": sum(r["electores"] for r in f25_all.values() if r["cod_estado"] == "99"),
    }
    report = []
    report.append("# Comparacion TM 2024 -> TM 2025 Macedonia\n")
    report.append("Analisis independiente. No se importo el TM 2025 a la aplicacion ni se modifico SQLite.\n")
    report.append("## Metodo\n")
    report.append(
        "- Fuente: https://asamblea.macedoniadelnorte.com/. Se inspeccionaron HTML/JS, `/api/estados`, `/api/buscar`, `/api/participacion`, `/api/verificacion` y endpoints de resultados. No se encontro dump RE/CSV/JSON completo; la reconstruccion usa HTML/RSC cacheado.\n"
    )
    report.append(
        "- Las paginas de estado no enlazan municipios; se usaron codigos territoriales del marco REP 2024 vigente como semillas de parroquia, y cada URL 2025 se valido por HTTP. Los centros 2025 se descubrieron desde enlaces publicados en cada parroquia.\n"
    )
    report.append("## Totales nacionales\n")
    report.append("| Metrica | 2024 | 2025 | Delta | Delta % |\n| --- | ---: | ---: | ---: | ---: |\n")
    for metric, label in [("centros", "Centros"), ("mesas", "Mesas"), ("electores", "Electores")]:
        a, b = totals[f"{metric}_2024"], totals[f"{metric}_2025"]
        pct = (b - a) / a * 100 if a else 0
        report.append(f"| {label} | {a:,} | {b:,} | {b-a:+,} | {pct:+.2f}% |\n")
    report.append("\nExterior separado: 2024 = {:,} electores; 2025 = {:,} electores.\n".format(totals["exterior_2024"], totals["exterior_2025"]))
    report.append("\n## Benchmarks 2025\n")
    report.append(
        f"- Extraido Macedonia nacional: {totals['centros_2025']:,} centros, {totals['mesas_2025']:,} mesas, {totals['electores_2025']:,} electores.\n"
    )
    report.append("- Benchmarks publicos del prompt: 15,736 centros; 27,713 mesas; padron 21,485,669 o 21,507,162.\n")
    report.append(
        f"- Deltas contra benchmark: centros {totals['centros_2025'] - 15736:+,}; mesas {totals['mesas_2025'] - 27713:+,}; electores vs 21,485,669 = {totals['electores_2025'] - 21485669:+,}; electores vs 21,507,162 = {totals['electores_2025'] - 21507162:+,}.\n"
    )
    report.append(
        f"- Endpoint `/api/participacion`: total_mesas={metadata.get('participacion', {}).get('total_mesas'):,}, total_electores={metadata.get('participacion', {}).get('total_electores'):,}, re_total_voters={metadata.get('participacion', {}).get('re_total_voters'):,}.\n"
    )
    report.append("\n## Exterior y estructuras especiales\n")
    report.append("- Exterior no aparece en `/api/estados` ni fue descubierto en el arbol de parroquias; queda en 0 para 2025 y separado de los nacionales.\n")
    report.append("- `/api/estados` lista GUAYANA (`cod_estado=26`), pero el arbol usado no produjo centros unicos con codigo 26.\n")
    report.append("- Busqueda puntual `q=GUAYANA` muestra el codigo `060703003` tambien etiquetado como GUAYANA; al abrir `/guayana/0607/060703/060703003`, el HTML del centro conserva parroquia SAN ISIDRO, municipio SIFONTES, estado BOLIVAR. Por tanto no se duplica ni se reasigna.\n")
    report.append("\n## Frame operativo >=800\n")
    e24_elect = sum(f24[c]["electores"] for c in eligible24)
    e25_elect = sum(f25[c]["electores"] for c in eligible25)
    report.append(f"- Piso importado: {min_electores} electores por centro.\n")
    report.append(f"- 2024: {len(eligible24):,} centros ({percent(len(eligible24), len(f24)):.2f}%), {e24_elect:,} electores ({percent(e24_elect, totals['electores_2024']):.2f}%).\n")
    report.append(f"- 2025: {len(eligible25):,} centros ({percent(len(eligible25), len(f25)):.2f}%), {e25_elect:,} electores ({percent(e25_elect, totals['electores_2025']):.2f}%).\n")
    report.append(f"- Cruzan <800 -> >=800: {len(crossed_up):,}; cruzan >=800 -> <800: {len(crossed_down):,}; nuevos >=800: {len(nuevos & eligible25):,}; desaparecidos >=800: {len(desaparecidos & eligible24):,}.\n")
    report.append("\n## Drift de centros\n")
    report.append(f"- Comunes: {len(comunes):,}; nuevos: {len(nuevos):,}; desaparecidos: {len(desaparecidos):,}.\n")
    report.append(f"- Cambios territoriales por codigo municipio/parroquia en comunes: {len(geo_changes):,}; posibles renombres con mismo codigo: {len(renames):,}.\n")
    if changes:
        report.append(f"- Distribucion delta electores comunes: min={min(changes):,}, p25={percentile(changes,.25):.0f}, mediana={percentile(changes,.5):.0f}, p75={percentile(changes,.75):.0f}, max={max(changes):,}.\n")
    report.append("\nMayores aumentos:\n")
    for d in sorted(deltas, key=lambda r: r["delta"], reverse=True)[:10]:
        report.append(f"- {d['codigo_centro']} {d['nombre_2025']} ({d['estado']}): {d['electores_2024']:,} -> {d['electores_2025']:,} ({d['delta']:+,})\n")
    report.append("\nMayores disminuciones:\n")
    for d in sorted(deltas, key=lambda r: r["delta"])[:10]:
        report.append(f"- {d['codigo_centro']} {d['nombre_2025']} ({d['estado']}): {d['electores_2024']:,} -> {d['electores_2025']:,} ({d['delta']:+,})\n")
    report.append("\n## Cuotas D'Hondt diagnosticas\n")
    report.append("N=120; 2 garantizados por 24 entidades nacionales + 72 adicionales D'Hondt. Exterior excluido.\n")
    report.append("| Estado | Cuota 2024 | Cuota 2025 | Delta |\n| --- | ---: | ---: | ---: |\n")
    for row in estado_rows:
        report.append(f"| {row['estado']} | {row['cuota_2024']} | {row['cuota_2025']} | {row['delta_cuota']:+} |\n")
    report.append("\n## Simulacion de muestra 2025\n")
    report.append("No ejecutada: hacerlo con el selector longitudinal actual requiere frame de aplicacion/SQLite; se mantiene read-only y se limita el analisis al frame.\n")
    return estado_rows, "".join(report)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-only", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.05)
    ap.add_argument("--limit-parishes", type=int, default=0)
    ap.add_argument("--limit-centers", type=int, default=0)
    ap.add_argument("--only-parish", default="", help="Ruta de parroquia para prueba, ej. /miranda/1318/131801")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    states = load_states(args.cache_only, args.sleep)
    state_by_slug = {s["slug"]: s for s in states}
    try:
        from selector_longitudinal import MIN_ELECTORES_CENTRO
    except Exception:
        sys.path.insert(0, str(BACKEND))
        from selector_longitudinal import MIN_ELECTORES_CENTRO

    participation, _, _ = read_json(f"{BASE}/api/participacion", args.cache_only, args.sleep)
    verification, _, _ = read_json(f"{BASE}/api/verificacion", args.cache_only, args.sleep)

    parish_seeds = parish_seed_from_2024(states)
    if args.only_parish:
        parts = args.only_parish.strip("/").split("/")
        if len(parts) != 3:
            raise ValueError("--only-parish debe tener formato /estado/municipio/parroquia")
        slug, mun_full, par_full = parts
        cod_estado = par_full[:2]
        parish_seeds = [(slug, cod_estado, mun_full, par_full)]
    if args.limit_parishes:
        parish_seeds = parish_seeds[: args.limit_parishes]
    centers: dict[str, tuple[str, str]] = {}
    errors = []
    pages_processed = 0
    for idx, (slug, _cod_estado, mun_full, par_full) in enumerate(parish_seeds, start=1):
        url = f"{BASE}/{slug}/{mun_full}/{par_full}"
        try:
            data, _path, _digest = fetch(url, cache_only=args.cache_only, sleep_s=args.sleep)
            pages_processed += 1
            if data is None:
                errors.append({"url": url, "error": "missing_cache"})
                continue
            parsed = parse_parish_page(slug, mun_full, par_full, data.decode("utf-8", errors="replace"))
            for code, name, href in parsed["centers"]:
                centers[code] = (name, urllib.parse.urljoin(BASE, href))
        except Exception as exc:
            errors.append({"url": url, "error": type(exc).__name__, "detail": str(exc)})
        if idx % 50 == 0:
            print(f"parroquias procesadas: {idx:,}/{len(parish_seeds):,}; centros descubiertos: {len(centers):,}", flush=True)

    rows: list[dict] = []
    provenance: list[dict] = []
    center_items = sorted(centers.items())
    if args.limit_centers:
        center_items = center_items[: args.limit_centers]
    print(f"iniciando centros: {len(center_items):,}; workers={max(1, args.workers)}", flush=True)

    def process_center(item: tuple[str, tuple[str, str]]) -> tuple[list[dict], list[dict], dict | None]:
        _code, (_name, url) = item
        try:
            data, cache_path, digest = fetch(url, cache_only=args.cache_only, sleep_s=args.sleep)
            if data is None:
                return [], [], {"url": url, "error": "missing_cache"}
            parsed_rows, parsed_prov = parse_center_page(url, data.decode("utf-8", errors="replace"), digest, cache_path)
            return parsed_rows, parsed_prov, None
        except Exception as exc:
            return [], [], {"url": url, "error": type(exc).__name__, "detail": str(exc)}

    workers = max(1, args.workers)
    center_pages_processed = 0
    if workers == 1:
        iterator = (process_center(item) for item in center_items)
        for idx, (parsed_rows, parsed_prov, err) in enumerate(iterator, start=1):
            center_pages_processed += 1
            rows.extend(parsed_rows)
            provenance.extend(parsed_prov)
            if err:
                errors.append(err)
            if idx % 50 == 0:
                print(f"centros procesados: {idx:,}/{len(center_items):,}", flush=True)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(process_center, item) for item in center_items]
            for idx, future in enumerate(as_completed(futures), start=1):
                center_pages_processed += 1
                parsed_rows, parsed_prov, err = future.result()
                rows.extend(parsed_rows)
                provenance.extend(parsed_prov)
                if err:
                    errors.append(err)
                if idx % 100 == 0:
                    print(f"centros procesados: {idx:,}/{len(center_items):,}", flush=True)
    pages_processed += center_pages_processed

    rows.sort(key=lambda r: (r["codigo_centro"], int(r["numero_mesa"] or 0)))
    tm_path = BACKEND / "tm_2025_macedonia_estandar.csv"
    prov_path = DATA_DIR / "tm_2025_macedonia_provenance.csv"
    write_csv(tm_path, rows, TM_COLUMNS)
    write_csv(
        prov_path,
        provenance,
        [
            "codigo_centro",
            "numero_mesa",
            "source_url",
            "fetched_at",
            "source_hash",
            "cache_ref",
            "electores_centro_reportado",
            "electores_mesa",
            "observaciones",
        ],
    )

    codes = {r["codigo_centro"] for r in rows}
    mesa_keys = Counter((r["codigo_centro"], r["numero_mesa"]) for r in rows)
    center_totals = center_frame(rows)
    domestic = {c: r for c, r in center_totals.items() if r["cod_estado"] in NATIONAL_CODES}
    exterior = {c: r for c, r in center_totals.items() if r["cod_estado"] == "99"}
    hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): sha256_file(p) for p in [tm_path, prov_path]}
    metadata = {
        "fuente": BASE,
        "fecha_proceso": "2025-05-25",
        "fecha_extraccion": datetime.now(timezone.utc).isoformat(),
        "metodo_extraccion": "HTML/RSC cacheado; estados desde /api/estados; semillas territoriales desde TM 2024 vigente; centros desde enlaces de parroquia; mesas/electores desde paginas de centro",
        "total_paginas": pages_processed,
        "total_estados": len({r["cod_estado"] for r in domestic.values()}),
        "total_municipios": len({(r["cod_estado"], r["cod_municipio"]) for r in domestic.values()}),
        "total_parroquias": len({(r["cod_estado"], r["cod_municipio"], r["cod_parroquia"]) for r in domestic.values()}),
        "total_centros": len(domestic),
        "total_mesas": sum(r["mesas"] for r in domestic.values()),
        "total_electores": sum(r["electores"] for r in domestic.values()),
        "total_exterior": {"centros": len(exterior), "mesas": sum(r["mesas"] for r in exterior.values()), "electores": sum(r["electores"] for r in exterior.values())},
        "hashes": hashes,
        "errores_omisiones": errors,
        "cobertura": {
            "estados_api": states,
            "entidades_api_sin_centros_extraidos": sorted(
                {
                    state["nombre"]
                    for state in states
                    if state["cod_estado"].zfill(2) not in {r["cod_estado"] for r in domestic.values()}
                }
            ),
            "estructuras_especiales": [
                "GUAYANA aparece en /api/estados con cod_estado=26; no se incorporo como entidad con centros unicos. La ruta /guayana/0607/060703/060703003 renderiza el mismo centro 060703003 con estado BOLIVAR.",
                "Exterior no aparece en /api/estados ni en el arbol extraido.",
            ],
            "centros_descubiertos": len(centers),
            "centros_parseados": len(codes),
            "mesas_duplicadas": [f"{k[0]}:{k[1]}" for k, v in mesa_keys.items() if v > 1],
            "centros_sin_mesas": sorted({p["codigo_centro"] for p in provenance if p["observaciones"] == "centro_sin_mesas_parseables"}),
            "discrepancias_total_vs_mesas": sorted({p["codigo_centro"] for p in provenance if str(p["observaciones"]).startswith("total_centro_reportado")}),
        },
        "participacion": participation,
        "verificacion_resumen": verification if isinstance(verification, dict) else {},
        "min_electores_centro": MIN_ELECTORES_CENTRO,
    }
    meta_path = DATA_DIR / "tm_2025_macedonia_metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    hashes[str(meta_path.relative_to(ROOT)).replace("\\", "/")] = sha256_file(meta_path)
    metadata["hashes"] = hashes
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    estado_rows, report = compare(tm_path, metadata, MIN_ELECTORES_CENTRO)
    docs = ROOT / "docs" / "tm"
    docs.mkdir(parents=True, exist_ok=True)
    estados_path = docs / "tm_2024_2025_estados.csv"
    write_csv(estados_path, estado_rows, list(estado_rows[0].keys()) if estado_rows else [])
    report_path = docs / "tm" / "TM_2024_2025_COMPARACION.md" if False else docs / "TM_2024_2025_COMPARACION.md"
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({
        "tm": str(tm_path),
        "provenance": str(prov_path),
        "metadata": str(meta_path),
        "report": str(report_path),
        "estados": str(estados_path),
        "centros": len(domestic),
        "mesas": sum(r["mesas"] for r in domestic.values()),
        "electores": sum(r["electores"] for r in domestic.values()),
        "errors": len(errors),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
