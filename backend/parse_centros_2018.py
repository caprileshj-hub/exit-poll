"""Parsea el Directorio de Centros de Votacion Elecciones 2018 (CNE) a CSV.

Fuente: centros_votacion_elecciones2018.pdf (Junta Nacional Electoral, ONIE),
recuperado via Wayback Machine.
"""
import csv
import re

HEADERS = [
    "COD ESTADO COD MUNICIPIO COD PARROQUIA CODIGO NOMBRE DIRECCION CANTIDAD",
    "MESAS ELECTORES",
    "OFICINA NACIONAL DE INFRAESTRUCTURA ELECTORAL",
    "JUNTA NACIONAL ELECTORAL",
    "ELECCIONES 2018",
    "DIRECTORIO DE CENTROS DE VOTACIÓN",
    "DIRECCIÓN DE CATASTRO Y GESTIÓN DE CENTROS DE VOTACIÓN",
]

DIR_TOKENS = (
    "SECTOR", "URBANIZACIÓN", "URBANIZACION", "BARRIO", "CASERÍO", "CASERIO",
    "AVENIDA", "CALLE", "CARRETERA", "ZONA", "VÍA", "VIA", "PARCELAMIENTO",
    "CONJUNTO", "COMUNIDAD", "SITIO", "PUEBLO", "CIUDAD", "SABANA", "MUNICIPIO",
    "PARROQUIA", "SECTORES", "ASENTAMIENTO", "SEC.", "URB.", "BO.",
)

# inicio de registro: <cod> <ENTIDAD> donde ENTIDAD empieza por DTTO./EDO./EMBAJADA/CONSULADO
START = re.compile(r"(?=\b\d{1,2}\s+(?:DTTO\.|EDO\.|EMBAJADA|CONSULADO))")
# cabecera territorial venezolana: <est> NOMBRE <mun> MP. X <par> PQ./CM. Y
TERR = re.compile(
    r"^\d{1,2}\s+(.+?)\s+\d{1,3}\s+(MP\..+?)\s+\d{1,3}\s+((?:PQ|CM)\..+)$"
)
TAIL = re.compile(r"^(.*?)\s+(\d{1,3})\s+(\d{1,3}(?:\.\d{3})*)$", re.S)


def limpiar(pagina: str) -> str:
    lineas = []
    for ln in pagina.split("\n"):
        s = ln.strip()
        if not s or s in HEADERS:
            continue
        if s.startswith("Fuente: Dirección General"):
            continue
        lineas.append(s)
    return " ".join(lineas)


def partir_nombre_direccion(texto: str):
    """Separa NOMBRE de DIRECCION por el primer token tipico de direccion."""
    pos = len(texto)
    for tok in DIR_TOKENS:
        i = texto.find(" " + tok + " ")
        if i != -1 and i < pos:
            pos = i
    if pos == len(texto):
        return texto.strip(), ""
    return texto[:pos].strip(), texto[pos:].strip()


def parsear(ruta_txt: str):
    texto = open(ruta_txt, encoding="utf-8").read()
    plano = " ".join(limpiar(p) for p in texto.split("\x0c"))
    plano = re.sub(r"\s+", " ", plano)

    registros, fallidos = [], []
    for bloque in START.split(plano):
        bloque = bloque.strip()
        if not bloque:
            continue
        m = re.match(r"^(\d{1,2})\s+(.+?)\s+(\d{8,9})\s+(.+)$", bloque)
        if not m:
            fallidos.append(bloque[:120])
            continue
        cabecera_full, codigo, resto = m.group(0), m.group(3), m.group(4)
        cab = cabecera_full[: cabecera_full.index(codigo)].strip()

        t = TERR.match(cab)
        if t:
            estado, municipio, parroquia = (x.strip() for x in t.groups())
        else:  # embajadas/consulados: <n> EMBAJADA <n> PAIS <n> CIUDAD
            e = re.match(r"^\d{1,2}\s+(.+?)\s+\d{1,3}\s+(.+?)\s+\d{1,3}\s+(.+)$", cab)
            if not e:
                fallidos.append(bloque[:120])
                continue
            estado, municipio, parroquia = (x.strip() for x in e.groups())

        tl = TAIL.match(resto)
        if not tl:
            fallidos.append(bloque[:120])
            continue
        cuerpo, mesas, electores = tl.groups()
        nombre, direccion = partir_nombre_direccion(cuerpo)

        c9 = codigo.zfill(9)
        registros.append(
            {
                "codigo_centro": codigo,
                "cod_estado": int(c9[0:2]),
                "cod_municipio": int(c9[2:4]),
                "cod_parroquia": int(c9[4:6]),
                "estado": estado,
                "municipio": municipio,
                "parroquia": parroquia,
                "nombre_centro": nombre,
                "direccion": direccion,
                "mesas": int(mesas),
                "electores": int(electores.replace(".", "")),
            }
        )
    return registros, fallidos


if __name__ == "__main__":
    regs, fallidos = parsear("centros_2018.txt")
    with open("centros_votacion_2018.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(regs[0].keys()))
        w.writeheader()
        w.writerows(regs)

    tot_e = sum(r["electores"] for r in regs)
    tot_m = sum(r["mesas"] for r in regs)
    nac = [r for r in regs if r["cod_estado"] != 99]
    ext = [r for r in regs if r["cod_estado"] == 99]
    print(f"centros           : {len(regs):,}  (nacional {len(nac):,} / exterior {len(ext):,})")
    print(f"mesas             : {tot_m:,}   | oficial CNE 34.143")
    print(f"electores         : {tot_e:,}  | oficial CNE 20.526.978")
    print(f"delta electores   : {20_526_978 - tot_e:,}")
    print(f"delta mesas       : {34_143 - tot_m:,}")
    print(f"entidades         : {len(set(r['estado'] for r in nac))}")
    print(f"bloques fallidos  : {len(fallidos)}")
    for f in fallidos[:5]:
        print("   !", f)
