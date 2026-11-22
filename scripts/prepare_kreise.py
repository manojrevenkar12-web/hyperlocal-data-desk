"""One-off: cut the 44 Baden-Württemberg districts out of the Germany district file and give them their official keys.

Source: isellsoap/deutschlandGeoJSON (4_kreise/3_mittel), derived from GADM via DIVA-GIS. Run once; the output
geo/bw_kreise.geojson is committed with attribution in geo/README.md.
"""
import json
import sys

from shapely.geometry import mapping, shape

# GADM name -> (official district key, official name, is a city district)
KREISE = {
    "Stuttgart Städte": ("08111", "Stuttgart", True), "Böblingen": ("08115", "Böblingen", False),
    "Esslingen": ("08116", "Esslingen", False), "Göppingen": ("08117", "Göppingen", False),
    "Ludwigsburg": ("08118", "Ludwigsburg", False), "Rems-Murr-Kreis": ("08119", "Rems-Murr-Kreis", False),
    "Heilbronn city Städte": ("08121", "Heilbronn", True), "Heilbronn": ("08125", "Landkreis Heilbronn", False),
    "Hohenlohe": ("08126", "Hohenlohekreis", False), "Schwäbisch Hall": ("08127", "Schwäbisch Hall", False),
    "Main-Tauber": ("08128", "Main-Tauber-Kreis", False), "Heidenheim": ("08135", "Heidenheim", False),
    "Ostalbkreis": ("08136", "Ostalbkreis", False), "Baden-Baden Städte": ("08211", "Baden-Baden", True),
    "Karlsruhe Städte": ("08212", "Karlsruhe", True), "Karlsruhe": ("08215", "Landkreis Karlsruhe", False),
    "Rastatt": ("08216", "Rastatt", False), "Heidelberg Städte": ("08221", "Heidelberg", True),
    "Mannheim Städte": ("08222", "Mannheim", True), "Neckar-Odenwald-Kreis": ("08225", "Neckar-Odenwald-Kreis", False),
    "Rhein-Neckar-Kreis": ("08226", "Rhein-Neckar-Kreis", False), "Pforzheim Städte": ("08231", "Pforzheim", True),
    "Calw": ("08235", "Calw", False), "Enz": ("08236", "Enzkreis", False), "Freudenstadt": ("08237", "Freudenstadt", False),
    "Freiburg": ("08311", "Freiburg im Breisgau", True),
    "Breisgau-Hochschwarzwald": ("08315", "Breisgau-Hochschwarzwald", False),
    "Emmendingen": ("08316", "Emmendingen", False), "Ortenaukreis": ("08317", "Ortenaukreis", False),
    "Rottweil": ("08325", "Rottweil", False), "Schwarzwald-Baar-Kreis": ("08326", "Schwarzwald-Baar-Kreis", False),
    "Tuttlingen": ("08327", "Tuttlingen", False), "Konstanz": ("08335", "Konstanz", False),
    "Lörrach": ("08336", "Lörrach", False), "Waldshut": ("08337", "Waldshut", False),
    "Reutlingen": ("08415", "Reutlingen", False), "Tübingen": ("08416", "Tübingen", False),
    "Zollernalbkreis": ("08417", "Zollernalbkreis", False), "Ulm Städte": ("08421", "Ulm", True),
    "Alb-Donau": ("08425", "Alb-Donau-Kreis", False), "Biberach": ("08426", "Biberach", False),
    "Bodensee": ("08435", "Bodenseekreis", False), "Ravensburg": ("08436", "Ravensburg", False),
    "Sigmaringen": ("08437", "Sigmaringen", False),
}

src, out = sys.argv[1], sys.argv[2]
features = []
for f in json.load(open(src, encoding="utf-8"))["features"]:
    p = f["properties"]
    if p.get("NAME_1") != "Baden-Württemberg":
        continue
    ags, name, city = KREISE[p["NAME_3"]]
    geom = shape(f["geometry"]).simplify(0.004, preserve_topology=True)
    features.append({"type": "Feature", "properties": {"ags": ags, "name": name, "city": city},
                     "geometry": json.loads(json.dumps(mapping(geom), default=list))})
features.sort(key=lambda f: f["properties"]["ags"])
assert len(features) == 44, len(features)
json.dump({"type": "FeatureCollection", "features": features}, open(out, "w", encoding="utf-8"), ensure_ascii=False,
          separators=(",", ":"))
print(len(features), "districts")
