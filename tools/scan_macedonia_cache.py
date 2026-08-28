from __future__ import annotations

import re
from pathlib import Path


CACHE = Path(__file__).resolve().parents[1] / "backend" / "data" / "2025" / "macedonia_cache"
KEYS = [
    "/api/",
    "cod_centro",
    "centros",
    "municipios",
    "parroquias",
    "resultados",
    "fetch(",
]


def main() -> int:
    for path in sorted(CACHE.glob("*.js")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not any(key in text for key in KEYS):
            continue
        print(f"\n--- {path.name} {len(text)}")
        print("contains:", ", ".join(key for key in KEYS if key in text))
        for key in KEYS:
            for match in re.finditer(re.escape(key), text):
                start = max(0, match.start() - 220)
                end = min(len(text), match.end() + 360)
                snippet = text[start:end].replace("\\x", " x")
                print(snippet[:700])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
