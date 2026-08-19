# -*- coding: utf-8 -*-
"""Candidate generation + scoring for one Trailrunde boundary gap.

Third approach (2026-08-16), after two attempts were rejected on the live map. The user's own diagnosis of
why the second one failed, and the design this file implements:

  "Aus meiner Sicht sollte es viele Varianten geben. Und du hast, glaube ich, vieles an eine Variante
   gepackt. [...] Gegebenenfalls wären mehrere Varianten auch dadurch erreichbar, indem nicht eindeutig auf
   OSM Wege gemappt werden kann. Und wir brauchen eine sinnvolle Metrik, um die Varianten zu bewerten."

So: MANY small, separately-named variants, an ambiguous way match SPAWNS one candidate per plausible way
instead of silently picking a winner, and every candidate is scored by `bridge_cost` (penalty metres, see
close_loop_gaps.py) rather than by raw length. The previous versions ranked by route length, which is not a
quality statement at all -- both failures the user found were SHORT.

THE HARD RULE, in the user's words: "Man muss immer eine Verbindung zum Endpunkt suchen oder den Endpunkt
verschieben." A bridge always terminates at a real segment endpoint -- the existing one, or a new one
created by trimming. Never at an arbitrary point in the middle of a way. That is what produced the
"connection across a stream to a point that isn't even the endpoint" the user rightly called nonsense.

A candidate is (cut_i, cut_j, mid_pts):
  * segment A (before the gap) keeps A[:cut_i+1]  -- so its new endpoint is A[cut_i]
  * segment B (after the gap)  keeps B[cut_j:]    -- so its new start    is B[cut_j]
  * the drawn bridge is [A[cut_i]] + mid_pts + [B[cut_j]]
Trimming either side is allowed (the user's explicit choice: "Beide").
"""
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trailmap_pipeline import haversine_m
from close_loop_gaps import (
    _project_on_edge, project_onto_way, slice_way_between, line_len_m,
    way_type_penalty_m, bridge_cost, WayIndex, MAX_TRIM_M,
)

#: A side's first/last points are exactly the unreliable ones -- they are the artefacts of the geometry
#: substitution that created the gap. Measured on Rodalben seg1: points 0-2 sit 45-55m from ANY way, point 3
#: onwards is on one to within 4m. Averaging over the dangling points matched the connector to the L482 and
#: produced the loop the user circled on the map. So a side is characterised by the first few points from
#: that end that genuinely lie on a way.
RELIABLE_MAX_OFF_M = 25.0
RELIABLE_COUNT = 6

#: An ambiguous match must SPAWN candidates rather than resolve itself. Every way whose mean distance to a
#: side's reliable points is within this is kept, up to WAY_CANDIDATES of them.
WAY_PLAUSIBLE_MAX_M = 30.0
WAY_CANDIDATES = 3

#: How close a walked way has to come to the other side's LINE (not its endpoint) to count as having met it.
#: The user: "bis man nah genug ist und es einfach verbinden würde".
MEET_TOL_M = 25.0
#: How far to walk a way looking for that meeting before giving up.
MAX_WALK_M = 400.0


def point_to_line(p, line):
    """Metres from p to the polyline `line`, plus the index of the closest edge."""
    best = (1e18, 0)
    for i in range(len(line) - 1):
        d = _project_on_edge(p, line[i], line[i + 1])[2]
        if d < best[0]:
            best = (d, i)
    return best


def reliable_points(coords, from_end, idx):
    """Up to RELIABLE_COUNT points, walking inward from one end, that actually lie on a way.

    CAUTION -- this is only safe for characterising a side's general course, NEVER for choosing the way to
    walk out of the gap. On Rodalben seg1 the first three points span 573m, so the "reliable" points sit over
    half a kilometre PAST the gap and describe a completely different stretch of road. Selecting the walk-out
    way with them is what silently disabled the user's own method three times in a row: V5 kept matching ways
    776m away and returning nothing, while the correct `path` -- which meets the trail line to within 0.1m --
    was never even a candidate. Use `ways_near_point` for anything anchored at the gap itself.
    """
    seq = list(reversed(coords)) if from_end else list(coords)
    out = []
    for p in seq:
        if idx.nearest(tuple(p)) <= RELIABLE_MAX_OFF_M:
            out.append(tuple(p))
            if len(out) >= RELIABLE_COUNT:
                break
    return out or [tuple(seq[0])]


#: How far from the gap's own endpoint a way may be and still be a candidate to walk out along. Generous on
#: purpose: the endpoint is frequently a dangling artefact sitting 50-60m off the road it belongs to, and
#: that is precisely the situation the walk is meant to repair.
ENDPOINT_WAY_MAX_M = 90.0
ENDPOINT_WAY_CANDIDATES = 5

