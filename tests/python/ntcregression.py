# -*- coding: utf-8 -*-
"""
@suite   ntcregression
@area    nearbyTrailConnector: what the procedure actually achieves on three real tours
@files   tools/nearby_trail_connector.py, tools/make_ntc_fixture.py, tests/fixtures/ntc_baseline.json
@touches solve, close_gaps, merge_roads, score, off_way_core, MAX_TRIM_FACTOR, MAX_BRIDGE_FACTOR, MAX_SEG_TRIM_FRACTION, MIN_SEG_POINTS, OFF_TOL_M, ON_WAY_M, MEET_M, OVERLAP_M, MIN_OVERLAP_M

This suite exists because the procedure degraded silently, twice, and both times the degradation was invisible
until a rider looked at the map.

`MAX_TRIM_FACTOR` was introduced at 3.0 in the same commit that first checked the tool in -- AFTER Rodalben
Felsentrails had already been closed with it. Two of that tour's confirmed solutions need factor 6.6, so from
that commit on the tool could no longer produce them, and nobody noticed for four days: the tour was already
closed in the region file, so nothing on screen changed. It only surfaced when the user asked why those two
gaps were suddenly being reported as unclosable.

The second one shipped. The proportionality limit measured trimming against the GAP only, so a 133m gap was
allowed to cut 242m -- and "Steps Heidenfelsen" happened to be exactly 242m long, so a whole named trail
section dissolved into a single point. The user found it on the map ("ist das Stueck hier kaputt gegangen").

Both are the same class of failure: the procedure keeps reporting success while producing worse routes. A
comparison against the region FILE cannot catch it either, because the file holds the old, already-good
result -- which is why this suite re-runs the procedure from each tour's pre-closure state instead.

**Rodalben Felsentrails is the required tour** (user, 2026-08-20: "grade die Rodalben Felsentrails sollten
herangezogen werden, denn da sind viele Faelle aufgefallen"). Landstuhl (Ost) is the second, because every
change made on 2026-08-20 came out of it: the overlap case, the per-segment trim limit, merging as an extra
candidate rather than a replacement, and one shared off-way threshold.

Two things about it are deliberate and easy to get wrong if this is ever rewritten:

* **It calls `close_gaps()` from the tool, not a copy of its loop.** The acceptance rules -- the off-way gate
  and the proportionality check -- are themselves part of what can regress, so the test has to execute exactly
  those, not a reimplementation that would keep passing after they changed.
* **The OSM ways ship with the fixture and are the provably identical set.** `tools/make_ntc_fixture.py`
  keeps the union of the per-gap bounding boxes that `fetch()` itself uses, so the way set is the same one a
  networked run sees. A test that needed Overpass would never be run, and a fixture trimmed by "near the
  tour" would quietly be testing a different input.

**The third tour, Landstuhl (West), is in for exactly one gap.** Its `seg10` is the only place in any of the
three where `OFF_TOL_M` decides anything -- measured, not assumed: with the first two tours alone,
`NTC_OFF_TOL_M=0` left this suite completely green.

Coverage gaps, stated rather than papered over:

* **Case 4 (projection) is not exercised.** It fired twice in the original Felsentrails session and in none of
  the thirteen tours closed since -- under the current procedure both of those gaps go through case 1. So
  `PROJ_MAX_MEAN_M`, `PROJ_MIN_RATIO`, `PROJ_MIN_SECOND_M` and `PROJ_NO_BRANCH_M` stay unpinned; overriding
  any of them changes nothing here.
* **`MAX_TRIM_FACTOR` is only pinned from below.** Nothing in these tours trims between factor 3 and 7, so
  tightening to 3 or loosening to 7 is invisible; 1.5 bites. Worth knowing why loosening cannot help: the one
  solution that needs a bigger limit, Felsentrails `seg0`, needs trim factor 6.6 AND bridge factor 6.9, so
  raising either alone leaves it rejected by the other.
* **`MEET_M` and `OFF_TOL_M` are pinned coarsely** -- 20 -> 8 and 0.5 -> 0 fail, 20 -> 15 and 0.5 -> 20 do not.

If a change to the procedure is intended, regenerate the baseline with
`python tools/make_ntc_fixture.py --baseline` and read the diff -- that diff IS the review. A shrinking
`closed` count or a shrinking `trail_m` entry is the signal this suite was written for.

Verified by mutation (2026-08-20), all through `NTC_*` overrides so no source edit is needed. Baseline is
12 cases / 39 checks; the column is how many cases each mutation breaks:

| mutation | cases failing |
|---|---|
| `ON_WAY_M` 20 -> 15 (the threshold two real cases missed by 0.2m and 0.9m) | 7 |
| the `break` back in case 1 (`NTC_CASE1_FIRST_ONLY=1`) | 7 |
| merging replaces the unmerged candidates again (`NTC_MERGE_ONLY=1`) | 6 |
| `MIN_SEG_POINTS` 2 -> 99 | 4 |
| `MAX_SEG_TRIM_FRACTION` 0.5 -> 99 (the "Steps Heidenfelsen" bug) | 3 |
| `OFF_TOL_M` 0.5 -> 0 | 2 |
| `MEET_M` 20 -> 8 | 2 |
| `MAX_TRIM_FACTOR` 4 -> 1.5 | 2 |
| `MAX_BRIDGE_FACTOR` 6 -> 3 | 2 |
| `OVERLAP_M` 20 -> 1 | 2 |
| `MIN_OVERLAP_M` 25 -> 200 | 2 |

One claim in the first version of this table was wrong and is worth remembering: it asserted that
`MAX_TRIM_FACTOR` 4 -> 3 would stop Landstuhl's `seg17` from closing. That gap trims 196m over 92m, i.e.
factor 2.1, so nothing happened -- a reminder that a mutation table has to be run, not reasoned about.

"""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(ROOT, "tools")
FIX = os.path.join(ROOT, "tests", "fixtures")


