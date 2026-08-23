# Backlog

General, cross-topic backlog for Trailmap — ideas, pending features and open decisions that aren't tied to
any single file. It travels with `git clone`/`git pull`, so it is the copy that survives switching device;
the assistant's own local memory notes mirror it, and this file wins if the two ever drift.

**Swept hard on 2026-08-21 at the user's own direction, and the shape of the file changed with it.** Three
things came out because they are finished, not because they were forgotten: all Touren rework (*"Touren
Nacharbeiten gibt es keine. Die sind jetzt alle gut soweit"*), the remaining region items for Gardasee,
Schwarzwald, Sauerland and Vogesen (*"für mich alles abgeschlossen"*), and rebuilding the Saalbach loops in
the Tourenbuilder. Two blocks moved to **Zurückgestellt** rather than out: the RIDE memory/crash work and
the open RIDE feature ideas. What is left at the top is what the user actually wants next.

Every built region has its own `docs/<region>.md` with the full sourcing account, so the per-region build
history is no longer repeated here — the table at the end is a status list, and git has the rest.

---

# Aktiv

## 1. Richtung App: Cloud, Accounts, App Stores

**The user's own priority as of 2026-08-21** (*"in Richtung App gehen ist weiterhin spannend"*). Approved as
a roadmap on 2026-08-02, and until now it lived ONLY in the assistant's local memory — exactly the failure
this file exists to prevent, so it is written down properly here. Full plan:
`C:\Users\flomo\.claude\plans\wie-k-nnen-wir-die-gleaming-peacock.md`.

Turn the Tourenbuilder from a local-only, `localStorage`-based feature into a cloud-backed, multi-user one,
and eventually ship through the real stores rather than only as an installable PWA.

**Decisions already locked in — do not re-open without a reason:**
- **Login via Google/Apple OAuth only**, no custom password system.
- **Supabase** as the backend (Postgres + Auth + Storage + Row Level Security), chosen specifically because
  `supabase-js` loads from a plain CDN `<script>` tag with no bundler — it fits this repo's "no build step,
  ever" architecture the same way the Leaflet tag does.
- Two tables: `routes` (Tourenbuilder exports) and `gpx_tracks` (imported GPX), **both with a nullable
  `share_token` column from day one**, even though the sharing UI ships later.
- Scope covers **both** builder-made routes and imported GPX, not just one.
- **Capacitor** for the store step — this project's first real build step (npm, native Xcode/Android Studio
  projects), planned for an isolated `mobile/` subfolder so day-to-day web dev (open `index.html`, no build)
  stays untouched. Apple mandates "Sign in with Apple" once Google login is offered (Guideline 4.8), which is
  why the auth decision above cannot be revisited cheaply later.

**Milestones**, deliberately incremental: M1 Google login + route sync (web/PWA) → M2 GPX import synced →
M3 link-sharing UI → M4–M6 per the plan file (Apple login, Capacitor, store submission).

**Prerequisites the user has not started yet, and which gate M1**: a Supabase project and the OAuth app
registrations. Confirm those exist before writing code. The user also wants to revisit hosting options when
this resumes — specifically whether a backend could replace GitHub Pages entirely.

**Still open on the Tourenbuilder itself:**
- **Reuse the gap-closing logic in the builder.** The user's own point (*"das hilft uns auch für den
  Tourenbuilder später noch"*): way-matching, the rideability check and the connection logic are the same
  building blocks when two chosen elements have to be joined. It all sits in `tools/close_loop_gaps.py`
  (Python, build time) while the builder runs in the browser, so whether the logic gets ported or
  precomputed is undecided.

## 2. Trail-Rating und Beliebtheit aus Trailforks

**Requested 2026-08-21.** Pull Trailforks' own per-trail rating and popularity into the app. The user's
reasoning is the part that should drive the design: *"gerade in größeren Regionen mit vielen Trails kann das
ein echter Mehrwert sein"*. That is a real problem statement — the Gardasee holds 916 trails and the
Pfälzerwald 805, and a difficulty colour alone does not tell a visitor which twenty are worth the day.

Concept: **`docs/trail-rating-konzept.md`**. Read it before building. It covers what the data actually is
(and is not), the sparse-votes trap, where the numbers belong in the UI, the per-region rollout, and the one
thing that must NOT happen — hiding unrated trails, which in a freshly-swept region is most of them.

## 3. Regionen, die noch offen sind

