from __future__ import annotations

import hashlib
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "https://asamblea.macedoniadelnorte.com/"
OUT_DIR = Path(__file__).resolve().parents[1] / "backend" / "data" / "2025" / "macedonia_cache"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def cache_name(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    suffix = Path(parsed.path).suffix or ".html"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.path.strip("/") or "index")
    return f"{safe[:120]}__{digest}{suffix}"


def cached_fetch(url: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / cache_name(url)
    if not path.exists():
        path.write_bytes(fetch(url))
        time.sleep(0.25)
    return path


def main() -> int:
    routes = sys.argv[1:] or ["/"]
    for route in routes:
        url = urllib.parse.urljoin(BASE_URL, route)
        page = cached_fetch(url)
        html = page.read_text(encoding="utf-8", errors="replace")
        scripts = sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', html)))
        scripts = [urllib.parse.urljoin(BASE_URL, s) for s in scripts]
        print(f"page={url} cache={page} bytes={page.stat().st_size} scripts={len(scripts)}")
        for script in scripts:
            print(script)
            cached_fetch(script)
        time.sleep(0.25)

    patterns = [
        re.compile(r"https?://[^'\"\\\s)]+"),
        re.compile(r"/(?:api|_next/data|data|assets|static|resultados|centros|estado|municipio|parroquia)[^'\"\\\s)]*"),
    ]
    hits: set[str] = set()
    for path in OUT_DIR.glob("*"):
        if path.suffix not in {".js", ".html", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pat in patterns:
            for match in pat.findall(text):
                if any(token in match.lower() for token in ["api", "json", "csv", "centro", "estado", "municip", "parroquia", "result"]):
                    hits.add(match)

    print("\nHITS")
    for hit in sorted(hits):
        print(hit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
