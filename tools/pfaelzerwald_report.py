# -*- coding: utf-8 -*-
"""Baseline / after-report for the Pfälzerwald Trailforks rework.

    python tools/pfaelzerwald_report.py                       # report the current region file
    python tools/pfaelzerwald_report.py --out baseline.json    # and save it for later diffing
    python tools/pfaelzerwald_report.py --diff baseline.json   # compare the current file against a saved one

The rework replaces long OSM-hiking-relation trails with Trailforks' individually-named descents, and
re-derives every Trailrunde's `trailSegments` from its own stored line. "Did it get better" cannot be read
off a trail count, so this measures the three things that actually should move:

1. **Attributed share per Trailrunde** — the fraction of each loop's length that falls on a NAMED component
   trail rather than an anonymous connector. This is the core number and it must go UP: the whole point of
   the Trailforks trails is that they name ground the OSM chains left as connector. It is also the number
   that would silently drop if the segment re-derivation lost attribution, which is the main risk in the
   rework.
2. **Difficulty distribution** — the current file has 319 of 437 trails on `blau` and just 2 on `schwarz`,
   which came from OSM rather than from riders and cannot be right for this region.
3. **Trail inventory** — counts per sub-region, plus total named trail length, so a reconciliation that
   deletes more than it adds is visible rather than implied.

The loop invariant (`trailGeo[loopId]` == exact concatenation of its `trailSegments`) is asserted here too,
because every number in section 1 is meaningless if it does not hold.
"""
import argparse
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import haversine_m

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = os.path.join(ROOT, "Trailmap App", "regions", "pfaelzerwald.json")
DIFFS = ["gruen", "blau", "rot", "schwarz"]


def line_len_m(coords):
    return sum(haversine_m(coords[i - 1], coords[i]) for i in range(1, len(coords)))


def measure(path=REGION):
    d = json.load(open(path, encoding="utf-8"))
    trails = d["lineTrails"]
    geo = d["trailGeo"]
    segs = d.get("trailSegments", {})

    by_id = {t["id"]: t for t in trails}
    loops = [t for t in trails if t.get("loop")]

    # --- invariant first: every number below depends on it -------------------------------------
    broken = [lid for lid, ss in segs.items()
              if [p for s in ss for p in s["coords"]] != geo.get(lid)]

    # --- 1. attributed share per loop ----------------------------------------------------------
    loop_rows = []
    for t in sorted(loops, key=lambda x: (x["region"], x["name"])):
        ss = segs.get(t["id"])
        total = line_len_m(geo[t["id"]])
        if not ss:
            loop_rows.append({"id": t["id"], "name": t["name"], "region": t["region"],
                              "total_m": round(total), "named_m": 0, "share": 0.0,
                              "components": 0, "segments": 0, "no_breakdown": True})
            continue
        named = sum(line_len_m(s["coords"]) for s in ss if s.get("trailId"))
        comps = {s["trailId"] for s in ss if s.get("trailId")}
        loop_rows.append({"id": t["id"], "name": t["name"], "region": t["region"],
                          "total_m": round(total), "named_m": round(named),
                          "share": round(named / total, 4) if total else 0.0,
                          "components": len(comps), "segments": len(ss), "no_breakdown": False})

    with_bd = [r for r in loop_rows if not r["no_breakdown"]]
    tot_len = sum(r["total_m"] for r in with_bd)
    tot_named = sum(r["named_m"] for r in with_bd)

    # --- 2 + 3. inventory ----------------------------------------------------------------------
    plain = [t for t in trails if not t.get("loop")]
    referenced = {s["trailId"] for ss in segs.values() for s in ss if s.get("trailId")}

    return {
        "file": os.path.basename(path),
        "trails_total": len(trails),
        "trails_plain": len(plain),
        "loops": len(loops),
        "loops_with_breakdown": len(with_bd),
        "invariant_broken": broken,
        "per_subregion": dict(collections.Counter(t["region"] for t in trails)),
        "per_diff": {k: sum(1 for t in trails if t["diff"] == k) for k in DIFFS},
        "per_diff_plain": {k: sum(1 for t in plain if t["diff"] == k) for k in DIFFS},
        "plain_trail_km": round(sum(line_len_m(geo[t["id"]]) for t in plain) / 1000, 1),
        "components_referenced": len(referenced),
        "plain_trails_never_used_by_a_loop": len([t for t in plain if t["id"] not in referenced]),
        "attributed_share_overall": round(tot_named / tot_len, 4) if tot_len else 0.0,
        "loop_km_total": round(tot_len / 1000, 1),
        "loop_km_named": round(tot_named / 1000, 1),
        "loops": loop_rows,
        "places": len(d.get("places", [])),
    }


