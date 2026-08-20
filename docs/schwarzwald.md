# Schwarzwald — sources, decisions, open ends

Built 2026-08-20 from the three links the user had left in `docs/backlog.md` item 10 plus one more that
turned up while working (Trailguide's own API). `tools/build_schwarzwald.py` is the whole build; this file
is the *why*, and the list of things left open.

The region is **one group with seven sub-regions**, spanning the whole range from Baiersbronn in the north
to Bonndorf in the south (bounds ~47.75–48.63 N). The user named the two brackets that had to exist
(Freiburg and Todtnau), asked for the club's own name to be one of them, and delegated the rest of the
subdivision (see the standing note that a region's borders are the assistant's call to settle and record).

| sub-region | label | what is in it |
|---|---|---|
| `mtbfr` | Mountainbike Freiburg e.V. | the club's own network: everything on its site plus everything in its Trailforks association (see below) |
| `freiburg` | Freiburg & Umgebung | the other trails around the city — Kybfelsensteig gelbe Raute, Hirzberg, Brombergsattel, Nessel, Schnute, Rappeneck, Hexenwald XC … |
| `todtnau` | Bikepark Todtnau | Hasenhorn: the park runs and its chairlift |
| `elztal` | Elztal & Kandel | Waldkirch (a network of ~20 short trails), Glottertal/Kandel, Simonswald, the Vorbergzone castles |
| `sued` | Südschwarzwald | Münstertal, Staufen, Sulzburg, Zastler, Bonndorf |
| `mitte` | Mittlerer Schwarzwald | Triberg, Hornberg, Schonach, Kinzigtal |
| `nord` | Nordschwarzwald | Baiersbronn, Sasbachwalden, Seebach, Hornisgrinde |

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

The **Hasenhorn-Sessellift** is in the data on the operator's word (the park sells bike tickets for it);
OSM way 28436489 supplies the geometry only, and also happens to tag `aerialway:bicycle=yes`. Stored
bottom-first, 0,85 km, 663 → 1 013 m — which matches the tourism figures (662 / 1 026) within the DEM's
own error.

## Overlapping pairs — reported, not silently resolved

An intra-region containment scan (the method from `tools/pfaelzerwald_containment.py`) found four pairs
sharing ground. All four are still in the file; three are almost certainly legitimate and one needs a
decision:

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

## Still open

- **Trailforks harvest** — the user's own next step ("dann können wir Trailforks abgrasen"). Only the
  club's own association (12404) has been worked in so far, not the Trailforks *regions*, so expect more:
  Bikepark Todtnau's Downhill Flow, **Bikepark Bad Wildbad** (one of Germany's biggest parks, in *none* of
  the sources used here — Trailguide has no Bad Wildbad at all), and more around Freiburg itself, which the
  user already expects ("sicher gibt es weitere Trails, die auch im Gebiet Freiburg sind"). Anonymous
  Trailforks page fetches worked throughout 2026-08-20 (seven trail pages plus two listings), contrary to
  the earlier "hard login wall after ~1 trail" note — but do not count on it; the
  harvest-from-the-user's-logged-in-Chrome method in `docs/backlog.md`'s Harz entry is the reliable one.
- **Schauinsland Enduro as the region's first Tour**, per the note above.
- **Touren/Trailrunden: none built.** Neither the club nor the bikepark publishes a combination route, and
  Trailguide's long entries ("Schauinsland-Staufen" 14,9 km, "Ganterweg & Brosiweg" 22,8 km) are single
  descents/traverses, not routes assembled from named trails — so they are plain trails, not `loop: true`.
- **Lifts beyond Hasenhorn.** The Schwarzwald's other summer lifts (Schauinsland-Bahn, Kandel, the
  Belchen cable car) were not researched; whether any of them carries bikes in summer is an operator
  question, and OSM's `aerialway:bicycle` tag is not an answer (it was wrong in both directions in
  Serfaus).
