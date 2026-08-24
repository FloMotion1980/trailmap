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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("region")
    ap.add_argument("--material", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    mat = a.material if os.path.isabs(a.material) else os.path.join(ROOT, "Material", a.material)
    rows, _ = run_match(a.region, mat)
    table = json.load(io.open(os.path.join(mat, "trailforks_table.json"), encoding="utf-8"))
    # Decided cases drop out here rather than being reported again. The matcher runs a stage earlier than
    # the decisions and cannot know about them, so filtering belongs in the report -- otherwise the pile
    # never shrinks as we work through it, which is exactly what it looked like after the first session.
    decided = {}
    mp = os.path.join(mat, "tf_manual.json")
    if os.path.exists(mp):
        decided = json.load(io.open(mp, encoding="utf-8"))
    open_rows = [r for r in rows if r["verdict"] == "review" and r["id"] not in decided]
    if decided:
        zug = sum(1 for v in decided.values() if (v.get("slug") if isinstance(v, dict) else v))
        print("%s: %d Faelle bereits entschieden (%d zugeordnet, %d ohne Gegenstueck)"
              % (a.region, len(decided), zug, len(decided) - zug))
    print("%s: %d Faelle zum Pruefen" % (a.region, len(open_rows)))
    print("%-30s %-28s %5s %5s %5s %6s  %-14s %s"
          % ("unser Trail", "Kandidat", "Deck", "Name", "Laen", "Enden", "Bewertung", "Zweiter"))
    out = []
    for r in open_rows:
        c = (r.get("candidates") or [{}])[0]
        second = (r.get("candidates") or [{}, {}])[1] if len(r.get("candidates") or []) > 1 else {}
        t = table.get(c.get("slug"), {})
        rate = ("%.2f/%s St." % (float(t["rating_bayesian"]), t.get("votes"))
                if t.get("rating_bayesian") else "keine")
        print("%-30s %-28s %5.2f %5.2f %5.2f %6s  %-14s %s"
              % (r.get("name", "")[:30], (c.get("slug") or "-")[:28], c.get("geo") or 0,
                 c.get("name_sim") or 0, c.get("len_ratio") or 0, c.get("end_gap_m") or "-", rate,
                 ("%s %.2f" % ((second.get("slug") or "-")[:18], second.get("geo") or 0)) if second else "-"))
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
