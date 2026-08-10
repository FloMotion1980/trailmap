# -*- coding: utf-8 -*-
"""Add Laax's 5 published Tours to regions/laax.json, on top of what build_laax.py produced.

Runs on top of an already-built regions/laax.json (build_laax.py first if the trails themselves changed),
matching each tour's own recorded GPX (Material/Laax/Touren/) CLASSICALLY against the region's existing
trails and lifts -- same reused engine as tools/build_bikekingdom_tours.py (see docs/trailrunde-feature.md
"Matching a tour against existing trails and lifts" for the four traps it already solves: lift-before-trail
matching, cable densification, gap-merging, edge-extension). Deliberately reused rather than reimplemented --
that engine is generic in its trails/geo/lifts/spec inputs, only `MAT`/`TOUR_REGION` are module-level and are
monkeypatched here per call.

Why these five, from laax.com/biking's own Outdooractive links (2026-08-10 audit, see memory
laax-audit-findings.md): the operator's overview page names "Vorab Trail" and "Crest la Siala" for what are
actually two different things sharing one card -- the short named trail (already in TRAILS, build_laax.py)
and a much longer Tour combining several trails + a lift + connecting stretches. The other three
(Crap Masegn Tour, Vom Gletscher bis zum Rhein, Crest da Tiarms bis Ilanz) are further downloads the user
supplied the same day -- the last two ride well outside the resort's own trail network (down to Ilanz /
the Rhein valley), so most of their length becomes an honest, unlabeled connector rather than a named trail
substitution -- that is expected, not a bug in the matcher.

Run:  python tools/build_laax_tours.py [--report <file>]
"""
import io
import json
import os
import sys
import traceback

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_bikekingdom_tours as BKT  # noqa: E402
from trailmap_pipeline import write_region, region_summary  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Trailmap App", "regions", "laax.json")
BKT.MAT = os.path.join(ROOT, "Material", "Laax", "Touren")

LOG = []


def say(line=""):
    LOG.append(line)
    print(line, flush=True)


BKT.say = say  # so build_tour's own verbose printing lands in this script's report too

# (id, gpx filename, display name, diff, official (km, up, down), region for the lineTrails entry)
TOURS = [
    dict(id="laax_tour_vorab", gpx="t23434882_vorab trail tour.gpx", name="Vorab Trail Tour",
         diff="schwarz", official=(20.7, 531, 1725), region="laax"),
    dict(id="laax_tour_crest_la_siala", gpx="t23434785_crest la siala tour.gpx",
         name="Crest la Siala Tour", diff="schwarz", official=(13.3, 106, 1234), region="laax"),
    dict(id="laax_tour_crap_masegn", gpx="t23434924_crap masegn tour.gpx", name="Crap Masegn Tour",
         diff="rot", official=(18.8, 301, 1437), region="laax"),
    dict(id="laax_tour_gletscher_rhein", gpx="t806597080_vom gletscher bis zum.gpx",
         name="Vom Gletscher bis zum Rhein", diff="schwarz", official=(43.3, 1359, 2454), region="laax"),
    dict(id="laax_tour_tiarms_ilanz", gpx="t806933144_crest da tiarms- vom crap.gpx",
         name="Crest da Tiarms: Vom Crap Sogn Gion bis nach Ilanz", diff="schwarz",
         official=(25.5, 445, 1962), region="laax"),
]


def run():
    data = json.load(io.open(OUT, encoding="utf-8"))
    trails = [t for t in data["lineTrails"] if not t.get("loop")]
    geo = {k: v for k, v in data["trailGeo"].items() if k in {t["id"] for t in trails}}
    profs = {k: v for k, v in data["elevationProfiles"].items() if k in geo}
    lifts = data.get("lifts") or []

    line_trails = list(trails)
    segments = {}
    for spec in TOURS:
        BKT.TOUR_REGION = spec["region"]
        entry, coords, prof, segs = BKT.build_tour(spec, trails, geo, lifts)
        line_trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof
        segments[entry["id"]] = segs

    out = write_region(OUT, line_trails, geo, profs, places=data.get("places") or [],
                       lifts=lifts, trail_segments=segments)
    say("\n%s" % region_summary(out))
    say("written: %s" % OUT)
    say("next: python tools/update_region_versions.py && python tools/validate_region.py laax")


def main():
    report = None
    if "--report" in sys.argv:
        report = sys.argv[sys.argv.index("--report") + 1]
    code = 0
    try:
        run()
    except BaseException:
        LOG.append("\n" + traceback.format_exc())
        code = 1
        traceback.print_exc()
    if report:
        io.open(report, "w", encoding="utf-8").write("\n".join(LOG) + "\n")
        print("report written: %s" % report)
    return code


if __name__ == "__main__":
    sys.exit(main())
