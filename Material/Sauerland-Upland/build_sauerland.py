# -*- coding: utf-8 -*-
"""Build regions/sauerland.json — Sauerland/Upland region group, 2026-08-11.

Three sub-regions, purely geographic bracket (user decision 2026-07-26):
  trailpark_winterberg - Trailpark Winterberg (winterberg.de, Outdooractive-hosted). Free, no lift --
                riders climb via the signed Uphill-Trail/Möppis Mover or their own legs.
  bikepark_winterberg  - "The Mother" / Bikepark Winterberg (bikepark-winterberg.de, Erlebnisberg
                Kappe). Lift-served: Panorama-Lift (main, to the summit), Kappe-Lift (mid zone),
                Schneewittchen-Lift (beginner trails) -- see tools/add_lifts.py's "sauerland" table.
                Two DISTINCT trail networks on different hills of the same town -- confirmed by
                cross-checking trail names/lift names/location text, not a duplicate. Split into two
                sub-regions 2026-08-13 (originally lumped into one "winterberg" sub-region) per the
                user, matching how Willingen/Green Hill are already split out.
  willingen   - Green Trails Willingen's two long touring loops (Gipfel-Runde Hoppecke,
                Ruthenaar-Double), via willingen.de's destination-data-proxy GPX endpoint.
  mtbzone_willingen - MTB Zone Willingen (the bikepark), added 2026-08-14 -- this file used to record
                it as having no GPX source anywhere; the user found its 8 main trails on Trailforks
                instead, kept as its own sub-region rather than merged into `willingen` above (two
                distinct networks sharing a town, same reasoning as the two Winterberg sub-regions).
                See the sub-region's own section further down for the sourcing detail.
  greenhill   - Green Hill Bikepark (Schmallenberg-Gellinghausen), harvested from Trailforks via the
                lighter /widgets/trail/?trailid=..&elevation=1&basic=1 embed, which still embeds a plain
                points[] array (lat/lng/elevation) in an inline <script> -- unlike the main trail page,
                which now renders geometry from Mapbox GL vector tiles with nothing embedded to extract.
                All 16 real trails built (2 non-linear POI-only entries -- Beginner/Kids Parcours and the
                Slopestyle-Area -- have zero length and are correctly excluded); iXS Downhill, Jump Line
                and Blackline 2.0 have real distances published but NO geometry in Trailforks' own data
                (gpx_file_url/geo.file_url null) and are left out rather than guessed.

Seven more trails added 2026-08-13, all sourced from Trailforks' own `/widgets/trail/?trailid=..` embed
(same technique as Green Hill above), found by the user directly rather than by search:
  - The Mother's own three previously-missing trails (iXS Downhill, Jump Line, Black Line 2.0) DO have
    geometry on Trailforks, unlike Green Hill's same-named gap above -- bikepark-winterberg.de's own API
    (`/get-route-details/<id>`) still has null for every geometry field for all three, re-checked and
    confirmed the same day, so Trailforks is a genuinely different, independent source here, not the
    same data surfacing through a second door.
  - A fourth Bikepark Winterberg trail neither this app nor bikepark-winterberg.de's own 18-trail list
    had: "Schwalbe Loose Lee (Pinball)" (Trailforks id 209457) -- same coordinate cluster as the other
    three (51.18-51.183N, 8.509-8.516E), so unambiguously the same park, just missing from the operator's
    own published trail list.
  - Three Trailpark Winterberg trails, also not on winterberg.de's own 16-trail list: Bremberg Blues,
    Biathlon Sprinter (near the biathlon stadium south of the main network -- see the "Start Loops"
    biathlete icon on the operator's own signboard map), Snowwhite and the red trail.
  - Trailforks' own per-trail page carries a distance/climb/descent stat line, like Green Hill's --
    checked against the actual point path (Black Line 2.0: 308 m stated, 308 m by the geometry itself)
    and found consistent, unlike bikepark-winterberg.de's own buggy aggregate block. Not used anyway,
    for a simpler reason: GPX-derived (this app's build_trail() default) is what the rest of the "tm_"
    group already uses, so all four Mother additions stay on the same footing as their 12 siblings
    rather than mixing two sourcing rules within one sub-region. GPX-derived is the only option anyway
    for the three Trailpark additions, which have no official numbers published anywhere.

## OSM pass, 2026-08-14

Per the user (after doing the same for Green Hill): checked both Winterberg sub-regions against OSM
too, cached raw ways+nodes in winterberg_osm_raw.json, processed results in winterberg_osm_final.json
(both next to this script, same reasoning as Green Hill's own cache files). OSM's own name for a
trail here is sometimes different from ours (dropped a version suffix, different capitalisation,
"-Uphill" left out) -- matched by geometry/endpoint proximity, not name alone, exactly the caution
the user asked for.

Switched (name matched with confidence -- length within ~5-20% and both endpoints within ~50 m of
the existing trail, or a clean two-connected-component join the same way Green Hill's Groomer/Save
Wimmons needed):
  - Trailpark Winterberg: Poppenberg Peak, Weltcup Flow, Uphill-Trail, Möppis Mover (reversed --
    forward endpoints didn't match, reversed did), Endless Trees, Sürenberg Sause, Poppies Track,
    Little Fluff (two components, B then A, joined across a 37 m real gap), Bremberg Blues, Biathlon
    Sprinter (two components, A then B, joined across a 3 m gap -- closes the gap the very first
    Trailforks-sourced build of this trail left open), Snowwhite and the red trail.
  - Bikepark Winterberg: North Shore, SRAM Flow Country.

Found on OSM but NOT switched -- length and/or endpoint mismatch too large to trust without a closer
look (flagged for follow-up rather than guessed):
  - Trailpark Winterberg: Cross Over (OSM "Cross Over" AND a separate "Cross Over Trail" both miss
    badly, neither is obviously the same line), Bremberg Flow (OSM ~18% short, its start 99 m from
    the known start -- may be missing a piece the same way Canadian Tuxedo's OSM way did in Green
    Hill), Shake the Lake (~24% short, one endpoint matches well), Popp Top Track (~36% LONGER, not
    just short -- may have picked up an unrelated stretch), Butzhols Bests (~23% short, one endpoint
    66 m off), Landal/Lolo Wahle Schanze/Lebe Wild Trail (no OSM match found under any obvious name).
  - Bikepark Winterberg: Kyrhill (OSM way is ~48% shorter), Schneewittchen Trail and Fairy Trail
    (OSM's own "Schneewittchen Trail / Fairy Trail" combined entry suggests the two share pavement,
    but each name's own components fall ~25% short with one endpoint 300-390 m off), Forrest Stump
    (~51% shorter), Shreddy Mörphy (OSM ~48% LONGER, one endpoint 294 m off -- likely a different
    or extended feature under the same name), Freeride (~11% short, moderate endpoint match, kept
    for now), Blackline 1.0 vs "Black Line" (OSM's unnumbered "Black Line" sits ~114-128 m off BOTH
    of Blackline 1.0's own endpoints -- may actually correspond to Blackline 2.0 instead, or be its
    own thing; not reassigned without checking), iXS Downhill (OSM ~19% longer than the Trailforks-
    sourced build, endpoints ~34-52 m off -- plausible but not confident enough yet). Jolli Jumper,
    Rocky Waldboa, Fly By, Jump Line: no OSM match found under any obvious name.

Schwalbe Loose Lee (Pinball) switched to OSM's "Pinball" way after all (2026-08-14) -- flagged above
as risky (78% longer, one endpoint 78 m off) purely on the numbers, but the user looked at it on the
map and it visibly reads as the better line; the length/endpoint mismatch was this trail genuinely
extending further than the Trailforks-widget-sourced build had it, not OSM tracing a different
feature. Same lesson as Canadian Tuxedo's missing piece in Green Hill: a length/endpoint mismatch by
itself is a reason to look closer, not a verdict -- worth checking the map before ruling out the rest
of this list on numbers alone.
  - Also spotted on OSM, unclaimed by anything built so far: "Woodpecker", "Herrloh Blitz", "Monkey
    Island" -- possibly more undiscovered Bikepark Winterberg trails, not investigated yet.

Difficulty mappings used, since no source here speaks the app's gruen/blau/rot/schwarz directly:
  - Trailpark Winterberg (winterberg.de) publishes a 3-tier LEICHT/MITTEL/SCHWER "Schwierigkeit" field
    (not a 4-tier ski-style scale) -- mapped the same way German hiking/tourism sites conventionally map
    that exact 3-word scale onto a 4-colour scheme: LEICHT->blau, MITTEL->rot, SCHWER->schwarz. No trail
    on this list used a 4th ("sehr leicht"/gruen) tier, so gruen is simply unused for this source -- not
    forced to fit.
  - "The Mother" (bikepark-winterberg.de) publishes its own 4-tier "Kinderleicht/Leicht/Mittel/Schwierig",
    which maps directly: Kinderleicht->gruen, Leicht->blau, Mittel->rot, Schwierig->schwarz.
  - Green Hill (Trailforks) uses Trailforks' own green/blue/red/black, which maps directly as it does for
    every other Trailforks-sourced region in this app.

Length/up/down sourcing:
  - Trailpark Winterberg: the operator's own published Länge/Aufstieg/Abstieg per trail (site's own
    numbers win over GPX-derived per project convention).
  - "The Mother": the site's own aggregate stats block has a visible unit bug (distance rendered "787,0 km"
    for a 2-minute trail that is obviously 787 m) and repeats the identical elevation figure (175 m) across
    several distinct trails sharing a lift zone -- both signs this in-progress site's own numbers aren't
    trustworthy yet. Real per-trail Strava-recorded GPX exists for 12 of its 18 trails, so length/up/down
    for those 12 are GPX-derived instead (this app's build_trail() default) rather than taken from the
    buggy aggregate block.
  - Green Hill: Trailforks' own per-trail page stats (Distance/Climb/Descent), which are independent of the
    embed widget bug categories above and read consistently trail to trail.
"""
import sys, json, os
sys.path.insert(0, r"D:\Trailmap\tools")
from trailmap_pipeline import build_trail, write_region, region_summary, parse_gpx, ElevationLookup

