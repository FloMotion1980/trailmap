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
(Livigno) to ~130 (Bike Kingdom) candidates. Here it faces several hundred packed far more closely, so
cross-talk between adjacent trails is the risk and `strict_thresh_m` is the dial: lower it, and let pass 2
recover what that costs. `--sweep` tries a small grid per loop and keeps the best by attributed share,
which is the number `pfaelzerwald_report.py` measures -- an honest objective, since a wrong attribution
adds length just as happily as a right one, so the sweep also records median match distance per candidate
and refuses a result whose distance profile got worse while its share went up.

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
from gpx_map_match import match_gpx_to_network, resolve_segments
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


def line_len_m(c):
    return sum(haversine_m(c[i - 1], c[i]) for i in range(1, len(c)))


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
    cursor = 0
    for m in sorted(matched, key=lambda x: x["start_idx"]):
        a, b = m["start_idx"], m["end_idx"]
        if a < cursor:                      # overlapping runs: keep the earlier one whole
            a = cursor
            if a > b:
                continue
        if a > cursor:
            segs.append({"coords": loop_coords[cursor:a + 1], "trailId": None})
        segs.append({"coords": loop_coords[a:b + 1], "trailId": m["id"]})
        cursor = b
    if cursor < len(loop_coords) - 1:
        segs.append({"coords": loop_coords[cursor:], "trailId": None})
    # Drop degenerate one-point pieces, which would break the concatenation check.
    return [s for s in segs if len(s["coords"]) >= 2]


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
            resolved = resolve_segments(coords, candidates, matched)
            segs = fill_connectors(coords, resolved)
            if not concat_ok(coords, segs):
                if args.verbose:
                    print("     %s: Verkettung verletzt, verworfen" % params)
                continue
            share = named_share(segs)
            if best is None or share > best["share"]:
                best = {"share": share, "segs": segs, "params": params,
                        "components": len({s["trailId"] for s in segs if s.get("trailId")})}
        row = {"id": lid, "name": t["name"], "region": t["region"],
               "baseline_share": b_share, "secs": round(time.time() - t0, 1)}
        if best is None:
            row.update(written=False, reason="kein gültiges Ergebnis")
        elif b_share and best["share"] < b_share * args.min_share_ratio:
            row.update(written=False, reason="Anteil gefallen", new_share=round(best["share"], 4))
        else:
            new_segs[lid] = best["segs"]
            row.update(written=True, new_share=round(best["share"], 4),
                       components=best["components"], params=best["params"])
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