def _load(name):
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(t):
    fixture = _load("make_ntc_fixture")
    ntc = _load("nearby_trail_connector")
    with open(os.path.join(FIX, "ntc_baseline.json"), encoding="utf-8") as fh:
        base = json.load(fh)

    for loop in sorted(base):
        want = base[loop]
        got = fixture.run_fixture(loop)
        short = loop.replace("pw_", "")

        t.case("%s: the procedure still closes what it closed before" % short)
        t.eq("gaps in the pre-closure state", got["gaps"], want["gaps"])
        t.eq("gaps closed", got["closed"], want["closed"])
        t.eq("gaps left open (metres)", got["still_open"], want["still_open"])
        t.eq("segments afterwards", got["segments"], want["segments"])
        # A metre of tolerance here would hide exactly the drift this suite is for.
        t.eq("total length (m)", got["length_m"], want["length_m"])

        t.case("%s: the same cases in the same places" % short)
        t.eq("case distribution", got["cases"], want["cases"])
        wrong = [(g["seg"], g["applied"], w["applied"]) for g, w in zip(got["per_gap"], want["per_gap"])
                 if g["applied"] != w["applied"]]
        t.eq("every gap resolved by the same case", wrong, [])
        moved = [(g["seg"], g["bridge"], w["bridge"]) for g, w in zip(got["per_gap"], want["per_gap"])
                 if g["bridge"] != w["bridge"]]
        t.eq("every bridge the same length", moved, [])
        cut = [(g["seg"], g["trim"], w["trim"]) for g, w in zip(got["per_gap"], want["per_gap"])
               if g["trim"] != w["trim"]]
        t.eq("every trim the same", cut, [])

        t.case("%s: no named trail section loses more than it did" % short)
        worse = {k: (v, want["trail_m"].get(k)) for k, v in got["trail_m"].items()
                 if want["trail_m"].get(k) is not None and v < want["trail_m"][k]}
        t.eq("no section shorter than the baseline", worse, {})
        t.eq("no section disappeared", sorted(got["trail_m"]), sorted(want["trail_m"]))

        # This case deliberately does NOT read the baseline. It is the invariant the "Steps Heidenfelsen" bug
        # broke, and it has to hold even if somebody regenerates the baseline while the bug is present --
        # which is exactly how a golden-file test can be talked into blessing a regression.
        t.case("%s: a repair may never dissolve a trail section" % short)
        fx = fixture.load(loop)
        full = {}
        for seg in fx["segments"]:
            if seg.get("trailId"):
                k = fx["names"].get(seg["trailId"], seg["trailId"])
                full[k] = full.get(k, 0) + ntc.C.line_len_m([list(q) for q in seg["coords"]])
        gone = sorted(k for k in full if got["trail_m"].get(k, 0) < 1)
        t.eq("nothing trimmed to nothing", gone, [])
        halved = sorted(k for k, v in full.items() if got["trail_m"].get(k, 0) < 0.5 * v - 1)
        t.eq("nothing trimmed below half its own length", halved, [])