MAT = r"D:\Trailmap\Material\Sauerland-Upland"
OUT = r"D:\Trailmap\Trailmap App\regions\sauerland.json"
ELEV_CACHE = r"D:\Trailmap\Material\elevation_cache.json"

trails, geo, profs = [], {}, {}
elevation = ElevationLookup(ELEV_CACHE)
winterberg_osm = json.load(open(os.path.join(MAT, "winterberg_osm_final.json"), encoding="utf-8"))


def add_from_gpx(tid, name, region, diff, gpx_path, *, official=None, uphill=False, descend=True,
                  loop=False):
    text = open(gpx_path, encoding="utf-8").read()
    pts = parse_gpx(text)
    entry, coords, prof = build_trail(tid, name, region, diff, pts, official=official,
                                       uphill=uphill, descend=descend)
    if loop:
        entry["loop"] = True
    trails.append(entry); geo[tid] = coords; profs[tid] = prof


def add_from_points(tid, name, region, diff, pts, *, uphill=False, descend=True, loop=False):
    """Same as add_from_gpx, for points harvested inline (Trailforks' widget embed) rather than a
    downloaded .gpx file -- see build_greenhill.py for the original use of this pattern."""
    entry, coords, prof = build_trail(tid, name, region, diff, pts, uphill=uphill, descend=descend)
    if loop:
        entry["loop"] = True
    trails.append(entry); geo[tid] = coords; profs[tid] = prof


