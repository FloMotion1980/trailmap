# -*- coding: utf-8 -*-
"""Pruefdaten fuer den nearbyTrailConnector-Regressionstest bauen.

    python tools/make_ntc_fixture.py                 # alle eingetragenen Touren neu bauen

Warum es das braucht: bis 2026-08-20 wurde jede Verfahrensaenderung von Hand gegen EINE Tour verglichen,
und die Referenz dafuer war ein Stand, der teils von Hand entstanden ist. Dadurch fiel nicht auf, dass
`MAX_TRIM_FACTOR = 3.0` zwei bestaetigte Loesungen in Rodalben Felsentrails unerreichbar machte -- das
Verfahren wurde still schlechter. Der Test friert deshalb fest, WAS das Verfahren auf echten Touren leistet.

Zwei Entscheidungen dahinter:

* **Die Wege werden mitgeliefert, nicht abgefragt.** Ein Test, der Overpass braucht, laeuft in der Praxis
  nie. Mitgeliefert wird genau die Vereinigung der Bounding-Boxen, die `fetch()` pro Luecke selbst benutzt --
  damit ist die Wegemenge beweisbar dieselbe wie im echten Lauf und nicht bloss "aehnlich". Gepackt, weil
  ungepackt allein Felsentrails 417 KB waere.
* **Der Ausgangsstand wird mitgeliefert, nicht aus git geholt.** Ein Test, der an Commit-Hashes haengt,
  bricht beim ersten Umschreiben der Historie.
"""
import gzip
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nearby_trail_connector as N
from trailmap_pipeline import haversine_m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = "Trailmap App/regions/pfaelzerwald.json"
FIX = os.path.join(ROOT, "tests", "fixtures")

# Welche Touren, und der Stand VOR dem Schliessen. Rodalben Felsentrails ist die Pflicht-Tour (Nutzer,
# 2026-08-20: "grade die Rodalben Felsentrails sollten herangezogen werden, denn da sind viele Faelle
# aufgefallen") -- sie ist die einzige, in der alle Faelle 1 bis 5 vorkommen. Landstuhl (Ost) deckt Fall 0
# ab plus alles, was am 2026-08-20 dazukam: die Segment-Grenze, die Verschmelzungs-Korrektur, OFF_TOL_M.
# Landstuhl (West) ist die dritte, und zwar wegen genau EINER Luecke: seg10 haengt an OFF_TOL_M. Ohne diese
# Tour deckt der Test die Schwelle nicht ab -- nachgemessen, nicht vermutet: `NTC_OFF_TOL_M=0` liess die
# Suite mit den ersten beiden Touren vollstaendig gruen.
# Felsenwanderweg Rodalben und Kurztour 3 Schopp kamen 2026-08-20 dazu, jede fuer genau eine Schwelle, die
# ohne sie nicht festgenagelt ist -- nachgemessen, nicht vermutet: mit den ersten drei Touren allein liessen
# `NTC_MAX_TRIM_ABS_M=99999` und `NTC_RELAX_DOUBLE_M=60` die Suite vollstaendig gruen. Der Felsenwanderweg
# haelt den Fall, in dem eine Loesung 1362m eines 5273m langen Abschnitts wegschnitt (Bruchteil-Grenze
# eingehalten, absolut indiskutabel); Schopp den Fall, in dem die EINZIGE Loesung 89,5m doppelt faehrt und
# eine offene Luecke die schlechtere Wahl waere.
TOURS = [("pw_rodalben_felsentrails", "4e14f36"),
         ("pw_kurztour_6_landstuhl_ost", "100f6ee~1"),
         ("pw_kurztour_6_landstuhl_west", "100f6ee~1"),
         ("pw_felsenwanderweg_rodalben", "495711f"),
         ("pw_kurztour_3_schopp", "100f6ee~1")]


def region_at(rev):
    out = subprocess.run(["git", "cat-file", "blob", rev + ":" + REG],
                         capture_output=True, cwd=ROOT)
    return json.loads(out.stdout.decode("utf-8"))


