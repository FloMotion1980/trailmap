# -*- coding: utf-8 -*-
"""
@suite   trailforks
@area    The Trailforks harvest and the region build that runs on it
@files   tools/harvest_trailforks.py, tools/build_trailforks_region.py, Material/*/trailforks_table.json
@touches parse_table, parse_trail, decode_polyline, harvest_tables, ALL_DIFF, PAGE_ROWS, ACCESS_DIFF, TF_DIFF, sid, CONFIGS, build

Two regions (Madeira, Gardasee) are built entirely from what these two files read out of Trailforks' own
HTML, so a silent parsing change here would not break anything visibly -- it would quietly produce a region
with the wrong difficulties, or one missing a whole tier. Three of the cases below pin a rule that is
invisible in the source data and was learnt the hard way:

* the difficulty comes from the `dicon_small` span, and every row ALSO carries a status span whose title
  ("All Clear / Green") reads exactly like a difficulty -- matching the first title in the row gives every
  trail a plausible, wrong grade;
* the listing pages at 100 rows through `?page=N` with no pager markup, no count and no error past the end;
* `difficulty=` must name every code including 10, and `activitytype=1` is what keeps hike-only lines out.

The `TF_DIFF` completeness case is data-driven against the harvested tables on purpose: it is what catches a
tier NOBODY HAS SEEN YET. "Easiest / White Circle" was exactly that -- absent from the Vogesen and the
Schwarzwald, worth 78 trails at the Gardasee, and it would have been dropped in silence.
"""
import contextlib
import io
import json
import os

import harvest_trailforks as H
import build_trailforks_region as B

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MATERIAL = os.path.join(ROOT, "Material")

#: One real row, trimmed of the star-rating block but otherwise byte-for-byte as Trailforks renders it
#: (Madeira's "Ana Ferreira", fetched 2026-08-21). Both spans that carry a title are kept, because telling
#: them apart is the whole point of the first case.
ROW = ('<tr  ><td   style="vertical-align:middle;"><span aria-hidden="true" data-icon="&#xe902;" '
       'class="sicon_small sgreen hovertip" title="All Clear / Green" data-sort="1"></span></td>'
       '<td   ><span class=\'none item-nid\' data-nid=\'846028\'></span>'
       '<a href="https://www.trailforks.com/trails/ana-ferreira/" class="green">Ana Ferreira</a></td>'
       '<td   ><span aria-hidden="true" data-icon="&#xe012;" data-sort="3" class="dicon_small dblue" '
       'title="Intermediate / Blue Square"></span></td>'
       '<td  class=" nowrap"><a href="https://www.trailforks.com/region/porto-santo-71311/">Porto Santo</a></td>'
       '<td   ><div style="display:inline-block;"></div></td>'
       '<td   ><span data-v="1720">2 km</span></td>'
       '<td   ><span data-v="-173.1">-173 m</span></td>'
       '<td   >11 m</td></tr>')
#: The same shape for a HIDDEN trail: Trailforks puts the flag in the anchor's own class list.
HIDDEN_ROW = ROW.replace('class="green">Ana Ferreira', 'class="green hidden_trail" rel="nofollow">Antenas') \
                .replace("trails/ana-ferreira/", "trails/antenas-24864/")


def table_html(rows):
    return ('<html><body><table id="trails_table" class="table1 tablesorter responsive" >'
            "<thead><tr ><th>t</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></body></html>")


