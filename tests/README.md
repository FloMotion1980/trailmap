# Trailmap tests

```bash
python tests/run.py --list        # every suite and what it watches
python tests/run.py --changed     # only the suites your current changes can affect
python tests/run.py               # everything
python tests/run.py --suite solo labels
```

`run.py` executes the Python suites itself and **bundles** the selected browser suites into one paste-ready
`tests/_bundle.js`, printing the path and the preconditions. That split is not a convenience — see *Two
runners* below.

**Keep the browser window visible while a suite runs.** A hidden or background tab has its timers
throttled to roughly one tick per minute, and every wait in the harness is a timer: the full browser run
takes **~25 seconds** in a visible window and does not finish at all in a hidden one. A run that seems to
hang part-way through is almost always this, not a failure.

Current state, all green:
**20 suites.** The Python half is **101 cases / 286 checks**, measured 2026-08-21 and green (`appshell`,
`geomerge`, `ntcregression`, `pipeline`, `regiondata`, `runner`, `trailforks`). The browser bundle was last
counted on 2026-08-21 at **193 cases** across the twelve bundled suites; `builder` runs on its own with 19
cases / 97 checks. Browser counts are only ever as fresh as the last time someone pasted the bundle, so treat
the date, not the number, as the claim.

**Two of those cases are skipped on purpose in a window that does not paint** (`bearing`'s eased-transition
case and `controls`' fold), and one is skipped when the active region happens to have no schwarz Trailrunde
segment (`palette`). See `TM.paints()` below.

**`ntcregression` is the slow one (~60 s)** and it is a Python suite that runs a real algorithm over three
tours' worth of OSM ways, not a unit test. That is deliberate — see its own docstring for why a faster
comparison against the region file cannot catch what it catches.

## Serve the repo root, not the app folder

```bash
python -m http.server 8099          # from D:/Trailmap
#   → http://localhost:8099/Trailmap%20App/index.html
```

The tests must be **same-origin with the app**. A script loaded from a different origin reports every error as
an opaque `Script error.` with no message and no line number, and the app's own `window.onerror` turns that
into its fatal-error panel — so a trivial typo in a suite looks like the app exploding. Same-origin turned
exactly that into `Uncaught SyntaxError: Identifier 'b' has already been declared (Zeile 171)`.

The tests deliberately do **not** live in `Trailmap App/`: that whole folder is the GitHub Pages artifact, so
everything in it is published and reachable by URL.

## Two runners, because the app cannot be imported

Everything the app owns — `lineLayers`, `LIFTS`, `soloId`, `TRAIL_GEO`, `activeRegions` — is a `const`/`let`
inside one top-level `try{}` block in `index.html`. That is genuinely unreachable from any separately
evaluated script. Plain **function declarations** do leak to the global scope (sloppy-mode Annex B), which is
why `applySolo`, `render` and `trailPassesFilters` can be called from the console at all.

One footnote with teeth: Annex B covers *plain* declarations only. `async function boot()` and
`async function activateRegionGroup()` stay block-scoped and **cannot be called**. Suites that need them go
through the UI (the region dialog's own buttons) or through `TM.bootFresh()`, which brings up a second copy of
the app in an off-screen same-origin iframe — that shares `localStorage` and gives a genuine first painted
frame, which is what both boot-order bugs were actually about.

## Which tests do I have to run?

Each suite declares that itself, in its own header:

```js
// @suite   solo
// @area    Solo mode for trails, Tours and lifts
// @files   Trailmap App/index.html
// @touches applySolo, clearSolo, applyLiftVisibility, baselineLineOpacity
// @needs   region=bikekingdom, builder=off
```

`--changed` picks a suite when one of its `@files` changed **and** (it declares no `@touches`, or one of those
symbols appears in the diff). `@always` marks the cheap data checks that run whatever changed. `@standalone`
marks a suite that brings its own harness and must be pasted alone.

Two properties this buys, both deliberate:

- **The mapping lives next to the tests.** A table in a doc rots the first time someone renames a function;
  this one is read by the runner on every invocation.
- **An unclaimed change is reported as a `GAP`.** If you touch a file no suite watches, the runner says so
  instead of printing a green run. That list is the to-do list for the library.

## The suites

| suite | what it covers | notes |
|---|---|---|
| `pipeline` | `tools/trailmap_pipeline.py`: GPX parsing tolerance, dedupe, simplify, profiles | ends with a **golden** rebuild of all 12 Laax trails, byte-identical against the committed region |
| `regiondata` | every `regions/*.json`, the catalog, `version.json` | `@always`; runs `validate_region.py` per region **and** proves it still bites |
| `appshell` | the three-way stylesheet version sync, `APP_SHELL`, `waitUntil`, `boot().catch` | `@always`; a stale `style.css` makes new elements vanish rather than look unstyled |
| `bearing` | the two map orientations: pane parenting, upright labels, the cone, the padding vectors, hit-testing | drives `handleOrientation` with synthetic readings; the compass itself is not drivable |
| `geometry` | every pure helper: distance, interpolation, profiles, arrows, chart SVG | no DOM state, fastest suite |
| `filters` | `trailPassesFilters` / `liftPassesFilters` / `liftHiddenBySolo` and all four counts | the categories are mutually exclusive on purpose |
| `lists` | the three list sections: grouping, sorting, cards, selection | found two real bugs on its first run |
| `palette` | per-basemap trail/lift/connector/selection colors, the schwarz-only Satellit halo, unknown-key fallback | reads the map's own SVG strokes (stroke + stroke-width for the halo), same rule as `lifts`/`solo` — `diffColor`/`HALO` etc. are unreachable from here too |
| `solo` | solo for a trail, a Tour and a lift | three separate causes, checked separately — see below |
| `labels` | trail/segment/lift name labels, hover marking, place labels | Leaflet *fades* tooltips out; poll, never sleep |
| `infopanel` | panel contents, reverse, Tour segments, elevation chart + hover sync | reverse is checked on the **map** too, not only in the numbers |
| `lifts` | lift drawing, stations, Tour routing, builder-from-list | the mask/symbol split is load-bearing, not cosmetic |
| `regions` | activate/deactivate, the limit, persistence, four fresh boots | slowest suite; it really loads data |
| `controls` | the map control cluster: the segmented column, the readout chip, what covers what | hit-tests five points per control — a covered button is not a state bug, nothing errors |
| `runner` | `run.py` itself: which suites `--changed` selects, and the GAP report | `@always`; a suite that never runs looks exactly like one that passes |
| `trailforks` | `harvest_trailforks.py` + `build_trailforks_region.py`: the table/trail-page parsers, the paging rule, the difficulty mapping | the mapping case is data-driven against every harvested table, so it catches a tier nobody has seen yet |
| `builder` | Tourenbuilder junctions, direction, clipping, drag/swipe | `@standalone`, needs `bikecircus` + builder ON + a phone viewport |

## Conventions that exist for a reason

**Every suite starts from `TM.baseline()`.** Order-dependence is the most expensive kind of false failure
here. One case failed because the previous one left a lift selected — the panel's × kept the map selection *by
design*, so the app was right and the test was wrong. (That × was removed on 2026-08-02 and closing now always
deselects, but the lesson is the reason this baseline exists.) The baseline clears solo, selection,
the builder and every filter before each suite runs.

**A suite that changes which regions are loaded must put them back itself.** `TM.baseline()` deliberately does
*not* touch the region set: loading a region is slow and every other suite is content with whatever is active.
`regions` is the only suite that changes it, so it snapshots and restores — **by row index**, because parsing
a region's name out of a dialog row is a trap ("3-Länder Enduro Trails" starts with a digit, and the first
attempt's regex matched the empty string, which matches every label). The bundler also puts `regions` last, so
nothing depends on that restore working. Getting this wrong once produced seven suites' worth of failures that
all read like broken filter rules.

**Let a wrong precondition SKIP, not fail.** Each suite's second argument to `TM.add` is a predicate; the ones
that use Bike Kingdom ids check for a Bike Kingdom card by name, not merely "some lifts exist" — Paznaun has
lifts and Tours too, and the weak version let six suites run against ids that were not loaded and report
fifteen confusing failures instead of one honest skip.

**Ask `TM.paints()` before measuring anything an animation produces.** A hidden or background tab runs no
animation frames — and this project's own preview pane measures zero even when fronted — so neither a CSS
transition nor Leaflet's animated pan/zoom progresses there. A case that measures the *result* of one reports
a correct app as broken: that is what the `controls` fold "flake" was (its fold is a `max-width` transition),
and what made `bearing`'s hit-testing case skip silently (its `flyToTrailBounds` never arrived). Assert the
contract that holds either way — the class, the requested scroll, the pixel positions — and gate only the
animated part. `TM.paintFrames` carries the count, so the skip can say how it decided.

**Never dereference `list[0]` after asserting `list.length`.** The assertion fails and the very next line
throws, and a throw takes out the whole suite — every case after it, plus the app state it was mid-way
through changing. `bearing`, `ride` and `lifts` all had exactly this, and between them it produced most of
the "flaky suite" reports: one arrow that had left the view aborted `bearing` half-way through, which left
the map mid-turn for `controls` and `infopanel` and made three unrelated cases fail. Read through a helper
that reports `"(nothing painted)"` instead.

**Never sleep to wait for the app; poll.** `TM.until(fn)` for a condition, `TM.settle(fn)` for anything read
in **pixels**. `flyToTrailBounds` animates for 0.6 s and Leaflet re-projects every marker throughout, which
produced a very convincing "the marker did not move back" failure that was purely the map still flying.
`TM.settle` waits out the flight and then demands three identical samples.

**Read the map's own SVG, not app state.** Which pane a stroke is in, plus its colour and width, is what
distinguishes a standalone lift (all three strokes in `LIFT_BAND_PANE`) from a Tour's own lift stretch (only
its mask there, symbol in the overlay pane). Asserting on internals would have passed for the wrong reason
in at least one case where the paint was wrong and the state was fine.

**A test that has never failed proves nothing.** See `MUTATIONS.md`: every suite records either a verified
mutation or the real bug it caught, and which is which.

**When a test disagrees with the app, decide which is wrong before touching either.** Of the failures in the
first full run, four were the test and two were the app. Writing the tests also surfaced three *latent* gaps
(`build_profile` ignoring implausible `0 m`, `elevationAtDistance` extrapolating below zero,
`versionedRegionUrl` throwing on an unknown key). Only the first was fixed — it contradicted its own
documented contract and the golden test proved it changed no committed region. The other two are recorded in
the suites as deliberate non-assertions, because silently hardening code while writing its tests removes the
evidence that anything was ever wrong.

## Not covered, and not coverable this way

- **Real CSS layout on a phone.** jsdom has no box model at all, and this harness runs in a desktop viewport.
  Chip wrapping, scrollbar-driven reflow and the drawer geometry need a real device or a resized browser.
- **GPS, compass, wake lock.** `watchPosition`, `DeviceOrientationEvent` and the permission prompts cannot be
  driven from here. This is why `#liveStatus` exists: it makes those failures readable in the field instead.
  What *is* covered is everything downstream of a reading: `bearing` calls `handleOrientation` and
  `updateUserLocation` directly with synthetic values, so the smoothing, the map bearing and the cone are
  tested even though the sensors are not.
- **Service-worker caching across app restarts.** Whether an iOS home-screen PWA picks up a new worker is a
  platform behaviour; the version line in Kartenoptionen is the answer to that, not a test.
- **Tile servers and any network source.** No suite makes an outbound request; the pipeline's golden case runs
  offline from the GPX in `Material/` on purpose.
