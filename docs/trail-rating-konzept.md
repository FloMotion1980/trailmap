# Konzept: Trail-Bewertung und Beliebtheit

**Status: Konzept, nichts davon gebaut.** Angefragt vom Nutzer am 2026-08-21: Trailforks' eigene Bewertung
und Beliebtheit pro Trail in die App holen. Seine Begründung ist der Maßstab, an dem der Entwurf gemessen
werden muss — *"gerade in größeren Regionen mit vielen Trails kann das ein echter Mehrwert sein"*.

## 1. Das Problem in Zahlen

Die Schwierigkeitsfarbe beantwortet „kann ich das fahren", nicht „lohnt sich das". In einer kleinen Region
fällt das nicht auf, in einer großen ist es die eigentliche Frage:

| Region | Trails | rot + schwarz |
|---|---:|---:|
| Gardasee & Trentino | 916 | 289 |
| Mountainbikepark Pfälzerwald | 805 | — |
| Schwarzwald | 622 | — |
| Nordvogesen | 483 | — |

289 rote und schwarze Trails am Gardasee sind für ein Wochenende keine Auswahl, sondern eine Wand. Genau da
soll eine Reihenfolge helfen.

## 2. Was die Daten wirklich sind (gemessen, nicht angenommen)

Jede Trailforks-Trailseite enthält einen JSON-Block mit diesen Feldern — **anonym abrufbar, ohne Login**.
Gemessen am 2026-08-21 an drei Madeira-Trails:

| Feld | „Hunters" Trail | „21" | „4 Estradas" | was es ist |
|---|---:|---:|---:|---|
| `rating_bayesian` | 4,29 | 4,13 | 4,28 | **Sterne 0–5, stimmenzahl-gewichtet** |
| `rating` | 95 | 87 | 90 | dasselbe als 0–100 |
| `votes` | 4 | 9 | 8 | Anzahl Bewertungen |
| `popularity_score` | 5 | 85 | 50 | Beliebtheit 0–100 |
| `total_checkins` | 114 | 1030 | 324 | Check-ins insgesamt |
| `ridden` | 110 | 648 | 308 | wie oft geloggt gefahren |
| `views` | 3237 | 3105 | 5607 | Seitenaufrufe |
| `faved` | 0 | 0 | 1 | Favorisierungen |

**Der entscheidende Punkt für den Aufwand: das kostet keine einzige zusätzliche Abfrage.**
`tools/harvest_trailforks.py` ruft im `--geo`-Durchlauf ohnehin jede Trailseite einzeln ab, um Polylinie und
Höhenprofil zu holen. Die Felder liegen im selben HTML. Es ist ein Parser-Zusatz von ~15 Zeilen, kein neuer
Harvest.

**Eine Falle beim Auslesen, schon hineingelaufen:** die *Regionstabelle* liefert die Bewertung **nicht** —
dort steht `data-rating="0"` und `data-score="0"` für jeden Trail, während der Tooltip „0 / 5 with 4 votes"
sagt. Die Stimmenzahl steckt in `data-sort`, der Wert nirgends. Wer nur die Tabelle parst, kommt zum Schluss
„Trailforks gibt anonym keine Bewertungen her" — falsch, sie stehen auf der Trailseite.

## 3. Vier Fallen, an denen das Feature scheitern würde

### 3.1 Die Stimmenlage ist dünn — gemessen

Verteilung über alle 184 Madeira-Trails:

| Stimmen | Trails | Anteil |
|---|---:|---:|
| 0 | 42 | 22,8 % |
| 1–2 | 67 | 36,4 % |
| 3–9 | 62 | 33,7 % |
| 10+ | 13 | 7,1 % |

Median 2 Stimmen, Maximum 17. **59 % der Trails haben zwei Stimmen oder weniger.** Ein rohes Sterne-Mittel
ist für die Mehrheit der Region also Rauschen: ein Trail mit einer einzigen 5-Sterne-Stimme steht über einem
mit 4,2 aus 17 Stimmen, und das ist sachlich falsch.

**Konsequenz, nicht verhandelbar:** immer `rating_bayesian` verwenden, nie das rohe Mittel. Trailforks
rechnet die Schrumpfung zum Regionsmittel schon selbst — wir müssen sie nur nicht kaputtmachen. Und **die
Stimmenzahl gehört sichtbar daneben**, damit „4,3 ★ (2)" nicht wie „4,3 ★ (86)" aussieht.

### 3.2 Beliebtheit ist nicht Qualität

Trailforks' eigene Legende sagt, was `popularity_score` ist: *"Popularity colour of trail on map based on
checkins from the past year"*. Das ist Verkehr, nicht Güte. Es bevorzugt systematisch, was nah an Ort, Lift
oder Parkplatz liegt, und was von Trailforks-Nutzern überhaupt geloggt wird. Der abgelegene Klassiker mit
drei Check-ins ist nicht schlechter — er ist abgelegen.

Deshalb: **zwei getrennte Größen, nie zu einem „Score" verrechnet.** Bewertung sagt „gut", Beliebtheit sagt
„viel gefahren". Beides ist nützlich, die Mischung wäre eine Zahl, die nichts mehr bedeutet.

