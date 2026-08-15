# Changelog

A chronological, skimmable log of notable changes — "what happened and when", newest first. For the
*why* behind any entry (design reasoning, rejected alternatives, exact bugs), check:

- **`CLAUDE.md`** — the living design doc. Every non-trivial decision here has a longer, dated writeup
  there, usually in the section for the feature it touches.
- **`tests/MUTATIONS.md`** — for a bugfix specifically, records the mutation that proves the fix's test
  actually catches the bug.
- **`docs/*.md`** — standalone writeups for bigger features (Tourenbuilder, lifts, Trailrunden, etc).

This file starts 2026-08-13 — it is not a full backfill of the project's history, which lives in
`git log`. Add a line here whenever you'd want to tell a teammate "here's what changed" without them
reading the diff; skip routine one-line data fixes (a single trail's difficulty, a name typo) unless
they're part of a larger entry.

**Any entry that adds/rebuilds trails, Tours or lifts must say where the data came from** — OSM Overpass,
an operator's own GPX/API, Trailforks (and which extraction method — the anonymous-polyline page source,
the `/widgets/trail/` embed, etc.), or sequential map-matching (`tools/gpx_map_match.py`) against an
existing region's trails/lifts. One clause is usually enough ("Trailforks' own encodedpath, harvested via
logged-in Chrome"); the full sourcing method, caveats and edge cases belong in the region's own build
script docstring or `CLAUDE.md`'s `Material/<region>/` bullet, not repeated here.

## 2026-08-16
- **Fixed: a difficulty/category/region/search filter that hid a trail left its halo casing glowing on
  Satellit/Relief** (reported live by the user). `render()`'s filter-driven hide branch only ever touched
  `layer.line`/`hitLine`/`startDot`/etc, never `layer.casing` — fine for a segmented Trailrunde (its
  casings are children of `layer.line` and go with it for free) but not for a plain trail, whose casing
  lives directly on `map` (same reason `destroyTrailLayer` has its own explicit removal for it). Fixed by
  adding the matching `map.removeLayer(layer.casing)` to the hide branch and a `syncHalo()` re-add to the
  show branch. New mutation-checked case in `tests/browser/palette.js`; see `tests/MUTATIONS.md`.
- **Basemap picker restructured: "Straße"/"Straße dezent"/"Straße hell" are now three peer options**
  (same osm tiles, three CSS filter levels — `brightness`/`saturate`/`contrast` on Leaflet's own tile
  pane, no tile-server involvement, works offline), not sub-options of one button as first built the
  same day. The old CARTO/Positron "Straße hell" basemap is kept (the user didn't want it removed after
  all) but renamed to **"Pastell"** so the two don't collide by name — `data-layer="carto"` is
  unchanged, so its own test coverage needed no changes beyond the visible label. **Default basemap on
  a first-ever visit is now "Straße dezent"**, not plain Straße. Persisted like the other filter
  toggles; general setting, not RIDE-only.
- **RIDE button emoji and the info-panel's own RIDE button.** Went 🚵 (mountain biker, "harder to
  recognize at a glance") → 🚴 (plain cyclist) → 🚲 (bicycle alone, no rider/hill) after the user found
  🚴 still rendered with a hill in the background on their phone's emoji font. A record/stop icon
  (⏺️/⏹️) was considered and rejected twice — once for the coloured background chip those render with
  on many platforms, once on principle ("solange wir nix aufnehmen ist das nicht das richtige", since
  nothing is actually being recorded). Also fixed: the info panel's own `.ride-btn` (in `.ip-btns`,
  alongside locate/solo/reverse/GPX) was visible on desktop too — RIDE only makes sense on a phone
  actually being ridden with, so it's now hidden by default and shown again only in the same
  touch-only media query `#locateCluster` already uses.
- **RIDE mode: bigger control buttons, and the halo's orange is now fully opaque.** `#mapControls`'s
  three cells grow 44px→64px (icon 20px→28px) while `html.ride-mode` is active — gloves/vibration on
  the bike, per the user's request — with the readout chip widened to match so the joined-corner
  design still lines up; unaffected outside RIDE. Separately, the focus halo's outer ring dropped its
  0.75 opacity to fully opaque: where a loop's own line runs close beside or crosses itself (a normal
  shape for a Trailrunde), two semi-transparent orange rings stacked and darkened toward red at the
  overlap, reading as an unrelated reddish smudge on the map.
