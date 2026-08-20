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
# 20m, nicht 15m: bei Kurztour 6 Landstuhl (Ost) verfehlten ZWEI unabhaengige Faelle die 15m-Grenze knapp
# und fielen damit aus der Kandidatenerzeugung heraus -- seg8 mit 15,9m (der Pfad, auf dem "Steps
# Heidenfelsen" ueber seine ganze Laenge laeuft, Mittel 14,1m) und seg14 mit 15,2m (ein Pfad, der mit 0,0m
# unter dem einen Ende liegt und die andere Seite auf 15,2m erreicht, Fall 1, Kappung 0). Beide bekamen
# stattdessen eine viel schlechtere Loesung ueber einen 41m entfernten Forstweg bzw. eine 506m-Kette. Das
# Tor ist GPS-Rauschtoleranz, kein Qualitaetsurteil -- letzteres faellt das Mass "weglos", das einen
# Anschluss-Versatz ueber 15m weiterhin anrechnet, ein 20m-Sprung kostet dort also 5m und verliert gegen
# jeden saubereren Kandidaten. Nur wer ohne dieses Tor gar nicht erst geprueft wird, kann nie gewinnen.
ON_WAY_M = 20.0     # "der Endpunkt liegt auf diesem Weg"
MEET_M = 20.0       # "der Weg trifft die Linie der anderen Seite"
BBOX_PAD_M = 500.0
# Verhaeltnismaessigkeit: eine 23m-Luecke darf nicht 416m Trail kosten. Ohne diese Grenze gewinnt eine
# formal saubere (weglos 0m) Loesung, die den halben Trail wegschneidet -- bei seg4/seg6 genau passiert.
# 4.0, nicht 3.0: die vom Nutzer bestaetigte Hilschberghaus-Loesung kappt 186m bei 61,5m Luecke, also
# Faktor 3,02 -- sie wurde von der 3,0-Grenze um 1,5 Meter verworfen. Genau daran ist der erste
# Stabilitaetstest gescheitert. Die unsinnigen Faelle lagen bei Faktor 18 und 3,8 und werden weiter
# abgefangen; letzterer zusaetzlich dadurch, dass weniger Kappung bei gleichem weglos jetzt vorgeht.
MAX_TRIM_FACTOR = 4.0    # gekappte Meter, bezogen auf die Luftlinie der Luecke
MAX_BRIDGE_FACTOR = 6.0  # Brueckenlaenge, bezogen auf die Luftlinie
# Die Grenze oben bezieht die Kappung nur auf die LUECKE -- nicht auf die eigene Laenge des Segments. Damit
# durfte bei Kurztour 6 Landstuhl (Ost) eine 133m-Luecke 242m kappen, und weil "Steps Heidenfelsen" genau
# 242m lang war, loeste sich ein kompletter benannter Trailabschnitt auf (5 Punkte -> 1). Drei weitere
# Abschnitte derselben Tour verloren 36-57% ihrer Laenge. Ein Segment darf hoechstens die Haelfte seiner
# eigenen Laenge verlieren und nie unter zwei Punkte fallen -- ein Trailabschnitt, den die Tour laut Daten
# fahren soll, darf nicht per Reparatur verschwinden.
MAX_SEG_TRIM_FRACTION = 0.5
MIN_SEG_POINTS = 2

# Die Bruchteil-Grenze allein hat ein Loch, das erst ein LANGER Abschnitt aufdeckt: bei seg0 des
# Felsenwanderwegs Rodalben gewann eine Loesung, die 1362m von "Felsenweg Sued" wegschnitt, um eine 379m-
# Luecke zu schliessen -- 26 % eines 5273m-Abschnitts und Faktor 3,6 der Luecke, beide Grenzen also
# eingehalten. 1362m Trail sind trotzdem indiskutabel. Die groesste je vom Nutzer bestaetigte Kappung ist
# 235m, deshalb liegt die absolute Grenze bei 300m -- und zwar in BEIDEN Durchgaengen: der gelockerte lockert
# den Bruchteil (fuer kurze Abschnitte), nicht die Erlaubnis, einen Kilometer Trail zu loeschen.
MAX_TRIM_ABS_M = 300.0

