# Schwarzwald — sources, decisions, open ends

Built 2026-08-20 from the three links the user had left in `docs/backlog.md` item 10 plus one more that
turned up while working (Trailguide's own API). `tools/build_schwarzwald.py` is the whole build; this file
is the *why*, and the list of things left open.

The region is **one group with ten sub-regions and 619 trails**, spanning the whole range from Lörrach to
Pforzheim (bounds 47.554–48.965 N). It was built in two passes on the same day: 119 trails from the
operator/Trailguide sources below, then a **Trailforks sweep** that added 500 more and forced the
subdivision to be redrawn — the original "Südschwarzwald" had been holding everything from the
Markgräflerland to Bonndorf, 60 km apart. The user named the two brackets that had to exist (Freiburg and
Todtnau), asked for the club's own name to be one of them, and delegated the rest (see the standing note
that a region's borders are the assistant's call to settle and record).

| sub-region | label | trails | what is in it |
|---|---|---|---|
| `mtbfr` | MTB Freiburg e.V. | 31 | the club's own network: its site plus its Trailforks association |
| `freiburg` | Freiburg & Umgebung | 39 | the other trails around the city — Kybfelsensteig, Hirzberg, Brombergsattel, Rappeneck, Hexenwald XC … plus the Schauinslandbahn |
| `todtnau` | Bikepark Todtnau | 3 | Hasenhorn: the park runs and its chairlift |
| `elztal` | Elztal & Kandel | 52 | Waldkirch, Glottertal/Kandel, Elzach, Simonswald, the Vorbergzone castles |
| `markgraefler` | Markgräflerland & Hotzenwald | 69 | Lörrach, Wiesental, Badenweiler, Münstertal, Bad Säckingen, Waldshut |
| `hochschwarzwald` | Hochschwarzwald | 28 | Feldberg, Titisee, Schluchsee, St. Blasien, Bonndorf, Wutach |
| `ortenau` | Ortenau & Kinzigtal | 104 | Offenburg, Gengenbach, Oberkirch, Oppenau, Haslach, Wolfach, Lahr |
| `mitte` | Mittlerer Schwarzwald | 57 | Triberg, Hornberg, Schonach, St. Georgen, and the Baar to Rottweil |
| `nord` | Nordschwarzwald | 133 | Baiersbronn, Freudenstadt, Baden-Baden, Murgtal, Sasbachwalden, Kniebis |
| `enztal` | Enztal & Nordrand | 103 | Bad Wildbad, Calw, Pforzheim, Dobel, Bad Herrenalb, Nagold, Neuenbürg |

**`mtbfr` is the one organisational bracket among six geographic ones**, on the user's own call
(2026-08-20): "Das gehört alles mindestens zum Mountainbike Freiburg e.V., was auch ein guter Name für die
Unterregion wäre." Membership is therefore "is this trail the club's" — the union of its own site and its
**Trailforks association 12404**
(`trailforks.com/trails/all/?association=12404&activitytype=0`, mirrored as
`Material/Schwarzwald/trailforks_association_12404.html`). Two consequences worth knowing before
"correcting" them: the club's Ortsgruppen trails (Woody at Waldkirch, Birdy/Turbo/Volles Rohr at
Emmendingen) are in this bracket and **not** in `elztal`, and Schauinsland-Staufen runs 20 km out of the
city into the Markgräflerland. Six trails join it from the association that the club's own site does not
list at all (Holzschlägermatte, Kybfelsensteig, Kandel Höhenweg, Präsident Thoma, Schneeburg,
Schauinsland-Staufen), and three more exist *only* there — see below.

## Sources, and which one wins

**1. Mountainbike Freiburg e.V. — the operator for Freiburg, and the only source that publishes both
geometry and difficulty.** `mountainbike-freiburg.com/trails/<slug>/` carries a `window.mtb_trails`
JSON blob with, per trail, up to two downhill GPX and two uphill GPX plus `color_dh1`/`color_dh2` —
`#46b414` green, `#148cf0` blue, `#dc1313` red, `#000000` black, i.e. exactly this app's four colours.
The GPX all carry real `<ele>` (no placeholder zeros), so no DEM lookup was needed for any of them.
23 files are mirrored in `Material/Schwarzwald/Freiburg/`.

