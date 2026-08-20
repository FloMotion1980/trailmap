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

### Fall 0 — Überlappung: `seg10`, Kurztour 6 Landstuhl (Ost) (2026-08-20)

Vom Nutzer gefunden, und der erste Fall, der **keine Lücke** ist: „Außerdem überlappen bereits in der
Originaltour zwei Trails: Der Anfang von Pavillonplatz Trail, das Ende von Landstuhl Trail 2. Da könnte man
einen von beiden Trailabschnitten kürzen. Das ist ein neuer Fall denke ich."

Gemessen: „Landstuhl Trail 2" (467 m) endet **6,0 m neben** der Linie von „Pavillonplatz Trail" (682 m) und
projiziert **82 m hinter deren Anfang**; umgekehrt liegt Pavillonplatz' Anfang 6,1 m neben Landstuhl Trail 2
und 107 m vor dessen Ende. Beide durchlaufen dasselbe ~82–107 m lange Stück, und die aufeinander folgenden
Punkte projizieren monoton — also **dieselbe Richtung**. Die Tour fährt das Stück damit zweimal: einmal als
Ende des einen Abschnitts, dann rückwärts zurück zum Anfang des anderen und wieder vorwärts.

**Lösung: den NACHFOLGENDEN Abschnitt bis zum Ende des vorigen kappen.** Die Fahrtrichtung entscheidet — sein
Anfangsstück ist zu dem Zeitpunkt schon gefahren, und zwar mit der Geometrie des vorigen Abschnitts. Ergebnis:
Pavillonplatz 682 m → 600 m (−12 %), Landstuhl Trail 2 unangetastet, Brücke 6 m (der reine Querversatz).

Zwei Dinge daran sind wichtig:

- **Fall 0 muss vor allen Brückenfällen geprüft werden.** Fall 1 fand für dieselbe Stelle eine formal saubere
  Lösung — 89 m Brücke, weglos 0, keine Kappung — die aber genau **rückwärts über die Überlappung** führt. Nach
  Fallnummer sortiert gewinnt Fall 0; hieße er `6_`, gewänne die falsche Lösung.
