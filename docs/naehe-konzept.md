# „In der Nähe" — Umgebungssuche um einen frei wählbaren Punkt

**UX-Konzept, entschieden mit dem Nutzer am 2026-08-24. Noch nicht gebaut — ausdrücklich seine Anweisung
("noch nicht bauen").** Gehört zu `docs/backlog.md` Punkt 2 und setzt `docs/trail-rating-konzept.md` voraus.

## Was es beantwortet

„Welche guten Trails sind hier in der Nähe?" — in einer Region mit 916 Trails (Gardasee) oder 805
(Pfälzerwald) beantwortet weder die Schwierigkeitsfarbe noch die Bewertung allein diese Frage, weil beide
nichts über die Entfernung sagen.

## Der Anker ist das Feature

Ein Bezugspunkt auf der Karte mit **zwei Wegen, ihn zu setzen**:

1. **Langer Druck auf die Karte** — der eigene Punkt, der Normalfall.
2. **Die eigene Position** (in der Ankerzeile), wenn eine vorliegt.

**Der Lift ist bewusst KEIN dritter Eingang** (Nutzer, 2026-08-24, nachdem er es zunächst so gesehen hatte:
„Das mit dem Lift würde ich nicht machen. Dann eher wenn man einen Lift anklickt, welche Startpunkte von
Trails von dort aus erreichbar sind"). Das ist die bessere Frage und eine andere: die Umgebungssuche
beantwortet „was liegt um diesen Punkt herum" und misst dafür zur nächsten Stelle einer Linie — beim Lift
geht es um **Einstiege** und um die Fahrtrichtung, also darum, was man von der Bergstation aus überhaupt
hinunterfahren kann. Steht als eigener Punkt im Backlog.

## Die Entscheidungen und ihre Gründe

| Frage | Entscheidung | Grund |
|---|---|---|
| Wie setzen? | langer Druck, plus Hinweis | Die Geste ist frei (auf der Karte hört heute nur ein kurzer Tipp), und die App hat für genau diese Lehrsituation schon ein Muster: den „Halten für Folgen-Modus"-Hinweis am Positionsknopf. |
| Wo steht die Bedienung? | eine **Ankerzeile, die erst erscheint, wenn ein Punkt gesetzt ist** | Wie der Highlights-Regler, der erst auftaucht, wenn es Bewertungen gibt. Im Ruhezustand kostet das Feature keine Fläche — um den senkrechten Platz in der Seitenleiste ist mehrfach gerungen worden. |
| Entfernung wozu? | **Luftlinie zur nächsten Stelle des Trails** | Die *erreichbare* Stelle wäre besser, braucht aber Navigation über OSM-Daten. Vom Nutzer so entschieden: „Für den Anfang geht zur nächsten Stelle des Trails." |
| Sortiert wonach? | **Bewertung**, der Radius filtert | Sonst steht der mittelmäßige Trail vor der Haustür über dem Highlight zwei Kilometer weiter — und das war der Zweck. Bewertung und Beliebtheit werden weiterhin **nicht** zu einem Score verrechnet. |
| Radius | **Regler mit Trefferzahl** („3 km · 9 Trails") | Dasselbe Idiom wie der Highlights-Regler; die Zahl daneben ist das, was eine nackte Entfernung lesbar macht. |
| Gemerkt? | **nein** | Ein Punkt gehört zu einer Situation, nicht zu einer Einstellung — wie `showHighlightsOnly` und `rideMode`, anders als die Regionsauswahl. |
| RIDE-Modus | **unangetastet** | Ausdrücklich der Nutzer: „im Ride Modus gar nix ändern. Das ist nur für die normale App." |

## Wie das Ergebnis erscheint — und warum das Handy die eigentliche Frage ist

Am Schreibtisch steht die Seitenleiste dauerhaft neben der Karte: man sieht Punkt und Liste gleichzeitig, es
gibt nichts zu entscheiden. **Auf dem Handy ist die Seitenleiste eine Schublade, die die Karte vollständig
verdeckt** (`position:fixed`, `z-index:2500`, `min(88vw,340px)`) — man setzt also einen Punkt auf der Karte
und müsste die Karte zudecken, um die Antwort zu lesen.

Deshalb **antwortet dort die Karte selbst**:

* alles außerhalb des Radius wird **gedimmt**, nicht ausgeblendet — genau wie „Nur Highlights" es tut;
* eine schmale Zeile am Kartenrand nennt „3 km · 9 Trails" und trägt „Liste" und „✕";
* „Liste" öffnet die Schublade mit der vollständigen, nach Bewertung sortierten Liste samt Entfernung je
  Kachel.

**Keine Rangnummern auf der Karte** (Nutzerentscheidung): die Reihenfolge liest man in der Liste, und die
Karte bleibt ruhig. Damit entfällt auch die Frage, ob Nummern eigene Marker oder Label-Präfixe wären.

Verworfen wurde ein **halbhohes Blatt** über der Karte (Karte oben, ausziehbare Liste unten). Es zeigt beides
gleichzeitig, wäre aber eine dritte Ansicht derselben Liste und eine Flächenart, die die App noch nicht hat.
Bleibt die Rückfallebene, falls die Kartenzeile im Gebrauch zu wenig ist.

## Was das im Code berührt

Der Grund, warum diese Form billig ist: **jeder Baustein existiert schon.**

* **Dimmen** — `applyHighlightDimming()` und `baselineLineOpacity(lid)` dimmen heute alles, was kein
  Highlight ist. Der Radius ist dieselbe Operation mit einer zweiten Bedingung. Vorrang beachten: Solo ist
  spezifischer als beides und muss gewinnen (steht so in `CLAUDE.md`).
* **Filtern** — der Radius gehört in `trailPassesFilters(t)`, die einzige Sichtbarkeitsregel, die die
  Kartenschleife *und* die Tourenliste benutzen. Alles andere lässt die beiden auseinanderlaufen.
* **Sortieren** — eine dritte Achse in `TRAIL_SORT_COMPARE` / `TRAIL_SORT_DEFAULT_DIR` (aufsteigend) plus
  ein Chip in `syncTrailViewChips()`.
* **Rechnen** — `haversineM` gibt es schon. Vorfilter über `layer.bounds`, um den Radius erweitert, dann
  Punkt für Punkt nur für die Übrigbleibenden: bei 4 555 Trails bleiben typisch ein Dutzend.
* **Geometrie** — Ring als `L.circle`, Ankerpunkt als `L.circleMarker`, beide im **rotierenden** Pane
  (`ROTATING_PANE()`), sonst stehen sie still, während sich die Karte dreht. Eigene Farbe, damit der Anker
  nie mit dem blauen Positionspunkt verwechselt wird.

Zwei Fallen, die vor dem Bauen zu bedenken sind:

1. **Der lange Druck muss den bestehenden Tipp-Abfangmechanismus kennen.** `map.getContainer()` trägt schon
   ein `touchstart`/`touchend`-Paar, das für eine Berührung auf einer Leaflet-Linie selbst einen `click`
   auslöst (weil Browser den synthetischen Klick an der *touchend*-Position hit-testen und iOS Safari den
   ersten Tipp auf ein hover-reaktives Element verschluckt). Wird aus der Berührung ein langer Druck, muss
   dieser Klick unterdrückt werden — sonst setzt ein Druck auf einen Trail den Anker **und** wählt den Trail
   aus. Schwellen wie dort: Bewegung über 14 px bricht ab, die Zeitmarke liegt bei 500 ms.
2. **Die Zeile am Kartenrand darf nicht unten mittig sitzen** — dort steht `#offlineBanner` (26 px über dem
   Attributionsstreifen). Oben links ist frei, seit der Schubladen-Griff am 2026-08-02 in den Header
   gewandert ist.

Auf dem Schreibtisch ist die Geste der **Rechtsklick** (`contextmenu` auf der Karte) — dort gibt es keinen
langen Druck, und `contextmenu` ist bisher nur auf dem Positionsknopf abgefangen.

## Leerer Radius

„Kein bewerteter Trail in 3 km" ist ein echtes Ergebnis, kein Fehler — die Zeile sagt es und bietet den
nächstgrößeren Radius mit einem Tipp an. Der Text nennt die Zahl, nicht die Ursache: in vier Regionen
(Donnersberg, 3-Länder, Serfaus, Waldmeister) gibt es überhaupt keine Bewertungen, dort ist „in der Nähe"
nach Bewertung sinnlos und die Achse müsste auf Entfernung allein zurückfallen.

## Ausbaustufen

* **Erreichbare Stelle statt Luftlinie** — die eigentlich richtige Messung, braucht Routing über OSM-Daten.
  Ein Trail, dessen Mitte 200 m entfernt vorbeiführt, dessen Einstieg aber drei Kilometer bergauf liegt, ist
  nicht „in der Nähe" in einem Sinn, der einem Fahrer hilft.
* Der Lift-Fall ist ein eigenes Feature, kein Ausbau dieses hier — siehe `docs/backlog.md`.