- **RIDE focus halo: thicker orange ring, and gaps between segments now get bridged too.** After
  phone/live-map feedback: `RIDE_OUTER_WEIGHT` bumped 14→18px, and any real gap between two
  consecutive Trailrunde segments (see `tools/close_loop_gaps.py` for why these exist) is now bridged
  with a plain orange line during RIDE, so an un-closed tour still reads as one continuous line instead
  of visibly breaking apart — verified on "Tour 1 - Rodalben" (34 known gaps), which now shows one
  unbroken orange ring end to end.
- **Closed all 29 real segment-boundary gaps on Rodalben Felsentrails** via a new tool,
  `tools/close_loop_gaps.py` — tries reusing an existing connector from another tour, walking the OSM
  way the other side already follows, or Dijkstra shortest-path as a fallback, and keeps whichever
  produces the shortest real route (average factor 1.02, no detours). Added the same day: a
  three-layer RIDE focus halo (orange outer ring, light per-difficulty tint, existing core line) for
  whichever trail/tour is open during RIDE, so it stays legible in bright sun on any basemap. See
  `docs/backlog.md`'s Trailrunden-Lückenschließen section for a known gap in the tool itself (no OSM
  access-tag check yet — one junction's winning route follows a `vehicle=forestry`-restricted track)
  and the plan for the next round (other tours, OSM-mapping prioritised over Dijkstra, a "trim the
  trail" candidate, a two-sided intersection search).
- **Fixed two follow-up bugs from the infobox refinements above.** (1) The km/h number was still not
  exactly centred in portrait — the number+unit sat together in one flex box, and the unit's own width
  shifted that whole box (and the number inside it) off from the panel's true centre. `.ride-speed-stat`
  is now sized to the number alone (`inline-block`), with the unit positioned beside it via
  `position:absolute` so it adds no width to what gets centred; landscape's existing stacked layout
  (already correct, confirmed unaffected) needed an explicit `display:flex`/`position:static` override to
  survive the more specific portrait rule. (2) The RIDE look-ahead offset (position dot at ~1/3 up from
  the visible bottom) was computed against `.map-wrap`'s full height, so once the portrait info panel
  grew taller (bigger fonts/padding, same day) the fraction was measured against a container that's now
  partly covered by the panel — pushing the dot lower than intended. `applyRideMapOffset()` now subtracts
  the panel's own live rendered height from that reference height, and is also re-run whenever the panel's
  content (and therefore its height) changes — i.e. whenever a trail is focused/unfocused mid-ride, not
  just once on entering RIDE.
- **RIDE infobox: phone-tested refinements after the redesign.** Speed number is now genuinely centred
  (`#rideInfoBig` needed an explicit `width:100%`, or the flex column shrinks to its content and sits
  left-aligned even with `align-items:center` set); altitude's portrait badge and the gap above the
  trail row both grew per the user's sizing calls; in landscape the speed number grew, each stat's unit
  moved below its number instead of beside it, and the trail row is now genuinely pinned to the bottom
  of the column instead of trailing after the big numbers. Also fixed: the length/⬆️/⬇️ stats sat at
  visibly different heights on a real phone (iOS's own emoji font has different vertical metrics than
  plain digits) — switched from baseline to centre alignment, which sidesteps the font-metric mismatch
  instead of compensating for one specific emoji font.
- **RIDE infobox redesigned for sunlight readability**, after reviewing mockups (built with the
  `visualize` tool first, before touching app code) instead of iterating live: speed is now a single
  dominant, centred 80px (58px landscape) number in a plain heavy sans (Arial/Helvetica, not the app's
  decorative Copperplate); altitude is a smaller secondary badge (corner in portrait, below a divider in
  landscape) rather than an equal second number. The focused trail's name/length/Hm moved into one row
  and is now hidden outright with nothing focused — no dash placeholder, unlike speed/altitude which
  always show something.
- **RIDE mode: added a big live speed (km/h) and altitude (m) readout**, sitting above the existing
  trail name/length/Hm in `#rideInfoPanel` (not replacing it, per the user's own preference). Pulled
  straight from each GPS fix's own `coords.speed`/`coords.altitude`; shown as "–" rather than a
  misleading 0 whenever the current fix doesn't carry a usable value.

## 2026-08-15
- **Merged `docs/region-backlog.md` into a new general `docs/backlog.md`**, per the user's request for
  one cross-topic backlog instead of a new per-topic file each time. Regions moved in as their own
  section, unchanged; a new "RIDE-Modus" section holds the open follow-up ideas from the same day
  (infobox rework, a manual orientation toggle, a possible record/stop icon, a separate tracking
  concept, and the still-thin test coverage). `CLAUDE.md`'s own pointer updated to match.
- **Fixed: a two-finger pinch never showed the position button, even while visibly moving the tracked
  position off-centre.** A pinch is handled entirely by leaflet-rotate's own `TouchGestures`, a different
  code path from Leaflet core's drag handler, which only fires "dragstart". Confirmed from the vendored
  source that a pinch fires "zoomstart" instead — now also listened for (guarded so the very first GPS fix's
  own zoom-in doesn't falsely trigger it). Also removed the blue/filled highlight on the position button
  while detached, per the user's request — it now just appears, nothing more.
- **Merged the position button (📍) and the old separate re-centre button (◎) into one.** Both ultimately
  meant "put my position back where it belongs" (the user's own observation). `#mapControls` order is now
  RIDE, bearing, position (RIDE leads as the entry point into riding; position is last since it's the only
  conditional cell now — hidden while centred and following, shown otherwise, taking over ◎'s old "tap to
  reattach" job when detached). Traded away: the brief "tap 📍 during RIDE for the true screen centre"
  override added earlier the same day has no reachable button once centred, since the cell hides then —
  an accepted cost of not having two buttons for one job. Fixed two now-stale assumptions in
  `tests/browser/bearing.js` while updating it for the merge: `followMode`/`followDetached` were never
  actually reachable from a test script (a wrong assumption in an earlier edit that would have silently
  no-opped), and a separate, unrelated case had been waiting on a `.active` class that stopped being set on
  the position button back when RIDE took over triggering follow mode — its wait was quietly running out
  its full timeout every run.
- **RIDE mode, round two, after the first phone test: bottom info bar + a look-ahead position placement.**
  `#rideInfoPanel` now docks at the BOTTOM in portrait, flush with the real bottom edge (was top, and
  briefly left a gap above Leaflet's attribution strip before that too got fixed the same day) — modelled
  loosely on the Bosch eBike Flow app's own "Ride" screen (dark background, readouts at the bottom, top
  kept clear for what's ahead). More significantly: while riding, the user's position now sits about a
  third of the map's height up from the bottom (not dead centre), so more of the map ahead is visible,
  since travel direction is "up" once "Blickrichtung oben" is active. First attempt patched two of the
  vendored `leaflet-rotate.js`'s own internals (`_getNewPixelOrigin`/`_getPixelCenter`) — reverted the same
  day after the phone test showed the rotation pivot moving correctly while the position dot stayed at
  true dead centre regardless (the same disagreement the 2026-08-01 "dead centre" fix was originally for,
  just from different internal math). What shipped instead touches none of Leaflet's own centring/rotation
  code: `#map` itself is made taller than the visible window and shifted upward during RIDE
  (`applyRideMapOffset()`/`clearRideMapOffset()`), so Leaflet's own dead-centre placement — provably
  correct, since nothing about it changed — lands lower within the cropped, visible part. The locate
  button (📍) still recentres to the true screen centre on tap, even mid-ride. See `CLAUDE.md`'s RIDE
  section and the plan file referenced there for the full reasoning, including why the first attempt
  failed and how the replacement was verified.
- **RIDE mode, same-day follow-up: the position dot is now horizontally centred in landscape too.**
  `#rideInfoPanel` docks along the left edge in landscape, covering part of the map — the dot sitting at
  the full container's horizontal centre read as visibly off-centre in the space actually left uncovered.
  `applyRideMapOffset()` now also widens/shifts `#map` horizontally by an amount derived from the panel's
  own live-measured width, landing the dot exactly mid-way between the panel and the map's right edge
  (verified: 0px off target). No change in portrait, where the panel is a full-width bottom bar instead.
- **Added a RIDE mode, replacing the old hold-to-follow gesture on the locate button.** A new 🚵 button
  (in the map controls cluster, and in a trail's info panel) starts a full-screen riding view: header,
  sidebar and the info panel hide, GPS follow + auto "Blickrichtung oben" rotation start, and a focused
  trail is shown solo (dimmed rest of the map) with the yellow selection ring always suppressed,
  regardless of how the trail got selected. A focused trail cannot be deselected by tapping empty map
  space while riding, and exiting RIDE always rotates back to north. A new permanent readout
  (`#rideInfoPanel`, top in portrait / left edge in landscape) shows the focused trail's name/length/Hm
  while riding, and stays visible (reduced) with nothing focused as a placeholder for future tracking
  info. Reuses the existing `startFollowing`/`stopFollowing`/solo/rotation machinery wholesale — only the
  trigger and the full-screen chrome are new. See `CLAUDE.md`'s architecture section for the exact
  functions touched.
- **Connector back to plain dark grey everywhere, and the contrast halo widened from schwarz-only to
  every trail/connector/lift on Satellit and Relief.** Both tried live at the user's own initiative,
  neither designed up front. The connector (`#e08a00` at the start of the day) was reported as low-
  contrast in bright sun on Straße/Straße hell; the user asked for the original dark grey (`#5a5a5a`)
  back — and once a halo made every colour's own contrast case for a separate connector hue redundant, it
  went onto Satellit too, closing out a three-week round trip through orange (`CLAUDE.md` keeps the full
  history so nobody reinvents it). The halo itself widened the same day: white behind every diff colour
  first, narrowed a step further once the user found plain white "zu neutral" — gruen/blau/rot now get
  their own light tint, the diff colours themselves went darker to compensate, and the connector's halo
  is a light orange after a grey-with-white-halo connector was rejected outright ("sieht noch nicht gut
  aus", read as a map boundary rather than part of a Tour). The ring itself is narrower too
  (`HALO_WEIGHT_TRAIL` +1 instead of +2), now that it covers every trail instead of a schwarz minority.
- **Lifts get the same contrast band, for free — by turning ON a layer that already existed rather than
  building a new one.** The user's own observation: "wir haben ja die Linie für Straße, die bei den
  anderen Ansichten ausgeblendet ist" — a lift's own grey MASK polyline (7px, sitting behind the 1.1px
  hairline and 3.8px dots in the same pane, by build order) is structurally identical to a halo casing.
  `liftMaskOpacity` flipped from 0 to 1 on Satellit/Relief is the entire change; its colour went white
  first, then light violet (`#dab6f0`) once white was rejected ("weiß ist nicht das richtige für Lifte")
  — a lift needed to read as its own kind of thing, not as another trail with a halo. Lift hairline/dots
  moved to the same dark grey as the connector too, separately: light grey (`#d9d9d9`) nearly vanished
  inside the yellow selection outline once a lift was selected.
- **Relief got Satellit's entire configuration wholesale, closing a gap open since 2026-08-13.** Tried
  directly rather than designed from scratch, since the underlying problem — hue collision with
  OpenTopoMap's own green/orange, not darkness — is exactly what Satellit's halo already fixed for a
  different reason. Verdict after seeing it live: "besser als vorher, aber Relief ist einfach schwierig.
  Wir lassen es so" — an improvement, accepted as the ceiling for this basemap rather than a full fix.
  `tests/browser/palette.js` rewritten for the new final colours/values, mutation-checked (`tests/
  MUTATIONS.md`).
- **A Tour's segment hit areas moved into their own Leaflet pane (`tourSegHitPane`, z-index 405), which
  closes the segment-click bug structurally instead of by ordering discipline.** Clicking a Tour's stretch gave
  the plain trail's panel until the Tour had been selected once — because `lineTrails` order IS the map's
  z-order and any trail built after a Tour lays its invisible 22px hitLine over that Tour's per-segment areas.
  Two rounds of re-raising (at build time, then in `applySolo`) each held only at the moment they ran, and the
  user named why that can never be enough: "wenn man in der App Filter aktiviert und wieder deaktiviert, kann
  man in so einen Zustand ja immer kommen" — `render()` adds and removes layers on every filter change. A pane
  makes the question disappear. Verified live: 92 hit areas in the new pane, zero left in the overlay pane, and
  the pane is **empty while the Tours are hidden**, so the trails underneath stay clickable (the user's own
  follow-up requirement). Lifts were already at the bottom (`liftBandPane`, 350) including a Tour's own lift
  stretches; putting the visible Tour LINES above the trail lines as well is deliberately left for its own
  change, since four suites select trail geometry via `.leaflet-overlay-pane`.
- **The selected stretch of a Tour is now drawn bold, on touch and desktop alike** (user request). Done by
  raising that segment's own `_tmBaseWeight` rather than setting a width, which is what makes the emphasis
  survive hover, solo dimming and a repaint without any of those needing to know about it -- the same
  mechanism that gives a connector its thinner baseline. A lift stretch is never bolded: it is three strokes
  that are exempt from the group's styling on purpose. Also fixes two bugs the user found on the live region:
  a Tour riding the same trail twice always highlighted the FIRST occurrence (`selectedSegmentId` is a trail
  id, so `segs.find()` could not tell them apart -- Felsenwanderweg Rodalben rides "Felsenweg Süd" at km
  0.7-5.9 and again at 27.5-42.8), and a tapped trail stayed bold on a phone because `setHover(true)` lives
  in the click handler and a finger produces no `mouseout` to undo it.

- **Tried, and rejected same-day, a light basemap that also draws forest roads and trails** — the gap
  between "Straße hell" (light, but its paths are hairline-faint and gone above z14) and "Relief" (draws
  everything, at the price of contour clutter and hue collision with our own lines) is real, but no keyless
  candidate closed it well enough to keep. **"Wald"** (the HOT style via OpenStreetMap France — calm sage
  green, cream path dashes, no contour lines) shipped first, with `maxNativeZoom: 16` and `retryFailedTiles()`
  to work around the server answering **404 above z16** everywhere but the densest areas (not the host —
  CyclOSM on the same infrastructure serves z18) and throttling bursts. It looked right, but the user's own
  verdict on the blurry z17+ upscale, after living with it, was to drop it rather than keep it ("Schade, dass
  Wald nicht so weit reinzoomt … Wald kann auch wieder raus"). **`openstreetmap.de`**, tried next specifically
  because it reaches z19, lost on sight ("sehr ähnlich zu Straße"). **Thunderforest Outdoors** ("Outdoor")
  reaches z19 too but needs an API key — keyless tiles carry a diagonal "API Key Required" watermark,
  byte-identical with and without a `Referer` — and was removed hours before "Wald" itself was. CyclOSM
  (contour-heavy, trail-like tracks) and CARTO Voyager (paths as faint as Positron's) were ruled out the same
  way, by comparing real tiles rather than descriptions. All three basemap entries, `retryFailedTiles()` and
  the browser-suite case that covered them are gone again; the comparison and the rejection reasons are kept
  in `CLAUDE.md` so nobody re-tries the same three without a real fix for the zoom ceiling.
- **`tests/browser/palette.js` carried a line that could never go green** — `T.eq(label, <boolean>, <array>)`
  where it meant `T.ok`, ever since the Monte Corno case was written on 2026-08-13 (`ddec83e`). A
  permanently red line is worse than a missing check: it trains everyone to read past red. Same class of
  thing in `tests/browser/solo.js`, a duplicate `const tourCard` in one callback (from `4cc3989`) — a
  SyntaxError that took down the **whole bundle**, i.e. every `--changed` run after an index.html change.
- **Pfälzerwald reworked against Trailforks: 437 → 805 trails, and the Trailrunden now name three times as
  much of their own length.** Source: all 485 Trailforks trails inside the region's box, from Trailforks'
  own `encodedpath` via logged-in Chrome; the Trailrunden's `trailSegments` re-derived with
  `tools/gpx_map_match.py` against the merged trail set. 112 existing entries replaced where a Trailforks
  trail covers them, 273 kept (mostly OSM hiking-route fragments, which the user confirmed may stay), two
  new sub-regions for ground the region never covered (`haardt` 112, `bienwald` 13). The headline number is
  the share of each Tour's length that falls on a *named* trail: **13.3% → 19.7%**, 37 of 42 Tours better,
  3 unchanged, 2 worse. Felsenwanderweg Rodalben went 24.3% → **85.2%** once the user pointed out it simply
  *is* the Rodalber Felsenwanderweg, which Trailforks carries as "Felsenweg Nord/Süd". Tools:
  `pfaelzerwald_{report,containment,integrate,rederive_loops,finalize}.py`.
- **That 13.3% is the corrected baseline, and finding it mattered more than the gain.** The region's 616
  existing attributions turned out bimodal — half exactly on their trail, then a tail reaching 827 m away
  ("König-Albrecht-Wanderweg 1"). About a tenth claimed ground their named trail is nowhere near, inflating
  the old headline to 15.2%. `pfaelzerwald_report.py` now measures both, and raw == clean after the rework:
  the gain is not paid for with new noise.
- **A Tour's segment must carry its component trail's geometry, not a slice of the Tour's own line.** Built
  the wrong way round first, and the user reported all three consequences from the preview: doubled offset
  lines, clicks opening the trail instead of extending the Tour's panel, and the same ground stored twice.
  Donnersberg/Bike Kingdom/Laax have 100% of segments sitting 0.0 m from their trail; the slice version
  managed 56%. Fixed via `resolve_segments()`, and the Tour lines moved at most 5.7 m in the process.
- **`lineTrails` order IS the map's z-order** — appending the 480 harvested trails after the Tours put 483
  hitlines over every Tour's per-segment hit areas, so segment clicks went to the wrong layer. The live
  region has 3 trails after its last Tour and Bike Kingdom 0, which is why it never showed there. Tours are
  sorted last now, and `applySolo` additionally re-raises the soloed layer's own hit areas — dimming a line
  never touched its invisible 22px hitline, so **Donnersberg carries the same bug latently** and is fixed
  by that half too.
- **Harz difficulties now follow the OPERATOR, not Trailforks** — the user's standing rule ("immer die
  Schwierigkeit des Betreibers übernehmen"), which reverses for this region the Trailforks-throughout rule
  it was built to. All six operator pages re-checked: only St. Andreasberg, Trailpark Ilsenburg and Bodetal
  publish a grade at all, so Hahnenklee/Schulenberg/Braunlage necessarily stay on Trailforks. The
  three-step German scale maps onto the app's own labels (leicht → blau, mittel → rot, schwer → schwarz),
  and a two-step grade ("mittel / schwer") rounds **up**. Net effect: **7 St. Andreasberg trails
  re-coloured**, Ilsenburg's and Bodetal's grades already agreed. `OPERATOR_DIFF`/`resolve_diff` in
  `tools/build_harz.py` carry the mapping plus each trail's operator wording; five new cases in
  `tests/python/geomerge.py` (mutation-checked) pin the rule, one of them comparing the shipped
  `harz.json` against it for all 42 trails.
- **Harz's remaining gaps reviewed and closed as accepted, not open**: the four trails with no geometry
  anywhere (Bodetal `05 Schwarze Köhlerliesel`, Schulenberg `OnAir`, St. Andreasberg `7 Super Enduro` and
  `8 Kids Trail Harz`) are dropped for good — the user found no GPX for them either — and the two
  non-park trails (`Spiegelthaler-Trail`, `Bodetrail`) stay in deliberately. See `docs/region-backlog.md`.

## 2026-08-13

- **Per-basemap map colors, several rounds of live iteration.** Trail/connector/lift colors were tuned
  against OSM's own tiles and nearly disappeared on Satellit (schwarz trails, the grey lift mask). Ended
  at: brightened gruen/blau/rot on "Straße"; unchanged on "Straße hell"/"Relief"; brightened gruen/blau/rot
  + near-black schwarz + a white geometry halo behind schwarz specifically on "Satellit". Connector color
  is orange everywhere, but not the same orange (`#e08a00` on Straße/Straße hell/Relief, `#ffb300` bright
  amber on Satellit) after two rounds of "too pale" / "too dull" feedback on the darker basemaps. See
  CLAUDE.md's "Trail/lift/connector/selection colors are per-basemap" section for the full history,
  including a CSS `filter: drop-shadow` halo that shipped, broke on iOS Safari (WebKit transform+filter
  bug), and was fully reverted the same day in favor of the current geometry-based, kind-scoped halo.
- **Fixed: a trail's halo (the white ring behind schwarz trails on Satellit) didn't dim with solo mode or
  disappear on selection.** Selecting any loop solos it, which dims other trails' lines but — until fixed
  — left their halos glowing at full opacity, misread by the user as "Monte Corno wird komplett weiß" (the
  real cause: a *different* Trailrunde sharing Monte Corno's path). `applyHaloOpacity()` now keeps a
  halo's opacity in sync with its own line everywhere opacity changes; selecting a trail now suppresses
  its own halo outright (redundant once the yellow selection ring is showing).
- **Fixed: selecting a Tour riding a lift forced that lift's (supposed to be invisible, on non-Straße
  basemaps) mask back to fully opaque.** `applyLiftSegmentOpacity()` was setting all three of a lift
  stretch's strokes to the same on/off opacity, ignoring `LIFT_MASK_OPACITY`. Read as a white/light band
  appearing specifically once the Tour was selected.
- **The lift mask (a grey band covering OSM's own vector aerialway rendering) is now Straße-only** — the
  other three basemaps didn't need it (Satellit is a photo with no aerialway line to cover at all). The
  lift symbol (hairline+dots) is light grey on Satellit instead of near-black, for the same "too dark to
  see against dark terrain" reason schwarz trails needed fixing.
- **Recovered:** Donnersberg's "Wasser & Holz" Trailrunde had silently lost its entire `trailSegments`
  breakdown several commits earlier (an unrelated region-expansion commit rewrote the file without
  carrying the key forward) — noticed by the user, recovered from git history since the referenced
  component trails' geometry was unchanged.
- Sauerland/Upland: Winterberg split into two sub-regions (Trailpark + MTB Zone Willingen), lifts added
  (`tools/add_lifts.py`'s "sauerland" table). Several individual trails switched from their original
  source to OSM geometry where OSM turned out more accurate (case-by-case, not a blanket rule). MTB Zone
  Willingen's 8 trails sourced from Trailforks (no GPX endpoint exists for this sub-region). The four
  Trailpark Winterberg loops (Bremberg/Family First/Poppenberg/Sürenberg) were built from each loop's own
  recorded GPX (winterberg.de's Outdooractive-hosted API), with `tools/gpx_map_match.py` sequentially
  matching which of the 16 already-built Trailpark trails each loop actually rides, in ride order —
  connectors come from the loop's own recording, not a guess.
- New region: **Harz** (6 bike parks, 42 trails, 6 lifts, 9 places) — geometry from Trailforks' own
  `encodedpath`, harvested through the user's own logged-in Chrome and decoded in-browser (`tools/build_harz.py`);
  names/difficulty from the operator where certain, Trailforks otherwise; elevation backfilled since
  Trailforks embeds none.
- `tools/gpx_map_match.py` (sequential map-matching: reconstructs which trails/lifts a recorded GPX rides,
  in order, including repeats) gained a test harness and a density-sensitivity fix; used to fill a missing
  Tgantieni lift ride and, the day before, to reconstruct Tutti Frutti's real component-trail segments
  from a hand-authored Tourenbuilder export.
- **Added CHANGELOG.md itself** (this file).
- **The info panel heading now shows a trail's/Tour's difficulty** as the same colored dot the sidebar
  card and map label already use, with a hover tooltip (Sehr leicht/Leicht/Mittel/Schwer) — previously
  only implied by the elevation chart's line color.
- **The desktop info panel is wider (340px, up from 280px) and its elevation chart taller (72px, up from
  46px)**, to make the profile easier to read; touch/mobile unchanged. Checked live whether the existing
  profile data (100–200 points per trail, resampled by length) would look blocky stretched into the bigger
  chart — it doesn't, so no pipeline/data change was needed this round.
