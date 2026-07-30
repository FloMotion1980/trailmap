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
whole region is built the same way rather than mixing sourced-vs-derived numbers trail by trail. One
exception found afterwards: Singletrack Haus-Aich's OWN overview page renders its three trails as a plain
HTML table (not a JS widget) with real Länge/Höhenmeter/Tiefenmeter cells -- Madame Flow Trail's 3.2 km /
40 up / 40 down there matches the GPX-derived 3.20/40/38 closely enough to trust the GPX numbers everywhere.

Difficulty IS a structured field after all -- the user was right to push back. It doesn't live on the
per-trail tour page (which only has it as loose prose, e.g. "im leichten Schwierigkeitsgrad"); it lives on
the LISTING pages, as a `teaser__difficulty--{blue,red,black}` badge on each trail's card
(schladming-dachstein.at/de/aktivitaeten/biken/bikepark-planai, .../bikepark-planai/downhill,
.../reiteralm-trails). Re-checked every trail against it 2026-07-30: all 12 Bikepark Schladming difficulties
already matched (including Stadium Flowline 408, previously only OSM-guessed -- confirmed official "leicht"
here). Reiteralm did not: Gassl Trail was rot, badge says schwer (schwarz); Hochalm Trail was blau, badge
says mittel (rot); Junior Trails was guessed gruen, badge says leicht (blau). All three corrected below.
The same listing page named two more real trails neither build had: Skill Area (110, blau) and Route 66
(66, rot) -- both added, both with a working tour page and GPX.
Singletrack Haus-Aich's own overview page is a plain table with no difficulty column at all; its three
trails keep the OSM mtb:scale=0 confirmation (Madame Flow, Jumper, AND Dr. Drop all tagged 0) as the only
available source.

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

# "Bike Area (400)" is not one trail -- the site's own connector-routes page names it as three parallel
# beginner lines sharing one top (the conveyor belt) and one bottom: Bobby Line, Cool Line, Rocket Line
# (schladming-dachstein.at's "Verbindungsstrecken" page; confirmed independently via a Sunkid press release,
# since no page names them per-GPX). The one "Bike Area" tour's GPX rides all three back to back, which is
# what drew as a self-crossing loop. Cut on raw-track revisits at the shared top/bottom points (index 0 =
# top, 41 = bottom, 43 = top again) -- see docs/adding-a-region.md and the trailrunde-feature.md loop notes
# for the same technique used on Forest Aisle. WHICH cut is Bobby/Cool/Rocket is not knowable from the data,
# so the user chose generic numbering (2026-07-30) rather than a guessed real name.
BIKE_AREA_CUTS = [(0, 42), (42, 63), (63, None)]  # raw-point index ranges, end exclusive except the last
# The listing page's own badge treats "Bike Area" as ONE card -- leicht -- covering all three lines; used
# for all three split entries since none has its own separate badge.
BIKE_AREA_DIFF = "blau"

