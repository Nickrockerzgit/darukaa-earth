# ADR-0007: Mapbox layers over React map components

**Status:** Accepted · **Date:** 2026-09-18

## Context

The map must render every site polygon, highlight hover and selection, show
labels above a zoom threshold, and let a user draw a new polygon.

`react-map-gl` allows either approach: render each feature as a React component
(`<Marker>`, `<Layer>` per site), or hand Mapbox one GeoJSON source and describe
the styling declaratively.

## Decision

One `<Source>` holding the whole `FeatureCollection`, styled by three
`<Layer>`s: fill, outline and symbol. Hover and selection are Mapbox **feature
state**, not React state.

## Why

**Rendering cost is flat in the number of sites.** With a component per feature,
500 sites is 500 React nodes that reconcile on every pan. With one source it is
three nodes regardless, and the work happens on the GPU.

**Styling is data-driven, evaluated in the style engine:**

```js
[
  'match',
  ['get', 'project_type'],
  'carbon',
  '#37d9a0',
  'biodiversity',
  '#5fb5f0',
  'mixed',
  '#b48ff0',
  '#37d9a0',
];
```

Colour by project type costs nothing per feature and needs no JavaScript.

**Hover and selection repaint without a data reload:**

```js
[
  'case',
  ['boolean', ['feature-state', 'selected'], false],
  0.55,
  ['boolean', ['feature-state', 'hover'], false],
  0.38,
  0.22,
];
```

`setFeatureState` triggers a GPU repaint. Changing a React prop would re-diff
the source and re-upload the geometry.

**Mapbox owns hit-testing and label collision.** `interactiveLayerIds` gives
precise polygon hit-testing for free, and the symbol layer hides labels that
would overlap. Both are genuinely hard to reimplement.

**One request feeds the map.** `GET /sites/geojson` returns a FeatureCollection
with a `bbox`, so the client can `fitBounds` without a second call or a
client-side sweep over every coordinate.

## Rejected

**A component per site.** Simpler to reason about and easy to attach React
handlers to, but the cost is linear in feature count, and hover state would live
in React — a re-render per mouse move.

**Rendering polygons on a canvas overlay.** Full control, but reimplements
projection, hit-testing and label placement. No.

## Cost

- Styling is Mapbox expression syntax, not CSS or React, so it is a second
  language in the codebase. It is confined to `lib/mapbox.ts`.
- Feature state needs stable ids. `promoteId="site_id"` lifts the property into
  the feature id, because `setFeatureState` cannot address a feature otherwise.
- The map cannot be unit-tested: `mapbox-gl` requires WebGL, which jsdom does
  not implement. `src/features/map/**` is therefore excluded from coverage and
  covered by the manual walkthrough in `docs/testing.md`. The page _around_ the
  map is tested with the map stubbed
  (`ProjectDetailPage.test.tsx`).
