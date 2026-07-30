# -*- coding: utf-8 -*-
"""Add Bike Kingdom's summer bike lifts and its four Biketicket-2-RIDE tours to the region file.

Runs ON TOP of what tools/build_bikekingdom.py produced -- it loads regions/bikekingdom.json, keeps every
trail untouched, and adds `lifts`, four `loop: true` entries and their `trailSegments`. So the order is
always: build_bikekingdom.py first (if the trails are being rebuilt), then this, then
update_region_versions.py + validate_region.py.

Two sources, each authoritative for a different thing:

  operator pages (see LIFTS below)     WHICH lifts run in summer and carry bikes -- never OSM's
                                       aerialway:bicycle tag, which was wrong in both directions in
                                       Saalbach. See docs/lifts-feature.md.
  OpenStreetMap                        the cable geometry only, matched by name.
  Material/BikeKingdom/*.gpx           the four tours' own recorded tracks (with real per-point elevation),
                                       from the same Outdooractive portal the trails came from.
  outdooractive.com/r/<id>             each tour's published length/ascent/descent, preferred over
                                       GPX-derived figures like everywhere else in this app.

The tours are matched CLASSICALLY against the region's existing trails and lifts -- deliberately not with
the Tourenbuilder, which is a tool for app users ("der ist ein Werkzeug für App Nutzer").

Run:  python tools/build_bikekingdom_tours.py [--report <file>]

`--report` writes the whole report (and any traceback) to a file as UTF-8. Worth using: the console this
runs on is cp850, which cannot encode the en-dashes in the Swiss lift names -- the first version of this
script died on `print("… Chur–Känzeli …")` with a UnicodeEncodeError right after the OSM dump, which looks
exactly like "it produced nothing". stdout is reconfigured below so that cannot happen again, but a file is
still easier to read back than a scrollback buffer.
"""
import io
import json
import math
import os
import re
import sys
import traceback

# The report is full of names this script has no control over (OSM's own strings, the operator's
# en-dashes), and it is diagnostic output -- it must never be the thing that kills the build.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import (haversine_m, douglas_peucker, dedupe_points, cumulative_km,  # noqa: E402
                               parse_gpx, build_profile, write_region, region_summary,
                               osm_aerialway_survey, ElevationLookup, norm_name)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, "Material", "BikeKingdom")
OUT = os.path.join(ROOT, "Trailmap App", "regions", "bikekingdom.json")
BBOX = "46.70,9.42,46.90,9.80"

LOG = []


def say(line=""):
    """Print and remember. `--report` dumps everything remembered, so a failed run is still readable."""
    LOG.append(line)
    print(line, flush=True)

# ---------------------------------------------------------------------------------------------------
# The lifts, from the operators' own summer pages
# ---------------------------------------------------------------------------------------------------
# `name` is the operator's own name and what the app shows. `osm` is a regex ANCHORED against OSM's own
# name for the way. Anchored deliberately: a loose pattern plus "longest match wins" silently picked the
# wrong cable twice in the first run of this script -- `Brambr[üu]esch` matched the *T-bar*
# "Brambrüesch - Hühnerköpfe" (1429 m) instead of the gondola, whose OSM name drops the r
# ("Känzeli - Brambüesch", 1319 m), and `Urden`/`H[öo]rnli`/`Tschuggen` each also matched a neighbouring
# chairlift. `region` is the sub-region the lift's stations sit in -- checked against the nearest trails,
# see report_lift_regions().
#
# Worth noting for the next region: OSM's own bike tags happen to agree with the operator here almost
# exactly -- `aerialway:bicycle=summer` sits on precisely these twelve minus the two Chur sections (which
# carry `=yes`), and Pradaschier has none. That is a pleasant coincidence, not a reason to start trusting
# the tag: it was wrong in both directions in Saalbach, and the operator's list is still what decides.
#
# Confirmed carrying bikes in summer 2026 (arosalenzerheide.swiss "Betriebszeiten Sommer",
# bikekingdom.ch's own sport report, churbergbahnen.ch for the two Chur sections). The four marked
# "keine Downhillbikes" DO carry normal bikes and belong here -- the data states only the stable
# property "this lift carries bikes in summer", the same reason a temporary closure is not modelled.
#
# Deliberately EXCLUDED: Sesselbahn Pradaschier (Churwalden), which the operator lists under
# "Kein Biketransport" -- it runs all summer for the toboggan run, but takes no bikes at all.
# Also excluded: the winter-only drag lifts (Crestas, Dieschen, Fastatsch, Valbella) and Sesselbahn
# Heimberg, none of which the summer list carries bikes on.
LIFTS = [
    # Chur -- the two sections up to the Alpenbikepark. Both take MTB/DH/e-bikes, the gondola up to 25 kg.
    dict(id="lift_bk_chur_kaenzeli", name="Luftseilbahn Chur–Känzeli",
         region="bk_park_chur", osm=r"^Chur - K[äa]nzeli$"),
    dict(id="lift_bk_kaenzeli_brambrueesch", name="Gondelbahn Känzeli–Brambrüesch",
         region="bk_park_chur", osm=r"^K[äa]nzeli - Bramb"),
    # Lenzerheide. The second section is a reversible aerial tramway, not a gondola -- OSM's cable_car
    # agrees with the operator, so the name says so.
    dict(id="lift_bk_rothorn1", name="Gondelbahn Rothorn 1",
         region="bk_park_lenzerheide", osm=r"^Rothorn 1$"),
    dict(id="lift_bk_rothorn2", name="Luftseilbahn Rothorn 2",
         region="bk_red_peak", osm=r"^Rothorn 2$"),
    dict(id="lift_bk_tgantieni", name="Sesselbahn Tgantieni",
         region="bk_western_summits", osm=r"^Tgantieni$"),
    dict(id="lift_bk_scalottas", name="Sesselbahn Scalottas",
         region="bk_western_summits", osm=r"^Scalottas$"),
    dict(id="lift_bk_heidbueel", name="Panoramabahn Heidbüel",
         region="bk_western_summits", osm=r"^Panoramabahn Heidb[üu]el$"),
    # Arosa
    dict(id="lift_bk_hoernli", name="Hörnli-Express",
         region="bk_bear_mountains", osm=r"^H[öo]rnli-Express$"),
    dict(id="lift_bk_urdenbahn", name="Urdenbahn",
         region="bk_bear_mountains", osm=r"^Urdenbahn$"),
    dict(id="lift_bk_weisshorn1", name="Luftseilbahn Arosa–Weisshorn 1. Sektion",
         region="bk_bear_mountains", osm=r"^Weisshornbahn 1\. Sektion$"),
    dict(id="lift_bk_weisshorn2", name="Luftseilbahn Weisshorn 2. Sektion",
         region="bk_bear_mountains", osm=r"^Weisshornbahn 2\. Sektion$"),
    dict(id="lift_bk_weisshorn_speed", name="Sesselbahn Weisshorn Speed",
         region="bk_bear_mountains", osm=r"^Weisshorn Speed$"),
]

