# -*- coding: utf-8 -*-
"""Trailmap region-building pipeline — the proven primitives, in one importable module.

Why this file exists: this pipeline had been written from scratch in every session that added a region
(~27 ad-hoc scripts in one session alone, all of which died with it), and CLAUDE.md itself noted it was
"scripted more than once, not currently committed". Re-deriving it each time risks silent inconsistency
between regions — a different simplification epsilon or a different resampling count makes new trails look
subtly unlike the existing ones, which is the same class of problem as the Challenge threshold tuning.

Standard library only, deliberately: no install step, works in a fresh sandbox.

    import sys; sys.path.insert(0, r"D:\\Trailmap\\tools")
    from trailmap_pipeline import *

Everything here is extracted from code that actually produced the regions currently in the app
(Paganella, Serfaus, Portes du Soleil, Bikecircus, Sölden, …), including the workarounds for real data
defects met along the way. Read the docstrings before "simplifying" any of it.
"""
import difflib
import html as _html
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request

__all__ = [
    "haversine_m", "perp_distance_m", "douglas_peucker", "cumulative_km", "bounds_of",
    "parse_gpx", "parse_kml", "gpx_name", "dedupe_points", "split_on_gaps",
    "ElevationLookup",
    "overpass", "osm_aerialway_survey", "osm_named_ways", "chain_ways", "norm_name", "fuzzy_lookup",
    "build_profile", "build_trail", "write_region", "region_summary",
    "SIMPLIFY_EPS_M", "MIN_POINT_SPACING_M", "MAX_TRACK_GAP_M",
]

# ---------------------------------------------------------------------------------------------------
# Constants that must stay the same across regions, or trails stop looking alike
# ---------------------------------------------------------------------------------------------------

#: Douglas-Peucker tolerance. Do NOT raise this to hit a point-count target -- it visibly distorts short
#: trails, which is exactly the mistake CLAUDE.md warns about.
SIMPLIFY_EPS_M = 2.0

#: Drop consecutive raw points closer than this before simplifying. GPS recordings contain dense clusters
#: while standing still, and they skew the simplification.
MIN_POINT_SPACING_M = 0.5


# ---------------------------------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------------------------------

