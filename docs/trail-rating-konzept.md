# Konzept: Trail-Bewertung und Beliebtheit

**Status: Stufe 1 ist gebaut (2026-08-23, Testregion Finale) — siehe den letzten Abschnitt. Der Rest
ist Konzept.** Angefragt vom Nutzer am 2026-08-21: Trailforks' eigene Bewertung
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

---

# Stufe 1 ist gebaut (2026-08-23, Testregion Finale)

Der Nutzer hat Finale als Testregion gewählt — große Zielregion, gute Datenlage, und er kennt sie selbst.
Bikeparks stehen bewusst hinten an ("Für Bikeparks sehe ich da wenig Mehrwert"), und die Gruppierung
"Top 3 pro Hub" ist bewusst NICHT gebaut: ob Hubs die richtige Klammer sind, hängt an der Region.

## Was drin ist

| | |
|---|---|
| Daten | `rate`/`votes`/`pop` an 131 der 219 Finale-Trails (60 %), plus ein `ratings`-Block mit Quelle und Datum |
| Sortierachsen | **Bewertung** und **Beliebtheit** in der bestehenden Zahnrad-Leiste, absteigend als Standard |
| Unbewertete | eigene Überschrift "ohne Bewertung (n)", NICHT als 0 untensortiert |
| Karte | Schalter **"Nur Highlights"** in Kartenoptionen — dimmt alles außerhalb des oberen Fünftels der Region |
| Label | ★ vor dem Namen, nur bei Highlights |
| Info-Panel | `4,77 ★ (124 Stimmen · Stand 2026-08-23) Beliebtheit 95`, bzw. "noch nicht bewertet" |
| Gate | die ganze Rating-UI blendet sich aus, wenn die aktiven Regionen unter 35 % Abdeckung liegen |

## Die Entscheidungen, die sich beim Bauen geschärft haben

**Die Highlight-Schwelle ist relativ, nicht absolut.** Ein festes "ab 4,4 Sterne" wäre genau die
regionsübergreifende Aussage, gegen die dieses Dokument argumentiert. Gebaut ist stattdessen das obere
Fünftel der bewerteten Trails **je Region** (`HIGHLIGHT_QUANTILE`), und nur wenn die
Region überhaupt 10 bewertete Trails hat. In Finale ergibt das 22 Trails von 219 — ein langes Wochenende.

**Der Schalter erfindet keine Mechanik.** Er ruft dieselbe `baselineLineOpacity()`, die jedes Hover-Ende
und jedes Solo-Ende schon fragt. Solo gewinnt über Highlights, weil es die spezifischere Anfrage ist.

**Das Gate ist der Grund, warum das Feature in anderen Regionen nicht peinlich wird.** Gemessene
Abdeckung: Finale 60 %, Madeira 34 %, Pfälzerwald 0–3 %. Unter 35 % verschwinden Chips und Schalter, und
ein gespeicherter Highlights-Zustand wird aktiv zurückgesetzt — sonst bliebe die Karte gedimmt, während der
Schalter zum Ausschalten nicht mehr da ist.

## Drei Fehler, die das Bauen selbst aufgedeckt hat

Alle drei sind jetzt mutationsgeprüft (`tests/browser/rating.js`, 8 Fälle / 32 Checks):

1. **`clearSolo()` stellte fest 0,85 wieder her.** Mit Highlights an ist das falsch: es gibt jetzt zwei
   Ruhezustände. Dieselbe Konstante hatte hier schon einmal einen echten Fehler verursacht.
2. **Die Highlight-Schwellen wurden nach dem Bauen der Layer berechnet** — und ein Trail-Label wird EINMAL
   beim Bauen gebunden. Ergebnis: das Dimmen funktionierte, die Sterne nicht, still.
3. **Der Stern stand doppelt im Info-Panel** (`★4,77 ★`).

