# -*- coding: utf-8 -*-
"""Phase 4 of the Pfälzerwald rework: re-derive every Trailrunde's `trailSegments` from its own line.

    python tools/pfaelzerwald_rederive_loops.py --region-out pfaelzerwald.new.json --report rederive.json
    python tools/pfaelzerwald_rederive_loops.py --only tour_4_hochspeyer --verbose     # one loop, for tuning

Built to run unattended for hours, so it checkpoints after every loop and can resume.

**Why this needs no original GPX.** The obvious approach -- re-match each official tour's recorded GPX --
is impossible for 20 of the 42 loops: only the 12 Kurztouren, 4 of 5 Fernwege and the 5 private rounds have
a GPX under `Material/Pfälzer Wald/`, and the official "Tour 1-20" files were never kept. It is also
unnecessary. `trailGeo[loopId]` IS the tour's line, and `validate_region.py`'s own loop invariant
guarantees it equals the exact concatenation of the current `trailSegments` -- verified here before
anything is touched, for all 41 loops that have a breakdown. So the stored line is a faithful recording to
re-match, and using it has a property the original GPX does not: **the drawn line cannot move.** Only the
attribution of its stretches changes, which is exactly the scope of this rework and removes any risk of
"lost ground" between the old route and the new one.

That is also what makes the ID-repointing problem disappear. Replacing a component trail would otherwise
mean rewriting every `trailSegments` entry that references it -- 382 component ids across 41 loops, and
that repointing logic was never built. Re-deriving sidesteps it entirely: the segments are recomputed from
scratch against whatever trail set now exists.

**Tuning is expected, not optional.** `gpx_map_match.py` has been validated against networks of 21
(Livigno) to ~130 (Bike Kingdom) candidates. Here it faces 768 packed far more closely, so cross-talk
between adjacent trails is the risk: a looser threshold does not just find more, it finds WRONG things, and
a wrong attribution adds length to the share exactly as happily as a right one.

**That is why attributed share cannot be the selection objective, and why `--sweep` is off by default.**
The grid runs from a 15 m strict threshold down to 8 m, i.e. progressively stricter, so "keep whichever
scores highest" would systematically pick the loosest setting and call cross-talk an improvement -- the
opposite of the intent. The guard that actually works is per-segment and independent of the threshold:
`MAX_MATCH_MEDIAN_M` drops any matched stretch whose points sit further from the claimed trail's own line
than a real ride ever would, measured as a median so a few noisy points cannot condemn a good match nor a
few good ones rescue a bad one. `--sweep` therefore selects on share only AFTER that filter has run, and
the report records the median per loop so a suspicious result is visible rather than buried in a number
that went up.

**A connector stays a connector.** Where no candidate matches, the stretch is written with `trailId: null`
exactly as today. The user's decision was to replace conservatively, so a loop losing attribution relative
to the baseline is a regression to report, not a result to accept -- `--min-share-ratio` refuses to write a
loop whose share fell below that fraction of its baseline and leaves the old breakdown in place instead.
"""
import argparse
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# resolve_segments() gives each matched candidate's OWN stored geometry, clipped to the ridden range and
# oriented the way it was ridden. That is what a segment's `coords` must be, and a first version of this
# script got it wrong: it used slices of the LOOP's line instead, reasoning that keeping the drawn line
# untouched was the safer promise. It is not the app's design, and the user reported all three consequences
# from the live preview -- a component trail and the Tour's own stretch drawn as two slightly offset lines,
# a click landing on the trail instead of the Tour's segment, and the same ground stored twice with
# different geometry. Measured across the regions that were built correctly (Donnersberg, Bike Kingdom,
# Laax) 100% of segments sit 0.0 m from their trail's line; the slice-based version managed 56%.
# The consequence is accepted deliberately: the Tour's line now SHIFTS onto its component trails, by up to
# ~25 m on a named stretch. That shift is precisely what "same course as the trail" means.
from gpx_map_match import match_gpx_to_network, resolve_segments
from trailmap_pipeline import ElevationLookup, build_profile, cumulative_km, haversine_m, write_region

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = os.path.join(ROOT, "Trailmap App", "regions", "pfaelzerwald.json")

# Denser network than anything the matcher has been validated on, so the strict threshold leads the sweep.
SWEEP = [
    dict(strict_thresh_m=15.0, loose_thresh_m=35.0),
    dict(strict_thresh_m=12.0, loose_thresh_m=30.0),
    dict(strict_thresh_m=10.0, loose_thresh_m=26.0),
    dict(strict_thresh_m=8.0, loose_thresh_m=22.0),
]


