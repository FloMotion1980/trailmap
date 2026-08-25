# -*- coding: utf-8 -*-
"""Harvest a Trailforks region tree: the trail tables first, then one page per trail.

Generic successor to `tools/harvest_schwarzwald_tf.py`, which only ever knew about the Schwarzwald's
own districts and needed the *table* half to be produced by hand (that ad-hoc script was lost, and the
paging rule with it). Both halves live here now.

    python tools/harvest_trailforks.py --dir Material/Madeira --seeds madeira-island,madeira --tables
    python tools/harvest_trailforks.py --dir Material/Madeira --geo
    python tools/harvest_trailforks.py --dir Material/Madeira --geo --limit 50   # a slice first

Two files under `--dir`, the same shapes the Schwarzwald build already reads:

    trailforks_table.json  {slug: {slug, name, diff, area, area_slug, m, down, up, hidden, src}}
    trailforks_geo.json    {slug: {"c": [[lat, lng], ...], "p": [[x_m, ele_m, lat, lng], ...]}}

Four things about the source, each of which has cost someone an hour:

* **Anonymous fetches work, but only through curl.** Trailforks answers 403 to urllib with a
  byte-identical User-Agent. Do not spend time on which header it dislikes.
* **A region's table includes every descendant region's trails** (verified: `madeira-island` returns
  Funchal, Fanal and Calheta rows), so seed the province/island, not each hub. The `riding area` column
  names the descendant, which is what makes it a usable hub hint later. But do not ASSUME the tree --
  Trailforks has a `madeira` region that is NOT an ancestor of `madeira-island`, so pass every seed that
  might hold trails and let the dedupe-by-slug sort it out.
* **The table pages at 100 rows via `?page=N`**, and nothing in the HTML says so -- no pager markup, no
  count, an over-the-end page just returns an empty table.
* **`difficulty=` must name every code including 10 (`Severe / Black`)** or the whole black tier
  disappears silently, and `activitytype=1` keeps hike-only lines out (the Harz's "Madonon Ridgeline"
  was Trailforks-tagged Hike).
"""
import argparse
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
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
#: Every difficulty code Trailforks knows. Leaving 10 out drops the entire black tier without a word.
ALL_DIFF = "3,4,9,5,1,7,2,6,8,10,11,12"
PAGE_ROWS = 100
#: Sentinel curl writes the final URL behind, so `fetch` can tell a real page from the error page.
FINAL_MARK = "@@tf-final@@"
#: Rows carrying these instead of a real grade are fireroads/uplift, not rated descents -- the same
#: exclusion Bike Kingdom's fire roads and the Schwarzwald sweep already follow.
ACCESS_DIFF = {"Access Trail, Road or Doubletrack", "Secondary Access Road/Trail",
               "Chairlifts & gondolas"}


def fetch(url, tries=3):
    """Fetch one Trailforks page, FOLLOWING REDIRECTS (`-L`).

    Without `-L` a slug that Trailforks 301s to its canonical, numeric-suffixed form comes back as a few
    hundred bytes of redirect body -- which every caller here reads as "no such region". That is how Elba
    stayed hidden until 2026-08-25: `isola-d-elba` redirects to `isola-d-elba-28064` and holds 310 trails,
    while the slugs that answered directly (`capoliveri`, `porto-azzurro`, `cavo-65916`) are village-sized
    corners of the same island totalling 14 rows. A region can therefore look like a 14-trail backwater and
    be a 300-trail one. `tools/probe_tf_slugs.py` and `tools/find_tf_regions.py` both go through here, so
    both inherit the fix; a probe that reports "-- none --" now really means the slug does not exist.
    """
    html = ""
    for attempt in range(tries):
        # `url_effective` is appended and stripped again, because following redirects means a MISS now
        # arrives as a full, 200-OK error page instead of a short redirect body -- and that page carries
        # three `/trails/` links of its own, which a probe counting those reads as three trails. Every
        # nonexistent slug then "hits". Asking where curl actually ended up is the only unambiguous answer.
        wfmt = "\n" + FINAL_MARK + "%{url_effective}"
        p = subprocess.run(["curl", "-sL", "-A", UA, "-w", wfmt, url], capture_output=True)
        html = p.stdout.decode("utf-8", "replace")
        i = html.rfind(FINAL_MARK)
        if i >= 0:
            final, html = html[i + len(FINAL_MARK):].strip(), html[:i]
            if "/error" in final:
                return ""
        if len(html) > 5000:
            return html
        time.sleep(2 + 3 * attempt)
    return html


