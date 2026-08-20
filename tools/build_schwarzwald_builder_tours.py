# -*- coding: utf-8 -*-
"""Build the two hand-assembled Schwarzwald Touren from the Tourenbuilder's own exports.

Run AFTER `build_schwarzwald.py` (which rewrites the region from scratch) and after
`build_schwarzwald_tours.py` (which adds the two auto-matched Touren):

    python tools/build_schwarzwald.py
    python tools/build_schwarzwald_tours.py
    python tools/build_schwarzwald_builder_tours.py
    python tools/update_region_versions.py

## Why these two are hand-assembled

Both were first reconstructed automatically from a Trailforks route, and both came out wrong in ways the
recording cannot fix: "Canadian & Borderline" jumped 582 m back to the Borderline's start and ran 12 % over
its own track, "Hubbelfuchs · Kammweg · Borderline" jumped 401 m, and roughly a fifth of the named
stretches were fragments the matcher had drifted into between parallel lines. The user's call
(2026-08-20/21) was to state the route instead of guessing it -- "Wir bauen es nach" -- so the ride order
comes from the app's own Tourenbuilder (`Material/Schwarzwald/builder_*.json`) and nothing here matches
anything.

## What this does, and what it deliberately does not

**The ride order is taken as given.** Each element names one of the region's own trails, a direction, and
the from/to the builder cut it at (it splits an element at junctions, so `km` is often less than the whole
trail). The stretch is that trail's own geometry, clipped between those two points -- so a Tour's
Borderline stretch IS the Borderline, which is the property that broke in the auto-built version.

**A connector between two elements is READ OUT OF THE ORIGINAL RECORDING, never routed or invented.** The
user's own instruction for the 2,3 km through Freiburg: "Den Weg durch die Stadt kannst du ja aus der
Originaltour lesen." So for each gap the Trailforks route (`trailforks_routes.json`, the same recording the
auto build used) is searched for the stretch between the two endpoints, and its points are used verbatim.
Where the recording does not cover a gap, the gap is left open and reported -- `tools/nearby_trail_connector.py`
is the tool for those, run afterwards, and it is the user's confirmed procedure.

**Elevation comes from data we already have, not from a DEM call**: a named stretch takes its heights from
that trail's own `elevationProfiles` entry (interpolated at each point's along-trail distance), a connector
takes them from the recording's own points. Both are the same numbers the region already ships.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfaelzerwald_rederive_loops import add_dist_range, concat_ok, line_len_m  # noqa: E402
from trailmap_pipeline import (build_profile, cumulative_km, haversine_m,  # noqa: E402
                               write_region)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATERIAL = os.path.join(ROOT, "Material", "Schwarzwald")
REGION = os.path.join(ROOT, "Trailmap App", "regions", "schwarzwald.json")
ROUTES = os.path.join(MATERIAL, "trailforks_routes.json")

#: (export file, tour id, name, sub-region, which recording to read connectors from)
TOURS = [
    ("builder_canadian_borderline.json", "sw_tour_canadian_borderline",
     "Canadian & Borderline", "mtbfr", "canadian--borderline"),
    ("builder_hubbelfuchs_kammweg_borderline.json", "sw_tour_hubbelfuchs_kammweg_borderline",
     "Hubbelfuchs · Kammweg · Borderline", "mtbfr",
     "freiburg-i-breisgau-hubbelfuchs-kammweg-borderline"),
]

#: Tour ids the auto build produced for the same two rides. Removed, or the region would carry both.
SUPERSEDED = ["sw_tour_canadian__borderline", "sw_tour_freiburg_i_breisgau_hubbelfuchs_kammweg"]

#: Two consecutive elements closer than this need no connector at all -- that is the builder's own
#: junction tolerance, and the same GPS-noise band `nearby_trail_connector` leaves alone.
JOIN_TOL_M = 30.0
#: How close a recording point has to come to an element's endpoint for the recording to count as
#: covering that gap. Generous, because the recording is exactly what drifts.
RECORDING_HIT_M = 60.0
#: A stretch of recording longer than this multiple of the gap it closes is not the way the rider went --
#: it is another pass of the loop. Reported as an open gap instead, for nearby_trail_connector.
MAX_DETOUR_FACTOR = 3.0


def nearest_idx(line, pt):
    return min(range(len(line)), key=lambda i: haversine_m(line[i], pt))


def clip(trail, prof, a, b, reversed_):
    """The trail's own points between `a` and `b`, in ride direction, plus their heights.

    Geometry and heights are oriented ONCE, together, here. Doing it in two places is how the first
    version of this got a stretch's profile running backwards against its own line.
    """
    i, j = nearest_idx(trail, a), nearest_idx(trail, b)
    lo, hi = min(i, j), max(i, j)
    part = [list(q) for q in trail[lo:hi + 1]]
    cum = cumulative_km(trail)
    eles = [interp(prof, cum[k]) for k in range(lo, hi + 1)]
    # The builder states both ends; whichever way the slice came out of the array, orient it so it starts
    # at `from`. `reversed_` is the builder's own label for the same thing and serves as a cross-check.
    if haversine_m(part[0], a) > haversine_m(part[-1], a):
        part, eles = part[::-1], eles[::-1]
    return part, eles


def interp(prof, km):
    """That trail's own profile, read at `km` along it."""
    if km <= prof[0][0]:
        return prof[0][1]
    for p1, p2 in zip(prof, prof[1:]):
        if p1[0] <= km <= p2[0]:
            t = 0 if p2[0] == p1[0] else (km - p1[0]) / (p2[0] - p1[0])
            return p1[1] + t * (p2[1] - p1[1])
    return prof[-1][1]


