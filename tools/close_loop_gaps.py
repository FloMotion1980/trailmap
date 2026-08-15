# -*- coding: utf-8 -*-
"""Close real-world segment-boundary gaps in a Trailrunde by routing them against OSM.

    python tools/close_loop_gaps.py --only pw_rodalben_felsentrails --report gaps.json
    python tools/close_loop_gaps.py --only pw_rodalben_felsentrails --gap-threshold-m 30 --write

Why this exists: each Trailrunde segment (`trailSegments[loopId]`) is drawn on the map as its OWN,
independent polyline (see `buildTrailLayer` in index.html) -- there is no line connecting one segment's
last point to the next segment's first point. Normally these coincide closely enough that nobody notices.
But `pfaelzerwald_rederive_loops.py` substitutes a NAMED segment's own stored trail geometry for that
stretch (so the Tour's line matches the trail's line pixel-for-pixel) -- and that geometry does not
necessarily end exactly where the ORIGINAL recording's next point picks up. The result is a real,
occasionally large (measured up to 180m on Rodalben Felsentrails) gap that is invisible on the map: nothing
is drawn between the two points, and a rider following the Tour hits a dead end with no visual cue where to
go next.

This is the user's own preferred fix over a one-off hand patch (2026-08-16): treat it as the structural
problem it is, and close it with an actual routing algorithm rather than eyeballing one gap at a time.
Reuses the exact method already validated for Tourenbuilder gap-filling (see
docs/tourenbuilder-gap-filling equivalent -- the assistant's own memory note of the same name): prefer
reusing geometry the region ALREADY has (an existing connector elsewhere that happens to pass by), and only
call out to OSM when nothing in the region covers the gap.

**Per [[no-silent-auto-corrections]]: this script never silently ships a guess.** It always writes a
`--report` of every gap it touched (beeline vs. routed length, route factor, which method closed it) and
requires `--write` to actually modify the region file -- the default is a dry run so the routes can be
reviewed before anything is committed.
"""
import argparse
import heapq
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfaelzerwald_rederive_loops import add_dist_range, concat_ok, line_len_m
from trailmap_pipeline import ElevationLookup, build_profile, cumulative_km, haversine_m, overpass, write_region

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = os.path.join(ROOT, "Trailmap App", "regions", "pfaelzerwald.json")

#: Highways worth routing over. `trunk` deliberately excluded by default -- a Trailrunde gap should route
#: over the kind of road/path a bike actually takes, and offering trunk invites a routed "fix" a rider
#: could not legally/sanely ride. Add it explicitly per-region if a valley's only through road is tagged
#: that way (see tools/trailmap_pipeline.py's own note on this).
HIGHWAY_WHITELIST = ("track|path|footway|cycleway|bridleway|unclassified|residential|service|tertiary|"
                     "secondary|primary|living_street|pedestrian")

#: A boundary gap under this is treated as normal (the routine "these two recordings didn't line up to the
#: metre" slop every loop has, per pfaelzerwald_rederive_loops.py's own "up to ~25m" note) and left alone.
DEFAULT_GAP_THRESHOLD_M = 30.0

#: How far past the two endpoints to pad the Overpass bbox, so the routing graph has room to find a real
#: detour rather than being boxed in exactly at the gap's own bounding box.
BBOX_PAD_M = 250.0

#: A routed replacement whose length is more than this many times the straight-line gap is flagged in the
#: report as speculative rather than silently accepted -- long detours are sometimes correct (a river/cliff
#: really is in the way) but need a human's eyes per [[no-silent-auto-corrections]].
SUSPICIOUS_ROUTE_FACTOR = 3.0


def pad_bbox(a, b, pad_m):
    lat_pad = pad_m / 111320.0
    lon_pad = pad_m / (111320.0 * max(0.15, abs(math.cos(math.radians((a[0] + b[0]) / 2)))))
    lat_min, lat_max = sorted([a[0], b[0]])
    lon_min, lon_max = sorted([a[1], b[1]])
    return "%.6f,%.6f,%.6f,%.6f" % (lat_min - lat_pad, lon_min - lon_pad, lat_max + lat_pad, lon_max + lon_pad)