### 3.3 Nicht jede Region hat die Daten

Die Bewertung existiert nur für Trails, die aus Trailforks stammen. Regionen, deren Geometrie und
Schwierigkeit vom Betreiber kommen — Silvretta, Bike Kingdom, Zugspitz Arena, Schladming, Brandnertal,
Serfaus, Laax, Teile des Harzes — haben nichts davon, und das bleibt so.

**Konsequenz für die UI:** „keine Bewertung" ist ein *dritter* Zustand, nicht eine Null. Wird nach Bewertung
sortiert, dürfen unbewertete Trails nicht hinten einsortiert werden, als wären sie schlecht. Sie gehören in
eine eigene, benannte Gruppe („ohne Bewertung"), so wie die Trail-Liste heute schon nach Sub-Region gruppiert.

### 3.4 Es ist eine Momentaufnahme

Die Zahlen sind der Stand des Harvests, nichts synchronisiert sie. Das ist genau die Lage, in der bei den
Liften ein `closed`/`note`-Feld gebaut und wieder verworfen wurde (siehe `docs/lifts-feature.md`): *nichts in
dieser App gleicht Betriebszustände ab, ein fest verdrahteter Wert veraltet und sieht dabei autoritativ aus.*

Unterschied zum Liftfall, und deshalb ist es hier trotzdem vertretbar: eine Sterne-Bewertung driftet über
Jahre, ein Liftfahrplan über Wochen. Aber es muss **datiert** sein — ein `ratingAsOf` pro Region, in
Kartenoptionen oder im Info-Panel lesbar, damit niemand eine drei Jahre alte Zahl für heute hält.

## 4. Datenmodell

Drei optionale Felder pro `lineTrails`-Eintrag, gleiche Bauart wie `uphill` und `loop`:

```json
{ "id": "gd_601_pernici", "name": "601", "region": "gd_garda_trentino", "diff": "rot",
  "len": 4.2, "up": 60, "down": 980,
  "rate": 4.13, "votes": 9, "pop": 85 }
```

- `rate` — `rating_bayesian`, auf zwei Stellen gerundet. Fehlt, wenn `votes` 0 ist.
- `votes` — Stimmenzahl. Fehlt statt 0, damit „nicht bewertet" und „mit 0 bewertet" unterscheidbar bleiben.
- `pop` — `popularity_score` 0–100. Unabhängig von `rate`; kann ohne Bewertung existieren.

Bewusst **nicht** aufgenommen: `views`, `ridden`, `total_checkins`, `faved`. `pop` ist aus ihnen abgeleitet,
und vier Rohzahlen pro Trail wären Gewicht ohne eigene Aussage.

**Größe:** `, "rate": 4.13, "votes": 9, "pop": 85` sind ~38 Zeichen. Gardasee: 916 × 38 ≈ 35 KB auf eine
2,84-MB-Datei, also ~1,2 %. Über alle 28 Regionen ~180 KB. Unkritisch — aber es geht in `version.json` ein,
also ein Hash-Bump pro Region und ein Nachladen auf den Geräten.

`validate_region.py` bekommt die passenden Prüfungen: `rate` nur mit `votes`, `rate` in 0–5, `pop` in 0–100,
und keins der drei Felder in einer Region, die keine Trailforks-Quelle hat.

## 5. UI — an vorhandene Mechanik gehängt, nicht daneben

### 5.1 Sortierachsen (der eigentliche Mehrwert, und das billigste Stück)

Die Trails-Liste hat schon ein Zahnrad mit Gruppierung und Sortierung (`trailSortMode`,
`TRAIL_SORT_COMPARE`, `TRAIL_SORT_DEFAULT_DIR`, persistiert unter eigenem Key). Dort kommen **zwei Achsen**
dazu: **Bewertung** und **Beliebtheit**, beide standardmäßig absteigend.

Das ist der Kern des Wunsches: In einer 916-Trail-Region ist „sortiere nach Bewertung" die Antwort auf „welche
zwanzig lohnen sich". Und es kostet keinen Pixel neue Fläche.

Unbewertete Trails landen dabei in einer eigenen Gruppe am Ende, mit eigener Überschrift und eigener Zahl —
nicht stillschweigend als 0,0 einsortiert (siehe 3.3).

### 5.2 Info-Panel

Eine Zeile bei den Kennzahlen, neben `len` / ⬆️ / ⬇️:

```
★ 4,1 (9 Stimmen)     ·     Beliebtheit 85
```

Fehlt die Bewertung, steht dort „noch nicht bewertet" — nicht „0". Das Panel ist auch der richtige Ort für
das Datum aus 3.4.

### 5.3 Trail-Karte in der Liste

Ein kompaktes `★ 4,1` in der `.trail-meta`-Zeile. **Vorher messen:** laut `CLAUDE.md` hat diese Zeile 96–122 px
gemessenen Spielraum, und `.card-solo-btn` reserviert dort schon 26 px. `★ 4,1` sind ~34 px — passt
voraussichtlich, aber die `lists`-Suite prüft ausdrücklich „kein Kartenname bricht um, während seine Zeile
noch Platz hat", und dieser Fall ist genau das, was diese Prüfung fangen soll. Also: bauen, messen, und wenn
es kneift, gehört es nur ins Panel.

### 5.4 Filter

Ein Schwellenfilter („ab ★ 4,0") im Filter-Abschnitt. **Mit einer Bedingung:** unbewertete Trails müssen
standardmäßig *drin* bleiben, sonst verschwinden in einer frisch gesweepten Region 23–59 % der Trails, ohne
dass jemand etwas über sie behauptet hätte. Also zwei Schalter, nicht einer: die Schwelle, und „ohne
Bewertung anzeigen" (Standard: an).

### 5.5 Was auf der Karte NICHT passiert

**Keine Farb- oder Deckkraft-Kodierung der Bewertung auf der Trail-Linie.** Die Linienfarbe ist die
Schwierigkeit, und das ist nach den eigenen Worten des Nutzers *"einer der großen Mehrwerte unserer App"* —
diese Aussage zu verwässern, um eine zweite Größe unterzubringen, wäre ein schlechter Tausch. Trailforks
liefert sogar ein fertiges `popularity_colour` (z. B. `ff5100`); es bleibt ungenutzt.

Falls Beliebtheit später doch auf die Karte soll, ist Linien**stärke** der einzige Kanal, der nicht mit der
Farbe kollidiert — und selbst der kollidiert mit Hover, Auswahl und dem RIDE-Fokus-Halo, die alle über die
Stärke arbeiten. Nicht in der ersten Stufe.

## 6. Rollout

Betroffen sind die Trailforks-Regionen. Reihenfolge nach Nutzen (= Trailzahl):

1. **Gardasee & Trentino** (916) und **Madeira** (158) — die beiden, die komplett aus Trailforks kommen und
   deren Harvest-Dateien aktuell sind. Hier ist der Nutzen am größten und der Weg am kürzesten.
2. **Nordvogesen** (483), **Südvogesen** (474), **Varazze** (195), **Finale** (219) — Trailforks-basiert,
   Harvest liegt in `Material/`.
3. **Schwarzwald** (622), **Pfälzerwald** (805), **Harz** — Mischquellen: nur die Trails mit
   Trailforks-Herkunft bekommen Werte, der Rest bleibt leer. Das ist der Fall, für den 3.3 existiert.

**Kosten:** eine Trailseite pro Trail, also derselbe Durchlauf wie beim Geometrie-Harvest. Gardasee ~993,
Madeira ~160 Seiten bei 0,8 s Pause ≈ 15 min zusammen; alle Trailforks-Regionen ~3 000 Seiten ≈ 40 min. Der
Harvester ist fortsetzbar und überspringt, was er hat.

## 7. Erste Ausbaustufe (klein und abgeschlossen)

1. `harvest_trailforks.py`: die vier Felder aus dem Trailseiten-Blob mitparsen und in
   `trailforks_table.json` schreiben (`--fields` läuft dieselben Seiten erneut, ohne Geometrie neu zu bauen).
2. `build_trailforks_region.py`: `rate` / `votes` / `pop` in die `lineTrails`-Einträge übernehmen.
3. Gardasee und Madeira neu bauen, `validate_region.py` um die Feldprüfungen erweitern, Hashes bumpen.
4. Zwei Sortierachsen in der Trails-Liste, unbewertete als eigene Gruppe.
5. Die Zeile im Info-Panel.

Filter (5.4) und Karten-Darstellung (5.5) bewusst **nicht** in Stufe 1 — erst ansehen, ob die Sortierung
allein die Frage schon beantwortet.

## 8. Tests

- **`trailforks`-Suite** (Python): der Trailseiten-Parser gegen eine echte, eingefrorene Blob-Fixture — und
  ausdrücklich ein Fall, der beweist, dass die **Regionstabelle** die Bewertung *nicht* liefert (3.2 oben),
  damit niemand den Parser „vereinfacht" und wieder Nullen einliest.
- **`regiondata`** (Python): eine Region ohne Trailforks-Quelle darf keins der Felder tragen; `rate` nie ohne
  `votes`.
- **`lists`** (Browser): die zwei neuen Sortierachsen sortieren wirklich (und umgekehrt beim zweiten Tippen);
  unbewertete Trails stehen in ihrer eigenen Gruppe und werden nicht als 0,0 eingemischt; die Karten-Geometrie
  bleibt unverändert (die bestehende Umbruch-Prüfung ist die scharfe hier).
- **`infopanel`** (Browser): „noch nicht bewertet" statt „0" bei fehlender Bewertung.

## 9. Offene Fragen für den Nutzer

1. **Beliebtheit überhaupt anzeigen, oder nur die Bewertung?** Beliebtheit ist die schwächere Aussage (3.2)
   und kostet eine zweite Sortierachse plus Panel-Platz.
2. **Soll die Sortierung nach Bewertung der neue Standard der Trails-Liste werden** (heute: Schwierigkeit
   innerhalb der Sub-Region), oder bleibt sie eine Option, die man wählt?
3. **Reicht Stufe 1**, oder soll der Schwellenfilter (5.4) gleich mit?
