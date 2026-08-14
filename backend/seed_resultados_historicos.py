"""Seed versioned historical result CSVs into resultados_historicos.

The files used here are aggregated by voting center. They must not contain
personal data or per-elector records.
"""

from __future__ import annotations

import csv
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd

try:
    import muestra_lab
except ImportError:  # pragma: no cover - package import path
    from . import muestra_lab


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "exitpoll.db"

DATASETS = [
    {
        "path": BASE_DIR / "resultados_cne2024.csv",
        "eleccion_ref": "2024-presidencial",
        "codigo_col": "centro_cne_id",
        "fuente": "actas_cvzla",
        "granularidad": "centro",
        "cobertura_pct": 81.0,
        "comparabilidad": "directa",
        "notas": "Actas agregadas por centro desde ComandoConVzla; cobertura parcial y no aleatoria.",
    },
    {
        "path": BASE_DIR / "resultados_rr2004.csv",
        "eleccion_ref": "2004-revocatorio",
        "codigo_col": "codigo_centro",
        "fuente": "esdata_wayback",
        "granularidad": "centro",
        "cobertura_pct": 91.4,
        "comparabilidad": "directa",
        "notas": "Recuperacion parcial por centro desde Esdata/Wayback; no cubre el 100% de centros habilitados.",
    },
]

