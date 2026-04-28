import json

with open("geoBoundaries-VEN-ADM2.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

print(data["features"][0]["properties"])
