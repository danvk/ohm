# OHM Boundary Viewer

Viewer for administrative=boundary features on OpenHistoricalMap.

🌎 [Live Site](https://danvk.org/ohm/)

The idea is to get a clearer sense for OHM's global coverage of administrative boundaries through time:

- Where are the blank spots?
- Where are there overlapping features?

The site is built using [Vite](https://vite.dev), [React](https://react.dev), [TypeScript](https://www.typescriptlang.org/) and [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/).

## Data encoding

This site is all static content. It loads the full data set on page load from `relations.json` and `ways.json`. Not very efficient, but simple and effective!

To make this at all workable, the boundary viewer encodes the ways and relations in a custom format (`extract_for_web.py`). Here's the gist:

1. Extract relevant relations (say admin_level=2) from a planet file.
2. Collect relevant ways and nodes.
3. Quantize latitudes and longitudes to 1m precision. Use delta encoding for ways: `[lng1,lat1,dlng1,dlat1,dlng2,dlat2,...]`.
4. For each relation, group ways into rings. If a way needs to be reversed to form a properly-oriented ring, store its way ID as a negative number.

This produces files that are large but workable (~7MB for `relations.json` and 22MB for `ways.json` for admin_level=2). The grouping into rings reduces the amount of work the frontend needs to do when you scrub through time. See OSM's [multipolygon algorithm] for details. (`extract_for_web.py` doesn't do all this.)

[multipolygon algorithm]: https://wiki.openstreetmap.org/wiki/Relation:multipolygon/Algorithm

## Prerequisites

- [Node.js](https://nodejs.org/) (v18 or later recommended)
- npm (bundled with Node.js)

## Getting started

Install dependencies:

```bash
npm install
```

## Development

Start the Vite dev server with hot module replacement:

```bash
npm run dev
```

The app will be available at `http://localhost:5173` (or the next available port).

## Type checking

Run the TypeScript type checker:

```bash
npx type-check
```

Or equivalently:

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
cp -r dist/* ../../danvk.github.io/ohm
```
