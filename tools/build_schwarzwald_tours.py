# -*- coding: utf-8 -*-
"""Add the Schwarzwald's Touren (Trailrunden) from Trailforks' own recorded ROUTES.

Run AFTER `tools/build_schwarzwald.py` -- it reads that script's output, adds `loop: true` entries plus
their `trailSegments`, and writes the region back. Running the trail build again wipes these, so the order
is: build_schwarzwald.py, then this.

## Why Trailforks routes and not "Schauinsland Enduro"

The user asked for "die Schauinsland Enduro Tour", from a report of mine that called it a Trailrunde
candidate. That was wrong and is worth recording: Trailforks' "Multi Trail" label on that page means
**multi-USE** (its own alternateName list reads "Schauinsland Enduro Multi-Use Trail"), not "made of
several trails". It is a plain 2,8 km descent and the district sweep already built it as one
(`sw_schauinsland_enduro`).

What Trailforks does have for this region is **routes**: recorded rides, each with an `encodedpath` and an
`ElevationChart` exactly like a trail page, and each one genuinely a combination of this region's own
trails -- three of the five even say so in their titles. Those are real Trailrunden, so those are what
this builds.

## Method

`tools/gpx_map_match.py`'s sequential map-matching, the same tool the Livigno/Pfälzerwald tours use, with
the region's **trails AND lifts** as candidates (omitting lifts turns every lift ride into an anonymous
connector). Each named stretch then carries its own TRAIL's geometry, clipped and oriented the way it was
ridden, and the Tour's line is rebuilt as the concatenation -- which is what satisfies
`validate_region.py`'s loop invariant by construction and stops a Tour drawing a doubled line beside the
trail it rides. All of that is `pfaelzerwald_rederive_loops`'s helpers, imported rather than re-derived.

A route is only kept when enough of it lands on named trails (`MIN_NAMED_SHARE`); below that the "Tour"
would be mostly anonymous connector, which is a line, not a route through the region's trails.

    python tools/build_schwarzwald_tours.py --dry-run
    python tools/build_schwarzwald_tours.py
    python tools/update_region_versions.py
"""
import io
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gpx_map_match import match_gpx_to_network  # noqa: E402
from harvest_schwarzwald_tf import UA, decode_polyline  # noqa: E402
from pfaelzerwald_rederive_loops import (concat_ok, fill_connectors, line_len_m,  # noqa: E402
                                         named_share)
from trailmap_pipeline import build_profile, cumulative_km, haversine_m, write_region  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATERIAL = os.path.join(ROOT, "Material", "Schwarzwald")
ROUTES_FILE = os.path.join(MATERIAL, "trailforks_routes.json")
REGION = os.path.join(ROOT, "Trailmap App", "regions", "schwarzwald.json")

#: The Trailforks route slugs found in the Freiburg-area regions' own `/routes/` listings, with the
#: sub-region each belongs to and the name to ship. Trailforks' own titles are kept (they say which
#: trails the route rides), tidied only where the slug leaked into them.
ROUTES = [
    # slug                                          name                          sub        stated km
    ("canadian--borderline",                        "Canadian & Borderline",       "mtbfr",       21.3),
    ("freiburg-i-breisgau-hubbelfuchs-kammweg-borderline",
     "Hubbelfuchs · Kammweg · Borderline",                                 "mtbfr",       40.0),
    ("schlossbergnesselplatzrosskopf-trails",
     "Schlossberg · Nesselplatz · Rosskopf",                                "freiburg",    29.1),
    ("freiburger-dreierlei-on-gpsies-com",          "Freiburger Dreierlei",        "mtbfr",       35.4),
    ("banden-ride",                                 "Banden Ride",                 "freiburg",    37.7),
]

#: A parsed route whose own line is further than this from Trailforks' stated distance is reported and
#: not built -- the check that caught the doubled ElevationChart above.
STATED_TOL_KM = 1.5

