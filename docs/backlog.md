# Backlog

General, cross-topic backlog for Trailmap — ideas, pending features and open decisions that aren't
tied to any single file. Mirrors the assistant's own local memory notes so the plan survives a switch
to a different device (memory lives on one machine only; this file travels with `git clone`/`git
pull`). Keep both roughly in sync when the backlog changes; if they ever drift, this file is the one
to trust, since it's the one guaranteed to be current on whatever device is in use.

Merged 2026-08-15 from the former standalone `docs/region-backlog.md` (regions) plus a new RIDE-Modus
section — one general backlog covering all topics, per the user's own request, instead of a new
per-topic file each time.

## RIDE-Modus

Follow-up ideas from the same day RIDE mode shipped and was confirmed working on the phone (see
`CLAUDE.md`'s RIDE section for the feature itself). Not yet designed or scoped — clarify with the user
before implementing any of these.

**Swept 2026-08-20, after the user pointed out this section was reporting shipped work as open.** Four
entries had been built (or deliberately dropped) without the backlog being nudged: the bigger RIDE-only
control buttons, the basemap-contrast ask, the bolder selected line, and the record/stop icon. They are kept
below as struck-through entries with what actually happened, rather than deleted — the reasoning behind a
rejected option is worth as much as the reasoning behind a shipped one. **When one of these gets done, edit
this section in the same commit as the code**, the same standing rule `CHANGELOG.md` already has.

- **Infobox (`#rideInfoPanel`) is probably done for now** — 2026-08-16 shipped a live speed/altitude
  readout, then a redesign after the user reviewed mockups (dominant centred speed, smaller altitude
  badge, trail row hidden outright with nothing focused). Only revisit if the user reports something
  new after testing on the phone.
- **A toggle button for map orientation, instead of driving it from the phone's own sensors.**
  Currently "Blickrichtung oben" is compass-driven (`setHeadingUp`/`handleOrientation`) and is
  auto-enabled when RIDE starts. The user wants a manual toggle instead — unclear yet whether this
  means replacing the compass entirely (e.g. a button that flips between a couple of fixed
  orientations) or just adding a manual on/off toggle *for* the existing compass-driven rotation
  (which already sort of exists as `#bearingBtn`) — needs clarifying next time, don't assume.
- ~~**Possibly a record/stop icon instead of the mountain-bike emoji for the RIDE button**~~ —
  **settled 2026-08-16, rejected twice and the emoji changed instead.** ⏺️/⏹️ was turned down once for the
  coloured background chip those render with on many platforms, and once on principle ("solange wir nix
  aufnehmen ist das nicht das richtige" — nothing is actually being recorded). The button went 🚵 → 🚴 → 🚲
  → 🚴‍♂️ instead. Re-open this only together with the Tracking point below, i.e. once something really is
  being recorded.
- **A separate "Tracking" concept in addition to RIDE mode** — the user explicitly said they don't yet
  know whether this is its own mode or connected to RIDE ("Ob das ein eigener Modus ist oder
  zusammenhängt weiß ich noch nicht"). Sounds like it could be about recording/saving a ridden track
  (GPX-style), distinct from RIDE's existing live GPS-follow display — but this is a guess, not
  confirmed. Needs a real discussion before any design/implementation, not just an assumption from the
  name.
- **2026-08-16 phone-test follow-ups:**
  - ~~**Basemap contrast during RIDE**~~ — **shipped 2026-08-16, but as a GENERAL setting rather than the
    RIDE-only one that was asked for.** The ask: "Straße" is the best basemap for navigation (colour-wise
    "Straße hell" would be nicer, but it is missing paths, which is a problem if you get lost), so could its
    own tile rendering be dimmed/desaturated while riding. What landed instead is "Straße / Straße dezent /
    Straße hell" as three peer basemap options (the same osm tiles at three CSS filter levels on Leaflet's
    own tile pane — no tile server involved, works offline), with **"Straße dezent" the default on a
    first-ever visit**; the old CARTO/Positron layer was kept and renamed "Pastell". Left as a general
    setting on purpose, so it is available outside RIDE too. **Still genuinely open, if the user wants it:**
    automatically switching to the dezent level while `html.ride-mode` is on and back afterwards, so riding
    does not need a manual basemap change first.
  - ~~**Selected trail/tour line needs to be bolder AND higher-contrast in sunlight**~~ — **shipped
    2026-08-16 as the three-layer RIDE focus halo**, after the mockup rounds recorded below (variants A-K).
    The constraint the user set held: each segment keeps its own difficulty colour as the core, with the
    accent added around it, never replacing it ("das ist einer der großen Mehrwerte unserer App"). What
    landed: orange outer ring + light per-difficulty tint + the existing core line, applied only to whichever
    trail/tour is open during RIDE. Tuned twice live afterwards — the ring went 14→18px and dropped its 0.75
    opacity to fully opaque (two semi-transparent rings stacking where a loop crosses itself darkened toward
    red), and any real gap between two consecutive segments is bridged with a plain orange line so an
    un-closed tour still reads as one continuous ring. See `CLAUDE.md`'s RIDE focus halo bullet.
  - ~~**Bigger `#mapControls` buttons for glove/on-bike use**~~ — **shipped 2026-08-16**: the three cells
    grow 44px→64px (icon 20px→28px) while `html.ride-mode` is active, with the readout chip widened to match
    so the joined-corner design still lines up. Unaffected outside RIDE, exactly as decided.
  - **Compass appears to freeze for a few seconds repeatedly while riding** — traced to intended
    behaviour, not a bug: `handleOrientation`'s bearing deliberately FREEZES (rather than resetting)
    when magnetometer readings go stale, and a bike's own metal frame/phone-mount magnets/vibration are
    the likely real-world cause of those brief dropouts — the user's own instinct that GPS reception is
    unrelated is correct. Komoot likely avoids this by driving its direction indicator mainly from GPS
    course-over-ground while moving rather than the magnetometer; this app currently prioritises the
    compass and only falls back to GPS course when there is no compass reading at all. A speed-gated
    hybrid (GPS course above some km/h, compass at a standstill) was floated as a possible fix but is a
    real design change, not implemented, not yet decided.
  - **Future idea, explicitly "im Hinterkopf behalten" (not scoped, not requested for now):** colour
    the already-ridden portion of the currently-open trail/tour differently from the part still ahead,
    the way Komoot does — would need live progress-along-the-line tracking (nearest point reached on
    `TRAIL_GEO`/loop line) feeding into the elevation-chart-segment-colouring style split already used
    elsewhere in the app.
  - **The line-style mockup work above converged on a concrete direction (2026-08-16, still mockups only,
    nothing built): a three-layer halo** — an outer accent ring, a middle tint in a light version of the
    segment's own colour, and the segment's own full colour as the core. For a component-trail stretch the
    middle/core follow that trail's own difficulty colour (light tint + full tone, matching the existing
    Satellit/Relief halo colours: `#a8e8ba`/`#a9cdf5`/`#f5aa9d` for grün/blau/rot; schwarz uses light GREY
    `#cfcfcf`, not white — white was tried first and rejected only for being the wrong shade, not the wrong
    idea). For a connector stretch (no component trail) the core is the existing dark grey
    dashed line, at a slightly bigger weight than before (`#3d3d3d`, ~5px — the user's pick over a lighter
    `#5a5a5a`/4px alternative). The OUTER ring is orange (`#ff6a00`, ~15-18px, ~0.75 opacity — brightened
    and widened once from a paler first attempt after the user found it invisible against the red trail's
    own light-red tint) on every kind (trail and connector alike).
  - **The outer ring's colour is NOT a placeholder — the user corrected this explicitly (2026-08-16):
    orange and grey are both permanent, meaning RIDE PROGRESS, not a temporary stand-in for one another.**
    When a RIDE session on a tour starts, the entire tour's outer ring is orange (nothing ridden yet); as
    the rider progresses, the outer ring behind the live position turns grey, ahead of it stays orange —
    exactly the Komoot-style already-ridden-vs-still-to-come split from the earlier bullet, just
    implemented as the SAME outer-ring layer rather than a separate feature. This needs live
    progress-along-the-line tracking (nearest point reached on the open tour's `TRAIL_GEO`) feeding a
    split point into the per-point outer-ring colour — real RIDE-mode work, not just a CSS/style change,
    so still backlog rather than something to build alongside the mockup styling. Outside of an active
    RIDE session (or before the rider has moved), the ring is presumably all-orange by default (nothing
    ridden yet) — not yet confirmed with the user what it should look like when a tour is merely selected
    without RIDE running.
- **Automated test coverage for RIDE mode is still thin and worth closing out.** What exists:
  `tests/browser/bearing.js` (the merged position-button reattach path, the pinch-vs-drag detach fix)
  and `tests/browser/controls.js` (the position cell's show/hide contract via
  `is-detached`/`is-centred-following`). What's still MISSING and only ever verified by hand/
  live-phone: `enterRideMode`/`exitRideMode` themselves (the `html.ride-mode` chrome-hiding, the RIDE
  button's own toggle), `applyRideMapOffset`/`clearRideMapOffset` (the look-ahead placement math,
  portrait AND landscape), and `updateRideInfoPanel`/`#rideInfoPanel`'s content updates. Add these once
  the info panel redesign (above) settles, so the tests aren't written against a UI that's about to
  change again.
  - **2026-08-16: `tests/browser/ride.js` was built to close exactly this gap** (11 cases covering
    enter/exit chrome, auto-solo + selection-ring suppression, the focus halo for both a plain trail and
    a segmented Tour, `applyRideMapOffset` in portrait AND landscape, and the info panel's speed/
    altitude/trail-row content) — while building it, it surfaced a REAL, previously-unreported crash (see
    the next bullet), not just a test-writing exercise.
- **FIXED (2026-08-16): entering RIDE mode (or just toggling "Blickrichtung oben" rapidly) could crash the
  whole app with "Karte konnte nicht geladen werden" / `Script error.`** — confirmed by the user on their own
  phone independently of this session's testing ("Immer beim Einschalten des Ride Modes... auch oft
  hintereinander", later corrected to "auch direkt nach App-Start... aber auch da nicht bei jedem Mal").
  **Real root cause, found from a full (not truncated) stack trace after extensive bisection:** an infinite
  event-handler loop, not a Leaflet/leaflet-rotate internals bug. A `map.stop()` call added earlier the same
  day (to cancel an in-flight pan/zoom animation before rotating/resizing the map) cancels a mid-flight
  flyTo/panTo by internally forcing a zoom reset, which fires Leaflet's own `"zoomstart"` event; this app's
  pre-existing `map.on("zoomstart", () => { if (!expectingOwnZoomChange) handleUserGestureStart(); })`
  listener (built for pinch-detach detection) reacted to that by calling `handleUserGestureStart()`, whose
  own body calls `map.stop()` again — which can fire `"zoomstart"` again, calling `handleUserGestureStart()`
  again, forever, until "Maximum call stack size exceeded". Confirmed with the FULL stack trace (not just the
  first few frames, which earlier looked like different, unrelated Leaflet-internal call sites each time —
  `_tryAnimatedZoom`, `_getCenterOffset`, `_resetView`, `latLngToLayerPoint` were all just different POINTS
  inside the SAME recursive loop, depending on how many bounces had already happened when the stack
  overflowed): `setView → _resetView → _moveStart → fire("zoomstart") → handleUserGestureStart →
  map.stop() → setZoom → getCenter → ...`. **The actual fix**: every `map.stop()` call in the file now goes
  through a new `safeMapStop()` helper (near `expectingOwnZoomChange`'s own declaration) — a plain reentrancy
  guard (`mapStopInProgress`) that makes a `map.stop()` call triggered WHILE another one is still unwinding a
  no-op instead of recursing, plus setting `expectingOwnZoomChange` for its own duration so the zoomstart
  listener doesn't even try. This replaced the four separate `map.stop()` call sites (`commitBearing`,
  `enterRideMode`, `handleUserGestureStart`, `recoverFromRotationCrash`). **Also added, and kept even though
  the real bug is now understood**: `toggleRideMode()`/`withRideCooldown()` (a 400ms cooldown so the two RIDE
  buttons can't fire the same transition twice before the first settles) and a `window.onerror`-level safety
  net (`recoverFromRotationCrash()`, aliased on `window` since the outer handler has no closure over the
  app's internal state) that resets rotation/RIDE state to a clean baseline if this class of crash — or any
  other stack overflow with this exact message — ever recurs for a different reason, so the app degrades to
  "tap the button again" rather than a dead end. Verified with two independent full 12-suite regression runs
  in a fresh browser tab, both landing on the identical 168/170 passed (the 2 remaining `bearing` failures and
  1 `infopanel` failure are unrelated, pre-existing flakes) — before the fix, `tests/browser/ride.js` and
  several unrelated suites (`lists`, `solo`, `regions`, `labels`) failed/threw inconsistently every run,
  because the corrupted rotation state this bug left behind bled into whatever suite ran next.
- **FIXED (2026-08-20): a trail selected from the sidebar list wore the yellow selection outline (correct)
  AND the bold hover width (wrong) on a TOUCH device.** The call site was not in the selection code at all:
  the CARD's own `mouseenter`/`mouseleave` handlers, which a tap synthesises on a touch screen just as a real
  mouse does. Both list call sites go through one `wireCardHover()` now, on `pointerenter`/`pointerleave`,
  skipping `pointerType === "touch"`. Read off the GESTURE rather than a `(hover: hover)` media query on
  purpose: a hybrid laptop with a touchscreen and a mouse keeps its real hover and loses only the
  tap-synthesised one — and the rule being per-gesture is also what makes it testable from a desktop harness
  at all. Knock-on: `labels`/`lifts`/`solo` dispatch PointerEvents on cards now, since a MouseEvent reaches
  nothing.
- **FIXED (2026-08-20): a selected trail's START marker read white while its Ziel read red — and it was
  never a RIDE bug.** The white `startDot` and the green `startMarker` sit at the EXACT same coordinate with
  the same radius, so whichever was added to the map last covers the other: `showEndpoints()` brings the green
  pair to the front once, but `updateStartDotVisibility()` re-adds the white dot on every zoomend. RIDE only
  made it constant, because the map zooms and pans throughout; the Ziel marker has no white counterpart, which
  is why only the Start looked wrong. Fixed by removing the overlap rather than re-fighting the z-order — one
  `syncStartDot(layer)` decides a startDot's visibility everywhere and suppresses it while that trail's own
  endpoints are showing. Two new mutation-checked cases in `tests/browser/lists.js`; the startDot one counts a
  DELTA rather than "no white dot at the green position", because several trails legitimately share a
  trailhead and that coordinate holds another trail's dot either way.
- **Open, measured, not fixed: RIDE mode more than doubles the vector-renderer memory, and that is why zooming
  far out could kill the app.** The crash itself is closed (a `RIDE_MIN_ZOOM` of 10 now blocks the trigger — see
  `CHANGELOG.md` 2026-08-20; confirmed on the user's own phone the same day), but the underlying overhead is untouched and will matter again for a bigger
  region or an older phone. Measured on a 375x812 viewport at a fixed 45° bearing:

  | | container | ratio | `rotationPadding()` | painted box | 3 renderer panes |
  |---|---|---|---|---|---|
  | rotation, RIDE off | 375x757 | 2.02 | 0.646 | 1835x1835 | ~38 MB |
  | rotation, RIDE on | 375x995 | 2.65 | **0.938** | **2786x2786** | **~89 MB** |

  Two individually-correct mechanisms colliding: RIDE's look-ahead inflates `#map` to place the position dot a
  third up from the bottom, and `rotationPadding()` must cover the circle the container sweeps, with the SHORT
  axis deciding — so a more elongated container costs quadratically. **The obvious fix, capping the padding, was
  offered to the user and declined** in favour of the zoom limit, and rightly: that padding exists because the
  user reported the rotation stutter, so capping it trades their own fix back. Options if this is ever picked up
  again, in rough order of appeal: (a) derive the padding from the radius needed to cover the VISIBLE crop
  rather than the whole inflated container — correct, but measured at only ~18% saving, since the crop reaches
  almost the full height anyway; (b) cap the padding only while RIDE is on and accept some stutter there; (c)
  shrink `RIDE_LOOKAHEAD_FRACTION`, which attacks the elongation itself but changes a placement the user chose
  deliberately; (d) drop the whole SVG-under-rotation approach for a GL/vector-tile map, which is the only one
  that removes the class of problem rather than the instance.
  **A second, unexplained observation from the same session, worth knowing before assuming memory is the whole
  story:** with the zoom guard mutated away, one of three `ride` suite runs threw `Invalid LatLng object: (NaN,
  NaN)` out of Leaflet. It did not reproduce and it is NOT the reported crash (a throw shows the fatal panel;
  the report is a white page) — but a far-zoomed-out rotated RIDE map may be a broken state and not just an
  expensive one. Nobody has chased this down.
- **General note from the same 2026-08-16 conversation: go through `CLAUDE.md`'s documented feature
  history looking for other behaviours that don't yet have a browser-suite case**, the same way this
  session's `ride.js` work surfaced a real bug purely from the exercise of writing tests for
  already-shipped behaviour. Not scoped into a concrete list yet — do this as a deliberate pass next time,
  cross-referencing CLAUDE.md's per-feature bullets against `tests/browser/*.js`'s `@touches` headers.

## Trailrunden-Lückenschließen (tools/close_loop_gaps.py)

**Die Methodik steht jetzt in `docs/trailrunden-lueckenschliessen.md`** — Leitgedanken, Prioritätsstufen,
Befahrbarkeitsprüfung, Wegtyp-Präferenz, die zwei Fallen des ersten Durchlaufs und das gemessene Ergebnis.
Dort nachlesen, bevor das Tool erneut angefasst oder auf eine weitere Tour angewendet wird; hier steht nur
noch, was davon offen ist.

**Stand 2026-08-16:** `pw_rodalben_felsentrails` ist mit dem überarbeiteten Verfahren komplett neu gerechnet
und hat **null Lücken über 2 m** (vorher: 38, obwohl der erste Report 29 Schließungen gemeldet hatte). Alle
29 Ziel-Lücken wurden allein durch OSM-Weg-Matching gelöst (Stufe 1), 22 davon auf echten `path`-Wegen; 11
hatten gesperrte Nachbarwege, die jetzt korrekt verworfen werden. Ein zweiter Durchlauf mit Schwelle 12 m
hat auch die verbliebenen kleinen Sprünge geschlossen.

### Offen

- **Alle übrigen Trailrunden durchgehen.** Bislang wurde das Tool nur auf Rodalben angewendet; jede andere
  Tour mit `trailSegments` hat ihre Lücken unverändert. Der Nutzer hat beim Durchsehen der App mindestens
  eine weitere betroffene Tour gefunden (Screenshot bei „Eisenbahnschienen" / „Wiesental Wildgehege",
  vermutlich eine weitere Pfälzerwald-Runde — noch nicht identifiziert). Das war immer der Plan: Rodalben war
  nur der Testfall.
  **Kosten im Blick behalten:** jede Lücke ist eine eigene Overpass-Abfrage, Rodalben brauchte ~29 min für 29
  Lücken. Der Cache (`--cache`) macht Läufe fortsetzbar; `CACHE_VERSION` bumpen, wenn sich die Routing-Logik
  ändert, sonst spielt der Cache die alten Ergebnisse zurück.
- **Touren, die gar nicht auf OSM-Wegen liegen.** Der Nutzer hat beim Durchsehen Touren gefunden, deren
  Trailabschnitte neben jedem gemappten Weg verlaufen — „in so einem Fall wird uns die OSM-Strategie keinen
  Erfolg bringen". Das Verfahren erkennt das inzwischen (`MATCH_MAX_MEAN_M`) und gibt in Stufe 1 auf, statt
  zu raten; ob die Stufen 2/3 dort brauchbare Ergebnisse liefern, ist noch **nicht** an einer echten solchen
  Tour geprüft worden — Rodalben hat Stufe 1 nie verlassen.
- **Kandidatenklasse „Trail kürzen" statt nur „Connector verlängern"** (eigener Vorschlag des Nutzers): die
  Segment-Geometrie an einer früheren Stelle kappen, bis eine sauber befahrbare Verbindung entsteht. Noch
  nicht gebaut — der Lösungsraum ist bisher rein additiv.
- **Für den Tourenbuilder wiederverwenden.** Der Nutzer hat ausdrücklich darauf hingewiesen, dass dieselbe
  Aufgabe dort ansteht („das hilft uns auch für den Tourenbuilder später noch"): Weg-Matching,
  Befahrbarkeitsprüfung und Verbindungslogik sind dieselben Bausteine, wenn zwei gewählte Elemente verbunden
  werden sollen. Aktuell liegt alles in `tools/close_loop_gaps.py` (Python, Build-Zeit) — der Tourenbuilder
  läuft im Browser, es ist also noch offen, ob die Logik portiert oder vorberechnet wird.


## Regionen

Ordered list of bike regions the user has asked to add to Trailmap, in the order they were
requested (as of 2026-07-26 unless noted).

1. **Tiroler Zugspitz Arena** — source: https://zugspitzarena.com/de/aktivitaeten/biken/downhill-enduro
   Its own URL structure already reveals the sub-regions (`/trails/ehrwald-wetterstein/…`,
   `/trails/lermoos-biberwier/…`) and trail names (Blue Bird, Fifty Fifty, Bachtl Trail,
   Forest Aisle, Mühlwald Trail, Schlägle Trail). **Built.**
2. **Bike Kingdom** (Lenzerheide/Arosa, CH) — 2 bike parks plus a very large trail network. **Built.**
3. **Planai/Schladming + Reiteralm** — one region, those two as sub-regions. **Built.**
4. **Brandnertal** (Vorarlberg, AT). **Built.**

Added to the list later the same day (no order given beyond "also on the list"):

5. ~~**Bikepark Laax**~~ — **built 2026-07-30** as "Flims Laax Falera": 12 trails, 8 lifts, 5 places
   (`tools/build_laax.py`). Geometry from the trails' own Outdooractive routes.
6. **Kronplatz** / Plan de Corones (Südtirol, IT) — **researched 2026-07-30, not built: no reachable
   geometry source.** All 19 trails with official difficulties, the three areas and the 5 bike lifts
   are written up in `docs/kronplatz-recherche.md`, together with the four sourcing routes already
   tried, so don't repeat them.
7. ~~**Livigno**~~ — **built 2026-08-11, completed same day**: 29 trails + 1 tour + 7 lifts, 2
   sub-regions (Carosello 3000, Bikepark Mottolino). "Tutti Frutti Epic MTB Tour" segmented later the
   same session — see `tools/gpx_map_match.py`'s own docstring for how. The two originally-skipped
   trails were found by the user under different names (Panoramica = "Sentiero delle Tee"; D.H. 2005 =
   Trailforks' "Downhill World Championship 2005") and added, plus a new "Hairy Cattle" the user also
   found. Carosello 3000's difficulty had a systematic one-tier-too-low error across 7 trails (Coast to
   Coast, Roller Coaster, Bikers United, Blueberry Line, Bike Academy, Madonon, Lonely Planet) — all
   fixed. A user-suggested extra trail, "Madonon Ridgeline"
   (trailforks.com/trails/madonon-ridgeline/), turned out to be Trailforks-tagged Hike, not Mountain
   Bike — correctly not added.
8. ~~**Winterberg** (markets itself as "The Mother"), **Willingen** (Ettelsberg) and **Green Hill**~~
   — all three in the Sauerland/Upland corner of Germany, decided 2026-07-26 as ONE region
   "Sauerland/Upland" with those three as sub-regions (a purely geographic bracket — unlike Portes du
   Soleil there is no shared ticket and no tours spanning them). **Built 2026-08-11**: 46 trails, 3
   sub-regions (Winterberg 28, Willingen 2, Green Hill 16). "The Mother"/`bikepark-winterberg.de` turned
   out to be a genuinely different network from Trailpark Winterberg (different hill), not the same one
   under two names as originally assumed. Green Hill's main Trailforks page renders from Mapbox vector
   tiles with nothing embedded to scrape — the old anonymous-polyline-extraction technique (see
   `docs/data-sourcing-general.md`) doesn't work there; the fix was the lighter
   `/widgets/trail/?trailid=<id>&elevation=1&basic=1` embed, which still inlines a plain point array.
   **Known gaps, left honest rather than guessed**: no lifts for any of the three parks yet (all three
   have real chairlifts); Winterberg's 4 combination loop routes not built (would need full Trailrunde
   segment-matching against the region's own trails, per `docs/trailrunde-feature.md`); 3 "The Mother"
   trails with no published GPX (Jump Line, iXS Downhill, Blackline 2.0); Willingen's 12 MTB Zone named
   descents have no GPX anywhere.
9. ~~**Harz**~~ — **built 2026-08-13**: one region `harz`, **42 trails, 6 lifts, 9 places, 6 sub-regions**
   (Trailpark Ilsenburg 5, Hahnenklee 11, Bodetal/Rosstrappe 6, Schulenberg 7, St. Andreasberg 8,
   Braunlage/Wurmberg 5). The user's call was one region with the parks as sub-regions, a purely
   geographic bracket like Sauerland/Upland — no shared ticket, no tours spanning them. **A sixth park
   turned up that was not on the original list: Trailpark Harz** (Ilsenburg, self-shuttle, no lift and no
   entry fee), which is why five of six sub-regions have a lift and it does not.
   - The "no GPX anywhere" note above was right about the operators but **the geometry problem was solved
     a different way**: the user supplied a Trailforks region URL per park, and all 67 sections came out of
     Trailforks' own embedded `encodedpath` — see `trailforks-anonymous-polyline-extraction` and, for a
     much faster harvesting method found here, the note at the end of this entry.
   - **Trailforks splits these parks into "upper/middle/lower" sections** (21 rows for Hahnenklee's 11
     real trails, 13 for Bodetal's 6) and the user asked for them to be merged. Which sections belong
     together is verified by measuring the actual endpoint joints, not read off the names — see
     `tools/build_harz.py`. Two joints the names get wrong: `harzer-roller-3` is the stretch
     **Brunhildenritt and Harzer Roller physically share** (which is why Trailforks has no "Brunhildenritt
     3"; the user knew this independently), and `senduro-entry` is Wildpig Enduro's entry despite sharing
     no word with it.
   - **Difficulty: the OPERATOR's own published grade wins, Trailforks only where there is none** —
     changed 2026-08-14 on the user's standing rule ("Immer die Schwierigkeit des Betreibers
     übernehmen"), replacing the Trailforks-throughout rule this region was first built to. All six
     operator pages were re-checked that day: only **three publish a grade at all** — St. Andreasberg
     (its own numbered 1–9 list), Trailpark Ilsenburg, and Bodetal (in prose) — while **Hahnenklee,
     Schulenberg and Braunlage publish none**, so those three necessarily stay on Trailforks' rating
     (Braunlage's coloured dots are trail *markings*, not grades). The three-step German scale maps onto
     the app's own labels: leicht → `blau`, mittel → `rot`, schwer → `schwarz`, and a grade stated across
     two steps ("mittel / schwer") takes the **harder** one, the user's own call. Nothing here is "sehr
     leicht", so `gruen` is never reached this way. **Result: 7 St. Andreasberg trails changed** (Flowtrail
     grün→blau, Singletrail blau→rot, Funride blau→rot, Freeride rot→schwarz, Enduro rot→schwarz, Downhill
     rot→schwarz, Jump Line blau→schwarz); Ilsenburg's and Bodetal's operator grades already agreed with
     what was shipped. The mapping table is `OPERATOR_DIFF` in `tools/build_harz.py`, with each trail's
     operator wording beside its colour, and `resolve_diff` there is pinned by five cases in
     `tests/python/geomerge.py` — including one comparing the shipped `harz.json` against the rule for all
     42 trails, since the file is hand-edited after the build writes it.
   - **Names**: St. Andreasberg resolved completely — Trailforks carries the park's own #1–#6/#9 numbers
     and `msbx-6`'s description confirms it ("#6 is the easiest of the steep routes, options to cross to
     #4 and #5"), so all eight carry their official names. Bodetal keeps the operator's 01–05 numbering.
     Schulenberg uses outdoorwerkstatt.eu's names. Hahnenklee keeps Trailforks' names (the operator names
     only two trails in prose). **"Alberti-Lift" is the operator company (Alberti-Lift GmbH), not a
     lift** — the Matthias-Schmidt-Berg has two parallel double chairlifts, both with bike holders, and
     both are in.
   - **Remaining gaps — reviewed with the user 2026-08-14 and accepted as they are** ("Die fehlenden
     Trails lassen wir dann weg. Ich habe auch keine GPX gefunden. Alles andere können wir so lassen"), so
     these are recorded rather than open. The user also confirmed the two non-park trails (Hahnenklee's
     `Spiegelthaler-Trail`, Bodetal's `Bodetrail`) stay in even though they are not park lines:
     * **Trailpark Harz's names do not line up with its own site.** trailparkharz.de lists Waldbad /
       Moosklippe / Mönchsgraben / Jack the Ripper / Wassertal / Kammweg. Only Jack the Ripper and
       Wassertal map with certainty (descents agree to the metre: −227 m, −231 m). `Eselsstieg` and
       `Stumpfrücken-Trail` keep their Trailforks names rather than being guessed onto Kammweg/Waldbad.
       Moosklippe and Mönchsgraben are officially **closed** and have no Trailforks geometry. Trailforks'
       `pahnberg` was excluded: no `encodedpath` at all and its own description reads "Trail existiert
       erstmal …".
     * **Braunlage's three "Downhill" sections keep the Trailforks name.** The operator publishes
       Freeride / Snakebite / Evil Rock's / Enduro and has no "Downhill"; calling them Snakebite would be
       a guess. Also **Trailforks is missing over a kilometre of Freeride** (operator ~3 400 m against our
       2 034 m of line) and its upper/lower halves have a real **83 m gap at the gondola mid-station**,
       stitched straight and recorded in `WIDE_JOINTS`.
     * **Missing trails with no geometry anywhere — dropped for good** (user, 2026-08-14, who found no GPX
       for them either): Bodetal's `05 Schwarze Köhlerliesel`, Schulenberg's `OnAir` (Pro Jumpline), St.
       Andreasberg's `7 Super Enduro` and `8 Kids Trail Harz`. Do not re-open this without a new source.
     * `Loam Line` (St. Andreasberg) carries no Trailforks number and does not match the operator's
       unnumbered #7 by length, so it keeps its Trailforks name.
     * **No Touren/Trailrunden** — none of the six operators publishes a combination route.
   - Sources used: the five operator pages listed in the original note above, plus
     https://trailparkharz.de/ (the sixth park), https://www.harz-bikepark.de/ (an aggregator covering all
     six — useful for cross-checking, but it renamed several Schulenberg trails, so the operator page
     wins), and the six Trailforks regions `trailpark-harz-39447`, `bikeparkhahnenklee`,
     `bikepark-bodetal-rosstrappe`, `racepark-schulenberg`, `msbxtrail-26002`, `bikepark-braunlage`
     (the last one found here — the user gave no link for Wurmberg).
   - **Method note worth reusing: harvesting a whole Trailforks region takes ~3 tool calls, not ~100.**
     From an already-loaded trailforks.com page in the user's logged-in Chrome, `fetch()` is same-origin
     and carries the session, so every trail page can be pulled in ONE background loop
     (`fetch` → regex the `encodedpath` → decode in page) instead of navigating per trail. Getting the
     result out without retyping it: build a Blob and `a.click()` it, i.e. let Chrome **download** the
     JSON into `~/Downloads` and read it from disk. That also sidesteps the backslash-escaping trap
     entirely. All 67 Harz sections came out this way and every decoded length matched Trailforks' own
     stated distance to within 2 m.
10. **Geißkopf / Freiburg / Todtnau** — added 2026-08-11. **Freiburg and Todtnau are BUILT**
    (2026-08-20) as part of a whole-range `schwarzwald` region: 119 trails, the Hasenhorn chairlift,
    seven sub-regions, `docs/schwarzwald.md` for the full account. The region file, its build script
    and its version hash are all in place, but **the `REGION_CATALOG` entry is not** — `index.html`
    was being edited by another session at the time, so the entry the build script prints still has
    to be pasted in before the region appears in the app. **Geißkopf is still open** and is NOT part
    of that region: it is in the Bayerischer Wald, 300 km east, and only ever shared this backlog
    item by accident of when the three links were collected. Still to do for the Schwarzwald: a
    Trailforks sweep (only the club's own association 12404 has been worked in), Bikepark Bad
    Wildbad — in none of the sources used, Todtnau's third run "Downhill Flow" (no geometry
    anywhere), and the region's first Tour ("Schauinsland Enduro", a Trailforks multi-trail).
    Geißkopf (Bodenmais, Bayerischer Wald) is geographically separate from Freiburg/Todtnau (both
    Schwarzwald) — do NOT assume these three form one region group like Sauerland/Upland; decide the
    grouping when picked up based on actual distance, same judgement call as Livigno/Waldmeister's
    "does this deserve its own bounding box" question. Sources:
    - https://mtbzone-bikepark.com/geisskopf/strecken — Geißkopf trail overview (same
      `mtbzone-bikepark.com` site as Willingen's — check if it has direct GPX for this park, since it
      did NOT for Willingen).
    - https://www.mountainbike-freiburg.com/trails/#trails — Freiburg-area trails. **Used**: the page's
      own `window.mtb_trails` blob carries per-trail GPX *and* the club's own difficulty colours.
    - https://2-cycle.de/pages/bikepark-todtnau-strecken — Bikepark Todtnau. **Used** for the three runs'
      names, grades and figures; it has no GPX at all, hence OSM/Trailforks for the geometry.
    - https://www.trailforks.com/trails/all/?association=12404&activitytype=0 — the club's own Trailforks
      association, given by the user 2026-08-20. **Used**: 25 trails, of which six were not on the club's
      own site and three existed nowhere else.
    - https://trailguide.net/html/Germany/Baden-W%C3%BCrttemberg/Freiburg — added 2026-08-11. **Used, and
      it turned out to be a bulk source, not a click-per-trail one**: Trailguide has an anonymous JSON API
      (two calls, documented in `docs/schwarzwald.md`) that returns every trail's full geometry WITH
      per-point elevation, so no headless browser and no DEM lookups were needed. Reuse it for any future
      region Trailguide covers. Original note, still accurate about the listing page: a bigger
      Freiburg trail list than mountainbike-freiburg.com's official one, with **overlap** (some of the
      same trails appear on both) plus several extra ones. GPX is reachable per-trail but needs a second
      click-through on the trail's own subpage (not a direct link from the list view) — check whether
      trailguide.net is scrapeable with a plain fetch before assuming a headless-Chromium workaround is
      needed. When this is picked up, reconcile the two Freiburg sources by name before building (don't
      double-build trails that appear on both).
11. **Rheinland-Pfalz/Saarland cluster** (near the user's home area, same corner as Donnersberg) — added
    2026-08-10. **Built 2026-08-11**: Bad Kreuznach region (Naheland Trails + Haardt Lines, 17 trails +
    3 tours), RadLust Waldmeister (1 trail, segmented into 20 component trails via
    `tools/gpx_map_match.py`), Saarland region (Saarbrücken's mv-sb.de network + the two "Die PUR"
    touring loops, merged into one group per the user).
12. **Naheland Mountainbike Tours** (mtb-kh.de/touren, Flow/Panorama/Enduro) — added 2026-08-11 alongside
    the Bad Kreuznach region above. **Built**: all 3 segmented via the contiguous-run matching method
    (superseded later the same session by `tools/gpx_map_match.py`'s sequential approach, see
    `docs/trailrunde-feature.md` / the tool's own docstring for the difference and why it matters for
    tours that revisit a trail more than once).

**Lifts are complete for every already-built region that has any** (as of 2026-07-30, re-verified
2026-08-11 with the Tgantieni fix in Bike Kingdom): the tables plus the reasons for each *excluded*
lift for the pre-2026-08 regions live in `tools/add_lifts.py` — use that script's pattern for the next
region rather than writing the query again. Odenwald, Pfälzerwald, Donnersberg and Finale have no
lifts by nature. Newer regions (Sauerland/Upland, Livigno initially) still have lift gaps noted above.
Harz brought its own six on 2026-08-13 via `tools/add_harz_lifts_places.py` rather than `add_lifts.py` --
same rules, but it needed one extra guard worth copying: **two parallel lifts up the same hill look exactly
like two sections of one lift to an endpoint-distance check** (St. Andreasberg's two chairlifts have top
stations 36 m apart, and joining them produced an 850 m "lift" climbing 14 m). Orient each section
bottom-first by elevation and require the join to keep climbing.

13. ~~**Vogesen**~~ — requested 2026-08-19 ("Die Nördlichen Vogesen. Vor allem die Region rund um
    Wissembourg. Also ungefähr alles nördlich von Colmar"), **built and live the same day as TWO regions**:
    `nordvogesen` (483 trails, 592 km, 7 sub-regions, 22 places) and `suedvogesen` (474 trails, 533 km,
    9 sub-regions, 22 places, 2 lifts). Source: Trailforks, harvested through the user's own logged-in
    Chrome; raw inputs in `Material/Vogesen/`, full writeups in `docs/nordvogesen.md` and
    `docs/suedvogesen.md`.
    - **The split is a line the user drew on a map**, turned into a rule in `tools/vogesen_boundary.py`;
      each sub-region is assigned by its own centroid and every build audits every trail against it. Lac
      Blanc is in the SOUTH (7 km below the line) despite being north of Colmar; Saint-Dié is in the NORTH.
    - **Two harvesting traps worth carrying to the next Trailforks region**: the table URL's `difficulty=`
      list must name code 10 (`Severe / Black`) or the whole black tier vanishes silently, and a parent
      region's own page is not a complete index of its children (nine communes had no link, including
      Gérardmer and the Markstein bike park). Both are recorded in `build_nordvogesen.py`'s docstring.
    - **Known gaps, deliberate**: no Touren/Trailrunden in either region — Trailforks has "Routes" for
      several of these areas (e.g. "Enduro VTT De La Scherhol" at Wissembourg, and "Enduro Bressaud" which
      appears as its own 27-trail Trailforks region), and segmenting them would be a `gpx_map_match.py`
      job against the 957 trails. Markstein's difficulties are unverified (its operator page now serves an
      age gate) and it probably has two pistes we do not hold. Markstein has no lift in the data because
      OSM knows no chairlift there and which T-bar takes bikes is unconfirmed. Two trails (`dahus`,
      `mansuy`) have no geometry on Trailforks at all.
    - **Pfälzerwald overlap resolved** the user's way ("Lass die doppelten Trails im Pfälzer Wald"):
      Zeppelinhalde, Sindelsberg ZickZack and Kühnenkopf were removed from Nordvogesen. Note this cost
      ~1.8 km of line the Pfälzerwald does not have (the Trailforks versions are the longer ones) — listed
      with per-trail coverage figures in `DUPLICATE_OF_PFAELZERWALD` in `tools/build_nordvogesen.py` if it
      is ever worth reversing.

14. **Gardasee** (Riva del Garda / Torbole / Arco / Monte Baldo / Ledrotal, IT) — requested by the user
    2026-08-20, "Das sollte noch auf jeden Fall in die App". Nothing researched yet; noted here so it
    survives a device change. What to expect when it is picked up:
    - **It is big and it is spread over several valleys** — Riva/Torbole (Monte Brione, Busatte,
      Pregasina), Arco (Monte Velo, Bocca di Trat, Dosso Gorai), Monte Baldo/Malcesine on the eastern
      shore (with a cable car that carries bikes in summer), the Ledrotal and Tremalzo, plus Monte Stivo
      and the Bondone side. That is a sub-region split to decide, not one hub, and probably one region
      group in the same way Finale Ligure is one group with a dozen hubs.
    - **Lifts:** the Malcesine–Monte Baldo cable car is the obvious one and is a genuine summer bike
      lift — check the operator's own summer page for the season and the bike ticket rather than OSM's
      `aerialway:bicycle`, per the standing rule.
    - **Sources to try, in this order:** any operator/consortium page that publishes per-trail GPX and a
      grade (Garda Trentino's own bike portal, `gardatrentino.it`, and Outdooractive-backed tourism
      portals — Outdooractive needs `tools/oa_harvest_server.py`); then **Trailguide**, whose anonymous
      JSON API is now a known-good bulk source (`docs/schwarzwald.md` documents the two calls and the
      mandatory `cropTrack`) and which has good coverage of the Garda classics; then Trailforks for the
      rest. Difficulty: operator first, Trailforks as the fallback.
    - **Watch for the same trap Finale had**: the famous descents (601, Pernici, Tremalzo, Altissimo) are
      long point-to-point routes that partly run on gravel roads, and several published "tours" model the
      shuttle/lift leg as a straight line — exclude those or build them as Touren with segments, never as
      a trail.

Sourcing order for each of these: **try the operator's own site for direct per-trail GPX before
falling back to OSM + a rate-limited elevation API.** Austrian/Swiss resort sites in particular have
repeatedly turned out to expose per-trail GPX with real elevation, which beats the OSM path. See
`docs/data-sourcing-general.md` for the full method, including the Trailforks-specific workarounds
(logged-in-Chrome embedded-polyline extraction, and the lighter `/widgets/trail/` embed for pages that
now render from Mapbox vector tiles).

**Pfälzerwald note (for whenever Trailforks trails are added there)**: this region already has 437
trails and is far denser than any region `tools/gpx_map_match.py` has been validated against so far
(Livigno: 21 candidates, Bike Kingdom: ~130). Expect `strict_thresh_m` to need lowering and the loose
second pass to fire more often — see the tool's own "Tune per region" docstring note, and
`tools/test_gpx_map_match.py` for the regression-testing pattern to extend before trusting any new
segmented tour built there.
