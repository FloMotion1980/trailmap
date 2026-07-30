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
- **F2 Streuböden II** — no bike transport (F1 carries bikes to the middle station only).
  Note saalbach.com's own combined overview row says "F1+F2 … yes"; the more specific Fieberbrunn
  source and OSM both say F2 does not. The specific source was followed — flag for the user.

**Temporary closures are deliberately NOT modelled.** `D1 Reiterkogelbahn` is included as a normal bike
lift even though it is being rebuilt for summer 2026 and isn't running: it is a permanent part of the
resort and will be back. A per-lift `closed`/`note` pair was built and then dropped the same day, per the
user — **nothing in this app synchronises lift operating status, so a hardcoded flag would silently rot
while looking authoritative.** The `lifts` data therefore states only the stable property "this lift
carries bikes in summer". (OSM's "Reiterkogelbahn II" is skipped: a 2-point, ref-less
`aerialway=construction` placeholder for the new section, not usable geometry.)

## Rendering — mask the base map's own line, then draw our symbol on it

**Current (2026-07-26, third and final iteration — the user's own design.)** A lift is two stacked
polylines:

1. **MASK** — an opaque thin grey band (`LIFT_MASK_COLOR #cfcfcf`, `LIFT_MASK_WEIGHT 7`) that *covers*
   the base map's own aerialway line, tick marks included.
2. **SYMBOL** — black, and drawn as **two** strokes rather than one dash-dot stroke: a hairline
   (`LIFT_HAIRLINE_WEIGHT 1.1`, solid) plus fat dots on top (`LIFT_DOT_WEIGHT 4.5`,
   `LIFT_DOT_DASH "1,13"`, round line cap). A single dashed stroke can only have one width, so "fat dots
   with a very fine line between them" — which is what the user asked for, matching OSM's own aerialway
   look — is impossible that way. A ~1px dash with a round cap renders as a dot, and because Leaflet
   applies `dashArray` in **screen** pixels the dot spacing stays constant at every zoom: zoom in and you
   get more dots, not longer gaps. No zoom handler needed.

Both live in the `LIFT_BAND_PANE` (z-index 350, between `tilePane` 200 and `overlayPane` 400), so they
sit above the tiles but below the trails.

**Why masking rather than coexisting.** The OSM/OpenTopoMap tiles draw every aerialway themselves, and
since our data comes from the same OSM ways the two land *exactly* on top of each other. Two earlier
attempts tried to live with that: a thin dotted line (mushed together with the tile's ticks — both became
unreadable) and then a wide translucent band meant to let the tile's line show through (readable, but see
below). Covering the tile's line and drawing our own symbol on it ends the conflict and loses nothing —
our symbol says the same thing plus "this one carries bikes".

### The mask is why solo cannot DIM a lift — it has to remove it (2026-07-30)

Solo mode dims trails to 15% opacity. Applying the same to a lift was the first attempt (2026-07-26,
`LIFT_DIM_OPACITY` / `baselineLiftOpacity()` / `applyLiftSoloStyles()`) and it silently did the opposite of
what it looked like in the code. Fading the mask **uncovers the tile's own aerialway line underneath**, and
our opacity cannot reach that — it is painted into the tile. A "dimmed" lift therefore came out looking like
an ordinary OSM lift at full strength, which is why the user reported solo as having no effect on lifts at
all, four days after the dimming had supposedly been implemented.

Lifts are therefore **removed from the map** in solo mode, not dimmed. That trio of functions is gone, and
the decision now lives in exactly one place, `applyLiftVisibility()`, which applies filters and solo
together — so there is no second code path that could disagree with it. Two rules inside it:

- **A soloed Tour keeps the lifts it rides** (`liftHiddenBySolo()` checks `TRAIL_SEGMENTS` for the soloed
  trail). They are part of that route, not competing clutter, and the Tour draws its own lift stretches
  anyway.
- **Only a filter may close the open lift's info panel, never solo.** `closeInfoPanelAndDeselect()` calls
  `clearSolo()`, which re-enters `applyLiftVisibility()` — closing the panel from the solo branch would
  recurse and then continue removing layers for a lift that had just become visible again. It cannot happen
  anyway (`showLiftInfo` drops any solo that isn't this lift's own), but the guard says so explicitly.

Lifts are soloable themselves since the same day. There is **one** solo state (`soloId`), holding a trail id
or a lift id, rather than a lift-specific copy of the mechanism: a soloed lift matches no entry in `lineLayers`,
so `applySolo`'s existing "everything else" branch dims every trail with no change needed. The button in
the lift panel carries `data-lift-id` — the same split the locate button already used — and
`syncSelectedCardSoloBtn()` walks both registries.

### The sidebar's own "Lifte" section (2026-07-30)

