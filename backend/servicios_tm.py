from __future__ import annotations

import asyncio
import io
import json
import re
import sqlite3
import unicodedata
import uuid
from typing import Any


TM_AI_CHUNK_SIZE = 15000


def _extraer_texto_pdf_sincrono(contenido_binario: bytes) -> str:
    """Extract PDF text in a worker thread caller, not in the event loop."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("Falta dependencia pdfplumber para leer PDF") from exc

    lines: list[str] = []
    with pdfplumber.open(io.BytesIO(contenido_binario)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            lines.append(f"### PAGE {i}")
            lines.append(page.extract_text() or "")
    return "\n".join(lines)


async def extraer_texto_pdf_async(contenido_binario: bytes) -> str:
    """Run CPU-heavy PDF parsing outside FastAPI's event loop."""
    return await asyncio.to_thread(_extraer_texto_pdf_sincrono, contenido_binario)


def fragmentar_texto(texto: str, max_caracteres: int = TM_AI_CHUNK_SIZE) -> list[str]:
    """Split text into LLM-sized chunks, preferring line boundaries."""
    texto = texto or ""
    if len(texto) <= max_caracteres:
        return [texto]

    chunks: list[str] = []
    pos = 0
    while pos < len(texto):
        end = min(len(texto), pos + max_caracteres)
        cut = texto.rfind("\n", pos, end)
        if cut <= pos + 1000:
            cut = end
        chunks.append(texto[pos:cut])
        pos = cut
    return chunks


def _normalize_match_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _canonical_estado_name(value: Any) -> str:
    name = _normalize_match_text(value or "")
    if name in {"VARGAS", "EDO VARGAS", "ESTADO VARGAS", "LA GUAIRA", "EDO LA GUAIRA", "ESTADO LA GUAIRA"}:
        return "LA GUAIRA"
    return name


def _to_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    match = re.search(r"\d+", str(value).replace(".", "").replace(",", ""))
    return int(match.group(0)) if match else None


