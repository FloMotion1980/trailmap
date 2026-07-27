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

**Tours are hidden while the mode is on** (2026-07-27, user: *"Die stören da nur"*) — whatever the 🔁
switch says, which is therefore `disabled` and dimmed for the duration rather than left looking functional.
A Tour lies on top of the very trails you are picking, so its line, its per-segment name labels and its wide
hit-lines all get in the way of the one activity this mode is for. `render()`'s category check reads
`t.loop ? (showLoop && !builderMode) : ...`, and the mode toggle calls `render()` as well as
`renderBuilder()`. Measured: 219 → 114 overlay paths, trail counter 51/51 → 49/51.

One consequence worth knowing: two of the nine `builderTryAdd` sites are a Tour's own segment hit-lines
(the "copy an existing route by clicking its segments" trick), and they are unreachable while the mode is
on. If that turns out to be missed, the better shape is a "copy this Tour into the builder" button on the
Tour's info panel, which does not need the Tour to be visible at all.

**Totals.** Taken from each element's own published figures (`lineTrails.len/up/down`, and `liftClimb()` for
a lift) rather than recomputed from geometry, so the builder agrees with what the trail list and the lift
panel already show. `reversed` swaps up/down for a trail; for a lift it moves the climb to the descent side,
which no real lift here does but is kept honest rather than silently ignored.

**Map highlight.** A **glow** per element, in its own pane `builderPane` at z-index **345** — below the
trails (overlayPane, 400) and below the lift mask (350), so a wide highlight can never cover the very lines
it is pointing at. Same reasoning as the lift band's own pane.

The glow is three stacked polylines (`BUILDER_GLOW`: soft 26px halo → 16px body → 8px bright core, all in
the `--highlight` amber family) plus a `drop-shadow()` filter on the **pane element itself**
(`.leaflet-builder-pane` in `style.css`) — one filter for the whole chain, so the halo reads as continuous
instead of showing per-line seams. The first cut's single 12px/0.5 band was too easy to lose against a busy
base map (user, 2026-07-27). The core stays wider than `BASE_WEIGHT` (3.5) so it shows on both sides of the
trail line drawn above it.

Note the pane's CSS class: Leaflet's `createPane("builderPane")` produces `leaflet-builder-pane`, not
`leaflet-builderPane` — it rewrites a trailing `Pane` into `-pane`. Getting this wrong fails silently (the
rule simply never matches anything), which is exactly what happened first.

**Numbered start dots.** One green circle per element, at `r.coords[0]` — and since `builderResolve()`
returns coordinates already clipped *and* oriented, that is by construction the end you actually set off
from, so the per-row 🔄 moves the number to the element's other end with no extra bookkeeping. Same green /
dark-green as the existing "Start" marker so the two read as the same kind of thing. These are `L.marker`s
with a `divIcon` and **no `pane` option**: markers belong in Leaflet's `markerPane` (600), *above* the
trails — unlike the glow bands, which deliberately sit below them.

## Junction clipping

A tour rarely rides a trail end to end: a new trail often starts partway along another one, and you
likewise join a trail somewhere other than its start. Rather than making the user mark those points, the
cut is **derived from the sequence**, which is what the sequence already says.

For each consecutive pair, the closest approach between the two lines is the junction: the earlier element
leaves there, the later one joins there. Per element, `full: true` opts out entirely.

### Cycling the candidates (2026-07-27)

The guess is right often but not always — the user's verdict after a day of riding it: X-Line into the
Schattberg Sprinter works, other spots do not, *"bei dem intelligenten Junction Clipping kann man mit
Fehlern leben… wenn es eine Möglichkeit gäbe, die verschiedenen Möglichkeiten durchzuwechseln"*. So instead
of chasing a smarter heuristic, **every plausible junction is offered and the user cycles**.

`junctionCandidates(A, B)` returns all of them, best first: for each point of A the distance to the nearest
point of B, then every **local minimum** of that curve, sorted by gap, dropping any beyond
`JUNCTION_MAX_GAP_M` (150 m — farther apart than that is not a junction, just two nearby trails) and any
within `JUNCTION_MIN_SEP_KM` (150 m along A) of a better one already kept, capped at
`JUNCTION_MAX_CANDIDATES`. Candidate 1 is by construction exactly what the old single-answer version
returned, so this could only add options, never change a default. If no minimum is close enough, the
closest approach is still returned as a single candidate — the UI flags the wide gap in rust instead.

Two details that are easy to get wrong:

