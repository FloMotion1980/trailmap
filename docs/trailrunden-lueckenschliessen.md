# Trailrunden-Lücken schließen — Strategien

Methodik-Dokument zu `tools/close_loop_gaps.py`. Das **Warum** (wie die Lücken überhaupt entstehen) steht
im Docstring des Tools selbst und in `CLAUDE.md`s `buildTrailLayer`-Abschnitt; **hier** steht, nach welchen
Regeln eine Lücke geschlossen wird, in welcher Reihenfolge die Verfahren greifen und wo sie bewusst
aufgeben.

Stand 2026-08-16, nach der zweiten Feedback-Runde des Nutzers am Live-Ergebnis von
`pw_rodalben_felsentrails`. Der erste Wurf (alle Verfahren gleichberechtigt, kürzeste Route gewinnt) hat
zwar 29/29 Lücken geschlossen, aber an mindestens einer Stelle eine Route gewählt, die real nicht befahrbar
ist — geometrisch unauffällig (Faktor 1,1), inhaltlich falsch.

---

## Leitgedanken des Nutzers (die Vorgaben, aus denen alles Folgende abgeleitet ist)

1. **„Wenn die Trails auf OSM liegen, sollten wir die Befahrbarkeitsprüfung machen."**
   Ein gewählter Weg muss real fahrbar sein, nicht nur nah dran. Reine Distanz als Kriterium reicht nicht.

2. **„Bei mehreren Kandidaten sollte ein Trail gegen einen Forstweg gewinnen."**
   Wegtyp ist ein echtes Qualitätsmerkmal, nicht nur die Entfernung.

3. **„Es gibt Touren, wo Trailabschnitte oder die Tour selbst nicht direkt auf OSM-Wegen liegen. In so
   einem Fall wird uns die OSM-Strategie keinen Erfolg bringen."**
   Das Tool muss erkennen können, dass OSM hier nicht hilft, und das ehrlich sagen — statt die Brücke auf
   irgendeinen zufällig nächstgelegenen Weg zu schnappen und das Route zu nennen.

4. **„Meistens ist es nicht schlimm, wenn es nicht 100 % exakt passt. Bei der Fahrt sieht man ja auch die
   anderen Wege und kann so schnell zurück zum Tourweg."**
   Kalibrierung der Ansprüche: eine plausible, befahrbare Verbindung schlägt eine millimetergenaue. Lieber
   eine leicht ungenaue durchgehende Linie als eine Lücke — aber nicht um den Preis einer Route, die real
   nicht geht.

5. **Reihenfolge statt Wettbewerb** (aus der Runde davor): erst konsequent versuchen, beide Enden auf echte
   OSM-Wege zu mappen und zu verbinden; die übrigen Verfahren nur als Fallback — nicht als gleichwertige
   Konkurrenten, unter denen die kürzeste Strecke gewinnt. Begründung: die Trail-Geometrie stimmt bekanntlich
   nicht exakt mit OSM überein (genau deshalb entsteht die Lücke ja), also ist „kürzeste Route unter allen
   Verfahren" nicht dasselbe Kriterium wie „folgt echten, zusammenhängenden Wegen".

6. **Das Verfahren zahlt auf den Tourenbuilder ein.** Was hier an Weg-Matching, Befahrbarkeits- und
   Verbindungslogik entsteht, ist dieselbe Aufgabe, die der Tourenbuilder beim Verbinden zweier gewählter
   Elemente hat — also so bauen, dass es dort wiederverwendbar ist.

---

## Die Verfahren, in Prioritätsstufen

Innerhalb einer Stufe gewinnt die kürzeste Route. Eine niedrigere Stufe wird **nur** betreten, wenn die
höhere gar nichts geliefert hat — nicht, weil sie kürzer wäre.

### Stufe 1 — beide Enden auf echte OSM-Wege mappen

