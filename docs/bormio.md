# Bormio & Valtellina — gebaut 2026-08-26

179 Trails + **1 Tour**, 7 Sub-Regionen, 74 mit Trailforks-Bewertung, **3 Lifte** (Betreibertabelle).
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

## Der Bikepark ist eine eigene Sub-Region

Auf Wunsch des Nutzers (2026-08-26). Der entscheidende Punkt: **der Bikepark ist durch die Liste des
Betreibers definiert, nicht durch Geografie.** Seine Pisten laufen von der Cima Bianca (3 017 m) nach
Bormio 2000 (1 945 m) und fallen nach reiner Nachbarschaft in *zwei verschiedene Täler* — die Ankerregel
hatte vier nach Valdisotto und eine nach Valfurva sortiert, jede für sich korrekt und in der Summe nutzlos.
Dafür gibt es jetzt `sub_override` in `tools/build_trailforks_region.py`: eine Zuordnung von Hand, die
**nach** der Entfernungsprüfung greift, damit sie nicht zugleich heimlich die Regionsgrenze aufweicht.

| Piste | Betreiber | gebaut |
|---|---|---|
| Paul Newman | rossa/blu, 1 800 m / 356 Hm | rot, 1,81 km |
| Viper | **blu**, 2 100 m / 400 Hm | **blau** — Trailforks sagte rot |
| Autobahn + Zombie | zwei Pisten, 800 + 1 400 m | rot, 2,59 km — **eine Linie**, siehe unten |
| Golf Club | blu, 1 700 m / 349 Hm | blau, 1,47 km |
| Hell Rocks | nera, 400 m / 100 Hm | schwarz, 0,30 km |
| Panther | blu, 300 m / 40 Hm | **fehlt** |

Die Grade stehen als `diff_override` mit der italienischen Formulierung daneben (blu → blau, rossa → rot,
nera → schwarz; bei „rossa/blu" gilt die härtere Stufe). **Nicht** im Bikepark: `Bormio 2000 DH` — das ist
die Talabfahrt Bormio 2000 → Bormio (1 892 → 1 204 m) und steht auf keiner der sieben Pistenseiten.

### Autobahn und Zombie lassen sich nicht trennen — vier Quellen geprüft

Trailforks führt beide als eine Linie „Autobahn + Zombie". Sie zu teilen wäre naheliegend, ist aber mit
nichts zu begründen, was ich habe:

* **Beide Betreiberseiten** (bormioski.eu und bormiostay.com) nennen dieselben Zahlen — und **Autobahns sind
  in sich widersprüchlich**: 548 Hm auf 800 m sind 68 % im Mittel, während dieselbe Seite „max 19°" (34 %)
  angibt. Zombies 253 Hm auf 1 400 m (18 %, max 23°) sind dagegen stimmig.
* **Die Summen passen nicht**: 2 200 m gegen unsere 2 593 m, und 801 Hm gegen unsere 496.
* **Unser eigenes Profil hat keine Bruchstelle**: 14 bis 25 % Gefälle durchgehend über alle 13 Abschnitte.
* **OSM kennt keine der sieben Pisten** namentlich (Overpass über den ganzen Bikepark-Kasten).
* **Die Bikepark-Karte des Betreibers** (`Sentieri_ITA.pdf`) ist ein Rasterbild; die sieben Namen stehen
  nur in der Legende, es gibt keine Geometrie darin.

An irgendeinem Meter zu schneiden wäre eine erfundene Grenze. Der Name „Autobahn + Zombie" ist Trailforks'
eigener und sagt ehrlich, was die Linie ist. Was es lösen würde: eine Aufzeichnung einer der beiden Pisten.

## Der Bikepark: alte Gegenüberstellung

Der Betreiber führt **sieben Downhill-Pisten am Monte Vallecetta**. Fünf sind gebaut (Paul Newman, Viper,
Golf Club, Hell Rocks, plus Autobahn und Zombie als EINE Trailforks-Linie „Autobahn + Zombie"),
**Panther fehlt ganz**, und **Viper trägt bei uns rot, wo der Betreiber blau sagt**. Die vollständige
Gegenüberstellung samt der drei nötigen Schritte steht in `docs/backlog.md`, Abschnitt 3b.

## Offen

* **Lifte.** Bormio 2000/3000, die Talstation Bormio und die Bahnen in Santa Caterina fahren im Sommer —
  aber die Liste muss von der Sommerseite des Betreibers kommen, siehe `docs/lifts-feature.md`.
* **Die epische Tour als Trailrunde**, siehe oben.
* 105 der 179 Trails tragen keine Bewertung; das ist für die dünn befahrenen Seitentäler normal.
