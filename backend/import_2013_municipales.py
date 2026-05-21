"""Import 2013 municipal exit-poll studies into historico tables.

The local core is ``auditoria4.xlsx``. It contains the fast-count input, the
weighted candidate totals, and the operational audit screens used as a
semaforo for center reliability. Official results are scraped from the archived
CNE municipal-results site, only for municipalities present in the study.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import time
import unicodedata
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests


BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "exitpoll.db"
DATA_DIR = BASE_DIR / "data" / "2013" / "municipales"
CORE = DATA_DIR / "auditoria4.xlsx"
PESOS = DATA_DIR / "PESO CENTROS DIC 2013.xlsx"
REF = "2013-municipales"
NOMBRE = "Elecciones Municipales 2013"
FECHA = "2013-12-08"
ARCHIVE_PREFIX = "https://web.archive.org/web/20190812031057/"
CNE_ROOT = "http://www.cne.gob.ve/resultado_municipal_2013/r"


STUDIED_MUNICIPALITIES = {
    1: ("distrito-metropolitano-caracas", "Distrito Metropolitano de Caracas", "Distrito Metropolitano de Caracas", "000001"),
    2: ("distrito-capital-libertador", "Distrito Capital", "Libertador", "010100"),
    3: ("amazonas-atures", "Amazonas", "Atures", "220100"),
    4: ("anzoategui-bolivar", "Anzoategui", "Bolivar", "020300"),
    5: ("anzoategui-freites", "Anzoategui", "Freites", "020600"),
    6: ("anzoategui-simon-rodriguez", "Anzoategui", "Simon Rodriguez", "021200"),
    7: ("anzoategui-sotillo", "Anzoategui", "Sotillo", "021300"),
    8: ("apure-san-fernando", "Apure", "San Fernando", "030600"),
    9: ("aragua-girardot", "Aragua", "Girardot", "040100"),
    10: ("aragua-jose-felix-ribas", "Aragua", "Jose Felix Ribas", "040300"),
    11: ("aragua-santiago-marino", "Aragua", "Santiago Marino", "040200"),
    12: ("aragua-zamora", "Aragua", "Zamora", "040800"),
    13: ("barinas-barinas", "Barinas", "Barinas", "050200"),
    14: ("bolivar-caroni", "Bolivar", "Caroni", "060100"),
    15: ("bolivar-heres", "Bolivar", "Heres", "060300"),
    16: ("carabobo-guacara", "Carabobo", "Guacara", "070400"),
    17: ("carabobo-libertador", "Carabobo", "Libertador", "071400"),
    18: ("carabobo-puerto-cabello", "Carabobo", "Puerto Cabello", "070700"),
    19: ("carabobo-valencia", "Carabobo", "Valencia", "070900"),
    20: ("cojedes-ezequiel-zamora", "Cojedes", "Ezequiel Zamora", "080600"),
    21: ("delta-amacuro-tucupita", "Delta Amacuro", "Tucupita", "230100"),
    22: ("falcon-carirubana", "Falcon", "Carirubana", "090400"),
    23: ("falcon-miranda", "Falcon", "Miranda", "091000"),
    24: ("guarico-juan-german-roscio", "Guarico", "Juan German Roscio", "100600"),
    25: ("guarico-miranda", "Guarico", "Miranda", "100300"),
    26: ("lara-iribarren", "Lara", "Iribarren", "110200"),
    27: ("lara-moran", "Lara", "Moran", "110400"),
    28: ("lara-palavecino", "Lara", "Palavecino", "110500"),
    29: ("lara-torres", "Lara", "Torres", "110600"),
    30: ("merida-libertador", "Merida", "Libertador", "120800"),
    31: ("miranda-baruta", "Miranda", "Baruta", "131600"),
    32: ("miranda-guaicaipuro", "Miranda", "Guaicaipuro", "130300"),
    33: ("miranda-plaza", "Miranda", "Plaza", "130800"),
    34: ("miranda-sucre", "Miranda", "Sucre", "130900"),
    35: ("monagas-maturin", "Monagas", "Maturin", "140700"),
    36: ("nueva-esparta-marino", "Nueva Esparta", "Marino", "150600"),
    37: ("portuguesa-araure", "Portuguesa", "Araure", "160100"),
    38: ("portuguesa-guanare", "Portuguesa", "Guanare", "160300"),
    39: ("portuguesa-paez", "Portuguesa", "Paez", "160600"),
    40: ("sucre-bermudez", "Sucre", "Bermudez", "170300"),
    41: ("sucre-sucre", "Sucre", "Sucre", "170900"),
    42: ("tachira-san-cristobal", "Tachira", "San Cristobal", "180800"),
    43: ("trujillo-valera", "Trujillo", "Valera", "190700"),
    44: ("vargas-vargas", "Vargas", "Vargas", "240100"),
    45: ("yaracuy-san-felipe", "Yaracuy", "San Felipe", "200400"),
    46: ("zulia-cabimas", "Zulia", "Cabimas", "211400"),
    47: ("zulia-lagunillas", "Zulia", "Lagunillas", "211100"),
    48: ("zulia-mara", "Zulia", "Mara", "210400"),
    49: ("zulia-maracaibo", "Zulia", "Maracaibo", "210500"),
    50: ("zulia-san-francisco", "Zulia", "San Francisco", "211800"),
    51: ("monagas-cedeno", "Monagas", "Cedeno", "140400"),
    52: ("anzoategui-anaco", "Anzoategui", "Anaco", "020100"),
}


GOV_CANDIDATE = 1
OPOS_CANDIDATE = 2
TURN_LABELS = {
    0: "Base auditada",
    1: "1er corte",
    2: "2do corte",
    3: "3er corte",
    4: "4to corte",
    5: "5to corte",
    6: "6to corte",
    7: "7mo corte",
    8: "8vo corte",
    9: "9no corte",
}


@dataclass
class OfficialResult:
    pct_gov: float
    pct_opos: float
    pct_otros: float
    total_votos: int
    source_url: str
    gov_name: str | None
    opos_name: str | None


MANUAL_OFFICIAL_RESULTS = {
    8: OfficialResult(
        pct_gov=65.27,
        pct_opos=32.19,
        pct_otros=2.54,
        total_votos=52279,
        source_url="CNE 2013 via archive.org, ficha tecnica provista manualmente",
        gov_name="OFELIA PADRON",
        opos_name="YADALA ABOUHADOUR",
    ),
    13: OfficialResult(
        pct_gov=48.58,
        pct_opos=50.44,
        pct_otros=0.98,
        total_votos=110772,
        source_url="CNE 2013 via archive.org, ficha tecnica provista manualmente",
        gov_name="EDGARDO RAMIREZ",
        opos_name="MACHIN MACHIN",
    ),
    35: OfficialResult(
        pct_gov=37.26,
        pct_opos=38.63,
        pct_otros=24.11,
        total_votos=194245,
        source_url="CNE 2013 via archive.org, ficha tecnica provista manualmente",
        gov_name="JOSE MAICAVARES",
        opos_name="WARNER JIMENEZ",
    ),
    39: OfficialResult(
        pct_gov=67.78,
        pct_opos=26.13,
        pct_otros=6.09,
        total_votos=55045,
        source_url="CNE 2013 via archive.org, ficha tecnica provista manualmente",
        gov_name="EFREN PEREZ",
        opos_name="ELIAS BITTAR",
    ),
    41: OfficialResult(
        pct_gov=54.71,
        pct_opos=42.35,
        pct_otros=2.94,
        total_votos=123333,
        source_url="CNE 2013 via archive.org, ficha tecnica provista manualmente",
        gov_name="DAVID VELASQUEZ",
        opos_name="ROBERT ALCALA",
    ),
}


def _strip_accents(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _norm(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value)))
    value = _strip_accents(value).upper()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _pct(part: float, total: float) -> float:
    return round(part * 100.0 / total, 2) if total else 0.0


def _archive_url(cne_path: str, side: int = 1) -> str:
    code = cne_path if cne_path.endswith(".html") else f"reg_{cne_path}.html"
    return f"{ARCHIVE_PREFIX}{CNE_ROOT}/{side}/{code}"


FETCH_DELAY_SECONDS = 0.0
FETCH_RETRIES = 3


def _fetch(url: str) -> str:
    last_exc = None
    for attempt in range(1, FETCH_RETRIES + 1):
        if FETCH_DELAY_SECONDS:
            time.sleep(FETCH_DELAY_SECONDS)
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "exit-poll-import/1.0"})
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            last_exc = exc
            if attempt < FETCH_RETRIES:
                time.sleep(max(FETCH_DELAY_SECONDS, 1.0) * attempt)
    raise last_exc


def _wayback_href(href: str) -> str:
    if href.startswith("/web/"):
        return "https://web.archive.org" + href
    if href.startswith("http://") or href.startswith("https://"):
        return ARCHIVE_PREFIX + href if "web.archive.org" not in href else href
    return urllib.parse.urljoin(ARCHIVE_PREFIX, href)


def _num(text: str) -> int:
    cleaned = re.sub(r"[^0-9]", "", text)
    return int(cleaned) if cleaned else 0


def _mayor_contest_segment(page: str) -> str:
    title_pattern = re.compile(
        r"<a\b[^>]*id=\"ContestTitle\"[^>]*>(.*?)</a>",
        re.S | re.I,
    )
    for match in title_pattern.finditer(page):
        title = _norm(match.group(1))
        if "ALCALDESA O ALCALDE" not in title:
            continue
        start = match.start()
        next_title = title_pattern.search(page, match.end())
        end = next_title.start() if next_title else len(page)
        return page[start:end]
    return page


def _candidate_rows(page: str) -> list[tuple[str, int]]:
    page = _mayor_contest_segment(page)
    rows = []
    pattern = re.compile(
        r"<tr class=\"tbsubtotalrow\".*?<a href=\"javascript:showCandidateInfo\('[^']+'\);\">(.*?)</a>.*?"
        r"<td class=\"lightRowContent\" align=\"right\"[^>]*><span>([\d.]+)</span></td>",
        re.S,
    )
    for name, votes in pattern.findall(page):
        rows.append((html.unescape(re.sub(r"<[^>]+>", " ", name)).strip(), _num(votes)))
    return rows


def _region_links(page: str) -> list[tuple[str, str, str]]:
    links = []
    pattern = re.compile(r"<a id=\"(\d{6})\" href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.S)
    for code, href, label in pattern.findall(page):
        text = html.unescape(re.sub(r"<[^>]+>", " ", label)).strip()
        text = re.sub(r"\s+", " ", text)
        links.append((code, text, href))
    return links


def discover_cne_codes() -> dict[str, tuple[str, str]]:
    national = _fetch(_archive_url("000000"))
    state_links = [item for item in _region_links(national) if item[0].endswith("0000")]
    found = {}
    for state_code, state_name, href in state_links:
        try:
            page = _fetch(_wayback_href(href))
        except Exception as exc:
            print(f"WARN: no se pudo leer {state_name} ({state_code}): {exc}")
            continue
        for code, name, link in _region_links(page):
            if code == state_code or code.endswith("0000"):
                continue
            found[f"{_norm(state_name)}|{_norm(name)}"] = (code, name)
    for code, name, _ in _region_links(national):
        if code in {"000001", "000002"}:
            found[f"ESPECIAL|{_norm(name)}"] = (code, name)
    return found


def _official_for_code(code: str) -> OfficialResult:
    for side in (1, 2):
        url = _archive_url(code, side)
        try:
            rows = _candidate_rows(_fetch(url))
        except Exception as exc:
            print(f"WARN: no se pudo leer {code} lado {side}: {exc}")
            continue
        if rows:
            gov_votes = opos_votes = 0
            gov_name = opos_name = None
            other_votes = 0
            for name, votes in rows:
                n = _norm(name)
                if n in {"ERNESTO VILLEGAS", "JORGE RODRIGUEZ"} or votes and name:
                    pass
                if n in GOV_NAMES:
                    gov_votes += votes
                    gov_name = gov_name or name
                elif n in OPOS_NAMES:
                    opos_votes += votes
                    opos_name = opos_name or name
                else:
                    other_votes += votes
            if gov_votes == 0 or opos_votes == 0:
                ordered = sorted(rows, key=lambda item: item[1], reverse=True)
                if len(ordered) >= 2:
                    # Fallback keeps the page usable if a low-salience municipality
                    # has an unexpected spelling; candidate 1/2 matching is validated
                    # against the study names in the generated notes.
                    gov_name, gov_votes = ordered[0]
                    opos_name, opos_votes = ordered[1]
                    other_votes = sum(v for _, v in ordered[2:])
            total = gov_votes + opos_votes + other_votes
            return OfficialResult(
                pct_gov=_pct(gov_votes, total),
                pct_opos=_pct(opos_votes, total),
                pct_otros=_pct(other_votes, total),
                total_votos=total,
                source_url=url,
                gov_name=gov_name,
                opos_name=opos_name,
            )
    raise RuntimeError(f"No se pudo leer resultado oficial para {code}")


GOV_NAMES = {
    _norm(name) for name in [
        "ERNESTO VILLEGAS", "JORGE RODRIGUEZ", "ELKIS BASTIDAS",
        "GUILLERMO MARTINEZ", "DANIEL HARO", "JESUS FIGUERA",
        "MAGGLIO ORDOÑEZ", "OFELIA PADRON", "PEDRO BASTIDAS",
        "JUAN C. SANCHEZ", "ALBERTO MORA", "MICHAEL REYES",
        "EDGARDO RAMIREZ", "JOSE RAMON LOPEZ", "SERGIO HERNANDEZ",
        "JUAN PEROZO", "MIGUEL FLORES", "RAFAEL LACAVA",
        "GERARDO SANCHEZ", "PABLO RODRIGUEZ", "ALEXIS GONZALEZ",
        "ALCIDES GOITIA", "PABLO ACOSTA", "GUSTAVO MENDEZ",
        "ZOBEIDA EL HINNAQUI", "LUIS BOHORQUEZ", "TEODULO MEDINA",
        "VICTOR DELGADO", "EDGAR CARRASCO", "MARIA CASTILLO",
        "WINSTON VALLENILLA", "FRANCISCO GARCES", "RODOLFO SANZ",
        "ANTONIO ALVAREZ", "JOSE MAICAVARES", "DANTE RIVAS",
        "NUBIA CUPARE", "RAFAEL CALLES", "EFREN PEREZ",
        "JULIO RODRIGUEZ", "DAVID VELASQUEZ", "JOSE ZAMBRANO",
        "GILBERTO HERNANDE", "CARLOS ALCALA", "ALEX SANCHEZ",
        "FELIX BRACHO", "FRANCISCO ALVARAD", "LUIS CALDERA",
        "PEREZ PIRELA", "OMAR PRIETO", "VILMA CARVAJAL",
        "MARCOS RAMOS",
    ]
}

OPOS_NAMES = {
    _norm(name) for name in [
        "ANTONIO LEDEZMA", "ISMAEL GARCIA", "ADRIANA GONZALEZ",
        "CARLOS MICHELANGELI", "EVELIN URDANETA", "JOSE BRITO",
        "MARCO FIGUEROA", "TONNY REAL", "LUIS BLANCO",
        "JESUS CASTILLO", "ALEXANDER RAMIREZ", "MACHIN MACHIN",
        "WILSON CASTRO", "VICTOR FUENMAYOR", "TITO DE FREITAS",
        "MICHELE COCCHIOLA", "YLIDIO DE ABREU", "ELIAS ALDANA",
        "RAMON MONCADA", "OMER FIGUEREDO", "GUSTAVO RIVERO",
        "VICTOR JURADO", "DOUGLAS GONZALEZ", "FRANCISCO DELGADO",
        "ALFREDO RAMOS", "VICTOR ESCALONA", "JOSE BARRERAS",
        "JESUS GUILLERMO", "CARLOS GARCIA", "DAVID UZCATEGUI",
        "ROMULO HERRERA", "ORLANDO CEBALLOS", "CARLOS OCARIZ",
        "WARNER JIMENEZ", "ALFREDO DIAZ", "LORENZO PIÑA",
        "FRANCISCO MORA", "ELIAS BITTAR", "MARIO FERRIGNO",
        "ROBERT ALCALA", "DANIEL CEBALLOS", "JOSE KARKOM",
        "FABIOLA COLMENAREZ", "JOSE LA CRUZ REYES", "ALENIS GUERRERO",
        "MERVIN MENDEZ", "SALVADOR SPINELLO", "EVELING DE ROSALES",
        "PEDRO EMILIO BRICEÑO", "JACINTO ROMERO",
    ]
}


def _load_weights() -> pd.DataFrame:
    pesos = pd.read_excel(PESOS)
    pesos["MUNICIPIO"] = pesos["MUNICIPIO"].ffill()
    return pesos.rename(columns={
        "CODIGOM": "municipio_id",
        "CODIGOC": "centro_id",
        "PESOC": "peso",
        "NOMBRE CENTRO": "centro_nombre",
    })


def _load_entrada() -> pd.DataFrame:
    entrada = pd.read_excel(CORE, sheet_name="Entrada", header=1)
    cols = ["CENTRO1", "MUNICIPIO1", "TURNO1", "CANDIDATO1", "VOTOS1"]
    entrada = entrada[cols].dropna()
    entrada.columns = ["centro_id", "municipio_id", "turno", "candidato", "votos"]
    for col in ["centro_id", "municipio_id", "turno", "candidato"]:
        entrada[col] = entrada[col].astype(int)
    entrada["votos"] = entrada["votos"].astype(float)
    return entrada[entrada["municipio_id"].isin(STUDIED_MUNICIPALITIES)]


def _study_totals(entrada: pd.DataFrame, pesos: pd.DataFrame) -> tuple[dict[int, dict], dict[tuple[int, int], dict]]:
    joined = entrada.merge(pesos[["municipio_id", "centro_id", "peso"]], on=["municipio_id", "centro_id"], how="left")
    joined = joined[joined["peso"].notna()]
    joined["bucket"] = joined["candidato"].map(
        lambda c: "gov" if c == GOV_CANDIDATE else "opos" if c == OPOS_CANDIDATE else "otros"
    )
    joined["weighted"] = joined["votos"] * joined["peso"]

    by_muni = {}
    by_turn = {}
    for municipio_id, g in joined.groupby("municipio_id"):
        final_turn = int(g["turno"].max())
        gf = g[g["turno"] <= final_turn]
        buckets = gf.groupby("bucket")["weighted"].sum().to_dict()
        total = sum(buckets.values())
        by_muni[municipio_id] = {
            "pct_gov": _pct(buckets.get("gov", 0), total),
            "pct_opos": _pct(buckets.get("opos", 0), total),
            "pct_otros": _pct(buckets.get("otros", 0), total),
            "n_respondentes": int(round(gf["votos"].sum())),
            "final_turn": final_turn,
        }
        for turno in sorted(g["turno"].unique()):
            gt = g[g["turno"] <= turno]
            buckets_t = gt.groupby("bucket")["weighted"].sum().to_dict()
            total_t = sum(buckets_t.values())
            by_turn[(municipio_id, int(turno))] = {
                "pct_gov": _pct(buckets_t.get("gov", 0), total_t),
                "pct_opos": _pct(buckets_t.get("opos", 0), total_t),
                "pct_otros": _pct(buckets_t.get("otros", 0), total_t),
                "num_centros": int(gt["centro_id"].nunique()),
            }
    return by_muni, by_turn


def _audit_summary(entrada: pd.DataFrame, pesos: pd.DataFrame) -> dict[int, dict]:
    known_centers = pesos.groupby("municipio_id")["centro_id"].apply(set).to_dict()
    out = {}
    for municipio_id, centers in known_centers.items():
        g = entrada[entrada["municipio_id"] == municipio_id]
        transmitted = set(g[g["turno"] > 0]["centro_id"].unique())
        totals_by_center_turn = g.groupby(["centro_id", "turno"])["votos"].sum()
        total_values = [float(v) for v in totals_by_center_turn.values if v > 0]
        suspicious = sum(1 for v in total_values if v >= 850)
        out[municipio_id] = {
            "centros_esperados": len(centers),
            "centros_transmiten": len(transmitted & centers),
            "centros_no_transmiten": len(centers - transmitted),
            "cortes_con_total_atipico": suspicious,
            "criterio": (
                "El semaforo operativo compara, por centro y turno, el total "
                "recibido contra el comportamiento esperado del centro. Un "
                "centro sin filas transmitidas queda como no transmite; totales "
                "desproporcionados o inconsistentes se revisan como informacion "
                "errada; el resto entra como informacion correcta para la "
                "publicacion agregada."
            ),
        }
    return out


def build_seed_rows(fetch_official: bool = True) -> dict[str, list[dict]]:
    pesos = _load_weights()
    entrada = _load_entrada()
    study, turnos = _study_totals(entrada, pesos)
    audit = _audit_summary(entrada, pesos)

    oficiales = {}
    if fetch_official:
        for municipio_id, (_, _, _, cne_code) in STUDIED_MUNICIPALITIES.items():
            slug, estado, municipio, _ = STUDIED_MUNICIPALITIES[municipio_id]
            print(f"[official] {municipio_id:02d}/52 {estado} - {municipio} ({cne_code})")
            try:
                oficiales[municipio_id] = _official_for_code(cne_code)
                print(f"[official] OK {slug}: {oficiales[municipio_id].total_votos} votos")
            except Exception as exc:
                if municipio_id in MANUAL_OFFICIAL_RESULTS:
                    oficiales[municipio_id] = MANUAL_OFFICIAL_RESULTS[municipio_id]
                    print(f"[official] MANUAL {slug}: {oficiales[municipio_id].total_votos} votos")
                else:
                    print(f"WARN: sin oficial para {slug}: {exc}")

    total_centros = int(pesos["centro_id"].nunique())
    total_resp = sum(v["n_respondentes"] for v in study.values())
    nacional_counts = Counter()
    for value in study.values():
        nacional_counts["gov"] += value["pct_gov"]
        nacional_counts["opos"] += value["pct_opos"]
        nacional_counts["otros"] += value["pct_otros"]
    n_muni = len(study) or 1

    notas_nacional = {
        "tipo": "coleccion_municipales",
        "n_estudios": len(study),
        "n_centros_total": total_centros,
        "n_respondentes_total": int(total_resp),
        "fuente_oficial": "CNE 2013 via archive.org",
        "layout": "auditoria4.xlsx Entrada + PESO CENTROS DIC 2013.xlsx",
        "semaforo": (
            "auditoria4.xlsx/Pantalla1-4 consolida los votos por centro y turno. "
            "Se usa para separar centros que transmiten informacion correcta, "
            "centros con informacion errada o atipica y centros sin transmision."
        ),
    }

    rows_e = [{
        "eleccion_ref": REF,
        "ambito": "NACIONAL",
        "nombre": "Nacional",
        "nombre_eleccion": NOMBRE,
        "fecha_eleccion": FECHA,
        "pct_gov": round(nacional_counts["gov"] / n_muni, 2),
        "pct_opos": round(nacional_counts["opos"] / n_muni, 2),
        "pct_otros": round(nacional_counts["otros"] / n_muni, 2),
        "num_centros": total_centros,
        "fuente": "auditoria4.xlsx + PESO CENTROS DIC 2013.xlsx",
        "notas": json.dumps(notas_nacional, ensure_ascii=False),
    }]
    rows_o = []
    rows_t = []

    if oficiales:
        gov = sum(o.pct_gov for o in oficiales.values()) / len(oficiales)
        opos = sum(o.pct_opos for o in oficiales.values()) / len(oficiales)
        otros = sum(o.pct_otros for o in oficiales.values()) / len(oficiales)
        rows_o.append({
            "eleccion_ref": REF,
            "ambito": "NACIONAL",
            "nombre": "Nacional",
            "nombre_eleccion": NOMBRE,
            "fecha_eleccion": FECHA,
            "pct_gov": round(gov, 2),
            "pct_opos": round(opos, 2),
            "pct_otros": round(otros, 2),
            "total_votos": sum(o.total_votos for o in oficiales.values()),
            "fuente": "CNE 2013 via archive.org",
        })

    for municipio_id, values in sorted(study.items()):
        slug, estado, municipio, cne_code = STUDIED_MUNICIPALITIES[municipio_id]
        num_centros = int(pesos[pesos["municipio_id"] == municipio_id]["centro_id"].nunique())
        notes = {
            "tipo": "municipal",
            "tipo_cargo": "Alcaldia",
            "estado": estado,
            "municipio": municipio,
            "codigo_municipio_local": municipio_id,
            "codigo_cne": cne_code,
            "candidato_gov": "candidato 1",
            "candidato_opos": "candidato 2",
            "n_respondentes": values["n_respondentes"],
            "final_turn": values["final_turn"],
            "auditoria": audit.get(municipio_id, {}),
        }
        if municipio_id in oficiales:
            notes.update({
                "cand_gov_nombre": oficiales[municipio_id].gov_name,
                "cand_opos_nombre": oficiales[municipio_id].opos_name,
                "fuente_oficial_url": oficiales[municipio_id].source_url,
            })
        rows_e.append({
            "eleccion_ref": REF,
            "ambito": slug,
            "nombre": f"{municipio}, {estado}",
            "nombre_eleccion": NOMBRE,
            "fecha_eleccion": FECHA,
            "pct_gov": values["pct_gov"],
            "pct_opos": values["pct_opos"],
            "pct_otros": values["pct_otros"],
            "num_centros": num_centros,
            "fuente": "auditoria4.xlsx + PESO CENTROS DIC 2013.xlsx",
            "notas": json.dumps(notes, ensure_ascii=False),
        })
        official = oficiales.get(municipio_id)
        if official:
            rows_o.append({
                "eleccion_ref": REF,
                "ambito": slug,
                "nombre": f"{municipio}, {estado}",
                "nombre_eleccion": NOMBRE,
                "fecha_eleccion": FECHA,
                "pct_gov": official.pct_gov,
                "pct_opos": official.pct_opos,
                "pct_otros": official.pct_otros,
                "total_votos": official.total_votos,
                "fuente": "CNE 2013 via archive.org",
            })
        for (mid, turno), tv in sorted(turnos.items()):
            if mid != municipio_id:
                continue
            rows_t.append({
                "eleccion_ref": REF,
                "ambito": slug,
                "turno": turno,
                "hora_label": TURN_LABELS.get(turno, f"Corte {turno}"),
                "pct_gov": tv["pct_gov"],
                "pct_opos": tv["pct_opos"],
                "pct_otros": tv["pct_otros"],
                "num_centros": tv["num_centros"],
            })

    return {
        "historico_estudios": rows_e,
        "historico_oficial": rows_o,
        "historico_estudios_turnos": rows_t,
    }


def seed_2013_municipales(
    conn: sqlite3.Connection,
    fetch_official: bool = True,
    data: dict[str, list[dict]] | None = None,
) -> dict[str, int]:
    if data is None:
        data = build_seed_rows(fetch_official=fetch_official)
    counts = {key: 0 for key in data}
    for row in data["historico_estudios"]:
        conn.execute("""
            INSERT INTO historico_estudios
                (eleccion_ref, ambito, nombre, nombre_eleccion, fecha_eleccion,
                 pct_gov, pct_opos, pct_otros, num_centros, fuente, notas)
            VALUES (:eleccion_ref, :ambito, :nombre, :nombre_eleccion, :fecha_eleccion,
                    :pct_gov, :pct_opos, :pct_otros, :num_centros, :fuente, :notas)
            ON CONFLICT(eleccion_ref, ambito) DO UPDATE SET
                nombre=excluded.nombre,
                nombre_eleccion=excluded.nombre_eleccion,
                fecha_eleccion=excluded.fecha_eleccion,
                pct_gov=excluded.pct_gov,
                pct_opos=excluded.pct_opos,
                pct_otros=excluded.pct_otros,
                num_centros=excluded.num_centros,
                fuente=excluded.fuente,
                notas=excluded.notas,
                updated_at=datetime('now')
        """, row)
        counts["historico_estudios"] += 1
    for row in data["historico_oficial"]:
        conn.execute("""
            INSERT INTO historico_oficial
                (eleccion_ref, ambito, nombre, nombre_eleccion, fecha_eleccion,
                 pct_gov, pct_opos, pct_otros, total_votos, fuente)
            VALUES (:eleccion_ref, :ambito, :nombre, :nombre_eleccion, :fecha_eleccion,
                    :pct_gov, :pct_opos, :pct_otros, :total_votos, :fuente)
            ON CONFLICT(eleccion_ref, ambito) DO UPDATE SET
                nombre=excluded.nombre,
                nombre_eleccion=excluded.nombre_eleccion,
                fecha_eleccion=excluded.fecha_eleccion,
                pct_gov=excluded.pct_gov,
                pct_opos=excluded.pct_opos,
                pct_otros=excluded.pct_otros,
                total_votos=excluded.total_votos,
                fuente=excluded.fuente,
                updated_at=datetime('now')
        """, row)
        counts["historico_oficial"] += 1
    for row in data["historico_estudios_turnos"]:
        conn.execute("""
            INSERT INTO historico_estudios_turnos
                (eleccion_ref, ambito, turno, hora_label, pct_gov, pct_opos, pct_otros, num_centros)
            VALUES (:eleccion_ref, :ambito, :turno, :hora_label,
                    :pct_gov, :pct_opos, :pct_otros, :num_centros)
            ON CONFLICT(eleccion_ref, ambito, turno) DO UPDATE SET
                hora_label=excluded.hora_label,
                pct_gov=excluded.pct_gov,
                pct_opos=excluded.pct_opos,
                pct_otros=excluded.pct_otros,
                num_centros=excluded.num_centros,
                updated_at=datetime('now')
        """, row)
        counts["historico_estudios_turnos"] += 1
    return counts


def _merge_into_seed(data: dict[str, list[dict]]) -> None:
    seed_path = BASE_DIR / "data" / "historico_estudios_seed.json"
    current = json.loads(seed_path.read_text(encoding="utf-8"))
    for section, rows in data.items():
        kept = [r for r in current.get(section, []) if r.get("eleccion_ref") != REF]
        current[section] = kept + rows
    seed_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-official", action="store_true", help="No consulta archive.org/CNE")
    parser.add_argument("--write-seed", action="store_true", help="Actualiza data/historico_estudios_seed.json")
    parser.add_argument("--discover-codes", action="store_true", help="Lista códigos CNE encontrados en archive.org")
    parser.add_argument("--delay-seconds", type=float, default=1.5, help="Pausa entre solicitudes a archive.org")
    parser.add_argument("--retries", type=int, default=3, help="Reintentos por URL de archive.org")
    parser.add_argument("--db", default=str(DB))
    args = parser.parse_args()

    global FETCH_DELAY_SECONDS, FETCH_RETRIES
    FETCH_DELAY_SECONDS = max(0.0, args.delay_seconds)
    FETCH_RETRIES = max(1, args.retries)

    if args.discover_codes:
        found = discover_cne_codes()
        for key, value in sorted(found.items()):
            print(f"{key} -> {value[0]} {value[1]}")
        return

    data = build_seed_rows(fetch_official=not args.no_official)
    if args.write_seed:
        _merge_into_seed(data)
        print(f"Seed actualizado con {REF}")

    conn = sqlite3.connect(args.db)
    try:
        counts = seed_2013_municipales(conn, fetch_official=not args.no_official, data=data)
        conn.commit()
        print("2013 municipales:", counts)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
