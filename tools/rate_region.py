# -*- coding: utf-8 -*-
"""One command per region: map our trails onto Trailforks, fetch the numbers, write them in.

    python tools/rate_region.py harz --material Harz --geo harz_tf_geo.json --table tf_ratings.json
    python tools/rate_region.py laax --material Laax --seeds laax,flims --fresh

With `--seeds` it harvests the region tree first (table, then one page per trail, which is where both the
geometry and the numbers come from). Without them it works off a harvest that is already on disk, which is
the case for every region this repo built from Trailforks.

The order matters and is the whole reason this file exists: mapping BEFORE fetching would work too, but
fetching first means the mapping can use the geometry that just arrived, and the mapping is what decides
which trails get a rating at all. Every step is resumable -- the harvest skips what it has, the rating pass
skips rows that already carry a number, and the apply step rewrites the region from scratch each time.
"""
import argparse
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def run(args):
    print("$ " + " ".join(args[1:]))
    sys.stdout.flush()
    return subprocess.call([sys.executable] + args[1:], cwd=ROOT)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("region")
    ap.add_argument("--material", required=True)
    ap.add_argument("--seeds", help="comma-separated Trailforks region slugs to harvest first")
    ap.add_argument("--geo", help="harvest file(s) for the mapping; default trailforks_geo.json")
    ap.add_argument("--table", default="trailforks_table.json")
    ap.add_argument("--as-of", default="2026-08-24")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    mat = os.path.join(ROOT, "Material", a.material)
    if a.seeds:
        if run([sys.executable, os.path.join(TOOLS, "harvest_trailforks.py"),
                "--dir", mat, "--seeds", a.seeds, "--tables"]):
            return 1
        if run([sys.executable, os.path.join(TOOLS, "harvest_trailforks.py"), "--dir", mat, "--geo"]):
            return 1
    else:
        cmd = [sys.executable, os.path.join(TOOLS, "harvest_tf_ratings.py"), "--dir", mat,
               "--table", a.table]
        if a.geo:
            cmd += ["--from-geo", a.geo]
        if run(cmd):
            return 1

    mp = os.path.join(mat, "tf_mapping.json")
    cmd = [sys.executable, os.path.join(TOOLS, "map_tf_slugs.py"), a.region,
           "--material", mat, "--json", mp]
    if a.geo:
        cmd += ["--geo", a.geo]
    if run(cmd):
        return 1
    if not json.load(io.open(mp, encoding="utf-8"))["mapping"]:
        print("keine Zuordnung -- nichts zu schreiben")
        return 0
    cmd = [sys.executable, os.path.join(TOOLS, "apply_trailforks_ratings.py"), a.region,
           "--material", mat, "--mapping", mp, "--table", a.table, "--as-of", a.as_of]
    if a.dry_run:
        cmd.append("--dry-run")
    if run(cmd):
        return 1
    if not a.dry_run:
        run([sys.executable, os.path.join(TOOLS, "update_region_versions.py")])
        run([sys.executable, os.path.join(TOOLS, "validate_region.py"), a.region])
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