Per the standing operator-wins rule this beats Trailguide, and it matters — the two disagree for six
trails: Hubbelfuchs (club red / TG blue), Al Natura (green / blue), Schädelwäg (black / red), Floh-Trail 1
(green / blue), Floh-Trail 2 (blue / red), and Turbo/Volles Rohr, whose grades Trailguide has **swapped**
relative to the club's own page.

Two club files are not used as they stand:

- `MTB-Freiburg-eV-Al-Natura-Uphill.gpx` is the *downhill* line despite its name (4 m of climb against
  134 m of drop) and is used as Al Natura's own geometry.
- `mtb-freiburg-turbo-downhill.gpx` is a 7-point, 118 m fragment. Trailguide has the same corridor at
  242 m with every club point within 13 m of it, so Turbo takes Trailguide's line and keeps the club's
  name and grade.
- `mtb-freiburg-borderline-uphill-final-latest.gpx` is served on **both** the Borderline and the
  Hubbelfuchs page — it is the shared Rosskopf climb. Built once, as "Borderline Uphill".

**1b. The club's Trailforks association, for the trails its own site does not list.** Three are built
from Trailforks geometry (the `encodedpath` on the trail page, Google-polyline encoded at precision 5,
readable from a plain anonymous fetch on 2026-08-20) with elevation from OpenTopoData, and Trailforks'
own **rating** as the grade — the documented fallback where no operator grade exists. Note the rating, not
the "voted" figure: Blaue Raute and the Kohlerhau connector are rated green and voted blue.

| from the association | grade | note |
|---|---|---|
| Blaue Raute (3,16 km) | green | 61 % of it runs within 25 m of Badish Moon Rising, shape "unclear" — a genuine parallel line on the Kybfelsen, not a duplicate |
| K-Trail (2,15 km) | green | **replaces Trailguide's "Hirzberg Highway"** (2 042 m, 94 % subsumed, same line): the club's own name for it wins |
| Rodelbahn – Kohlerhau Connector (857 m) | green | **not built** — it lies entirely (containment 1.00) inside Trailguide's "Schauinsland Gipfel – Kohlerhau" (2 886 m), so it would be a second line over a third of that trail |

Two more association entries are deliberately out: **Schauinsland Enduro**, which Trailforks itself calls a
*multi trail* — a route stitched from other trails, i.e. a Trailrunde candidate (`loop: true` plus
`trailSegments`, matched with `tools/gpx_map_match.py`) and not a trail of its own — and
**Trimm-Dich-Pfad**, tagged `hike`.

**1c. The Trailforks sweep — 500 of the region's 619 trails.** `tools/harvest_schwarzwald_tf.py` takes the
trail table of every Schwarzwald district (paginated; a district table DOES include its communities'
trails, verified against the child regions) and then one page per trail. Two things make this cheap and
self-checking, both carried over from the Vogesen build:

- A trail page carries the line **twice** — the `encodedpath` polyline and an `ElevationChart` config
  whose points hold lat/lng, real elevation and cumulative distance. The profile is what gets built, so
  the sweep needed **no elevation API at all**; the two lengths are compared per trail and **all 602
  agreed within 60 m**. Watch the point pattern: `lat`/`lng` come **quoted** in this config, and an
  unquoted-number regex silently returns no profile at all — 12 trails were harvested that way before it
  was noticed.
- The `difficulty=` list in the table URL must name **every** code including 10 (`Severe / Black`), or the
  whole black tier disappears silently. This build passes `3,4,9,5,1,7,2,6,8,10,11,12`.

Anonymous `curl` worked throughout (~700 pages) — but `urllib` gets a 403 with the identical User-Agent,
so fetch with curl and do not spend time on which header it dislikes.

**How the sweep decides what is in and where it goes.** A district is an administrative box, not a
massif: the Enzkreis reaches into the Stromberg, the Ortenaukreis into the Rhine plain, Emmendingen onto
the Kaiserstuhl. So the sweep ignores the district it came from and assigns every trail to the sub-region
of the **nearest anchor town** (`tools/schwarzwald_anchors.py`, 103 anchors), dropping anything further
than 12 km from every anchor as "not in the Schwarzwald". One rule does the assigning and the excluding at
once, which is what makes the exclusions reviewable — the build prints all 30, and they are the
Kraichgau/Stromberg cluster east of Pforzheim (the whole "Eppinger-Linie" set), two Rhine-plain trails and
three isolated Hotzenwäld/Heckengäu ones.

