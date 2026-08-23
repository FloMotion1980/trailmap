# -*- coding: utf-8 -*-
"""Probe a hand-written list of Trailforks slugs per region and report which ones hold trails.

    python tools/probe_tf_slugs.py hand_seeds.json --out confirmed.json

The companion to `find_tf_regions.py`, which derives its candidates from the names in our own region files.
That covers a region whose Trailforks slug IS one of our place names and misses the rest -- the Harz has
Hahnenklee, Schulenberg and Bodetal areas that our data never names, and Serfaus sits under
`serfaus-fiss-ladis`. Local knowledge is the only source for those, so this takes it as input.

Prints the row count per hit, which is the number worth reading: a slug with 3 rows is a hamlet inside a
region already covered by a bigger seed, and seeding both costs a duplicate pass over the same trails.
"""
import argparse
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_trailforks import fetch  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out")
    ap.add_argument("--sleep", type=float, default=0.3)
    a = ap.parse_args(argv)
    plan = json.load(io.open(a.file, encoding="utf-8"))
    found = {}
    for region, slugs in plan.items():
        hits = []
        for s in slugs:
            html = fetch("https://www.trailforks.com/region/%s/trails/?activitytype=1" % s, tries=1)
            n = len(re.findall(r"trailforks\.com/trails/", html))
            if n:
                hits.append([s, n])
            time.sleep(a.sleep)
        found[region] = hits
        print("%-16s %s" % (region, ", ".join("%s (%d)" % (s, n) for s, n in hits) or "nichts"))
        sys.stdout.flush()
        if a.out:
            json.dump(found, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
