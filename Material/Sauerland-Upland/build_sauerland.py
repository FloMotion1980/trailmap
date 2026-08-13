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
  willingen   - Willingen/Ettelsberg. MTB Zone Bikepark Willingen's 12 named descents have NO GPX
                source (confirmed: mtbzone-bikepark.com page has names/difficulty only) and are left
                OUT rather than fabricated. Willingen Greentrails' two long touring loops (Gipfel-Runde
                Hoppecke, Ruthenaar-Double) DO have direct GPX via willingen.de's destination-data-proxy
                endpoint and are the only Willingen trails built.
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

trails, geo, profs = [], {}, {}


def add_from_gpx(tid, name, region, diff, gpx_path, *, official=None, uphill=False, descend=True):
    text = open(gpx_path, encoding="utf-8").read()
    pts = parse_gpx(text)
    entry, coords, prof = build_trail(tid, name, region, diff, pts, official=official,
                                       uphill=uphill, descend=descend)
    trails.append(entry); geo[tid] = coords; profs[tid] = prof


def add_from_points(tid, name, region, diff, pts, *, uphill=False, descend=True):
    """Same as add_from_gpx, for points harvested inline (Trailforks' widget embed) rather than a
    downloaded .gpx file -- see build_greenhill.py for the original use of this pattern."""
    entry, coords, prof = build_trail(tid, name, region, diff, pts, uphill=uphill, descend=descend)
    trails.append(entry); geo[tid] = coords; profs[tid] = prof


# ---------------------------------------------------------------------------------------------------
# Sub-region 1: Trailpark Winterberg (winterberg.de) -- 16 trails, operator numbers. Free, no lift --
# LEICHT -> blau, MITTEL -> rot, SCHWER -> schwarz (see module docstring). Split into its own
# sub-region 2026-08-13 (was lumped into one "winterberg" sub-region with The Mother below, per the
# user: two distinct networks on different hills of the same town deserve two sub-regions, matching
# how Willingen/Green Hill are already split out).
# ---------------------------------------------------------------------------------------------------
WB = os.path.join(MAT, "winterberg_gpx")
add_from_gpx("wb_poppenberg_peak", "Poppenberg Peak", "trailpark_winterberg", "rot",
             os.path.join(WB, "poppenberg_peak.gpx"), official=(0.3, 0, 16))
add_from_gpx("wb_weltcup_flow", "Weltcup Flow", "trailpark_winterberg", "schwarz",
             os.path.join(WB, "weltcup_flow.gpx"), official=(0.6, 0, 87))
add_from_gpx("wb_uphill_trail", "Uphill-Trail", "trailpark_winterberg", "blau",
             os.path.join(WB, "uphill_trail.gpx"), official=(1.2, 51, 5), uphill=True, descend=False)
add_from_gpx("wb_moeppis_mover", "Möppis Mover (Uphill)", "trailpark_winterberg", "rot",
             os.path.join(WB, "moeppis_mover.gpx"), official=(0.5, 56, 0), uphill=True, descend=False)
add_from_gpx("wb_endless_trees", "Endless Trees", "trailpark_winterberg", "rot",
             os.path.join(WB, "endless_trees.gpx"), official=(0.8, 0, 71))
add_from_gpx("wb_popp_top_track", "Popp Top Track", "trailpark_winterberg", "rot",
             os.path.join(WB, "popp_top_track.gpx"), official=(0.2, 1, 41))
add_from_gpx("wb_suerenberg_sause", "Sürenberg Sause", "trailpark_winterberg", "blau",
             os.path.join(WB, "suerenberg_sause.gpx"), official=(0.4, 0, 10))
add_from_gpx("wb_butzhols_bests", "Butzhols Bests", "trailpark_winterberg", "schwarz",
             os.path.join(WB, "butzhols_bests.gpx"), official=(0.3, 7, 36))
add_from_gpx("wb_little_fluff", "Little Fluff", "trailpark_winterberg", "rot",
             os.path.join(WB, "little_fluff.gpx"), official=(0.5, 0, 37))
add_from_gpx("wb_shake_the_lake", "Shake the Lake", "trailpark_winterberg", "schwarz",
             os.path.join(WB, "shake_the_lake.gpx"), official=(0.4, 0, 14))
