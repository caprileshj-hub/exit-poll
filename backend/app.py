"""
Dashboard de Configuración — Exit Poll Venezuela
FastAPI + Jinja2 + Bootstrap 5
Uso: uvicorn app:app --reload
"""

import csv
import os
import random
import re
import sys
import sqlite3
import shutil
import tempfile
import uuid
import io
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "exitpoll.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Exit Poll — Configuración")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ── helpers ──────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def flash(request: Request, msg: str, cat: str = "success"):
    """Almacena un flash message en query-string (stateless)."""
    pass  # usaremos query params ?msg=...&cat=...


# ── INDEX ────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = get_db()
    eleccion = db.execute(
        "SELECT * FROM elecciones WHERE activa = 1 LIMIT 1"
    ).fetchone()
    stats = {}
    if eleccion:
        eid = eleccion["id"]
        stats["candidatos"] = db.execute(
            "SELECT COUNT(*) c FROM candidatos WHERE id_eleccion=?", (eid,)
        ).fetchone()["c"]
        stats["centros_muestra"] = db.execute(
            "SELECT COUNT(*) c FROM muestra WHERE id_eleccion=?", (eid,)
        ).fetchone()["c"]
        stats["centros_con_peso"] = db.execute(
            """SELECT COUNT(*) c FROM pesos p
               JOIN muestra m ON p.id_muestra=m.id
               WHERE m.id_eleccion=?""", (eid,)
        ).fetchone()["c"]
    db.close()
    return templates.TemplateResponse(request=request, name="index.html", context={
        "eleccion": eleccion, "stats": stats
    })


# ══════════════════════════════════════════════════════════════════
# ELECCIONES
# ══════════════════════════════════════════════════════════════════

@app.get("/elecciones", response_class=HTMLResponse)
async def elecciones_list(request: Request, msg: str = "", cat: str = "success"):
    db = get_db()
    rows = db.execute("SELECT * FROM elecciones ORDER BY fecha DESC").fetchall()
    db.close()
    return templates.TemplateResponse(request=request, name="elecciones.html", context={
        "elecciones": rows, "msg": msg, "cat": cat
    })


@app.get("/elecciones/nueva", response_class=HTMLResponse)
async def eleccion_form(request: Request):
    return templates.TemplateResponse(request=request, name="eleccion_form.html", context={
        "eleccion": None
    })


