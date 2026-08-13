# Region backlog

Ordered list of bike regions the user has asked to add to Trailmap, in the order they were
requested (as of 2026-07-26 unless noted). Mirrors the assistant's own local memory note of the
same name so the plan survives a switch to a different device — the memory file only lives on one
machine, this file travels with the repo. Keep both roughly in sync when the backlog changes;
if they drift, this file is the one to trust.

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
9. **Harz** (5 bike parks) — added 2026-08-11, **explicitly flagged by the user as having NO GPX
   anywhere** ("Leider komplett ohne gpx"), so this one needs the OSM+elevation-API fallback path (or a
   headless-Chromium Trailforks/embedded-map check per park before assuming OSM is the only option)
   rather than the usual operator-GPX-first approach. Not grouped into sub-regions/one-region yet —
   five separate physical locations, decide when picked up whether they share a region group at all
   (spread across the whole Harz, not one valley like Portes du Soleil/Livigno). Sources:
   - https://www.bikepark-andreasberg.de/trails — Bikepark St. Andreasberg.
   - https://www.bikepark-hahnenklee.de/bikepark — Bikepark Hahnenklee.
   - https://bikepark-bodetal.de/ — Bikepark Bodetal.
   - https://www.outdoorwerkstatt.eu/ — Racepark Schulenberg.
   - https://www.wurmberg-seilbahn.de/sommer.html — Wurmberg-Seilbahn summer/bike offering.
   Not yet researched beyond the links themselves.
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