def add_osm(tid, name, region, diff, *, uphill=False, descend=True):
    """OSM-sourced (winterberg_osm_final.json, no elevation of its own -- ElevationLookup fills it
    in, same cache Green Hill and add_lifts.py already share). GPX-derived length/up/down, same
    reasoning as build_greenhill.py's own add_osm()."""
    pts = winterberg_osm[tid]
    entry, coords, prof = build_trail(tid, name, region, diff, pts, uphill=uphill, descend=descend,
                                       elevation=elevation)
    trails.append(entry); geo[tid] = coords; profs[tid] = prof


# ---------------------------------------------------------------------------------------------------
# Sub-region 1: Trailpark Winterberg (winterberg.de) -- 16 trails, operator numbers. Free, no lift --
# LEICHT -> blau, MITTEL -> rot, SCHWER -> schwarz (see module docstring). Split into its own
# sub-region 2026-08-13 (was lumped into one "winterberg" sub-region with The Mother below, per the
# user: two distinct networks on different hills of the same town deserve two sub-regions, matching
# how Willingen/Green Hill are already split out).
# ---------------------------------------------------------------------------------------------------
WB = os.path.join(MAT, "winterberg_gpx")
add_osm("wb_poppenberg_peak", "Poppenberg Peak", "trailpark_winterberg", "rot")
add_osm("wb_weltcup_flow", "Weltcup Flow", "trailpark_winterberg", "schwarz")
add_osm("wb_uphill_trail", "Uphill-Trail", "trailpark_winterberg", "blau", uphill=True, descend=False)
add_osm("wb_moeppis_mover", "Möppis Mover (Uphill)", "trailpark_winterberg", "rot", uphill=True, descend=False)
add_osm("wb_endless_trees", "Endless Trees", "trailpark_winterberg", "rot")
add_from_gpx("wb_popp_top_track", "Popp Top Track", "trailpark_winterberg", "rot",
             os.path.join(WB, "popp_top_track.gpx"), official=(0.2, 1, 41))
add_osm("wb_suerenberg_sause", "Sürenberg Sause", "trailpark_winterberg", "blau")
add_from_gpx("wb_butzhols_bests", "Butzhols Bests", "trailpark_winterberg", "schwarz",
             os.path.join(WB, "butzhols_bests.gpx"), official=(0.3, 7, 36))
