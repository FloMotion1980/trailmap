# Trailrunden (multi-trail loop routes)

Split out of `CLAUDE.md` 2026-07-23 to keep that file lean — this is the single largest architecture section, covering a feature built out over several iterations on 2026-07-22/23.

An optional `loop: true` field on a `lineTrails` entry marks it as a route combining several of a region's individual trails plus connecting fireroad/access stretches (first example: Donnersberg's "Wasser & Holz", combining Langer Stein/Hungerbrunnen/Dicke Eiche/Schlossberg). Shows a 🔁 badge (`.badge-loop`) next to the name, same pattern as the uphill badge. `TRAIL_GEO[id]` still holds the loop's full flat coordinate list as normal (bounds/hit-testing/GPX-export/elevation-profile all work unchanged) — the loop-specific part is a **parallel, optional** `TRAIL_SEGMENTS[id]` entry: `[{coords, trailId|null}, ...]`, where `trailId` present means that stretch **is** one of the loop's component trails — not just color-matched, its `coords` are a byte-for-byte copy of that trail's own `TRAIL_GEO[trailId]` (see "geometry" note below) — and `trailId: null` means a connector stretch (rendered dashed, `CONNECTOR_COLOR`). `buildTrailLayer` resolves each segment's render color by looking up `lineTrails.find(tr => tr.id === seg.trailId).diff` **at render time** (not a color baked into the segment data), so it can never drift out of sync if that trail's own `diff` is ever corrected later. `buildTrailLayer` checks for `TRAIL_SEGMENTS[t.id]`: if present, `layer.line` is an `L.featureGroup` of per-segment polylines instead of the usual single `L.polyline` — `L.FeatureGroup` forwards `setStyle`/`bringToFront`/`removeLayer` to every child, so hover/solo-dim/selection-highlight/teardown all keep working unchanged on a loop the same as on any other trail. One consequence: the permanent name-label tooltip is bound to `hitLine` (not `line`) for *every* trail now, not just loops — `hitLine` is always a single flat polyline regardless of segments, so this keeps tooltip behavior uniform.

**Connector stretches are drawn thinner than trails** — `CONNECTOR_WEIGHT` (2.8) against `BASE_WEIGHT` (3.5), on the user's request (2026-07-28: "einen Tick schmaler"); they are the least important part of a loop and were competing visually with the trails at the same width. That broke the convenience above, though: since `L.FeatureGroup.setStyle` forwards to every child, the old `styleTarget.setStyle({weight: BASE_WEIGHT})` in `resetAllHoverStyles`/`setHover` would have fattened every connector back to 3.5 the first time the mouse touched *any* trail on the map — no click needed, exactly like the solo-mode opacity bug recorded in `CLAUDE.md`. Each styleable layer therefore carries its own `_tmBaseWeight`, and `applyLineWeight(target, hover, opacity)` walks the group (`eachLayer` when present, otherwise the single polyline) restoring per-layer widths and adding the *same* hover delta to whatever the baseline is — so a hovered connector goes 2.8 → 5.8 while its trails go 3.5 → 6.5, and the relative thinness survives hovering too. Verified on Donnersberg's loop: 2.8 at rest, still 2.8 after hovering an unrelated trail, 5.8 while the loop itself is hovered.

A loop with **no** `TRAIL_SEGMENTS` entry is a different case and deliberately stays at `BASE_WEIGHT`: there the *entire* route is drawn dashed grey (see the Odenwald cluster loops below), so it is the route itself rather than a connector, and thinning it would just make those loops harder to see.

## Geometry

A component-trail segment's `coords` deliberately reuse that trail's own already-simplified `TRAIL_GEO` array rather than an independent simplification of the loop's own GPX for that stretch (changed 2026-07-22 — the two traces are recorded on separate rides and never lined up exactly, which the user found visually irritating whenever both the loop and the individual trail were visible at once). Rebuilding this for a new loop: cluster the loop's raw GPX against each candidate component trail's raw GPX by point-to-point proximity (~20m threshold, then merge short connector gaps <10 points) to find each segment's `[start,end]` index range and which trail (if any) it matches; for a match, compare the segment's first/last point against the trail's `TRAIL_GEO[0]`/`[-1]` to check whether the loop travels the segment in the same direction as the trail's own recording (reverse the substituted array if not) — for Donnersberg's loop all 4 matched segments were already aligned, no reversal needed. One-off script, not yet repo-tracked.

