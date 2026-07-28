# Tourenbuilder

Added 2026-07-26. A map mode for assembling a route by clicking trails and lifts in ride order.

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
`.map-wrap`) and the switch is **one button in the header** (`#builderModeBtn`). The sidebar has no builder
section at all any more.

The user's problem: on a phone the sidebar is a full-height drawer behind an opaque backdrop
(`#sidebarBackdrop`, z-index 2400), so while the list was visible the map was unreachable — *"In der Sidebar
ist es schwer die Trails anzuklicken auf der Karte, wenn man am handy arbeitet."* Their own follow-up
question settled the design: *"Ist das Bottom Sheet ein eigenes GUI element zusätzlich zur Sidebar?"* No —
two copies of the same list would mean two sets of handlers and inevitable drift, so the list moved out of
the sidebar rather than being duplicated. They also asked for desktop and mobile to stay similar, which is
what makes a single element workable at all.

`renderBuilder()` and `drawBuilderHighlight()` needed **no changes**: they address `#builderList` and
`#builderTotals` by id, and those ids just moved.

- **One width rule for phone and small desktop**: `min(100% - margins, 420px)`, anchored bottom-left. On a
  phone that *is* full width; on a narrow desktop window it is a 420px panel that clears the info panel
  (top right, 280px) and the locate button (bottom right) with no per-platform case.
- **From 1024px with a fine pointer it becomes a full-height column on the right** (user, 2026-07-27), 360px
  wide. Same element and markup — only the geometry changes, so no JS knows about it. Collapsed, the column
  shrinks back to its handle rather than staying a full-height empty strip. Two things have to step aside
  for it, both keyed on `html.has-builder-sheet`: `#infoPanel`, which lives at that exact corner, and
  Leaflet's **attribution**, which sits bottom right and has to stay readable — it gets
  `margin-right: 360px`.
- **No backdrop** — the entire point. Taps reach the map underneath. z-index 1600: above the map's floating
  controls, below the drawer (2500) and its backdrop (2400), so opening the drawer still covers it.
- **Collapsed it is just its handle** (~34px) showing `Tourenbuilder · 3 · 7.38 km`. State persisted as
  `builderSheetOpen` in the same `localStorage` key.
- **The switch is the header button**, and it is the *only* one. It started as a sidebar switch, then also
  got a round 🧭 button on the map, and the user rejected both placements: the sidebar hides a map-mode
  switch behind two taps, and the map corner already holds the locate button and Leaflet's attribution. The
  header is the only element that looks the same in both layouts, needs no drawer, and covers no map. Both
  earlier controls were **removed**, not kept alongside — one state with three owners is how they drift
  apart. Everything routes through `setBuilderMode(on)`, which also closes the drawer when switching on.