- **Scan the side that has a shape.** A lift contributes one station point (see below), so when the lift is
  the element being *left*, the alternatives live on the following trail's side. `junctionCandidates` swaps
  the roles in that case, otherwise a trail passing its arrival station twice would offer one candidate.
- **`<=` on both neighbours** when detecting a minimum, so a flat stretch still registers; the separation
  filter removes the duplicates that produces.

The chosen candidate is stored as `junctionAlt` on the **later** element, meaning "the Nth candidate for the
junction with whatever is in front of me". That reading matches the UI and keeps a row's control from
reaching backwards past its own row. It also means the value is nonsense as soon as that neighbour changes,
so every structural edit brackets itself in `builderPredecessorSnapshot()` /
`builderClearStaleAlts()`, which clears the alts of exactly the pairs the edit touched and leaves the rest
tuned. A lift's `reversed` is part of that key, since flipping a lift changes which station it contributes.

**UI:** the junction gets its own thin row *between* the two element rows, because that is where it sits:
`↳ Übergang · 84 m · 1/3 ⟳`. The gap doubles as a quality signal — a few metres means the lines really do
meet there, a hundred-plus means the guess is probably wrong and worth cycling. The **whole row** is the
control, not the ⟳ glyph, which at 19×16 px is not a hittable target on a phone.

**A lift contributes only one point to the junction search, not its whole cable** — its boarding station
when it is being joined, its arrival station when it is being left. This matters: the user's own example is
leaving the X-Line for the Schattberg Sprinter, and you quit the trail where the *valley station* is, not
where the cable happens to pass overhead. Lifts themselves are never clipped; you ride a cable end to end.

Direction falls out of the clip (entry index vs exit index).

### An open end follows the trail's own direction (fixed 2026-07-27)

**Not** "whichever terminus leaves the longer ride", which is what the first version did and is simply the
wrong criterion: every trail here has a direction of its own, drawn with Start/Ziel markers and direction
arrows. The Schattberg Sprinter's valley station sits at X-Line index 118 of 617, near the summit, so the
longer ride started in the valley and the builder rode a 1117 m descent backwards *uphill* — 990 m →
1826 m. The user hit it from both sides: the numbered start dot jumping to the far end of the trail when a
lift was appended, and *"wenn ich Back to Black als 1 anklicke und als 2 die xline, dann fährt er die xline
hoch"*.

Measured against the region data, before → after:

| sequence | ridden | elevation |
|---|---|---|
| X-Line → Sprinter | 5.33 → **1.31 km** | 990 → 1826 m *becomes* 2009 → 1826 m |
| Back-to-Black → X-Line | 4.27 → **2.38 km** | uphill *becomes* 1412 → 990 m |

The `Math.abs(b - a) < 1` guards cover a junction sitting **on** the terminus the direction points at —
there is nothing to ride that way, so the stretch comes from the other end instead (ScheeLeitn Line joins
the Wurzel-Trail at its own index 0 and is therefore ridden 69 → 0).

Some sequences genuinely force a climb: `Back-to-Black → X-Line → Sprinter` pins both X-Line ends down and
the lift station is above where the trail was joined, so it has to be pedalled up. Nothing in the row said
so, hence **`r.against`** — a stretch ridden against its trail's own direction shows a rust ↑ with a
tooltip. `uphill`-flagged trails are exempt, since for those a climb is the point.

### What 🔄 means on a clipped trail (fixed 2026-07-27)

It flips **which terminus the open end runs to** — not the finished stretch. Reversing the stretch is only
meaningful when nothing constrains the direction: once a junction pins one end down, the direction of travel
is a fact of the sequence. You leave a junction you have just joined at; you do not ride back into it.

The first version flipped `forward` *after* the clip, which is what the user hit with the Wurzel-Trail
ridden backwards. Verified against the real Saalbach data: for `ScheeLeitn Line → Wurzel-Trail`, the Wurzel
stretch is joined at index 114 and ridden down to 0 — pressing 🔄 turned that into 0 → 114, i.e. the stretch
ran *into* its own entry junction. Now it instead runs 114 → 117, the other way out of the same junction
(0.11 km, and the row says so).

Consequences worth knowing:

- A trail clipped at **both** ends has no freedom left, so its 🔄 is `disabled` with a title saying why
  (`r.dirFixed`). Opting out with ⇔ frees both ends and makes 🔄 a plain reversal again — which is the way
  to force a direction the sequence would otherwise dictate.
- An element with no junction at all (single-element tour, or `full`) reverses exactly as before.
- The degenerate-clip fallback (`hi - lo < 1` → whole trail) now also catches "the flip picked the terminus
  the junction sits on", which would otherwise be a zero-length stretch.

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