## Critical invariant, learned the hard way 2026-07-23

`TRAIL_GEO[loopId]` (the loop's own full flat coordinate array — used for the yellow selection-highlight outline, bounds, hit-testing, and GPX export) **must be built as the exact concatenation of `TRAIL_SEGMENTS[loopId]`'s own `coords` arrays, in order** — never independently re-derived or re-simplified from the loop's raw GPX for the matched (`trailId` non-null) stretches. The first version of this feature got this wrong: `TRAIL_SEGMENTS` was updated to reuse each component trail's exact geometry, but `TRAIL_GEO[loopId]` was left as the loop's own original (different) raw-GPX-derived trace for those same stretches — meaning the visible colored segment and the yellow selection-highlight silently drew two different lines for the same stretch, only noticed because the user compared the selection highlight against the visible line and found them not identical. When rebuilding a loop's geometry, always regenerate `TRAIL_GEO[loopId]` by concatenating the (by-then-already-decided) segment coords, never treat the two as separately-maintainable arrays.

## Why `trailId` (not just a color) is stored

This is intentionally the seed of two features, per the user (2026-07-22) — (1) letting a Trailrunde's individual segments be clicked/hovered to show *that specific component trail's own* info panel, distinct from the loop's own panel, especially useful when only the loop (not its component trails) is currently filtered visible — **implemented 2026-07-23**, see below; (2) a planned "build a Trailrunde from existing trails" authoring UI, where a loop is fundamentally *composed of* references to existing trails (or pieces of them) plus connector stretches — the data model already reflects that composition, the authoring UI itself does not exist yet.

## Per-segment click (implemented 2026-07-23, simplified same day)

For every segment with a non-null `trailId`, `buildTrailLayer` additionally creates one invisible wide polyline (`weight:18, opacity:0`, same "fat invisible line over a thin visible one" trick as the whole-trail `hitLine`) over that segment's `coords`, carrying a tooltip with the referenced trail's own name (see the hover-tooltip-gating note below for exactly when it shows). Clicking toggles `selectedSegmentId` (module-level state, alongside `openTrailId`/`soloId`/`reversedId`) to that trail's id (or back to `null` if the same segment is clicked again) and calls `showTrailInfo(t)` + `selectCardFor(t.id)` for **the loop itself** (`t`, from `buildTrailLayer`'s own closure) — not the referenced trail — so the loop stays the map selection/highlight. These per-segment hitlines live in `layer.segmentHitLines` (an array) — **deliberately kept out of the `line` featureGroup**, because the group's `setStyle({opacity})` calls (whole-loop hover/solo-dimming) would otherwise overwrite these hitlines' always-0 opacity and make them visible; `render()`'s visibility toggle and `destroyTrailLayer` add/remove `layer.segmentHitLines` in parallel with `layer.line`/`layer.hitLine` instead. A connector segment (`trailId: null`) gets no hitline of its own — clicking/hovering there falls through to the loop's own whole-track `hitLine` underneath, opening/keeping the loop's own info panel as before.

**Z-order bug found building this**: `segmentHitLines` were added to the map before `hitLine` (built earlier, while constructing `line`) — since Leaflet's default SVG renderer stacks later-added paths on top, `hitLine` would otherwise sit above them and swallow every real pointer event across the whole track, so the more specific per-segment hit-areas never actually receive clicks/hovers in a real browser (only in a test that fires events directly on the layer objects, bypassing hit-testing entirely — which is exactly how this bug slipped through, see "Leaflet interaction testing" lesson). Fixed with `segmentHitLines.forEach(h => h.bringToFront());` placed right after `hitLine` is created.