def fetch_routing_ways(bbox):
    q = '[out:json][timeout:60];way["highway"~"^(%s)$"](%s);out tags geom;' % (HIGHWAY_WHITELIST, bbox)
    j = overpass(q)
    ways = []
    for e in j.get("elements", []):
        if e.get("type") != "way":
            continue
        g = [(round(p["lat"], 7), round(p["lon"], 7)) for p in e.get("geometry", [])]
        if len(g) >= 2:
            ways.append(g)
    return ways


def build_graph(ways):
    """Node key = rounded (lat, lon) tuple. Edge weight = haversine metres between consecutive way points."""
    graph = {}
    for way in ways:
        for i in range(1, len(way)):
            a, b = way[i - 1], way[i]
            if a == b:
                continue
            d = haversine_m(a, b)
            graph.setdefault(a, []).append((b, d))
            graph.setdefault(b, []).append((a, d))
    return graph


def nearest_node(graph, p, max_m=80.0):
    best, best_d = None, max_m
    for node in graph:
        d = haversine_m(node, p)
        if d < best_d:
            best, best_d = node, d
    return best, best_d


def dijkstra(graph, start, goal):
    dist = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]
    visited = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u == goal:
            break
        for v, w in graph.get(u, []):
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if goal not in dist:
        return None
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return [list(p) for p in path]


def route_via_dijkstra(a, b, ways):
    """Shortest path across the WHOLE fetched network graph, snapping each endpoint independently to its
    own nearest node. This is the general-purpose fallback -- it can find a real route where no single OSM
    way covers the gap -- but snapping each end independently means it can wander onto an unrelated nearby
    path and stitch together a technically-shortest-in-the-graph route that is a real-world detour (measured
    on Rodalben Felsentrails: a 181m gap routed to 633m, factor 3.5 -- the user's own catch, 2026-08-16:
    "Umwege machen gar keinen Sinn"). Kept as one candidate among several in `best_bridge_for_gap`, not the
    only method, specifically because of this failure mode.
    """
    graph = build_graph(ways)
    if not graph:
        return None, "kein Wegenetz im Suchraum"
    na, da = nearest_node(graph, tuple(a))
    nb, db = nearest_node(graph, tuple(b))
    if na is None or nb is None:
        return None, "kein Netzknoten nah genug an einem der beiden Enden"
    path = dijkstra(graph, na, nb)
    if path is None:
        return None, "kein Pfad zwischen den beiden Netzknoten gefunden"
    return [list(a)] + path + [list(b)], None


def walk_along_matched_way(a, b, ways, match_pts):
    """Identify the SINGLE OSM way that `match_pts` (a few points from one side of the gap, e.g. the
    connector's own first points) already follows, then walk THAT way's own point sequence to find where it
    comes closest to the other endpoint. This is the fix the user pointed out directly (2026-08-16, from
    the actual map): "schau dir an auf welchen Weg die graue gestrichelte Linie entlang läuft... gehst du
    zurück bis du auf die grüne Linie stößt" -- the connector already follows a real, ridden road; that
    SAME road usually passes close to the other side's endpoint too, at a point closer than the two
    segments' own stored endpoints are to each other. Verified on Rodalben Felsentrails' worst gap: the
    matched way has a point 34.9m from the trail's own end, vs. the connector's stored start being 180.7m
    away -- walking back along the real road cuts the gap by more than half before any routing is needed.

    Returns (full_path_incl_a_and_b, route_m) or (None, reason).
    """
    if not ways:
        return None, "kein Wegenetz im Suchraum"
    best = None
    for w in ways:
        score = sum(min(haversine_m(p, tuple(q)) for q in w) for p in match_pts)
        if best is None or score < best[0]:
            best = (score, w)
    way = best[1]
    ia, da = min(((k, haversine_m(pt, a)) for k, pt in enumerate(way)), key=lambda x: x[1])
    ib, db = min(((k, haversine_m(pt, b)) for k, pt in enumerate(way)), key=lambda x: x[1])
    if ia <= ib:
        mid = [list(p) for p in way[ia:ib + 1]]
    else:
        mid = [list(p) for p in reversed(way[ib:ia + 1])]
    path = [list(a)] + mid + [list(b)]
    # de-dupe consecutive near-identical points (both ends can coincide with the way's own point exactly)
    dedup = [path[0]]
    for p in path[1:]:
        if haversine_m(dedup[-1], p) > 0.5:
            dedup.append(p)
    return dedup, None


