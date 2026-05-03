"""
Seed de la eleccion presidencial 2006 desde archivos historicos.

Archivos esperados en backend/data/2006/:
  - resultado_elecciones_presidenciales_2006.xlsx
  - Presentacion_Basica_Copia5.xls

Uso:
  python seed_2006.py [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import unicodedata
from typing import Any

import pandas as pd

import init_db
from cargador_tm import normalizar, obtener_o_crear


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "exitpoll.db")
DATA_DIR = os.path.join(BASE_DIR, "data", "2006")
ELECCION_REF = "2006-presidencial"
FUENTE_CNE = "Esdata_2006"


def _data_path(*names: str) -> str:
    for name in names:
        path = os.path.join(DATA_DIR, name)
        if os.path.exists(path):
            return path
    return os.path.join(DATA_DIR, names[0])


CNE_2006_PATH = _data_path(
    "resultado_elecciones_presidenciales_2006.xlsx",
    "resultado elecciones presidenciales 2006.xlsx",
)
CAMPO_2006_PATH = _data_path(
    "Presentacion_Basica_Copia5.xls",
    "Presentacion Basica Copia5.xls",
)


def to_cne(edo: Any, mun: Any, par: Any, seq: Any) -> str:
    return f"{_to_int(edo):02d}{_to_int(mun):02d}{_to_int(par):02d}{_to_int(seq):03d}"


def _to_int(value: Any) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    text = str(value).strip()
    if text == "" or text.upper() in {"NAN", "NONE"}:
        return 0
    if re.fullmatch(r"-?\d+(\.0+)?", text):
        return int(float(text))
    digits = re.sub(r"[^\d-]+", "", text)
    if digits in {"", "-"}:
        return 0
    return int(digits)


def _code9(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.0+)?", text):
        return f"{int(float(text)):09d}"
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits.zfill(9) if digits else ""


def _row_to_cne(row: pd.Series) -> str:
    try:
        parts = [_to_int(row[col]) for col in ["Entidad", "Municipio", "Parroquia", "Centro"]]
        if any(part <= 0 for part in parts):
            return ""
        return to_cne(*parts)
    except (TypeError, ValueError):
        return ""


def _strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip().lower()


def _rename_aliases(df: pd.DataFrame, aliases: dict[str, list[str]], source_name: str) -> pd.DataFrame:
    rename: dict[str, str] = {}
    folded = {_fold(col): col for col in df.columns}
    for canonical, candidates in aliases.items():
        if canonical in df.columns:
            continue
        match = next((folded[_fold(candidate)] for candidate in candidates if _fold(candidate) in folded), None)
        if match:
            rename[match] = canonical
    df = df.rename(columns=rename)
    _require_columns(df, list(aliases), source_name)
    return df


def _require_columns(df: pd.DataFrame, required: list[str], source_name: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{source_name} no contiene columnas requeridas: {', '.join(missing)}")


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return column in {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _insert_eleccion(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        """
        SELECT id FROM elecciones
        WHERE fecha=? AND tipo=? AND nombre=?
        """,
        ("2006-12-03", "nacional", "Elección Presidencial 2006"),
    ).fetchone()
    notas_col = _has_column(conn, "elecciones", "notas")
    if row:
        if notas_col:
            conn.execute("UPDATE elecciones SET activa=0, notas=NULL WHERE id=?", (row[0],))
        else:
            conn.execute("UPDATE elecciones SET activa=0 WHERE id=?", (row[0],))
        return int(row[0])

    if notas_col:
        cur = conn.execute(
            """
            INSERT INTO elecciones
                (fecha, tipo, nombre, activa, notas)
            VALUES (?, ?, ?, 0, NULL)
            """,
            ("2006-12-03", "nacional", "Elección Presidencial 2006"),
        )
    else:
        cur = conn.execute(
            """
            INSERT INTO elecciones
                (fecha, tipo, nombre, activa)
            VALUES (?, ?, ?, 0)
            """,
            ("2006-12-03", "nacional", "Elección Presidencial 2006"),
        )
    return int(cur.lastrowid)


def _upsert_candidato(
    conn: sqlite3.Connection,
    id_eleccion: int,
    nombre: str,
    partido: str,
    bando: str,
    orden: int,
) -> None:
    row = conn.execute(
        "SELECT id FROM candidatos WHERE id_eleccion=? AND nombre=?",
        (id_eleccion, nombre),
    ).fetchone()
    if row:
        conn.execute(
            """
            UPDATE candidatos
            SET partido=?, bando=?, tipo='unico', orden=?
            WHERE id=?
            """,
            (partido, bando, orden, row[0]),
        )
        return
    conn.execute(
        """
        INSERT INTO candidatos
            (id_eleccion, nombre, partido, bando, tipo, orden)
        VALUES (?, ?, ?, ?, 'unico', ?)
        """,
        (id_eleccion, nombre, partido, bando, orden),
    )


def _insert_candidatos(conn: sqlite3.Connection, id_eleccion: int) -> None:
    _upsert_candidato(conn, id_eleccion, "Hugo Chávez Frías", "MVR", "gobierno", 1)
    _upsert_candidato(conn, id_eleccion, "Manuel Rosales", "MUD", "oposicion", 2)


def _load_cne_2006() -> pd.DataFrame:
    if not os.path.exists(CNE_2006_PATH):
        raise FileNotFoundError(f"No existe {CNE_2006_PATH}")
    df = _strip_columns(pd.read_excel(CNE_2006_PATH, dtype=str))
    df = _rename_aliases(
        df,
        {
            "codigo_estado": ["codigo_estado"],
            "estado": ["estado"],
            "codigo_municipio": ["codigo_municipio"],
            "municipio": ["municipio"],
            "codigo_parroquia": ["codigo_parroquia"],
            "parroquia": ["parroquia"],
            "codigo_centro_nuevo": ["codigo_centro_nuevo"],
            "centro": ["centro"],
            "mesa": ["mesa"],
            "votos_rosales": ["votos_rosales"],
            "votos_chavez": ["votos_chavez", "votos_chávez"],
            "inscritos_rep": ["inscritos_rep"],
            "votos_validos": ["votos_validos", "votos_válidos"],
            "votos_nulos": ["votos_nulos"],
        },
        os.path.basename(CNE_2006_PATH),
    )
    df["codigo_cne"] = df["codigo_centro_nuevo"].map(_code9)
    df = df[df["codigo_cne"] != ""].copy()
    for col in ["mesa", "votos_rosales", "votos_chavez", "inscritos_rep", "votos_validos", "votos_nulos"]:
        df[col] = df[col].map(_to_int)
    return df


def _load_campo_2006() -> pd.DataFrame:
    if not os.path.exists(CAMPO_2006_PATH):
        raise FileNotFoundError(f"No existe {CAMPO_2006_PATH}")
    aliases = {
        "Turno": ["Turno"],
        "Entidad": ["Entidad"],
        "Municipio": ["Municipio"],
        "Parroquia": ["Parroquia"],
        "Centro": ["Centro"],
        "Hugo Chavez": ["Hugo Chavez", "Hugo Chávez"],
        "Manuel Rosales": ["Manuel Rosales"],
        "Otros": ["Otros"],
        "Nulos": ["Nulos"],
    }
    last_error: Exception | None = None
    for skiprows in (1, 2, 0):
        try:
            df = _strip_columns(pd.read_excel(CAMPO_2006_PATH, sheet_name="Entrada", skiprows=skiprows, dtype=str))
            df = _rename_aliases(df, aliases, os.path.basename(CAMPO_2006_PATH))
            break
        except ValueError as exc:
            last_error = exc
    else:
        raise last_error or ValueError(f"No se pudo leer {CAMPO_2006_PATH}")
    df = df.dropna(how="all").copy()
    df["turno"] = df["Turno"].map(_to_int)
    df["codigo_cne"] = df.apply(_row_to_cne, axis=1)
    for col in ["Hugo Chavez", "Manuel Rosales", "Otros", "Nulos"]:
        df[col] = df[col].map(_to_int)
    df = df[(df["codigo_cne"] != "") & (df["turno"] > 0)].copy()
    return df


def _upsert_centros(conn: sqlite3.Connection, cne_df: pd.DataFrame) -> int:
    loaded = 0
    grouped = (
        cne_df.groupby("codigo_cne", as_index=False)
        .agg(
            nombre=("centro", "first"),
            codigo_estado=("codigo_estado", "first"),
            estado=("estado", "first"),
            codigo_municipio=("codigo_municipio", "first"),
            municipio=("municipio", "first"),
            codigo_parroquia=("codigo_parroquia", "first"),
            parroquia=("parroquia", "first"),
            num_mesas=("mesa", "count"),
            num_electores=("inscritos_rep", "sum"),
        )
    )

    for _, row in grouped.iterrows():
        id_estado = obtener_o_crear(
            conn,
            "estados",
            {"codigo_cne": f"{_to_int(row['codigo_estado']):02d}"},
            {"nombre": normalizar(row["estado"]), "es_excepcion": 0},
        )
        id_municipio = obtener_o_crear(
            conn,
            "municipios",
            {"id_estado": id_estado, "codigo_cne": f"{_to_int(row['codigo_municipio']):02d}"},
            {"nombre": normalizar(row["municipio"])},
        )
        id_parroquia = obtener_o_crear(
            conn,
            "parroquias",
            {"id_municipio": id_municipio, "codigo_cne": f"{_to_int(row['codigo_parroquia']):02d}"},
            {"nombre": normalizar(row["parroquia"])},
        )

        existing = conn.execute(
            "SELECT codigo_cne FROM centros WHERE codigo_cne=?",
            (row["codigo_cne"],),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE centros
                SET num_mesas=?,
                    num_electores=?,
                    id_estado=?,
                    id_municipio=?,
                    id_parroquia=?,
                    activo=1
                WHERE codigo_cne=?
                """,
                (
                    int(row["num_mesas"]),
                    int(row["num_electores"]),
                    id_estado,
                    id_municipio,
                    id_parroquia,
                    row["codigo_cne"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO centros
                    (codigo_cne, nombre, id_estado, id_municipio, id_parroquia,
                     num_mesas, num_electores, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    row["codigo_cne"],
                    normalizar(row["nombre"]),
                    id_estado,
                    id_municipio,
                    id_parroquia,
                    int(row["num_mesas"]),
                    int(row["num_electores"]),
                ),
            )
        loaded += 1
    return loaded


def _insert_resultados_mesa(conn: sqlite3.Connection, id_eleccion: int, cne_df: pd.DataFrame) -> int:
    loaded = 0
    for _, row in cne_df.iterrows():
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO resultados_mesa
                (id_eleccion, codigo_cne, numero_mesa, votos_gov, votos_opos,
                 votos_otros, votos_nulos, votos_validos, inscritos, fuente)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (
                id_eleccion,
                row["codigo_cne"],
                int(row["mesa"]),
                int(row["votos_chavez"]),
                int(row["votos_rosales"]),
                int(row["votos_nulos"]),
                int(row["votos_validos"]),
                int(row["inscritos_rep"]),
                FUENTE_CNE,
            ),
        )
        loaded += 1
    return loaded