# Fall 0, Ueberlappung (Nutzer, 2026-08-20, bei Kurztour 6 Landstuhl (Ost) gefunden): zwei aufeinander
# folgende Abschnitte koennen sich schon in der ORIGINALTOUR ueberlappen -- "Landstuhl Trail 2" endet 82m
# innerhalb von "Pavillonplatz Trail", beide durchlaufen dasselbe Stueck in derselben Richtung. Die Tour
# faehrt es dadurch zweimal: einmal als Ende des einen, dann rueckwaerts zum Anfang des anderen und wieder
# vorwaerts. Das ist keine Luecke, sondern ein Datenfehler, und er muss VOR allen Brueckenfaellen geprueft
# werden -- sonst baut Fall 1 eine formal saubere 82m-Bruecke rueckwaerts ueber genau diese Ueberlappung.
# Die Rangfolge rundet weglos auf ganze Meter, das Tor "weglos > 0" tat es nicht -- ein Kandidat mit 0,4m
# wurde als "0m" angezeigt, sortierte wie 0 und wurde dann als mangelhaft verworfen. Bei seg10 der Kurztour 6
# Landstuhl (West) blieb die Luecke deshalb offen, obwohl der Report eine saubere Loesung meldete. Unter
# einem halben Meter ist die Frage "liegt das noch auf dem Weg" ohnehin nicht entscheidbar -- die Genauigkeit
# der OSM-Geometrie selbst liegt darueber. EINE Schwelle fuer Tor, Vorauswahl und Sortierung.
OFF_TOL_M = 0.5

# ZWEITER DURCHGANG mit gelockerter Verhaeltnismaessigkeit -- gleiche Bauform wie Fall 5, der auch nur
# anlaeuft, wenn die einfacheren Faelle nichts Brauchbares liefern. Grund: Rodalben Felsentrails seg0 und
# seg34 sind vom Nutzer auf der Karte bestaetigt, aber unter den strengen Grenzen unerreichbar -- seg0
# braucht Bruecke 6,9x und Kappung 6,6x der Luecke, seg34 kappt 95m eines nur 150m langen Abschnitts (63%).
# Am Hilschberghaus (seg34) ist die Loesung MIT der groesseren Kappung die richtige, weil nur sie durchgehend
# auf der Strasse bleibt; die kappungsfreie Alternative dort ist eine 1459m-Kette, Faktor 66.
#
# Warum ein zweiter Durchgang und nicht einfach hoehere Grenzen: global gelockert wechselt Landstuhl (Ost)
# seg21 von einer Schnittpunkt-Loesung mit Faktor 1,02 und OHNE Kappung auf eine, die 76m von 151m eines
# benannten Abschnitts wegschneidet -- weil die Fallnummer vor der Brueckenlaenge rangiert und Fall 2 damit
# eine fast perfekte Fall-3-Loesung ueberholt, sobald er viel kappen darf. Die Fallhierarchie kodiert
# Vertrauen, nicht Laenge; sie umzusortieren war der andere Versuch und brach zwei weitere Stellen auf
# (darunter eine, die von Fall 1 auf Fall 3 rutschte -- fuer wenige Meter Bruecke schlechteres Vertrauen).
# Wer eine brauchbare strenge Loesung hat, behaelt sie also. Nur wo es keine gibt, wird gelockert.
#
# Die zwei Werte sind aus genau diesen zwei bestaetigten Faellen abgeleitet und liegen knapp darueber -- sie
# sind NICHT breit geprueft. Ein so geschlossener Uebergang wird deshalb als "gelockert" gemeldet und gehoert
# angesehen. MAX_TRIM_FACTOR faellt im zweiten Durchgang ganz weg: nachgemessen bringt er nichts, was
# MAX_SEG_TRIM_FRACTION (schuetzt den Abschnitt) und MAX_BRIDGE_FACTOR (schuetzt vor Umwegen) nicht schon
# leisten -- die Kopplung "gekappte Meter gegen Lueckengroesse" sagt ohnehin nichts darueber, ob das Kappen
# an dieser Stelle richtig ist.
RELAX_BRIDGE_FACTOR = 7.0
RELAX_SEG_TRIM_FRACTION = 0.65
# Doppelt fahren ist ein Mangel, eine offene Luecke ist schlimmer -- sie fuehrt den Fahrer an eine falsche
# Stelle, und genau darueber hat der Nutzer sich am deutlichsten beschwert. Bei seg5 der Kurztour 3 Schopp ist
# die einzige Loesung eine, die 89,5m doppelt faehrt; streng verworfen bliebe die Luecke offen. Der zweite
# Durchgang darf sie also nehmen, wird aber als "gelockert" gemeldet.
RELAX_DOUBLE_M = 120.0

