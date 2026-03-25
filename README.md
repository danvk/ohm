# OHM Exploration

Scripts for exploring OpenHistoryMap.

## Setup

- Create & sync the environment: `uv lock && uv sync`
- Run tests: `uv run pytest`
- Format/fix with ruff: `uv run ruff format .`
- Run ruff checks: `uv run ruff check .`

## Boundary Viewer

🌎 [Live Site](https://danvk.org/ohm/)

The boundary viewer is a web app for viewing administrative=boundary features in OHM. For more on running it, see [app/README.md](app/README.md).

The viewer encodes ways and relations in a special format so that it can load the entire history of the world into a browser tab. To extract data in this format, run:

```
uv run extract_for_web.py planet-260214_0301.osm.pbf
```

The exact commands for the live site were:

```
uv run build_connectivity_graph.py planet-260322_0301.osm.pbf
uv run extract_for_web.py --simplify-tolerance-m 1000 --vw-tolerance-m2 100000 planet-260322_0301.osm.pbf --admin-levels 1,2,3,4 --graph graph.json --coloring welsh-powell
```

## Tools

Most of these tools work with an OHM [planet file].

[planet file]: https://planet.openhistoricalmap.org/?prefix=planet/

### decade_coverage.py

This prints stats on how many square kilometers are covered by admin_level=2 and admin_level=4 features each decade. Since areas are often covered by two or more such features, this script does a geometric union of all features in each decade.

```
uv run decade_coverage.py planet.osm.pbf > admin.decade.txt
```

### dupe_finder.py

Find duplicate relations in a planet dump. Duplicates must:

- share all tags (except a few non-semantic tags like `source` and `fixme`)
- have the same underlying geometry

There is a little bit of wiggle room in the geometry matching, proportional to the scale of the feature. Large features can be off by a few hundred meters, but small features must match within a meter or so. Takes 30s-1m to run on an OHM Planet file.

```
$ uv run dupe_finder.py planet-260322_0301.osm.pbf
Candidate IDs: 7293
(7) Bicocca Stadium
  2797764 https://www.openhistoricalmap.org/relation/2797764
  2797792 https://www.openhistoricalmap.org/relation/2797792
  2797799 https://www.openhistoricalmap.org/relation/2797799
  ...
```

### find_by_name.py

Search `name` tag in a planet file. The parameter is a regular expression matched at the start of the string.

```
$ uv run find_by_name.py planet.osm.pbf "Imperium Roman
um"
Searching for 'Imperium Romanum' in planet.osm.pbf...
Found relation/2684681 Imperium Romanum
Found relation/2692869 Imperium Romanum
Found relation/2800647 Imperium Romanum Occidentale
...
```

### geojson_to_osm.py

Convert a GeoJSON FeatureCollection to an osm.pbf file, extracting common nodes and ways to the greatest extent possible. The Features will wind up as relations. [shp2osm] and [ogr2osm] should do something like this, but I was unable to get them to do exactly what I wanted.

```
uv run geojson_to_osm.py --filter='tag=val1,val2,...' input.geojson output.osm.pbf
```

This file can be imported into JOSM for uploading to OSM/OHM. The filter is applied _after_ topology extraction, so features that get filtered out will still affect how a polygon is broken up into ways. (This is what you want.)

### build_connectivity_graph.py

This is an exploration of [map coloring for OHM][color].

The idea is to create a color-coded political map where:

1. A country stays the same color over time.
2. Neighboring countries never have the same color.

The general approach is to form a graph and then apply a greedy graph-coloring algorithm to it. See the GitHub thread for details. As of March 2026, the OHM planet file could be colored with nine colors.

```
# Writes graph.json
$ uv run build_connectivity_graph.py

# Colors the graph, either using Welsh-Powell or DSatur
$ uv run python color_graph.py --coloring welsh-powell

# Analyze the graph, coloring it and looking for the max clique
$ uv run analyze_graph.py
```

See [Boundary Viewer](#boundary-viewer) for a command to use this coloring to create a political map.

[shp2osm]: https://wiki.openstreetmap.org/wiki/Shp2osm
[ogr2osm]: https://wiki.openstreetmap.org/wiki/Ogr2osm
[color]: https://github.com/OpenHistoricalMap/issues/issues/700
