# -*- coding: utf-8 -*-
"""Build regions/laax.json -- Flims Laax Falera (Graubünden, CH).

Sources, each authoritative for a different thing:

  Outdooractive GPX          geometry with real per-point elevation, plus the published length/descent.
                             Fetched unauthenticated via download.tour.gpx (docs/finale-ligure.md), cached in
                             Material/Laax/.
  flimslaax.com / laax.com   the operator's own difficulty COLOUR, which wins where it states one.
  Outdooractive S-rating     difficulty for the trails the operator publishes no colour for, on the same
                             S1->blau / S2->rot / S3->schwarz / S4->schwarz shift used in Finale.
  OpenStreetMap              lift geometry only, and the Gronda Trail, which has no Outdooractive route.

One conflict worth knowing: Outdooractive rates **Never End** S2 (which would be rot) while the region's own
pages call it black. The operator wins -- it is their grading of their own trail, and OSM agrees
(mtb:scale:imba=3, i.e. black diamond).

Run:  python tools/build_laax.py     (then update_region_versions.py + validate_region.py laax)
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import (parse_gpx, build_trail, write_region, region_summary,  # noqa: E402
                               overpass, chain_ways, haversine_m, cumulative_km, ElevationLookup,
                               bounds_of)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, "Material", "Laax")
OUT = os.path.join(ROOT, "Trailmap App", "regions", "laax.json")
BBOX = "46.78,9.15,46.90,9.32"
ELEV_CACHE = os.path.join(ROOT, "Material", "elevation_cache.json")

# (slug, id, display name, diff, diff source, official (km, up, down) or None)
# `official` uses the published descent with up=0 where the source only gives a drop -- every one of these is
# a gravity descent, and build_trail keeps the GPX's own figures when official is None.
TRAILS = [
    ("foppa", 801776376, "Foppa Trail", "gruen", "operator: green", (3.5, 0, 330)),
    ("gronda", None, "Gronda Trail", "blau", "operator: blue", None),
    ("alp_dadens", 801776324, "Alp Dadens Trail", "blau", "OA S1", (2.6, 0, 333)),
    ("runca", 56205408, "Runca Trail", "rot", "operator: red", None),
    ("segnes", 65006536, "Segnes Trail", "rot", "operator: red", (3.8, 0, 482)),
    ("nagens", 64989761, "Nagens Trail", "rot", "operator: red", (5.2, 0, 583)),
    ("green_valley", 64989808, "Green Valley Trail", "rot", "operator: red", (2.1, 0, 248)),
    ("never_end", 64989486, "Never End Trail", "schwarz", "operator: black", (6.2, 0, 967)),
    ("vorab", 65005896, "Vorab Trail", "schwarz", "OA S3", (2.2, 0, 294)),
    ("crest_la_siala", 65006309, "Crest la Siala Trail", "schwarz", "OA S4", (3.2, 0, 589)),
    ("laaxer_stoeckli", 806996596, "Laaxer Stöckli", "schwarz", "OA S4", (2.2, 0, 327)),
    ("crest_da_tiarms", 806994780, "Crest da Tiarms Trail", "schwarz", "OA S4", (4.7, 0, 614)),
]

# Lifts: OSM's bike tag agrees with the operator here (FlemXpress, Arena Express and the Laax cable car),
# so both point the same way. Sections are separate ways in OSM and stay separate lifts -- that is what they
# are on the ground, and it is how Bike Kingdom's Chur sections are stored too.
LIFTS = [
    ("lift_laax_crap_sogn_gion", "Luftseilbahn LAAX – Crap Sogn Gion", "laax", r"^LAAX - Crap Sogn Gion$"),
    ("lift_laax_flemx_1", "FlemXpress Flims – Foppa", "flims", r"^FlemXpress Flims - Foppa$"),
    ("lift_laax_flemx_2", "FlemXpress Foppa – Startgels", "flims", r"^FlemXpress Foppa - Startgels$"),
    ("lift_laax_flemx_3", "FlemXpress Startgels – Segnes", "flims", r"^FlemXpress Startgels - Segnes$"),
    ("lift_laax_flemx_4", "FlemXpress Segnes – Nagens Sura", "flims", r"^FlemXpress Segnes - Nagens Sur"),
    ("lift_laax_arena_1", "Arena Express Flims – Plaun", "flims", r"^Arena Express Flims - Plaun$"),
    ("lift_laax_arena_2", "Arena Express Plaun – Scansinas", "flims", r"^Arena Express Plaun - Scansina"),
    ("lift_laax_arena_3", "Arena Express Scansinas – Nagens", "flims", r"^Arena Express Scansinas - Nage"),
]
# Deliberately excluded: everything OSM marks without a bike tag, including the Vorab chain
# (Crap Masegn / Fuorcla / Vorab). laax.com names a "Vorab cable car" for bike access in prose, but no
# single OSM way for that chain carries a bike tag, and guessing which of four sections take bikes would be
# inventing operator policy. The Vorab Trail is in the data; how you get up there is left unstated.

# OSM's own node for the village is named "Laax GR" (the canton suffix); our label drops it, since nobody
# calls it that. The rest match their OSM names exactly.
PLACES = [("Flims", "Flims"), ("Laax", "Laax GR"), ("Falera", "Falera"),
          ("Sagogn", "Sagogn"), ("Schluein", "Schluein")]


def osm_named(name_regex, highway=r"path|track|footway|cycleway"):
    """The named trail as one chained line from OSM. Returns (coords, kept_m, total_m)."""
    j = overpass('[out:json][timeout:240];way[highway~"%s"]["name"~"%s"](%s);out tags geom;'
                 % (highway, name_regex, BBOX))
    geoms = [[[p["lat"], p["lon"]] for p in e["geometry"]] for e in j["elements"]
             if len(e.get("geometry") or []) >= 2]
    if not geoms:
        raise SystemExit("OSM: nothing named %r" % name_regex)
    chain, _left = chain_ways(geoms)
    return chain, cumulative_km(chain)[-1] * 1000, sum(cumulative_km(g)[-1] for g in geoms) * 1000


def osm_lifts():
    q = ('[out:json][timeout:240];(way[aerialway]["aerialway"!="station"](%s);'
         'way[railway~"funicular"](%s););out tags geom;' % (BBOX, BBOX))
    out = []
    for e in overpass(q)["elements"]:
        t = e.get("tags", {})
        g = [[round(p["lat"], 6), round(p["lon"], 6)] for p in e.get("geometry", [])]
        if len(g) >= 2 and t.get("name"):
            out.append((t, g, e["id"]))
    return out


def osm_places(names):
    q = ('[out:json][timeout:180];node[place~"^(city|town|village)$"]["name"~"^(%s)$"](%s);out tags center;'
         % ("|".join(names), BBOX))
    got = {}
    for e in overpass(q)["elements"]:
        got.setdefault(e["tags"]["name"], (round(e["lat"], 5), round(e["lon"], 5)))
    return got


def main():
    ele = ElevationLookup(ELEV_CACHE)
    trails, geo, profs, notes = [], {}, {}, []

    for slug, rid, name, diff, why, official in TRAILS:
        if rid is None:                       # Gronda has no Outdooractive route; OSM has the whole trail
            coords, kept, total = osm_named(r"^Gronda Trail$")
            raw = coords
            notes.append("%s: aus OSM (%.0f m von %.0f m verkettet)" % (name, kept, total))
        else:
            path = os.path.join(MAT, "%s_%d.gpx" % (slug, rid))
            raw = parse_gpx(io.open(path, encoding="utf-8", errors="replace").read())
            if len(raw) < 2:
                raise SystemExit("%s: %s has no points" % (name, path))
        entry, coords, prof = build_trail("laax_" + slug, name, region="?", diff=diff,
                                         raw_points=raw, official=official, elevation=ele)
        trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof

    # Lifts, and the sub-region split derived FROM them: a trail belongs to the side of the resort whose
    # bike lift its start is closest to. Beats eyeballing a longitude, and it is the same split the operator's
    # own trail table uses when it lists an access lift per trail.
    ways = osm_lifts()
    lifts = []
    for lid, name, region, rx in LIFTS:
        hits = [w for w in ways if re.search(rx, w[0]["name"])]
        if len(hits) != 1:
            raise SystemExit("%s: %r matched %d ways" % (lid, rx, len(hits)))
        tags, coords, wid = hits[0]
        e = ele([coords[0], coords[-1]])
        if e[0] > e[-1]:
            coords, e = coords[::-1], e[::-1]
        lifts.append({"id": lid, "name": name, "region": region, "type": tags.get("aerialway") or "gondola",
                      "coords": coords, "baseEle": int(round(e[0])), "topEle": int(round(e[-1])),
                      "osm": "way/%d" % wid})

    # The sub-region split follows which side of the resort a trail's start is served from, measured against
    # EVERY lift there rather than only the bike ones: the high-alpine trails (Vorab, Laaxer Stöckli) start
    # next to lifts that take no bikes, and against bike lifts only they came out 3-4 km from the wrong side's
    # gondola -- Vorab was assigned to Flims, which is the far side of the massif. The side of each lift comes
    # from its own name, which in this resort says plainly where it belongs.
    FLIMS_LIFT = re.compile(r"FlemXpress|Arena Express|Crap da Flem|Cassons|Nagens|Segnes|Plaun|Scansinas")
    for t in trails:
        start = geo[t["id"]][0]
        def d(w):
            return min(haversine_m(start, c) for c in w[1])
        tags, coords, _wid = min(ways, key=d)
        t["region"] = "flims" if FLIMS_LIFT.search(tags["name"]) else "laax"
        notes.append("%-24s -> %-6s (naechste Bahn: %s, %.0f m)"
                     % (t["name"], t["region"], tags["name"], d((tags, coords, None))))

    found = osm_places([osm for _, osm in PLACES])
    places = [{"name": label, "lat": found[osm][0], "lng": found[osm][1]}
              for label, osm in PLACES if osm in found]
    missing = [label for label, osm in PLACES if osm not in found]

    data = write_region(OUT, trails, geo, profs, places=places, lifts=lifts)
    print("\n".join(notes))
    print("\nfehlende Orte in OSM: %s" % (missing or "keine"))
    print(region_summary(data))
    print("bounds fuer REGION_CATALOG: %s" % bounds_of(geo))
    for t in trails:
        print("   %-24s %-8s %5.2f km  %4d up / %4d down" % (t["name"], t["diff"], t["len"], t["up"], t["down"]))


if __name__ == "__main__":
    sys.exit(main())