@app.get("/elecciones/{eid}/editar", response_class=HTMLResponse)
async def eleccion_edit(request: Request, eid: int):
    db = get_db()
    row = db.execute("SELECT * FROM elecciones WHERE id=?", (eid,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(404)
    return templates.TemplateResponse(request=request, name="eleccion_form.html", context={
        "eleccion": row
    })


@app.post("/elecciones/guardar")
async def eleccion_save(
    request: Request,
    eid: int = Form(0),
    nombre: str = Form(...),
    tipo: str = Form(...),
    fecha: str = Form(...),
    hora_apertura: str = Form("07:00"),
    hora_cierre: str = Form("18:00"),
    activa: int = Form(0),
):
    db = get_db()
    if activa:
        db.execute("UPDATE elecciones SET activa=0")
    if eid:
        db.execute(
            """UPDATE elecciones
               SET nombre=?, tipo=?, fecha=?, hora_apertura=?, hora_cierre=?, activa=?
               WHERE id=?""",
            (nombre, tipo, fecha, hora_apertura, hora_cierre, activa, eid),
        )
    else:
        db.execute(
            """INSERT INTO elecciones (nombre, tipo, fecha, hora_apertura, hora_cierre, activa)
               VALUES (?,?,?,?,?,?)""",
            (nombre, tipo, fecha, hora_apertura, hora_cierre, activa),
        )
    db.commit()
    db.close()
    return RedirectResponse("/elecciones?msg=Elección+guardada", status_code=303)


@app.post("/elecciones/{eid}/eliminar")
async def eleccion_delete(eid: int):
    db = get_db()
    db.execute("DELETE FROM elecciones WHERE id=?", (eid,))
    db.commit()
    db.close()
    return RedirectResponse("/elecciones?msg=Elección+eliminada&cat=warning", status_code=303)


@app.post("/elecciones/{eid}/activar")
async def eleccion_activar(eid: int):
    db = get_db()
    db.execute("UPDATE elecciones SET activa=0")
    db.execute("UPDATE elecciones SET activa=1 WHERE id=?", (eid,))
    db.commit()
    db.close()
    return RedirectResponse("/elecciones?msg=Elección+activada", status_code=303)


# ══════════════════════════════════════════════════════════════════
# CANDIDATOS
# ══════════════════════════════════════════════════════════════════

@app.get("/candidatos", response_class=HTMLResponse)
async def candidatos_list(request: Request, msg: str = "", cat: str = "success"):
    db = get_db()
    eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1 LIMIT 1").fetchone()
    rows = []
    if eleccion:
        rows = db.execute(
            """SELECT c.*, e.nombre as eleccion_nombre
               FROM candidatos c JOIN elecciones e ON c.id_eleccion=e.id
               WHERE c.id_eleccion=? ORDER BY c.orden""",
            (eleccion["id"],)
        ).fetchall()
    db.close()
    return templates.TemplateResponse(request=request, name="candidatos.html", context={
        "candidatos": rows, "eleccion": eleccion,
        "msg": msg, "cat": cat
    })


@app.get("/candidatos/nuevo", response_class=HTMLResponse)
async def candidato_form(request: Request):
    db = get_db()
    eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1 LIMIT 1").fetchone()
    estados = db.execute("SELECT * FROM estados ORDER BY nombre").fetchall()
    db.close()
    if not eleccion:
        return RedirectResponse("/elecciones?msg=Primero+active+una+elección&cat=warning", status_code=303)
    return templates.TemplateResponse(request=request, name="candidato_form.html", context={
        "candidato": None, "eleccion": eleccion,
        "estados": estados
    })


@app.get("/candidatos/{cid}/editar", response_class=HTMLResponse)
async def candidato_edit(request: Request, cid: int):
    db = get_db()
    row = db.execute("SELECT * FROM candidatos WHERE id=?", (cid,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404)
    eleccion = db.execute("SELECT * FROM elecciones WHERE id=?", (row["id_eleccion"],)).fetchone()
    estados = db.execute("SELECT * FROM estados ORDER BY nombre").fetchall()
    db.close()
    return templates.TemplateResponse(request=request, name="candidato_form.html", context={
        "candidato": row, "eleccion": eleccion,
        "estados": estados
    })


@app.post("/candidatos/guardar")
async def candidato_save(
    request: Request,
    cid: int = Form(0),
    id_eleccion: int = Form(...),
    nombre: str = Form(...),
    partido: str = Form(""),
    bando: str = Form("otro"),
    tipo: str = Form("unico"),
    orden: int = Form(1),
    foto: UploadFile = File(None),
):
    foto_url = None
    if foto and foto.filename:
        ext = Path(foto.filename).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            return RedirectResponse(
                "/candidatos?msg=Formato+de+imagen+no+válido&cat=danger", status_code=303
            )
        fname = f"{uuid.uuid4().hex}{ext}"
        dest = UPLOAD_DIR / fname
        with open(dest, "wb") as f:
            shutil.copyfileobj(foto.file, f)
        foto_url = f"/static/uploads/{fname}"

    db = get_db()
    if cid:
        if foto_url:
            db.execute(
                """UPDATE candidatos
                   SET nombre=?, partido=?, bando=?, tipo=?, orden=?, foto_url=?
                   WHERE id=?""",
                (nombre, partido, bando, tipo, orden, foto_url, cid),
            )
        else:
            db.execute(
                """UPDATE candidatos
                   SET nombre=?, partido=?, bando=?, tipo=?, orden=?
                   WHERE id=?""",
                (nombre, partido, bando, tipo, orden, cid),
            )
    else:
        db.execute(
            """INSERT INTO candidatos (id_eleccion, nombre, partido, bando, tipo, orden, foto_url)
               VALUES (?,?,?,?,?,?,?)""",
            (id_eleccion, nombre, partido, bando, tipo, orden, foto_url),
        )
    db.commit()
    db.close()
    return RedirectResponse("/candidatos?msg=Candidato+guardado", status_code=303)


@app.post("/candidatos/{cid}/eliminar")
async def candidato_delete(cid: int):
    db = get_db()
    db.execute("DELETE FROM candidatos WHERE id=?", (cid,))
    db.commit()
    db.close()
    return RedirectResponse("/candidatos?msg=Candidato+eliminado&cat=warning", status_code=303)


# ══════════════════════════════════════════════════════════════════
# FICHA TÉCNICA DE LA MUESTRA
# ══════════════════════════════════════════════════════════════════

@app.get("/ficha", response_class=HTMLResponse)
async def ficha_tecnica(request: Request):
    db = get_db()
    eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1 LIMIT 1").fetchone()

    # --- Registro Electoral (siempre, independiente de elección/muestra) ---
    re = {}
    re["centros_activos"] = db.execute(
        "SELECT COUNT(*) c FROM centros WHERE activo=1"
    ).fetchone()["c"]
    re["centros_inactivos"] = db.execute(
        "SELECT COUNT(*) c FROM centros WHERE activo=0"
    ).fetchone()["c"]
    re["electores"] = db.execute(
        "SELECT COALESCE(SUM(num_electores),0) s FROM centros WHERE activo=1"
    ).fetchone()["s"]
    re["mesas"] = db.execute(
        "SELECT COALESCE(SUM(num_mesas),0) s FROM centros WHERE activo=1"
    ).fetchone()["s"]
    re["con_gps"] = db.execute(
        "SELECT COUNT(*) c FROM centros WHERE lat IS NOT NULL AND lon IS NOT NULL AND activo=1"
    ).fetchone()["c"]
    re["total_estados"] = db.execute("SELECT COUNT(*) c FROM estados").fetchone()["c"]
    re["estados_activos"] = db.execute(
        "SELECT COUNT(DISTINCT id_estado) c FROM centros WHERE activo=1"
    ).fetchone()["c"]

    # Desglose RE por estado (incluye estados con centros inactivos)
    re_estados = db.execute(
        """SELECT e.nombre as estado,
                  SUM(CASE WHEN c.activo=1 THEN 1 ELSE 0 END) as centros_activos,
                  SUM(CASE WHEN c.activo=0 THEN 1 ELSE 0 END) as centros_inactivos,
                  SUM(CASE WHEN c.activo=1 THEN c.num_electores ELSE 0 END) as electores,
                  SUM(CASE WHEN c.activo=1 THEN c.num_mesas ELSE 0 END) as mesas,
                  SUM(CASE WHEN c.lat IS NOT NULL AND c.activo=1 THEN 1 ELSE 0 END) as con_gps
           FROM estados e
           LEFT JOIN centros c ON c.id_estado=e.id
           GROUP BY e.id ORDER BY e.nombre"""
    ).fetchall()

    # --- Muestra (solo si hay elección activa con muestra) ---
    muestra = {}
    muestra_estados = []
    if eleccion:
        eid = eleccion["id"]
        muestra["total_centros"] = db.execute(
            "SELECT COUNT(*) c FROM muestra WHERE id_eleccion=? AND activo=1", (eid,)
        ).fetchone()["c"]
        if muestra["total_centros"] > 0:
            muestra["electores"] = db.execute(
                """SELECT COALESCE(SUM(ct.num_electores),0) s
                   FROM muestra m JOIN centros ct ON m.codigo_centro=ct.codigo_cne
                   WHERE m.id_eleccion=? AND m.activo=1""", (eid,)
            ).fetchone()["s"]
            muestra["mesas"] = db.execute(
                """SELECT COALESCE(SUM(ct.num_mesas),0) s
                   FROM muestra m JOIN centros ct ON m.codigo_centro=ct.codigo_cne
                   WHERE m.id_eleccion=? AND m.activo=1""", (eid,)
            ).fetchone()["s"]
            if re["electores"]:
                muestra["cobertura_pct"] = round(
                    100 * muestra["electores"] / re["electores"], 2)
            else:
                muestra["cobertura_pct"] = 0
            muestra["estados_cubiertos"] = db.execute(
                """SELECT COUNT(DISTINCT ct.id_estado) c
                   FROM muestra m JOIN centros ct ON m.codigo_centro=ct.codigo_cne
                   WHERE m.id_eleccion=? AND m.activo=1""", (eid,)
            ).fetchone()["c"]
            muestra_estados = db.execute(
                """SELECT e.nombre as estado, COUNT(m.id) as centros,
                          SUM(ct.num_electores) as electores, SUM(ct.num_mesas) as mesas
                   FROM muestra m
                   JOIN centros ct ON m.codigo_centro=ct.codigo_cne
                   JOIN estados e ON ct.id_estado=e.id
                   WHERE m.id_eleccion=? AND m.activo=1
                   GROUP BY e.id ORDER BY e.nombre""", (eid,)
            ).fetchall()
            muestra["tipos"] = db.execute(
                """SELECT tipo_centro, COUNT(*) c
                   FROM muestra WHERE id_eleccion=? AND activo=1 AND tipo_centro IS NOT NULL
                   GROUP BY tipo_centro""", (eid,)
            ).fetchall()

    # --- Error muestral ---
    # Formula: e = Z * sqrt(P*Q/n) * sqrt(1 - n/N)
    # Z=1.96 (95%), P=Q=0.5
    error_muestral = None
    if muestra.get("total_centros", 0) > 0 and muestra.get("electores", 0) > 0 and re["electores"] > 0:
        import math
        n = muestra["electores"]
        N = re["electores"]
        error_muestral = 1.96 * math.sqrt(0.25 / n) * math.sqrt(1 - n / N) * 100

    db.close()
    return templates.TemplateResponse(request=request, name="ficha.html", context={
        "eleccion": eleccion,
        "re": re, "re_estados": re_estados,
        "muestra": muestra, "muestra_estados": muestra_estados,
        "error_muestral": error_muestral
    })


# ══════════════════════════════════════════════════════════════════
# PESOS POR CENTRO
# ══════════════════════════════════════════════════════════════════

@app.get("/pesos", response_class=HTMLResponse)
async def pesos_list(request: Request, estado: str = "", msg: str = "", cat: str = "success"):
    db = get_db()
    eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1 LIMIT 1").fetchone()
    rows = []
    estados = []
    tiene_muestra = False

    if eleccion:
        eid = eleccion["id"]
        tiene_muestra = db.execute(
            "SELECT COUNT(*) c FROM muestra WHERE id_eleccion=?", (eid,)
        ).fetchone()["c"] > 0

    if eleccion and tiene_muestra:
        # Estados con centros en la muestra
        estados = db.execute(
            """SELECT DISTINCT e.id, e.nombre FROM estados e
               JOIN centros ct ON ct.id_estado=e.id
               JOIN muestra m ON m.codigo_centro=ct.codigo_cne
               WHERE m.id_eleccion=?
               ORDER BY e.nombre""", (eid,)
        ).fetchall()

        # Centros de la muestra con sus pesos
        query = """
            SELECT m.id as id_muestra, m.codigo_centro, ct.nombre as centro_nombre,
                   e.nombre as estado, mu.nombre as municipio, p2.nombre as parroquia,
                   m.tipo_centro, m.activo,
                   COALESCE(p.peso_parroquia,0) as peso_parroquia,
                   COALESCE(p.peso_municipio,0) as peso_municipio,
                   COALESCE(p.peso_estado,0) as peso_estado,
                   COALESCE(p.peso_nacion,0) as peso_nacion,
                   ct.num_electores, ct.num_mesas
            FROM muestra m
            JOIN centros ct ON m.codigo_centro=ct.codigo_cne
            JOIN estados e ON ct.id_estado=e.id
            LEFT JOIN municipios mu ON ct.id_municipio=mu.id
            LEFT JOIN parroquias p2 ON ct.id_parroquia=p2.id
            LEFT JOIN pesos p ON p.id_muestra=m.id
            WHERE m.id_eleccion=? AND m.activo=1
        """
        params = [eid]
        if estado:
            query += " AND e.id=?"
            params.append(int(estado))
        query += " ORDER BY e.nombre, mu.nombre, ct.nombre"
        rows = db.execute(query, params).fetchall()

    db.close()
    return templates.TemplateResponse(request=request, name="pesos.html", context={
        "eleccion": eleccion, "pesos": rows,
        "estados": estados, "estado_sel": estado, "msg": msg, "cat": cat,
        "tiene_muestra": tiene_muestra
    })


@app.post("/pesos/{id_muestra}/guardar")
async def peso_save(
    id_muestra: int,
    peso_parroquia: float = Form(0),
    peso_municipio: float = Form(0),
    peso_estado: float = Form(0),
    peso_nacion: float = Form(0),
):
    db = get_db()
    exists = db.execute("SELECT 1 FROM pesos WHERE id_muestra=?", (id_muestra,)).fetchone()
    if exists:
        db.execute(
            """UPDATE pesos SET peso_parroquia=?, peso_municipio=?, peso_estado=?, peso_nacion=?
               WHERE id_muestra=?""",
            (peso_parroquia, peso_municipio, peso_estado, peso_nacion, id_muestra),
        )
    else:
        db.execute(
            """INSERT INTO pesos (id_muestra, peso_parroquia, peso_municipio, peso_estado, peso_nacion)
               VALUES (?,?,?,?,?)""",
            (id_muestra, peso_parroquia, peso_municipio, peso_estado, peso_nacion),
        )
    db.commit()
    db.close()
    return RedirectResponse("/pesos?msg=Peso+actualizado", status_code=303)


@app.post("/pesos/guardar-todos")
async def pesos_save_all(request: Request):
    """Guarda todos los pesos editados desde la tabla inline."""
    form = await request.form()
    db = get_db()
    count = 0
    for key, val in form.items():
        if key.startswith("pp_"):
            mid = int(key[3:])
            pp = float(val or 0)
            pm = float(form.get(f"pm_{mid}", 0) or 0)
            pe = float(form.get(f"pe_{mid}", 0) or 0)
            pn = float(form.get(f"pn_{mid}", 0) or 0)
            exists = db.execute("SELECT 1 FROM pesos WHERE id_muestra=?", (mid,)).fetchone()
            if exists:
                db.execute(
                    """UPDATE pesos SET peso_parroquia=?, peso_municipio=?, peso_estado=?, peso_nacion=?
                       WHERE id_muestra=?""",
                    (pp, pm, pe, pn, mid),
                )
            else:
                db.execute(
                    """INSERT INTO pesos (id_muestra, peso_parroquia, peso_municipio, peso_estado, peso_nacion)
                       VALUES (?,?,?,?,?)""",
                    (mid, pp, pm, pe, pn),
                )
            count += 1
    db.commit()
    db.close()
    return RedirectResponse(f"/pesos?msg=Pesos+actualizados+({count}+centros)&cat=success", status_code=303)


@app.get("/pesos/{id_muestra}/editar", response_class=HTMLResponse)
async def peso_edit_form(request: Request, id_muestra: int):
    db = get_db()
    row = db.execute(
        """SELECT m.id as id_muestra, m.codigo_centro, ct.nombre as centro_nombre,
                  e.nombre as estado, mu.nombre as municipio,
                  COALESCE(p.peso_parroquia,0) as peso_parroquia,
                  COALESCE(p.peso_municipio,0) as peso_municipio,
                  COALESCE(p.peso_estado,0) as peso_estado,
                  COALESCE(p.peso_nacion,0) as peso_nacion,
                  ct.num_electores
           FROM muestra m
           JOIN centros ct ON m.codigo_centro=ct.codigo_cne
           JOIN estados e ON ct.id_estado=e.id
           LEFT JOIN municipios mu ON ct.id_municipio=mu.id
           LEFT JOIN pesos p ON p.id_muestra=m.id
           WHERE m.id=?""", (id_muestra,)
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(404)
    return templates.TemplateResponse(request=request, name="peso_edit.html", context={
        "centro": row
    })


# ══════════════════════════════════════════════════════════════════
# TABLA DE MESA — Carga y gestión
# ══════════════════════════════════════════════════════════════════

@app.get("/tm", response_class=HTMLResponse)
async def tm_index(request: Request, msg: str = "", cat: str = "success"):
    db = get_db()
    stats = {}
    stats["centros_activos"] = db.execute(
        "SELECT COUNT(*) c FROM centros WHERE activo=1"
    ).fetchone()["c"]
    stats["centros_inactivos"] = db.execute(
        "SELECT COUNT(*) c FROM centros WHERE activo=0"
    ).fetchone()["c"]
    stats["con_gps"] = db.execute(
        "SELECT COUNT(*) c FROM centros WHERE lat IS NOT NULL AND lon IS NOT NULL"
    ).fetchone()["c"]
    stats["electores"] = db.execute(
        "SELECT COALESCE(SUM(num_electores),0) s FROM centros WHERE activo=1"
    ).fetchone()["s"]
    stats["estados"] = db.execute("SELECT COUNT(*) c FROM estados").fetchone()["c"]
    stats["municipios"] = db.execute("SELECT COUNT(*) c FROM municipios").fetchone()["c"]
    stats["parroquias"] = db.execute("SELECT COUNT(*) c FROM parroquias").fetchone()["c"]

    # Resumen por estado
    por_estado = db.execute(
        """SELECT e.nombre, COUNT(c.codigo_cne) as centros,
                  SUM(c.num_electores) as electores, SUM(c.num_mesas) as mesas,
                  SUM(CASE WHEN c.lat IS NOT NULL THEN 1 ELSE 0 END) as con_gps
           FROM centros c
           JOIN estados e ON c.id_estado=e.id
           WHERE c.activo=1
           GROUP BY e.id ORDER BY e.nombre"""
    ).fetchall()
    db.close()
    return templates.TemplateResponse(request=request, name="tm.html", context={
        "stats": stats, "por_estado": por_estado,
        "msg": msg, "cat": cat
    })


@app.post("/tm/cargar")
async def tm_upload(
    request: Request,
    archivo: UploadFile = File(...),
    formato: str = Form("auto"),
    hoja: str = Form(""),
    dry_run: int = Form(0),
):
    """Recibe un archivo TM (Excel o CSV), lo convierte y carga en la BD."""
    # Guardar archivo temporal
    ext = Path(archivo.filename).suffix.lower()
    if ext not in (".xlsx", ".xls", ".xlsm", ".csv"):
        return RedirectResponse(
            "/tm?msg=Formato+no+soportado.+Use+Excel+o+CSV&cat=danger",
            status_code=303,
        )

    tmp_path = UPLOAD_DIR / f"tm_upload_{uuid.uuid4().hex}{ext}"
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(archivo.file, f)

    output_lines = []
    try:
        # Importar convertidor y cargador
        sys.path.insert(0, str(BASE_DIR))
        import convertidor_tm
        import cargador_tm

        # Paso 1: si es Excel, convertir a CSV estándar
        if ext in (".xlsx", ".xls", ".xlsm"):
            csv_path = tmp_path.with_suffix(".csv")
            df_raw = convertidor_tm.cargar_archivo(str(tmp_path), hoja=hoja or None)
            fmt = formato
            if fmt == "auto":
                fmt = convertidor_tm.detectar_formato(df_raw)
            output_lines.append(f"Formato detectado: {fmt}")

            df = convertidor_tm.CONVERTIDORES[fmt](df_raw)
            df = convertidor_tm.limpiar(df)

            centros = df["codigo_centro"].nunique()
            electores = df["electores"].sum()
            output_lines.append(f"Convertido: {len(df):,} mesas, {centros:,} centros, {electores:,} electores")

            df.to_csv(str(csv_path), index=False, encoding="utf-8-sig")
        else:
            csv_path = tmp_path

        # Paso 2: cargar en BD
        # Capturar output del cargador
        import io as _io
        from contextlib import redirect_stdout
        buf = _io.StringIO()
        with redirect_stdout(buf):
            cargador_tm.cargar_tm(str(csv_path), dry_run=bool(dry_run))
        output_lines.append(buf.getvalue())

        # Limpiar archivos temporales
        tmp_path.unlink(missing_ok=True)
        if csv_path != tmp_path:
            csv_path.unlink(missing_ok=True)

        result_msg = " | ".join(output_lines)
        return RedirectResponse(
            f"/tm?msg={result_msg[:500]}&cat=success",
            status_code=303,
        )

    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        error_msg = str(e)[:300]
        return RedirectResponse(
            f"/tm?msg=Error:+{error_msg}&cat=danger",
            status_code=303,
        )


# ══════════════════════════════════════════════════════════════════
# MUESTRA — Selección de centros para el exit poll
# ══════════════════════════════════════════════════════════════════

@app.get("/muestra", response_class=HTMLResponse)
async def muestra_index(request: Request, msg: str = "", cat: str = "success"):
    db = get_db()
    eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1 LIMIT 1").fetchone()

    muestra_actual = []
    if eleccion:
        muestra_actual = db.execute(
            """SELECT m.id, m.codigo_centro, ct.nombre as centro_nombre,
                      e.nombre as estado, mu.nombre as municipio, p.nombre as parroquia,
                      m.tipo_centro, ct.num_electores, ct.num_mesas,
                      rh.pct_oposicion, rh.pct_gobierno
               FROM muestra m
               JOIN centros ct ON m.codigo_centro=ct.codigo_cne
               JOIN estados e ON ct.id_estado=e.id
               LEFT JOIN municipios mu ON ct.id_municipio=mu.id
               LEFT JOIN parroquias p ON ct.id_parroquia=p.id
               LEFT JOIN resultados_historicos rh
                   ON rh.codigo_centro=m.codigo_centro AND rh.eleccion_ref='2024-presidencial'
               WHERE m.id_eleccion=? AND m.activo=1
               ORDER BY e.nombre, mu.nombre, ct.num_electores DESC""",
            (eleccion["id"],)
        ).fetchall()

    # Resultado nacional de referencia
    nac = db.execute("""
        SELECT SUM(votos_validos) v, SUM(votos_gobierno) g, SUM(votos_oposicion) o
        FROM resultados_historicos WHERE eleccion_ref='2024-presidencial'
    """).fetchone()
    pct_nac = {}
    if nac and nac["v"]:
        pct_nac["gobierno"] = round(100 * nac["g"] / nac["v"], 1)
        pct_nac["oposicion"] = round(100 * nac["o"] / nac["v"], 1)

    # Refs historicas disponibles
    refs = db.execute(
        "SELECT DISTINCT eleccion_ref FROM resultados_historicos"
    ).fetchall()

    db.close()
    return templates.TemplateResponse(request=request, name="muestra.html", context={
        "eleccion": eleccion,
        "muestra": muestra_actual, "pct_nac": pct_nac,
        "refs": refs, "msg": msg, "cat": cat
    })


@app.get("/muestra/generar", response_class=HTMLResponse)
async def muestra_generar(
    request: Request,
    centros_por_unidad: int = 2,
    candidatos_por_unidad: int = 5,
    umbral_pct: float = 10.0,
    eleccion_ref: str = "2024-presidencial",
):
    db = get_db()
    eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1 LIMIT 1").fetchone()
    if not eleccion:
        db.close()
        return RedirectResponse("/muestra?msg=Active+una+elección+primero&cat=warning", status_code=303)

    sys.path.insert(0, str(BASE_DIR))
    import selector_muestra
    # Reload in case module was cached
    import importlib
    importlib.reload(selector_muestra)

    nac = selector_muestra.resultado_nacional(db, eleccion_ref)
    candidatos = selector_muestra.generar_candidatos(
        db, eleccion_ref=eleccion_ref,
        candidatos_por_unidad=candidatos_por_unidad,
        umbral_pct=umbral_pct,
    )

    db.close()
    return templates.TemplateResponse(request=request, name="muestra_generar.html", context={
        "eleccion": eleccion,
        "candidatos": candidatos, "nac": nac,
        "centros_por_unidad": centros_por_unidad,
        "candidatos_por_unidad": candidatos_por_unidad,
        "umbral_pct": umbral_pct,
        "eleccion_ref": eleccion_ref,
    })


@app.post("/muestra/aplicar")
async def muestra_aplicar(request: Request):
    form = await request.form()
    codigos = form.getlist("codigo_centro")
    id_eleccion = int(form.get("id_eleccion", 0))

    if not codigos or not id_eleccion:
        return RedirectResponse("/muestra?msg=No+se+seleccionaron+centros&cat=warning", status_code=303)

    db = get_db()
    sys.path.insert(0, str(BASE_DIR))
    import selector_muestra
    import importlib
    importlib.reload(selector_muestra)

    n = selector_muestra.aplicar_muestra(db, id_eleccion, codigos)
    db.close()
    return RedirectResponse(f"/muestra?msg=Muestra+creada+con+{n}+centros&cat=success", status_code=303)


@app.post("/muestra/{mid}/quitar")
async def muestra_quitar(mid: int):
    db = get_db()
    db.execute("DELETE FROM pesos WHERE id_muestra=?", (mid,))
    db.execute("DELETE FROM muestra WHERE id=?", (mid,))
    db.commit()
    db.close()
    return RedirectResponse("/muestra?msg=Centro+removido+de+la+muestra&cat=warning", status_code=303)


# ══════════════════════════════════════════════════════════════════
# VISUALIZACIÓN — Heatmap y Dashboard interactivo
# ══════════════════════════════════════════════════════════════════

VIZ_DIR = BASE_DIR / "static" / "viz"
VIZ_DIR.mkdir(parents=True, exist_ok=True)


def _datos_ventaja_por_estado(db) -> dict:
    """Extrae ventaja gobierno-oposición por estado desde resultados_historicos."""
    rows = db.execute("""
        SELECT e.nombre,
               SUM(rh.votos_gobierno) as gob,
               SUM(rh.votos_oposicion) as opo,
               SUM(rh.votos_validos) as val
        FROM resultados_historicos rh
        JOIN centros c ON rh.codigo_centro = c.codigo_cne
        JOIN estados e ON c.id_estado = e.id
        WHERE c.activo = 1
        GROUP BY e.id
    """).fetchall()
    datos = {}
    for r in rows:
        if r["val"] and r["val"] > 0:
            pct_gob = 100 * r["gob"] / r["val"]
            pct_opo = 100 * r["opo"] / r["val"]
            ventaja = round(pct_gob - pct_opo, 1)
            # Normalizar nombre: "EDO. ZULIA" → "Zulia", "DTTO. CAPITAL" → "Distrito Capital"
            nombre = r["nombre"]
            nombre = nombre.replace("EDO. ", "").replace("DTTO. ", "Distrito ")
            nombre = nombre.replace("DELTA AMAC", "Delta Amacuro")
            nombre = nombre.replace("LA GUAIRA", "La Guaira")
            nombre = nombre.replace("NVA. ESPARTA", "Nueva Esparta")
            if nombre not in ("Distrito Capital", "La Guaira", "Delta Amacuro", "Nueva Esparta"):
                nombre = nombre.title()
            datos[_norm_estado(r["nombre"])] = ventaja
    return datos


def _datos_ventaja_muestra(db, id_eleccion: int) -> dict:
    """Ventaja solo para centros en la muestra, por estado."""
    rows = db.execute("""
        SELECT e.nombre,
               SUM(rh.votos_gobierno) as gob,
               SUM(rh.votos_oposicion) as opo,
               SUM(rh.votos_validos) as val
        FROM muestra m
        JOIN centros c ON m.codigo_centro = c.codigo_cne
        JOIN estados e ON c.id_estado = e.id
        LEFT JOIN resultados_historicos rh ON rh.codigo_centro = m.codigo_centro
        WHERE m.id_eleccion = ? AND m.activo = 1
        GROUP BY e.id
    """, (id_eleccion,)).fetchall()
    datos = {}
    for r in rows:
        if r["val"] and r["val"] > 0:
            pct_gob = 100 * r["gob"] / r["val"]
            pct_opo = 100 * r["opo"] / r["val"]
            ventaja = round(pct_gob - pct_opo, 1)
            nombre = r["nombre"]
            nombre = nombre.replace("EDO. ", "").replace("DTTO. ", "Distrito ")
            nombre = nombre.replace("DELTA AMAC", "Delta Amacuro")
            nombre = nombre.replace("LA GUAIRA", "La Guaira")
            nombre = nombre.replace("NVA. ESPARTA", "Nueva Esparta")
            if nombre not in ("Distrito Capital", "La Guaira", "Delta Amacuro", "Nueva Esparta"):
                nombre = nombre.title()
            datos[_norm_estado(r["nombre"])] = ventaja
    return datos


def _norm_municipio(nombre: str) -> str:
    """Normaliza nombres CNE de municipio para cruzarlos con ADM2."""
    nombre = (nombre or "").strip()
    for pref in ("MP. ", "CM. ", "MCPIO. ", "MUNICIPIO "):
        if nombre.upper().startswith(pref):
            nombre = nombre[len(pref):]
            break
    especiales = {
        "BLVNO LIBERTADOR": "Libertador",
        "LIBERTADOR": "Libertador",
    }
    return especiales.get(nombre.upper(), nombre.title())


def _datos_ventaja_por_municipio(db) -> dict:
    """Extrae ventaja gobierno-oposicion por municipio."""
    rows = db.execute("""
        SELECT e.nombre AS estado, mu.nombre AS municipio,
               SUM(rh.votos_gobierno) AS gob,
               SUM(rh.votos_oposicion) AS opo,
               SUM(rh.votos_validos) AS val
        FROM resultados_historicos rh
        JOIN centros c ON rh.codigo_centro = c.codigo_cne
        JOIN estados e ON c.id_estado = e.id
        JOIN municipios mu ON c.id_municipio = mu.id
        WHERE c.activo = 1
        GROUP BY e.id, mu.id
    """).fetchall()
    datos = {}
    for r in rows:
        if r["val"] and r["val"] > 0:
            pct_gob = 100 * r["gob"] / r["val"]
            pct_opo = 100 * r["opo"] / r["val"]
            datos[(_norm_estado(r["estado"]), _norm_municipio(r["municipio"]))] = round(pct_gob - pct_opo, 1)
    return datos


def _datos_ventaja_muestra_municipio(db, id_eleccion: int) -> dict:
    """Extrae ventaja de centros en muestra por municipio."""
    rows = db.execute("""
        SELECT e.nombre AS estado, mu.nombre AS municipio,
               SUM(rh.votos_gobierno) AS gob,
               SUM(rh.votos_oposicion) AS opo,
               SUM(rh.votos_validos) AS val
        FROM muestra m
        JOIN centros c ON m.codigo_centro = c.codigo_cne
        JOIN estados e ON c.id_estado = e.id
        JOIN municipios mu ON c.id_municipio = mu.id
        LEFT JOIN resultados_historicos rh ON rh.codigo_centro = m.codigo_centro
        WHERE m.id_eleccion = ? AND m.activo = 1
        GROUP BY e.id, mu.id
    """, (id_eleccion,)).fetchall()
    datos = {}
    for r in rows:
        if r["val"] and r["val"] > 0:
            pct_gob = 100 * r["gob"] / r["val"]
            pct_opo = 100 * r["opo"] / r["val"]
            datos[(_norm_estado(r["estado"]), _norm_municipio(r["municipio"]))] = round(pct_gob - pct_opo, 1)
    return datos


def _tendencia_simulada(datos_ventaja: dict, n_puntos: int = 15) -> dict:
    """Genera tendencia simulada a partir de datos de ventaja históricos.
    Simula la llegada progresiva de datos desde las 7AM con la tendencia
    convergiendo al resultado final conocido."""
    import datetime
    import random
    tendencias = {}
    start = datetime.datetime(2025, 1, 1, 7, 0)

    # Nacional: promedio ponderado
    if datos_ventaja:
        avg_ventaja = sum(datos_ventaja.values()) / len(datos_ventaja)
        final_gob = 50 + avg_ventaja / 2
        final_opo = 50 - avg_ventaja / 2
    else:
        final_gob, final_opo = 50, 50

    etiquetas = {
        (f"{k[0]} - {k[1]}" if isinstance(k, tuple) else str(k)): v
        for k, v in datos_ventaja.items()
    }

    for nombre in ["VENEZUELA"] + [n.upper() for n in etiquetas.keys()]:
        if nombre == "VENEZUELA":
            tgt_gob, tgt_opo = final_gob, final_opo
        else:
            orig = next((k for k in etiquetas if k.upper() == nombre), None)
            v = etiquetas.get(orig, 0) if orig else 0
            tgt_gob = 50 + v / 2
            tgt_opo = 50 - v / 2

        puntos = []
        gob = 50 + random.uniform(-5, 5)  # Inicia cerca de 50/50
        for i in range(n_puntos):
            hora = (start + datetime.timedelta(minutes=40 * i)).strftime('%H:%M')
            # Converge al resultado final con ruido decreciente
            t = (i + 1) / n_puntos
            noise = random.uniform(-3, 3) * (1 - t)
            gob = tgt_gob * t + gob * (1 - t) + noise
            gob = max(5, min(95, gob))
            opo = 100 - gob
            puntos.append({'hora': hora, 'gob': round(gob, 1), 'opo': round(opo, 1)})
        tendencias[nombre] = puntos

    return tendencias


def _nombres_candidatos(db, id_eleccion: int = None) -> dict:
    """Obtiene nombres de candidatos gobierno/oposición de la elección."""
    cand = {'gobierno': 'Gobierno', 'oposicion': 'Oposici\u00f3n'}
    if id_eleccion:
        for bando in ('gobierno', 'oposicion'):
            row = db.execute(
                "SELECT nombre FROM candidatos WHERE id_eleccion=? AND bando=? ORDER BY orden LIMIT 1",
                (id_eleccion, bando)
            ).fetchone()
            if row:
                cand[bando] = row["nombre"]
    return cand


@app.get("/visualizacion", response_class=HTMLResponse)
async def visualizacion_index(request: Request, msg: str = "", cat: str = "success"):
    db = get_db()
    eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1 LIMIT 1").fetchone()

    tiene_resultados = db.execute(
        "SELECT COUNT(*) c FROM resultados_historicos"
    ).fetchone()["c"] > 0

    tiene_muestra = False
    if eleccion:
        tiene_muestra = db.execute(
            "SELECT COUNT(*) c FROM muestra WHERE id_eleccion=?", (eleccion["id"],)
        ).fetchone()["c"] > 0

    # Verificar si ya hay archivos generados
    heatmap_existe = (VIZ_DIR / "heatmap.html").exists()
    dashboard_existe = (VIZ_DIR / "dashboard.html").exists()

    refs = db.execute(
        "SELECT DISTINCT eleccion_ref FROM resultados_historicos"
    ).fetchall()

    db.close()
    return templates.TemplateResponse(request=request, name="visualizacion.html", context={
        "eleccion": eleccion,
        "tiene_resultados": tiene_resultados,
        "tiene_muestra": tiene_muestra,
        "heatmap_existe": heatmap_existe,
        "dashboard_existe": dashboard_existe,
        "refs": refs,
        "msg": msg, "cat": cat,
    })


@app.post("/visualizacion/generar")
async def visualizacion_generar(
    request: Request,
    tipo: str = Form("heatmap"),
    nivel: str = Form("estado"),
    fuente: str = Form("todos"),
):
    db = get_db()
    eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1 LIMIT 1").fetchone()
    eid = eleccion["id"] if eleccion else None

    candidatos_dict = _nombres_candidatos(db, eid)

    # Obtener datos de ventaja
    if nivel == "municipio":
        if fuente == "muestra" and eid:
            datos_ventaja = _datos_ventaja_muestra_municipio(db, eid)
        else:
            datos_ventaja = _datos_ventaja_por_municipio(db)
    elif fuente == "muestra" and eid:
        datos_ventaja = _datos_ventaja_muestra(db, eid)
    else:
        datos_ventaja = _datos_ventaja_por_estado(db)

    db.close()

    if not datos_ventaja:
        return RedirectResponse(
            "/visualizacion?msg=No+hay+datos+de+resultados+hist%C3%B3ricos&cat=warning",
            status_code=303
        )

    sys.path.insert(0, str(BASE_DIR))

    titulo = eleccion["nombre"] if eleccion else "Exit Poll Venezuela"

    try:
        if tipo == "dashboard":
            import generador_dashboard
            import importlib
            importlib.reload(generador_dashboard)

            tendencias = _tendencia_simulada(datos_ventaja)
            ruta = str(VIZ_DIR / "dashboard.html")
            generador_dashboard.generar_dashboard(
                datos_ventaja, tendencias,
                nivel=nivel, ruta_salida=ruta,
                titulo=titulo, candidatos=candidatos_dict
            )
            return RedirectResponse(
                "/visualizacion?msg=Dashboard+generado+exitosamente&cat=success",
                status_code=303
            )
        else:
            import generador_heatmap
            import importlib
            importlib.reload(generador_heatmap)

            ruta = str(VIZ_DIR / "heatmap.html")
            generador_heatmap.generar_heatmap(
                datos_ventaja, nivel=nivel, ruta_salida=ruta,
                titulo=titulo, candidatos=candidatos_dict
            )
            return RedirectResponse(
                "/visualizacion?msg=Heatmap+generado+exitosamente&cat=success",
                status_code=303
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e)[:200]
        return RedirectResponse(
            f"/visualizacion?msg=Error:+{error_msg}&cat=danger",
            status_code=303
        )


# ══════════════════════════════════════════════════════════════════
# LIVE — Dashboard en tiempo real para el Showcase
# ══════════════════════════════════════════════════════════════════

def _norm_estado(nombre: str) -> str:
    """Normaliza nombres de estado del CNE para que coincidan con el GeoJSON."""
    nombre = (nombre
              .replace("EDO. ", "")
              .replace("DTTO. ", "Distrito ")
              .replace("DELTA AMAC", "Delta Amacuro")
              .replace("LA GUAIRA", "La Guaira")
              .replace("NVA. ESPARTA", "Nueva Esparta"))
    if nombre not in ("Distrito Capital", "La Guaira", "Delta Amacuro", "Nueva Esparta"):
        nombre = nombre.title()
    return nombre


def _datos_vivos(db, id_eleccion: int) -> tuple:
    """
    Lee votos reales de la BD y devuelve
    (datos_ventaja, datos_tendencia, total_votos).

    datos_ventaja  : {nombre_estado: ventaja_float}   — gobierno - oposición en %
    datos_tendencia: {NOMBRE_UPPER: [{"hora","gob","opo"}, ...]}  — acumulados por turno
    """
    total = db.execute("""
        SELECT COUNT(*) c FROM votos v
        JOIN muestra m ON m.codigo_centro = v.codigo_centro
        WHERE m.id_eleccion = ? AND v.valido = 1
    """, (id_eleccion,)).fetchone()["c"]

    if total == 0:
        return {}, {}, 0

    # ── Ventaja final por estado ──────────────────────────────────
    rows_est = db.execute("""
        SELECT
            est.nombre                                              AS estado,
            SUM(CASE WHEN ca.bando = 'gobierno'  THEN 1 ELSE 0 END) AS gob,
            SUM(CASE WHEN ca.bando = 'oposicion' THEN 1 ELSE 0 END) AS opo,
            COUNT(*)                                                AS total
        FROM votos v
        JOIN muestra    m   ON m.codigo_centro = v.codigo_centro
        JOIN centros    c   ON c.codigo_cne    = v.codigo_centro
        JOIN estados    est ON est.id          = c.id_estado
        JOIN candidatos ca  ON ca.id           = v.id_candidato
        WHERE v.valido = 1 AND m.id_eleccion = ?
        GROUP BY est.id
    """, (id_eleccion,)).fetchall()

    datos_ventaja = {}
    for r in rows_est:
        if r["total"] > 0:
            ventaja = round(100 * r["gob"] / r["total"] - 100 * r["opo"] / r["total"], 1)
            datos_ventaja[_norm_estado(r["estado"])] = ventaja

    # ── Tendencias acumuladas — nacional ─────────────────────────
    rows_nac = db.execute("""
        SELECT
            v.turno,
            MIN(v.hora)                                             AS hora_min,
            SUM(CASE WHEN ca.bando = 'gobierno'  THEN 1 ELSE 0 END) AS gob,
            SUM(CASE WHEN ca.bando = 'oposicion' THEN 1 ELSE 0 END) AS opo
        FROM votos v
        JOIN muestra    m  ON m.codigo_centro = v.codigo_centro
        JOIN candidatos ca ON ca.id           = v.id_candidato
        WHERE v.valido = 1 AND m.id_eleccion = ?
        GROUP BY v.turno
        ORDER BY v.turno
    """, (id_eleccion,)).fetchall()

    datos_tendencia = {}
    puntos_nac, cum_g, cum_o = [], 0, 0
    for r in rows_nac:
        cum_g += r["gob"]
        cum_o += r["opo"]
        tot = cum_g + cum_o
        if tot:
            h = r["hora_min"]
            hora = h[11:16] if h and "T" in h else (h or "07:00")[:5]
            puntos_nac.append({
                "hora": hora,
                "gob": round(100 * cum_g / tot, 1),
                "opo": round(100 * cum_o / tot, 1),
            })
    datos_tendencia["VENEZUELA"] = puntos_nac

    # ── Tendencias acumuladas — por estado ────────────────────────
    rows_t = db.execute("""
        SELECT
            est.nombre                                              AS estado,
            v.turno,
            MIN(v.hora)                                             AS hora_min,
            SUM(CASE WHEN ca.bando = 'gobierno'  THEN 1 ELSE 0 END) AS gob,
            SUM(CASE WHEN ca.bando = 'oposicion' THEN 1 ELSE 0 END) AS opo
        FROM votos v
        JOIN muestra    m   ON m.codigo_centro = v.codigo_centro
        JOIN centros    c   ON c.codigo_cne    = v.codigo_centro
        JOIN estados    est ON est.id          = c.id_estado
        JOIN candidatos ca  ON ca.id           = v.id_candidato
        WHERE v.valido = 1 AND m.id_eleccion = ?
        GROUP BY est.id, v.turno
        ORDER BY est.nombre, v.turno
    """, (id_eleccion,)).fetchall()

    por_estado = {}
    for r in rows_t:
        por_estado.setdefault(r["estado"], []).append(r)

    for estado_db, turnos in por_estado.items():
        nombre_up = _norm_estado(estado_db).upper()
        puntos, cum_g, cum_o = [], 0, 0
        for r in sorted(turnos, key=lambda x: x["turno"]):
            cum_g += r["gob"]
            cum_o += r["opo"]
            tot = cum_g + cum_o
            if tot:
                h = r["hora_min"]
                hora = h[11:16] if h and "T" in h else (h or "07:00")[:5]
                puntos.append({
                    "hora": hora,
                    "gob": round(100 * cum_g / tot, 1),
                    "opo": round(100 * cum_o / tot, 1),
                })
        datos_tendencia[nombre_up] = puntos

    return datos_ventaja, datos_tendencia, total


def _html_sin_datos(motivo: str, refresh: int) -> str:
    """Página con mapa base en gris y mensaje de espera. Auto-refresca."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        import generador_heatmap
        import importlib
        importlib.reload(generador_heatmap)
        tmp = tempfile.mktemp(suffix=".html")
        generador_heatmap.generar_heatmap(
            {}, nivel="estado", ruta_salida=tmp,
            titulo="Exit Poll — En Vivo"
        )
        with open(tmp, encoding="utf-8") as f:
            base_html = f.read()
        os.unlink(tmp)
    except Exception:
        base_html = "<html><head></head><body></body></html>"

    overlay = f"""
<div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
     z-index:9999;background:rgba(0,0,0,.75);color:white;
     font-family:sans-serif;font-size:16px;padding:28px 40px;
     border-radius:12px;text-align:center;max-width:440px;
     box-shadow:0 4px 24px rgba(0,0,0,.4);">
  <div style="font-size:36px;margin-bottom:14px;">&#x1F4E1;</div>
  <div style="font-weight:bold;margin-bottom:10px;line-height:1.4">{motivo}</div>
  <div style="font-size:12px;opacity:.65;margin-top:6px;">
    Actualizando cada {refresh}s&nbsp;&nbsp;&#x21BB;
  </div>
</div>"""

    meta = f'<meta http-equiv="refresh" content="{refresh}">'
    html = base_html.replace("</head>", f"{meta}</head>", 1)
    html = re.sub(r"(<body[^>]*>)", r"\1" + overlay + _analista_live_panel(), html, count=1)
    return html


def _contexto_analista(db, eleccion, candidatos_dict: dict) -> dict:
    """Codex: resume el live dashboard en datos cerrados para el analista sin tokens."""
    if not eleccion:
        return {
            "ok": False,
            "motivo": "No hay eleccion activa",
            "total_votos": 0,
        }

    eid = eleccion["id"]
    datos_ventaja, datos_tendencia, total_votos = _datos_vivos(db, eid)
    muestra_total = db.execute(
        "SELECT COUNT(*) c FROM muestra WHERE id_eleccion=? AND activo=1",
        (eid,),
    ).fetchone()["c"]
    centros_reportando = db.execute("""
        SELECT COUNT(DISTINCT v.codigo_centro) c
        FROM votos v
        JOIN muestra m ON m.codigo_centro = v.codigo_centro
        WHERE m.id_eleccion = ? AND v.valido = 1
    """, (eid,)).fetchone()["c"]

    puntos_nac = datos_tendencia.get("VENEZUELA") or []
    ventajas_nacionales = [
        round(float(p["gob"]) - float(p["opo"]), 1)
        for p in puntos_nac
    ]
    ventaja_actual = ventajas_nacionales[-1] if ventajas_nacionales else None
    hora_actual = puntos_nac[-1]["hora"] if puntos_nac else None

    if ventaja_actual is None:
        candidato_arriba = None
        candidato_abajo = None
    elif ventaja_actual >= 0:
        candidato_arriba = candidatos_dict.get("gobierno", "Gobierno")
        candidato_abajo = candidatos_dict.get("oposicion", "Oposicion")
    else:
        candidato_arriba = candidatos_dict.get("oposicion", "Oposicion")
        candidato_abajo = candidatos_dict.get("gobierno", "Gobierno")

    tendencias_por_estado = {k: v for k, v in datos_tendencia.items() if k != "VENEZUELA"}

    return {
        "ok": True,
        "eleccion": eleccion["nombre"],
        "hora_actual": hora_actual,
        "total_votos": total_votos,
        "centros_reportando": centros_reportando,
        "centros_muestra_total": muestra_total,
        "cobertura_pct": round(100 * centros_reportando / muestra_total, 1) if muestra_total else 0,
        "ventaja_actual": ventaja_actual,
        "ventajas_nacionales": ventajas_nacionales,
        "candidato_arriba": candidato_arriba,
        "candidato_abajo": candidato_abajo,
        "ventajas_por_estado": datos_ventaja,
        "tendencias_por_estado": tendencias_por_estado,
        "candidatos": candidatos_dict,
    }


@app.get("/api/analista/contexto")
async def analista_contexto():
    db = get_db()
    try:
        eleccion = db.execute(
            "SELECT * FROM elecciones WHERE activa = 1 LIMIT 1"
        ).fetchone()
        candidatos_dict = _nombres_candidatos(db, eleccion["id"]) if eleccion else {}
        return JSONResponse(_contexto_analista(db, eleccion, candidatos_dict))
    finally:
        db.close()


@app.post("/api/analista/preguntar")
async def analista_preguntar(request: Request):
    payload = await request.json()
    pregunta = (payload.get("pregunta") or "").strip()
    db = get_db()
    try:
        eleccion = db.execute(
            "SELECT * FROM elecciones WHERE activa = 1 LIMIT 1"
        ).fetchone()
        candidatos_dict = _nombres_candidatos(db, eleccion["id"]) if eleccion else {}
        contexto = _contexto_analista(db, eleccion, candidatos_dict)

        sys.path.insert(0, str(BASE_DIR))
        import analista_ia
        return JSONResponse(analista_ia.analizar_contexto(contexto, pregunta))
    finally:
        db.close()


def _analista_live_panel() -> str:
    """Codex: panel persistente; localStorage evita perder el chat con refresh cada 5s."""
    return """
<!-- Codex: AI electoral analyst panel, deterministic and refresh-safe. -->
<style>
  #ai-analyst {
    position: fixed; right: 16px; bottom: 16px; z-index: 100000;
    width: min(390px, calc(100vw - 32px)); background: #fff; color: #1f2933;
    border: 1px solid rgba(0,0,0,.18); border-radius: 8px;
    box-shadow: 0 8px 28px rgba(0,0,0,.28); font-family: Arial, sans-serif;
  }
  #ai-analyst header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 9px 11px; background: #1a3a5c; color: #fff;
    border-radius: 8px 8px 0 0; font-size: 13px; font-weight: 700;
  }
  #ai-analyst-log { max-height: 270px; overflow-y: auto; padding: 10px; font-size: 12px; }
  .ai-msg { margin-bottom: 8px; line-height: 1.35; }
  .ai-q { color: #1a3a5c; font-weight: 700; }
  .ai-a { background: #f4f7fb; border-left: 3px solid #1a3a5c; padding: 8px; border-radius: 4px; }
  #ai-analyst form { display: flex; gap: 6px; padding: 9px; border-top: 1px solid #e5e7eb; }
  #ai-analyst input { flex: 1; min-width: 0; padding: 7px; border: 1px solid #cbd5e1; border-radius: 5px; font-size: 12px; }
  #ai-analyst button { border: 0; border-radius: 5px; padding: 7px 9px; background: #1a3a5c; color: #fff; font-size: 12px; cursor: pointer; }
  #ai-analyst-clear { background: transparent !important; padding: 0 !important; color: #dbeafe !important; }
</style>
<section id="ai-analyst" aria-label="Analista electoral">
  <header>
    <span>AI Electoral Analyst</span>
    <button id="ai-analyst-clear" type="button">limpiar</button>
  </header>
  <div id="ai-analyst-log"></div>
  <form id="ai-analyst-form">
    <input id="ai-analyst-input" autocomplete="off" placeholder="Pregunta por la tendencia actual">
    <button type="submit">Analizar</button>
  </form>
</section>
<script>
(function() {
  var key = 'exitpoll.aiAnalyst.history';
  var draftKey = 'exitpoll.aiAnalyst.draft';
  var log = document.getElementById('ai-analyst-log');
  var input = document.getElementById('ai-analyst-input');
  var form = document.getElementById('ai-analyst-form');
  var clear = document.getElementById('ai-analyst-clear');

  function history() {
    try { return JSON.parse(localStorage.getItem(key) || '[]'); }
    catch(e) { return []; }
  }
  function save(items) { localStorage.setItem(key, JSON.stringify(items.slice(-8))); }
  function render() {
    var items = history();
    if (!items.length) {
      log.innerHTML = '<div class="ai-msg ai-a">Pregunta por ventaja, estabilidad o suficiencia de datos. No declaro ganadores.</div>';
      return;
    }
    log.innerHTML = items.map(function(item) {
      return '<div class="ai-msg"><div class="ai-q">' + escapeHtml(item.q) + '</div>' +
             '<div class="ai-a">' + escapeHtml(item.a) + '</div></div>';
    }).join('');
    log.scrollTop = log.scrollHeight;
  }
  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, function(c) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  }
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    var q = (input.value || '').trim();
    if (!q) return;
    input.value = '';
    localStorage.removeItem(draftKey);
    fetch('/api/analista/preguntar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({pregunta: q})
    }).then(function(r) { return r.json(); }).then(function(data) {
      var items = history();
      items.push({q: q, a: data.resumen || 'No hay lectura disponible.'});
      save(items);
      render();
    }).catch(function() {
      var items = history();
      items.push({q: q, a: 'No pude consultar el analista en este momento.'});
      save(items);
      render();
    });
  });
  input.value = localStorage.getItem(draftKey) || '';
  input.addEventListener('input', function() { localStorage.setItem(draftKey, input.value || ''); });
  clear.addEventListener('click', function() {
    localStorage.removeItem(key);
    localStorage.removeItem(draftKey);
    input.value = '';
    render();
  });
  render();
})();
</script>
"""


@app.get("/live", response_class=HTMLResponse)
async def live_dashboard(refresh: int = 5):
    """
    Dashboard en tiempo real.
    Abrir en el browser y correr simulador_showcase.py en otra terminal.
    El mapa y las tendencias se actualizan solos cada `refresh` segundos.
    """
    db = get_db()
    try:
        eleccion = db.execute(
            "SELECT * FROM elecciones WHERE activa = 1 LIMIT 1"
        ).fetchone()

        if not eleccion:
            return HTMLResponse(_html_sin_datos("No hay elección activa", refresh))

        eid = eleccion["id"]
        datos_ventaja, datos_tendencia, total_votos = _datos_vivos(db, eid)
        candidatos_dict = _nombres_candidatos(db, eid)
    finally:
        db.close()

    if total_votos == 0:
        return HTMLResponse(_html_sin_datos(
            f"Simulación no iniciada<br>"
            f"<small style='font-size:13px;opacity:.8'>{eleccion['nombre']}</small><br>"
            f"<small style='font-size:11px;opacity:.55'>"
            f"Corre: python backend/simulador_showcase.py --reset</small>",
            refresh,
        ))

    # ── Generar dashboard completo ────────────────────────────────
    sys.path.insert(0, str(BASE_DIR))
    import generador_dashboard
    import importlib
    importlib.reload(generador_dashboard)

    titulo = f"{eleccion['nombre']} — EN VIVO"
    tmp = tempfile.mktemp(suffix=".html")
    try:
        generador_dashboard.generar_dashboard(
            datos_ventaja, datos_tendencia,
            nivel="estado", ruta_salida=tmp,
            titulo=titulo, candidatos=candidatos_dict,
        )
        with open(tmp, encoding="utf-8") as f:
            html = f.read()
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    # ── Inyectar meta-refresh y barra de estado ───────────────────
    meta = f'<meta http-equiv="refresh" content="{refresh}">'

    barra = (
        f'<style>:root{{--ep-top-offset:28px;}}</style>'
        f'<div style="position:fixed;top:0;left:0;right:0;z-index:99999;'
        f'background:#1B5E20;color:white;font-family:sans-serif;font-size:12px;'
        f'padding:5px 16px;display:flex;justify-content:space-between;align-items:center;'
        f'box-shadow:0 2px 6px rgba(0,0,0,.35);">'
        f'<span>&#x1F534;&nbsp; EN VIVO &nbsp;&#x2502;&nbsp; {eleccion["nombre"]}'
        f'&nbsp;&#x2502;&nbsp; {total_votos:,} votos procesados</span>'
        f'<span style="opacity:.7">&#x21BB;&nbsp;cada {refresh}s</span>'
        f'</div>'
    )

    html = html.replace("</head>", f"{meta}</head>", 1)
    html = re.sub(r"(<body[^>]*>)", r"\1" + barra + _analista_live_panel(), html, count=1)

    return HTMLResponse(html)


# =============================================================
# TEST — carga de datos de demostración
# =============================================================

CSV_2024 = BASE_DIR / "resultados_cne2024.csv"
_CANDIDATOS_DEMO = [
    {"nombre": "Nicolás Maduro",   "partido": "PSUV", "bando": "gobierno",  "tipo": "unico", "orden": 1},
    {"nombre": "Edmundo González", "partido": "PUD",  "bando": "oposicion", "tipo": "unico", "orden": 2},
]


def _pct_2024() -> dict[str, tuple[float, float]]:
    pct: dict[str, tuple[float, float]] = {}
    with open(CSV_2024, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pct[row["centro_cne_id"]] = (
                float(row["pct_gobierno"]) / 100,
                float(row["pct_oposicion"]) / 100,
            )
    return pct


def _asegurar_candidatos(db: sqlite3.Connection, id_eleccion: int) -> dict[str, int]:
    rows = db.execute(
        "SELECT id, bando FROM candidatos WHERE id_eleccion=?", (id_eleccion,)
    ).fetchall()
    if rows:
        return {r["bando"]: r["id"] for r in rows}
    for c in _CANDIDATOS_DEMO:
        db.execute(
            "INSERT INTO candidatos (id_eleccion, nombre, partido, bando, tipo, orden) "
            "VALUES (?,?,?,?,?,?)",
            (id_eleccion, c["nombre"], c["partido"], c["bando"], c["tipo"], c["orden"]),
        )
    db.commit()
    return {r["bando"]: r["id"] for r in db.execute(
        "SELECT id, bando FROM candidatos WHERE id_eleccion=?", (id_eleccion,)
    )}


def _insertar_votos(db: sqlite3.Connection, eleccion, centros, cands, pct, turnos_subset):
    for idx, hora_str in enumerate(turnos_subset):
        turno_num = idx + 1
        hora_iso  = f'{eleccion["fecha"]}T{hora_str}:00'
        for c in centros:
            cod  = c["codigo_centro"]
            p_g, p_o = pct.get(cod, (0.5, 0.5))
            p_tot = p_g + p_o
            tel  = f'+58414{c["id_muestra"]:07d}'
            lat  = c["lat"]  or (10.5  + random.uniform(-2, 2))
            lon  = c["lon"]  or (-66.9 + random.uniform(-3, 3))
            for _ in range(3):
                id_cand = (cands["gobierno"]
                           if random.random() < (p_g / p_tot)
                           else cands["oposicion"])
                cur = db.execute(
                    "INSERT INTO sms_raw (from_number, contenido, recibido_at, procesado) "
                    "VALUES (?,?,?,1)",
                    (tel, f"DEMO T{turno_num}", hora_iso),
                )
                db.execute(
                    "INSERT INTO votos (id_sms, codigo_centro, id_candidato, telefono, "
                    "hora, turno, lat, lon, distancia_m, valido) VALUES (?,?,?,?,?,?,?,?,?,1)",
                    (cur.lastrowid, cod, id_cand, tel,
                     hora_iso, turno_num, lat, lon, random.randint(30, 280)),
                )


def _encuestadores_demo(db: sqlite3.Connection, centros, id_eleccion: int):
    for c in centros:
        tel = f'+58414{c["id_muestra"]:07d}'
        db.execute(
            "INSERT OR IGNORE INTO encuestadores (telefono, nombre, codigo_centro, id_eleccion) "
            "VALUES (?,?,?,?)",
            (tel, f'Demo-{c["id_muestra"]}', c["codigo_centro"], id_eleccion),
        )


def _turnos(eleccion) -> list[str]:
    t      = datetime.strptime(eleccion["hora_apertura"], "%H:%M")
    cierre = datetime.strptime(eleccion["hora_cierre"],   "%H:%M")
    result = []
    while t <= cierre:
        result.append(t.strftime("%H:%M"))
        t += timedelta(minutes=20)
    return result


@app.post("/test/demo")
async def test_demo():
    """Carga el dataset completo (todos los turnos) con datos CNE 2024."""
    db = get_db()
    try:
        eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1").fetchone()
        if not eleccion:
            return JSONResponse({"ok": False, "mensaje": "No hay elección activa."}, status_code=400)
        cands   = _asegurar_candidatos(db, eleccion["id"])
        centros = db.execute(
            "SELECT m.id AS id_muestra, m.codigo_centro, c.num_electores, c.lat, c.lon "
            "FROM muestra m JOIN centros c ON c.codigo_cne=m.codigo_centro "
            "WHERE m.id_eleccion=? AND m.activo=1 AND c.activo=1", (eleccion["id"],)
        ).fetchall()
        pct = _pct_2024()
        db.execute("DELETE FROM votos"); db.execute("DELETE FROM sms_raw"); db.commit()
        _encuestadores_demo(db, centros, eleccion["id"])
        turnos = _turnos(eleccion)
        _insertar_votos(db, eleccion, centros, cands, pct, turnos)
        db.commit()
        total = db.execute("SELECT COUNT(*) FROM votos").fetchone()[0]
        return JSONResponse({"ok": True, "mensaje": f"Dataset completo cargado: {total:,} votos en {len(turnos)} turnos."})
    except Exception as e:
        db.rollback()
        return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=500)
    finally:
        db.close()


@app.post("/test/entrada")
async def test_entrada():
    """Carga solo los primeros 6 turnos (~2 horas) para mostrar el estado de muestra parcial."""
    db = get_db()
    try:
        eleccion = db.execute("SELECT * FROM elecciones WHERE activa=1").fetchone()
        if not eleccion:
            return JSONResponse({"ok": False, "mensaje": "No hay elección activa."}, status_code=400)
        cands   = _asegurar_candidatos(db, eleccion["id"])
        centros = db.execute(
            "SELECT m.id AS id_muestra, m.codigo_centro, c.num_electores, c.lat, c.lon "
            "FROM muestra m JOIN centros c ON c.codigo_cne=m.codigo_centro "
            "WHERE m.id_eleccion=? AND m.activo=1 AND c.activo=1", (eleccion["id"],)
        ).fetchall()
        pct = _pct_2024()
        db.execute("DELETE FROM votos"); db.execute("DELETE FROM sms_raw"); db.commit()
        _encuestadores_demo(db, centros, eleccion["id"])
        # Solo la mitad de centros reportan (simula entrada parcial de datos)
        centros_activos = centros[: len(centros) // 2]
        turnos = _turnos(eleccion)[:6]
        _insertar_votos(db, eleccion, centros_activos, cands, pct, turnos)
        db.commit()
        total = db.execute("SELECT COUNT(*) FROM votos").fetchone()[0]
        return JSONResponse({"ok": True, "mensaje": f"Entrada parcial cargada: {total:,} votos — {len(centros_activos)}/{len(centros)} centros, primeros 6 turnos."})
    except Exception as e:
        db.rollback()
        return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=500)
    finally:
        db.close()


@app.post("/test/reset")
async def test_reset():
    """Elimina todos los votos y sms_raw de la elección activa."""
    db = get_db()
    try:
        db.execute("DELETE FROM votos")
        db.execute("DELETE FROM sms_raw")
        db.commit()
        return JSONResponse({"ok": True, "mensaje": "Datos de prueba eliminados."})
    except Exception as e:
        db.rollback()
        return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=500)
    finally:
        db.close()
