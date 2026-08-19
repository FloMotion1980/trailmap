# nearbyTrailConnector

Verfahren zum Schließen von Lücken zwischen Trailrunden-Segmenten. Wird **fallweise** entwickelt: wir gehen
einzelne Lücken durch, halten pro Fall die richtige Lösung und die Methode fest, die dorthin geführt hat, und
unterscheiden dabei **akzeptabel** von **perfekt**. Ziel ist ein Verfahren, das am Ende in vielen Fällen von
selbst gute Ergebnisse liefert (Nutzer-Strategie, 2026-08-16).

Das *Warum* der Lücken steht im Docstring von `tools/close_loop_gaps.py`; hier steht nur, wie man sie
schließt.

---

## Die Grundregeln (vom Nutzer vorgegeben, mehrfach wiederholt)

1. **Zum Endpunkt verbinden oder den Endpunkt verschieben.** Eine Brücke endet immer an einem echten
   Segment-Endpunkt — dem vorhandenen oder einem neuen durch Kürzung. Nie an einem Punkt mitten auf einem Weg.
2. **Dem Weg folgen, nicht der Luftlinie.** Vom Lücken-Endpunkt auf dem Weg zurück-/weiterlaufen, bis er die
   **Linie** der anderen Seite schneidet — nicht bis zu deren Endpunkt.
3. **Dort kappen.** Der Schnittpunkt ist der neue Endpunkt der anderen Seite; ihr Überhang entfällt. Kappen
   ist die Reparatur, nicht der Schaden.
4. **Möglichst 100 % auf OSM-Wegen bleiben.** Das ist das Kriterium, das perfekt von akzeptabel trennt.

### Qualitätsmaß

`weglos` = Meter der Brücke, die weiter als 20 m von jedem gemappten Weg entfernt liegen.
**perfekt = weglos 0 m UND kein Stück abseits eines Wegs**, auch nicht kurz. Ein Ergebnis kann weglos 0 m
haben und trotzdem nur akzeptabel sein, wenn es z. B. 20 m quer durch den Wald springt, die zufällig nah an
einem anderen Weg liegen.

---

## Die entscheidende Einsicht: OSM zerlegt eine Straße in mehrere Way-Objekte

Das war die Ursache dafür, dass mehrere Fälle unlösbar aussahen. Am Hilschberghaus bestand **eine** Straße
aus **5 Way-Objekten**; solange nur einzelne Objekte betrachtet wurden, berührte keines davon beide Seiten der
Lücke, und jede Lösung brauchte ein Stück quer durchs Gelände.

**Also vor allem anderen: Way-Objekte zu durchgehenden Wegen verketten** — gleicher `highway`-Typ, gleicher
`name`, Endpunkte berühren sich (≤1 m). Im Testgebiet wurden aus 192 Objekten 133 durchgehende Wege, und
danach gab es genau eine Straße, die Connector-Ende (0,0 m) und Trail-Linie (0,5 m) verband.

Die Nutzer-Vorgabe „die Rückwärtsbewegung geht nicht über mehrere Wege" bedeutet: **nicht über verschiedene
Straßen hinweg routen**. Einer durchgehenden Straße zu folgen, die OSM in Stücke zerlegt hat, ist genau
richtig.

---

## Fallkatalog

### Fall 1 — `seg0`, Felsenweg Nord Ende (L 482)

Lücke 180,7 m, Trail → CONNECTOR.

**Perfekt.** Der Connector-Anfang liegt **exakt** (0,0 m) auf einem `highway=track`; der kommt der Trail-Linie
auf 2,8 m nahe. Auf ihm zurücklaufen, Trail um 230 m kappen. Brücke 405 m, weglos 0 m.

**Was es blockiert hatte:** der Track ist `vehicle=forestry` getaggt, und meine Befahrbarkeitsprüfung hatte
ihn aussortiert — vor jeder Variantenberechnung. Fünf Fehlversuche, eine Ursache.
→ **Regel: ein Weg, auf dem die Tour ohnehin schon liegt, darf nie wegen Zugangs-Tags ausgeschlossen werden.**
Die Prüfung gilt nur für Wege, die neu dazukämen.

### Fall 2 — `seg1`, Gipfelstürmer Anfang

Lücke 46,7 m, CONNECTOR → Trail. Vom Nutzer als **„die perfekte Lösung"** bezeichnet.

