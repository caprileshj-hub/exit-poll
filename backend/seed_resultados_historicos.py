"""Seed versioned historical result CSVs into resultados_historicos.

The files used here are aggregated by voting center. They must not contain
personal data or per-elector records.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd

try:
    import muestra_lab
    from historico_normalizacion import ensure_historico_normalizado_schema
except ImportError:  # pragma: no cover - package import path
    from . import muestra_lab
    from .historico_normalizacion import ensure_historico_normalizado_schema


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
        "incluye_exterior": 0,
        "corte_fuente": "actas publicadas por centro; cobertura parcial",
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
        "incluye_exterior": 0,
        "corte_fuente": "recuperacion parcial Esdata/Wayback",
        "notas": "Recuperacion parcial por centro desde Esdata/Wayback; no cubre el 100% de centros habilitados.",
    },
    {
        "path": BASE_DIR / "resultados_ref2007.csv",
        "eleccion_ref": "2007-referendum",
        "codigo_col": "codigo_centro",
        "fuente": "esdata_wayback",
        "granularidad": "mesa",
        "cobertura_pct": 86.5,
        "comparabilidad": "directa",
        "incluye_exterior": 0,
        "corte_fuente": "primer boletin CNE recuperado",
        "notas": "Referendum constitucional 2007, primer boletin CNE recuperado desde Esdata/Wayback; combina bloques A/B en una tendencia por centro, preservando volumen aproximado de votantes.",
    },
    {
        "path": BASE_DIR / "resultados_enmienda2009.csv",
        "eleccion_ref": "2009-enmienda",
        "codigo_col": "codigo_centro",
        "fuente": "esdata_wayback",
        "granularidad": "mesa",
        "cobertura_pct": 99.0,
        "comparabilidad": "directa",
        "incluye_exterior": 0,
        "corte_fuente": "segundo boletin CNE recuperado",
        "notas": "Enmienda constitucional 2009, segundo boletin CNE recuperado desde Esdata/Wayback y agregado por centro; SI se almacena como gobierno y NO como oposicion.",
    },
    {
        "path": BASE_DIR / "data" / "2018" / "resultados_venpres_a_2018.csv",
        "eleccion_ref": "2018-presidencial",
        "codigo_col": "codigo_centro",
        "fuente": "venpres_a",
        "granularidad": "centro",
        "cobertura_pct": 98.37,
        "comparabilidad": "provisional_arqueologica",
        "incluye_exterior": 0,
        "corte_fuente": "VENPRES-A v1.1; 14.400 centros domesticos agregados; DOI 10.7910/DVN/NO1XJ2",
        "notas": "Presidencial 2018 desde The Venezuelan Presidential Election Archive (VENPRES-A). La columna fuente mesas es cantidad de mesas del centro, no identificador de mesa. Maduro se almacena como gobierno, Falcon como oposicion y Bertucci+Quijada como otros.",
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
        "nulos_col": "votos_nulos",
        "votantes_col": "votos_escrutados",
        "cod_edo_col": "codigo_estado",
        "fuente": "cne_recuperado",
        "granularidad": "mesa",
        "cobertura_pct": 100.0,
        "comparabilidad": "directa",
        "incluye_exterior": 1,
        "corte_fuente": "mesa nacional completo segun archivo recuperado; cod_edo=99 identifica exterior",
        "notas": "Resultado oficial presidencial 2006 por mesa desde archivo historico Esdata/CNE. A diferencia de import_2006.py, el seed normalizado conserva exterior cuando esta presente.",
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
        "nulos_col": "votos nulos",
        "votantes_col": "votantes que_votaron",
        "cod_edo_col": "cod_edo",
        "fuente": "cne_recuperado",
        "granularidad": "mesa",
        "cobertura_pct": 100.0,
        "comparabilidad": "directa",
        "incluye_exterior": 1,
        "corte_fuente": "mesa nacional completo segun archivo recuperado; cod_edo=99 identifica exterior",
        "notas": "Resultado oficial presidencial 2012 por mesa desde archivo historico Esdata/CNE. Los nulos se conservan separados y no integran votos_otros.",
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
        "nulos_col": "votos nulos",
        "votantes_col": "votos escrutados",
        "cod_edo_col": "cod_edo",
        "fuente": "cne_recuperado",
        "granularidad": "mesa",
        "cobertura_pct": 100.0,
        "comparabilidad": "directa",
        "incluye_exterior": 1,
        "corte_fuente": "mesa nacional completo segun archivo recuperado; cod_edo=99 identifica exterior",
        "notas": "Resultado oficial presidencial 2013 por mesa desde archivo historico Esdata/CNE. Los nulos se conservan separados y no integran votos_otros.",
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


def _int_optional(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text.replace(",", ".")))
    except ValueError:
        return None


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


def _upsert_fuente(conn: sqlite3.Connection, dataset: dict, totals: dict | None = None) -> None:
    totals = totals or {}
    conn.execute(
        """
        INSERT INTO historico_fuentes
            (eleccion_ref, fuente, granularidad, cobertura_pct, comparabilidad, notas,
             incluye_exterior, corte_fuente, centros_cubiertos, mesas_cubiertas,
             electores_inscritos, votantes, votos_validos, votos_nulos,
             votos_gobierno, votos_oposicion, votos_otros)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(eleccion_ref) DO UPDATE SET
            fuente=excluded.fuente,
            granularidad=excluded.granularidad,
            cobertura_pct=excluded.cobertura_pct,
            comparabilidad=excluded.comparabilidad,
            notas=excluded.notas,
            incluye_exterior=excluded.incluye_exterior,
            corte_fuente=excluded.corte_fuente,
            centros_cubiertos=excluded.centros_cubiertos,
            mesas_cubiertas=excluded.mesas_cubiertas,
            electores_inscritos=excluded.electores_inscritos,
            votantes=excluded.votantes,
            votos_validos=excluded.votos_validos,
            votos_nulos=excluded.votos_nulos,
            votos_gobierno=excluded.votos_gobierno,
            votos_oposicion=excluded.votos_oposicion,
            votos_otros=excluded.votos_otros,
            updated_at=datetime('now')
        """,
        (
            dataset["eleccion_ref"],
            dataset["fuente"],
            dataset["granularidad"],
            dataset["cobertura_pct"],
            dataset["comparabilidad"],
            dataset["notas"],
            dataset.get("incluye_exterior"),
            dataset.get("corte_fuente"),
            totals.get("centros"),
            totals.get("mesas"),
            totals.get("electores"),
            totals.get("votantes"),
            totals.get("validos"),
            totals.get("nulos"),
            totals.get("gobierno"),
            totals.get("oposicion"),
            totals.get("otros"),
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
                "nulos": 0,
                "votantes": 0,
                "incluye_exterior": 0,
            },
        )
        cod_edo = _int_optional(row.get(dataset.get("cod_edo_col", "")))
        if cod_edo == 99:
            item["incluye_exterior"] = 1
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
        nulos = int(_number(row.get(dataset.get("nulos_col", ""))))
        votantes = int(_number(row.get(dataset.get("votantes_col", "")))) or (validos + nulos if nulos else 0)
        item["gobierno"] += gobierno
        item["oposicion"] += oposicion
        item["otros"] += max(0, otros_cols if otros_cols else validos - gobierno - oposicion)
        item["validos"] += validos
        item["nulos"] += nulos
        item["votantes"] += votantes

    loaded = 0
    totals = {
        "centros": 0,
        "mesas": 0,
        "electores": 0,
        "votantes": 0,
        "validos": 0,
        "nulos": 0,
        "gobierno": 0,
        "oposicion": 0,
        "otros": 0,
    }
    for item in by_center.values():
        validos = int(item["validos"])
        if validos <= 0:
            continue
        nulos = int(item["nulos"])
        votantes = int(item["votantes"]) or (validos + nulos if nulos else None)
        electores = int(item["electores"]) if item["electores"] else None
        mesas = len(item["mesas"]) if item["mesas"] else None
        pct_otros = round(100 * item["otros"] / validos, 6) if validos else None
        participacion = round(100 * votantes / electores, 6) if votantes and electores else None
        conn.execute(
            """
            INSERT INTO resultados_historicos
                (codigo_centro, eleccion_ref,
                 votos_validos, votos_gobierno, votos_oposicion,
                 votos_otros, electores_inscritos, votantes, votos_nulos,
                 pct_gobierno, pct_oposicion, pct_otros, participacion,
                 incluye_exterior, granularidad, fuente, corte_fuente, notas, num_mesas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(codigo_centro, eleccion_ref) DO UPDATE SET
                votos_validos   = excluded.votos_validos,
                votos_gobierno  = excluded.votos_gobierno,
                votos_oposicion = excluded.votos_oposicion,
                votos_otros     = excluded.votos_otros,
                electores_inscritos = excluded.electores_inscritos,
                votantes       = excluded.votantes,
                votos_nulos    = excluded.votos_nulos,
                pct_gobierno    = excluded.pct_gobierno,
                pct_oposicion   = excluded.pct_oposicion,
                pct_otros       = excluded.pct_otros,
                participacion   = excluded.participacion,
                incluye_exterior = excluded.incluye_exterior,
                granularidad    = excluded.granularidad,
                fuente          = excluded.fuente,
                corte_fuente    = excluded.corte_fuente,
                notas           = excluded.notas,
                num_mesas       = excluded.num_mesas
            """,
            (
                item["codigo"],
                ref,
                validos,
                int(item["gobierno"]),
                int(item["oposicion"]),
                int(item["otros"]),
                electores,
                votantes,
                nulos,
                round(100 * item["gobierno"] / validos, 6),
                round(100 * item["oposicion"] / validos, 6),
                pct_otros,
                participacion,
                int(item["incluye_exterior"]),
                dataset["granularidad"],
                dataset["fuente"],
                dataset.get("corte_fuente"),
                dataset["notas"],
                mesas,
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
                mesas,
                electores,
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
        totals["centros"] += 1
        totals["mesas"] += mesas or 0
        totals["electores"] += electores or 0
        totals["votantes"] += votantes or 0
        totals["validos"] += validos
        totals["nulos"] += nulos
        totals["gobierno"] += int(item["gobierno"])
        totals["oposicion"] += int(item["oposicion"])
        totals["otros"] += int(item["otros"])
    _upsert_fuente(conn, dataset, totals)
    return loaded



# ---------------------------------------------------------------------------
# Skip por huella de las fuentes
# ---------------------------------------------------------------------------
# Re-sembrar cuesta ~34 s en SSD local y bastante mas sobre Azure Files, y
# mantiene una transaccion de escritura abierta todo ese tiempo: cualquier
# otra escritura concurrente choca contra el timeout de sqlite y revienta con
# "database is locked". Como el seed corre en cada arranque, esa ventana se
# repetia en cada deploy y en cada reinicio.
#
# La huella cubre tanto los ficheros de origen (tamano + mtime) como los
# metadatos declarados en DATASETS/EXCEL_DATASETS, asi que editar un CSV o
# cambiar la definicion de un dataset vuelve a disparar el seed completo.
_SEED_FINGERPRINT_KEY = "resultados_historicos_fuentes"


def _ensure_seed_state_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seed_state (
            clave       TEXT PRIMARY KEY,
            valor       TEXT NOT NULL,
            updated_at  TEXT DEFAULT (datetime('now'))
        )
    """)