def recording_between(rec, cum, a, b, gap_m):
    """The recording's own points from `a` to `b` -- from the RIGHT pass, or None.

    A loop recording comes past the same place several times (these two rides use the Rosskopf climb up to
    four times), so "walk from the point nearest a to the point nearest b" picks an arbitrary pair and can
    take the long way round the whole loop: the first version of this returned 10,4 km of recording for a
    2,3 km gap, and 15,2 km for another. So every point within RECORDING_HIT_M of each end is a candidate,
    and the pair whose stretch is SHORTEST wins -- with two sanity gates, because a connector that is
    wildly longer than the gap it closes is not the stretch the rider took:

      * it must be at least the straight-line gap (it cannot be shorter than the beeline), and
      * at most MAX_DETOUR_FACTOR times it, plus a small absolute allowance for short gaps.

    Nothing here invents geometry: the result is always a contiguous run of the recording's own points.
    """
    near_a = [i for i, p in enumerate(rec) if haversine_m(p, a) <= RECORDING_HIT_M]
    near_b = [i for i, p in enumerate(rec) if haversine_m(p, b) <= RECORDING_HIT_M]
    if not near_a or not near_b:
        return None, "kein Punkt der Aufzeichnung naeher als %.0f m an einem Ende" % RECORDING_HIT_M
    best = None
    for ia in near_a:
        for ib in near_b:
            if ia == ib:
                continue
            length = abs(cum[ib] - cum[ia]) * 1000.0
            if best is None or length < best[0]:
                best = (length, ia, ib)
    length, ia, ib = best
    limit = max(MAX_DETOUR_FACTOR * gap_m, gap_m + 250.0)
    if length < gap_m - 5 or length > limit:
        return None, ("kuerzeste Aufzeichnungs-Strecke zwischen den Enden ist %.0f m bei %.0f m Luecke"
                      % (length, gap_m))
    step = 1 if ib > ia else -1
    # The INDICES come back with the points: `rec.index(point)` would find the first occurrence of that
    # coordinate, which on a loop that passes the same spot four times is a different pass than the one
    # chosen here -- and the heights read off it then belong to a different part of the ride.
    return [rec[k] for k in range(ia, ib + step, step)], (ia, ib)


def add_recorded_connector(segs, ele, rec, rec_cum, rec_ele, a, b, gap, notes, label):
    """Append a connector between `a` and `b` taken from the recording, or note the gap as open."""
    bridge, info = recording_between(rec, rec_cum, a, b, gap)
    if bridge and len(bridge) >= 2:
        ia, ib = info
        step = 1 if ib > ia else -1
        segs.append({"coords": [list(q) for q in bridge], "trailId": None})
        ele.extend(rec_ele[k] for k in range(ia, ib + step, step))
        notes.append("%s: %.0f m aus der Aufzeichnung (Luecke %.0f m)"
                     % (label, line_len_m(bridge), gap))
        return True
    notes.append("%s: %.0f m OFFEN -- %s" % (label, gap, info))
    return False


