# -*- coding: utf-8 -*-
"""
@suite   pipeline
@area    GPX -> geometry/elevation build pipeline
@files   tools/trailmap_pipeline.py, tools/build_*.py
@touches parse_gpx, dedupe_points, douglas_peucker, build_profile, build_trail, cumulative_km, haversine_m, split_on_gaps, chain_ways, write_region

Every region in the app was produced by these functions, and the pipeline had been re-derived from scratch
in each session that added a region before it was committed as a module -- so a silent change here would
diverge new regions from old ones with nothing to notice it. The last case is the one that matters most: it
rebuilds all 12 Laax trails from their source GPX and demands byte-identical geometry and profiles against
the committed regions/laax.json.

The tolerance cases are not hypothetical. Each malformed shape below appears in some file under Material/,
which is why parse_gpx is a regex and not an XML parser.
"""
import io
import json
import os

from trailmap_pipeline import (parse_gpx, dedupe_points, douglas_peucker, build_profile, build_trail,
                               cumulative_km, haversine_m, split_on_gaps, bounds_of, SIMPLIFY_EPS_M,
                               MIN_POINT_SPACING_M)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGIONS = os.path.join(ROOT, "Trailmap App", "regions")
MATERIAL = os.path.join(ROOT, "Material")


def gpx(points_xml, head='<gpx><trk><trkseg>', tail="</trkseg></trk></gpx>"):
    return head + points_xml + tail


