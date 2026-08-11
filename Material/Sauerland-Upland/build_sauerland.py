# -*- coding: utf-8 -*-
"""Build regions/sauerland.json — Sauerland/Upland region group, 2026-08-11.

Three sub-regions, purely geographic bracket (user decision 2026-07-26):
  winterberg  - Trailpark Winterberg (winterberg.de, Outdooractive-hosted) + "The Mother" /
                Bikepark Winterberg (bikepark-winterberg.de, Erlebnisberg Kappe). Two DISTINCT trail
                networks on different hills of the same town -- confirmed by cross-checking trail
                names/lift names/location text, not a duplicate. Both feed one sub-region per the task.
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


# ---------------------------------------------------------------------------------------------------
# Winterberg sub-region, part 1: Trailpark Winterberg (winterberg.de) -- 16 trails, operator numbers.
# LEICHT -> blau, MITTEL -> rot, SCHWER -> schwarz (see module docstring).
# ---------------------------------------------------------------------------------------------------
WB = os.path.join(MAT, "winterberg_gpx")
add_from_gpx("wb_poppenberg_peak", "Poppenberg Peak", "winterberg", "rot",
             os.path.join(WB, "poppenberg_peak.gpx"), official=(0.3, 0, 16))
add_from_gpx("wb_weltcup_flow", "Weltcup Flow", "winterberg", "schwarz",
             os.path.join(WB, "weltcup_flow.gpx"), official=(0.6, 0, 87))
add_from_gpx("wb_uphill_trail", "Uphill-Trail", "winterberg", "blau",
             os.path.join(WB, "uphill_trail.gpx"), official=(1.2, 51, 5), uphill=True, descend=False)
add_from_gpx("wb_moeppis_mover", "Möppis Mover (Uphill)", "winterberg", "rot",
             os.path.join(WB, "moeppis_mover.gpx"), official=(0.5, 56, 0), uphill=True, descend=False)
add_from_gpx("wb_endless_trees", "Endless Trees", "winterberg", "rot",
             os.path.join(WB, "endless_trees.gpx"), official=(0.8, 0, 71))
add_from_gpx("wb_popp_top_track", "Popp Top Track", "winterberg", "rot",
             os.path.join(WB, "popp_top_track.gpx"), official=(0.2, 1, 41))
add_from_gpx("wb_suerenberg_sause", "Sürenberg Sause", "winterberg", "blau",
             os.path.join(WB, "suerenberg_sause.gpx"), official=(0.4, 0, 10))
add_from_gpx("wb_butzhols_bests", "Butzhols Bests", "winterberg", "schwarz",
             os.path.join(WB, "butzhols_bests.gpx"), official=(0.3, 7, 36))
add_from_gpx("wb_little_fluff", "Little Fluff", "winterberg", "rot",
             os.path.join(WB, "little_fluff.gpx"), official=(0.5, 0, 37))
add_from_gpx("wb_shake_the_lake", "Shake the Lake", "winterberg", "schwarz",
             os.path.join(WB, "shake_the_lake.gpx"), official=(0.4, 0, 14))
add_from_gpx("wb_poppies_track", "Poppies Track", "winterberg", "rot",
             os.path.join(WB, "poppies_track.gpx"), official=(0.4, 1, 31))
add_from_gpx("wb_landal", "Landal", "winterberg", "schwarz",
             os.path.join(WB, "landal.gpx"), official=(0.4, 0, 70))
add_from_gpx("wb_bremberg_flow", "Bremberg Flow", "winterberg", "schwarz",
             os.path.join(WB, "bremberg_flow.gpx"), official=(0.4, 0, 51))
add_from_gpx("wb_lolo_wahle_schanze", "Lolo Wahle Schanze", "winterberg", "schwarz",
             os.path.join(WB, "lolo_wahle_schanze.gpx"), official=(0.8, 1, 78))
add_from_gpx("wb_lebe_wild_trail", "Lebe Wild Trail", "winterberg", "schwarz",
             os.path.join(WB, "lebe_wild_trail.gpx"), official=(0.4, 0, 72))
add_from_gpx("wb_cross_over", "Cross Over", "winterberg", "blau",
             os.path.join(WB, "cross_over.gpx"), official=(0.5, 20, 14))

# ---------------------------------------------------------------------------------------------------
# Winterberg sub-region, part 2: "The Mother" / Bikepark Winterberg (Erlebnisberg Kappe) -- 12 of 18
# trails with real GPX. Kinderleicht->gruen, Leicht->blau, Mittel->rot, Schwierig->schwarz.
# GPX-derived len/up/down (site's own aggregate numbers have a visible unit bug, see docstring).
# ---------------------------------------------------------------------------------------------------
TM = os.path.join(MAT, "themother_gpx")
add_from_gpx("tm_kyrhill", "Kyrhill", "winterberg", "blau", os.path.join(TM, "kyrhill.gpx"))
add_from_gpx("tm_jolli_jumper", "Jolli Jumper", "winterberg", "rot", os.path.join(TM, "jolli_jumper.gpx"))
add_from_gpx("tm_north_shore", "North Shore", "winterberg", "rot", os.path.join(TM, "north_shore.gpx"))
add_from_gpx("tm_freeride", "Freeride", "winterberg", "rot", os.path.join(TM, "freeride.gpx"))
add_from_gpx("tm_blackline_1", "Blackline 1.0", "winterberg", "schwarz", os.path.join(TM, "blackline_1.gpx"))
add_from_gpx("tm_sram_flow_country", "SRAM Flow Country", "winterberg", "blau",
             os.path.join(TM, "sram_flow_country.gpx"))
add_from_gpx("tm_schneewittchen_trail", "Schneewittchen-Trail", "winterberg", "gruen",
             os.path.join(TM, "schneewittchen_trail.gpx"))
add_from_gpx("tm_fairy_trail", "Fairy-Trail", "winterberg", "gruen", os.path.join(TM, "fairy_trail.gpx"))
add_from_gpx("tm_forrest_stump", "Forrest Stump", "winterberg", "rot", os.path.join(TM, "forrest_stump.gpx"))
add_from_gpx("tm_rocky_waldboa", "Rocky Waldboa", "winterberg", "rot", os.path.join(TM, "rocky_waldboa.gpx"))
add_from_gpx("tm_shreddy_moerphy", "Shreddy Mörphy", "winterberg", "rot",
             os.path.join(TM, "shreddy_moerphy.gpx"))
add_from_gpx("tm_fly_by", "Fly By", "winterberg", "blau", os.path.join(TM, "fly_by.gpx"))

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
