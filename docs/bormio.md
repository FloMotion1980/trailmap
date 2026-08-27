# Bormio & Valtellina — gebaut 2026-08-26

179 Trails, 538 km, 6 Sub-Regionen, 74 mit Trailforks-Bewertung, **3 Lifte** (Betreibertabelle).
Verfahren, Quelle und die Vorbehalte dazu: **`docs/sechs-regionen-2026-08.md`** — hier steht nur, was für
diese Region eigen ist.

## Warum sie gebaut wurde

Wunsch des Nutzers, 2026-08-25, aus eigener Erfahrung: *„Da war ich schon mal im Bikepark und ganz oben ging
auch eine epische Tour los... Bormio 3000 nach Sankt Katharina oder so"*. Genau diese Abfahrt war der Anlass,
und sie ist in den Daten wiedergefunden — siehe unten.

## Zuschnitt

Bewusst **über das Bormio-Becken hinaus bis Tirano und Aprica** — ein Tal, eine Region — aber **vor Sondrio
zu Ende**, das 60 km talabwärts liegt und zur Bassa Valtellina gehört. **Livigno ist nicht dabei**: das ist
seit 2026-08-11 seine eigene Region, und den Foscagno-Pass dazwischen fährt niemand als Verbindung zweier
Hausrunden.

| Sub-Region | Trails |
|---|---:|
| Valdidentro | 43 |
| Aprica/Teglio | 42 |
| Valfurva | 35 |
| Grosio/Tirano | 22 |
| Valdisotto/Oga | 21 |
| Bormio | 16 |

Ein Befund, der die Gebietsspalte wieder als Verwaltungskasten entlarvt: Trailforks' **„Stelvio Natural
Trail Park"** (19 Trails) liegt mit Schwerpunkt 46,406 / 10,496 im **Valfurva** bei Santa Caterina — nicht
am Stilfserjoch, wie der Name nahelegt.

## Die Tour des Nutzers, wiedergefunden

Sie steht als **zwei aufeinanderfolgende Trails** in den Daten, deren Enden **3 m** auseinanderliegen:

| | Länge | Höhe |
|---|---:|---|
| Bormio 3000 single | 8,0 km | 3 000 → 2 320 m |
| Le Cune | 3,3 km | 2 313 → 1 837 m |
| **zusammen** | **11,3 km** | **3 000 → 1 837 m, −1 163 Hm** |

Das Ende liegt rund 100 Höhenmeter über Santa Caterina Valfurva (1 740 m) und 3,5 km westlich davon — der
Rest ist Talweg. `Le Cune` ist mit 4,55 aus 14 Stimmen der zweitbestbewertete Trail der ganzen Region.

**Als Trailrunde ist sie NICHT gebaut.** Dafür bräuchte es eine Aufzeichnung, die durch
`tools/gpx_map_match.py` läuft — die beiden Linien aneinanderzuhängen wäre eine Behauptung über eine
Verbindung, die ich nicht gemessen habe. Wenn der Nutzer ein GPX der Fahrt hat, ist das eine kurze Sache.

## Ausgeschieden

6 Zeilen im **Val di Scalve** (Passo Vivione, Passo Venerocolo, Lago Belviso, Rif. Tagliaferri, Passo
Demigone) — Provinz Bergamo, jenseits des Passes, 10–29 km vom nächsten Anker. Dazu eine Namensdublette
(`Valentina Trail`).

## Lifte: drei, und OSM hätte null gefunden

`bormioski.eu/estate/impianti-aperti-in-estate/` führt eine Tabelle „Situazione impianti" mit **genau drei**
Anlagen im Sommer (04.07.–06.09.2026; Bike Park ab 18.07., montags geschlossen):

| Lift | Typ | Tal → Berg |
|---|---|---|
| Bormio – Bormio 2000 | Kabinenbahn | 1 198 → 1 934 m |
| Bormio 2000 – Cima Bianca | Pendelbahn | 1 938 → 2 996 m |
| Bormio 2000 – Cimino | Vierersessel | 1 943 → 2 608 m |

**Alle drei OSM-Wege tragen überhaupt kein Bike-Tag.** Wer sich auf `aerialway:bicycle` verlassen hätte,
hätte hier null Lifte gefunden — das ist die Regel aus `docs/lifts-feature.md` einmal in der anderen
Richtung, nachdem sie bei Kronplatz zwei falsch-positive geliefert hatte. Die übrigen 20 Anlagen im
Kasten (Valbella–Bormio 3000, Ciuk–Laghetti, Pian dei Larici, Schlepplifte, Förderbänder, Projekte) stehen
nicht auf der Sommerliste; sie sind mit Begründung in `add_lifts.py`s `excluded`.

## Der Bikepark: 5 von 7 Pisten sind drin, aber unter der Oberfläche

Der Betreiber führt **sieben Downhill-Pisten am Monte Vallecetta**. Fünf sind gebaut (Paul Newman, Viper,
Golf Club, Hell Rocks, plus Autobahn und Zombie als EINE Trailforks-Linie „Autobahn + Zombie"),
**Panther fehlt ganz**, und **Viper trägt bei uns rot, wo der Betreiber blau sagt**. Die vollständige
Gegenüberstellung samt der drei nötigen Schritte steht in `docs/backlog.md`, Abschnitt 3b.

## Offen

* **Lifte.** Bormio 2000/3000, die Talstation Bormio und die Bahnen in Santa Caterina fahren im Sommer —
  aber die Liste muss von der Sommerseite des Betreibers kommen, siehe `docs/lifts-feature.md`.
* **Die epische Tour als Trailrunde**, siehe oben.
* 105 der 179 Trails tragen keine Bewertung; das ist für die dünn befahrenen Seitentäler normal.
