# -*- coding: utf-8 -*-
"""Add or replace a region's `lifts` array. One table per region, OSM for geometry only.

    python tools/add_lifts.py brandnertal schladming zugspitzarena
    python tools/add_lifts.py                 # every region listed below

The rules this encodes are the ones docs/lifts-feature.md records the hard way:

* **The operator's summer list decides membership**, never OSM's `aerialway:bicycle` tag. That tag was wrong
  in both directions in Saalbach, and is reported here only as a cross-check.
* **Anchor the name pattern**, and treat two matches as an error rather than picking the longer way. A loose
  pattern plus "longest wins" silently chose a T-bar over the gondola it was meant to find in Bike Kingdom.
* **A funicular is not an `aerialway`.** Sölden's Zentrum Shuttle is `railway=funicular`, which is why the
  aerialway survey could never find it -- so this queries both.
* **Store bottom-station-first.** The app derives the climb and the boarding station from the coordinate
  order; a flipped lift would board at the top and show a negative climb.
* Temporary closures are deliberately not modelled: nothing in this app syncs operating status, so a
  hardcoded flag would rot while looking authoritative.

Each entry: id, name, region (a sub-region key), osm (anchored regex on OSM's own name), and `note` for why
it is in or what is unusual about it. Lifts the operator excludes belong in EXCLUDED with the reason, so the
next session does not have to re-research them.
"""
import collections
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import overpass, haversine_m, cumulative_km, ElevationLookup  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS_DIR = os.path.join(ROOT, "Trailmap App", "regions")
#: One cache for every region -- a coordinate is globally unique, so sharing it only saves lookups.
ELEV_CACHE = os.path.join(ROOT, "Material", "elevation_cache.json")

