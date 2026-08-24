# -*- coding: utf-8 -*-
"""Print the fuzzy matcher's `review` cases with all the evidence, so a human can decide them.

    python tools/review_cases.py paznaun --material Paznaun
    python tools/review_cases.py harz --material Harz --geo harz_tf_geo.json,trailforks_geo.json

One line per open case: our trail, the best candidate, and the four signals the verdict is made of --
geometric coverage, name similarity, length ratio and endpoint gap -- plus what the candidate would
contribute (rating, votes, popularity) and how far the runner-up is behind. That last column is what makes
a case decidable at all: a lone candidate at 0,68 coverage is a different question from two at 0,68.
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_trailforks import run as run_match  # noqa: E402
from trailmap_pipeline import haversine_m  # noqa: E402

#: A line counts as "lying on ours" at this share of ITS points within 25 m of OUR line. Deliberately not
#: the other direction: Trailforks splits trails, so the interesting relationship is a short line of theirs
#: sitting inside a long one of ours -- which scores near 1.00 this way round and near 0.10 the other.
ON_LINE = 0.60


def lines_on_ours(coords, tf_geo, table):
    """Every Trailforks line lying on one of our trails, with what it would contribute.

    This is the view that actually decides a case, and the top-candidate list is not: a trail our line
    passes over scores 1.00 on containment, so the ranking fills up with neighbours while the section that
    carries our own name sits below the cut. Bike Kingdom's Medergen Trail was decided by exactly this --
    none of Trailforks' five "Medergen" lines is on it, and "Tiejer Wald" is.
    """
    out = []
    for slug, g in tf_geo.items():
        line = g.get("c") or ([[p[2], p[3]] for p in g["p"]] if g.get("p") else None)
        if not line or len(line) < 2:
            continue
        near = sum(1 for p in line if min(haversine_m(p, q) for q in coords) <= 25.0) / float(len(line))
        if near >= ON_LINE:
            row = table.get(slug, {})
            out.append({"slug": slug, "name": row.get("name"), "on_ours": round(near, 2),
                        "m": row.get("m"), "rate": row.get("rating_bayesian"), "votes": row.get("votes"),
                        "diff": row.get("diff"),
                        "len_m": round(sum(haversine_m(line[i], line[i + 1]) for i in range(len(line) - 1)))})
    return sorted(out, key=lambda x: -x["on_ours"])

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("region")
    ap.add_argument("--material", required=True)
    ap.add_argument("--json")
    ap.add_argument("--sections", action="store_true",
                    help="fuer jeden offenen Fall auch jede Trailforks-Linie zeigen, die auf unserer liegt")
    a = ap.parse_args(argv)
    mat = a.material if os.path.isabs(a.material) else os.path.join(ROOT, "Material", a.material)
    rows, _ = run_match(a.region, mat)
    table = json.load(io.open(os.path.join(mat, "trailforks_table.json"), encoding="utf-8"))
    region = tf_geo = None
    if a.sections:
        region = json.load(io.open(os.path.join(ROOT, "Trailmap App", "regions", a.region + ".json"),
                                   encoding="utf-8"))
        tf_geo = json.load(io.open(os.path.join(mat, "trailforks_geo.json"), encoding="utf-8"))
    # Decided cases drop out here rather than being reported again. The matcher runs a stage earlier than
    # the decisions and cannot know about them, so filtering belongs in the report -- otherwise the pile
    # never shrinks as we work through it, which is exactly what it looked like after the first session.
    decided = {}
    mp = os.path.join(mat, "tf_manual.json")
    if os.path.exists(mp):
        decided = json.load(io.open(mp, encoding="utf-8"))
    open_rows = [r for r in rows if r["verdict"] == "review" and r["id"] not in decided]
    if decided:
        # Beide Formen zaehlen: eine Handentscheidung kann EINEN Slug tragen oder mehrere ("slugs",
        # der gewichtete Abschnittsfall). Nur nach "slug" zu fragen meldete 14 der 18 Harz-Entscheidungen
        # als "ohne Gegenstueck", obwohl vierzehn davon zugeordnet sind.
        zug = sum(1 for v in decided.values()
                  if ((v.get("slugs") or v.get("slug")) if isinstance(v, dict) else v))
        print("%s: %d Faelle bereits entschieden (%d zugeordnet, %d ohne Gegenstueck)"
              % (a.region, len(decided), zug, len(decided) - zug))
    print("%s: %d Faelle zum Pruefen" % (a.region, len(open_rows)))
    print("%-30s %-42s %5s %5s %5s %6s  %-14s %s"
          % ("unser Trail", "Kandidat (vollstaendig)", "Deck", "Name", "Laen", "Enden", "Bewertung", "Zweiter"))
    out = []
    for r in open_rows:
        c = (r.get("candidates") or [{}])[0]
        second = (r.get("candidates") or [{}, {}])[1] if len(r.get("candidates") or []) > 1 else {}
        t = table.get(c.get("slug"), {})
        rate = ("%.2f/%s St." % (float(t["rating_bayesian"]), t.get("votes"))
                if t.get("rating_bayesian") else "keine")
        print("%-30s %-42s %5.2f %5.2f %5.2f %6s  %-14s %s"
              % (r.get("name", "")[:30], (c.get("slug") or "-"), c.get("geo") or 0,
                 c.get("name_sim") or 0, c.get("len_ratio") or 0, c.get("end_gap_m") or "-", rate,
                 ("%s %.2f" % ((second.get("slug") or "-")[:18], second.get("geo") or 0)) if second else "-"))
        if a.sections:
            for x in lines_on_ours(region["trailGeo"][r["id"]], tf_geo, table):
                print("      %-42s %-24s %5s m  Bew %-6s %-3s  auf uns %.2f  %s"
                      % (x["slug"], (x["name"] or "")[:26], x["len_m"],
                         ("%.2f" % float(x["rate"])) if x["rate"] else "-", x["votes"] or "-",
                         x["on_ours"], (x["diff"] or "")[:20]))
        out.append({"id": r["id"], "name": r.get("name"), "slug": c.get("slug"), "signals": c,
                    "rating": t.get("rating_bayesian"), "votes": t.get("votes"),
                    "pop": t.get("popularity_score"), "why": r.get("why")})
    if a.json:
        json.dump(out, io.open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("geschrieben: %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
