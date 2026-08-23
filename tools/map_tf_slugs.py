# -*- coding: utf-8 -*-
"""Map a region's trails onto Trailforks slugs, for the regions that were BUILT from Trailforks.

    python tools/map_tf_slugs.py gardasee --material Gardasee
    python tools/map_tf_slugs.py madeira  --material Madeira --json /tmp/madeira_map.json

`tools/match_trailforks.py` exists for the hard case: our line and Trailforks' line are two independent
recordings of the same trail, so it needs four fuzzy signals and a margin rule. That is the wrong tool for
the Gardasee, Madeira and the Schwarzwald trails that CAME from this source -- there our stored `trailGeo`
IS their decoded polyline, so the mapping is a lookup rather than an inference.

**It is not bit-identical, though, and assuming it was cost the first version of this file 78 of Madeira's
158 trails.** The build pipeline de-duplicates points within 0.5 m and runs Douglas-Peucker over them, which
keeps the endpoints but re-rounds them (32.68785 against Trailforks' 32.68784), and occasionally trims a
tail (Avalanche Raposeira ends 25 m short). So the rule is a tolerance, not an equality:

* the id carries the slug -- `md_babylon_84563` came from `babylon-84563` -- so the first candidate is the
  id with its prefix stripped and underscores turned back into hyphens, accepted when its endpoints are
  within ID_TOL_M. That is our OWN build's naming, which is far stronger evidence than a name similarity
  between two independent sources would be;
* otherwise the nearest line by endpoint distance, in either orientation, accepted only when it is within
  GEO_TOL_M **and** clearly better than the runner-up -- the same margin idea `match_trailforks.py` uses,
  because two trails sharing a trailhead are the norm in a hub, not the exception.

Anything left over is reported, never guessed.
"""
import argparse
import io
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import haversine_m  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = os.path.join(ROOT, "Trailmap App", "regions")

#: A slug taken from our own id may sit this far off -- generous, because the evidence is the id itself and
#: the only thing being ruled out is a slug that happens to exist somewhere else entirely in the region.
ID_TOL_M = 400.0
#: Without that evidence, the endpoints have to genuinely coincide: the build only re-rounds and trims.
GEO_TOL_M = 60.0
#: ...and the runner-up has to be clearly worse, or the pair is left unmapped rather than guessed.
MARGIN = 3.0


def name_slug(name):
    """Our trail name as Trailforks would slug it -- lowercase, ascii, hyphens, umlauts spelled out."""
    low = (name or "").lower()
    low = "".join({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}.get(c, c) for c in low)
    low = unicodedata.normalize("NFKD", low).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", low).strip("-")


def load_geo(paths):
    """{slug: [[lat, lng], ...]} from one or more harvest files, whatever shape they are in.

    Three shapes are in the repo, all of them Trailforks polylines, and none of them convertible to the
    others by hand without losing a region: `{slug: {"c": [...], "p": [...]}}` (the generic harvester and
    the Vogesen), `{slug: [[lat, lng], ...]}` (the Harz, harvested a month earlier), and a region split
    across several files because a later run picked up a tier the first one missed
    (`vogesen_geo_black.json`, the whole black grade). Later files win on a repeated slug.
    """
    out = {}
    for path in paths:
        d = json.load(io.open(path, encoding="utf-8"))
        for slug, v in d.items():
            c = v.get("c") if isinstance(v, dict) else v
            if c and len(c) > 1:
                out[slug] = c
    return out


def ends(coords):
    return (coords[0], coords[-1]) if coords and len(coords) > 1 else None


def end_dist(a, b):
    """Metres between two lines' endpoints, taking the better of the two orientations."""
    fwd = haversine_m(a[0], b[0]) + haversine_m(a[1], b[1])
    rev = haversine_m(a[0], b[1]) + haversine_m(a[1], b[0])
    return min(fwd, rev)


def run(region, material, geo_files=None):
    data = json.load(io.open(os.path.join(REGIONS, region + ".json"), encoding="utf-8"))
    mat = material if os.path.isabs(material) else os.path.join(ROOT, "Material", material)
    files = [f if os.path.isabs(f) else os.path.join(mat, f) for f in (geo_files or ["trailforks_geo.json"])]
    geo = load_geo(files)

    tf = {slug: ends(c) for slug, c in geo.items() if ends(c)}
    trails = [t for t in data["lineTrails"] if not t.get("loop")]   # a Tour is never one Trailforks line

    mapping, unmapped, by_id, by_name, by_geo = {}, [], 0, 0, 0
    claimed = {}
    for t in trails:
        e = ends(data["trailGeo"].get(t["id"]))
        if not e:
            unmapped.append((t["id"], "keine Geometrie"))
            continue
        # 1. the slug our own id was built from
        guess = re.sub(r"^[a-z]{2,4}_", "", t["id"]).replace("_", "-")
        if guess in tf and end_dist(e, tf[guess]) <= ID_TOL_M:
            mapping[t["id"]] = guess
            by_id += 1
            claimed.setdefault(guess, []).append(t["id"])
            continue
        # 2. the slug the NAME would produce. The Harz was harvested before this pipeline and its ids carry
        #    no slug, but a Trailforks slug IS the slugged name, optionally with its numeric id appended
        #    (`dh-upper-140882`). Endpoint-verified like the id rule, so a same-name trail elsewhere in the
        #    region cannot slip through.
        ns = name_slug(t.get("name"))
        if ns:
            hits = [sl for sl in tf if sl == ns or re.match(r"^%s-\d+$" % re.escape(ns), sl)]
            hits = [sl for sl in hits if end_dist(e, tf[sl]) <= ID_TOL_M]
            if len(hits) == 1:
                mapping[t["id"]] = hits[0]
                by_name += 1
                claimed.setdefault(hits[0], []).append(t["id"])
                continue
        # 3. nearest endpoints, with a margin over the runner-up
        scored = sorted(((end_dist(e, v), slug) for slug, v in tf.items()))[:2]
        if scored and scored[0][0] <= GEO_TOL_M and (
                len(scored) < 2 or scored[1][0] > max(scored[0][0] * MARGIN, GEO_TOL_M)):
            mapping[t["id"]] = scored[0][1]
            by_geo += 1
            claimed.setdefault(scored[0][1], []).append(t["id"])
            continue
        unmapped.append((t["id"], "bester Abstand %.0f m (%s), naechster %s"
                         % (scored[0][0], scored[0][1], "%.0f m" % scored[1][0] if len(scored) > 1 else "-")
                         if scored else "kein Kandidat"))
    # One Trailforks line claimed by two of our trails means one of them is wrong -- drop both rather than
    # attach the same rating twice. This is the same-line-two-names case, which really happens here.
    for slug, ids in claimed.items():
        if len(ids) > 1:
            for tid in ids:
                mapping.pop(tid, None)
                unmapped.append((tid, "teilt %s mit %s" % (slug, ", ".join(i for i in ids if i != tid))))
    print("%s: %d Trails, %d zugeordnet (%d id, %d Name, %d Geometrie), %d offen"
          % (region, len(trails), len(mapping), by_id, by_name, by_geo, len(unmapped)))
    return mapping, unmapped


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("region")
    ap.add_argument("--material", required=True)
    ap.add_argument("--geo", help="comma-separated harvest file(s) under --material; "
                                  "default trailforks_geo.json")
    ap.add_argument("--json", help="write the mapping to this file")
    a = ap.parse_args(argv)
    mapping, ambiguous = run(a.region, a.material, a.geo.split(",") if a.geo else None)
    if a.json:
        json.dump({"mapping": mapping, "ambiguous": ambiguous},
                  io.open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("geschrieben: %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