def _upsert_resultados_historicos(conn: sqlite3.Connection, cne_df: pd.DataFrame) -> int:
    loaded = 0
    grouped = (
        cne_df.groupby("codigo_cne", as_index=False)
        .agg(
            votos_validos=("votos_validos", "sum"),
            votos_gobierno=("votos_chavez", "sum"),
            votos_oposicion=("votos_rosales", "sum"),
        )
    )
    for _, row in grouped.iterrows():
        validos = int(row["votos_validos"])
        gov = int(row["votos_gobierno"])
        opos = int(row["votos_oposicion"])
        pct_gov = round(gov * 100.0 / validos, 2) if validos else None
        pct_opos = round(opos * 100.0 / validos, 2) if validos else None
        conn.execute(
            """
            INSERT INTO resultados_historicos
                (codigo_centro, eleccion_ref, votos_validos, votos_gobierno,
                 votos_oposicion, votos_otros, pct_gobierno, pct_oposicion)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(codigo_centro, eleccion_ref) DO UPDATE SET
                votos_validos=excluded.votos_validos,
                votos_gobierno=excluded.votos_gobierno,
                votos_oposicion=excluded.votos_oposicion,
                votos_otros=excluded.votos_otros,
                pct_gobierno=excluded.pct_gobierno,
                pct_oposicion=excluded.pct_oposicion
            """,
            (row["codigo_cne"], ELECCION_REF, validos, gov, opos, pct_gov, pct_opos),
        )
        loaded += 1
    return loaded