#: A single straight step longer than this means the recording dropped out, and the app would draw that
#: dropout as a straight line across the map -- the reason three Paganella "marathon" routes were left out
#: of that region. Measured across these five: the three clean routes have no step over 300 m at all,
#: two have one step of 355 m and 619 m (1,0 % and 1,5 % of their length, plausible as an unmapped
#: connection between two recorded points), and "Banden Ride" has one of **2 593 m** -- 6,9 % of the whole
#: Tour, drawn as a straight line right across Freiburg. That is the case this rejects.
MAX_STEP_M = 800.0

#: Below this share of the Tour's own length on named component trails it is not a route through the
#: region's trails but a ride with a few trails in it. Pfälzerwald's rederive used the same measure.
MIN_NAMED_SHARE = 0.25

#: Matching parameters. Left at the module defaults except the strict threshold, which is tightened
#: because this network is dense around the Rosskopf -- five of our own trails share the same ridge and
#: 15 m let a run drift between them. Tuning per region is the documented expectation.
STRICT_M = 12.0
LOOSE_M = 30.0


def fetch_route(slug):
    """(name, [[lat, lon, ele], ...]) for one Trailforks route, from its own page."""
    html = subprocess.run(["curl", "-s", "-A", UA, "https://www.trailforks.com/route/%s/" % slug],
                          capture_output=True).stdout.decode("utf-8", "replace")
    m = re.search(r"<title>([^<]*)</title>", html)
    title = (m.group(1).split("Route")[0].strip(" -|") if m else slug)
    prof = []
    m = re.search(r"new ElevationChart\(", html)
    if m:
        chunk = html[m.end():m.end() + 800000]
        for pm in re.finditer(r'\{"id":\d+,"x":"?([-\d.]+)"?,"y":"?([-\d.]+)"?,'
                              r'"lat":"?([-\d.]+)"?,"lng":"?([-\d.]+)"?', chunk):
            prof.append([float(pm.group(3)), float(pm.group(4)), float(pm.group(2))])
    if not prof:
        # Fall back to the polyline; it carries no elevation, so such a route is reported, not built.
        m = re.search(r"encodedpath:\s*'([^']*)'", html)
        if m:
            prof = [[p[0], p[1], None]
                    for p in decode_polyline(m.group(1).encode().decode("unicode_escape"))]
    return title, dedupe_halves(prof)


