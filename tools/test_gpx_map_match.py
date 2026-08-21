# -*- coding: utf-8 -*-
"""Regression harness for gpx_map_match.py, against tours this app has ALREADY built and
(to varying degrees) verified -- a growing test bed for improving the matcher without having to
re-litigate every case by hand each time. See tools/gpx_map_match.py's own docstring for the
method and memory note gpx-map-matching-tool for why this exists.

Ground-truth strength varies by case and is stated per case:
- "tourenbuilder": the user hand-built the exact ride in the app's own Tourenbuilder and exported
  it -- the strongest evidence available (Livigno's Tutti Frutti).
- "region": the tour's CURRENT trailSegments in the live region file, built by matching + at least
  one round of user-caught correction and a visual browser check -- trusted but not independently
  authored. Do not over-index on small length/seam differences against this kind of ground truth;
  a NEW result that disagrees is sometimes the matcher finding something the original build missed
  (or a case worth a human look), not automatically a matcher bug.

Run: python tools/test_gpx_map_match.py [case_name ...]  (omit args to run all cases)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import parse_gpx, cumulative_km, haversine_m
from gpx_map_match import match_gpx_to_network, resolve_segments, closest_point_on_polyline

#: Derived, not hardcoded: this file carried an absolute `D:\Trailmap` for both of these, which makes it
#: unrunnable on any other machine -- and the whole reason the plan lives in the repo is that it has to
#: survive a device change.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _region_path(key):
    return os.path.join(ROOT, "Trailmap App", "regions", f"{key}.json")


def _load_region(key):
    return json.load(open(_region_path(key), encoding="utf-8"))


def _candidates_from_region(region_data, exclude_ids=(), region_keys=None):
    """All trails+lifts in the region file, optionally restricted to given sub-region keys.

    ALWAYS excludes every `loop: true` entry (every Tour in this region file), not just the one
    being tested -- a Tour is never itself a ridable "component", and a region with several Tours
    (Bike Kingdom has 4, Naheland has 3) will otherwise silently offer one tour's own line as a
    candidate for matching a DIFFERENT tour, since their routes often overlap in a shared resort.
    Found via bk_tour_b2r_schwarz matching stretches of bk_tour_615_blau/616_rot/b2r_e_rot."""
    exclude_ids = set(exclude_ids) | {t["id"] for t in region_data["lineTrails"] if t.get("loop")}
    cands = {}
    for t in region_data["lineTrails"]:
        if t["id"] in exclude_ids:
            continue
        if region_keys and t["region"] not in region_keys:
            continue
        cands[t["id"]] = region_data["trailGeo"][t["id"]]
    for l in region_data.get("lifts") or []:
        if region_keys and l["region"] not in region_keys:
            continue
        cands[l["id"]] = l["coords"]
    return cands


def _ground_truth_from_region_segments(region_data, tour_id, candidates):
    """Read the tour's CURRENT trailSegments as a trusted-but-not-authored reference sequence:
    ordered (id, reversed) pairs, connectors dropped, consecutive dupes of the same id collapsed."""
    segs = region_data["trailSegments"][tour_id]
    seq = []
    for s in segs:
        cid = s.get("trailId") or s.get("liftId")
        if cid is None:
            continue
        cgeo = candidates.get(cid)
        reversed_ = False
        if cgeo and len(s["coords"]) >= 2:
            d0, _, _ = closest_point_on_polyline(cgeo, s["coords"][0])
            d_start_is_geo_start = haversine_m(cgeo[0], s["coords"][0])
            d_start_is_geo_end = haversine_m(cgeo[-1], s["coords"][0])
            reversed_ = d_start_is_geo_end < d_start_is_geo_start
        if seq and seq[-1][0] == cid:
            continue
        seq.append((cid, reversed_))
    return seq


def _extract_waldmeister_gpx(json_path):
    """Waldmeister's own source isn't a GPX file -- it's Outdooractive's trackinfo API response,
    saved raw. Same extraction as the original build (segments[].routes[].features[].geometry)."""
    data = json.load(open(json_path, encoding="utf-8"))
    track = data["answer"]["contents"][0]["track"]
    pts = []
    for seg in track["segments"]:
        for route in seg.get("routes") or []:
            for feat in route.get("features") or []:
                geom = feat.get("geometry") or {}
                if geom.get("type") != "LineString":
                    continue
                for c in geom["coordinates"]:
                    lon, lat = c[0], c[1]
                    pt = [lat, lon]
                    if pts and pts[-1] == pt:
                        continue
                    pts.append(pt)
    return pts


def _lcs_align(a_ids, b_ids):
    """Longest-common-subsequence alignment on id sequences only (ignores direction/length) --
    a single early miss (a lift the matcher dropped, say) must not cascade into looking like every
    later element is also wrong, which is exactly what naive positional i==i comparison does.
    Returns the list of (i, j) index pairs that align, in order."""
    n, m = len(a_ids), len(b_ids)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if a_ids[i] == b_ids[j]:
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    pairs = []
    i = j = 0
    while i < n and j < m:
        if a_ids[i] == b_ids[j]:
            pairs.append((i, j))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def _compare(name, ground_truth, resolved):
    print(f"\n=== {name} ===")
    print(f"ground truth: {len(ground_truth)} elements, matcher: {len(resolved)} segments")
    gt_ids = [g[0] for g in ground_truth]
    auto_ids = [r["id"] for r in resolved]
    pairs = _lcs_align(gt_ids, auto_ids)
    aligned_gt = {i for i, j in pairs}
    aligned_auto = {j for i, j in pairs}
    dir_ok = sum(1 for i, j in pairs if ground_truth[i][1] == resolved[j]["reversed"])

    gi = ai = 0
    for i, j in pairs + [(len(ground_truth), len(resolved))]:
        while gi < i:
            print(f"  MISS  gt[{gi:2d}]  {ground_truth[gi][0]:38s} rev={ground_truth[gi][1]!s:5s}  "
                  f"(matcher never found this)")
            gi += 1
        while ai < j:
            print(f"  EXTRA         auto[{ai:2d}] {resolved[ai]['id']:38s} rev={resolved[ai]['reversed']!s:5s}  "
                  f"(matcher found this, not in ground truth)")
            ai += 1
        if i < len(ground_truth):
            gt_id, gt_rev = ground_truth[i]
            r = resolved[j]
            dmark = "" if gt_rev == r["reversed"] else " (DIR MISMATCH)"
            print(f"  OK    gt[{i:2d}]=auto[{j:2d}] {gt_id:38s} rev={gt_rev!s:5s}{dmark}")
            gi = i + 1
            ai = j + 1

    id_order_ok = len(pairs)
    print(f"  summary: {id_order_ok}/{len(ground_truth)} ground-truth elements found (LCS-aligned, "
          f"order-preserving), {len(ground_truth) - id_order_ok} missed, "
          f"{len(resolved) - id_order_ok} extra; direction correct on {dir_ok}/{id_order_ok} of the aligned ones")
    return id_order_ok, dir_ok, len(ground_truth)


def case_livigno_tutti_frutti():
    d = _load_region("livigno")
    candidates = _candidates_from_region(d, exclude_ids={"c3000_tutti_frutti"},
                                          region_keys={"carosello3000mtb", "carosello3000natur"})
    gpx = parse_gpx(open(os.path.join(ROOT, "Material", "Livigno", "tutti-frutti-original.gpx"),
                          encoding="utf-8", errors="replace").read())
    builder = json.load(open(os.path.join(ROOT, "Material", "Livigno",
                                           "tutti-frutti-tourenbuilder-export.json"), encoding="utf-8"))
    ground_truth = [(el["id"], el["reversed"]) for el in builder["elements"]]
    segs = match_gpx_to_network(gpx, candidates)
    resolved = resolve_segments(gpx, candidates, segs)
    return "Livigno Tutti Frutti (ground truth: tourenbuilder)", ground_truth, resolved


def case_waldmeister():
    d = _load_region("waldmeister")
    tour_id = "wm_radlust_waldmeister"
    candidates = _candidates_from_region(d, exclude_ids={tour_id})
    gpx = _extract_waldmeister_gpx(os.path.join(ROOT, "Material", "Waldmeister",
                                                 "outdooractive-trackinfo-42450801.json"))
    ground_truth = _ground_truth_from_region_segments(d, tour_id, candidates)
    segs = match_gpx_to_network(gpx, candidates)
    resolved = resolve_segments(gpx, candidates, segs)
    return "RadLust Waldmeister (ground truth: region build)", ground_truth, resolved


def case_naheland(tour_id, gpx_filename):
    d = _load_region("naheland")
    candidates = _candidates_from_region(d, exclude_ids={tour_id})
    gpx = parse_gpx(open(os.path.join(ROOT, "Material", "Naheland", "tours", gpx_filename),
                          encoding="utf-8", errors="replace").read())
    ground_truth = _ground_truth_from_region_segments(d, tour_id, candidates)
    segs = match_gpx_to_network(gpx, candidates)
    resolved = resolve_segments(gpx, candidates, segs)
    return f"Naheland {tour_id} (ground truth: region build)", ground_truth, resolved


def case_bikekingdom(tour_id, gpx_filename):
    d = _load_region("bikekingdom")
    candidates = _candidates_from_region(d, exclude_ids={tour_id})
    gpx = parse_gpx(open(os.path.join(ROOT, "Material", "BikeKingdom", gpx_filename),
                          encoding="utf-8", errors="replace").read())
    ground_truth = _ground_truth_from_region_segments(d, tour_id, candidates)
    segs = match_gpx_to_network(gpx, candidates)
    resolved = resolve_segments(gpx, candidates, segs)
    return f"Bike Kingdom {tour_id} (ground truth: region build)", ground_truth, resolved


def case_portesdusoleil():
    d = _load_region("portesdusoleil")
    tour_id = "pds_tour_vtt_2025"
    candidates = _candidates_from_region(d, exclude_ids={tour_id})
    gpx = parse_gpx(open(os.path.join(ROOT, "Material", "Portes du Soleil",
                                       "Portes Du Soleil MTB Tour .gpx"), encoding="utf-8", errors="replace").read())
    ground_truth = _ground_truth_from_region_segments(d, tour_id, candidates)
    segs = match_gpx_to_network(gpx, candidates)
    resolved = resolve_segments(gpx, candidates, segs)
    return "Portes du Soleil Tour VTT (ground truth: region build)", ground_truth, resolved


CASES = {
    "livigno": case_livigno_tutti_frutti,
    "waldmeister": case_waldmeister,
    "naheland_flow": lambda: case_naheland("nlt_flow_tour", "flow-tour.gpx"),
    "naheland_panorama": lambda: case_naheland("nlt_panorama_tour", "panorama-tour.gpx"),
    "naheland_enduro": lambda: case_naheland("nlt_enduro_tour", "enduro-tour.gpx"),
    "bk_615": lambda: case_bikekingdom("bk_tour_615_blau", "t2805733_615 biketicket to ride.gpx"),
    "bk_616": lambda: case_bikekingdom("bk_tour_616_rot", "t2811055_616 biketicket to ride red.gpx"),
    "bk_b2r_schwarz": lambda: case_bikekingdom("bk_tour_b2r_schwarz", "t3508125_biketicket 2 ride black.gpx"),
    "bk_b2r_e_rot": lambda: case_bikekingdom("bk_tour_b2r_e_rot", "t37756137_e-biketicket 2 ride red.gpx"),
    "pds": case_portesdusoleil,
}

#: Per-case scores this matcher is known to reach, as [id+order, direction, total]. Written by
#: `--update-baseline`, compared on every plain run, and the whole reason this file is a TEST rather than a
#: report: without it the harness printed its comparison and exited 0 WHATEVER happened, which is
#: indistinguishable from passing (see tests/README.md's own note on exactly that). A score going up is
#: reported as an improvement, not a failure, so the baseline gets refreshed deliberately.
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpx_map_match_baseline.json")


def _run(names):
    scores, totals = {}, [0, 0, 0]
    for name in names:
        title, gt, resolved = CASES[name]()
        a, b, c = _compare(title, gt, resolved)
        scores[name] = [a, b, c]
        totals[0] += a
        totals[1] += b
        totals[2] += c
    print(f"\n=== TOTAL across {len(names)} case(s): "
          f"id+order {totals[0]}/{totals[2]}, direction {totals[1]}/{totals[2]} ===")
    return scores


if __name__ == "__main__":
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(CASES.keys())
    scores = _run(names)
    if "--update-baseline" in flags:
        old = json.load(open(BASELINE, encoding="utf-8")) if os.path.exists(BASELINE) else {}
        old.update(scores)
        json.dump(old, open(BASELINE, "w", encoding="utf-8"), indent=1, sort_keys=True)
        print("baseline written: " + BASELINE)
        sys.exit(0)
    if not os.path.exists(BASELINE):
        print("NO BASELINE yet -- run once with --update-baseline to record the current scores.")
        sys.exit(2)
    base = json.load(open(BASELINE, encoding="utf-8"))
    worse, better, unknown = [], [], []
    for name in sorted(scores):
        a, b, c = scores[name]
        if name not in base:
            unknown.append(name)
            continue
        ba, bb, bc = base[name]
        if c != bc:
            worse.append("%s: %d ground-truth elements, baseline had %d" % (name, c, bc))
        if a < ba or b < bb:
            worse.append("%s: id+order %d/%d (baseline %d), direction %d/%d (baseline %d)"
                         % (name, a, c, ba, b, c, bb))
        elif a > ba or b > bb:
            better.append("%s: id+order %d (was %d), direction %d (was %d)" % (name, a, ba, b, bb))
    for line in better:
        print("IMPROVED  " + line)
    for line in unknown:
        print("NO BASELINE for case " + line)
    if worse:
        for line in worse:
            print("REGRESSED " + line)
        sys.exit(1)
    print("OK: no case scores below its baseline (%d compared)" % len(scores))
