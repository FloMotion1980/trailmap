# -*- coding: utf-8 -*-
"""Match a region's existing trails onto Trailforks trails, so their rating/popularity can be attached.

    python tools/match_trailforks.py finale --material "Finale Ligure" --report out.json
    python tools/match_trailforks.py finale --material "Finale Ligure" --control gardasee

WHY THIS EXISTS. For a region built FROM Trailforks (Gardasee, Madeira) the trail id already IS the
Trailforks slug and there is nothing to match. Finale's ids come from Outdooractive, so its 219 trails have
to be paired with Trailforks' 235 by measurement.

**Names get you almost nowhere here — measured, not assumed: 11 % of Finale's 219 trail names match a
Trailforks row exactly after normalisation.** So geometry decides and the name is one vote among several.

## The four signals, and why each one is needed

Each was added because a real Finale case defeats the others:

1. **Two-way coverage** at `TOL_M`: the share of A's points within tolerance of B, and the reverse. The PAIR
   of numbers classifies the relationship instead of just scoring it — both high is 1:1, one high is a
   section-of relationship (Trailforks splits trails into upper/middle/lower; the Harz needed 21 rows for 11
   real trails), both low is unrelated.
2. **Name similarity** (difflib, diacritics folded, leading "353 - " stripped). Base Nato and Madre Natura
   run 22 m apart over most of their length (56 % coverage at 25 m, 85 % at 50 m) — geometry cannot separate
   them, and their name similarity of 0.57 can.
3. **Both endpoints**, in either orientation. Never one: those same two trails START 6 m apart, so a
   "start matches" test picks the wrong trail; they END 364 m apart, which is what refuses it.
4. **Length ratio**, free of charge — the Trailforks table carries a length per row without fetching any
   trail page at all.

## The rule that matters most: margin, not threshold

A Trailforks "Madre Natura" line scores high against BOTH our Madre Natura and our Base Nato. Absolute
coverage therefore cannot decide; the winner has to beat the RUNNER-UP by `MARGIN`. A near-tie is reported
for review, never assigned. Without this the rating eventually lands on the neighbouring trail, silently.

`TOL_M` stays at 25. At 50 those two parallel trails merge (85 % coverage), so loosening the tolerance to
catch noisy Trailforks lines is exactly what breaks the hardest case. The accepted cost is an unmatched
trail rather than a wrong match.

## Reading the report

Every one of our trails gets its top `TOP_N` candidates with all four numbers, not just the winner — a
report that shows only the winner cannot be reviewed, since the question is always whether the runner-up
was the right one. Verdicts: `match`, `review` (with the reason) or `none`.

`--control <other-region-material>` runs the same matching against a DIFFERENT region's Trailforks table,
where every match is false by construction. It is a falsification test: if that produces matches, the
thresholds are too loose.
"""
import argparse
import difflib
import io
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfaelzerwald_containment import bbox, bbox_overlaps, dist_profile, line_len_m  # noqa: E402
from trailmap_pipeline import haversine_m  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = os.path.join(ROOT, "Trailmap App", "regions")

TOL_M = 25.0            # see the module docstring: 50 merges Base Nato and Madre Natura
MARGIN = 0.15           # how far the winner must lead the runner-up on the geometric score
STRONG_COV = 0.70       # coverage that decides on its own, given the margin
WEAK_COV = 0.40         # below this, geometry says nothing
NAME_SIM = 0.75         # "similar name" for the tie-breaking path
END_NEAR_M = 120.0      # both endpoints within this, in either orientation
LEN_RATIO = 0.6         # shorter/longer length ratio a 1:1 match must reach
NAME_TIE_LEAD = 0.30    # how far the winner's name must beat the runner-up's when geometry ties
CELL = 0.004            # spatial prefilter cell, ~450 m
TOP_N = 3


