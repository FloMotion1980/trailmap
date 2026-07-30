# -*- coding: utf-8 -*-
"""Rebuild regions/schladming.json's trails from schladming-dachstein.at's own per-trail tour pages.

Replaces the 2026-07-28 build, whose geometry came from planai.at directly. The user found two trails
(Peak Flowline, Bike Area) visibly not matching schladming-dachstein.at's own map -- rather than track down
which of the two sources drew the wrong line, this rebuilds every trail from ONE consistent, current source:
each trail's own tour page at schladming-dachstein.at/de/aktivitaeten/touren/<Name>-7C-<num>_tour_<id>, which
embeds a real per-point-elevation GPX at tirol.mapservices.eu/nefos_app/api/gpx/... (found by the user, same
CONTWISE MAPS backend Zugspitz Arena and other Tirol tourism sites use). GPX cached in Material/Schladming/.

No official length/up/down is published as clean per-trail text on these pages (the stat widget loads via
JS, not present in the static HTML) -- length/up/down are GPX-derived throughout, for every trail, so the
whole region is built the same way rather than mixing sourced-vs-derived numbers trail by trail.

Difficulty: kept as-is for every trail that already existed (not what the user flagged as wrong, and the
2026-07-28 build sourced it from the operator's own colour words). The 5 trails new in this rebuild --
Reiteralm's Junior Trails and Hochalm Enduro Trail, and all three of Haus-Aich's -- have no operator colour
found; difficulty there is OSM mtb:scale (Madame Flow=0, Jumper=0) or inferred from sibling naming/branding
where OSM has nothing, flagged per-entry below.

Run:  python tools/build_schladming.py     (then update_region_versions.py + validate_region.py schladming)
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import build_trail, parse_gpx, bounds_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, "Material", "Schladming")
OUT = os.path.join(ROOT, "Trailmap App", "regions", "schladming.json")

# (gpx slug, id, display name, region, diff, diff source)
TRAILS = [
    # --- Bikepark Schladming (planai) -- diff unchanged from the 2026-07-28 build ---
    ("planai_400_bike_area", "planai_400_bike_area", "Bike Area (400)", "planai", "blau", "unchanged"),
    ("planai_401_uphill_flow_trail", "planai_401_uphill_flow_trail", "Uphill Flow Trail (401)", "planai",
     "blau", "unchanged"),
    ("planai_402_peak_flowline", "planai_402_peak_flowline", "Peak Flowline (402)", "planai", "blau",
     "unchanged"),
    ("planai_403_pro_downhill", "planai_403_pro_downhill", "Pro Downhill (403)", "planai", "schwarz",
     "unchanged"),
    ("planai_404_rookie_downhill", "planai_404_rookie_downhill", "Rookie Downhill (404)", "planai", "rot",
     "unchanged"),
    ("planai_405_99_jumpline", "planai_405_99_jumpline", "99 Jumpline (405)", "planai", "schwarz",
     "unchanged"),
    ("planai_406_monster_jumpline", "planai_406_monster_jumpline", "Monster Jumpline (406)", "planai",
     "schwarz", "unchanged"),
    ("planai_407_kessler_line", "planai_407_kessler_line", "Kessler Line (407)", "planai", "rot",
     "unchanged"),
    ("planai_408_stadium_flowline", "planai_408_stadium_flowline", "Stadium Flowline (408)", "planai",
     "blau", "unchanged"),
    ("planai_409_jack_lumber_trail", "planai_409_jack_lumber_trail", "Jack Lumber Trail (409)", "planai",
     "schwarz", "unchanged"),
    ("planai_410_worldcup_downhill", "planai_410_worldcup_downhill", "Worldcup Downhill (410)", "planai",
     "schwarz", "unchanged"),
    ("planai_411_downtown_line", "planai_411_downtown_line", "Downtown Line (411)", "planai", "rot",
     "unchanged"),
    # --- Reiteralm Trails -- 8 unchanged from 2026-07-28, 2 new ---
    ("reiteralm_100_eiskar_trail", "reiteralm_100_eiskar_trail", "Eiskar Trail (100)", "reiteralm", "blau",
     "unchanged"),
    ("reiteralm_101_buckelwald_trail", "reiteralm_101_buckelwald_trail", "Buckelwald Trail (101)",
     "reiteralm", "rot", "unchanged"),
    ("reiteralm_102_schnepfenwald_trail", "reiteralm_102_schnepfenwald_trail", "Schnepfenwald Trail (102)",
     "reiteralm", "blau", "unchanged"),
    ("reiteralm_103_gassl_trail", "reiteralm_103_gassl_trail", "Gassl Trail (103)", "reiteralm", "rot",
     "unchanged"),
    ("reiteralm_104_hochalm_trail", "reiteralm_104_hochalm_trail", "Hochalm Trail (104)", "reiteralm",
     "blau", "unchanged"),
    ("reiteralm_105_junior_trails", "reiteralm_105_junior_trails", "Junior Trails (105)", "reiteralm",
     "gruen", "new: kids progression area, treated like Haus-Aich's equally-branded beginner lines"),
    ("reiteralm_106_holzer_trail", "reiteralm_106_holzer_trail", "Holzer Trail (106)", "reiteralm", "rot",
     "unchanged"),
    ("reiteralm_107_jump_trail", "reiteralm_107_jump_trail", "Jump Trail (107)", "reiteralm", "schwarz",
     "unchanged"),
    ("reiteralm_108_enduro_trail", "reiteralm_108_enduro_trail", "Enduro Trail (108)", "reiteralm",
     "schwarz", "unchanged, confirmed by OSM mtb:scale=3"),
    ("reiteralm_109_hochalm_enduro_trail", "reiteralm_109_hochalm_enduro_trail",
     "Hochalm Enduro Trail (109)", "reiteralm", "schwarz",
     "new: no OSM tag found; inferred from Enduro Trail (108)'s own confirmed schwarz, which this trail "
     "runs parallel to and is named the same way relative to Hochalm Trail (104, blau)"),
    # --- Singletrack Haus-Aich -- new sub-region, 3 trails ---
    ("hausaich_801_madame_flow_trail", "hausaich_801_madame_flow_trail", "Madame Flow Trail (801)",
     "hausaich", "gruen", "new: OSM mtb:scale=0"),
    ("hausaich_802_jumper_trail", "hausaich_802_jumper_trail", "Jumper Trail (802)", "hausaich", "gruen",
     "new: OSM mtb:scale=0"),
    ("hausaich_803_dr_drop_trail", "hausaich_803_dr_drop_trail", "Dr. Drop Trail (803)", "hausaich",
     "gruen", "new: OSM mtb:scale=0"),
]


def main():
    d = json.load(io.open(OUT, encoding="utf-8"))
    old_ids = {t["id"] for t in d["lineTrails"]}
    trails, geo, profs = [], {}, {}

    for slug, tid, name, region, diff, why in TRAILS:
        path = os.path.join(MAT, slug + ".gpx")
        raw = parse_gpx(io.open(path, encoding="utf-8").read())
        entry, coords, prof = build_trail(tid, name, region=region, diff=diff, raw_points=raw)
        trails.append(entry)
        geo[tid] = coords
        profs[tid] = prof
        tag = "" if tid in old_ids else "  [NEU]"
        print("%-38s %-8s %6.2f km  %4d up / %4d down%s" % (name, diff, entry["len"], entry["up"],
                                                             entry["down"], tag))
        if not why.startswith("unchanged"):
            print("     -> %s" % why)

    d["lineTrails"] = trails
    d["trailGeo"] = geo
    d["elevationProfiles"] = profs
    # A place label for Haus-Aich is added separately once its OSM coordinate is looked up -- see the
    # runbook in docs/adding-a-region.md: never a typed coordinate.

    json.dump(d, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(", ", ": "))
    print("\n%d Trails, bounds: %s" % (len(trails), bounds_of(geo)))


if __name__ == "__main__":
    sys.exit(main())
