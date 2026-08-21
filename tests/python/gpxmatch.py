# -*- coding: utf-8 -*-
"""
@suite   gpxmatch
@area    Sequential GPX map-matching against a region's own trails and lifts
@files   tools/gpx_map_match.py, tools/test_gpx_map_match.py, tools/gpx_map_match_baseline.json
@touches match_gpx_to_network, resolve_segments, closest_point_on_polyline, strict_thresh_m, CASES, BASELINE

SLOW (~40 s) and deliberately NOT `@always`: it is selected only when the matcher or its own harness
changes, which is exactly when its answer is worth waiting for.

**It runs five of the harness's ten cases, and which five is measured, not arbitrary.** Timed per case:
Livigno 24 s, Waldmeister 3 s, the three Naheland tours 3 s each — against **over two minutes each** for the
four Bike Kingdom tours and the 100 km Portes du Soleil one, which match a long recording against a whole
dense region. The full ten-case run takes well over twenty minutes, which is not a suite anybody will run;
those five are a manual `python tools/test_gpx_map_match.py` away and the committed baseline covers all ten,
so a manual run compares against the same numbers. The fast five still include the strongest ground truth
there is (Livigno's Tutti Frutti, hand-assembled by the user in the Tourenbuilder).

`tools/test_gpx_map_match.py` has been the matcher's regression harness since it was written, over ten tours
this app has already built (one of them hand-assembled by the user in the Tourenbuilder, the strongest
ground truth available). But **it always exited 0**: it printed a per-case comparison and left the reading
of it to a human, which for an automated runner is indistinguishable from passing — the exact failure mode
tests/README.md warns about, sitting in the repo unnoticed because no suite claimed the file. It now
compares each case against a committed per-case baseline and exits 1 when one scores below it (a score going
UP is reported as an improvement, not a failure, so the baseline is refreshed deliberately).

This suite is deliberately thin: it shells out rather than importing, because the harness's value is its
output and because a case that throws mid-way should be reported as one failure with its own text rather
than aborting a Python suite.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS = os.path.join(ROOT, "tools", "test_gpx_map_match.py")
BASELINE = os.path.join(ROOT, "tools", "gpx_map_match_baseline.json")
#: See the header: the other five cases are minutes each, and a suite nobody runs proves nothing.
FAST_CASES = ["livigno", "waldmeister", "naheland_flow", "naheland_panorama", "naheland_enduro"]


def run(t):
    t.case("the matcher's own regression harness is present, and can fail")
    t.ok("the harness exists", os.path.exists(HARNESS), os.path.exists(HARNESS), True)
    src = open(HARNESS, encoding="utf-8").read()
    t.ok("it compares against a baseline rather than only printing", "BASELINE" in src, True, True)
    t.ok("and it exits non-zero when a case regresses", "sys.exit(1)" in src, True, True)
    # It used to carry an absolute D:\Trailmap for both its sys.path entry and its ROOT, which makes it
    # unrunnable anywhere else -- and the reason this plan lives in the repo at all is that it has to
    # survive a device change.
    # Comment lines stripped first: this file's own note ABOUT the old hardcoded path is not the path, and
    # the first version of this check failed on the harness's own documentation of the fix.
    code = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
    t.eq("no absolute machine path is baked into the code",
         [ln.strip() for ln in code.splitlines() if "D:\\Trailmap" in ln], [])
    t.ok("a baseline has been recorded", os.path.exists(BASELINE), os.path.exists(BASELINE), True)

    t.case("no tour matches worse than its recorded baseline")
    p = subprocess.run([sys.executable, HARNESS] + FAST_CASES,
                       capture_output=True, text=True, cwd=ROOT, timeout=600)
    tail = "\n".join([ln for ln in (p.stdout or "").splitlines()
                      if ln.startswith(("REGRESSED", "IMPROVED", "NO BASELINE", "OK:", "==="))][-12:])
    t.eq("the harness exits clean", p.returncode, 0)
    t.ok("...and says so", "OK:" in (p.stdout or ""), tail or (p.stderr or "")[-400:], "OK: ...")
