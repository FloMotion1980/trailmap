# -*- coding: utf-8 -*-
"""Check a region JSON against the app's invariants. Run this after building or editing any region.

    python tools/validate_region.py                 # every region in the catalog
    python tools/validate_region.py paganella       # just one

Each check exists because breaking it produced a real, user-visible bug at some point. The rules live in
CLAUDE.md and docs/*.md as prose; this makes them executable, which is the difference between "documented"
and "enforced". Exit code is non-zero if anything failed, so it can gate a commit.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import haversine_m  # noqa: E402

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Trailmap App")
REGIONS = os.path.join(APP, "regions")
INDEX = os.path.join(APP, "index.html")

DIFFS = {"gruen", "blau", "rot", "schwarz"}
FOREST = "#2f4a3a"          # the group-label button's colour; a sub-region must not equal it


def _strip_comments(s):
    """Remove // and /* */ comments while respecting string literals.

    Needed because the catalog is heavily commented -- several entries carry a dozen lines of sourcing
    notes between the key and its `label`, and those comments contain both quotes and slashes.
    """
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in "\"'":
            q = c
            out.append(c)
            i += 1
            while i < n:
                out.append(s[i])
                if s[i] == "\\":
                    if i + 1 < n:
                        out.append(s[i + 1])
                        i += 2
                        continue
                elif s[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            while i < n and s[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            i = s.find("*/", i)
            i = n if i < 0 else i + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _block_at(s, i):
    """Given the index of a '{', return (body_without_braces, index_after_closing_brace)."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
    raise ValueError("unbalanced braces")


def _entries(body):
    """Yield (key, inner_body) for each `key: { ... }` at this level of an object literal."""
    i = 0
    while True:
        m = re.compile(r'([A-Za-z_$][\w$]*)\s*:\s*\{').search(body, i)
        if not m:
            return
        inner, after = _block_at(body, m.end() - 1)
        yield m.group(1), inner
        i = after


def catalog():
    """Parse REGION_CATALOG out of index.html into {groupKey: {label, trailCount, subRegions{key: colour}}}.

    A brace-matching scanner rather than one big regex: the first attempt used a regex anchored on
    `{ label:` and silently mis-parsed the commented entries, reporting a *sub-region* (shaped_lines) as a
    missing region file while skipping the group it belonged to. A validator that misreports is worse than
    none, so this parses structure instead of guessing at it.
    """
    src = _strip_comments(open(INDEX, encoding="utf-8").read())
    start = src.index("const REGION_CATALOG")
    block, _ = _block_at(src, src.index("{", start))
    out = {}
    for key, body in _entries(block):
        cnt = re.search(r"trailCount\s*:\s*(\d+)", body)
        label = re.search(r'label\s*:\s*"([^"]*)"', body)
        subs = {}
        msub = re.search(r"subRegions\s*:\s*\{", body)
        if msub:
            sub_body, _ = _block_at(body, msub.end() - 1)
            for sk, sinner in _entries(sub_body):
                col = re.search(r'color\s*:\s*"([^"]+)"', sinner)
                subs[sk] = col.group(1) if col else None
        out[key] = {"label": label.group(1) if label else key,
                    "trailCount": int(cnt.group(1)) if cnt else None,
                    "subRegions": subs}
    return out


