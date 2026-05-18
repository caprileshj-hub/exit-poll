"""Import 2006 presidential election data into historico tables."""
import xlrd
import openpyxl
import sqlite3
from collections import defaultdict

DB       = 'exitpoll.db'
REF      = '2006-presidencial'
NOMBRE   = 'Presidencial 2006'
FECHA    = '2006-12-03'
CORE_XLS = 'data/2006/Presentacion Basica Copia5.xls'
OFF_XLSX = 'data/2006/resultado elecciones presidenciales 2006.xlsx'


def fv(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def r2(x):
    return round(x, 2)


# ── DB connection ────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

estados = {
    int(r['codigo_cne']): {'cod': r['codigo_cne'], 'nombre': r['nombre']}
    for r in conn.execute("SELECT codigo_cne, nombre FROM estados").fetchall()
}

# ── 1. Core: aggregate Entrada sheet by state ────────────────────────────────
wb_core = xlrd.open_workbook(CORE_XLS, encoding_override='latin-1')
sh_ent  = wb_core.sheet_by_name('Entrada')

by_state = defaultdict(lambda: {'c': 0., 'r': 0., 'o': 0., 'n': 0., 'ctrs': set()})
by_turno_ctrs = defaultdict(set)

for row_i in range(2, sh_ent.nrows):
    row = [sh_ent.cell_value(row_i, c) for c in range(sh_ent.ncols)]
    if not row[1]:
        continue
    ent = int(fv(row[1]))
    t   = int(fv(row[0]))
    mc = fv(row[5]); mr = fv(row[6]); mo = fv(row[7]); mn = fv(row[8])
    by_state[ent]['c'] += mc
    by_state[ent]['r'] += mr
    by_state[ent]['o'] += mo
    by_state[ent]['n'] += mn
    ctr_key = (ent, int(fv(row[2])), int(fv(row[3])), int(fv(row[4])))
    by_state[ent]['ctrs'].add(ctr_key)
    by_turno_ctrs[t].add(ctr_key)

# National study totals
nat_c = sum(s['c'] for s in by_state.values())
nat_r = sum(s['r'] for s in by_state.values())
nat_o = sum(s['o'] for s in by_state.values())
nat_n = sum(s['n'] for s in by_state.values())
nat_ctrs = sum(len(s['ctrs']) for s in by_state.values())
nat_tot  = nat_c + nat_r + nat_o + nat_n

# ── 2. Core: turn-by-turn from Cálculos sheet ────────────────────────────────
sh_cal = wb_core.sheet_by_index(0)   # 'Cálculos'

# Cumulative center count per turn
seen_ctrs = set()
cum_ctrs  = {}
for t in range(1, 13):
    seen_ctrs |= by_turno_ctrs.get(t, set())
    cum_ctrs[t] = len(seen_ctrs)

# rows 2-13 = turnos 1-12
# cols: 1=turno, 3=chavez_acum, 6=rosales_acum, 9=otros_acum, 12=nulos_acum
turnos_data = []
for row_i in range(2, 14):
    row  = [sh_cal.cell_value(row_i, c) for c in range(sh_cal.ncols)]
    trno = int(fv(row[1]))
    ca = fv(row[3]); ra = fv(row[6]); oa = fv(row[9]); na = fv(row[12])
    tot_t = ca + ra + oa + na
    if tot_t == 0:
        continue
    turnos_data.append({
        'turno':      trno,
        'pct_gov':    r2(ca / tot_t * 100),
        'pct_opos':   r2(ra / tot_t * 100),
        'pct_otros':  r2((oa + na) / tot_t * 100),
        'num_centros': cum_ctrs.get(trno, 0),
    })

# ── 3. Official results: aggregate by state ───────────────────────────────────
wb_off = openpyxl.load_workbook(OFF_XLSX, read_only=True, data_only=True)
ws_off = wb_off.active

by_off  = defaultdict(lambda: {'c': 0, 'r': 0, 'v': 0, 'e': 0, 'n': 0, 'nom': ''})
nat_off = {'c': 0, 'r': 0, 'v': 0, 'e': 0, 'n': 0}

for row in ws_off.iter_rows(min_row=2, values_only=True):
    if not row[0]:
        continue
    cod = int(row[0])
    if cod == 99:
        continue  # skip exterior
    c = int(row[11] or 0); r = int(row[10] or 0)
    v = int(row[15] or 0); e = int(row[14] or 0); n = int(row[16] or 0)
    by_off[cod]['c'] += c;  by_off[cod]['r'] += r
    by_off[cod]['v'] += v;  by_off[cod]['e'] += e;  by_off[cod]['n'] += n
    by_off[cod]['nom'] = row[1]
    nat_off['c'] += c;  nat_off['r'] += r
    nat_off['v'] += v;  nat_off['e'] += e;  nat_off['n'] += n


# ── 4. Upsert helpers ─────────────────────────────────────────────────────────
def upsert_estudio(ambito, nombre, pct_gov, pct_opos, pct_otros, num_centros=0):
    conn.execute("""
        INSERT INTO historico_estudios
            (eleccion_ref, ambito, nombre, nombre_eleccion, fecha_eleccion,
             pct_gov, pct_opos, pct_otros, num_centros)
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(eleccion_ref, ambito) DO UPDATE SET
            nombre=excluded.nombre,
            nombre_eleccion=excluded.nombre_eleccion,
            fecha_eleccion=excluded.fecha_eleccion,
            pct_gov=excluded.pct_gov, pct_opos=excluded.pct_opos,
            pct_otros=excluded.pct_otros, num_centros=excluded.num_centros,
            updated_at=datetime('now')
    """, (REF, ambito, nombre, NOMBRE, FECHA, pct_gov, pct_opos, pct_otros, num_centros))


def upsert_oficial(ambito, nombre, pct_gov, pct_opos, pct_otros, total_votos=0):
    conn.execute("""
        INSERT INTO historico_oficial
            (eleccion_ref, ambito, nombre, nombre_eleccion, fecha_eleccion,
             pct_gov, pct_opos, pct_otros, total_votos)
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(eleccion_ref, ambito) DO UPDATE SET
            nombre=excluded.nombre,
            nombre_eleccion=excluded.nombre_eleccion,
            fecha_eleccion=excluded.fecha_eleccion,
            pct_gov=excluded.pct_gov, pct_opos=excluded.pct_opos,
            pct_otros=excluded.pct_otros, total_votos=excluded.total_votos,
            updated_at=datetime('now')
    """, (REF, ambito, nombre, NOMBRE, FECHA, pct_gov, pct_opos, pct_otros, total_votos))


def upsert_turno(turno, pct_gov, pct_opos, pct_otros, num_centros=0):
    conn.execute("""
        INSERT INTO historico_estudios_turnos
            (eleccion_ref, turno, pct_gov, pct_opos, pct_otros, num_centros)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(eleccion_ref, turno) DO UPDATE SET
            pct_gov=excluded.pct_gov, pct_opos=excluded.pct_opos,
            pct_otros=excluded.pct_otros, num_centros=excluded.num_centros,
            updated_at=datetime('now')
    """, (REF, turno, pct_gov, pct_opos, pct_otros, num_centros))


# ── 5. Insert study data ──────────────────────────────────────────────────────
upsert_estudio('NACIONAL', 'Nacional',
               r2(nat_c / nat_tot * 100),
               r2(nat_r / nat_tot * 100),
               r2((nat_o + nat_n) / nat_tot * 100),
               nat_ctrs)

for ent, s in by_state.items():
    if ent not in estados:
        continue
    tot_s = s['c'] + s['r'] + s['o'] + s['n']
    if tot_s == 0:
        continue
    upsert_estudio(
        estados[ent]['cod'],
        estados[ent]['nombre'],
        r2(s['c'] / tot_s * 100),
        r2(s['r'] / tot_s * 100),
        r2((s['o'] + s['n']) / tot_s * 100),
        len(s['ctrs']),
    )

# ── 6. Insert turnos ──────────────────────────────────────────────────────────
for td in turnos_data:
    upsert_turno(td['turno'], td['pct_gov'], td['pct_opos'], td['pct_otros'], td['num_centros'])

# ── 7. Insert official results ────────────────────────────────────────────────
d  = nat_off['e']
ot = nat_off['v'] - nat_off['c'] - nat_off['r']
upsert_oficial('NACIONAL', 'Nacional',
               r2(nat_off['c'] / d * 100),
               r2(nat_off['r'] / d * 100),
               r2((ot + nat_off['n']) / d * 100),
               d)

for ent, s in by_off.items():
    if ent not in estados:
        continue
    d  = s['e']
    ot = s['v'] - s['c'] - s['r']
    if d == 0:
        continue
    upsert_oficial(
        estados[ent]['cod'],
        estados[ent]['nombre'],
        r2(s['c'] / d * 100),
        r2(s['r'] / d * 100),
        r2((ot + s['n']) / d * 100),
        d,
    )

conn.commit()

# ── 8. Verify ─────────────────────────────────────────────────────────────────
ne  = conn.execute("SELECT COUNT(*) FROM historico_estudios WHERE eleccion_ref=?", (REF,)).fetchone()[0]
no  = conn.execute("SELECT COUNT(*) FROM historico_oficial WHERE eleccion_ref=?", (REF,)).fetchone()[0]
nt  = conn.execute("SELECT COUNT(*) FROM historico_estudios_turnos WHERE eleccion_ref=?", (REF,)).fetchone()[0]
nac_e = dict(conn.execute("SELECT * FROM historico_estudios WHERE eleccion_ref=? AND ambito='NACIONAL'", (REF,)).fetchone())
nac_o = dict(conn.execute("SELECT * FROM historico_oficial  WHERE eleccion_ref=? AND ambito='NACIONAL'", (REF,)).fetchone())

print(f"historico_estudios  : {ne} filas")
print(f"historico_oficial   : {no} filas")
print(f"historico_turnos    : {nt} filas")
print()
print(f"Estudio nacional : Chavez {nac_e['pct_gov']}%  Rosales {nac_e['pct_opos']}%  Otros {nac_e['pct_otros']}%  ({nac_e['num_centros']} centros)")
print(f"Oficial nacional : Chavez {nac_o['pct_gov']}%  Rosales {nac_o['pct_opos']}%  Otros {nac_o['pct_otros']}%  ({nac_o['total_votos']:,} votos)")
print()
print("Turnos:")
for row in conn.execute("SELECT turno, pct_gov, pct_opos, num_centros FROM historico_estudios_turnos WHERE eleccion_ref=? ORDER BY turno", (REF,)).fetchall():
    print(f"  T{row[0]:2d}: Chavez {row[1]}%  Rosales {row[2]}%  ({row[3]} centros)")

conn.close()
print("\nImportación completada.")
