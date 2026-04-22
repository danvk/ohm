# OHM Boundary Viewer

Viewer for administrative=boundary features on OpenHistoricalMap.

🌎 [Live Site](https://danvk.org/ohm/)

The idea is to get a clearer sense for OHM's global coverage of administrative boundaries through time:

- Where are the blank spots?
- Where are there overlapping features?

The site is built using [Vite](https://vite.dev), [React](https://react.dev), [TypeScript](https://www.typescriptlang.org/) and [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/).

## Data encoding

This site is all static content. It loads the full data set on page load from `relationsN.json` and `waysN.json` (where N is the admin level). Not very efficient, but simple and effective!

To make this at all workable, the boundary viewer encodes the ways and relations in a custom format (`extract_for_web.py`). Here's the gist:

1. Extract relevant relations (say admin_level=8) from a planet file.
2. Collect relevant ways and nodes.
3. Quantize latitudes and longitudes to ~10m precision. Use delta encoding for ways: `[lng1,lat1,dlng1,dlat1,dlng2,dlat2,...]`.
4. For each relation, group ways into rings using the [multipolygon algorithm]. If a way needs to be reversed to form a properly-oriented ring, store its way ID as a negative number.

The grouping into rings reduces the amount of work the frontend needs to do when scrubbing through time. (`extract_for_web.py` doesn't implement the full algorithm.)

### Way ring encoding

Each ring in `relationsN.json` is a base64-encoded byte stream. Way IDs within a relation cluster in OSM ID space (assigned around the same time), so delta encoding the absolute values shrinks them dramatically. The encoding per ring:

1. For each way ID in order, compute `delta = abs(cur_id) - abs(prev_id)` (0 for the first entry).
2. Encode the delta with [zigzag encoding] to handle negative deltas: `zz = 2*delta if delta >= 0 else -2*delta - 1`.
3. Interleave a sign-change bit in the LSB: `v = zz * 2 + (1 if sign_changed else 0)`.
4. Write `v` as a [varint] (7 bits per byte, little-endian, high bit = more bytes follow).

This reduces the way data in `relations8.json` by ~45% compared to fixed 4-byte int32, from ~14 MB to ~8 MB (base64-encoded).

### Tag encoding

`relationsN.json` is a JSON object (not a bare array) with three lookup tables at the top level:

```json
{
  "tagPairs": [["boundary", "administrative"], ["type", "boundary"], ...],
  "tagKeys":  ["admin_level", "name", "source", ...],
  "tagVals":  ["county", "administrative", "1800", ...],
  "relations": [...]
}
```

Each relation's `tags` field is a flat array. Elements are decoded as:

- **Negative int `n`**: a complete key+value pair at index `-(n+1)` in `tagPairs`.
- **Non-negative int `k`** followed by **string or int**: key `tagKeys[k]` + value (literal string if unique, or `tagVals[v]` if int).

This replaces repeated string keys and common values with small integers, reducing tag storage by ~75%.

[multipolygon algorithm]: https://wiki.openstreetmap.org/wiki/Relation:multipolygon/Algorithm
[zigzag encoding]: https://protobuf.dev/programming-guides/encoding/#signed-ints
[varint]: https://protobuf.dev/programming-guides/encoding/#varints

## Quickstart

```bash
npm install
npm run dev
```

The app will be available at `http://localhost:5173` (or the next available port).

## Type checking

Run the TypeScript type checker:

```bash
npm run type-check
```

This performs type checking only and does not emit any files.

## Building for production

Compile and bundle the app for production:

```bash
npm run build
```

Output is written to the `dist/` directory. The contents of `dist/` can be served by any static file server.

To preview the production build locally:

```bash
npm run preview
```

## Deployment

To deploy to https://danvk.org/ohm/

```
npm run build
rm -rf ../../danvk.github.io/ohm && cp -r dist ../../danvk.github.io/ohm && cp dist/index.html ../../danvk.github.io/whm3/
```