LIFTS = {
    # ---------------------------------------------------------------------------------------------
    # Brandnertal (Vorarlberg). Source: bikepark-brandnertal.at/betriebszeiten -- it names exactly three
    # lifts as the ones serving the park and the trails, all three running 14.5.-1.11.2026.
    # ---------------------------------------------------------------------------------------------
    "brandnertal": dict(bbox="47.09,9.68,47.17,9.80", lifts=[
        dict(id="lift_bnt_loischkopfbahn", name="Loischkopfbahn", region="tschengla",
             osm=r"^Loischkopfbahn$",
             note="new for summer 2026, a 10-person gondola with bike cabs; it is what serves the "
                  "Tschengla bike park"),
        dict(id="lift_bnt_dorfbahn", name="Dorfbahn Brand", region="brand_singletrails",
             osm=r"^Dorfbahn$"),
        dict(id="lift_bnt_panoramabahn", name="Panoramabahn Burtschasattel", region="brand_singletrails",
             osm=r"^Panoramabahn Burtschasattel$",
             note="the operator calls it just 'Panoramabahn'; OSM's fuller name is kept, it is unambiguous"),
    ], excluded=[
        ("Palüdbahn", "runs in summer but is not on the bike-park's own lift list, and OSM has no bike tag"),
    ]),

    # ---------------------------------------------------------------------------------------------
    # Planai/Schladming. planai.at: bikes go up in the Planai gondola (two sections, A and B);
    # reiteralm.at: the bike centre sits at the Preunegg Jet valley station, which is the bike access.
    # ---------------------------------------------------------------------------------------------
    "schladming": dict(bbox="47.32,13.52,47.44,13.80", lifts=[
        dict(id="lift_sch_planaibahn_i", name="Planaibahn I", region="planai", osm=r"^Planaibahn I$",
             note="the '10er-Planai' is these two sections together"),
        dict(id="lift_sch_planaibahn_ii", name="Planaibahn II", region="planai", osm=r"^Planaibahn II$"),
        dict(id="lift_sch_preunegg_jet", name="Preunegg Jet", region="reiteralm", osm=r"^Preunegg Jet$",
             note="the Reiteralm bike centre is at its valley station"),
    ], excluded=[
        ("Silver Jet, Sepp'n Jet, Reiteralm I, Gasselhöhe II",
         "Reiteralm winter lifts; the operator routes bike transport over the Preunegg Jet"),
        ("Hochwurzenbahn", "outside the two sub-regions we have trails for"),
    ]),

    # ---------------------------------------------------------------------------------------------
    # Tiroler Zugspitz Arena. zugspitzarena.com lists six summer cable cars; the region's own bike pages
    # state free bike transport on the Ehrwalder Almbahn, Grubigstein, Marienberg lifts, Almkopfbahn and the
    # Berwang lifts. Grubigstein and Marienberg are two sections each, hence eight OSM ways for six lifts.
    # ---------------------------------------------------------------------------------------------
    "zugspitzarena": dict(bbox="47.32,10.68,47.47,11.00", lifts=[
        dict(id="lift_zta_ehrwalder_almbahn", name="Ehrwalder Almbahn", region="ehrwald_wetterstein",
             osm=r"^Ehrwalder Almbahn$"),
        dict(id="lift_zta_wettersteinbahn", name="Ehrwalder Wettersteinbahn", region="ehrwald_wetterstein",
             osm=r"^Wettersteinbahn$", note="9 m from the Blue Bird trail head"),
        dict(id="lift_zta_grubigsteinbahn", name="Grubigsteinbahn (1. Sektion)",
             region="lermoos_biberwier", osm=r"^Grubigsteinbahn$"),
        dict(id="lift_zta_grubig_ii", name="Grubigsteinbahn (2. Sektion)", region="lermoos_biberwier",
             osm=r"^Grubig II$", note="OSM calls it 'Grubig II'; it is the upper section to the Grubigstein"),
        dict(id="lift_zta_marienbergbahn_i", name="Marienbergbahn I", region="lermoos_biberwier",
             osm=r"^Marienbergbahn I$"),
        dict(id="lift_zta_marienbergbahn_ii", name="Marienbergbahn II", region="lermoos_biberwier",
             osm=r"^Marienbergbahn II$"),
        dict(id="lift_zta_sunnalmbahn", name="Berwanger SunnAlmBahn", region="berwang_bichlbach",
             osm=r"^Berwanger SunnAlmBahn$"),
        dict(id="lift_zta_almkopfbahn", name="Almkopfbahn Bichlbach", region="berwang_bichlbach",
             osm=r"^Almkopfbahn$", note="a mixed_lift -- gondolas and chairs on one cable"),
    ], excluded=[
        ("Tiroler Zugspitzbahn, Seilbahn Zugspitze, Zugspitz-Gletscherbahn",
         "glacier cable cars, no bike transport (OSM has bicycle=no on two of them)"),
        ("Schihüttenbahn, GamsJet, Grubigalmbahn, Hochmoos-Express",
         "Grubigstein winter lifts, not on the operator's summer list"),
        ("Rastkopfbahn, Egghof Sun Jet, Thanellerbahn, Obere Karbahn I+II",
         "Berwang/Bichlbach winter lifts"),
    ]),

    # ---------------------------------------------------------------------------------------------
    # Sauerland/Upland. Bbox covers both Winterberg and Willingen (Ettelsberg), ~15 km apart -- checked
    # for name collisions across the combined area before relying on it, since a duplicate elsewhere
    # would otherwise "resolve" to the wrong way silently.
    #
    # bikepark-winterberg.de ("The Mother") names exactly three lifts as bringing riders up --
    # Panorama-Lift (main, to the summit), Kappe-Lift (mid zone), Schneewittchen-Lift (beginner
    # trails). All three carry OSM's own aerialway:bicycle=summer tag, confirming the operator's list
    # independently. Trailpark Winterberg (the other Winterberg sub-region) is free and has no lift at
    # all -- riders climb via the signed Uphill-Trail/Möppis Mover instead, so it gets no entry here.
    #
    # willingen.de: Green Trails Willingen's two touring loops are served by the Ettelsberg-Seilbahn
    # (the valley gondola, bicycle=yes) and the K1 8er-Sesselbahn (bicycle=summer) -- both independently
    # confirmed by OSM's own bike tag, same as the Winterberg three. MTB Zone Bikepark Willingen's own
    # lift(s), if any, are moot here since none of its 12 named descents have a GPX source and are not
    # built (see docs/sauerland-recherche.md) -- nothing to serve yet.
    #
    # OSM's own names differ from the operators' marketing names in three of five cases (kept as the
    # `name` here; `osm` matches OSM's shorter/different name).
    #
    # Green Hill Bikepark: two drag lifts, Hohe Lied 1 and Hohe Lied 2 (both aerialway:bicycle=yes,
    # website=greenhill-bikepark.de -- confirmed as this park's own, not a coincidence of naming).
    # Bbox widened to 8.343 on the west to reach Green Hill (~40 km from Winterberg/Willingen);
    # re-checked for collisions across the whole widened area before relying on it.
    # ---------------------------------------------------------------------------------------------
    "sauerland": dict(bbox="51.17,8.343,51.32,8.65", lifts=[
        dict(id="lift_wb_panoramabahn", name="Panorama-Lift", region="bikepark_winterberg",
             osm=r"^Panoramabahn$", note="Hauptlift zum Gipfel"),
        dict(id="lift_wb_kappe", name="Kappe-Lift", region="bikepark_winterberg", osm=r"^Kappe$",
             note="mittlere Zone"),
        dict(id="lift_wb_schneewittchen", name="Schneewittchen-Lift", region="bikepark_winterberg",
             osm=r"^Schneewittchenhang$", note="Einsteiger-Strecken"),
        dict(id="lift_wi_ettelsberg", name="Ettelsberg-Seilbahn", region="willingen",
             osm=r"^Ettelsberg-Kabinenseilbahn$", note="Talstation-Kabinenseilbahn zum Ettelsberg"),
        dict(id="lift_wi_k1", name="K1 8er-Sesselbahn", region="willingen",
             osm=r"^Sesselbahn Köhlerhagen K1$", note="8er-Sesselbahn für die leichteren Trails"),
        dict(id="lift_gh_hohe_lied_1", name="Hohe Lied 1", region="greenhill",
             osm=r"^Hohe Lied 1$", note="Schlepplift"),
        dict(id="lift_gh_hohe_lied_2", name="Hohe Lied 2", region="greenhill",
             osm=r"^Hohe Lied 2$", note="Schlepplift"),
    ], excluded=[
        ("Rauher Busch, Bäre-Herrloh, Quick Jet, Kleine Bäre, Bäre Bremberg X-Press, Brembergkopf 1, "
         "Poppenberg 1, Poppenberg 2, Astenstraße, St Georg Schanze, Sürenberg, Landallift, "
         "Rodellift Bremberg, Förderband Herrloh 1, Förderband Köppchen, Förderband Kinderland, "
         "Übungslift Herrloh II, Übungslift Herrloh III",
         "Winterberg winter/ski lifts and magic-carpets/rope-tows elsewhere on the same mountain -- "
         "none carry OSM's aerialway:bicycle tag, and none are on the operator's own three-lift summer "
         "list"),
        ("Oberer Wilddieblift, Sonnenlift, Sesselbahn Ritzhagen, Ski- und Rodelförderband Ritzhagen, "
         "Mittlerer Wilddieblift, Unterer Wilddieblift I/II, Förderband Dorfwiese 1/2, "
         "R1 - Rodelpiste Dorfwiese, Rodel-/Skihanglift Sonnenhang",
         "Willingen winter/ski/sledge lifts on the same mountain -- no bicycle tag, not part of Green "
         "Trails Willingen's two lift-served loops"),
    ]),
}