**Perfekt: beide Wege bis zum echten Schnittpunkt.** Weg unter dem Connector-Ende (`track`) und Weg unter dem
Trail-Anfang (`path`) bestimmen, beide weiterlaufen bis zu ihrem Schnittpunkt, Brücke = Ende A → Weg A →
Schnittpunkt → Weg B → Ende B. 190 m bei 47 m Luftlinie (Faktor 4,1), weglos 0 m.

**Dass die Route bis zur Kreuzung hochfährt und auf dem anderen Weg zurückkommt, ist kein Fehler** und darf
nicht wegoptimiert werden — so fährt man vor Ort auch. Die kürzere Variante mit 15-m-Übersprung (124 m) wurde
ausdrücklich nur als *akzeptabel* eingestuft, die Schnittpunkt-Variante als perfekt.

### Fall 3 — `seg34`, Hilschberghaus

Lücke 61,5 m, CONNECTOR → Trail.

**Perfekt: der durchgehenden Straße folgen.** Nach dem Verketten der Way-Objekte (siehe oben) gibt es eine
`service`-Straße aus 5 Teilstücken, die den Connector-Endpunkt berührt (0,0 m) und die Trail-Linie erreicht
(0,5 m). Auf ihr entlang, Trail-Anfang um 186 m kappen. Brücke 275 m, weglos 0 m.

**Akzeptabel, aber nicht perfekt** war die Zwischenlösung über ein einzelnes Way-Objekt: 21,9 m vom
Connector-Ende quer zur Straße, dann auf ihr weiter (Brücke 179 m). Formal weglos 0 m, real 21,9 m durch den
Wald — der Nutzer: „akzeptabel aber nicht perfekt … einfach der Straße folgen".

### Fall 4 — `seg4` / `seg6`, Rodalber Felsenwanderweg

Lücken 23 m und 46 m, Trail → CONNECTOR.

**Perfekt: Projektion des Trailabschnitts auf „seinen" Weg.** Nutzer-Hinweis: ein Trailabschnitt läuft oft
nicht exakt auf seinem OSM-Weg, ist ihm aber eindeutig zuzuordnen, weil kein anderer Weg in der Nähe liegt.
10–15 m Versatz sind GPS-Ungenauigkeit. Für die *Verbindung* darf man deshalb mit dem Lotfußpunkt rechnen.

Gemessen: Trailabschnitt Ø 4,5 m bzw. 3,5 m neben einem `path`, zweitnächster Weg 103 m bzw. 85 m entfernt —
eindeutig. Brücke 32 m bzw. 66 m ohne Kappung, statt 433 m mit 416 m Kappung.

**Zwei harte Bedingungen:** die Trail-Geometrie wird nie verändert (sonst weicht der Abschnitt in der Tour von
der Geometrie des eigenständigen Trails ab), und projiziert wird nur bei eindeutiger Zuordnung — „wenn mehrere
Wege oder Abzweigungen in der Nähe sind, wird das schwer", dann liefert dieser Fall nichts.

Der bleibende Querversatz von 13–14 m ist gewollt: die Brücke folgt exakt dem Weg, der Trail liegt daneben.
Der Nutzer dazu: „Die Sprünge sind zwar unschön, aber unvermeidbar mit der Prämisse, dass wir Trailgeo nicht
verändern."

### Fall 5 — `seg33` / `seg34`, Baumbuschstraße und Bruderfelsen

Lücken 80 m und 43 m, die letzten beiden der Tour. Beide brauchen eine Verbindung über **mehrere
verschiedene Wege hintereinander**, was Fall 1–4 nicht können.

**Perfekt: Wegekette über echte Kreuzungen.** Die verketteten Wege werden selbst zu Knoten eines Graphen;
eine Kante besteht nur, wo zwei Wege einen **gemeinsamen Stützpunkt** haben, also real abzweigen. Kette auf
maximal 3 Wege begrenzt.

- `seg33`: Kette `path` → `track` — die Nutzer-Vorgabe war wörtlich „von der Baumbuschstraße den Pfad und
  dann auf die Forststraße bis zum Trailanfang". 150 m bei 80 m Lücke.
- `seg34`: Kette `path` → `track` → `path`, **kombiniert mit Kappen** — „am Bruderfelsen den Otto-Stolz-Pfad
  runter, grüner Trail wird früher verlassen". Der Trail wird 95 m früher verlassen; die Kette muss also
  nicht seinen Endpunkt erreichen, sondern seine **Linie**. 139 m Brücke.

**Abgrenzung zum verworfenen Netzwerk-Routing:** dort wurden Endpunkte unabhängig auf beliebige Netzknoten
geschnappt und kürzeste Kanten zusammengestückelt — das erzeugte Umwege durch den Wald. Hier ist jeder
Wegwechsel eine reale Abzweigung, die Kettenlänge begrenzt, und die Kandidaten werden weiterhin über
weglos und Verhältnismäßigkeit bewertet (`seg34` hatte 3 Kandidaten, einer davon 1634 m lang).