def best_bridge_for_gap(region_data, loop_id, seg_i_coords, seg_j_coords, a, b, verbose=False):
    """Try every candidate method for one boundary gap and keep whichever produces the SHORTEST real route
    -- the user's own instruction (2026-08-16): "probier verschiedene Ansätze, die beste Füllmethode
    gewinnt", after `route_via_dijkstra` alone produced a nonsensical 7.6x detour on one gap while
    `walk_along_matched_way` found a nearly-direct 1.0x path on the same one. A single fixed priority order
    (as this script used to have) can't tell a good detour from a bad one; comparing actual lengths can.

    Returns (method_name, full_path_incl_endpoints, route_m, extra) for the winner, or (None, None, None,
    reason) if nothing worked at all.
    """
    candidates = []  # (route_m, method, path, extra)

    sub, via_loop = find_reusable_connector(region_data, loop_id, a, b)
    if sub is not None:
        candidates.append((line_len_m(sub), "reused_connector", sub, {"source_loop": via_loop}))

    bbox = pad_bbox(a, b, BBOX_PAD_M)
    ways = fetch_routing_ways(bbox)
    if verbose:
        print("     Overpass: %d Wege im Suchraum" % len(ways))

    for label, match_pts in (("matched_way_b", seg_j_coords[:3]), ("matched_way_a", seg_i_coords[-3:])):
        path, err = walk_along_matched_way(a, b, ways, match_pts)
        if path is not None:
            candidates.append((line_len_m(path), label, path, {}))

    path, err = route_via_dijkstra(a, b, ways)
    if path is not None:
        candidates.append((line_len_m(path), "osm_route", path, {}))

    if not candidates:
        return None, None, None, (err or "kein Wegenetz im Suchraum")

    candidates.sort(key=lambda c: c[0])
    route_m, method, path, extra = candidates[0]
    if verbose:
        print("     Kandidaten: %s (gewählt: %s, %.0fm)"
              % (", ".join("%s=%.0fm" % (c[1], c[0]) for c in candidates), method, route_m))
    return method, path, route_m, extra


def find_reusable_connector(region_data, loop_id, a, b, max_off_m=60.0):
    """An existing PURE connector stretch (any loop) whose own line passes within max_off_m of both a and b.

    Mirrors the Tourenbuilder gap-filling method: search both directions (a connector can be walked
    reversed). Returns the sub-slice [a-ish .. b-ish] oriented a->b, or None.
    """
    best = None
    for t in region_data["lineTrails"]:
        if not t.get("loop"):
            continue
        for seg in region_data["trailSegments"].get(t["id"], []):
            if seg.get("trailId") or seg.get("liftId"):
                continue
            coords = seg["coords"]
            if len(coords) < 2:
                continue
            ia, offa = min(((i, haversine_m(p, a)) for i, p in enumerate(coords)), key=lambda x: x[1])
            ib, offb = min(((i, haversine_m(p, b)) for i, p in enumerate(coords)), key=lambda x: x[1])
            if offa > max_off_m or offb > max_off_m or ia == ib:
                continue
            sub = coords[ia:ib + 1] if ia < ib else list(reversed(coords[ib:ia + 1]))
            score = offa + offb
            if best is None or score < best[0]:
                best = (score, sub, t["id"])
    if best is None:
        return None, None
    return best[1], best[2]


def boundary_gaps(segs, threshold_m):
    n = len(segs)
    gaps = []
    for i in range(n):
        a = segs[i]["coords"][-1]
        b = segs[(i + 1) % n]["coords"][0]
        d = haversine_m(a, b)
        if d > threshold_m:
            gaps.append((i, (i + 1) % n, d))
    return gaps