def run(t):
    # ------------------------------------------------------------------ the table parser
    t.case("parse_table reads a row, and takes the difficulty from the difficulty icon")
    rows = H.parse_table(table_html([ROW]))
    t.eq("one row", len(rows), 1)
    r = rows[0]
    t.eq("slug", r["slug"], "ana-ferreira")
    t.eq("name", r["name"], "Ana Ferreira")
    # The trap: "All Clear / Green" is the STATUS span's title and sits earlier in the row.
    t.eq("difficulty is the dicon title, not the status title", r["diff"], "Intermediate / Blue Square")
    t.eq("riding area label", r["area"], "Porto Santo")
    t.eq("riding area slug", r["area_slug"], "porto-santo-71311")
    t.eq("length in metres from data-v, not the rounded '2 km' text", r["m"], 1720.0)
    t.eq("descent is negative and keeps its decimals", r["down"], -173.1)
    t.eq("a plain row is not hidden", r["hidden"], False)

    t.case("parse_table flags a hidden trail and survives a page with no table at all")
    t.eq("hidden_trail in the anchor's class is picked up", H.parse_table(table_html([HIDDEN_ROW]))[0]["hidden"], True)
    t.eq("a page past the end yields nothing rather than throwing", H.parse_table("<html>nothing</html>"), [])
    t.eq("the header row is not mistaken for a trail", len(H.parse_table(table_html([]))), 0)

    # ------------------------------------------------------------------ the paging rule
    t.case("harvest_tables pages at 100 rows, stops on a short page, and dedupes across seeds")
    # Nothing in the HTML says the listing pages, so this is pinned against a fake server rather than
    # against the real one: page 1 full, page 2 short. A full page must be followed by another request.
    asked = []

    def fake_fetch(url, tries=3):
        asked.append(url)
        page = int(url.split("page=")[1])
        seed = url.split("/region/")[1].split("/")[0]
        if page == 1:
            return table_html([ROW.replace("trails/ana-ferreira/", "trails/%s-%d/" % (seed, i))
                               for i in range(H.PAGE_ROWS)])
        if page == 2:
            return table_html([ROW.replace("trails/ana-ferreira/", "trails/%s-x%d/" % (seed, i))
                               for i in range(7)])
        return "<html>nothing</html>"

    real_fetch, real_sleep = H.fetch, H.time.sleep
    H.fetch, H.time.sleep = fake_fetch, lambda s: None
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tf_table_tmp.json")
    try:
        # harvest_tables reports progress on stdout; a test suite's own output should be its results.
        with contextlib.redirect_stdout(io.StringIO()):
            table = H.harvest_tables(["alpha", "beta"], tmp)
    finally:
        H.fetch, H.time.sleep = real_fetch, real_sleep
        if os.path.exists(tmp):
            os.remove(tmp)
    t.eq("both pages of both seeds were read", len(table), 2 * (H.PAGE_ROWS + 7))
    t.eq("and it stopped after the short page", len(asked), 4)
    t.ok("every URL carries the full difficulty list", all("difficulty=" + H.ALL_DIFF in u for u in asked),
         asked[0], "difficulty=" + H.ALL_DIFF)
    t.ok("and activitytype=1, which is what keeps hike-only lines out",
         all("activitytype=1" in u for u in asked), asked[0], "activitytype=1")
    # Leaving code 10 out drops the whole black tier without a word -- that is a data loss no other check
    # in this repo would notice, so the list is pinned literally.
    t.ok("code 10 (Severe / Black) is in the difficulty list",
         "10" in H.ALL_DIFF.split(","), H.ALL_DIFF, "contains 10")
    t.eq("every code 1..12 is asked for", sorted(int(x) for x in H.ALL_DIFF.split(",")), list(range(1, 13)))

    t.case("a seed whose rows a later seed repeats does not double-count")
    H.fetch, H.time.sleep = (lambda url, tries=3: table_html([ROW])), (lambda s: None)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            again = H.harvest_tables(["alpha", "beta"], tmp)
    finally:
        H.fetch, H.time.sleep = real_fetch, real_sleep
        if os.path.exists(tmp):
            os.remove(tmp)
    t.eq("the same slug from two seeds is one trail", len(again), 1)
    t.eq("and it keeps the seed that found it first", again["ana-ferreira"]["src"], "alpha")

    # ------------------------------------------------------------------ the trail page
    t.case("decode_polyline decodes Google's precision-5 encoding")
    # The canonical example from Google's own format description.
    pts = H.decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    t.eq("three points", len(pts), 3)
    t.eq("first", [round(pts[0][0], 5), round(pts[0][1], 5)], [38.5, -120.2])
    t.eq("last", [round(pts[2][0], 5), round(pts[2][1], 5)], [43.252, -126.453])

    t.case("parse_trail reads the polyline AND the profile, whether or not lat/lng are quoted")
    # QUOTED lat/lng is the real shape and an unquoted-number pattern silently returns NO profile at all --
    # 12 Schwarzwald trails were harvested that way before anyone noticed, so both spellings are pinned.
    quoted = ('<script>var m = { encodedpath: \'_p~iF~ps|U_ulLnnqC\' };'
              'new ElevationChart({"points":[{"id":1,"x":"0","y":"1500.5","lat":"38.5","lng":"-120.2"},'
              '{"id":2,"x":"120.4","y":"1490","lat":"40.7","lng":"-120.95"}]});</script>')
    coords, prof = H.parse_trail(quoted)
    t.eq("the polyline is decoded", len(coords), 2)
    t.eq("the profile has both points", len(prof), 2)
    t.eq("a profile point is [distance_m, ele_m, lat, lng]", [round(v, 2) for v in prof[1]],
         [120.4, 1490.0, 40.7, -120.95])
    unquoted = quoted.replace('"x":"0"', '"x":0').replace('"lat":"38.5"', '"lat":38.5')
    t.eq("the unquoted spelling parses too", len(H.parse_trail(unquoted)[1]), 2)

    t.case("parse_trail reports a page that carries neither, rather than inventing one")
    coords, prof = H.parse_trail("<html>a trail page with no map and no chart</html>")
    t.eq("no polyline", coords, None)
    t.eq("no profile", prof, None)

    # ------------------------------------------------------------------ the build's own rules
    t.case("TF_DIFF covers every difficulty title the harvested tables actually contain")
    # Data-driven on purpose: this is the case that catches a tier nobody has seen yet, which is what
    # "Easiest / White Circle" was. A missing tier is silent -- the trails simply are not built.
    seen, missing = set(), {}
    for name in sorted(os.listdir(MATERIAL)):
        path = os.path.join(MATERIAL, name, "trailforks_table.json")
        if not os.path.exists(path):
            continue
        for row in json.load(io.open(path, encoding="utf-8")).values():
            d = row.get("diff")
            if not d or d in H.ACCESS_DIFF:
                continue
            seen.add(d)
            if d not in B.TF_DIFF:
                missing.setdefault(d, row.get("name"))
    t.ok("at least one harvested table was read", len(seen) > 0, len(seen), "> 0")
    t.eq("no unmapped difficulty title", missing, {})
    t.ok("and every mapping lands on one of the app's four colours",
         set(B.TF_DIFF.values()) <= {"gruen", "blau", "rot", "schwarz"},
         sorted(set(B.TF_DIFF.values())), "gruen/blau/rot/schwarz")
    # .get, not [] -- indexing here made the whole suite abort with a KeyError under the very mutation the
    # case above exists to catch (a tier missing from TF_DIFF), which cost the four cases that follow it.
    t.eq("white and green share the bottom step, since the app has nothing below 'Sehr leicht'",
         [B.TF_DIFF.get("Easiest / White Circle"), B.TF_DIFF.get("Easy / Green Circle")],
         ["gruen", "gruen"])

    t.case("an id is the region's prefix plus the Trailforks slug, so a trail is traceable to its page")
    t.eq("plain slug", B.sid("md", "ana-ferreira"), "md_ana_ferreira")
    t.eq("a numeric suffix survives", B.sid("md", "antenas-24864"), "md_antenas_24864")
    t.eq("odd characters collapse to one underscore", B.sid("gd", "601--Pernici/Trail"), "gd_601_pernici_trail")

    t.case("sub_override actually moves a trail, and only the ones it names")
    # Die Invariante darunter prueft nur die KONFIGURATION. Eine Mutation, die `sub_override` im Bau
    # komplett ignoriert (`forced = None`), liess die ganze Suite gruen -- das Verhalten war ungeprueft.
    # Also hier: der Bau selbst, trocken, gegen die eingecheckten Material-Dateien.
    mat = os.path.join(ROOT, "Material", "Bormio")
    if not os.path.isdir(mat):
        t.ok("uebersprungen: Material/Bormio fehlt", True, "skip", "skip")
    else:
        # Der Bau druckt seinen ganzen Bericht; hier interessiert nur das Ergebnis.
        with contextlib.redirect_stdout(io.StringIO()):
            data = B.build("bormio", dry_run=True)
        cfg = B.CONFIGS["bormio"]
        want = set(B.sid(cfg["prefix"], slug) for slug, sub in cfg["sub_override"].items()
                   if sub == "bo_bikepark")
        got = set(x["id"] for x in data["lineTrails"] if x["region"] == "bo_bikepark")
        t.eq("genau die benannten Linien liegen im Bikepark", sorted(got), sorted(want))
        t.ok("und es sind wirklich fuenf", len(got) == 5, len(got), 5)
        # Die Gegenprobe, die die Mutation oben haette fangen muessen: ohne den Override waeren dieselben
        # Trails nach reiner Nachbarschaft auf zwei ANDERE Taeler verteilt.
        by = dict((x["id"], x) for x in data["lineTrails"])
        t.ok("ohne Override laegen sie nicht zusammen",
             len(set(cfg["sub_override"].values())) == 1 and all(i in by for i in want),
             sorted(set(cfg["sub_override"].values())), ["bo_bikepark"])

    t.case("every configured region's anchors name a declared sub-region, and vice versa")
    for key, cfg in sorted(B.CONFIGS.items()):
        declared = set(k for k, _label, _color in cfg["subregions"])
        anchored = set(a[2] for a in cfg["anchors"])
        # `sub_override` is the SECOND way a sub-region gets filled, and it exists precisely for the case
        # that has no anchor: Bormio's Bikepark is defined by the operator's own piste list, and its five
        # lines fall into two different valleys geographically. So the invariant is "reachable at all",
        # not "has an anchor" -- but both halves still have to name something declared, which is what
        # actually catches a typo (2026-08-26).
        forced = set((cfg.get("sub_override") or {}).values())
        used = anchored | forced
        t.eq("%s: no anchor points at an undeclared sub-region" % key, sorted(anchored - declared), [])
        t.eq("%s: no sub_override points at an undeclared sub-region" % key, sorted(forced - declared), [])
        t.eq("%s: no sub-region nothing can ever fill" % key, sorted(declared - used), [])
        t.ok("%s: colours are distinct within the group" % key,
             len(set(c for _k, _l, c in cfg["subregions"])) == len(cfg["subregions"]),
             len(set(c for _k, _l, c in cfg["subregions"])), len(cfg["subregions"]))
        # #2f6b3a is --forest, the group-label button's own fill, and it sits directly above these chips.
        t.ok("%s: no sub-region borrows the group button's own colour" % key,
             all(c.lower() not in ("#2f6b3a", "#3a5a40") for _k, _l, c in cfg["subregions"]),
             [c for _k, _l, c in cfg["subregions"]], "not --forest")
