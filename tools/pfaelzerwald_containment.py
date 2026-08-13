# -*- coding: utf-8 -*-
"""Phase 2 of the Pfälzerwald rework: decide which existing trails a Trailforks trail replaces.

    python tools/pfaelzerwald_containment.py --new harz_style_geo.json --out decisions.json

The user's decision (2026-08-13) is **"nur ersetzen wo Trailforks liegt"**: an existing entry is removed
only when an incoming Trailforks trail actually covers it. Everything else stays. That guarantees the
attributed share measured by `pfaelzerwald_report.py` cannot fall, and it means this file never has to
choose between two plausible trails -- only between "covered" and "not covered".

What the existing 395 entries are matters for reading the output. They came from matching the region's own
official tours against OSM **hiking** routes, so their names are the hiking route's ("Clauser Haweweg 1-4"
is four separate crossings of one Wanderweg, "Annweiler Nordic Walking 1" is exactly what it says), their
median length is 325 m, and 382 of them exist only as a tour component. The user confirmed this is expected
and that hiking routes may stay. So a removal here is never "this trail was wrong" -- it is "a rider-named
trail now describes this ground better", which is why Trailforks wins on name, difficulty and geometry.

`naturtrail_deidesheim` is excluded from the whole comparison at the user's instruction: those 3 are real
MTB trails with the user's own difficulty and they are correct as they stand.

**The metric is directional containment, not average distance.** For the SHORTER of a pair (by real length,
not point count), what fraction of its points lie within TOL of the LONGER one's line. An average nearest-
neighbour distance over both directions under-detects badly when lengths differ, because the longer trail's
unmatched extra length drags the mean up even when the short one is fully inside it. A bounding-box
pre-filter keeps a full pairwise scan cheap at ~900 trails.

**And the aggregate fraction alone does not decide the middle band.** Two shapes produce a similar number
and mean opposite things, so `profile_shape()` classifies the per-point distance SEQUENCE:

* `subsumed` -- near-zero for most of the run, diverging at one or both ENDS. A real duplicate.
* `junction` -- near-zero at one end, then a monotonically growing divergence. Two trails sharing a
  trailhead and then genuinely parting; both must stay.
* `unclear` -- neither, e.g. alternating near/far. Goes on the review list rather than being decided.

This is what separated Donnersberg's real duplicates from its shared-trailhead pairs, where an endpoint
check had found only 3 of 10. Cases the shape cannot settle are collected for the user instead of guessed
(their second decision the same day: "sammeln, ich entscheide morgen"), so nothing here blocks a batch run.
"""
import argparse
import io
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import haversine_m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = os.path.join(ROOT, "Trailmap App", "regions", "pfaelzerwald.json")

TOL_M = 20.0                 # "on the same line as"
BBOX_PAD_DEG = 0.004         # ~300-450 m; a pair further apart than this cannot be contained at TOL_M
SURE_REPLACE = 0.70          # >= this fraction contained -> replace, no shape question asked
MAYBE_LOW = 0.30             # below this -> keep, no question asked
EXCLUDE_SUBREGIONS = {"naturtrail_deidesheim"}


def _utf8_stdout():
    """Force UTF-8 output, but only when run as a script.

    Doing this at import time breaks any importer: the test runner imports these tools to check their
    logic, the wrapper it installs replaces the runner's own stdout, and when that wrapper is collected it
    closes the underlying buffer -- the runner then dies with "I/O operation on closed file" AFTER its
    cases have already passed, which reads like a test failure rather than an import side effect.
    """
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def line_len_m(c):
    return sum(haversine_m(c[i - 1], c[i]) for i in range(1, len(c)))


def bbox(coords, pad=0.0):
    la = [p[0] for p in coords]
    lo = [p[1] for p in coords]
    return (min(la) - pad, min(lo) - pad, max(la) + pad, max(lo) + pad)


def bbox_overlaps(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _seg_dist_m(p, a, b):
    """Point-to-segment, in metres. Longitude pre-scaled by cos(lat) so Euclidean maths is valid.

    Note the result is NOT divided by that factor again -- doing so is the bug `check_geo_vs_osm.py`
    shipped with, inflating east-west offsets by 1/cos(lat).
    """
    scale = math.cos(math.radians(p[0]))
    ax, ay = (a[1] - p[1]) * scale, a[0] - p[0]
    bx, by = (b[1] - p[1]) * scale, b[0] - p[0]
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    if den == 0:
        return math.hypot(ax, ay) * 111320.0
    t = max(0.0, min(1.0, -(ax * dx + ay * dy) / den))
    return math.hypot(ax + t * dx, ay + t * dy) * 111320.0


def dist_profile(short, long_):
    """Per-point distance from each point of `short` to the nearest SEGMENT of `long_`."""
    grid = {}
    cell = 0.002
    for i in range(1, len(long_)):
        a, b = long_[i - 1], long_[i]
        k0 = (int(math.floor(a[0] / cell)), int(math.floor(a[1] / cell)))
        k1 = (int(math.floor(b[0] / cell)), int(math.floor(b[1] / cell)))
        for ky in range(min(k0[0], k1[0]), max(k0[0], k1[0]) + 1):
            for kx in range(min(k0[1], k1[1]), max(k0[1], k1[1]) + 1):
                grid.setdefault((ky, kx), []).append((a, b))
    out = []
    for p in short:
        ky, kx = int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))
        best = 9999.0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for a, b in grid.get((ky + dy, kx + dx), ()):
                    d = _seg_dist_m(p, a, b)
                    if d < best:
                        best = d
        out.append(best)
    return out


