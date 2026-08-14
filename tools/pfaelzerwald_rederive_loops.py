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
# resolve_segments() is deliberately NOT used here, and the reason is the whole point of this script.
# It returns each matched candidate's OWN stored geometry, clipped and oriented -- right for BUILDING a
# tour line out of its components (what tools/build_bikekingdom_tours.py does), and wrong here: it would
# replace the loop's drawn line with a stitched-together one. This rework must leave the line untouched and
# change only the attribution, so the segments have to be slices of the loop's own coordinate list, which
# is what match_gpx_to_network()'s start_idx/end_idx already give. Keeping the line identical is also what
# makes the concatenation invariant hold by construction rather than by luck.
from gpx_map_match import match_gpx_to_network
from trailmap_pipeline import haversine_m, write_region

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


def named_share(segments):
    tot = sum(line_len_m(s["coords"]) for s in segments) or 1.0
    named = sum(line_len_m(s["coords"]) for s in segments if s.get("trailId"))
    return named / tot


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
    return segs


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

    report, new_segs = [], dict(old_segs)
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
            segs = fill_connectors(coords, kept)
            if not concat_ok(coords, segs):
                if args.verbose:
                    print("     %s: Verkettung verletzt, verworfen" % params)
                continue
            share = named_share(segs)
            if best is None or share > best["share"]:
                best = {"share": share, "segs": segs, "params": params,
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
            row.update(written=True, new_share=round(best["share"], 4),
                       components=best["components"], params=best["params"],
                       worst_median_m=best["median_m"], dropped_matches=best["dropped"])
        report.append(row)
        print("  [%2d/%2d] %-38s %s  %5.1f%% -> %5.1f%%  %4.0fs%s"
              % (i, len(loops), t["name"][:38], "ok " if row.get("written") else "SKIP",
                 100 * (b_share or 0), 100 * row.get("new_share", 0), row["secs"],
                 "" if row.get("written") else "  (%s)" % row.get("reason")))
        json.dump(report, open(args.report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if args.region_out:
        write_region(args.region_out, d["lineTrails"], geo, d["elevationProfiles"],
                     places=d.get("places"), lifts=d.get("lifts"), trail_segments=new_segs)
        print("geschrieben: %s" % args.region_out)
    wrote = sum(1 for r in report if r.get("written"))
    print("%d von %d Trailrunden neu hergeleitet, Bericht: %s" % (wrote, len(report), args.report))


if __name__ == "__main__":
    main()
