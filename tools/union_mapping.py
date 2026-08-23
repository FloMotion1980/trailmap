# -*- coding: utf-8 -*-
"""Combine the strict slug mapping with the fuzzy matcher, and write one mapping the apply step can use.

    python tools/union_mapping.py bikekingdom --material BikeKingdom

The two tools answer different questions and a region can need both. `map_tf_slugs.py` asks "is this the
same LINE" and is right for a region built from Trailforks; `match_trailforks.py` asks "is this the same
TRAIL, recorded twice" -- four signals plus a margin rule -- and is the only one that can work where our
geometry came from an operator's GPX or from OSM. Bike Kingdom is the case that forced this: 4 of 117 trails
matched strictly, because its lines are the operator's own recordings.

The strict mapping WINS on a trail both claim: it is an identity, not an inference. The fuzzy matcher only
fills the gaps, and only its `match` verdicts -- a `review` row is exactly the case a human still has to
look at, so attaching a rating to it would be the silent guess this whole pipeline avoids.
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_trailforks import run as run_match  # noqa: E402
from map_tf_slugs import run as run_strict  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("region")
    ap.add_argument("--material", required=True)
    ap.add_argument("--geo")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    mat = a.material if os.path.isabs(a.material) else os.path.join(ROOT, "Material", a.material)

    strict, _ = run_strict(a.region, mat, a.geo.split(",") if a.geo else None)
    try:
        rows, _ = run_match(a.region, mat)
    except Exception as exc:                      # a region with no usable table is not a failure here
        print("Fuzzy-Abgleich nicht moeglich: %s" % exc)
        rows = []
    added = 0
    taken = set(strict.values())
    for r in rows:
        if r.get("verdict") != "match" or not r.get("candidates"):
            continue
        tid, slug = r["id"], r["candidates"][0]["slug"]
        if tid in strict or slug in taken:
            continue
        strict[tid] = slug
        taken.add(slug)
        added += 1
    print("%s: %d streng + %d unscharf = %d Zuordnungen" % (a.region, len(strict) - added, added, len(strict)))
    out = a.out or os.path.join(mat, "tf_mapping_union.json")
    json.dump({"mapping": strict}, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("geschrieben: %s" % out)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
