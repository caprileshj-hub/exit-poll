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
    if name in {"VARGAS", "ESTADO VARGAS", "LA GUAIRA", "ESTADO LA GUAIRA"}:
        return "LA GUAIRA"
    return name


def _to_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    match = re.search(r"\d+", str(value).replace(".", "").replace(",", ""))
    return int(match.group(0)) if match else None


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


def _obtener_o_crear_geo(
    conn: sqlite3.Connection,
    estado: str | None,
    municipio: str | None,
    parroquia: str | None,
) -> tuple[int, int | None, int | None]:
    estado_nom = _canonical_estado_name(estado or "SIN ESTADO") or "SIN ESTADO"
    row = conn.execute("SELECT id FROM estados WHERE nombre = ?", (estado_nom,)).fetchone()
    if not row and estado_nom == "LA GUAIRA":
        row = conn.execute("SELECT id FROM estados WHERE nombre IN ('VARGAS', 'ESTADO VARGAS')").fetchone()
    if row:
        id_estado = row["id"]
    else:
        total = conn.execute("SELECT COUNT(*) c FROM estados").fetchone()["c"]
        conn.execute("INSERT INTO estados (codigo_cne, nombre) VALUES (?, ?)", (f"AI{total + 1:02d}", estado_nom))
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
    codigo = str(codigo or "").strip()
    return codigo or f"AI_{eleccion_id}_{uuid.uuid4().hex[:12]}"


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
    stats = {"processed": 0, "written": 0, "skipped": 0}
    conn = _connect(db_path)
    try:
        _ensure_tm_ai_tables(conn)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE centros SET activo = 0")
        conn.execute(
            "UPDATE election_centers SET eligible = 0, updated_at = datetime('now') WHERE eleccion_id = ?",
            (eleccion_id,),
        )

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
