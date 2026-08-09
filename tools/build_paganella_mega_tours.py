# -*- coding: utf-8 -*-
"""Add Dolomiti Paganella's two multi-zone combo Tours ("Lake to Lake", "Bear Trails") to the region file.

Runs on top of the existing regions/paganella.json (28 trails already includes the other, simpler Tours and
the 10 lifts) -- it re-reads the file, drops these two Tours if already present, rebuilds them, and writes
the file back. Everything else in the file is untouched.

Why these two need real `trailSegments` while every other "Shared trail" Tour doesn't: their recorded track
rides UP a lift several times mid-route (both hop between all three park zones), and each such ride is
recorded as a straight GPS jump between two points -- see the LIFT-AS-STRAIGHT-LINE DEFECT note in
index.html's `paganella` REGION_CATALOG comment. A single plain line would draw those as visible straight
teleports across the mountain. "From Top To Lake" has the same defect but only at the very start (two lift
rides before the descent begins), so clipping those leading points was enough for that one -- see the
region file's own build history in index.html.

Reuses tools/build_bikekingdom_tours.py's classical tour-vs-trail-and-lift matcher wholesale (see
docs/trailrunde-feature.md's "Matching a tour against existing trails and lifts" section for the four traps
it already had to solve) rather than re-deriving it. One adjustment was needed: that matcher's own
candidate list skips any trail with `loop: true`, which in Bike Kingdom correctly meant "another tour built
in the same run" -- but here it also excludes every other "Shared trail" Tour (Ude's Trail, Monte Corno,
Ribs Trail, ...), which is exactly the kind of real named descent these two mega-routes actually ride. Fixed
by handing the matcher a shallow copy of the trail list with `loop` stripped for matching purposes only
(never written back to the region file).

Track source: regio.outdooractive.com's own project API, hit directly (no browser automation needed -- a
plain server-side GET works): `api/v2/project/oar-paganella/contents/tour/<id>?display=trackinfo&key=...`.
The key was found in the tour page's own network requests. Same underlying recording as the operator site's
per-trail GPX download, different API shape.

Run:  python tools/build_paganella_mega_tours.py [--report <file>]
"""
import io
import json
import os
import sys
import traceback
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import (haversine_m, douglas_peucker, dedupe_points, cumulative_km,  # noqa: E402
                               build_profile, write_region, region_summary)
import build_bikekingdom_tours as bkt  # noqa: E402 -- reused wholesale, see module docstring

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION_FILE = os.path.join(ROOT, "Trailmap App", "regions", "paganella.json")

OA_KEY = "XMEBUY3Z-EMWGKPCA-4OSSBA9A"
OA_PROJECT = "oar-paganella"

TOURS = [
    dict(id="pag_lake_to_lake", oa_id=103198194, name="Lake To Lake (TC)", region="shared",
         diff="schwarz", official=(75.4, 300, 2500)),
    dict(id="pag_bear_trails", oa_id=105623451, name="Bear Trails (TC)", region="shared",
         diff="schwarz", official=(59.7, 1000, 4050)),
]

LOG = []


def say(line=""):
    LOG.append(line)
    print(line, flush=True)


def fetch_oa_track(oa_id):
    """[(lat, lon, ele), ...] for an Outdooractive tour id, straight from the project API."""
    url = ("https://regio.outdooractive.com/api/v2/project/%s/contents/tour/%d"
           "?display=trackinfo&jsapi=1&key=%s&lang=de&legacyJson=false&format=json"
           % (OA_PROJECT, oa_id, OA_KEY))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    tour = data["answer"]["contents"][0]
    pts = []
    for seg in tour["track"]["segments"]:
        for route in seg.get("routes", []):
            for feat in route["features"]:
                for c in feat["geometry"]["coordinates"]:
                    lon, lat = c[0], c[1]
                    pts.append((lat, lon, c[2] if len(c) > 2 else None))
    return tour["title"], pts


