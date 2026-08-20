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

#: How much worse (in "equivalent metres of match error") a way type is than a real trail, when two ways both
#: plausibly match the same stretch. The user's own rule (2026-08-16): "bei mehreren Kandidaten sollte ein
#: Trail gegen einen Forstweg gewinnen". Deliberately MODEST numbers: a Trailrunde's connector stretches
#: genuinely DO run along forest roads a lot of the time, so this must only break a near-tie, never drag the
#: match onto a singletrack that is visibly further away than the track the line actually follows. Typical
#: real match error is under 5m, so +6m is enough to decide a tie and not enough to override a clear winner.
WAY_TYPE_PENALTY_M = {
    "path": 0.0, "footway": 0.0, "bridleway": 0.0, "cycleway": 0.0,   # real trails
    "track": 6.0,                                                      # forest/field road
    "service": 10.0, "unclassified": 10.0, "residential": 10.0,
    "living_street": 10.0, "pedestrian": 10.0,
    "tertiary": 20.0, "secondary": 20.0, "primary": 20.0,              # actual roads, last resort
}
DEFAULT_TYPE_PENALTY_M = 12.0

#: Mean distance (metres) from a side's own last/first points to the way it was matched against, above which
#: we conclude the stretch does NOT actually run along that way. The user pointed out (2026-08-16) that some
#: tours/segments simply are not on OSM ways at all -- "in so einem Fall wird uns die OSM Strategie keinen
#: Erfolg bringen" -- so the way-following methods must be able to say "not applicable here" instead of
#: snapping the bridge onto whatever happened to be nearest and calling it a route.
MATCH_MAX_MEAN_M = 15.0

#: How close two matched ways have to come to each other to count as actually joining up, for the
#: both-sides-mapped candidate (see walk_both_ways_junction).
JUNCTION_MAX_M = 60.0

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

# ---------------------------------------------------------------------------------------------------
# QUALITY METRIC (2026-08-16, third round)
#
# The user's own diagnosis after reviewing the second attempt on the map: "wir brauchen eine sinnvolle
# Metrik, um die Varianten zu bewerten. Da scheint es aktuell noch keine zu geben." Correct -- the first two
# attempts ranked candidates by ROUTE LENGTH, which is not a statement about quality at all. Both failures
# they found were SHORT: a bridge striking off through the forest, and one crossing a stream where OSM has
# no way, plus a zigzag along a road instead of simply following it. Every one of those wins a
# shortest-route contest.
#
# So candidates are scored in "penalty metres" instead, and the component that actually catches those cases
# is OFF_WAY: how much of the proposed bridge runs where no rideable OSM way exists. That is the direct
# measurement of "läuft ins Leere, einfach durch den Wald".
COST_W_OFF_WAY = 3.0      # bridge metres further than OFF_WAY_TOL_M from any rideable way
# Trimming is the REPAIR, not damage -- it is what the user asked for from the start ("und grünen Trail dann
# kürzen"), and the tail being cut is usually the artefact that created the gap. At 2.0 this weight buried
# the correct answer: cutting 100m of stale trail scored 200 penalty metres, more than a visibly wrong
# 156-point detour, so the metric picked the detour. Kept small but non-zero so that, between two otherwise
# equal candidates, the one that preserves more real geometry still wins -- and capped by MAX_TRIM_M below.
COST_W_TRIMMED = 0.3      # metres of existing trail/connector geometry thrown away
MAX_TRIM_M = 250.0        # beyond this a candidate is rejected outright, not merely penalised
COST_W_DETOUR = 1.0       # route length minus beeline
COST_W_RESIDUAL = 5.0     # metres still left open at the join after the bridge
# 5m, nicht 20m. Bei 20m sahen am Hilschberghaus VIER Kandidaten identisch gut aus (alle weglos 0m),
# obwohl drei davon 20m querab durchs Gelaende sprangen -- die Auswahl war damit zufaellig, und der Nutzer
# hat den Unterschied auf der Karte sofort gesehen ("akzeptabel aber nicht perfekt ... einfach der Strasse
# folgen"). Bei 5m trennt die Kennzahl sauber: nur die Loesung, die durchgehend auf der Strasse bleibt,
# behaelt weglos 0m. Gemessen an genau diesem Fall.
OFF_WAY_TOL_M = 5.0       # further than this from any way = "not on a way"
SAMPLE_STEP_M = 10.0      # how finely a bridge is sampled for the off-way measurement