## Per-segment permanent name labels (added 2026-07-23)

Same segments-with-`trailId` also each get a standalone `L.tooltip({permanent:true, ...})` (not bound to any layer — created via `L.tooltip().setLatLng(midCoord).setContent(name)`, so it's unaffected by the hover tooltip bound to that segment's own hitline) positioned at that segment's own midpoint, stored in `layer.segmentNameLabels` (array of `{trailId, label}`). `applyNameLabels()` — already called at the end of every `render()`, after that run's region/diff/category visibility has been applied via `map.addLayer`/`removeLayer` — adds/removes each one based on `showNames && !map.hasLayer(lineLayers[trailId].line)`: **suppressed whenever that specific component trail is also independently visible right now**, since the segment reuses that trail's *exact* geometry (see the "critical invariant" note above) and would otherwise show the identical name twice at almost the same spot — which is the common case, not an edge case, since `showDownhill`/`showLoop` both default to *on* simultaneously. Toggling either category filter off re-evaluates this immediately (next `render()` call), so a loop's own trail names correctly "fill in" the moment their standalone lines are hidden, and vice versa.

## Hover-triggered name tooltip, gated on "Namen" being off (added 2026-07-23)

Hovering any trail or Trailrunde on the map now shows its name as a tooltip — but *only* when the "Namen" checkbox (`showNames`) is currently off; when it's on, the permanent label is already shown and a hover tooltip would just be a redundant duplicate at almost the same spot. Every trail's `hitLine` tooltip is bound `{permanent:true, ...}` (so Leaflet does **not** auto-wire its own hover-driven open/close for it — permanent tooltips skip that internal wiring); the shared per-trail `setHover(on)` closure then opens/closes it manually, guarded by `if (!showNames)` on **both** the open (mouseover) and the close (mouseout) branch. Guarding the close branch matters just as much as the open one: without it, moving the mouse off a trail while "Namen" is on would wrongly force-close the permanent label that `applyNameLabels()` is independently holding open. The same trick is used for a loop's per-segment `segHit` hitlines (previously bound `{permanent:false}`, which made Leaflet auto-show them on hover unconditionally, regardless of `showNames`) — now also `{permanent:true}` + manual `openTooltip()`/`closeTooltip()` in its own mouseover/mouseout handlers, `openTooltip()` gated on `!showNames`, `closeTooltip()` called unconditionally on mouseout (safe/idempotent when it was never opened, and a segment's hitline tooltip is never the thing `applyNameLabels()` manages, only `segmentNameLabels` is, so there's no permanent-state to protect here the way there is for `hitLine`).

## Name label positioned off the line, not centered on it (added 2026-07-23)

Every trail-name tooltip (`hitLine`'s own, plus a loop's per-segment `segmentNameLabels`) uses `direction:"top", offset:[0,-6]` rather than `direction:"center"` — the label now floats just above its anchor point instead of sitting directly on top of the line, so the actual trail stays visible underneath its own name instead of being covered by it. Matters most for short trails/segments, where a centered label could visually cover most or all of the line. Raised by the user specifically as a simpler alternative to zoom-dependent font scaling or hiding labels below a pixel-length threshold (both discussed as ideas, neither implemented) — repositioning the anchor turned out to solve the core complaint ("the label covers the trail") directly, with no zoom/pixel-geometry bookkeeping needed. `.trail-label-tooltip::before{ display:none; }` already hides Leaflet's default tooltip arrow, so changing `direction` needed no other CSS adjustment. The `startMarker`/`endMarker` "Start"/"Ziel" labels and the place-name labels (`PLACES`) already used `direction:"top"` with an offset — this just brings trail names in line with that existing pattern instead of being the one outlier using `"center"`.

## Inline segment info in the loop's own panel (implemented 2026-07-23)