EXCEL_DATASETS = [
    {
        "path": BASE_DIR / "data" / "2006" / "resultado elecciones presidenciales 2006.xlsx",
        "eleccion_ref": "2006-presidencial",
        "sheet": "resultados_2006-12-03",
        "codigo_col": "codigo_centro_nuevo",
        "codigo_viejo_col": "codigo_centro_viejo",
        "nombre_col": "centro",
        "mesa_col": "mesa",
        "electores_col": "inscritos_rep",
        "gobierno_cols": ["votos_chavez"],
        "oposicion_cols": ["votos_rosales"],
        "otros_cols": [],
        "validos_col": "votos_validos",
        "fuente": "cne_recuperado",
        "granularidad": "mesa",
        "cobertura_pct": 100.0,
        "comparabilidad": "directa",
        "notas": "Resultado oficial presidencial 2006 por mesa desde archivo historico Esdata/CNE.",
    },
    {
        "path": BASE_DIR / "data" / "2012" / "presidenciales" / "resultados oficiales presidenciales 2012.xlsx",
        "eleccion_ref": "2012-presidencial",
        "sheet": "resultados_2012-10-07",
        "codigo_col": "codigo nuevo",
        "codigo_viejo_col": "codigo viejo",
        "nombre_col": "centro",
        "mesa_col": "mesa",
        "electores_col": "electores escrutados",
        "gobierno_cols": ["chavez"],
        "oposicion_cols": ["capriles"],
        "otros_cols": ["chirino", "sequera", "reyes", "bolivar"],
        "validos_col": "votos validos",
        "fuente": "cne_recuperado",
        "granularidad": "mesa",
        "cobertura_pct": 100.0,
        "comparabilidad": "directa",
        "notas": "Resultado oficial presidencial 2012 por mesa desde archivo historico Esdata/CNE.",
    },
    {
        "path": BASE_DIR / "data" / "2013" / "presidenciales" / "resultados oficiales elecciones presidenciales 2013.xlsx",
        "eleccion_ref": "2013-presidencial",
        "sheet": "resultados_2013-04-14",
        "codigo_col": "codigo nuevo",
        "codigo_viejo_col": "codigo viejo",
        "nombre_col": "centro",
        "mesa_col": "mesa",
        "electores_col": "electores esperados",
        "gobierno_cols": ["maduro"],
        "oposicion_cols": ["capriles"],
        "otros_cols": ["sequera", "bolivar", "mora", "mendez"],
        "validos_col": "votos validos",
        "fuente": "cne_recuperado",
        "granularidad": "mesa",
        "cobertura_pct": 100.0,
        "comparabilidad": "directa",
        "notas": "Resultado oficial presidencial 2013 por mesa desde archivo historico Esdata/CNE.",
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


def _norm_col(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    return " ".join(text.replace("\n", " ").strip().lower().split())


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


def _upsert_fuente(conn: sqlite3.Connection, dataset: dict) -> None:
    conn.execute(
        """
        INSERT INTO historico_fuentes
            (eleccion_ref, fuente, granularidad, cobertura_pct, comparabilidad, notas)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(eleccion_ref) DO UPDATE SET
            fuente=excluded.fuente,
            granularidad=excluded.granularidad,
            cobertura_pct=excluded.cobertura_pct,
            comparabilidad=excluded.comparabilidad,
            notas=excluded.notas,
            updated_at=datetime('now')
        """,
        (
            dataset["eleccion_ref"],
            dataset["fuente"],
            dataset["granularidad"],
            dataset["cobertura_pct"],
            dataset["comparabilidad"],
            dataset["notas"],
        ),
    )


def _seed_excel_dataset(conn: sqlite3.Connection, dataset: dict) -> int:
    path = Path(dataset["path"])
    ref = str(dataset["eleccion_ref"])
    if not path.exists():
        return 0

    conn.execute("DELETE FROM resultados_historicos WHERE eleccion_ref=?", (ref,))
    conn.execute("DELETE FROM centro_snapshot WHERE eleccion_ref=?", (ref,))
    df = pd.read_excel(path, sheet_name=dataset["sheet"])
    df = df.rename(columns={col: _norm_col(col) for col in df.columns})
    _upsert_fuente(conn, dataset)

    by_center: dict[str, dict] = {}
    for _, row in df.iterrows():
        codigo = _code9(row.get(dataset["codigo_col"]))
        if not codigo:
            continue
        item = by_center.setdefault(
            codigo,
            {
                "codigo": codigo,
                "codigo_viejo": "",
                "nombre": "",
                "mesas": set(),
                "electores": 0,
                "gobierno": 0,
                "oposicion": 0,
                "otros": 0,
                "validos": 0,
            },
        )
        codigo_viejo = str(row.get(dataset["codigo_viejo_col"]) or "").strip()
        if codigo_viejo and not item["codigo_viejo"]:
            if codigo_viejo.endswith(".0"):
                codigo_viejo = codigo_viejo[:-2]
            item["codigo_viejo"] = "".join(ch for ch in codigo_viejo if ch.isdigit())
        if not item["nombre"]:
            item["nombre"] = str(row.get(dataset["nombre_col"]) or "").strip()
        mesa = row.get(dataset["mesa_col"])
        if mesa is not None and str(mesa).strip():
            item["mesas"].add(str(int(_number(mesa))))
        item["electores"] += int(_number(row.get(dataset["electores_col"])))
        gobierno = sum(int(_number(row.get(col))) for col in dataset["gobierno_cols"])
        oposicion = sum(int(_number(row.get(col))) for col in dataset["oposicion_cols"])
        otros_cols = sum(int(_number(row.get(col))) for col in dataset["otros_cols"])
        validos = int(_number(row.get(dataset["validos_col"]))) or (gobierno + oposicion + otros_cols)
        item["gobierno"] += gobierno
        item["oposicion"] += oposicion
        item["otros"] += max(0, otros_cols if otros_cols else validos - gobierno - oposicion)
        item["validos"] += validos

    loaded = 0
    for item in by_center.values():
        validos = int(item["validos"])
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
                item["codigo"],
                ref,
                validos,
                int(item["gobierno"]),
                int(item["oposicion"]),
                int(item["otros"]),
                round(100 * item["gobierno"] / validos, 6),
                round(100 * item["oposicion"] / validos, 6),
            ),
        )
        conn.execute(
            """
            INSERT INTO centro_snapshot
                (codigo_cne, eleccion_ref, nombre_centro, num_mesas, num_electores, fuente)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(codigo_cne, eleccion_ref) DO UPDATE SET
                nombre_centro=COALESCE(excluded.nombre_centro, centro_snapshot.nombre_centro),
                num_mesas=excluded.num_mesas,
                num_electores=excluded.num_electores,
                fuente=excluded.fuente
            """,
            (
                item["codigo"],
                ref,
                item["nombre"] or None,
                len(item["mesas"]),
                int(item["electores"]),
                dataset["fuente"],
            ),
        )
        if item["codigo_viejo"] and item["codigo_viejo"] != item["codigo"]:
            conn.execute(
                """
                INSERT OR REPLACE INTO centro_codigos
                    (codigo_cne, codigo_alterno, tipo_codigo, fuente, confianza_match)
                VALUES (?, ?, 'codigo_viejo', ?, 1.0)
                """,
                (item["codigo"], item["codigo_viejo"], dataset["fuente"]),
            )
        loaded += 1
    return loaded


def seed_resultados_historicos(db_path: str | Path = DB_PATH) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        muestra_lab.ensure_muestra_lab_tables(conn)
        counts: dict[str, int] = {}
        for dataset in DATASETS:
            path = Path(dataset["path"])
            ref = str(dataset["eleccion_ref"])
            codigo_col = str(dataset["codigo_col"])
            if not path.exists():
                counts[ref] = 0
                continue
            conn.execute("DELETE FROM resultados_historicos WHERE eleccion_ref=?", (ref,))
            conn.execute("DELETE FROM centro_snapshot WHERE eleccion_ref=?", (ref,))
            _upsert_fuente(conn, dataset)

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
                    electores = _int_value(row.get("rep_2004") or row.get("num_electores"))
                    mesas = _int_value(row.get("num_mesas"))
                    nombre_centro = (row.get("nombre_centro") or "").strip() or None
                    if electores or mesas or nombre_centro:
                        conn.execute(
                            """
                            INSERT INTO centro_snapshot
                                (codigo_cne, eleccion_ref, nombre_centro, num_mesas, num_electores, fuente)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(codigo_cne, eleccion_ref) DO UPDATE SET
                                nombre_centro=COALESCE(excluded.nombre_centro, centro_snapshot.nombre_centro),
                                num_mesas=excluded.num_mesas,
                                num_electores=excluded.num_electores,
                                fuente=excluded.fuente
                            """,
                            (codigo, ref, nombre_centro, mesas, electores, dataset["fuente"]),
                        )
                    codigo_viejo = (row.get("codigo_viejo") or row.get("codigo_cne_viejo") or "").strip()
                    if codigo_viejo and codigo_viejo != codigo:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO centro_codigos
                                (codigo_cne, codigo_alterno, tipo_codigo, fuente, confianza_match)
                            VALUES (?, ?, 'codigo_viejo', ?, 1.0)
                            """,
                            (codigo, codigo_viejo, dataset["fuente"]),
                        )
                    loaded += 1
            counts[ref] = loaded
        for dataset in EXCEL_DATASETS:
            counts[str(dataset["eleccion_ref"])] = _seed_excel_dataset(conn, dataset)
        conn.commit()
        return counts
    finally:
        conn.close()


if __name__ == "__main__":
    stats = seed_resultados_historicos()
    print("Resultados historicos seed:", stats)
