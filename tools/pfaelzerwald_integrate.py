# -*- coding: utf-8 -*-
"""Phase 3 of the Pfälzerwald rework: merge the harvested Trailforks trails into the region.

    python tools/pfaelzerwald_integrate.py --dry-run          # print the plan, write nothing
    python tools/pfaelzerwald_integrate.py --out pfaelzerwald.merged.json

Takes the 485 harvested trails and the containment decisions, drops the existing entries a Trailforks
trail covers, and writes the merged region. `trailSegments` is carried over UNCHANGED here and is expected
to be stale afterwards -- Phase 4 (`pfaelzerwald_rederive_loops.py`) rewrites all of it from each loop's
own line, which is what resolves the dangling references this step necessarily creates. Run the two in
sequence; the intermediate file is not a valid region on its own and `validate_region.py` will say so.

**Difficulty** is Trailforks' own rating for every incoming trail, per the user's instruction and the rule
already applied to Finale Ligure and the Harz. Existing entries keep theirs, and `naturtrail_deidesheim`
was excluded from the comparison entirely at the user's request -- those three are correct as they stand.

**Sub-regions.** The user's call (2026-08-14) was to take everything the harvest found, which reaches past
the region's current footprint in two directions, so two new sub-regions carry those blocks rather than
stretching an existing one across ground it has never covered:

* `haardt` -- the northern Haardt edge around Bad Dürkheim/Wachenheim, north of 49.445. Geographically
  Pfälzerwald and directly adjoining the Weinstraße sub-region, but absent from our data until now, so
  every trail here is new ground rather than a replacement. Donnersberg's own region starts at 49.5355, so
  the two stay disjoint.
* `bienwald` -- the south-east around Kandel/Langenbach, 27-31 km from any existing sub-region centre.
  This is the flat Rhine plain rather than the forest proper; kept separate so it reads honestly on the map
  and can be split off later if it ever deserves its own region.

Everything else is assigned to whichever of `johanniskreuz` / `weinstrasse` / `wasgau` its centroid is
nearest, which is how those three were divided in the first place. `naturtrail_deidesheim` is never an
assignment target: it is three specific trails, not an area.
"""
import argparse
import collections
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import ElevationLookup, build_profile, cumulative_km, haversine_m, write_region

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = os.path.join(ROOT, "Trailmap App", "regions", "pfaelzerwald.json")
SRC = os.path.join(ROOT, "Material", "Pfälzer Wald", "trailforks")
REWORK = os.path.join(ROOT, "Material", "Pfälzer Wald", "rework")
ELEV_CACHE = os.path.join(ROOT, "Material", "elevation_cache.json")

TF_DIFF = {"Easiest": "gruen", "Easy": "gruen", "Intermediate": "blau", "Difficult": "rot",
           "Severe": "schwarz", "Extremely Difficult": "schwarz",
           "Extremely Difficult & dangerous, pros only!": "schwarz"}
ASSIGNABLE = ["johanniskreuz", "weinstrasse", "wasgau"]

#: Trailforks trails NOT to import, because the region already has the same ground under a better entry.
#:
#: These five are the RV Edelweiss Deidesheim "Naturtrail" descents, which Trailforks also carries. The
#: user's instruction was that the three existing `naturtrail_deidesheim` entries are correct and need no
#: reconciling -- which `pfaelzerwald_containment.py` implements by excluding that sub-region from the
#: comparison entirely. Correct as far as it goes, and it created exactly the problem it was meant to avoid:
#: nothing then stopped the Trailforks copies being ADDED alongside, putting two entries on one trail. Found
#: 2026-08-14 by checking the excluded trails against the incoming set afterwards, which is the check the
#: exclusion made necessary.
#:
#: Ours win on both counts, so this is not a close call: they are complete where Trailforks is split
#: (Churchner 1.82 km against Teil 1 + Teil 2 = 1.50 km; Pechstein 1.68 km against upper + lower = 1.47 km),
#: and they carry the trail's actual name instead of 74 characters of sponsor text, which would wreck the
#: sidebar's card layout (see the card-sizing notes in CLAUDE.md).
SKIP_SLUGS = {
    "drei-eichen-sponsored-by-sigma-rv-edelweiss-1924-deidesheim-e-v",
    "pechstein-upper-sponsored-by-trp-rv-edelweiss-1924-deidesheim-e-v",
    "pechstein-lower-sponsored-by-trp-rv-edelweiss-1924-deidesheim-e-v",
    "churchner-sponsored-by-raaw-rv-edelweiss-1924-deidesheim-e-v--teil-1",
    "churchner-sponsored-by-raaw-rv-edelweiss-1924-deidesheim-e-v--teil-2",
}
HAARDT_MIN_LAT = 49.445
BIENWALD_MAX_LAT = 49.12
BIENWALD_MIN_LON = 8.00


