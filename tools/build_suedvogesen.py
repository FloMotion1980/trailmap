# -*- coding: utf-8 -*-
"""Build regions/suedvogesen.json -- the Vosges from Colmar southwards, plus the Lorraine west side.

The user's own split, given on seeing the first Nordvogesen build (2026-08-19): "Ohne colmar und
vosges_ouest, das passt besser. Fuer Colmar und weiter Suedlich machen wir eine eigene Region. Da sind
ja auch die Bikeparks Lac Blanc und La Bresse."

So this region takes over the two brackets Nordvogesen dropped (Hohlandsbourg south of Colmar, and
Saint-Die/Raon-l'Etape on the Lorraine side) and adds everything Trailforks has further south: the
Munster valley, Guebwiller/Markstein, Thann and the Vallon d'Olima, Masevaux/Ballon d'Alsace, the
Hautes-Vosges around La Bresse, and Gerardmer.

**The boundary is the red line the user drew on a Trailforks map** (2026-08-19, "Ich wuerde alles unter
der eingezeichneten roten Linie zu der Region Suedvogesen zaehlen"), not the earlier bracket-by-name
wording. It is in `tools/vogesen_boundary.py`, together with how it was read off the screenshot and how
far to trust it; every build audits itself against it. Two brackets moved when it arrived, in OPPOSITE
directions: `kaysersberg` -- with the LAC BLANC bike park the user had named as one of this region's
parks all along -- came here from Nordvogesen, and `vosges_ouest` (Saint-Die, Raon-l'Etape, Lac de la
Maix, Donon) went back to Nordvogesen, because the line runs south of Saint-Die.

Method, sources and the two traps (Trailforks' embedded ElevationChart as the elevation source; the
`difficulty=` code list that must name code 10 or the whole black tier vanishes) are identical to
`tools/build_nordvogesen.py` -- read that docstring first.

One extra completeness step was needed here that the north did not need: the two departement-level
tables (`haut-rhin-27353`, `vosges`) are hard-capped near 100 rows, and comparing their rows against the
union of the child regions listed on their own pages surfaced NINE communes with no child region link at
all -- Gerardmer (13 trails), Bikepark du Markstein, Buhl, Dolleren, Cornimont, Orbey, Ventron,
Whir-au-Val, Donon. Their region slugs were recovered from the breadcrumb on one of their own trails'
pages (`bikepark-du-markstein-39293`, `whirauval` -- neither guessable) and harvested directly. Do this
check on any future region: a parent page's sub-region list is NOT a complete index of its children.

Harvest inputs (through the user's own logged-in Chrome):
  Material/Vogesen/sued_table.json         -- trail list for the southern regions
  Material/Vogesen/sued_geo.json           -- per slug {c: encodedpath, p: ElevationChart sections}
  Material/Vogesen/vogesen_table_full.json -- the north's list, for the two carried-over brackets
  Material/Vogesen/vogesen_geo.json        -- the north's geometry, same reason
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
EXPECT_SIDE = "sued"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: The harvest inputs, checked in for the same reason Material/Harz/harz_tf_geo.json is: without
#: them this script does nothing on a fresh clone. See Material/Vogesen/README.md.
WORK = os.path.join(ROOT, "Material", "Vogesen")
OUT = os.path.join(ROOT, "Trailmap App", "regions", "suedvogesen.json")

CHECK_TOLERANCE_M = 60.0

TF_DIFF = {
    "Easy / Green Circle": "gruen",
    "Intermediate / Blue Square": "blau",
    "Difficult / Red": "rot",
    "Severe / Black": "schwarz",
    "Very Difficult / Black Diamond": "schwarz",
    "Extremely Difficult & dangerous, pros only!": "schwarz",
}
ACCESS_DIFF = {"Access Trail, Road or Doubletrack", "Secondary Access Road/Trail"}

# THE OPERATOR'S OWN PUBLISHED GRADE WINS, Trailforks is only the fallback -- the project's standing rule
# (`operator-difficulty-wins`, CLAUDE.md). It bites in exactly three places in this region, the bike
# parks; everywhere else these are Club-Vosgien / community trails in a natural park with no operator
# and no published scale, so the fallback applies by default.
#
# A French park publishes the same four-colour scale the app uses, so the mapping is direct:
# vert->gruen, bleu->blau, rouge->rot, noir->schwarz (unlike the German three-step leicht/mittel/schwer
# scale in `tools/build_harz.py`, which never reaches gruen). **A grade stated across two steps takes the
# HARDER one**, the same direction a merged trail's per-section max() already rounds in.
#
# Keyed by trail slug, with the operator's own wording beside the colour so the mapping stays auditable
# without re-fetching the pages.
OPERATOR_DIFF = {
    # --- Bike Park du Lac Blanc (sub-region `kaysersberg`) -----------------------------------------
    # Source: the station's own site, https://www.lac-blanc.com/ete/velo-vtt-vosges/bike-park-dh/
    # (checked 2026-08-19, French page -- its English translation garbles two of the colours, so use the
    # French one). Seven DH pistes plus the 4X track; all seven are in our data and all seven matched.
    "smooth-17950":     ("gruen",   "La SMOOTH -- verte"),
    "la-easy":          ("gruen",   "La EASY -- verte"),
    "la-cool-463604":   ("blau",    "La COOL -- bleue"),
    "la-flow":          ("rot",     "La FLOW -- rouge"),
    "la-roots":         ("rot",     "La ROOTS -- rouge"),
    "la-fat-17948":     ("schwarz", "La FAT -- rouge/noir, slopestyle -> the harder of the two"),
    "la-nuts-161193":   ("schwarz", "La NUTS -- noire"),
    # `four-cross-463718` (4X Track, 400 m) is deliberately absent: the operator lists it without a
    # colour, so Trailforks' own rating stands.

    # --- Bike Park La Bresse-Hohneck (sub-region `labresse`) ---------------------------------------
    # Source: the operator, https://labresse.labellemontagne.com/fr/ete/vtt-et-bikepark/bike-park/
    # (checked 2026-08-19): 6 pistes techniques + 4 pistes freeride. Eight of the ten are in our data
    # and **every one already agreed with Trailforks** -- listed anyway, because "checked and identical"
    # and "never checked" must not look the same in this table.
    "la-ballade-des-contrebandiers": ("gruen",   "La Balade des Contrebandiers -- verte"),
    "d3-chitelet":                   ("blau",    "Chitelet -- bleue"),
    "d4-barrage-6736":               ("blau",    "Barrage -- bleue"),
    "retour-a-l-ecole-663084":       ("rot",     "Retour Ecole -- rouge"),
    "d5-schuss":                     ("rot",     "Schuss -- rouge (freeride)"),
    "virolo":                        ("rot",     "Virolo -- rouge (freeride)"),
    "l-express-504798":              ("schwarz", "L'express -- noire"),
    "la-haute-goutte":               ("schwarz", "La Haute Goutte -- noire"),
    "la-goutte-663083":              ("schwarz", "La Goutte -- noire (freeride)"),
    # Not found in Trailforks: "Schuss Line" (rouge). Not guessed onto any existing entry.

    # --- Bikepark du Markstein (sub-region `guebwiller`) -------------------------------------------
    # NOT verifiable, and therefore NOT in this table. The operator page kelbikepark names as official
    # (alsacefreerideacademy.fr/bikepark-markstein) now serves an "18+ ONLY" age gate instead of a bike
    # park, and neither lemarkstein.net nor the valley's tourism site publishes a piste list.
    # kelbikepark.fr does publish a DISTRIBUTION -- 6 pistes, 2 green / 2 blue / 1 red / 1 black -- which
    # does not match what we hold (Manala gruen, Papala blau, Spaetzle blau, Schloppa rot, Papala rouge
    # rot), so a green and a black are probably missing rather than mis-graded. Left on Trailforks'
    # rating and recorded as unresolved: see docs/suedvogesen.md.
}


def resolve_diff(slug, tf_diff):
    """The operator's grade if it publishes one, else Trailforks'. Returns (diff, source)."""
    if slug in OPERATOR_DIFF:
        return OPERATOR_DIFF[slug][0], "operator"
    return tf_diff, "trailforks"

# Sub-regions, keyed on the harvested Trailforks region slug (same reasoning as the north: 46 rows carry
# a blank "riding area" cell, the slug never is). Brackets follow the valleys, which is how this massif
# is actually organised and ridden. Colours distinct within the group and none is --forest (#2f5d3a);
# they may repeat colours used in OTHER groups, which is explicitly fine.
# The three bike parks are their own sub-regions (user, 2026-08-20: "die Bikeparks eine eigene
# Unterregion"). They are lift-served, graded by an operator and ridden as a destination, so folding them
# into the valley bracket around them hid them: Lac Blanc's 8 pistes were 32 % of `kaysersberg`, La Bresse's
# 9 were 10 % of `labresse`, and Markstein's 6 were 15 % of `guebwiller`.
#
# Membership comes from the trail's own Trailforks region slug -- each park IS a Trailforks region, and the
# three lists came out exactly as the operators publish them (Lac Blanc 7 DH pistes + the 4X track,
# La Bresse 6 technique + 3 freeride, Markstein 6). Checked FIRST in `resolve_sub`, before the valley map,
# so a trail that carries both its park and its commune cannot land in the valley by list order.
PARK_REGS = {
    "lac-blanc-bike-park": "bp_lacblanc",
    "bikepark-la-bresse-25099": "bp_labresse",
    "bikepark-du-markstein-39293": "bp_markstein",
}

# Labels are ONE name each (user, 2026-08-20: "Die Namen der Unterregionen ... sind zu lang"). They were
# "Thann / Saint-Amarin", "Masevaux / Ballon d'Alsace", "Epinal / Vallon d'Olima" and so on -- honest about
# what a bracket spans, but a sidebar chip has ~14 characters before it wraps, and a valley is navigated by
# one name anyway. What each bracket actually covers is in the slug list right here, and in
# docs/suedvogesen.md.
SUBREGIONS = {
    "colmar": ("Colmar", "#a03a8a", [
        "hohlandsbourg", "wintzenheim", "wettolsheim-9426"]),
    "kaysersberg": ("Kaysersberg", "#a8452f", [
        "labaroche", "le-bonhomme", "trois-epis", "turckheim"]),
    "bp_lacblanc": ("Bikepark Lac Blanc", "#e07a1f", ["lac-blanc-bike-park"]),
    "munstertal": ("Münstertal", "#3a6ea5", [
        "munster", "munster-valley-22230", "stosswihr", "luttenbachpresmunster", "metzeral",
        "hohrod", "whirauval", "breitenbachhautrhin", "orbey"]),
    "guebwiller": ("Guebwiller", "#c1440e", [
        "guebwiller", "buhl", "orschwihr", "bergholtzzel", "soultzhautrhin"]),
    "bp_markstein": ("Bikepark Markstein", "#8a2f5a", ["bikepark-du-markstein-39293"]),
    "thann": ("Thann", "#8a6a2f", [
        "thann", "mollau", "moosch", "urbes", "fellering", "kruth"]),
    "masevaux": ("Masevaux", "#2f8a7a", [
        "masevaux", "dolleren", "bourbachlehaut", "wegscheid", "giromagny",
        "ballon-d-alsace-31436", "mulhouse-south-alsace-32280"]),
    "labresse": ("La Bresse", "#6a3a8a", [
        "la-bresse", "enduro-bressaud-30938", "ventron", "cornimont",
        "saulxuressurmoselotte", "le-menil", "bussang", "remiremont-9316", "vagney-37825"]),
    "bp_labresse": ("Bikepark La Bresse", "#2f6ea8", ["bikepark-la-bresse-25099"]),
    "gerardmer": ("Gérardmer", "#4a7d3f", ["gerardmer", "xonruptlongemer"]),
    # 65 km west of Colmar in the Lorraine plain rather than the massif, but below the line and 76 real
    # trails -- its own bracket so it can be switched off in the sidebar instead of dropped.
    "epinal": ("Épinal", "#7a3a2f", [
        "epinal", "vallon-d-olima", "vallon-d-olima-33741", "la-40-semaine-42294"]),
}

# Harvested and deliberately NOT built: `glaserberg-25360` (3 trails) centres at 47.442, 7.310 -- the
# JURA above Leymen near Basel, 60 km south of Guebwiller and not the Vosges at any reading of
# "Colmar und weiter suedlich". Listed rather than silently missing.
EXCLUDED_REGS = {"glaserberg-25360": "Jura near Basel, not the Vosges"}

# Single trails excluded for the same reason as `glaserberg-25360` -- they are not in this massif -- but
# which arrive through an in-scope region slug, so the region-level map cannot catch them.
EXCLUDED_SLUGS = {
    # Flat trail in the Nonnenbruch, Mulhouse's own city forest (47.7676, 7.2880): 23 km from the
    # Saint-Amarin valley whose bracket it landed in, and the only trail of this region anywhere in the
    # Rhine plain. Found because it was pulling THREE agglomeration labels (Mulhouse, Kingersheim,
    # Lutterbach) onto a mountain map through tools/add_region_places.py -- one outlier trail deciding a
    # region's labels is the tell that the trail, not the label rule, is what is out of place.
    "nonnenbruch-pfastatt-side": "Mulhouse city forest, 23 km outside the massif",
}

# `vosges_ouest` (Saint-Die, Raon-l'Etape, Lac de la Maix, Donon) was built HERE until the red line
# arrived: the user's earlier wording ("ohne vosges_ouest") had put it in the south, but the line they
# then drew runs clearly SOUTH of Saint-Die -- that bracket centres 18 km NORTH of the line -- so those
# trails are Nordvogesen's. They sit in NORTH_REGS below.

REG_TO_SUB = {r: k for k, (_l, _c, regs) in SUBREGIONS.items() for r in regs}

# Slugs belonging to Nordvogesen: their rows turn up here too, because the two capped departement-level
# tables list them, and building them twice would put the same trail in two regions.
NORTH_REGS = {
    "barr", "heidenkopf", "boersch", "breitenbach", "cleebourg", "climbach", "cosswiler", "dabo",
    "dambach", "danneetquatrevents", "goersdorf", "haegen", "lampertsloch", "le-hohwald", "lembach",
    "lutzelbourg", "lutzelhouse-74628", "muhlbachsurbruche", "niederbronn", "niedersteinbach",
    "oberbronn", "obersteinbach", "phalsbourg", "reinhardsmunster", "saverne", "soultzsousforets",
    "wangenbourg", "windstein", "wingen", "wissembourg-62557", "niederbronn-bike-trail",
    # `ville` -- 7 to 19 km NORTH of the line.
    "ribeauville", "liepvre", "neubois", "breitenau",
    # `vosges_ouest` -- 10 to 39 km NORTH of the line, see the note above EXCLUDED_REGS.
    "saintdie-des-vosges", "raon-l-etape", "raon-l-etape-41060", "lac-de-la-maix", "donon",
}

ID_PREFIX = "sv_"


def slug_to_id(slug):
    return ID_PREFIX + re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")


def profile_points(entry):
    pts = []
    for sec in entry.get("p") or []:
        for lat, lng, y, _x in sec:
            pts.append([lat, lng, y])
    return pts


def line_length_m(pts):
    return sum(haversine_m(pts[i - 1], pts[i]) for i in range(1, len(pts)))


def resolve_park(meta):
    """A bike-park sub-region, checked before the valley map so list order cannot decide it."""
    for r in (meta.get("reg") or "").split(","):
        if r in PARK_REGS:
            return PARK_REGS[r]
    return None


def resolve_sub(meta, slug=None):
    """Sub-region for this row, or a sentinel string the caller reports/skips on.

    A per-slug override (see vogesen_boundary.SLUG_OVERRIDE) wins over everything: it exists for trails
    whose Trailforks region membership disagrees with where their own line actually is.
    """
    if slug is not None:
        ov = override(slug)
        if ov is not None:
            return ov[1] if ov[0] == EXPECT_SIDE else "OTHERSIDE"

    park = resolve_park(meta)
    if park is not None:
        return park

    return _resolve_sub_by_region(meta)


def _resolve_sub_by_region(meta):
    regs = (meta.get("reg") or "").split(",")
    for r in regs:
        if r in REG_TO_SUB:
            return REG_TO_SUB[r]
    for r in regs:
        if r in NORTH_REGS:
            return "OUT"
    for r in regs:
        if r in EXCLUDED_REGS:
            return "SKIP: " + EXCLUDED_REGS[r]
    return None


def nearest_sub(pt, centroids):
    return min(centroids, key=lambda k: haversine_m(pt, centroids[k]))


def main():
    table = {}
    for name in ("sued_table.json", "vogesen_table_full.json"):
        for slug, meta in json.load(open(os.path.join(WORK, name), encoding="utf-8"))["trails"].items():
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
    pending = []
    sub_pts = defaultdict(list)
    operator_graded = []

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
        if meta["df"] in ACCESS_DIFF:
            skipped["access/fireroad row (excluded by rule)"].append(slug)
            continue
        diff = TF_DIFF.get(meta["df"])
        if diff is None:
            skipped["no usable difficulty (%s)" % (meta["df"] or "blank")].append(slug)
            continue
        diff, diff_src = resolve_diff(slug, diff)
        if diff_src == "operator":
            operator_graded.append((slug, diff, OPERATOR_DIFF[slug][1],
                                    TF_DIFF.get(meta["df"]) != diff))
        sub = resolve_sub(meta, slug)
        if slug in EXCLUDED_SLUGS:
            skipped["not in the massif: %s" % EXCLUDED_SLUGS[slug]].append(slug)
            continue
        if sub == "OTHERSIDE":
            continue                       # a per-slug override sends it to the other region
        if sub == "OUT":
            continue                       # belongs to Nordvogesen, silently
        if sub and sub.startswith("SKIP: "):
            skipped[sub[6:]].append(slug)
            continue
        g = geo.get(slug)
        if not g or g.get("wall") or g.get("empty") or g.get("err"):
            skipped["no geometry harvested"].append(slug)
            continue
        pts = profile_points(g)
        if len(pts) < 2:
            skipped["profile empty (polyline only, no elevation)"].append(slug)
            continue
        enc = g.get("c") or []
        if len(enc) > 1 and abs(line_length_m(pts) - line_length_m(enc)) > CHECK_TOLERANCE_M:
            checks.append((slug, round(line_length_m(pts)), round(line_length_m(enc))))
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

    # Carry an existing `places`/`lifts` array through a rebuild. Both are written into the region file
    # AFTER this build (tools/add_region_places.py, tools/add_lifts.py) and write_region() only emits what
    # it is handed -- so without this, re-running the build silently drops them, the same ordering trap
    # CLAUDE.md records for Bike Kingdom ("in that order, since the second runs on top of the first's
    # output"). Preserving them here removes the ordering rule instead of documenting it.
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

    changed = [g for g in operator_graded if g[3]]
    print("\n  operator difficulty applied to %d bike-park trail(s), %d of them differing from "
          "Trailforks:" % (len(operator_graded), len(changed)))
    for slug, diff, wording, diff_changed in operator_graded:
        print("    %-32s %-8s %-2s %s" % (slug[:32], diff, "!!" if diff_changed else "", wording))

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
                 sum(t["len"] for t in line_trails if t["region"] == sub), SUBREGIONS[sub][0]))
    print()
    print(json.dumps(region_summary(data), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
