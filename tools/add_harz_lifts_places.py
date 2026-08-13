# -*- coding: utf-8 -*-
"""Add the Harz region's `lifts` and `places` to regions/harz.json (pieces 2 and 4 of a region).

Membership comes from each operator's own summer page, OSM supplies geometry only -- the rule
docs/lifts-feature.md records, and the reason `aerialway:bicycle` is printed here as a cross-check and
nothing more (it reads `no` on Bodetal's Seilbahn Thale, which the operator does not run for bikes anyway,
and `None` on the Wurmbergseilbahn, which is unambiguously the park's own gondola).

Trailpark Harz deliberately has NO lift: it is a self-shuttle park, no lift and no entry fee, which is how
its own site leads.

Two of the six parks came out ambiguous against OSM and are handled explicitly rather than guessed:

* **St. Andreasberg** -- "Alberti-Lift" turns out to be the OPERATOR (Alberti-Lift GmbH, alberti-lift.de),
  not a lift, which is why the operator page reads as naming one: the Matthias-Schmidt-Berg has **two
  parallel double chairlifts** plus a drag lift, and the operator states the *chairlifts* (plural) were
  retrofitted with bicycle holders. So both go in as separate lifts, and our own trail endpoints confirm
  both are ridden -- Funride and Singletrail finish 29 m and 117 m from Doppelsesselbahn 1's base, while
  Flowtrail, Freeride and Enduro finish 50 m, 30 m and 89 m from Doppelsesselbahn 2's.
  **This is also where a first version of this script went wrong**, and the lesson generalises: the two
  sections chained happily on a 36 m endpoint check (their TOP stations are 36 m apart) and produced one
  850 m "lift" climbing 14 m. Two parallel lifts up the same hill always look like two sections joined at
  one end. `chain_sections()` therefore requires the joined line to keep CLIMBING -- an endpoint distance
  alone cannot tell a section joint from a pair of neighbours.
* **Racepark Schulenberg** -- the operator names one "Schlepplift" and OSM has two unrelated-looking ski
  drag lifts ("Skilift Großer Wiesenberg", "Skilift Quellental"), both within 30 m of our trails. The one
  whose TOP lands on the trails' own start area is taken; the other is recorded as excluded with the reason.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import (ElevationLookup, cumulative_km, haversine_m, osm_aerialway_survey,
                               overpass, write_region)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = os.path.join(ROOT, "Trailmap App", "regions", "harz.json")
ELEV_CACHE = os.path.join(ROOT, "Material", "elevation_cache.json")

BBOX = "51.68,10.28,51.89,11.06"

# (lift id, display name, sub-region, [OSM name(s) making up the ride, bottom section first], note)
WANTED = [
    ("lift_hz_bocksbergseilbahn", "Bocksbergseilbahn", "hahnenklee", ["Bocksbergseilbahn"],
     "the bike park's own access gondola; OSM also tags it aerialway:bicycle=yes, which agrees for once"),
    ("lift_hz_sessellift_rosstrappe", "Sessellift Rosstrappe", "bodetal", ["Sessellift Rosstrappe"],
     "the operator's 'Sessellift zur Rosstrappe', 09:30-18:00, carries riders and bikes"),
    ("lift_hz_wurmbergseilbahn", "Wurmbergseilbahn", "braunlage", ["Wurmbergseilbahn"],
     "6-person gondola to the 971 m summit, two start platforms at the top; e-bikes permitted"),
    ("lift_hz_doppelsesselbahn_1", "Doppelsesselbahn 1", "andreasberg", ["Doppelsesselbahn 1"],
     "one of the Matthias-Schmidt-Berg's two parallel double chairlifts, both retrofitted with bicycle "
     "holders by the operator (Alberti-Lift GmbH); Funride and Singletrail finish at its base"),
    ("lift_hz_doppelsesselbahn_2", "Doppelsesselbahn 2", "andreasberg", ["Doppelsesselbahn 2"],
     "the second parallel chairlift, ~176 m west at the base and 36 m from the other at the top; "
     "Flowtrail, Freeride and Enduro finish at its base"),
    ("lift_hz_schlepplift_schulenberg", "Schlepplift Racepark", "schulenberg",
     ["Skilift Großer Wiesenberg"],
     "the park's own single Schlepplift; picked over 'Skilift Quellental' because its top station sits 4 m "
     "from the trails' own start area while Quellental's lands 31 m from a trail's lower half"),
]

EXCLUDED = [
    ("Seilbahn Thale", "bodetal", "the Kabinenbahn to the Hexentanzplatz on the opposite valley side; the "
                                 "bike park runs only the Rosstrappe chairlift, and OSM tags this one "
                                 "aerialway:bicycle=no"),
    ("Zauberteppich", "hahnenklee", "a 171 m magic carpet for the beginners' area, not a bike-carrying lift"),
    ("Schlepplift", "andreasberg", "a 285 m t-bar on the same hill; the operator retrofitted bike holders "
                                   "on the two CHAIRLIFTS only, so this one carries no bikes"),
    ("Skilift Quellental", "schulenberg", "the second, shorter ski drag lift on the hill; not the park's"),
    ("Hexen-Express", "braunlage", "Braunlage's winter chairlift on the Hexenritt side; the bike park runs "
                                   "only the Wurmberg gondola in summer"),
    ("Hasselkopflift / Hexenrittlift / Nordhang / Rathauslift", "braunlage", "winter-only drag lifts"),
]

# Villages the six parks are actually described by -- one per park plus the two larger towns the Trailpark
# is spread between. Coordinates come from OSM's own place nodes, never typed by hand (a hand-typed Samnaun
# once landed 1 460 m from the village).
#
# Names are OSM's own spelling, which is not always the one a tourism page uses: the town is
# "Ilsenburg (Harz)" and the village is plain "Schulenberg", not "Schulenberg im Oberharz". Goslar and
# Wernigerode are deliberately absent -- both sit 5 km+ from any trail in the region, and Hahnenklee (a
# Goslar district) already labels that corner. Drübeck and Darlingerode stay despite being 1.7-1.8 km out,
# because Trailpark Harz's own site describes itself as lying "rund um Ilsenburg, Darlingerode und
# Drübeck": they are how that park is located, which is exactly what a place label is for.
PLACE_NAMES = ["Ilsenburg (Harz)", "Darlingerode", "Drübeck", "Hahnenklee", "Thale", "Treseburg",
               "Schulenberg", "Sankt Andreasberg", "Braunlage"]


def chain_sections(lift_id, parts, ele):
    """Join a lift's OSM sections into one bottom-to-top line, verifying the result actually climbs.

    An endpoint-distance check alone is not enough and this is not hypothetical -- St. Andreasberg's two
    PARALLEL chairlifts sit 36 m apart at their top stations, so a distance-only check joined them into a
    single 850 m line that gained 14 m over its length. Requiring each appended section to continue
    climbing is what distinguishes "the next section up" from "the neighbouring lift".
    """
    geom = [list(p) for p in parts[0]["geom"]]
    elevs = ele([[p[0], p[1]] for p in geom])
    if elevs[0] > elevs[-1]:                      # orient the first section bottom-first
        geom.reverse()
        elevs.reverse()
    for nxt in parts[1:]:
        g = [list(p) for p in nxt["geom"]]
        e = ele([[p[0], p[1]] for p in g])
        if e[0] > e[-1]:
            g.reverse()
            e.reverse()
        gap = haversine_m(geom[-1], g[0])
        if gap > 120:
            raise SystemExit("%s: %s starts %.0f m from the previous section's top -- not one lift"
                             % (lift_id, nxt["name"], gap))
        if e[-1] <= elevs[-1] + 20:
            raise SystemExit("%s: appending %s would gain only %.0f m -- these are parallel lifts, not "
                             "two sections of one" % (lift_id, nxt["name"], e[-1] - elevs[-1]))
        print("   %s: chained %s at +%.0f m, %+.0f m of further climb"
              % (lift_id, nxt["name"], gap, e[-1] - elevs[-1]))
        skip = 1 if gap < 1 else 0
        geom.extend(g[skip:])
        elevs.extend(e[skip:])
    return geom, elevs


def main():
    data = json.load(open(REGION, encoding="utf-8"))
    rows = {r["name"]: r for r in osm_aerialway_survey(BBOX, min_len_m=150)}
    ele = ElevationLookup(ELEV_CACHE)

    lifts = []
    for lift_id, name, region, osm_names, note in WANTED:
        parts = []
        for n in osm_names:
            if n not in rows:
                raise SystemExit("OSM has no aerialway named %r" % n)
            parts.append(rows[n])
        geom, elevs = chain_sections(lift_id, parts, ele)
        # Store bottom-station-first: the app derives the climb and the boarding station from the order.
        if elevs[0] > elevs[-1]:
            geom.reverse()
            elevs.reverse()
        lift = {"id": lift_id, "name": name, "region": region,
                "len": round(cumulative_km(geom)[-1], 2),
                "baseEle": round(elevs[0]), "topEle": round(elevs[-1]),
                "coords": [[round(p[0], 6), round(p[1], 6)] for p in geom]}
        lifts.append(lift)
        print("%-34s %-14s %5.2f km  %4d -> %4d m  (%s, OSM bike=%s)"
              % (name, region, lift["len"], lift["baseEle"], lift["topEle"],
                 parts[0]["aerialway"], parts[0]["bike"]))

    # ---- places -------------------------------------------------------------------------------------
    q = ('[out:json][timeout:180];node[place~"^(city|town|village|hamlet|suburb)$"](%s);out tags center;'
         % BBOX)
    found = {}
    for e in overpass(q)["elements"]:
        nm = e.get("tags", {}).get("name")
        if nm in PLACE_NAMES and nm not in found:
            found[nm] = [round(e["lat"], 5), round(e["lon"], 5)]
    places = []
    all_pts = [c for g in data["trailGeo"].values() for c in g[::3]]
    for nm in PLACE_NAMES:
        if nm not in found:
            print("   place NOT in OSM, skipped: %s" % nm)
            continue
        ll = found[nm]
        dist = min(haversine_m(ll, p) for p in all_pts)
        places.append({"name": nm, "lat": ll[0], "lng": ll[1]})
        print("place %-26s %.5f,%.5f   nearest trail %5.0f m" % (nm, ll[0], ll[1], dist))

    write_region(REGION, data["lineTrails"], data["trailGeo"], data["elevationProfiles"],
                 places=places, lifts=lifts)
    print("\nwrote %d lifts, %d places" % (len(lifts), len(places)))
    print("excluded:")
    for nm, reg, why in EXCLUDED:
        print("   %-46s (%s) %s" % (nm, reg, why))


if __name__ == "__main__":
    main()