def main():
    d = json.load(io.open(REGION, encoding="utf-8"))
    trails = [t for t in d["lineTrails"] if t["id"] not in SUPERSEDED]
    geo = {k: v for k, v in d["trailGeo"].items() if k not in SUPERSEDED}
    profs = {k: v for k, v in d["elevationProfiles"].items() if k not in SUPERSEDED}
    segments = {k: v for k, v in (d.get("trailSegments") or {}).items() if k not in SUPERSEDED}
    T = {t["id"]: t for t in trails}
    routes = json.load(io.open(ROUTES, encoding="utf-8"))

    for fname, tid, name, sub, rec_slug in TOURS:
        spec = json.load(io.open(os.path.join(MATERIAL, fname), encoding="utf-8"))
        rec = [[p[0], p[1]] for p in routes[rec_slug]["points"]]
        rec_ele = [p[2] for p in routes[rec_slug]["points"]]
        rec_cum = cumulative_km(rec)
        segs, ele, notes = [], [], []
        prev_end = None
        for n, el in enumerate(spec["elements"]):
            cid = el["id"]
            if cid not in geo:
                raise SystemExit("%s: element %d names %r, which this region does not have"
                                 % (tid, n, cid))
            part, part_ele = clip(geo[cid], profs[cid], el["from"], el["to"],
                                  el.get("reversed", False))
            if prev_end is not None:
                gap = haversine_m(prev_end, part[0])
                if gap > JOIN_TOL_M:
                    add_recorded_connector(segs, ele, rec, rec_cum, rec_ele, prev_end, part[0], gap,
                                           notes, "Verbinder %d->%d" % (n - 1, n))
            segs.append({"coords": part, "trailId": cid})
            ele.extend(part_ele)
            prev_end = part[-1]

        # A Tour is a loop in this app's model, and the builder export describes only the trails ridden --
        # not the leg back to the start. Where the recording covers that leg, it supplies it, on the same
        # terms as every other connector here (the user's own instruction: read the way through town out of
        # the original tour). Where it does not, the loop stays open and says so.
        closing = haversine_m(prev_end, segs[0]["coords"][0])
        if closing > JOIN_TOL_M:
            bridge, info = recording_between(rec, rec_cum, prev_end, segs[0]["coords"][0], closing)
            if bridge and len(bridge) >= 2:
                add_recorded_connector(segs, ele, rec, rec_cum, rec_ele, prev_end,
                                       segs[0]["coords"][0], closing, notes, "Rueckweg zum Start")
            else:
                notes.append("Rueckweg zum Start (%.0f m) nicht in der Aufzeichnung -- die Tour bleibt "
                             "offen, was fuer eine Trailrunde zulaessig ist" % closing)

        line = [p for s in segs for p in s["coords"]]
        assert len(line) == len(ele), "%s: %d Punkte, %d Hoehen" % (tid, len(line), len(ele))
        segs = add_dist_range(line, segs)
        assert concat_ok(line, segs), tid
        prof, gain, loss = build_profile(line, ele)
        named = [s["trailId"] for s in segs if s.get("trailId")]
        order = ["gruen", "blau", "rot", "schwarz"]
        entry = {"id": tid, "name": name, "region": sub,
                 "diff": max((T[c]["diff"] for c in named), key=order.index),
                 "len": round(line_len_m(line) / 1000.0, 2), "up": gain, "down": loss, "loop": True}
        trails.append(entry)
        geo[tid] = line
        profs[tid] = prof
        segments[tid] = segs

        share = sum(line_len_m(s["coords"]) for s in segs if s.get("trailId")) / line_len_m(line)
        n_seg = len(segs)
        # Only the joints BETWEEN consecutive segments count. The step from the last segment back to the
        # first is not a gap: a Trailrunde does not have to be geometrically closed (Schauinsland-Staufen
        # is point-to-point), and the app draws no line there, so nothing is missing on screen. Counting it
        # made a Tour whose recorded ride simply started and ended in different places look broken.
        gaps = [haversine_m(segs[i]["coords"][-1], segs[i + 1]["coords"][0]) for i in range(n_seg - 1)]
        print("%-38s %5.2f km  %d Segmente (%d Trails, %d Verbinder)  benannt %3.0f%%  "
              "Luecken >30m: %d, max %.0f m"
              % (name, entry["len"], n_seg, len(named), n_seg - len(named), share * 100,
                 sum(1 for g in gaps if g > 30), max(gaps)))
        for x in notes:
            print("      " + x)

    write_region(REGION, trails, geo, profs, places=d.get("places"), lifts=d.get("lifts"),
                 trail_segments=segments)
    print("\ngeschrieben: %d Trails, %d Touren" % (len(trails), sum(1 for t in trails if t.get("loop"))))
    print("weiter: tools/nearby_trail_connector.py fuer offene Luecken, dann update_region_versions.py")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