# Oberhalb davon ist ein Uebergang keine Luecke mehr, die dieses Verfahren behandelt. Gefunden 2026-08-20 an
# den zwei Fernwegen des Pfaelzerwalds: "Ost-West-Passage" und "Trans Pfaelzerwald" sind PUNKT-ZU-PUNKT, ihr
# Anfang liegt 37 bzw. 38,6 km von ihrem Ende -- wer jede Tour als geschlossene Runde behandelt, sieht dort
# eine 37-km-"Luecke". Die zu ueberbruecken ist nicht bloss falsch, es laedt auch ein halbes Bundesland an
# OSM-Wegen. Die groesste ECHTE Luecke im ganzen Bestand ist 976m, also liegt die Grenze weit ueber allem
# Vorkommenden und trifft nur den Unsinn. So ein Uebergang wird gemeldet, nicht stillschweigend uebergangen:
# er kann auch bedeuten, dass die Tour zwei getrennte Teile hat, und das gehoert angesehen.
MAX_GAP_M = 1500.0

# Eine Bruecke, die auf der LINIE eines der beiden Abschnitte entlanglaeuft, laesst dieses Stueck zweimal
# fahren -- hin als Verbinder, zurueck als Trail. Das Mass weglos ist dafuer blind (alles liegt ja auf Wegen)
# und die Laenge auch (die Bruecke ist kaum laenger als die Luftlinie). Gefunden 2026-08-20 vom Nutzer auf
# der Karte, an drei Stellen der Ost-West-Passage gleichzeitig: dort lief die Bruecke zu 100 % auf der Linie
# des Abschnitts, zu dem sie fuehrt, also 87m, 73m und 85m doppelt. Seine Anweisung war jedes Mal dieselbe:
# "Da haette man doch nur den Pfad weiter gehen muessen, bis man auf den Brunnenwanderweg trifft. Der wird
# dann wieder etwas abgeschnitten." Das ist ein MANGEL, nicht nur ein Nachteil, deshalb verwirft er den
# Kandidaten und rangiert vor der Fallnummer: die Fallnummer sagt, wie gut die Zuordnung belegt ist, und
# nuetzt nichts, wenn die Route Unsinn faehrt. Die Toleranz ist grosszuegig, weil die ersten und letzten
# Meter einer Bruecke zwangslaeufig an den beiden Abschnitten liegen.
# Die Schwelle ist an den 71 bisher angewendeten Loesungen kalibriert, nicht geraten: 54 von ihnen liegen
# unter 10m, zehn zwischen 10 und 20, und dann bricht die Verteilung ab -- der hoechste Wert unter den vom
# Nutzer beanstandeten liegen bei 106,1m, 80m und 73,1m, die hoechste UNbeanstandete bei 51,2m -- 60m trennt
# die beiden Gruppen also exakt, und die Grenze steht nicht auf einer runden Zahl, weil sie an echten Werten
# haengt. Zwei Fehlversuche davor: 25m griff viel zu weit (Landstuhl (Ost) verlor drei Luecken ganz und sechs
# Abschnitte wurden gekappt), 50m verwarf noch die 51,2m-Loesung an einer Stelle, die niemand beanstandet hat.
#
# In der Sortierung steht das Mass HINTER der Fallnummer, aus demselben Grund wie die Kappung: vor die
# Fallnummer gestellt verschob es ein Dutzend Stellen, die niemand beanstandet hatte. Dahinter entscheidet es
# nur noch zwischen Kandidaten desselben Falls -- und dort muss es entscheiden: bei seg15 der Kurztour 6
# standen zwei Fall-2-Loesungen, 80m Bruecke ohne Kappung mit 38m doppelt gegen 37m Bruecke mit 64m Kappung
# und 18m doppelt. Nach Laenge allein gewinnt die erste; der Nutzer hat fuer diese Stelle ausdruecklich das
# Kappen verlangt ("Da muss man halt auch den Trail kuerzen").
MAX_DOUBLE_M = 60.0

OVERLAP_M = 20.0          # so nah muss ein Punkt an der Linie der anderen Seite liegen, um als "darauf" zu gelten
MIN_OVERLAP_M = 25.0      # kuerzere Ueberlappungen sind Endpunkt-Rauschen, kein doppelt gefahrenes Stueck

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

