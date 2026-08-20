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

### Qualitätsmaß: weglos nach Projektion

Vorschlag des Nutzers, und die Größe, an der alles hängt. Weil die Brücken **aus** Weg-Geometrie gebaut sind
(`slice_way_between`), liegt ihr Inneres per Konstruktion exakt auf dem Weg — abseits kann nur an den zwei
Anschlüssen entstehen, also im Querversatz zwischen Trail-Aufzeichnung und OSM-Weg. Deshalb:

    weglos = (was INNEN abseits der Wege läuft, Toleranz 5 m)
           + max(0, Anschluss-Versatz − 15 m)

Beide Zahlen sind an echten Fällen kalibriert, nicht geraten:

- **Innen 5 m statt 20 m.** Bei 20 m sahen am Hilschberghaus *vier* Kandidaten identisch gut aus (alle
  weglos 0 m), obwohl drei davon 20 m querab durchs Gelände sprangen — die Auswahl war damit zufällig.
- **Anschluss-Versatz bis 15 m frei.** 10–15 m sind GPS-Ungenauigkeit und vom Nutzer ausdrücklich akzeptiert
  („Die Sprünge sind zwar unschön, aber unvermeidbar"). Die 21,9 m querab am Hilschberghaus sind dagegen ein
  echtes Geländestück und zählen — genau der Unterschied, den der Nutzer auf der Karte gesehen hat und den
  ein einheitliches 20-m-Maß nicht sehen konnte.

**perfekt = weglos 0 m.** Akzeptabel ist ein Ergebnis, das die Lücke schließt, aber ein Stück abseits der
Wege enthält.

### Rangfolge

`(verworfen, weglos, Fallnummer, Brückenlänge)`. **Die Kappung gehört nicht in die Sortierung** — sie ist die
Reparatur, kein Kostenfaktor, und wird nur über `MAX_TRIM_FACTOR` begrenzt. Ein Versuch, „weniger Kappung"
vorzuziehen, hat bei `seg0` eine 637-m-Kette ohne Kappung der bestätigten 406-m-Lösung mit 230 m Kappung
vorgezogen.

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

## Stabilitätstest: vier Durchläufe, drei Mängel

Nach dem Einbau von Fall 5 wurde das Verfahren komplett neu auf die Original-Geometrie angewendet und mit dem
bestätigten Ergebnis verglichen — auf Wunsch des Nutzers, weil das Verfahren sich verändert hatte. Es war
**nicht** stabil, und jeder Durchlauf legte einen eigenen Mangel offen:

| Lauf | Ergebnis | Mangel |
|---|---|---|
| 1 | 1 Lücke offen, 41,72 km | `MAX_TRIM_FACTOR` 3,0 verwarf die bestätigte Hilschberghaus-Lösung um **1,5 m** (Faktor 3,02) → auf 4,0 erhöht |
| 2 | 4 Lücken offen, 42,20 km | Weglos-Toleranz 5 m zählte den akzeptierten Querversatz (12–13 m) als Mangel → Anschluss-Versatz getrennt bewertet |
| 3 | 0 Lücken, 42,27 km | „weniger Kappung zuerst" zog bei `seg0` eine 637-m-Kette vor → Kappung aus der Sortierung entfernt |
| 4 | **0 Lücken, 41,81 km** | reproduziert den bestätigten Stand |

Lauf 4 gegen den bestätigten Stand: gleiche Länge, gleiche Segmentzahl, **36 von 38 Segmenten identisch**.
Die zwei Abweichungen (`seg3`/`seg4`, zusammen +13 m) sind eine gleichwertige Entscheidung — Fall 1 mit 47 m
Brücke ohne Kappung statt Fall 2 mit 75 m und 41 m Kappung, beide weglos 0 m.

**Lehre: ein geändertes Verfahren muss gegen die bestätigten Ergebnisse nachgerechnet werden.** Alle drei
Mängel waren unsichtbar, solange nur einzelne neue Fälle gerechnet wurden.

---

## Feste Regel: immer die ganze Region vorab laden

Nutzer, 2026-08-17: *„Bitte immer die Region komplett laden, wenn unser TrailConnector läuft."*

`prefetch()` holt alle Wege im Umfeld der kompletten Tour in **einem** Overpass-Abruf und legt sie als Datei
ab; `fetch()` schneidet daraus nur noch lokal aus und geht nicht mehr ins Netz. `main()` ruft das unbedingt
auf. Wer `solve()` direkt benutzt, muss `prefetch()` selbst vorher aufrufen — sonst fällt `fetch()` auf eine
Einzelabfrage pro Lücke zurück (20–80 s pro Fall statt 0,9 s für vier).

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

## Zweite Tour: „Kurztour 1 – Leimen" (2026-08-17)

Erste Anwendung auf eine Tour, mit der das Verfahren nicht entwickelt wurde. **Alle 14 Lücken geschlossen,
23,66 km, weglos 0 m, kein einziges Mal gekappt — 14 von 14 über Fall 1**, ohne dass ein Grenzwert angefasst
werden musste. Vom Nutzer bestätigt („Sieht perfekt aus").

Die Tour hat einen anderen Charakter als Rodalben (Wanderweg-Abschnitte statt MTB-Trails, Lücken bis 185 m)
und trotzdem greift dasselbe Muster. Das stützt die Vermutung, dass das **Verketten der Way-Objekte** der
tragende Schritt ist: sobald eine Straße als Ganzes sichtbar ist, erreicht sie meist beide Lücken-Enden.
Fall 4 und 5 wurden hier gar nicht gebraucht, ebenso keine Verhältnismäßigkeits-Ablehnung — die noch
unbewährten Grenzwerte (`PROJ_MIN_SECOND_M`, die 15-m-Schwellen) sind also weiterhin nur an Rodalben geprüft.

## Dritte Tour: „Kurztour 1 – Rodalben" (2026-08-20)

**Alle 25 Lücken geschlossen, 32,98 km, weglos 0 m.** Vom Nutzer bestätigt. Verteilung: 17× Fall 1, 6× Fall 3,
2× Fall 2, 1× Fall 5.

Diese Tour hat das Verfahren erstmals breiter beansprucht als Leimen — **Fall 3 (Schnittpunkt) sechsmal und
Fall 5 (Wegekette) einmal**, bei Leimen beide gar nicht. Vier Stellen wurden dem Nutzer gesondert vorgelegt
und bestätigt: eine 184-m-Brücke bei 50 m Lücke (Faktor 3,7), eine mit 164 m Kappung gegen eine Alternative
mit 351 m ohne Kappung, eine mit 200 m Kappung **ohne jede Alternative** (derselbe Trail und dieselbe Gegend
wie `seg0` der Felsentrails, wo dasselbe Muster bestätigt wurde), und eine 219-m-Lücke im
Hin-und-zurück-Muster.

**Fall 4 (Projektion) blieb auch hier ungenutzt** — seine Grenzwerte (`PROJ_MIN_SECOND_M`, `PROJ_MAX_MEAN_M`)
sind damit weiterhin nur an Rodalben Felsentrails geprüft.

## Fünf Touren, 114 Lücken (Stand 2026-08-20)

| Tour | Lücken | km | Fälle |
|---|---|---|---|
| Rodalben Felsentrails | 36 | 41,81 | 27×1, 3×2, 2×3, 2×4, 2×5 |
| Kurztour 1 – Leimen | 14 | 23,66 | 14×1 |
| Kurztour 1 – Rodalben | 25 | 32,98 | 17×1, 2×2, 6×3, 1×5 |
| Kurztour 3 – Finsterbrunnertal | 25 | 29,18 | 24×1, 1×5 |
| Kurztour 5 – Johanniskreuz | 14 | 10,65 | 14×1 |

**Alle mit weglos 0 m.** Gesamt: 86× Fall 1, 5× Fall 2, 8× Fall 3, 2× Fall 4, 4× Fall 5.

Bemerkenswert an den letzten zwei Touren: **keine einzige Kappung, keine Verhältnismäßigkeits-Ablehnung**, und
die beiden größten Lücken überhaupt schließen fast maßgenau — 468 m → 483 m Brücke (Faktor 1,03) und
270 m → 271 m (Faktor 1,00). Dort spannt jeweils *ein* verketteter Weg die ganze Lücke, was die Bedeutung des
Verkettungsschritts noch einmal unterstreicht.

**Fall 4 kam in vier von fünf Touren nicht vor** — seine Grenzwerte sind weiterhin nur an zwei Lücken der
ersten Tour geprüft. Das ist erwartbar (schwierige Sonderfälle sind selten), heißt aber: bei einer
Automatisierung sollten Fall 4 und 5 weiter einzeln vorgelegt werden. Fall 1 mit Brücke ≈ Luftlinie und ohne
Kappung wären 86 von 114 Fällen, die ohne Rückfrage durchlaufen könnten.

### Bekannte Nebensache: `len` in `lineTrails` wird nicht mitgezogen

Wächst die Geometrie durch eine Brücke, bleibt die Metadaten-Länge stehen (Abweichung +0,01 bis +0,26 km; die
Seitenleiste zeigt den Metadaten-Wert). Bewusst nicht angefasst, weil laut `CLAUDE.md` offizielle
veröffentlichte Längen Vorrang vor aus der Geometrie berechneten haben und unklar ist, welcher Wert hier
welcher ist. Bei „Kurztour 3 – Finsterbrunnertal" besteht die Abweichung ohnehin schon vorher und ist groß
(30,86 km Metadaten gegen 29,05 km Geometrie) — dort stammen die zwei Zahlen offensichtlich aus verschiedenen
Quellen, unabhängig von diesem Verfahren.

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