def profile_shape(prof, tol=TOL_M):
    """Classify the per-point distance sequence: 'subsumed' | 'junction' | 'unclear'.

    The aggregate fraction cannot tell these apart, and getting it wrong in either direction is a real
    error: calling a junction a duplicate deletes a trail that genuinely exists, and calling a duplicate a
    junction leaves two entries on one piece of ground.
    """
    n = len(prof)
    if n < 4:
        return "unclear"
    near = [d <= tol for d in prof]
    if all(near):
        return "subsumed"
    # Magnitude before shape. A line that never gets further than a few tens of metres away is the same
    # line, whatever its distance sequence looks like -- that is simplification and survey noise between
    # two sources, not a fork. Without this, a gentle 1->52 m drift over twelve points fell through every
    # shape branch and came out "unclear" purely because its near-run was 58% of the points instead of 60%,
    # i.e. it was being decided by a run-length threshold rather than by anything meaningful.
    if max(prof) <= tol * 3:
        return "subsumed"
    # A junction diverges from ONE end and never comes back: find the longest near-run, and require it to
    # start at an end, with everything after it growing away more or less monotonically.
    best_len, best_start = 0, 0
    i = 0
    while i < n:
        if near[i]:
            j = i
            while j < n and near[j]:
                j += 1
            if j - i > best_len:
                best_len, best_start = j - i, i
            i = j
        else:
            i += 1
    if best_len == 0:
        return "unclear"
    touches_start = best_start == 0
    touches_end = best_start + best_len == n
    tail = prof[best_start + best_len:] if touches_start else (
        prof[:best_start][::-1] if touches_end else None)
    if tail is not None and len(tail) >= 3:
        # allow small dips: count how much of the tail is non-decreasing
        rises = sum(1 for k in range(1, len(tail)) if tail[k] >= tail[k - 1] - tol * 0.25)
        if rises / (len(tail) - 1) >= 0.75 and max(tail) > tol * 4:
            return "junction"
    if touches_start and touches_end:
        return "subsumed"
    if not touches_start and not touches_end:
        # Near in the MIDDLE, away at both ends. Two very different things look like this and only the
        # magnitude of the two excursions tells them apart: a duplicate whose ends wander off by a few tens
        # of metres (noise, still the same trail), versus a short line that genuinely runs out past both
        # ends of its match (a different trail crossing it). Judging by shape alone called the first one
        # "unclear" and left a real duplicate for the user to decide by hand.
        excursion = max(prof[:best_start] + prof[best_start + best_len:])
        return "subsumed" if excursion <= tol * 4 else "unclear"
    return "subsumed" if best_len / n >= 0.6 else "unclear"


def main():
    _utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True,
                    help='JSON {slug: [[lat,lon],...]} of the incoming Trailforks geometry')
    ap.add_argument("--meta", help='JSON listing with name/difficulty per slug (rlp_listing.json)')
    ap.add_argument("--out", default="decisions.json")
    ap.add_argument("--tol", type=float, default=TOL_M)
    args = ap.parse_args()

    d = json.load(open(REGION, encoding="utf-8"))
    geo = d["trailGeo"]
    old = [t for t in d["lineTrails"]
           if not t.get("loop") and t["region"] not in EXCLUDE_SUBREGIONS]
    new = json.load(open(args.new, encoding="utf-8"))
    if isinstance(new, dict) and "rows" in new:
        new = new["rows"]

    old_pre = [(t, geo[t["id"]], line_len_m(geo[t["id"]]), bbox(geo[t["id"]], BBOX_PAD_DEG))
               for t in old]
    new_pre = [(s, c, line_len_m(c), bbox(c)) for s, c in new.items()]
    print("vergleiche %d bestehende (ohne %s) gegen %d neue Trailforks-Trails"
          % (len(old_pre), "/".join(EXCLUDE_SUBREGIONS), len(new_pre)))

    decisions = {"replace": [], "keep": [], "review": []}
    for t, oc, olen, ob in old_pre:
        best = None
        for slug, nc, nlen, nb in new_pre:
            if not bbox_overlaps(ob, nb):
                continue
            short, long_ = (oc, nc) if olen <= nlen else (nc, oc)
            prof = dist_profile(short, long_)
            frac = sum(1 for x in prof if x <= args.tol) / len(prof)
            if best is None or frac > best["frac"]:
                best = {"slug": slug, "frac": round(frac, 3), "shape": profile_shape(prof, args.tol),
                        "short_is_old": olen <= nlen, "old_m": round(olen), "new_m": round(nlen),
                        "prof": [round(x) for x in prof]}
        rec = {"old_id": t["id"], "old_name": t["name"], "region": t["region"], "diff": t["diff"],
               "old_m": round(olen), "match": best}
        if best is None or best["frac"] < MAYBE_LOW:
            decisions["keep"].append(rec)
        elif best["frac"] >= SURE_REPLACE and best["shape"] == "subsumed":
            decisions["replace"].append(rec)
        elif best["shape"] == "junction":
            decisions["keep"].append(rec)
        else:
            decisions["review"].append(rec)

    for k in decisions:
        print("   %-8s %4d" % (k, len(decisions[k])))
    json.dump(decisions, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("geschrieben: %s" % args.out)


if __name__ == "__main__":
    main()