add_osm("wb_little_fluff", "Little Fluff", "trailpark_winterberg", "rot")
add_from_gpx("wb_shake_the_lake", "Shake the Lake", "trailpark_winterberg", "schwarz",
             os.path.join(WB, "shake_the_lake.gpx"), official=(0.4, 0, 14))
add_osm("wb_poppies_track", "Poppies Track", "trailpark_winterberg", "rot")
add_from_gpx("wb_landal", "Landal", "trailpark_winterberg", "schwarz",
             os.path.join(WB, "landal.gpx"), official=(0.4, 0, 70))
add_from_gpx("wb_bremberg_flow", "Bremberg Flow", "trailpark_winterberg", "schwarz",
             os.path.join(WB, "bremberg_flow.gpx"), official=(0.4, 0, 51))
add_from_gpx("wb_lolo_wahle_schanze", "Lolo Wahle Schanze", "trailpark_winterberg", "schwarz",
             os.path.join(WB, "lolo_wahle_schanze.gpx"), official=(0.8, 1, 78))
add_from_gpx("wb_lebe_wild_trail", "Lebe Wild Trail", "trailpark_winterberg", "schwarz",
             os.path.join(WB, "lebe_wild_trail.gpx"), official=(0.4, 0, 72))
add_from_gpx("wb_cross_over", "Cross Over", "trailpark_winterberg", "blau",
             os.path.join(WB, "cross_over.gpx"), official=(0.5, 20, 14))

# Three more Trailpark Winterberg trails (2026-08-13), not on winterberg.de's own 16-trail list --
# found by the user on Trailforks, later found on OSM too (see module docstring) and switched.
add_osm("wb_bremberg_blues", "Bremberg Blues", "trailpark_winterberg", "gruen")
add_osm("wb_biathlon_sprinter", "Biathlon Sprinter", "trailpark_winterberg", "blau")
add_osm("wb_snowwhite_red_trail", "Snowwhite and the red trail", "trailpark_winterberg", "gruen")

# ---------------------------------------------------------------------------------------------------
# Sub-region 2: "The Mother" / Bikepark Winterberg (Erlebnisberg Kappe) -- 12 of 18 trails with real
# GPX. Kinderleicht->gruen, Leicht->blau, Mittel->rot, Schwierig->schwarz. GPX-derived len/up/down
# (site's own aggregate numbers have a visible unit bug, see docstring). Its own sub-region since
# 2026-08-13 (see note above) -- lift-served (Panorama-/Kappe-/Schneewittchen-Lift), unlike Trailpark
# Winterberg above.
# ---------------------------------------------------------------------------------------------------
TM = os.path.join(MAT, "themother_gpx")
add_from_gpx("tm_kyrhill", "Kyrhill", "bikepark_winterberg", "blau", os.path.join(TM, "kyrhill.gpx"))
add_from_gpx("tm_jolli_jumper", "Jolli Jumper", "bikepark_winterberg", "rot", os.path.join(TM, "jolli_jumper.gpx"))
add_osm("tm_north_shore", "North Shore", "bikepark_winterberg", "rot")
add_from_gpx("tm_freeride", "Freeride", "bikepark_winterberg", "rot", os.path.join(TM, "freeride.gpx"))
add_from_gpx("tm_blackline_1", "Blackline 1.0", "bikepark_winterberg", "schwarz", os.path.join(TM, "blackline_1.gpx"))
add_osm("tm_sram_flow_country", "SRAM Flow Country", "bikepark_winterberg", "blau")
add_from_gpx("tm_schneewittchen_trail", "Schneewittchen-Trail", "bikepark_winterberg", "gruen",
             os.path.join(TM, "schneewittchen_trail.gpx"))
add_from_gpx("tm_fairy_trail", "Fairy-Trail", "bikepark_winterberg", "gruen", os.path.join(TM, "fairy_trail.gpx"))
add_from_gpx("tm_forrest_stump", "Forrest Stump", "bikepark_winterberg", "rot", os.path.join(TM, "forrest_stump.gpx"))
add_from_gpx("tm_rocky_waldboa", "Rocky Waldboa", "bikepark_winterberg", "rot", os.path.join(TM, "rocky_waldboa.gpx"))
add_from_gpx("tm_shreddy_moerphy", "Shreddy Mörphy", "bikepark_winterberg", "rot",
             os.path.join(TM, "shreddy_moerphy.gpx"))
add_from_gpx("tm_fly_by", "Fly By", "bikepark_winterberg", "blau", os.path.join(TM, "fly_by.gpx"))

