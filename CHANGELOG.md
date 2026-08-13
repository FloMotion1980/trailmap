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
