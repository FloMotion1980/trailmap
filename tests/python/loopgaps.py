# -*- coding: utf-8 -*-
"""
@suite   loopgaps
@area    Closing segment-boundary gaps in a Trailrunde (tools/close_loop_gaps.py)
@files   tools/close_loop_gaps.py
@touches boundary_gaps, close_gap, build_graph, dijkstra, way_blocked, rideable_ways, way_type_penalty_m, sample_polyline, off_way_metres

A Trailrunde's segments are drawn as INDEPENDENT polylines -- nothing joins one segment's last point to the
next segment's first -- so a real gap between them is invisible on the map and leaves a rider at a dead end
with no cue where to go. This script is the user's own preferred structural fix for that
(`docs/trailrunden-lueckenschliessen.md`), and it edits committed Tour geometry, which is why the parts of
it that need no network are worth pinning.

Everything below is offline and synthetic on purpose: the routing itself goes through Overpass, and no suite
in this repo makes an outbound request. What IS covered is the part that decides what gets written --

* `boundary_gaps`, including the WRAP-AROUND boundary (last segment's end to first segment's start), which a
  plain pairwise loop over the list would miss on exactly the closure a round needs most;
* `close_gap` in all four of its branches AND in the degenerate case that shipped a real bug: with no
  intermediate points at all, nothing was inserted and the gap silently stayed OPEN while the report claimed
  a route factor of 1.00 -- 16 of 29 gaps on Rodalben Felsentrails, found by measuring the written file
  rather than trusting the report;
* `way_blocked`, which exists because the first version judged candidates purely on distance and routed a
  Tour up a `vehicle=forestry` track the user could see was unrideable;
* `build_graph`/`dijkstra`, where a wrong edge weight or a missing reverse edge silently produces a longer
  route rather than an error.
"""
from close_loop_gaps import (boundary_gaps, build_graph, close_gap, dijkstra, rideable_ways,
                             sample_polyline, way_blocked, way_type_penalty_m)
from trailmap_pipeline import haversine_m


def seg(coords, trail_id=None, lift_id=None):
    s = {"coords": [list(c) for c in coords]}
    if trail_id:
        s["trailId"] = trail_id
    if lift_id:
        s["liftId"] = lift_id
    return s


#: ~111 m per 0.001° of latitude, which is what makes the expected metres below readable.
def at(i, j=0):
    return [49.0 + i * 0.001, 7.0 + j * 0.001]


def joined(segs):
    """Every boundary either coincides or is within a metre -- the property the app actually needs."""
    return boundary_gaps(segs, 1.0)