# ---------------------------------------------------------------------------------------------- table
ROW_RE = re.compile(r"<tr\s*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def parse_table(html):
    """[{slug, name, diff, area, area_slug, m, down, up, hidden}] for one listing page."""
    i = html.find('id="trails_table"')
    if i < 0:
        return []
    body = html[i:]
    body = body[:body.find("</table>")]
    out = []
    for rm in ROW_RE.finditer(body):
        cells = CELL_RE.findall(rm.group(1))
        if len(cells) < 6:
            continue
        am = re.search(r'trailforks\.com/trails/([A-Za-z0-9_-]+)/"([^>]*)>(.*?)</a>', rm.group(1))
        if not am:
            continue
        dm = re.search(r'class="dicon_small[^"]*"\s+title="([^"]*)"', rm.group(1))
        gm = re.search(r'trailforks\.com/region/([A-Za-z0-9_-]+)/">(.*?)</a>', rm.group(1))
        nums = re.findall(r'data-v="(-?[\d.]+)"', rm.group(1))
        # `nid` is Trailforks' own numeric trail id. Needed because a trail PAGE embeds several rating
        # blobs -- its own plus the neighbours its map draws -- so the rating parse has to anchor on this
        # id rather than on the first blob in the file.
        nm = re.search(r"data-nid=['\"](\d+)['\"]", rm.group(1))
        out.append({
            "slug": am.group(1),
            "nid": int(nm.group(1)) if nm else None,
            "name": re.sub(r"<[^>]+>", "", am.group(3)).strip(),
            "diff": dm.group(1) if dm else None,
            "area": re.sub(r"<[^>]+>", "", gm.group(2)).strip() if gm else None,
            "area_slug": gm.group(1) if gm else None,
            "m": float(nums[0]) if len(nums) > 0 else None,
            "down": float(nums[1]) if len(nums) > 1 else None,
            "up": float(nums[2]) if len(nums) > 2 else None,
            "hidden": "hidden_trail" in am.group(2),
        })
    return out


def harvest_tables(seeds, path):
    table = json.load(io.open(path, encoding="utf-8")) if os.path.exists(path) else {}
    for seed in seeds:
        page, added, seen = 1, 0, 0
        while True:
            url = ("https://www.trailforks.com/region/%s/trails/?difficulty=%s&activitytype=1&page=%d"
                   % (seed, ALL_DIFF, page))
            rows = parse_table(fetch(url))
            if not rows:
                break
            for r in rows:
                seen += 1
                r["src"] = seed
                if r["slug"] not in table:
                    table[r["slug"]] = r
                    added += 1
            if len(rows) < PAGE_ROWS:
                break
            page += 1
            time.sleep(0.6)
        print("  %-38s %4d rows over %d page(s), %4d new" % (seed, seen, page, added))
        sys.stdout.flush()
        json.dump(table, io.open(path, "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
    print("table: %d trails" % len(table))
    return table


# ------------------------------------------------------------------------------------------------ geo
def decode_polyline(p):
    """Google-encoded polyline, precision 5 -- Trailforks' `encodedpath`."""
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


#: The community numbers, read off the same trail page the geometry comes from -- so they cost no extra
#: request. Verified anonymously 2026-08-21: `rating_bayesian` is the vote-count-shrunk 0-5 star value,
#: `popularity_score` a 0-100 figure Trailforks derives from a year of check-ins.
#:
#: **The region TABLE does not carry the rating** -- it serves `data-rating="0"` for every trail while its
#: own tooltip says "0 / 5 with 4 votes". Anyone who parses only the table concludes Trailforks does not
#: expose ratings anonymously, which is wrong. Take them from the trail page.
RATING_FIELDS = ("rating_bayesian", "votes", "popularity_score", "total_checkins", "ridden", "views")


def parse_rating(html, trail_id=None):
    """{rating_bayesian, votes, popularity_score, ...} for ONE trail, or {} if the blob is absent.

    A trail page embeds several of these blobs -- its own plus the neighbours its map shows -- so the
    window has to be anchored on the page's OWN trailid, not on the first match anywhere in the file.
    """
    if trail_id:
        i = html.find('"trailid":"%s"' % trail_id)
    else:
        m = re.search(r'"trailid"\s*:\s*"(\d+)"', html)
        i = m.start() if m else -1
    if i < 0:
        return {}
    blob = html[max(0, i - 400):i + 3000]
    out = {}
    for f in RATING_FIELDS:
        m = re.search(r'"%s"\s*:\s*"?([\d.]+)' % f, blob)
        if m:
            try:
                out[f] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
            except ValueError:
                pass
    return out


def parse_trail(html):
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
        chunk = html[m.end():m.end() + 400000]
        pts = []
        # lat/lng come QUOTED and y sometimes does too; an unquoted-number pattern silently misses them.
        for pm in re.finditer(r'\{"id":\d+,"x":"?([-\d.]+)"?,"y":"?([-\d.]+)"?,'
                              r'"lat":"?([-\d.]+)"?,"lng":"?([-\d.]+)"?', chunk):
            pts.append([float(pm.group(1)), float(pm.group(2)),
                        float(pm.group(3)), float(pm.group(4))])
        prof = pts or None
    return coords, prof


def harvest_geo(table_path, geo_path, limit=None, sleep=0.7, skip_areas=(), only_areas=()):
    table = json.load(io.open(table_path, encoding="utf-8"))
    geo = json.load(io.open(geo_path, encoding="utf-8")) if os.path.exists(geo_path) else {}
    skip = set(skip_areas)
    # `only_areas` is what makes a broad seed usable. Laax has no region of its own, so its trails come out
    # of `graubunden` -- 2 416 rows over 70 areas, of which "Biketrails Flims Laax" and "Flims LAAX" are the
    # 122 that matter. Fetching the canton to rate 19 trails is an hour of requests for nothing.
    keep = set(only_areas)
    todo = [s for s, r in sorted(table.items())
            if r.get("diff") and r["diff"] not in ACCESS_DIFF and s not in geo
            and (r.get("area") or "") not in skip
            and (not keep or (r.get("area") or "") in keep)]
    if limit:
        todo = todo[:limit]
    print("%d in the table, %d already harvested, %d to fetch" % (len(table), len(geo), len(todo)))
    sys.stdout.flush()
    dirty = False
    for n, slug in enumerate(todo, 1):
        html = fetch("https://www.trailforks.com/trails/%s/" % slug)
        coords, prof = parse_trail(html)
        # An explicit miss, so a rerun does not keep retrying a page that has no line; the build
        # reports these rather than inventing geometry for them.
        geo[slug] = {"c": coords, "p": prof}
        # The community numbers ride along in the SAME fetch, so they cost nothing extra, and they go
        # into the table next to the row they describe -- which is where the build already looks for a
        # trail's metadata.
        rating = parse_rating(html, str(table[slug].get("nid") or "") or None)
        if rating:
            table[slug].update(rating)
            dirty = True
        if n % 20 == 0:
            json.dump(geo, io.open(geo_path, "w", encoding="utf-8"), separators=(",", ":"))
            if dirty:
                json.dump(table, io.open(table_path, "w", encoding="utf-8"),
                          ensure_ascii=False, separators=(",", ":"))
            print("  %d/%d fetched, %d with a line"
                  % (n, len(todo), sum(1 for v in geo.values() if v.get("c"))))
            sys.stdout.flush()
        time.sleep(sleep)
    json.dump(geo, io.open(geo_path, "w", encoding="utf-8"), separators=(",", ":"))
    if dirty:
        json.dump(table, io.open(table_path, "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
        print("ratings: %d of %d rows carry one now"
              % (sum(1 for r in table.values() if r.get("rating_bayesian")), len(table)))
    both = [s for s in todo if geo[s].get("c") and geo[s].get("p")]
    missing = [s for s in todo if not geo[s].get("c") and not geo[s].get("p")]
    print("done: %d fetched, %d have both sources, %d have no geometry at all"
          % (len(todo), len(both), len(missing)))
    if missing:
        print("no geometry: " + ", ".join(missing[:40]))
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


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="material directory for this region")
    ap.add_argument("--seeds", default="", help="comma-separated Trailforks region slugs")
    ap.add_argument("--tables", action="store_true")
    ap.add_argument("--geo", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sleep", type=float, default=0.7)
    ap.add_argument("--areas", help="only fetch pages for these `riding area` names (comma-separated) -- "
                                     "for a seed that covers far more ground than the region does")
    ap.add_argument("--skip-areas", help="JSON list of `riding area` names not to fetch geometry for. "
                                        "A harvest-COST filter only: what is finally in the region is "
                                        "decided by the build's own anchor rule, which sees only "
                                        "harvested lines, so never encode a region border here.")
    a = ap.parse_args(argv)
    d = a.dir if os.path.isabs(a.dir) else os.path.join(ROOT, a.dir)
    if not os.path.isdir(d):
        os.makedirs(d)
    table_path = os.path.join(d, "trailforks_table.json")
    geo_path = os.path.join(d, "trailforks_geo.json")
    if a.tables:
        harvest_tables([s for s in a.seeds.split(",") if s], table_path)
    if a.geo:
        skip = json.load(io.open(a.skip_areas, encoding="utf-8")) if a.skip_areas else []
        harvest_geo(table_path, geo_path, a.limit, a.sleep, skip,
                    [x for x in (a.areas or "").split(",") if x])


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main(sys.argv[1:])