def build(loop, rev):
    d = region_at(rev)
    s = d["trailSegments"][loop]
    n = len(s)
    names = {t["id"]: t["name"] for t in d["lineTrails"]}
    gaps = [i for i in range(n)
            if haversine_m(s[i]["coords"][-1], s[(i + 1) % n]["coords"][0]) > 2]
    N._WAYS = None
    N.prefetch([q for seg in s for q in seg["coords"]])
    # Genau die Wege, die `fetch()` fuer irgendeine dieser Luecken zurueckgeben kann -- nicht mehr, nicht
    # weniger. Eine engere Auswahl (etwa "nah an der Tour") waere eine ANDERE Wegemenge und der Test wuerde
    # etwas anderes pruefen als der echte Lauf.
    need = set()
    for i in gaps:
        for w in N.fetch(s[i]["coords"][-1], s[(i + 1) % n]["coords"][0]):
            need.add(w["id"])
    ways = [{"geom": [list(q) for q in w["geom"]], "tags": w["tags"], "id": w["id"]}
            for w in N._WAYS if w["id"] in need]
    used = {t["id"]: names[t["id"]] for t in d["lineTrails"]
            if any(x.get("trailId") == t["id"] for x in s)}
    path = os.path.join(FIX, "ntc_%s.json.gz" % loop)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"loop": loop, "rev": rev, "ways": ways, "names": used,
                   "segments": [{"coords": [list(q) for q in x["coords"]],
                                 "trailId": x.get("trailId"), "liftId": x.get("liftId")} for x in s]}, fh)
    return path, len(gaps), len(ways), os.path.getsize(path)


def load(loop):
    with gzip.open(os.path.join(FIX, "ntc_%s.json.gz" % loop), "rt", encoding="utf-8") as fh:
        return json.load(fh)


def run_fixture(loop):
    """Das Verfahren OHNE Netz auf die mitgelieferten Wege anwenden und messen, was herauskommt.

    Benutzt `close_gaps()` aus dem Werkzeug selbst -- also dieselbe Annahmelogik (weglos-Tor,
    Verhaeltnismaessigkeit, Reihenfolge) wie ein echter Lauf, keine nachgebaute Kopie. Ein Test, der die
    Regeln nachbaut, kann nicht merken, wenn sie sich aendern.
    """
    fx = load(loop)
    N._WAYS = [{"geom": [tuple(q) for q in w["geom"]], "tags": w["tags"], "id": w["id"]}
               for w in fx["ways"]]
    s = [{"coords": [list(q) for q in x["coords"]], "trailId": x.get("trailId")} for x in fx["segments"]]
    for x, src in zip(s, fx["segments"]):
        if src.get("liftId"):
            x["liftId"] = src["liftId"]
    n = len(s)
    gaps = [i for i in range(n) if haversine_m(s[i]["coords"][-1], s[(i + 1) % n]["coords"][0]) > 2]
    recs = N.close_gaps(s, gaps, names=fx["names"], write=True)
    trails = {}
    for x in s:
        if x.get("trailId"):
            k = fx["names"].get(x["trailId"], x["trailId"])
            trails[k] = trails.get(k, 0) + N.C.line_len_m(x["coords"])
    return {"gaps": len(gaps),
            "closed": sum(1 for r in recs if r["applied"]),
            "still_open": sorted(round(haversine_m(s[i]["coords"][-1], s[(i + 1) % len(s)]["coords"][0]), 1)
                                 for i in range(len(s))
                                 if haversine_m(s[i]["coords"][-1], s[(i + 1) % len(s)]["coords"][0]) > 2),
            "segments": len(s),
            "length_m": round(sum(N.C.line_len_m(x["coords"]) for x in s)),
            "cases": {k: sum(1 for r in recs if (r["applied"] or "").split("(")[0] == k)
                      for k in sorted({(r["applied"] or "").split("(")[0] for r in recs if r["applied"]})},
            "trail_m": {k: round(v) for k, v in sorted(trails.items())},
            "relaxed": sorted(r["seg"] for r in recs if r.get("relaxed")),
            "per_gap": [{"seg": r["seg"], "gap": r["gap"], "applied": r["applied"],
                         "bridge": r.get("bridge"), "trim": r.get("trim"),
                         "relaxed": bool(r.get("relaxed")),
                         "skipped": r.get("skipped")} for r in recs]}


def write_baseline():
    out = {}
    for loop, _rev in TOURS:
        out[loop] = run_fixture(loop)
    path = os.path.join(FIX, "ntc_baseline.json")
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    return path, out


if __name__ == "__main__":
    if "--baseline" in sys.argv:
        path, out = write_baseline()
        for loop, r in sorted(out.items()):
            print("%-34s %2d Luecken -> %2d geschlossen, offen %s, %d Seg, %.2f km  %s"
                  % (loop.replace("pw_", ""), r["gaps"], r["closed"], r["still_open"],
                     r["segments"], r["length_m"] / 1000.0,
                     " ".join("%s:%d" % (k.split("_")[0], v) for k, v in sorted(r["cases"].items()))))
        print("geschrieben: %s" % path)
    else:
        for loop, rev in TOURS:
            p, g, w, size = build(loop, rev)
            print("%-34s %2d Luecken, %4d Wege -> %s (%.0f KB)"
                  % (loop.replace("pw_", ""), g, w, os.path.basename(p), size / 1024))
        print("jetzt noch: python tools/make_ntc_fixture.py --baseline")