# ---------------------------------------------------------------------------------------------------
# The four tours
# ---------------------------------------------------------------------------------------------------
# `official` is (km, up_m, down_m) as outdooractive publishes it for that route id -- the same figures the
# operator's own tour pages show. They include the metres the mountain railways climb, which is why the
# black route reads 6385 m of ascent while its own description says you only pedal ~700 m of it.
TOURS = [
    dict(id="bk_tour_615_blau", gpx="t2805733_615 biketicket to ride.gpx",
         name="615 Biketicket to ride blau", diff="blau", official=(60.8, 2904, 2400)),
    dict(id="bk_tour_616_rot", gpx="t2811055_616 biketicket to ride red.gpx",
         name="616 Biketicket to ride rot", diff="rot", official=(46.7, 2887, 2882)),
    dict(id="bk_tour_b2r_schwarz", gpx="t3508125_biketicket 2 ride black.gpx",
         name="Biketicket 2 RIDE schwarz", diff="schwarz", official=(90.6, 6385, 6385)),
    dict(id="bk_tour_b2r_e_rot", gpx="t37756137_e-biketicket 2 ride red.gpx",
         name="E-Biketicket 2 RIDE rot", diff="rot", official=(63.9, 3730, 3725)),
]
TOUR_REGION = "bk_biketickets"

# Matching parameters. Every one of these was tuned by eye against the report this script prints; the
# thresholds below are the ones that reproduce the lift lists the operators' own tour descriptions name.
DENSIFY_M = 10.0      # both the tour track and the candidate trails, so a short component cannot fall
                      # between two raw vertices (GPX tracks here are up to ~90 m apart in places)
MATCH_M = 25.0        # a tour point this close to a trail counts as riding it
EXTEND_MATCH_M = 100.0  # looser -- only to GROW an already-found run into its neighbouring connector,
                        # never to start a new match from scratch (see extend_trail_ends)
MIN_RUN_M = 200.0     # shorter runs are crossings or a shared first corner, not a ride
GAP_FILL_M = 150.0    # same trail either side of a gap this short -> one ride, not two
MERGE_SAME_TRAIL_M = 600.0  # ...and up to this far, when the trail also continues where it left off
MAX_TRAIL_GAP_M = 600.0     # ...or any ridden distance, as long as this little TRAIL is missing in between
LIFT_NEAR_M = 60.0    # a tour point this close to a cable may be a ride on it
LIFT_STATION_M = 250.0  # ...but only if the run reaches both stations, one at each end
LIFT_SPAN_FRAC = 0.6  # ...and covers at least this much of the cable, so passing UNDER one is not a ride
LIFT_DETOUR_MAX = 1.2   # ...and runs almost straight, which a switchbacking uphill trail under it does not
MAX_QUIET_JOIN_M = 115.0  # a longer seam between two segments is a defect to report, not one to bridge --
                          # raised from 60 once extend_trail_ends existed: it deliberately stops a trail
                          # extension right at EXTEND_MATCH_M (100 m), so the following connector's own
                          # recorded point can legitimately sit up to that far from the trail's last accepted
                          # point. That is not a defect, it is where extension correctly gave up.


