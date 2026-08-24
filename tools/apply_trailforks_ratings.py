# -*- coding: utf-8 -*-
"""Write Trailforks' community rating and popularity into a region file.

    python tools/apply_trailforks_ratings.py finale --material "Finale Ligure" --dry-run
    python tools/apply_trailforks_ratings.py finale --material "Finale Ligure"

Reads the match report `tools/match_trailforks.py` produced (or recomputes it) and copies three fields onto
the matched trails' `lineTrails` entries:

    "rate": 4.64      # rating_bayesian, 0-5, vote-count-shrunk -- NEVER the raw average
    "votes": 108      # so the app can show how thin the basis is
    "pop": 95         # popularity_score 0-100, a year of check-ins, NOT a quality statement
    "tf": "base-nato" # the Trailforks slug this came from

**`tf` is the field that makes this repeatable** (the user's own point, 2026-08-23: "Merk dir die Trailforks
ID der Trails für künftige Updates der Werte"). Matching Finale's 219 trails onto Trailforks cost a full
geometric run and 22 cases that still need a human; with the slug stored, refreshing the NUMBERS later is a
harvest plus a dictionary lookup. It is also what makes a single rating auditable: without it, nobody can
check where a 4,64 came from.

Only `verdict == "match"` rows are used. A review or unmatched trail gets nothing, which is a third state
the app has to render honestly ("noch nicht bewertet"), never a zero.

**`rate` is the Bayesian value on purpose.** Across Madeira's trails 59 % have two votes or fewer, so a raw
star average is noise for most of a region; Trailforks already shrinks toward the regional mean and the job
here is not to undo that. `votes` ships alongside so nothing has to be taken on trust.

The region also gets a `ratings` block of its own:

    "ratings": {"source": "trailforks", "asOf": "2026-08-23", "matched": 131, "trails": 219}

`asOf` matters because nothing synchronises these numbers — same reasoning that keeps lift operating status
out of the data (`docs/lifts-feature.md`), only slower-moving: a star rating drifts over years, a lift
timetable over weeks. Dated, it is honest; undated, it silently ages.
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_trailforks import run as run_match  # noqa: E402
from trailmap_pipeline import write_region  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = os.path.join(ROOT, "Trailmap App", "regions")


def merge_sections(slugs, table):
    """One of our trails against SEVERAL Trailforks sections of it -- the user's own rule (2026-08-24).

    Where Trailforks splits a trail we carry whole, picking one section throws away the votes of the other
    and picks a winner by nothing in particular (Rock'n'Roll: 4,08 from 6 votes against 4,12 from 3). So:

    * the rating is the **vote-weighted mean** -- 6 riders saying 4,08 and 3 saying 4,12 is one trail at
      4,09, which is what those nine riders actually said;
    * the votes are **summed**, because they are nine distinct verdicts;
    * the popularity is the **maximum, not the sum** -- it counts a year of check-ins, and a rider who rides
      the trail logs every section of it, so adding them counts the same rider twice. The busiest section is
      the honest figure for the trail.
    """
    rows = [(table.get(s) or {}) for s in slugs]
    rated = [(r, int(r.get("votes") or 0)) for r in rows if r.get("rating_bayesian")]
    entry = {"slug": list(slugs), "rate": None, "votes": 0, "pop": None}
    pops = [int(r["popularity_score"]) for r in rows if r.get("popularity_score") is not None]
    if pops:
        entry["pop"] = max(pops)
    if rated:
        v = sum(n for _, n in rated)
        entry["rate"] = round(sum(float(r["rating_bayesian"]) * n for r, n in rated) / max(v, 1), 2)
        entry["votes"] = v
    return entry


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("region")
    ap.add_argument("--material", required=True)
    ap.add_argument("--table", default="trailforks_table.json",
                    help="where the numbers live under --material; the regions harvested before this "
                         "pipeline keep theirs in tf_ratings.json, since their harvest kept no table")
    ap.add_argument("--report", help="reuse an existing match report instead of recomputing")
    ap.add_argument("--mapping", help="a {trailId: slug} map from tools/map_tf_slugs.py -- used INSTEAD of "
                                      "the fuzzy matcher, for a region built from Trailforks")
    ap.add_argument("--as-of", required=True, help="harvest date, YYYY-MM-DD -- see the module docstring")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.mapping:
        # A region built FROM Trailforks needs no inference: map_tf_slugs.py resolves our id back to the
        # slug it was built from and checks the endpoints, so every row here is a "match" by construction.
        mp = json.load(io.open(a.mapping, encoding="utf-8"))
        mp = mp.get("mapping", mp)
        rows = [{"id": tid, "verdict": "match", "candidates": [{"slug": slug}]} for tid, slug in mp.items()]
        print("Zuordnung uebernommen: %s (%d Trails)" % (a.mapping, len(rows)))
    elif a.report and os.path.exists(a.report):
        rows = json.load(io.open(a.report, encoding="utf-8"))
        print("Bericht wiederverwendet: %s" % a.report)
    else:
        rows, _ = run_match(a.region, a.material)

    mat = a.material if os.path.isabs(a.material) else os.path.join(ROOT, "Material", a.material)
    table = json.load(io.open(os.path.join(mat, a.table), encoding="utf-8"))
    by_id = {}
    for r in rows:
        if r["verdict"] != "match" or not r["candidates"]:
            continue
        slug = r["candidates"][0]["slug"]
        if isinstance(slug, list):
            by_id[r["id"]] = merge_sections(slug, table)
            continue
        t = table.get(slug) or {}
        # The SLUG is written for every resolved trail, rated or not (fixed 2026-08-24, the user asked
        # whether every trail had kept its id -- 1 428 mapped trails had not). A trail Trailforks knows but
        # nobody has voted on yet is the case this matters most for: the mapping is the expensive half and it
        # does not expire, while the votes arrive later. Without the slug, the next refresh would have to
        # re-derive that mapping from scratch -- and for a region where our geometry is an operator's own
        # recording, "from scratch" means the fuzzy matcher and another round of review cases.
        entry = {"slug": slug, "rate": None, "votes": 0, "pop": None}
        if t.get("rating_bayesian"):
            entry["rate"] = round(float(t["rating_bayesian"]), 2)
            entry["votes"] = int(t.get("votes") or 0)
            entry["pop"] = int(t["popularity_score"]) if t.get("popularity_score") is not None else None
        by_id[r["id"]] = entry

    path = os.path.join(REGIONS, a.region + ".json")
    data = json.load(io.open(path, encoding="utf-8"))
    applied = mapped = 0
    for t in data["lineTrails"]:
        for k in ("rate", "votes", "pop", "tf"):
            t.pop(k, None)
        v = by_id.get(t["id"])
        if not v:
            continue
        t["tf"] = v["slug"]
        mapped += 1
        if v["rate"] is None or not v["votes"]:
            continue
        t["rate"] = v["rate"]
        t["votes"] = v["votes"]
        if v["pop"] is not None:
            t["pop"] = v["pop"]
        applied += 1

    rated = [t for t in data["lineTrails"] if t.get("rate")]
    print("%s: %d von %d Trails mit Bewertung (%.0f %%), %d mit gespeicherter Trailforks-ID"
          % (a.region, applied, len(data["lineTrails"]), 100.0 * applied / len(data["lineTrails"]), mapped))
    if rated:
        best = sorted(rated, key=lambda t: -t["rate"])[:3]
        print("  Beste: " + ", ".join("%s %.2f (%d Stimmen)" % (t["name"], t["rate"], t["votes"])
                                      for t in best))
    if a.dry_run:
        print("--dry-run: nichts geschrieben")
        return 0
    write_region(path, data["lineTrails"], data["trailGeo"], data["elevationProfiles"],
                 places=data.get("places"), lifts=data.get("lifts"),
                 trail_segments=data.get("trailSegments"),
                 ratings={"source": "trailforks", "asOf": a.as_of,
                          "matched": applied, "trails": len(data["lineTrails"])})
    print("geschrieben: %s" % os.path.basename(path))
    print("weiter: python tools/validate_region.py %s && python tools/update_region_versions.py" % a.region)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
