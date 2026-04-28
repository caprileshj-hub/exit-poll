import json

# Ruta del archivo GeoJSON
archivo = "geoBoundaries-VEN-ADM2_simplified.geojson"

with open(archivo, "r", encoding="utf-8") as f:
    data = json.load(f)

municipios = set()

for feature in data["features"]:
    props = feature["properties"]

    # Detectamos automáticamente el campo correcto
    posibles_claves = [
        "shapeName", "NAME_2", "ADM2_ES", "municipio",
        "NAME_1", "NAME_0", "shapeGroup", "shapeID"
    ]

    nombre = None
    for clave in posibles_claves:
        if clave in props:
            nombre = props[clave]
            break

    if nombre:
        municipios.add(nombre.strip().upper())

# Ordenar alfabéticamente
municipios = sorted(list(municipios))

# Guardar en archivo
with open("municipios_mapa.txt", "w", encoding="utf-8") as f:
    for m in municipios:
        f.write(m + "\n")

print("Listo. Se generó municipios_mapa.txt con", len(municipios), "municipios.")