**`both_ways_junction`** (neu)
Für beide Seiten der Lücke getrennt den best passenden OSM-Weg bestimmen (Trail-Ende → Weg A,
Connector-Anfang → Weg B). Sind es zwei verschiedene Wege, den Punkt suchen, an dem sie sich am nächsten
kommen; liegt der unter `JUNCTION_MAX_M` (60 m), ist genau das der geometrisch fundierte Anschlusspunkt:
a → entlang Weg A bis zum Treffpunkt → entlang Weg B → b.

Das ist die eigentliche Antwort auf „beide Seiten mappen und schauen, wo sie sich schneiden" — im Gegensatz
zur alten Variante, die nur **eine** Seite matchte und dann stur bis zum rohen Endpunkt der anderen Seite
lief.

**`matched_way_a` / `matched_way_b`**
Der Fall, dass beide Seiten auf **demselben** Weg liegen (dann gibt es keinen Schnittpunkt zu suchen, man
läuft einfach auf diesem einen Weg von a nach b) — bzw. der Rückfall, wenn nur eine Seite sauber matcht.

Alle Stufe-1-Verfahren stehen unter drei harten Bedingungen:

- **Match-Qualität.** Der mittlere Abstand der Referenzpunkte einer Seite zu „ihrem" Weg muss unter
  `MATCH_MAX_MEAN_M` (15 m) liegen. Darüber gilt: dieser Abschnitt liegt nicht auf diesem Weg, das Verfahren
  ist hier **nicht anwendbar** (Leitgedanke 3). Es liefert dann bewusst nichts, statt etwas Falsches.
- **Befahrbarkeit.** Gesperrte Wege werden vorher aussortiert (siehe unten).
- **Wegtyp-Präferenz.** Bei vergleichbar gutem geometrischen Match gewinnt der Trail (Leitgedanke 2).

### Stufe 2 — Geometrie wiederverwenden, die die Region schon hat

**`reused_connector`**
Ein bestehendes reines Connector-Stück (aus irgendeiner Trailrunde derselben Region), dessen Linie an beiden
Lücken-Enden innerhalb von 60 m vorbeikommt. Das ist real aufgezeichnete, von jemandem tatsächlich gefahrene
Geometrie — inhaltlich stark, aber nach Leitgedanke 5 bewusst **hinter** dem OSM-Weg-Matching einsortiert.

### Stufe 3 — Kürzester Pfad im Wegenetz

**`osm_route`** (Dijkstra)
Letzter Ausweg, wenn keine der beiden oberen Stufen greift. Bekannte Schwäche, die diese Einsortierung
begründet: beide Enden werden unabhängig voneinander auf ihren jeweils nächsten Netzknoten geschnappt,
wodurch die Route auf einen unbeteiligten Nachbarpfad abwandern und einen im Graphen zwar kürzesten, real
aber unsinnigen Umweg zusammensetzen kann (gemessen: 181 m Lücke → 633 m Route, Faktor 3,5). Der Graph wird
inzwischen ebenfalls um gesperrte Wege bereinigt.

### Keine Stufe greift

Die Lücke bleibt **offen** und wird im Report als `failed` mit Grund geführt. Das ist ein gewolltes Ergebnis,
kein Fehler des Tools — per [[no-silent-auto-corrections]] ist eine ehrlich markierte Lücke besser als eine
stillschweigend erfundene Route. Im RIDE-Modus wird eine verbliebene Lücke ohnehin durch die orange
Überbrückungslinie sichtbar gemacht (siehe `applyRideFocusHalo`), ist für den Fahrer also nicht unsichtbar.

---

## Befahrbarkeitsprüfung

Ein Weg wird komplett aussortiert (nicht nur schlechter bewertet), wenn seine Tags ihn für Radfahrer
sperren. Auswertungsreihenfolge, spezifisch vor allgemein:

| Bedingung | Wirkung |
|---|---|
| `bicycle` = `yes` / `designated` / `permissive` / `official` | **explizit erlaubt** — schlägt alles Folgende |
| `bicycle` = `no` / `private` / `dismount` | gesperrt |
| `access` = `private` / `no` / `permit` / `customers` | gesperrt |
| `vehicle` = `private` / `no` / `forestry` / `agricultural` / `delivery` | gesperrt |
| `motor_vehicle` = irgendwas | **nicht** sperrend (betrifft nur Kfz) |

`vehicle=forestry` ist genau der Fall, der den Rodalben-Startpunkt kaputt gemacht hat: ein
`highway=track`, den OSM klar als nicht für den Durchgangsverkehr gedacht ausweist, der aber geometrisch
perfekt passte. In OSMs Tag-Hierarchie ist ein Fahrrad ein `vehicle`, `vehicle=forestry` schließt es also
mit ein — deshalb sperrend, sofern kein explizites `bicycle=yes` daneben steht.

**Gesperrte Wege werden im Report protokolliert** (`rejected_ways`), nicht nur weggelassen — damit
nachvollziehbar bleibt, warum eine Lücke offen geblieben ist oder eine längere Route gewonnen hat.

## Wegtyp-Präferenz

Umgesetzt als Aufschlag in „Metern Match-Fehler-Äquivalent" auf die gemessene Match-Distanz, nicht als
hartes Ausschlusskriterium:

| Wegtyp | Aufschlag |
|---|---|
| `path`, `footway`, `bridleway`, `cycleway` | 0 m |
| `track` (Forst-/Feldweg) | 6 m |
| `service`, `unclassified`, `residential`, `living_street`, `pedestrian` | 10 m |
| `tertiary`, `secondary`, `primary` | 20 m |

Bewusst **kleine** Zahlen. Die Connector-Abschnitte einer Trailrunde laufen real sehr häufig über Forstwege
— der Aufschlag darf eine echte Entscheidung nur bei annähernd gleichem Match kippen, nicht das Matching auf
einen sichtbar weiter entfernten Singletrail zerren. Typische echte Match-Distanz liegt unter 5 m, damit
entscheidet +6 m einen Gleichstand und überstimmt keinen klaren Sieger.

---

## Was der Report ausweist

Pro Lücke zusätzlich zu Luftlinie/Routenlänge/Faktor/Verfahren:

- `tier` — welche Prioritätsstufe gewonnen hat (1/2/3)
- `match_m` — wie gut die Seite(n) auf ihren Weg gepasst haben
- `way_type` — Wegtyp des gewählten Wegs (`path`, `track`, …)
- `rejected_ways` — wegen Zugangsbeschränkung aussortierte Kandidaten samt Grund
- `suspicious` — Routenfaktor über `SUSPICIOUS_ROUTE_FACTOR` (3,0)

Ein Ergebnis mit auffälligem Wegtyp oder aussortierten Nachbarn ist damit im Report erkennbar, **ohne** dass
man die Karte aufmachen muss — genau die Lücke in der ersten Fassung, die den Rodalben-Fehler durchrutschen
ließ (Faktor völlig unauffällig, Problem rein inhaltlich).

---

## Reihenfolge des Vorgehens (Nutzer-Vorgabe)

1. Verfahren erweitern (dieses Dokument).
2. **Erst Felsentrails erneut überarbeiten** und das Ergebnis ansehen — „ich würde trotzdem nochmal
   probieren, bessere Ergebnisse auf Felsentrails zu bekommen".
3. Erst danach dasselbe Verfahren auf die übrigen Trailrunden anwenden. Bisher wurde `close_loop_gaps.py`
   ausschließlich auf `pw_rodalben_felsentrails` angewendet; alle anderen Touren mit `trailSegments` haben
   ihre Lücken noch unverändert.

## Zwei Fallen, die beim ersten Durchlauf mit diesen Regeln aufgeflogen sind

Beide wurden erst dadurch sichtbar, dass die **geschriebene Datei nachgemessen** wurde statt dem Report zu
glauben — der Report meldete in beiden Fällen brav Erfolg.