def haversine_m(a, b):
    """Great-circle distance in metres between two [lat, lon] points (extra elements ignored)."""
    R = 6371000.0
    r = math.pi / 180
    dla = (b[0] - a[0]) * r
    dlo = (b[1] - a[1]) * r
    x = math.sin(dla / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def perp_distance_m(p, a, b):
    """Perpendicular distance from p to the segment a-b, via a local equirectangular projection.

    Projecting first (rather than doing spherical maths) is accurate enough at trail scale and keeps
    Douglas-Peucker cheap. The cos(lat) factor uses a's latitude, which is fine over a few hundred metres.
    """
    la = a[0] * math.pi / 180
    to_xy = lambda q: (q[1] * math.cos(la) * 111320, q[0] * 110540)
    P, A, B = to_xy(p), to_xy(a), to_xy(b)
    num = abs((B[0] - A[0]) * (A[1] - P[1]) - (A[0] - P[0]) * (B[1] - A[1]))
    den = math.hypot(B[0] - A[0], B[1] - A[1])
    return haversine_m(p, a) if den < 1e-6 else num / den


def douglas_peucker(points, eps_m=SIMPLIFY_EPS_M):
    """Simplify a [[lat, lon, ele?], ...] list, keeping any third element on the points it keeps."""
    if len(points) < 3:
        return list(points)
    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = perp_distance_m(points[i][:2], points[0][:2], points[-1][:2])
        if d > dmax:
            dmax, idx = d, i
    if dmax <= eps_m:
        return [points[0], points[-1]]
    return (douglas_peucker(points[:idx + 1], eps_m)[:-1]
            + douglas_peucker(points[idx:], eps_m))


def cumulative_km(coords):
    """Cumulative distance in km along a coordinate list; same length as the input."""
    out = [0.0]
    for i in range(1, len(coords)):
        out.append(out[-1] + haversine_m(coords[i - 1][:2], coords[i][:2]) / 1000.0)
    return out


def bounds_of(trail_geo):
    """The [[latMin, lngMin], [latMax, lngMax]] box a REGION_CATALOG entry needs.

    Accepts the region's `trailGeo` dict (or any iterable of coordinate lists).
    """
    geoms = trail_geo.values() if isinstance(trail_geo, dict) else trail_geo
    lats, lons = [], []
    for g in geoms:
        for c in g:
            lats.append(c[0])
            lons.append(c[1])
    if not lats:
        raise ValueError("bounds_of: no coordinates")
    return [[round(min(lats), 5), round(min(lons), 5)],
            [round(max(lats), 5), round(max(lons), 5)]]


# ---------------------------------------------------------------------------------------------------
# GPX
# ---------------------------------------------------------------------------------------------------

def parse_gpx(text):
    """Extract [[lat, lon, ele|None], ...] from GPX text.

    Regex on purpose, not an XML parser: real source GPX in Material/ breaks strict parsers in at least
    three ways -- unescaped `&` inside <name>, CDATA-wrapped <ele> values, and `lon` before `lat` in the
    attribute order. A parser that chokes on any of those is useless here. Handles both self-closing
    <trkpt/> and <trkpt>…</trkpt>, and reads <rtept> too, since some operator exports use routes.
    """
    pts = []
    for tag in ("trkpt", "rtept"):
        for m in re.finditer(r'<%s\b([^>]*?)(?:/>|>(.*?)</%s>)' % (tag, tag), text, re.S):
            attrs = m.group(1) or ""
            body = m.group(2) or ""
            la = re.search(r'lat="([-\d.]+)"', attrs)
            lo = re.search(r'lon="([-\d.]+)"', attrs)
            if not (la and lo):
                continue
            # CDATA or plain, and possibly with whitespace
            e = re.search(r'<ele>\s*(?:<!\[CDATA\[)?\s*([-\d.]+)\s*(?:\]\]>)?\s*</ele>', body)
            pts.append([float(la.group(1)), float(lo.group(1)),
                        float(e.group(1)) if e else None])
        if pts:
            break
    return pts


def gpx_name(text):
    """The track name, HTML-unescaped and stripped of a leading trail number.

    Operator exports arrive like '787 &quot;Ribs Trail&quot;' or 'TC Foo'; the number belongs in the
    display name only when the region's brochure uses it (see the Nauders/Finale conventions).
    """
    m = (re.search(r"<metadata>.*?<name>(.*?)</name>", text, re.S)
         or re.search(r"<name>(.*?)</name>", text, re.S))
    if not m:
        return None
    n = _html.unescape(m.group(1)).strip()
    n = re.sub(r"^\s*(?:TC|\d+)\s*", "", n).strip()
    n = n.strip('"\u201c\u201d').strip()
    return re.sub(r"\s+", " ", n)


def parse_kml(text):
    """Extract [[lat, lon, ele|None], ...] from KML `<coordinates>` blocks (lon,lat[,ele] order).

    Needed because some operator portals serve KML from a URL that ends in `.gpx` — the Tiroler Zugspitz
    Arena's per-tour download does exactly that. Elevation is often a placeholder 0 there, which
    `build_trail` detects and backfills.
    """
    pts = []
    for block in re.findall(r"<coordinates>(.*?)</coordinates>", text, re.S):
        for tok in block.split():
            p = tok.split(",")
            if len(p) >= 2:
                try:
                    pts.append([float(p[1]), float(p[0]),
                                float(p[2]) if len(p) > 2 else None])
                except ValueError:
                    continue
    return pts


#: A jump longer than this between consecutive raw points is a segment boundary, not a ride.
MAX_TRACK_GAP_M = 120.0


def split_on_gaps(points, max_gap_m=MAX_TRACK_GAP_M):
    """Split a point list wherever consecutive points jump implausibly far apart.

    Portal exports routinely concatenate several segments into one track (a descent plus a variant, or a
    trail plus its access road) with no separator. Flattening those blindly welds them together with a
    phantom straight line across the map — the Zugspitz Arena's "Blue Bird" KML jumps 1.8 km back east
    partway through, which alone made its computed length 6.16 km against 4.1 km official. This is the same
    defect that got Paganella's lift-assisted marathon routes excluded.

    Returns a list of segments, longest first, so `split_on_gaps(pts)[0]` is the main line. **Always check
    the chosen segment's length against the operator's published figure** rather than assuming the longest
    one is the right one.
    """
    if not points:
        return []
    segs, cur = [], [points[0]]
    for prev, p in zip(points, points[1:]):
        if haversine_m(prev[:2], p[:2]) > max_gap_m:
            segs.append(cur)
            cur = [p]
        else:
            cur.append(p)
    segs.append(cur)
    segs.sort(key=lambda s: cumulative_km(s)[-1] if len(s) > 1 else 0.0, reverse=True)
    return segs


def dedupe_points(points, min_spacing_m=MIN_POINT_SPACING_M):
    """Drop consecutive points closer together than `min_spacing_m` (standing-still clusters)."""
    out = []
    for p in points:
        if not out or haversine_m(out[-1][:2], p[:2]) > min_spacing_m:
            out.append(p)
    return out


# ---------------------------------------------------------------------------------------------------
# Elevation (OpenTopoData) — for geometry that has no usable <ele> of its own
# ---------------------------------------------------------------------------------------------------

class ElevationLookup:
    """Batched OpenTopoData lookups with an on-disk cache.

    Needed whenever geometry comes from OSM (no elevation at all) or from a GPX whose <ele> is a
    placeholder -- e.g. all four Donnersberg site downloads carry <ele>0</ele> throughout.

    Datasets are tried in descending quality and the first that answers for the whole batch wins.
    The public API is rate-limited (1 call/s, 100 locations/call), hence the sleeps; without the cache a
    re-run of a build would take minutes and risk a ban.
    """

    DATASETS = ("eudem25m", "mapzen", "srtm30m")
    BATCH = 100

    def __init__(self, cache_path="elevation_cache.json"):
        self.cache_path = cache_path
        self.cache = {}
        if os.path.exists(cache_path):
            try:
                self.cache = json.load(open(cache_path, encoding="utf-8"))
            except Exception:
                self.cache = {}

    @staticmethod
    def _key(p):
        return "%.5f,%.5f" % (p[0], p[1])

    def _save(self):
        json.dump(self.cache, open(self.cache_path, "w", encoding="utf-8"))

    def __call__(self, points):
        """Return one elevation per [lat, lon] in `points`, fetching only what is not cached."""
        todo = [p for p in points if self._key(p) not in self.cache]
        # de-duplicate within the request too, or a doubled-back trail pays twice
        seen, uniq = set(), []
        for p in todo:
            k = self._key(p)
            if k not in seen:
                seen.add(k)
                uniq.append(p)
        for i in range(0, len(uniq), self.BATCH):
            batch = uniq[i:i + self.BATCH]
            loc = "|".join("%.5f,%.5f" % (p[0], p[1]) for p in batch)
            got = None
            for ds in self.DATASETS:
                for attempt in range(4):
                    try:
                        url = "https://api.opentopodata.org/v1/%s?locations=%s" % (ds, loc)
                        req = urllib.request.Request(url, headers={"User-Agent": "trailmap/1.0"})
                        r = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
                        if r.get("status") == "OK":
                            vals = [x["elevation"] for x in r["results"]]
                            if all(v is not None for v in vals):
                                got = vals
                                break
                    except Exception:
                        pass
                    time.sleep(2 + 2 * attempt)
                if got:
                    break
            if got is None:
                raise RuntimeError("elevation lookup failed for a batch of %d" % len(batch))
            for p, e in zip(batch, got):
                self.cache[self._key(p)] = e
            self._save()
            time.sleep(1.1)
        return [self.cache[self._key(p)] for p in points]


# ---------------------------------------------------------------------------------------------------
# OpenStreetMap / Overpass
# ---------------------------------------------------------------------------------------------------

def overpass(query, timeout=240):
    """Run an Overpass query, falling back across mirrors.

    kumi.systems first: it is consistently the most reliable of the three for these bbox-sized queries.
    """
    endpoints = ("https://overpass.kumi.systems/api/interpreter",
                 "https://overpass-api.de/api/interpreter",
                 "https://overpass.openstreetmap.fr/api/interpreter")
    last = None
    for ep in endpoints:
        for _ in range(2):
            try:
                req = urllib.request.Request(
                    ep, data=urllib.parse.urlencode({"data": query}).encode(),
                    headers={"User-Agent": "trailmap/1.0"})
                return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
            except Exception as e:
                last = e
                time.sleep(3)
    raise RuntimeError("overpass failed: %r" % (last,))


def osm_aerialway_survey(bbox, min_len_m=200):
    """Every named aerialway in `bbox` ("latMin,lonMin,latMax,lonMax"), with geometry.

    Returns rows of {id, name, aerialway, ref, bike, len, geom}. `bike` is OSM's own
    aerialway:bicycle/bicycle tag -- reported for information only. **It does not decide whether a lift
    belongs in the data**: the operator's summer list does. That tag was wrong in both directions in
    Serfaus (bicycle=yes on a lift the operator excludes, and tags on three it never lists). See
    docs/lifts-feature.md.
    """
    q = ('[out:json][timeout:%d];way["aerialway"]["aerialway"!="station"](%s);out tags geom;'
         % (240, bbox))
    j = overpass(q)
    rows = []
    for e in j.get("elements", []):
        if e.get("type") != "way":
            continue
        t = e.get("tags", {})
        g = [[p["lat"], p["lon"]] for p in e.get("geometry", [])]
        if len(g) < 2 or not t.get("name"):
            continue
        L = sum(haversine_m(g[i - 1], g[i]) for i in range(1, len(g)))
        if L < min_len_m:
            continue
        rows.append({"id": e["id"], "name": t["name"], "aerialway": t.get("aerialway"),
                     "ref": t.get("ref"),
                     "bike": t.get("aerialway:bicycle") or t.get("bicycle"),
                     "len": round(L), "geom": g})
    rows.sort(key=lambda r: r["name"])
    return rows


def osm_named_ways(bbox, name_regex, highway_regex="path|track|footway|cycleway"):
    """Ways in `bbox` whose name matches, with geometry — for trails OSM has mapped by name.

    This is how the four Donnersberg trails are built: their own site's GPX deviated visibly from the
    OSM/OpenTopoMap base layer this app renders, and matching the base map matters more than picking the
    nominally most accurate source. See CLAUDE.md's Donnersberg note.
    """
    q = ('[out:json][timeout:240];way["highway"~"%s"]["name"~"%s"](%s);out tags geom;'
         % (highway_regex, name_regex, bbox))
    j = overpass(q)
    rows = []
    for e in j.get("elements", []):
        if e.get("type") != "way":
            continue
        g = [[p["lat"], p["lon"]] for p in e.get("geometry", [])]
        if len(g) < 2:
            continue
        rows.append({"id": e["id"], "name": e.get("tags", {}).get("name"),
                     "tags": e.get("tags", {}), "geom": g,
                     "len": round(sum(haversine_m(g[i - 1], g[i]) for i in range(1, len(g))))})
    return rows


def chain_ways(geoms, tol_m=25.0):
    """Stitch OSM way fragments into one ordered line. Returns (chain, leftovers).

    OSM splits a single trail into many ways wherever a tag changes, so a bike-park line arrives as 3-6
    disconnected fragments in arbitrary order and arbitrary direction. Concatenating them as they come
    produces a zig-zag across the mountain.

    Greedy endpoint matching: start from the longest fragment, then repeatedly attach whichever remaining
    fragment starts or ends within `tol_m` of the current chain's head or tail, reversing it if needed.

    **Always check both return values.** A non-empty `leftovers` means the fragments do not form one line —
    usually a branch or a same-named but separate trail — and the result should be treated as suspect
    rather than drawn. `docs/finale-ligure.md` records the same lesson from the other direction: letting a
    route renderer do relation-assembly beats reimplementing it, so prefer a clean single-track export when
    one exists and use this only when the source is raw ways.
    """
    segs = [list(g) for g in geoms if len(g) >= 2]
    if not segs:
        return [], []
    segs.sort(key=lambda g: cumulative_km(g)[-1], reverse=True)
    chain = segs.pop(0)
    changed = True
    while changed and segs:
        changed = False
        for i, s in enumerate(segs):
            for cand in (s, s[::-1]):
                if haversine_m(chain[-1][:2], cand[0][:2]) <= tol_m:
                    chain = chain + cand[1:]
                    segs.pop(i); changed = True; break
                if haversine_m(chain[0][:2], cand[-1][:2]) <= tol_m:
                    chain = cand[:-1] + chain
                    segs.pop(i); changed = True; break
            if changed:
                break
    return chain, segs


def norm_name(s):
    """Lowercase, strip everything non-alphanumeric — for matching operator names against OSM names."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def fuzzy_lookup(name, by_norm, cutoff=0.8):
    """Find `name` in a {norm_name: row} dict, tolerating mojibake in OSM's own name strings.

    A U+FFFD replacement character normalises to nothing, silently dropping a letter -- OSM's corrupted
    "S\ufffdraussaix" becomes "sraussaix", one character short of "seraussaix", so plain equality misses
    it. Some cases are not even recoverable this way (dreilaender's Schönebenbahn had to be fetched by
    way id instead).
    """
    k = norm_name(name)
    if k in by_norm:
        return by_norm[k]
    close = difflib.get_close_matches(k, list(by_norm.keys()), n=1, cutoff=cutoff)
    return by_norm[close[0]] if close else None


# ---------------------------------------------------------------------------------------------------
# Region assembly
# ---------------------------------------------------------------------------------------------------

def build_profile(coords, elevations, smooth=2):
    """Resample to an ELEVATION_PROFILES entry: [[km, m], ...] over the trail's own length.

    Point count follows length so a 40 km tour is not squeezed into the same 100 samples as a 1 km run --
    the app's chart and its hover-sync interpolate between whatever is here.

    Returns (profile, gain_m, loss_m). Note the gain/loss computed here is measured on the RESAMPLED
    profile, so it understates small undulations; prefer the operator's published numbers when they
    exist, exactly as `build_trail` does.
    """
    if len(coords) != len(elevations):
        raise ValueError("build_profile: %d coords vs %d elevations" % (len(coords), len(elevations)))
    ele = list(elevations)
    # Fill gaps: GPS glitches and missing <ele> read as None or an implausible ~0 in an alpine region.
    # The ~0 half of that sentence was only a comment until 2026-07-31 -- the code filled None alone, so a
    # SINGLE <ele>0</ele> in the middle of a track (Donnersberg's downloads had them throughout, which
    # build_trail catches because *every* value is 0) produced a full-depth dip and a matching phantom
    # climb back out. Found by tests/python/pipeline.py; it changes no committed region, verified by the
    # golden Laax rebuild in that same suite.
    # Not applied when every value is ~0: there is nothing to interpolate from, and build_trail's own
    # elevation-lookup path is what handles that case.
    if not all(e is None or abs(e) < 0.5 for e in ele):
        ele = [None if (e is not None and abs(e) < 0.5) else e for e in ele]
    for i, e in enumerate(ele):
        if e is None:
            back = next((ele[j] for j in range(i, -1, -1) if ele[j] is not None), None)
            fwd = next((ele[j] for j in range(i, len(ele)) if ele[j] is not None), None)
            ele[i] = back if back is not None else (fwd if fwd is not None else 0.0)
    if smooth:
        w = smooth
        ele = [sum(ele[max(0, i - w):i + w + 1]) / len(ele[max(0, i - w):i + w + 1])
               for i in range(len(ele))]
    cum = cumulative_km(coords)
    total = cum[-1]
    if total <= 0:
        raise ValueError("build_profile: zero-length track")

    def at(dk):
        if dk <= 0:
            return ele[0]
        if dk >= total:
            return ele[-1]
        for j in range(len(cum) - 1):
            if cum[j] <= dk <= cum[j + 1]:
                span = cum[j + 1] - cum[j]
                t = 0 if span == 0 else (dk - cum[j]) / span
                return ele[j] + t * (ele[j + 1] - ele[j])
        return ele[-1]

    n = 100 if total < 7 else (150 if total < 25 else 200)
    prof = [[round(total * k / (n - 1), 4), round(at(total * k / (n - 1)), 1)] for k in range(n)]
    gain = round(sum(max(0.0, prof[i + 1][1] - prof[i][1]) for i in range(n - 1)))
    loss = round(sum(max(0.0, prof[i][1] - prof[i + 1][1]) for i in range(n - 1)))
    return prof, gain, loss


def build_trail(trail_id, name, region, diff, raw_points, *, uphill=False,
                official=None, elevation=None, descend=True, eps_m=SIMPLIFY_EPS_M):
    """Turn raw GPX/OSM points into the three things a region JSON needs for one trail.

    Returns (lineTrails_entry, geo, profile).

    `official` is (len_km, up_m, down_m) from the operator/brochure when it exists, and is preferred over
    the GPX-derived figures so the region agrees with the rest of `lineTrails`. GPX-derived numbers are an
    acceptable fallback only where nothing official is published.

    `elevation` is an ElevationLookup (or any callable taking [[lat,lon],...]) used when the points carry
    no usable third element. Points whose elevation is exactly 0 in a mountain region are treated as
    missing -- that is the Donnersberg placeholder case, not sea level.

    `descend=True` flips the stored direction when the track climbs by more than 15 m end to end. Bike-park
    runs are gravity descents, and several operator exports are recorded uphill; the app draws Start/Ziel
    and direction arrows from the stored order, so this has to be right. Set descend=False for an uphill
    trail (and pass uphill=True), or where the recording direction is already known good.
    """
    pts = douglas_peucker(dedupe_points(raw_points), eps_m)
    if len(pts) < 2:
        raise ValueError("%s: fewer than 2 points after simplification" % trail_id)

    ele = [p[2] if len(p) > 2 else None for p in pts]
    if all(e is None or abs(e) < 0.5 for e in ele):
        if elevation is None:
            raise ValueError("%s: no usable <ele> and no elevation lookup given" % trail_id)
        ele = elevation([[p[0], p[1]] for p in pts])

    if descend and not uphill:
        first = next((e for e in ele if e is not None), None)
        last = next((e for e in reversed(ele) if e is not None), None)
        if first is not None and last is not None and last > first + 15:
            pts = pts[::-1]
            ele = ele[::-1]

    coords = [[round(p[0], 6), round(p[1], 6)] for p in pts]
    prof, gain, loss = build_profile(coords, ele)
    if official:
        length, up, down = official
    else:
        length, up, down = round(cumulative_km(coords)[-1], 2), gain, loss

    entry = {"id": trail_id, "name": name, "region": region, "diff": diff,
             "len": length, "up": up, "down": down}
    if uphill:
        entry["uphill"] = True
    # No `url`: the info panel's "Zur Tour auf der Website" link was dropped on 2026-07-28 at the user's
    # request and the field went with it, so writing one here would only put dead weight back into the data.
    return entry, coords, prof


#: The keys a region file carries BESIDES the three a build produces. Each is written by a different tool
#: at a different time -- `places` by add_region_places.py, `lifts` by add_lifts.py, `trailSegments` by the
#: Tour builds and close_loop_gaps.py, `ratings` by apply_trailforks_ratings.py -- and none of them is
#: recomputable from the trails alone. See write_region's own docstring for why they are carried, not asked for.
REGION_SIDE_KEYS = ("places", "lifts", "trailSegments", "ratings")


def carried_names(carried):
    """`["lifts (2)", ...]` -> `{"lifts", ...}`; see write_region's ratings rule."""
    return {c.split(" ")[0] for c in carried}


def write_region(path, line_trails, trail_geo, elevation_profiles, places=None, lifts=None,
                 trail_segments=None, ratings=None, verbose=True):
    """Write a regions/<key>.json in the app's own shape and formatting.

    The separators match the existing files, so a rebuild produces a readable diff rather than one giant
    changed line.

    **A side key the caller does not pass is CARRIED FORWARD from the file being overwritten, not dropped.**
    This function used to write only what it was handed, and that is a footgun that has cost this project
    real data more than once: commit `b881699` silently removed donnersberg.json's entire `trailSegments`
    key (nobody noticed until a user reported a Trailrunde rendering with no coloured component stretches),
    `add_region_places.py --force` removed a region's `ratings` block while leaving the per-trail numbers
    in place, and a plain rebuild deleted a region's `lifts`. Roughly a third of the 25 call sites had
    already grown a hand-written `places=d.get("places"), lifts=d.get("lifts")` to route around it -- which
    is the tell that the default was wrong, since every new caller has to rediscover the same workaround.

    The distinction is **missing vs. deliberately empty**, the same one `restoreActiveState()` draws in the
    app: `lifts=None` (or omitted) means "I have nothing to say about lifts, keep what is there", while
    `lifts=[]` means "this region has no lifts" and really clears them.

    `ratings` gets one extra rule, because carrying it blindly would be a lie: a rebuild replaces every
    trail object, so the per-trail `rate`/`votes`/`pop` go with them. If none of the trails being written
    carries a rating, the block is dropped even when the old file had one -- and `verbose` says so, since
    the fix is to re-run tools/apply_trailforks_ratings.py.
    """
    prev = {}
    if os.path.exists(path):
        try:
            prev = json.load(open(path, encoding="utf-8"))
        except Exception:
            prev = {}
    incoming = {"places": places, "lifts": lifts, "trailSegments": trail_segments, "ratings": ratings}
    kept = {}
    carried = []
    for key in REGION_SIDE_KEYS:
        if incoming[key] is not None:
            kept[key] = incoming[key]
            continue
        if prev.get(key):
            kept[key] = prev[key]
            carried.append("%s (%d)" % (key, len(prev[key])))
    # Only a CARRIED ratings block is second-guessed. One the caller passed explicitly is its own statement
    # -- apply_trailforks_ratings.py writes the block and the per-trail numbers in the same call, and a
    # rounding rule here must not overrule that.
    if "ratings" in carried_names(carried) and not any(t.get("rate") for t in line_trails):
        kept.pop("ratings", None)
        carried = [c for c in carried if not c.startswith("ratings")]
        if verbose:
            print("  write_region: `ratings` verworfen -- kein Trail traegt mehr eine Bewertung. "
                  "tools/apply_trailforks_ratings.py erneut laufen lassen.")
    if verbose and carried:
        print("  write_region: uebernommen aus der alten Datei: %s" % ", ".join(carried))
    # The key ORDER is part of the file's shape: three built keys, then places, then the optional rest.
    data = {"lineTrails": line_trails, "trailGeo": trail_geo,
            "elevationProfiles": elevation_profiles, "places": kept.get("places") or []}
    for key in ("trailSegments", "lifts", "ratings"):
        if kept.get(key):
            data[key] = kept[key]
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(", ", ": "))
    return data


def region_summary(data):
    """A one-glance report: counts per sub-region and per difficulty, plus the catalog bounds."""
    from collections import Counter
    trails = data["lineTrails"]
    return {
        "trails": len(trails),
        "perRegion": dict(Counter(t["region"] for t in trails)),
        "perDiff": dict(Counter(t["diff"] for t in trails)),
        "lifts": len(data.get("lifts") or []),
        "bounds": bounds_of(data["trailGeo"]),
    }
