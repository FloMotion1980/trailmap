# Bormio & Valtellina — gebaut 2026-08-26

179 Trails + **1 Tour**, 6 Sub-Regionen, 74 mit Trailforks-Bewertung, **3 Lifte** (Betreibertabelle).
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

## Die Tour des Nutzers — gebaut, und die erste Vermutung war falsch

Der Nutzer ist sie gefahren, hat sie aber nicht aufgezeichnet. Der **Betreiber** führt sie als „Itinerario
Freeride MTB Bormio 3000 - Santa Caterina Valfurva" mit Zahlen und Wegnummern (S541 → S518 → S523 → S549 →
S522), aber **ohne GPX** — nur PDF und Kartenbild. Die Spur kam am Ende von **bergfex** (Tour 2861858), auf
den Hinweis des Nutzers hin.

**Der GPX-Download braucht dort kein Konto, nur einen Referer.** `/downloads/gps/?id=<id>&fileType=gpx`
antwortet anonym mit `application/gpx+xml`, sobald die Tourseite als `Referer` mitgeht; ohne ihn kommt die
HTML-Seite zurück. Dieselbe Klasse von Hürde wie Trailforks' 403 gegen urllib — keine Anmeldung, nur eine
Erwartung an den Aufrufer. Die Datei liegt als `Material/Bormio/freeride-bormio3000-santa-caterina.gpx` im
Repo.

**Gegen die Betreiberzahlen geprüft, bevor gebaut wurde:**

| | Länge | Höhenmeter | von → bis |
|---|---|---|---|
| Betreiber | 12,3 km | +254 / −1 482 | 3 017 → 1 738 m |
| bergfex-Spur | 12,29 km | +294 / −1 561 | 2 997 → 1 730 m |

Länge auf 10 m genau, beide Endhöhen auf 20 m. Gebaut sind die Zahlen des **Betreibers**, nicht die der
Spur — aufsummiertes GPS-Rauschen gegen eine geglättete Verlagsangabe, und offizielle Zahlen gewinnen.

### Was die Abschnitte sagen

`tools/gpx_map_match.py` gegen Bormios eigene 179 Trails und 3 Lifte, **91 % der Linie auf benannten
Trails**:

| Abschnitt | Länge |
|---|---:|
| Bormio 3000 single | 8,04 km |
| *Verbinder* | 0,04 km |
| Panoramico Le Cune | 2,80 km |
| *Verbinder* | 0,13 km |
| Le Cune | 0,75 km |
| *Verbinder* (Auslauf ins Dorf) | 0,88 km |

**Das widerlegt, was hier am Vortag stand.** Die Vermutung war `Bormio 3000 single` + `Le Cune`, weil deren
Enden 3 m auseinanderliegen und die Summe ungefähr passte. Tatsächlich führt die Tour über
**`Panoramico Le Cune`**, die panoramische Variante, und berührt vom `Le Cune` nur die letzten 750 m. Zwei
Linien, die am selben Punkt beginnen, sind mit blossem Endpunktvergleich nicht zu unterscheiden — genau
dafür gibt es den Matcher und nicht das Augenmass.

Die 0,88 km am Schluss bleiben ein ehrlicher **Verbinder**: der Auslauf nach Santa Caterina, den unsere
Daten nicht als Trail führen. Ihn auf die nächstliegende Linie zu ziehen wäre die stille Zurechtbiegung,
die dieses Projekt nicht macht.

Gebaut von `tools/build_bormio_tour.py`; ein Neubau braucht kein Netz.

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
