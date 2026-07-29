"""Build regions/bikekingdom.json from the harvested Outdooractive data plus the user's own catalogue.

Two sources, and each is authoritative for a different thing:
  Material/BikeKingdom/oa_tours.json      geometry (with real per-point elevation), length, ascent, descent
  Material/BikeKingdom/Trails Lenzerheide.ods   the user's own difficulty and sub-region for 104 trails

The ods wins on difficulty and sub-region -- it is a first-hand catalogue from a visit, and CLAUDE.md is
explicit that difficulties are not to be invented. The API wins on geometry and the numbers.

Run:  python tools/build_bikekingdom.py            (then update_region_versions.py + validate_region.py)
"""
import io
import json
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import (build_profile, douglas_peucker, dedupe_points, bounds_of,  # noqa
                               write_region, haversine_m, cumulative_km, overpass, chain_ways,
                               ElevationLookup)

#: Trails whose geometry comes from OSM instead of the Outdooractive sections, keyed by lower-case title.
#: Only for trails whose OA sections do not form one line while OSM has the whole trail mapped -- and it is
#: the right call there for the reason the four Donnersberg trails come from OSM too: this app renders
#: OSM/OpenTopoMap tiles, so OSM's line is the one every user compares ours against on the same screen.
#: "701 Brambi Flow" arrives from OA as two pieces 348 m apart (the stretch between them is mapped once, as
#: part of Rock'n'Roll); OSM has it as seven ways that chain into one continuous 2 643 m line.
OSM_GEOMETRY = {
    "701 brambi flow": r"^Brambi Flow$",
}
OSM_BBOX = "46.64,9.42,46.89,9.77"

#: Place labels, coordinates from OSM `node[place]` (never typed -- a hand-typed Samnaun sat 1 460 m from the
#: village). They live HERE rather than only in the region file, because this script rewrites that file from
#: scratch: the first version wrote no places at all, so a rebuild for one trail's geometry silently dropped
#: all 19 of them, and the tours script that runs afterwards only restores lifts and tours. Every one of a
#: region's four pieces has to survive a rebuild -- see docs/adding-a-region.md.
#: Picked as one reference point per area plus the larger settlements; Zorten, Alp Stätz, Scharmoin,
#: Brambrüesch and Innerarosa were dropped again at the user's request as too fine-grained.
PLACES = [
    ("Chur", 46.85475, 9.52649), ("Passugg", 46.82942, 9.54748), ("Maladers", 46.83628, 9.5604),
    ("Malix", 46.81187, 9.53137), ("Praden", 46.82409, 9.58156), ("Tschiertschen", 46.81739, 9.60665),
    ("Churwalden", 46.77845, 9.54297), ("Parpan", 46.75963, 9.55982), ("Valbella", 46.74579, 9.55415),
    ("Lenzerheide", 46.72803, 9.55844), ("Sporz", 46.71356, 9.54088), ("Arosa", 46.77972, 9.67814),
    ("Maran", 46.79296, 9.68185), ("Litzirüti", 46.79872, 9.70278), ("Langwies", 46.82056, 9.71264),
    ("Medergen", 46.80444, 9.73942), ("Tiefencastel", 46.66156, 9.57649),
    ("Alvaschein", 46.67506, 9.55032), ("Mon", 46.64996, 9.56398),
]

#: Two consecutive sections further apart than this do not form one line. Same value as the pipeline's
#: MAX_TRACK_GAP_M, for the same reason: beyond it, concatenating welds a phantom straight line onto the map.
MAX_SECTION_GAP_M = 120.0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, "Material", "BikeKingdom")
OUT = os.path.join(ROOT, "Trailmap App", "regions", "bikekingdom.json")