def _utf8_stdout():
    """Force UTF-8 output, but only when run as a script.

    Doing this at import time breaks any importer: the test runner imports these tools to check their
    logic, the wrapper it installs replaces the runner's own stdout, and when that wrapper is collected it
    closes the underlying buffer -- the runner then dies with "I/O operation on closed file" AFTER its
    cases have already passed, which reads like a test failure rather than an import side effect.
    """
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


#: A matched stretch whose points sit further than this from the claimed trail's own line, in the median,
#: is cross-talk rather than a ride. The matcher labels individual points within its strict threshold, but
#: smoothing and run consolidation deliberately pull neighbouring points into a run, so a run as a whole can
#: drift well past that threshold -- which is exactly how a trail running parallel 30 m away gets claimed.
#:
#: Calibrated against the region's own 616 existing attributions, which turn out to be bimodal: 50% sit at
#: 0.0 m and 80% within 9.2 m, then the tail breaks down completely -- the 95th percentile is 181 m and the
#: worst is 827 m ("König-Albrecht-Wanderweg 1"). Roughly a tenth of the existing attributions are simply
#: wrong, claiming ground the named trail is nowhere near. 25 m keeps everything plausible and drops 9.7%,
#: i.e. almost exactly that broken tail. A first attempt at 12 m was miscalibrated in the other direction
#: and discarded 16%, including components the old data had right.
#:
#: The consequence for judging this rework: the 15.2% baseline is INFLATED by those wrong attributions, so
#: the honest comparison is against `attributed_share_clean` in pfaelzerwald_report.py, not the raw figure.
MAX_MATCH_MEDIAN_M = 25.0


def line_len_m(c):
    return sum(haversine_m(c[i - 1], c[i]) for i in range(1, len(c)))