def sample_polyline(pts, step_m=SAMPLE_STEP_M):
    """Points every ~step_m along the polyline, so a long straight leg through the woods is measured by its
    LENGTH and not by its two vertices -- a two-point line across 200m of forest would otherwise score the
    same as a two-point line along 200m of road."""
    if len(pts) < 2:
        return [tuple(p) for p in pts]
    out = [tuple(pts[0])]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = haversine_m(a, b)
        n = max(1, int(d // step_m))
        for k in range(1, n + 1):
            t = k / float(n)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


class WayIndex(object):
    """Grid index over every way EDGE, so "how far is this point from the nearest way" is a handful of cell
    lookups instead of a scan over every edge of every way. Without it the off-way measurement is
    O(samples x edges) and a single gap took minutes with ~300 ways in the bbox.
    """
    CELL_DEG = 0.0025  # ~275m lat; a few cells cover any tolerance we use

    def __init__(self, ways):
        self.cells = {}
        self.ways = ways
        for w in ways:
            g = w["geom"]
            for i in range(len(g) - 1):
                a, b = g[i], g[i + 1]
                for key in self._keys_for_edge(a, b):
                    self.cells.setdefault(key, []).append((a, b, w))

    def _key(self, lat, lon):
        return (int(math.floor(lat / self.CELL_DEG)), int(math.floor(lon / self.CELL_DEG)))

    def _keys_for_edge(self, a, b):
        k0, k1 = self._key(*a), self._key(*b)
        out = set()
        for y in range(min(k0[0], k1[0]), max(k0[0], k1[0]) + 1):
            for x in range(min(k0[1], k1[1]), max(k0[1], k1[1]) + 1):
                out.add((y, x))
        return out

    def nearest(self, p, max_cells=1):
        ky, kx = self._key(*p)
        best = 1e18
        for y in range(ky - max_cells, ky + max_cells + 1):
            for x in range(kx - max_cells, kx + max_cells + 1):
                for a, b, _w in self.cells.get((y, x), ()):
                    d = _project_on_edge(p, a, b)[2]
                    if d < best:
                        best = d
        return best


def dist_to_ways(p, ways_or_index):
    """Metres from p to the nearest rideable way's polyline."""
    if isinstance(ways_or_index, WayIndex):
        return ways_or_index.nearest(p)
    return WayIndex(ways_or_index).nearest(p)


def off_way_metres(bridge, ways_or_index, tol_m=OFF_WAY_TOL_M):
    """How many metres of `bridge` run further than tol_m from every rideable way."""
    idx = ways_or_index if isinstance(ways_or_index, WayIndex) else WayIndex(ways_or_index)
    if len(bridge) < 2 or not idx.cells:
        return line_len_m(bridge) if len(bridge) >= 2 else 0.0
    s = sample_polyline(bridge)
    off = 0.0
    for i in range(len(s) - 1):
        mid = ((s[i][0] + s[i + 1][0]) / 2.0, (s[i][1] + s[i + 1][1]) / 2.0)
        if idx.nearest(mid) > tol_m:
            off += haversine_m(s[i], s[i + 1])
    return off


def bridge_cost(bridge, ways, beeline_m, trimmed_m=0.0, residual_m=0.0):
    """Penalty-metre score for one candidate bridge; lower is better. Returns the breakdown too, so the
    report can show WHY a candidate won or lost rather than just a number."""
    route_m = line_len_m(bridge) if len(bridge) >= 2 else 0.0
    off = off_way_metres(bridge, ways)
    detour = max(0.0, route_m - beeline_m)
    parts = {
        "route_m": round(route_m, 1),
        "off_way_m": round(off, 1),
        "detour_m": round(detour, 1),
        "trimmed_m": round(trimmed_m, 1),
        "residual_m": round(residual_m, 1),
    }
    parts["cost"] = round(COST_W_OFF_WAY * off + COST_W_TRIMMED * trimmed_m +
                          COST_W_DETOUR * detour + COST_W_RESIDUAL * residual_m, 1)
    return parts


def pad_bbox(a, b, pad_m):
    lat_pad = pad_m / 111320.0
    lon_pad = pad_m / (111320.0 * max(0.15, abs(math.cos(math.radians((a[0] + b[0]) / 2)))))
    lat_min, lat_max = sorted([a[0], b[0]])
    lon_min, lon_max = sorted([a[1], b[1]])
    return "%.6f,%.6f,%.6f,%.6f" % (lat_min - lat_pad, lon_min - lon_pad, lat_max + lat_pad, lon_max + lon_pad)


def _bbox_nums(bbox):
    return [float(x) for x in bbox.split(",")]


def _overlaps(a, b):
    """Two bboxes as (latMin, lonMin, latMax, lonMax) -- Overpass' own way-selection semantics."""
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


#: One prefetched superset of routable ways, as (bbox_nums, ways). Filled by prefetch_routing_ways().
_WAY_CACHE = []


def prefetch_routing_ways(bboxes, verbose=False):
    """Fetch the routing ways for ALL of a loop's gaps in one Overpass query.

    Why: `close_gap()` used to call `fetch_routing_ways()` itself, i.e. **one Overpass query per gap**.
    With four Schwarzwald Tours and ~32 gaps between them that is 32 queries, each waiting in Overpass'
    own queue, and the run did not finish in ten minutes -- the user spotted the cause from the runtime
    alone (2026-08-20: "Machen wir wieder pro Lücke eine OSM Abfrage anstatt sie am Anfang einmal zu
    machen?"). One query over the union of the gap bboxes is a strict superset of every per-gap bbox, so
    each gap still searches exactly the ways it did before; `fetch_routing_ways()` now filters the cached
    set by the same bbox-intersection rule Overpass applies, instead of asking again.

    **`nearby_trail_connector.prefetch_gaps()` already did this, and does it better**: one query carrying
    one small box PER GAP rather than a single box around all of them (its own measurement: 46 km2 against
    534 km2 for the Trans Pfaelzerwald), plus a disk cache. It was written for the same reason and this
    one was written without noticing it. If either is touched again, unify them -- and note the import
    direction, since that module already imports this one.
    """
    if not bboxes:
        return
    nums = [_bbox_nums(b) for b in bboxes]
    union = (min(n[0] for n in nums), min(n[1] for n in nums),
             max(n[2] for n in nums), max(n[3] for n in nums))
    bbox = "%.6f,%.6f,%.6f,%.6f" % union
    ways = _fetch_routing_ways_overpass(bbox)
    _WAY_CACHE.append((union, ways))
    if verbose:
        print("  Overpass: eine Abfrage über %s -> %d Wege für %d Lücken"
              % (bbox, len(ways), len(bboxes)))


def _fetch_routing_ways_overpass(bbox):
    q = '[out:json][timeout:180];way["highway"~"^(%s)$"](%s);out tags geom;' % (HIGHWAY_WHITELIST, bbox)
    j = overpass(q)
    ways = []
    for e in j.get("elements", []):
        if e.get("type") != "way":
            continue
        g = [(round(p["lat"], 7), round(p["lon"], 7)) for p in e.get("geometry", [])]
        if len(g) >= 2:
            ways.append({"geom": g, "tags": e.get("tags", {}) or {}, "id": e.get("id")})
    return ways


def fetch_routing_ways(bbox):
    """Every routable way in the bbox, WITH its tags -- the tags are what the rideability check and the
    way-type preference below run on, so dropping them (as the first version of this script did) makes both
    impossible. Returns [{"geom": [(lat,lon),...], "tags": {...}, "id": osm_id}, ...].

    Served from the prefetched superset when one covers this bbox (see prefetch_routing_ways); only a bbox
    nothing prefetched still goes to Overpass.
    """
    want = _bbox_nums(bbox)
    for union, ways in _WAY_CACHE:
        if (want[0] >= union[0] and want[1] >= union[1]
                and want[2] <= union[2] and want[3] <= union[3]):
            out = []
            for w in ways:
                la = [p[0] for p in w["geom"]]
                lo = [p[1] for p in w["geom"]]
                if _overlaps((min(la), min(lo), max(la), max(lo)), want):
                    out.append(w)
            return out
    return _fetch_routing_ways_overpass(bbox)


#: Values that, on their own key, mean "a bicycle may not ride here". `motor_vehicle` is deliberately absent:
#: it restricts only motorised traffic and says nothing about a bike. See docs/trailrunden-lueckenschliessen.md.
_BLOCKING = {
    "bicycle": ("no", "private", "dismount"),
    "access": ("private", "no", "permit", "customers"),
    "vehicle": ("private", "no", "forestry", "agricultural", "delivery"),
}
_BICYCLE_ALLOWED = ("yes", "designated", "permissive", "official")


def way_blocked(tags):
    """(blocked_bool, reason_or_None) for one way's tags, from a BICYCLE's point of view.

    Exists because the first version of this script judged a candidate purely on distance, and the user
    caught the consequence live on the map (2026-08-16): the winning bridge at Rodalben's start followed a
    `highway=track` tagged `vehicle=forestry` -- geometrically a perfect match (route factor 1.1, nothing
    suspicious in the report at all), but "auf OSM ist klar, dass man da nicht hochfahren kann".

    An explicit bicycle permission wins over every general restriction: a forestry track carrying
    `bicycle=yes` really is open to us. Otherwise, a restriction on the general `access` or on `vehicle`
    applies -- in OSM's own access hierarchy a bicycle IS a `vehicle`, which is exactly why `vehicle=forestry`
    has to count here and not be waved through as "that's only about lorries".
    """
    if tags.get("bicycle") in _BICYCLE_ALLOWED:
        return False, None
    for key, bad_values in _BLOCKING.items():
        v = tags.get(key)
        if v in bad_values:
            return True, "%s=%s" % (key, v)
    return False, None


def way_type_penalty_m(tags):
    """Surcharge in 'equivalent metres of match error' for this way's type -- the user's own rule that a
    trail should beat a forest road when both plausibly match. Modest on purpose; see the constant's comment.
    """
    return WAY_TYPE_PENALTY_M.get(tags.get("highway"), DEFAULT_TYPE_PENALTY_M)


def rideable_ways(ways):
    """(kept, rejected) split by way_blocked. `rejected` carries the reason so the report can show WHY a gap
    stayed open or a longer route won, instead of the restriction being invisible."""
    kept, rejected = [], []
    for w in ways:
        blocked, reason = way_blocked(w["tags"])
        if blocked:
            rejected.append({"id": w.get("id"), "highway": w["tags"].get("highway"), "reason": reason})
        else:
            kept.append(w)
    return kept, rejected


def best_matching_way(ways, match_pts):
    """Which way does this side of the gap actually run along, and how well?

    Score = mean distance of `match_pts` to the way + the way's own type penalty. Returns
    (way, mean_dist_m, score) for the best, or (None, None, None) when `ways` is empty. The caller decides
    whether `mean_dist_m` is good enough (MATCH_MAX_MEAN_M) -- this function does not reject on its own, so
    the caller can report the actual number rather than just "no match".
    """
    if not ways:
        return None, None, None
    best = None
    for w in ways:
        geom = w["geom"]
        mean_d = sum(min(haversine_m(p, q) for q in geom) for p in match_pts) / float(len(match_pts))
        score = mean_d + way_type_penalty_m(w["tags"])
        if best is None or score < best[2]:
            best = (w, mean_d, score)
    return best


def build_graph(ways):
    """Node key = rounded (lat, lon) tuple. Edge weight = haversine metres between consecutive way points.
    `ways` must already be access-filtered (see rideable_ways) -- a blocked way must not even be an edge, or
    Dijkstra will happily route straight through it."""
    graph = {}
    for w in ways:
        way = w["geom"]
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


def _dedup(path):
    """Drop consecutive near-identical points -- an endpoint often coincides with a way's own vertex."""
    out = [path[0]]
    for p in path[1:]:
        if haversine_m(out[-1], p) > 0.5:
            out.append(p)
    return out


def _slice_towards(geom, from_idx, to_idx):
    """The way's own points from from_idx to to_idx, oriented in that direction."""
    if from_idx <= to_idx:
        return [list(p) for p in geom[from_idx:to_idx + 1]]
    return [list(p) for p in reversed(geom[to_idx:from_idx + 1])]


def _project_on_edge(p, s, e):
    """Perpendicular projection of p onto the segment s-e, in a local metre frame. (t, point, dist_m)."""
    lat0 = math.radians((s[0] + e[0]) / 2.0)
    mx = 111320.0 * max(0.15, math.cos(lat0))
    my = 110540.0
    sx, sy = s[1] * mx, s[0] * my
    ex, ey = e[1] * mx, e[0] * my
    px, py = p[1] * mx, p[0] * my
    dx, dy = ex - sx, ey - sy
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / l2))
    q = ((sy + t * dy) / my, (sx + t * dx) / mx)
    return t, q, haversine_m(p, q)


