# -*- coding: utf-8 -*-
"""nearbyTrailConnector -- schliesst eine Trailrunden-Luecke nach dem Verfahren, das in
docs/nearby-trail-connector.md fallweise erarbeitet und vom Nutzer bestaetigt wurde.

Das ist KEIN allgemeines Verfahren, sondern die Kodierung der bisher bestaetigten Faelle. Jeder neue Fall
wird erst einzeln geprueft und dann hier ergaenzt -- die Strategie des Nutzers (2026-08-16): "Wir gehen
solange einzelne Faelle durch, bis es einigermassen sicher klappt."

    python tools/nearby_trail_connector.py --gap 3 4 5 6            # Trockenlauf, nur Zahlen
    python tools/nearby_trail_connector.py --gap 3 --write

Reihenfolge der Faelle (aus den bestaetigten Loesungen abgeleitet):
  1. EIN verketteter Weg erreicht beide Seiten          -> ihm folgen           (seg34, seg2)
  2. Weg unter einem Endpunkt trifft die andere LINIE   -> folgen + kappen      (seg0)
  3. Zwei verschiedene Wege                             -> bis zum Schnittpunkt (seg1)

Vor allem anderen werden **Way-Objekte zu durchgehenden Wegen verkettet** -- OSM zerlegt eine Strasse in
mehrere Objekte, und ohne diesen Schritt sehen loesbare Faelle unloesbar aus (am Hilschberghaus: 5 Objekte
einer Strasse). Zugangs-Tags werden hier NICHT gefiltert: ein Weg, auf dem die Tour ohnehin schon liegt,
darf nicht wegen `vehicle=forestry` o.ae. ausgeschlossen werden -- genau das hatte fuenf Anlaeufe blockiert.
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import haversine_m, overpass, write_region, ElevationLookup, build_profile
import close_loop_gaps as C
from gap_variants import point_to_line, _intersect
from pfaelzerwald_rederive_loops import add_dist_range, concat_ok

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = os.path.join(ROOT, "Trailmap App", "regions", "pfaelzerwald.json")

# 15m, nicht 8m: der Nutzer hat darauf hingewiesen, dass ein Trailabschnitt regelmaessig 10-15m neben
# seinem OSM-Weg laeuft -- das ist GPS-Ungenauigkeit, kein anderer Weg. Bei 8m fiel seg14 durch ALLE vier
# Faelle, obwohl die Zuordnung voellig eindeutig war (Trail auf einem path, Connector auf einem track,
# 11,9m auseinander, naechster Konkurrent 106m weg).
ON_WAY_M = 15.0     # "der Endpunkt liegt auf diesem Weg"
MEET_M = 15.0       # "der Weg trifft die Linie der anderen Seite"
BBOX_PAD_M = 500.0
# Verhaeltnismaessigkeit: eine 23m-Luecke darf nicht 416m Trail kosten. Ohne diese Grenze gewinnt eine
# formal saubere (weglos 0m) Loesung, die den halben Trail wegschneidet -- bei seg4/seg6 genau passiert.
# 4.0, nicht 3.0: die vom Nutzer bestaetigte Hilschberghaus-Loesung kappt 186m bei 61,5m Luecke, also
# Faktor 3,02 -- sie wurde von der 3,0-Grenze um 1,5 Meter verworfen. Genau daran ist der erste
# Stabilitaetstest gescheitert. Die unsinnigen Faelle lagen bei Faktor 18 und 3,8 und werden weiter
# abgefangen; letzterer zusaetzlich dadurch, dass weniger Kappung bei gleichem weglos jetzt vorgeht.
MAX_TRIM_FACTOR = 4.0    # gekappte Meter, bezogen auf die Luftlinie der Luecke
MAX_BRIDGE_FACTOR = 6.0  # Brueckenlaenge, bezogen auf die Luftlinie

# --- Fall 4: Projektion des Trailabschnitts auf "seinen" OSM-Weg -------------------------------------
# Nutzer-Hinweis (2026-08-16): ein Trailabschnitt laeuft oft NICHT exakt auf seinem OSM-Weg, ist ihm aber
# eindeutig zuzuordnen, weil kein anderer Weg in der Naehe liegt und keiner abzweigt. 10-15m Versatz sind
# normale GPS-Ungenauigkeit. Fuer die VERBINDUNG darf man deshalb mit der Projektion rechnen.
#
# ZWEI HARTE BEDINGUNGEN:
#  * Die Trail-Geometrie wird NIE veraendert -- sonst weicht der Abschnitt in der Tour von der Geometrie des
#    eigenstaendigen Trails ab, und genau diese Invariante darf nicht brechen.
#  * Projiziert wird nur bei EINDEUTIGER Zuordnung. "Wenn mehrere Wege oder Abzweigungen in der Naehe sind,
#    wird das schwer" -- dann liefert dieser Fall nichts.
PROJ_MAX_MEAN_M = 15.0     # so weit darf der Abschnitt im Mittel neben seinem Weg liegen
PROJ_MIN_RATIO = 3.0       # der zweitbeste Weg muss mindestens so viel weiter weg sein
PROJ_MIN_SECOND_M = 40.0   # ... und zusaetzlich absolut so weit
PROJ_NO_BRANCH_M = 25.0    # am Anschlusspunkt darf kein anderer Weg so nah abzweigen

# FESTE REGEL (Nutzer, 2026-08-17): "Bitte immer die Region komplett laden, wenn unser TrailConnector laeuft."
# Ein einziger Overpass-Abruf fuer die GANZE Tour statt einer pro Luecke -- pro Fall 20-80s Wartezeit war der
# eigentliche Bremsklotz ("Komoot macht das in Echtzeit"), 1 min 35 s wurden dadurch zu 0,9 s. `main()` ruft
# prefetch() unbedingt vor der ersten Luecke auf; das Ergebnis liegt als Datei daneben und wird
# wiederverwendet. `fetch()` schneidet daraus nur noch lokal aus und geht NIE ins Netz, solange _WAYS steht.
# Wer solve() direkt benutzt, muss prefetch() selbst vorher aufrufen -- sonst faellt fetch() auf eine
# Einzelabfrage pro Luecke zurueck und alles ist wieder langsam.
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".tmpwork")
_WAYS = None


def prefetch(all_coords, pad_m=BBOX_PAD_M, cache=None):
    """Alle Wege im Umfeld der kompletten Tour EINMAL holen und ablegen.

    Der Cache-Dateiname wird aus der BOUNDING BOX abgeleitet. Vorher hiess die Datei fuer jede Tour gleich,
    sodass ein Lauf auf einer anderen Tour stillschweigend die Wege der vorigen benutzt haette -- also Wege
    aus einer voellig anderen Ecke des Waldes. Bisher habe ich die Datei zwischen den Touren von Hand
    geloescht; das faellt bei der ersten Unachtsamkeit auf, und zwar in Form von Bruecken, die aus dem
    Nichts kommen. Deshalb jetzt pro Gebiet eine eigene Datei.
    """
    global _WAYS
    lat = [p[0] for p in all_coords]
    lon = [p[1] for p in all_coords]
    dlat = pad_m / 111320.0
    dlon = pad_m / 80000.0
    bbox = "%.6f,%.6f,%.6f,%.6f" % (min(lat) - dlat, min(lon) - dlon, max(lat) + dlat, max(lon) + dlon)
    if cache is None:
        import hashlib
        key = hashlib.md5(bbox.encode("utf-8")).hexdigest()[:12]
        cache = os.path.join(CACHE_DIR, "osm_ways_%s.json" % key)
    if os.path.exists(cache):
        _WAYS = json.load(open(cache, encoding="utf-8"))
        _WAYS = [{"geom": [tuple(q) for q in w["geom"]], "tags": w["tags"], "id": w["id"]} for w in _WAYS]
        return _WAYS
    q = '[out:json][timeout:180];way["highway"](%s);out tags geom;' % bbox
    W = [{"geom": [(round(p["lat"], 7), round(p["lon"], 7)) for p in e.get("geometry", [])],
          "tags": e.get("tags", {}) or {}, "id": e.get("id")} for e in overpass(q).get("elements", [])]
    _WAYS = [w for w in W if len(w["geom"]) >= 2]
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump([{"geom": [list(q) for q in w["geom"]], "tags": w["tags"], "id": w["id"]} for w in _WAYS],
              open(cache, "w", encoding="utf-8"))
    return _WAYS


def merge_roads(ways, tol=1.0):
    """Way-Objekte gleichen Typs und Namens, die sich an einem Endpunkt beruehren, zu EINEM Weg verketten."""
    items = [{"geom": [tuple(q) for q in w["geom"]], "tags": w["tags"], "ids": [w.get("id")]} for w in ways]
    changed = True
    while changed:
        changed = False
        for i in range(len(items)):
            for k in range(len(items)):
                if i == k:
                    continue
                u, v = items[i], items[k]
                if u["tags"].get("highway") != v["tags"].get("highway"):
                    continue
                if u["tags"].get("name") != v["tags"].get("name"):
                    continue
                for ue, ve, ng in ((u["geom"][-1], v["geom"][0], u["geom"] + v["geom"][1:]),
                                   (u["geom"][-1], v["geom"][-1], u["geom"] + list(reversed(v["geom"]))[1:]),
                                   (u["geom"][0], v["geom"][-1], v["geom"] + u["geom"][1:]),
                                   (u["geom"][0], v["geom"][0], list(reversed(v["geom"])) + u["geom"][1:])):
                    if haversine_m(ue, ve) <= tol:
                        u["geom"] = ng
                        u["ids"] += v["ids"]
                        items.pop(k)
                        changed = True
                        break
                if changed:
                    break
            if changed:
                break
    return items


def fetch(a, b):
    """Wege im Umfeld dieser einen Luecke -- aus dem vorab geholten Regionsbestand geschnitten, ohne Netz."""
    if _WAYS is None:
        q = '[out:json][timeout:60];way["highway"](%s);out tags geom;' % C.pad_bbox(a, b, BBOX_PAD_M)
        W = [{"geom": [(round(p["lat"], 7), round(p["lon"], 7)) for p in e.get("geometry", [])],
              "tags": e.get("tags", {}) or {}, "id": e.get("id")} for e in overpass(q).get("elements", [])]
        return [w for w in W if len(w["geom"]) >= 2]
    dlat = BBOX_PAD_M / 111320.0
    dlon = BBOX_PAD_M / 80000.0
    lo_lat, hi_lat = min(a[0], b[0]) - dlat, max(a[0], b[0]) + dlat
    lo_lon, hi_lon = min(a[1], b[1]) - dlon, max(a[1], b[1]) + dlon
    return [w for w in _WAYS
            if any(lo_lat <= p[0] <= hi_lat and lo_lon <= p[1] <= hi_lon for p in w["geom"])]


def _clean(pts):
    out = [list(pts[0])]
    for p in pts[1:]:
        if haversine_m(out[-1], p) > 0.5:
            out.append(list(p))
    return out


def solve(A, B, trail_A=False, trail_B=False):
    """Beste Loesung fuer die Luecke zwischen A (endet) und B (beginnt), Kandidaten nach Kosten sortiert.
    trail_A/trail_B sagen, welche Seite ein benannter Trailabschnitt ist -- nur dort darf Fall 5 kappen."""
    a, b = A[-1], B[0]
    W = fetch(a, b)
    idx = C.WayIndex(W)
    M = merge_roads(W)
    beeline = haversine_m(a, b)
    out = []

    # Der Querversatz an den beiden Anschluessen ist GPS-Rauschen zwischen Trail-Aufzeichnung und OSM-Weg,
    # kein Umweg -- der Nutzer hat ihn ausdruecklich akzeptiert ("Die Spruenge sind zwar unschoen, aber
    # unvermeidbar mit der Praemisse, dass wir Trailgeo nicht veraendern"). Er wird deshalb aus dem
    # weglos-Mass herausgerechnet: nur was DAZWISCHEN abseits der Wege laeuft, ist ein echter Mangel.
    # Ohne diese Trennung lehnte die 5m-Toleranz vier vom Nutzer bestaetigte Loesungen ab, alle mit 12-13m
    # -- also genau der Versatz und nichts sonst.
    def off_way_core(bridge):
        if len(bridge) < 3:
            return 0.0
        inner = bridge[1:-1]
        if len(inner) < 2:
            return 0.0
        return C.off_way_metres(inner, idx)

    def ends_off(bridge):
        """Der Querversatz an den beiden Anschluessen -- Trail-Aufzeichnung gegen OSM-Weg."""
        return C.off_way_metres(bridge, idx) - off_way_core(bridge)

    def score(name, bridge, newA, newB, extra):
        trimmed = 0.0
        if len(newA) < len(A):
            trimmed += C.line_len_m(A[len(newA) - 1:])
        if len(newB) < len(B):
            trimmed += C.line_len_m(B[:len(B) - len(newB) + 1])
        out.append({"name": name, "bridge": bridge, "newA": newA, "newB": newB,
                    "len": C.line_len_m(bridge),
                    # weglos = was INNEN abseits der Wege laeuft, plus der Teil des Anschluss-Versatzes, der
                    # ueber die GPS-Ungenauigkeit hinausgeht. 13m Versatz sind Rauschen und zaehlen nicht;
                    # die 21,9m querab am Hilschberghaus sind ein echtes Gelaendestueck und zaehlen -- genau
                    # der Unterschied, den der Nutzer auf der Karte gesehen hat.
                    "off": off_way_core(bridge) + max(0.0, ends_off(bridge) - PROJ_MAX_MEAN_M),
                    "off_ends": round(ends_off(bridge), 1),
                    "trim": trimmed, "beeline": beeline, "extra": extra})

    # --- Fall 1: EIN verketteter Weg erreicht beide Seiten
    for m in sorted(M, key=lambda m: point_to_line(a, m["geom"])[0]):
        g = [list(q) for q in m["geom"]]
        da, db = point_to_line(a, g)[0], point_to_line(b, g)[0]
        if da <= ON_WAY_M and db <= ON_WAY_M:
            mid, _x, _y = C.slice_way_between(g, a, b)
            score("1_ein-Weg-beide-Seiten", _clean([a] + mid + [b]), A, B,
                  "highway=%s, %d Teilstuecke, a %.1fm / b %.1fm" % (m["tags"].get("highway"), len(m["ids"]), da, db))
            break

    # --- Fall 2: Weg unter einem Endpunkt trifft die LINIE der anderen Seite -> dort kappen
    for anchor_is_b in (True, False):
        anchor, other = (b, A) if anchor_is_b else (a, B)
        cands = [m for m in M if point_to_line(anchor, m["geom"])[0] <= ON_WAY_M]
        if not cands:
            continue
        m = min(cands, key=lambda m: min(point_to_line(q, other)[0] for q in m["geom"]))
        g = [list(q) for q in m["geom"]]
        k, dmeet = min(((k, point_to_line(q, other)[0]) for k, q in enumerate(g)), key=lambda x: x[1])
        if dmeet > MEET_M:
            continue
        cut = point_to_line(g[k], other)[1]
        if anchor_is_b:
            newA, newB = A[:cut + 1], B
        else:
            newA, newB = A, B[cut:]
        mid, _x, _y = C.slice_way_between(g, newA[-1], newB[0])
        score("2_Weg-folgen-und-kappen(%s)" % ("A" if anchor_is_b else "B"),
              _clean([newA[-1]] + mid + [newB[0]]), newA, newB,
              "highway=%s, Treffer %.1fm" % (m["tags"].get("highway"), dmeet))

    # --- Fall 3: zwei verschiedene Wege -> echter Schnittpunkt
    ma = min(M, key=lambda m: point_to_line(a, m["geom"])[0])
    mb = min(M, key=lambda m: point_to_line(b, m["geom"])[0])
    if ma is not mb and point_to_line(a, ma["geom"])[0] <= ON_WAY_M and point_to_line(b, mb["geom"])[0] <= ON_WAY_M:
        ga, gb = [list(q) for q in ma["geom"]], [list(q) for q in mb["geom"]]
        X = None
        for i in range(len(ga) - 1):
            for k in range(len(gb) - 1):
                x = _intersect(ga[i], ga[i + 1], gb[k], gb[k + 1])
                if x:
                    X = x
                    break
            if X:
                break
        if X:
            l1, _x, _y = C.slice_way_between(ga, a, X)
            l2, _x, _y = C.slice_way_between(gb, X, b)
            score("3_Schnittpunkt", _clean([a] + l1 + l2 + [b]), A, B,
                  "highway=%s + %s" % (ma["tags"].get("highway"), mb["tags"].get("highway")))

    # --- Fall 4: Trailabschnitt auf seinen Weg projizieren (Geometrie bleibt unveraendert)
    for trail_is_A in (True, False):
        trail = A if trail_is_A else B
        other_end = b if trail_is_A else a
        t_end = a if trail_is_A else b
        rows = []
        for m in M:
            ds = [point_to_line(p, m["geom"])[0] for p in trail]
            rows.append((sum(ds) / len(ds), m))
        rows.sort(key=lambda r: r[0])
        if len(rows) < 2:
            continue
        mean, m = rows[0]
        second = rows[1][0]
        if mean > PROJ_MAX_MEAN_M:
            continue
        if second < max(PROJ_MIN_SECOND_M, PROJ_MIN_RATIO * mean):
            continue                      # nicht eindeutig zuzuordnen -> kein Fall 4
        g = [list(q) for q in m["geom"]]
        _i, _t, P, dproj = C.project_onto_way(g, t_end)
        # zweigt am Anschlusspunkt ein anderer Weg ab?
        branch = [x for x in M if x is not m and point_to_line(P, x["geom"])[0] <= PROJ_NO_BRANCH_M]
        if branch:
            continue
        # von P aus dem Weg folgen bis zum anderen Endpunkt (der muss auf diesem Weg liegen)
        if point_to_line(other_end, g)[0] > ON_WAY_M:
            continue
        mid, _x, _y = C.slice_way_between(g, P, other_end)
        bridge = _clean(([t_end, P] + mid + [other_end]) if trail_is_A
                        else list(reversed([t_end, P] + mid + [other_end])))
        score("4_Projektion(%s)" % ("A" if trail_is_A else "B"), bridge, A, B,
              "highway=%s, Abschnitt Ø %.1fm daneben, Versatz %.1fm, 2. Weg %.0fm"
              % (m["tags"].get("highway"), mean, dproj, second))

    # --- Fall 5: Kette aus mehreren Wegen ueber echte Kreuzungen. Nur als NACHRANG, wenn Fall 1-4 nichts
    # Brauchbares liefern -- die Kettensuche ist deutlich teurer als die uebrigen Faelle.
    def acceptable(r):
        return r["off"] <= 0 and r["trim"] <= MAX_TRIM_FACTOR * max(beeline, 1.0)             and r["len"] <= MAX_BRIDGE_FACTOR * max(beeline, 1.0)
    if not any(acceptable(r) for r in out):
        for bridge, kinds in chain_bridges(A, B, M, idx):
            score("5_Wegekette", bridge, A, B, " -> ".join(str(k) for k in kinds))
        for trail_is_A in ([True] if trail_A else []) + ([False] if trail_B else []):
            for bridge, nA, nB, kinds, dmeet in chain_bridges_trim(A, B, M, idx, trail_is_A=trail_is_A):
                score("5_Wegekette+kappen(%s)" % ("A" if trail_is_A else "B"), bridge, nA, nB,
                      "%s, Treffer %.1fm" % (" -> ".join(str(k) for k in kinds), dmeet))

    if not out:
        return None
    for r in out:
        bad = []
        if r["trim"] > MAX_TRIM_FACTOR * max(beeline, 1.0):
            bad.append("kappt %.0fm bei %.0fm Luecke" % (r["trim"], beeline))
        if r["len"] > MAX_BRIDGE_FACTOR * max(beeline, 1.0):
            bad.append("Bruecke %.0fm bei %.0fm Luecke" % (r["len"], beeline))
        r["reject"] = "; ".join(bad)
        # Bei Fall 4 ist der Querversatz zum Trail bewusst in Kauf genommener GPS-Versatz, kein Umweg --
        # er wird getrennt gemeldet statt die Loesung ueber die weglos-Schwelle zu heben.
        if r["name"].startswith("4_"):
            r["off_note"] = "davon %.0fm Querversatz zum Trail" % min(r["off"], PROJ_MAX_MEAN_M)
    # weglos zaehlt zuerst, dann Reihenfolge der Faelle, dann kurze Bruecke -- Unverhaeltnismaessige zuletzt
    # Rangfolge: verworfene zuletzt; dann weglos (das eigentliche Qualitaetsmass); dann WENIGER Kappung,
    # weil eine Loesung ohne Kappung eine reale Trail-Geometrie erhaelt; dann Fallnummer, dann Laenge.
    # Die Kappung erst nach weglos zu werten ist wichtig: am Hilschberghaus ist die Loesung MIT der
    # groesseren Kappung die richtige, weil nur sie durchgehend auf der Strasse bleibt.
    # Rangfolge: verworfene zuletzt; dann weglos; dann Fallnummer; dann kurze Bruecke. Die Kappung NICHT
    # vor die Laenge stellen -- damit hatte der Neulauf bei seg0 eine 637m-Kette ohne Kappung der bestaetigten
    # 406m-Loesung mit 230m Kappung vorgezogen. Kappung ist die Reparatur, kein Kostenfaktor; sie wird nur
    # noch ueber MAX_TRIM_FACTOR begrenzt.
    out.sort(key=lambda r: (bool(r["reject"]), round(r["off"]), r["name"][0], r["len"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=REGION)
    ap.add_argument("--loop", default="pw_rodalben_felsentrails")
    ap.add_argument("--gap", type=int, nargs="+", required=True, help="Segment-Index i der Luecke i->i+1")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    d = json.load(open(args.region, encoding="utf-8"))
    s = d["trailSegments"][args.loop]
    prefetch([q for seg in s for q in seg["coords"]])
    names = {t["id"]: t["name"] for t in d["lineTrails"]}
    chosen = {}
    for i in sorted(args.gap, reverse=True):
        j = (i + 1) % len(s)
        A, B = s[i]["coords"], s[j]["coords"]
        kind = lambda x: names.get(x.get("trailId"), "?")[:22] if x.get("trailId") else "CONNECTOR"
        print("seg%-2d %6.1fm  %-22s -> %s" % (i, haversine_m(A[-1], B[0]), kind(s[i]), kind(s[j])))
        res = solve(A, B, trail_A=bool(s[i].get("trailId")), trail_B=bool(s[j].get("trailId")))
        if not res:
            print("    keine Loesung gefunden")
            continue
        for r in res:
            print("    %-28s Bruecke %4.0fm | weglos %3.0fm | kappt %4.0fm | %s%s"
                  % (r["name"], r["len"], r["off"], r["trim"], r["extra"],
                     ("   VERWORFEN: " + r["reject"]) if r["reject"] else ""))
        best = res[0]
        if best["off"] > 0:
            print("    -> weglos > 0, nichts angewendet")
            continue
        if best["reject"]:
            print("    -> unverhaeltnismaessig, nichts angewendet")
            continue
        chosen[i] = best
        if args.write:
            s[i]["coords"] = best["newA"]
            s[j]["coords"] = best["newB"]
            C.close_gap(s, i, j, [list(q) for q in best["bridge"][1:-1]], best["newA"][-1], best["newB"][0])
            print("    -> angewendet: %s" % best["name"])

    if args.write and chosen:
        line = [q for seg in s for q in seg["coords"]]
        assert concat_ok(line, s), "Verkettung verletzt"
        d["trailSegments"][args.loop] = add_dist_range(line, s)
        d["trailGeo"][args.loop] = line
        ele = ElevationLookup(os.path.join(ROOT, "Material", "elevation_cache.json"))
        prof, _g, _l = build_profile(line, ele([[q[0], q[1]] for q in line]))
        d["elevationProfiles"][args.loop] = prof
        write_region(args.region, d["lineTrails"], d["trailGeo"], d["elevationProfiles"],
                     places=d.get("places"), lifts=d.get("lifts"), trail_segments=d["trailSegments"])
        n = len(s)
        gaps = [haversine_m(s[k]["coords"][-1], s[(k + 1) % n]["coords"][0]) for k in range(n)]
        print("\ngeschrieben | %d Segmente, %.2f km, noch %d Luecken >2m"
              % (n, C.line_len_m(line) / 1000, sum(1 for x in gaps if x > 2)))




# --- Fall 5: Kette aus mehreren Wegen ueber ECHTE Kreuzungen -----------------------------------------
# Nutzer-Vorgabe fuer die zwei letzten Rodalben-Luecken (2026-08-16), beide auf der Karte eingezeichnet:
#   "von der Baumbuschstrasse den Pfad und dann auf die Forststrasse bis zum Trailanfang"
#   "am Bruderfelsen den Otto-Stolz-Pfad runter (gruener Trail wird frueher verlassen)"
# Beides sind Verbindungen ueber MEHRERE verschiedene Wege hintereinander -- Fall 1-4 koennen das nicht.
#
# Unterschied zum frueher verworfenen Netzwerk-Routing: der Graph hat als KNOTEN die verketteten Wege und
# als KANTEN nur echte Kreuzungen (gemeinsame Stuetzpunkte). Damit bleibt jeder Wegwechsel eine reale
# Abzweigung, und die Kette ist auf wenige Wechsel begrenzt -- kein Zusammenstueckeln kuerzester Kanten,
# das damals Umwege durch den Wald erzeugte.
MAX_CHAIN = 3          # so viele Wege darf eine Kette umfassen
JUNCTION_GRID = 5      # Nachkommastellen fuers Zusammenfallen von Stuetzpunkten (~1m)


def way_junctions(M):
    """(graph, nodes): graph[i] -> [(j, Kreuzungspunkt)], ueber gemeinsame Stuetzpunkte der verketteten Wege."""
    cells = {}
    for i, m in enumerate(M):
        for q in m["geom"]:
            cells.setdefault((round(q[0], JUNCTION_GRID), round(q[1], JUNCTION_GRID)), set()).add(i)
    graph = {}
    for key, ws in cells.items():
        if len(ws) < 2:
            continue
        pt = (key[0], key[1])
        for i in ws:
            for j in ws:
                if i != j:
                    graph.setdefault(i, []).append((j, pt))
    return graph


def chain_bridges(A, B, M, idx, trim_trail_side=None):
    """Alle Bruecken, die ueber eine Kette von bis zu MAX_CHAIN Wegen von A's Ende zu B's Anfang fuehren.
    trim_trail_side: 'A' oder 'B' -> auf dieser Seite darf der Trail gekappt werden, wo die Kette ihn trifft."""
    a, b = A[-1], B[0]
    graph = way_junctions(M)
    starts = [i for i, m in enumerate(M) if point_to_line(a, m["geom"])[0] <= ON_WAY_M]
    goals = {i for i, m in enumerate(M) if point_to_line(b, m["geom"])[0] <= ON_WAY_M}
    out = []
    for s0 in starts:
        # Breitensuche ueber Wege, Pfad = [(way, Einstiegspunkt)]
        queue = [(s0, [(s0, None)])]
        seen = {s0}
        while queue:
            cur, path = queue.pop(0)
            if cur in goals and len(path) > 1:
                pts, ok = [], True
                for k, (w, entry) in enumerate(path):
                    g = [list(q) for q in M[w]["geom"]]
                    frm = a if k == 0 else entry
                    to = b if k == len(path) - 1 else path[k + 1][1]
                    seg, _x, _y = C.slice_way_between(g, frm, to)
                    if seg is None:
                        ok = False
                        break
                    pts += seg
                if ok:
                    out.append((_clean([a] + pts + [b]), [M[w]["tags"].get("highway") for w, _e in path]))
            if len(path) >= MAX_CHAIN:
                continue
            for nxt, jp in graph.get(cur, []):
                if nxt in seen:
                    continue
                seen.add(nxt)
                queue.append((nxt, path + [(nxt, jp)]))
    return out


def chain_bridges_trim(A, B, M, idx, trail_is_A=True):
    """Wie chain_bridges, aber die Kette muss nicht den ENDPUNKT des Trails erreichen, sondern seine LINIE --
    der Trail wird dort gekappt. Nutzer-Vorgabe fuer die Bruderfelsen-Luecke: "gruener Trail wird frueher
    verlassen", d.h. der Anschluss liegt weiter innen auf dem Trail, nicht an seinem aufgezeichneten Ende."""
    a, b = A[-1], B[0]
    trail = A if trail_is_A else B
    start_pt = b if trail_is_A else a
    graph = way_junctions(M)
    starts = [i for i, m in enumerate(M) if point_to_line(start_pt, m["geom"])[0] <= ON_WAY_M]
    out = []
    for s0 in starts:
        queue = [(s0, [(s0, None)])]
        seen = {s0}
        while queue:
            cur, path = queue.pop(0)
            g = [list(q) for q in M[cur]["geom"]]
            k, dmeet = min(((k, point_to_line(q, trail)[0]) for k, q in enumerate(g)), key=lambda x: x[1])
            if dmeet <= MEET_M:
                cut = point_to_line(g[k], trail)[1]
                pts, ok = [], True
                for n, (w, entry) in enumerate(path):
                    gg = [list(q) for q in M[w]["geom"]]
                    frm = start_pt if n == 0 else entry
                    to = g[k] if n == len(path) - 1 else path[n + 1][1]
                    seg, _x, _y = C.slice_way_between(gg, frm, to)
                    if seg is None:
                        ok = False
                        break
                    pts += seg
                if ok:
                    if trail_is_A:
                        newA, newB = A[:cut + 1], B
                        bridge = _clean([newA[-1]] + list(reversed(pts)) + [b])
                    else:
                        newA, newB = A, B[cut:]
                        bridge = _clean([a] + pts + [newB[0]])
                    out.append((bridge, newA, newB,
                                [M[w]["tags"].get("highway") for w, _e in path], dmeet))
            if len(path) >= MAX_CHAIN:
                continue
            for nxt, jp in graph.get(cur, []):
                if nxt in seen:
                    continue
                seen.add(nxt)
                queue.append((nxt, path + [(nxt, jp)]))
    return out


if __name__ == "__main__":
    main()
