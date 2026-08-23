# -*- coding: utf-8 -*-
"""Harvest, map and apply Trailforks ratings for every region that has no harvest yet.

    python tools/phase_b_run.py --seeds seeds_merged.json --order varazze,bikekingdom,...
    python tools/phase_b_run.py --seeds seeds_merged.json --only harz

One region at a time, on purpose: each is a table harvest plus one page per trail, and three concurrent
streams against Trailforks already produced occasional empty bodies (which `harvest_tf_ratings.py` now
refuses to record as "unrated"). Sequential also means a failure stops after one region rather than half of
them.

Every step is resumable, so re-running this after an interruption costs only the pages that never arrived.
The per-region Material directory is created here and keeps the harvest, exactly as the Gardasee, Madeira,
Schwarzwald and Vogesen ones do -- the geometry is what makes the mapping checkable later, and what a future
expansion of that region would start from.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
#: Which Material directory a region key harvests into. Only the ones whose name is not the key's own
#: capitalisation need an entry, but they are all listed so a typo shows up here rather than as a stray dir.
MATERIAL = {
    "varazze": "Varazze", "bikekingdom": "BikeKingdom", "portesdusoleil": "Portes du Soleil",
    "sauerland": "Sauerland-Upland", "odenwald": "Odenwald", "bikecircus": "Saalbach",
    "harz": "Harz", "donnersberg": "Donnersberg", "soelden": "Sölden", "livigno": "Livigno",
    "schladming": "Schladming", "dreilaender": "3-Laender-Enduro-Trails", "paganella": "Paganella",
    "paznaun": "Paznaun", "laax": "Laax", "saarland": "Saarpfalz-PUR", "waldmeister": "Waldmeister",
    "naheland": "Naheland", "serfaus": "Serfaus", "zugspitzarena": "Zugspitzarena",
    "brandnertal": "Brandnertal", "pfaelzerwald": "Pfälzer Wald",
}


def run(args, label):
    print("\n=== %s: %s" % (label, " ".join(os.path.basename(a) for a in args[1:4])))
    sys.stdout.flush()
    return subprocess.call([sys.executable] + args[1:], cwd=ROOT)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--order", help="comma-separated region keys; default every key in the seed file")
    ap.add_argument("--only")
    ap.add_argument("--as-of", default="2026-08-24")
    ap.add_argument("--union-only", action="store_true",
                    help="nichts ernten: nur streng+unscharf zusammenfuehren und schreiben. Der zweite "
                         "Durchgang, nachdem die Ernte einmal durch ist -- der unscharfe Abgleich braucht "
                         "die Geometrie, die die Ernte erst gebracht hat.")
    a = ap.parse_args(argv)
    seeds = json.load(io.open(a.seeds, encoding="utf-8"))
    order = [k for k in (a.order.split(",") if a.order else sorted(seeds)) if k in seeds]
    if a.only:
        order = [k for k in order if k == a.only]

    for key in order:
        mat = os.path.join(ROOT, "Material", MATERIAL.get(key, key.capitalize()))
        if not os.path.isdir(mat):
            os.makedirs(mat)
        slugs = ",".join(s for s, _ in seeds[key])
        t0 = time.time()
        print("\n" + "#" * 90)
        print("# %s  <-  %s" % (key, slugs))
        sys.stdout.flush()
        if not a.union_only:
            if run([sys.executable, os.path.join(TOOLS, "harvest_trailforks.py"),
                    "--dir", mat, "--seeds", slugs, "--tables"], key + " Tabelle"):
                print("!! Tabelle fehlgeschlagen, Region uebersprungen")
                continue
            if run([sys.executable, os.path.join(TOOLS, "harvest_trailforks.py"),
                    "--dir", mat, "--geo", "--sleep", "0.5"], key + " Seiten"):
                print("!! Seiten fehlgeschlagen, weiter mit dem, was da ist")
        mp = os.path.join(mat, "tf_mapping_union.json" if a.union_only else "tf_mapping.json")
        tool = "union_mapping.py" if a.union_only else "map_tf_slugs.py"
        if run([sys.executable, os.path.join(TOOLS, tool), key,
                "--material", mat, "--out" if a.union_only else "--json", mp], key + " Zuordnung"):
            continue
        if not json.load(io.open(mp, encoding="utf-8"))["mapping"]:
            print("keine Zuordnung -- nichts zu schreiben")
            continue
        run([sys.executable, os.path.join(TOOLS, "apply_trailforks_ratings.py"), key,
             "--material", mat, "--mapping", mp, "--as-of", a.as_of], key + " schreiben")
        run([sys.executable, os.path.join(TOOLS, "update_region_versions.py")], key + " Manifest")
        run([sys.executable, os.path.join(TOOLS, "validate_region.py"), key], key + " Pruefung")
        print("# %s fertig in %.0f s" % (key, time.time() - t0))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