Three left; everything else on the original request list is built (table at the end).

6. **Kronplatz** / Plan de Corones (Südtirol, IT) — **researched 2026-07-30, not built: no reachable
   geometry source.** All 19 trails with official difficulties, the three areas and the 5 bike lifts
   are written up in `docs/kronplatz-recherche.md`, together with the four sourcing routes already
   tried, so don't repeat them.

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

16. **Elba** (IT) — requested by the user 2026-08-20. **They have ridden there themselves**, so the same rule
    as Madeira applies: their own account of the trails beats a scraped rating, and it is the fastest route to
    a sub-region split that matches how the island is actually ridden. Nothing researched yet, and
    deliberately little written here — what follows is the shape of the questions, not findings:
    - **Sub-regions almost certainly follow the island's three massifs**, which are separated by real
      distance rather than by a naming convention: Monte Capanne in the west, the Monte Calamita peninsula in
      the south-east (the old iron-mining area), and the Volterraio/Rio ridge in the east. Confirm against
      where the harvested trails actually fall, the same way the Schwarzwald's seven were decided.
    - **Check whether any lift takes bikes before assuming one does.** The Monte Capanne cabinovia from
      Marciana is a standing open-basket type, which is not a plausible bike carrier — but that is exactly the
      kind of assumption `docs/lifts-feature.md` says to settle from the operator's own summer page rather
      than from OSM's `aerialway:bicycle` tag or from reasoning. If nothing carries bikes, the region gets no
      `lifts` array at all, like Odenwald and Donnersberg, and the entry should say so rather than leave it
      unaccounted for.
    - **Sources: unknown, and worth ten minutes before committing to a method.** Trailforks has an Elba tree;
      whether the local operators publish per-trail GPX with an official grade is untested. Follow the
      standing order below — operator first, Trailforks only where no grade is published.

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

## 4. Test-Abdeckung: was noch keine Suite beansprucht

Swept 2026-08-21 by asking the runner itself which tracked files no suite's `@files` claims — that list IS
the to-do list for the library (`tests/README.md` says as much). Closed that night: the Trailforks
harvest/build pair (new `trailforks` suite), `close_loop_gaps.py`'s offline half (new `loopgaps` suite), and
`gpx_map_match.py`, whose own regression harness existed but **always exited 0** and was claimed by nothing
— it compares against a committed per-case baseline now and is wired in as the `gpxmatch` suite (SLOW,
~2–4 min, selected only when the matcher changes).

Still unclaimed, in rough order of what a silent regression would cost:

- **`tools/add_region_places.py`** — real logic nobody tests: the per-sub-region quota,
  `MIN_SEPARATION_KM`, the population/type ranking. A bad change here quietly makes a region's labels
  useless (it already needed a per-region cap for the Gardasee, see `docs/gardasee.md`). Offline-testable
  apart from the Overpass call.
- **`tools/region_dupe_check.py`** — the duplicate metric every new region's build leans on. The metric's
  own primitives in `pfaelzerwald_containment.py` are claimed; the wrapper is not.
- **`tools/harvest_schwarzwald_tf.py`** — superseded by `harvest_trailforks.py` for anything new. Worth
  DELETING rather than testing, once someone confirms nothing still runs it.
- One-off region scripts (`pfaelzerwald_*.py`, `vogesen_boundary.py`, `add_lifts.py`,
  `add_harz_lifts_places.py`, `gap_variants.py`) and the two harvest servers (`harvest_receiver.py`,
  `oa_harvest_server.py`). These ran once and produced committed data that IS checked (`regiondata`,
  `validate_region.py`), so testing them now buys little — leave them.


---

# Zurückgestellt

Both blocks were pushed back by the user on 2026-08-21. Kept in full: the measurements and the rejected
options are worth as much as the open questions.

## RIDE-Modus: Speicher und der weiße Bildschirm

*"Der Ride Absturz ist mir erstmal nicht so wichtig. Wir haben eine einfache Möglichkeit, es zu beheben und
im Moment tritt es nicht auf."* The "simple way" is the first bullet below — gating the empty lift pane, the
same move that saved 40 MB on the builder pane. It is ready when the crash comes back.

