"""Build regions/harz.json -- the Harz region (6 bike parks as sub-regions).

Geometry source: Trailforks' own per-trail `encodedpath` (see the project's
`trailforks-anonymous-polyline-extraction` notes), harvested 2026-08-13 through the user's own logged-in
Chrome and decoded IN the browser so the backslash-escaping trap that corrupted 52 of Varazze's 53 trails
cannot apply here at all -- every one of the 67 decoded lines was checked against Trailforks' own stated
distance and agreed to within 2 m. The decoded coordinates live in `Material/Harz/harz_tf_geo.json`.

Elevation: Trailforks does not embed a profile on the trail page (checked -- no numeric array anywhere in
the page's scripts), so `ElevationLookup` fills it in the usual way.

Two things about this region need explaining, because they are decisions rather than mechanics:

**Teilabschnitte.** Trailforks splits most of these parks' trails into numbered "upper/middle/lower"
sections -- 21 rows for Hahnenklee's 11 real trails, 13 for Bodetal's 6. The user asked for them to be
merged. Which sections belong together is NOT taken from their names: `SECTIONS` below lists the chain and
`chain()` verifies every joint by measuring the actual endpoint distance, refusing anything over
`MAX_JOINT_M`. That is what caught the two cases the names get wrong -- `harzer-roller-3` joins
`brunhildenritt-2` at 0.7 m (it is the stretch the two trails SHARE, which is why Trailforks has no
"Brunhildenritt 3"; the user told us this independently) and `senduro-entry` is the entry to Wildpig
Enduro, 2.3 m from its start, despite sharing no word with it.

**Names and difficulties** come from the operator where the mapping is certain, from Trailforks otherwise.
St. Andreasberg resolved cleanly and completely: Trailforks carries the park's own `#1`-`#6`/`#9` numbers,
and `msbx-6`'s own description ("#6 is the easiest of the steep routes, several options to cross over to #4
and #5") confirms they are the same numbering the operator publishes -- so all eight get their official
name. Difficulty was Trailforks' own per-trail rating throughout when this region was first built (the rule
the user set for Finale Ligure, see `finale-difficulty-realignment`); **since 2026-08-14 the operator's own
published grade wins wherever there is one**, per the user's standing rule -- see `OPERATOR_DIFF` below for
which parks publish one at all, how a three-step German scale maps onto this app's four colours, and which
trails are therefore left on Trailforks' rating.

`len` is the geometry's own length, not the operator's published figure, wherever the two disagree by more
than rounding -- the published numbers are marketing-rounded and several of them (Braunlage's Freeride at
"ca. 3.400 m" against a 2 034 m line) would put a number on screen that the drawn trail visibly is not.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import (ElevationLookup, build_trail, haversine_m, region_summary,
                               write_region)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO_SRC = os.path.join(ROOT, "Material", "Harz", "harz_tf_geo.json")
OUT = os.path.join(ROOT, "Trailmap App", "regions", "harz.json")

# A joint wider than this is treated as a build error rather than stitched over. Every real joint in this
# data came in under 50 m; the widest kept one is Harzer Roller's 2->3 at 49.5 m, which is a genuine short
# link in the trail and short enough that a straight stitch stays inside the corridor (the same call made
# for Portes du Soleil's ~100 m stitches). Anything larger would need real routing, not a straight line.
MAX_JOINT_M = 55.0

# Joints that are genuinely wider than MAX_JOINT_M and are stitched straight anyway, listed one by one with
# the measured distance so a NEW wide joint still fails loudly instead of being absorbed by a raised global
# threshold. Only one exists in this region: Braunlage's Freeride passes the gondola's MIDDLE STATION
# between its upper and lower halves, and both halves end/start on the platform apron rather than at the
# same point -- Trailforks has no section covering the crossing. 83 m is inside the range this project has
# stitched straight before (Portes du Soleil: 86 m, 106.67 m, 111 m). Note this is NOT the whole story for
# that trail: the operator publishes Freeride at ~3 400 m against our 2 034 m of line, so Trailforks is
# missing well over a kilometre of it -- recorded as a known gap rather than interpolated.
WIDE_JOINTS = {("hz_bl_freeride", "freeride-lower"): 90.0}

TF_DIFF = {"Easy": "gruen", "Intermediate": "blau", "Difficult": "rot", "Severe": "schwarz"}
DIFF_ORDER = ["gruen", "blau", "rot", "schwarz"]

# Trailforks' own per-trail rating for every harvested section, straight off each region's table view.
SECTION_DIFF = {
    # Trailpark Harz (Ilsenburg)
    "eselsstieg": "Intermediate", "jack-the-ripper-195079": "Severe",
    "jack-the-ripper-alt": "Severe", "stumpfruckentrail": "Easy",
    # not in the region table (it is filed under Wernigerode); read off its own trail page instead
    "wassertal-dh-ilsenburg": "Severe",
    # Bikepark Hahnenklee
    "aline-hahnenklee": "Difficult", "bockchen--flowtrail": "Intermediate",
    "dh-middle-hahnenklee": "Severe", "dh-upper-hahnenklee": "Severe",
    "flowtrail-hahnenklee-middle-part": "Intermediate",
    "hahnenklee-dh-race-straight-jump-109259": "Severe",
    "hahnenklee-lower-freeride-to-dh-race": "Intermediate",
    "hahnenklee-middle-freeride": "Intermediate", "hahnenklee-upper-freeride": "Intermediate",
    "jump-line-184348": "Difficult", "race-track-lower": "Severe", "race-track-middle": "Severe",
    "race-track-upper": "Severe", "senduro-entry": "Intermediate", "spiegelthalertrail": "Easy",
    "sprung-bockchen": "Intermediate", "wilder-bock--ex-north-shore": "Severe",
    "wildpig-enduro-lower": "Difficult", "wildpig-enduro-lower-middle": "Intermediate",
    "wildpig-enduro-upper": "Difficult", "wildpig-enduro-upper-middle": "Intermediate",
    # Bikepark Bodetal (Rosstrappe)
    "bodetrail": "Intermediate", "bodopass": "Intermediate", "brunhildenritt-1": "Intermediate",
    "brunhildenritt-2": "Difficult", "brunhildenritt-4": "Difficult", "felsenweg-637714": "Intermediate",
    "harzer-roller-1": "Intermediate", "harzer-roller-2": "Intermediate",
    "harzer-roller-3": "Intermediate", "harzer-roller-4": "Intermediate",
    "rosstrappendownhill-1": "Difficult", "rosstrappendownhill-2": "Difficult",
    "rosstrappendownhill-3": "Difficult",
    # Racepark Schulenberg
    "flowtrail-757021": "Intermediate", "freeride-124762": "Difficult",
    "hidden-track-757023": "Difficult", "hidden-track-alternative-unten": "Difficult",
    "schulenberg-bx": "Intermediate", "schulenberg-dh-race": "Severe", "stempelstieg": "Severe",
    # Bikepark St. Andreasberg (MSB-X-Trail)
    "flowtrail-lower": "Easy", "loam-line-221019": "Difficult", "msbx-6": "Difficult",
    "msbx-enduro": "Difficult", "msbx-north-shore-lower": "Intermediate",
    "msbx-north-shore-upper": "Intermediate", "msbx1-flowtrail": "Easy",
    "msbx2-wurzeltrail-lower": "Intermediate", "msbx2-wurzeltrail-upper": "Easy",
    "msbxjumpline": "Intermediate", "schwarzer-keiler": "Difficult",
    # Bikepark Braunlage (Wurmberg)
    "dh-upper-140882": "Intermediate", "downhill-lower-section": "Intermediate",
    "downhill-middle-section": "Intermediate", "enduro-lower": "Difficult", "enduro-upper": "Difficult",
    "evil-rocks-upper": "Severe", "freeride-lower": "Difficult", "freeride-upper": "Difficult",
    "singletrail-lower": "Severe", "wurmberg-roller-upper-dh": "Easy",
}

# The OPERATOR's own published grade, which WINS over Trailforks wherever it exists and the trail is mapped
# to the operator's own name with certainty -- the user's standing rule (2026-08-14), replacing the
# Trailforks-throughout rule this region was first built to.
#
# Only three of the six parks publish a grade at all (all six operator pages re-checked 2026-08-14):
# St. Andreasberg's numbered 1-9 list, Trailpark Ilsenburg's six, and Bodetal's prose. Hahnenklee,
# Schulenberg and Braunlage publish NONE -- Braunlage's own coloured dots are trail MARKINGS, not grades,
# which its Enduro's Trailforks description confirms ("official trail number 4, white markings") -- so those
# three keep Trailforks' rating and there is nothing here to override.
#
# The operator scale is three-step (leicht / mittel / schwer) against this app's four colours, so it maps
# onto the app's OWN labels rather than onto Trailforks' tiers: leicht -> blau ("Leicht"), mittel -> rot
# ("Mittel"), schwer -> schwarz ("Schwer"). No operator here says "sehr leicht", so `gruen` is simply never
# reached this way -- a park's easiest line being blau is the honest reading of "leicht", not a lost tier.
# A trail the operator rates across TWO steps ("leicht / mittel", "mittel / schwer") takes the HARDER one:
# the user's own call, and the same direction `max()` already resolves a merged trail's sections in.
#
# Each entry carries the operator's own wording next to the colour, so the mapping is auditable without
# re-fetching six pages.
OPERATOR_DIFF = {
    # ---- Bikepark St. Andreasberg -- bikepark-andreasberg.de/trails, its own numbered 1-9 list ---------
    "hz_ab_flowtrail": ("leicht", "blau"),
    "hz_ab_singletrail": ("leicht / mittel", "rot"),
    "hz_ab_funride": ("mittel", "rot"),
    "hz_ab_freeride": ("schwer", "schwarz"),
    "hz_ab_enduro": ("mittel / schwer", "schwarz"),
    "hz_ab_downhill": ("schwer", "schwarz"),
    "hz_ab_jump_line": ("mittel / schwer", "schwarz"),
    # `Loam Line` is absent from the operator's list (unnumbered on Trailforks, and no length match to the
    # unnumbered #7 Super Enduro), so no operator grade applies and it keeps Trailforks' Difficult/rot.

    # ---- Trailpark Harz (Ilsenburg) -- trailparkharz.de -----------------------------------------------
    # Only these two map to an operator name with certainty (see TRAILS below), and both were already
    # schwarz -- listed anyway to record that the operator WAS checked and agrees. Eselsstieg and
    # Stumpfrücken-Trail cannot be mapped to an operator name at all, so no operator grade exists for them.
    "hz_tp_jack_the_ripper": ("schwer", "schwarz"),
    "hz_tp_wassertal": ("schwer", "schwarz"),

    # ---- Bikepark Bodetal (Rosstrappe) -- bikepark-bodetal.de, stated in prose rather than as grades ---
    # Brunhildenritt is graded across its own length ("im oberen Teil leichten, im unteren Teil
    # mittelschweren Enduro-Trail"), which is the same two-step case as St. Andreasberg's: the harder half
    # decides.
    "hz_bt_brunhildenritt": ("oben leicht / unten mittelschwer", "rot"),
    "hz_bt_harzer_roller": ("leichte Strecke", "blau"),
    "hz_bt_bodopass": ("weitere leichte Strecke", "blau"),
    # 04 Rosstrappendownhill and 04a Felsenweg carry no operator wording, and `Bodetrail` is not one of the
    # park's own numbered trails at all -- all three keep Trailforks' rating.
}

# (id, display name, sub-region, [section slugs in ride order])
TRAILS = [
    # ---- Trailpark Harz (Ilsenburg) -- no lift, no entry fee, five natural trails ------------------
    # The operator's own site (trailparkharz.de) lists Waldbad / Moosklippe / Mönchsgraben / Jack the
    # Ripper / Wassertal / Kammweg. Only Jack the Ripper and Wassertal map to a Trailforks trail with
    # certainty (their descents agree to the metre: -227 m and -231 m). Eselsstieg and Stumpfrücken-Trail
    # keep their Trailforks names rather than being guessed onto Kammweg/Waldbad -- both are real local
    # names carrying their own Trailforks description ("from Ilsestein towards Ilsenburg", "very fast
    # trail, 50-60 km/h"), and renaming them on a length resemblance is the kind of silent auto-correction
    # this project has rejected before. Moosklippe and Mönchsgraben are officially CLOSED and have no
    # Trailforks geometry at all, so they are absent rather than invented.
    ("hz_tp_eselsstieg", "Eselsstieg", "trailpark_harz", ["eselsstieg"]),
    ("hz_tp_jack_the_ripper", "Jack the Ripper", "trailpark_harz", ["jack-the-ripper-195079"]),
    ("hz_tp_jack_the_ripper_alt", "Jack the Ripper Alt", "trailpark_harz", ["jack-the-ripper-alt"]),
    ("hz_tp_stumpfruecken", "Stumpfrücken-Trail", "trailpark_harz", ["stumpfruckentrail"]),
    ("hz_tp_wassertal", "Wassertal", "trailpark_harz", ["wassertal-dh-ilsenburg"]),

    # ---- Bikepark Hahnenklee (Bocksberg) ----------------------------------------------------------
    # The operator's page names only two trails in prose ("Flowtrail", "Wilde Drachen"), so these keep
    # Trailforks' names. Every multi-section chain below is endpoint-verified by chain().
    ("hz_hk_flowtrail", "Böckchen / Flowtrail", "hahnenklee",
     ["bockchen--flowtrail", "flowtrail-hahnenklee-middle-part"]),
    ("hz_hk_downhill", "Downhill", "hahnenklee", ["dh-upper-hahnenklee", "dh-middle-hahnenklee"]),
    ("hz_hk_freeride", "Freeride", "hahnenklee",
     ["hahnenklee-upper-freeride", "hahnenklee-middle-freeride", "hahnenklee-lower-freeride-to-dh-race"]),
    ("hz_hk_race_track", "Race Track", "hahnenklee",
     ["race-track-upper", "race-track-middle", "race-track-lower"]),
    # "senduro Entry" ends 2.3 m from Wildpig Enduro's start and is named Entry; merged as this trail's
    # first stretch rather than left as a 214 m orphan.
    ("hz_hk_wildpig_enduro", "Wildpig Enduro", "hahnenklee",
     ["senduro-entry", "wildpig-enduro-upper", "wildpig-enduro-upper-middle",
      "wildpig-enduro-lower-middle", "wildpig-enduro-lower"]),
    ("hz_hk_aline", "A-Line", "hahnenklee", ["aline-hahnenklee"]),
    ("hz_hk_jump_line", "Jump Line", "hahnenklee", ["jump-line-184348"]),
    ("hz_hk_sprung_boeckchen", "Sprung Böckchen", "hahnenklee", ["sprung-bockchen"]),
    ("hz_hk_wilder_bock", "Wilder Bock (ex North Shore)", "hahnenklee",
     ["wilder-bock--ex-north-shore"]),
    ("hz_hk_dh_race_jump", "DH Race Straight Jump", "hahnenklee",
     ["hahnenklee-dh-race-straight-jump-109259"]),
    ("hz_hk_spiegelthaler", "Spiegelthaler-Trail", "hahnenklee", ["spiegelthalertrail"]),

    # ---- Bikepark Bodetal (Rosstrappe, Thale) -----------------------------------------------------
    # The operator numbers its trails 01-05 and those numbers are kept in the display names. Trailforks
    # has no "Brunhildenritt 3" because segment 3 of Brunhildenritt IS Harzer Roller 3 -- one physical
    # stretch both trails use (the user's own note, independently confirmed here by the 0.7 m joint).
    # It therefore appears in both chains, which is correct: two trails sharing a stretch is not a
    # duplicate.
    ("hz_bt_brunhildenritt", "Brunhildenritt (01)", "bodetal",
     ["brunhildenritt-1", "brunhildenritt-2", "harzer-roller-3", "brunhildenritt-4"]),
    ("hz_bt_harzer_roller", "Harzer Roller (02)", "bodetal",
     ["harzer-roller-1", "harzer-roller-2", "harzer-roller-3", "harzer-roller-4"]),
    ("hz_bt_bodopass", "Bodopass (03)", "bodetal", ["bodopass"]),
    ("hz_bt_rosstrappendownhill", "Rosstrappendownhill (04)", "bodetal",
     ["rosstrappendownhill-1", "rosstrappendownhill-2", "rosstrappendownhill-3"]),
    ("hz_bt_felsenweg", "Felsenweg (04a)", "bodetal", ["felsenweg-637714"]),
    # Not one of the park's numbered runs -- the long Bodetal valley trail, in the same Trailforks region.
    ("hz_bt_bodetrail", "Bodetrail", "bodetal", ["bodetrail"]),

    # ---- Racepark Schulenberg ---------------------------------------------------------------------
    # Nothing to merge here: all four of Flowtrail/Freeride/Hidden Track/BX share a start area at the top
    # and converge on one point at the bottom (0.0-1.1 m apart), i.e. they are four complete parallel
    # trails, not sections of one. Names are the operator's own (outdoorwerkstatt.eu).
    ("hz_sb_flowtrail", "Flowtrail", "schulenberg", ["flowtrail-757021"]),
    ("hz_sb_freeride", "Freeride", "schulenberg", ["freeride-124762"]),
    ("hz_sb_hidden_track", "Hidden Track", "schulenberg", ["hidden-track-757023"]),
    # Branches off Hidden Track mid-trail, not at an endpoint (which is why it has no joint to anything)
    # -- an alternative lower line, so it stays its own entry.
    ("hz_sb_hidden_track_alt", "Hidden Track (Alternative unten)", "schulenberg",
     ["hidden-track-alternative-unten"]),
    ("hz_sb_bx", "BX Bikercross", "schulenberg", ["schulenberg-bx"]),
    ("hz_sb_downhill", "Downhill", "schulenberg", ["schulenberg-dh-race"]),
    ("hz_sb_stempelstieg", "Stempelstieg", "schulenberg", ["stempelstieg"]),

    # ---- Bikepark St. Andreasberg (MSB-X-Trail) ---------------------------------------------------
    # Fully resolved against the operator's own numbered list 1-9; the Trailforks rows carry the same
    # numbers. Trailforks' section names are the local ones (Wurzeltrail = the official "Singletrail",
    # North Shore = "Funride", Schwarzer Keiler = "Freeride"), so the official name leads and the local
    # one follows in brackets where it differs and is worth keeping.
    ("hz_ab_flowtrail", "Flowtrail (1)", "andreasberg", ["msbx1-flowtrail", "flowtrail-lower"]),
    ("hz_ab_singletrail", "Singletrail (2) – Wurzeltrail", "andreasberg",
     ["msbx2-wurzeltrail-upper", "msbx2-wurzeltrail-lower"]),
    ("hz_ab_funride", "Funride (3) – North Shore", "andreasberg",
     ["msbx-north-shore-upper", "msbx-north-shore-lower"]),
    # Operator: "schwer". Trailforks: Difficult/Red. The operator wins since 2026-08-14 -- see OPERATOR_DIFF.
    ("hz_ab_freeride", "Freeride (4) – Schwarzer Keiler", "andreasberg", ["schwarzer-keiler"]),
    ("hz_ab_enduro", "Enduro Trail (5)", "andreasberg", ["msbx-enduro"]),
    ("hz_ab_downhill", "Downhill Trail (6)", "andreasberg", ["msbx-6"]),
    ("hz_ab_jump_line", "Jump Line (9)", "andreasberg", ["msbxjumpline"]),
    # No number on Trailforks and no length match to the operator's unnumbered #7 "Super Enduro", so it
    # keeps its Trailforks name instead of being assigned one.
    ("hz_ab_loam_line", "Loam Line", "andreasberg", ["loam-line-221019"]),

    # ---- Bikepark Braunlage (Wurmberg) -----------------------------------------------------------
    # The operator publishes four trails (Freeride, Snakebite, Evil Rock's, Enduro) and numbers them;
    # `enduro-upper`'s own Trailforks description names its number outright ("official Braunlage Bikepark
    # trail number 4, white markings"), which is what fixes Enduro. Freeride matches by description
    # (Trailforks: "Northshore Line, wooden structures, drops and jumps"; operator: "wood elements, jumps,
    # chicken lines"). Evil Rock's takes its Trailforks name plus the "former racetrack" lower stretch it
    # joins at 6.6 m. The three "Downhill" sections keep the Trailforks name: the operator has no
    # "Downhill", and calling them Snakebite would be a guess -- flagged for the user.
    ("hz_bl_freeride", "Freeride", "braunlage", ["freeride-upper", "freeride-lower"]),
    ("hz_bl_enduro", "Enduro (4)", "braunlage", ["enduro-upper", "enduro-lower"]),
    ("hz_bl_evil_rocks", "Evil Rock's", "braunlage", ["evil-rocks-upper", "singletrail-lower"]),
    ("hz_bl_downhill", "Downhill", "braunlage",
     ["dh-upper-140882", "downhill-middle-section", "downhill-lower-section"]),
    ("hz_bl_wurmberg_roller", "Wurmberg Roller (oben)", "braunlage", ["wurmberg-roller-upper-dh"]),
]


def chain(geo, slugs, trail_id):
    """Concatenate `slugs` into one ride-order coordinate list, orienting each section by measurement.

    Each section is flipped or not depending on which of its two ends is nearer the running chain's tail,
    and every joint is asserted under MAX_JOINT_M -- a section list that is wrong in order or in membership
    fails here instead of silently welding a straight line across the hillside.
    """
    out = [list(p) for p in geo[slugs[0]]]
    joints = []
    for slug in slugs[1:]:
        pts = [list(p) for p in geo[slug]]
        to_start = haversine_m(out[-1], pts[0])
        to_end = haversine_m(out[-1], pts[-1])
        if to_end < to_start:
            pts.reverse()
            gap = to_end
        else:
            gap = to_start
        limit = WIDE_JOINTS.get((trail_id, slug), MAX_JOINT_M)
        if gap > limit:
            raise SystemExit("%s: joint to %s is %.1f m (> %.0f m) -- section list is wrong, or add an "
                             "explicit WIDE_JOINTS entry if the gap is real"
                             % (trail_id, slug, gap, limit))
        joints.append((slug, round(gap, 1)))
        # Drop a duplicated shared point so the merged line has no zero-length segment.
        if gap < 0.5:
            pts = pts[1:]
        out.extend(pts)
    return out, joints


def resolve_diff(trail_id, slugs):
    """The colour a trail is built with, as (diff, trailforks_diff, operator_wording).

    Two rules in one place: the operator's own published grade WINS wherever OPERATOR_DIFF has one, and a
    trail Trailforks split into sections takes the HARDEST of those sections' ratings (a trail is only as
    easy as its hardest stretch). `trailforks_diff` is returned alongside so a caller can report where the
    two sources disagree instead of silently discarding one of them.
    """
    tf = TF_DIFF[max((SECTION_DIFF[s] for s in slugs), key=lambda d: DIFF_ORDER.index(TF_DIFF[d]))]
    wording, diff = OPERATOR_DIFF.get(trail_id, (None, tf))
    return diff, tf, wording


def main():
    geo_src = json.load(open(GEO_SRC, encoding="utf-8"))
    missing = [s for _, _, _, ss in TRAILS for s in ss if s not in geo_src]
    if missing:
        raise SystemExit("missing geometry for: %s" % sorted(set(missing)))

    ele = ElevationLookup(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "elevation_cache.json"))
    trails, geo, profs = [], {}, {}
    for trail_id, name, region, slugs in TRAILS:
        raw, joints = chain(geo_src, slugs, trail_id)
        diff, tf, wording = resolve_diff(trail_id, slugs)
        entry, coords, prof = build_trail(trail_id, name, region, diff, raw, elevation=ele)
        trails.append(entry)
        geo[trail_id] = coords
        profs[trail_id] = prof
        if wording and diff != tf:
            print("%-28s Betreiber: %-26s -> %-7s (Trailforks: %s)" % (trail_id, wording, diff, tf))
        note = ("  joints: " + ", ".join("%s +%.1fm" % (s, g) for s, g in joints)) if joints else ""
        print("%-28s %-32s %-7s %5.2f km  +%3d/-%3d m  %3d pts%s"
              % (trail_id, name, entry["diff"], entry["len"], entry["up"], entry["down"],
                 len(coords), note))

    data = write_region(OUT, trails, geo, profs)
    print()
    print(region_summary(data))


if __name__ == "__main__":
    main()
