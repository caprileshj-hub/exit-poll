from __future__ import annotations

import hashlib
import json
import mimetypes
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from selector_longitudinal import MIN_ELECTORES_CENTRO
    from selector_muestra import frame_hash
except ImportError:  # pragma: no cover
    from .selector_longitudinal import MIN_ELECTORES_CENTRO
    from .selector_muestra import frame_hash


DOMESTIC_STATE_IDS = set(range(1, 25))


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def ensure_tm_audit_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tm_cargas (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            eleccion_id          INTEGER REFERENCES elecciones(id),
            periodo_tm           TEXT NOT NULL,
            fecha_tm             TEXT NOT NULL,
            filename             TEXT NOT NULL,
            file_hash            TEXT,
            file_size            INTEGER,
            mime_type            TEXT,
            detected_format      TEXT,
            parser_mode          TEXT,
            loaded_at            TEXT DEFAULT (datetime('now')),
            frame_before_hash    TEXT,
            frame_after_hash     TEXT,
            centros_before       INTEGER NOT NULL DEFAULT 0,
            centros_after        INTEGER NOT NULL DEFAULT 0,
            electores_before     INTEGER NOT NULL DEFAULT 0,
            electores_after      INTEGER NOT NULL DEFAULT 0,
            mesas_before         INTEGER NOT NULL DEFAULT 0,
            mesas_after          INTEGER NOT NULL DEFAULT 0,
            report_json          TEXT NOT NULL,
            status               TEXT NOT NULL DEFAULT 'completed'
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tm_cargas_eleccion ON tm_cargas(eleccion_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tm_cargas_loaded ON tm_cargas(loaded_at)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tm_carga_cambios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            carga_id         INTEGER NOT NULL REFERENCES tm_cargas(id),
            codigo_centro    TEXT NOT NULL,
            tipo_cambio      TEXT NOT NULL,
            before_json      TEXT,
            after_json       TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tm_cambios_carga ON tm_carga_cambios(carga_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tm_cambios_tipo ON tm_carga_cambios(tipo_cambio)")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_metadata(path: Path, filename: str | None = None, detected_format: str | None = None) -> dict[str, Any]:
    ext = path.suffix.lower().lstrip(".")
    return {
        "filename": filename or path.name,
        "file_hash": sha256_file(path) if path.exists() else None,
        "file_size": path.stat().st_size if path.exists() else None,
        "mime_type": mimetypes.guess_type(filename or path.name)[0] or "application/octet-stream",
        "detected_format": detected_format or ext or "unknown",
    }


def infer_period_from_filename(filename: str, eleccion_nombre: str | None = None) -> dict[str, str]:
    text = Path(filename or "").stem.replace("_", " ").replace("-", " ")
    year = ""
    for token in text.split():
        if token.isdigit() and 1900 <= int(token) <= 2100:
            year = token
            break
    periodo = eleccion_nombre or (f"Tabla Mesa {year}" if year else "")
    fecha = year if year else ""
    return {"periodo_tm": periodo, "fecha_tm": fecha}


def snapshot_frame(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT c.codigo_cne, c.nombre, c.num_mesas, c.num_electores, c.activo,
               e.id AS id_estado, e.nombre AS estado,
               mu.nombre AS municipio, p.nombre AS parroquia
        FROM centros c
        JOIN estados e ON e.id = c.id_estado
        LEFT JOIN municipios mu ON mu.id = c.id_municipio
        LEFT JOIN parroquias p ON p.id = c.id_parroquia
        WHERE c.activo = 1
        ORDER BY c.codigo_cne
        """
    ).fetchall()
    items: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = {
            "codigo_cne": row["codigo_cne"],
            "nombre": row["nombre"],
            "num_mesas": int(row["num_mesas"] or 0),
            "num_electores": int(row["num_electores"] or 0),
            "id_estado": int(row["id_estado"] or 0),
            "estado": row["estado"],
            "municipio": row["municipio"],
            "parroquia": row["parroquia"],
        }
        items[item["codigo_cne"]] = item

    all_rows = list(items.values())
    domesticos = [row for row in all_rows if _is_domestic(row)]
    exterior = [row for row in items.values() if int(row["id_estado"]) not in DOMESTIC_STATE_IDS]
    frame_rows = [
        {
            "codigo_cne": row["codigo_cne"],
            "id_estado": row["id_estado"],
            "num_electores": row["num_electores"],
            "num_mesas": row["num_mesas"],
        }
        for row in all_rows
    ]
    return {
        "items": items,
        "hash": frame_hash(frame_rows),
        "nacional": _stats(all_rows),
        "domestico": _stats(domesticos),
        "exterior": _stats(exterior),
        "por_estado": _stats_by_state(all_rows),
        "elegibilidad": _eligibility_stats(domesticos),
    }


def _stats(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "centros": len(rows),
        "electores": sum(int(r.get("num_electores") or 0) for r in rows),
        "mesas": sum(int(r.get("num_mesas") or 0) for r in rows),
        "entidades": len({int(r.get("id_estado") or 0) for r in rows}),
        "municipios": len({(int(r.get("id_estado") or 0), r.get("municipio") or "") for r in rows if r.get("municipio")}),
        "parroquias": len({(int(r.get("id_estado") or 0), r.get("municipio") or "", r.get("parroquia") or "") for r in rows if r.get("parroquia")}),
    }


def _stats_by_state(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[int, dict[str, Any]] = {}
    for row in rows:
        state = int(row["id_estado"])
        b = buckets.setdefault(
            state,
            {"id_estado": state, "estado": row["estado"], "centros": 0, "electores": 0, "mesas": 0},
        )
        b["centros"] += 1
        b["electores"] += int(row.get("num_electores") or 0)
        b["mesas"] += int(row.get("num_mesas") or 0)
    return [buckets[k] for k in sorted(buckets)]


def _eligibility_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [r for r in rows if int(r.get("num_electores") or 0) >= MIN_ELECTORES_CENTRO]
    total_electores = sum(int(r.get("num_electores") or 0) for r in rows)
    eleg_electores = sum(int(r.get("num_electores") or 0) for r in eligible)
    return {
        "piso": MIN_ELECTORES_CENTRO,
        "centros_ge_piso": len(eligible),
        "electores_ge_piso": eleg_electores,
        "pct_centros": round(100 * len(eligible) / len(rows), 2) if rows else 0,
        "pct_electores": round(100 * eleg_electores / total_electores, 2) if total_electores else 0,
    }


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_items = before["items"]
    after_items = after["items"]
    codes = sorted(set(before_items) | set(after_items))
    cambios: list[dict[str, Any]] = []
    threshold = MIN_ELECTORES_CENTRO

    for code in codes:
        b = before_items.get(code)
        a = after_items.get(code)
        if b is None and a is not None:
            cambios.append({"codigo_centro": code, "tipo_cambio": "nuevo", "before": None, "after": a})
            if _is_domestic(a) and int(a.get("num_electores") or 0) >= threshold:
                cambios.append({"codigo_centro": code, "tipo_cambio": "nuevo_ge_piso", "before": None, "after": a})
            continue
        if a is None and b is not None:
            cambios.append({"codigo_centro": code, "tipo_cambio": "desaparecido", "before": b, "after": None})
            if _is_domestic(b) and int(b.get("num_electores") or 0) >= threshold:
                cambios.append({"codigo_centro": code, "tipo_cambio": "desaparecido_ge_piso", "before": b, "after": None})
            continue
        if not a or not b:
            continue

        diffs = {}
        for field in ("nombre", "estado", "municipio", "parroquia", "num_mesas", "num_electores"):
            if (b.get(field) or "") != (a.get(field) or ""):
                diffs[field] = {"before": b.get(field), "after": a.get(field)}
        if diffs:
            cambios.append({"codigo_centro": code, "tipo_cambio": "modificado", "before": b, "after": {**a, "diffs": diffs}})
        if _is_domestic(a) and _is_domestic(b):
            old_ok = int(b.get("num_electores") or 0) >= threshold
            new_ok = int(a.get("num_electores") or 0) >= threshold
            if not old_ok and new_ok:
                cambios.append({"codigo_centro": code, "tipo_cambio": "cruza_umbral_arriba", "before": b, "after": a})
            elif old_ok and not new_ok:
                cambios.append({"codigo_centro": code, "tipo_cambio": "cruza_umbral_abajo", "before": b, "after": a})

    return {
        "metricas": _metric_delta(before["nacional"], after["nacional"]),
        "domestico": _metric_delta(before.get("domestico", before["nacional"]), after.get("domestico", after["nacional"])),
        "exterior": _metric_delta(before["exterior"], after["exterior"]),
        "por_estado": _state_delta(before["por_estado"], after["por_estado"]),
        "elegibilidad": _metric_delta(before["elegibilidad"], after["elegibilidad"]),
        "cambios": cambios,
        "resumen_cambios": _count_by_type(cambios),
    }


def _is_domestic(row: dict[str, Any]) -> bool:
    return int(row.get("id_estado") or 0) in DOMESTIC_STATE_IDS


def _metric_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(before) | set(after))
    out = {}
    for key in keys:
        b = before.get(key, 0) or 0
        a = after.get(key, 0) or 0
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            out[key] = {"before": b, "after": a, "delta": a - b}
        else:
            out[key] = {"before": b, "after": a, "delta": None}
    return out


def _state_delta(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_before = {int(r["id_estado"]): r for r in before}
    by_after = {int(r["id_estado"]): r for r in after}
    rows = []
    for state in sorted(set(by_before) | set(by_after)):
        b = by_before.get(state, {"estado": "", "centros": 0, "electores": 0, "mesas": 0})
        a = by_after.get(state, {"estado": b.get("estado", ""), "centros": 0, "electores": 0, "mesas": 0})
        rows.append({
            "id_estado": state,
            "estado": a.get("estado") or b.get("estado"),
            "centros_before": b.get("centros", 0),
            "centros_after": a.get("centros", 0),
            "centros_delta": a.get("centros", 0) - b.get("centros", 0),
            "electores_before": b.get("electores", 0),
            "electores_after": a.get("electores", 0),
            "electores_delta": a.get("electores", 0) - b.get("electores", 0),
        })
    return rows


def _count_by_type(cambios: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in cambios:
        counts[item["tipo_cambio"]] = counts.get(item["tipo_cambio"], 0) + 1
    return counts


def sample_impact(conn: sqlite3.Connection, eleccion_id: int, after_codes: set[str]) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT m.codigo_centro, c.num_electores
        FROM muestra m
        JOIN centros c ON c.codigo_cne = m.codigo_centro
        JOIN estados e ON e.id = c.id_estado
        WHERE m.id_eleccion = ?
          AND m.activo = 1
          AND COALESCE(m.rol_muestra, 'titular') = 'titular'
          AND e.id IN (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24)
        """,
        (eleccion_id,),
    ).fetchall()
    actual = {r["codigo_centro"] for r in rows}
    eligibles = {code for code in after_codes}
    permanecen = sorted(actual & eligibles)
    saldrian = sorted(actual - eligibles)
    return {
        "muestra_actual": len(actual),
        "permanecen": len(permanecen),
        "saldrian": len(saldrian),
        "entrarian": 0,
        "saldrian_codigos": saldrian[:100],
        "nota": "Impacto read-only: no sustituye la muestra automaticamente.",
    }


def persist_report(
    conn: sqlite3.Connection,
    *,
    eleccion_id: int | None,
    periodo_tm: str,
    fecha_tm: str,
    file_meta: dict[str, Any],
    parser_mode: str,
    before: dict[str, Any],
    after: dict[str, Any],
    processing: dict[str, Any] | None = None,
    status: str = "completed",
) -> int:
    ensure_tm_audit_schema(conn)
    comparison = compare_snapshots(before, after)
    after_codes = {
        code for code, row in after["items"].items()
        if _is_domestic(row) and int(row.get("num_electores") or 0) >= MIN_ELECTORES_CENTRO
    }
    report = {
        "identificacion": {
            "periodo_tm": periodo_tm,
            "fecha_tm": fecha_tm,
            "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "parser_mode": parser_mode,
            **file_meta,
        },
        "archivo": processing or {},
        "normalizaciones": {
            "vargas_la_guaira": True,
            "codigos_normalizados": True,
            "campos_operativos_preservados": ["lat", "lon", "riesgo", "radio_m"],
        },
        "before": before["nacional"],
        "after": after["nacional"],
        "comparison": comparison,
        "impacto_muestra": sample_impact(conn, eleccion_id, after_codes) if eleccion_id else {},
        "exterior": after["exterior"],
    }
    cur = conn.execute(
        """
        INSERT INTO tm_cargas (
            eleccion_id, periodo_tm, fecha_tm, filename, file_hash, file_size,
            mime_type, detected_format, parser_mode, frame_before_hash,
            frame_after_hash, centros_before, centros_after, electores_before,
            electores_after, mesas_before, mesas_after, report_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            eleccion_id,
            periodo_tm,
            fecha_tm,
            file_meta.get("filename") or "archivo",
            file_meta.get("file_hash"),
            int(file_meta.get("file_size") or 0),
            file_meta.get("mime_type"),
            file_meta.get("detected_format"),
            parser_mode,
            before["hash"],
            after["hash"],
            before["nacional"]["centros"],
            after["nacional"]["centros"],
            before["nacional"]["electores"],
            after["nacional"]["electores"],
            before["nacional"]["mesas"],
            after["nacional"]["mesas"],
            _json_dumps(report),
            status,
        ),
    )
    carga_id = int(cur.lastrowid)
    for item in comparison["cambios"]:
        conn.execute(
            """
            INSERT INTO tm_carga_cambios (carga_id, codigo_centro, tipo_cambio, before_json, after_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                carga_id,
                item["codigo_centro"],
                item["tipo_cambio"],
                _json_dumps(item.get("before")) if item.get("before") is not None else None,
                _json_dumps(item.get("after")) if item.get("after") is not None else None,
            ),
        )
    return carga_id
