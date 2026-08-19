# -*- coding: utf-8 -*-
"""Cross-region duplicate check: does a region share real ground with any other region we ship?

    python tools/region_dupe_check.py nordvogesen                 # against every other region
    python tools/region_dupe_check.py suedvogesen nordvogesen     # against named regions only

Why this is not optional. Region bounding boxes are allowed to touch, and two of them genuinely do:
the Vosges du Nord and the Pfälzerwald are the SAME forest massif either side of the German/French
border (one UNESCO cross-border biosphere reserve), and `pfaelzerwald.json` already reaches south to
lat 49.024 -- past Wissembourg's own latitude. A trail around Cleebourg or Nothweiler can therefore be
the same ground as a Wasgau or Bienwald entry we already ship, under a different name from a different
source. The same applies to any two regions built from different sources in one massif.

The metric is the one the project already settled on (see `trailforks-duplicate-detection-method` and
`tools/pfaelzerwald_containment.py`, whose functions this reuses rather than re-deriving): directional
containment of the SHORTER line in the LONGER one, plus the per-point distance SHAPE, because the
aggregate fraction alone cannot tell a real duplicate from two trails sharing a trailhead. A
bounding-box pre-filter keeps a full pairwise scan cheap even at 900 trails a side.

Reports only -- it deletes nothing. Which of a duplicate pair to keep is the user's call, and a pair
whose older half is referenced by a Trailrunde's `TRAIL_SEGMENTS` cannot simply be dropped anyway (the
repointing logic for that does not exist yet).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfaelzerwald_containment import bbox, bbox_overlaps, dist_profile, line_len_m, profile_shape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = os.path.join(ROOT, "Trailmap App", "regions")

#: Padding on the bounding-box pre-filter, in degrees (~300 m), same as the in-region scan uses.
BBOX_PAD = 0.003
#: Report from here up; the in-region tool treats >0.60-0.70 as a duplicate, and the band below that is
#: exactly what needs a human look rather than a threshold.
REPORT_FROM = 0.35
#: A point this close to the other line counts as "on" it.
TOL_M = 20.0


def load(key):
    d = json.load(open(os.path.join(REGIONS, key + ".json"), encoding="utf-8"))
    return d["trailGeo"], {t["id"]: t["name"] for t in d["lineTrails"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("region")
    ap.add_argument("others", nargs="*")
    a = ap.parse_args()

    others = a.others or sorted(
        f[:-5] for f in os.listdir(REGIONS)
        if f.endswith(".json") and f != "version.json" and f[:-5] != a.region)

    new_geo, new_names = load(a.region)
    new_bb = {i: bbox(c, BBOX_PAD) for i, c in new_geo.items()}
    hits = []
    for other in others:
        if not os.path.exists(os.path.join(REGIONS, other + ".json")):
            print("skip %s (no file)" % other)
            continue
        old_geo, old_names = load(other)
        pairs = 0
        for oid, oc in old_geo.items():
            if len(oc) < 2:
                continue
            ob = bbox(oc, BBOX_PAD)
            for nid, nc in new_geo.items():
                if len(nc) < 2 or not bbox_overlaps(ob, new_bb[nid]):
                    continue
                pairs += 1
                short, long_ = (nc, oc) if line_len_m(nc) <= line_len_m(oc) else (oc, nc)
                prof = dist_profile(short, long_)
                if not prof:
                    continue
                frac = sum(1 for d in prof if d <= TOL_M) / float(len(prof))
                if frac >= REPORT_FROM:
                    hits.append((frac, profile_shape(prof), other, oid, old_names.get(oid, "?"),
                                 nid, new_names.get(nid, "?"), round(line_len_m(nc)),
                                 round(line_len_m(oc))))
        if pairs:
            print("%-16s %d bbox-overlapping pairs compared" % (other, pairs))

    hits.sort(reverse=True)
    print("\n%d pair(s) at or above %.0f%% containment:" % (len(hits), REPORT_FROM * 100))
    for frac, shape, other, oid, oname, nid, nname, nlen, olen in hits[:60]:
        print("  %5.1f%% %-9s  %s %-32s %5dm  <->  %s %-32s %5dm  (%s)"
              % (frac * 100, shape, a.region[:4], nname[:32], nlen, other[:4], oname[:32], olen, oid))
    if not hits:
        print("  none -- no shared ground found")


if __name__ == "__main__":
    main()
