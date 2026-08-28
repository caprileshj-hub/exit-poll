from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "backend/tm_2025_macedonia_estandar.csv",
    "backend/data/2025/tm_2025_macedonia_provenance.csv",
    "backend/data/2025/tm_2025_macedonia_metadata.json",
    "docs/tm/TM_2024_2025_COMPARACION.md",
    "docs/tm/tm_2024_2025_estados.csv",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hash_algorithm": "sha256",
        "files": {name: sha256(ROOT / name) for name in FILES},
    }
    out = ROOT / "backend" / "data" / "2025" / "tm_2025_macedonia_hashes.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(out)
    for name, digest in manifest["files"].items():
        print(f"{digest}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