- **Open, measured, partly fixed: RIDE mode carries ~9x the vector-renderer memory of the normal map — the
  single most likely cause of the white-screen crashes, and the biggest remaining lever in the app.**
  **Superseded numbers below**: the table further down said 2.3x/89 MB across three panes; a re-measurement at
  a real 375x812 phone viewport with RIDE fully applied gives **33 Mpx / ~126 MB across FOUR panes**, against
  3.6 Mpx / ~14 MB north-up. Also corrected: **tiles play no part**, in either zoom direction (20 tiles vs 25,
  one level, JS heap 12–14 MB) — the earlier "tile burst" explanation was wrong, which is why `RIDE_MIN_ZOOM`
  did not close the crash. It blocked one route to the cliff; the user found the other by zooming far IN
  (2026-08-20, Donnersberg).
  Per-pane, RIDE + rotation on that viewport:

  | pane | surface | paths |
  |---|---|---|
  | overlay | 3235x3236 = 39.9 MB | 655 |
  | liftBand | 3235x3236 = 39.9 MB | 63 |
  | builder | 3235x3236 = 39.9 MB | **0** |
  | tourSegHit | 1245x1244 = 5.9 MB | 92 |

  **Done (2026-08-20): the builder pane is gone**, −40 MB, no visual change — `eachVectorRenderer` was
  materialising it by asking `map.getRenderer()` about a pane nothing used. 126 → 86 MB. **Still open, in
  order of appeal:**
  - **`LIFT_BAND_PANE` pays a full 39.9 MB for 63 short lift paths, and is a wholly empty surface in every
    region that has no lifts** — Donnersberg, Pfälzerwald, Odenwald, Finale, and now the Gardasee and
    Madeira. **Measured again 2026-08-21 with only the Gardasee active** (911 trails, 1 822 paths, no lifts)
    at a 375x812 viewport: RIDE costs 30.4 MB across two panes and **15.2 MB of that is the empty lift
    pane** — half the region's entire vector footprint for zero paths. That is the same waste the builder
    pane paid until it was removed, in a region that cannot ever use the pane at all, which makes this the
    clearest case yet for gating it on whether the active regions have any lifts. Two questions worth separating:
    whether it needs the rotation padding at all (re-rasterising 63 short lines per degree is far cheaper than
    doing it for 655), and whether it should exist when the active regions have no lifts. The pane itself
    cannot simply be dropped: the lift's grey mask must sit UNDER the trails and OVER the tiles, and Leaflet
    offers no z-index between its own tilePane (200) and overlayPane (400), which is the entire reason for a
    third pane at 350.
  - **Cap `rotationPadding()`** — declined twice (see below) and worth re-raising now that the zoom guard has
    demonstrably not closed the crash. 0.938 → 0.65 takes roughly a third off every remaining surface.
  - **The original entry's own options (a)–(d) still stand** for the elongation itself.
- **Original entry, kept for the reasoning (its numbers are superseded above): RIDE mode more than doubles the
  vector-renderer memory, and that is why zooming far out could kill the app.** **The crash is NOT closed, and "it did not happen today" is not evidence that it is.** A `RIDE_MIN_ZOOM`
  of 10 was tried and removed the same day: it stopped the user's zoom-OUT reproduction — confirmed on
  their phone, recorded as fixed — and then the crash returned zoomed far IN. After the empty builder pane
  came out (126 → 86 MB) the user tested again, zooming freely with no clamp, and reported no crash so far
  (2026-08-20). Treat that as encouraging and nothing more: a memory kill needs enough to accumulate, so a
  short session proves less than it feels like, and the same wording was already wrong once today, but the underlying overhead is untouched and will matter again for a bigger
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

## RIDE-Modus: offene Feature-Ideen

*"Ob wir den Ride Modus erweitern auf einen Aufnahmemodus oder die Strecken hintendran grau machen weiß ich
noch nicht. Kann auch mal hinter."*

- **A toggle button for map orientation, instead of driving it from the phone's own sensors.**
  Currently "Blickrichtung oben" is compass-driven (`setHeadingUp`/`handleOrientation`) and is
  auto-enabled when RIDE starts. The user wants a manual toggle instead — unclear yet whether this
  means replacing the compass entirely (e.g. a button that flips between a couple of fixed
  orientations) or just adding a manual on/off toggle *for* the existing compass-driven rotation
  (which already sort of exists as `#bearingBtn`) — needs clarifying next time, don't assume.