def resolve(bbox, specs, verbose=True):
    """Match each spec against OSM geometry and return the region file's `lifts` array."""
    q = ('[out:json][timeout:240];('
         'way["aerialway"]["aerialway"!="station"](%s);'
         'way["railway"~"funicular"](%s););out tags geom;' % (bbox, bbox))
    ways = []
    for e in overpass(q)["elements"]:
        g = [[round(p["lat"], 6), round(p["lon"], 6)] for p in e.get("geometry", [])]
        if len(g) >= 2 and (e.get("tags") or {}).get("name"):
            ways.append((e["tags"], g, e["id"]))

    ele = ElevationLookup(ELEV_CACHE)
    out = []
    for spec in specs:
        rx = re.compile(spec["osm"])
        hits = [w for w in ways if rx.search(w[0]["name"])]
        if not hits:
            raise SystemExit("%s: no OSM way matches %r" % (spec["id"], spec["osm"]))
        if len(hits) > 1:
            raise SystemExit("%s: %r matches %d ways: %s"
                             % (spec["id"], spec["osm"], len(hits), [h[0]["name"] for h in hits]))
        tags, coords, wid = hits[0]
        e = ele([coords[0], coords[-1]])
        if e[0] > e[-1]:
            coords, e = coords[::-1], e[::-1]
        entry = collections.OrderedDict([
            ("id", spec["id"]), ("name", spec["name"]), ("region", spec["region"]),
            ("type", tags.get("aerialway") or tags.get("railway")), ("coords", coords),
            ("baseEle", int(round(e[0]))), ("topEle", int(round(e[-1]))), ("osm", "way/%d" % wid),
        ])
        out.append(entry)
        if verbose:
            print("  ok %-34s %-11s %5.0f m  %d -> %d m  bike-Tag: %-7s way/%d"
                  % (spec["name"], entry["type"], cumulative_km(coords)[-1] * 1000,
                     entry["baseEle"], entry["topEle"],
                     tags.get("aerialway:bicycle") or tags.get("bicycle") or "-", wid))
    return out


def main():
    wanted = [a for a in sys.argv[1:] if not a.startswith("-")] or sorted(LIFTS)
    for key in wanted:
        if key not in LIFTS:
            raise SystemExit("no lift table for %r" % key)
        cfg = LIFTS[key]
        print("=== %s" % key)
        lifts = resolve(cfg["bbox"], cfg["lifts"])
        for name, why in cfg.get("excluded", []):
            print("  -- %-34s %s" % (name, why))

        path = os.path.join(REGIONS_DIR, key + ".json")
        d = json.load(io.open(path, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
        subs = {t["region"] for t in d["lineTrails"]}
        for l in lifts:
            if l["region"] not in subs:
                raise SystemExit("%s: region %r is not one this file's trails use (%s)"
                                 % (l["id"], l["region"], sorted(subs)))
            # sanity: a lift far from every trail is a same-named way somewhere else entirely
            near = min(haversine_m(l["coords"][0], c) for t in d["lineTrails"]
                       for c in d["trailGeo"][t["id"]][::3])
            if near > 3000:
                raise SystemExit("%s: base station is %.0f m from the nearest trail" % (l["id"], near))
        d["lifts"] = lifts
        json.dump(d, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(", ", ": "))
        print("  %d Lifte geschrieben\n" % len(lifts))
    print("danach: python tools/update_region_versions.py && python tools/validate_region.py")


if __name__ == "__main__":
    sys.exit(main())