**First implementation tried a whole second info panel** (`#infoPanelSecondary`) shown alongside the primary one — the user asked for it, then simplified the request once it existed: the segment info needs none of a full panel's buttons (solo/reverse/GPX-download) or its own elevation chart, so a small inline section within the *existing* loop panel does the job with much less code. The two-panel version (and its `primaryTrailId`/`secondaryTrailId`/`showSecondaryTrailInfo`/`refreshOpenPanels` machinery) was built, verified, and then **fully removed same day** — worth remembering before re-building something similar from scratch.

**Current, simplified design**: `buildInfoPanelHtml(t)` — when `t.loop` and `selectedSegmentId` is set — looks up that segment's entry in `TRAIL_SEGMENTS[t.id]` (for its precomputed `distStart`/`distEnd`, see the data-build note below) and the referenced trail's own `lineTrails` entry, then (a) passes `{distStart, distEnd, color: diffColor[segTrail.diff]}` to `buildElevationSvg(profile, highlight)`, which draws a shaded `<rect>` band across that distance range *behind* the existing polyline/area (added as an optional second param, `null` for every non-loop trail — zero effect on normal rendering), and (b) appends one small `.ip-segment-info` block below the `.ip-actions` GPX button with that trail's own name/len/up/down. Toggling logic lives in the segment hitline's click handler itself (not inside `showTrailInfo`, to avoid the same reset-ordering trap noted below) — it manually pre-sets `openTrailId = t.id` *before* computing the new `selectedSegmentId` and calling `showTrailInfo(t)`, specifically so `showTrailInfo`'s own `if (openTrailId !== t.id) selectedSegmentId = null` reset (which exists for the ordinary case: opening a genuinely different trail/loop clears any stale segment selection) doesn't fire and immediately wipe out the just-computed value.

**Data**: every `TRAIL_SEGMENTS[loopId]` entry — connector stretches included, not just trail-matched ones (extended same day so the whole chart could be colored, not just highlighted stretches) — carries `distStart`/`distEnd` (km, same units as the elevation profile's own x-axis). Computed once at data-build time by walking cumulative haversine distance along `TRAIL_GEO[loopId]` (which is exactly the segment concatenation) up to each segment's start/end index, then rescaled by `profileTotalKm / geoTotalKm` to line up with the profile's own total distance (built from the slightly-longer raw/unsimplified point set) — a few meters of drift either way is imperceptible at chart resolution.

## Elevation chart segment-coloring + map/chart hover-sync dot (2026-07-23)

- Elevation chart is colored by the trail's own difficulty: `buildElevationSvg(profile, highlight, color, trailId, reversed, segments)` takes a `color` param (`diffColor[t.diff]`, passed from `buildInfoPanelHtml`) used for both the polyline stroke and — via a `hexToRgba(hex, alpha)` helper — the translucent area fill beneath it, for a normal trail. Previously both were hardcoded green regardless of the trail's actual difficulty, which was actively misleading since green is itself one of this app's difficulty colors.
- **For a Trailrunde specifically**: pass `segments` instead — an array of `{distStart, distEnd, color}` mirroring the *same* per-stretch coloring already used on the map (that stretch's own trail's `diffColor`, or `CONNECTOR_COLOR` for a connector) — and the chart draws one polyline+polygon pair per segment instead of a single flat-colored one, so the profile visually matches the map exactly. `buildInfoPanelHtml` builds this array from `TRAIL_SEGMENTS[t.id]` (skipping any entries missing `distStart`) — when `isReversed`, each segment's `distStart`/`distEnd` is flipped (`totalDist - distEnd, totalDist - distStart`) the same way `reverseElevationProfile()` flips the profile itself.
- `profileSlice(profile, distStart, distEnd)` (using an `elevationAtDistance(profile, d)` interpolation helper) cuts a clean sub-range of the profile at each segment boundary — including interpolated endpoints exactly at `distStart`/`distEnd` — so adjacent per-segment polylines meet with no visible gap or overlap.
- The highlighted-segment `<rect>` (shown when a specific segment was clicked) is drawn **after** (on top of) the per-segment lines/areas, so it reads as a "you clicked this one" tint over an already fully-colored chart.
- **Hover sync**: moving the mouse across a trail's (or Trailrunde's) elevation chart shows a blue dot moving along the profile line *and* a matching dot on the map at that same point along the trail. `buildElevationSvg` stamps the SVG with `data-trail-id`/`data-reversed`/`data-profile` (JSON-encoded) plus axis-scaling constants needed to convert a mouse pixel position back into a distance-along-profile and then an elevation. One delegated `mousemove` listener on `#ipContent` (`handleEleChartHover`) handles every currently-open trail's chart generically:
  - `cumulativeDistanceKm(coords)` (using `haversineM`) precomputes cumulative distance per point of the trail's `TRAIL_GEO`; `getEleHoverData(svg)` caches this (plus the parsed profile) keyed by `trailId`.
  - `latLngAtDistance(coords, cumDist, targetKm, reversed)` binary-searches `cumDist` and linearly interpolates — `reversed` measures from the *end* of `coords` instead of the start, since the coords array itself is never physically reordered, only which end counts as "start".
  - A single reusable `eleHoverMapMarker` (`L.circleMarker`, `interactive:false`) is added to the map on first hover and repositioned via `setLatLng` rather than recreated.
  - Works generically for a Trailrunde too — a loop's `TRAIL_GEO[loopId]` is already the full concatenated track, so the hover dot walks the *entire* loop, not just one segment.