def match_median_m(loop_coords, m, candidates):
    """Median distance from a matched stretch's own points to the candidate line it was matched to."""
    cand = candidates[m["id"]]
    ds = []
    for p in loop_coords[m["start_idx"]:m["end_idx"] + 1]:
        best = 1e9
        for q in cand:
            d = haversine_m(p, q)
            if d < best:
                best = d
        ds.append(best)
    ds.sort()
    return ds[len(ds) // 2] if ds else 1e9


def named_share(segments, loop_coords=None):
    """Share of the LOOP's length that falls on a named component trail.

    The denominator has to be the loop's own line, not the sum of the segment lengths. Those differ, and
    not slightly: the segments partition the loop's points half-open, so the step between one segment's
    last point and the next segment's first point is counted in neither. Over Kurztour 5's 15 segments that
    swallowed 1 301 m of 10 590 m -- 12% -- and dividing by the smaller figure inflated every share this
    script reported by about that much. Caught by comparing against pfaelzerwald_report.py, which always
    used the loop line and therefore measured baseline and result on the same basis; its numbers were the
    trustworthy ones all along.
    """
    tot = line_len_m(loop_coords) if loop_coords else sum(line_len_m(s["coords"]) for s in segments)
    named = sum(line_len_m(s["coords"]) for s in segments if s.get("trailId"))
    return named / (tot or 1.0)


def build_segments(loop_coords, matched, candidates):
    """Segments whose named stretches carry their TRAIL's geometry, and the loop line rebuilt from them.

    Returns (segments, new_loop_coords). A named stretch's coords come from `resolve_segments()`, i.e. they
    are an exact contiguous slice of that trail's own stored points (reversed if it was ridden the other
    way) -- so the Tour's stretch and the trail's own polyline coincide pixel-for-pixel, which is what makes
    the stretch clickable as part of the Tour and stops the two drawing as a doubled line. A connector keeps
    the loop's own recorded points, because no named trail describes that ground.

    The loop line is then the concatenation, which satisfies validate_region.py's loop invariant by
    construction. It is NOT the line that went in: on each named stretch it snaps onto the trail.
    """
    resolved = {(r["gpx_start_idx"], r["gpx_end_idx"]): r
                for r in resolve_segments(loop_coords, candidates, matched)}
    segs = []
    cursor = 0
    for m in sorted(matched, key=lambda x: x["start_idx"]):
        a, b = m["start_idx"], m["end_idx"]
        r = resolved.get((m["start_idx"], m["end_idx"]))
        if r is None or len(r["coords"]) < 2:
            continue
        if a < cursor:
            a = cursor
        if a > b:
            continue
        if a > cursor + 1:                     # a 1-point connector would draw nothing; drop it
            segs.append({"coords": [list(p) for p in loop_coords[cursor:a]], "trailId": None})
        segs.append({"coords": [list(p) for p in r["coords"]], "trailId": m["id"]})
        cursor = b + 1
    if cursor < len(loop_coords) - 1:
        segs.append({"coords": [list(p) for p in loop_coords[cursor:]], "trailId": None})
    new_line = [p for s in segs for p in s["coords"]]
    return add_dist_range(new_line, segs), new_line


def fill_connectors(loop_coords, matched):
    """Turn the matcher's matched stretches into a gapless segment list over the loop's own line.

    Every point of the loop must end up in exactly one segment and in the original order -- that is the
    invariant `validate_region.py` checks, and it is what lets the drawn line stay byte-identical.
    """
    segs = []
    cursor = 0                                  # first index not yet assigned to a segment
    for m in sorted(matched, key=lambda x: x["start_idx"]):
        a, b = m["start_idx"], m["end_idx"]
        if a < cursor:                          # overlapping runs: the earlier one keeps the shared part
            a = cursor
        if a > b or b < cursor:
            continue
        if a - cursor == 1:
            # A single leftover point would be a segment that draws nothing, and dropping it instead
            # would punch a hole in the partition. Absorb it into the stretch that follows.
            a = cursor
        elif a > cursor:
            segs.append({"coords": loop_coords[cursor:a], "trailId": None})
        segs.append({"coords": loop_coords[a:b + 1], "trailId": m["id"]})
        cursor = b + 1                          # HALF-OPEN: slices must not share an endpoint, or the
                                                # concatenation gains a duplicated point per joint
    if cursor < len(loop_coords):
        tail = loop_coords[cursor:]
        if len(tail) == 1 and segs:             # same absorption at the end of the line
            segs[-1]["coords"] = segs[-1]["coords"] + tail
        else:
            segs.append({"coords": tail, "trailId": None})
    return add_dist_range(loop_coords, segs)


def add_dist_range(loop_coords, segs):
    """Stamp each segment with `distStart`/`distEnd`, its span on the ELEVATION PROFILE's own km axis.

    Not optional, and leaving it out is not a silent omission -- it changes the info panel in two visible
    ways, both of which the user reported before this was traced (2026-08-14):

    * `buildInfoPanelHtml` builds the elevation chart's per-segment colour array from `TRAIL_SEGMENTS`
      **skipping any entry without `distStart`**. With none of them carrying it the array comes out empty
      and the chart falls back to one flat colour -- the Tour's own difficulty -- instead of showing each
      component trail's colour the way the map does.
    * A clicked segment's highlight is a `<rect>` spanning `[distStart, distEnd]`, so without the field
      there is nothing to highlight and the panel no longer extends with that stretch's own information.

    The values are simply the loop's cumulative distance at the segment's first and last point, which is
    what the existing region data contains, verified segment-for-segment against it. Consecutive segments
    are therefore NOT contiguous on this axis: the step across each joint belongs to no segment, exactly as
    before, which is why the chart has always had thin uncoloured slivers at the joins.
    """
    cum = cumulative_km(loop_coords)
    idx = 0
    for s in segs:
        first = idx
        last = idx + len(s["coords"]) - 1
        s["distStart"] = round(cum[first], 3)
        s["distEnd"] = round(cum[last], 3)
        idx = last + 1
    return segs


def shift_m(before, after):
    """Median distance from the rebuilt line's points to the original recording -- how far the Tour moved."""
    ds = sorted(min(haversine_m(p, q) for q in before) for p in after[::5])
    return ds[len(ds) // 2] if ds else 0.0


def concat_ok(loop_coords, segs):
    return [p for s in segs for p in s["coords"]] == loop_coords


def main():
    _utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=REGION)
    ap.add_argument("--region-out")
    ap.add_argument("--report", default="rederive.json")
    ap.add_argument("--baseline", default=os.path.join(ROOT, "Material", "Pfälzer Wald", "rework",
                                                       "baseline.json"))
    ap.add_argument("--only", action="append")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--min-share-ratio", type=float, default=0.9)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    d = json.load(open(args.region, encoding="utf-8"))
    geo = d["trailGeo"]
    old_segs = d.get("trailSegments", {})
    loops = [t for t in d["lineTrails"] if t.get("loop")]
    if args.only:
        loops = [t for t in loops if t["id"] in set(args.only)]

    base = {}
    if os.path.exists(args.baseline):
        base = {r["id"]: r for r in json.load(open(args.baseline, encoding="utf-8"))["loops"]}

    # Candidates: every non-loop trail. A loop must never be offered as a candidate for another loop --
    # a Tour is stored in lineTrails like any real trail, and an early version of the matcher's own test
    # harness let one tour's line match a different tour in the same region.
    candidates = {t["id"]: geo[t["id"]] for t in d["lineTrails"] if not t.get("loop")}
    print("Kandidaten: %d Einzeltrails, %d Trailrunden neu herzuleiten" % (len(candidates), len(loops)))

    ele = ElevationLookup(os.path.join(ROOT, "Material", "elevation_cache.json"))
    report, new_segs = [], dict(old_segs)
    new_geo, new_profs = dict(geo), dict(d["elevationProfiles"])
    for i, t in enumerate(loops, 1):
        lid = t["id"]
        coords = geo[lid]
        if lid in old_segs and not concat_ok(coords, old_segs[lid]):
            print("  !! %s: bestehende Segmente sind keine exakte Verkettung -- übersprungen" % lid)
            continue
        b_share = base.get(lid, {}).get("share")
        t0 = time.time()
        best = None
        for params in (SWEEP if args.sweep else SWEEP[:1]):
            matched = match_gpx_to_network(coords, candidates, **params)
            meds = [(m, match_median_m(coords, m, candidates)) for m in matched]
            kept = [m for m, md in meds if md <= MAX_MATCH_MEDIAN_M]
            dropped = [(m["id"], round(md)) for m, md in meds if md > MAX_MATCH_MEDIAN_M]
            if args.verbose and dropped:
                print("     %s: %d Treffer wegen Abstand verworfen: %s"
                      % (params, len(dropped), dropped[:6]))
            segs, new_line = build_segments(coords, kept, candidates)
            if not concat_ok(new_line, segs):
                if args.verbose:
                    print("     %s: Verkettung verletzt, verworfen" % params)
                continue
            share = named_share(segs, new_line)
            if best is None or share > best["share"]:
                best = {"share": share, "segs": segs, "line": new_line, "params": params,
                        "components": len({s["trailId"] for s in segs if s.get("trailId")}),
                        "median_m": round(max([md for _, md in meds if md <= MAX_MATCH_MEDIAN_M] or [0]), 1),
                        "dropped": len(dropped)}
        row = {"id": lid, "name": t["name"], "region": t["region"],
               "baseline_share": b_share, "secs": round(time.time() - t0, 1)}
        if best is None:
            row.update(written=False, reason="kein gültiges Ergebnis")
        elif b_share and best["share"] < b_share * args.min_share_ratio:
            row.update(written=False, reason="Anteil gefallen", new_share=round(best["share"], 4))
        else:
            new_segs[lid] = best["segs"]
            # The loop's own line and profile are rebuilt too, because the named stretches now follow their
            # trails rather than the recording. Leaving the old profile in place would misalign the chart's
            # x-axis against the new line -- and the segment highlight rides that same axis.
            new_geo[lid] = best["line"]
            elevs = ele([[p[0], p[1]] for p in best["line"]])
            prof, gain, loss = build_profile(best["line"], elevs)
            new_profs[lid] = prof
            row.update(written=True, new_share=round(best["share"], 4),
                       line_shift_m=round(shift_m(coords, best["line"]), 1),
                       new_km=round(cumulative_km(best["line"])[-1], 2),
                       components=best["components"], params=best["params"],
                       worst_median_m=best["median_m"], dropped_matches=best["dropped"])
        report.append(row)
        print("  [%2d/%2d] %-38s %s  %5.1f%% -> %5.1f%%  %4.0fs%s"
              % (i, len(loops), t["name"][:38], "ok " if row.get("written") else "SKIP",
                 100 * (b_share or 0), 100 * row.get("new_share", 0), row["secs"],
                 "" if row.get("written") else "  (%s)" % row.get("reason")))
        json.dump(report, open(args.report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if args.region_out:
        write_region(args.region_out, d["lineTrails"], new_geo, new_profs,
                     places=d.get("places"), lifts=d.get("lifts"), trail_segments=new_segs)
        print("geschrieben: %s" % args.region_out)
    wrote = sum(1 for r in report if r.get("written"))
    print("%d von %d Trailrunden neu hergeleitet, Bericht: %s" % (wrote, len(report), args.report))


if __name__ == "__main__":
    main()
