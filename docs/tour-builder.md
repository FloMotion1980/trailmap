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

## Where it lives in the GUI (2026-07-27)

The list is **one element pinned to the map** (`#builderSheet`, a sibling of `#map` and `#infoPanel` inside
`.map-wrap`), on every screen size. The sidebar's `#secBuilder` keeps only the mode switch and a note
pointing at it.

The user's problem: on a phone the sidebar is a full-height drawer behind an opaque backdrop
(`#sidebarBackdrop`, z-index 2400), so while the list was visible the map was unreachable — *"In der Sidebar
ist es schwer die Trails anzuklicken auf der Karte, wenn man am handy arbeitet."* Their own follow-up
question settled the design: *"Ist das Bottom Sheet ein eigenes GUI element zusätzlich zur Sidebar?"* No —
two copies of the same list would mean two sets of handlers and inevitable drift, so the list moved out of
the sidebar rather than being duplicated. They also asked for desktop and mobile to stay similar, which is
what makes a single element workable at all.

`renderBuilder()` and `drawBuilderHighlight()` needed **no changes**: they address `#builderList`,
`#builderTotals` and `#builderCountLabel` by id, and those ids just moved.

- **One width rule for both platforms**: `min(100% - margins, 420px)`, anchored bottom-left. On a phone that
  *is* full width; on a desktop it is a 420px panel that clears the info panel (top right, 280px) and the
  locate button (bottom right) with no per-platform case.
- **No backdrop** — the entire point. Taps reach the map underneath. z-index 1600: above the map's floating
  controls, below the drawer (2500) and its backdrop (2400), so opening the drawer still covers it.
- **Collapsed it is just its handle** (~34px) showing `Tourenbuilder · 3 · 7.38 km`. State persisted as
  `builderSheetOpen` in the same `localStorage` key.
- **🧭 button on the map** (`#builderBtn`) toggles the mode, because with the list off the drawer you must
  not need the drawer to switch the mode *on* either. It and the sidebar switch both go through
  `setBuilderMode(on)`, which also closes the drawer when switching on.
- **The sheet carries its own ✕**. Not decoration: on a phone the sheet is full width at z-index 1600 and
  `#builderBtn` sits at 1000, so the map button is *behind* the sheet and could not switch the mode back
  off. `#builderSheetHandle` is therefore a `div` (a button inside a button is invalid HTML) whose click
  handler bails on `e.target.closest("#builderSheetOff")`.
- **Mobile only**, while the sheet is visible: `#locateBtn` moves to the top right (free there — drawer
  toggle is top left, `#liveStatus` top centre) and `#builderBtn` is hidden. Both via
  `html.has-builder-sheet`, the same technique the app already uses for `landscape-compact`, and with
  `!important` to beat the existing `html.is-standalone` overrides.
- One trap worth recording: `#locateBtn` is **not** at `bottom:16px` on mobile but 54px higher, to clear the
  bottom-centred info panel. `#builderBtn` sits beside it and has to mirror that offset *and* its
  `html.is-standalone` override, or the two buttons end up at different heights.

Still open: the builder glow and its numbered dots stay on the map when the mode is switched off (they
always did — `drawBuilderHighlight()` does not check `builderMode`). With the list in the sidebar that was
harmless; now that the sheet disappears with the mode, the glow is left without a visible list explaining
it. Not changed unasked.

## How it works

**State.** `builderMode` (bool) and `builderItems` (`[{kind:"trail"|"lift", id, reversed}]`), persisted
under its own `localStorage` key `trailmap-builder-v1` — deliberately separate from the filter state, since
it is a work-in-progress document rather than a view preference.

`boot()` splits the two halves of bringing it back, and the order matters in both directions:

- **`restoreBuilder()` before `render()`** — `render()` hides Tours while builder mode is on, so restoring
  the state afterwards left a reloaded page in builder mode with the Tours still showing (user, 2026-07-27).
- **`renderBuilder()` after `render()`**, and after the regions are loaded — a row's name and length resolve
  against `lineTrails`/`LIFTS`, so doing it earlier renders a list of bare ids.

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

## Row focus: pointing at one element (2026-07-27)

Hovering a row (desktop) or tapping it (phone) marks that element on the map: its glow switches to
`BUILDER_GLOW_FOCUS` — same widths, only brighter, up to a **near-white core** — and a **numbered red dot
marks where its stretch ends**, built exactly like the green start dot with the same number.

