# -*- coding: utf-8 -*-
"""Build the Garda Trentino MTB Touren from the destination's own Outdooractive tracks.

    python tools/build_gardasee_tours.py --dry-run
    python tools/build_gardasee_tours.py

Source: `Material/Gardasee/oa_tours.json`, harvested through a real browser (Outdooractive answers 404 to
every plain HTTP client -- see `tools/oa_harvest_server.py`, which this used with
`--proj api-gardatrentino --key ... --out Material/Gardasee/oa_tours.json`). The ids come from
gardatrentino.it's own MTB-route pages, which is also where the length/ascent/descent numbers below come
from: **the destination's published figures win over anything derived from the track**, per the project's
standing rule on official numbers.

WHICH TOURS, AND WHY NOT ALL NINE. The destination publishes nine; four are gravel/asphalt loops and are
deliberately left out. The measure that decides is not the whole track -- with 4 200 m of climbing most of
the distance IS the climb, and a climb is a fireroad by nature (the user's own correction, 2026-08-21, after
a first pass wrongly judged every tour on its total trail share). It is the DESCENT: split the track by its
own smoothed elevation and ask what the descending kilometres run on, per OSM's way types.

    tour                      km   descent  trail on the way down   verdict
    Ronda Extrema           88.7   33.2 km  31.8 %  (10.5 km)      built
    Ronda Grande            74.6   27.4 km  27.2 %  ( 7.4 km)      built
    Variante Caset Pubregn  12.3    7.5 km  31.1 %  ( 2.3 km)      built
    Malga Grassi Trail-Tour 24.2    7.4 km  21.8 %  ( 1.6 km)      built
    Laghel - Tour           10.3    2.2 km  31.3 %  ( 0.7 km)      built
    Lago di Ledro - Tour    16.5    5.1 km   3.2 %  ( 0.2 km)      skipped
    Monte Velo - Tour       29.4   11.8 km   0.8 %  ( 0.1 km)      skipped
    Bio Palafitte Bike Tour 15.5    5.3 km   0.1 %  ( 0.0 km)      skipped
    Duvredo Shortcut         1.1    1.1 km   0.0 %  ( 0.0 km)      skipped

Monte Velo is the instructive one: 11.8 km of descent and 100 m of it on singletrail. Its "difficult"
grade comes from the 1 240 m of climbing, not from the terrain.

DIFFICULTY is the destination's own three-step wording, mapped the way `CLAUDE.md` documents for a German
three-step scale: leicht -> blau, mittel -> rot, schwer -> schwarz (`gruen` is not reachable from it). OA
exposes it as 1/2/3.

SEGMENTS come from `tools/gpx_map_match.py`, sequential map-matching against the region's own 911 trails
and 2 lifts. Two things to know before trusting a rebuild: this network is far denser than anything that
matcher was validated against (Livigno 21 candidates, Bike Kingdom ~130), which is what forced the spatial
prefilter into `_label_points` -- without it one 88 km tour is ~860 million polyline projections per pass
and produces no output in three minutes; and a stretch that matches nothing stays an honest CONNECTOR rather
than being stretched onto the nearest trail -- these tours ride a lot of ground the region does not hold
(the Ronda Extrema alone descends ~7 km of singletrail that is not in our data), and inventing attribution
for it is exactly what `no-silent-auto-corrections` forbids.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gpx_map_match import match_gpx_to_network, resolve_segments  # noqa: E402
from trailmap_pipeline import build_profile, cumulative_km, haversine_m, write_region  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = os.path.join(ROOT, "Trailmap App", "regions", "gardasee.json")
TOURS = os.path.join(ROOT, "Material", "Gardasee", "oa_tours.json")

#: The module's own Livigno-validated defaults, kept after comparing them against a lower pair on this
#: network rather than assuming density needed one: 12/30 and 15/35 produce the SAME named segments and the
#: same lengths on all five tours (13 vs 14 raw segments on the Ronda Extrema, identical attribution). So
#: the threshold is not what limits the match here -- these tours simply only ride 4-6 of the region's
#: trails for a meaningful distance -- and an invented constant would have looked like tuning.
STRICT_M = 15.0
LOOSE_M = 35.0
DIFF = {1: "blau", 2: "rot", 3: "schwarz"}

#: oa id -> (our id, name, sub-region). The sub-region is where the tour STARTS, which is the convention
#: every other region's Touren already follow.
BUILD = [
    ("9952405", "gd_tour_ronda_extrema", "Ronda Extrema", "gd_garda_trentino"),
    ("9952384", "gd_tour_ronda_grande", "Ronda Grande (All Mountain)", "gd_garda_trentino"),
    ("27036092", "gd_tour_caset_pubregn", "Variante Caset Pubregn", "gd_garda_trentino"),
    ("1543379", "gd_tour_malga_grassi", "Malga Grassi Trail-Tour", "gd_sarca"),
    ("1491092", "gd_tour_laghel", "Laghel-Tour", "gd_garda_trentino"),
]
#: Left out on purpose, with the reason, so a later run does not "helpfully" add them back.
SKIP = {
    "27150779": "Lago di Ledro - Tour: 3.2 % of its descent on singletrail, a road loop round the lake",
    "1480775": "Monte Velo - Tour: 11.8 km of descent, 0.1 km of it singletrail -- a gravel climb",
    "6137057": "Bio Palafitte Bike Tour: lakeside asphalt/gravel, 0.1 % trail on the descent",
    "6137011": "Duvredo Shortcut: 1.1 km of fireroad, not a tour at all",
}


def oa_points(geom):
    """OA serves geometry as space-separated `lon,lat,ele` triples."""
    out = []
    for t in geom.split(" "):
        a = t.split(",")
        if len(a) >= 2:
            out.append([float(a[1]), float(a[0])] + ([float(a[2])] if len(a) > 2 else []))
    return out


def main(argv):
    dry = "--dry-run" in argv
    # --strict/--loose, so the threshold this dense network wants can be compared on evidence rather than
    # picked. 12/30 was chosen this way against 15/35 (the module's own Livigno-validated defaults) and 18/40.
    strict = float(argv[argv.index("--strict") + 1]) if "--strict" in argv else STRICT_M
    loose = float(argv[argv.index("--loose") + 1]) if "--loose" in argv else LOOSE_M
    region = json.load(io.open(REGION, encoding="utf-8"))
    tours = json.load(io.open(TOURS, encoding="utf-8"))
    candidates = dict((t["id"], region["trailGeo"][t["id"]]) for t in region["lineTrails"]
                      if not t.get("loop"))
    for l in region.get("lifts") or []:
        candidates[l["id"]] = l["coords"]
    print("network: %d candidates (%d trails + %d lifts)"
          % (len(candidates), len(candidates) - len(region.get("lifts") or []),
             len(region.get("lifts") or [])))

    line_trails = [t for t in region["lineTrails"] if not str(t["id"]).startswith("gd_tour_")]
    geo = dict((k, v) for k, v in region["trailGeo"].items() if not k.startswith("gd_tour_"))
    profs = dict((k, v) for k, v in region["elevationProfiles"].items()
                 if not k.startswith("gd_tour_"))
    segments = dict((k, v) for k, v in (region.get("trailSegments") or {}).items()
                    if not k.startswith("gd_tour_"))

    for oid, tid, name, sub in BUILD:
        t = tours[oid]
        pts = oa_points(t["geometry"])
        runs = match_gpx_to_network([p[:2] for p in pts], candidates,
                                    strict_thresh_m=strict, loose_thresh_m=loose)
        resolved = resolve_segments([p[:2] for p in pts], candidates, runs)
        # Build the segment list by walking the track and swapping in each matched candidate's OWN
        # geometry, so a Tour's line lies pixel-for-pixel on the trail it rides -- the whole point of the
        # segment model. Everything between two matches is a connector made of the recording's own points.
        segs = []
        cur = 0
        for r in resolved:
            if r["gpx_start_idx"] > cur:
                segs.append({"coords": [p[:2] for p in pts[cur:r["gpx_start_idx"] + 1]], "trailId": None})
            key = "liftId" if r["id"].startswith("lift_") else "trailId"
            segs.append({"coords": [list(c) for c in r["coords"]], key: r["id"]})
            cur = r["gpx_end_idx"]
        if cur < len(pts) - 1:
            segs.append({"coords": [p[:2] for p in pts[cur:]], "trailId": None})
        segs = [s for s in segs if len(s["coords"]) >= 2]
        flat = [c for s in segs for c in s["coords"]]
        # THE loop invariant validate_region.py checks: trailGeo[id] IS the concatenation, exactly.
        coords = [[round(c[0], 6), round(c[1], 6)] for c in flat]
        for s in segs:
            s["coords"] = [[round(c[0], 6), round(c[1], 6)] for c in s["coords"]]
        ele = []
        for c in coords:
            near = min(pts, key=lambda p: haversine_m(c, p[:2]))
            ele.append(near[2] if len(near) > 2 else None)
        prof, gain, loss = build_profile(coords, ele)
        named = [s for s in segs if s.get("trailId") or s.get("liftId")]
        on = sum(sum(haversine_m(s["coords"][i], s["coords"][i + 1])
                     for i in range(len(s["coords"]) - 1)) for s in named)
        total = cumulative_km(coords)[-1] * 1000.0
        entry = {"id": tid, "name": name, "region": sub, "diff": DIFF[int(t["difficulty"])],
                 "len": round((t["length"] or total) / 1000.0, 2),
                 "up": int(round(t["ascent"] or gain)), "down": int(round(t["descent"] or loss)),
                 "loop": True}
        line_trails.append(entry)
        geo[tid] = coords
        profs[tid] = prof
        segments[tid] = segs
        print("%-28s %5.1f km  %2d segments (%2d named, %.1f km = %.0f%% of the line)  %s"
              % (name[:28], entry["len"], len(segs), len(named), on / 1000.0,
                 100.0 * on / total, entry["diff"]))
    for oid, why in sorted(SKIP.items()):
        print("  skipped %s" % why)

    if dry:
        print("\n--dry-run: nothing written")
        return 0
    write_region(REGION, line_trails, geo, profs, places=region.get("places"),
                 lifts=region.get("lifts"), trail_segments=segments)
    print("\nwrote %s -- %d trails incl. %d Touren"
          % (os.path.basename(REGION), len(line_trails), len(BUILD)))
    print("next: python tools/validate_region.py gardasee && python tools/update_region_versions.py")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