- **The title is the mode indicator**: the `<h1>` reads "Trailbuilder" while the mode is on and "Trailmap"
  otherwise (the user's own idea). It still scrolls the sidebar to the top; only its text changes.
- On mobile the header switches to `flex-wrap: nowrap` with `min-width: 0` on `#regionsBtn`, so the three
  items stay on one line and the region chip takes the squeeze via its existing ellipsis. Without this,
  "Trailbuilder" — wider than "Trailmap" — wrapped the header onto a second line and shoved the map down
  every time the mode was switched on. `min-width: 0` is the part that does the work: a flex item's
  automatic minimum is its min-content width, which `white-space: nowrap` text otherwise refuses to go
  below.
- **The sheet carries its own ✕**. Not decoration: on a phone the sheet is full width at z-index 1600 and
  `#builderBtn` sits at 1000, so the map button is *behind* the sheet and could not switch the mode back
  off. `#builderSheetHandle` is therefore a `div` (a button inside a button is invalid HTML) whose click
  handler bails on `e.target.closest("#builderSheetOff")`.
- **Mobile only**, while the sheet is visible: `#locateBtn` moves to the top right (free there — drawer
  toggle is top left, `#liveStatus` top centre), via `html.has-builder-sheet` — the same technique the app
  already uses for `landscape-compact` — and with `!important` to beat the existing `html.is-standalone`
  override.
- **The glow and its dots are drawn only while the mode is on.** They used to stay, which was harmless when
  the list lived in the sidebar and was always there to explain them, but the sheet disappears with the
  mode and a glowing numbered chain with no list beside it explains nothing. `builderItems` is untouched, so
  switching back on restores the whole chain.

## How it works

**State.** `builderMode` (bool) and `builderItems` (`[{kind:"trail"|"lift", id, reversed}]`), persisted
under its own `localStorage` key `trailmap-builder-v1` — deliberately separate from the filter state, since
it is a work-in-progress document rather than a view preference.

`boot()` splits the two halves of bringing it back, and the order matters in both directions:

- **`restoreBuilder()` before `render()`** — `render()` hides Tours while builder mode is on, so restoring
  the state afterwards left a reloaded page in builder mode with the Tours still showing (user, 2026-07-27).
- **`renderBuilder()` after `render()`**, and after the regions are loaded — a row's name and length resolve
  against `lineTrails`/`LIFTS`, so doing it earlier renders a list of bare ids.

## Long lists on a phone (2026-07-28)

Three fixes for the same situation — more elements than the sheet is tall:

**A new element scrolls itself into view and flashes once.** Elements are appended, so once the list scrolls,
a new one lands below the fold: you tap a trail on the map and nothing visibly happens. `builderScrollToNewest()`
scrolls the container (`scrollTo` on `#builderSheetBody`, *not* `scrollIntoView` on the row — that also scrolls
every ancestor, which drags the page/map about when the sheet sits near the viewport edge), and the row gets a
one-shot `is-new` class for the flash. `builderNewIdx` is set just before the render and cleared inside it, or
every later render would replay the animation on that row. The flash is a **background**, not a ring:
`.builder-row` has `overflow:hidden` for the swipe-delete hint, which would clip a box-shadow or outline.

**Dragging to the list's edge auto-scrolls.** `.bi-drag` carries `touch-action:none`, so the browser will not
scroll for us — a long list simply could not be reordered past the visible area. A `requestAnimationFrame`
ticker does it, not the `pointermove` handler, because a finger resting at the edge fires no events at all;
speed ramps up across a 30px zone so it neither crawls nor overshoots.

Two traps in that, both hit while building it:

- **Scrolling invalidates the once-measured geometry.** Rather than re-measuring (which would let the shifted
  rows feed back into the target calculation — the flicker this design exists to avoid), everything works in
  the coordinate frame of the drag's *start*, and `scrollDelta` converts the current pointer position back
  into it. The dragged row's own offset includes that delta too, which is what keeps it under the finger while
  the list slides beneath.
- **A CSS transform extends its scroll container's scrollable overflow area**, so the naive version ran away:
  scrolling grows the drag offset → pushes the transformed row further down → grows `scrollHeight` → allows
  more scrolling. Held at the bottom edge it reached `scrollTop` 825, then 1133, on a list whose real maximum
  is 275, and snapped back only on release. Fixed by capturing the true maximum at `pointerdown`, while no row
  carries a transform yet, and clamping to it. The same effect is visible harmlessly in `builderRowIn`'s 7px
  slide, which briefly reports a maximum of 346 instead of 275 before settling.

**The scrollbar shows only while the list moves** (touch layouts only; the user asked for the permanent grey
bar to go). The second of the two options they offered, because it keeps the one cue that there is more list
below. The thumb is painted transparent rather than the bar removed — `display:none` or a width change would
alter the content width mid-scroll and reflow the rows under the finger. `.is-scrolling` is toggled in JS with
a 700ms idle timer, since CSS has no such state; the timer outlasts a flick's inertia so the bar does not blink
out mid-glide.

**Related simplification, same day:** `#locateBtn` now sits **top right on every layout**. It used to be
bottom right and get pushed to the top only while the builder sheet was open; the user saw that and asked for
it permanently — *"Die Stelle ist gut. Mach ihn immer dahin. Positiv. Wir sparen uns Sonderlogik"*. It did:
four positioning rules collapsed into one, including an `!important` that existed only to beat another rule.
Verified free of collisions in the one layout where `#infoPanel` is also top right (`landscape-compact`): the
button ends at y=117 and the panel starts at y=125, both inside `.map-wrap`.

## Regression cases

**`tools/builder_testcases.js` — paste it into the browser console with the `bikecircus` region active and
Tourenbuilder mode on.** 19 cases, 97 checks, all green as of 2026-07-28. Run it at a phone viewport: the last
three cases cover the touch-layout behaviour and one of them skips itself on a desktop layout. Every rule described below was
derived from one concrete ride the user tried, and each of them broke an earlier rule when it landed (three
separate direction bugs in two days), so the cases *are* those rides, with their real lengths and index
ranges. Run it after touching `builderResolve`, `junctionCandidates`, the row rendering or the drag handler.

It drives the real UI rather than calling the resolver directly, because `builderItems`, `TRAIL_GEO` and
`lineTrails` are `let`/`const` inside the app's top-level `try{}` and are therefore unreachable from a
separately-evaluated script — only the function declarations leak to the global scope. That is also why it
checks index ranges and not just lengths: "the same 2.38 km measured from the wrong end" is exactly the bug
class this feature keeps producing, and a length alone would not catch it.

The file's header lists two mutations and the failures they must produce, so its teeth can be re-verified
cheaply. Also worth knowing what one of those mutations revealed: removing the entry-side junction check
brings back **17** empty stretches across the region, not just the one pair the user reported.

## Row anatomy and gestures (2026-07-27)

A row is a shell, not the visible box:

```
#builderList
├ .builder-row        positioning shell, overflow:hidden, carries the 🗑 delete hint in ::before
│ └ .bi-body          the visible box (border, background) -- this is what slides on a swipe
│   └ .bi-main        ⠿ handle · number · name · [∅] · km · →/← · ✕
└ .builder-connector   iConnect for the junction to the NEXT row -- a sibling, not a child
```

`.builder-connector` is a sibling of the rows on purpose: it annotates the *chain* rather than an element,
and its negative margins let it sit between the two boxes it talks about.

**Button icons carry state, not actions** (user, 2026-07-27): **→** / **←** is the direction, and pressing
the arrow flips it. The old `↺` after a reversed row's name is gone — the arrow says it, and saying it twice
cost width the name needed.

**The arrow shows YOUR choice (`reversed`), never a direction derived from the geometry.** This was tried
the other way for one iteration and the user ruled it out (2026-07-28): *"ich würde keine automatische
Rückwärtserkennung machen. Das sollte eine bewusste Entscheidung sein. Wenn der User Murks zusammenbaut ist
das halt so. Man könnte höchstens eine Warnung anzeigen."* Nothing is ever quietly rewritten.

### The direction wins over the junction (2026-07-28)

That principle was still being violated one level down, in the clipping itself. A junction pins *both* ends
of a stretch, and honouring both is what produced a backwards ride without anyone choosing it —
`Back-to-Black → X-Line → Sprinter` ran the X-Line 2.95 km **uphill**, and the arrow was then disabled
because both ends were fixed. The user, twice: *"dann fährt er die xline hoch"*, and *"Ich möchte nicht, dass
er automatisch erkennt, dass er ihn rückwärts einplanen soll. Das mache ich dann von Hand."*

So the clip is now **direction-first**. The entry junction is always honoured; the exit junction only if it
lies *ahead* of the entry along the direction the element is actually being ridden:

```js
const rev = !!item.reversed;
const ownStart = rev ? last : 0, ownEnd = rev ? 0 : last;
const ahead = (from, to) => (rev ? to < from : to > from);
const a = entry[i] !== null ? entry[i] : ownStart;
const b = (exit[i] !== null && ahead(a, exit[i])) ? exit[i] : ownEnd;
const skippedExit = exit[i] !== null && b !== exit[i];
```

A skipped exit is not silently absorbed: it **leaves a real gap** in the chain (the user's call — *"Trailrichtung
behalten, Lücke entsteht"*), which is honest in exactly the way the rest of this feature is. `dirFixed` is
gone with it, so the arrow is now always usable — and pressing it is what *closes* such a gap, since riding
the other way makes the far junction lie ahead again. Same case, verified against the real Saalbach data:

| | length | profile | gap |
|---|---|---|---|
| X-Line, direction kept | 2.38 km | 1412 → 990 m downhill | yes, exit skipped |
| X-Line, arrow pressed | 2.95 km | 1412 → 1826 m uphill | no |

The gap is reported as **one symbol in the row** — `.bi-gap` `⤳`, rust-coloured, with the full explanation in
its `title`. It replaced a full-width `.builder-warning` strip below the row, at the user's request (*"Nur
ein Symbol in der Zeile"*), which also keeps the row height unchanged. `uphill`-flagged trails are exempt
from the whole notion; for those a climb is the point.

Turning the offending iConnect **off** remains the other way out, and is still the tool against "Murks":
the X-Line becomes 1.31 km and the tour's climb drops from 686 m to 258 m.

Two touch details that go with them:

- **Rows stay strictly one line on a phone.** Wrapping the tail onto a second line was tried and rejected
  outright -- *"Ich wollte auf keinen Fall dass das Listenelement größer wird. Wir sind auf dem Handy und
  haben eh wenig platz"* (2026-07-28). It also turned out to be unnecessary: once the 🏁 button was absorbed
  into iConnect, one button left the row and the name fits again. Measured at 375px on the worst case
  (a long name plus the ∅ marker plus a clipped "0.00 / 5.44 km"): rows are 52px, the name needs 119px and
  gets 119px, nothing truncated. If a future addition squeezes it again, take the width from around the name
  -- not from the row's height.
- **Pressing any of a row's buttons also marks that element**, on touch layouts only. Without it you would
  change a row on a phone without ever seeing which stretch on the map you changed; on a mouse, hover
  already does it and a lasting mark would outstay its welcome.
- **No grey block under a pressed button.** On a touch screen `:hover` sticks after a tap until you tap
  something else, so the hover rule now lives in `@media (hover: hover)`, the tap highlight is cleared, and
  `:focus` drops its background while `:focus-visible` keeps a ring for keyboard use. A pressed-in toggle
  (🏁 `.on`) uses the accent colour instead of grey, so a state cannot be mistaken for that artefact.

**iConnect** — the user's name for the junction, short for intelligent connector — is **one control per
junction, drawn between the two rows it belongs to** (`.builder-connector`, a sibling of the rows in
`#builderList`), straddling both boxes via negative margins with a short vertical stub to the left.

It took three placements to get there, and the two rejected ones are worth recording because each looked
right until it was used:

1. Its own strip between the rows — read as detached from everything.
2. Inside one element's box. But a junction clips *both* sides, so whichever box you pick misattributes the
   other half. The user hit it from both ends: *"das iConnect steht unten bei 2 … es bezieht sich auf den
   Trail obendrüber"*, and in the mirrored case (lift → trail) it sat on the **lift**, which is never
   clipped at all — the control changed a length two rows away and none of its own.
3. Between the rows, touching both. Nothing left to misattribute.

**It also absorbed the "ride the whole trail" flag**, which is the user's own insight: *"Trail ganz fahren
ist eigentlich iConnect ausschalten."* One step further than they put it, though — turning a junction off
unclips **both** neighbours, so "ridden whole" is not a property of a trail but the off state of the
junctions touching it. The 🏁 button is gone; the connector cycles candidate 1 … n, then **off**, then back
to the first.

Consequences of moving the state from the element to the pair:

- Stored on the **earlier** element as `connectAlt` / `connectOff`, describing the junction to what comes
  next. `builderJunctionKey()` therefore looks *forward* now, and `full` no longer exists.
- Migration in `restoreBuilder()` for tours saved before this: `junctionAlt` on element i described junction
  i-1 → i, so it moves to i-1 as `connectAlt`; `full` on element i becomes `connectOff` on the junctions on
  **both** sides of it. Without it a saved tour would silently come back a different shape.
- A junction between two lifts clips nothing, so it gets no control (`j.clips`).
- Export field renamed `junction` → `iConnect`, and carries `{off: true}` for the off state.

**Dragging replaced ↑/↓ entirely** and, on a touch screen, **a right swipe replaced ✕** — both because
"auf dem Handy sind die Knöpfe für hoch und runter bzw. löschen viel zu klein". With four buttons down to
two, the survivors get real 38×38px targets on mobile. Plain pointer events, since HTML5 drag-and-drop does
not work on mobile Safari at all.

- **The axis split is left to the browser** via `touch-action`: `pan-y` on `.bi-body` means a vertical drag
  scrolls the sheet (we get a `pointercancel`) while a horizontal one arrives as `pointermove`; `none` on
  `.bi-drag` stops a vertical drag there from being stolen by that same scrolling. No manual guessing.
- **Drag**: row geometry is measured **once**, before anything moves — nothing here changes the layout, every
  row is only ever shifted by a `transform`, so the measurements stay valid for the whole gesture. Move/end
  listeners live on `window`, and `setPointerCapture` is wrapped in try/catch: it is an enhancement, and it
  throws outright for a pointer id the browser does not consider active.
- **The list reorders live**: the rows between the grab point and the destination step aside, so the opening
  gap *is* the drop indicator. A marker line on the destination row came first and the user found it hard to
  read. `.builder-row` gets a `transition: transform .16s` for that glide, and `.is-dragging` sets
  `transition: none` — the dragged row has to track the finger exactly. Measuring once is also what stops the
  shifted rows from feeding back into the target calculation and flickering.
- **How far a displaced row travels comes from the measured slot centres, not from `rowHeight + gap`.** That
  formula was wrong and had to go (2026-07-28): an iConnect pill sits between two rows and, even on its
  negative margins, still contributes ~5px of layout plus a second 4px gap. Real distance 46px against a
  computed 37px on desktop, and **71px against 56px on mobile** — the larger error on the one device where
  dragging is the *only* way to reorder. The visible symptom is mild (rows land short of the gap they open)
  but the drop threshold is off by the same amount, so short drags did nothing at all. `slotShift(from, to)
  = mids[to] - mids[from]` is exact per row, survives rows of unequal height, and cannot drift if the pill's
  metrics ever change.
- **The iConnect pills hide for the duration of a drag** (`#builderList.is-dragging .builder-connector`,
  user 2026-07-28). They sit between the rows on negative margins, so while the rows glide aside the pills
  would stay put and read as leftover garbage — and a pill labelled with a junction that is mid-reorder is
  meaningless anyway.
- **`#builderSheet` sets `touch-action: manipulation`** so a quick double-tap on a row does not zoom the page
  (user 2026-07-28). It goes on the sheet deliberately: `.bi-body`'s `pan-y` and `.bi-drag`'s `none` are more
  specific and still win, so the gesture split above is unaffected.
- **Swipe**: right only, deletes past `SWIPE_DELETE_PX` (96), snaps back below it. Any movement past
  `GESTURE_SLOP_PX` sets `data-gesture` on the row so the click that follows does not also toggle the row
  focus.
- Both reorder and delete clear `builderActiveIdx` — that index no longer points at what it did — and run
  `builderClearStaleAlts()`.

**A CSS trap this uncovered**: `.builder-row button` (specificity 0,1,1) beats `.bi-connect` (0,1,0), so the
generic row-button rules silently stripped iConnect's border, background, font size and padding — it
rendered as unstyled text apparently *outside* the box, which is exactly what it was supposed to be inside.
The button rules are therefore scoped to **`.bi-main button`**, which is where ⇔/🔄/✕ actually live.

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

### Cycling the candidates ("iConnect", 2026-07-27)

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
junction with whatever is in front of me". *(Superseded later the same week: it is now `connectAlt` on the
**earlier** element, once the control moved between the rows — see "iConnect" above. The staleness argument
below applies unchanged, only the direction it looks in flipped.)* It also means the value is nonsense as soon as that neighbour changes,
so every structural edit brackets itself in `builderPredecessorSnapshot()` /
`builderClearStaleAlts()`, which clears the alts of exactly the pairs the edit touched and leaves the rest
tuned. A lift's `reversed` is part of that key, since flipping a lift changes which station it contributes.

### Too far apart is OFF by default (2026-07-28)

`junctionCandidates` can never answer "there is no junction here": when nothing passes the 150 m filter it
still returns the single closest approach. That fallback was mine, justified as "never worse than the old
single answer" — and it was wrong. It is why chaining two trails that simply do not touch produced a
"junction" 1.6 km wide and clipped the second trail to start in its middle. The user found it on
`Hacklberg-Trail → Z-Line`: *"Ich hätte erwartet, dass bei Trails, die so weit weg voneinander sind, kein
iConnect greift."*

Measured over all 49 Saalbach trails, **the fallback fires for 2216 of 2352 ordered pairs — 94 %**, and in
796 of them it cut more than a kilometre away. The worst are trails in different sub-regions:

```
Streuböden Line -> X-Line        10393 m apart   clips 6.62 of 6.66 km away
Flying Gangster -> Steinberg Line  614 m apart   clips 7.13 of 8.11 km away
Hacklberg-Trail -> 12er Sky-Line  1632 m apart   clips 5.22 of 5.61 km away
```

So the 150 m threshold almost never has anything to filter — two trails that genuinely meet are the
exception in a park, where the lines run parallel down one mountain. The fallback therefore fires *precisely*
when the pair does not touch, i.e. exactly where a gap is what you want.

**The fallback is kept, but it is no longer the default:** too far apart means the junction starts **off**.
The user's call — *"zu weit weg, iconnect aus"* — and deliberately not "delete the fallback", because a wide
gap is sometimes a real long connector (Steinberg Line at 614 m), and cycling the candidate on is one tap.
Same principle as iConnect itself: offer the option, do not guess harder.

**The decisive argument is about the next feature, not about honesty.** Gaps are meant to be closed by real
connections later, and a connection has to run from A's end to **B's own start**. An entry landing in B's
middle would make the connector route into the middle of a trail while B's first kilometres silently vanish —
a gap that is already half-wrongly closed. Off-by-default yields exactly the geometry the connector step
needs: two whole trails and one clearly bounded gap.

Consequences:

- **`connectOff` is tri-state**: absent = the derived default, `true`/`false` = your explicit choice. A far
  junction has to be switchable *on*, and "on" used to be expressed by the flag's absence. `builderCycleConnect`
  therefore takes the effective `off` as a parameter (cycling has to start from the state you can see) and
  writes `connectOff = false` rather than deleting it, or turning one on would snap straight back to off.
- `builderClearStaleAlts` needs no change: it deletes both flags when the pair changes, so a new pair
  re-derives its own default. That is the wanted behaviour, not a leak.
- A saved tour containing such a junction comes back a different shape than it was left. The old shape is the
  wrong one, so this is a correction rather than a regression — but it is a visible one.
- **No `⤳` in the row for this.** At 94 % of pairs, nearly every row would carry a warning symbol; that is
  noise, not information. The pill between the rows already says it.
- `Steinbergbahn I → II → Asitz-Trail` now resolves as the full 1.53 km Asitz rather than the empty stretch
  documented further down — its junction is 300 m out, so it is off by default. Both outcomes are honest; this
  one is more useful.

### A junction is only used if BOTH sides can honour it (2026-07-28)

The exit side has been checked since earlier the same day; this is the mirror image on the entry side, and the
user found it on `Z-Line → 12er Sky-Line`. The two lines really do come within **108 m**, so the junction is
genuine and the too-far default correctly does not apply — but the candidate joins the **Z-Line's start to the
12er's end** (`Z-Line idx0 ↔ 12er idx199 of 199`), i.e. it describes the ride in the *other* order. Entering
the 12er at its own last point left nothing to ride: `∅ 0.00 / 5.61 km` and a hollow dot.

Worth noting how the user reached the question, because it shows what the UI was and was not telling them:
they saw the *whole Z-Line* highlighted and reasonably inferred there was no junction near its end — *"Der
Endpunkt der 12er ist doch deutlich mehr als 150m vom Endpunkt der zline weg"*. But the full Z-Line **was
itself the symptom**: its exit junction lay behind its direction and had been skipped, and the only sign of
that was the `⤳`. Their endpoint-to-endpoint intuition also does not match the search, which compares every
point pair — a trail's start pairing with another's end is exactly what makes `12er Sky-Line → Z-Line` work.
They agreed the search itself is right: *"Prinzipiell ist es ja richtig, alle Kreuzungen zu suchen."*

So an entry is honoured only if the terminus its direction points at still lies strictly ahead of it.
Otherwise the junction is unusable **in this order**, and *neither* side is clipped — dropping the exit too,
because clipping A to a point that connects to nothing is the half-wrongly-closed gap again. `junctionInfo`
carries `unmade`, the pill goes dashed while keeping its distance and `n/m` (cycling may find a usable
candidate), and the row shows `⤳` with a reason-specific tooltip (`gapReason` is `"exit"` or `"next"`).

Reversing the pair shows the junction was real all along: `12er Sky-Line → Z-Line` uses it, and needs no clip
at all, because it sits exactly at the 12er's end and the Z-Line's start.

**One consequence: `empty` / `∅` is now unreachable.** If the entry is used, `ownEnd` is strictly ahead of it,
so `a ≠ ownEnd`; and `b` is either `ownEnd` or an exit strictly ahead of `a`. Verified empirically as well —
all 2352 ordered trail pairs in Saalbach, with and without the junction forced on, produce no empty stretch
(17 pairs hit `unmade`, 30 hit a skipped exit). The flag, the badge and `.builder-num.is-empty` are kept as a
guard so a future rule change finds the honest marker already in place, but nothing reaches them today. The
Asitz-Trail case documented further down is one of the cases that moved: it now rides whole either way.

**Two different distances, and the pill must not mix them up.** The candidate's `dist` is how close the two
*lines* come — the gap you would still bridge if the junction is used. Once it is **off**, both neighbours ride
to their own termini, so the real gap is end-of-A to start-of-B (`gapOff`, via `facingTerminus()`), and that
can be far larger: `Steinbergbahn II → Asitz-Trail` is 300 m at the closest approach, because the lift arrives
near the trail's *end*, but **1609 m** from the arrival station to where you would actually start riding. The
off pill shows `gapOff`, the on pill shows `dist`, and the export carries both (`gapM` / `nearestM`). Showing
the closest approach next to the word "aus" would have been exactly the kind of quietly wrong number this
whole change exists to remove.

**UI:** the junction gets its own thin row *between* the two element rows, because that is where it sits:
`iConnect · 84 m · 1/3 ⟳`. The gap doubles as a quality signal — a few metres means the lines really do
meet there, a hundred-plus means the guess is probably wrong and worth cycling. The **whole row** is the
control, not the ⟳ glyph, which at 19×16 px is not a hittable target on a phone.

**A lift contributes only one point to the junction search, not its whole cable** — its boarding station
when it is being joined, its arrival station when it is being left. This matters: the user's own example is
leaving the X-Line for the Schattberg Sprinter, and you quit the trail where the *valley station* is, not
where the cable happens to pass overhead. Lifts themselves are never clipped; you ride a cable end to end.

~~Direction falls out of the clip (entry index vs exit index).~~ **Reversed 2026-07-28**: the direction is
the input now and the clip follows it. See "The direction wins over the junction".

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
The arrow then gives the backwards option by explicit choice (1.53 km), and switching that iConnect off gives
the whole trail in its own direction.

Since a too-far junction is off by default (see above), this Asitz case no longer reaches `empty` at all —
its junction is 300 m out, so the trail simply rides whole. `empty` still happens for a *near* junction that
lands on the terminus the direction points at.

Note that `empty` is reachable only through the **entry** junction, which is the case above: the junction
pins the start, the direction points away from the rest of the trail, and nothing is left. A behind-you
**exit** junction no longer produces an empty stretch — since 2026-07-28 it is skipped and leaves a gap
instead. `ScheeLeitn Line → Wurzel-Trail` is the example that moved: it briefly resolved as empty, and now
rides the ScheeLeitn's own full 1.70 km with `⤳` marking the unmade connection (the Wurzel is joined at the
ScheeLeitn's index 0, i.e. behind it). That sequence really is geometrically backwards —
`Wurzel-Trail → ScheeLeitn Line` resolves cleanly — and it is better seen than silently smoothed over.

~~Some sequences genuinely force a climb … hence **`r.against`**, a rust ↑ in the row.~~ **Gone
2026-07-28**: no sequence can force a climb any more, so the flag had no case left to report. What replaced
it is `r.skippedExit` / `⤳`, which reports the gap that *not* forcing the climb leaves.

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

- ~~A trail clipped at **both** ends has no freedom left, so its 🔄 is `disabled`~~ — **superseded
  2026-07-28** (see "The direction wins over the junction"). Both ends can no longer be pinned against the
  direction of travel: the exit junction is skipped when it lies behind, leaving a gap, and the arrow stays
  usable. `r.dirFixed` no longer exists.
- An element with no junction at all (single-element tour, or both junctions off) reverses exactly as before.
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
   version: a straight link, drawn as a connector. Better: snap to nearby paths. The export already states
   each gap: an off junction carries `gapM` (end of one element to the start of the next — the length the
   connector has to cover) plus `tooFar` when that is *why* it is off, and an element whose exit junction was
   skipped carries `unconnected: true`. Since 2026-07-28 a too-far junction is off by default precisely so
   this step gets whole trails and clean gap endpoints instead of an entry point in the middle of a trail.
2. **Turn a built route into a real Tour.** Once gaps are closed, the assembled coordinate list can be
   concatenated and `len`/`up`/`down`/profile/`distStart`/`distEnd` derived from it — the same
   "derive-everything-from-the-assembled-geometry" rule that made the Challenge rebuild consistent by
   construction. Elevation still needs a DEM lookup, which cannot happen in the browser, so this either
   stays an offline step or needs an elevation source added.
3. **Drag to reorder** instead of the ↑/↓ buttons.
4. **Name the tour** and write it straight into a region JSON.
