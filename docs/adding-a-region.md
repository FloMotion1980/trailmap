# Adding a region — runbook

Written 2026-07-28 so a fresh session can build the next region without re-deriving the method. The
mechanics live in `tools/trailmap_pipeline.py`; this file is the order of operations, the decisions that
need the user, and how to know you are done.

Read first: the region-catalog architecture in `CLAUDE.md`, plus `docs/lifts-feature.md` if the region gets
lifts and `docs/data-sourcing-general.md` if a source site blocks bots.

## A region is FOUR things, not one

Added 2026-07-29, after Bike Kingdom was reported "done" three times and each time something was missing —
first the lifts, then the tours, then the place labels. The trails are the biggest piece of work, which is
exactly why they get mistaken for the whole job. **A region is not finished until all four are present or
consciously ruled out:**

| # | Piece | Where it lives | Source of truth | Skip only when |
|---|---|---|---|---|
| 1 | **Trails** | `lineTrails` + `trailGeo` + `elevationProfiles` | operator GPX, else OSM; difficulty from the operator or the user | never |
| 2 | **Lifts** | `lifts` | the operator's own summer lift list — never OSM's bike tag | the region has no lifts (Odenwald, Pfälzerwald, Donnersberg) |
| 3 | **Tours** | `loop: true` entries + `trailSegments` | the operator's published routes, matched against pieces 1 and 2 | the operator publishes none |
| 4 | **Places** | `places` | OSM `node[place]`, never a typed coordinate | never — a region with no labels is unreadable when zoomed out |

Say explicitly which of the four are done and which are ruled out when reporting a region as finished.
"121 trails and 12 lifts" reads like completion while `places: []` is still sitting in the file.

**Checklist per piece**

1. **Trails** — geometry from the best source (see step 1 below), one entry per trail the user wants (not per
   section — collapse "Sektion 1-4" into one line, but only where the sections actually connect, see the
   Rock'n'Roll trap in `docs/trailrunde-feature.md`), difficulty on this app's four-colour scale, `len`/`up`/
   `down` from the operator where published, `uphill: true` decided from ascent-vs-descent rather than the
   name.
2. **Lifts** — research which lifts run in summer *and* carry bikes, get geometry from OSM by an **anchored**
   name or `ref` match, store bottom-station-first, backfill `baseEle`/`topEle`. `docs/lifts-feature.md`.
3. **Tours** — match the route's GPX against the region's own trails and lifts so each stretch is attributed;
   never a single flat line if the operator's route is made of named trails. `docs/trailrunde-feature.md`
   has the four matching traps that each drew a wrong line.
4. **Places** — take the names the region is actually described by: the valley towns, the lift bases, the
   points where trails start and end, and whatever appears in a tour's own title (the Pfälzerwald tours are
   literally named after villages). Coordinates come from `node[place][name=...]` via Overpass — a
   hand-typed Samnaun sat 1 460 m from the village. Sanity-check each candidate by its distance to the
   nearest trail in that region and drop the ones far away; OSM knows hundreds of `locality`/
   `isolated_dwelling` names in any Italian or Swiss hinterland, and 200 names in the woods are noise, not
   orientation. Aim for one reference point per sub-region plus the larger settlements.

## What the user has to supply

Everything else can be derived, but these cannot, and guessing at them has produced real errors:

1. **Difficulties**, whenever no official source publishes them. Donnersberg's four came from the user
   directly; Saalbach's were checked against the operator's own list. Do not invent them from trail names or
   from OSM's `mtb:scale` alone — cross-checking against OSM is fine (it matched the user exactly for
   Donnersberg), inventing is not.
2. **The sub-region split**, unless the operator's own site makes it obvious. Its URL structure often does
   (Zugspitz Arena has `/trails/ehrwald-wetterstein/…`), and Paganella's zones are named on the site.
3. **Whether the region gets lifts** at all.
4. **One region or several.** Livigno's two parks are one region with two sub-regions, and
   Winterberg/Willingen/Green Hill are one "Sauerland/Upland" — both were the user's calls, and the second
   one brackets purely geographically with no shared ticket.

Ask for these up front. Everything after that is mechanical.

## Order of operations

**1. Find the source and decide what a "trail" is.** The operator's own site is the primary source. Prefer
per-trail GPX from the operator over OSM: it carries real elevation, whereas OSM carries none and needs
rate-limited DEM lookups. Exclude routes whose GPX represents lift rides as straight lines — three
Paganella "marathon" routes were left out for exactly that reason (a 2.4 km straight line across the map,
and a climb figure of 1083 m against 200 m official). Those belong in the Touren/segment feature instead.

**2. Geometry and profiles.**

```python
import sys, json; sys.path.insert(0, r"D:\Trailmap\tools")
from trailmap_pipeline import *

ele = ElevationLookup()                      # only needed if the source has no usable <ele>
trails, geo, profs = [], {}, {}
for src in sources:
    entry, coords, prof = build_trail(
        trail_id="zta_blue_bird", name="Blue Bird", region="ehrwald",
        diff="blau", raw_points=parse_gpx(open(src, encoding="utf-8").read()),
        official=(3.4, 12, 410),   # operator figures win over GPX-derived ones
        elevation=ele)
    trails.append(entry); geo[entry["id"]] = coords; profs[entry["id"]] = prof

data = write_region(r"D:\Trailmap\Trailmap App\regions\zugspitzarena.json", trails, geo, profs)
print(region_summary(data))                  # counts per sub-region/difficulty + the catalog bounds
```

`build_trail` handles the traps: tolerant GPX parsing, 0.5 m point de-duplication, Douglas-Peucker at 2 m,
placeholder `<ele>0</ele>` detection, and flipping a track that was recorded uphill (bike-park runs are
gravity descents, and the app draws Start/Ziel and direction arrows from the stored order).