def run(t):
    t.case("boundary_gaps finds every boundary over the threshold, wrap-around included")
    segs = [seg([at(0), at(1)]), seg([at(1), at(2)]), seg([at(5), at(6)])]
    gaps = boundary_gaps(segs, 30.0)
    # 1->2 coincides exactly; 2->3 is ~333 m; 3->1 (the wrap) is ~666 m back to the start.
    t.eq("two gaps, and the wrap-around is one of them", [(g[0], g[1]) for g in gaps], [(1, 2), (2, 0)])
    t.near("the 2->3 gap is measured, not guessed", gaps[0][2], 333.0, 5.0)
    t.near("and so is the closing one", gaps[1][2], 666.0, 8.0)
    t.eq("a threshold above every gap reports none", boundary_gaps(segs, 1000.0), [])
    t.eq("a coincident boundary is never a gap", boundary_gaps([seg([at(0), at(1)]), seg([at(1), at(0)])], 0.5), [])

    t.case("close_gap grows the adjacent CONNECTOR when there is one, on either side")
    # segs[j] is the connector -> it gets the bridge prepended, and must now start where segs[i] ended.
    segs = [seg([at(0), at(1)], trail_id="x"), seg([at(3), at(4)]), seg([at(4), at(0)], trail_id="y")]
    out = close_gap([dict(s) for s in segs], 0, 1, [at(2)], at(1), at(3))
    t.eq("no new segment was inserted", len(out), 3)
    t.eq("the connector now starts at segment 0's own last point", out[1]["coords"][0], at(1))
    t.eq("and the routed point is in it", out[1]["coords"][1], at(2))
    t.eq("it is still the same connector, not a copy", out[1]["coords"][-1], at(4))
    # The other way round: segs[i] is the connector -> the bridge is appended and must END at segs[j]'s start.
    segs2 = [seg([at(0), at(1)]), seg([at(3), at(4)], trail_id="x"), seg([at(4), at(0)], trail_id="y")]
    out2 = close_gap([dict(s) for s in segs2], 0, 1, [at(2)], at(1), at(3))
    t.eq("still no new segment", len(out2), 3)
    t.eq("the connector now ends at segment 1's own first point", out2[0]["coords"][-1], at(3))

    t.case("close_gap inserts a fresh connector only when BOTH neighbours are named stretches")
    segs = [seg([at(0), at(1)], trail_id="x"), seg([at(3), at(4)], trail_id="y")]
    out = close_gap([dict(s) for s in segs], 0, 1, [at(2)], at(1), at(3))
    t.eq("one segment was added", len(out), 3)
    t.eq("it was inserted BEFORE the segment it leads into", out[1].get("trailId"), None)
    t.eq("it spans the whole gap, endpoints included", out[1]["coords"], [at(1), at(2), at(3)])
    t.eq("and the named stretches are untouched", [out[0].get("trailId"), out[2].get("trailId")], ["x", "y"])

    t.case("close_gap handles the WRAP-AROUND gap by appending, never by inserting at index 0")
    # j == 0 means the gap is between the last segment and the first; inserting at 0 would put a connector
    # in front of the Tour's own start and shift every index the caller still holds.
    segs = [seg([at(0), at(1)], trail_id="x"), seg([at(3), at(4)], trail_id="y")]
    out = close_gap([dict(s) for s in segs], 1, 0, [at(5)], at(4), at(0))
    t.eq("the connector went to the END of the list", [s.get("trailId") for s in out], ["x", "y", None])
    t.eq("and it spans from the last point back to the first", out[-1]["coords"], [at(4), at(5), at(0)])

    t.case("close_gap with NO intermediate points still makes the two lines touch")
    # The bug this exists for: with an empty bridge the old version inserted nothing, the gap stayed open,
    # and the report claimed a route factor of 1.00 -- 16 of 29 gaps on one Tour. Every branch has to repeat
    # the endpoint it grows away from, so a degenerate bridge is still a real join.
    named = [seg([at(0), at(1)], trail_id="x"), seg([at(3), at(4)], trail_id="y")]
    out = close_gap([dict(s) for s in named], 0, 1, [], at(1), at(3))
    t.eq("a connector spanning just the two endpoints was inserted", out[1]["coords"], [at(1), at(3)])
    # Checked as the two boundaries it created, not with boundary_gaps over the whole list: this closed ONE
    # gap of two, and the wrap-around is legitimately still open.
    t.eq("segment 0's end and the new connector's start are the same point",
         out[0]["coords"][-1], out[1]["coords"][0])
    t.eq("and so are the connector's end and segment 1's start",
         out[1]["coords"][-1], out[2]["coords"][0])
    conn = [seg([at(0), at(1)], trail_id="x"), seg([at(3), at(4)])]
    out = close_gap([dict(s) for s in conn], 0, 1, [], at(1), at(3))
    t.eq("and the extend-a-connector branch does the same", out[1]["coords"], [at(1), at(3), at(4)])

    t.case("closing every reported gap really leaves the loop joined end to end")
    # The property the app needs, asserted as a property rather than per branch: after one pass, nothing is
    # left above a metre -- including the wrap-around, and with a mix of named, lift and connector segments.
    segs = [seg([at(0), at(1)], trail_id="x"), seg([at(4), at(5)], lift_id="l1"),
            seg([at(8), at(9)]), seg([at(12), at(13)], trail_id="z")]
    # RE-COMPUTED each pass, because close_gap can INSERT a segment and every index after it shifts --
    # closing a captured list of gaps in one loop closes the wrong boundaries, which is what the first
    # version of this case did (and is worth knowing before writing a caller of close_gap by hand).
    for _guard in range(20):
        gaps = boundary_gaps(segs, 30.0)
        if not gaps:
            break
        i, j, _d = gaps[0]
        segs = close_gap(segs, i, j, [], segs[i]["coords"][-1], segs[j]["coords"][0])
    t.eq("no boundary gap survives", joined(segs), [])
    t.ok("and a lift's own stretch was not extended into a bridge",
         all(len(s["coords"]) == 2 for s in segs if s.get("liftId")),
         [len(s["coords"]) for s in segs if s.get("liftId")], "[2]")

    t.case("way_blocked reads OSM's access hierarchy from a bicycle's point of view")
    t.eq("a plain track is fine", way_blocked({"highway": "track"}), (False, None))
    # The case the user caught on the map: geometrically perfect, and unrideable.
    t.eq("vehicle=forestry blocks it -- a bicycle IS a vehicle in OSM's hierarchy",
         way_blocked({"highway": "track", "vehicle": "forestry"}), (True, "vehicle=forestry"))
    t.eq("access=private blocks it", way_blocked({"highway": "track", "access": "private"})[0], True)
    t.eq("an explicit bicycle permission overrides the general restriction",
         way_blocked({"highway": "track", "vehicle": "forestry", "bicycle": "yes"}), (False, None))
    kept, rejected = rideable_ways([{"id": 1, "tags": {"highway": "path"}},
                                    {"id": 2, "tags": {"highway": "track", "access": "no"}}])
    t.eq("rideable_ways keeps the open one", [w["id"] for w in kept], [1])
    t.eq("and says WHY the other was dropped", [(r["id"], r["reason"]) for r in rejected], [(2, "access=no")])
    t.ok("a path is preferred over a forest road, per the user's own rule",
         way_type_penalty_m({"highway": "path"}) < way_type_penalty_m({"highway": "track"}),
         [way_type_penalty_m({"highway": "path"}), way_type_penalty_m({"highway": "track"})], "path cheaper")

    t.case("build_graph and dijkstra find the shorter of two ways round")
    # A square with a diagonal: the diagonal is shorter than going round two sides, and both directions of
    # every edge have to exist or the router silently takes the long way.
    nw, ne, se = (49.0, 7.0), (49.0, 7.002), (49.002, 7.002)
    ways = [{"geom": [nw, ne], "tags": {}}, {"geom": [ne, se], "tags": {}}, {"geom": [nw, se], "tags": {}}]
    graph = build_graph(ways)
    t.eq("every node knows both of its neighbours", sorted(len(v) for v in graph.values()), [2, 2, 2])
    t.eq("the diagonal is one hop", dijkstra(graph, nw, se), [list(nw), list(se)])
    # Remove the diagonal and it has to go round -- same call, different network, no error either way.
    graph2 = build_graph(ways[:2])
    t.eq("without it, the route goes round the corner",
         dijkstra(graph2, nw, se), [list(nw), list(ne), list(se)])
    t.eq("an unreachable goal is None, not an exception", dijkstra(graph2, nw, (48.0, 6.0)), None)
    t.ok("edge weights are real metres, not degrees",
         abs(haversine_m(nw, ne) - sum(w for _n, w in graph[nw] if _n == ne)) < 0.001,
         haversine_m(nw, ne), "haversine metres")

    t.case("sample_polyline walks a line at a fixed spacing and keeps both ends")
    pts = sample_polyline([at(0), at(9)], step_m=100.0)
    t.ok("it produced samples along the way", len(pts) >= 8, len(pts), ">= 8")
    t.eq("starting at the start", [round(v, 6) for v in pts[0]], [round(v, 6) for v in at(0)])
    t.near("and reaching the end", haversine_m(pts[-1], at(9)), 0.0, 100.0)
    t.ok("with no step much longer than asked for",
         max(haversine_m(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) <= 101.0,
         round(max(haversine_m(pts[i], pts[i + 1]) for i in range(len(pts) - 1)), 1), "<= 101 m")