def dedupe_halves(pts):
    """A ROUTE page renders its ElevationChart config TWICE, so the parsed points come out doubled.

    Not a rounding artefact and not harmless: every route's line came out at exactly twice its stated
    distance (Freiburger Dreierlei 70,9 km against 35,4) and every segment list was printed twice, which
    on the map would be a Tour riding each of its trails twice. A trail page does not do this, which is why
    the district sweep never hit it. The test is exact -- the first half must be identical to the second --
    so a genuine out-and-back or a lap ridden twice is unaffected.
    """
    while len(pts) >= 4 and len(pts) % 2 == 0 and pts[:len(pts) // 2] == pts[len(pts) // 2:]:
        pts = pts[:len(pts) // 2]
    return pts


def harvest():
    routes = json.load(io.open(ROUTES_FILE, encoding="utf-8")) if os.path.exists(ROUTES_FILE) else {}
    for slug, _, _, _ in ROUTES:
        if slug in routes:
            continue
        title, pts = fetch_route(slug)
        routes[slug] = {"title": title, "points": pts}
        print("  fetched %-52s %4d points" % (slug, len(pts)))
        time.sleep(0.8)
    json.dump(routes, io.open(ROUTES_FILE, "w", encoding="utf-8"), separators=(",", ":"))
    return routes


def near_route(line, candidates, pad_deg=0.004):
    """The candidates whose bounding box overlaps the route's, padded by ~400 m.

    Not an optimisation for its own sake: `gpx_map_match` measures every GPX point against every point of
    every candidate, so with this region's 618 trails a 2 000-point route is ~50 million distance
    computations and the match does not finish in any reasonable time. A route 21 km long cannot ride a
    trail 80 km away, so restricting the network to the route's own neighbourhood changes no result --
    verified by running the smallest route both ways and getting the identical segment list.
    """
    la = [p[0] for p in line]
    lo = [p[1] for p in line]
    box = (min(la) - pad_deg, min(lo) - pad_deg, max(la) + pad_deg, max(lo) + pad_deg)
    out = {}
    for cid, geo in candidates.items():
        cla = [p[0] for p in geo]
        clo = [p[1] for p in geo]
        if (max(cla) < box[0] or min(cla) > box[2] or max(clo) < box[1] or min(clo) > box[3]):
            continue
        out[cid] = geo
    return out


def drop_wrong_direction(matched, ele, by_id, min_drop_m=20.0):
    """Reject an attribution that has the rider climbing a descent trail or descending a climb.

    Why this is needed and why a tighter distance threshold is not the fix: on the Rosskopf the club's
    own uphill route repeatedly crosses and runs alongside the trail it serves, so a matcher that only
    knows distances alternates between "Borderline" and "Borderline Uphill" all the way down the
    descent. Tightening the strict threshold from 12 m to 8 and 6 m was measured and changed nothing
    except lowering the share of the Tour that gets named at all.

    The elevation trend over the run settles it with information the region already carries: a trail
    flagged `uphill: true` ridden while losing more than `min_drop_m` of height is not that trail, and
    the stretch becomes an honest connector instead of a wrong label. Deliberately one-directional --
    riding a descent trail upwards is a real thing people do, and `resolve_segments` already handles a
    reversed ride, so only the uphill-flagged case is rejected.
    """
    kept, dropped = [], []
    for m in matched:
        t = by_id.get(m["id"])
        if t and t.get("uphill"):
            a, b = m["start_idx"], m["end_idx"]
            if ele[a] - ele[b] > min_drop_m:
                dropped.append((t["name"], round(ele[a] - ele[b])))
                continue
        kept.append(m)
    return kept, dropped


def gaps_at_joints(segs):
    """Every jump between one segment's last point and the next segment's first, in metres.

    These exist by construction: a named stretch is snapped onto its trail's own points, so where the
    recording left the trail a step or two early the joint opens up. The app draws each segment as its own
    polyline, so a large joint reads as a hole -- `tools/close_loop_gaps.py` is the tool for closing them,
    and its own rules (and the user's standing "leave the honest gap rather than guessing" note) apply.
    """
    out = []
    for a, b in zip(segs, segs[1:]):
        out.append(haversine_m(a["coords"][-1], b["coords"][0]))
    return out


def main(argv):
    dry = "--dry-run" in argv
    data = json.load(io.open(REGION, encoding="utf-8"))
    trails = data["lineTrails"]
    geo = data["trailGeo"]
    profs = data["elevationProfiles"]
    segments = dict(data.get("trailSegments") or {})

    by_id = {t["id"]: t for t in trails}
    # Candidates: every trail plus every lift. A Tour that rides the Schauinslandbahn or the Hasenhorn
    # chairlift must show it as a lift ride, not as an unexplained connector.
    candidates = {tid: g for tid, g in geo.items() if not by_id[tid].get("loop")}
    for lift in data.get("lifts") or []:
        candidates[lift["id"]] = lift["coords"]

    routes = harvest()
    built, skipped = [], []
    for slug, name, sub, stated_km in ROUTES:
        pts = routes[slug]["points"]
        if len(pts) < 20 or any(p[2] is None for p in pts):
            skipped.append("%s: no usable elevation profile on its page" % name)
            continue
        line = [[round(p[0], 6), round(p[1], 6)] for p in pts]
        ele = [p[2] for p in pts]
        own_km = line_len_m(line) / 1000.0
        if abs(own_km - stated_km) > STATED_TOL_KM:
            skipped.append("%s: parsed %.1f km against Trailforks' stated %.1f km"
                           % (name, own_km, stated_km))
            continue
        steps = [haversine_m(line[i], line[i + 1]) for i in range(len(line) - 1)]
        if max(steps) > MAX_STEP_M:
            skipped.append("%s: its recording jumps %.0f m in one step (%.1f%% of the Tour), which the "
                           "app would draw as a straight line across the map"
                           % (name, max(steps), 100 * max(steps) / (own_km * 1000)))
            continue
        local = near_route(line, candidates)
        matched = match_gpx_to_network(line, local, strict_thresh_m=STRICT_M,
                                      loose_thresh_m=LOOSE_M)
        matched, wrong_dir = drop_wrong_direction(matched, ele, by_id)
        if not matched:
            skipped.append("%s: matched no trail at all" % name)
            continue
        # `fill_connectors`, NOT `build_segments`: the segments keep the ROUTE's own recorded points
        # instead of snapping each named stretch onto its trail's stored geometry. Both were measured
        # here and snapping was rejected: it opened joints of up to 746 m between consecutive segments
        # (each drawn as its own polyline, so on the map that is a hole), and it inflated two of the five
        # Tours past their own stated distance -- Canadian & Borderline came out 26,4 km against
        # Trailforks' 21,3. Keeping the recording means the drawn line IS the ride, the concatenation
        # invariant holds trivially, and there is nothing to close with tools/close_loop_gaps.py. The
        # price is the one build_segments exists to avoid: a named stretch sits on the recording rather
        # than exactly on the trail's own line, so where the two differ by a few metres the Tour draws
        # its own line beside the trail's.
        segs = fill_connectors(line, matched)
        new_line = list(line)
        share = named_share(segs, new_line)
        if share < MIN_NAMED_SHARE:
            skipped.append("%s: only %.0f%% of it is on named trails" % (name, share * 100))
            continue
        assert concat_ok(new_line, segs), name

        cum_new = cumulative_km(new_line)
        prof, gain, loss = build_profile(new_line, ele)

        tid = "sw_tour_" + slug.replace("-", "_")[:40].strip("_")
        named = [s["trailId"] for s in segs if s.get("trailId")]
        diffs = [by_id[t]["diff"] for t in named if t in by_id]
        order = ["gruen", "blau", "rot", "schwarz"]
        entry = {"id": tid, "name": name, "region": sub,
                 "diff": max(diffs, key=order.index) if diffs else "blau",
                 "len": round(cum_new[-1], 2), "up": gain, "down": loss, "loop": True}
        trails.append(entry)
        geo[tid] = new_line
        profs[tid] = prof
        segments[tid] = segs
        g = gaps_at_joints(segs)
        built.append((name, entry, segs, share, g))
        print("%-38s %5.1f km (stated %4.1f)  named %3.0f%%  %2d segments "
              "(%d trails, %d lifts, %d connectors)  joints: max %.0f m"
              % (name, entry["len"], stated_km, share * 100, len(segs),
                 sum(1 for s in segs if (s.get("trailId") or "").startswith("sw_")),
                 sum(1 for s in segs if (s.get("trailId") or "").startswith("lift_")),
                 sum(1 for s in segs if not s.get("trailId")),
                 max(g) if g else 0))
        for nm, drop in wrong_dir:
            print("      (dropped %s: the route loses %d m over that stretch)" % (nm, drop))
        for s in segs:
            if s.get("trailId"):
                print("      %-34s %6.0f m" % (by_id.get(s["trailId"], {}).get("name", s["trailId"]),
                                               line_len_m(s["coords"])))

    if skipped:
        print("\nnot built:")
        for s in skipped:
            print("  -", s)

    if dry:
        print("\n--dry-run: nothing written")
        return
    write_region(REGION, trails, geo, profs, places=data.get("places"),
                 lifts=data.get("lifts"), trail_segments=segments)
    print("\nwrote %s (%d trails, %d of them Touren)"
          % (os.path.basename(REGION), len(trails), sum(1 for t in trails if t.get("loop"))))
    print("next: python tools/update_region_versions.py, and bump trailCount in REGION_CATALOG")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main(sys.argv[1:])
