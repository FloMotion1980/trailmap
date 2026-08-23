# -*- coding: utf-8 -*-
"""Merge one harvested Trailforks table into another, without losing a rating either side has.

    python tools/merge_tf_tables.py "Material/Harz" --from tf_ratings.json --into trailforks_table.json

A region can end up with two tables when it was harvested twice by different means -- the Harz has a
month-old geometry-only harvest plus a fresh table, the Pfälzerwald the same. The apply step reads ONE
table, so the numbers have to sit together first.

Rows are merged per slug and per FIELD: a row that exists on both sides keeps whichever value is present,
so a fresh row with a name and a difficulty gains the rating an older run had already fetched. `_norate`
is dropped whenever the other side has a real rating -- it means "asked, no votes", and that can stop being
true.
"""
import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--into", dest="dst", required=True)
    a = ap.parse_args(argv)
    d = a.dir if os.path.isabs(a.dir) else os.path.join(ROOT, a.dir)
    src = json.load(io.open(os.path.join(d, a.src), encoding="utf-8"))
    dp = os.path.join(d, a.dst)
    dst = json.load(io.open(dp, encoding="utf-8")) if os.path.exists(dp) else {}
    new = filled = 0
    for slug, row in src.items():
        if slug not in dst:
            dst[slug] = dict(row)
            new += 1
            continue
        for k, v in row.items():
            if v is not None and dst[slug].get(k) in (None, ""):
                dst[slug][k] = v
                filled += 1
        if dst[slug].get("rating_bayesian"):
            dst[slug].pop("_norate", None)
    json.dump(dst, io.open(dp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    rated = sum(1 for r in dst.values() if r.get("rating_bayesian"))
    print("%s: %d Zeilen (%d neu, %d Felder ergaenzt), %d mit Bewertung"
          % (a.dst, len(dst), new, filled, rated))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
