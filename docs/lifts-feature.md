# Bike lifts (map objects + filter + lift segments in Touren)

Added 2026-07-26. Motivated by the two Bikecircus "Challenge" tours, which are partly ridden by
gondola: before this, those stretches were drawn as anonymous grey connectors, implying you pedal
them. The user asked for lifts as their own map objects with a filter — "Die Lifte, die fürs
Mountainbiken sind, könnten wir als neue Objekte auf der Karte und einen Filter dafür einbauen."

## Data model

A new **optional `lifts` array** per `regions/<group>.json`, alongside `lineTrails`/`trailGeo`/
`elevationProfiles`/`trailSegments`/`places`:

```json
{ "id": "lift_bc_a1", "name": "Schattberg X-Press I", "code": "A1",
  "region": "saalbach", "type": "gondola",
  "coords": [[lat,lng], ...], "baseEle": 996, "topEle": 1471, "osm": "way/123" }
```

- `region` is a `REGIONS` sub-region key, exactly like a trail's.
- `coords` is **always stored bottom-station-first**, so `baseEle`/`topEle` need no per-lift direction
  flag and the info panel can say "base → top" without checking anything.
- `type` maps to a German label via `LIFT_TYPE_LABEL` (gondola/chair_lift/cable_car/funicular/
  platter/t-bar/drag_lift/mixed_lift).

In the app, `LIFTS` is a mutable array that starts empty and is filled/emptied per region group by
`activateRegionGroup`/`deactivateRegionGroup`, exactly like `lineTrails`.

**A lift is deliberately NOT an entry in `lineTrails` with a flag.** It is not a rideable trail, so it
has to stay out of the difficulty filter, the `shown/total` counters, the trail list and the elevation-
profile machinery. It gets one global on/off switch (`showLifts`, sidebar "🚡 Lifte", persisted with
the other filters) and is not gated on `activeDiffs` or the Downhill/Uphill/Touren switches — only on
`showLifts` plus its own sub-region being active.

## Which lifts belong in the data — operator only, never OSM's bike tag

**OSM supplies geometry only.** Whether a lift runs in summer *and* carries bikes must come from the
operator's own summer-lift page. The user flagged this up front ("natürlich musst du recherchieren,
welche Lifte im Sommer laufen und bikes transportieren"), and Saalbach proved it in both directions:

- OSM has `aerialway:bicycle=yes` on **Reiterkogelbahn I (D1)** — which is closed for the whole of
  summer 2026 for a rebuild.
- OSM has **no** bike tag on **12er KOGELbahn 2 (B2)** — which the operator does carry bikes on.

So a `bicycle`/`aerialway:bicycle` tag is neither sufficient nor necessary. Join instead on OSM's
**`ref` tag**, which matches the resorts' own lift codes (A1, A2, B1, H2, L3, F1 …) exactly — that
turned out to be a clean, reliable key between the operator's published list and the OSM ways.

Deliberately excluded in Bikecircus, and worth re-checking each season:
- **C1 Hochalmbahn** — runs in summer, but no bike transport.
- **D1 Reiterkogelbahn** — closed all summer 2026 (rebuild).
- **F2 Streuböden II** — no bike transport (F1 carries bikes to the middle station only).
  Note saalbach.com's own combined overview row says "F1+F2 … yes"; the more specific Fieberbrunn
  source and OSM both say F2 does not. The specific source was followed — flag for the user.

## Rendering — OSM's own aerialway look

The user picked OSM's rendering as the model (screenshot): a **thin line with evenly spaced dots**,
where the **dot spacing stays constant on screen** — zoom in and you get more dots, not longer gaps.