- **A separate "Tracking" concept in addition to RIDE mode** — the user explicitly said they don't yet
  know whether this is its own mode or connected to RIDE ("Ob das ein eigener Modus ist oder
  zusammenhängt weiß ich noch nicht"). Sounds like it could be about recording/saving a ridden track
  (GPX-style), distinct from RIDE's existing live GPS-follow display — but this is a guess, not
  confirmed. Needs a real discussion before any design/implementation, not just an assumption from the
  name.

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

- **Switch to "Straße dezent" automatically while `html.ride-mode` is on**, and back afterwards — the one
  half of the 2026-08-16 contrast request that was never done. What shipped instead was "Straße / Straße
  dezent / Straße hell" as three peer basemaps with "dezent" the first-visit default; the automatic switch
  during RIDE stayed open.

  - **Compass appears to freeze for a few seconds repeatedly while riding** — traced to intended
    behaviour, not a bug: `handleOrientation`'s bearing deliberately FREEZES (rather than resetting)
    when magnetometer readings go stale, and a bike's own metal frame/phone-mount magnets/vibration are
    the likely real-world cause of those brief dropouts — the user's own instinct that GPS reception is
    unrelated is correct. Komoot likely avoids this by driving its direction indicator mainly from GPS
    course-over-ground while moving rather than the magnetometer; this app currently prioritises the
    compass and only falls back to GPS course when there is no compass reading at all. A speed-gated
    hybrid (GPS course above some km/h, compass at a standstill) was floated as a possible fix but is a
    real design change, not implemented, not yet decided.

---

# Gebaute Regionen (Stand 2026-08-21)

28 Regionen, **4 657 Trails, 136 Lifte, 102 Touren**. Jede hat ihr eigenes `docs/<region>.md` bzw. ihr
Build-Skript in `tools/` mit der vollen Quellen-Herkunft; `python tools/validate_region.py` prüft alle.

| Region | Label | Trails | Lifte | Touren | Sub-Regionen |
|---|---|---:|---:|---:|---:|
| `gardasee` | Gardasee & Trentino | 916 | 2 | 5 | 10 |
| `pfaelzerwald` | Mountainbikepark Pfälzerwald | 805 | 0 | 42 | 9 |
| `schwarzwald` | Schwarzwald | 622 | 3 | 4 | 10 |
| `nordvogesen` | Nordvogesen | 483 | 0 | 0 | 7 |
| `suedvogesen` | Südvogesen | 474 | 3 | 0 | 12 |
| `finale` | Finale Ligure | 219 | 0 | 0 | 12 |
| `varazze` | Varazze | 195 | 0 | 0 | 7 |
| `madeira` | Madeira | 158 | 0 | 0 | 6 |
| `bikekingdom` | Bike Kingdom | 121 | 12 | 4 | 9 |
| `portesdusoleil` | Portes du Soleil | 80 | 24 | 1 | 6 |
| `sauerland` | Sauerland/Upland | 73 | 7 | 6 | 5 |
| `odenwald` | Geo-Naturpark Odenwald | 66 | 0 | 14 | 9 |
| `bikecircus` | Saalfelden Leogang | 51 | 16 | 2 | 4 |
| `harz` | Harz | 42 | 6 | 0 | 6 |
| `donnersberg` | Donnersberger Land | 41 | 0 | 1 | 4 |
| `soelden` | Bike Republic Sölden | 38 | 5 | 4 | 4 |
| `livigno` | Livigno | 31 | 7 | 1 | 3 |
| `dreilaender` | 3-Länder Enduro Trails | 29 | 5 | 0 | 4 |
| `schladming` | Bikeland Schladming-Dachstein | 29 | 3 | 0 | 3 |
| `paganella` | Dolomiti Paganella | 28 | 10 | 5 | 4 |
| `paznaun` | Silvretta Bike Arena | 26 | 8 | 2 | 3 |
| `laax` | Flims Laax Falera | 24 | 6 | 5 | 2 |
| `saarland` | Saarland | 22 | 0 | 2 | 2 |
| `waldmeister` | RadLust Waldmeister | 21 | 0 | 1 | 1 |
| `zugspitzarena` | Tiroler Zugspitz Arena | 17 | 8 | 0 | 3 |
| `serfaus` | Serfaus-Fiss-Ladis | 17 | 8 | 0 | 2 |
| `naheland` | Bad Kreuznach | 17 | 0 | 3 | 2 |
| `brandnertal` | Bikepark Brandnertal | 12 | 3 | 0 | 2 |