## Pre-existing bug also fixed 2026-07-23 (unrelated, just noticed at the same time)

The "Start"/"Ziel" tooltips on `startMarker`/`endMarker` could get stuck visible after the mouse naturally moves off them (with an actual mouse, not touch). Took three attempts:
1. `hideEndpoints(id)` calls `.closeTooltip()` on both markers before `map.removeLayer(...)` — covers the case where the marker gets removed from the map entirely. Didn't fix it (only helps when the trail *isn't* currently selected).
2. Added `.closeTooltip()` directly inside `startMarker`/`endMarker`'s own `mouseout` handlers, instead of relying on Leaflet's built-in hover-tooltip auto-close. Still didn't fix it.
3. **What actually fixed it**: moved the `.closeTooltip()` calls into the shared `setHover(on)` closure itself (unconditionally, whenever `on` is false, for *both* markers) rather than any specific element's own mouseout handler. Root cause suspected: `startDot` (always on the map) and `startMarker` (only added on hover/selection) sit at the *exact same coordinate* — when `startMarker` gets added directly under an already-stationary cursor, the browser doesn't necessarily transfer "currently hovered" state to it the way a genuine pointer transition would. Since `hitLine`/`startDot`/`startMarker`/`endMarker` all already call the shared `setHover(false)` on their own mouseout, closing both tooltips unconditionally inside that one shared function no longer depends on that ambiguity at all.

## Matching a tour against existing trails and lifts — four traps (Bike Kingdom, 2026-07-29)

`tools/build_bikekingdom_tours.py` is the first repo-tracked implementation of this matching (the earlier
ones were one-off scripts and are gone). Each of these produced a visibly wrong map before it was fixed, and
each was found only because the script prints a per-segment report with two diagnostic numbers: the length it
*drew* against the length the tour actually *rode* there, and every seam longer than 60 m.

1. **Densify the cable, not just the trails.** An OSM aerialway is often two vertices, tower to tower.
   Measuring track-point-to-vertex puts a point in the middle of a 937 m cable ~470 m from either end while
   it sits exactly on the line, so the "within 60 m" run collapses to the two ends. First run: **0 lift rides
   found across 4 tours**, with every station matching within 20 m.
2. **Match lifts BEFORE trails, over the whole track.** In a bike park the trail runs directly under the
   gondola that serves it, so trail-matching first dropped a 130 m sliver of "703 Rock'n'Roll" into the middle
   of the Känzeli–Brambrüesch ride, split the cable run, and both halves then failed the span test — the
   gondola vanished into a grey connector. Doing lifts first is safe because a ride is geometrically
   unmistakable: station to station, and **straight**. A detour check (walked ≤ 1.2 × straight span) is what
   separates it from a switchbacking uphill trail beneath the same cable.