Duplicates are caught twice: by **name** (only within 5 km — there are three separate "Jägerpfad"s, two
"Kammweg"s and two "Woody"s in these tables, and matching on the name alone dropped the far ones as
duplicates of the near one) and by **geometry** (the project's containment metric: 60 % of the shorter
line's points within 25 m, shape "subsumed"). 40 name and 36 geometry duplicates were dropped this way,
the already-built trail always winning because it came from the operator or from Trailguide's cropped
line. Four trails under 80 m and three whose pages carry no line at all are also out, all listed by the
build.

**2. Trailguide (trailguide.net) for every trail no operator publishes.** Its own API answers
anonymously, no key and no login:

```
GET https://trailguide.net/a?query={"action":"session.create"}                     -> data._id  (the sid)
GET https://trailguide.net/a?query={"action":"trails.get.query","tracks":true,
        "cropTrack":true,"trailsToLoad":[1553,1552,...]}     header: tg-sid: <sid>
```

Trail ids (`sequence`) come from the region listing pages, which are plain server-rendered HTML:
`/html/Germany/Baden-Württemberg/Freiburg` (102 trails) and `.../Karlsruhe` (11, of which the 6
Baiersbronn ones are Schwarzwald). Each returned trail carries `name`, `place`, `county`, `color`,
`meters` and `latlng.points` with `lat`/`lng`/**`alt`** — so no DEM lookups here either (four trails have
a handful of points without `alt`; `build_profile` interpolates those).

**`cropTrack: true` is not optional.** Without it, a trail whose track was recorded as part of a longer
ride comes back with that whole ride's geometry: "Wurzi" is 776 m of trail against 1 983 points spanning
several kilometres, and four Waldkirch trails share one parent track. With it, every returned line's own
measured length matches its stated `meters` to the metre — checked for all 108 fetched.

**3. Bikepark Todtnau: OSM and Trailforks, because the park publishes no GPX at all.** The operator's own
pages (`2-cycle.de/pages/bikepark-todtnau-strecken`, `bikepark-todtnau.de` — the same Shopify site) give
the three runs, their grades and their figures, and nothing else: Downhill (black, 2,7 km / 450 hm),
Wildride (red, 2,6 km / 450 hm), Downhill Flow (red, 2,6 km / 450 hm).

Geometry per trail from whichever source has the more complete line. They trace the same corridor —
median deviation 2,5 m for Downhill, 5,1 m for Wildride — so this is a coverage choice, not a
which-line-is-right one:

- **Wildride → Trailforks** (`bikepark-todtnau-wildride`, 2 339 m). It *contains* OSM's way 128871487 and
  adds 800 m at the bottom, so OSM's copy was dropped automatically as a duplicate.
- **Downhill → Trailforks** (`bikepark-todtnau-racetrack`, 1 525 m), **on the user's own call**
  (2026-08-20): "Bikepark Todtnau Racetrack ist eigentlich der gleiche Trail wie Downhill in Todtnau.
  Lösch den jetzigen Downhill und nenn den anderen schwarzen dann einfach Downhill." The first build had
  used OSM's way 35830938 (1 657 m) because it reaches the valley station while Trailforks' line stops
  100 m short of it; the sweep then built the Trailforks line as a second trail under its own name. The
  Trailforks one now carries the name and keeps the old id `sw_todtnau_downhill`.
  Worth knowing why the duplicate check did not catch that pair by itself: the two lines trace the same
  corridor (median deviation 2,5 m) but each covers 100–200 m the other does not, at **opposite** ends,
  and the containment metric with its "subsumed" shape test is deliberately strict about exactly that.

**Both are well short of the operator's stated distance** (1,64 km against 2,7; 2,34 km against 2,6–3,0)
and `len`/`down` are therefore the measured figures of the line we actually draw, not the operator's — the
same call the Harz's Braunlage Freeride already carries (2,11 km of line against ~3 400 m stated). Do not
"fix" this by writing the operator's number next to a line that is 40 % shorter.

**Downhill Flow is deliberately not built.** No GPX from the operator, not mapped in OSM, and the
Trailforks region `todtnau` carries only the two runs above. Same decision as the four Harz runs dropped
on 2026-08-14: no line rather than an invented one. Add it when a real track turns up.

## Lifts — three in, two out, each on the operator's word

OSM's `aerialway:bicycle` tag decides nothing here (it was wrong in both directions in Serfaus); the
operator's own summer page does. 52 aerialways over 500 m sit in this bounding box, and four were worth
checking:

| lift | | why |
|---|---|---|
| **Hasenhorn-Sessellift** (Todtnau) | in | the bikepark's own uplift, bike tickets sold. 0,85 km, 663 → 1 013 m, matching the tourism figures (662/1 026) within the DEM's error |
| **Schauinslandbahn** (Freiburg) | in | its own "Biking" page states the fare — "12,00 € zzgl. Tarif pro Person. Pro Kabine können maximal 2 Fahrräder mitgenommen werden" — and it is the uplift for Badish Moon Rising and the Canadian. 3,52 km, 477 → 1 210 m |
| **Feldbergbahn** (Seebuck) | in | the Liftverbund's own summer page: 8-seat cabins with room for "Kinderwagen, Rollstuhl, Fahrrad". 0,91 km, 1 282 → 1 442 m. Note OSM still tags it `chair_lift` while the operator describes cabins — same line either way |
| **Belchen-Seilbahn** | **out** | this is the case the rule exists for: OSM tags it `aerialway:bicycle=yes`, but the operator's price list carries no bike fare and its site says nothing about carrying bikes |
| **Sommerbergbahn** (Bad Wildbad) | **out** | it carried bikes two days a week *for the bikepark*, and that park's operating company stopped on 2025-12-31 (below) |

## Bikepark Bad Wildbad: the runs are in, the park is not

Adventure-Bikepark GmbH, which ran the six runs at Bad Wildbad, **ceased operating on 2025-12-31** — the
investor's decision, a surprise to the park's own management, with the town since looking at a
club/community model. The runs exist on the ground and Trailforks holds their lines, so they are in the
region (in `enztal`) — but they carry **Trailforks grades, not an operator's**, and the park has no lift
in the data, because the bike transport was part of the operation that stopped. If it reopens, its own
published grades take precedence over Trailforks', per the standing rule.

## Overlapping pairs — reported, not silently resolved

An intra-region containment scan (the method from `tools/pfaelzerwald_containment.py`) over the first
119 trails found four pairs sharing ground; the Trailforks sweep then ran the same test against every
candidate and dropped 36 more (listed by the build). These four are deliberately still in the file — in
each case the operator publishes both lines:

| pair | containment | reading |
|---|---|---|
| Floh-Trail 1 (278 m) in Floh-Trail 2 (293 m) | 1.00 | two lines side by side in one small field; the club publishes both, with different grades |
| Canadian Uphill 1 (4 546 m) in Canadian Uphill 2 (5 266 m) | 0.95 | same climb, Uphill 2 continues 720 m higher to the Sektion-0 start; both are the club's own files |
| ~~Schöni Trail in Shooter~~ | 0.94 | **settled while building: one trail, two names.** Trailforks has it a third time as "Schöni DH" (2 266 m), whose description — "vom Gipfel des Schönbergs … bis zum Schützenhaus" — is the club's Schöni. Trailguide's "Shooter" is dropped; the club's name and grade stand. Worth noting that Trailforks' *voted* difficulty (red) sides with Trailguide against the operator's blue, which the operator-wins rule settles. |
| Turbo (241 m) in Volles Rohr (257 m) | 0.75 | the two Emmendingen jump lines, side by side; the club publishes both |

`tools/region_dupe_check.py schwarzwald` finds no overlap with any other shipped region.

## Deliberately out of scope

- **Hardheim** (4 trails) and **Ettlingen** (1) come back in Trailguide's Karlsruhe listing but are not
  Schwarzwald. Hardheim is Odenwald — worth a look next time `odenwald.json` is touched.
- **"Sohlacker – Kybfelsen – Canadian Trail Sektion 0"** (Trailguide, 1 608 m) is dropped: its last 381 m
  *are* our "Canadian Sektion 0" and the rest is the approach "Kybfelsensteig" already covers.
- **Geißkopf** stays out — it is in the Bayerischer Wald, 300 km east, and was only ever bracketed with
  these two links by accident of when they were collected (backlog item 10).
- **30 Trailforks trails east and west of the range**, dropped by the anchor rule and each printed by the
  build with its distance: the Kraichgau/Stromberg cluster beyond Pforzheim (the whole "Eppinger-Linie"
  set, Maulbronn, Sternenfels, Knittlingen, Zaberfeld), two Rhine-plain trails near Kenzingen, and three
  isolated ones in the Heckengäu and above the Klettgau. Widening `MAX_ANCHOR_KM` would pull the
  Stromberg in; adding an anchor there would be the honest way to include it, and it is not Schwarzwald.
- **Trailguide's "Hardheim" (4 trails)** is Odenwald and this app already ships an `odenwald` region —
  worth a look next time that one is touched.

## Touren — four: two matched, two assembled in the Tourenbuilder

`tools/build_schwarzwald_tours.py`, run **after** the trail build (which would otherwise overwrite the
`trailSegments` it adds).

The user asked for "die Schauinsland Enduro Tour", from a report of mine that had called it a Trailrunde
candidate. **That was wrong**: Trailforks' "Multi Trail" label means multi-USE (its own alternateName list
reads "Schauinsland Enduro Multi-Use Trail"), not "assembled from several trails". It is a plain 2,8 km
descent and the sweep already built it as one. What this region does have is Trailforks **routes** —
recorded rides, each with an `encodedpath` and an `ElevationChart` like a trail page, and each genuinely a
combination of the region's own trails:

| Tour | km | named | built from |
|---|---|---|---|
| Canadian & Borderline | 19,30 | 84 % | **Tourenbuilder** — Canadian Uphill 1 → Canadian Trail → Borderline Uphill → Borderline |
| Hubbelfuchs · Kammweg · Borderline | 40,05 | 83 % | **Tourenbuilder** — 12 stretches incl. Hubbelfuchs, Fritzis Ende, Kammweg, Jägerwegle, Borderline |
| Schlossberg · Nesselplatz · Rosskopf | 29,15 | 35 % | matched from the Trailforks route |
| Freiburger Dreierlei | 35,43 | 46 % | matched from the Trailforks route |

### The two that are assembled, not matched

`tools/build_schwarzwald_builder_tours.py`, from the app's own Tourenbuilder exports in
`Material/Schwarzwald/builder_*.json`. Both had been matched first and both came out wrong in ways the
recording cannot fix — Canadian & Borderline jumped 582 m back to the Borderline's start and ran 12 % over
its own track, Hubbelfuchs · Kammweg · Borderline jumped 401 m, and about a fifth of their named stretches
were fragments the matcher had drifted into between parallel lines (on the Rosskopf the club's uphill route
runs beside and across the trail it serves). The user's call, after seeing it on the map: state the route
instead of guessing it.

So the ride order is given, and nothing here matches anything:

- **A named stretch is that trail's own geometry**, clipped between the two points the builder cut it at
  (it splits an element at junctions, so an element's `km` is often less than the whole trail) and oriented
  by the builder's `reversed`. Measured afterwards: 0,0 m from the trail for every stretch.
- **A connector is read out of the ORIGINAL recording**, never routed and never invented — the user's own
  instruction for the 2,3 km through Freiburg ("Den Weg durch die Städt kannst du ja aus der Originaltour
  lesen"). Three were filled that way: 2 770 m, 1 540 m, 3 702 m. **Picking the right PASS matters**: a loop
  recording comes past the same place up to four times, so "walk from the point nearest a to the point
  nearest b" returned 10,4 km of recording for a 2,3 km gap on the first attempt. Every point within 60 m
  of each end is a candidate and the shortest stretch wins, gated at 3× the straight-line gap.
- **What the recording does not cover goes to `tools/nearby_trail_connector.py`** afterwards, the user's
  confirmed procedure: four short gaps (78–152 m) and — the one exception to the GPX-first rule — the
  **875 m between Fritzis Ende and Baden To The Bone Uphill**, where the recording has no point within 60 m
  of the uphill's start as the builder set it, so a chain of ways closed it instead. Worth a look on the
  map before it is taken as settled.
- **The return leg to the start is left open** in Canadian & Borderline (2 448 m, not in the recording). A
  Trailrunde does not have to be geometrically closed and the app draws no line from the last segment back
  to the first, so nothing is missing on screen — and the gap count deliberately ignores that wrap-around.
- Neither Tour has a gap over 30 m left; the largest are 29 m and 21 m, which is the GPS-noise band the
  procedure leaves alone.

**Three scripts, in this order, every time** — the first rewrites the region from scratch and would
otherwise drop the Touren:

```
python tools/build_schwarzwald.py
python tools/build_schwarzwald_tours.py          # the two matched Touren
python tools/build_schwarzwald_builder_tours.py  # the two assembled ones
python tools/nearby_trail_connector.py --region "Trailmap App/regions/schwarzwald.json" --loop <id> --gap <i ...> --write
python tools/update_region_versions.py
```
| ~~Banden Ride~~ | 37,8 | 59 % | **not built**: its recording jumps 2 593 m in one step — 6,9 % of the Tour, drawn as a straight line across Freiburg. Same call as the three Paganella marathon routes. The other four have no step over 619 m (1,5 %) |

Four things about the method are worth keeping:

- **The named stretches carry their TRAIL's geometry, not the recording's** — and getting this wrong the
  first time is the one defect a user actually saw: with `fill_connectors` every segment kept the Tour's
  own recorded points, so two Tours riding Borderline drew two slightly different Borderlines and neither
  matched the trail (the user, 2026-08-20: "Die Geo von Borderline ist aber nicht identisch"). Measured
  then: 0 of 35 named segments on their trail, mean median offset 4,1 m, 11 of them over 5 m. Now: **0,0 m
  for all 35.** Worth knowing for the next check of this kind — a point-for-point "is this an exact slice"
  test is the WRONG measure and reported four healthy regions (Bike Kingdom, Laax, Paganella, Portes du
  Soleil) as 0 %: in all 65 Bike Kingdom segments the only points not on the trail's own list are the two
  interpolated clip endpoints, and the user's own spot check was right. Measure the DISTANCE.
- **Two of the four are assembled from the Tourenbuilder, not matched** — see the Touren section above for
  why and how. The matcher's own failure mode is worth keeping in mind for the next region: it extends a
  stretch to the trail's real end where the recording had already turned off (`endpoint_extend_m`, 60 m),
  so the next stretch can start *behind* the last one's end, which reads as a jump backwards and inflates
  the Tour's length.
- **The boundary gaps are closed, with `tools/nearby_trail_connector.py`** — the user's own confirmed
  procedure (`docs/nearby-trail-connector.md`), not `close_loop_gaps.py`'s tier system. 34 gaps over 30 m
  across the four Tours, every one solved: 31 by "ein Weg erreicht beide Seiten", 2 by
  "Weg folgen und kappen", 1 by a chain of ways — and every applied bridge at **weglos 0 m**, i.e.
  entirely on OSM ways. What is left is the 10–29 m band the procedure deliberately leaves alone as GPS
  noise ("Die Sprünge sind zwar unschön, aber unvermeidbar"). Two things this cost, both fixed rather
  than worked around: the tool **left `len`/`up`/`down` in `lineTrails` untouched** while the line itself
  grew by its bridges (Canadian & Borderline wrote 22,18 km and kept claiming 21,35), and
  `close_loop_gaps.py` was doing **one Overpass query per gap**, which the user spotted from the runtime
  — `nearby_trail_connector` had had a batched prefetch all along.
- **`fill_connectors`, not `build_segments`.** Both were measured. Snapping each named stretch onto its
  trail's own stored geometry (what the Pfälzerwald rederive does) opened joints of up to **746 m**
  between consecutive segments — each is drawn as its own polyline, so that is a hole in the Tour — and
  inflated two of the five past their own stated distance (Canadian & Borderline came out 26,4 km against
  21,3). Keeping the recording's own points means every Tour's length now matches Trailforks' stated
  distance to within 100 m, the concatenation invariant holds trivially, and the remaining "joints" are
  just the recording's own point spacing. The price is the one snapping exists to avoid: where recording
  and trail differ by a few metres, the Tour draws its own line beside the trail's.
- **A route page renders its ElevationChart config TWICE**, so the parsed points come out doubled. Every
  route's line was exactly twice its stated distance and every segment list printed twice — which on the
  map would be a Tour riding each trail twice. `dedupe_halves()` cuts it, with an exact
  first-half-equals-second-half test so a real out-and-back is unaffected. Trail pages do not do this,
  which is why the sweep never hit it.
- **Direction settles what distance cannot.** On the Rosskopf the club's uphill route repeatedly crosses
  and runs beside the trail it serves, so a distance-only matcher alternates between "Borderline" and
  "Borderline Uphill" all the way down the descent. Tightening the strict threshold from 12 m to 8 and to
  6 m was measured and fixed nothing — it only lowered how much got named at all. `drop_wrong_direction()`
  rejects an attribution to an `uphill: true` trail on a stretch where the route loses more than 20 m,
  which removed exactly the wrong labels (2 in the first Tour, 1 in the second) at a cost of four points
  of named share.
- **A single straight step over 800 m rejects the route.** The three clean routes have no step over
  300 m at all; two have one of 355 m and 619 m, which read as an unmapped connection between two
  recorded points. Banden Ride's 2 593 m does not.
- **A candidate list of 618 trails does not finish.** The matcher measures every route point against every
  point of every candidate, so each route is first restricted to the trails whose bounding box overlaps
  its own (`near_route`, ~30 of 621). No result changes; without it the match does not complete.

## Still open

- **More Trailforks routes.** Four of the five found were built, all from the two Freiburg-area regions' own
  `/routes/` listings; the other districts' listings were not read. `Schauinslandstaufen` and `Titisee` are two more
  that exist. Note the long Trailguide entries ("Schauinsland-Staufen" 14,9 km, "Ganterweg & Brosiweg"
  22,8 km) are single descents, not assembled routes, so they stay plain trails.
- **The Tours ride no lift.** All five climb by bike, which is why none has a lift segment even though
  lifts were in the candidate list. A Tour riding the Schauinslandbahn would be a genuinely different
  kind of route for this region and none of the five is one.
- **Two trails disagree badly with OSM** and are the ones to look at first if anything looks wrong on the
  map: `sw_mullerweg` (13 % of its points within 25 m of any OSM way, median 99 m off) and
  `sw_lotenbachklamm_1` (24 %, median 60 m). Every other Hochschwarzwald trail is at 87 % or better, and
  all 31 of the club's are at 98 %+. A low score means "look at this one", not "this one is wrong" — a
  purpose-built line OSM has not mapped scores low legitimately.
- **Three Trailforks trails carry no line on their own page** (`Buhlbachwegle`, `Hof Dicke Downhill`,
  `Ottenbronn Downhill`) and four are under 80 m; both sets are printed by the build and stay out.
- ~~**Bikepark Todtnau's "Downhill Flow"**~~ — **closed, not open.** No geometry in any source checked
  here (operator, OSM, Trailforks) and none found by the user either, who looked for a GPX independently
  and settled it on 2026-08-20: "Für Downhill Flow hab ich auch keine GPX gefunden. Lassen wir halt
  weg." Same standing as the four Harz runs dropped on 2026-08-14 — do not re-open without a genuinely
  new source, and do not draw a line for it.
- **Difficulty for the swept trails is Trailforks' own rating**, which is the documented fallback and
  correct here — these are community trails without an operator. The exceptions to keep an eye on are
  the ones with a real operator: Todtnau (grades taken from the operator) and Bad Wildbad (operator gone,
  see above). If a park publishes its grades again, they win.
- **Two overlap questions the sweep raised but did not settle**: "Präsident Thoma Weg" reads as 98 %
  contained in "El Presidente" and "Kandel Cruise" as 98 % in "Bodyguard" — both were dropped as
  duplicates, but the Kandel has several named lines running close together and it is worth a look on the
  map whether those are really one trail each.
