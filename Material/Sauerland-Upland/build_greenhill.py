# -*- coding: utf-8 -*-
"""Green Hill Bikepark (Schmallenberg-Gellinghausen) trail data.

Originally (2026-08-11) all 16 trails were harvested from Trailforks' lighter
/widgets/trail/?trailid=<id>&elevation=1&basic=1 embed. Reworked 2026-08-13 per the user: OSM maps
this park in unusual detail, and where a trail's own OSM way(s) reconstruct cleanly they read as
visibly more precise than Trailforks' embed points (which are comparatively coarse, e.g. 34-95 pts
for a several-hundred-metre trail) -- so OSM now wins for every trail where it can be trusted, and
Trailforks-sourced geometry is kept only where OSM genuinely can't back it up. Also added: three
trails found on OSM that were on neither Trailforks' original list nor the operator's own -- Insta
360 Think Bold, BYND Whip-Off Line, Mile high Club (all schwarz, given directly by the user; OSM
carries no mtb:scale tag for any of them and Trailforks was unreachable behind its own hard
registration wall for a from-scratch difficulty lookup).

## Reconstructing a named trail from OSM's own fragments

OSM splits one physical trail into several way fragments (a tag change, a junction, a mapping
session boundary) that have to be re-assembled in the right order and direction -- `chain_ways()` in
tools/gpx_map_match.py already does exactly this for a coordinate-proximity tolerance, but this
region needed a second, stricter signal too, because the two disagree in both directions here:

- **Coordinate-tolerance chaining can bridge to the WRONG feature.** Raising `tol_m` to close a
  real gap for one trail (Groomer, Save Wimmons) pulled in unrelated nearby fragments instead --
  the tell was the resulting length jumping far past the trail's own already-known Trailforks
  length (Groomer: 331 m -> 1584 m at tol_m=150, a park's black DH line does not gain 5x by
  raising a tolerance 6x). Both stayed on Trailforks geometry; OSM's own mapping of them is
  genuinely too fragmented here to trust.
- **Exact shared-OSM-node chaining can MISS a real, fully-ridable trail.** "I.love.Fidlock" looked
  fragmented at a coordinate tolerance of 25 m (1 leftover way), which is what this file first
  reported -- but the user checked the line on osm.org directly and saw no gap. Rebuilding the
  chain from the ways' own shared node IDs (exact OSM topology, no coordinate rounding at all)
  confirms the user: 0 leftover, one genuinely continuous line. Node-ID chaining is what
  `chain_exact()`/the hybrid chainer below actually use now, with coordinate proximity (tol_m,
  15-25 m depending on the trail) only as a *secondary* attach step for fragments that don't share
  a node but sit within a plausible real-world mapping gap of the chain's own two ends -- and even
  then, cross-checked against the trail's known Trailforks length before trusting the result.

Per trail, in the order decided:
  - Groomer, Save Wimmons: kept on Trailforks geometry -- OSM fragments do not reconstruct within a
    length that stays anywhere near the trail's own already-known distance.
  - Beer Connector, Happy End: OSM has nothing under either name at all (confirmed by the user
    first) -- kept on Trailforks geometry, unchanged.
  - Canadian Tuxedo, Thin Air, Time Shift, I Love Fidlock, Bounce & Blow, Moose Cruise: switched to
    OSM. Node/hybrid-chained cleanly (0-2 unresolved fragments, each checked to sit far enough from
    the main chain's ends to be a genuinely separate spur, not a piece of the real line).
  - Jonas + Pablo: OSM maps both as ONE way group, "Jonas & Pablo" -- chained into one line, then
    split back into the app's own existing two trails at their already-established shared boundary
    point (closest_point_on_polyline found it 3.5 m from the chain, i.e. the same real point).
  - Mamut Lower/Upper Section: same pattern, OSM's "Mammut" split at the existing boundary (0.4 m
    off the chain -- effectively exact).
  - Bike Republic Sölden Line (+ Lower): OSM has no trail under this name at all -- because the
    operator renamed it "MixTape" after a sponsorship deal with Sölden ended (the user's own
    correction; this is why the name search first turned up an unexplained extra "MixTape" entry
    instead of a match). "MixTape"'s main chain splits at the existing Line/Lower boundary (5.8 m
    off) the same way as the two pairs above.
  - Insta 360 Think Bold, BYND Whip-Off Line, Mile high Club: new, single clean OSM ways (Mile high
    Club needed the same hybrid chaining as the switched trails above; the other two are already
    one way each).

Length/up/down: GPX-derived (this app's build_trail() default) for every OSM-sourced trail above,
rather than carrying over the old Trailforks-page stat line -- keeping a stat that describes a
different (Trailforks-drawn) line next to a now-different (OSM-drawn) one would be internally
inconsistent, and GPX-derived is what the rest of this app already falls back to whenever no
official number applies. The four Trailforks-geometry trails keep their original Trailforks-page
stat, unchanged.

Elevation: OSM ways carry no <ele> at all, so every switched/new trail's elevation comes from
`ElevationLookup` (OpenTopoData, cached in Material/elevation_cache.json -- the same cache
add_lifts.py and the OSM-sourced Donnersberg trails already share).

The processed OSM geometry itself (chained, split, ready to feed into build_trail) is cached in
greenhill_osm_final.json next to this script, rather than re-deriving it from a live Overpass query
on every rebuild -- assembling it needed several slow Overpass round-trips plus the hybrid-chaining
logic above; regenerating that from scratch belongs in a one-off script, not this repo-tracked build
step. greenhill_osm_raw.json (every named way's own nodes, kept for the same reason) is what it was
built from, should the chaining ever need redoing with a different tolerance.
"""
import sys, os, json
sys.path.insert(0, r"D:\Trailmap\tools")
from trailmap_pipeline import build_trail, write_region, region_summary, ElevationLookup