Nothing is dimmed and no other element changes. The first cut faded the rest back to 0.28 opacity and used
the app's own small "Ziel" `circleMarker` for the end; the user replaced both (2026-07-27): *"Ich würde die
anderen Elemente nicht ausblenden / dimmen. Mach einfach das Leuchten heller/fast weiß… Und ich würde den
roten Punkt wie den grünen zeichnen. Mit Zahl drin nur halt rot anstatt grün."*

That last part is the reason the feature exists. The user wanted to see whether a trail is being ridden
backwards; for normal trails the app already answers this (`setHover(true)` → `showEndpoints()`, so hover or
click shows the green "Start" and red "Ziel" markers), but a *builder element is usually clipped*, so those
markers sit at the trail's real ends rather than at the ends of what is actually ridden. With a start and an
end dot on the ridden stretch, direction reads straight off the map. Deliberately only while pointed at,
never permanently — *"nicht immer, nur bei Highlight"*.

Implementation notes:

- **Drawing is split out of `renderBuilder()`** into `drawBuilderHighlight()`, and `builderResolve()`'s
  output is cached in `builderResolved`. Rebuilding the rows on hover would replace the element the cursor
  is over, so its `mouseleave` would never fire and the highlight would stick; re-resolving on every
  mousemove would also redo every `junctionCandidates()` scan.
- `builderHoverIdx` (mouse, transient) and `builderActiveIdx` (tapped, survives rebuilds when the row still
  exists) with `builderFocusIdx()` preferring hover. `renderBuilder()` clears the hover — no pointer
  movement happens during a rebuild, so no `mouseenter` would fire — and clamps the active index.
- **Exactly one row is ever marked**, matching the map, which can only single out one element. A hover
  therefore takes the marking off a previously tapped row instead of adding a second highlight; the first
  version styled `.is-active` separately and it read as two selections at once.
- The row's click handler bails on `e.target.closest("button")` — a click on ⇔/🔄/↑/↓/✕ is not a request to
  focus the row.
- **The focused element's glow is drawn last.** All bands share one pane and Leaflet's SVG renderer stacks
  later paths on top, so drawing in list order would let a following element's 26px halo wash out the
  bright one.
- **The red end dot carries `zIndexOffset: 1000`** so it sits above every other marker. This is not
  cosmetic: element N's end and element N+1's start are the *same junction*, so the red dot lands within a
  few pixels of the next element's green dot almost every time (measured: 6 px for X-Line → Schattberg
  Sprinter). Without the offset, Leaflet's latitude-based marker ordering decides which one wins.
- No red dot on an `empty` stretch, where start and end coincide.

Still open, per the user: the existing direction arrows on trail lines ("die gefallen mir nicht") want a
redesign, and whatever that becomes should be applied to the builder's resolved coordinates too —
`builderResolve()` already returns them clipped *and* oriented, so `buildDirectionArrows()` can run on them
directly.

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

### Nothing ever auto-reverses; an empty stretch stays empty

A junction can land **on** the very terminus the trail's direction points at, leaving nothing to ride. The
first version of this rule "repaired" that by riding the whole trail from the other end — which the user
ruled out (2026-07-27): *"Ich möchte nicht, dass er automatisch erkennt, dass er ihn rückwärts einplanen
soll. Das mache ich dann von Hand."* Their case was `Steinbergbahn I → Steinbergbahn II → Asitz-Trail`,
where the whole Asitz-Trail lit up: the mountain station is **298 m from the trail's end** and 1600 m from
its start, so the sole candidate lands on the last point (and its 300 m gap is past
`JUNCTION_MAX_GAP_M`, i.e. it is the "no candidate close enough" fallback — the junction row shows it in
rust).

So there is no fallback at all now: `lo === hi` yields a zero-length stretch, marked `r.empty`. The row
shows `∅ 0.00 / 1.53 km` and the map draws **no glow** for it (the user: *"Müsste ja eigentlich gar nix gelb
leuchten, oder?"*) — only its numbered dot, hollow instead of solid green, so the element stays locatable.
🔄 then gives the backwards option by explicit choice (1.53 km, flagged ↑) and ⇔ the whole trail in its own
direction.

One knock-on: `ScheeLeitn Line → Wurzel-Trail` is now empty for the ScheeLeitn too (it joins the Wurzel at
its own index 0), where it used to report 1.70 km ridden backwards. That sequence really is geometrically
backwards — `Wurzel-Trail → ScheeLeitn Line` resolves cleanly — and it is better seen than silently
smoothed over.

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
