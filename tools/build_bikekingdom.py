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
from trailmap_pipeline import build_profile, douglas_peucker, dedupe_points, bounds_of, write_region  # noqa

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

    trails, geo, profs, unresolved = [], {}, {}, []
    for key, members in sorted(groups.items()):
        base = members[0][2]
        title = re.sub(r"\s*:\s*(Sektion|Section)\s*\d+\s*$", "", base["title"]).strip()
        title = re.sub(r"\s*:\s*Jump Section\s*$", "", title).strip()

        # geometry: concatenate the sections in order, then de-duplicate and simplify once over the whole line
        raw = []
        for _, _, t in members:
            if t.get("geometry"):
                raw.extend(parse_geometry(t["geometry"]))
        if len(raw) < 2:
            unresolved.append((title, "keine Geometrie"))
            continue
        pts = douglas_peucker(dedupe_points(raw))
        coords = [[round(p[0], 6), round(p[1], 6)] for p in pts]
        eles = [p[2] if len(p) > 2 else None for p in pts]

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

        # sum the sections' own official figures rather than recomputing from the simplified line
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
        prof, _gain, _loss = build_profile(coords, eles)
        profs[entry["id"]] = prof

    # Access routes with no ods entry inherit the sub-region of the nearest trail that has one -- they exist
    # to serve those trails, so that is where they belong in the list.
    placed = [(t, geo[t["id"]]) for t in trails if t["region"]]
    from trailmap_pipeline import haversine_m
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

    data = write_region(OUT, trails, geo, profs)
    print("Trails: %d" % len(trails))
    from collections import Counter
    print("je Unterregion:", dict(Counter(t["region"] for t in trails)))
    print("je Schwierigkeit:", dict(Counter(t["diff"] for t in trails)))
    print("Zufahrtswege: %d, davon uphill: %d"
          % (sum(1 for t in trails if t.get("access")), sum(1 for t in trails if t.get("uphill"))))
    print("bounds:", bounds_of(geo))
    if unresolved:
        print("\nNICHT gebaut:")
        for name, why in unresolved:
            print("   %-44s %s" % (name, why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
