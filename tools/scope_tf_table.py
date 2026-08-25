# -*- coding: utf-8 -*-
"""Cut a region-sized trail table out of a big Trailforks table (a whole state/canton/province).

    python tools/scope_tf_table.py Bormio lombardia "Valdidentro,Bormio,Stelvio Natural Trail Park"

Why this exists: `harvest_trailforks.py --seeds` pages a whole administrative region, and for the Alps that
is the cheapest way to SEE what is there (16 pages buys Tirol's 1 554 trails). But the geometry half costs
one page per trail, so fetching a canton to build one valley is an hour of requests for nothing.
`--areas`/`--skip-areas` exist for that and are the right tool from a shell -- except that some Trailforks
area names carry a zero-width space (several in Savoie do), which no hand-typed CLI list will ever match.

So the areas are matched HERE, by regex, against the strings in the table itself, and the rows are written
out verbatim. What lands in the region is still decided by the build's nearest-anchor rule, exactly as
before -- this is a harvest-COST filter, the same statement `areas_out_of_scope.json` makes. The chosen
areas are recorded next to the table in `harvest_scope.json` so the cut is reproducible and reviewable.
"""
import collections
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_trailforks import ACCESS_DIFF  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    material, src, pattern = argv[0], argv[1], argv[2]
    src_path = src if os.path.isabs(src) else os.path.join(ROOT, src)
    table = json.load(io.open(src_path, encoding="utf-8"))
    rx = re.compile(pattern, re.I)
    out, areas = {}, collections.Counter()
    for slug, row in table.items():
        area = (row.get("area") or "").replace("\u200b", "").strip()
        if not rx.fullmatch(area):
            continue
        out[slug] = row
        if row.get("diff") and row["diff"] not in ACCESS_DIFF:
            areas[area] += 1
    d = os.path.join(ROOT, "Material", material)
    if not os.path.isdir(d):
        os.makedirs(d)
    json.dump(out, io.open(os.path.join(d, "trailforks_table.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    json.dump({"source_table": src, "area_pattern": pattern,
               "areas": dict(areas.most_common()), "rows": len(out),
               "note": "Kostenfilter fuer die Geometrie-Ernte. Was in der Region landet, entscheidet "
                       "allein die Anker-Regel in tools/build_trailforks_region.py."},
              io.open(os.path.join(d, "harvest_scope.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("%s: %d Zeilen, davon %d bewertete Trails in %d Gebieten"
          % (material, len(out), sum(areas.values()), len(areas)))
    for a, n in areas.most_common():
        print("   %4d  %s" % (n, a))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
