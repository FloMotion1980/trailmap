# -*- coding: utf-8 -*-
"""
@suite   runner
@area    The test runner's own suite selection (--changed) and header parsing
@always
@files   tests/run.py
@touches select, parse_header, SYMBOL_HOMES, _symbol_searchable

A suite that never runs is indistinguishable from a suite that passes, so the rule deciding WHICH suites run is
worth checking as much as the suites themselves. It is not hypothetical: `@touches` is a search for the app's own
identifiers, and for a whole day it was applied to every claimed file including `style.css` -- where such an
identifier cannot appear. A CSS-only edit therefore selected nothing but the two @always Python suites, and the
region-frame colour change on 2026-08-02 went in with none of the three suites that claim that file. The cases
below pin both halves of the rule: a symbol-bearing file still needs its symbol, an opaque file does not.

Deliberately checks `select()` against HAND-WRITTEN suite dicts rather than the real ones. The real headers
change; the rule should not have to be re-verified every time one does.
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import run as runner  # noqa: E402  (the path has to be set up first)


CSS = "Trailmap App/style.css"
HTML = "Trailmap App/index.html"
ROTATE = "Trailmap App/leaflet-rotate.js"


def suite(name, files, touches=(), always=False):
    return {"suite": name, "files": list(files), "touches": list(touches),
            "always": always, "standalone": False, "kind": "browser", "path": name + ".js"}


def picked(suites, changed, diff):
    chosen, reasons, gaps = runner.select(suites, set(changed), diff)
    return sorted(s["suite"] for s in chosen), reasons, gaps


def run(t):
    labels = suite("labels", [HTML, CSS], ["applyNameLabels", "setLabelHovered"])
    solo = suite("solo", [HTML], ["applySolo", "clearSolo"])
    always = suite("regiondata", ["regions/*.json"], always=True)
    all_three = [labels, solo, always]

    t.case("a stylesheet change selects every suite that claims it")
    # No @touches symbol appears in this diff, and that is the whole point: none could.
    names, reasons, _ = picked(all_three, [CSS], "-  border: 1.5px solid var(--forest);\n+  border: 1.5px solid #e3e6da;")
    t.eq("labels is selected", "labels" in names, True)
    t.eq("solo is not (it does not claim the stylesheet)", "solo" in names, False)
    t.eq("the @always suite still runs", "regiondata" in names, True)
    t.ok("and the reason says why", "no @touches symbol" in reasons.get("labels", ""),
         reasons.get("labels"), "names the file and the reason")

    t.case("a vendored library is opaque in the same way")
    bearing = suite("bearing", [HTML, CSS, ROTATE], ["applyMapBearing", "setHeadingUp"])
    names, reasons, _ = picked([bearing, solo], [ROTATE], "+  L.Map.include({ setBearing: function () {} });")
    t.eq("bearing is selected", "bearing" in names, True)
    t.ok("for the file, not for a symbol", "no @touches symbol" in reasons.get("bearing", ""),
         reasons.get("bearing"), "opaque-file reason")

    t.case("but index.html still needs one of the suite's own symbols")
    # The gate that keeps a one-line HTML edit from running all thirteen suites has to survive the change above.
    names, _, _ = picked(all_three, [HTML], "-      <div id=\"x\">a</div>\n+      <div id=\"x\">b</div>")
    t.eq("labels sits it out", "labels" in names, False)
    t.eq("so does solo", "solo" in names, False)
    names, _, _ = picked(all_three, [HTML], "+  applySolo(id);")
    t.eq("and runs when its symbol is there", "solo" in names, True)
    t.eq("while the other one still does not", "labels" in names, False)

    t.case("a suite with no @touches at all runs on any of its files")
    bare = suite("bare", [HTML])
    names, _, _ = picked([bare], [HTML], "+ anything")
    t.eq("selected", names, ["bare"])

    t.case("a changed file no suite claims is still reported as a GAP")
    # The other half of the contract: silence about an unwatched file would read as a green run.
    _, _, gaps = picked(all_three, ["Trailmap App/sw.js"], "+ const CACHE_NAME = 'x';")
    t.eq("sw.js is reported", gaps, ["Trailmap App/sw.js"])
    _, _, gaps = picked(all_three, [CSS, "docs/notes.md", "CLAUDE.md", "tests/browser/labels.js"], "+ x")
    t.eq("a claimed file is not a gap, and docs/tests/CLAUDE.md never are", gaps, [])

    t.case("the real suites' headers still parse, and style.css is claimed by more than one")
    real = runner.discover()
    t.ok("every suite has a name and at least one @files or @always",
         all(s["suite"] and (s["files"] or s["always"]) for s in real),
         [s["suite"] for s in real if not (s["files"] or s["always"])], "none unclaimed")
    css_claimers = [s["suite"] for s in real if CSS in s["files"]]
    t.ok("style.css is watched", len(css_claimers) >= 3, sorted(css_claimers), ">= 3 suites")
    # @always suites are excluded on both sides: they run whatever changed, so they say nothing about the rule
    # under test. Comparing a filtered selection against an unfiltered expectation is what the first version of
    # this check did, and it failed on `appshell`, which claims the stylesheet AND is @always.
    selectable = [s for s in real if not s["always"]]
    expected = sorted(s["suite"] for s in selectable if CSS in s["files"])
    names, _, _ = picked(selectable, [CSS], "+  color: #e3e6da;")
    t.ok("and a CSS-only change now selects every one of them", sorted(names) == expected, sorted(names), expected)