# Jede der Schwellen laesst sich per Umgebungsvariable ueberschreiben. Das ist kein Konfigurations-Feature,
# sondern das Werkzeug fuer die Pflichtaufgabe "ein geaendertes Verfahren MUSS nachgerechnet werden": nur so
# laesst sich eine Aenderung einzeln abschalten und messen, welche von mehreren gleichzeitigen Aenderungen
# eine bestaetigte Tour verschiebt, und nur so sind die Mutationen in tests/python/ntcregression.py ohne
# Quellcode-Aenderung nachvollziehbar. Ohne das bleibt bei einer Abweichung nur Raten.
# Der Block MUSS hinter ALLEN Konstanten stehen: er stand einmal vor PROJ_MAX_MEAN_M und den drei anderen
# Projektions-Schwellen, sodass eine Ueberschreibung von genau denen stillschweigend wirkungslos war -- die
# gefaehrlichste Variante, weil der Ablationslauf dann "kein Unterschied" meldet und man das glaubt.
for _k in ("ON_WAY_M", "MEET_M", "MAX_TRIM_FACTOR", "MAX_BRIDGE_FACTOR", "MAX_SEG_TRIM_FRACTION",
           "MIN_SEG_POINTS", "OFF_TOL_M", "OVERLAP_M", "MIN_OVERLAP_M", "PROJ_MAX_MEAN_M",
           "RELAX_BRIDGE_FACTOR", "RELAX_SEG_TRIM_FRACTION", "MAX_GAP_M", "MAX_DOUBLE_M",
           "MAX_TRIM_ABS_M", "RELAX_DOUBLE_M",
           "PROJ_MIN_RATIO", "PROJ_MIN_SECOND_M", "PROJ_NO_BRANCH_M", "MERGE_ONLY", "CASE1_FIRST_ONLY"):
    if os.environ.get("NTC_" + _k) is not None:
        globals()[_k] = float(os.environ["NTC_" + _k])
MERGE_ONLY = bool(globals().get("MERGE_ONLY", 0))
CASE1_FIRST_ONLY = bool(globals().get("CASE1_FIRST_ONLY", 0))

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


def prefetch_gaps(pairs, pad_m=BBOX_PAD_M):
    """Wie prefetch(), aber nur die Umgebung der LUECKEN -- ein Abruf, viele Boxen, als Vereinigung.

    Noetig fuer lange Touren: die Gesamtbox der "Trans Pfaelzerwald" ist 14 x 38 km = 534 km2, die
    Vereinigung ihrer Lueckenboxen nur 46 km2. Einmal `way["highway"]` ueber ein halbes Bundesland zu holen
    ist zehnmal so viel Daten fuer dieselbe Antwort.

    Das Ergebnis ist DASSELBE, was die Gesamtbox liefern wuerde, denn `fetch()` filtert ohnehin auf die Box
    der einzelnen Luecke mit demselben Rand -- und Overpass' Box-Filter und dieser Filter benutzen dasselbe
    Kriterium (ein Stuetzpunkt liegt darin). An einer bereits bestaetigten Tour nachgemessen: bytegleich.
    """
    global _WAYS
    dlat = pad_m / 111320.0
    dlon = pad_m / 80000.0
    boxes = sorted({"%.6f,%.6f,%.6f,%.6f" % (min(a[0], b[0]) - dlat, min(a[1], b[1]) - dlon,
                                             max(a[0], b[0]) + dlat, max(a[1], b[1]) + dlon)
                    for a, b in pairs})
    import hashlib
    cache = os.path.join(CACHE_DIR, "osm_ways_gaps_%s.json"
                         % hashlib.md5("|".join(boxes).encode("utf-8")).hexdigest()[:12])
    if os.path.exists(cache):
        _WAYS = [{"geom": [tuple(q) for q in w["geom"]], "tags": w["tags"], "id": w["id"]}
                 for w in json.load(open(cache, encoding="utf-8"))]
        return _WAYS
    q = "[out:json][timeout:300];(%s);out tags geom;" % "".join('way["highway"](%s);' % b for b in boxes)
    W = [{"geom": [(round(p["lat"], 7), round(p["lon"], 7)) for p in e.get("geometry", [])],
          "tags": e.get("tags", {}) or {}, "id": e.get("id")} for e in overpass(q).get("elements", [])]
    _WAYS = [w for w in W if len(w["geom"]) >= 2]
    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump([{"geom": [list(q) for q in w["geom"]], "tags": w["tags"], "id": w["id"]} for w in _WAYS],
              open(cache, "w", encoding="utf-8"))
    return _WAYS


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