**1. Auf den nächsten Stützpunkt schnappen statt auf die Wegstrecke projizieren.**
Die erste Fassung suchte zu jedem Lücken-Ende den nächstgelegenen *Vertex* des gematchten Wegs. Sind die
Stützpunkte weit auseinander (auf einem geraden Forstweg völlig normal), landen beide Enden am **selben**
Vertex — die „Route entlang des Wegs" besteht dann aus null Zwischenpunkten, ist also exakt die Luftlinie,
und der Report weist stolz `route_factor 1.00` aus. Betraf **16 von 29** Lücken auf Rodalben. Behoben durch
echte senkrechte Projektion auf die Kanten (`project_onto_way` / `slice_way_between`): das liefert sowohl die
korrekte Position entlang des Wegs als auch reale Geometrie dazwischen.

**2. Eine leere Brücke schließt nichts.**
`close_gap` fügte nur die *Zwischen*punkte ein, in der Annahme, die beiden Endpunkte existierten ja schon.
Bei leerer Brücke wurde damit gar nichts eingefügt und die Lücke blieb offen — und selbst bei nicht-leerer
Brücke war der Anschluss nur so exakt, wie der erste geroutete Punkt zufällig am Segmentende lag. Jetzt
wiederholt **jeder** Zweig den Endpunkt, von dem er wegwächst (`[a] + bridge`, `bridge + [b]`, bzw.
`[a] + bridge + [b]` für einen neu eingefügten Connector), sodass die Polylinien garantiert aneinander
anschließen. Kostet einen Null-Längen-Schritt in der Verkettung, sonst nichts.

**Lehre fürs nächste Mal: nach jedem Lauf die Datei selbst nachmessen** (Abstand zwischen
`segs[i].coords[-1]` und `segs[i+1].coords[0]`), nicht den Report als Beleg nehmen. Der Report sagt, was das
Verfahren zu tun glaubte; die Datei sagt, was tatsächlich drin steht.

## Ergebnis auf `pw_rodalben_felsentrails` (2026-08-16)

Ausgangslage auf die Original-Geometrie zurückgesetzt (Stand `d017a59`) und komplett neu gerechnet:

| | Erster Versuch (v1) | Mit diesen Regeln (v3) |
|---|---|---|
| geschlossene Lücken laut Report | 29 | 29 + 7 kleine |
| **tatsächlich geschlossen (nachgemessen)** | 13 | **alle** |
| verbleibende Lücken > 2 m | 38 | **0** |
| gewählte Stufe | gemischt | **29× Stufe 1** |
| Wegtypen | u. a. gesperrter Forstweg | 22× `path`, Rest `track`/`service` |
| Ø Routenfaktor | 1,02 (geschönt, s. o.) | 1,18 |

Insgesamt 11 Lücken hatten gesperrte Wege in der Nachbarschaft, die jetzt korrekt verworfen werden
(`vehicle=forestry`, `bicycle=no`, `access=private`, `access=customers`) — darunter der ursprünglich
gemeldete Startpunkt `seg0→seg1`, der jetzt über einen `path` läuft statt über den Forstweg.

Weder Stufe 2 (vorhandener Connector) noch Stufe 3 (Dijkstra) wurden überhaupt gebraucht: das reine
OSM-Weg-Matching hat jede einzelne Lücke gelöst. Der Schwellwert wurde in einem zweiten Durchlauf von 30 m
auf 12 m gesenkt, um auch die verbliebenen kleinen Sprünge zu schließen (7 Stück, alle unauffällig,
max. Faktor 1,40).

## Noch offen

- **Kandidatenklasse „Trail kürzen" statt nur „Connector verlängern"** (eigener Vorschlag des Nutzers): die
  Segment-Geometrie an einer früheren Stelle kappen, bis eine sauber befahrbare Verbindung entsteht. Noch
  nicht gebaut — der Lösungsraum ist aktuell rein additiv (Brücke einfügen), nie subtraktiv.