DIFF = {"sehr einfach": "gruen", "einfach": "blau", "mittel": "rot", "schwierig": "schwarz"}
SUBREGION = {  # ods label -> our sub-region key
    "Alpenbikepark Chur": "bk_park_chur",
    "Bike Kingdom Park Lenzerheide": "bk_park_lenzerheide",
    "Bear Mountains": "bk_bear_mountains",
    "Western Summits": "bk_western_summits",
    "Red Peak": "bk_red_peak",
    "The Capital": "bk_the_capital",
    "Steep Trees": "bk_steep_trees",
    "Southern Delights": "bk_southern_delights",
}
# Difficulties the user supplied for trails the ods does not list (asked for explicitly, not guessed).
EXTRA_DIFF = {
    "bike attack traverse": ("rot", "bk_red_peak"),
    "ninos gold-trail": ("rot", "bk_western_summits"),
    "hexenwald": ("blau", "bk_southern_delights"),
    "val malera trail": ("blau", "bk_southern_delights"),
    # Added 2026-07-29 on the user's request, with rot given by them. Outdooractive marks it "geschlossen";
    # it is in anyway, and carries no closed flag -- same rule as the lifts, nothing in this app syncs
    # operating status, so a hardcoded one would rot while looking authoritative (docs/lifts-feature.md).
    # bk_red_peak, not bk_park_lenzerheide: it runs Scharmoin -> Lenzerheide right beside the park lines
    # (79 m from FLOWline at its closest), but that sub-region is exactly the five built park lines, and
    # this is a natural trail in the Rothorn area like "Got da Lai" next to it.
    "wasserfall lenzerheide": ("rot", "bk_red_peak"),
    # Corrected by the user 2026-07-29. It has no ods row, so it had inherited the sub-region of its nearest
    # trail and landed in the park -- but it feeds the Weisshorn Speed chairlift, whose own closest trails are
    # Red Peak's (Motta Express, 8 m).
    "access weisshorn speed": ("gruen", "bk_red_peak"),
}
# ods spelling -> API spelling. Each one verified by eye against the harvested titles.
ALIAS = {
    "sytleline": "shorelinestyleline",      # ods typo (SYTLE) and the API keeps the pair as one trail
    "shoreline": "shorelinestyleline",
    "brambueschchurwaldentrail": "brambrueschchurwaldentrail",   # ods drops the r
    "brambueschpradaschiertrail": "brambrueschpradaschiertrail",
    "aufstiegmittelstation": "aufstiegmittelstationweisshorn",   # ods truncated
}
# Lower halves of a park line: same line, same difficulty as their parent.
INHERIT = {"flowline lower": "flowline", "primeline lower": "primeline"}


def norm(s):
    s = s.lower().replace("–", "-").replace("—", "-").replace("’", "'")
    # Transliterate rather than strip: stripping turned "Brambüesch" into "brambesch" on one side and
    # "Brambrüesch" into "brambresch" on the other, so the alias meant to bridge that missing r could never
    # match. Both sides go through this, so it stays consistent for Hörnli, Älplisee, Löser and the rest.
    for a, b in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss"), ("é", "e"), ("à", "a")):
        s = s.replace(a, b)
    s = re.sub(r"\b(sektion|section)\s*\d+\b", "", s)
    s = re.sub(r"\bjump\s*section\b", "", s)
    s = re.sub(r"^\d{3}\s*", "", s)                 # "703 Rock'n'Roll" -> "Rock'n'Roll"
    return re.sub(r"[^a-z0-9]", "", s)