def _normalize_center_code(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    first_part = raw.split(".", 1)[0].strip()
    if first_part.isdigit() and len(first_part) >= 6:
        return first_part
    digits = re.sub(r"\D+", "", raw)
    return digits or raw.upper()


def _digits_code(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _estado_code_from_centro(centro: dict[str, Any], codigo: str | None = None) -> str:
    estado = _digits_code(centro.get("cod_estado"))
    if estado:
        return estado.zfill(2)[-2:]
    codigo_norm = _normalize_center_code(codigo or centro.get("codigo_centro") or centro.get("codigo_cne"))
    if codigo_norm.isdigit() and len(codigo_norm) >= 2:
        return codigo_norm[:2]
    return ""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_tm_ai_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS election_centers (
            eleccion_id     INTEGER NOT NULL REFERENCES elecciones(id),
            centro_id       TEXT NOT NULL REFERENCES centros(codigo_cne),
            eligible        INTEGER NOT NULL DEFAULT 1,
            source_file     TEXT,
            campos_extra    TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            PRIMARY KEY(eleccion_id, centro_id),
            CHECK(eligible IN (0,1))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ec_eleccion ON election_centers(eleccion_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ec_centro ON election_centers(centro_id)")


def _estado_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT id, codigo_cne, nombre FROM estados").fetchall()


def _estado_ids_by_canonical(conn: sqlite3.Connection, canonical_name: str) -> set[int]:
    if not canonical_name:
        return set()
    return {
        row["id"] for row in _estado_rows(conn)
        if _canonical_estado_name(row["nombre"]) == canonical_name
    }


def _estado_row_for_centro(conn: sqlite3.Connection, centro: dict[str, Any], codigo: str | None = None) -> sqlite3.Row | None:
    estado_code = _estado_code_from_centro(centro, codigo)
    if estado_code:
        for row in _estado_rows(conn):
            if _digits_code(row["codigo_cne"]).zfill(2)[-2:] == estado_code:
                return row

    canonical_name = _canonical_estado_name(centro.get("estado") or "")
    if canonical_name:
        for row in _estado_rows(conn):
            if _canonical_estado_name(row["nombre"]) == canonical_name:
                return row
    return None


def _obtener_o_crear_geo(
    conn: sqlite3.Connection,
    estado: str | None,
    municipio: str | None,
    parroquia: str | None,
    cod_estado: str | None = None,
    codigo_centro: str | None = None,
) -> tuple[int, int | None, int | None]:
    estado_nom = _canonical_estado_name(estado or "SIN ESTADO") or "SIN ESTADO"
    row = _estado_row_for_centro(conn, {"estado": estado, "cod_estado": cod_estado}, codigo_centro)
    if row:
        id_estado = row["id"]
    else:
        code = _estado_code_from_centro({"cod_estado": cod_estado}, codigo_centro)
        if not code:
            total = conn.execute("SELECT COUNT(*) c FROM estados").fetchone()["c"]
            code = f"AI{total + 1:02d}"
        conn.execute("INSERT INTO estados (codigo_cne, nombre) VALUES (?, ?)", (code, estado_nom))
        id_estado = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    id_municipio = None
    municipio_nom = _normalize_match_text(municipio or "")
    if municipio_nom:
        row = conn.execute(
            "SELECT id FROM municipios WHERE id_estado = ? AND nombre = ?",
            (id_estado, municipio_nom),
        ).fetchone()
        if row:
            id_municipio = row["id"]
        else:
            total = conn.execute(
                "SELECT COUNT(*) c FROM municipios WHERE id_estado = ?",
                (id_estado,),
            ).fetchone()["c"]
            conn.execute(
                "INSERT INTO municipios (id_estado, codigo_cne, nombre) VALUES (?, ?, ?)",
                (id_estado, f"AI{total + 1:02d}", municipio_nom),
            )
            id_municipio = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    id_parroquia = None
    parroquia_nom = _normalize_match_text(parroquia or "")
    if id_municipio and parroquia_nom:
        row = conn.execute(
            "SELECT id FROM parroquias WHERE id_municipio = ? AND nombre = ?",
            (id_municipio, parroquia_nom),
        ).fetchone()
        if row:
            id_parroquia = row["id"]
        else:
            total = conn.execute(
                "SELECT COUNT(*) c FROM parroquias WHERE id_municipio = ?",
                (id_municipio,),
            ).fetchone()["c"]
            conn.execute(
                "INSERT INTO parroquias (id_municipio, codigo_cne, nombre) VALUES (?, ?, ?)",
                (id_municipio, f"AI{total + 1:02d}", parroquia_nom),
            )
            id_parroquia = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    return id_estado, id_municipio, id_parroquia


def _centro_desde_item(item: dict[str, Any]) -> dict[str, Any]:
    centro = item.get("centro")
    return centro if isinstance(centro, dict) else item


def _codigo_desde_item(item: dict[str, Any], centro: dict[str, Any], eleccion_id: int) -> str:
    codigo = (
        item.get("resolved_codigo_centro")
        or item.get("matched_codigo_centro")
        or centro.get("codigo_centro")
        or centro.get("codigo_cne")
    )
    codigo = _normalize_center_code(codigo)
    return codigo or f"AI_{eleccion_id}_{uuid.uuid4().hex[:12]}"


def _confirmed_estado_ids(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> list[int]:
    ids: set[int] = set()
    for item in rows:
        if item.get("match_status") == "EXTRACTION_ERROR":
            continue
        centro = _centro_desde_item(item)
        codigo = _codigo_desde_item(item, centro, 0)

        if codigo:
            existing = conn.execute("SELECT id_estado FROM centros WHERE codigo_cne = ?", (codigo,)).fetchone()
            if existing and existing["id_estado"] is not None:
                ids.add(existing["id_estado"])

        row = _estado_row_for_centro(conn, centro, codigo)
        if row:
            ids.add(row["id"])

        canonical = _canonical_estado_name(centro.get("estado") or "")
        ids.update(_estado_ids_by_canonical(conn, canonical))

    return sorted(ids)


def _deactivate_tm_scope(conn: sqlite3.Connection, eleccion_id: int, estado_ids: list[int]) -> None:
    if not estado_ids:
        return
    placeholders = ",".join("?" for _ in estado_ids)
    conn.execute(f"UPDATE centros SET activo = 0 WHERE id_estado IN ({placeholders})", estado_ids)
    conn.execute(
        f"""
        UPDATE election_centers
        SET eligible = 0, updated_at = datetime('now')
        WHERE eleccion_id = ?
          AND centro_id IN (
              SELECT codigo_cne FROM centros WHERE id_estado IN ({placeholders})
          )
        """,
        [eleccion_id, *estado_ids],
    )


def _upsert_centro_confirmado(
    conn: sqlite3.Connection,
    eleccion_id: int,
    item: dict[str, Any],
    source_file: str,
) -> str:
    centro = _centro_desde_item(item)
    codigo = _codigo_desde_item(item, centro, eleccion_id)
    num_mesas = _to_int_or_none(centro.get("num_mesas"))
    num_electores = _to_int_or_none(centro.get("num_electores"))
    direccion = centro.get("direccion")

    existing = conn.execute("SELECT codigo_cne FROM centros WHERE codigo_cne = ?", (codigo,)).fetchone()
    if existing:
        conn.execute("""
            UPDATE centros SET
                activo = 1,
                num_mesas = COALESCE(?, num_mesas),
                num_electores = COALESCE(?, num_electores),
                direccion = CASE
                    WHEN (direccion IS NULL OR TRIM(direccion) = '') AND ? IS NOT NULL AND TRIM(?) != ''
                    THEN ?
                    ELSE direccion
                END
            WHERE codigo_cne = ?
        """, (num_mesas, num_electores, direccion, direccion or "", direccion, codigo))
    else:
        id_estado, id_municipio, id_parroquia = _obtener_o_crear_geo(
            conn,
            centro.get("estado"),
            centro.get("municipio"),
            centro.get("parroquia"),
            centro.get("cod_estado"),
            codigo,
        )
        conn.execute("""
            INSERT INTO centros (
                codigo_cne, nombre, direccion, id_parroquia, id_municipio, id_estado,
                num_mesas, num_electores, activo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            codigo,
            _normalize_match_text(centro.get("nombre_centro") or centro.get("nombre") or codigo),
            direccion,
            id_parroquia,
            id_municipio,
            id_estado,
            num_mesas or 0,
            num_electores or 0,
        ))

    conn.execute("""
        INSERT INTO election_centers (eleccion_id, centro_id, eligible, source_file, campos_extra, updated_at)
        VALUES (?, ?, 1, ?, ?, datetime('now'))
        ON CONFLICT(eleccion_id, centro_id) DO UPDATE SET
            eligible = 1,
            source_file = excluded.source_file,
            campos_extra = excluded.campos_extra,
            updated_at = datetime('now')
    """, (
        eleccion_id,
        codigo,
        source_file,
        json.dumps(centro.get("campos_extra") or {}, ensure_ascii=False),
    ))
    return codigo


def procesar_confirmacion_tm(
    db_path: str,
    eleccion_id: int,
    rows: list[dict[str, Any]],
    source_file: str = "ai_import",
) -> dict[str, int]:
    """
    Apply the confirmed TM import in one transaction.

    It preserves lat/lon/riesgo, deactivates absent centers, clears previous
    election eligibility, and reactivates only confirmed centers.
    """
    stats = {"processed": 0, "written": 0, "skipped": 0, "scope_estados": 0}
    conn = _connect(db_path)
    try:
        _ensure_tm_ai_tables(conn)
        affected_estado_ids = _confirmed_estado_ids(conn, rows)
        stats["scope_estados"] = len(affected_estado_ids)
        conn.execute("BEGIN IMMEDIATE")
        _deactivate_tm_scope(conn, eleccion_id, affected_estado_ids)

        for item in rows:
            stats["processed"] += 1
            status = item.get("match_status")
            if status == "EXTRACTION_ERROR":
                stats["skipped"] += 1
                continue
            _upsert_centro_confirmado(conn, eleccion_id, item, item.get("source_file") or source_file)
            stats["written"] += 1

        conn.commit()
        return stats
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
