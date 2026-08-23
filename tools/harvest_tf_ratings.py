# -*- coding: utf-8 -*-
"""Fetch ONLY the community numbers for trails already harvested, and merge them into the table.

    python tools/harvest_tf_ratings.py --dir Material/Madeira
    python tools/harvest_tf_ratings.py --dir Material/Gardasee --limit 50     # a slice first
    python tools/harvest_tf_ratings.py --dir Material/Harz --slugs a,b,c      # only these

Why this exists rather than a flag on `harvest_trailforks.py --geo`: the three regions built from
Trailforks (Gardasee, Madeira, Schwarzwald) were harvested BEFORE `RATING_FIELDS` was added, so their
`trailforks_geo.json` is complete and their ratings are missing. Re-running `--geo` would re-download
every polyline to pick up a number that sits on the same page -- 2 000 requests for the Gardasee alone.
This walks the same pages, keeps only the rating blob, and skips a trail that already has one, so an
interrupted run resumes for free.

The numbers land in `trailforks_table.json` next to the row they belong to, which is where
`apply_trailforks_ratings.py` already reads them from.
"""
import argparse
import collections
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_trailforks import fetch, parse_rating  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def own_nid(slug, row, html):
    """Trailforks' numeric id for THIS trail, from the cheapest reliable source available.

    It matters which blob the rating is read from: a trail page embeds one per trail its map shows, so an
    unanchored parse can attach a neighbour's stars. Three sources, in order of confidence:

    * the harvested table row -- but the older harvests (Madeira, Gardasee, Schwarzwald) predate the `nid`
      capture and have none, which is why the other two exist;
    * the digits at the end of the slug: Trailforks appends the id when a name is not unique
      (`babylon-84563`), so this is exact when it is present;
    * the id that appears MOST OFTEN as `trailid=` in the page. The own id is in every one of the page's own
      links (7 times on the Babylon page) while a neighbour appears once or twice, so the mode is the page's
      own trail. Counting beats taking the first match, which is whichever trail the map happened to list.
    """
    if row.get("nid"):
        return row["nid"]
    m = re.search(r"-(\d{3,})$", slug)
    if m:
        return int(m.group(1))
    ids = collections.Counter(re.findall(r"trailid=(\d+)", html))
    return int(ids.most_common(1)[0][0]) if ids else None


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--table", default="trailforks_table.json",
                    help="the file the numbers are stored in, created if absent")
    ap.add_argument("--from-geo", help="comma-separated harvest file(s) to take the slug list from, for a "
                                       "region whose harvest kept no table (the Harz, the Vogesen)")
    ap.add_argument("--slugs", help="comma-separated; default is every row in the table")
    ap.add_argument("--slugs-file", help="a file holding the same list -- 900 slugs are 20 000 characters "
                                         "of command line, which Windows will take but nobody can read")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sleep", type=float, default=0.45)
    ap.add_argument("--save-every", type=int, default=25)
    a = ap.parse_args(argv)

    d = a.dir if os.path.isabs(a.dir) else os.path.join(ROOT, a.dir)
    path = os.path.join(d, a.table)
    table = json.load(io.open(path, encoding="utf-8")) if os.path.exists(path) else {}
    if a.from_geo:
        # The Harz and the Vogesen were harvested before this pipeline existed and kept only geometry, so
        # there is no table row to hang a rating on. The slug list is all that is needed: an empty row is a
        # place to put the numbers, and `nid` is recoverable from the slug or the page (see own_nid).
        added = 0
        for f in a.from_geo.split(","):
            fp = f if os.path.isabs(f) else os.path.join(d, f)
            for slug in json.load(io.open(fp, encoding="utf-8")):
                if slug not in table:
                    table[slug] = {"slug": slug}
                    added += 1
        print("aus der Geometrie ergaenzt: %d Slugs" % added)

    raw = a.slugs
    if a.slugs_file:
        raw = io.open(a.slugs_file, encoding="utf-8").read().strip()
    if raw:
        want = [s for s in raw.replace(chr(10), ",").split(",") if s and s in table]
    else:
        want = list(table)
    todo = [s for s in want if not table[s].get("rating_bayesian") and not table[s].get("_norate")]
    if a.limit:
        todo = todo[:a.limit]
    print("%s: %d Zeilen, %d ohne Bewertung, %d werden geholt"
          % (os.path.basename(d), len(table), len(want) - sum(1 for s in want if table[s].get("rating_bayesian")), len(todo)))
    sys.stdout.flush()

    got = miss = failed = 0
    for i, slug in enumerate(todo, 1):
        html = fetch("https://www.trailforks.com/trails/%s/" % slug)
        # A FETCH failure and a trail with no votes must never be recorded the same way. `fetch` gives up
        # after three tries and returns whatever short body it got, so without this a rate-limit block would
        # walk the whole region marking every trail "_norate" -- and a later run, which skips those, would
        # never come back. Anything under fetch's own 5 000-character success bar is left untouched instead,
        # and the run backs off so a temporary block does not eat the rest of the queue.
        if len(html) < 5000:
            failed += 1
            print("  Abruf fehlgeschlagen: %s (%d Zeichen) -- bleibt offen" % (slug, len(html)))
            sys.stdout.flush()
            time.sleep(5 + min(failed, 6) * 5)
            continue
        nid = own_nid(slug, table[slug], html)
        if nid and not table[slug].get("nid"):
            table[slug]["nid"] = nid
        r = parse_rating(html, nid)
        if r.get("rating_bayesian"):
            table[slug].update(r)
            got += 1
        else:
            # Remember the miss, so a resumed run does not fetch it again. A trail can genuinely carry no
            # rating at all (no votes yet), and that is not an error -- it is the third state the app
            # already renders as "noch nicht bewertet".
            table[slug]["_norate"] = True
            miss += 1
        if i % a.save_every == 0 or i == len(todo):
            json.dump(table, io.open(path, "w", encoding="utf-8"),
                      ensure_ascii=False, separators=(",", ":"))
            print("  %4d/%d  mit %d  ohne %d%s"
                  % (i, len(todo), got, miss, "  fehlgeschlagen %d" % failed if failed else ""))
            sys.stdout.flush()
        time.sleep(a.sleep)
    print("fertig: %d mit Bewertung, %d ohne, %d fehlgeschlagen (bleiben offen)" % (got, miss, failed))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