def show(m):
    print("== %s" % m["file"])
    print("   trails %d  (%d einzeln, %d Trailrunden, %d davon mit Segment-Aufschlüsselung)"
          % (m["trails_total"], m["trails_plain"], len(m["loops"]), m["loops_with_breakdown"]))
    print("   Verkettungs-Invariant verletzt: %s" % (m["invariant_broken"] or "nein"))
    print("   Schwierigkeiten (alle):     %s" % m["per_diff"])
    print("   Schwierigkeiten (einzeln):  %s" % m["per_diff_plain"])
    print("   Sub-Regionen: %s" % m["per_subregion"])
    print("   Einzeltrail-Länge gesamt: %.1f km" % m["plain_trail_km"])
    print("   von Runden referenzierte Komponenten: %d   nie von einer Runde genutzt: %d"
          % (m["components_referenced"], m["plain_trails_never_used_by_a_loop"]))
    print()
    print("   ZUGEORDNETER ANTEIL der Trailrunden: %.1f%%  (%.1f von %.1f km auf benannten Trails)"
          % (100 * m["attributed_share_overall"], m["loop_km_named"], m["loop_km_total"]))
    print()
    print("   %-38s %-22s %7s %7s %6s %5s" % ("Trailrunde", "Sub-Region", "km", "benannt", "Anteil", "Komp"))
    for r in m["loops"]:
        flag = "  <- keine Aufschlüsselung" if r["no_breakdown"] else ""
        print("   %-38s %-22s %7.2f %7.2f %5.1f%% %5d%s"
              % (r["name"][:38], r["region"], r["total_m"] / 1000, r["named_m"] / 1000,
                 100 * r["share"], r["components"], flag))


def diff(before, after):
    print("== Vergleich  %s -> %s" % (before["file"], after["file"]))
    for key, label, pct in [("trails_total", "Trails gesamt", False),
                            ("trails_plain", "Einzeltrails", False),
                            ("plain_trail_km", "Einzeltrail-km", False),
                            ("components_referenced", "referenzierte Komponenten", False),
                            ("attributed_share_overall", "ZUGEORDNETER ANTEIL", True)]:
        b, a = before[key], after[key]
        if pct:
            print("   %-28s %6.1f%% -> %6.1f%%   %+.1f Punkte"
                  % (label, 100 * b, 100 * a, 100 * (a - b)))
        else:
            print("   %-28s %8s -> %8s   %+g" % (label, b, a, a - b))
    print("   Schwierigkeiten  %s -> %s" % (before["per_diff"], after["per_diff"]))
    if after["invariant_broken"]:
        print("   !! Verkettungs-Invariant verletzt bei: %s" % after["invariant_broken"])

    bl = {r["id"]: r for r in before["loops"]}
    print()
    print("   Trailrunden mit gesunkenem Anteil (das wären Regressionen):")
    worse = []
    for r in after["loops"]:
        b = bl.get(r["id"])
        if b and r["share"] < b["share"] - 0.005:
            worse.append((r["share"] - b["share"], r["name"], b["share"], r["share"]))
    if not worse:
        print("      keine")
    for d_, name, bs, as_ in sorted(worse):
        print("      %-40s %5.1f%% -> %5.1f%%  (%+.1f)" % (name[:40], 100 * bs, 100 * as_, 100 * d_))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--diff", metavar="BASELINE_JSON")
    ap.add_argument("--region", default=REGION)
    args = ap.parse_args()

    m = measure(args.region)
    if args.diff:
        diff(json.load(open(args.diff, encoding="utf-8")), m)
    else:
        show(m)
    if args.out:
        json.dump(m, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\ngespeichert: %s" % args.out)


if __name__ == "__main__":
    main()