def _insert_reportes_campo(conn: sqlite3.Connection, id_eleccion: int, campo_df: pd.DataFrame) -> tuple[int, int, int]:
    codigos = sorted(set(campo_df["codigo_cne"]))
    existentes = {
        row[0]
        for row in conn.execute(
            f"SELECT codigo_cne FROM centros WHERE codigo_cne IN ({','.join('?' for _ in codigos)})",
            codigos,
        ).fetchall()
    } if codigos else set()
    faltantes = set(codigos) - existentes

    muestra_loaded = 0
    for codigo in sorted(existentes):
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO muestra
                (id_eleccion, codigo_centro, tipo_centro, activo)
            VALUES (?, ?, 'estandar', 1)
            """,
            (id_eleccion, codigo),
        )
        muestra_loaded += max(cur.rowcount, 0)

    reportes_loaded = 0
    for _, row in campo_df[campo_df["codigo_cne"].isin(existentes)].iterrows():
        conn.execute(
            """
            INSERT INTO reportes_campo
                (id_eleccion, codigo_cne, turno, votos_gov, votos_opos, votos_otros, votos_nulos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_eleccion,
                row["codigo_cne"],
                int(row["turno"]),
                int(row["Hugo Chavez"]),
                int(row["Manuel Rosales"]),
                int(row["Otros"]),
                int(row["Nulos"]),
            ),
        )
        reportes_loaded += 1
    return muestra_loaded, reportes_loaded, len(faltantes)