def _utf8_stdout():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def centroid(coords):
    return [sum(p[0] for p in coords) / len(coords), sum(p[1] for p in coords) / len(coords)]


def trail_id(slug):
    return "pw_tf_" + re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")


def main():
    _utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reg = json.load(open(REGION, encoding="utf-8"))
    geo_new = json.load(open(os.path.join(SRC, "pw_geo_decoded.json"), encoding="utf-8"))
    meta = json.load(open(os.path.join(SRC, "pw_meta.json"), encoding="utf-8"))
    dec = json.load(open(os.path.join(REWORK, "decisions.json"), encoding="utf-8"))

    drop = {r["old_id"] for r in dec["replace"]}
    print("bestehend: %d Trails, davon %d ersetzt" % (len(reg["lineTrails"]), len(drop)))

    # sub-region centres, from the existing data that defined them
    pts = collections.defaultdict(list)
    for t in reg["lineTrails"]:
        if t.get("loop") or t["region"] not in ASSIGNABLE:
            continue
        pts[t["region"]].extend(reg["trailGeo"][t["id"]][::5])
    centres = {k: centroid(v) for k, v in pts.items()}

    def assign(c):
        if c[0] > HAARDT_MIN_LAT:
            return "haardt"
        if c[0] < BIENWALD_MAX_LAT and c[1] > BIENWALD_MIN_LON:
            return "bienwald"
        return min(centres.items(), key=lambda kv: haversine_m(c, kv[1]))[0]

    ele = ElevationLookup(ELEV_CACHE)
    line_trails = [t for t in reg["lineTrails"] if t["id"] not in drop]
    geo = {k: v for k, v in reg["trailGeo"].items() if k not in drop}
    profs = {k: v for k, v in reg["elevationProfiles"].items() if k not in drop}

    added, per_sub, per_diff, clashes = 0, collections.Counter(), collections.Counter(), []
    existing_ids = {t["id"] for t in line_trails}
    skipped_dupes = []
    for slug, coords in sorted(geo_new.items()):
        if slug in SKIP_SLUGS:
            skipped_dupes.append(slug)
            continue
        m = meta[slug]
        tid = trail_id(slug)
        if tid in existing_ids:
            clashes.append(tid)
            continue
        sub = assign(centroid(coords))
        diff = TF_DIFF.get(m["diff"])
        if diff is None:
            clashes.append("%s: unbekannte Schwierigkeit %r" % (slug, m["diff"]))
            continue
        per_sub[sub] += 1
        per_diff[diff] += 1
        added += 1
        if args.dry_run:
            continue
        elevs = ele([[p[0], p[1]] for p in coords])
        prof, gain, loss = build_profile(coords, elevs)
        line_trails.append({"id": tid, "name": m["name"], "region": sub, "diff": diff,
                            "len": round(cumulative_km(coords)[-1], 2), "up": gain, "down": loss})
        geo[tid] = coords
        profs[tid] = prof
        existing_ids.add(tid)
        if added % 50 == 0:
            print("   ... %d/%d Höhenprofile" % (added, len(geo_new)), flush=True)

    print("neu hinzugefügt: %d  (%d Trailforks-Dubletten übersprungen: %s)"
          % (added, len(skipped_dupes), ", ".join(s.split("-sponsored")[0] for s in skipped_dupes)))
    print("   je Sub-Region: %s" % dict(per_sub))
    print("   je Schwierigkeit: %s" % dict(per_diff))
    if clashes:
        print("   PROBLEME: %s" % clashes[:6])
    print("Region danach: %d Trails (%d einzeln, %d Trailrunden)"
          % (len(line_trails), sum(1 for t in line_trails if not t.get("loop")),
             sum(1 for t in line_trails if t.get("loop"))))

    stale = {s["trailId"] for ss in reg.get("trailSegments", {}).values() for s in ss
             if s.get("trailId") and s["trailId"] in drop}
    print("Trailrunden-Segmente, die auf ersetzte Trails zeigen: %d Ids -- Phase 4 leitet alles neu her"
          % len(stale))

    if args.out and not args.dry_run:
        write_region(args.out, line_trails, geo, profs, places=reg.get("places"),
                     lifts=reg.get("lifts"), trail_segments=reg.get("trailSegments"))
        print("geschrieben: %s" % args.out)


if __name__ == "__main__":
    main()