add_from_gpx("wb_poppies_track", "Poppies Track", "trailpark_winterberg", "rot",
             os.path.join(WB, "poppies_track.gpx"), official=(0.4, 1, 31))
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
# found by the user on Trailforks. GPX-derived (no official numbers exist for these anywhere).
add_from_points("wb_bremberg_blues", "Bremberg Blues", "trailpark_winterberg", "gruen", [
    [51.18842, 8.49846, 782], [51.18844, 8.49851, 782], [51.18846, 8.49853, 782], [51.18848, 8.49856, 783],
    [51.18849, 8.49858, 783], [51.18851, 8.49863, 778], [51.18855, 8.49867, 778], [51.18867, 8.49876, 778],
    [51.18877, 8.49892, 782], [51.18881, 8.49907, 782], [51.18884, 8.49919, 779], [51.18886, 8.4993, 779],
    [51.18891, 8.4994, 779], [51.18899, 8.49953, 779], [51.18907, 8.49963, 781], [51.18912, 8.49974, 777],
    [51.18917, 8.49987, 777], [51.18919, 8.50001, 777], [51.18922, 8.50017, 777], [51.18928, 8.50027, 777],
    [51.18936, 8.5004, 776], [51.1893, 8.50043, 774], [51.18918, 8.50039, 774], [51.18907, 8.50035, 774],
    [51.18902, 8.50037, 774], [51.18894, 8.50042, 774], [51.18892, 8.50064, 774], [51.18893, 8.50084, 772],
    [51.189, 8.50109, 772], [51.18907, 8.50135, 773], [51.18912, 8.50149, 771], [51.18918, 8.50159, 771],
    [51.18922, 8.50167, 771], [51.18928, 8.50184, 771], [51.1893, 8.50199, 768], [51.18927, 8.50218, 768],
    [51.18921, 8.50223, 768], [51.18913, 8.50223, 768], [51.18902, 8.5022, 765], [51.18886, 8.50227, 765],
    [51.18887, 8.50251, 764], [51.1889, 8.50261, 764], [51.18894, 8.50276, 764], [51.18895, 8.50284, 764],
    [51.18889, 8.50286, 764], [51.1888, 8.50287, 764], [51.18874, 8.50293, 763], [51.18862, 8.50302, 763],
    [51.18857, 8.50312, 759], [51.18851, 8.50321, 759], [51.18849, 8.50331, 759],
])
add_from_points("wb_biathlon_sprinter", "Biathlon Sprinter", "trailpark_winterberg", "blau", [
    [51.19019, 8.49667, 804.5], [51.19009, 8.49666, 805], [51.18997, 8.49668, 804.8], [51.18985, 8.49666, 804.1],
    [51.18978, 8.49668, 803.3], [51.18974, 8.49667, 802.6], [51.18961, 8.49676, 800.5], [51.18948, 8.4968, 799.2],
    [51.18943, 8.49685, 799.2], [51.18936, 8.49697, 799.1], [51.18937, 8.49729, 800.9], [51.18943, 8.49745, 802.7],
    [51.18951, 8.49763, 803.7], [51.18965, 8.49785, 803.9], [51.1897, 8.49786, 804.2], [51.18966, 8.49789, 803.5],
    [51.1896, 8.49787, 803], [51.18958, 8.49782, 803.2], [51.18953, 8.49776, 802.8], [51.18948, 8.49776, 802.1],
    [51.18946, 8.49783, 800.9], [51.18948, 8.49798, 800.6], [51.18957, 8.49808, 801.1], [51.18961, 8.49817, 800.9],
    [51.18972, 8.49829, 801.4], [51.18955, 8.49831, 798.8], [51.18952, 8.49842, 797.2], [51.18953, 8.49854, 796.4],
    [51.18962, 8.49886, 795.2], [51.18966, 8.49895, 794.8], [51.1896, 8.49901, 794.8], [51.18941, 8.499, 792.4],
    [51.18924, 8.49907, 789.6], [51.18919, 8.49905, 789.5], [51.18913, 8.49905, 789.2], [51.18908, 8.4991, 788.4],
    [51.18906, 8.49914, 787.7], [51.18905, 8.49921, 786.9], [51.1891, 8.49939, 785.6], [51.18915, 8.49947, 785.4],
    [51.18933, 8.49966, 785.5], [51.18943, 8.4997, 786.2], [51.18957, 8.49981, 786.5], [51.18969, 8.49997, 785.8],
    [51.18972, 8.50009, 784.9], [51.18972, 8.5003, 782.7], [51.18969, 8.50035, 781.7], [51.1896, 8.50047, 778.7],
    [51.18952, 8.5007, 771.5], [51.1895, 8.5008, 771.1], [51.18948, 8.50111, 770.1], [51.18956, 8.50149, 769],
    [51.18961, 8.50162, 768.7], [51.18962, 8.50169, 768.2], [51.1896, 8.50192, 766.2], [51.18962, 8.50199, 765.9],
    [51.1897, 8.50216, 765.2], [51.18986, 8.50232, 765.2], [51.18992, 8.50235, 765.4], [51.19005, 8.50251, 765.1],
    [51.19006, 8.50256, 764.8], [51.19, 8.50264, 763.8], [51.18997, 8.50275, 762.8], [51.18991, 8.5028, 762],
    [51.18986, 8.50288, 761.1], [51.18982, 8.5029, 760.7], [51.18979, 8.50288, 760.7], [51.18973, 8.50288, 760.3],
    [51.1897, 8.50294, 759.8], [51.18966, 8.50295, 759.4], [51.18966, 8.50299, 759.2], [51.18963, 8.50305, 758.2],
    [51.18958, 8.50307, 757], [51.18953, 8.50307, 756],
])
add_from_points("wb_snowwhite_red_trail", "Snowwhite and the red trail", "trailpark_winterberg", "gruen", [
    [51.18849, 8.50331, 759], [51.1885, 8.50332, 759], [51.18852, 8.50339, 759], [51.18854, 8.50348, 759],
    [51.18856, 8.50357, 759], [51.18859, 8.50367, 757], [51.18862, 8.50377, 757], [51.18865, 8.50384, 757],
    [51.18868, 8.50391, 757], [51.18871, 8.50398, 757], [51.18873, 8.50405, 757], [51.18873, 8.50413, 757],
    [51.18872, 8.50419, 752], [51.1887, 8.50424, 752], [51.18868, 8.50429, 752], [51.18867, 8.50434, 752],
    [51.18866, 8.5044, 752], [51.18864, 8.50447, 752], [51.18863, 8.50455, 752], [51.18863, 8.50462, 752],
    [51.18864, 8.50469, 752], [51.18866, 8.50474, 747], [51.18868, 8.50478, 747], [51.1887, 8.50485, 747],
    [51.18871, 8.5049, 747], [51.18872, 8.50495, 747], [51.18872, 8.505, 747], [51.18872, 8.50507, 747],
    [51.18871, 8.50513, 747], [51.18871, 8.5052, 747], [51.18871, 8.50528, 745], [51.18872, 8.50533, 745],
    [51.18873, 8.50537, 745], [51.18875, 8.50543, 747], [51.18876, 8.50547, 747], [51.18877, 8.50551, 747],
    [51.18878, 8.50554, 747], [51.18878, 8.50558, 747], [51.18877, 8.50564, 747], [51.18875, 8.50569, 747],
    [51.18872, 8.50577, 745],
])

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
add_from_gpx("tm_north_shore", "North Shore", "bikepark_winterberg", "rot", os.path.join(TM, "north_shore.gpx"))
add_from_gpx("tm_freeride", "Freeride", "bikepark_winterberg", "rot", os.path.join(TM, "freeride.gpx"))
add_from_gpx("tm_blackline_1", "Blackline 1.0", "bikepark_winterberg", "schwarz", os.path.join(TM, "blackline_1.gpx"))
add_from_gpx("tm_sram_flow_country", "SRAM Flow Country", "bikepark_winterberg", "blau",
             os.path.join(TM, "sram_flow_country.gpx"))
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
add_from_points("tm_schwalbe_loose_lee", "Schwalbe Loose Lee (Pinball)", "bikepark_winterberg", "rot", [
    [51.18147, 8.50974, 760], [51.18152, 8.50975, 760], [51.18155, 8.5098, 758], [51.18154, 8.50987, 758],
    [51.18154, 8.50994, 758], [51.1816, 8.50998, 758], [51.18167, 8.51, 758], [51.18176, 8.50993, 758],
    [51.18184, 8.5099, 752], [51.18193, 8.50981, 752], [51.18197, 8.50974, 752], [51.18229, 8.50944, 756],
    [51.18232, 8.50938, 756], [51.18235, 8.50941, 756], [51.18238, 8.50948, 750], [51.18236, 8.50953, 756],
    [51.18228, 8.50962, 756], [51.18222, 8.50972, 756], [51.18219, 8.50988, 747], [51.18222, 8.5099, 747],
    [51.18224, 8.50989, 747], [51.18232, 8.50967, 756], [51.18241, 8.50969, 750], [51.18243, 8.50982, 742],
    [51.18242, 8.50986, 742], [51.18236, 8.50996, 747], [51.18227, 8.51002, 747], [51.18225, 8.51007, 747],
    [51.18227, 8.51013, 747], [51.18232, 8.51013, 747], [51.18236, 8.5101, 747], [51.18242, 8.51, 742],
    [51.18246, 8.51, 742], [51.18248, 8.51003, 742], [51.18249, 8.51009, 742], [51.18243, 8.51019, 742],
    [51.18239, 8.51022, 742], [51.18239, 8.51028, 732], [51.1824, 8.51031, 732], [51.18243, 8.51033, 732],
    [51.18257, 8.51033, 732], [51.18256, 8.51041, 732], [51.18242, 8.5105, 732], [51.18241, 8.51055, 732],
    [51.18242, 8.51063, 732], [51.18251, 8.51063, 732], [51.18264, 8.5105, 723], [51.18268, 8.51055, 723],
    [51.18265, 8.51065, 723], [51.18262, 8.51065, 732], [51.18253, 8.51076, 732], [51.18257, 8.51082, 732],
    [51.18264, 8.51083, 723], [51.18266, 8.51089, 708], [51.18265, 8.51093, 708], [51.18263, 8.51092, 720],
    [51.18261, 8.51096, 720], [51.18259, 8.51104, 720], [51.1826, 8.51112, 720], [51.18268, 8.51112, 708],
    [51.18271, 8.51122, 708], [51.18263, 8.51139, 705], [51.18263, 8.51145, 705], [51.18264, 8.51148, 696],
    [51.18272, 8.51154, 696], [51.18281, 8.51152, 696], [51.18288, 8.51165, 696], [51.18278, 8.51182, 696],
    [51.18279, 8.51195, 685], [51.18281, 8.51199, 685], [51.18284, 8.51199, 685], [51.18287, 8.51193, 696],
    [51.18294, 8.51191, 688], [51.18298, 8.51193, 688], [51.18299, 8.51198, 678], [51.1829, 8.51242, 685],
    [51.18291, 8.51253, 672], [51.18293, 8.51254, 667], [51.18306, 8.51251, 667], [51.18315, 8.51246, 678],
    [51.18316, 8.51249, 678], [51.18311, 8.51268, 667], [51.18295, 8.51309, 655], [51.18295, 8.51317, 655],
    [51.18297, 8.51321, 655], [51.1831, 8.51319, 655], [51.18318, 8.51318, 655], [51.18325, 8.51316, 648],
    [51.18328, 8.51325, 648], [51.18323, 8.51338, 648], [51.18319, 8.51341, 655], [51.18312, 8.51347, 655],
    [51.18309, 8.51353, 655], [51.18311, 8.51358, 655], [51.18314, 8.51361, 655], [51.18323, 8.51361, 648],
    [51.18329, 8.51363, 632], [51.18323, 8.51383, 632], [51.18316, 8.51403, 637], [51.18316, 8.51409, 637],
    [51.1832, 8.5141, 632], [51.18326, 8.51413, 632], [51.18327, 8.5142, 619], [51.18322, 8.51427, 619],
    [51.18317, 8.5143, 620], [51.18313, 8.51433, 620], [51.18312, 8.51437, 620], [51.18313, 8.5144, 620],
    [51.18316, 8.51441, 620], [51.18323, 8.51438, 619], [51.18327, 8.51441, 619], [51.18326, 8.51447, 619],
    [51.18315, 8.51461, 620], [51.18311, 8.51479, 612],
])

# ---------------------------------------------------------------------------------------------------
# Willingen sub-region: Green Trails Willingen's two long touring loops (official numbers).
# MTB Zone Bikepark Willingen's 12 named descents have no GPX source anywhere and are NOT built --
# see the module docstring and the final report for this gap.
# ---------------------------------------------------------------------------------------------------
WG = os.path.join(MAT, "willingen_gpx")
add_from_gpx("wi_gipfel_runde_hoppecke", "Green Trails Willingen Gipfel-Runde Hoppecke (GRU)",
             "willingen", "blau", os.path.join(WG, "gipfel_runde_hoppecke.gpx"),
             official=(12.91, 314, 282))
add_from_gpx("wi_ruthenaar_double", "Green Trails Willingen Ruthenaar-Double (RUD)",
             "willingen", "blau", os.path.join(WG, "ruthenaar_double.gpx"),
             official=(6.11, 255, 255))

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
