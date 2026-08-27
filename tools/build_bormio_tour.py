# -*- coding: utf-8 -*-
"""Baut Bormios Freeride-Itinerar Bormio 3000 -> Santa Caterina Valfurva als Trailrunde.

    python tools/build_bormio_tour.py --dry-run
    python tools/build_bormio_tour.py

## Woher die Linie kommt

Der Nutzer ist die Tour selbst gefahren und hat sie sich gewuenscht, konnte sie aber nicht aufzeichnen
(2026-08-26). Der BETREIBER fuehrt sie unter "Itinerario Freeride MTB Bormio 3000 - Santa Caterina
Valfurva" (`bormioski.eu/itinerario-freeride-mtb/`) mit Zahlen und Wegnummern, aber ohne GPX -- nur ein
PDF und ein Kartenbild. Die Spur kommt deshalb von **bergfex**, wo dieselbe Tour als 2861858 liegt; die
URL hat der Nutzer geliefert.

**Der GPX-Download braucht kein Konto, nur einen Referer.** `/downloads/gps/?id=<id>&fileType=gpx`
antwortet anonym mit `application/gpx+xml`, sobald die Tourseite als `Referer` mitgeht -- ohne ihn kommt
die HTML-Seite zurueck. Das ist dieselbe Klasse von Huerde wie Trailforks' 403 gegen urllib: keine
Anmeldung, nur eine Erwartung an den Aufrufer. Die Datei liegt als
`Material/Bormio/freeride-bormio3000-santa-caterina.gpx` im Repo, ein Neubau braucht also kein Netz.

**Gegen die Betreiberzahlen geprueft, bevor irgendetwas gebaut wurde:**

    Betreiber   12,3 km   +254 / -1482 Hm   3017 -> 1738 m
    bergfex     12,29 km  +294 / -1561 Hm   2997 -> 1730 m

Laenge auf 10 m genau, beide Endhoehen auf 20 m. Die Hoehenmeter weichen wie ueblich ab (aufsummiertes
GPS-Rauschen gegen eine geglaettete Verlagsangabe) -- deshalb stehen im gebauten Trail die Zahlen des
BETREIBERS, nicht die aus der Spur, so wie es die stehende Regel fuer offizielle Angaben verlangt.

## Was die Abschnitte sagen -- und was das korrigiert

`tools/gpx_map_match.py` gegen Bormios eigene 179 Trails und 3 Lifte:

    Bormio 3000 single   7,78 km
      Verbinder            0,04 km
    Panoramico Le Cune   2,74 km
      Verbinder            0,13 km
    Le Cune              0,71 km
      Verbinder            0,88 km  (Auslauf nach Santa Caterina)

**Das widerlegt die Vermutung vom Vortag.** In `docs/bormio.md` stand, die Tour sei `Bormio 3000 single`
plus `Le Cune` -- weil deren Enden 3 m auseinanderliegen und die Summe ungefaehr passte. Tatsaechlich
faehrt sie ueber `Panoramico Le Cune`, die panoramische Variante, und beruehrt vom `Le Cune` nur die
letzten 700 m. Genau dafuer ist der Matcher da und nicht das Augenmass: zwei Linien, die am selben Punkt
beginnen, sind mit blossem Endpunktvergleich nicht zu unterscheiden.

Die 0,88 km am Schluss bleiben ein ehrlicher VERBINDER. Es ist der Auslauf ins Dorf, und ihn auf den
naechstliegenden Trail zu ziehen waere genau die stille Zurechtbiegung, die dieses Projekt nicht macht.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gpx_map_match import match_gpx_to_network, resolve_segments  # noqa: E402
from trailmap_pipeline import (build_profile, cumulative_km, haversine_m,  # noqa: E402
                               parse_gpx, write_region)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = os.path.join(ROOT, "Trailmap App", "regions", "bormio.json")
GPX = os.path.join(ROOT, "Material", "Bormio", "freeride-bormio3000-santa-caterina.gpx")

TOUR_ID = "bo_tour_freeride_bormio3000"
TOUR_NAME = "Freeride Bormio 3000 - Santa Caterina"
#: Sub-Region: die Tour startet auf der Cima Bianca ueber Bormio und endet in Santa Caterina, laeuft also
#: quer durchs Valfurva. Der groessere Teil ihrer Linie liegt dort, und dort endet sie auch.
TOUR_SUB = "bo_valfurva"
#: Der Betreiber gibt keinen Schwierigkeitsgrad an, wohl aber "Il primo tratto e molto tecnico" und den
#: Charakter Freeride/Enduro. Die Komponenten sind rot (Bormio 3000 single) und blau (Le Cune / Panoramico
#: Le Cune); der schwerste Abschnitt entscheidet, wie bei jeder zusammengesetzten Runde in diesem Projekt.
TOUR_DIFF = "rot"
#: Zahlen des Betreibers, nicht der Spur -- siehe Modul-Docstring.
OFFICIAL_LEN_KM = 12.3
OFFICIAL_UP_M = 254
OFFICIAL_DOWN_M = 1482


def main(argv):
    dry = "--dry-run" in argv
    region = json.load(io.open(REGION, encoding="utf-8"))
    pts = parse_gpx(io.open(GPX, encoding="utf-8", errors="replace").read())
    flat_pts = [[p[0], p[1]] for p in pts]

    candidates = dict((t["id"], region["trailGeo"][t["id"]]) for t in region["lineTrails"]
                      if not t.get("loop"))
    for l in region.get("lifts") or []:
        candidates[l["id"]] = l["coords"]
    print("Netz: %d Kandidaten (%d Trails + %d Lifte)"
          % (len(candidates), len(candidates) - len(region.get("lifts") or []),
             len(region.get("lifts") or [])))

    runs = match_gpx_to_network(flat_pts, candidates)
    resolved = resolve_segments(flat_pts, candidates, runs)

    segs, cur = [], 0
    for r in resolved:
        if r["gpx_start_idx"] > cur:
            segs.append({"coords": [p[:2] for p in flat_pts[cur:r["gpx_start_idx"] + 1]], "trailId": None})
        key = "liftId" if r["id"].startswith("lift_") else "trailId"
        segs.append({"coords": [list(c) for c in r["coords"]], key: r["id"]})
        cur = r["gpx_end_idx"]
    if cur < len(flat_pts) - 1:
        segs.append({"coords": [p[:2] for p in flat_pts[cur:]], "trailId": None})
    segs = [s for s in segs if len(s["coords"]) >= 2]

    # DIE Invariante, die validate_region.py prueft: trailGeo[id] IST die Verkettung, exakt.
    for s in segs:
        s["coords"] = [[round(c[0], 6), round(c[1], 6)] for c in s["coords"]]
    coords = [c for s in segs for c in s["coords"]]

    seg_cum = cumulative_km(coords)
    off = 0
    for s in segs:
        n = len(s["coords"])
        s["distStart"] = round(seg_cum[off], 3)
        s["distEnd"] = round(seg_cum[off + n - 1], 3)
        off += n

    ele = []
    for c in coords:
        near = min(pts, key=lambda p: haversine_m(c, p[:2]))
        ele.append(near[2] if len(near) > 2 else None)
    prof, gain, loss = build_profile(coords, ele)

    by = dict((t["id"], t) for t in region["lineTrails"])
    named = [s for s in segs if s.get("trailId") or s.get("liftId")]
    on = sum(sum(haversine_m(s["coords"][i], s["coords"][i + 1])
                 for i in range(len(s["coords"]) - 1)) for s in named)
    total = seg_cum[-1] * 1000.0
    print("\n%d Abschnitte, davon %d benannt (%.2f km = %.0f %% der Linie)"
          % (len(segs), len(named), on / 1000.0, 100.0 * on / total))
    for s in segs:
        who = s.get("trailId") or s.get("liftId")
        label = by.get(who, {}).get("name", who) if who else "Verbinder"
        print("   %-34s %5.2f km   %6.3f - %6.3f km"
              % (label[:34], s["distEnd"] - s["distStart"], s["distStart"], s["distEnd"]))
    print("\nSpur: %.2f km, +%d / -%d Hm   |   Betreiber: %.1f km, +%d / -%d Hm  (gebaut wird der Betreiber)"
          % (total / 1000.0, gain, loss, OFFICIAL_LEN_KM, OFFICIAL_UP_M, OFFICIAL_DOWN_M))

    entry = {"id": TOUR_ID, "name": TOUR_NAME, "region": TOUR_SUB, "diff": TOUR_DIFF,
             "len": OFFICIAL_LEN_KM, "up": OFFICIAL_UP_M, "down": OFFICIAL_DOWN_M, "loop": True}
    line_trails = [t for t in region["lineTrails"] if t["id"] != TOUR_ID] + [entry]
    geo = dict((k, v) for k, v in region["trailGeo"].items() if k != TOUR_ID)
    profs = dict((k, v) for k, v in region["elevationProfiles"].items() if k != TOUR_ID)
    segments = dict((k, v) for k, v in (region.get("trailSegments") or {}).items() if k != TOUR_ID)
    geo[TOUR_ID] = coords
    profs[TOUR_ID] = prof
    segments[TOUR_ID] = segs

    if dry:
        print("\n--dry-run: nichts geschrieben")
        return 0
    write_region(REGION, line_trails, geo, profs, trail_segments=segments)
    print("\ngeschrieben: bormio.json")
    print("weiter: python tools/update_region_versions.py && python tools/validate_region.py bormio")
    print("HINWEIS: trailCount in index.html auf %d setzen" % len(line_trails))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
