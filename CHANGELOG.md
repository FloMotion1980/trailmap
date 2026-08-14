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

## 2026-08-14
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
