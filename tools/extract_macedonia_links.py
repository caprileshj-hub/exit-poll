from __future__ import annotations

import html
import re
import sys
from pathlib import Path


def main() -> int:
    for arg in sys.argv[1:]:
        path = Path(arg)
        text = path.read_text(encoding="utf-8", errors="replace")
        print(f"\n--- {path.name}")
        for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text):
            clean = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", label))).strip()
            print(f"{href}\t{clean[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
