# OHM Boundary Viewer

Viewer for administrative=boundary features on OpenHistoricalMap.

Built using [Vite](https://vite.dev), [React](https://react.dev), and [TypeScript](https://www.typescriptlang.org/).

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