Und eine vierte Falle, die die Suite selbst aufdeckte: der Highlights-Schalter ist **persistiert**, also
erbte die nächste Suite eine Karte mit 197 gedimmten Linien. Er wird jetzt in `TM.baseline()`
zurückgesetzt, wie die anderen Kartenschalter.

## Was als Nächstes offen ist

Im Backlog unter diesem Themenkomplex: die zwei Presets ("Muss man fahren" / "Versteckte Perlen"),
"In der Nähe", die Abfahrten je Bergstation, das Ranken der Tourenbuilder-Kandidaten, Touren, die die
Bewertung ihrer Komponenten erben — und die 22 Vorlage-Fälle plus 39 Trailforks-Linien ohne Gegenstück aus
dem Zuordnungslauf.

## Nachjustiert am 2026-08-24, alles auf Anweisung des Nutzers

Fünf Änderungen an Stufe 1, jede eine Korrektur an einer Annahme aus diesem Dokument:

1. **Der Schalter wurde ein Regler.** Statt an/aus jetzt ein Schieber über die *echte* Spanne der
   Bewertungen der angezeigten Regionen (Finale: 2,99–4,77), voreingestellt auf das obere Fünftel, mit
   Live-Trefferzahl daneben („4,49 ★ · 18 Trails"). Die 0–5-Skala, die dieses Dokument vorschlug, wäre zu
   drei Fünfteln Leerlauf gewesen. Ein Regionswechsel setzt ihn zurück und schaltet ihn aus — die Spanne,
   gegen die er gewählt wurde, existiert dann nicht mehr.
   **Nachgezogen am 2026-08-24:** er ist sichtbar, sobald etwas Angezeigtes bewertet ist, nicht erst wenn
   der Schalter an ist. Die erste Rückmeldung des Nutzers zum fertigen Feature war „ich sehe den Regler
   nicht" — ein Bedienelement hinter einem anderen zu verstecken ist keine Aufgabenteilung, sondern
   Unsichtbarkeit. Ziehen schaltet Highlights selbst ein (sonst tut der erste Zug nichts Sichtbares), der
   Schalter ist das Aus. **Noch am selben Tag ersetzt:** Schalter, Regler und Trefferzahl stehen jetzt in
   einer Zeile, und der Regler ist deaktiviert, solange der Schalter aus ist — womit das Ziehen-schaltet-ein
   wieder weg ist. Es war ein zweiter Weg in denselben Zustand; sichtbar-aber-grau löst dasselbe Problem
   (der Regler ist findbar und nennt seinen Wert) mit einem Weg. Und was ein Highlight *ist*, sagt der Regler jetzt selbst, im Tooltip: Bewertung ab
   dem eingestellten Wert, voreingestellt auf das beste Fünftel der bewerteten Trails
   der angezeigten Regionen — genau die Frage, die der Nutzer im selben Atemzug gestellt hat.
   **Der Preis, offen benannt:** ein einzelner absoluter Schwellenwert über mehrere Regionen IST der
   regionsübergreifende Vergleich, vor dem Abschnitt 3.2 warnt. Vertretbar hier, weil die Zahl sichtbar ist
   und der Fahrer sie selbst setzt — und weil die Voreinstellung weiter aus den Daten kommt.
2. **Beide Zahlen stehen immer in der Kachel** (`⭐ 4,71 🔥 100`), nicht nur die der aktiven Sortierachse.
   Meine Begründung fürs Weglassen war eine hochgerechnete Schätzung; gemessen hat die engste Kachel am
   Handy **39px Luft**, und alle 219 bleiben 52px hoch.
3. **Keine Stimmenzahl in der Oberfläche.** Abschnitt 3.1 fordert sie „nicht verhandelbar" — das war zu
   stark: `rate` ist der **Bayes-Wert**, also schon stimmengewichtet, ein Trail mit 3 Stimmen kann keine 4,9
   zeigen. Die Schrumpfung leistet, was die sichtbare Zahl leisten sollte. `votes` bleibt in den Daten.
4. **Keine Quellenangabe in der Oberfläche**, nirgends. Die Herkunft bleibt in den Daten (`tf`-Slug je
   Trail, `ratings.source`), damit eine Bewertung nachprüfbar bleibt. Ein Testfall prüft die Abwesenheit in
   Seitenleiste, Info-Panel und Regionsdialog, inklusive `title`-Attributen — dort war sie hineingerutscht.
5. **Kein Dichte-Gate mehr.** Abschnitt 3.3 verlangte, die UI unter 35 % Abdeckung auszublenden. Der Nutzer
   hat das verworfen („Ist doch trotzdem gut zu sehen"), und die erste Fassung war ohnehin fehlerhaft: sie
   poolte die aktiven Regionen, also machte das Zuschalten von Madeira (158 Trails, keine Bewertungen) aus
   Finales 60 % ein 34,7 % — und ließ das Feature **für Finale** verschwinden. Übrig bleibt eine
   Datenbedingung statt einer Regel: der Regler braucht ≥10 bewertete Trails für eine Spanne.

**Neu gemerkt:** jeder bewertete Trail trägt seinen Quell-Slug (`tf`). Die Zuordnung von Finales 219 Trails
kostete einen vollen geometrischen Lauf und 22 Fälle, die noch ein Mensch ansehen muss — mit dem Slug ist
ein Aktualisieren der *Werte* künftig eine Ernte plus ein Wörterbuch-Zugriff.

Und ein Fehler, der beim Bauen auffiel und nichts mit dem Rating zu tun hatte: **dem Kartenlabel fehlte das
⬆️ für Uphill-Trails.** Karte und Info-Panel trugen es immer, das Label nicht — dieselbe Lücke, die 2026-07-28
schon der Schwierigkeitspunkt geschlossen hat.

Suite: `tests/browser/rating.js`, **14 Fälle / 65 Checks**, sechs geprüfte Mutationen (Stand 2026-08-24, nach der Krone).

6. **Die Mindest-Stimmenzahl ist weg** (2026-08-24, Anweisung des Nutzers). Abschnitt 3.1 hatte sie als Netz
   gegen „zwei begeisterte Stimmen, 4,9 Sterne" gefordert — einen Fall, den `rate` gar nicht erzeugen kann,
   weil es der bayessche Wert ist: Finales bestbewerteter Trail mit unter fünf Stimmen kommt auf **4,11**,
   die Vorgabe lag bei 4,49. Die Regel hat also in 131 bewerteten Trails nichts abgefangen, aber 21 davon
   aus der Spanne des Reglers herausgehalten. Ohne sie zählen 131 statt 110 Trails, die Vorgabe wandert von
   4,47 auf 4,45 und hält 26 statt 22 Trails; die Spanne selbst (2,99–4,77) bleibt gleich. `votes` bleibt in
   den Daten für ein späteres Update, wird von der App aber nirgends mehr gelesen.
   **Und zur Vorgabe selbst, weil die Frage kam:** es ist das beste **Fünftel**, nicht 10 % — die
   Bewertungen absteigend sortiert, Schwellenwert ist die des letzten Trails im obersten Fünftel. Ein festes
   Sternmaß wäre in jeder Region etwas anderes; ein Anteil ist überall gleich streng.

## Die Krone (2026-08-24)

Das Wort „Highlight" stand am Ende an genau einer Stelle in der Oberfläche — als goldenes Etikett im
Info-Panel — und hat dort auf dem Handy zu viel Platz gekostet. Der Nutzer hat daraus nicht „weg damit"
gemacht, sondern die bessere Frage gestellt: *„Wenn wir für Highlights eine Metapher einführen würden,
könnten wir es vielleicht anders handhaben."* Eine Metapher an allen Stellen kostet weniger Platz als ein
Wort an einer.

**Warum die Krone und nicht Flamme, Diamant oder Lorbeer:** Flamme und Stern sind hier schon vergeben
(Beliebtheit und Bewertung), und ein zweites Feuer hätte genau die Verwechslung erzeugt, die das Trennen
der beiden Achsen vermeiden soll. Der Lorbeer liest sich wie eine Auszeichnung durch jemanden, der Diamant
wie Seltenheit — die Krone sagt „das Beste hier", was die Schwelle tatsächlich behauptet.

**Sie sitzt auf dem Schwierigkeitsbalken**, nicht vor dem Namen (Entscheidung des Nutzers, nachdem beides
vorlag). Der Balken ist seit der Info-Box 2.0 ohnehin das senkrechte Element links, und die Kachel hat
denselben Balken über die volle Kachelhöhe bekommen, damit Liste und Panel dieselbe Form zeigen — der
farbige Punkt im Namen ist dafür entfallen, zwei Anzeigen derselben Sache waren eine zu viel.

| Ort | Form |
|---|---|
| Kachel | Krone **vor dem Namen**, im Textfluss; der Schwierigkeitsbalken bleibt ein reiner Balken über die ganze Kachelhöhe |
| Info-Panel | dieselbe Krone vor dem Namen in der Überschrift |
| Kartenlabel | Krone statt des ★ vor dem Namen |
| Abschnittsblock einer Trailrunde | Krone im Textfluss vor dem Namen, wenn der angeklickte Abschnitt ein gekrönter Komponenten-Trail ist |
| weißer Startpunkt | **goldener Ring** (`#e0a326`, 2,5px statt 1,5px) statt einer Krone — ein Emoji auf einem 5px-Punkt wäre nicht lesbar |
| Start und Ziel eines markierten Trails | **nichts** — dort sagt die gelbe Auswahlkontur schon, welcher Trail gemeint ist |
| Highlights-Regler | der Griff **ist** eine Krone (Inline-SVG), denn er ist die Grenze, ab der etwas eines ist |
| RIDE-Modus | nichts davon — dort zählt die Linie, nicht die Auszeichnung |

**Vier Korrekturen am Tag danach, alle aus der Benutzung** (2026-08-25, Nutzer): der Strich hat die Krone
zweimal nicht getragen — *auf* ihm verdeckte sie ihn („Der Strich müsste dann erst unter der Krone losgehen"),
und mit genug Luft darüber blieben von 52px Kachelhöhe nur 30 für den Strich, im Panel von 21px sogar nur 7.
Fünf Varianten lagen als Entwurf vor, bevor App-Code entstand; gewählt wurde die Form, die Kartenlabel und
Abschnittsblock schon hatten: **vor dem Namen, im Textfluss**, mittig zur Schrift ausgerichtet, weil die
Emoji-Schrift die Krone tief in ihr eigenes Kästchen setzt und sie auf der Grundlinie unter der Schrift hing. Der
goldene Ring gehört **allein dem weißen Punkt**: ist der Trail markiert, stehen Start und Ziel wieder in ihren
eigenen Farben, denn der Ring würde dasselbe ein zweites Mal sagen. Und der Abschnittsblock einer Trailrunde
war die sechste Stelle, die den gekrönten Trail nannte, ohne ihn zu krönen.

**Ein echter Fehler kam dabei heraus, und er ist der Grund, warum die Ringe zu einer Prüfung geführt haben:**
die Schwelle rastet auf das 0,05-Raster des Reglers ein (`input.value` gelesen, nachdem es gesetzt wurde),
Kartenlabel und Ringe waren zu diesem Zeitpunkt aber schon mit dem *ungerasteten* Wert gebaut. In Bike
Kingdom trug „Fürhörnli" mit 4,32 goldene Ringe, während seine Kachel bei gerasteter Schwelle 4,33 korrekt
keine Krone hatte. `lastAppliedHighlightMin` vergleicht jetzt den tatsächlich angewandten Wert und zieht
Labels und Ringe nach. Die Zusicherung dazu („Karte und Liste krönen dieselben Trails") steht in der Suite,
ist dort aber **nicht** mutationsgeprüft — in Finale liegt die gerechnete Vorgabe zufällig auf dem Raster,
der Fehler kann in dieser Vorlage also gar nicht auftreten; siehe `tests/MUTATIONS.md`.

## Wie die Bewertungen in die übrigen Regionen kamen (2026-08-24)

Finale war der Sonderfall, nicht die Regel: dort mussten unsere Linien und die von Trailforks über vier
unscharfe Signale und eine Margin-Regel zusammengebracht werden, weil es zwei unabhängige Aufzeichnungen
derselben Trails sind (`tools/match_trailforks.py`, 22 Fälle zur Nachprüfung durch einen Menschen). Für den
Rest der Regionen gibt es zwei billigere und stärkere Wege, und welcher gilt, hängt daran, woher die
Geometrie der Region kommt.

**Weg 1 — die Region wurde AUS Trailforks gebaut** (Gardasee, Madeira, Schwarzwald zur Hälfte, beide
Vogesen, Pfälzerwald zu zwei Dritteln). Dann ist unsere `trailGeo` deren dekodierte Polyline, und die
Zuordnung ist ein Nachschlagen statt einer Schätzung — `tools/map_tf_slugs.py` mit drei Regeln in dieser
Reihenfolge, jede gegen die Endpunkte geprüft:

1. **die id**, weil unser Build sie aus dem Slug gebaut hat (`md_babylon_84563` ← `babylon-84563`);
2. **der Name**, weil ein Trailforks-Slug der geslugte Name ist, optional mit angehängter Nummer — das ist
   der Weg für den Harz und den Pfälzerwald, deren ids den Slug nicht tragen;
3. **die nächstliegende Linie**, akzeptiert nur innerhalb von 60 m und nur wenn sie deutlich besser ist als
   die zweitbeste. Zwei Trails am selben Trailhead sind in einem Hub die Regel, nicht die Ausnahme.

Was übrig bleibt, wird gemeldet, nicht geraten. **Bit-identisch ist es nämlich nicht** — und diese Annahme
hat die erste Fassung 78 von Madeiras 158 Trails gekostet: die Pipeline entfernt Punkte unter 0,5 m Abstand
und fährt Douglas-Peucker darüber, was die Endpunkte behält, aber neu rundet (32.68785 gegen 32.68784), und
kürzt gelegentlich einen Ausläufer (Avalanche Raposeira endet 25 m früher). Mit Toleranzen statt Gleichheit:
Madeira 158/158, Gardasee 911/911, Vogesen 954/957, Schwarzwald 538/618, Pfälzerwald 481/763 — die
Fehlbeträge sind genau die Trails, die diese beiden Regionen aus anderen Quellen haben.
Geprüft, nicht gehofft: über 1 606 Zuordnungen **kein einziger abweichender Name**, und die sieben
Zuordnungen mit über 60 m Endpunktabstand tragen alle denselben Namen auf beiden Seiten.

**Weg 2 — die Region kam von einem Betreiber, aus OSM oder von Trailguide.** Dann muss zuerst überhaupt
gefunden werden, welche Trailforks-Region ihre Trails hält, und dafür gibt es keine Suche: `/search/?q=`
liefert serverseitig nichts, `/ajax/autocomplete/` antwortet „Bad OP", die Region-API will einen Schlüssel.
Was funktioniert, ist Probieren — ein Slug ist fast immer ein Ortsname:

* `tools/find_tf_regions.py` bildet Kandidaten aus den Namen, die wir schon haben (Katalog-Label,
  Unterregionen, `places`), jeweils in beiden Umlaut-Schreibweisen, weil Trailforks `soelden` oder `solden`
  schreibt und welches, nicht vorhersagbar ist;
* `tools/probe_tf_slugs.py` nimmt eine handgeschriebene Liste für die Gebiete, die unsere Daten nie
  benennen. Beides ist nötig und keines enthält das andere: Laax liegt unter `graubunden` (nur in der
  Handliste), die Odenwald-Gebiete `amorbach` und `momlingen` fand nur der automatische Lauf.
  **Und eine Region muss nicht unter ihrem eigenen Namen liegen** — Paznaun hat bei Trailforks keine eigene
  Region, seine Trails hängen unter `ischgl`; Bike Kingdom liegt unter `chur`, nicht unter `lenzerheide`.

Danach ist es dieselbe Kette wie oben, nur mit einer frischen Ernte davor: Tabelle (Seiten von 100 Zeilen),
dann eine Seite je Trail — und da die Bewertung auf derselben Seite steht wie die Polyline, kostet sie
keinen zusätzlichen Abruf. `tools/phase_b_run.py` fährt das Region für Region durch.

**Zwei Dinge, die wichtiger sind, als sie aussehen.** `tools/harvest_tf_ratings.py` verankert die Bewertung
an der **eigenen** Trail-id der Seite (aus der Tabelle, aus den Ziffern am Slug-Ende, oder der am
häufigsten als `trailid=` vorkommenden Nummer — die eigene steht in jedem Link der Seite, ein Nachbar
einmal, also ist der Modus richtig, wo „erster Treffer" ein Münzwurf ist). Und ein **fehlgeschlagener Abruf
wird nie als „keine Bewertung" verbucht**: ohne das würde eine einzige Drosselung eine ganze Region als
unbewertet markieren, und der spätere Lauf, der genau diese Zeilen überspringt, käme nie zurück.

Die Abdeckung je Region steht in **`docs/trail-rating-abdeckung.md`**, erzeugt von
`tools/rating_report.py` aus den Regionsdateien selbst.

### Die Nummer-Regel (2026-08-24, beim Durchgehen der offenen Fälle gefunden)

Beim ersten offenen Fall — Velill Trail im Paznaun — fiel auf, dass **Trailforks die Trailnummern des
Betreibers im eigenen Namen führt**: „Velilltrail #7134" gegen unser „Velill Trail (7134)". Das ist kein
Ähnlichkeitsmaß, sondern eine Identitätsaussage beider Quellen, und sie ist das einzige Signal, das den
Fall löst, an dem die anderen vier scheitern: Trailforks zerlegt einen Trail in Abschnitte, deren 2,0 km
„Schmuggler Trail #7187" liegen also mitten in unseren 8,5 km desselben Namens — Längenverhältnis 0,23,
während ein benachbarter Abschnitt auf reine Deckung **höher** kommt. Die Nummer trennt die beiden.

Drei Dinge waren dafür nötig, jedes davon durch einen konkreten Fall erzwungen:

1. **Die Nummer sortiert vor der Geometrie.** Sonst sieht die Regel den richtigen Kandidaten nie an: beim
   Schmuggler Trail kommt der Nachbarabschnitt auf 0,99 und der nummerierte auf 0,94.
2. **Bei einem Doppelanspruch gewinnt die Nummer, nicht die Deckung.** „Velill Trail Expert (7146)" hatte
   `velilltrail` unserem 7134 weggenommen — der Linie, deren Nummer es trägt.
3. **Der Name entscheidet, wenn die Geometrie gleichstellt** (`NAME_TIE_LEAD`), und die Sortierung braucht
   den Namen als dritten Schlüssel. Mehrere Abschnitte in einer langen Linie erreichen alle 1,00, die
   Margin-Regel kann sie nie trennen — und welcher „erster" war, entschied vorher die Reihenfolge im
   Wörterbuch: `che-d-mot` in einem Lauf, `planer-salaas` im nächsten. Ein Urteil, das sich ändert, ohne
   dass sich die Daten ändern.

Die Nummer wirkt nur **zusätzlich zu** echter geometrischer Deckung, nie allein — deshalb genügen zwei
Ziffern, ohne dass „Trail 2" gegen „#2" zum Problem wird. Belegt durch die Negativkontrolle gegen den
Gardasee, in der jeder Treffer per Konstruktion falsch wäre: **0 Treffer, 0 zur Prüfung**, unverändert.

Wirkung: Finale 142 → 145 Treffer, Paznaun 6 → 9, Bike Kingdom 61 → 63, Sölden 32 → 33, Bikecircus 40 → 42,
Brandnertal 9 → 10. Insgesamt 1 717 → 1 731 bewertete Trails.

**Handentscheidungen stehen in `Material/<Region>/tf_manual.json`** — `{unsere_id: {slug, why}}`, und sie
überstimmen beide Regeln. Ohne diese Datei würde jeder erneute Lauf einen gemeinsam entschiedenen Fall
zurück in den Prüfstapel werfen.

### Die Regeln, die beim Durchgehen der Fälle entstanden sind (Paznaun und Bike Kingdom, 2026-08-24)

Die 39 Fälle dieser beiden Regionen einzeln zu entscheiden hat drei Regeln erzeugt, die der Nutzer
vorgegeben hat und die für jede weitere Region gelten:

1. **Zwei Trailforks-Abschnitte eines unserer Trails werden stimmen-gewichtet zusammengefasst.** Einen
   auszuwählen wirft die Stimmen des anderen weg und wählt einen Sieger nach nichts Bestimmtem
   (Rock'n'Roll: 4,08 aus 6 gegen 4,12 aus 3). Der Wert ist das gewichtete Mittel, die Stimmen werden
   addiert — **die Beliebtheit aber nicht**: sie zählt Check-ins eines Jahres, und wer den Trail fährt,
   loggt jeden seiner Abschnitte, also zählt eine Summe denselben Fahrer doppelt. Der belebteste Abschnitt
   ist die ehrliche Zahl. Steht in `merge_sections()`.
2. **Ein anders benannter Trail wird angehängt, wenn er DIE Linie ist — nicht wenn er eines von mehreren
   Teilstücken ist.** „Butterfly" gegen unser „Tschiertschen – Praden" hat 96 % gleiche Länge und 47 m
   Endpunktabstand, „Tiejer Wald" deckt unseren Medergen Trail zu 0,94 bei 0,02 für den Zweitbesten — beide
   angenommen. Dagegen abgelehnt: vier Fälle, in denen unsere Linie zwei oder drei fremd benannte Trails
   überfährt (Brambrüesch–Churwalden, Back to town, Isla, Bual). Ein Mittel darüber beschreibt das Gebiet,
   nicht den Weg. Denselben Grund hat Ninos Gold-Trail, über den vier fremde Trails laufen.
3. **Eine Zufahrt hat keine Bewertung.** Unsere fünf „Access …"/„Aufstieg …"-Einträge bekommen nichts:
   Trailforks führt dort entweder eigene „Secondary Access Road"-Zeilen ohne Wert oder benachbarte echte
   Trails mit anderem Namen (Fanüllatobel #616, 4,37 — ein Trail, keine Zufahrt, Deckung 0,09).

Und ein Befund, der die Zahlen relativiert: `tiejer-wald` und `medregen-langwies` tragen beide exakt 4,23
bei je 3 Stimmen. Bei so wenigen Stimmen liegt der bayessche Wert fast auf dem Regionsmittel und sagt kaum
etwas über den einzelnen Trail. Der Nutzer hat entschieden, das vorerst so zu lassen (die Mindest-Stimmenzahl
war bewusst entfernt worden), aber es ist der Grund, warum solche Werte nicht überinterpretiert werden
sollten.

Stand nach dem Durchgang: **Paznaun 0 offene Fälle** (4 → 7 bewertet), **Bike Kingdom 0 offene Fälle**
(56 → 71 bewertet, 77 IDs). Beide Regionen tragen ihre Entscheidungen samt Begründung in
`Material/<Region>/tf_manual.json`.