def solve(A, B, trail_A=False, trail_B=False, relax=False):
    """Beste Loesung fuer die Luecke zwischen A (endet) und B (beginnt), Kandidaten nach Kosten sortiert.

    trail_A/trail_B sagen, welche Seite ein benannter Trailabschnitt ist -- nur dort darf Fall 5 kappen.
    relax lockert die Verhaeltnismaessigkeit fuer den zweiten Durchgang (siehe RELAX_* oben); die
    Kandidatensuche selbst und das Mass weglos sind davon unberuehrt, es aendert sich nur, was als
    unverhaeltnismaessig gilt.
    """
    lim_trim = float("inf") if relax else MAX_TRIM_FACTOR
    lim_bridge = RELAX_BRIDGE_FACTOR if relax else MAX_BRIDGE_FACTOR
    lim_seg = RELAX_SEG_TRIM_FRACTION if relax else MAX_SEG_TRIM_FRACTION
    lim_dbl = RELAX_DOUBLE_M if relax else MAX_DOUBLE_M
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

    def double_ride(bridge, newA, newB):
        """Meter der Bruecke, die auf der Linie eines der beiden Abschnitte liegen -- also doppelt gefahren.

        Erste und letzte Kante bleiben aussen vor: die beruehren die Endpunkte zwangslaeufig.
        """
        if len(bridge) < 4:
            return 0.0
        tot = 0.0
        for k in range(1, len(bridge) - 2):
            mid = [(bridge[k][0] + bridge[k + 1][0]) / 2.0, (bridge[k][1] + bridge[k + 1][1]) / 2.0]
            if min(point_to_line(mid, newA)[0], point_to_line(mid, newB)[0]) <= OVERLAP_M:
                tot += haversine_m(bridge[k], bridge[k + 1])
        return tot

    def score(name, bridge, newA, newB, extra):
        # Die Kappung wird als LAENGENDIFFERENZ gerechnet, nicht ueber Punktzahlen. Fall 0 setzt einen
        # projizierten Punkt an die Stelle des weggeschnittenen Anfangs, die Punktzahl bleibt also gleich --
        # ueber Punktzahlen gemessen waere die Kappung 0 gewesen und die Segment-Grenze haette 82 doppelt
        # gefahrene Meter nicht einmal gesehen. Fuer die Faelle, die vorher an Vertexgrenzen kappten, ist die
        # Laengendifferenz derselbe Wert.
        trimmed = 0.0
        seg_over = []
        for side, orig, new in (("A", A, newA), ("B", B, newB)):
            full = C.line_len_m(orig)
            cut = full - C.line_len_m(new)
            if cut <= 0.5:
                continue
            trimmed += cut
            if len(new) < MIN_SEG_POINTS or cut > lim_seg * full or cut > MAX_TRIM_ABS_M:
                seg_over.append("kappt %.0fm von %.0fm des Segments %s" % (cut, full, side))
        blen = C.line_len_m(bridge)
        # Der Ablehnungsgrund wird HIER bestimmt, nicht erst am Ende. Er stand vorher zweimal im Code --
        # einmal in acceptable() als Tor fuer Fall 5, einmal in der Schlussrunde fuer den Report -- und
        # beide liefen auseinander: bei seg8 der Kurztour 6 galt der einzige Kandidat als brauchbar
        # (Kappung 242m < 4x133m Luecke), also lief die Kettensuche nicht an, und danach verwarf ihn die
        # Segment-Grenze doch. Ergebnis: Luecke offen, obwohl Fall 5 sie ueber Pfad + Forstweg schliesst.
        dbl = double_ride(bridge, newA, newB)
        reject = list(seg_over)
        if dbl > lim_dbl:
            reject.append("faehrt %.0fm doppelt" % dbl)
        if trimmed > lim_trim * max(beeline, 1.0):
            reject.append("kappt %.0fm bei %.0fm Luecke" % (trimmed, beeline))
        if blen > lim_bridge * max(beeline, 1.0):
            reject.append("Bruecke %.0fm bei %.0fm Luecke" % (blen, beeline))
        out.append({"name": name, "bridge": bridge, "newA": newA, "newB": newB,
                    "reject": "; ".join(reject), "len": blen, "dbl": dbl,
                    # weglos = was INNEN abseits der Wege laeuft, plus der Teil des Anschluss-Versatzes, der
                    # ueber die GPS-Ungenauigkeit hinausgeht. 13m Versatz sind Rauschen und zaehlen nicht;
                    # die 21,9m querab am Hilschberghaus sind ein echtes Gelaendestueck und zaehlen -- genau
                    # der Unterschied, den der Nutzer auf der Karte gesehen hat.
                    # Der Freibetrag fuer den Anschluss-Versatz ist ON_WAY_M, NICHT PROJ_MAX_MEAN_M. Beide
                    # standen auf 15, bis ON_WAY_M am 2026-08-20 auf 20 ging -- danach wurde ein Anschluss,
                    # der bei 16m als "auf dem Weg" akzeptiert wird, fuer genau diese 16m bestraft. Gefunden
                    # an seg37 der Ost-West-Passage: 124m Bruecke fuer 109m Luecke, durchgehend auf einer
                    # Landstrasse, Kern 0,00m abseits -- und trotzdem verworfen, weil der Trail-Endpunkt 16,3m
                    # neben der Strasse aufgezeichnet ist. Das ist das GPS-Rauschen, das der Nutzer
                    # ausdruecklich akzeptiert hat. Hier ON_WAY_M zu benutzen koppelt die beiden Zahlen per
                    # Konstruktion, damit sie nicht wieder auseinanderlaufen; PROJ_MAX_MEAN_M gehoert Fall 4
                    # und beantwortet eine andere Frage (wie weit ein ABSCHNITT im Mittel neben seinem Weg
                    # laeuft), sie hatten nur denselben Wert.
                    "off": off_way_core(bridge) + max(0.0, ends_off(bridge) - ON_WAY_M),
                    "off_ends": round(ends_off(bridge), 1),
                    "trim": trimmed, "beeline": beeline, "extra": extra})

    # --- Fall 0: die beiden Abschnitte ueberlappen sich bereits in der Originaltour
    # Die Fahrtrichtung entscheidet, welcher gekappt wird: der NACHFOLGENDE. Sein Anfangsstueck ist zu dem
    # Zeitpunkt schon gefahren -- als Ende des vorigen Abschnitts, dessen Geometrie es ja auch enthaelt.
    # Die umgekehrte Variante (den vorigen kappen) ist absichtlich NICHT eingebaut: sie ist an keinem Fall
    # geprueft, und ein nicht geprueftes Muster hat hier schon sechs Anlaeufe gekostet.
    _i, _t, P, dproj = C.project_onto_way([list(q) for q in B], a)
    if dproj <= OVERLAP_M:
        ahead = C.line_len_m([list(q) for q in B[:_i + 1]] + [P])
        # Laufen beide dasselbe Stueck in DERSELBEN Richtung? A's letzte Punkte, soweit sie auf B liegen,
        # muessen auf B immer weiter nach vorne projizieren. Bei entgegengesetzter Richtung ist es ein
        # bewusstes Hin-und-Zurueck -- der Nutzer hat so eine Stelle ausdruecklich als richtig bestaetigt
        # ("Da ist eine Pausenstelle und deswegen faehrt man das Stueck hin und zurueck").
        pos, k = [], len(A) - 1
        while k >= 0 and point_to_line(A[k], B)[0] <= OVERLAP_M:
            j, _u, Q, _d = C.project_onto_way([list(q) for q in B], A[k])
            pos.append(C.line_len_m([list(q) for q in B[:j + 1]] + [Q]))
            k -= 1
        same_dir = len(pos) >= 2 and all(pos[x] > pos[x + 1] for x in range(len(pos) - 1))
        if ahead >= MIN_OVERLAP_M and same_dir:
            newB = [list(P)] + [list(q) for q in B[_i + 1:]]
            if len(newB) >= MIN_SEG_POINTS:
                score("0_Ueberlappung(B gekappt)", _clean([a, list(P)]), A, newB,
                      "%d Punkte / %.0fm von B doppelt gefahren, Versatz %.1fm" % (_i + 1, ahead, dproj))

    # --- Fall 1: EIN verketteter Weg erreicht beide Seiten
    # Verschmelzen ist ein ZUSAETZLICHER Kandidat, kein Ersatz. Bei seg14 der Kurztour 6 erreicht der
    # unverschmolzene 255m-Pfad beide Seiten und liefert 94m Bruecke fuer 88m Luecke; in eine 2472m-Kette
    # aus fuenf Teilstuecken verschmolzen wachsen daraus 1041m, weil sich die Projektionen von a und b auf
    # der langen Kette weit auseinanderschieben. Beide Formen antreten lassen, die Rangfolge entscheidet.
    seen_ids = set()
    cand1 = []
    for m in M + ([] if MERGE_ONLY else [{"geom": w["geom"], "tags": w["tags"], "ids": [w["id"]]} for w in W]):
        key = tuple(sorted(str(i) for i in m["ids"]))
        if key in seen_ids:
            continue
        seen_ids.add(key)
        cand1.append(m)
    for m in sorted(cand1, key=lambda m: point_to_line(a, m["geom"])[0]):
        g = [list(q) for q in m["geom"]]
        da, db = point_to_line(a, g)[0], point_to_line(b, g)[0]
        if da <= ON_WAY_M and db <= ON_WAY_M:
            mid, _x, _y = C.slice_way_between(g, a, b)
            score("1_ein-Weg-beide-Seiten", _clean([a] + mid + [b]), A, B,
                  "highway=%s, %d Teilstuecke, a %.1fm / b %.1fm" % (m["tags"].get("highway"), len(m["ids"]), da, db))
            if CASE1_FIRST_ONLY:
                break
            # KEIN break: "liegt dem Endpunkt am naechsten" sagt nichts darueber, wie gut die Bruecke wird.
            # Bei seg14 der Kurztour 6 lagen fuenf Wege bei 0,0m unter dem Endpunkt, und der so gewaehlte
            # lieferte 1041m Bruecke fuer 88m Luecke, waehrend ein 255m-Pfad daneben beide Seiten sauber
            # erreicht. Jeder Kandidat wird bewertet, die Rangfolge entscheidet.

    # --- Fall 2: Weg unter einem Endpunkt trifft die LINIE der anderen Seite -> dort kappen
    # Der Treffer ist der ERSTE Punkt, den man vom Endpunkt aus auf dem Weg erreicht -- nicht der naechste.
    # Das ist die Anweisung des Nutzers woertlich ("geh die Linie zurueck, du wirst den Trail schneiden, DAS
    # ist der neue Endpunkt"), und der Unterschied ist gross: `min()` ueber alle Stuetzpunkte nahm bei seg9
    # der Ost-West-Passage einen Punkt 197m in den Brunnenwanderweg hinein, weil der Weg lange neben ihm
    # herlaeuft und dort am dichtesten ist. Diese 197m von 245m trafen die Segment-Grenze, der Kandidat fiel
    # weg -- und uebrig blieb eine Fall-1-Bruecke, die 90m auf der Linie des Brunnenwanderwegs entlanglaeuft
    # und ihn danach von vorne faehrt: 87m doppelt. Derselbe Fehler an drei Stellen, alle vom Nutzer auf der
    # Karte gefunden ("Da haette man doch nur den Pfad weiter gehen muessen, bis man auf den Brunnenwanderweg
    # trifft. Der wird dann wieder etwas abgeschnitten").
    # Ausserdem treten ALLE Wege unter dem Endpunkt an, in BEIDE Laufrichtungen, statt nur der, der der
    # anderen Linie irgendwo am naechsten kommt -- "am naechsten" sagt nichts darueber, wo man sie zuerst
    # trifft, und die Rangfolge kann ohnehin nur zwischen Kandidaten waehlen, die es gibt.
    for anchor_is_b in (True, False):
        anchor, other = (b, A) if anchor_is_b else (a, B)
        for m in [m for m in M if point_to_line(anchor, m["geom"])[0] <= ON_WAY_M]:
            g = [list(q) for q in m["geom"]]
            i0 = C.project_onto_way(g, anchor)[0]
            for step, label in ((1, "vorwaerts"), (-1, "rueckwaerts")):
                k = None
                # NICHT `idx` nennen: so hiess der WayIndex dieser Funktion, und die Schleife hat ihn
                # ueberschrieben -- der Fehler kam dann erst in off_way_metres heraus.
                pos = i0 + (1 if step > 0 else 0)
                while 0 <= pos < len(g):
                    if point_to_line(g[pos], other)[0] <= MEET_M:
                        k = pos
                        break
                    pos += step
                if k is None:
                    continue
                dmeet, cut = point_to_line(g[k], other)
                if anchor_is_b:
                    newA, newB = A[:cut + 1], B
                else:
                    newA, newB = A, B[cut:]
                if len(newA) < MIN_SEG_POINTS or len(newB) < MIN_SEG_POINTS:
                    continue
                mid, _x, _y = C.slice_way_between(g, newA[-1], newB[0])
                score("2_Weg-folgen-und-kappen(%s)" % ("A" if anchor_is_b else "B"),
                      _clean([newA[-1]] + mid + [newB[0]]), newA, newB,
                      "highway=%s %s, erster Treffer %.1fm" % (m["tags"].get("highway"), label, dmeet))

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
        return r["off"] <= OFF_TOL_M and not r["reject"]
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
    # round() faellt fuer alles unter einem halben Meter selbst auf 0 -- die Sortierung war also schon mit
    # OFF_TOL_M konsistent, nur Tor und Vorauswahl waren es nicht. Die Rundung hier NICHT feiner machen: das
    # loest Gleichstaende auf, die bisher die Fallnummer entschieden hat, und verschiebt damit Ergebnisse.
    #
    # Die Kappung steht INNERHALB eines Falls in der Rangfolge, aber nie davor. Beide Haelften sind an echten
    # Faellen belegt:
    #   * Davor waere falsch: nach "Bruecke + Kappung" global sortiert rutschte Landstuhl (Ost) seg15 von
    #     Fall 1 auf Fall 3 -- fuer wenige Meter kuerzere Bruecke schlechteres Vertrauen. Die Fallnummer
    #     kodiert, wie gut die Zuordnung belegt ist, nicht wie lang sie ist.
    #   * Gar nicht waere auch falsch: bei seg0 des Felsenwanderwegs Rodalben standen zwei Fall-5-Loesungen
    #     nebeneinander, 654m Bruecke mit 1095m Kappung und 698m Bruecke mit 62m Kappung. Ohne die Kappung im
    #     Schluessel entschied allein die Bruecke -- 44m kuerzer, dafuer 1033m echter Trail weg.
    # Danach `trim` und erst zuletzt `len`: bei gleicher Summe ist die Loesung besser, die mehr reale
    # Trail-Geometrie stehen laesst.
    out.sort(key=lambda r: (bool(r["reject"]), round(r["off"]), r["name"][0], round(r["dbl"] / 10.0),
                            round(r["len"] + r["trim"]), r["trim"], r["len"]))
    return out