#: Tolerances tried in turn for "the walked way has met the other side's line". Each one that produces a hit
#: becomes its OWN candidate, so a tight, exact meeting and a loose, further-back one both get scored rather
#: than one threshold silently deciding. The user: "bis man nah genug ist und es einfach verbinden würde",
#: and separately "meistens ist es nicht schlimm, wenn es nicht 100% exakt passt".
MEET_TOL_STEPS = (15.0, 30.0, 50.0)


def ways_near_point(ways, p, max_m=ENDPOINT_WAY_MAX_M, top=ENDPOINT_WAY_CANDIDATES):
    """Ways passing close to ONE point -- the gap's own endpoint. This is the selection the walk-out variants
    (V4/V5) must use: the question is "which road is this endpoint hanging off", not "which road does this
    segment follow on average", and those two have wildly different answers when the endpoint is an artefact.
    """
    scored = [(point_to_line(p, w["geom"])[0], w) for w in ways]
    scored = [(d, w) for d, w in scored if d <= max_m]
    scored.sort(key=lambda x: x[0] + way_type_penalty_m(x[1]["tags"]))
    return scored[:top]


def plausible_ways(ways, pts):
    """Every way this side could plausibly be running along, best first -- NOT one winner. Ambiguity here is
    exactly what the user wanted turned into extra variants."""
    scored = []
    for w in ways:
        g = w["geom"]
        md = sum(point_to_line(p, g)[0] for p in pts) / float(len(pts))
        if md <= WAY_PLAUSIBLE_MAX_M:
            scored.append((md + way_type_penalty_m(w["tags"]), md, w))
    scored.sort(key=lambda x: x[0])
    return [(w, md) for _s, md, w in scored[:WAY_CANDIDATES]]


def walk_way_to_line(way_geom, start_pt, other_line, tol_m=MEET_TOL_M, max_walk_m=MAX_WALK_M):
    """Walk the way from start_pt's projection, in BOTH directions, until a vertex comes within tol_m of
    `other_line`. Returns a list of (mid_pts, meet_vertex, walked_m, dist_to_line) -- one per direction that
    found something. This is the "rückwärts/vorwärts laufen bis es auf den Trail stößt" the user described.
    """
    if len(way_geom) < 2:
        return []
    i0, _t0, q0, _d0 = project_onto_way(way_geom, start_pt)
    found = []
    for step in (1, -1):
        mid = [list(q0)]
        walked, prev = 0.0, q0
        k = i0 + 1 if step > 0 else i0
        while 0 <= k < len(way_geom):
            p = way_geom[k]
            walked += haversine_m(prev, p)
            prev = p
            mid.append(list(p))
            d, _e = point_to_line(p, other_line)
            if d <= tol_m:
                found.append((list(mid), p, walked, d))
                break
            if walked > max_walk_m:
                break
            k += step
    return found


def _cand(name, cut_i, cut_j, mid, info=None):
    return {"name": name, "cut_i": cut_i, "cut_j": cut_j, "mid": mid, "info": info or {}}