# (gpx slug, id, display name, region, diff, diff source)
TRAILS = [
    # --- Bikepark Schladming (planai) -- diff unchanged from the 2026-07-28 build ---
    # "Bike Area (400)" itself is not built -- see BIKE_AREA_CUTS above and main() below.
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
    # --- Reiteralm Trails -- corrected 2026-07-30 against the listing page's teaser__difficulty badge ---
    ("reiteralm_100_eiskar_trail", "reiteralm_100_eiskar_trail", "Eiskar Trail (100)", "reiteralm", "blau",
     "confirmed: badge leicht"),
    ("reiteralm_101_buckelwald_trail", "reiteralm_101_buckelwald_trail", "Buckelwald Trail (101)",
     "reiteralm", "rot", "confirmed: badge mittel"),
    ("reiteralm_102_schnepfenwald_trail", "reiteralm_102_schnepfenwald_trail", "Schnepfenwald Trail (102)",
     "reiteralm", "blau", "confirmed: badge leicht"),
    ("reiteralm_103_gassl_trail", "reiteralm_103_gassl_trail", "Gassl Trail (103)", "reiteralm", "schwarz",
     "CORRECTED rot -> schwarz: badge says schwer"),
    ("reiteralm_104_hochalm_trail", "reiteralm_104_hochalm_trail", "Hochalm Trail (104)", "reiteralm",
     "rot", "CORRECTED blau -> rot: badge says mittel"),
    ("reiteralm_105_junior_trails", "reiteralm_105_junior_trails", "Junior Trails (105)", "reiteralm",
     "blau", "CORRECTED gruen (guessed) -> blau: badge says leicht"),
    ("reiteralm_106_holzer_trail", "reiteralm_106_holzer_trail", "Holzer Trail (106)", "reiteralm", "rot",
     "confirmed: badge mittel"),
    ("reiteralm_107_jump_trail", "reiteralm_107_jump_trail", "Jump Trail (107)", "reiteralm", "schwarz",
     "confirmed: badge schwer"),
    ("reiteralm_108_enduro_trail", "reiteralm_108_enduro_trail", "Enduro Trail (108)", "reiteralm",
     "schwarz", "confirmed: badge schwer, also matches OSM mtb:scale=3"),
    ("reiteralm_109_hochalm_enduro_trail", "reiteralm_109_hochalm_enduro_trail",
     "Hochalm Enduro Trail (109)", "reiteralm", "schwarz",
     "confirmed: badge schwer (previously only inferred from Enduro Trail's own confirmed schwarz)"),
    ("reiteralm_110_skill_area", "reiteralm_110_skill_area", "Skill Area (110)", "reiteralm", "blau",
     "new: found via the listing page after Bike Area's split raised the question of what else was missing; "
     "badge leicht"),
    ("reiteralm_66_route_66", "reiteralm_66_route_66", "Route 66 (66)", "reiteralm", "rot",
     "new: the 2026-07-28 build noted this name from OSM but couldn't find it in that bbox -- it has its "
     "own tour page after all; badge mittel"),
    # --- Singletrack Haus-Aich -- new sub-region, 3 trails ---
    ("hausaich_801_madame_flow_trail", "hausaich_801_madame_flow_trail", "Madame Flow Trail (801)",
     "hausaich", "gruen", "new: OSM mtb:scale=0"),
    ("hausaich_802_jumper_trail", "hausaich_802_jumper_trail", "Jumper Trail (802)", "hausaich", "gruen",
     "new: OSM mtb:scale=0"),
    ("hausaich_803_dr_drop_trail", "hausaich_803_dr_drop_trail", "Dr. Drop Trail (803)", "hausaich",
     "gruen", "new: OSM mtb:scale=0"),
]


def build_bike_area(trails, geo, profs, old_ids):
    """The three Bobby/Cool/Rocket lines, cut from the one recorded "Bike Area" GPX -- see BIKE_AREA_CUTS."""
    raw = parse_gpx(io.open(os.path.join(MAT, "planai_400_bike_area.gpx"), encoding="utf-8").read())
    for i, (lo, hi) in enumerate(BIKE_AREA_CUTS, start=1):
        tid = "planai_400_bike_area_%d" % i
        seg = raw[lo:hi]
        entry, coords, prof = build_trail(tid, "Bike Area %d (400)" % i, region="planai",
                                          diff=BIKE_AREA_DIFF, raw_points=seg)
        trails.append(entry)
        geo[tid] = coords
        profs[tid] = prof
        print("%-38s %-8s %6.2f km  %4d up / %4d down%s"
              % (entry["name"], BIKE_AREA_DIFF, entry["len"], entry["up"], entry["down"],
                 "" if tid in old_ids else "  [NEU]"))
    print("     -> split from one recorded loop (see BIKE_AREA_CUTS) -- which segment is really Bobby/Cool/"
          "Rocket Line is not knowable from the data, so the user chose generic numbering")


def main():
    d = json.load(io.open(OUT, encoding="utf-8"))
    old_ids = {t["id"] for t in d["lineTrails"]}
    trails, geo, profs = [], {}, {}

    build_bike_area(trails, geo, profs, old_ids)

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
