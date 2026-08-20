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
                               parse_gpx, region_summary, write_region)

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
    "sued":     ("Südschwarzwald", "#b45309"),    # Münstertal, Staufen, Sulzburg, Zastler, Bonndorf
    "mitte":    ("Mittlerer Schwarzwald", "#1d4ed8"),  # Triberg, Hornberg, Schonach, Kinzigtal
    "nord":     ("Nordschwarzwald", "#be185d"),   # Baiersbronn, Sasbachwalden, Seebach, Hornisgrinde
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
    "Schonach im Schwarzwald": "mitte", "Haslach im Kinzigtal": "mitte",
    "Sasbach": "nord", "Sasbachwalden": "nord", "Seebach": "nord", "Baiersbronn": "nord",
    "Münstertal/Schwarzwald": "sued", "Staufen": "sued", "Sulzburg": "sued",
    "Bonndorf im Schwarzwald": "sued",
}
#: Per-trail overrides where the municipality name is not where the trail is ridden. Oberried reaches
#: from the Schauinsland (a Freiburg hub the city's own trails share) to the Zastler under the Feldberg.
TRAIL_SUB = {
    "Schauinsland Gipfel - Kohlerhau": "freiburg",
    "Zastler Steig": "sued",
    "deadmansfirstride": "sued",
}

#: Bikepark Todtnau. Geometry per trail from whichever of the two sources is the more complete line --
#: they trace the same corridor (median deviation 2.5 m for Downhill, 5.1 m for Wildride), so this is a
#: choice about coverage, not about which line is right. OSM's Downhill starts 200 m below the top
#: station but reaches the valley station; Trailforks' stops 100 m short of the valley but starts at the
#: top. For Wildride, Trailforks' line CONTAINS OSM's and adds 800 m at the bottom.
#: Both still fall well short of the operator's own stated distance (see docs/schwarzwald.md).
TODTNAU = [
    ("todtnau_downhill", "Downhill", "schwarz", "osm", 35830938, (None, None, None)),
    ("todtnau_wildride", "Wildride", "rot", "trailforks", "trailforks_wildride.json", (None, None, None)),
]

#: The park's third run has no geometry in any source checked: the operator publishes no GPX, OSM has
#: not mapped it, and the Trailforks region carries only the two above. Same call as the four Harz runs
#: dropped on 2026-08-14 -- do not invent a line for it; add it when a real track turns up.
NOT_BUILT = [
    "Downhill Flow (Bikepark Todtnau) -- 2,6 km / 450 hm, red, no geometry in any source",
    # Trailforks calls it a MULTI TRAIL, i.e. a route stitched from other trails rather than a trail of
    # its own -- 2 756 m that would draw a second line over the trails it is made of. That makes it a
    # Trailrunde candidate (`loop: true` plus `trailSegments`, matched with tools/gpx_map_match.py), not
    # a plain trail, and the region has no Touren yet at all.
    "Schauinsland Enduro (Trailforks, MTB Freiburg e.V.) -- multi-trail route, Tour candidate",
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

    # ---- 4. the lift ---------------------------------------------------------------------------
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

    places = json.load(open(OUT, encoding="utf-8")).get("places") if os.path.exists(OUT) else []
    data = write_region(OUT, trails, geo, profs, places=places or [], lifts=lifts)
    summary = region_summary(data)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
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