def check(key, cat):
    """Return a list of problem strings for one region (empty means clean)."""
    path = os.path.join(REGIONS, key + ".json")
    if not os.path.exists(path):
        return ["regions/%s.json missing (referenced by REGION_CATALOG)" % key]
    d = json.load(open(path, encoding="utf-8"))
    bad = []
    trails = d.get("lineTrails") or []
    geo = d.get("trailGeo") or {}
    prof = d.get("elevationProfiles") or {}
    segs = d.get("trailSegments") or {}
    lifts = d.get("lifts") or []
    subs = cat["subRegions"]

    ids = [t["id"] for t in trails]
    for dup in {i for i in ids if ids.count(i) > 1}:
        bad.append("duplicate trail id %r" % dup)

    for t in trails:
        tid = t["id"]
        # A sub-region key not in the catalog renders a trail into a group heading that never appears,
        # i.e. the trail silently vanishes from the sidebar.
        if t["region"] not in subs:
            bad.append("%s: region %r is not a subRegion of %s" % (tid, t["region"], key))
        if t.get("diff") not in DIFFS:
            bad.append("%s: diff %r is not one of %s" % (tid, t.get("diff"), sorted(DIFFS)))
        # `url` was removed from the data model on 2026-07-28 together with the info panel's link to it, so
        # any occurrence now is leftover weight -- previously this check only rejected an EMPTY one.
        if "url" in t:
            bad.append("%s: has a url -- the field was removed from the data model" % tid)
        if tid not in geo:
            bad.append("%s: no trailGeo" % tid)
        elif len(geo[tid]) < 2:
            bad.append("%s: trailGeo has %d point(s)" % (tid, len(geo[tid])))
        if tid not in prof:
            bad.append("%s: no elevationProfile" % tid)
        elif len(prof[tid]) < 2:
            bad.append("%s: elevationProfile has %d point(s)" % (tid, len(prof[tid])))
        for fld in ("len", "up", "down"):
            if not isinstance(t.get(fld), (int, float)):
                bad.append("%s: %s is %r" % (tid, fld, t.get(fld)))

    for tid in geo:
        if tid not in ids:
            bad.append("trailGeo has %r with no lineTrails entry" % tid)
    for tid in prof:
        if tid not in ids:
            bad.append("elevationProfiles has %r with no lineTrails entry" % tid)

    # THE loop invariant, learned the hard way (docs/trailrunde-feature.md): TRAIL_GEO[loopId] must be the
    # exact concatenation of its segments' coords. When it was not, the yellow selection highlight and the
    # visible coloured segments drew two different lines for the same stretch.
    for tid, seglist in segs.items():
        if tid not in geo:
            bad.append("trailSegments %r has no trailGeo" % tid)
            continue
        joined = [c for s in seglist for c in s["coords"]]
        if joined != geo[tid]:
            bad.append("%s: trailGeo is NOT the concatenation of its trailSegments "
                       "(%d vs %d points)" % (tid, len(geo[tid]), len(joined)))
        for s in seglist:
            if s.get("trailId") and s["trailId"] not in ids:
                bad.append("%s: segment references unknown trail %r" % (tid, s["trailId"]))
            if s.get("liftId") and s["liftId"] not in {l["id"] for l in lifts}:
                bad.append("%s: segment references unknown lift %r" % (tid, s["liftId"]))

    lift_ids = [l["id"] for l in lifts]
    for dup in {i for i in lift_ids if lift_ids.count(i) > 1}:
        bad.append("duplicate lift id %r" % dup)
    for l in lifts:
        if l.get("region") not in subs:
            bad.append("lift %s: region %r is not a subRegion of %s" % (l["id"], l.get("region"), key))
        if len(l.get("coords") or []) < 2:
            bad.append("lift %s: needs at least 2 coords" % l["id"])
            continue
        # Lifts are stored bottom-station-first; the app derives the climb and the boarding station from
        # that order, so a flipped one would have a negative climb and board at the top.
        if l.get("baseEle") is not None and l.get("topEle") is not None and l["baseEle"] > l["topEle"]:
            bad.append("lift %s: baseEle %s > topEle %s (store bottom station first)"
                       % (l["id"], l["baseEle"], l["topEle"]))

    # Sub-region colours only have to be distinct WITHIN a group (repeats across groups are fine and
    # expected), and none may equal the group-label button's own colour, which sits directly above them.
    seen = {}
    for sk, col in subs.items():
        c = col.lower()
        if c == FOREST:
            bad.append("subRegion %s: colour equals the group-label --forest" % sk)
        if c in seen:
            bad.append("subRegion %s: colour %s already used by %s in this group" % (sk, col, seen[c]))
        seen[c] = sk

    if cat["trailCount"] is not None and cat["trailCount"] != len(trails):
        bad.append("REGION_CATALOG trailCount is %d but the file has %d trails"
                   % (cat["trailCount"], len(trails)))

    # A trail whose geometry sits far from the rest is usually a same-named OSM way somewhere else
    # entirely -- that is exactly how a "Tronchey" lift 8 km north nearly made it into Portes du Soleil.
    if geo:
        lats = [c[0] for g in geo.values() for c in g]
        lons = [c[1] for g in geo.values() for c in g]
        mid = [(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2]
        span = haversine_m([min(lats), min(lons)], [max(lats), max(lons)])
        for tid, g in geo.items():
            d = min(haversine_m(mid, c) for c in g)
            if span > 0 and d > span:          # closest point is further away than the whole region is wide
                bad.append("%s: geometry is %.0f km from the region centre -- wrong way matched?"
                           % (tid, d / 1000))

    # regions/version.json is what actually invalidates a cached region: the app fetches
    # regions/<key>.json?v=<hash> and the service worker serves those cache-first. A stale hash means an
    # edited region never reaches a device that already has it; a MISSING entry is worse, because the URL is
    # then unversioned and that copy stays cached forever. Both had happened by 2026-07-28 -- an edit to
    # paznaun.json left its hash untouched, and three regions added the night before were never listed.
    # tools/update_region_versions.py fixes it.
    try:
        manifest = json.load(open(os.path.join(REGIONS, "version.json"), encoding="utf-8"))
    except (IOError, ValueError):
        bad.append("regions/version.json missing or unreadable -- run tools/update_region_versions.py")
    else:
        want = hashlib.md5(open(path, "rb").read()).hexdigest()[:10]
        have = manifest.get(key)
        if have is None:
            bad.append("not listed in regions/version.json -- it would be cached forever; "
                       "run tools/update_region_versions.py")
        elif have != want:
            bad.append("regions/version.json hash is stale (%s, file is %s) -- edits will not reach "
                       "cached clients; run tools/update_region_versions.py" % (have, want))
    return bad


def main():
    cats = catalog()
    wanted = sys.argv[1:] or sorted(cats)
    unknown = [w for w in wanted if w not in cats]
    for w in unknown:
        print("? %s is not in REGION_CATALOG" % w)
    failed = bool(unknown)
    for key in [w for w in wanted if w in cats]:
        problems = check(key, cats[key])
        if problems:
            failed = True
            print("FAIL %s (%d)" % (key, len(problems)))
            for p in problems:
                print("     - %s" % p)
        else:
            d = json.load(open(os.path.join(REGIONS, key + ".json"), encoding="utf-8"))
            print("ok   %-16s %3d trails, %2d lifts, %d sub-regions"
                  % (key, len(d["lineTrails"]), len(d.get("lifts") or []),
                     len(cats[key]["subRegions"])))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
