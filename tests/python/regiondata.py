# -*- coding: utf-8 -*-
"""
@suite   regiondata
@area    Region JSON files, the catalog and the version manifest
@always
@files   Trailmap App/regions/*.json, Trailmap App/index.html, tools/validate_region.py, tools/update_region_versions.py
@touches REGION_CATALOG, trailCount, subRegions, bounds

Runs for every change, because it is fast and because it guards the two mistakes that reach a phone silently:
a region edited without bumping its hash in version.json (the app fetches `regions/<key>.json?v=<hash>` and
the service worker serves that cache-first, so the hash is the ONLY thing that invalidates it), and a region
missing from the manifest entirely (then the URL is unversioned and stays cached forever). Both had already
happened once before the validator learned to check them.

This suite deliberately does not re-implement `tools/validate_region.py` -- it calls it, for every region in
the catalog, and additionally proves the validator still bites by handing it a deliberately broken copy.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(ROOT, "Trailmap App")
REGIONS = os.path.join(APP, "regions")
TOOLS = os.path.join(ROOT, "tools")


def catalog_keys():
    """The region keys the app itself declares, read from index.html rather than from the folder listing --
    a file nobody references is a different problem from a reference with no file, and both should show up."""
    src = io.open(os.path.join(APP, "index.html"), encoding="utf-8").read()
    start = src.index("const REGION_CATALOG")
    body = src[start:src.index("\n};", start)]
    return re.findall(r'file:\s*"regions/([a-z0-9_]+)\.json"', body), body


def run(t):
    keys, catalog_body = catalog_keys()

    t.case("the catalog and the regions folder agree")
    on_disk = sorted(f[:-5] for f in os.listdir(REGIONS) if f.endswith(".json") and f != "version.json")
    t.eq("every catalog entry has a file", sorted(set(keys) - set(on_disk)), [])
    t.eq("every file is referenced by the catalog", sorted(set(on_disk) - set(keys)), [])

    t.case("version.json lists every region with its current hash")
    import update_region_versions as urv
    manifest_path = os.path.join(REGIONS, urv.MANIFEST)
    manifest = json.load(io.open(manifest_path, encoding="utf-8"))
    missing = [k for k in on_disk if k not in manifest]
    t.eq("no region is absent from the manifest", missing, [])
    stale = []
    for k in on_disk:
        if k in manifest and manifest[k] != urv.file_hash(os.path.join(REGIONS, k + ".json")):
            stale.append(k)
    # This is the one that silently strands an edit on a device that already has the region.
    t.eq("no hash is stale (run tools/update_region_versions.py)", stale, [])
    t.eq("nothing extra in the manifest", sorted(set(manifest) - set(on_disk)), [])

    t.case("validate_region passes for every region in the catalog")
    failures = []
    for key in keys:
        out = subprocess.run([sys.executable, os.path.join(TOOLS, "validate_region.py"), key],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        if out.returncode != 0:
            failures.append("%s: %s" % (key, (out.stdout + out.stderr).strip().splitlines()[-1:]))
    t.eq("all clean", failures, [])

    t.case("validate_region still bites: a broken copy must fail")
    # Without this, "all clean" above could mean the validator has quietly stopped checking anything.
    key = keys[0]
    src = os.path.join(REGIONS, key + ".json")
    backup = io.open(src, encoding="utf-8").read()
    data = json.loads(backup)
    broke = None
    try:
        # Orphan a geometry entry: a trailGeo key with no matching lineTrails entry. Cheap, reversible, and
        # exactly the class of mistake a hand-edit makes.
        data["trailGeo"]["__test_orphan__"] = [[47.0, 10.0], [47.001, 10.001]]
        io.open(src, "w", encoding="utf-8", newline="\n").write(json.dumps(data, ensure_ascii=False))
        out = subprocess.run([sys.executable, os.path.join(TOOLS, "validate_region.py"), key],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        broke = out.returncode
        said = "orphan" in (out.stdout + out.stderr).lower() or "__test_orphan__" in (out.stdout + out.stderr)
    finally:
        io.open(src, "w", encoding="utf-8", newline="\n").write(backup)
    t.ok("non-zero exit on an orphaned geometry", broke not in (0, None), broke, "non-zero")
    t.ok("and it says what it found", said, said, True)
    t.eq("the region file was restored", io.open(src, encoding="utf-8").read(), backup)

    t.case("every trailCount in the catalog matches its region file")
    counts = dict(re.findall(r'file:\s*"regions/([a-z0-9_]+)\.json",\s*\n?\s*trailCount:\s*(\d+)', catalog_body))
    if not counts:      # the fields may be on one line in either order; fall back to a per-entry scan
        for entry in re.finditer(r'file:\s*"regions/([a-z0-9_]+)\.json"([\s\S]{0,400}?)(?=\n  [a-z]|\Z)', catalog_body):
            m = re.search(r"trailCount:\s*(\d+)", entry.group(2))
            if m:
                counts[entry.group(1)] = m.group(1)
    wrong = []
    for key, declared in counts.items():
        data = json.load(io.open(os.path.join(REGIONS, key + ".json"), encoding="utf-8"))
        actual = len(data["lineTrails"])
        if int(declared) != actual:
            wrong.append("%s: catalog says %s, file has %d" % (key, declared, actual))
    t.ok("at least most entries were found to check", len(counts) >= max(1, len(keys) - 2), len(counts), len(keys))
    t.eq("all counts agree", wrong, [])

    t.case("every sub-region a trail claims exists in the catalog, and none is unused")
    problems = []
    for key in keys:
        block = re.search(r'file:\s*"regions/%s\.json"([\s\S]*?)\n  \},' % key, catalog_body)
        if not block:
            continue
        declared = set(re.findall(r'\n\s+([a-z0-9_]+):\s*\{\s*label:', block.group(1)))
        data = json.load(io.open(os.path.join(REGIONS, key + ".json"), encoding="utf-8"))
        used = {e["region"] for e in data["lineTrails"]} | {l["region"] for l in data.get("lifts", [])}
        if declared and used - declared:
            problems.append("%s: used but not declared: %s" % (key, sorted(used - declared)))
        if declared and declared - used:
            problems.append("%s: declared but unused: %s" % (key, sorted(declared - used)))
    t.eq("sub-region keys line up both ways", problems, [])

    t.case("no region reintroduced the url field")
    # The loop-concatenation invariant deliberately is NOT re-implemented here: validate_region owns it and
    # the case above runs the validator over every region in the catalog. Two copies of one invariant is how
    # they drift -- and writing the second copy here got the rule wrong on the first try (segments store their
    # boundary point twice, they do not share it), which is precisely the failure mode.
    bad_url = []
    for key in on_disk:
        data = json.load(io.open(os.path.join(REGIONS, key + ".json"), encoding="utf-8"))
        if any("url" in e for e in data["lineTrails"]):
            bad_url.append(key)
    t.eq("no url fields", bad_url, [])

    t.case("no region silently lost its trailSegments")
    # `donnersberg.json` lost its ENTIRE `trailSegments` key in commit b881699 (a rebuild that regenerated
    # lineTrails/trailGeo without carrying it forward) and stayed that way for several commits, until the user
    # noticed "Wasser & Holz" drawing with none of its coloured component-trail stretches. Nothing caught it:
    # validate_region checks segment/geometry CONSISTENCY when the key is present, and says nothing about a
    # key that is gone.
    #
    # Why a committed expectation and not a derived invariant. The obvious derived rule -- "a loop:true trail
    # must have a trailSegments entry" -- is false: 15 loops across 6 regions legitimately have none (a
    # published round with no component-trail breakdown; see buildTrailLayer's own "no TRAIL_SEGMENTS data"
    # branch). A geometric version ("this loop retraces other trails in its own region") was measured against
    # the real data and flagged 3 of those 15, which is a check people would learn to ignore. A count that may
    # only go UP has no false positives at all, and the one time it is wrong -- a region deliberately losing a
    # Tour -- the fix is a one-line, deliberate edit here, which is exactly the moment of attention the bug
    # above went through without.
    expected = json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "segments_expected.json"), encoding="utf-8"))
    lost = []
    for key, want in sorted(expected.items()):
        path = os.path.join(REGIONS, key + ".json")
        if not os.path.exists(path):
            lost.append("%s: the region file is gone" % key)
            continue
        got = len(json.load(io.open(path, encoding="utf-8")).get("trailSegments") or {})
        if got < want:
            lost.append("%s: %d trailSegments entries, had %d -- if a Tour was really dropped, say so in "
                        "tests/python/segments_expected.json" % (key, got, want))
    t.eq("every region still has at least the Touren it had", lost, [])
    # And the other direction, so the file cannot quietly fall behind reality: a region that GAINED segments
    # is fine, but one that has them while the manifest has never heard of it is a manifest that is not
    # watching it.
    unwatched = sorted(k for k in on_disk
                       if k not in expected
                       and (json.load(io.open(os.path.join(REGIONS, k + ".json"), encoding="utf-8"))
                            .get("trailSegments")))
    t.eq("and every region that has segments is watched here", unwatched, [])

    t.case("every region a phone could load has place labels and plausible geometry")
    # Not covered by the per-catalog-key run above if a file ever exists without a catalog entry.
    thin = []
    for key in on_disk:
        data = json.load(io.open(os.path.join(REGIONS, key + ".json"), encoding="utf-8"))
        if not data.get("places"):
            thin.append("%s: no places" % key)
        if not data.get("lineTrails"):
            thin.append("%s: no trails" % key)
        for tid, geo in data["trailGeo"].items():
            if len(geo) < 2:
                thin.append("%s/%s: %d points" % (key, tid, len(geo)))
    t.eq("nothing unusable", thin, [])