def build_tour_from_points(spec, trails, geo, lifts, verbose=True):
    """Like build_bikekingdom_tours.build_tour, but from an in-memory point list, not a GPX file."""
    title, raw = fetch_oa_track(spec["oa_id"])
    pts = douglas_peucker(dedupe_points(raw))
    own = [[round(p[0], 6), round(p[1], 6)] for p in pts]
    own_ele = [p[2] if len(p) > 2 else None for p in pts]

    # See the module docstring: strip `loop` for matching purposes only, so the OTHER Shared-trail Tours
    # count as real candidate trails instead of being skipped as "another tour in this run".
    trails_for_matching = [dict(t, loop=False) for t in trails]
    track = bkt.densify(own)
    parts = bkt.match_components(track, trails_for_matching, geo, lifts, verbose=verbose)

    by_id = {t["id"]: t for t in trails}
    lift_by_id = {l["id"]: l for l in lifts}
    tpts = [(p[0], p[1]) for p in track]
    segs = []
    for kind, key, a, b in parts:
        rode = bkt.run_len_m(tpts, a, b)
        sampling = bkt.own_spacing(own, track[a][2], track[b][2])
        if kind == "trail":
            tid, lo, hi, fwd = key
            coords = [list(c) for c in geo[tid][lo:hi + 1]]
            if not fwd:
                coords = coords[::-1]
            if len(coords) < 2:
                kind = "connector"
            else:
                segs.append({"coords": coords, "trailId": tid, "_rode": rode, "_sampling": sampling})
                continue
        if kind == "lift":
            cable = [list(c) for c in lift_by_id[key]["coords"]]
            if haversine_m(track[a][:2], cable[-1]) < haversine_m(track[a][:2], cable[0]):
                cable = cable[::-1]
            segs.append({"coords": cable, "trailId": None, "liftId": key, "_rode": rode,
                         "_sampling": sampling})
            continue
        coords = [[round(p[0], 6), round(p[1], 6)]
                  for p in douglas_peucker([[t[0], t[1]] for t in track[a:b + 1]])]
        if len(coords) >= 2:
            segs.append({"coords": coords, "trailId": None, "_rode": rode, "_sampling": sampling})

    segs = [s for s in segs if len(s["coords"]) >= 2]
    joins = []
    for i in range(1, len(segs)):
        prev_end = segs[i - 1]["coords"][-1]
        gap = haversine_m(prev_end, segs[i]["coords"][0])
        if segs[i]["coords"][0] != prev_end:
            segs[i]["coords"].insert(0, list(prev_end))
        if gap > bkt.MAX_QUIET_JOIN_M:
            joins.append((i, gap))

    loop_geo = [c for s in segs for c in s["coords"]]

    prof, gain, loss = build_profile(own, own_ele)
    geo_total = cumulative_km(loop_geo)[-1]
    scale = (prof[-1][0] / geo_total) if geo_total else 1.0
    cum = cumulative_km(loop_geo)
    off = 0
    for s in segs:
        n = len(s["coords"])
        s["distStart"] = round(cum[off] * scale, 4)
        s["distEnd"] = round(cum[off + n - 1] * scale, 4)
        off += n
    length, up, down = spec["official"]
    entry = {"id": spec["id"], "name": spec["name"], "region": spec["region"], "diff": spec["diff"],
             "len": length, "up": up, "down": down, "loop": True}

    if verbose:
        say("\n%s  (%s)" % (spec["name"], spec["id"]))
        say("   raw %d -> %d points, own track %.2f km, profile %.2f km, geometry %.2f km "
            "(gain/loss from track %d/%d, official %d/%d)"
            % (len(raw), len(own), cumulative_km(own)[-1], prof[-1][0], geo_total, gain, loss, up, down))
        for s in segs:
            if s.get("liftId"):
                what = "LIFT  " + lift_by_id[s["liftId"]]["name"]
            elif s["trailId"]:
                what = "trail " + by_id[s["trailId"]]["name"]
            else:
                what = "~~~~~ Verbindung"
            drawn = bkt.run_len_m([tuple(c) for c in s["coords"]], 0, len(s["coords"]) - 1)
            rode = s.pop("_rode", 0.0)
            sampling = s.pop("_sampling", 0.0)
            ratio = (drawn / rode) if rode > 1 else 0.0
            mark = ""
            if ratio and (ratio > 1.3 or ratio < 0.75):
                how = ("Aufzeichnung alle %.0f m" % sampling) if sampling else "kuerzer als ein Trackpunkt-Schritt"
                mark = "  <-- %.2fx geritten, %s" % (ratio, how)
            say("   %6.2f - %6.2f km  %-48s %5.0f m%s" % (s["distStart"], s["distEnd"], what, drawn, mark))
        for i, gap in joins:
            say("   !! Naht vor Segment %d: %.0f m Luftlinie ueberbrueckt" % (i, gap))
    for s in segs:
        s.pop("_rode", None)
        s.pop("_sampling", None)
    return entry, loop_geo, prof, segs


def run():
    data = json.load(io.open(REGION_FILE, encoding="utf-8"))
    building_ids = {t["id"] for t in TOURS}
    trails = [t for t in data["lineTrails"] if t["id"] not in building_ids]
    geo = {k: v for k, v in data["trailGeo"].items() if k in {t["id"] for t in trails}}
    profs = {k: v for k, v in data["elevationProfiles"].items() if k in geo}
    lifts = data["lifts"]
    segments = {k: v for k, v in data.get("trailSegments", {}).items() if k not in building_ids}

    line_trails = list(trails)
    for spec in TOURS:
        entry, coords, prof, segs = build_tour_from_points(spec, trails, geo, lifts)
        line_trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof
        segments[entry["id"]] = segs

    out = write_region(REGION_FILE, line_trails, geo, profs, places=data.get("places") or [],
                        lifts=lifts, trail_segments=segments)
    say("\n%s" % region_summary(out))
    say("written: %s" % REGION_FILE)
    say("next: python tools/update_region_versions.py && python tools/validate_region.py paganella")


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
