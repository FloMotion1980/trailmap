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

- **Coordinate-tolerance chaining can bridge to the WRONG feature -- but the fix isn't "give up",
  it's "find the real structure first".** Raising `tol_m` to close what looked like a gap in
  Groomer/Save Wimmons pulled in unrelated nearby fragments instead -- the tell was the resulting
  length jumping far past the trail's own already-known Trailforks length (Groomer: 331 m -> 1584 m
  at tol_m=150). The first version of this file concluded from that alone that OSM's mapping of
  both was too fragmented to trust and left them on Trailforks geometry. The user pushed back
  (2026-08-13, having looked at the map) and that turned out right: **proper connected-component
  analysis** (union-find over each way's own OSM node IDs, not "grow one chain from the longest way
  and call everything else a leftover") shows each of these two trails is actually TWO separate,
  but each fully self-connected, clusters of ways -- Groomer: 331 m + 703 m, Save Wimmons: 831 m +
  353 m -- with a small, genuine, unmapped gap between the two clusters (52 m and 33 m). Joining
  each pair end-to-end lands within 9%/22% of the trail's own known length, which is what actually
  measures success here, not "0 leftovers from a single greedy chain". The earlier tolerance-based
  attempt failed for a different reason than "OSM lacks this trail": a single greedy chain-grower
  can only ever report ONE connected component and calls every fragment outside it a leftover, even
  when those fragments are perfectly connected *to each other* -- worth remembering before
  concluding "too fragmented" again for a future region.
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
  - Beer Connector, Happy End: OSM has nothing under either name at all (confirmed by the user
    first) -- kept on Trailforks geometry, unchanged.
  - Thin Air, Time Shift, I Love Fidlock, Bounce & Blow, Moose Cruise: switched to OSM.
    Node/hybrid-chained cleanly (0-2 unresolved fragments, each checked to sit far enough from the
    main chain's ends to be a genuinely separate spur, not a piece of the real line).
  - Canadian Tuxedo: same, but the first pass got the "genuinely separate spur" call wrong for its
    own 2nd, smaller way (137 m) -- excluded for sitting 16 m past a 15 m attach tolerance, which
    read as consistent at the time (the main way alone, 868 m, already matched the trail's known
    Trailforks length of 874 m closely). The user caught it directly ("ein kleines Teilstück am
    Ende fehlt") after the switch: that excluded fragment's own far end lines up with the trail's
    real, previously-recorded end point, so it was the missing continuation, not a spur -- a 16 m
    OSM mapping gap being slightly bigger than average is not the same as it being wrong. Included
    now (1022 m total). Worth remembering: closely matching an old length is a good sign but not
    proof that nothing was left off the end.
  - Groomer, Save Wimmons: switched to OSM -- two connected components each (see above), joined
    end-to-end across their one real, small gap.
  - Jonas + Pablo: OSM maps both as ONE way group, "Jonas & Pablo" -- and per the user (2026-08-13,
    after seeing how cleanly it reconstructed) merged into one trail, `gh_jonas_pablo`, rather than
    split back into the app's original two. (The split point had been located anyway --
    closest_point_on_polyline found the two trails' existing shared boundary just 3.5 m from the
    chain -- before the user asked for the merge instead.)
  - Mamut Lower/Upper Section: OSM's "Mammut" still split into the app's existing two trails at that
    boundary (0.4 m off the chain -- effectively exact); the user did not ask to merge this pair.
  - Bike Republic Sölden Line (+ Lower): OSM has no trail under this name at all -- because the
    operator renamed it "MixTape" after a sponsorship deal with Sölden ended (the user's own
    correction; this is why the name search first turned up an unexplained extra "MixTape" entry
    instead of a match). Per the user, merged into one trail the same way as Jonas + Pablo, keeping
    the operator's current name (not the OSM/pre-rename "MixTape").
  - Insta 360 Think Bold, BYND Whip-Off Line, Mile high Club: new, single clean OSM ways (Mile high
    Club needed the same hybrid chaining as the switched trails above; the other two are already
    one way each).
  - Warm Up: new, single clean OSM way (39 pts, 127 m) -- gruen, given directly by the user.

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
# Switched to OSM geometry (see module docstring for how each was reconstructed/verified).
# ---------------------------------------------------------------------------------------------------
add_osm("gh_canadian_tuxedo", "Canadian Tuxedo", "rot")
add_osm("gh_thin_air", "Thin Air", "blau")
add_osm("gh_time_shift", "Time Shift", "schwarz")
add_osm("gh_i_love_fidlock", "I Love Fidlock", "schwarz")
add_osm("gh_bounce_blow", "Bounce & Blow", "rot")
add_osm("gh_moose_cruise", "Moose Cruise", "gruen")

# Groomer, Save Wimmons: two OSM connected components each, joined across one real, small gap
# (52 m / 33 m) -- see module docstring for why the first attempt at these two got it wrong.
add_osm("gh_groomer", "Groomer", "schwarz")
add_osm("gh_save_wimmons", "Save Wimmons", "blau")

# Jonas + Pablo: one OSM way group ("Jonas & Pablo"), merged into one trail per the user.
add_osm("gh_jonas_pablo", "Jonas & Pablo", "blau")

# Mamut Lower/Upper: one OSM way group ("Mammut"), split at the existing boundary (not merged --
# the user only asked to merge Jonas+Pablo and the two Sölden trails).
add_osm("gh_mamut_upper_section", "Mamut Upper Section", "schwarz")
add_osm("gh_mamut_lower_section", "Mamut Lower Section", "schwarz")

# Bike Republic Sölden Line (+ Lower): OSM has no trail under this name -- the operator renamed it
# "MixTape" after ending a Sölden sponsorship (user correction). One OSM way group ("MixTape"),
# merged into one trail per the user, keeping the operator's current name.
add_osm("gh_bike_republic_soelden_line", "Bike Republic Sölden Line", "rot")

# ---------------------------------------------------------------------------------------------------
# New (2026-08-13): found on OSM, on neither Trailforks' nor the operator's own original list.
# Difficulty given directly by the user for all four -- OSM carries no mtb:scale tag for any of
# them, and Trailforks itself was unreachable for a from-scratch lookup (hard regwall).
# ---------------------------------------------------------------------------------------------------
add_osm("gh_insta_360_think_bold", "Insta 360 Think Bold", "schwarz")
add_osm("gh_bynd_whip_off_line", "BYND Whip-Off Line", "schwarz")
add_osm("gh_mile_high_club", "Mile high Club", "schwarz")
add_osm("gh_warm_up", "Warm Up", "gruen")

if __name__ == "__main__":
    out = {"lineTrails": trails, "trailGeo": geo, "elevationProfiles": profs}
    json.dump(out, open(os.path.join(MAT, "greenhill_partial.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, separators=(", ", ": "))
    print("built", len(trails), "trails")
    for t in trails:
        print(t["id"], t["name"], t["diff"], t["len"], t["up"], t["down"])
