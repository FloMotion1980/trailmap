# -*- coding: utf-8 -*-
"""Build regions/nordvogesen.json -- Nordvogesen / Vosges du Nord (Wissembourg and everything north
of Colmar), from Trailforks.

Requested by the user 2026-08-19: "Die Noerdlichen Vogesen. Vor allem die Region rund um
wissembourg. Also ungefaehr alles noerdlich von Colmar." The southern boundary was then pinned exactly
by a red line the user drew on a Trailforks map -- everything below it is Suedvogesen. That line lives in
`tools/vogesen_boundary.py`, and every build here audits itself against it.

GEOMETRY + ELEVATION -- a better source than the Harz build had, found here: a Trailforks trail page
embeds not only the `encodedpath` polyline but a full
`new ElevationChart({... sections: [{"points":[{"id":0,"x":<metres along>,"y":<elevation m>,
"lat":..,"lng":..,"grade":..}, ...]}]})` config. That carries lat/lng AND real elevation AND the
cumulative distance per point, so this region needs NO elevation API at all (build_harz.py's own
docstring states Trailforks embeds no profile -- that is either no longer true or was missed then).
The profile's last `x` reproduces Trailforks' own stated trail distance, which is what proves the
extraction is not corrupted -- the same verify-by-distance discipline the polyline-decode notes insist
on. Both sources are harvested and cross-checked against each other per trail (CHECK_TOLERANCE_M).

Harvest inputs, all produced through the user's own logged-in Chrome (see
`trailforks-anonymous-polyline-extraction`):
  Material/Vogesen/vogesen_table_full.json -- trail list: name, riding area, TF difficulty, activity
                                         type, one Trailforks region TABLE view per sub-region
                                         (not per trail)
  Material/Vogesen/vogesen_geo.json   -- per slug {c: decoded encodedpath, p: ElevationChart sections}
  Material/Vogesen/vogesen_geo_black.json -- the same, for the 38 trails the first list missed

THE TABLE URL'S `difficulty=` LIST MUST NAME EVERY CODE, and this region proves why for the second time
(the first was `finale-difficulty-realignment`). The list carried over from the Varazze/Harz recipe was
`difficulty=3,4,9,5,1,7,2,6,8`, which looks exhaustive and is not: **code 10 is `Severe / Black`**, and
leaving it out silently dropped THE ENTIRE schwarz tier -- 38 trails, including all 8 black ones in Barr
and 19 around Saint-Die/Raon-l'Etape. Nothing about the output looked wrong; it was found only by
comparing a region's row count against a per-code partition (`d1`=Access, `d3`=Easy/Green,
`d4`=Intermediate/Blue, `d7`=Secondary Access, `d9`=Difficult/Red, `d10`=Severe/Black, measured on
`barr`; 11 carries "Extremely Difficult", 2/5/6/8/12+ were empty everywhere here). Also note an
UNFILTERED table URL is not the safe fallback -- it returns FEWER rows (66 for Barr against 79), i.e. it
applies a default filter of its own.

DIFFICULTY: no operator publishes a grade for these -- they are community/Club-Vosgien trails in a
natural park, not a bike park with a signposted scale -- so the standing "operator's grade wins" rule
falls through to its documented fallback, Trailforks' own per-trail rating.
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import build_trail, haversine_m, region_summary, write_region
from vogesen_boundary import report as report_boundary
from vogesen_boundary import side, override

#: Which side of the red line this region is. See tools/vogesen_boundary.py.
EXPECT_SIDE = "nord"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: The harvest inputs, checked in for the same reason Material/Harz/harz_tf_geo.json is: without
#: them this script does nothing on a fresh clone. See Material/Vogesen/README.md.
WORK = os.path.join(ROOT, "Material", "Vogesen")
OUT = os.path.join(ROOT, "Trailmap App", "regions", "nordvogesen.json")

#: A trail whose profile length and whose encodedpath length disagree by more than this is reported --
#: the two come from the same Trailforks record and should agree; a real gap means one of them was
#: truncated, and that trail needs looking at rather than being built silently from the shorter one.
CHECK_TOLERANCE_M = 60.0

# Trailforks' own difficulty titles, exactly as they appear in the region table's dicon `title`
# attribute, mapped onto this app's four colours. The last one is Trailforks' double-black.
TF_DIFF = {
    "Easy / Green Circle": "gruen",
    "Intermediate / Blue Square": "blau",
    "Difficult / Red": "rot",
    "Severe / Black": "schwarz",
    "Very Difficult / Black Diamond": "schwarz",
    "Extremely Difficult & dangerous, pros only!": "schwarz",
}
# Rows carrying these instead of a real grade are fireroads/access, not rated descents -- excluded from
# the region entirely, the same rule as Bike Kingdom's fire roads and Varazze's 13 access rows.
ACCESS_DIFF = {"Access Trail, Road or Doubletrack", "Secondary Access Road/Trail"}

# Which Trailforks region a trail was harvested from decides its sub-region here. Trailforks files
# these trails under 44 communes -- far too many to be sidebar chips, so they are bracketed into
# geographic groups the way Sauerland/Upland and the Harz were. Colours are distinct within this group
# and against --forest (#2f5d3a).
#
# Keyed on the harvested REGION SLUG, not on the table's "riding area" text: 28 rows carry a blank or
# parent-level area cell (all 18 of Hohlandsbourg's, all 7 of Lac Blanc's, two Niederbronn ones), and
# the slug is always present and unambiguous. Anything the slug cannot settle falls through to a
# nearest-centroid assignment, so a trail is never dropped for a missing label.
SUBREGIONS = {
    "wissembourg": ("Wissembourg / Nordvogesen", "#3a6ea5", [
        "wissembourg-62557", "cleebourg", "climbach", "lembach", "goersdorf", "lampertsloch",
        "soultzsousforets", "wingen", "obersteinbach", "niedersteinbach", "windstein"]),
    # `dambach` is Dambach-Neunhoffen in the NORTHERN Vosges (canton Niederbronn, 49.008 N -- Chateau
    # de Schoeneck sits above it), NOT Dambach-la-Ville down by Barr. Its six trails were filed under
    # Barr/Mont-Sainte-Odile by a first version of this map, 65 km from where they actually are, which
    # is why every sub-region's own extent is printed at the end of a build.
    "niederbronn": ("Niederbronn / Heidenkopf", "#a8452f", [
        "niederbronn", "heidenkopf", "oberbronn", "niederbronn-bike-trail", "dambach"]),
    "saverne": ("Saverne / Dabo / Wangenbourg", "#8a6a2f", [
        "saverne", "haegen", "reinhardsmunster", "dabo", "phalsbourg", "danneetquatrevents",
        "lutzelbourg", "cosswiler", "wangenbourg"]),
    "sainteodile": ("Barr / Mont Sainte-Odile", "#6a3a8a", [
        "barr", "boersch", "le-hohwald", "breitenbach"]),
    "bruche": ("Bruche-Tal", "#2f8a7a", ["lutzelhouse-74628", "muhlbachsurbruche"]),
    "ville": ("Val de Villé / Ribeauvillé", "#c2185b", [
        "neubois", "liepvre", "breitenau", "ribeauville"]),
    "vosges_ouest": ("Vogesen West (Saint-Dié)", "#7a7a2f", [
        "saintdie-des-vosges", "raon-l-etape", "raon-l-etape-41060", "lac-de-la-maix", "donon"]),
}

# Harvested, verified, and deliberately NOT part of this region: everything BELOW the red line the user
# drew on 2026-08-19 ("Ich wuerde alles unter der eingezeichneten roten Linie zu der Region Suedvogesen
# zaehlen"). See tools/vogesen_boundary.py for the line itself and for each bracket's measured distance
# from it. These rows stay in the harvest files and are built by tools/build_suedvogesen.py; listed here
# so the exclusion is visible rather than implicit in a missing key.
SOUTH_REGS = {
    "munster", "munster-valley-22230", "stosswihr", "luttenbachpresmunster", "metzeral", "hohrod",
    "whirauval", "breitenbachhautrhin", "orbey", "guebwiller", "buhl", "orschwihr", "bergholtzzel",
    "soultzhautrhin", "bikepark-du-markstein-39293", "thann", "mollau", "moosch", "urbes", "fellering",
    "kruth", "masevaux", "dolleren", "bourbachlehaut", "wegscheid", "giromagny",
    "ballon-d-alsace-31436", "mulhouse-south-alsace-32280", "la-bresse", "bikepark-la-bresse-25099",
    "enduro-bressaud-30938", "ventron", "cornimont", "saulxuressurmoselotte", "le-menil", "bussang",
    "remiremont-9316", "vagney-37825", "gerardmer", "xonruptlongemer", "epinal", "vallon-d-olima",
    "vallon-d-olima-33741", "la-40-semaine-42294", "glaserberg-25360",
}

EXCLUDED_REGS = {
    "hohlandsbourg": "Colmar / Hohlandsbourg -- 5 km south of the line",
    "wintzenheim": "Colmar -- south of the line",
    "wettolsheim-9426": "Colmar -- south of the line",
    # The Kaysersberg valley, 2-10 km south of the line. This is where the Lac Blanc bike park is, which
    # the user had named as a SOUTHERN park from the start -- the line settles it the same way.
    "labaroche": "Kaysersberg valley -- south of the line",
    "lac-blanc-bike-park": "Kaysersberg valley -- south of the line",
    "le-bonhomme": "Kaysersberg valley -- south of the line (2 km, inside the reading error)",
    "trois-epis": "Kaysersberg valley -- south of the line",
    "turckheim": "Kaysersberg valley -- south of the line",
}
# Trails whose ground `pfaelzerwald.json` ALREADY SHIPS. The Vosges du Nord and the Pfaelzerwald are one
# forest massif either side of the border and our two regions genuinely overlap there; with both groups
# activated the same ground would be drawn twice, under two names and two difficulty colours. The user's
# call (2026-08-19): "Lass die doppelten Trails im Pfaelzer Wald. Doppelt brauche wir sie nicht." -- so
# the Pfaelzerwald keeps them and these three go.
#
# Note this is the OPPOSITE direction to the project's usual "Trailforks wins on name and geometry" rule,
# deliberately: all four Pfaelzerwald counterparts are referenced by Tour 14 and Tour 15's
# `TRAIL_SEGMENTS`, and repointing a loop's segments at a replacement id is not built (see
# `trailforks-duplicate-detection-method`). Dropping on this side costs nothing structural.
#
# Measured containment against pfaelzerwald.json, per point at 20 m (tools/region_dupe_check.py, plus a
# per-point coverage pass against EVERY pfaelzerwald line, not just the named counterpart). The
# `uncovered` figure is what leaving them out actually costs -- recorded so the choice stays reversible
# rather than being rediscovered:
DUPLICATE_OF_PFAELZERWALD = {
    # 89 % covered; contains pw_bundenthal_sued_trail_1 + _2 whole. A clean duplicate, ~56 m uncovered.
    "sindelsberg-zickzack": "duplicates pw_bundenthal_sued_trail_1/_2 (89 % covered)",
    # 57 % covered; contains pw_bundenthal_suedost_trail_1 (844 m) to 77 %. ~692 m uncovered.
    "kuhnenkopf": "duplicates pw_bundenthal_suedost_trail_1 (57 % covered, ~692 m uncovered)",
    # 45 % covered; contains pw_bundenthal_suedost_trail_2 (486 m) whole. ~1 095 m uncovered -- the
    # largest single loss of the three, and the one to reinstate first if the longer line is ever wanted.
    "zeppelinhalde": "duplicates pw_bundenthal_suedost_trail_2 (45 % covered, ~1 095 m uncovered)",
}

REG_TO_SUB = {r: k for k, (_l, _c, regs) in SUBREGIONS.items() for r in regs}

ID_PREFIX = "nv_"


def slug_to_id(slug):
    return ID_PREFIX + re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")


def profile_points(entry):
    """Flatten the harvested ElevationChart sections into [[lat, lon, ele], ...] plus its own length."""
    pts, last_x = [], 0.0
    for sec in entry.get("p") or []:
        for lat, lng, y, x in sec:
            pts.append([lat, lng, y])
            last_x = max(last_x, float(x))
    return pts, last_x


def line_length_m(pts):
    return sum(haversine_m(pts[i - 1], pts[i]) for i in range(1, len(pts)))


def resolve_sub(meta, slug=None):
    """Sub-region for this row, or a sentinel string the caller reports/skips on.

    A per-slug override (see vogesen_boundary.SLUG_OVERRIDE) wins over everything: it exists for trails
    whose Trailforks region membership disagrees with where their own line actually is.
    """
    if slug is not None:
        ov = override(slug)
        if ov is not None:
            return ov[1] if ov[0] == EXPECT_SIDE else "OTHERSIDE"

    return _resolve_sub_by_region(meta)


def _resolve_sub_by_region(meta):
    """Sub-region from the harvested Trailforks region slug.

    Returns a key, or the string reason it is deliberately out of scope, or None when nothing matches
    (which sends it to the nearest-centroid fallback rather than dropping it).
    """
    regs = (meta.get("reg") or "").split(",")
    for r in regs:
        if r in REG_TO_SUB:
            return REG_TO_SUB[r]
    for r in regs:
        if r in EXCLUDED_REGS:
            return "OUT: " + EXCLUDED_REGS[r]
    for r in regs:
        if r in SOUTH_REGS:
            return "SOUTH"
    return None


def nearest_sub(pt, centroids):
    return min(centroids, key=lambda k: haversine_m(pt, centroids[k]))


def main():
    # BOTH harvest batches, merged: a region slug can turn up in either one (`donon` was harvested with
    # the southern batch yet sits 39 km NORTH of the line), and reading only one batch silently loses
    # those trails. Which region a row belongs to is decided by REG_TO_SUB / EXCLUDED_REGS alone.
    # Moselle (Metz/Thionville, ~60 rows) was harvested during the survey and is not the Vosges at all;
    # it is excluded by simply not appearing in either map, which `resolve_sub` then reports.
    table = {}
    for name in ("vogesen_table_full.json", "sued_table.json"):
        path = os.path.join(WORK, name)
        if not os.path.exists(path):
            continue
        for slug, meta in json.load(open(path, encoding="utf-8"))["trails"].items():
            if not re.fullmatch(r"[a-z0-9][a-z0-9\-_]*", slug):
                continue
            if meta["n"].strip().lower() in ("next", "prev", "previous"):
                continue
            if slug in table:
                for r in meta["reg"].split(","):
                    if r not in table[slug]["reg"]:
                        table[slug]["reg"] += "," + r
            else:
                table[slug] = dict(meta)

    geo = {}
    for name in ("vogesen_geo.json", "vogesen_geo_black.json", "sued_geo.json"):
        path = os.path.join(WORK, name)
        if os.path.exists(path):
            geo.update(json.load(open(path, encoding="utf-8")))

    line_trails, trail_geo, profiles = [], {}, {}
    skipped = defaultdict(list)
    checks = []
    pending = []                      # (slug, meta, diff, pts) with no sub-region from the slug
    sub_pts = defaultdict(list)       # sub -> midpoints, for the centroid fallback

    def add(slug, meta, diff, sub, pts):
        uphill = "uphill" in slug or "uphill" in meta["n"].lower()
        entry, tgeo, prof = build_trail(
            slug_to_id(slug), meta["n"].strip(), sub, diff, pts,
            uphill=uphill, descend=not uphill)
        line_trails.append(entry)
        trail_geo[entry["id"]] = tgeo
        profiles[entry["id"]] = prof

    for slug in sorted(table):
        meta = table[slug]
        if slug in DUPLICATE_OF_PFAELZERWALD:
            skipped["already in pfaelzerwald: %s" % DUPLICATE_OF_PFAELZERWALD[slug]].append(slug)
            continue
        # Access rows first: they are excluded by rule, so no geometry was ever harvested for them and
        # reporting them as a geometry failure would bury a real one among 96 expected lines.
        if meta["df"] in ACCESS_DIFF:
            skipped["access/fireroad row (excluded by rule)"].append(slug)
            continue
        g = geo.get(slug)
        if not g or g.get("wall") or g.get("empty") or g.get("err"):
            skipped["no geometry harvested"].append(slug)
            continue
        diff = TF_DIFF.get(meta["df"])
        if diff is None:
            skipped["no usable difficulty (%s)" % (meta["df"] or "blank")].append(slug)
            continue

        pts, _prof_x = profile_points(g)
        if len(pts) < 2:
            skipped["profile empty (polyline only, no elevation)"].append(slug)
            continue

        # Cross-check the two independent copies of the same line Trailforks serves. Compare real
        # lengths, not the profile's own `x` axis: that axis silently switches from metres to
        # KILOMETRES above 1 km (`br4me-du-cerf` reports 702, a 1 060 m trail reports 1.06), which the
        # first version of this check read as a 1 059 m mismatch on 300-odd trails.
        enc = g.get("c") or []
        prof_len = line_length_m(pts)
        enc_len = line_length_m(enc) if len(enc) > 1 else 0.0
        if enc_len and abs(prof_len - enc_len) > CHECK_TOLERANCE_M:
            checks.append((slug, round(prof_len), round(enc_len)))

        sub = resolve_sub(meta, slug)
        if sub == "OTHERSIDE":
            continue                       # a per-slug override sends it to the other region
        if sub == "SOUTH":
            continue                       # belongs to Suedvogesen, silently
        if sub and sub.startswith("OUT: "):
            skipped[sub[5:]].append(slug)
            continue
        if sub is None:
            pending.append((slug, meta, diff, pts))
            continue
        sub_pts[sub].append(pts[len(pts) // 2])
        add(slug, meta, diff, sub, pts)

    centroids = {k: [sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)]
                 for k, v in sub_pts.items()}
    for slug, meta, diff, pts in pending:
        mid = pts[len(pts) // 2]
        # The fallback can only offer THIS region's brackets, so without this guard a trail belonging to
        # the other side of the line gets force-fitted into the least bad bracket here. That is how
        # "Noire Goutte Red Line" (filed directly under the `vosges` parent, no commune) landed in
        # `ville`, 37.8 km on the wrong side.
        if side(mid[0], mid[1]) != EXPECT_SIDE:
            skipped["no bracket, and on the %s side of the red line" % side(mid[0], mid[1])].append(slug)
            continue
        sub = nearest_sub(mid, centroids)
        skipped["assigned by nearest centroid -> %s" % sub].append(slug)
        add(slug, meta, diff, sub, pts)

    line_trails.sort(key=lambda t: (t["region"], t["name"].lower()))

    # Carry an existing `places` (and `lifts`) array through a rebuild. Both are written into the region
    # file AFTER this build by tools/add_region_places.py and tools/add_lifts.py, and write_region() only
    # emits what it is handed -- so without this, re-running the build silently drops them.
    prev = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    data = write_region(OUT, line_trails, trail_geo, profiles,
                        places=prev.get("places") or [], lifts=prev.get("lifts"))

    print("built %d trails -> %s" % (len(line_trails), OUT))
    for k in sorted(skipped):
        print("  skipped %3d  %s  %s" % (len(skipped[k]), k, skipped[k][:5]))
    if checks:
        print("  length mismatch profile vs polyline (>%d m):" % CHECK_TOLERANCE_M)
        for slug, a, b in checks[:25]:
            print("    %-42s profile %6d m  polyline %6d m" % (slug, a, b))
    else:
        print("  geometry cross-check: all %d trails agree with their own polyline within %d m"
              % (len(line_trails), CHECK_TOLERANCE_M))

    # Every sub-region's real extent, printed every build: this is what surfaced `dambach` sitting 65 km
    # from the bracket it had been mapped into, and it is the only cheap check on a scope this wide.
    report_boundary(line_trails, trail_geo, EXPECT_SIDE)

    print("\n  sub-region extents (Colmar is at 48.079 N):")
    pts_by_sub = defaultdict(list)
    for t in line_trails:
        pts_by_sub[t["region"]].extend(trail_geo[t["id"]])
    for sub in sorted(pts_by_sub):
        pts = pts_by_sub[sub]
        la = [p[0] for p in pts]
        lo = [p[1] for p in pts]
        n = sum(1 for t in line_trails if t["region"] == sub)
        print("    %-13s n=%3d  lat %.3f..%.3f  lon %.3f..%.3f  km %5.1f  %s"
              % (sub, n, min(la), max(la), min(lo), max(lo),
                 sum(t["len"] for t in line_trails if t["region"] == sub),
                 SUBREGIONS[sub][0]))
    print()
    print(json.dumps(region_summary(data), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
