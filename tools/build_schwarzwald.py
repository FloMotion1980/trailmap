"""Build regions/schwarzwald.json -- Schwarzwald (Freiburg, Bikepark Todtnau and the rest of the range).

Sources, in order of authority (see docs/schwarzwald.md for the full account):

1. **Mountainbike Freiburg e.V.** (mountainbike-freiburg.com) -- the OPERATOR of the Freiburg trails, and
   the only source here that publishes both a per-trail GPX *and* its own difficulty. The difficulty is a
   hex colour in the site's own `window.mtb_trails` blob (#46b414 green / #148cf0 blue / #dc1313 red /
   #000000 black), which maps 1:1 onto this app's four colours. Per the standing operator-wins rule this
   beats Trailguide wherever the two disagree -- and they do, for six trails (Hubbelfuchs, Al Natura,
   Schaedelwaeg, both Floh-Trails, and Turbo/Volles Rohr, whose grades Trailguide has swapped).
2. **Trailguide** (trailguide.net) for every trail no operator publishes. Its own JSON API answers
   anonymously: `GET /a?query={"action":"trails.get.query","tracks":true,"cropTrack":true,
   "trailsToLoad":[<seq>,...]}` with a `tg-sid` header from `{"action":"session.create"}`.
   **`cropTrack` is not optional.** Without it a trail whose track was recorded as part of a longer ride
   comes back with that whole ride's geometry -- "Wurzi" is 776 m of trail against 1983 points spanning a
   multi-kilometre tour, and four Waldkirch trails share one parent track. With it, every returned line's
   own length matches the stated `meters` to the metre (checked for all 108).
3. **OSM / Trailforks** for Bikepark Todtnau, which publishes no GPX at all. Neither source has the third
   run ("Downhill Flow"), so it is deliberately absent -- see NOT_BUILT below.

Run it, then the two follow-ups the runbook asks for:

    python tools/build_schwarzwald.py
    python tools/update_region_versions.py
    python tools/validate_region.py schwarzwald
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import (ElevationLookup, build_trail, haversine_m,  # noqa: E402
                               osm_aerialway_survey, parse_gpx, region_summary, write_region)
from pfaelzerwald_containment import (bbox, bbox_overlaps, dist_profile,  # noqa: E402
                                     line_len_m, profile_shape)
from schwarzwald_anchors import ANCHORS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATERIAL = os.path.join(ROOT, "Material", "Schwarzwald")
GPX = os.path.join(MATERIAL, "Freiburg")
OUT = os.path.join(ROOT, "Trailmap App", "regions", "schwarzwald.json")

#: The sub-region split, and the REGION_CATALOG entry it becomes. Six brackets, decided from where the
#: trails actually are rather than from the municipality names: the two the user named (Freiburg and the
#: Bikepark) plus four that each hold a cluster with its own valley. `tools/add_region_places.py` reads
#: this table by name while the region is not yet in REGION_CATALOG, so keep the labels here in step with
#: the ones in index.html. Colours only need to differ inside this group, and none may be the
#: group-label button's own --forest (#2f4a3a).
SUBREGIONS = {
    "mtbfr":    ("MTB Freiburg e.V.", "#c2410c"),  # the club's own network -- see MTBFR below
    "freiburg": ("Freiburg & Umgebung", "#0891b2"),  # everything else around the city
    "todtnau":  ("Bikepark Todtnau", "#7c3aed"),  # Hasenhorn
    "elztal":   ("Elztal & Kandel", "#0f766e"),   # Waldkirch, Glottertal, Simonswald
    # The five brackets below were added/reshaped by the Trailforks sweep (2026-08-20), which raised the
    # region from 119 trails to several hundred and made the original "Südschwarzwald" catch-all useless:
    # it had held everything from the Markgräflerland to Bonndorf, 60 km apart. It is gone, split into
    # `markgraefler` (Rhine-facing slope plus the Hotzenwald) and `hochschwarzwald` (Feldberg, the lakes,
    # the Wutach). `ortenau` and `enztal` are new for the same reason -- Ortenau/Kinzigtal and the Enz
    # valley are each bigger than the whole region was before the sweep.
    "markgraefler":    ("Markgräflerland & Hotzenwald", "#b45309"),
    "hochschwarzwald": ("Hochschwarzwald", "#0e7490"),
    "ortenau":         ("Ortenau & Kinzigtal", "#7f1d1d"),
    "mitte":           ("Mittlerer Schwarzwald", "#1d4ed8"),
    "nord":            ("Nordschwarzwald", "#be185d"),
    "enztal":          ("Enztal & Nordrand", "#4d7c0f"),
}

#: `mtbfr` is the one ORGANISATIONAL bracket among six geographic ones -- the user's own call
#: (2026-08-20), after pointing at the club's Trailforks association list. Membership is therefore
#: neither a bounding box nor a municipality but "is this trail the club's": the union of the trails on
#: the club's own site and of Trailforks association 12404 (mirrored as
#: `Material/Schwarzwald/trailforks_association_12404.html`). That deliberately reaches outside Freiburg
#: -- the club's Ortsgruppen trails at Waldkirch and Emmendingen are the club's, so they are in this
#: bracket and not in `elztal`, and Schauinsland-Staufen ends 20 km south-west of the city.
#: Everything the association does NOT claim, but which is still around Freiburg, is `freiburg`.
MTBFR_ASSOCIATION = {
    # Trailguide/our name                          -> in association 12404 under
    "Holzschlägermatte",                         # holzschlagermatte
    "Kybfelsensteig",                            # kybfelsensteig
    "Kandel Höhenweg Rosskopf",                  # kandelhohenweg
    "Präsident Thoma - Suggental",               # prasident-thoma-weg
    "Schneeburg",                                # schneeburg
    "Schauinsland-Staufen",                      # schauinslandstaufen
}

#: The club's own difficulty colours -> this app's four.
CLUB_COLOUR = {"#46b414": "gruen", "#148cf0": "blau", "#dc1313": "rot", "#000000": "schwarz"}
#: Trailguide's, same mapping one word further on.
TG_COLOUR = {"green": "gruen", "blue": "blau", "red": "rot", "black": "schwarz"}

# --------------------------------------------------------------------------------------------------
# 1. The club's own trails. `diff` is quoted from the club's own colour, not from Trailguide.
#    An uphill has no published grade anywhere, so it takes `gruen` -- the same convention Bike
#    Kingdom's thirteen "Access"/"Uphill" entries already follow.
# --------------------------------------------------------------------------------------------------
CLUB = [
    # id                     name                        file                                             diff       sub        uphill
    ("borderline",           "Borderline",               "mtb-freiburg-borderline-downhill.gpx",           "rot",     "mtbfr", False),
    ("borderline_uphill",    "Borderline Uphill",        "mtb-freiburg-borderline-uphill-final-latest.gpx", "gruen",  "mtbfr",    True),
    ("canadian",             "Canadian Trail",           "mtb-freiburg-canadian-trail.gpx",                "rot",     "mtbfr", False),
    ("canadian_s0",          "Canadian Sektion 0",       "mtb-freiburg-canadian-sektion-0-trail.gpx",      "schwarz", "mtbfr", False),
    ("canadian_uphill1",     "Canadian Uphill 1",        "mtb-freiburg-canadian-uphill1.gpx",              "gruen",   "mtbfr",    True),
    ("canadian_uphill2",     "Canadian Uphill 2",        "mtb-freiburg-canadian-uphill2.gpx",              "gruen",   "mtbfr",    True),
    ("baden_to_the_bone",    "Baden To The Bone",        "baden-to-the-bone-downhill.gpx",                 "schwarz", "mtbfr", False),
    ("btb_uphill",           "Baden To The Bone Uphill", "baden-to-the-bone-uphill.gpx",                   "gruen",   "mtbfr",    True),
    ("badish_moon_rising",   "Badish Moon Rising",       "mtb-freiburg-badish-moon-rising-downhill.gpx",   "blau",    "mtbfr", False),
    ("hubbelfuchs",          "Hubbelfuchs",              "mtb-freiburg-hubbelfuchs-downhill.gpx.gpx",      "rot",     "mtbfr", False),
    ("hexentrail",           "Hexentrail",               "Hexentrail-Downhill-MTB-Freiburg-eV.gpx",        "blau",    "mtbfr", False),
    ("hexentrail_uphill",    "Hexentrail Uphill",        "Hexentrail-Uphill-MTB-Freiburg-eV.gpx",          "gruen",   "mtbfr",    True),
    ("al_natura",            "Al Natura",                "MTB-Freiburg-eV-Al-Natura-Uphill.gpx",           "gruen",   "mtbfr", False),
    ("flying_gufi",          "Flying GuFi",              "mtb-freiburg-flying-gufi-trail-downhill.gpx",    "gruen",   "mtbfr", False),
    ("flohtrail1",           "Floh-Trail 1",             "flohtrail-1-kids-und-jugendstrecke.gpx",         "gruen",   "mtbfr", False),
    ("flohtrail2",           "Floh-Trail 2",             "flohtrail-2-kinder-und-jugendstrecke.gpx",       "blau",    "mtbfr", False),
    ("schoeni",              "Schöni Trail",             "mtb-freiburg-schoeni-downhill.gpx",              "blau",    "mtbfr", False),
    ("schaedelwaeg",         "Schädelwäg",               "mtb-freiburg-schadelwaeg-downhill.gpx",          "schwarz", "mtbfr", False),
    ("schaedelwaeg_uphill",  "Schädelwäg Uphill",        "mtb-freiburg-schadelwaeg-uphill.gpx",            "gruen",   "mtbfr",    True),
    ("woody",                "Woody",                    "mtb-freiburg-woody-downhill.gpx",                "blau",    "mtbfr",   False),
    ("birdy",                "Birdy",                    "mtb-freiburg-birdy-downhill.gpx",                "rot",     "mtbfr",   False),
    ("volles_rohr",          "Volles Rohr",              "mtb-freiburg-volles-rohr-downhill.gpx",          "rot",     "mtbfr",   False),
]

#: "Al Natura" and "Turbo" are the two club files that are NOT the club's own best line.
#: Al Natura's upload is mislabelled `...-Uphill.gpx` but descends throughout (4 m of climb against
#: 134 m of drop), so it is the trail and is used as one. Turbo's, by contrast, is a genuine fragment:
#: 118 m of 7 points where Trailguide has the same corridor at 242 m, every club point within 13 m of
#: it. Trailguide supplies the geometry, the club still supplies the name and the grade.
CLUB_NAME_ON_TG_GEOMETRY = {"Turbo-Trail": ("turbo", "Turbo", "blau", "mtbfr")}

# --------------------------------------------------------------------------------------------------
# 1b. Club trails that exist ONLY in the club's Trailforks association, not on the club's own site --
#     which is why they need Trailforks geometry (`encodedpath` off the trail page, Google-polyline
#     encoded, precision 5) and a Trailforks grade. The club publishes no grade for any of them, so
#     this is the documented fallback case for the operator-wins rule, not an exception to it.
#     Difficulty here is Trailforks' own RATING, not its "voted" figure (Blaue Raute and the connector
#     are rated green and voted blue) -- the rating is the one Trailforks itself shows on the trail.
# --------------------------------------------------------------------------------------------------
TF_CLUB = [
    # id             name                               file                                    diff
    ("blaue_raute",  "Blaue Raute",                     "blaue-raute.json",                     "gruen"),
    ("ktrail",       "K-Trail",                         "ktrail-195608.json",                   "gruen"),
    # "Rodelbahn - Kohlerhau Connector" is NOT here: its 857 m lie entirely (containment 1.00) inside
    # Trailguide's "Schauinsland Gipfel - Kohlerhau" (2 886 m), so building it would draw a second line
    # along a third of that trail. The longer line stays; the association's own name for the piece is
    # recorded here instead.
]

#: Trailguide entries that are the club's trail under another name -- dropped so the map draws one line.
TG_DUPLICATES = {
    "Borderline", "Canadian Trail", "Baden To The Bone", "Badish Moon Rising", "Hubbelfuchs",
    "Hexentrail", "Al Natura", "Schädelwäg", "Flying GuFi", "Floh-Trail 1 Kids- und Jugendstrecke",
    "Floh-Trail 2 Kinder-und Jugendstrecke", "Volles-Rohr-Trail",
    # 1608 m of which the last 381 m ARE our "Canadian Sektion 0" and the rest is the Sohlacker/
    # Kybfelsen approach that "Kybfelsensteig" already covers. Two lines over one piece of ground is
    # what the duplicate rule exists to prevent, and the club's own definition of its section wins.
    "Sohlacker - Kybfelsen - Canadian Trail Sektion 0",
    # 94 % of "Shooter" (2 478 m, red) lies within 25 m of the club's "Schöni Trail" (2 264 m, blue),
    # shape "subsumed" -- one line on the Schönberg under two names. Trailforks has it as "Schöni DH",
    # 2 266 m, whose own description ("vom Gipfel des Schönbergs ... bis zum Schützenhaus") is the same
    # trail again. The club's name and grade win; note that Trailforks' VOTED difficulty (red) agrees
    # with Trailguide against the operator's blue, which the operator-wins rule settles.
    "Shooter",
    # Same case one valley over: 94 % of "Hirzberg Highway" (2 042 m, green) lies within 25 m of the
    # club's own "K-Trail" (2 153 m, also green), shape "subsumed". "Hirzberg Highway" is a Trailguide
    # contributor's name for it; the club's association name is the one the trail is signed under.
    "Hirzberg Highway",
}

#: Not in the Schwarzwald at all. Hardheim is Odenwald (which this app already has as its own region --
#: worth a look when that one is next touched); Ettlingen's Albtal trail sits on the range's northern
#: rim, 130 km from Freiburg, alone in its corner and with no second trail to share a sub-region with.
TG_OUT_OF_SCOPE_PLACES = {"Hardheim", "Ettlingen"}

#: Trailguide's `place` -> sub-region. Oberried straddles two and is decided per trail below.
PLACE_SUB = {
    "Freiburg": "freiburg", "Freiburg im Breisgau": "freiburg", "Gundelfingen": "freiburg",
    "Stegen": "freiburg",
    "Emmendingen": "elztal", "Waldkirch": "elztal", "Glottertal": "elztal", "Simonswald": "elztal",
    "Gutach im Breisgau": "elztal", "Herbolzheim": "elztal", "Kenzingen": "elztal",
    "Malterdingen": "elztal",
    "Triberg (Schwarzwald)": "mitte", "Triberg im Schwarzwald": "mitte", "Hornberg": "mitte",
    "Schonach im Schwarzwald": "mitte",
    "Sasbach": "nord", "Sasbachwalden": "nord", "Seebach": "nord", "Baiersbronn": "nord",
    "Haslach im Kinzigtal": "ortenau",
    "Münstertal/Schwarzwald": "markgraefler", "Staufen": "markgraefler", "Sulzburg": "markgraefler",
    "Bonndorf im Schwarzwald": "hochschwarzwald",
}
#: Per-trail overrides where the municipality name is not where the trail is ridden. Oberried reaches
#: from the Schauinsland (a Freiburg hub the city's own trails share) to the Zastler under the Feldberg.
TRAIL_SUB = {
    "Schauinsland Gipfel - Kohlerhau": "freiburg",
    "Zastler Steig": "hochschwarzwald",
    "deadmansfirstride": "hochschwarzwald",
}

#: Bikepark Todtnau. Both runs come from Trailforks, and the OSM lines are NOT used.
#:
#: The first build took the Downhill from OSM (way 35830938) because that line reaches the valley station
#: while Trailforks' `bikepark-todtnau-racetrack` stops 100 m short of it. Then the district sweep built
#: the Trailforks one too, as its own trail under its own name, and the user settled it (2026-08-20):
#: "Bikepark Todtnau Racetrack ist eigentlich der gleiche Trail wie Downhill in Todtnau. Loesch den
#: jetzigen Downhill und nenn den anderen schwarzen dann einfach Downhill." So the OSM copy is gone and
#: the swept Trailforks line carries the name -- see TF_RENAME below, which also keeps the old id
#: `sw_todtnau_downhill` so nothing that referenced it breaks.
#:
#: Worth knowing why the duplicate check did not catch this pair by itself: the two lines trace the same
#: corridor (median deviation 2.5 m) but each covers ~100-200 m the other does not, at OPPOSITE ends, and
#: the containment metric with the "subsumed" shape test is deliberately strict about exactly that. The
#: Wildride pair, where Trailforks' line contains OSM's outright, WAS caught and dropped automatically.
#: Both runs still fall well short of the operator's stated distance (see docs/schwarzwald.md).
TODTNAU = [
    ("todtnau_wildride", "Wildride", "rot", "trailforks", "trailforks_wildride.json", (None, None, None)),
]

#: The park's third run has no geometry in any source checked: the operator publishes no GPX, OSM has
#: not mapped it, and the Trailforks region carries only the two above. Same call as the four Harz runs
#: dropped on 2026-08-14 -- do not invent a line for it; add it when a real track turns up.
NOT_BUILT = [
    "Downhill Flow (Bikepark Todtnau) -- 2,6 km / 450 hm, red, no geometry in any source",
    # Not a trail but worth stating with the rest: the park itself stopped. Adventure-Bikepark GmbH,
    # which ran Bikepark Bad Wildbad's six runs and had the Sommerbergbahn carry bikes two days a week,
    # ceased operating on 2025-12-31; the town is looking at a club/community model. The RUNS are in the
    # region (they exist on the ground and Trailforks holds their lines) but they carry Trailforks
    # grades, not an operator's, and no lift -- the bike transport was part of the closed operation.
    "Bikepark Bad Wildbad as an operating park -- operator ceased 2025-12-31, runs kept, no lift",
    # NOTE, corrected 2026-08-20: "Schauinsland Enduro" is NOT excluded and is not a route. Trailforks'
    # "Multi Trail" label means multi-USE (its own alternateName list reads "Schauinsland Enduro
    # Multi-Use Trail"), not "assembled from several trails" -- it is a plain 2,8 km descent, and the
    # district sweep builds it as `sw_schauinsland_enduro`. The region's Touren come from Trailforks'
    # own ROUTES instead; see tools/build_schwarzwald_tours.py.
    "Trimm-Dich-Pfad (Trailforks, MTB Freiburg e.V.) -- tagged as a hiking trail, not mtb",
]


def slug(name):
    s = name.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def tg_points(entry):
    return [[p["lat"], p["lng"], p.get("alt")] for p in entry["latlng"]["points"]]


def looks_uphill(points):
    """An uphill trail is one that climbs end to end -- read from the track, never from the name.

    Two thresholds, both needed. A net rise alone flagged "Wasserfall Sprint" (46 m of climb against 27 m
    of drop over 2.8 km, i.e. an undulating traverse) as an uphill route, which would have hidden it
    behind the wrong sidebar switch: a trail only counts as uphill when the climbing clearly dominates.
    """
    ele = [p[2] for p in points if p[2] is not None]
    if not ele:
        return False
    gain = sum(max(0.0, ele[i + 1] - ele[i]) for i in range(len(ele) - 1))
    loss = sum(max(0.0, ele[i] - ele[i + 1]) for i in range(len(ele) - 1))
    return ele[-1] - ele[0] > 30 and gain > 1.5 * loss


# --------------------------------------------------------------------------------------------------
# 4. The Trailforks sweep: every trail in the Schwarzwald districts' own Trailforks tables.
#    Harvested by tools/harvest_schwarzwald_tf.py (table + per-trail polyline AND elevation profile);
#    read its docstring before touching any of this.
# --------------------------------------------------------------------------------------------------
TF_TABLE = os.path.join(MATERIAL, "trailforks_table.json")
TF_GEO = os.path.join(MATERIAL, "trailforks_geo.json")

#: Trailforks' own difficulty titles, exactly as the region table renders them, onto our four colours.
#: Same table as build_nordvogesen.py's -- the mapping is a project-wide convention, not per region.
#: Swept trails that get a different name and/or id than Trailforks' own. Keyed by slug.
#: `bikepark-todtnau-racetrack` IS the park's "Downhill" (the user's call, see TODTNAU above); it keeps
#: the id the OSM-sourced copy had, so the region's ids stay stable across this change.
TF_RENAME = {
    "bikepark-todtnau-racetrack": ("sw_todtnau_downhill", "Downhill"),
}

TF_DIFF = {
    "Easy / Green Circle": "gruen",
    "Intermediate / Blue Square": "blau",
    "Difficult / Red": "rot",
    "Severe / Black": "schwarz",
    "Very Difficult / Black Diamond": "schwarz",
    "Extremely Difficult & dangerous, pros only!": "schwarz",
}
#: Rows carrying these instead of a grade are fireroads/uplift, not rated descents.
ACCESS_DIFF = {"Access Trail, Road or Doubletrack", "Secondary Access Road/Trail",
               "Chairlifts & gondolas"}

#: A district is an administrative box, not a massif: the Enzkreis reaches into the Stromberg, the
#: Ortenaukreis into the Rhine plain, Emmendingen onto the Kaiserstuhl. So the sweep does NOT trust the
#: district it came from -- every trail is assigned to the sub-region of the nearest ANCHOR TOWN
#: (tools/schwarzwald_anchors.py), and one that is further than this from every anchor is not in the
#: Schwarzwald at all and is dropped, with its name printed. That single rule does the assigning and
#: the excluding at once, which is what makes the exclusions reviewable instead of a hidden name list.
MAX_ANCHOR_KM = 12.0

#: Two trails of the same name are the same trail only if they are also in the same place. See the
#: comment on `by_norm` in main() for the three Jägerpfads this exists for.
SAME_NAME_KM = 5.0

#: Containment at or above this share of the shorter line's points, with the "subsumed" shape, means the
#: two entries are one piece of ground -- the project's own duplicate metric (see
#: `trailforks-duplicate-detection-method` and tools/pfaelzerwald_containment.py). The already-built
#: trail wins: it came from the operator or from Trailguide's cropped line, both better sourced.
DUPE_FRACTION = 0.6
DUPE_TOL_M = 25.0


def nearest_anchor(point):
    best = min(ANCHORS, key=lambda a: haversine_m(point, (a[0], a[1])))
    return best[2], haversine_m(point, (best[0], best[1])) / 1000.0, best[3]


def norm(name):
    """A name key for duplicate detection. Only the word "trail" is dropped.

    NOT "uphill"/"downhill"/"dh": stripping those made a trail collide with its own counterpart --
    "Borderline" normalised to the same key as "Borderline Uphill", which would drop a genuine climb as a
    duplicate of the descent that shares its name. Anything the name test misses this way is still caught
    by the geometry test, which is the reliable one anyway.
    """
    n = slug(name)
    return n.replace("_trail", "").replace("trail_", "")


def duplicate_of(coords, geo, index):
    """The id of an already-built trail this line shares its ground with, or None.

    `index` is {id: bbox} so the full pairwise scan stays cheap at 700 trails a side.
    """
    b = bbox(coords, pad=0.0005)
    for tid, other_b in index.items():
        if not bbox_overlaps(b, other_b):
            continue
        other = geo[tid]
        short, long_ = ((coords, other) if line_len_m(coords) <= line_len_m(other)
                        else (other, coords))
        prof = dist_profile(short, long_)
        frac = sum(1 for d in prof if d <= DUPE_TOL_M) / len(prof)
        if frac >= DUPE_FRACTION and profile_shape(prof) == "subsumed":
            return tid, frac
    return None


def main():
    trails, geo, profs = [], {}, {}
    # Named explicitly: ElevationLookup's default path is relative to the CURRENT directory, so running
    # this from the repo root left a second, near-empty cache there instead of reusing the tool's own.
    ele_lookup = ElevationLookup(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "elevation_cache.json"))

    # ---- 1. the club's own trails ---------------------------------------------------------------
    for tid, name, fname, diff, sub, uphill in CLUB:
        pts = parse_gpx(open(os.path.join(GPX, fname), encoding="utf-8", errors="replace").read())
        entry, coords, prof = build_trail("sw_" + tid, name, sub, diff, pts,
                                          uphill=uphill, descend=not uphill)
        trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof

    # ---- 1b. club trails that only exist in the club's Trailforks association -------------------
    tf_dir = os.path.join(MATERIAL, "Freiburg-Trailforks")
    for tid, name, fname, diff in TF_CLUB:
        pts = [list(p) for p in json.load(open(os.path.join(tf_dir, fname), encoding="utf-8"))]
        entry, coords, prof = build_trail("sw_" + tid, name, "mtbfr", diff, pts,
                                          elevation=ele_lookup)
        trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof

    # ---- 2. Trailguide -------------------------------------------------------------------------
    tg = json.load(open(os.path.join(MATERIAL, "trailguide_freiburg.json"), encoding="utf-8"))
    tg += [t for t in json.load(open(os.path.join(MATERIAL, "trailguide_karlsruhe.json"),
                                    encoding="utf-8"))
           if t.get("place") not in TG_OUT_OF_SCOPE_PLACES]

    for t in sorted(tg, key=lambda t: t["name"]["def"]):
        name = t["name"]["def"]
        if name in TG_DUPLICATES:
            continue
        club_named = name in CLUB_NAME_ON_TG_GEOMETRY
        if club_named:
            tid, name, diff, sub = CLUB_NAME_ON_TG_GEOMETRY[name]
        else:
            tid = slug(name)
            diff = TG_COLOUR[t["color"]]
            sub = ("mtbfr" if name in MTBFR_ASSOCIATION
                   else TRAIL_SUB.get(name) or PLACE_SUB[t["place"]])
        pts = tg_points(t)
        # Turbo is a jump line the club lists as a descent; Trailguide's copy of it happens to be
        # recorded uphill, which `looks_uphill` would otherwise take at face value and store backwards.
        uphill = False if club_named else looks_uphill(pts)
        entry, coords, prof = build_trail("sw_" + tid, name, sub, diff, pts,
                                          uphill=uphill, descend=not uphill,
                                          elevation=ele_lookup)
        trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof

    # ---- 3. Bikepark Todtnau -------------------------------------------------------------------
    osm = {e["id"]: [[g["lat"], g["lon"]] for g in e["geometry"]]
           for e in json.load(open(os.path.join(MATERIAL, "Todtnau", "osm_bikepark_lift.json"),
                                   encoding="utf-8"))["elements"] if e.get("geometry")}
    for tid, name, diff, src, ref, official in TODTNAU:
        if src == "osm":
            pts = [list(p) for p in osm[ref]]
        else:
            pts = [list(p) for p in json.load(open(os.path.join(MATERIAL, "Todtnau", ref),
                                                   encoding="utf-8"))]
        entry, coords, prof = build_trail("sw_" + tid, name, "todtnau", diff, pts,
                                          elevation=ele_lookup)
        trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof

    # ---- 4. the lifts --------------------------------------------------------------------------
    # THREE candidates were checked against their OPERATOR's own summer pages, because OSM's
    # `aerialway:bicycle` tag does not decide membership (it was wrong in both directions in Serfaus):
    #
    #   Schauinslandbahn (Freiburg)  -> IN. Its own "Biking" page states the fare: "Der Preis für eine
    #       Fahrradmitnahme in der Schauinslandbahn beträgt 12,00 € zzgl. Tarif pro Person. Pro Kabine
    #       können maximal 2 Fahrräder mitgenommen werden." It is also the uplift for Badish Moon Rising
    #       and the Canadian, i.e. for this region's best-known descents.
    #   Feldbergbahn-Seebuck         -> IN. The Liftverbund's own summer page: 8-seat cabins with room
    #       for "Kinderwagen, Rollstuhl, Fahrrad oder sogar den vierbeinigen Freund". Note OSM still has
    #       it tagged `chair_lift` while the operator describes cabins — the geometry is the same line.
    #   Belchen-Seilbahn             -> OUT, and this is the case the rule exists for: OSM tags it
    #       `aerialway:bicycle=yes`, but the operator's own price list has no bike fare at all and its
    #       site says nothing about carrying bikes. No operator word, no lift.
    #
    # Bad Wildbad's Sommerbergbahn is a fourth candidate and is also out: it carried bikes on two days a
    # week *for the bikepark*, and that park's operating company stopped on 2025-12-31 (see NOT_BUILT).
    OSM_LIFTS = [
        ("lift_sw_schauinslandbahn", "Schauinslandbahn", "freiburg", "Schauinslandbahn"),
        ("lift_sw_feldbergbahn", "Feldbergbahn", "hochschwarzwald", "Feldbergbahn-Seebuck"),
    ]

    # ---- 4a. the Hasenhorn chairlift -----------------------------------------------------------
    # The Hasenhorn chairlift is the park's own uplift and the operator sells bike tickets for it, so
    # it belongs in the data on the operator's word; OSM (which also tags `aerialway:bicycle=yes` here)
    # only supplies the geometry. Stored bottom-station-first, which is the order OSM already has.
    lift_coords = [[round(p[0], 6), round(p[1], 6)] for p in osm[28436489]]
    base, top = ele_lookup([lift_coords[0]])[0], ele_lookup([lift_coords[-1]])[0]
    if base > top:                                   # never assume the source's direction
        lift_coords, base, top = lift_coords[::-1], top, base
    length = sum(haversine_m(lift_coords[i], lift_coords[i + 1])
                 for i in range(len(lift_coords) - 1)) / 1000.0
    lifts = [{"id": "lift_sw_hasenhorn", "name": "Hasenhorn-Sessellift", "region": "todtnau",
              "len": round(length, 2), "baseEle": int(round(base)), "topEle": int(round(top)),
              "coords": lift_coords}]

    # ---- 4b. the two operator-confirmed lifts, geometry from OSM by an anchored name --------------
    survey = {r["name"]: r for r in osm_aerialway_survey("47.55,7.60,49.00,8.90", min_len_m=500)}
    for lid, label, sub, osm_name in OSM_LIFTS:
        row = survey.get(osm_name)
        if not row:
            print("  !! %s: no OSM aerialway called %r -- lift skipped" % (label, osm_name))
            continue
        coords = [[round(p[0], 6), round(p[1], 6)] for p in row["geom"]]
        e0, e1 = ele_lookup([coords[0]])[0], ele_lookup([coords[-1]])[0]
        if e0 > e1:                                  # store bottom-station-first
            coords, e0, e1 = coords[::-1], e1, e0
        lifts.append({"id": lid, "name": label, "region": sub,
                      "len": round(sum(haversine_m(coords[i], coords[i + 1])
                                       for i in range(len(coords) - 1)) / 1000.0, 2),
                      "baseEle": int(round(e0)), "topEle": int(round(e1)), "coords": coords})

    places = json.load(open(OUT, encoding="utf-8")).get("places") if os.path.exists(OUT) else []
    # ---- 5. the Trailforks sweep ----------------------------------------------------------------
    tf_table = json.load(open(TF_TABLE, encoding="utf-8"))
    tf_geo = json.load(open(TF_GEO, encoding="utf-8")) if os.path.exists(TF_GEO) else {}
    # {normalised name: [(id, midpoint)]} -- a LIST, and with a position, because a name means nothing
    # on its own across 200 km of range: there are three separate "Jägerpfad"s, two "Kammweg"s and two
    # "Woody"s in these tables, and matching on the name alone silently dropped the far ones as
    # duplicates of the near one. A name match only counts as a duplicate within SAME_NAME_KM.
    by_norm = {}
    for t in trails:
        g = geo[t["id"]]
        by_norm.setdefault(norm(t["name"]), []).append((t["id"], g[len(g) // 2]))
    index = {t["id"]: bbox(geo[t["id"]], pad=0.0005) for t in trails}
    stats = {"built": 0, "dupe_name": [], "dupe_geo": [], "far": [], "nogeo": [], "tiny": []}
    for tf_slug, row in sorted(tf_table.items()):
        diff = row.get("diff")
        if not diff or diff in ACCESS_DIFF:
            continue
        name = row["cells"][0] if row["cells"] else tf_slug
        g = tf_geo.get(tf_slug) or {}
        # The profile is preferred over the polyline: the same line, but carrying Trailforks' own
        # elevation, so the sweep needs no DEM lookup at all.
        if g.get("p") and len(g["p"]) >= 2:
            pts = [[q[2], q[3], q[1]] for q in g["p"]]
        elif g.get("c") and len(g["c"]) >= 2:
            pts = [[q[0], q[1], None] for q in g["c"]]
        else:
            stats["nogeo"].append(name)
            continue
        sub, km, anchor = nearest_anchor(pts[len(pts) // 2][:2])
        if km > MAX_ANCHOR_KM:
            stats["far"].append("%s (%.0f km from %s)" % (name, km, anchor))
            continue
        mid = pts[len(pts) // 2][:2]
        near_same_name = [tid for tid, other_mid in by_norm.get(norm(name), [])
                          if haversine_m(mid, other_mid) / 1000.0 <= SAME_NAME_KM]
        if near_same_name:
            stats["dupe_name"].append("%s = %s" % (name, near_same_name[0]))
            continue
        coords_only = [[q[0], q[1]] for q in pts]
        if line_len_m(coords_only) < 80:
            stats["tiny"].append(name)
            continue
        dup = duplicate_of(coords_only, geo, index)
        if dup:
            stats["dupe_geo"].append("%s = %s (%.0f%%)" % (name, dup[0], dup[1] * 100))
            continue
        up = looks_uphill(pts)
        tid, name = TF_RENAME.get(tf_slug, ("sw_" + tf_slug.replace("-", "_"), name))
        entry, coords, prof = build_trail(tid, name, sub,
                                         TF_DIFF[diff], pts, uphill=up, descend=not up,
                                         elevation=ele_lookup)
        trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof
        by_norm.setdefault(norm(name), []).append((entry["id"], coords[len(coords) // 2]))
        index[entry["id"]] = bbox(coords, pad=0.0005)
        stats["built"] += 1

    data = write_region(OUT, trails, geo, profs, places=places or [], lifts=lifts)
    summary = region_summary(data)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("\nTrailforks sweep: %d built, %d name duplicates, %d geometry duplicates, "
          "%d outside the Schwarzwald, %d without geometry, %d under 80 m"
          % (stats["built"], len(stats["dupe_name"]), len(stats["dupe_geo"]), len(stats["far"]),
             len(stats["nogeo"]), len(stats["tiny"])))
    for key, label in (("dupe_name", "same name as"), ("dupe_geo", "same ground as"),
                       ("far", "dropped, too far from any anchor"),
                       ("nogeo", "no geometry harvested"), ("tiny", "dropped, under 80 m")):
        if stats[key]:
            print("  %s: %s" % (label, "; ".join(sorted(stats[key]))))

    print("\nnot built:")
    for line in NOT_BUILT:
        print("  -", line)
    print("\nREGION_CATALOG entry (paste into index.html):\n")
    print(catalog_entry(data))
    print("\nnext: python tools/add_region_places.py schwarzwald"
          "  /  python tools/update_region_versions.py")


def catalog_entry(data):
    """The one index.html change a new region needs, printed rather than written.

    index.html is edited by hand (and, while this region was built, by another session at the same time),
    so the build script states its own catalog entry instead of patching the file.
    """
    b = region_summary(data)["bounds"]
    subs = "\n".join('        %s: { label: "%s", color: "%s" },' % (k, v[0], v[1])
                     for k, v in SUBREGIONS.items())
    return ('    schwarzwald: {\n'
            '      label: "Schwarzwald", file: "regions/schwarzwald.json", trailCount: %d,\n'
            '      countries: ["DE"],\n'
            '      bounds: [[%s, %s], [%s, %s]],\n'
            '      subRegions: {\n%s\n      },\n'
            '    },' % (len(data["lineTrails"]), b[0][0], b[0][1], b[1][0], b[1][1], subs))


if __name__ == "__main__":
    # Only when run as a script: importing this module (add_region_places.py reads SUBREGIONS from it,
    # and the catalog snippet is printed from a one-liner) must not touch the caller's stdout.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
