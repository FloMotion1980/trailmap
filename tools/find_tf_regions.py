# -*- coding: utf-8 -*-
"""Find the Trailforks region slug(s) that hold a region's trails, by probing names we already have.

    python tools/find_tf_regions.py paznaun laax soelden
    python tools/find_tf_regions.py --all --skip gardasee,madeira,schwarzwald

Trailforks has no usable search for this: `/search/?q=` renders nothing server-side, `/ajax/autocomplete/`
answers "Bad OP", and the region API wants a key. What DOES work is that a region slug is almost always the
place name -- so the candidates are the names this repo already knows: the catalog label, every sub-region
label, and every `places` entry of the region file. Each is tried as a slug and kept if its trails table
returns rows.

Two things make the hit rate worth the requests:

* **German and Italian names need transliteration variants.** Trailforks writes `soelden` or `solden`, never
  `sölden`, and which one it picked is not predictable -- so every umlaut name is probed both ways.
* **A hit does not have to be the region we named.** Trailforks' own tree is what it is: Paznaun has no
  region of its own, its trails sit under `ischgl`. So the probe list is the *places*, not the region.

Prints one line per confirmed slug with its row count, which is what to pass to
`harvest_trailforks.py --seeds`.
"""
import argparse
import io
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_trailforks import fetch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = os.path.join(ROOT, "Trailmap App", "regions")
INDEX = os.path.join(ROOT, "Trailmap App", "index.html")
UMLAUT = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def slugify(name, keep_umlaut_pairs=True):
    """Slug candidates for one place name -- both umlaut spellings, since Trailforks picks either."""
    out = []
    low = (name or "").strip().lower()
    if not low:
        return out
    pair = "".join(UMLAUT.get(c, c) for c in low)
    plain = unicodedata.normalize("NFKD", low).encode("ascii", "ignore").decode()
    for v in ([pair, plain] if keep_umlaut_pairs else [plain]):
        v = re.sub(r"[^a-z0-9]+", "-", v).strip("-")
        if v and v not in out:
            out.append(v)
    return out


def candidates(region):
    """Every name worth probing for one region, most specific last (labels first, then places)."""
    data = json.load(io.open(os.path.join(REGIONS, region + ".json"), encoding="utf-8"))
    html = io.open(INDEX, encoding="utf-8").read()
    names = []
    m = re.search(r'\b%s:\s*\{(.{0,4000}?)\n    \}' % re.escape(region), html, re.S)
    if m:
        blob = m.group(1)
        lm = re.search(r'label:\s*"([^"]+)"', blob)
        if lm:
            names.append(lm.group(1))
        names += re.findall(r'label:\s*"([^"]+)"', blob)[1:]
    for p in (data.get("places") or []):
        n = p.get("name") if isinstance(p, dict) else (p[2] if isinstance(p, list) and len(p) > 2 else None)
        if n:
            names.append(n)
    # A label like "Ischgl / Samnaun" or "Arosa & Lenzerheide" is two places, and each half is a candidate.
    parts = []
    for n in names:
        parts.append(n)
        parts += [x.strip() for x in re.split(r"[/&,]", n) if len(x.strip()) >= 4]
    seen, out = set(), []
    for n in parts:
        for s in slugify(n):
            if s not in seen and len(s) >= 4:
                seen.add(s)
                out.append(s)
    return out


def probe(slug):
    html = fetch("https://www.trailforks.com/region/%s/trails/?activitytype=1" % slug, tries=1)
    return len(re.findall(r"trailforks\.com/trails/", html))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("regions", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--skip", default="")
    ap.add_argument("--sleep", type=float, default=0.35)
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    regs = a.regions
    if a.all:
        skip = set(x for x in a.skip.split(",") if x)
        regs = sorted(f[:-5] for f in os.listdir(REGIONS)
                      if f.endswith(".json") and f != "version.json" and f[:-5] not in skip)
    found = {}
    for r in regs:
        cands = candidates(r)
        hits = []
        for c in cands:
            n = probe(c)
            if n:
                hits.append((c, n))
            time.sleep(a.sleep)
        found[r] = hits
        print("%-16s %2d Kandidaten -> %s" % (r, len(cands), ", ".join("%s (%d)" % h for h in hits) or "nichts"))
        sys.stdout.flush()
    if a.out:
        json.dump(found, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("geschrieben: %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