MAT = r"D:\Trailmap\Material\Sauerland-Upland"
REGION = "greenhill"
ELEV_CACHE = r"D:\Trailmap\Material\elevation_cache.json"

osm = json.load(open(os.path.join(MAT, "greenhill_osm_final.json"), encoding="utf-8"))
elevation = ElevationLookup(ELEV_CACHE)

trails, geo, profs = [], {}, {}


def add(tid, name, diff, len_m, up, down, pts, uphill=False):
    """Trailforks-sourced (points already carry elevation) -- unchanged trails only."""
    entry, coords, prof = build_trail(tid, name, REGION, diff, pts,
                                       official=(round(len_m / 1000.0, 2), up, down), uphill=uphill)
    trails.append(entry); geo[tid] = coords; profs[tid] = prof


def add_osm(tid, name, diff, uphill=False):
    """OSM-sourced (no elevation in the geometry itself -- ElevationLookup fills it in).
    GPX-derived length/up/down (no official number carries over from the old geometry source)."""
    pts = osm[tid]
    entry, coords, prof = build_trail(tid, name, REGION, diff, pts, uphill=uphill,
                                       elevation=elevation)
    trails.append(entry); geo[tid] = coords; profs[tid] = prof


# ---------------------------------------------------------------------------------------------------
# Kept on Trailforks geometry: OSM has nothing under these two names at all.
# ---------------------------------------------------------------------------------------------------
add("gh_beer_connector", "Beer Connector", "gruen", 281, 3, 21, [[51.23779,8.35488,577],[51.23775,8.35495,577],[51.23773,8.35496,577],[51.2377,8.35496,577],[51.23768,8.35493,577],[51.23764,8.35481,577],[51.23761,8.35454,569],[51.23762,8.35429,569],[51.23758,8.35413,568],[51.23746,8.35396,568],[51.23729,8.35375,559],[51.23712,8.35359,568],[51.23702,8.35352,564],[51.23696,8.35355,564],[51.2369,8.35365,553],[51.23692,8.35378,553],[51.23704,8.35394,553],[51.23715,8.35409,559],[51.2372,8.35421,559],[51.23723,8.35443,559],[51.23724,8.35464,559],[51.23725,8.3548,559],[51.23732,8.35495,559],[51.23733,8.35507,559]])