def seed_2006(dry_run: bool = False) -> dict[str, int]:
    conn = init_db.init_db(reset=False)
    init_db.migrar(conn)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    cne_df = _load_cne_2006()
    campo_df = _load_campo_2006()

    stats: dict[str, int] = {}
    try:
        conn.execute("BEGIN IMMEDIATE")
        id_eleccion = _insert_eleccion(conn)
        _insert_candidatos(conn, id_eleccion)
        stats["centros_loaded"] = _upsert_centros(conn, cne_df)
        stats["mesas_loaded"] = _insert_resultados_mesa(conn, id_eleccion, cne_df)
        stats["historicos_loaded"] = _upsert_resultados_historicos(conn, cne_df)
        muestra_loaded, reportes_loaded, campo_sin_centro = _insert_reportes_campo(conn, id_eleccion, campo_df)
        stats["muestra_loaded"] = muestra_loaded
        stats["field_reports_loaded"] = reportes_loaded
        stats["field_centers_missing"] = campo_sin_centro

        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed historico presidencial 2006")
    parser.add_argument("--dry-run", action="store_true", help="Lee y valida sin conservar cambios de datos")
    args = parser.parse_args()

    stats = seed_2006(dry_run=args.dry_run)
    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}Resumen 2006:")
    print(f"    centros loaded:        {stats['centros_loaded']:>6,}")
    print(f"    mesas loaded:          {stats['mesas_loaded']:>6,}")
    print(f"    historicos loaded:     {stats['historicos_loaded']:>6,}")
    print(f"    muestra loaded:        {stats['muestra_loaded']:>6,}")
    print(f"    field reports loaded:  {stats['field_reports_loaded']:>6,}")
    if stats["field_centers_missing"]:
        print(f"    field centers missing: {stats['field_centers_missing']:>6,}")


if __name__ == "__main__":
    main()