def run(t):
    # ---------------------------------------------------------------- parse_gpx tolerance
    t.case("parse_gpx reads a plain track")
    pts = parse_gpx(gpx('<trkpt lat="47.0" lon="10.0"><ele>1500</ele></trkpt>'
                        '<trkpt lat="47.001" lon="10.001"><ele>1490.5</ele></trkpt>'))
    t.eq("two points", len(pts), 2)
    t.eq("lat/lon/ele of the first", [round(pts[0][0], 3), round(pts[0][1], 3), pts[0][2]], [47.0, 10.0, 1500.0])
    t.eq("fractional ele survives", pts[1][2], 1490.5)

    t.case("parse_gpx survives the four malformed shapes seen in Material/")
    # 1. lon BEFORE lat -- attribute order is not fixed, several operator exports write it the other way.
    swapped = parse_gpx(gpx('<trkpt lon="10.0" lat="47.0"><ele>1500</ele></trkpt>'
                            '<trkpt lon="10.001" lat="47.001"><ele>1490</ele></trkpt>'))
    t.eq("lon-before-lat is not read as lat-before-lon", [round(swapped[0][0], 1), round(swapped[0][1], 1)], [47.0, 10.0])
    # 2. an unescaped & in a name -- a real XML parser aborts the whole document on this one.
    amp = parse_gpx('<gpx><trk><name>Wasser & Holz</name><trkseg>'
                    '<trkpt lat="47.0" lon="10.0"><ele>1500</ele></trkpt>'
                    '<trkpt lat="47.001" lon="10.001"><ele>1490</ele></trkpt>'
                    "</trkseg></trk></gpx>")
    t.eq("unescaped & does not lose the points", len(amp), 2)
    # 3. CDATA-wrapped elevation.
    cdata = parse_gpx(gpx('<trkpt lat="47.0" lon="10.0"><ele><![CDATA[1500]]></ele></trkpt>'
                          '<trkpt lat="47.001" lon="10.001"><ele><![CDATA[1490]]></ele></trkpt>'))
    t.eq("CDATA ele is read", [p[2] for p in cdata], [1500.0, 1490.0])
    # 4. waypoints/routepoints rather than track points.
    rte = parse_gpx('<gpx><rte><rtept lat="47.0" lon="10.0"><ele>1500</ele></rtept>'
                    '<rtept lat="47.001" lon="10.001"><ele>1490</ele></rtept></rte></gpx>')
    t.ok("route points are found too", len(rte) == 2, len(rte), 2)

    t.case("parse_gpx returns nothing rather than guessing on an empty or broken file")
    t.eq("empty string", parse_gpx(""), [])
    t.eq("no coordinates at all", parse_gpx("<gpx><trk><trkseg></trkseg></trk></gpx>"), [])

    # ---------------------------------------------------------------- dedupe + simplify
    t.case("dedupe_points drops points closer than the spacing floor, keeps the ends")
    # ~0.11 m apart at this latitude, i.e. GPS jitter standing still.
    jitter = [[47.0, 10.0, 1500], [47.000001, 10.000001, 1500], [47.000002, 10.0, 1500], [47.01, 10.01, 1400]]
    kept = dedupe_points(jitter)
    t.eq("three jitter points collapse to one", len(kept), 2)
    t.eq("the far end survives", [round(kept[-1][0], 3), round(kept[-1][1], 3)], [47.01, 10.01])
    t.ok("floor is the documented 0.5 m", MIN_POINT_SPACING_M == 0.5, MIN_POINT_SPACING_M, 0.5)

    t.case("douglas_peucker keeps corners and drops points on a straight line")
    straight = [[47.0, 10.0, 0], [47.0005, 10.0, 0], [47.001, 10.0, 0], [47.0015, 10.0, 0], [47.002, 10.0, 0]]
    t.eq("a straight run collapses to its two ends", len(douglas_peucker(straight)), 2)
    corner = [[47.0, 10.0, 0], [47.001, 10.0, 0], [47.001, 10.001, 0]]
    t.eq("a right-angle corner is kept", len(douglas_peucker(corner)), 3)
    t.ok("epsilon is the documented 2 m", SIMPLIFY_EPS_M == 2.0, SIMPLIFY_EPS_M, 2.0)
    t.ok("endpoints are never moved",
         douglas_peucker(straight)[0][:2] == straight[0][:2] and douglas_peucker(straight)[-1][:2] == straight[-1][:2],
         True, True)

    # ---------------------------------------------------------------- profiles
    t.case("build_profile resamples to the documented point counts")
    def line(n, km_total, ele_from, ele_to):
        # A due-north line, so distance is easy to reason about: 1 deg lat ~ 111.2 km.
        step = (km_total / 111.195) / (n - 1)
        return ([[47.0 + i * step, 10.0] for i in range(n)],
                [ele_from + (ele_to - ele_from) * i / (n - 1.0) for i in range(n)])
    coords, ele = line(400, 3.0, 1800, 1200)
    prof, gain, loss = build_profile(coords, ele)
    t.eq("a 3 km trail gets 100 points", len(prof), 100)
    t.near("its length is the last x value", prof[-1][0], 3.0, 0.05)
    t.near("descent is reported", loss, 600, 12)
    t.near("no phantom climb", gain, 0, 12)
    coords, ele = line(600, 9.0, 2000, 1000)
    t.eq("above 7 km it is 150 points", len(build_profile(coords, ele)[0]), 150)
    coords, ele = line(900, 30.0, 2000, 1000)
    t.eq("above 25 km it is 200 points", len(build_profile(coords, ele)[0]), 200)

    t.case("build_profile interpolates missing and implausible elevations")
    coords, ele = line(50, 2.0, 1500, 1400)
    holed = list(ele)
    holed[20] = None            # a gap in the source
    holed[21] = 0.0             # the Donnersberg placeholder: 0 m in a mountain region is missing, not sea level
    prof, gain, loss = build_profile(coords, holed)
    lows = [e for _, e in prof if e is None or e < 1000]
    t.eq("no None and no 0 m survives into the profile", lows, [])
    t.near("the hole did not invent 1400 m of descent", loss, 100, 25)

    t.case("cumulative_km and haversine_m agree with each other")
    a, b = [47.0, 10.0], [47.01, 10.0]
    t.near("1/100 degree of latitude is ~1112 m", haversine_m(a, b), 1112, 5)
    t.near("cumulative over two equal legs doubles", cumulative_km([a, b, [47.02, 10.0]])[-1] * 1000, 2224, 10)
    t.eq("a single point is zero length", cumulative_km([a])[-1], 0)

    t.case("split_on_gaps cuts a track where the recording jumped")
    near = [[47.0, 10.0], [47.0005, 10.0]]
    far = [[47.1, 10.0], [47.1005, 10.0]]
    parts = split_on_gaps(near + far)
    t.eq("two segments", len(parts), 2)
    t.eq("nothing is lost", sum(len(p) for p in parts), 4)
    t.eq("a continuous track stays one piece", len(split_on_gaps(near)), 1)

    t.case("bounds_of covers every point of every trail")
    bb = bounds_of({"a": [[47.0, 10.0], [47.5, 10.5]], "b": [[46.5, 11.0]]})
    t.eq("south-west corner", [round(bb[0][0], 3), round(bb[0][1], 3)], [46.5, 10.0])
    t.eq("north-east corner", [round(bb[1][0], 3), round(bb[1][1], 3)], [47.5, 11.0])

    # ---------------------------------------------------------------- the golden case
    t.case("GOLDEN: rebuilding Laax from its GPX reproduces the committed region byte for byte")
    laax_json = os.path.join(REGIONS, "laax.json")
    laax_mat = os.path.join(MATERIAL, "Laax")
    if not (os.path.exists(laax_json) and os.path.isdir(laax_mat)):
        t.ok("skipped: Laax region or Material missing", True, "skipped", "skipped")
    else:
        import build_laax
        data = json.load(io.open(laax_json, encoding="utf-8"))
        by_id = {e["id"]: e for e in data["lineTrails"]}
        rebuilt = checked = 0
        mismatch = []
        for slug, rid, name, diff, why, official in build_laax.TRAILS:
            if rid is None:            # Gronda comes from OSM, not from a file here -- not reproducible offline
                continue
            path = os.path.join(laax_mat, "%s_%d.gpx" % (slug, rid))
            if not os.path.exists(path):
                continue
            raw = parse_gpx(io.open(path, encoding="utf-8", errors="replace").read())
            tid = "laax_" + slug
            # No elevation lookup on purpose: these exports carry real <ele>, so a network call here would
            # mean the pipeline had started ignoring it.
            entry, coords, prof = build_trail(tid, name, region=by_id[tid]["region"], diff=diff,
                                              raw_points=raw, official=official)
            rebuilt += 1
            if coords != data["trailGeo"][tid]:
                mismatch.append("%s geometry (%d vs %d points)" % (tid, len(coords), len(data["trailGeo"][tid])))
            elif prof != data["elevationProfiles"][tid]:
                mismatch.append("%s profile" % tid)
            else:
                checked += 1
            for field in ("len", "up", "down", "name", "diff"):
                if entry[field] != by_id[tid][field]:
                    mismatch.append("%s.%s = %r, committed %r" % (tid, field, entry[field], by_id[tid][field]))
        t.ok("at least 10 trails were actually rebuilt", rebuilt >= 10, rebuilt, ">= 10")
        t.eq("every rebuilt trail matches the committed data", mismatch, [])
        t.eq("geometry and profile identical for all of them", checked, rebuilt)