add("gh_happy_end", "Happy End", "gruen", 278, 2, 14, [[51.23769,8.35923,517],[51.23765,8.35926,517],[51.23763,8.35928,509],[51.23762,8.35931,509],[51.23763,8.35934,509],[51.23765,8.35936,517],[51.23768,8.35934,517],[51.23769,8.35931,517],[51.23769,8.35928,517],[51.23767,8.35925,517],[51.23763,8.3592,509],[51.23752,8.35906,523],[51.23735,8.35883,514],[51.23716,8.35862,514],[51.23707,8.35849,513],[51.23694,8.35833,513],[51.23678,8.35817,504],[51.2367,8.35806,504],[51.23658,8.35792,513],[51.23645,8.35769,502],[51.23631,8.35744,512],[51.23619,8.35727,502],[51.23609,8.3572,502],[51.23599,8.35715,502],[51.23587,8.35715,501]])

# ---------------------------------------------------------------------------------------------------
# Kept on Trailforks geometry: OSM's own mapping of these two is too fragmented to trust (raising
# the chaining tolerance enough to close the gaps balloons the length far past what's already known
# -- see module docstring).
# ---------------------------------------------------------------------------------------------------
add("gh_groomer", "Groomer", "schwarz", 996, 1, 179, [[51.23644,8.34873,684],[51.23636,8.349,684],[51.23637,8.34911,684],[51.23629,8.34953,681],[51.23624,8.34967,681],[51.23618,8.34971,681],[51.23605,8.34984,670],[51.23599,8.34993,670],[51.23598,8.35021,670],[51.23595,8.35028,659],[51.23587,8.35032,659],[51.23568,8.35031,658],[51.23551,8.35035,658],[51.23538,8.35035,656],[51.23546,8.35055,658],[51.23542,8.35075,658],[51.23531,8.35086,648],[51.2352,8.35119,648],[51.235,8.35136,646],[51.23498,8.35145,634],[51.23507,8.35154,634],[51.23509,8.35164,634],[51.23503,8.35182,634],[51.23493,8.35191,634],[51.23474,8.35197,612],[51.23466,8.35204,612],[51.2346,8.35205,612],[51.23453,8.35202,608],[51.23448,8.35206,608],[51.23466,8.35251,593],[51.23462,8.35262,593],[51.23446,8.35269,590],[51.23434,8.35272,590],[51.23421,8.35279,585],[51.23413,8.35281,585],[51.23419,8.35296,585],[51.23418,8.35302,585],[51.23413,8.35302,585],[51.23389,8.35286,581],[51.23384,8.35291,581],[51.2339,8.35309,565],[51.23395,8.35316,565],[51.23397,8.35326,565],[51.23391,8.35326,565],[51.23383,8.35323,565],[51.23374,8.35314,558],[51.23369,8.35319,558],[51.23372,8.35329,558],[51.23412,8.35378,549],[51.23466,8.35452,536],[51.23503,8.35549,508],[51.23516,8.35567,513],[51.23526,8.35572,513],[51.23532,8.35568,513],[51.23533,8.3556,513],[51.23531,8.35556,513],[51.23528,8.35554,513],[51.23525,8.35554,513],[51.23523,8.35557,513],[51.23522,8.35562,513],[51.23524,8.35598,505],[51.23535,8.35647,502],[51.23542,8.35694,502]])

