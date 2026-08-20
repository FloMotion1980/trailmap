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

- **Downhill → OSM** (way 35830938, 1 657 m). Trailforks' `bikepark-todtnau-racetrack` starts exactly at
  the top station but stops 100 m short of the valley; OSM starts 200 m below the top station and reaches
  the valley station.
- **Wildride → Trailforks** (`bikepark-todtnau-wildride`, 2 339 m). It *contains* OSM's way 128871487 and
  adds 800 m at the bottom.

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

## Still open

- **Touren/Trailrunden: none built.** No operator here publishes a combination route, and the long
  Trailguide entries ("Schauinsland-Staufen" 14,9 km, "Ganterweg & Brosiweg" 22,8 km) are single
  descents/traverses, not routes assembled from named trails — so they are plain trails, not
  `loop: true`. The one real candidate is **"Schauinsland Enduro"**, which Trailforks itself calls a
  *multi trail*: with 619 trails now in the region it is a good `tools/gpx_map_match.py` job.
- **Trailforks "Routes"** were not harvested at all — only its trails. Several of these districts have
  them, and they are the same Trailrunde-shaped work as the item above.
- **Two trails disagree badly with OSM** and are the ones to look at first if anything looks wrong on the
  map: `sw_mullerweg` (13 % of its points within 25 m of any OSM way, median 99 m off) and
  `sw_lotenbachklamm_1` (24 %, median 60 m). Every other Hochschwarzwald trail is at 87 % or better, and
  all 31 of the club's are at 98 %+. A low score means "look at this one", not "this one is wrong" — a
  purpose-built line OSM has not mapped scores low legitimately.
- **Three Trailforks trails carry no line on their own page** (`Buhlbachwegle`, `Hof Dicke Downhill`,
  `Ottenbronn Downhill`) and four are under 80 m; both sets are printed by the build and stay out.
- **Bikepark Todtnau's "Downhill Flow"** still has no geometry in any source checked (operator, OSM,
  Trailforks). Add it when a real track turns up; do not draw one.
- **Difficulty for the swept trails is Trailforks' own rating**, which is the documented fallback and
  correct here — these are community trails without an operator. The exceptions to keep an eye on are
  the ones with a real operator: Todtnau (grades taken from the operator) and Bad Wildbad (operator gone,
  see above). If a park publishes its grades again, they win.
- **Two overlap questions the sweep raised but did not settle**: "Präsident Thoma Weg" reads as 98 %
  contained in "El Presidente" and "Kandel Cruise" as 98 % in "Bodyguard" — both were dropped as
  duplicates, but the Kandel has several named lines running close together and it is worth a look on the
  map whether those are really one trail each.