def close_gaps(s, gaps, names=None, write=False, report=None):
    """Die Luecken einer Tour der Reihe nach schliessen -- der EINE Kern, den Werkzeug und Regressionstest
    gemeinsam benutzen.

    Die Annahmeregeln (weglos-Tor, Verhaeltnismaessigkeit) stehen absichtlich hier und nicht in main(): sie
    sind selbst Teil dessen, was regressieren kann, also muss der Test genau sie ausfuehren und nicht eine
    nachgebaute Kopie. Rueckwaerts durchlaufen, weil `close_gap` ein Segment einfuegen kann und dabei alle
    hoeheren Indizes verschiebt.
    """
    names = names or {}
    out = []
    for i in sorted(gaps, reverse=True):
        j = (i + 1) % len(s)
        A, B = s[i]["coords"], s[j]["coords"]
        kind = lambda x: names.get(x.get("trailId"), "?")[:22] if x.get("trailId") else "CONNECTOR"
        rec = {"seg": i, "gap": round(haversine_m(A[-1], B[0]), 1),
               "from": kind(s[i]), "to": kind(s[j]), "applied": None}
        if report:
            report("seg%-2d %6.1fm  %-22s -> %s" % (i, rec["gap"], rec["from"], rec["to"]))
        if rec["gap"] > MAX_GAP_M:
            rec["skipped"] = "%.0fm ist keine Luecke, sondern eine Strecke -- ansehen" % rec["gap"]
            if report:
                report("    -> %s" % rec["skipped"])
            out.append(rec)
            continue
        res = solve(A, B, trail_A=bool(s[i].get("trailId")), trail_B=bool(s[j].get("trailId")))
        usable = res and res[0]["off"] <= OFF_TOL_M and not res[0]["reject"]
        if res and not usable:
            # Zweiter Durchgang: nur wo streng nichts Brauchbares uebrig bleibt (siehe RELAX_* oben). Ein
            # Uebergang mit einer brauchbaren strengen Loesung kommt hier nie an und aendert sich also nicht.
            alt = solve(A, B, trail_A=bool(s[i].get("trailId")), trail_B=bool(s[j].get("trailId")), relax=True)
            if alt and alt[0]["off"] <= OFF_TOL_M and not alt[0]["reject"]:
                res, rec["relaxed"] = alt, True
        if not res:
            rec["skipped"] = "keine Loesung gefunden"
        else:
            if report:
                for r in res:
                    report("    %-28s Bruecke %4.0fm | weglos %3.0fm | doppelt %4.0fm | kappt %4.0fm | %s%s"
                           % (r["name"], r["len"], r["off"], r["dbl"], r["trim"], r["extra"],
                              ("   VERWORFEN: " + r["reject"]) if r["reject"] else ""))
            best = res[0]
            if best["off"] > OFF_TOL_M:
                rec["skipped"] = "weglos > %.1fm" % OFF_TOL_M
            elif best["reject"]:
                rec["skipped"] = "unverhaeltnismaessig"
            else:
                rec["applied"] = best["name"]
                rec["bridge"] = round(best["len"])
                rec["trim"] = round(best["trim"])
                rec["best"] = best
                if write:
                    s[i]["coords"] = best["newA"]
                    s[j]["coords"] = best["newB"]
                    C.close_gap(s, i, j, [list(q) for q in best["bridge"][1:-1]],
                                best["newA"][-1], best["newB"][0])
        if report and rec["applied"]:
            report("    -> angewendet: %s%s" % (rec["applied"],
                                                "  [GELOCKERT -- ansehen]" if rec.get("relaxed") else ""))
        elif report and res:
            report("    -> %s, nichts angewendet" % rec["skipped"])
        elif report:
            report("    %s" % rec["skipped"])
        out.append(rec)
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
    pairs = [(s[i]["coords"][-1], s[(i + 1) % len(s)]["coords"][0]) for i in args.gap]
    prefetch_gaps([(a, b) for a, b in pairs if haversine_m(a, b) <= MAX_GAP_M])
    names = {t["id"]: t["name"] for t in d["lineTrails"]}
    recs = close_gaps(s, args.gap, names=names, write=args.write, report=lambda t: print(t))
    chosen = {r["seg"]: r["best"] for r in recs if r["applied"]}

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