**3. One `REGION_CATALOG` entry** in `index.html` — `label`, `file`, `trailCount`, `bounds` (take it from
`region_summary`), and `subRegions` with a label and colour each. Colours only need to be distinct *within*
the group; repeats across groups are fine and expected. None may equal the group-label button's
`--forest` (#2f4a3a), which sits directly above them.

Nothing else in the app needs touching. The dialog, sidebar, `render()`, persistence and map-fitting all
iterate the catalog.

**4. Lifts, if any.** The operator's summer list decides *which* lifts exist; OSM supplies geometry only,
matched by name. `osm_aerialway_survey(bbox)` returns every named aerialway with its `aerialway:bicycle`
tag — **that tag does not decide membership**, it was wrong in both directions in Serfaus. Store each lift
bottom-station-first; `ElevationLookup` on the two end points tells you which end that is. Anchor the name
pattern and treat two matches as an error, not a choice. See `docs/lifts-feature.md`.

**5. Tours, if the operator publishes any.** A published route through the region's own trails becomes a
`loop: true` entry plus a `trailSegments` list attributing every stretch to a component trail, a lift, or a
connector. Match it classically against pieces 1 and 2 — the Tourenbuilder is a tool for app users, not a
build step. `tools/build_bikekingdom_tours.py` is the worked example (densify both sides, lifts before
trails, clip to entry/exit, keep `trailGeo == concat(trailSegments)`), and
`docs/trailrunde-feature.md` lists the traps.

**6. Places.** One `places` entry per name the region is described by, coordinates from OSM:

```python
q = ('[out:json][timeout:180];node[place~"^(city|town|village|hamlet)$"](%s);out tags center;' % bbox)
for e in overpass(q)["elements"]:
    d = min(haversine_m([e["lat"], e["lon"]], c) for g in geo.values() for c in g[::4])
    ...   # keep the ones near our trails, drop the hinterland localities
```

Sort by that distance and read the list: anything past a few hundred metres from every trail in the region
is usually not worth a label. Include the villages a tour is named after — a rider looking for
"Tour 12 - Hauenstein" should find Hauenstein on the map.

**7. Update the version manifest.** This is not optional and it is the step most easily forgotten — it was
missed for three regions in a row (2026-07-28), and once for an edit to an existing one:

```bash
python tools/update_region_versions.py
```

The app fetches `regions/<key>.json?v=<hash>` from `regions/version.json`, and the service worker serves those
**cache-first**. The hash is therefore the only thing that invalidates a cached region. A stale hash means an
edit never reaches a device that already has the region; a **missing** entry is worse, because the URL is then
unversioned and that copy stays cached forever. `validate_region.py` now fails on both.

**8. Verify.**

```bash
python tools/validate_region.py zugspitzarena
```

It checks the invariants that have actually bitten: sub-region keys that exist, valid difficulties, no `url`
(the field was removed from the data model on 2026-07-28), geometry and a profile
per trail and no orphans of either, `trailCount` matching reality, lifts stored bottom-first, sub-region
colours distinct within the group, the loop invariant that `trailGeo[loopId]` is the exact concatenation of
its `trailSegments`, a sanity check that no trail's geometry sits further from the region centre than
the region is wide — which is how a same-named lift 8 km away nearly got into Portes du Soleil — and the
`version.json` hash from step 7.

**It does not check the four pieces above**, and deliberately so: whether a region *should* have lifts,
tours or places is a judgement, not an invariant. Walk the table yourself before calling a region done, and
**look at the map** — the two defects that reached the user in Bike Kingdom (a 1 065 m straight line welded
into Rock'n'Roll, and no place labels at all) both pass every automated check.

**9. And deploy.** `git push` to `main` is what makes any of this visible; the user tests the GitHub Pages
build, not the working tree. A region that validates locally and was never pushed looks exactly like a
region whose lifts are missing — that is what "In Bike Kingdom fehlen die Lifte" turned out to mean.

## Changing an existing region

Same two obligations as a new one, and both were missed on 2026-07-28 while removing one lift and moving one
village label:

- **Write the file with the pipeline's own writer** (`json.dump(..., separators=(", ", ": "))`, one line).
  Re-dumping it with `indent=` reformatted 24 350 lines for a two-value change; the diff was unreviewable.
- **Then run `tools/update_region_versions.py`**, or the change reaches nobody who already has the region.

For a place label specifically, take the coordinate from OSM (`node[place][name=...]`) rather than typing one:
the base map *is* OSM, so its node is the position every user compares against. Samnaun's hand-typed
`46.933, 10.35` sat 1 460 m from the village.

Then load it in a browser (`python3 -m http.server` from inside `Trailmap App/`, **not** `file://`) and
look at the lines against the base map.

## Two things to know before rebuilding an existing region

**The committed regions are not all built to the same parameters.** The pipeline's constants match the most
recent convention, verified by reproducing all 24 Dolomiti Paganella trails byte-identically — same
coordinates, same profile lengths. Older regions are coarser: Paznaun's trails carry roughly half the
points and fixed 100-point profiles, where the pipeline scales to 150/200 for long tracks. Re-running the
pipeline over an old region would therefore change its geometry slightly. That is not a bug to fix
wholesale; only rebuild an old region when there is a reason to touch it anyway.

**Match the base map, not the "best" source.** If a source's geometry disagrees with what OSM/OpenTopoMap
renders, follow the base map — that is the line every user compares against on screen. This is why the four
Donnersberg trails come from OSM despite the site offering its own GPX; see the Donnersberg note in
`CLAUDE.md`.
