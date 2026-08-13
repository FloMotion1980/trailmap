# -*- coding: utf-8 -*-
"""
@suite   geomerge
@area    Joining split trail/lift sections, comparing two sources' lines, measuring against OSM's own ways
@files   tools/build_harz.py, tools/add_harz_lifts_places.py, tools/check_geo_vs_osm.py, tools/pfaelzerwald_containment.py, tools/pfaelzerwald_rederive_loops.py
@touches chain, chain_sections, _key, _seg_distance_m, nearest_m, MAX_JOINT_M, WIDE_JOINTS, profile_shape, dist_profile, bbox_overlaps, fill_connectors, concat_ok, named_share

Both halves of this suite exist because both shipped a bug first, and both bugs looked like success.

**Section chaining.** Trailforks splits most bike-park trails into "upper/middle/lower" rows, so building the
Harz meant welding 67 sections into 42 trails. An endpoint-distance check alone cannot tell "the next section
down" from "the neighbouring trail": St. Andreasberg's two PARALLEL chairlifts have top stations 36 m apart,
and a distance-only join produced one 850 m lift that climbed 14 m end to end -- a plausible-looking object
that no later check would have questioned. So the lift joiner additionally requires the joined line to keep
climbing, and the trail joiner refuses any joint over MAX_JOINT_M unless it is named in WIDE_JOINTS with its
measured value. Both rules are pinned below, including the negative cases.

**OSM agreement.** The `_key` grid used `round(lat, 3) + 0.001`, which evaluates to 51.746000000000004 and
therefore matches no cell at all -- every trail was reported as far from every way, i.e. the check said
"broken" about geometry that was fine. Integer floor keys and a point-to-SEGMENT distance replaced it. The
segment distance matters independently: OSM ways carry nodes hundreds of metres apart on a straight forest
road, so a point-to-NODE distance calls a trail lying exactly on that road 100 m away from it. And the
`cos(lat)` case below is here because writing it is what FOUND the third bug: the segment distance divided
its already-scaled result by cos(lat) a second time, inflating every east-west offset by 1.6x at Harz
latitudes, so the first agreement run reported distances that much too large.

**Duplicate-vs-junction shape.** `profile_shape` decides whether an existing Pfälzerwald trail is deleted
in favour of an incoming Trailforks one, so a wrong answer either removes a trail that genuinely exists or
leaves two entries on one piece of ground. The aggregate containment fraction cannot separate the two cases
-- an endpoint check on Donnersberg found only 3 of its 10 real duplicates -- and the distinguishing signal
is the SHAPE of the per-point distance sequence, which is what the cases below pin: near-zero throughout or
at both ends is `subsumed`, near-zero at one end followed by monotonically growing divergence is a
`junction` (shared trailhead, both stay), and anything else is `unclear` and goes to the user rather than
being decided.

**Loop segment partition.** `fill_connectors` must slice a Trailrunde's own line into segments that
concatenate back to it byte-for-byte -- that is `validate_region.py`'s loop invariant, and it is what lets
this rework promise the drawn line never moves. Half-open slices, and single leftover points absorbed into a
neighbour rather than dropped (a hole in the partition) or emitted (a segment that draws nothing).

Verified by mutation (2026-08-13); each row produces a failure, and note the last three: two earlier
attempts at these did NOT bite because the mutation was additive instead of removing the branch under test,
which proves nothing about the test.

| mutation | fails |
|---|---|
| `hypot(cx, cy)` -> `hypot(cx / scale, cy)` in `_seg_distance_m` | a point beyond a segment's end |
| `if e[-1] <= elevs[-1] + 20:` -> `if False:` in `chain_sections` | the climb requirement |
| `MAX_JOINT_M = 55.0` -> `5000.0` | WIDE_JOINTS lets exactly one joint through |
| `_key` integer floor -> `round(lat, 3), round(lon, 3)` | grid keys are integers (+ aborts the suite) |
| `cursor = b + 1` -> `cursor = b` in `fill_connectors` | 3 partition cases at once |
| the `a - cursor == 1` absorption -> `if False:` | a one-point gap is absorbed |
| the one-point-TAIL absorption -> `if False:` | a one-point TAIL is absorbed |
| `if max(prof) <= tol * 3:` -> `if False:` in `profile_shape` | a growing tail that never gets far |
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(ROOT, "tools")


def _load(mod_name):
    """Import a tools/ script by path.

    `add_harz_lifts_places` and `check_geo_vs_osm` are scripts, not packages, and `build_harz` shares a
    module name with nothing -- importing by spec keeps this suite from depending on how tools/ is laid out.
    """
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(TOOLS, mod_name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def line(lat0, lon0, lat1, lon1, n=6):
    return [[lat0 + (lat1 - lat0) * i / (n - 1), lon0 + (lon1 - lon0) * i / (n - 1)] for i in range(n)]


class FakeEle:
    """Elevation by lookup table on rounded coordinates, falling back to a linear ramp in latitude."""

    def __init__(self, table=None, base=500.0, per_deg=0.0):
        self.table = table or {}
        self.base = base
        self.per_deg = per_deg

    def __call__(self, points):
        out = []
        for p in points:
            k = (round(p[0], 5), round(p[1], 5))
            out.append(self.table.get(k, self.base + (p[0] - 51.0) * self.per_deg))
        return out


def run(t):
    harz = _load("build_harz")
    lifts = _load("add_harz_lifts_places")
    osmchk = _load("check_geo_vs_osm")

    # ---- trail section chaining ----------------------------------------------------------------
    t.case("two sections meeting exactly are joined without a duplicated point")
    a = line(51.80, 10.50, 51.79, 10.51)
    b = line(51.79, 10.51, 51.78, 10.52)
    merged, joints = harz.chain({"a": a, "b": b}, ["a", "b"], "x")
    t.eq("the joint measured zero", joints, [("b", 0.0)])
    t.eq("no point is repeated at the seam", len(merged), len(a) + len(b) - 1)
    t.eq("the chain starts at the first section's start", merged[0], a[0])
    t.eq("and ends at the last section's end", merged[-1], b[-1])

    t.case("a section stored backwards is flipped rather than rejected")
    # Trailforks stores plenty of sections uphill; the joiner has to orient them, not refuse them.
    rev = list(reversed(line(51.79, 10.51, 51.78, 10.52)))
    merged, joints = harz.chain({"a": a, "b": rev}, ["a", "b"], "x")
    t.eq("still a zero joint", joints[0][1], 0.0)
    t.eq("and the chain runs downhill to the far end", merged[-1], [51.78, 10.52])

    t.case("a joint wider than MAX_JOINT_M is a build failure, not a straight stitch")
    far = line(51.7500, 10.6000, 51.7400, 10.6100)
    try:
        harz.chain({"a": a, "b": far}, ["a", "b"], "hz_test")
        t.ok("chain() refused the joint", False, "no exception", "SystemExit")
    except SystemExit as e:
        t.ok("chain() refused the joint", True, str(e)[:60], "SystemExit")
        t.ok("and the message names the trail", "hz_test" in str(e), str(e)[:80], "id in message")

    t.case("WIDE_JOINTS lets exactly one named joint through, and nothing else")
    # This is the mechanism keeping Braunlage's real 83 m mid-station gap from becoming a blanket
    # tolerance -- the same distance on any other trail must still fail.
    t.ok("Braunlage's Freeride gap is the only entry",
         list(harz.WIDE_JOINTS) == [("hz_bl_freeride", "freeride-lower")],
         list(harz.WIDE_JOINTS), "one entry")
    t.ok("and its allowance is above MAX_JOINT_M",
         harz.WIDE_JOINTS[("hz_bl_freeride", "freeride-lower")] > harz.MAX_JOINT_M,
         harz.WIDE_JOINTS[("hz_bl_freeride", "freeride-lower")], "> %s" % harz.MAX_JOINT_M)

    t.case("the Harz trail table only ever references geometry that exists")
    src = os.path.join(ROOT, "Material", "Harz", "harz_tf_geo.json")
    import json
    geo = json.load(open(src, encoding="utf-8"))
    used = [s for _, _, _, ss in harz.TRAILS for s in ss]
    t.eq("every referenced section is in the source file", sorted(set(used) - set(geo)), [])
    t.eq("every section has a Trailforks difficulty recorded",
         sorted(set(used) - set(harz.SECTION_DIFF)), [])
    # harzer-roller-3 is deliberately used twice: it is the stretch Brunhildenritt and Harzer Roller share.
    twice = sorted(s for s in set(used) if used.count(s) > 1)
    t.eq("exactly one section is shared between two trails", twice, ["harzer-roller-3"])

    t.case("a merged trail takes the hardest of its sections' difficulties")
    order = harz.DIFF_ORDER
    hardest = max(["Intermediate", "Severe", "Easy"], key=lambda d: order.index(harz.TF_DIFF[d]))
    t.eq("Severe wins over Intermediate and Easy", harz.TF_DIFF[hardest], "schwarz")

    # ---- lift section chaining ------------------------------------------------------------------
    t.case("two genuine lift sections chain bottom-to-top")
    lower = {"name": "L", "geom": line(51.70, 10.52, 51.705, 10.523)}
    upper = {"name": "U", "geom": line(51.705, 10.523, 51.710, 10.526)}
    ele = FakeEle(per_deg=20000.0)          # ~200 m of climb per 0.01 deg of latitude
    geom, elevs = lifts.chain_sections("lift_x", [lower, upper], ele)
    t.eq("the joined line has both sections", len(geom), len(lower["geom"]) + len(upper["geom"]) - 1)
    t.ok("and it climbs throughout", elevs[-1] > elevs[0] + 100, round(elevs[-1] - elevs[0]),
         "> 100 m of climb")

    t.case("the first section is oriented bottom-first even when OSM stored it downhill")
    geom, elevs = lifts.chain_sections("lift_x", [{"name": "L", "geom": list(reversed(lower["geom"]))}], ele)
    t.ok("bottom station first", elevs[0] < elevs[-1], (round(elevs[0]), round(elevs[-1])),
         "ascending")

    t.case("two PARALLEL lifts are refused even though their tops nearly touch")
    # The real shape: Doppelsesselbahn 1 and 2 climb the same hill with their TOP stations 36 m apart.
    # Orienting each section bottom-first is what defuses this -- the distance then gets measured from the
    # previous section's top to the next one's BOTTOM (431 m in the real data), never top-to-top. The
    # original code skipped that orientation, found the 36 m top-to-top pair, and welded on a descending
    # copy: one 850 m "lift" gaining 14 m.
    par = {"name": "Doppelsesselbahn 2", "geom": line(51.7098, 10.5259, 51.6999, 10.5198)}
    try:
        lifts.chain_sections("lift_par", [lower, par], ele)
        t.ok("chain_sections() refused it", False, "no exception", "SystemExit")
    except SystemExit as e:
        t.ok("chain_sections() refused it", True, str(e)[:70], "SystemExit")

    t.case("and the climb requirement catches a section that starts at the top but does not climb")
    # The second guard, isolated: adjacent enough to pass the distance check, but level. Without this a
    # side-branch leaving the top station would still weld on.
    level = {"name": "Level", "geom": [[51.705, 10.523], [51.7051, 10.5240], [51.70505, 10.5250]]}
    flat = FakeEle(base=700.0)          # every point the same height
    try:
        lifts.chain_sections("lift_flat", [lower, level], flat)
        t.ok("chain_sections() refused it", False, "no exception", "SystemExit")
    except SystemExit as e:
        t.ok("chain_sections() refused it", True, str(e)[:80], "SystemExit")
        t.ok("and says they are parallel, not sections", "parallel" in str(e), str(e)[:100],
             "'parallel' in message")

    # ---- OSM agreement primitives ---------------------------------------------------------------
    t.case("grid keys are integers, so a neighbouring cell is actually reachable")
    # The shipped bug: round(lat,3)+0.001 == 51.746000000000004, which is not any cell's key.
    k = osmchk._key(51.7455, 11.0075)
    t.eq("a key is a pair of ints", [type(k[0]).__name__, type(k[1]).__name__], ["int", "int"])
    kn = osmchk._key(51.7455 + osmchk.CELL, 11.0075)
    t.eq("the cell one step north is exactly one greater", kn[0] - k[0], 1)
    t.eq("and the same point always lands in the same cell", osmchk._key(51.7455, 11.0075), k)
    t.ok("a cell is wider than the default tolerance",
         osmchk.CELL * 111320.0 > 25.0 * 2, round(osmchk.CELL * 111320.0), "> 50 m")

    t.case("distance is measured to the segment, not to its nearest node")
    # A straight OSM forest road with nodes 300 m apart, and a trail point sitting right on it midway.
    a2, b2 = [51.8000, 10.5000], [51.8000, 10.5040]      # ~275 m of east-west road
    mid = [51.80002, 10.5020]                            # ~2 m off the road, 135 m from either node
    seg = osmchk._seg_distance_m(mid, a2, b2)
    t.ok("the point is metres from the segment", seg < 12, round(seg, 1), "< 12 m")
    from trailmap_pipeline import haversine_m
    to_node = min(haversine_m(mid, a2), haversine_m(mid, b2))
    t.ok("while the nearest NODE is over 100 m away", to_node > 100, round(to_node), "> 100 m")

    t.case("a point beyond a segment's end falls back to that end, not to the infinite line")
    off_end = osmchk._seg_distance_m([51.8000, 10.5100], a2, b2)
    t.ok("clamped to the endpoint distance", abs(off_end - haversine_m([51.8000, 10.5100], b2)) < 8,
         (round(off_end), round(haversine_m([51.8000, 10.5100], b2))), "within 8 m of each other")

    # ---- duplicate vs junction, the shape that decides a deletion --------------------------------
    cont = _load("pfaelzerwald_containment")

    t.case("a fully contained line reads as subsumed")
    t.eq("all near", cont.profile_shape([1, 2, 1, 3, 2, 1, 2, 1]), "subsumed")

    t.case("near in the middle with both ends drifting off is still subsumed")
    # A real duplicate from a second source typically diverges at the ends under GPS/simplification noise.
    t.eq("ends only", cont.profile_shape([70, 30, 4, 2, 1, 3, 2, 5, 28, 66]), "subsumed")

    t.case("a shared trailhead that then parts is a junction, not a duplicate")
    # This is the Eiserner Mann pair: near-zero for the first stretch, then a clean monotone walk away.
    t.eq("monotone divergence from one end",
         cont.profile_shape([1, 2, 1, 3, 2, 18, 40, 75, 130, 210, 320, 420]), "junction")

    t.case("and the same shape mirrored, sharing the OTHER end")
    t.eq("monotone divergence from the far end",
         cont.profile_shape([420, 320, 210, 130, 75, 40, 18, 2, 3, 1, 2, 1]), "junction")

    t.case("a growing tail that never gets far is NOT a junction")
    # Divergence has to be real; a 60 m drift is simplification noise on the same trail, not a fork.
    t.eq("small drift stays subsumed",
         cont.profile_shape([1, 2, 1, 3, 2, 8, 14, 22, 30, 38, 44, 52]), "subsumed")

    t.case("alternating near and far is unclear, and must not be decided")
    t.eq("no coherent shape", cont.profile_shape([1, 90, 2, 120, 3, 150, 2, 110]), "unclear")

    t.case("a short line sticking out both ends of its match is unclear, not subsumed")
    t.eq("near only in the middle, far beyond both ends",
         cont.profile_shape([300, 200, 2, 1, 2, 210, 340]), "unclear")

    t.case("a sequence too short to have a shape is unclear rather than guessed")
    t.eq("three points", cont.profile_shape([1, 2, 400]), "unclear")

    t.case("dist_profile measures to the segment, so sparse reference nodes do not inflate it")
    ref = [[49.20, 7.80], [49.20, 7.804]]          # one ~290 m segment, two nodes
    on_it = [[49.20001, 7.8010], [49.20001, 7.8020], [49.20001, 7.8030]]
    prof = cont.dist_profile(on_it, ref)
    t.ok("every point reads as on the line", max(prof) < 12, [round(x) for x in prof], "all < 12 m")

    t.case("bbox_overlaps rejects a pair that cannot possibly be contained")
    a = cont.bbox([[49.20, 7.80], [49.21, 7.81]], cont.BBOX_PAD_DEG)
    near = cont.bbox([[49.205, 7.805], [49.212, 7.812]])
    far = cont.bbox([[49.40, 8.10], [49.41, 8.11]])
    t.eq("an overlapping neighbour passes the prefilter", cont.bbox_overlaps(a, near), True)
    t.eq("a distant trail is filtered out", cont.bbox_overlaps(a, far), False)

    t.case("naturtrail_deidesheim is excluded from the comparison outright")
    # The user's instruction: those three are real MTB trails with their own difficulty and are correct.
    t.eq("excluded", "naturtrail_deidesheim" in cont.EXCLUDE_SUBREGIONS, True)

    # ---- a re-derived loop must partition its own line, not resample it -------------------------
    red = _load("pfaelzerwald_rederive_loops")
    loop = [[49.30 + i * 0.0005, 7.90 + i * 0.0004] for i in range(40)]

    t.case("segments concatenate back to the loop's own line exactly")
    # The invariant validate_region.py checks, and the reason this rework can promise the drawn line does
    # not move. The first version sliced [cursor:a+1] and [a:b+1], which shares index a -- every joint
    # silently duplicated a point and the whole loop was rejected as invalid.
    segs = red.fill_connectors(loop, [{"id": "t1", "start_idx": 5, "end_idx": 12},
                                      {"id": "t2", "start_idx": 20, "end_idx": 31}])
    t.eq("byte-identical concatenation", red.concat_ok(loop, segs), True)
    t.eq("connector / trail / connector / trail / connector",
         [s["trailId"] for s in segs], [None, "t1", None, "t2", None])
    t.eq("no segment is degenerate", min(len(s["coords"]) for s in segs) >= 2, True)

    t.case("a match touching both ends produces no empty leading or trailing connector")
    segs = red.fill_connectors(loop, [{"id": "t1", "start_idx": 0, "end_idx": 39}])
    t.eq("one segment, the whole line", [s["trailId"] for s in segs], ["t1"])
    t.eq("still exact", red.concat_ok(loop, segs), True)

    t.case("overlapping runs still partition, the earlier one keeping the shared part")
    segs = red.fill_connectors(loop, [{"id": "t1", "start_idx": 4, "end_idx": 20},
                                      {"id": "t2", "start_idx": 15, "end_idx": 30}])
    t.eq("exact", red.concat_ok(loop, segs), True)
    t.eq("both trails survive", [s["trailId"] for s in segs if s["trailId"]], ["t1", "t2"])

    t.case("a one-point gap is absorbed rather than dropped or left degenerate")
    # Dropping it would punch a hole in the partition; keeping it would draw nothing.
    segs = red.fill_connectors(loop, [{"id": "t1", "start_idx": 0, "end_idx": 10},
                                      {"id": "t2", "start_idx": 12, "end_idx": 39}])
    t.eq("exact", red.concat_ok(loop, segs), True)
    t.eq("no degenerate piece", min(len(s["coords"]) for s in segs) >= 2, True)

    t.case("a one-point TAIL is absorbed into the last segment, not left dangling")
    # A run ending one point short of the line's end leaves a single trailing point. Emitting it as its own
    # segment would draw nothing and would show up as a phantom connector in the report's share maths.
    segs = red.fill_connectors(loop, [{"id": "t1", "start_idx": 5, "end_idx": 38}])
    t.eq("exact", red.concat_ok(loop, segs), True)
    t.eq("no degenerate piece", min(len(s["coords"]) for s in segs) >= 2, True)
    t.eq("and no phantom trailing connector", [s["trailId"] for s in segs], [None, "t1"])

    t.case("named_share counts length, not segment count")
    t.near("half the line named",
           red.named_share([{"coords": loop[:20], "trailId": "t1"},
                            {"coords": loop[20:], "trailId": None}]), 0.5, 0.02)

    t.case("nearest_m finds a way in a neighbouring cell, not only its own")
    grid = {}
    ka, kb = osmchk._key(*a2), osmchk._key(*b2)
    for ky in range(min(ka[0], kb[0]), max(ka[0], kb[0]) + 1):
        for kx in range(min(ka[1], kb[1]), max(ka[1], kb[1]) + 1):
            grid.setdefault((ky, kx), []).append((a2, b2))
    t.ok("a point on the road reads as near it", osmchk.nearest_m(grid, mid) < 12,
         round(osmchk.nearest_m(grid, mid), 1), "< 12 m")
    t.eq("and a point far away reads as the cap",
         osmchk.nearest_m(grid, [51.9000, 10.9000]), 9999.0)
