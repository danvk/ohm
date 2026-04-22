# WorldHistoryMaps (WHM) Import and Comparison

[World History Maps](http://www.worldhistorymaps.com/) (WHM) provides historical boundary data in a custom SVG format. It is the work of [John C. Nelson](http://www.worldhistorymaps.com/About.html).

This repo includes tools for converting this into OSM format, so that it can be compared with OHM. The idea is to see where OHM has gaps in coverage that could plausibly be filled with more mapping work.

![Boundary viewer showing WHM data](/whm/whm-boundary.png)

## Import

The global maps portion of WHM is no longer being updated as of 2014, so this import process only needs to be run once. The output is in `whm/whm_all.osm.pbf`.

### Download and Extract

Download all the SVG files from http://www.worldhistorymaps.com/World/index.htm and place them in a directory. This is around 850MB.

Then run:

```sh
uv run whm/build_countries.py --svg-dir path/to/whm/dir
```

This produces `whm/countries.json`, which is ~50MB. This uses a simple encoding scheme that only stores the SVG path and properties for a feature when they change.

### Unproject and Clip

The raw SVG files have two issues:

- They use an undocumented projection, rather than lat/lng.
- To simplify the polygons, SVG shapes do not include coastlines.

To import into osm.pbf format, we need to fix both of these issues. The projection is close to a [Winkel Tripel]. To improve its precision, we use a mesh of known points and adjust it using an [IDW interpolation] scheme.

To get coastlines, we intersection each feature with the earth's land (`land.geojson`). This comes from Natural Earth Data's [Land polygons].

```sh
uv run whm/whm_to_osm.py -o whm/whm_all.osm.pbf
```

The feature are then run through `geojson_to_osm.py` to produce an osm.pbf file with common ways shared across relations. This also generates chronologies to track changes to features over time.

Takes ~3 minutes. The output `whm_all.osm.pbf` is ~3 MB. The whole history of the world in 3MB!

[Winkel Tripel]: https://en.wikipedia.org/wiki/Winkel_tripel_projection
[IDW interpolation]: https://en.wikipedia.org/wiki/Inverse_distance_weighting
[Land polygons]: https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/

## Analysis and Visualization

### Load into the boundary viewer

🌎 [Live Site](https://danvk.org/whm3/)

This follows the [usual process] for extracting JSON for visualization. WHM only contains country-level data and provides its own coloring, which we respect.

```sh
uv run extract_for_web.py whm/whm_all.osm.pbf \
    --config whm/boundary-viewer.config.jsonc \
    --output-dir /path/to/whm-boundary
```

This writes `relations2.b64.json` and `ways2.json` to the output directory.

To view the data in the boundary viewer locally, serve it on port 8081 with CORS:

```sh
cd path/to/whm-boundary
npx http-server --cors -p 8081
```

Then run the vite dev server with appropriate flags:

```sh
WHM=1 VITE_BOUNDARY_SERVER=//localhost:8081 npm run dev
```

The deployed WHM boundary viewer uses the same JS as the OHM version, so it doesn't need to be deployed separately.

[usual process]: https://github.com/danvk/ohm/#boundary-viewer

### Compare with OHM data

This produces an analysis of the coverage of OHM and WHM by region and era.

You can generate the OHM boundary viewer data from a planet file yourself, or grab it from the boundary viewer. (You need `relations2.json` and `ways.json`.)

First, a high-level comparison by region and era (takes ~30s):

```sh
uv run whm/region_era_coverage.py \
    --ohm-dir ~/code/ohmdash/boundary \
    --whm-dir ~/code/ohmdash/whm-boundary
```

If you want to drill down into specific chronologies, you can run this (~15 minutes):

```sh
uv run whm/whm_gap.py \
    --ohm-dir .../ohmdash/boundary \
    --whm-dir .../whm-boundary \
    --output-dir whm/gap
```

To produce decade coverage data (~30s):

```sh
uv run decade_coverage.py whm/whm_all.osm.pbf > whm-decades.txt
```

The corresponding stats for OHM planet take much longer (~10 minutes).

### Run stats pipeline

Something like this works:

```sh
TIMESTAMP=2026-04-22 ./extract-stats.sh whm/whm_all.osm.pbf whm/stats
```

Not all of these stats make sense in the context of WHM, but some highlights do:

```text
earth-years-admin-2,484.963135
double-covered-admin-2,11.841592
nested-shells,13
nonclosed-ring,15
self-intersect,43
```