# ---------------------------------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------------------------------

def densify(coords, step=DENSIFY_M):
    """[(lat, lon, source_vertex_index), ...] with no gap longer than `step`.

    The source index is what lets a matched run be clipped back to the component trail's OWN vertices:
    the segment drawn has to be the trail's geometry, not the tour's coarser recording of it.
    """
    out = []
    for i in range(len(coords) - 1):
        a, b = coords[i], coords[i + 1]
        d = haversine_m(a, b)
        n = max(1, int(d // step))
        for k in range(n):
            t = k / float(n)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, i))
    out.append((coords[-1][0], coords[-1][1], len(coords) - 1))
    return out


CELL_LAT = 0.00045          # ~50 m
CELL_LON = 0.00065


def grid_build(items):
    """{cell: [(lat, lon, key, vertex_index), ...]} for fast nearest lookups."""
    g = {}
    for lat, lon, key, idx in items:
        g.setdefault((int(lat / CELL_LAT), int(lon / CELL_LON)), []).append((lat, lon, key, idx))
    return g


def grid_nearest(g, lat, lon, max_m):
    """The closest (dist, key, vertex_index) within max_m, or None."""
    ci, cj = int(lat / CELL_LAT), int(lon / CELL_LON)
    best = None
    for i in range(ci - 1, ci + 2):
        for j in range(cj - 1, cj + 2):
            for plat, plon, key, idx in g.get((i, j), ()):
                d = haversine_m((lat, lon), (plat, plon))
                if d <= max_m and (best is None or d < best[0]):
                    best = (d, key, idx)
    return best


def runs_of(labels):
    """[(label, start, end_inclusive), ...] over consecutive equal labels."""
    out, i = [], 0
    while i < len(labels):
        j = i
        while j + 1 < len(labels) and labels[j + 1] == labels[i]:
            j += 1
        out.append((labels[i], i, j))
        i = j + 1
    return out


def run_len_m(pts, a, b):
    return sum(haversine_m(pts[k], pts[k + 1]) for k in range(a, b))


# ---------------------------------------------------------------------------------------------------
# Lifts
# ---------------------------------------------------------------------------------------------------

def build_lifts(verbose=True):
    """Resolve every entry in LIFTS against OSM geometry; returns the region file's `lifts` array."""
    survey = osm_aerialway_survey(BBOX)
    if verbose:
        say("OSM aerialways in the bbox: %d" % len(survey))
        for r in sorted(survey, key=lambda r: r["name"]):
            say("   %-46s %-11s ref=%-6s bike=%-5s %5d m  way/%s"
                % (r["name"][:46], r["aerialway"], r["ref"], r["bike"], r["len"], r["id"]))

    say("\nresolving %d lifts (station elevations via OpenTopoData, cached in Material/BikeKingdom)"
        % len(LIFTS))
    ele = ElevationLookup(os.path.join(MAT, "elevation_cache.json"))
    out, missing = [], []
    for spec in LIFTS:
        rx = re.compile(spec["osm"], re.I)
        hits = [r for r in survey if rx.search(r["name"] or "")]
        if not hits:
            missing.append(spec["name"])
            continue
        # Anchored patterns are expected to hit exactly one way. Ambiguity is an error rather than a
        # "longest wins" guess -- that guess is what picked the wrong cable in this script's first run.
        if len(hits) > 1:
            raise SystemExit("%s matches %d OSM ways: %s"
                             % (spec["name"], len(hits), ", ".join(h["name"] for h in hits)))
        row = hits[0]
        coords = [[round(c[0], 6), round(c[1], 6)] for c in row["geom"]]
        e = ele([coords[0], coords[-1]])
        if e[0] > e[-1]:                       # store bottom-station-first, always
            coords, e = coords[::-1], e[::-1]
        # No `code`: Bike Kingdom publishes no lift codes the way Saalbach's A1/B2 do, and the info panel
        # already treats the field as optional.
        out.append({"id": spec["id"], "name": spec["name"],
                    "region": spec["region"], "type": row["aerialway"], "coords": coords,
                    "baseEle": int(round(e[0])), "topEle": int(round(e[-1])),
                    "osm": "way/%s" % row["id"]})
        if verbose:
            say("  ok %-44s <- OSM %-30s %-11s %5d m  %d->%d m"
                % (spec["name"], row["name"], row["aerialway"], row["len"],
                   out[-1]["baseEle"], out[-1]["topEle"]))
    if missing:
        raise SystemExit("no OSM aerialway matched: %s" % ", ".join(missing))
    return out


