# -*- coding: utf-8 -*-
"""Harvest Trailforks geometry for the Schwarzwald, one trail page at a time.

Two inputs/outputs, both under `Material/Schwarzwald/`:

    trailforks_table.json  <- the region tables (name, slug, TF difficulty, riding area, distance)
    trailforks_geo.json    -> per slug {"c": [[lat, lng], ...], "p": [[x_m, ele_m, lat, lng], ...]}

A Trailforks trail page carries the line TWICE — the `encodedpath` polyline and an `ElevationChart`
config whose points hold lat/lng AND real elevation AND the cumulative distance. That is why this
region needs no elevation API: same as the Vogesen build, and the two lengths cross-check each other.

**Anonymous fetches work** (verified 2026-08-20 over ~700 pages) but only through curl: Trailforks
answers 403 to urllib's request even with an identical User-Agent. Resumable and polite — it skips
what it already has, sleeps between pages, and writes the file every few trails, so an interrupted run
costs nothing.

    python tools/harvest_schwarzwald_tf.py            # everything still missing
    python tools/harvest_schwarzwald_tf.py --limit 50 # a slice, to check before committing to the rest
"""
import io
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import haversine_m  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATERIAL = os.path.join(ROOT, "Material", "Schwarzwald")
TABLE = os.path.join(MATERIAL, "trailforks_table.json")
GEO = os.path.join(MATERIAL, "trailforks_geo.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
#: Rows carrying these instead of a real grade are fireroads/access, not rated descents — the same
#: exclusion Bike Kingdom's fire roads and Varazze's access rows already follow.
ACCESS_DIFF = {"Access Trail, Road or Doubletrack", "Secondary Access Road/Trail",
               "Chairlifts & gondolas"}


def fetch(slug):
    url = "https://www.trailforks.com/trails/%s/" % slug
    return subprocess.run(["curl", "-s", "-A", UA, url],
                          capture_output=True).stdout.decode("utf-8", "replace")


def decode_polyline(p):
    """Google-encoded polyline, precision 5 — Trailforks' `encodedpath`."""
    pts, lat, lng, i = [], 0, 0, 0
    while i < len(p):
        for j in range(2):
            shift = res = 0
            while True:
                b = ord(p[i]) - 63
                i += 1
                res |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(res >> 1) if res & 1 else res >> 1
            if j == 0:
                lat += d
            else:
                lng += d
        pts.append([lat / 1e5, lng / 1e5])
    return pts


def parse(html):
    """(polyline, profile) from one trail page; either may be None."""
    coords = None
    m = re.search(r"encodedpath:\s*'([^']*)'", html)
    if m:
        try:
            coords = decode_polyline(m.group(1).encode().decode("unicode_escape"))
        except Exception:
            coords = None
    prof = None
    m = re.search(r"new ElevationChart\(", html)
    if m:
        # The config is JS, not JSON, so take just the points arrays out of it.
        chunk = html[m.end():m.end() + 400000]
        pts = []
        # lat/lng come QUOTED and y sometimes does too, which an unquoted-number pattern silently
        # misses -- 12 trails were harvested with no profile at all before this was noticed.
        for pm in re.finditer(r'\{"id":\d+,"x":"?([-\d.]+)"?,"y":"?([-\d.]+)"?,'
                              r'"lat":"?([-\d.]+)"?,"lng":"?([-\d.]+)"?', chunk):
            pts.append([float(pm.group(1)), float(pm.group(2)),
                        float(pm.group(3)), float(pm.group(4))])
        prof = pts or None
    return coords, prof


def main(argv):
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    table = json.load(io.open(TABLE, encoding="utf-8"))
    geo = json.load(io.open(GEO, encoding="utf-8")) if os.path.exists(GEO) else {}
    todo = [s for s, r in sorted(table.items())
            if r.get("diff") and r["diff"] not in ACCESS_DIFF and s not in geo]
    if limit:
        todo = todo[:limit]
    print("%d in the table, %d already harvested, %d to fetch" % (len(table), len(geo), len(todo)))
    done = 0
    for slug in todo:
        html = fetch(slug)
        coords, prof = parse(html)
        if not coords and not prof:
            # Recorded as an explicit miss so a rerun does not keep retrying a page that has no line;
            # the build reports these rather than inventing geometry for them.
            geo[slug] = {"c": None, "p": None}
        else:
            geo[slug] = {"c": coords, "p": prof}
        done += 1
        if done % 10 == 0:
            json.dump(geo, io.open(GEO, "w", encoding="utf-8"), separators=(",", ":"))
            got = sum(1 for v in geo.values() if v.get("c"))
            print("  %d/%d fetched, %d with a line" % (done, len(todo), got))
        time.sleep(0.7)
    json.dump(geo, io.open(GEO, "w", encoding="utf-8"), separators=(",", ":"))
    missing = [s for s in todo if not geo[s].get("c") and not geo[s].get("p")]
    both = [s for s in todo if geo[s].get("c") and geo[s].get("p")]
    print("done: %d fetched, %d have both sources, %d have no geometry at all"
          % (len(todo), len(both), len(missing)))
    if missing:
        print("no geometry: " + ", ".join(missing[:40]))
    # A quick cross-check on what we just got, the same discipline the Vogesen build uses.
    bad = []
    for slug in both:
        c, p = geo[slug]["c"], geo[slug]["p"]
        lc = sum(haversine_m(c[i], c[i + 1]) for i in range(len(c) - 1))
        lp = sum(haversine_m(p[i][2:4], p[i + 1][2:4]) for i in range(len(p) - 1))
        if abs(lc - lp) > 60:
            bad.append((slug, round(lc), round(lp)))
    print("polyline vs profile length disagreement over 60 m: %d" % len(bad))
    for b in bad[:20]:
        print("   %s  polyline %d m, profile %d m" % b)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main(sys.argv[1:])