def generate_candidates(A, B, ways, idx, region_data=None, loop_id=None):
    """Every candidate bridge for the gap between segment A (ends) and segment B (starts).

    A and B are plain coordinate lists. Returns a list of candidate dicts (see module docstring).
    """
    a, b = A[-1], B[0]
    last_i, first_j = len(A) - 1, 0
    out = []

    # ---- V9: straight line. Always available, always a valid endpoint-to-endpoint connection.
    out.append(_cand("V9_gerade", last_i, first_j, []))

    # Ways are chosen by proximity to the gap's OWN endpoints throughout -- never by averaging over points
    # far up the segment (see reliable_points' warning for what that cost).
    ways_a = ways_near_point(ways, a)
    ways_b = ways_near_point(ways, b)

    # ---- V1: a way at A's endpoint, walked forward to B's endpoint. One candidate PER plausible way.
    for md, w in ways_a:
        mid, _da, _db = slice_way_between(w["geom"], a, b)
        if mid:
            out.append(_cand("V1_A-Weg-vorwaerts", last_i, first_j, mid,
                             {"way": w["tags"].get("highway"), "endpoint_off_m": round(md, 1)}))

    # ---- V2: a way at B's endpoint, walked backward to A's endpoint. One candidate PER plausible way.
    for md, w in ways_b:
        mid, _da, _db = slice_way_between(w["geom"], a, b)
        if mid:
            out.append(_cand("V2_B-Weg-rueckwaerts", last_i, first_j, mid,
                             {"way": w["tags"].get("highway"), "endpoint_off_m": round(md, 1)}))

    # ---- V3: both sides' ways continued until they meet each other.
    for _mda, wa in ways_a:
        for _mdb, wb in ways_b:
            if wa is wb:
                continue
            ga, gb = wa["geom"], wb["geom"]
            best = None
            for i, p in enumerate(ga):
                for j, q in enumerate(gb):
                    dd = haversine_m(p, q)
                    if best is None or dd < best[0]:
                        best = (dd, i, j)
            if best is None or best[0] > 60.0:
                continue
            _d, ja, jb = best
            lead, _x, _y = slice_way_between(ga, a, ga[ja])
            tail, _x, _y = slice_way_between(gb, gb[jb], b)
            if lead and tail:
                out.append(_cand("V3_Schnittpunkt", last_i, first_j, lead + tail,
                                 {"way": "%s+%s" % (wa["tags"].get("highway"), wb["tags"].get("highway")),
                                  "junction_m": round(best[0], 1)}))

    # ---- V4: walk out of A's OWN ENDPOINT along each nearby way until it MEETS B's line, then trim B's head
    #          to the meeting point.
    for d0, w in ways_near_point(ways, a):
        for tol in MEET_TOL_STEPS:
            for mid, meet, walked, dd in walk_way_to_line(w["geom"], a, B, tol_m=tol):
                cj = point_to_line(meet, B)[1]
                out.append(_cand("V4_A-Weg + B kappen", last_i, cj, mid,
                                 {"way": w["tags"].get("highway"), "meet_m": round(dd, 1),
                                  "walk_m": round(walked, 1), "tol": tol,
                                  "endpoint_off_m": round(d0, 1)}))

    # ---- V5: walk out of B's OWN ENDPOINT backward along each nearby way until it MEETS A's line, then trim
    #          A's tail. This is exactly the shape the user specified, three times over: "gestrichelte Linie
    #          auf OSM Weg zurück laufen, bis es auf den grünen Trail stößt und grünen Trail dann kürzen".
    #          It only started producing anything once the way came from `ways_near_point(b)` instead of from
    #          averaged distant points -- see reliable_points' own warning.
    for d0, w in ways_near_point(ways, b):
        for tol in MEET_TOL_STEPS:
            for mid, meet, walked, dd in walk_way_to_line(w["geom"], b, A, tol_m=tol):
                ci = point_to_line(meet, A)[1]
                out.append(_cand("V5_B-Weg + A kappen", ci, first_j, list(reversed(mid)),
                                 {"way": w["tags"].get("highway"), "meet_m": round(dd, 1),
                                  "walk_m": round(walked, 1), "tol": tol,
                                  "endpoint_off_m": round(d0, 1)}))

    # ---- V6: cut BOTH sides back to a way they each touch, and let that way BE the connection. The cleanest
    #          shape when a single road runs past both segments: instead of jumping from a dangling endpoint
    #          to the road and back off it again, both segments simply end where they genuinely meet it.
    #          This is what removes the "letzter Meter quer durchs Gelände" leg that the walk-out variants
    #          still carry when an endpoint hangs 60m off its own road.
    seen_ways = set()
    for _d, w in list(ways_near_point(ways, a)) + list(ways_near_point(ways, b)):
        if id(w) in seen_ways:
            continue
        seen_ways.add(id(w))
        g = w["geom"]
        # where does each side's LINE come closest to this way, and where on the way is that
        ia, da = min(((k, point_to_line(p, g)[0]) for k, p in enumerate(A)), key=lambda x: x[1])
        jb, db = min(((k, point_to_line(p, g)[0]) for k, p in enumerate(B)), key=lambda x: x[1])
        if da > MEET_TOL_STEPS[-1] or db > MEET_TOL_STEPS[-1]:
            continue
        mid, _x, _y = slice_way_between(g, A[ia], B[jb])
        if not mid:
            continue
        out.append(_cand("V6_beide auf Weg kappen", ia, jb, mid,
                         {"way": w["tags"].get("highway"),
                          "meet_m": round(max(da, db), 1)}))

    # ---- V7: an existing pure connector elsewhere in the region that passes both endpoints.
    if region_data and loop_id:
        from close_loop_gaps import find_reusable_connector
        sub, via = find_reusable_connector(region_data, loop_id, a, b)
        if sub:
            out.append(_cand("V7_vorhandener-Connector", last_i, first_j,
                             [list(p) for p in sub[1:-1]], {"source_loop": via}))

    # ---- V8: shortest path through the rideable network.
    from close_loop_gaps import route_via_dijkstra
    path, _err = route_via_dijkstra(a, b, ways)
    if path:
        out.append(_cand("V8_Dijkstra", last_i, first_j, path[1:-1]))

    return out