def read_ods():
    ns = {"table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
          "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
    root = ET.fromstring(zipfile.ZipFile(os.path.join(MAT, "Trails Lenzerheide.ods")).read("content.xml"))
    rows = []
    for tr in root.find(".//table:table", ns).findall("table:table-row", ns):
        cells = []
        for tc in tr.findall("table:table-cell", ns):
            rep = int(tc.get("{%s}number-columns-repeated" % ns["table"], "1"))
            txt = " ".join("".join(p.itertext()).strip() for p in tc.findall("text:p", ns)).strip()
            for _ in range(min(rep, 30)):
                cells.append(txt)
        while cells and cells[-1] == "":
            cells.pop()
        if cells:
            rows.append(cells)
    out = {}
    for r in rows[2:]:
        if len(r) < 3 or r[1] not in ("sehr einfach", "einfach", "mittel", "schwierig", "Zufahrtsweg"):
            continue
        key = ALIAS.get(norm(r[0]), norm(r[0]))
        out[key] = {"schwierigkeit": r[1], "region": r[2].strip()}
    return out


def parse_geometry(s):
    """"lon,lat,ele lon,lat,ele ..." -> [[lat, lon, ele], ...]; the app's own order is lat,lon."""
    pts = []
    for token in s.split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        lon, lat = float(parts[0]), float(parts[1])
        ele = float(parts[2]) if len(parts) > 2 and parts[2] not in ("", "0") else None
        pts.append([lat, lon] + ([ele] if ele is not None else []))
    return pts


def osm_line(name_regex):
    """The named trail as ONE ordered [[lat, lon], ...] line from OSM. Raises if it does not chain up.

    OSM splits a trail wherever a tag changes, so this arrives as several ways in arbitrary order and
    direction; chain_ways() stitches them by endpoint. Its leftovers are tolerated only while they are
    negligible next to the chain (Brambi Flow has one redundant 10 m stub whose ends are already on the
    chain) -- a real leftover means the ways do not form a single line and must not be drawn as one.
    """
    j = overpass('[out:json][timeout:180];way["name"~"%s"](%s);out tags geom;' % (name_regex, OSM_BBOX))
    geoms = [[[p["lat"], p["lon"]] for p in e["geometry"]] for e in j["elements"]
             if len(e.get("geometry") or []) >= 2]
    if not geoms:
        raise SystemExit("OSM has no way matching %r" % name_regex)
    chain, left = chain_ways(geoms)
    total = sum(cumulative_km(g)[-1] for g in geoms)
    if cumulative_km(chain)[-1] < 0.9 * total:
        raise SystemExit("%r: ways do not chain into one line (%.0f m of %.0f m, %d left over)"
                         % (name_regex, cumulative_km(chain)[-1] * 1000, total * 1000, len(left)))
    return [[round(c[0], 6), round(c[1], 6)] for c in chain]


def is_access(title):
    return bool(re.match(r"^(access|uphill|aufstieg|connection|umleitung)\b", title.strip(), re.I))


def main():
    tours = json.load(io.open(os.path.join(MAT, "oa_tours.json"), encoding="utf-8"))
    ods = read_ods()

    # Sections of one numbered trail collapse into a single entry (the user does not want the sections).
    # Sort by the section number so the concatenation runs top to bottom.
    groups = {}
    for tid, t in tours.items():
        key = norm(t["title"])
        m = re.search(r"(?:sektion|section)\s*(\d+)", t["title"], re.I)
        order = int(m.group(1)) if m else (99 if re.search(r"jump", t["title"], re.I) else 0)
        groups.setdefault(key, []).append((order, tid, t))
    for g in groups.values():
        g.sort(key=lambda x: x[0])

    trails, geo, profs, unresolved, gaps = [], {}, {}, [], []
    elev = ElevationLookup(os.path.join(MAT, "elevation_cache.json"))
    for key, members in sorted(groups.items()):
        base = members[0][2]
        title = re.sub(r"\s*:\s*(Sektion|Section)\s*\d+\s*$", "", base["title"]).strip()
        title = re.sub(r"\s*:\s*Jump Section\s*$", "", title).strip()

        # Geometry: concatenate the sections in order -- but ONLY where each one actually continues where the
        # previous ended. A blind extend() welded a 1065 m straight line across the map into
        # "703 Rock'n'Roll", because its "Jump Section" is a parallel variant beside section 2 and order=99
        # parks it behind section 4. Sections that do not connect start a new chain; the longest chain wins
        # and the rest is reported, never bridged (the user's standing rule: leave the honest gap).
        chains, dropped = [], []
        for _, _, t in members:
            if not t.get("geometry"):
                continue
            seg = parse_geometry(t["geometry"])
            if len(seg) < 2:
                continue
            if chains and haversine_m(chains[-1][-1], seg[0]) <= MAX_SECTION_GAP_M:
                chains[-1].extend(seg)
            else:
                chains.append(list(seg))
        if not chains:
            unresolved.append((title, "keine Geometrie"))
            continue
        chains.sort(key=lambda c: cumulative_km(c)[-1], reverse=True)
        raw = chains[0]
        for c in chains[1:]:
            dropped.append(round(cumulative_km(c)[-1] * 1000))
        from_osm = OSM_GEOMETRY.get(title.lower())
        if from_osm:
            raw = osm_line(from_osm)
            dropped = []                    # OSM has the whole trail; nothing is left out
            print("   %-40s aus OSM: %d Punkte, %d m"
                  % (title, len(raw), round(cumulative_km(raw)[-1] * 1000)))
        elif dropped:
            gaps.append((title, dropped, round(cumulative_km(raw)[-1] * 1000)))
        pts = douglas_peucker(dedupe_points(raw))
        coords = [[round(p[0], 6), round(p[1], 6)] for p in pts]
        eles = [p[2] if len(p) > 2 else None for p in pts]
        # OSM carries no elevation at all, so a trail taken from there needs a DEM lookup -- simplified
        # first, so it is a few dozen points rather than a few hundred, and cached on disk between runs.
        if all(e is None for e in eles):
            eles = elev(coords)

        info = ods.get(key)
        extra = EXTRA_DIFF.get(title.lower())
        access = is_access(title)
        if info and info["schwierigkeit"] != "Zufahrtsweg":
            diff = DIFF[info["schwierigkeit"]]
            region = SUBREGION[info["region"]]
        elif info:                                  # ods says "Zufahrtsweg"
            diff, region, access = "gruen", SUBREGION[info["region"]], True
        elif extra:
            diff, region = extra
        elif norm(title) in {norm(k): 1 for k in INHERIT}:
            parent = ods.get(norm(INHERIT[title.lower()]))
            diff = DIFF[parent["schwierigkeit"]]
            region = SUBREGION[parent["region"]]
        elif access:
            diff, region = "gruen", None            # region filled in below, from what it serves
        else:
            unresolved.append((title, "keine Schwierigkeit"))
            continue

        # Sum the sections' own official figures rather than recomputing from the simplified line -- but only
        # while every section is actually drawn. Where a section was dropped as disconnected, the official sum
        # would describe a line longer than the one on the map, so the drawn line's own figures are used
        # instead and the difference is visible in the report rather than hidden in a mismatched number.
        prof_pre, gain_pre, loss_pre = build_profile(coords, eles)
        if dropped or from_osm:
            # An OSM line is longer than the sum of the OA sections (it includes the stretch OA maps only
            # once, under the other trail that shares it), so the published sum would understate the drawn
            # line -- the drawn line's own figures are the honest ones here.
            length, up, down = cumulative_km(coords)[-1], gain_pre, loss_pre
        else:
            length = sum((t.get("length") or 0) for _, _, t in members) / 1000.0
            up = sum((t.get("ascent") or 0) for _, _, t in members)
            down = sum((t.get("descent") or 0) for _, _, t in members)

        # norm() for the id too, so "Fanüllatobel" does not become "fan_llatobel"
        slug = title.lower()
        for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
            slug = slug.replace(a, b)
        entry = {"id": "bk_" + re.sub(r"[^a-z0-9]+", "_", slug).strip("_"),
                 "name": title, "region": region, "diff": diff,
                 "len": round(length, 2), "up": int(up), "down": int(down)}
        # An access route that climbs gets the uphill flag too, so the existing ⚡ filter covers it. Decided
        # from the numbers, not the name: "Down to Town" and "Höhenweg Alp Scharmoin" are called connections
        # but descend, and calling those uphill would be wrong.
        # No `access` flag and no special rendering: the user's call -- "Mach die Access Trails einfach grün.
        # Sonst haben wir Sonderbehandlung." Green already says "technically easy", which is what a fire road
        # is. `uphill` stays, because it is not special treatment -- the ⚡ badge and its filter exist already,
        # and it is decided from the numbers, not the name: "Down to Town" and "Höhenweg Alp Scharmoin" are
        # called connections but descend, so calling those uphill would be wrong.
        if access and up > 2 * down:
            entry["uphill"] = True
        trails.append(entry)
        geo[entry["id"]] = coords
        # build_profile returns (profile, gain, loss) -- storing the whole tuple gave every trail a
        # "profile" of exactly 3 entries, which the validator's ">= 2 points" check happily accepted.
        profs[entry["id"]] = prof_pre

    # Access routes with no ods entry inherit the sub-region of the nearest trail that has one -- they exist
    # to serve those trails, so that is where they belong in the list.
    placed = [(t, geo[t["id"]]) for t in trails if t["region"]]
    for t in trails:
        if t["region"]:
            continue
        mine = geo[t["id"]]
        best, bestd = None, 1e18
        for other, ocoords in placed:
            d = min(haversine_m(mine[0], c) for c in ocoords[::5])
            d = min(d, min(haversine_m(mine[-1], c) for c in ocoords[::5]))
            if d < bestd:
                bestd, best = d, other["region"]
        t["region"] = best

    places = [{"name": n, "lat": la, "lng": lo} for n, la, lo in PLACES]
    data = write_region(OUT, trails, geo, profs, places=places)
    print("Trails: %d, Orte: %d" % (len(trails), len(places)))
    print("   (Lifte und Touren ergaenzt tools/build_bikekingdom_tours.py -- danach laufen lassen)")
    from collections import Counter
    print("je Unterregion:", dict(Counter(t["region"] for t in trails)))
    print("je Schwierigkeit:", dict(Counter(t["diff"] for t in trails)))
    print("Zufahrtswege: %d, davon uphill: %d"
          % (sum(1 for t in trails if t.get("access")), sum(1 for t in trails if t.get("uphill"))))
    print("bounds:", bounds_of(geo))
    if gaps:
        print("\nSektionen VERWORFEN, weil sie nicht anschliessen (Luecke > %.0f m):" % MAX_SECTION_GAP_M)
        for name, dropped, kept in gaps:
            print("   %-40s gezeichnet %5d m, weggelassen %s"
                  % (name, kept, " + ".join("%d m" % x for x in dropped)))
    if unresolved:
        print("\nNICHT gebaut:")
        for name, why in unresolved:
            print("   %-44s %s" % (name, why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
