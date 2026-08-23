# -*- coding: utf-8 -*-
"""Merge the two seed probes into one per-region seed list, and print the commands to run.

    python tools/phase_b_seeds.py --auto tf_seeds.json --hand hand_hits.json --out seeds_merged.json

`find_tf_regions.py` derives candidates from the names in our own region files; `probe_tf_slugs.py` takes a
hand-written list for the areas our data never names. Neither is a superset of the other -- Laax is only in
the hand list (its trails sit under `graubunden`), while the Odenwald's `amorbach` and `momlingen` only came
out of the automatic pass -- so the seed list is the union.

Every hit is kept, however few rows it has. A seed that duplicates another's trails costs one extra table
page and nothing else, because the harvester dedupes by slug; a seed left out costs the trails only it
covers.
"""
import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", required=True)
    ap.add_argument("--hand", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    auto = json.load(io.open(a.auto, encoding="utf-8"))
    hand = json.load(io.open(a.hand, encoding="utf-8"))
    merged = {}
    for src in (auto, hand):
        for region, hits in src.items():
            for hit in hits:
                slug, n = (hit[0], hit[1]) if isinstance(hit, (list, tuple)) else (hit, 0)
                merged.setdefault(region, {})
                merged[region][slug] = max(n, merged[region].get(slug, 0))
    out = {r: sorted(d.items(), key=lambda kv: -kv[1]) for r, d in merged.items()}
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    total = 0
    for r, hits in sorted(out.items(), key=lambda kv: -sum(n for _, n in kv[1])):
        rows = sum(n for _, n in hits)
        total += rows
        print("%-16s %5d Zeilen  %s" % (r, rows, ",".join(s for s, _ in hits)))
    print("%-16s %5d Zeilen in %d Regionen" % ("SUMME", total, len(out)))
    print("geschrieben: %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