# Four more Bikepark Winterberg trails (2026-08-13), found by the user on Trailforks -- the three
# previously-missing ones (bikepark-winterberg.de's own API still answers null geometry for all
# three, re-checked the same day) plus one the operator's own 18-trail list never had at all.
# GPX-derived, same as the 12 trails above (see module docstring for why).
add_from_points("tm_black_line_2", "Black Line 2.0", "bikepark_winterberg", "schwarz", [
    [51.18188, 8.51183, 733], [51.1819, 8.51188, 733], [51.18188, 8.51197, 723], [51.18179, 8.51208, 726],
    [51.18172, 8.5122, 726], [51.18166, 8.51234, 726], [51.18166, 8.5124, 726], [51.18175, 8.51245, 726],
    [51.18181, 8.51249, 723], [51.1819, 8.51247, 723], [51.18197, 8.51248, 723], [51.18199, 8.51253, 704],
    [51.18194, 8.51262, 704], [51.1818, 8.51278, 712], [51.18175, 8.51286, 712], [51.1817, 8.51289, 712],
    [51.18165, 8.51294, 712], [51.18163, 8.51299, 712], [51.18158, 8.51309, 696], [51.18146, 8.51317, 700],
    [51.18142, 8.51323, 700], [51.18145, 8.51328, 700], [51.1815, 8.51331, 700], [51.18155, 8.51332, 696],
    [51.18161, 8.51334, 696], [51.1817, 8.51337, 696], [51.18182, 8.51334, 683], [51.18199, 8.51325, 683],
    [51.18215, 8.51336, 669], [51.1822, 8.51337, 669], [51.18224, 8.51342, 669], [51.18224, 8.51348, 669],
    [51.18219, 8.51359, 669], [51.18217, 8.51382, 651], [51.18213, 8.51393, 651],
])
add_from_points("tm_jump_line", "Jump Line", "bikepark_winterberg", "schwarz", [
    [51.18187, 8.50747, 772], [51.1819, 8.5076, 772], [51.18196, 8.50755, 772], [51.18202, 8.50749, 772],
    [51.18208, 8.50738, 772], [51.18212, 8.50727, 769], [51.18217, 8.50714, 769], [51.18221, 8.50703, 769],
    [51.18223, 8.50697, 769], [51.18226, 8.50687, 769], [51.1823, 8.50681, 769], [51.18235, 8.5068, 769],
    [51.18239, 8.50684, 764], [51.1824, 8.50693, 764], [51.18237, 8.50705, 767], [51.18233, 8.50718, 769],
    [51.18228, 8.50728, 769], [51.18225, 8.50739, 769], [51.18223, 8.50748, 769], [51.18222, 8.50755, 769],
    [51.18225, 8.50759, 769], [51.18229, 8.50756, 769], [51.18234, 8.50748, 769], [51.1824, 8.50741, 767],
    [51.18245, 8.50732, 767], [51.1825, 8.50722, 767], [51.18254, 8.50709, 767], [51.18255, 8.507, 767],
    [51.18259, 8.50695, 767], [51.18263, 8.50697, 767], [51.18269, 8.50698, 760], [51.18273, 8.50701, 760],
    [51.1828, 8.50705, 760], [51.18286, 8.50712, 760], [51.1829, 8.50719, 760], [51.18292, 8.50727, 752],
    [51.18289, 8.50733, 760], [51.18286, 8.50739, 760], [51.18285, 8.50746, 760], [51.18288, 8.50752, 758],
    [51.18293, 8.50753, 747], [51.18298, 8.50748, 752], [51.18303, 8.50733, 752], [51.18311, 8.50708, 752],
    [51.18317, 8.50686, 754], [51.18323, 8.50673, 750], [51.18327, 8.50665, 750], [51.18332, 8.50664, 750],
    [51.18336, 8.50666, 750], [51.18338, 8.50675, 750], [51.18337, 8.50682, 750], [51.18333, 8.50685, 750],
    [51.1833, 8.50693, 750], [51.1833, 8.50703, 744], [51.18335, 8.50701, 744], [51.18344, 8.50697, 744],
    [51.18352, 8.50688, 745], [51.18364, 8.50679, 745], [51.18373, 8.50673, 745], [51.18382, 8.50669, 740],
    [51.18391, 8.50664, 740], [51.18395, 8.50662, 740], [51.18402, 8.50663, 740], [51.18406, 8.50667, 737],
    [51.18408, 8.50675, 737], [51.18406, 8.50681, 737], [51.18404, 8.5069, 737], [51.18404, 8.50696, 735],
    [51.18404, 8.50702, 735], [51.18408, 8.50708, 735], [51.18414, 8.50705, 735], [51.18419, 8.507, 735],
    [51.18423, 8.50694, 737], [51.18427, 8.50689, 737], [51.1843, 8.50691, 737], [51.18433, 8.50697, 736],
    [51.18432, 8.50707, 736], [51.18428, 8.50714, 735], [51.18423, 8.5072, 735], [51.18419, 8.50726, 735],
    [51.18413, 8.50733, 735], [51.18408, 8.50735, 735], [51.18402, 8.50737, 735], [51.18398, 8.5074, 735],
    [51.18399, 8.50749, 735], [51.18404, 8.50755, 729], [51.18413, 8.50753, 729],
])
add_from_points("tm_ixs_downhill", "iXS Downhill", "bikepark_winterberg", "schwarz", [
    [51.18095, 8.51074, 757], [51.18088, 8.51086, 749], [51.18091, 8.51111, 749], [51.18096, 8.51126, 749],
    [51.18101, 8.51139, 738], [51.18106, 8.51144, 738], [51.18111, 8.51149, 738], [51.18112, 8.51153, 738],
    [51.18115, 8.51172, 738], [51.18115, 8.51183, 738], [51.18113, 8.51192, 738], [51.18105, 8.51203, 725],
    [51.18093, 8.5121, 722], [51.1808, 8.51213, 722], [51.1806, 8.51212, 720], [51.18054, 8.51216, 720],
    [51.18044, 8.51231, 720], [51.18038, 8.51248, 717], [51.18039, 8.51255, 705], [51.1805, 8.51278, 708],
    [51.18051, 8.51301, 708], [51.18054, 8.51314, 703], [51.18054, 8.51333, 703], [51.18048, 8.51363, 698],
    [51.18049, 8.51371, 698], [51.18052, 8.51376, 698], [51.1806, 8.51381, 698], [51.18065, 8.51382, 698],
    [51.18075, 8.51379, 693], [51.18082, 8.51382, 693], [51.18086, 8.51388, 693], [51.18089, 8.51405, 693],
    [51.18086, 8.51428, 680], [51.18079, 8.51457, 680], [51.1807, 8.51507, 674], [51.18058, 8.51536, 676],
    [51.18059, 8.51552, 676], [51.18064, 8.51564, 676], [51.18075, 8.51571, 672], [51.18076, 8.51594, 664],
    [51.1808, 8.51624, 664], [51.18083, 8.51626, 664], [51.18085, 8.51625, 664], [51.18095, 8.51609, 664],
    [51.18098, 8.51609, 654], [51.18101, 8.51611, 654], [51.18105, 8.51629, 654], [51.18107, 8.5163, 654],
    [51.18112, 8.5163, 654], [51.18121, 8.51625, 654], [51.18129, 8.51627, 638], [51.18134, 8.51621, 638],
    [51.18146, 8.51591, 638], [51.18155, 8.5156, 636], [51.1816, 8.51552, 636], [51.1817, 8.51548, 636],
    [51.18175, 8.51548, 636], [51.18185, 8.51554, 626], [51.18206, 8.51552, 626], [51.18222, 8.51553, 616],
    [51.18247, 8.51551, 609],
])
add_osm("tm_schwalbe_loose_lee", "Schwalbe Loose Lee (Pinball)", "bikepark_winterberg", "rot")

