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
- **Possibly a record/stop icon instead of the mountain-bike emoji for the RIDE button** ("Aufnahme
  Symbol und Stopp Button anstatt dem Mountainbiker") — a visual change to `#rideModeBtn`/`.ride-btn`
  (🚵 → something like ⏺/⏹), tying into the next point.
- **A separate "Tracking" concept in addition to RIDE mode** — the user explicitly said they don't yet
  know whether this is its own mode or connected to RIDE ("Ob das ein eigener Modus ist oder
  zusammenhängt weiß ich noch nicht"). Sounds like it could be about recording/saving a ridden track
  (GPX-style), distinct from RIDE's existing live GPS-follow display — but this is a guess, not
  confirmed. Needs a real discussion before any design/implementation, not just an assumption from the
  name.
- **Automated test coverage for RIDE mode is still thin and worth closing out.** What exists:
  `tests/browser/bearing.js` (the merged position-button reattach path, the pinch-vs-drag detach fix)
  and `tests/browser/controls.js` (the position cell's show/hide contract via
  `is-detached`/`is-centred-following`). What's still MISSING and only ever verified by hand/
  live-phone: `enterRideMode`/`exitRideMode` themselves (the `html.ride-mode` chrome-hiding, the RIDE
  button's own toggle), `applyRideMapOffset`/`clearRideMapOffset` (the look-ahead placement math,
  portrait AND landscape), and `updateRideInfoPanel`/`#rideInfoPanel`'s content updates. Add these once
  the info panel redesign (above) settles, so the tests aren't written against a UI that's about to
  change again.

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
10. **Geißkopf / Freiburg / Todtnau** — added 2026-08-11, links only, not researched. Geißkopf
    (Bodenmais, Bayerischer Wald) is geographically separate from Freiburg/Todtnau (both Schwarzwald)
    — do NOT assume these three form one region group like Sauerland/Upland; decide the grouping when
    picked up based on actual distance, same judgement call as Livigno/Waldmeister's "does this deserve
    its own bounding box" question. Sources:
    - https://mtbzone-bikepark.com/geisskopf/strecken — Geißkopf trail overview (same
      `mtbzone-bikepark.com` site as Willingen's — check if it has direct GPX for this park, since it
      did NOT for Willingen).
    - https://www.mountainbike-freiburg.com/trails/#trails — Freiburg-area trails.
    - https://2-cycle.de/pages/bikepark-todtnau-strecken — Bikepark Todtnau.
    - https://trailguide.net/html/Germany/Baden-W%C3%BCrttemberg/Freiburg — added 2026-08-11: a bigger
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
