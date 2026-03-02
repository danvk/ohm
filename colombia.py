#!/usr/bin/env python

import json
import sys

WIKI = {
    "Q230607": "es:Caldas",
    "Q44724": "es:Amazonas (Colombia)",
    "Q238629": "es:Meta (Colombia)",
    "Q232564": "es:Cundinamarca",
    "Q234501": "es:Tolima",
    "Q123304": "es:Antioquia",
    "Q230882": "es:Atlántico (Colombia)",
    "Q230597": "es:Bolívar (Colombia)",
    "Q234916": "es:Cesar",
    "Q199910": "es:Magdalena (Colombia)",
    "Q235188": "es:Sucre (Colombia)",
    "Q234912": "es:Córdoba (Colombia)",
    "Q272747": "es:La Guajira",
    "Q230584": "es:Chocó",
    "Q13990": "es:Valle del Cauca",
    "Q233058": "es:Norte de Santander",
    "Q13995": "es:Quindío",
    "Q268729": "es:Vichada",
    "Q234505": "es:Vaupés",
    "Q235166": "es:Santander (Colombia)",
    "Q13993": "es:Risaralda",
    "Q232953": "es:Putumayo (Colombia)",
    "Q230217": "es:Nariño (Colombia)",
    "Q272885": "es:Guaviare",
    "Q238645": "es:Guainía",
    "Q230223": "es:Arauca (Colombia)",
    "Q121233": "es:Boyacá",
    "Q13984": "es:Casanare",
    "Q230602": "es:Cauca (Colombia)",
    "Q13985": "es:Caquetá",
    "Q234920": "es:Huila",
    "Q26855": "es:Archipiélago de San Andrés, Providencia y Santa Catalina",
    "Q2841": "es:Bogotá",
}


def main():
    (input_fc,) = sys.argv[1:]
    fc = json.load(open(input_fc))
    assert fc["type"] == "FeatureCollection"
    features = fc["features"]
    f_in = len(features)
    features_out = []
    tags_in = 0
    tags_out = 0
    for f in features:
        p = f["properties"]
        if not p["name"]:
            continue
        if p["wikidataid"] == "Q2841":
            p["iso_3166_2"] = "CO-DC"
        tags_in += len(p)
        props = {
            "admin_level": 4,
            "boundary": "administrative",
            "type": "boundary",
            "place": "department",
            "start_date": "1991",
            "source": "Natural Earth Data",
            "name": p["name_es"],
            "wikidata": p["wikidataid"],
            "wikipedia": WIKI[p["wikidataid"]],
            "ISO3166-2": p["iso_3166_2"],
        }
        for k, v in p.items():
            if k.startswith("name_") and k not in (
                "name_alt",
                "name_len",
                "name_local",
            ):
                _, lang = k.split("_")
                props[f"name:{lang}"] = v
        f["properties"] = props
        tags_out += len(props)
        features_out.append(f)

    fc["features"] = features_out
    sys.stderr.write(
        f"{f_in} -> {len(features_out)} features, {tags_in} -> {tags_out} tags\n"
    )
    json.dump(fc, sys.stdout)


if __name__ == "__main__":
    main()
