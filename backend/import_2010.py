"""Import 2010 Asamblea Nacional study into historico tables.

The source workbook has study outputs for nominal, list, and indigenous seats.
There is no local official tabulation file, so the official national reference
uses the published aggregate from Wikipedia/CNE summary.
"""

import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl


BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "exitpoll.db"
XLSM = BASE_DIR / "data" / "2010" / "aplicacion03.xlsm"
REF = "2010-asamblea"
NOMBRE = "Asamblea Nacional 2010"
FECHA = "2010-09-26"
TOTAL_ESCANOS = 165

NAME_TO_CODE = {
    "AMAZONAS": "22",
    "ANZOATEGUI": "02",
    "ANZOÁTEGUI": "02",
    "APURE": "03",
    "ARAGUA": "04",
    "BARINAS": "05",
    "BOLIVAR": "06",
    "BOLÍVAR": "06",
    "CARABOBO": "07",
    "COJEDES": "08",
    "DELTA AMACURO": "23",
    "DISTRITO CAPITAL": "01",
    "FALCON": "09",
    "FALCÓN": "09",
    "GUARICO": "10",
    "GUÁRICO": "10",
    "LARA": "11",
    "MERIDA": "12",
    "MÉRIDA": "12",
    "MIRANDA": "13",
    "MONAGAS": "14",
    "NUEVA ESPARTA": "15",
    "PORTUGUESA": "16",
    "SUCRE": "17",
    "TACHIRA": "18",
    "TÁCHIRA": "18",
    "TRUJILLO": "19",
    "VARGAS": "24",
    "YARACUY": "20",
    "ZULIA": "21",
}


def _bando(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if "gobierno" in text:
        return "gov"
    if "opos" in text:
        return "opos"
    if "otro" in text:
        return "otros"
    return None


def _pct(part: int, total: int) -> float:
    return round(part * 100.0 / total, 2) if total else 0.0


def _count_unique_centers(wb) -> int:
    centers = set()
    for row in wb["ENTRADA"].iter_rows(min_row=2, values_only=True):
        if row[1]:
            centers.add(row[1])
    return len(centers)


def _seat_counts(wb) -> tuple[Counter, dict[str, Counter]]:
    total = Counter()
    by_state: dict[str, Counter] = defaultdict(Counter)

    def add(sheet: str, bando_cols: list[int]) -> None:
        current_state = None
        for row in wb[sheet].iter_rows(min_row=5, values_only=True):
            if row[1]:
                current_state = str(row[1]).strip().upper()
            for idx in bando_cols:
                value = row[idx] if idx < len(row) else None
                bando = _bando(value)
                if not bando:
                    continue
                total[bando] += 1
                if current_state:
                    by_state[current_state][bando] += 1

    add("R Nominal", [6])
    add("R Lista", [4, 6, 8])
    add("R Indigena", [6])
    return total, by_state


def _study_list_vote_pct(wb) -> dict[str, float]:
    counts = Counter()
    current_state = None
    for row in wb["LISTA"].iter_rows(values_only=True):
        label = row[2]
        total = row[4]
        if isinstance(label, str) and label.startswith("LISTA "):
            current_state = label.replace("LISTA ", "").strip()
            continue
        if not current_state or not isinstance(label, str) or not isinstance(total, (int, float)):
            continue
        bando = _bando(label) or "otros"
        counts[bando] += float(total)
    total_votes = sum(counts.values())
    return {key: round(value * 100.0 / total_votes, 2) for key, value in counts.items()}


def seed_2010(conn: sqlite3.Connection) -> dict[str, int]:
    wb = openpyxl.load_workbook(XLSM, read_only=True, data_only=True, keep_vba=False)
    conn.row_factory = sqlite3.Row
    estados = {r["codigo_cne"]: r["nombre"] for r in conn.execute("SELECT codigo_cne, nombre FROM estados")}

    study_seats, state_seats = _seat_counts(wb)
    unique_centers = _count_unique_centers(wb)
    list_vote_pct = _study_list_vote_pct(wb)

    official_seats = {"gov": 98, "opos": 65, "otros": 2}
    official_votes = {"gov": 5423324, "opos": 5320364, "otros": 353979}
    official_vote_pct = {"gov": 48.13, "opos": 47.22, "otros": 3.14}
    voters = 11097667

    notes = {
        "tipo": "asamblea",
        "metrica": "escanos",
        "sin_tendencia": True,
        "estudio_escanos": dict(study_seats),
        "estudio_total_escanos": sum(study_seats.values()),
        "estudio_voto_lista_pct": list_vote_pct,
        "oficial_escanos": official_seats,
        "oficial_total_escanos": TOTAL_ESCANOS,
        "oficial_votos": official_votes,
        "oficial_voto_pct": official_vote_pct,
        "oficial_fuente": "Wikipedia/CNE agregado nacional",
        "nota": "Eleccion parlamentaria con votos nominales, lista e indigenas; sin tabulado oficial local por estado.",
    }

    conn.execute("""
        INSERT INTO historico_estudios
            (eleccion_ref, ambito, nombre, nombre_eleccion, fecha_eleccion,
             pct_gov, pct_opos, pct_otros, num_centros, fuente, notas)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
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
    """, (
        REF, "NACIONAL", "Nacional", NOMBRE, FECHA,
        _pct(study_seats["gov"], TOTAL_ESCANOS),
        _pct(study_seats["opos"], TOTAL_ESCANOS),
        _pct(study_seats["otros"], TOTAL_ESCANOS),
        unique_centers,
        "aplicacion03.xlsm",
        json.dumps(notes, ensure_ascii=False),
    ))

    conn.execute("""
        INSERT INTO historico_oficial
            (eleccion_ref, ambito, nombre, nombre_eleccion, fecha_eleccion,
             pct_gov, pct_opos, pct_otros, total_votos, fuente)
        VALUES (?,?,?,?,?,?,?,?,?,?)
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
    """, (
        REF, "NACIONAL", "Nacional", NOMBRE, FECHA,
        _pct(official_seats["gov"], TOTAL_ESCANOS),
        _pct(official_seats["opos"], TOTAL_ESCANOS),
        _pct(official_seats["otros"], TOTAL_ESCANOS),
        voters,
        "Wikipedia/CNE agregado nacional",
    ))

    state_rows = 0
    for state_name, counts in state_seats.items():
        code = NAME_TO_CODE.get(state_name)
        if not code or code not in estados:
            continue
        total_state = sum(counts.values())
        conn.execute("""
            INSERT INTO historico_estudios
                (eleccion_ref, ambito, nombre, nombre_eleccion, fecha_eleccion,
                 pct_gov, pct_opos, pct_otros, num_centros, fuente, notas)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
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
        """, (
            REF, code, estados[code], NOMBRE, FECHA,
            _pct(counts["gov"], total_state),
            _pct(counts["opos"], total_state),
            _pct(counts["otros"], total_state),
            total_state,
            "aplicacion03.xlsm",
            json.dumps({"tipo": "asamblea", "metrica": "escanos", "estudio_escanos": dict(counts)}, ensure_ascii=False),
        ))
        state_rows += 1

    conn.commit()
    return {
        "estudio_filas": state_rows + 1,
        "oficial_filas": 1,
        "estudio_escanos_gov": study_seats["gov"],
        "estudio_escanos_opos": study_seats["opos"],
        "estudio_escanos_otros": study_seats["otros"],
    }


def main() -> None:
    conn = sqlite3.connect(DB)
    try:
        stats = seed_2010(conn)
    finally:
        conn.close()
    print("2010-asamblea:", stats)


if __name__ == "__main__":
    main()
