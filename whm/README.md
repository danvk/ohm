# WorldHistoryMaps (WHM) Import and Comparison

[World History Maps](http://www.worldhistorymaps.com/) (WHM) provides historical boundary data in a custom SVG format. It is the work of [John C. Nelson](http://www.worldhistorymaps.com/About.html).

This repo includes tools for converting this into OSM format, so that it can be compared with OHM. The idea is to see where OHM has gaps in coverage that could plausibly be filled with more mapping work.

## Import

The global maps portion of WHM is no longer being updated as of 2014, so this import process only needs to be run once. The output is in `whm/whm_all.osm.pbf`.

### Download and Extract

Download all the SVG files from http://www.worldhistorymaps.com/World/index.htm and place them in a directory. This is around 850MB.

Then run:

```
uv run whm/build_countries.py --svg-dir path/to/whm/dir
```

This produces `whm/countries.json`, which is ~50MB. This uses a simple encoding scheme that only stores the SVG path and properties for a feature when they change.

### Unproject and Clip

The raw SVG files have two issues:

- They use an undocumented projection, rather than lat/lng.
- To simplify the polygons, SVG shapes do not include coastlines.

To import into osm.pbf format, we need to fix both of these issues. The projection is close to a [Winkel Tripel]. To improve its precision, we use a mesh of known points and adjust it using an [IDW interpolation] scheme.

To get coastlines, we intersection each feature with the earth's land (`land.geojson`). This comes from Natural Earth Data's [Land polygons].

```
uv run whm_to_osm.py -o whm/whm_all.osm.pbf
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

```
uv run extract_for_web.py whm/whm_all.osm.pbf \
    --config whm/boundary-viewer.config.jsonc \
    --output-dir /path/to/whm-boundary
```

This writes `relations2.b64.json` and `ways2.json` to the output directory. Point the boundary viewer at this directory by setting `BASE_URL` in `app/src/loader.ts`.

[usual process]

### Compare with OHM data