def close_gap(segs, i, j, bridge_points):
    """Insert `bridge_points` (intermediate points only, NOT including segs[i]'s last or segs[j]'s first
    point -- those already exist) between segment i and segment j. Extends an adjacent connector in place
    when one exists, so a real connector just gets longer instead of gaining a redundant neighbour; only
    inserts a brand-new connector segment when both neighbours are named stretches.
    """
    if not bridge_points:
        return segs
    if j == 0:  # wrap-around: the gap is between the LAST segment and the FIRST -- insert at the very end
        if segs[i].get("trailId") is None and not segs[i].get("liftId"):
            segs[i]["coords"] = segs[i]["coords"] + bridge_points
        elif segs[j].get("trailId") is None and not segs[j].get("liftId"):
            segs[j]["coords"] = bridge_points + segs[j]["coords"]
        else:
            segs.append({"coords": bridge_points, "trailId": None})
        return segs
    if segs[j].get("trailId") is None and not segs[j].get("liftId"):
        segs[j]["coords"] = bridge_points + segs[j]["coords"]
    elif segs[i].get("trailId") is None and not segs[i].get("liftId"):
        segs[i]["coords"] = segs[i]["coords"] + bridge_points
    else:
        segs.insert(j, {"coords": bridge_points, "trailId": None})
    return segs


def gap_cache_key(loop_id, a, b):
    """Stable key for a boundary gap, independent of segment INDEX (which shifts as gaps get closed) --
    keyed on the two endpoints themselves, rounded to ~1m, so a resumed/re-run invocation can skip the
    network entirely for a gap whose geometry hasn't changed. This is what makes an interrupted multi-hour
    run (each gap costs a real Overpass round-trip) resumable in seconds instead of from scratch, and lets
    the SAME cache serve a later "show me the actual route" request without re-fetching.
    """
    return "%s|%.6f,%.6f|%.6f,%.6f" % (loop_id, a[0], a[1], b[0], b[1])