def _fingerprint_fuentes() -> str:
    partes: list = []
    for dataset in list(DATASETS) + list(EXCEL_DATASETS):
        path = Path(dataset["path"])
        try:
            st = path.stat()
            marca = [st.st_size, st.st_mtime_ns]
        except OSError:
            marca = None
        meta = {k: str(v) for k, v in sorted(dataset.items()) if k != "path"}
        partes.append([path.name, marca, meta])
    payload = json.dumps(partes, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _counts_actuales(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT eleccion_ref, COUNT(*) FROM resultados_historicos GROUP BY eleccion_ref"
        )
    }


def seed_resultados_historicos(db_path: str | Path = DB_PATH) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        muestra_lab.ensure_muestra_lab_tables(conn)
        ensure_historico_normalizado_schema(conn)
        _ensure_seed_state_table(conn)

        huella = _fingerprint_fuentes()
        previa = conn.execute(
            "SELECT valor FROM seed_state WHERE clave = ?", (_SEED_FINGERPRINT_KEY,)
        ).fetchone()
        ya_hay_datos = conn.execute(
            "SELECT EXISTS(SELECT 1 FROM resultados_historicos)"
        ).fetchone()[0]
        if previa and previa[0] == huella and ya_hay_datos:
            # Fuentes sin cambios: no hay nada que reescribir.
            return _counts_actuales(conn)

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

            loaded = 0
            totals = {
                "centros": 0,
                "mesas": 0,
                "electores": 0,
                "votantes": 0,
                "validos": 0,
                "nulos": 0,
                "gobierno": 0,
                "oposicion": 0,
                "otros": 0,
            }
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
                    gobierno = _int_value(row.get("votos_gobierno"))
                    oposicion = _int_value(row.get("votos_oposicion"))
                    otros = _int_value(row.get("votos_otros"))
                    nulos = _int_optional(row.get("votos_nulos"))
                    electores = _int_optional(row.get("rep_2004") or row.get("num_electores") or row.get("electores_inscritos"))
                    mesas = _int_optional(row.get("num_mesas"))
                    votantes = _int_optional(row.get("total_votos") or row.get("votantes"))
                    if votantes is None and nulos is not None:
                        votantes = validos + nulos
                    pct_gobierno = round(100 * gobierno / validos, 6) if validos else None
                    pct_oposicion = round(100 * oposicion / validos, 6) if validos else None
                    pct_otros = round(100 * otros / validos, 6) if validos else None
                    participacion = round(100 * votantes / electores, 6) if votantes and electores else None
                    conn.execute(
                        """
                        INSERT INTO resultados_historicos
                            (codigo_centro, eleccion_ref,
                             votos_validos, votos_gobierno, votos_oposicion,
                             votos_otros, electores_inscritos, votantes, votos_nulos,
                             pct_gobierno, pct_oposicion, pct_otros, participacion,
                             incluye_exterior, granularidad, fuente, corte_fuente, notas,
                             num_mesas, detalle_otros_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(codigo_centro, eleccion_ref) DO UPDATE SET
                            votos_validos   = excluded.votos_validos,
                            votos_gobierno  = excluded.votos_gobierno,
                            votos_oposicion = excluded.votos_oposicion,
                            votos_otros     = excluded.votos_otros,
                            electores_inscritos = excluded.electores_inscritos,
                            votantes       = excluded.votantes,
                            votos_nulos    = excluded.votos_nulos,
                            pct_gobierno    = excluded.pct_gobierno,
                            pct_oposicion   = excluded.pct_oposicion,
                            pct_otros       = excluded.pct_otros,
                            participacion   = excluded.participacion,
                            incluye_exterior = excluded.incluye_exterior,
                            granularidad    = excluded.granularidad,
                            fuente          = excluded.fuente,
                            corte_fuente    = excluded.corte_fuente,
                            notas           = excluded.notas,
                            num_mesas       = excluded.num_mesas,
                            detalle_otros_json = excluded.detalle_otros_json
                        """,
                        (
                            codigo,
                            ref,
                            validos,
                            gobierno,
                            oposicion,
                            otros,
                            electores,
                            votantes,
                            nulos,
                            pct_gobierno if pct_gobierno is not None else _float_value(row.get("pct_gobierno")),
                            pct_oposicion if pct_oposicion is not None else _float_value(row.get("pct_oposicion")),
                            pct_otros,
                            participacion,
                            dataset.get("incluye_exterior"),
                            dataset["granularidad"],
                            dataset["fuente"],
                            dataset.get("corte_fuente"),
                            dataset["notas"],
                            mesas,
                            (row.get("detalle_otros_json") or "").strip() or None,
                        ),
                    )
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
                    totals["centros"] += 1
                    totals["mesas"] += mesas or 0
                    totals["electores"] += electores or 0
                    totals["votantes"] += votantes or 0
                    totals["validos"] += validos
                    totals["nulos"] += nulos or 0
                    totals["gobierno"] += gobierno
                    totals["oposicion"] += oposicion
                    totals["otros"] += otros
            counts[ref] = loaded
            _upsert_fuente(conn, dataset, totals)
        for dataset in EXCEL_DATASETS:
            counts[str(dataset["eleccion_ref"])] = _seed_excel_dataset(conn, dataset)
        conn.execute("""
            INSERT INTO seed_state (clave, valor, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(clave) DO UPDATE
                SET valor = excluded.valor, updated_at = excluded.updated_at
        """, (_SEED_FINGERPRINT_KEY, huella))
        conn.commit()
        return counts
    finally:
        conn.close()


if __name__ == "__main__":
    stats = seed_resultados_historicos()
    print("Resultados historicos seed:", stats)