def report_lift_regions(lifts, trails, geo):
    """Print, for each lift, which sub-region's trails are actually nearest -- a check on LIFTS' `region`.

    A lift's sub-region is a judgement call (the resort's own areas overlap), so this does not overwrite
    anything; it just makes a wrong call visible.
    """
    say("\nsub-region check (nearest trails to each lift):")
    for l in lifts:
        mid = l["coords"][len(l["coords"]) // 2]
        best = {}
        for t in trails:
            if t.get("loop"):
                continue
            d = min(haversine_m(mid, c) for c in geo[t["id"]][::4])
            if d < best.get(t["region"], (1e18,))[0]:
                best[t["region"]] = (d, t["name"])
        near = sorted(best.items(), key=lambda kv: kv[1][0])[:3]
        flag = "" if near and near[0][0] == l["region"] else "   <-- differs from LIFTS"
        say("   %-44s %-22s | %s%s"
            % (l["name"], l["region"],
               ", ".join("%s %.0fm (%s)" % (k, v[0], v[1]) for k, v in near), flag))


# ---------------------------------------------------------------------------------------------------
# Tours
# ---------------------------------------------------------------------------------------------------

def label_lifts(pts, labels, lifts):
    """Mark every stretch of `pts` that is a ride on one of `lifts`, in place.

    The cable is densified first, for the same reason the trails are: an OSM aerialway is often just TWO
    vertices, tower to tower. Measuring point-to-vertex puts a track point in the middle of a 937 m cable
    ~470 m from either end while it sits exactly ON the line -- which is why an earlier version found 0 lift
    rides in 4 tours even though every station matched within 20 m. It goes through the same grid the trails
    use rather than a nested loop: a densified cable is ~200 points, and 8000 x 12 x 200 was minutes a tour.
    """
    cable_grid = grid_build([(p[0], p[1], lf["id"], i)
                            for lf in lifts for i, p in enumerate(densify(lf["coords"]))])
    near_by_lift = {}
    for k, p in enumerate(pts):
        ci, cj = int(p[0] / CELL_LAT), int(p[1] / CELL_LON)
        for i in range(ci - 2, ci + 3):
            for j in range(cj - 2, cj + 3):
                for plat, plon, lid, _ in cable_grid.get((i, j), ()):
                    if haversine_m(p, (plat, plon)) <= LIFT_NEAR_M:
                        near_by_lift.setdefault(lid, set()).add(k)

    walk = [0.0]
    for i in range(1, len(pts)):
        walk.append(walk[-1] + haversine_m(pts[i - 1], pts[i]))

    for lf in lifts:
        cable = lf["coords"]
        clen = cumulative_km(cable)[-1] * 1000
        near = sorted(near_by_lift.get(lf["id"], ()))
        # every maximal consecutive run, not just the longest: a tour may ride the same lift twice
        runs, cur = [], None
        for k in near:
            if cur and k == cur[1] + 1:
                cur = (cur[0], k)
            else:
                if cur:
                    runs.append(cur)
                cur = (k, k)
        if cur:
            runs.append(cur)

        # Search WITHIN each run for a station-to-station piece rather than testing the run as a whole. A
        # tour often rides a lift up and comes back down the trail built beside it -- the Hörnli Trail lies
        # under the Hörnli-Express, so both directions land in ONE run whose walked length is twice its
        # straight span, and testing the whole run threw the ride away (schwarz lost the Hörnli-Express
        # entirely). The descent still cannot win a pair: it switchbacks, so its walked/span ratio fails.
        todo = list(runs)
        while todo:
            s, e = todo.pop()
            if e - s < 1:
                continue
            bots = [k for k in range(s, e + 1) if haversine_m(pts[k], cable[0]) <= LIFT_STATION_M]
            tops = [k for k in range(s, e + 1) if haversine_m(pts[k], cable[-1]) <= LIFT_STATION_M]
            best = None
            for i in bots:
                for j in tops:
                    a, b = min(i, j), max(i, j)
                    if b - a < 1:
                        continue
                    span = haversine_m(pts[a], pts[b])
                    walked = walk[b] - walk[a]
                    if span < LIFT_SPAN_FRAC * clen or walked > LIFT_DETOUR_MAX * span:
                        continue
                    # the widest valid pair is the full ride; a shorter one would clip it
                    if best is None or span > best[2]:
                        best = (a, b, span)
            if best is None:
                continue
            a, b, _ = best
            for k in range(a, b + 1):
                labels[k] = lf["id"]
            # a second ride on the same lift can sit in what is left of this run
            if a - s > 1:
                todo.append((s, a - 1))
            if e - b > 1:
                todo.append((b + 1, e))


def _edge_dense_pos(dense, v, toward_larger):
    """A starting index into `dense` (a (lat,lon,srcIdx) list, srcIdx non-decreasing) next to vertex `v`.

    toward_larger=True: the LAST dense index with srcIdx <= v, so stepping +1 moves into larger srcIdx.
    toward_larger=False: the FIRST dense index with srcIdx >= v, so stepping -1 moves into smaller srcIdx.
    """
    if toward_larger:
        pos = -1
        for i, (_, _, s) in enumerate(dense):
            if s <= v:
                pos = i
            else:
                break
        return pos
    for i, (_, _, s) in enumerate(dense):
        if s >= v:
            return i
    return len(dense)


#: How many densified trail points (~10 m each) the walk may consume for ONE track point while catching up.
#: Needed because the tour's track and the trail are sampled at different effective speeds, so a strict
#: one-for-one walk slowly loses sync and then fails a distance check while the tour is still on the trail.
EXTEND_CATCHUP = 8


def _advance(p, dense, pos, step):
    """Next densified-trail index for track point `p`, moving only in `step` direction. None if it diverged.

    Scans up to EXTEND_CATCHUP steps ahead and takes the closest candidate within EXTEND_MATCH_M. Strictly
    monotonic by construction -- it can never return an index behind `pos`, which is what stops the walk from
    latching onto an earlier stretch of the same trail that the tour happens to pass near later (verified on
    Hörnli Trail's tail; see the docstring below).
    """
    best, best_d = None, None
    for n in range(1, EXTEND_CATCHUP + 1):
        cand = pos + step * n
        if not (0 <= cand < len(dense)):
            break
        dist = haversine_m(p, dense[cand][:2])
        if dist <= EXTEND_MATCH_M and (best_d is None or dist < best_d):
            best, best_d = cand, dist
    return best


def extend_trail_ends(pts, labels, vidx, trails, geo, lift_ids, vertex_at):
    """Grow each trail run outward into its neighbouring connector, at a looser tolerance, in place.

    MATCH_M's strict 25 m is right for deciding WHICH trail a point belongs to, but it also means a GPS
    recording that drifts off a narrow trail falls out of the match entirely -- the user found this on the
    E-bike tour: Älplisee Trail lost ~1.3 km in the middle and ~600 m at the end, Hörnli Trail lost 50 m at the
    start and 1.26 km at the end, even though the tour's own track stays within roughly 90-200 m of the trail
    there the whole time. The visible defect was exactly what the user described: the gap gets drawn using the
    tour's own (drifted) recording, a visibly different line than the trail's real one shown everywhere else.

    The fix is the one already agreed for the multi-run overlap case: draw the trail's OWN clean geometry
    instead of the tour's line, wherever the tour plausibly still follows it. This walks outward from each
    trail run's two edges, one track point and one trail vertex at a time, absorbing connector points into the
    run as long as they stay within EXTEND_MATCH_M of the trail's next vertex -- looser than MATCH_M, since
    rescuing exactly this kind of drift is the point, but it still stops the moment the tour genuinely diverges
    (a real fork), or the connector, or the trail itself, runs out. Two runs of the SAME trail extending toward
    each other close the gap between them entirely, which is how Älplisee's middle stretch gets bridged.

    Walks along DENSIFIED trail points (~10 m apart, same spacing as the densified track), not the original
    simplified vertices directly -- those can be tens or hundreds of metres apart on a straight stretch, which
    would make a one-vertex-per-track-point walk overshoot and fail immediately from pacing alone, not from
    any real divergence.

    The walk advances via _advance(), which may consume several trail points for one track point but can only
    ever move FORWARD. Strict monotonicity is the load-bearing property: without it a free nearest-point
    search latches onto an earlier stretch of the same trail that the tour passes near again later, and draws
    the tour riding backward over ground it already covered (Hörnli Trail's tail is exactly such a case).

    An earlier version advanced strictly one trail point per track point, which was too rigid -- the two are
    sampled at different effective speeds, so the pairing slowly lost sync and then failed a distance check
    while the tour was demonstrably still on the trail. That is what cut Hörnli Trail 404 m short of its own
    end on the E-bike tour: past the cut, the track sits 2-22 m from the trail with its matched vertex index
    climbing steadily (379 -> 385 -> 387 -> 399 -> 402 -> 408 -> 414), i.e. still riding it. Worth knowing WHY
    that spot is hard: Hörnli Trail and Älplisee Trail share their final 1297 m and end 42 m apart, so on that
    stretch the neighbouring trail is intermittently the closer of the two -- which a rigid lockstep walk
    cannot survive but a catch-up window can.
    """
    dense_by_trail = {t["id"]: densify(geo[t["id"]]) for t in trails if not t.get("loop")}
    rs = runs_of(labels)
    for i, (lab, a, b) in enumerate(rs):
        if lab is None or lab in lift_ids:
            continue
        tid = lab
        dense = dense_by_trail[tid]
        v_a, v_b = vertex_at(a, b), vertex_at(a, b, last=True)
        if v_a is None or v_b is None:
            continue
        fwd = v_b >= v_a

        if i < len(rs) - 1 and rs[i + 1][0] is None:
            _, _ca, cb = rs[i + 1]
            step = 1 if fwd else -1
            pos = _edge_dense_pos(dense, v_b, toward_larger=fwd)
            k = b + 1
            while k <= cb:
                if labels[k] is not None and labels[k] != tid:
                    break
                nxt = _advance(pts[k], dense, pos, step)
                if nxt is None:
                    break
                pos = nxt
                labels[k], vidx[k] = tid, dense[pos][2]
                k += 1

        if i > 0 and rs[i - 1][0] is None:
            _, ca, _cb = rs[i - 1]
            step = -1 if fwd else 1
            pos = _edge_dense_pos(dense, v_a, toward_larger=not fwd)
            k = a - 1
            while k >= ca:
                if labels[k] is not None and labels[k] != tid:
                    break
                nxt = _advance(pts[k], dense, pos, step)
                if nxt is None:
                    break
                pos = nxt
                labels[k], vidx[k] = tid, dense[pos][2]
                k -= 1


def match_components(track, trails, geo, lifts, verbose=True):
    """Label each point of `track` with the component trail it is riding, then find the lift rides.

    Returns a list of (kind, key, start, end) over `track`'s indices, where kind is "trail", "lift" or
    "connector" and `key` carries the trail/lift id plus, for a trail, the traversed vertex range.
    """
    pts = [(p[0], p[1]) for p in track]
    labels = [None] * len(pts)

    # LIFTS FIRST, over the whole track -- not inside the leftover connectors. In a bike park a trail runs
    # directly UNDER the gondola it is served by, so trail-matching first put a 130 m sliver of
    # "703 Rock'n'Roll" in the middle of the Känzeli–Brambrüesch ride, which split the cable run in two and
    # made both halves fail the 60% span test. The gondola then vanished into a grey connector.
    #
    # Doing it the other way round is safe because a lift ride is geometrically unmistakable: it follows the
    # cable from one station to the other, and it is STRAIGHT. The detour check is what separates it from an
    # uphill trail beneath the same cable -- that trail switchbacks, so its own length far exceeds the
    # straight-line span, while a cable ride's barely exceeds it at all.
    label_lifts(pts, labels, lifts)

    items = []
    for t in trails:
        if t.get("loop"):
            continue
        for lat, lon, idx in densify(geo[t["id"]]):
            items.append((lat, lon, t["id"], idx))
    g = grid_build(items)

    lift_ids = {l["id"] for l in lifts}
    vidx = []
    for k, (lat, lon, _) in enumerate(track):
        hit = None if labels[k] is not None else grid_nearest(g, lat, lon, MATCH_M)
        if hit:
            labels[k] = hit[1]
        vidx.append(hit[2] if hit else None)

    # despeckle: a run too short to be a ride is not one. Lift runs are exempt -- they already had to span
    # 60% of their cable to get here, and dropping one would put the gondola back into a connector.
    for lab, a, b in runs_of(labels):
        if lab is not None and lab not in lift_ids and run_len_m(pts, a, b) < MIN_RUN_M:
            for k in range(a, b + 1):
                labels[k] = None

    def vertex_at(a, b, last=False):
        """First (or last) matched trail vertex index within a run -- gap-fill leaves some points without."""
        span = vidx[a:b + 1]
        return next((v for v in (reversed(span) if last else span) if v is not None), None)

    # Gap-fill: the same trail either side of a short gap is one ride through a junction, not two.
    #
    # Two thresholds, because there are two different situations. Up to GAP_FILL_M it is enough that the same
    # trail is on both sides -- that is a junction or a few stray points. Up to MERGE_SAME_TRAIL_M it also has
    # to be the SAME CONTINUING ride: the tour must re-join the trail near where it left it, and travel the
    # same way. Without that second test a trail ridden twice from the top would be welded into one segment.
    #
    # This is what the user hit on the E-bike tour: the Hörnli Trail came out as three segments with 295 m and
    # 475 m connectors between them and the Weisshorn Trail as two with 480 m, because the tour's own recording
    # drifts more than MATCH_M off the trail there. The trails themselves are fine -- only the tour's stretches
    # were broken up, and the three overlapping clips also drew the Hörnli Trail 1.6x longer than it was
    # ridden. Merging them gives one clean stretch per ride.
    def merge_same_trail_gaps():
        changed = True
        while changed:
            changed = False
            rs = runs_of(labels)
            for i in range(1, len(rs) - 1):
                (lab, a, b) = rs[i]
                tid = rs[i - 1][0]
                if lab is not None or tid is None or tid != rs[i + 1][0] or tid in lift_ids:
                    continue
                gap = run_len_m(pts, a, b)
                if gap >= GAP_FILL_M:
                    left_out, right_in = vertex_at(*rs[i - 1][1:], last=True), vertex_at(*rs[i + 1][1:])
                    left_in, right_out = vertex_at(*rs[i - 1][1:]), vertex_at(*rs[i + 1][1:], last=True)
                    if None in (left_in, left_out, right_in, right_out):
                        continue
                    # Keeps going the same way along the trail -- a trail ridden twice from the top must not
                    # merge into one segment.
                    if (left_out >= left_in) != (right_out >= right_in):
                        continue
                    # How much TRAIL is missing between leaving it and re-joining it. This, not the ridden
                    # distance, is the size that matters: the user's Älplisee gaps had only 417 m and 340 m of
                    # trail missing while the tour covered 986 m and more going around them, so a
                    # ridden-distance limit rejected exactly the gaps that most obviously needed closing. Only
                    # a connector can sit between the two runs (a lift or another trail would be its own run
                    # and fail the `tid != rs[i+1][0]` test above), so a long ridden gap here just means the
                    # recording wandered off the trail and came back -- which is what we want to draw over.
                    lo, hi = sorted((left_out, right_in))
                    trail_gap = cumulative_km(geo[tid][lo:hi + 1])[-1] * 1000 if hi > lo else 0.0
                    if trail_gap > MAX_TRAIL_GAP_M and gap > MERGE_SAME_TRAIL_M:
                        continue
                for k in range(a, b + 1):
                    labels[k] = tid
                changed = True
                break

    # Runs BEFORE and AFTER the edge extension, deliberately. Before, it joins runs that are already close
    # enough. After matters just as much: extending both runs' edges shrinks the trail gap between them, and
    # a gap that was too wide to merge on the first pass can fall under the limit once the edges have grown.
    # That is exactly what kept Älplisee Trail's 417 m gap open in the black tour -- the merge test ran while
    # the two runs were still their un-extended, shorter selves.
    merge_same_trail_gaps()
    extend_trail_ends(pts, labels, vidx, trails, geo, lift_ids, vertex_at)
    merge_same_trail_gaps()

    out = []
    for lab, a, b in runs_of(labels):
        if lab is None:
            out.append(("connector", None, a, b))
        elif lab in lift_ids:
            out.append(("lift", lab, a, b))
        else:
            # Clip to where the tour ENTERED and LEFT the trail, not to min/max of every matched vertex:
            # one outlier match (a trail that loops back near itself, a junction touched in passing) widened
            # the range enough to inflate the substituted geometry by ~10% over the tour's own track, which
            # would draw the tour line running past the end of a trail it never rode that far on.
            # gap-fill assigns a label without a vertex index, so take the first/last index that has one.
            span = vidx[a:b + 1]
            first = next(v for v in span if v is not None)
            last = next(v for v in reversed(span) if v is not None)
            out.append(("trail", (lab, min(first, last), max(first, last), last >= first), a, b))
    return out


def build_tour(spec, trails, geo, lifts, verbose=True):
    """Returns (lineTrails entry, loop coords, profile, segments)."""
    raw = parse_gpx(io.open(os.path.join(MAT, spec["gpx"]), encoding="utf-8", errors="replace").read())
    pts = douglas_peucker(dedupe_points(raw))
    own = [[round(p[0], 6), round(p[1], 6)] for p in pts]
    own_ele = [p[2] if len(p) > 2 else None for p in pts]

    track = densify(own)
    parts = match_components(track, trails, geo, lifts, verbose=verbose)

    by_id = {t["id"]: t for t in trails}
    lift_by_id = {l["id"]: l for l in lifts}
    tpts = [(p[0], p[1]) for p in track]
    segs = []
    for kind, key, a, b in parts:
        # what the tour itself actually rode here, so the report can show substituted-vs-ridden length
        rode = run_len_m(tpts, a, b)
        if kind == "trail":
            tid, lo, hi, fwd = key
            coords = [list(c) for c in geo[tid][lo:hi + 1]]
            if not fwd:
                coords = coords[::-1]
            if len(coords) < 2:
                kind = "connector"          # an empty clip is left as an honest connector, never widened
            else:
                segs.append({"coords": coords, "trailId": tid, "_rode": rode})
                continue
        if kind == "lift":
            cable = [list(c) for c in lift_by_id[key]["coords"]]
            # orient the cable the way the tour travels it
            if haversine_m(track[a][:2], cable[-1]) < haversine_m(track[a][:2], cable[0]):
                cable = cable[::-1]
            segs.append({"coords": cable, "trailId": None, "liftId": key, "_rode": rode})
            continue
        # Connector: the tour's own line for exactly the stretch it rode, taken from the densified track and
        # simplified back down. NOT own[min(vertex):max(vertex)+2] as a first version did -- when the whole
        # stretch falls inside ONE long Douglas-Peucker edge of the tour's own track (a straight road, a
        # cable), min and max collapse to the same vertex and the slice then draws that entire edge: schwarz
        # got a 4384 m connector for 40 m of riding. Densify+simplify reproduces the original line, because
        # every densified point lies exactly on it.
        coords = [[round(p[0], 6), round(p[1], 6)]
                  for p in douglas_peucker([[t[0], t[1]] for t in track[a:b + 1]])]
        if len(coords) >= 2:
            segs.append({"coords": coords, "trailId": None, "_rode": rode})

    segs = [s for s in segs if len(s["coords"]) >= 2]
    # Adjacent segments share their boundary point, exactly like the existing loops: the joins between a
    # substituted trail/cable and the tour's own line are metres apart, and a shared point closes them with
    # a zero-length step that changes neither the length nor the profile.
    #
    # A join is only allowed to be that quiet while it IS a few metres. Anything longer is a straight line
    # drawn across the map where the tour never went -- a substituted clip that ended in the wrong place --
    # so it gets reported instead of disappearing into the geometry. (An e-bike-red join was 1144 m.)
    joins = []
    for i in range(1, len(segs)):
        prev_end = segs[i - 1]["coords"][-1]
        gap = haversine_m(prev_end, segs[i]["coords"][0])
        if segs[i]["coords"][0] != prev_end:
            segs[i]["coords"].insert(0, list(prev_end))
        if gap > MAX_QUIET_JOIN_M:
            joins.append((i, gap))

    loop_geo = [c for s in segs for c in s["coords"]]

    # The profile comes from the tour's OWN track, which is the only thing carrying elevation; its total
    # differs a little from the substituted geometry's, so the segment distances are rescaled onto it.
    prof, gain, loss = build_profile(own, own_ele)
    geo_total = cumulative_km(loop_geo)[-1]
    scale = (prof[-1][0] / geo_total) if geo_total else 1.0
    cum = cumulative_km(loop_geo)
    # Segment i occupies loop_geo[off : off+n], and because it repeats its predecessor's last point,
    # cum[off] == cum[off-1] -- so distEnd of one segment and distStart of the next come out equal, as they
    # do in the existing loops. Advancing by n-1 instead of n would drift by one point per segment.
    off = 0
    for s in segs:
        n = len(s["coords"])
        s["distStart"] = round(cum[off] * scale, 4)
        s["distEnd"] = round(cum[off + n - 1] * scale, 4)
        off += n
    length, up, down = spec["official"]
    entry = {"id": spec["id"], "name": spec["name"], "region": TOUR_REGION, "diff": spec["diff"],
             "len": length, "up": up, "down": down, "loop": True}

    if verbose:
        say("\n%s  (%s)" % (spec["name"], spec["id"]))
        say("   GPX %d raw -> %d points, own track %.2f km, profile %.2f km, geometry %.2f km "
            "(gain/loss from GPX %d/%d, official %d/%d)"
            % (len(raw), len(own), cumulative_km(own)[-1], prof[-1][0], geo_total, gain, loss, up, down))
        for s in segs:
            if s.get("liftId"):
                what = "LIFT  " + lift_by_id[s["liftId"]]["name"]
            elif s["trailId"]:
                what = "trail " + by_id[s["trailId"]]["name"]
            else:
                what = "~~~~~ Verbindung"
            # Substituted geometry against what the tour itself rode there. A ratio far from 1 means the clip
            # is drawing a stretch the tour never rode -- reported rather than quietly trimmed, because the
            # honest way to fix it is a better clip, not a silently shortened line.
            drawn = run_len_m([tuple(c) for c in s["coords"]], 0, len(s["coords"]) - 1)
            rode = s.pop("_rode", 0.0)
            ratio = (drawn / rode) if rode > 1 else 0.0
            mark = "  <-- %.2fx geritten" % ratio if ratio and (ratio > 1.3 or ratio < 0.75) else ""
            say("   %6.2f - %6.2f km  %-48s %5.0f m%s" % (s["distStart"], s["distEnd"], what, drawn, mark))
        for i, gap in joins:
            say("   !! Naht vor Segment %d: %.0f m Luftlinie ueberbrueckt" % (i, gap))
    for s in segs:
        s.pop("_rode", None)        # diagnostic only -- must not reach the region file
    return entry, loop_geo, prof, segs


# ---------------------------------------------------------------------------------------------------

def run():
    data = json.load(io.open(OUT, encoding="utf-8"))
    trails = [t for t in data["lineTrails"] if not t.get("loop")]
    geo = {k: v for k, v in data["trailGeo"].items() if k in {t["id"] for t in trails}}
    profs = {k: v for k, v in data["elevationProfiles"].items() if k in geo}

    lifts = build_lifts()
    report_lift_regions(lifts, trails, geo)

    line_trails = list(trails)
    segments = {}
    for spec in TOURS:
        entry, coords, prof, segs = build_tour(spec, trails, geo, lifts)
        line_trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof
        segments[entry["id"]] = segs

    out = write_region(OUT, line_trails, geo, profs, places=data.get("places") or [],
                       lifts=lifts, trail_segments=segments)
    say("\n%s" % region_summary(out))
    say("written: %s" % OUT)
    say("next: python tools/update_region_versions.py && python tools/validate_region.py bikekingdom")


def main():
    report = None
    if "--report" in sys.argv:
        report = sys.argv[sys.argv.index("--report") + 1]
    code = 0
    try:
        run()
    except BaseException:
        LOG.append("\n" + traceback.format_exc())
        code = 1
        traceback.print_exc()
    if report:
        io.open(report, "w", encoding="utf-8").write("\n".join(LOG) + "\n")
        print("report written: %s" % report)
    return code


if __name__ == "__main__":
    sys.exit(main())