- **Die Richtungsprüfung ist nicht optional.** Bei entgegengesetzter Richtung ist ein doppelt gefahrenes Stück
  legitim — der Nutzer hat genau so eine Stelle in Rodalben Felsentrails als richtig bestätigt („Da ist eine
  Pausenstelle und deswegen fährt man das Stück hin und zurück"). Geprüft wird, ob die letzten Punkte von A,
  soweit sie auf B liegen, auf B monoton nach vorne projizieren.

Die umgekehrte Variante (den *vorigen* Abschnitt kappen) ist **absichtlich nicht eingebaut** — an keinem Fall
geprüft, und ein ungeprüftes Muster hat hier schon sechs Anläufe gekostet.

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
- **Ein benannter Trailabschnitt darf nicht per Reparatur verschwinden.** Die Verhältnismäßigkeitsgrenze bezog
  die Kappung nur auf die **Lücke** — bei `seg8` der Kurztour 6 Landstuhl (Ost) durfte eine 133-m-Lücke also
  242 m kappen, und weil „Steps Heidenfelsen" genau 242 m lang war, löste sich der ganze Abschnitt auf
  (5 Punkte → 1). Der Nutzer hat es auf der Karte gesehen: „ist das Stück hier kaputt gegangen". Es braucht
  **zusätzlich** eine Grenze relativ zur **eigenen Länge des Segments** (`MAX_SEG_TRIM_FRACTION`, halbe Länge)
  und ein Minimum an Punkten.
- **Die Kappung als Längendifferenz rechnen, nicht über Punktzahlen.** Fall 0 setzt einen projizierten Punkt an
  die Stelle des weggeschnittenen Anfangs — die Punktzahl bleibt gleich, also hätte eine punktbasierte Messung
  82 doppelt gefahrene Meter als „0 m gekappt" gemeldet und die Segment-Grenze hätte sie nicht gesehen.
- **Dieselbe Schwelle für Tor, Vorauswahl und Sortierung.** Die Rangfolge rundete weglos auf ganze Meter, das
  Tor `weglos > 0` tat es nicht: ein Kandidat mit 0,4 m wurde als „0 m" angezeigt, sortierte wie 0 und wurde
  dann als mangelhaft verworfen — bei `seg10` der Kurztour 6 Landstuhl (West) blieb die Lücke offen, obwohl
  der Report eine saubere Lösung meldete. Jetzt eine Konstante (`OFF_TOL_M`, 0,5 m) für alle drei.
- **Ablehnungsgrund an einer Stelle bestimmen.** Er stand zweimal im Code — einmal als Tor für die Kettensuche,
  einmal für den Report — und die beiden liefen auseinander: bei `seg8` galt der einzige Kandidat als brauchbar,
  also lief Fall 5 nicht an, und danach verwarf ihn die neue Segment-Grenze doch. Ergebnis: Lücke offen, obwohl
  Fall 5 sie über Pfad → Wohnstraße → Forstweg ohne jede Kappung schließt.
- **Verschmelzen ist ein zusätzlicher Kandidat, kein Ersatz.** Bei `seg14` derselben Tour erreicht der
  *unverschmolzene* 255-m-Pfad beide Seiten und liefert 94 m Brücke für 88 m Lücke; in eine 2472-m-Kette aus
  fünf Teilstücken verschmolzen wachsen daraus 1041 m, weil sich die Projektionen von a und b auf der langen
  Kette weit auseinanderschieben. Beide Formen antreten lassen.
- **In Fall 1 nicht nach dem ersten Treffer abbrechen.** „Liegt dem Endpunkt am nächsten" sagt nichts darüber,
  wie gut die Brücke wird — bei `seg14` lagen fünf Wege bei 0,0 m unter dem Endpunkt.
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

## Dreizehn Touren, 235 Lücken (Stand 2026-08-20)

Achter bis dreizehnter Einsatz: die restlichen acht Kurztouren, **121 Lücken, alle geschlossen, keine offen**.
Fallverteilung über diese 121: 102× Fall 1, 9× Fall 3, 4× Fall 2(B), 2× Fall 5, 1× Fall 5+kappen(A),
1× Fall 5+kappen(B), 1× Fall 2(A), 1× Fall 0. Nur sechs Trailabschnitte wurden überhaupt gekappt.

Diese Runde hat das Verfahren an fünf Stellen verändert (siehe die handwerklichen Regeln), ausgelöst durch
**einen** Befund des Nutzers an „Kurztour 6 – Landstuhl (Ost)": ein aufgelöster Trailabschnitt und eine
Überlappung. Die Nachrechnung gegen die fünf bestätigten Touren ist der Grund, warum das überhaupt
verantwortbar war — und sie brauchte erst eine brauchbare Referenz:

- **Der bestätigte Stand von Rodalben Felsentrails ist KEINE Referenz für das Werkzeug.** Er enthält
  Lösungen, die es nicht erzeugen kann: `seg0` kappt 230 m bei 34,9 m Lücke, Faktor 6,6 gegen eine Grenze von
  4,0. Beim Schließen der Tour stand `MAX_TRIM_FACTOR` sogar auf 3,0. Der Doku-Eintrag „36 von 38 Segmenten
  identisch" heißt genau das: zwei Segmente waren von Hand. Ein Vergleich dagegen meldet 18 von 38 — auch mit
  **allen** Änderungen abgeschaltet, was per Ablation nachgewiesen ist.
- **Die belastbare Prüfung ist Werkzeug-wie-committet gegen Werkzeug-mit-Änderung, auf demselben
  Ausgangsstand.** Ergebnis über alle fünf bestätigten Touren: es ändern sich **ausschließlich
  Verbinder-Segmente, um 0–9 m kürzer**, kein einziger Trailabschnitt, und keine Lücke bleibt zusätzlich offen.
- **Dafür lassen sich alle Schwellen per `NTC_*`-Umgebungsvariable überschreiben.** Das ist kein
  Konfigurations-Feature, sondern das Werkzeug für genau diese Pflichtaufgabe: nur so lässt sich eine von
  mehreren gleichzeitigen Änderungen einzeln abschalten und messen. Ohne das bleibt bei einer Abweichung nur
  Raten. `MERGE_ONLY` und `CASE1_FIRST_ONLY` schalten die beiden Kandidaten-Änderungen ab.

---

## Zweiter Durchgang mit gelockerter Verhältnismäßigkeit (2026-08-20)

`seg0` und `seg34` von Rodalben Felsentrails waren vom Nutzer auf der Karte bestätigt, aber unter den strengen
Grenzen unerreichbar. Genau gemessen:

| Lücke | bestätigte Lösung | scheitert an |
|---|---|---|
| `seg0`, 34,9 m | Brücke 240 m, kappt 230 m von 711 m | Kappungsfaktor 6,6 > 4,0 **und** Brückenfaktor 6,9 > 6,0 |
| `seg34`, 22,0 m | Brücke 116 m, kappt 95 m von **150 m** | Kappungsfaktor 4,3 > 4,0 **und** Segment-Grenze 63 % > 50 % |

Der zweite Punkt ist der lehrreiche: **63 % eines kurzen Abschnitts war die richtige Antwort.** Am
Hilschberghaus bleibt nur diese Lösung durchgehend auf der Straße; die kappungsfreie Alternative dort ist eine
1459-m-Kette, Faktor 66. Meine 50-%-Grenze hat sie also zu Unrecht verboten.

**Global lockern war der falsche Weg, und das war messbar.** Mit 7/7/0,65 schließen beide Lücken mit genau den
bestätigten Kappungen — aber Landstuhl (Ost) `seg21` wechselt dann von einer Schnittpunkt-Lösung mit Faktor
1,02 und **ohne** Kappung auf eine, die 76 m von 151 m eines benannten Abschnitts wegschneidet. Ursache: die
Fallnummer rangiert vor der Brückenlänge, also überholt Fall 2 eine fast perfekte Fall-3-Lösung, sobald er
viel kappen darf.

Die Rangfolge umzusortieren (nach Brücke + Kappung als gemeinsamem Maß) war der zweite Versuch und **wurde
verworfen**: `seg21` war damit behoben, aber zwei andere Stellen brachen auf, darunter eine, die von Fall 1 auf
Fall 3 rutschte — für wenige Meter kürzere Brücke schlechteres Vertrauen. **Die Fallhierarchie kodiert
Vertrauen, nicht Länge; Kosten dürfen sie nicht überstimmen.**

Was funktioniert, hat dieselbe Bauform wie Fall 5: **gelockert wird nur, wo streng gar nichts Brauchbares übrig
bleibt.** `RELAX_BRIDGE_FACTOR = 7.0`, `RELAX_SEG_TRIM_FRACTION = 0.65`, und `MAX_TRIM_FACTOR` fällt im zweiten
Durchgang ganz weg — nachgemessen bringt er nichts, was die anderen zwei nicht schon leisten, und die Kopplung
„gekappte Meter gegen Lückengröße" sagt ohnehin nichts darüber, ob das Kappen an dieser Stelle richtig ist.

Ergebnis: Felsentrails 38/38, Landstuhl Ost und West **unverändert**, drei weitere Touren bytegleich
nachgerechnet. Ein so geschlossener Übergang wird als `[GELOCKERT -- ansehen]` gemeldet, und *welche* Lücken
den zweiten Durchgang brauchen, ist Teil der festgeschriebenen Erwartung — eine Lücke, die neu darin auftaucht,
hat ihre verhältnismäßige Lösung verloren, und das ist ein Befund.

Die zwei Werte stammen aus genau diesen zwei bestätigten Fällen und liegen knapp darüber. Sie sind **nicht**
breit geprüft.

Zur Einordnung: in der ausgelieferten Region hatte Felsentrails schon vorher 0 Lücken. Die zwei „offenen"
Lücken gab es nur beim Neurechnen vom Ausgangsstand — es ging also um das Können des Verfahrens für künftige
Touren, nicht um fehlende Daten in der App. Die Region wurde deshalb **nicht** neu geschrieben: das Ergebnis
weicht in 16 Verbindern von dem bestätigten Stand ab (anders geroutet, teils kürzer), und dafür gibt es keinen
Anlass, der eine erneute Durchsicht rechtfertigt.

---

## Wahrzeichen-Touren und zwei Fernwege (2026-08-20)

Vier der fünf Wahrzeichen-Touren waren offen. Drei davon sind jetzt zu, und die vierte ist eine andere
Aufgabe:

| Tour | Lücken | Ergebnis |
|---|---|---|
| Felsenwanderweg Rodalben | 16 | zu, 18 Segmente, 44,29 km |
| Ost-West-Passage | 60 | zu, 71 Segmente, 78,32 km — **Punkt-zu-Punkt** |
| Trans Pfälzerwald | 58 | zu, 65 Segmente, 91,24 km — **Punkt-zu-Punkt** |
| Dahner Felsenpfad | 0 | ein einziges Segment, also **keine** Trail-Zuordnung — Zuordnungs-, nicht Lückenarbeit |

**Ein Fernweg ist keine Runde, und das war lebensgefährlich für die Zählung.** Die „Ost-West-Passage" beginnt
37 km von ihrem Ende, die „Trans Pfälzerwald" 38,6 km. Wer jede Tour über `(i+1) % n` durchläuft, sieht dort
eine 37-km-„Lücke" — sie zu überbrücken wäre nicht bloß falsch, die Wegesuche würde dafür ein halbes
Bundesland laden. `MAX_GAP_M = 1500` fängt das ab und **meldet** es, statt es zu überspringen: es kann auch
bedeuten, dass eine Tour in zwei Teile zerfallen ist. Die größte echte Lücke im ganzen Bestand ist 976 m, die
Grenze liegt also weit über allem Vorkommenden.

**Lange Touren brauchen ein anderes Vorab-Laden.** Die Gesamtbox der „Trans Pfälzerwald" ist 14 × 38 km =
534 km², die Vereinigung ihrer Lückenboxen nur 46 km². `prefetch_gaps()` holt letztere — weiter **ein** Abruf
(die feste Regel bleibt gewahrt), nur zehnmal weniger Daten. Das Ergebnis ist beweisbar dasselbe, weil
`fetch()` ohnehin auf die Box der einzelnen Lücke mit demselben Rand filtert und Overpass' Box-Filter dasselbe
Kriterium benutzt; an zwei bestätigten Touren bytegleich nachgemessen.

### Zwei Verfahrensfehler, beide von diesen Touren aufgedeckt

Das ist das Argument dafür, eine Änderung erst auf einer *neuen* Tour laufen zu lassen, statt sie zu
durchdenken:

**1. Der Freibetrag für den Anschluss-Versatz muss dieselbe Zahl sein wie die Endpunkt-Toleranz.** Beide
standen auf 15, bis `ON_WAY_M` heute Morgen auf 20 ging — danach wurde ein Anschluss, der bei 16 m als „auf
dem Weg" akzeptiert wird, für genau diese 16 m bestraft. Gefunden an `seg37` der Ost-West-Passage: 124 m
Brücke für 109 m Lücke, durchgehend auf einer Landstraße, Kern **0,00 m** abseits — und verworfen, weil der
Trail-Endpunkt 16,3 m neben der Straße aufgezeichnet ist. Das Maß liest jetzt `ON_WAY_M`, was die beiden per
Konstruktion koppelt. Das schloss nicht nur diese Lücke, sondern **hob vier Kappungen auf, die dieselbe
Inkonsistenz erzwungen hatte** — darunter „Lambrecht Trail 7" mit −39 %, „Felsenweg Nord" +199 m und
„Gipfelstürmer" +163 m in Kurztour 1 Rodalben, und „Curvy Up'N'Down" in Landstuhl Ost.

**2. Die Kappung gehört in die Rangfolge — innerhalb eines Falls, nie davor.** An `seg0` des Felsenwanderwegs
Rodalben standen zwei Fall-5-Lösungen nebeneinander: 654 m Brücke mit **1095 m** Kappung und 698 m Brücke mit
62 m. Ohne die Kappung im Schlüssel entschied allein die Brücke — 44 m kürzer, dafür 1033 m echter Trail weg.
Davor zu sortieren ist der umgekehrte Fehler und ebenfalls gemessen (siehe den Abschnitt zum zweiten
Durchgang): Landstuhl Ost `seg15` rutschte dann von Fall 1 auf Fall 3.

Danach wurden **alle 15 Touren einmal mit dem endgültigen Verfahren neu gebaut**, damit der ganze Bestand aus
einem Verfahren stammt. Rodalben Felsentrails blieb auf Wunsch des Nutzers unangetastet. Ergebnis: 17 Touren
ohne eine einzige offene innere Lücke, und nur noch sieben gekappte Abschnitte im ganzen Bestand.

---

## Regressionstest (2026-08-20)

`python tests/run.py --suite ntcregression` — 12 Fälle, ~60 s. Rechnet drei Touren aus ihrem Stand **vor** dem
Schließen neu und vergleicht gegen `tests/fixtures/ntc_baseline.json`: geschlossene Lücken, welcher Fall wo
gegriffen hat, jede Brückenlänge, jede Kappung, und die Restlänge jedes benannten Trailabschnitts.

Es gibt ihn, weil das Verfahren zweimal still schlechter geworden ist und beides erst auf der Karte auffiel.
Die Regionsdatei kann das nicht zeigen — sie enthält das alte, schon gute Ergebnis, an dem eine Degradation
im Verfahren nichts ändert. `MAX_TRIM_FACTOR = 3.0` blieb so vier Tage unbemerkt.

Drei Entscheidungen daran sind wichtig:

- **Die Wege liegen gepackt daneben** (264 KB für drei Touren), und zwar genau die Vereinigung der
  Bounding-Boxen, die `fetch()` pro Lücke selbst benutzt — beweisbar dieselbe Wegemenge wie im echten Lauf.
  Ein Test, der Overpass braucht, wird nicht gelaufen; einer mit einer engeren Auswahl prüft etwas anderes.
- **Der Test ruft `close_gaps()` aus dem Werkzeug**, nicht eine Kopie der Schleife. Die Annahmeregeln
  (weglos-Tor, Verhältnismäßigkeit) sind selbst Teil dessen, was regressieren kann.
- **Ein Fall liest die Erwartung absichtlich NICHT**: „ein Reparaturschritt darf keinen Trailabschnitt
  auflösen" gilt auch dann, wenn jemand die Erwartung mit dem Fehler drin neu erzeugt — genau so segnet ein
  Golden-File-Test sonst eine Regression ab.

Elf Mutationen sind nachgemessen und in der Suite tabelliert, drei Deckungslücken benannt: Fall 4 kommt in
keiner reproduzierbaren Tour vor, `MAX_TRIM_FACTOR` ist nur nach unten festgenagelt, `MEET_M`/`OFF_TOL_M` nur
grob. Und eine Warnung aus eigener Erfahrung: die erste Fassung der Tabelle behauptete eine Mutation, die
nichts tat. **Eine Mutationstabelle muss gelaufen sein, nicht gedacht.**

---

## Offen

- **Andere Trailrunden.** Bisher nur `pw_rodalben_felsentrails` behandelt; jede andere Tour mit
  `trailSegments` hat ihre Lücken unverändert. Das Verfahren steckt in `tools/nearby_trail_connector.py` und
  sollte dort ohne Änderung anwendbar sein — aber jede neue Tour zuerst im Trockenlauf ansehen, nicht blind
  schreiben.
- **Zwei Grenzwerte sind noch nicht belastbar geprüft**: `PROJ_MIN_SECOND_M` (40 m) hat bei `seg33`/`seg34`
  Fall 4 blockiert, was dort richtig war — ob der Wert generell passt, zeigt erst die nächste Tour.
  `MEET_M`/`ON_WAY_M` mussten von 8 m auf 15 m und 2026-08-20 auf 20 m, weil zwei unabhängige Fälle bei 15,2 m
  und 15,9 m knapp herausfielen und dadurch gar nicht erst geprüft wurden.
- **Zwei Kappungen über einem Drittel sind noch nicht vom Nutzer beurteilt**: „Lambrecht Trail 7" −39 %
  (511 → 311 m) und „Westpfalz-Wanderweg Schwarzes W" −36 % (549 → 353 m). Beide entstehen, weil das Maß
  weglos zuerst zählt und die kappungsärmere Alternative 11 m weglos hat. Innerhalb der Grenze, aber viel.
- `tools/close_loop_gaps.py` und `tools/gap_variants.py` enthalten viel Verworfenes und sind **nicht** der
  Stand dieses Dokuments — nur `nearby_trail_connector.py` ist es.
