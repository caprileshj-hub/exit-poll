import json
from collections import defaultdict

archivo = "geoBoundaries-VEN-ADM2_simplified.geojson"

with open(archivo, "r", encoding="utf-8") as f:
    data = json.load(f)

estados = defaultdict(list)

for feature in data["features"]:
    props = feature["properties"]

    # Detectar claves posibles
    claves_estado = ["shapeGroup", "NAME_1", "ADM1_ES"]
    claves_municipio = ["shapeName", "NAME_2", "ADM2_ES"]

    estado = None
    municipio = None

    for c in claves_estado:
        if c in props:
            estado = props[c].strip().upper()
            break

    for c in claves_municipio:
        if c in props:
            municipio = props[c].strip().upper()
            break

    if estado and municipio:
        estados[estado].append(municipio)

# Ordenar municipios dentro de cada estado
for e in estados:
    estados[e] = sorted(list(set(estados[e])))

# Guardar resultado
with open("estados_municipios.json", "w", encoding="utf-8") as f:
    json.dump(estados, f, indent=4, ensure_ascii=False)

print("Listo. Se generó estados_municipios.json con la estructura completa.")