# ---------------------------------------------------------------------------------------------------
# Willingen sub-region: Green Trails Willingen's two long touring loops. Kept separate from the MTB
# Zone Willingen sub-region below per the user (2026-08-14) -- two distinct networks sharing a town,
# same pattern as the two Winterberg sub-regions. Both marked loop=True per the user (2026-08-14) --
# no TRAIL_SEGMENTS breakdown (neither is composed of this app's own named component trails), so
# each renders the same way the Odenwald cluster's own unsegmented loops already do: the whole route
# dashed grey, in the Touren list instead of Trails.
# ---------------------------------------------------------------------------------------------------
WG = os.path.join(MAT, "willingen_gpx")
add_from_gpx("wi_gipfel_runde_hoppecke", "Green Trails Willingen Gipfel-Runde Hoppecke (GRU)",
             "willingen", "blau", os.path.join(WG, "gipfel_runde_hoppecke.gpx"),
             official=(12.91, 314, 282), loop=True)

# Ruthenaar-Double: the recorded GPX opens with an out-and-back into town (points 1-37 of 219,
# 714 m) before the real loop starts -- found by the user riding it, confirmed in the raw track
# itself (point 37 lands back on point 1, and points 18-20 sit on the exact same coordinate, the
# turnaround). Trimmed here (point 0 + points 38 onward) rather than fixed at the source, since the
# spur is a real recorded detour, not a mapping error. The official number (6.11 km) turns out to
# already match the UNTRIMMED recording almost exactly (6110 m) -- i.e. it was seemingly derived
# from this same recording including the detour, not an independent measurement -- so official is
# dropped here in favour of GPX-derived, which now describes the trimmed line actually drawn.
_rud_raw = parse_gpx(open(os.path.join(WG, "ruthenaar_double.gpx"), encoding="utf-8").read())
add_from_points("wi_ruthenaar_double", "Green Trails Willingen Ruthenaar-Double (RUD)",
                 "willingen", "blau", [_rud_raw[0]] + _rud_raw[38:], loop=True)