def score_candidate(c, A, B, idx, beeline_m):
    """Attach the penalty-metre cost (and its breakdown) to one candidate."""
    a2, b2 = A[c["cut_i"]], B[c["cut_j"]]
    bridge = [list(a2)] + [list(p) for p in c["mid"]] + [list(b2)]
    # de-dupe so a bridge whose first point IS the endpoint doesn't count a zero-length leg
    ded = [bridge[0]]
    for p in bridge[1:]:
        if haversine_m(ded[-1], p) > 0.5:
            ded.append(p)
    trimmed = 0.0
    if c["cut_i"] < len(A) - 1:
        trimmed += line_len_m(A[c["cut_i"]:])
    if c["cut_j"] > 0:
        trimmed += line_len_m(B[:c["cut_j"] + 1])
    c["bridge"] = ded
    c.update(bridge_cost(ded, idx, beeline_m, trimmed_m=trimmed, residual_m=0.0))
    if trimmed > MAX_TRIM_M:
        c["cost"] = float("inf")   # cutting away this much is never the right repair
        c["rejected"] = "kappt %.0fm (> %.0fm)" % (trimmed, MAX_TRIM_M)
    return c


def best_for_gap(A, B, ways, idx, region_data=None, loop_id=None):
    """All candidates, scored, cheapest first."""
    beeline = haversine_m(A[-1], B[0])
    cands = [score_candidate(c, A, B, idx, beeline) for c in generate_candidates(A, B, ways, idx, region_data, loop_id)]
    cands.sort(key=lambda c: c["cost"])
    return cands


# ---------------------------------------------------------------------------------------------------
# THE method, in the user's own words after four failed attempts (2026-08-16):
#   "Geh die Linie zurück auf dem OSM Weg. Du wirst den grünen Trailabschnitt SCHNEIDEN. Das ist der neue
#    Endpunkt des grünen Trails. Er muss dafür gekürzt werden."
#
# Two things were wrong in every earlier attempt, and both are in that one sentence:
#   1. "schneiden" means a real geometric INTERSECTION of the walked way with the trail's line -- not
#      "comes within N metres of it", which is what walk_way_to_line tested. A near-miss tolerance produced
#      links that ended beside the trail and had to cut across open ground to reach it.
#   2. The walk back follows the WAY NETWORK, across way boundaries. Every earlier variant matched a single
#      OSM way and walked only that one; between this trail's end and its connector's start there are
#      several ways in sequence, so no single-way method could ever get there.
def _intersect(p1, p2, p3, p4):
    """Intersection point of segments p1p2 and p3p4, in a local metre frame, or None."""
    lat0 = math.radians((p1[0] + p3[0]) / 2.0)
    mx = 111320.0 * max(0.15, math.cos(lat0))
    my = 110540.0
    def xy(p): return (p[1] * mx, p[0] * my)
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = xy(p1), xy(p2), xy(p3), xy(p4)
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / den
    if not (0.0 <= t <= 1.0 and 0.0 <= u <= 1.0):
        return None
    return ((y1 + t * (y2 - y1)) / my, (x1 + t * (x2 - x1)) / mx)


def walk_network_back_to_cut(start_pt, trail, ways, max_walk_m=1200.0):
    """Walk the rideable way NETWORK outward from `start_pt` and return the first place where it actually
    CUTS the trail's line, together with the route that got there.

    Returns (route_pts_from_start_to_cut, cut_point, trail_edge_index, walked_m) or None.
    """
    import heapq
    from close_loop_gaps import build_graph, nearest_node
    graph = build_graph(ways)
    if not graph:
        return None
    n0, _d0 = nearest_node(graph, tuple(start_pt), max_m=120.0)
    if n0 is None:
        return None
    dist = {n0: 0.0}
    prev = {}
    pq = [(0.0, n0)]
    seen = set()
    best = None
    while pq:
        dcur, u = heapq.heappop(pq)
        if u in seen or dcur > max_walk_m:
            continue
        seen.add(u)
        for v, w in graph.get(u, ()):
            # does this edge of the network cut the trail?
            for ti in range(len(trail) - 1):
                x = _intersect(u, v, trail[ti], trail[ti + 1])
                if x is not None:
                    total = dcur + haversine_m(u, x)
                    if best is None or total < best[0]:
                        best = (total, u, x, ti)
            nd = dcur + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if best is None:
        return None
    walked, u, cut, ti = best
    chain = [u]
    while chain[-1] != n0:
        chain.append(prev[chain[-1]])
    chain.reverse()
    route = [list(start_pt)] + [list(p) for p in chain] + [list(cut)]
    return route, cut, ti, walked