Lifts get a section of their own rather than rows in the trail list, and the 🚡 switch moved into it: a
lift has no difficulty, no category and no length, so it shares none of the Filter section's axes, and that
one switch is its entire filter. Deliberately *not* a mirror of the Trails section — no difficulty chips, no
count in the `x/y sichtbar` line (that counts rideable trails). Placed **above** Trails and collapsed by
default: it is short, and below a 250-trail list nobody would find it.

Cards carry `class="trail-card lift-card"` so every existing `.trail-card` rule applies — hover, `.selected`,
and the `.trail-card.selected .card-solo-btn` reveal — with no second set of styles. Two things they share
with trail cards by design: clicking one in builder mode routes through `builderTryAdd("lift", id)` (the
builder's hint has always promised "auf der Karte **oder in der Liste**"), and `selectLiftCard()` reuses the
trail list's own `selectedCard` variable, since a trail and a lift are never selected at the same time.
List membership follows the **filters only**, not solo — a lift list that lost its rows during solo would
make solo impossible to undo from the list.

### A Tour draws its own lift stretch, and is style-exempt there — `line` vs `styleTarget`

A Tour draws its lift stretch itself, with the same two strokes, exactly as it draws a component-trail
stretch (per the user: "Ich will Lifte wie Trails"). So the Tour's line is continuous and a lift looks
identical everywhere.

**The constraint to understand before changing any of this.** A Tour renders its segments as members of
one `L.featureGroup`, and every existing call site styles the whole Tour through it — `setHover`,
`applySolo`, `clearSolo`, `resetAllHoverStyles` — with `setStyle({weight, opacity})`. Colour and
`dashArray` survive those calls; **width and opacity do not**. A hairline-plus-fat-dots symbol is a
*width* contrast, so passing it through the group would flatten both strokes to the same width and destroy
the look (this is also why the earlier translucent band could never be a group member).

The fix is two handles per trail, both stored in `lineLayers[id]`:

| handle | contains | used for |
|---|---|---|
| `line` | **every** segment | add/remove, `bringToFront` — the lifecycle |
| `styleTarget` | only the **non-lift** segments | every `setStyle` call |

For a trail without segments, `styleTarget === line`. All five `setStyle` call sites go through
`styleTarget`; verified afterwards that a normal trail still behaves exactly as before (hover 3.5→6.5 and
back, solo 0.85→0.15 with the soloed one at 0.9, and back).

**Deliberate consequence:** a Tour's lift stretch does not dim or thicken with the Tour. It stays as it is
— which also means the Tour never has a gap there, unlike the earlier "band only, no line in the Tour"
version. Hovering the stretch itself still gives feedback: its own dots grow.

The grey mask is not duplicated per Tour — it belongs to the lift object, and render() keeps that object
visible wherever a visible Tour rides it, so the mask is already under the Tour's stretch.

Hover on a lift widens the mask slightly and thickens the symbol to `HOVER_WEIGHT`. The selection outline
is opaque again (a yellow rim around the mask) — there is nothing underneath left to preserve now that the
mask deliberately covers the tile's line.

**Note on the black:** `schwarz` is also a difficulty colour, so a lift's symbol and a black-rated trail
share a hue. The dash-dot pattern plus the grey casing are what tell them apart. This also means the
elevation chart paints a Tour's lift stretch in near-black, close to a `schwarz` stretch — flagged rather
than solved.

## Superseded: the translucent highlight band

**Current (2026-07-26, second iteration).** A standalone lift is drawn as one **wide translucent band**
(`LIFT_BAND_WEIGHT` 11, `LIFT_BAND_OPACITY` 0.38, round caps, no dash), plus the usual invisible wide
hit-line so it stays tappable on touch.

Why a band: the **OSM/OpenTopoMap base tiles already draw every aerialway themselves** — a dark grey
line with perpendicular ticks. Since our data comes from the same OSM ways, the two land *exactly* on top
of each other, and a line of our own just mushes together with the tile's, making both harder to read
(the user hit this immediately: "dann liegen der OSM Lift und unsere Liftlinie übereinander"). A band
sidesteps the competition instead of fighting it: the base map's crisp line shows **through** the
translucent band, which then only has to say "this one carries bikes". Same idiom the app already uses
for its selection highlight — a wider line behind, not a recolour.

Two implementation notes:
- **"Behind" is achieved by transparency, not stacking.** Leaflet's `tilePane` (z 200) always sits below
  every vector layer, so the band is technically *above* the tile image; it just lets it through.
- The band **does** need to sit below the trails, or it would tint every trail crossing it. It gets its
  own pane, `LIFT_BAND_PANE` at z-index **350** — between `tilePane` (200) and `overlayPane` (400) —
  passed to the polyline via Leaflet's `pane` option. The hit-line and station markers stay in the
  default panes, so they remain on top and clickable.

Hover widens the band and raises its opacity a little, but deliberately not to full opacity — it must
keep letting the base map's own lift line through.

**A Tour's own lift stretches still use the dotted style** (`LIFT_DOT_WEIGHT` 4.5 +
`LIFT_DOT_DASH "1,11"` + round cap), not the band: inside a tour line the surrounding segments give
enough context, and the stretch has to read as part of a continuous route. Unify later if it looks
inconsistent in practice.

