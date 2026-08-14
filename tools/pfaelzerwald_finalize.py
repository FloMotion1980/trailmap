# -*- coding: utf-8 -*-
"""Phase 5 of the Pfälzerwald rework: drop the late-found duplicates and check the result is publishable.

    python tools/pfaelzerwald_finalize.py --in  Material/…/pfaelzerwald.rederived.json \
                                          --out Material/…/pfaelzerwald.final.json

Two jobs, both of which have to happen after the loop re-derivation rather than before it.

**Dropping the five Deidesheim duplicates.** They were found only after Phase 3 had already produced the
merged file that Phase 4 then spent hours re-deriving loops against, and re-running the integration from
scratch would have thrown that away for five entries. Removing them afterwards is safe only if no loop
attributes any of its length to them, which is exactly what this checks -- and refuses to write if it is not
true, rather than leaving a segment pointing at a trail that no longer exists. `SKIP_SLUGS` in
pfaelzerwald_integrate.py is the permanent fix; this is the one-off repair of an already-built file.

**Verifying the invariants that make a region publishable at all.** `validate_region.py` runs against the
live regions folder, so it cannot see a candidate file. The checks here are the ones that would otherwise
only fail after the file was already in place: every trail has geometry and a profile and vice versa, every
sub-region a trail claims is one the catalog will declare, no `url` field crept back in, and -- the one that
matters most for this rework -- `trailGeo[loopId]` is still the exact concatenation of that loop's segments,
so the drawn line is provably unchanged from what the user already knows.
"""
import argparse
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfaelzerwald_integrate import SKIP_SLUGS, trail_id
from trailmap_pipeline import write_region

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: Sub-regions the catalog will declare after this rework. A trail claiming anything else is a build error.
EXPECTED_SUBS = {"johanniskreuz", "weinstrasse", "wasgau", "kurztouren", "fernwege_felsentouren",
                 "private_runden", "naturtrail_deidesheim", "haardt", "bienwald"}


def _utf8_stdout():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def main():
    _utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    d = json.load(open(args.src, encoding="utf-8"))
    trails, geo, profs = d["lineTrails"], d["trailGeo"], d["elevationProfiles"]
    segs = d.get("trailSegments", {})

    # --- 1. the five duplicates -----------------------------------------------------------------
    drop = {trail_id(s) for s in SKIP_SLUGS} & {t["id"] for t in trails}
    referencing = collections.defaultdict(list)
    for lid, ss in segs.items():
        for s in ss:
            if s.get("trailId") in drop:
                referencing[s["trailId"]].append(lid)
    print("Dubletten im Eingabefile: %d" % len(drop))
    for tid in sorted(drop):
        print("   %-58s referenziert von: %s" % (tid[:58], referencing.get(tid) or "keiner Runde"))
    if referencing:
        raise SystemExit("ABBRUCH: %d Dublette(n) sind Rundenkomponenten -- diese Runden muessen neu "
                         "hergeleitet werden, bevor die Trails entfernt werden duerfen" % len(referencing))
    trails = [t for t in trails if t["id"] not in drop]
    for tid in drop:
        geo.pop(tid, None)
        profs.pop(tid, None)

    # --- 2. publishability ----------------------------------------------------------------------
    ids = {t["id"] for t in trails}
    problems = []
    if ids - set(geo):
        problems.append("Trails ohne Geometrie: %s" % sorted(ids - set(geo))[:5])
    if ids - set(profs):
        problems.append("Trails ohne Profil: %s" % sorted(ids - set(profs))[:5])
    if set(geo) - ids:
        problems.append("Geometrie-Waisen: %s" % sorted(set(geo) - ids)[:5])
    if set(profs) - ids:
        problems.append("Profil-Waisen: %s" % sorted(set(profs) - ids)[:5])
    bad_sub = sorted({t["region"] for t in trails} - EXPECTED_SUBS)
    if bad_sub:
        problems.append("unbekannte Sub-Regionen: %s" % bad_sub)
    unused = sorted(EXPECTED_SUBS - {t["region"] for t in trails})
    if unused:
        problems.append("deklarierte, aber leere Sub-Regionen: %s" % unused)
    if any("url" in t for t in trails):
        problems.append("das entfernte url-Feld ist zurueck")
    stale = {s["trailId"] for ss in segs.values() for s in ss if s.get("trailId")} - ids
    if stale:
        problems.append("Segmente zeigen auf %d nicht mehr existierende Trails: %s"
                        % (len(stale), sorted(stale)[:5]))
    broken = [lid for lid, ss in segs.items()
              if [p for s in ss for p in s["coords"]] != geo.get(lid)]
    if broken:
        problems.append("Verkettungs-Invariant verletzt bei: %s" % broken[:5])

    print()
    print("Trails: %d   Sub-Regionen: %s" % (len(trails), dict(collections.Counter(
        t["region"] for t in trails))))
    print("Schwierigkeiten: %s" % dict(collections.Counter(t["diff"] for t in trails)))
    print("Trailrunden mit Segmenten: %d   Verkettung exakt: %s"
          % (len(segs), "ja" if not broken else "NEIN"))
    if problems:
        print()
        for p in problems:
            print("   PROBLEM: %s" % p)
        raise SystemExit("nicht veroeffentlichungsfaehig -- %d Problem(e)" % len(problems))
    print("alle Invarianten erfuellt")

    if args.out:
        write_region(args.out, trails, geo, profs, places=d.get("places"), lifts=d.get("lifts"),
                     trail_segments=segs)
        print("geschrieben: %s" % args.out)


if __name__ == "__main__":
    main()