3. **Search within a near-cable run for a station-to-station piece**, don't test the run as a whole. A tour
   rides the lift up and comes back down the trail beside it (Hörnli Trail under the Hörnli-Express), so both
   directions land in one run whose walked length is twice its span — testing the whole run threw the ride
   away. The descent can never win a candidate pair, because its own ratio fails.
4. **Rebuild a connector from the densified track, not from a vertex range of the tour's own line.**
   `own[min(vertex):max(vertex)+2]` looks right and is wrong: when the stretch falls inside a single long
   Douglas-Peucker edge, min and max collapse and the slice draws that whole edge — one connector drew
   **4384 m for 40 m of riding**. Densify-then-simplify reproduces the line exactly, since every densified
   point lies on it.

Also: clip a matched trail to where the tour **entered and left** it, not to min/max of every matched vertex.
One outlier match inflated the substituted geometry ~10 % over the tour's own track (schwarz: 99.8 km against
90.2 km ridden), drawing the line past the end of a trail the tour never rode that far on. After all of the
above, schwarz draws 90.4 km against 90.2 km, and the worst remaining seam is 95 m instead of 1144 m.

Seams are reported rather than silently trimmed, per the standing rule that an uncertain heuristic must
produce the honest output plus a marker, not the clever guess.

## A fifth trap, found after the first four (2026-07-30): MATCH_M is right for deciding, wrong for extending

Even with all four fixes above, the user found the E-bike tour's Hörnli Trail still missing 50 m at the
start and 1.26 km at the end, and Älplisee Trail missing ~1.3 km in the middle and ~600 m at the end — every
one of those gaps was drawn using the tour's own recorded line, which visibly diverges from the trail's real
line rendered everywhere else on the map. In every case the tour's actual track stayed within roughly
90-200 m of the true trail there — well beyond `MATCH_M` (25 m, correct for *deciding which trail a point
belongs to*, since two trails can run that close together) but well within what a human looking at the map
would call "still riding this trail."

**Fix: `extend_trail_ends`**, a second pass after the initial match + despeckle + gap-fill. It grows each
matched trail run outward into its neighbouring connector, one *densified* trail point (~10 m spacing, same
as the densified track — walking the original, coarser simplified vertices directly overshoots on a long
straight stretch and fails from pacing alone) and one track point at a time, accepting each step only while
it stays within `EXTEND_MATCH_M` (100 m — looser, and used *only* to grow an already-found run, never to
start one). Two runs of the same trail extending toward each other close the gap between them entirely,
which is how Älplisee's middle stretch got bridged.

**Why a strict one-step lockstep walk, not a free "nearest point within 100 m" search**: verified directly
against where the walk gives up (Hörnli Trail's tail, E-bike tour) that stopping is correct there, not just a
threshold that could be nudged further. Tracking the closest-matching trail vertex onward with no distance
cutoff at all shows it jump *backward* to smaller vertex numbers a few points later — the tour genuinely
leaves the trail's corridor at that point and happens to pass near an *earlier* stretch of the same trail
afterwards, rather than continuing forward along it. A free nearest-vertex search would have latched onto
that coincidence and drawn the tour riding backward over ground already covered. The strict, monotonic,
one-vertex-per-step walk cannot do that — it can only fail safely.

**`MAX_QUIET_JOIN_M` raised from 60 to 115** as a consequence: a trail extension deliberately stops right at
`EXTEND_MATCH_M`, so the following connector's own first recorded point can legitimately sit up to that far
from the trail's last accepted point — not a defect, just where extension correctly gave up. Reports dropped
from 20+ flagged seams to 1 on rebuilding all four tours.

## Deliberately not addressed

The overlap-when-both-visible case (loop and its component trails simultaneously shown) was explicitly *not* addressed with extra suppression logic — the user was fine with it (toggle the relevant category filter off if it's ever distracting), especially now that the geometry lines up exactly instead of jittering.