# ---------------------------------------------------------------------------------------------------
# MTB Zone Willingen sub-region (2026-08-14) -- the bikepark this app's own docs previously recorded
# as "no GPX source anywhere". The user found it on Trailforks (region "willingen-2012") via the
# same /widgets/trail/ embed technique used for Green Hill/Winterberg -- both trail names AND
# difficulties, per the user, are sourced from there. Points already carry real elevation from
# Trailforks' own data, same as every other Trailforks-sourced trail in this app -- no
# ElevationLookup needed here.
#
# Difficulty conflict, resolved by the user: mtbzone-bikepark.com's own trail pages rate "Enduro"
# and "Downhill" both schwer/schwarz; Trailforks rates "Enduro-Line"/"Willingen Downhill" as
# Difficult/Red. The user chose the operator's own rating (schwarz) for both.
#
# Length/up/down: the operator's own published Länge/Höhendifferenz where it exists and reads as a
# real, trail-specific measurement (Freeride: 1590 m/190 m; Willingen Downhill: 1600 m/250 m).
# NOT used for Flowtrail/Flow Country Trail/Enduro-Line/Pump Track: the operator's own page states
# "2900 Meter" for BOTH Flow Trail and Flow Country Trail -- an identical figure for two different
# trails reads as a copied placeholder rather than two independent measurements (their own drawn
# geometry differs from that number by ~20% either way and from each other by 2 m), so GPX-derived
# is trusted more here. Freeride Lower/Enduro-Line Lower have no operator page at all -- Trailforks'
# own stat line for both matches their own geometry's length exactly, so used as official.
WI2 = json.load(open(os.path.join(MAT, "willingen_mtbzone_pts.json"), encoding="utf-8"))
WI2_OSM = json.load(open(os.path.join(MAT, "willingen_osm_final2.json"), encoding="utf-8"))
WI2_OSM["willingen_downhill"] = json.load(open(os.path.join(MAT, "willingen_downhill_osm.json"),
                                                encoding="utf-8"))


def add_wi2(tid, name, diff, key, *, official=None):
    entry, coords, prof = build_trail(tid, name, "mtbzone_willingen", diff, WI2[key], official=official)
    trails.append(entry); geo[tid] = coords; profs[tid] = prof


def add_wi2_osm(tid, name, diff, key, *, official=None):
    """OSM-sourced (willingen_osm_final2.json) -- plain Overpass nodes carry no elevation at all
    (unlike the Trailforks-widget-sourced ones above), so ElevationLookup fills it in."""
    entry, coords, prof = build_trail(tid, name, "mtbzone_willingen", diff, WI2_OSM[key],
                                       elevation=elevation, official=official)
    trails.append(entry); geo[tid] = coords; profs[tid] = prof


# Freeride/Flowtrail/Flow Country Trail switched to OSM (2026-08-14, per the user: "sehen etwas
# genauer aus"). This exposed a braided network the single Trailforks-widget lines didn't capture:
# ~108 m into the ride, "Freeride" forks -- the OSM way used here (id 83468327) is the LEFT/main
# line; a second, separately-tagged parallel line (mtb:type=enduro, same name "Freeride Trail" in
# OSM) runs to its RIGHT, crosses a bridge (one of its own 3 fragments carries `bridge=yes` --
# confirms the user's own description exactly), then swaps to the LEFT of the main line and rejoins
# it ~7 m away, right where the user said it meets the Forstweg. Built as a new trail, "Old
# Freeride" (the user's own name for it; OSM has no distinct name, same "Freeride Trail" tag with a
# different mtb:type).
#
# Lower down, Freeride/Flow Trail/Flow Country Trail's own OSM lines all converge onto ONE shared
# final stretch (OSM's own combined-name way, "Flow Trail / Flow Country Trail") before forking
# again into Freeride Lower/Enduro-Line Lower -- confirmed node-exact: Freeride Lower's own start
# point sits 1 m from a point partway along that combined way, Enduro-Line Lower's 3 m from another
# point on it. Per the user, the shared stretch AND everything after (i.e. all the way past where
# Freeride Lower/Enduro-Line Lower branch off, to the combined way's own end) counts as Flow Country
# Trail -- not Flow Trail, not Freeride, not Old Freeride, even though all of them physically feed
# into it. Flow Trail's own OSM line therefore stops at the convergence point, same as
# Freeride/Old Freeride, so none of the four overlaps another's claimed geometry.
add_wi2_osm("wiz_freeride", "Freeride", "rot", "freeride")
add_wi2_osm("wiz_old_freeride", "Old Freeride", "rot", "old_freeride")
add_wi2_osm("wiz_flowtrail", "Flowtrail", "blau", "flowtrail")
add_wi2_osm("wiz_flow_country", "Flow Country Trail", "blau", "flow_country")

