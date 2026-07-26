# Tourenbuilder

Added 2026-07-26. A sidebar mode for assembling a route by clicking trails and lifts in ride order.

## Why it exists

Tours (Trailrunden/Touren) were until now derived offline from a recorded GPX, by matching each track point
against the region's trails and lifts. That works, but it is inherently a guessing game: the Challenge
tours needed three rounds of threshold tuning, and the user still found real errors afterwards (lift
stretches off the cable, a trail rendering mostly grey, the elevation profile out of sync with the drawn
line — see `docs/lifts-feature.md` and the Challenge rebuild commit).

The builder attacks the cause: instead of *inferring* a route from geometry, let the route be *stated*.
The user's framing — "In Richtung Trailbuilder gedacht… Trails und Lifte in der richtigen Reihenfolge
hintereinander platzieren" — is the same insight that fixed the Challenges, made interactive.

## Scope of this first cut

Deliberately limited, per the user ("Es ist OK, dass dann erstmal Lücken zwischen den Elementen bleiben —
das regeln wir später"):

- pick trails and lifts, in order
- reorder, flip direction, remove
- see the chain highlighted on the map and the running totals
- export the ordered element list

**Gaps between consecutive elements are left visible and unresolved.** That is why the export contains
only the element list and *not* `distStart`/`distEnd` or an elevation profile: both would be fabrications
until the gaps are closed. The export is exactly the input the offline assembler needs.

## How it works

**State.** `builderMode` (bool) and `builderItems` (`[{kind:"trail"|"lift", id, reversed}]`), persisted
under its own `localStorage` key `trailmap-builder-v1` — deliberately separate from the filter state, since
it is a work-in-progress document rather than a view preference. Restored at the *end* of `boot()`, after
the regions are loaded, because a row's name and length are resolved against `lineTrails`/`LIFTS`; restoring
earlier would render a list of bare ids.

**Adding.** Every click site funnels through one guard, `builderTryAdd(kind, id)`, which returns true when
the builder consumed the click so the caller can skip its normal "open the info panel" behaviour. There are
9 such sites: a trail's map line, its startDot/startMarker/endMarker, a lift's map line and its two station
markers, a Tour's own component-trail and lift segment hit-lines, and the sidebar trail card. Clicking a
Tour's segment adds the *referenced* trail or lift, which is a convenient way to copy an existing route.

**Totals.** Taken from each element's own published figures (`lineTrails.len/up/down`, and `liftClimb()` for
a lift) rather than recomputed from geometry, so the builder agrees with what the trail list and the lift
panel already show. `reversed` swaps up/down for a trail; for a lift it moves the climb to the descent side,
which no real lift here does but is kept honest rather than silently ignored.

**Map highlight.** One wide translucent line per element in the app's `--highlight` amber, in its own pane
`builderPane` at z-index **345** — below the trails (overlayPane, 400) and below the lift mask (350), so a
12px highlight can never cover the very lines it is pointing at. Same reasoning as the lift band's own pane.

## Junction clipping

A tour rarely rides a trail end to end: a new trail often starts partway along another one, and you
likewise join a trail somewhere other than its start. Rather than making the user mark those points, the
cut is **derived from the sequence**, which is what the sequence already says.

For each consecutive pair, the closest approach between the two lines is the junction: the earlier element
leaves there, the later one joins there. Per element, `full: true` opts out — needed when two trails cross
each other more than once, where the automatic guess can pick the wrong crossing.

**A lift contributes only one point to the junction search, not its whole cable** — its boarding station
when it is being joined, its arrival station when it is being left. This matters: the user's own example is
leaving the X-Line for the Schattberg Sprinter, and you quit the trail where the *valley station* is, not
where the cable happens to pass overhead. Lifts themselves are never clipped; you ride a cable end to end.

Direction falls out of the clip (entry index vs exit index); the per-row 🔄 flips the traversal on top of
that. The first and last elements run to whichever terminus leaves the longer ride.

Rows show `ridden / full km` in the accent colour whenever a clip happened, so it is never silent.

**up/down:** an unclipped trail reports its own published figures, so the builder agrees with the trail
list. A clipped stretch has to be integrated from `ELEVATION_PROFILES`, which **understates climbs** — the
profile is resampled to ~100 points and smooths small undulations away (Hacklberg integrates to 49 m
against its official 124 m). Nothing better is available in the browser; the offline assembler recomputes
up/down from full-resolution elevation when a tour is finalised.

## Extending it

The obvious next steps, in rough order of value:

1. **Close the gaps.** For each pair of consecutive elements, find a connecting path. Cheapest useful
   version: a straight link, drawn as a connector. Better: snap to nearby paths.
2. **Turn a built route into a real Tour.** Once gaps are closed, the assembled coordinate list can be
   concatenated and `len`/`up`/`down`/profile/`distStart`/`distEnd` derived from it — the same
   "derive-everything-from-the-assembled-geometry" rule that made the Challenge rebuild consistent by
   construction. Elevation still needs a DEM lookup, which cannot happen in the browser, so this either
   stays an offline step or needs an elevation source added.
3. **Drag to reorder** instead of the ↑/↓ buttons.
4. **Name the tour** and write it straight into a region JSON.