def project_onto_way(geom, p):
    """Closest point on the way's POLYLINE (not merely on one of its vertices): (edge_idx, t, point, dist_m).

    Snapping to the nearest vertex instead -- what the first version did -- silently fails whenever the way's
    vertices are sparse: an 84m gap whose two ends both happen to be nearest the SAME vertex produced a
    "route" with no intermediate geometry at all, i.e. a straight line of exactly the beeline length, which
    the report then proudly recorded as route_factor 1.00 while the gap stayed wide open on the map. That was
    16 of 29 gaps on Rodalben Felsentrails. Projecting onto the edges gives both a correct position along the
    way and real geometry between the two.
    """
    best = None
    for i in range(len(geom) - 1):
        t, q, d = _project_on_edge(p, geom[i], geom[i + 1])
        if best is None or d < best[3]:
            best = (i, t, q, d)
    return best


def slice_way_between(geom, pa, pb):
    """The way's own course between the projections of pa and pb, oriented pa->pb, including both projected
    endpoints. Returns (points, dist_a_m, dist_b_m) or (None, None, None) for a degenerate way."""
    if len(geom) < 2:
        return None, None, None
    ia, ta, qa, da = project_onto_way(geom, pa)
    ib, tb, qb, db = project_onto_way(geom, pb)
    if ia + ta <= ib + tb:
        mid = [list(q) for q in geom[ia + 1:ib + 1]]
    else:
        mid = [list(q) for q in reversed(geom[ib + 1:ia + 1])]
    return [list(qa)] + mid + [list(qb)], da, db


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

    Now refuses rather than guessing when the side does not actually run along its best way
    (MATCH_MAX_MEAN_M): some tours simply are not on OSM at all, and forcing this method there produced a
    bridge snapped onto whatever happened to be nearest (user, 2026-08-16).

    Returns (full_path_incl_a_and_b, info_dict) or (None, reason).
    """
    if not ways:
        return None, "kein Wegenetz im Suchraum"
    w, mean_d, _score = best_matching_way(ways, match_pts)
    if w is None:
        return None, "kein Weg im Suchraum"
    if mean_d > MATCH_MAX_MEAN_M:
        return None, "Abschnitt liegt nicht auf einem OSM-Weg (Ø %.0fm daneben)" % mean_d
    mid, da, db = slice_way_between(w["geom"], a, b)
    if mid is None:
        return None, "Weg hat keine nutzbare Geometrie"
    path = _dedup([list(a)] + mid + [list(b)])
    return path, {"match_m": round(mean_d, 1), "way_type": w["tags"].get("highway"),
                  "snap_m": [round(da, 1), round(db, 1)]}


def walk_both_ways_junction(a, b, ways, pts_a, pts_b):
    """Map BOTH sides of the gap onto their own OSM way and join them where those two ways actually meet.

    The user's own proposal (2026-08-16), replacing the older "match ONE side, then walk stubbornly to the
    other side's raw endpoint": that older shape has no notion of where the two roads genuinely connect, so
    it produces a route that leaves one real way and jumps across open ground to a stored coordinate. Mapping
    both sides and finding where their ways come closest is the geometrically founded junction -- it is the
    point a rider would actually turn at.

    Only applicable when both sides really do lie on a way (MATCH_MAX_MEAN_M each) and those ways come within
    JUNCTION_MAX_M of each other. Same way on both sides is left to walk_along_matched_way, which handles that
    case directly with no junction to find.

    Returns (full_path_incl_a_and_b, info_dict) or (None, reason).
    """
    if not ways:
        return None, "kein Wegenetz im Suchraum"
    wa, mean_a, _ = best_matching_way(ways, pts_a)
    wb, mean_b, _ = best_matching_way(ways, pts_b)
    if wa is None or wb is None:
        return None, "kein Weg im Suchraum"
    if mean_a > MATCH_MAX_MEAN_M or mean_b > MATCH_MAX_MEAN_M:
        return None, ("eine Seite liegt nicht auf einem OSM-Weg (Ø %.0fm / %.0fm)" % (mean_a, mean_b))
    if wa is wb:
        return None, "beide Seiten auf demselben Weg -- matched_way deckt das ab"

    ga, gb = wa["geom"], wb["geom"]
    best = None  # (dist, idx_a, idx_b)
    for i, p in enumerate(ga):
        for j, q in enumerate(gb):
            d = haversine_m(p, q)
            if best is None or d < best[0]:
                best = (d, i, j)
    if best[0] > JUNCTION_MAX_M:
        return None, "die beiden Wege treffen sich nicht (%.0fm auseinander)" % best[0]
    _jd, ja, jb = best
    # a -> along way A to the junction vertex, then way B's junction vertex -> b. Both halves are cut by
    # projection (see slice_way_between) so the endpoints land ON the way rather than on its nearest vertex.
    lead, da, _ = slice_way_between(ga, a, ga[ja])
    tail, _, db = slice_way_between(gb, gb[jb], b)
    if lead is None or tail is None:
        return None, "Weg hat keine nutzbare Geometrie"
    path = _dedup([list(a)] + lead + tail + [list(b)])
    return path, {"match_m": round(max(mean_a, mean_b), 1),
                  "way_type": "%s+%s" % (wa["tags"].get("highway"), wb["tags"].get("highway")),
                  "junction_m": round(best[0], 1), "snap_m": [round(da, 1), round(db, 1)]}


def best_bridge_for_gap(region_data, loop_id, seg_i_coords, seg_j_coords, a, b, verbose=False):
    """Close one boundary gap, trying the methods in PRIORITY TIERS rather than as equal competitors.

    Reworked 2026-08-16 (second feedback round; see docs/trailrunden-lueckenschliessen.md for the full
    reasoning). The first version put all four methods in one pot and took whichever produced the shortest
    route -- which is not the same question as "which follows real, connected, rideable ways". The user's
    instruction: map both ends onto genuine OSM ways FIRST, and use the other methods only when that does
    not work at all -- not because they happen to be shorter.

      Tier 1  both_ways_junction / matched_way_*  -- the sides genuinely run along OSM ways
      Tier 2  reused_connector                    -- geometry this region already has
      Tier 3  osm_route (Dijkstra)                -- last resort, known to invent detours

    Within a tier the shortest route wins; a lower tier is only consulted when the higher one produced
    nothing. Ways a bicycle may not use are removed before any of this (way_blocked), and the way-following
    methods refuse outright when the stretch does not actually lie on a way -- some tours simply are not on
    OSM, and a snapped-to-nearest bridge there is worse than an honest gap.

    Returns (method_name, full_path_incl_endpoints, route_m, extra) for the winner, or (None, None, None,
    reason) if nothing worked at all.
    """
    bbox = pad_bbox(a, b, BBOX_PAD_M)
    all_ways = fetch_routing_ways(bbox)
    ways, rejected = rideable_ways(all_ways)
    if verbose:
        print("     Overpass: %d Wege im Suchraum, %d wegen Zugangsbeschränkung verworfen"
              % (len(all_ways), len(rejected)))
        for r in rejected:
            print("        verworfen: highway=%s (%s)" % (r["highway"], r["reason"]))
    shared = {"rejected_ways": rejected} if rejected else {}

    reasons = []

    def tier(label, entries):
        """entries: list of (method, path_or_None, info_or_reason). Returns winner tuple or None."""
        found = []
        for method, path, info in entries:
            if path is None:
                reasons.append("%s: %s" % (method, info))
                continue
            found.append((line_len_m(path), method, path, info if isinstance(info, dict) else {}))
        if not found:
            return None
        found.sort(key=lambda c: c[0])
        if verbose:
            print("     %s: %s" % (label, ", ".join("%s=%.0fm" % (c[1], c[0]) for c in found)))
        return found[0]

    # --- Tier 1: both ends on real OSM ways -------------------------------------------------------
    t1 = []
    p, info = walk_both_ways_junction(a, b, ways, seg_i_coords[-3:], seg_j_coords[:3])
    t1.append(("both_ways_junction", p, info))
    for label, match_pts in (("matched_way_b", seg_j_coords[:3]), ("matched_way_a", seg_i_coords[-3:])):
        p, info = walk_along_matched_way(a, b, ways, match_pts)
        t1.append((label, p, info))
    win = tier("Stufe 1 (OSM-Weg-Matching)", t1)
    if win:
        route_m, method, path, info = win
        extra = dict(shared); extra.update(info); extra["tier"] = 1
        return method, path, route_m, extra

    # --- Tier 2: geometry the region already has --------------------------------------------------
    sub, via_loop = find_reusable_connector(region_data, loop_id, a, b)
    win = tier("Stufe 2 (vorhandener Connector)",
               [("reused_connector", sub, {"source_loop": via_loop} if sub is not None
                 else "kein passender Connector in der Region")])
    if win:
        route_m, method, path, info = win
        extra = dict(shared); extra.update(info); extra["tier"] = 2
        return method, path, route_m, extra

    # --- Tier 3: shortest path through the (access-filtered) network ------------------------------
    p, err = route_via_dijkstra(a, b, ways)
    win = tier("Stufe 3 (Dijkstra)", [("osm_route", p, err if p is None else {})])
    if win:
        route_m, method, path, info = win
        extra = dict(shared); extra.update(info); extra["tier"] = 3
        return method, path, route_m, extra

    return None, None, None, "; ".join(reasons) or "kein Wegenetz im Suchraum"


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


def close_gap(segs, i, j, bridge_points, a, b):
    """Join segment i's end (`a`) to segment j's start (`b`) via `bridge_points` (the intermediate points
    only). Extends an adjacent connector in place when one exists, so a real connector just gets longer
    instead of gaining a redundant neighbour; only inserts a brand-new connector segment when both
    neighbours are named stretches.

    **Every branch repeats the endpoint it grows away from**, so the two polylines genuinely touch: whatever
    gets prepended to segs[j] starts at `a`, whatever gets appended to segs[i] ends at `b`, and a freshly
    inserted connector spans `a`..`b`. Without that the join was only as exact as the routed path's own first
    point happened to be -- and in the degenerate case (no intermediate points at all) nothing was inserted
    and the gap silently stayed open while the report claimed a route_factor of 1.00. That was 16 of 29 gaps
    on Rodalben Felsentrails, found by measuring the written file rather than trusting the report
    (2026-08-16). The repeated coordinate costs one zero-length step in the concatenation and nothing else.
    """
    a, b = list(a), list(b)
    to_j = [a] + bridge_points          # prepended to segs[j]: now starts where segs[i] ends
    to_i = bridge_points + [b]          # appended to segs[i]:  now ends where segs[j] starts
    fresh = [a] + bridge_points + [b]   # standalone connector spanning the whole gap
    if j == 0:  # wrap-around: the gap is between the LAST segment and the FIRST -- insert at the very end
        if segs[i].get("trailId") is None and not segs[i].get("liftId"):
            segs[i]["coords"] = segs[i]["coords"] + to_i
        elif segs[j].get("trailId") is None and not segs[j].get("liftId"):
            segs[j]["coords"] = to_j + segs[j]["coords"]
        else:
            segs.append({"coords": fresh, "trailId": None})
        return segs
    if segs[j].get("trailId") is None and not segs[j].get("liftId"):
        segs[j]["coords"] = to_j + segs[j]["coords"]
    elif segs[i].get("trailId") is None and not segs[i].get("liftId"):
        segs[i]["coords"] = segs[i]["coords"] + to_i
    else:
        segs.insert(j, {"coords": fresh, "trailId": None})
    return segs


#: Bumped whenever the ROUTING LOGIC changes, so a cache written by an older algorithm is ignored instead of
#: silently replaying its results. v1 = "all methods compete, shortest wins"; v2 = tiered priority + access
#: check + way-type preference + both-ways junction (2026-08-16). Without this the whole rework would have
#: been invisible on a re-run -- every gap would have come straight back out of the v1 cache.
CACHE_VERSION = 3


def gap_cache_key(loop_id, a, b):
    """Stable key for a boundary gap, independent of segment INDEX (which shifts as gaps get closed) --
    keyed on the two endpoints themselves, rounded to ~1m, so a resumed/re-run invocation can skip the
    network entirely for a gap whose geometry hasn't changed. This is what makes an interrupted multi-hour
    run (each gap costs a real Overpass round-trip) resumable in seconds instead of from scratch, and lets
    the SAME cache serve a later "show me the actual route" request without re-fetching.
    """
    return "v%d|%s|%.6f,%.6f|%.6f,%.6f" % (CACHE_VERSION, loop_id, a[0], a[1], b[0], b[1])


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

    # ONE Overpass query for all of this loop's gaps, before touching any of them -- see
    # prefetch_routing_ways() for why (it used to be one query per gap, and that is what made a run over
    # four Tours with 32 gaps not finish).
    prefetch_routing_ways([pad_bbox(segs[i]["coords"][-1], segs[j]["coords"][0], BBOX_PAD_M)
                           for i, j, _ in gaps], verbose=verbose)

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
            row.update(cached.get("extra") or {})
            segs = close_gap(segs, i, j, bridge, a, b)
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
        cache[ckey] = {"method": method, "route_m": row["route_m"], "bridge": bridge,
                       "extra": extra_or_reason}
        flush_cache()
        factor = (row["route_m"] / dist_m) if dist_m > 0 else 0
        row["route_factor"] = round(factor, 2)
        row["suspicious"] = factor > SUSPICIOUS_ROUTE_FACTOR
        segs = close_gap(segs, i, j, bridge, a, b)
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

    by_tier, by_method = {}, {}
    for row in all_report:
        if row.get("method") in (None, "failed"):
            continue
        by_tier[row.get("tier")] = by_tier.get(row.get("tier"), 0) + 1
        by_method[row["method"]] = by_method.get(row["method"], 0) + 1
    if by_method:
        print("  Verfahren: %s" % ", ".join("%s=%d" % kv for kv in sorted(by_method.items())))
        print("  Stufen:    %s" % ", ".join("Stufe %s=%d" % kv for kv in sorted(
            by_tier.items(), key=lambda kv: (kv[0] is None, kv[0]))))
        closed = [r for r in all_report if r.get("route_factor")]
        if closed:
            print("  Ø Routenfaktor: %.2f" % (sum(r["route_factor"] for r in closed) / len(closed)))

    for row in all_report:
        if row.get("suspicious"):
            print("  !! VERDÄCHTIG: %s seg%s->seg%s  Luftlinie %.0fm, Route %.0fm (Faktor %.1f) via %s [%s]"
                  % (row["loop"], row["seg_i"], row["seg_j"], row["beeline_m"], row["route_m"],
                     row["route_factor"], row["method"], row.get("way_type") or "?"))
        elif row.get("method") == "failed":
            print("  !! NICHT GESCHLOSSEN: %s seg%s->seg%s  Luftlinie %.0fm -- %s"
                  % (row["loop"], row["seg_i"], row["seg_j"], row["beeline_m"], row["reason"]))
        elif row.get("rejected_ways"):
            print("  -- Zugang: %s seg%s->seg%s via %s [%s], %d Weg(e) wegen %s verworfen"
                  % (row["loop"], row["seg_i"], row["seg_j"], row["method"], row.get("way_type") or "?",
                     len(row["rejected_ways"]),
                     ", ".join(sorted({w["reason"] for w in row["rejected_ways"]}))))

    if args.write and touched:
        write_region(args.region, d["lineTrails"], d["trailGeo"], d["elevationProfiles"],
                     places=d.get("places"), lifts=d.get("lifts"), trail_segments=d["trailSegments"])
        print("\ngeschrieben: %s" % args.region)
    elif touched:
        print("\n(Dry Run -- nichts geschrieben. --write zum Übernehmen.)")


if __name__ == "__main__":
    main()