# Enduro-Line: last ~300 m corrected per the user ("das Ende geht auf OSM nochmal links ab") -- OSM
# tags that final stretch as its own way (mtb:type=enduro), forking left off what this app's
# original Trailforks-widget line drew as a straight continuation into the Freeride/Flow
# Trail/Flow Country convergence point. Found node-exact: the Trailforks line's own point 69 (of
# 88) sits 12 m from that OSM way's start. Spliced in points[:70] + the OSM way's own points.
add_wi2("wiz_enduro_line", "Enduro-Line", "schwarz", "enduro_line_fixed")

# Willingen Downhill: switched to OSM, which calls it "Weltcup-Downhill-Strecke" (the user's own
# correction) -- three ways chained, ending 1469 m in, closer to the operator's own 1600 m than the
# original Trailforks-widget line's 1285 m was.
add_wi2_osm("wiz_downhill", "Willingen Downhill", "schwarz", "willingen_downhill")
add_wi2("wiz_pump_track", "Pump Track", "blau", "pump_track")
add_wi2("wiz_freeride_lower", "Freeride Lower", "rot", "freeride_lower", official=(0.354, 1, 30))
add_wi2("wiz_enduro_line_lower", "Enduro-Line Lower", "schwarz", "enduro_line_lower", official=(0.117, 0, 13))

# Four Cross (2026-08-14, corrected 2026-08-14): the way first used here (169824662) was wrong -- it
# is the outer boundary polygon of the "Mountainbike-Fun-Parcours" sports_centre area, not a trail at
# all. The user pointed out the actual line snakes alongside the Weltcup-Downhill-Strecke to the same
# endpoint. Found it node-exact: way 336853512 (OSM name "Jumptrack", mtb:scale=1) shares its end node
# (2883016585) exactly with the Downhill way's own end node -- confirming it's the parallel line the
# user described, not the area boundary. Official numbers from the operator's own 4X page (500 m,
# 60 m) kept, close enough to this way's own 388 m. Difficulty corrected to rot per the user (not
# schwarz -- the operator's "mittel bis schwer" wording was overselling it, not underselling).
add_wi2_osm("wiz_fourcross", "Four Cross", "rot", "fourcross", official=(0.5, 0, 60))

# ---------------------------------------------------------------------------------------------------
# Four more Willingen (Ettelsberg) downhill trails (2026-08-14), found by the user on Trailforks --
# kept in the `willingen` sub-region (Green Trails' own touring loops), not `mtbzone_willingen`,
# per the user. Trailforks' own difficulty rating used directly (no operator-page conflict here,
# unlike MTB Zone Willingen's Enduro-Line/Downhill). GPX-derived length/up/down -- no official
# numbers published for any of these.
# ---------------------------------------------------------------------------------------------------
WI_DH = json.load(open(os.path.join(MAT, "willingen_greentrails_dh_pts.json"), encoding="utf-8"))
add_from_points("wi_langenberg_dh", "Langenberg DH", "willingen", "rot", WI_DH["langenberg"])
add_from_points("wi_ritzhagen_dh", "Ritzhagen DH", "willingen", "rot", WI_DH["ritzhagen"])
add_from_points("wi_dreiskopf_downhill", "Dreiskopf Downhill", "willingen", "blau", WI_DH["dreiskopf"])
add_from_points("wi_muehlenkopf_dh", "Mühlenkopf DH", "willingen", "rot", WI_DH["muehlenkopf"])

# ---------------------------------------------------------------------------------------------------
# Green Hill sub-region: import the already-built 16 trails from build_greenhill.py's output.
# ---------------------------------------------------------------------------------------------------
gh = json.load(open(os.path.join(MAT, "greenhill_partial.json"), encoding="utf-8"))
for e in gh["lineTrails"]:
    e["region"] = "greenhill"
    trails.append(e)
geo.update(gh["trailGeo"])
profs.update(gh["elevationProfiles"])

# ---------------------------------------------------------------------------------------------------
# Places: one reference point per sub-region (OSM node[place], per docs/adding-a-region.md).
# ---------------------------------------------------------------------------------------------------
places = [
    {"name": "Winterberg", "lat": 51.1933391, "lng": 8.5334064},
    {"name": "Willingen (Upland)", "lat": 51.2953614, "lng": 8.609738},
    {"name": "Gellinghausen", "lat": 51.2449234, "lng": 8.3593038},
]

data = write_region(OUT, trails, geo, profs, places=places)
print(region_summary(data))