add("gh_save_wimmons", "Save Wimmons", "blau", 1000, 0, 93, [[51.23618,8.34905,689],[51.23596,8.34906,688],[51.23586,8.34916,688],[51.23573,8.34918,678],[51.23547,8.34914,685],[51.23538,8.34904,680],[51.23524,8.34894,680],[51.23521,8.34902,680],[51.2353,8.34916,680],[51.23544,8.34929,674],[51.23552,8.34941,674],[51.2354,8.34946,669],[51.2353,8.34941,669],[51.23516,8.3493,669],[51.23508,8.3493,665],[51.23511,8.34938,665],[51.23522,8.3495,669],[51.23528,8.34961,669],[51.23518,8.34962,669],[51.23507,8.34958,665],[51.23508,8.34964,665],[51.2352,8.34975,661],[51.23545,8.34993,665],[51.23552,8.35,665],[51.23553,8.35004,665],[51.2355,8.35005,665],[51.23544,8.35003,665],[51.23507,8.34994,659],[51.23497,8.34995,659],[51.23491,8.34993,659],[51.23489,8.34999,659],[51.23494,8.35016,659],[51.2349,8.35016,659],[51.23471,8.35005,658],[51.23462,8.34993,658],[51.23458,8.34991,651],[51.2346,8.35017,658],[51.23468,8.35055,651],[51.23487,8.35093,646],[51.2348,8.35101,642],[51.23467,8.35102,642],[51.23455,8.35093,634],[51.23439,8.35069,643],[51.23433,8.35066,643],[51.23433,8.35075,643],[51.2345,8.35121,634],[51.23465,8.35147,629],[51.23477,8.35157,629],[51.23474,8.35164,629],[51.23452,8.35162,625],[51.23438,8.35154,625],[51.23423,8.35138,625],[51.23408,8.35115,625],[51.23404,8.35119,625],[51.23404,8.35136,625],[51.23417,8.35185,618],[51.23417,8.3519,618],[51.23415,8.35192,618],[51.23408,8.35188,618],[51.234,8.3518,609],[51.23397,8.35183,609],[51.23409,8.35202,604],[51.23406,8.35205,604],[51.23397,8.35201,597],[51.23386,8.35192,609],[51.23373,8.35173,601],[51.2337,8.35177,601],[51.23397,8.35228,597],[51.23394,8.35232,597],[51.23385,8.35227,597],[51.23358,8.35205,589]])

# ---------------------------------------------------------------------------------------------------
# Switched to OSM geometry (see module docstring for how each was reconstructed/verified).
# ---------------------------------------------------------------------------------------------------
add_osm("gh_canadian_tuxedo", "Canadian Tuxedo", "rot")
add_osm("gh_thin_air", "Thin Air", "blau")
add_osm("gh_time_shift", "Time Shift", "schwarz")
add_osm("gh_i_love_fidlock", "I Love Fidlock", "schwarz")
add_osm("gh_bounce_blow", "Bounce & Blow", "rot")
add_osm("gh_moose_cruise", "Moose Cruise", "gruen")

# Jonas + Pablo: one OSM way group ("Jonas & Pablo"), split at the two trails' existing boundary.
add_osm("gh_jonas", "Jonas", "blau")
add_osm("gh_pablo", "Pablo", "blau")

# Mamut Lower/Upper: one OSM way group ("Mammut"), split at the existing boundary.
add_osm("gh_mamut_upper_section", "Mamut Upper Section", "schwarz")
add_osm("gh_mamut_lower_section", "Mamut Lower Section", "schwarz")

# Bike Republic Sölden Line (+ Lower): OSM has no trail under this name -- the operator renamed it
# "MixTape" after ending a Sölden sponsorship (user correction). One OSM way group ("MixTape"),
# split at the existing Line/Lower boundary.
add_osm("gh_bike_republic_soelden_line", "Bike Republic Sölden Line", "rot")
add_osm("gh_bike_republic_soelden_line_lower", "Bike Republic Sölden Line Lower", "rot")

# ---------------------------------------------------------------------------------------------------
# New (2026-08-13): found on OSM, on neither Trailforks' nor the operator's own original list.
# Difficulty given directly by the user (schwarz for all three) -- OSM carries no mtb:scale tag for
# any of them, and Trailforks itself was unreachable for a from-scratch lookup (hard regwall).
# ---------------------------------------------------------------------------------------------------
add_osm("gh_insta_360_think_bold", "Insta 360 Think Bold", "schwarz")
add_osm("gh_bynd_whip_off_line", "BYND Whip-Off Line", "schwarz")
add_osm("gh_mile_high_club", "Mile high Club", "schwarz")

if __name__ == "__main__":
    out = {"lineTrails": trails, "trailGeo": geo, "elevationProfiles": profs}
    json.dump(out, open(os.path.join(MAT, "greenhill_partial.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, separators=(", ", ": "))
    print("built", len(trails), "trails")
    for t in trails:
        print(t["id"], t["name"], t["diff"], t["len"], t["up"], t["down"])