def process_loop(region_data, loop_id, threshold_m, verbose=False, cache=None, cache_path=None):
    cache = cache if cache is not None else {}

    def flush_cache():
        if cache_path:
            json.dump(cache, open(cache_path, "w", encoding="utf-8"))
    segs = region_data["trailSegments"][loop_id]
    old_line = [p for s in segs for p in s["coords"]]
    if not concat_ok(old_line, segs):
        return None, [{"loop": loop_id, "ok": False, "reason": "Segmente sind keine exakte Verkettung -- übersprungen"}]

    gaps = boundary_gaps(segs, threshold_m)
    if not gaps:
        return None, []

    report = []
    # Process from the END backwards so earlier indices stay valid as segments get inserted.
    for i, j, dist_m in sorted(gaps, key=lambda g: -g[0]):
        a, b = segs[i]["coords"][-1], segs[j]["coords"][0]
        row = {"loop": loop_id, "seg_i": i, "seg_j": j, "beeline_m": round(dist_m, 1)}
        ckey = gap_cache_key(loop_id, a, b)
        cached = cache.get(ckey)
        if cached is not None:
            if verbose:
                print("  -> aus Cache: %s" % ckey)
            if cached.get("method") == "failed":
                row.update(method="failed", reason=cached["reason"])
                report.append(row)
                continue
            bridge = cached["bridge"]
            row.update(method=cached["method"], route_m=cached["route_m"])
            if cached.get("source_loop"):
                row["source_loop"] = cached["source_loop"]
            segs = close_gap(segs, i, j, bridge)
            factor = (row["route_m"] / dist_m) if dist_m > 0 else 0
            row["route_factor"] = round(factor, 2)
            row["suspicious"] = factor > SUSPICIOUS_ROUTE_FACTOR
            report.append(row)
            continue

        if verbose:
            print("  -> Lücke %.0fm: probiere mehrere Ansätze, beste Route gewinnt" % dist_m)
        method, path, route_m, extra_or_reason = best_bridge_for_gap(
            region_data, loop_id, segs[i]["coords"], segs[j]["coords"], a, b, verbose=verbose)
        if method is None:
            row.update(method="failed", reason=extra_or_reason)
            cache[ckey] = {"method": "failed", "reason": extra_or_reason}
            flush_cache()
            report.append(row)
            continue
        bridge = path[1:-1]  # a and b themselves already exist as segs[i]'s/segs[j]'s own endpoints
        row.update(method=method, route_m=round(route_m, 1))
        row.update(extra_or_reason)
        cache[ckey] = {"method": method, "route_m": row["route_m"], "bridge": bridge}
        cache[ckey].update(extra_or_reason)
        flush_cache()
        factor = (row["route_m"] / dist_m) if dist_m > 0 else 0
        row["route_factor"] = round(factor, 2)
        row["suspicious"] = factor > SUSPICIOUS_ROUTE_FACTOR
        segs = close_gap(segs, i, j, bridge)
        report.append(row)

    new_line = [p for s in segs for p in s["coords"]]
    if not concat_ok(new_line, segs):
        return None, report + [{"loop": loop_id, "ok": False, "reason": "Verkettung nach dem Einfügen verletzt"}]
    return (segs, new_line), report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=REGION)
    ap.add_argument("--only", action="append", required=True, help="loop id(s) to process")
    ap.add_argument("--gap-threshold-m", type=float, default=DEFAULT_GAP_THRESHOLD_M)
    ap.add_argument("--report", default="close_loop_gaps_report.json")
    ap.add_argument("--cache", default="close_loop_gaps_cache.json",
                     help="routed/reused bridges are cached here, keyed by endpoint -- a re-run (after a "
                          "kill, or just to re-render the report) costs no network calls for an unchanged gap")
    ap.add_argument("--write", action="store_true", help="without this, the region file is left untouched")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    d = json.load(open(args.region, encoding="utf-8"))
    ele = ElevationLookup(os.path.join(ROOT, "Material", "elevation_cache.json"))
    cache = {}
    if os.path.exists(args.cache):
        try:
            cache = json.load(open(args.cache, encoding="utf-8"))
        except Exception:
            cache = {}

    all_report = []
    touched = {}
    for loop_id in args.only:
        if loop_id not in d.get("trailSegments", {}):
            all_report.append({"loop": loop_id, "ok": False, "reason": "keine trailSegments für diese ID"})
            continue
        t0 = time.time()
        result, report = process_loop(d, loop_id, args.gap_threshold_m, verbose=args.verbose,
                                       cache=cache, cache_path=args.cache)
        for row in report:
            row.setdefault("ok", True)
        all_report.extend(report)
        if result is None:
            print("%-32s: keine Lücke über %.0fm, oder nicht verarbeitbar (%.1fs)"
                  % (loop_id, args.gap_threshold_m, time.time() - t0))
            continue
        segs, new_line = result
        d["trailSegments"][loop_id] = add_dist_range(new_line, segs)
        d["trailGeo"][loop_id] = new_line
        elevs = ele([[p[0], p[1]] for p in new_line])
        prof, gain, loss = build_profile(new_line, elevs)
        d["elevationProfiles"][loop_id] = prof
        touched[loop_id] = True
        print("%-32s: %d Lücke(n) über %.0fm geschlossen (%.1fs)"
              % (loop_id, len([r for r in report if r.get("method") not in (None, "failed")]),
                 args.gap_threshold_m, time.time() - t0))

    json.dump(all_report, open(args.report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nBericht: %s" % args.report)
    for row in all_report:
        if row.get("suspicious"):
            print("  !! VERDÄCHTIG: %s seg%s->seg%s  Luftlinie %.0fm, Route %.0fm (Faktor %.1f) via %s"
                  % (row["loop"], row["seg_i"], row["seg_j"], row["beeline_m"], row["route_m"],
                     row["route_factor"], row["method"]))
        elif row.get("method") == "failed":
            print("  !! NICHT GESCHLOSSEN: %s seg%s->seg%s  Luftlinie %.0fm -- %s"
                  % (row["loop"], row["seg_i"], row["seg_j"], row["beeline_m"], row["reason"]))

    if args.write and touched:
        write_region(args.region, d["lineTrails"], d["trailGeo"], d["elevationProfiles"],
                     places=d.get("places"), lifts=d.get("lifts"), trail_segments=d["trailSegments"])
        print("\ngeschrieben: %s" % args.region)
    elif touched:
        print("\n(Dry Run -- nichts geschrieben. --write zum Übernehmen.)")


if __name__ == "__main__":
    main()
