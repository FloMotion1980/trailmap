# -*- coding: utf-8 -*-
"""Measure how closely a region's trail lines sit on the OSM ways the base map itself draws.

    python tools/check_geo_vs_osm.py harz
    python tools/check_geo_vs_osm.py harz --tol 30 --sub bodetal

Why this exists as a tool rather than a one-off: this app's base layers ARE OpenStreetMap/OpenTopoMap, so
OSM's line is the one visual reference every user compares our trail against on the same screen. That is
the Donnersberg lesson in `CLAUDE.md` -- the point is not that OSM is the most accurate source available,
it is that a line disagreeing with the tiles underneath it reads as broken no matter how good its source
was. `validate_region.py` cannot catch this (it only checks that geometry is near the region's centre), and
neither can a distance comparison against the source's own stated length, which is what the Trailforks
extraction already verifies.

Reported per trail: the share of its points lying within `--tol` of any OSM path/track/footway/cycleway/
bridleway/road, and the single worst point. A trail on a purpose-built bike-park line that OSM has not
mapped will legitimately score low -- this measures agreement, not correctness, so read a low score as
"look at this one", not "this one is wrong".
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import haversine_m, overpass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS_DIR = os.path.join(ROOT, "Trailmap App", "regions")
HIGHWAYS = "path|track|footway|cycleway|bridleway|service|unclassified|residential|tertiary"
#: Grid cell in degrees. 0.002 deg of latitude is ~222 m, comfortably more than any sane --tol, so a
#: point's own cell plus its eight neighbours always contains everything within tolerance.
CELL = 0.002


def _key(lat, lon):
    # Integer keys on purpose: `round(lat, 3) + 0.001` produces 51.746000000000004 and silently matches
    # nothing, which is how the first version of this check reported every trail as far from every way.
    return int(math.floor(lat / CELL)), int(math.floor(lon / CELL))


def _seg_distance_m(p, a, b):
    """Distance from p to the SEGMENT a-b, not to its endpoints.

    Densifying every OSM way to 10 m instead was what made the first version too slow to finish.

    Longitude degrees are pre-multiplied by cos(lat) so that plain Euclidean maths is valid; the result is
    therefore already in "latitude-equivalent" degrees and must NOT be divided by that factor again on the
    way out. Doing so is a real bug this shipped with: it inflated every east-west offset by 1/cos(lat),
    which is 1.6x at Harz latitudes, and the first OSM-agreement run reported distances that much too large.
    """
    scale = math.cos(math.radians(p[0]))
    ax, ay = (a[1] - p[1]) * scale, a[0] - p[0]
    bx, by = (b[1] - p[1]) * scale, b[0] - p[0]
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom == 0:
        return haversine_m(p, a)
    t = max(0.0, min(1.0, -(ax * dx + ay * dy) / denom))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(cx, cy) * 111320.0


def build_index(bbox):
    """{cell: [(a, b), ...]} of every OSM way segment in bbox, bucketed into every cell it touches."""
    q = ('[out:json][timeout:240];way[highway~"^(%s)$"](%s);out geom;' % (HIGHWAYS, bbox))
    grid, nseg = {}, 0
    for e in overpass(q).get("elements", []):
        g = [[p["lat"], p["lon"]] for p in e.get("geometry", [])]
        for i in range(1, len(g)):
            a, b = g[i - 1], g[i]
            nseg += 1
            k0, k1 = _key(*a), _key(*b)
            for ky in range(min(k0[0], k1[0]), max(k0[0], k1[0]) + 1):
                for kx in range(min(k0[1], k1[1]), max(k0[1], k1[1]) + 1):
                    grid.setdefault((ky, kx), []).append((a, b))
    return grid, nseg


def nearest_m(grid, p, cap=9999.0):
    best = cap
    ky, kx = _key(p[0], p[1])
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for a, b in grid.get((ky + dy, kx + dx), ()):
                d = _seg_distance_m(p, a, b)
                if d < best:
                    best = d
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("region")
    ap.add_argument("--tol", type=float, default=25.0)
    ap.add_argument("--sub", default=None, help="only this sub-region key")
    args = ap.parse_args()

    data = json.load(open(os.path.join(REGIONS_DIR, args.region + ".json"), encoding="utf-8"))
    trails = [t for t in data["lineTrails"] if args.sub is None or t["region"] == args.sub]

    by_sub = {}
    for t in trails:
        by_sub.setdefault(t["region"], []).append(t)

    worst_overall = []
    for sub, group in by_sub.items():
        lo = [90.0, 180.0]
        hi = [-90.0, -180.0]
        for t in group:
            for c in data["trailGeo"][t["id"]]:
                lo = [min(lo[0], c[0]), min(lo[1], c[1])]
                hi = [max(hi[0], c[0]), max(hi[1], c[1])]
        bbox = "%.4f,%.4f,%.4f,%.4f" % (lo[0] - .004, lo[1] - .006, hi[0] + .004, hi[1] + .006)
        grid, nseg = build_index(bbox)
        print("== %-16s %6d OSM segments in %s" % (sub, nseg, bbox))
        for t in sorted(group, key=lambda x: x["id"]):
            pts = data["trailGeo"][t["id"]]
            dists = [nearest_m(grid, p) for p in pts]
            near = sum(1 for d in dists if d <= args.tol)
            pct = 100.0 * near / len(pts)
            flag = "" if pct >= 80 else ("   <-- CHECK" if pct >= 50 else "   <-- CHECK HARD")
            if pct < 80:
                worst_overall.append((pct, t["id"], t["name"]))
            print("   %-26s %3d pts  %5.1f%% <=%.0fm   median %3.0fm  worst %4.0fm%s"
                  % (t["id"], len(pts), pct, args.tol,
                     sorted(dists)[len(dists) // 2], max(dists), flag))

    if worst_overall:
        print("\n%d trail(s) below 80%% agreement, worst first:" % len(worst_overall))
        for pct, tid, name in sorted(worst_overall):
            print("   %5.1f%%  %-26s %s" % (pct, tid, name))
    else:
        print("\nevery trail is >=80%% within %.0f m of an OSM way" % args.tol)


if __name__ == "__main__":
    main()