def norm_name(s):
    """Fold a trail name for comparison. Diacritics out, Trailforks' "#97" suffix out, a leading
    catalogue number out -- but ONLY if a real name remains.

    That last condition is not a nicety: Finale has trails whose name IS a number ("115", "353"), and
    stripping it unconditionally left both sides empty, so the calibration run scored our "115" against
    Trailforks' "115 #97" at a name similarity of 0.00 and sent a geometrically perfect 1:1 match
    (coverage 1.00, endpoints 37 m apart, length ratio 0.99) to manual review.
    """
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\s*#\d+\s*$", "", s)                # Trailforks' own trailing "#97"
    stripped = re.sub(r"^\s*\d+\s*[-.]+\s*", "", s)  # "353 - Strada delle Gatelle"
    if len(re.sub(r"[^a-z0-9]+", "", stripped)) >= 3:
        s = stripped
    s = re.sub(r"\b(trail|sentiero|dh)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


#: The operator's own trail number, as either side happens to write it: ours in brackets after the name
#: ("Velill Trail (7134)"), Trailforks' appended with a hash ("Velilltrail #7134"), and both sometimes
#: leading ("353 - Strada delle Gatelle"). Two digits is enough BECAUSE the rule below also demands real
#: geometric overlap -- a coincidental "2" on two lines that already share 40 % of their points is not a
#: coincidence worth worrying about.
NUM_RE = re.compile(r"#(\d{1,5})|\((\d{1,5})\)|^(\d{2,5})(?![\d])")


def catalogue_numbers(name):
    """Catalogue numbers in a name, compared NUMERICALLY: our "(01)" and their "#1" are the same number.

    Both halves of that mattered in the Harz, where Trailforks writes our own numbering as "#1"/"#2"/"#4"
    while we write "(01)"/"(02)"/"(04)" -- so a two-digit minimum missed every one of them, and a string
    comparison would have missed them again. A LEADING number still needs two digits, because a name that
    merely starts with a digit ("4-Burgen-Weg", "19 Kehren") is not a catalogue reference.
    """
    return set(str(int(g)) for m in NUM_RE.finditer(name or "") for g in m.groups() if g)


def coverage(a, b, tol=TOL_M):
    """Share of a's points within `tol` of b's line."""
    prof = dist_profile(a, b)
    return sum(1 for d in prof if d <= tol) / float(len(prof))


def endpoint_gap(a, b):
    """Worst of the two endpoint distances, in the better of the two orientations."""
    fwd = max(haversine_m(a[0], b[0]), haversine_m(a[-1], b[-1]))
    rev = max(haversine_m(a[0], b[-1]), haversine_m(a[-1], b[0]))
    return min(fwd, rev)


def grid_of(lines):
    g = {}
    for key, coords in lines.items():
        cells = set()
        for lat, lng in coords:
            cells.add((int(lat / CELL), int(lng / CELL)))
        for c in cells:
            g.setdefault(c, set()).add(key)
    return g


def candidates_for(coords, grid):
    near = set()
    for lat, lng in coords:
        gy, gx = int(lat / CELL), int(lng / CELL)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                near |= grid.get((gy + dy, gx + dx), set())
    return near


def score_pair(ours, theirs, our_name, their_name, our_len_m, their_len_m):
    cov_ot = coverage(ours, theirs)
    cov_to = coverage(theirs, ours)
    shared = catalogue_numbers(our_name) & catalogue_numbers(their_name)
    return {
        # A shared catalogue number is an IDENTITY claim by the two sources, not a similarity score, and it
        # is the one signal that survives what defeats the other four: Trailforks splits a trail into
        # sections, so its 2,0 km "Schmuggler Trail #7187" sits inside our 8,5 km trail of the same number
        # at a length ratio of 0,23 -- while a neighbouring section scores HIGHER on pure coverage. The
        # number is what tells those two apart. Found because Trailforks turns out to carry Ischgl's own
        # numbering in its names, which nothing here was looking at.
        "num": sorted(shared),
        "cov_ours_on_theirs": round(cov_ot, 3),
        "cov_theirs_on_ours": round(cov_to, 3),
        "geo": round(max(cov_ot, cov_to), 3),
        "name_sim": round(difflib.SequenceMatcher(None, norm_name(our_name),
                                                  norm_name(their_name)).ratio(), 2),
        "end_gap_m": round(endpoint_gap(ours, theirs)),
        "len_ratio": round(min(our_len_m, their_len_m) / max(our_len_m, their_len_m, 1.0), 2),
        "shape": ("1:1" if cov_ot >= STRONG_COV and cov_to >= STRONG_COV else
                  "theirs_is_part_of_ours" if cov_to >= STRONG_COV else
                  "ours_is_part_of_theirs" if cov_ot >= STRONG_COV else "loose"),
    }


def verdict(best, second):
    """`match` / `review` / `none`, plus the reason. The margin rule lives here."""
    if not best or best["geo"] < WEAK_COV:
        return "none", "no candidate reaches the weak coverage floor"
    # The catalogue number decides before anything else -- but only ON TOP of real overlap (the floor above),
    # never on its own, and never when a second candidate carries the same number: two lines both calling
    # themselves #7187 is precisely the split-into-sections case, and picking one of them by coverage is the
    # silent guess the margin rule exists to prevent.
    if best.get("num"):
        if second and second.get("num") and set(second["num"]) & set(best["num"]):
            return "review", ("two candidates carry the same trail number %s" % ",".join(best["num"]))
        return "match", "the operator's own trail number agrees (%s)" % ",".join(best["num"])
    lead = best["geo"] - (second["geo"] if second else 0.0)
    contradicted = []
    if best["name_sim"] < 0.35:
        contradicted.append("name disagrees (%.2f)" % best["name_sim"])
    if best["shape"] == "1:1" and best["len_ratio"] < LEN_RATIO:
        contradicted.append("lengths disagree (%.2f)" % best["len_ratio"])
    if second and lead < MARGIN:
        # A geometric tie is the NORM, not an anomaly, wherever Trailforks splits a trail into sections:
        # several of its short lines sit inside one of ours, so each scores 1.00 on containment and the
        # margin rule can never separate them. The name is the only thing left that carries information --
        # but only when it is decisive on its own AND clearly beats the runner-up's name, which is what
        # keeps "Schäfersteig" from being decided against "Schäfersteig Continued" (0.83 vs 0.70).
        if (best["name_sim"] >= NAME_SIM
                and best["name_sim"] - (second["name_sim"] or 0) >= NAME_TIE_LEAD):
            return "match", ("geometry ties (%.2f vs %.2f) but the name decides (%.2f vs %.2f)"
                             % (best["geo"], second["geo"], best["name_sim"], second["name_sim"]))
        return "review", ("two candidates within %.2f of each other (%.2f vs %.2f)"
                          % (MARGIN, best["geo"], second["geo"]))
    if best["geo"] >= STRONG_COV:
        if contradicted:
            return "review", "geometry leads but " + " and ".join(contradicted)
        return "match", "geometry decides (%.2f, lead %.2f)" % (best["geo"], lead)
    # The tie-breaking path: geometry undecided, but name AND endpoints AND length all agree.
    if (best["name_sim"] >= NAME_SIM and best["end_gap_m"] <= END_NEAR_M
            and best["len_ratio"] >= LEN_RATIO):
        return "match", "geometry weak (%.2f) but name, endpoints and length agree" % best["geo"]
    return "review", "geometry in the middle band (%.2f) with no confirming signal" % best["geo"]


def run(region_key, material, control=None, report_path=None):
    region = json.load(io.open(os.path.join(REGIONS, region_key + ".json"), encoding="utf-8"))
    ours = {t["id"]: t for t in region["lineTrails"] if not t.get("loop")}
    our_geo = region["trailGeo"]

    mat = material if os.path.isabs(material) else os.path.join(ROOT, "Material", material)
    table = json.load(io.open(os.path.join(mat, "trailforks_table.json"), encoding="utf-8"))
    tf_geo = json.load(io.open(os.path.join(mat, "trailforks_geo.json"), encoding="utf-8"))
    theirs = {}
    for slug, g in tf_geo.items():
        line = g.get("c") or ([[p[2], p[3]] for p in g["p"]] if g.get("p") else None)
        if line and len(line) >= 2:
            theirs[slug] = line
    print("%s: %d of our trails, %d Trailforks lines with geometry" % (region_key, len(ours), len(theirs)))

    grid = grid_of(theirs)
    tf_bb = {s: bbox(c, pad=0.002) for s, c in theirs.items()}
    rows, counts = [], {"match": 0, "review": 0, "none": 0}
    for tid, t in sorted(ours.items()):
        oc = our_geo[tid]
        ob = bbox(oc, pad=0.002)
        our_len = line_len_m(oc)
        scored = []
        for slug in candidates_for(oc, grid):
            if not bbox_overlaps(ob, tf_bb[slug]):
                continue
            s = score_pair(oc, theirs[slug], t["name"], table.get(slug, {}).get("name") or slug,
                           our_len, table.get(slug, {}).get("m") or line_len_m(theirs[slug]))
            s["slug"] = slug
            s["their_name"] = table.get(slug, {}).get("name") or slug
            scored.append(s)
        # A numbered agreement outranks raw coverage, or the section-inside-our-line case never even gets
        # LOOKED at: for the Schmuggler Trail the neighbouring section scores 0.99 and the numbered one 0.94,
        # so sorting by geometry alone hands the verdict to the wrong line before any rule can weigh in.
        # The name is the third key and it is not cosmetic: with several candidates at exactly 1.00 the
        # order was decided by dictionary iteration, which put `che-d-mot` ahead of `planer-salaas` on one
        # run and the other way round on the next -- a verdict that changes without the data changing.
        scored.sort(key=lambda x: (0 if x.get("num") else 1, -x["geo"], -x["name_sim"]))
        v, why = verdict(scored[0] if scored else None, scored[1] if len(scored) > 1 else None)
        counts[v] += 1
        rows.append({"id": tid, "name": t["name"], "len_km": t["len"], "verdict": v, "why": why,
                     "candidates": scored[:TOP_N]})

    # ONE Trailforks line may not feed two of our trails. Each of our trails picks its own best candidate
    # independently, so nothing above prevents two of them claiming the same line -- and on the first Finale
    # run three did, every time because the two claimants are near-duplicates in OUR OWN data (Cava -
    # Tappeto Verde vs Cava-Green Carpet, which is the same name in Italian and English). Attaching one
    # rating to both would state a community's verdict twice, so the weaker claim goes to review and says
    # who took it. That makes the multi-claim a duplicate REPORT rather than a silent overwrite.
    claims = {}
    for r in rows:
        if r["verdict"] == "match":
            claims.setdefault(r["candidates"][0]["slug"], []).append(r)
    for slug, group in claims.items():
        if len(group) < 2:
            continue
        # A NUMBERED claim wins here, before geometry -- otherwise the identity is overruled by a
        # neighbour that merely overlaps more. Measured: "Velill Trail Expert (7146)" took `velilltrail`
        # away from our "Velill Trail (7134)", which is the trail whose number that line actually carries.
        group.sort(key=lambda r: (0 if r["candidates"][0].get("num") else 1,
                                  -r["candidates"][0]["geo"], -r["candidates"][0]["len_ratio"]))
        keeper = group[0]
        for loser in group[1:]:
            loser["verdict"] = "review"
            loser["why"] = ("%r also claims %s and has the stronger claim (%s) -- these two may be the "
                            "same trail in our own data"
                            % (keeper["name"], slug,
                               ("trail number %s" % ",".join(keeper["candidates"][0]["num"]))
                               if keeper["candidates"][0].get("num") else
                               ("coverage %.2f vs %.2f" % (keeper["candidates"][0]["geo"],
                                                           loser["candidates"][0]["geo"]))))
            counts["match"] -= 1
            counts["review"] += 1

    print("  match %d, review %d, none %d" % (counts["match"], counts["review"], counts["none"]))
    if report_path:
        json.dump(rows, io.open(report_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("  report: %s" % report_path)
    return rows, counts


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("region")
    ap.add_argument("--material", required=True, help="Material/ subdir holding the Trailforks harvest")
    ap.add_argument("--report")
    ap.add_argument("--control", help="a DIFFERENT region's Material dir; every match there is false")
    a = ap.parse_args(argv)
    run(a.region, a.material, report_path=a.report)
    if a.control:
        print("\n--- Negativkontrolle gegen %s (jeder Treffer ist falsch) ---" % a.control)
        _, c = run(a.region, a.control)
        print("  Kontrolle: %d falsche Treffer, %d zur Pruefung" % (c["match"], c["review"]))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