That needs no zoom handler and no marker recomputation. SVG `stroke-dasharray` is applied by Leaflet
in **screen pixels** (the overlay pane re-projects paths on zoom but never rescales stroke attributes —
the same reason a connector's `"6,6"` dash looks identical at every zoom). A very short dash drawn with
a **round line cap renders as a dot**, so `dashArray: "1,11"` + `lineCap: "round"` gives dots 12
screen-px apart at any zoom, for free.

Two stacked polylines per lift: the hairline cable (`LIFT_CABLE_WEIGHT` 1.4) plus the dotted overlay
(`LIFT_DOT_WEIGHT` 4.5). Plus a hollow station `circleMarker` at each end — hollow so it doesn't read
as a trail's own filled green Start / red Ziel dot — and the usual invisible wide hit-line so a
hairline is still tappable on touch.

`LIFT_COLOR` is violet `#5b4a9e`, deliberately outside the `diffColor` palette and away from
`CONNECTOR_COLOR`'s grey. OSM draws aerialways near-black, but black here is already the `schwarz`
difficulty, and the user has previously objected (correctly) to a non-trail line reading as a
black-rated trail — that is exactly why `CONNECTOR_COLOR` was moved off `#222222`.

## Lifts inside a Tour (`TRAIL_SEGMENTS`)

A segment may now carry **`liftId`** instead of `trailId`. Three kinds of stretch exist:

| segment has | meaning | drawn as |
|---|---|---|
| `trailId` | one of the tour's component trails | that trail's own difficulty colour, solid |
| `liftId` | a lift ride | the lift's dotted violet style |
| neither | fireroad/access connector | `CONNECTOR_COLOR`, dashed `6,6` |

A lift segment behaves like a component-trail segment: its own hit-line, hover tooltip, and a click
that **keeps the tour's own panel open** (per the user's earlier rule that clicking into a tour must not
lose its context) and toggles a small lift block into it via `selectedSegmentId` — which therefore now
holds either a trail id or a lift id, and `buildInfoPanelHtml` resolves it against both. The elevation
chart colours that stretch violet too, so the profile keeps matching the map and a rider can see which
climbs they do not have to pedal.

**Ordering gotcha (was a real bug):** `LIFTS` must be filled **before** `buildTrailLayer` runs, because
a tour's lift segments resolve `seg.liftId` against `LIFTS` while being built. Filling it afterwards
silently drew those stretches as plain grey connectors. The lift *layers* are still built after the
trails, so the dotted cables sit above the trail lines in Leaflet's add-order z-stack.

**Filter interaction:** turning "Lifte" off hides the standalone lift objects but keeps a tour's own
lift stretches — otherwise the tour's line would have a gap in it. Deliberate.

## How the Challenge tours' lift segments were derived

The tours' source GPX bundles "pedal to the valley station, then ride up" into a *single* connector, so
a lift ride sits **inside** a connector rather than being one — a first pass that only looked for whole
connectors matching a lift found just 1 of 8. The connectors have to be **split**:

1. For each connector point, measure distance to each lift's cable; find the maximal run of consecutive
   points within 60 m.
2. Require that run to **span the cable from one station to the other** (both ends within 200 m of a
   station, and end-to-end distance ≥ 60% of the cable's) — otherwise a trail merely passing *under* a
   gondola would be tagged as a ride on it.
3. Cut the connector into `[before, lift, after]`, then re-examine the leftovers, since one connector
   can contain two lifts in sequence (BIG-5 rides Steinbergbahn I **and** II back to back).

Result: 8 lift rides — BIG-5: L3, L4, A2, A6; THE CHALLENGE: A2, A6, B1, F1.

**Two invariants to preserve when splitting** (both are asserted by the build script):

- **`concat(segment coords) == TRAIL_GEO[loop]` exactly.** The existing segments *share* their boundary
  point (`seg[i].coords[-1] == seg[i+1].coords[0]`), so a split must duplicate the cut point too, and
  `TRAIL_GEO` is rebuilt from the concatenation afterwards. A duplicate adds a zero-length step, so
  neither the total length nor the elevation profile shifts (verified, not assumed).
- **`distStart`/`distEnd` are on the elevation profile's x-axis and must not be recomputed globally.**
  Their existing values do not match a naive haversine walk of the geometry, so re-deriving them would
  silently shift every segment. New boundaries are interpolated *within* the split connector's own
  `[distStart, distEnd]` range, proportional to geometric length — purely a subdivision.

A first attempt that did **not** share the cut point produced 1-point stub segments carrying a
kilometre-wide distance range (an off-by-one: a piece ending at index `i0` was given the distance of
index `i0`, which belongs to the next piece). Watch for degenerate segments — `len(coords) < 2` or
`distStart == distEnd` — if this is ever re-run.

## Adding lifts to another region

1. Research the operator's summer lift list: which lifts run, and which carry bikes. Note the official
   lift codes.
2. Fetch `way["aerialway"]` from Overpass for that region's bbox (several small bboxes — one big one
   times out) and join on `ref` == the official code.
3. Backfill `baseEle`/`topEle` for the two endpoints (OpenTopoData `eudem25m`), store `coords`
   bottom-first.
4. Write the `lifts` array into `regions/<group>.json`. No app code changes needed — activation,
   teardown, the filter and persistence all iterate the data.
5. Optionally, split that region's tour connectors to tag lift rides (see above).