### The earlier dotted-line version, and the trick worth remembering

The first iteration copied OSM's own look — a thin line with evenly spaced dots whose **spacing stays
constant on screen** (zoom in, get more dots). That was replaced by the band for the overlap reason
above, but the technique is worth keeping in mind, and is still used for the tour segments:

SVG `stroke-dasharray` is applied by Leaflet in **screen pixels** (the overlay pane re-projects paths on
zoom but never rescales stroke attributes — the same reason a connector's `"6,6"` dash looks identical at
every zoom). A very short dash drawn with a **round line cap renders as a dot**, so `dashArray: "1,11"`
+ `lineCap: "round"` gives dots 12 screen-px apart at any zoom — no zoom handler, no marker
recomputation.

**Known trade-off of the band:** on the **satellite** base layer the map draws no aerialways at all, so
there is no crisp line for the band to sit under and it reads as a fairly faint violet stripe on dark
forest. Street and relief both draw lifts, so only satellite is affected. If that becomes a problem,
raise the opacity or add a thin crisp core line back.

**Station markers follow the trail convention exactly** (changed 2026-07-26 on the user's request, after
a first version drew them permanently as hollow violet dots): green at the valley station, red at the
top station, and **only while that lift is the selected one** — the same show-on-selection rule as a
trail's Start/Ziel dots, via `showLiftEndpoints`/`hideLiftEndpoints`/`hideAllLiftEndpoints` mirroring
`showEndpoints`/`hideEndpoints`. Because `coords` is always stored bottom-first, `coords[0]` is the
valley station, so no per-lift direction check is needed. Tooltips are "Talstation"/"Bergstation".
They are hidden on: selecting a different lift, selecting any trail (`showTrailInfo`), closing the
panel, clicking empty map (`closeInfoPanelAndDeselect`), a filter hiding that lift, and teardown.
`render()` deliberately does **not** add them back when a lift becomes visible again — visibility of the
line and selection of the lift are separate things.

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

## Anchor the OSM name pattern — "longest match wins" picks the wrong cable

Learned in Bike Kingdom (2026-07-29), where `ref` tags do not exist at all and the join has to be by name.
A loose pattern plus a "take the longest hit" tiebreak silently chose a **T-bar** over the gondola it was
meant to find: OSM spells the Chur gondola `Känzeli - Bramb**ü**esch` (no r), so `Brambr[üu]esch` missed it
and matched `Brambrüesch - Hühnerköpfe` (1429 m) instead of the right way (1319 m). Three more patterns had
the same trap waiting — `Urden` also matches the Sesselbahn *Urdenfürggli*, `Hörnli` the Sesselbahn *Hörnli*
next to the Hörnli-**Express**, `Tschuggen` two lifts that are not Weisshorn Speed.

So: anchor every pattern (`^Urdenbahn$`), spell the local variant into it (`^K[äa]nzeli - Bramb`), and make
**more than one hit an error rather than a choice**. A wrong cable looks entirely plausible on the map — it
starts at the right station — which is why this has to fail loudly instead of resolving itself.

Also worth knowing: this is the region where OSM's own `aerialway:bicycle` tag happened to be *right*
(`=summer` on exactly the twelve bike lifts, nothing on Pradaschier, which the operator lists under "Kein
Biketransport"). That is a coincidence, not a licence to start trusting the tag — Saalbach had it wrong in
both directions. Read it as a cross-check on the operator research, never as the source.

## Adding lifts to another region

1. Research the operator's summer lift list: which lifts run, and which carry bikes. Note the official
   lift codes.
2. Fetch `way["aerialway"]` from Overpass for that region's bbox (several small bboxes — one big one
   times out) and join on `ref` == the official code, or on an **anchored** name pattern where the resort
   publishes no codes (see the section above before writing one).
3. Backfill `baseEle`/`topEle` for the two endpoints (OpenTopoData `eudem25m`), store `coords`
   bottom-first.
4. Write the `lifts` array into `regions/<group>.json`. No app code changes needed — activation,
   teardown, the filter and persistence all iterate the data.
5. Optionally, split that region's tour connectors to tag lift rides (see above).
