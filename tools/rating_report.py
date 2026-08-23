# -*- coding: utf-8 -*-
"""Region-wide summary of the rating coverage, straight from the region files.

    python tools/rating_report.py                       # Tabelle auf stdout
    python tools/rating_report.py --md docs/trail-rating-abdeckung.md

Reads only what the app itself reads, so the numbers cannot drift from what a rider sees: `rate`, `votes`,
`pop` and `tf` per trail, plus the region-level `ratings` block. A Tour is counted separately and never as
an unrated trail -- a Tour has no rating of its own by design (`ratingRowHtml` returns nothing for one).
"""
import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = os.path.join(ROOT, "Trailmap App", "regions")


def region_rows():
    rows = []
    for f in sorted(os.listdir(REGIONS)):
        if not f.endswith(".json") or f == "version.json":
            continue
        d = json.load(io.open(os.path.join(REGIONS, f), encoding="utf-8"))
        lt = d.get("lineTrails") or []
        trails = [t for t in lt if not t.get("loop")]
        tours = [t for t in lt if t.get("loop")]
        rated = [t for t in trails if isinstance(t.get("rate"), (int, float))]
        pop = [t for t in trails if isinstance(t.get("pop"), (int, float))]
        best = sorted(rated, key=lambda t: -t["rate"])[:3]
        rows.append({
            "region": f[:-5],
            "trails": len(trails),
            "tours": len(tours),
            "rated": len(rated),
            "pop": len(pop),
            "share": (100.0 * len(rated) / len(trails)) if trails else 0.0,
            "median": sorted(t["rate"] for t in rated)[len(rated) // 2] if rated else None,
            "max": max((t["rate"] for t in rated), default=None),
            "asOf": (d.get("ratings") or {}).get("asOf"),
            "best": [(t["name"], t["rate"], t.get("votes")) for t in best],
        })
    return rows


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", help="write a markdown report here as well")
    a = ap.parse_args(argv)
    rows = region_rows()
    tr = sum(r["trails"] for r in rows)
    ra = sum(r["rated"] for r in rows)
    print("%-16s %7s %7s %7s  %6s %6s  %s" % ("Region", "Trails", "bewert", "Anteil", "Median", "Max", "Stand"))
    for r in sorted(rows, key=lambda r: -r["rated"]):
        print("%-16s %7d %7d %6.0f %%  %6s %6s  %s"
              % (r["region"], r["trails"], r["rated"], r["share"],
                 "%.2f" % r["median"] if r["median"] else "-",
                 "%.2f" % r["max"] if r["max"] else "-", r["asOf"] or "-"))
    print("%-16s %7d %7d %6.0f %%" % ("SUMME", tr, ra, 100.0 * ra / tr if tr else 0))

    if a.md:
        out = ["# Bewertungen: Abdeckung je Region", "",
               "Erzeugt von `tools/rating_report.py` aus den Regionsdateien selbst — dieselben Felder, die",
               "die App liest (`rate`, `votes`, `pop`, `tf`). Touren stehen getrennt, weil eine Tour",
               "bewusst keine eigene Bewertung hat.", "",
               "| Region | Trails | bewertet | Anteil | Median | Max | Beliebtheit | Touren | Stand |",
               "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for r in sorted(rows, key=lambda r: -r["rated"]):
            out.append("| `%s` | %d | %d | %.0f %% | %s | %s | %d | %d | %s |"
                       % (r["region"], r["trails"], r["rated"], r["share"],
                          ("%.2f" % r["median"]).replace(".", ",") if r["median"] else "–",
                          ("%.2f" % r["max"]).replace(".", ",") if r["max"] else "–",
                          r["pop"], r["tours"], r["asOf"] or "–"))
        out.append("| **Summe** | **%d** | **%d** | **%.0f %%** | | | | | |"
                   % (tr, ra, 100.0 * ra / tr if tr else 0))
        out += ["", "## Bestbewertete Trails je Region", ""]
        for r in sorted(rows, key=lambda r: -r["rated"]):
            if not r["best"]:
                continue
            out.append("- **%s** — %s" % (r["region"], ", ".join(
                "%s (%s, %s Stimmen)" % (n, ("%.2f" % v).replace(".", ","), s) for n, v, s in r["best"])))
        io.open(a.md, "w", encoding="utf-8", newline="").write("\n".join(out) + "\n")
        print("geschrieben: %s" % a.md)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