---

## Zwei Ebenen von Verkettung — der Kern des Verfahrens

1. **Innerhalb eines Wegs:** OSM-Objekte desselben Wegs zusammenfügen. Das brachte **27 von 34** Fällen auf
   den einfachsten Fall „einem Weg folgen".
2. **Zwischen Wegen:** Ketten über echte Abzweigungen (Fall 5). Das löst die verbleibenden schwierigen Fälle.

---

## Ergebnis auf `pw_rodalben_felsentrails` (2026-08-16)

**Alle 36 Lücken geschlossen**, 0 Lücken über 2 m, 41,81 km, Validierung grün. Jede Lösung vom Nutzer auf
der Karte bestätigt.

| Fall | Anzahl |
|---|---|
| 1 — ein verketteter Weg erreicht beide Seiten | 27 |
| 2 — Weg folgen + kappen | 3 |
| 3 — Schnittpunkt zweier Wege | 2 |
| 4 — Projektion auf den zugeordneten Weg | 2 |
| 5 — Wegekette über echte Kreuzungen | 2 |

Alle mit weglos 0 m.

**Geschwindigkeit:** ein einziger Overpass-Abruf für die ganze Tour (`prefetch`, Ergebnis als Datei) statt
einer Abfrage pro Lücke — von 1 min 35 s auf **0,9 s** für vier Lücken.

---

## Handwerkliche Regeln, jede aus einem echten Fehler

- **Way-Objekte verketten, bevor irgendetwas gesucht wird** (siehe oben).
- **Immer projektionsgenau schneiden** (`slice_way_between`), nie an Stützpunkt-Indizes — sonst entstehen
  Hin-und-zurück-Überstände. Der Nutzer hat sie zweimal auf einem Screenshot gelb markiert.
- **Der Weg muss nicht *unter* dem Endpunkt liegen, er muss beide Seiten erreichen.** Ein Filter „Weg ≤3 m vom
  Endpunkt" hat in Fall 3 genau die richtige Straße ausgeschlossen.
- **Kappen nicht bestrafen.** Eine Bewertung, die verworfene Trail-Meter mit 2 Strafmetern belegte, stellte
  eine sichtbar falsche Lösung über die gewünschte.
- **Nie zwei Ausgangsstände mischen.** Segmente aus einem anderen Stand nachzuladen hat einmal einen
  funktionierenden Fix überschrieben und die Tour zerlegt. Rückgängig immer über dieselbe Basis.
- **Immer die geschriebene Datei nachmessen** (`segs[i].coords[-1]` ↔ `segs[i+1].coords[0]`), nie dem Report
  glauben. Ein Lauf meldete 29 Schließungen, wirksam waren 13.
- **Segment-Indizes verschieben sich**, wenn ein Segment eingefügt wird — nach dem Schreiben immer alle
  Übergänge neu messen, nicht dieselben Indexnummern wie vorher.

---

## Offen

- **Andere Trailrunden.** Bisher nur `pw_rodalben_felsentrails` behandelt; jede andere Tour mit
  `trailSegments` hat ihre Lücken unverändert. Das Verfahren steckt in `tools/nearby_trail_connector.py` und
  sollte dort ohne Änderung anwendbar sein — aber jede neue Tour zuerst im Trockenlauf ansehen, nicht blind
  schreiben.
- **Fall 5 ist noch nicht im Tool verdrahtet.** `chain_bridges`/`chain_bridges_trim` existieren als
  Funktionen, werden von `solve()` aber noch nicht aufgerufen; die zwei Fälle wurden mit einem eigenen Skript
  angewendet. Beim nächsten Einsatz einbauen und die Rangfolge festlegen (Fall 5 nach Fall 1–4).
- **Zwei Grenzwerte sind noch nicht belastbar geprüft**: `PROJ_MIN_SECOND_M` (40 m) hat bei `seg33`/`seg34`
  Fall 4 blockiert, was dort richtig war — ob der Wert generell passt, zeigt erst die nächste Tour.
  `MEET_M`/`ON_WAY_M` mussten von 8 m auf 15 m, weil `seg14` sonst durch alle Fälle fiel.
- `tools/close_loop_gaps.py` und `tools/gap_variants.py` enthalten viel Verworfenes und sind **nicht** der
  Stand dieses Dokuments — nur `nearby_trail_connector.py` ist es.
