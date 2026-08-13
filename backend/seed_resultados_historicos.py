"""Seed versioned historical result CSVs into resultados_historicos.

The files used here are aggregated by voting center. They must not contain
personal data or per-elector records.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "exitpoll.db"

DATASETS = [
    {
        "path": BASE_DIR / "resultados_cne2024.csv",
        "eleccion_ref": "2024-presidencial",
        "codigo_col": "centro_cne_id",
    },
    {
        "path": BASE_DIR / "resultados_rr2004.csv",
        "eleccion_ref": "2004-revocatorio",
        "codigo_col": "codigo_centro",
    },
]

FORBIDDEN_COLUMNS = {
    "cedula", "ci", "nacionalidad", "nombre", "nombres", "apellido", "apellidos",
    "telefono", "direccion_habitacion", "fecha_nacimiento", "elector",
}


def _int_value(value: str | None) -> int:
    if value in (None, ""):
        return 0
    return int(float(str(value).replace(",", ".")))


def _float_value(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(str(value).replace(",", "."))


def seed_resultados_historicos(db_path: str | Path = DB_PATH) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        counts: dict[str, int] = {}
        for dataset in DATASETS:
            path = Path(dataset["path"])
            ref = str(dataset["eleccion_ref"])
            codigo_col = str(dataset["codigo_col"])
            if not path.exists():
                counts[ref] = 0
                continue

            loaded = 0
            with path.open("r", newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                headers = {h.strip().lower() for h in (reader.fieldnames or [])}
                pii = sorted(headers & FORBIDDEN_COLUMNS)
                if pii:
                    raise ValueError(f"{path.name} contiene columnas PII no permitidas: {', '.join(pii)}")

                for row in reader:
                    codigo_raw = (row.get(codigo_col) or "").strip()
                    if not codigo_raw:
                        continue
                    codigo = codigo_raw.zfill(9)
                    validos = _int_value(row.get("votos_validos"))
                    if validos <= 0:
                        continue
                    conn.execute(
                        """
                        INSERT INTO resultados_historicos
                            (codigo_centro, eleccion_ref,
                             votos_validos, votos_gobierno, votos_oposicion,
                             votos_otros, pct_gobierno, pct_oposicion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(codigo_centro, eleccion_ref) DO UPDATE SET
                            votos_validos   = excluded.votos_validos,
                            votos_gobierno  = excluded.votos_gobierno,
                            votos_oposicion = excluded.votos_oposicion,
                            votos_otros     = excluded.votos_otros,
                            pct_gobierno    = excluded.pct_gobierno,
                            pct_oposicion   = excluded.pct_oposicion
                        """,
                        (
                            codigo,
                            ref,
                            validos,
                            _int_value(row.get("votos_gobierno")),
                            _int_value(row.get("votos_oposicion")),
                            _int_value(row.get("votos_otros")),
                            _float_value(row.get("pct_gobierno")),
                            _float_value(row.get("pct_oposicion")),
                        ),
                    )
                    loaded += 1
            counts[ref] = loaded
        conn.commit()
        return counts
    finally:
        conn.close()


if __name__ == "__main__":
    stats = seed_resultados_historicos()
    print("Resultados historicos seed:", stats)
