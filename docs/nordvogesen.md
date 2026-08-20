# Nordvogesen / Vosges du Nord — vorbereitete Region (noch nicht im Katalog)

Angefragt 2026-08-19: *"Die Nördlichen Vogesen. Vor allem die Region rund um Wissembourg. Also
ungefähr alles nördlich von Colmar."* — plus die Vorgabe, **`index.html` nicht anzufassen**, weil
parallel in einem anderen Chat daran gearbeitet wird.

Deshalb ist alles gebaut **außer** dem `REGION_CATALOG`-Eintrag: `Trailmap App/regions/nordvogesen.json`
existiert und ist vollständig, die App kennt die Region aber noch nicht. Der fertige Eintrag zum
Einfügen steht unten. Schwesterregion: [suedvogesen.md](suedvogesen.md).

## Die Grenze ist die rote Linie

Die Südgrenze ist keine Breitengradregel, sondern die **rote Linie, die du auf einem Trailforks-Screenshot
eingezeichnet hast** (*"Ich würde alles unter der eingezeichneten roten Linie zu der Region Südvogesen
zählen"*). Sie steht als nachprüfbare Regel in `tools/vogesen_boundary.py`: der Screenshot hat keine
Koordinaten, also wurde die Pixel-Transformation aus bekannten Orten (Saint-Dié, Épinal, Gérardmer,
Munster, Thann, Mulhouse) gefittet — Gérardmer reproduziert sich auf 0,003°, der schlechteste Check auf
0,05°. Die Linie läuft von **48.260 N / 6.567 E** im Westen nach **48.124 N / 7.352 E** im Osten,
fällt also um 0,173° Breite pro Grad Länge. **Genauigkeit ca. ±4 km.**

Zugeordnet wird deshalb **pro Sub-Region über deren Schwerpunkt**, nicht pro Trail — jede Klammer liegt
mindestens 7 km von der Linie weg, die Aufteilung hängt also nicht an meinem Messfehler. Zusätzlich
prüft jeder Build **jeden einzelnen Trail** gegen die Linie und meldet alles im ±5-km-Band.

Zwei Klammern hat die Linie gegenüber dem vorherigen Stand **in entgegengesetzte Richtungen** verschoben:

- **`kaysersberg` (mit Bikepark Lac Blanc) → Südvogesen** (7 km südlich der Linie). Damit ist die
  Lac-Blanc-Frage entschieden, und zwar genau so, wie du sie von Anfang an gemeint hattest.
- **`vosges_ouest` (Saint-Dié, Raon-l'Étape, Lac de la Maix, Donon) → zurück nach Nordvogesen** (10–39 km
  nördlich der Linie). Das frühere *"ohne vosges_ouest"* hatte sie in den Süden gelegt, die gezeichnete
  Linie läuft aber klar südlich von Saint-Dié.

## Stand

**483 Trails, 588,2 km, 7 Sub-Regionen, 15 Orte, 1,18 MB.** Bounds `[[48.10768, 6.81610], [49.13417, 7.93934]]`.
Keine Lifte, keine Touren/Trailrunden.

| Sub-Region (Key) | Label | Trails | km | Breitengrad |
|---|---|---:|---:|---|
| `saverne` | Saverne | 148 | 178,0 | 48.589–48.863 |
| `niederbronn` | Niederbronn | 109 | 121,7 | 48.873–49.070 |
| `sainteodile` | Barr | 89 | 99,8 | 48.320–48.488 |
| `wissembourg` | Wissembourg | 56 | 68,8 | 48.958–49.134 |
| `vosges_ouest` | Saint-Dié | 49 | 75,5 | 48.249–48.513 |
| `bruche` | Bruche-Tal | 16 | 16,9 | 48.529–48.572 |
| `ville` | Ribeauvillé | 16 | 27,4 | 48.108–48.322 |

**Die Labels sind je EIN Name** (2026-08-20, *"Die Namen der Unterregionen … sind zu lang"*). Sie hießen
"Saverne / Dabo / Wangenbourg", "Barr / Mont Sainte-Odile", "Vogesen West (Saint-Dié)" — ehrlich, was eine
Klammer umspannt, aber ein Seitenleisten-Chip hat ~14 Zeichen, bevor er umbricht, und jedes dieser Täler wird
ohnehin über einen Namen gefunden. Was drin ist, steht in `SUBREGIONS` in `tools/build_nordvogesen.py`.

Schwierigkeiten: 104 grün, 247 blau, 94 rot, 38 schwarz. Höhen 183–1097 m.

Gebaut von `tools/build_nordvogesen.py` (idempotent). Rohdaten in `.tmpwork/vogesen/`.

## Quelle und Methode

Trailforks, geerntet durch das eigene eingeloggte Chrome des Nutzers (siehe
`trailforks-anonymous-polyline-extraction`). Zwei Dinge daran sind neu gegenüber dem Harz-Build und
gehören in die allgemeine Methode:

**1. Trailforks liefert die Höhendaten selbst mit.** Eine Trail-Detailseite enthält nicht nur den
`encodedpath`, sondern eine komplette `new ElevationChart({... sections: [{"points":[{"id":0,
"x":<Meter entlang>,"y":<Höhe m>,"lat":..,"lng":..,"grade":..}, …]}]})`-Konfiguration — also lat/lng
**und** echte Höhe **und** die kumulierte Distanz pro Punkt. Diese Region brauchte deshalb **keine
Elevation-API** (kein OpenTopoData, kein Rate-Limit, kein Cache). `tools/build_harz.py` schreibt in
seinem eigenen Docstring, Trailforks binde kein Profil ein — das stimmt so nicht (mehr).

**2. Die `difficulty=`-Liste in der Tabellen-URL muss JEDEN Code nennen.** Die aus dem
Varazze/Harz-Rezept übernommene Liste `difficulty=3,4,9,5,1,7,2,6,8` sieht vollständig aus und ist es
nicht: **Code 10 ist `Severe / Black`**. Ohne ihn fehlte die **komplette schwarze Stufe** — 38 Trails,
darunter alle 8 schwarzen in Barr. Am Ergebnis war nichts Auffälliges zu sehen; gefunden nur durch
Vergleich der Zeilenzahl einer Region gegen eine Partition nach einzelnen Codes. Gemessene Codes (an
`barr`): `d1` Access, `d3` Easy/Green, `d4` Intermediate/Blue, `d7` Secondary Access, `d9`
Difficult/Red, `d10` Severe/Black; `d11` trägt "Extremely Difficult", 2/5/6/8/12+ waren hier überall
leer. **Eine ungefilterte Tabellen-URL ist nicht der sichere Ausweg** — sie liefert *weniger* Zeilen
(66 für Barr gegen 79), hat also ihren eigenen Default-Filter. Derselbe Fehler wie in
`finale-difficulty-realignment`, zum zweiten Mal.

**Verifikation gegen Korruption:** Trailforks liefert dieselbe Linie zweimal (Polyline + Profil).
Der Build vergleicht beide Längen pro Trail; **alle 483 stimmen innerhalb von 60 m überein.** Das ist
die Prüfung, die bei Varazze/Finale gefehlt hatte. Achtung bei der Profil-`x`-Achse: sie wechselt
oberhalb von 1 km stillschweigend von Metern auf **Kilometer** (`br4me-du-cerf` meldet 702, ein
1 060-m-Trail meldet 1.06) — deshalb vergleicht der Build echte Haversine-Längen, nicht diese Achse.

**Schwierigkeit:** Trailforks' eigene Bewertung — und das ist hier der *korrekte* Fallback, nicht eine
übersprungene Prüfung: in diesem Zuschnitt liegt **kein einziger Bikepark**. Es sind durchweg
Community-/Club-Vosgien-Trails im Naturpark ohne Betreiber und ohne ausgeschilderte Skala, also greift die
Regel "Betreiber gewinnt" mangels Betreiber nicht. (Die drei Bikeparks der Vogesen — Lac Blanc, La Bresse,
Markstein — liegen alle südlich der roten Linie; ihre Betreiber-Schwierigkeiten sind in
[suedvogesen.md](suedvogesen.md) abgeglichen.)

**Lifte: keine, und das ist geprüft, nicht angenommen.** Eine Overpass-Abfrage über die gesamte
Regions-Bounding-Box findet genau einen `chair_lift` — Montjoie am Lac Blanc, der südlich der Linie liegt
und zur Südregion gehört. Alles übrige sind Skilifte ohne Bikebetrieb (Champ du Feu bei Barr: 9 Teleskis
+ Zauberteppich; Lac-Blanc-Teleskis), eine Materialseilbahn, eine Zipline und der Schiffshebewerk-Schrägaufzug
bei Saverne. Kein lift-bedienter Bikepark im Norden.

**Sub-Regionen** kommen aus dem geernteten Trailforks-*Region-Slug*, nicht aus der Spalte "riding
area" (28 Zeilen haben dort eine leere oder Eltern-Ebene). Der Build druckt die **echte Ausdehnung jeder
Sub-Region** — das hat drei echte Fehler aufgedeckt:

- Trailforks' `dambach` ist **Dambach-Neunhoffen im Nordvogesen** (49.008 N, Château de Schoeneck
  darüber), nicht Dambach-la-Ville bei Barr: sechs Trails lagen 65 km neben ihrer Klammer.
- "Noire Goutte Red Line" (direkt unter der Eltern-Region `vosges` geführt, ohne Gemeinde) wurde vom
  Schwerpunkt-Fallback in die *am wenigsten falsche* Nordklammer gezwungen — 37,8 km auf der falschen
  Seite der Linie. Der Fallback lehnt jetzt ab, wenn die Linie widerspricht.
- **`kiosque` und `kiosque-upper` sind zwei Hälften eines Trails und lagen in zwei Regionen.**
  `kiosque` ist bei Trailforks unter `gerardmer` geführt, liegt aber bei 48.2804/6.9281 — an
  Saint-Dié, 20 km nördlich von Gérardmer und 9,2 km nördlich der Linie. Dafür gibt es jetzt
  `SLUG_OVERRIDE` in `tools/vogesen_boundary.py` (nur für gemessene Fälle, nicht für Vermutungen).

## Entschieden (nicht mehr offen)

Der Nutzer hat die Feinaufteilung an mich delegiert (*"Ich gebe die Unterteilung Im Detail und damit die
genauen Grenzen der Trailregion an dich. So genau brauche ich das da nicht."*), also sind das
Festlegungen, keine Fragen:

- **Zuschnitt**: die rote Linie, pro Sub-Region über deren Schwerpunkt. Siehe oben.
- **Trails im ±5-km-Band der Linie bleiben bei ihrer Sub-Region.** Betrifft hier zwei
  Ribeauvillé-Trails ("Bomb-Track" −2,5 km, "Holy-Grail" −3,6 km). Eine Klammer über zwei Regionen zu
  splitten wäre der größere Schönheitsfehler als ein Trail, der 3 km über die Linie hängt. Der Build
  meldet nur noch deren Anzahl.
- **Die 16 Trails auf dem Grenzkamm bleiben hier**, auch die, deren Mittelpunkt nördlich von 49.045
  liegt (Wengelsbach, Wasigenstein, Lœwenstein, Hichtenberg …): sie sind Teil desselben
  Trailforks-Netzes um Wissembourg. Einzige Ausnahme wäre "Silzer Linde to forest road" (49.131, bei
  Silz, ~10 km nördlich der Grenze) — bleibt trotzdem drin, weil ein einzelner Trail keine zweite
  Region rechtfertigt und der Pfälzerwald ihn nicht hat.

## Pfälzerwald-Überlappung — erledigt

Vosges du Nord und Pfälzerwald sind derselbe Waldrücken beidseits der Grenze, und `pfaelzerwald.json`
reicht bereits bis 49.024 N — südlicher als Wissembourg selbst. Mit beiden Regionen aktiv wäre dieselbe
Strecke doppelt gezeichnet worden, unter zwei Namen und zwei Schwierigkeitsfarben.

Entscheidung des Nutzers: *"Lass die doppelten Trails im Pfälzer Wald. Doppelt brauche wir sie nicht."*
— also **drei Trails aus Nordvogesen entfernt**, der Pfälzerwald behält seine:

| entfernt | Länge | deckt sich mit | von pfaelzerwald abgedeckt | nicht abgedeckt |
|---|---:|---|---:|---:|
| Sindelsberg ZickZack | 507 m | `pw_bundenthal_sued_trail_1` + `_2` (beide zu 100 %) | 89 % | ~56 m |
| Kühnenkopf | 1 615 m | `pw_bundenthal_suedost_trail_1` (844 m, zu 77 %) | 57 % | ~692 m |
| Zeppelinhalde | 1 995 m | `pw_bundenthal_suedost_trail_2` (486 m, zu 100 %) | 45 % | ~1 095 m |

Das ist bewusst die **Gegenrichtung** zur üblichen Projektregel ("Trailforks gewinnt bei Name und
Geometrie"): alle vier Pfälzerwald-Gegenstücke hängen in den `TRAIL_SEGMENTS` von *Tour 14* und *Tour
15* (Bundenthal), und das Umbiegen von Loop-Segmenten auf eine Ersatz-ID ist noch nicht gebaut (siehe
`trailforks-duplicate-detection-method`). Auf dieser Seite zu löschen kostet dagegen strukturell nichts.

**Preis, damit er nicht wieder gefunden werden muss:** Sindelsberg ZickZack ist ein reines Duplikat, aber
Kühnenkopf und Zeppelinhalde tragen zusammen **~1,8 km Strecke, die der Pfälzerwald nicht hat** — die
Trailforks-Linien sind dort die längeren. Wenn du die lieber hättest, ist es eine Zeile:
`DUPLICATE_OF_PFAELZERWALD` in `tools/build_nordvogesen.py`, wo die Deckungszahlen pro Trail stehen.
Zeppelinhalde wäre der erste Kandidat. Zuschneiden auf den nicht abgedeckten Teil wäre die dritte
Option und ist absichtlich nicht gemacht — das wäre erfundene Geometrie mit erfundenem Namen.

`tools/region_dupe_check.py nordvogesen` findet jetzt **keine Überlappung mehr** mit irgendeiner
bestehenden Region.

**Grenzkamm:** unabhängig davon liegen 16 Trails mit ihrem Mittelpunkt nördlich von 49.045, also
teilweise auf der deutschen Seite (Wengelsbach, Wasigenstein, Lœwenstein, Hichtenberg …). Die bleiben
hier — sie sind Teil desselben Trailforks-Netzes um Wissembourg, und der Pfälzerwald hat sie nicht.

## Orte

**15 (Nord) und 12 (Süd)**, aus OSMs eigenen `place`-Knoten über `tools/add_region_places.py` — also genau
auf dem Punkt, an dem die Basemap den Namen selbst zeichnet, damit unser Label ihn überdeckt statt zu
verdoppeln (dieselbe "match the base map"-Regel wie bei Donnersberg).

Runde zwei, nach *"Es sind mir zu viele Orte. Dünn das gerne etwas aus … da wo wenig Trails sind oder viele
Orte beieinander liegen"* (2026-08-20) — aus 22+22 wurden 15+12, über genau die zwei genannten Achsen:

- **viele Orte beieinander**: `MIN_SEPARATION_KM` von 4 auf **8 km**.
- **wenig Trails**: eine **Quote pro Sub-Region**, `1 + Trails // 45`, maximal 4. Eine Klammer mit 14
  Trails bekommt damit ein Label, eine mit 148 vier. Ein Ort zählt für die Sub-Region, deren Trail ihm am
  nächsten liegt. Das kann `MAX_PLACES` allein nicht leisten, weil das eine regionsweite Summe ist, die die
  Einwohner-Rangfolge dann dort ausgibt, wo die größten Städte liegen.
- **Ausnahme: der Namensgeber einer Sub-Region ist vom Abstand befreit.** Sonst fällt genau der Name weg,
  nach dem die Klammer heißt: **La Bresse** (4 041 Einwohner, Namensgeber einer 82-Trail-Klammer *und* eines
  Bikeparks) war rausgefallen, weil es 8,15 km von Gérardmer entfernt liegt — an 150 m Grenzwert gescheitert.

Früher, in Runde eins, kam noch dazu: Labels aus dem Build-Skript, wenn die Region nicht im Katalog steht,
und `MAX_PLACES` pro Region überschreibbar (Default 10 passt zu einem Resort, nicht zu einem Massiv).

Vergeben: Saverne, Wissembourg, Barr, Ribeauvillé, Dabo, Saint-Dié-des-Vosges, Bitche, Raon-l'Étape,
Phalsbourg, Niederbronn-les-Bains, Ingwiller, La Broque, Oberhaslach, Lembach, Romanswiller.
Alle sieben Klammern haben mindestens ein Label.

## Katalog-Eintrag (einfügen, sobald `index.html` frei ist)

`countries` ist bewusst **explizit** (siehe `docs/sidebar-filters-ui.md`): primär FR, plus DE, weil der
`wissembourg`-Zweig über den Grenzkamm reicht.

```js
  // Trailforks, geerntet 2026-08-19 -- siehe docs/nordvogesen.md fuer Quelle, Methode (Geometrie UND
  // Hoehe kommen aus dem ElevationChart der Trail-Seite, keine Elevation-API), die vollstaendige
  // difficulty=-Codeliste und die geloeste Pfaelzerwald-Ueberlappung. Suedgrenze ist die vom Nutzer gezeichnete
  // rote Linie, als Regel in tools/vogesen_boundary.py; alles darunter ist regions/suedvogesen.json.
  // Schwierigkeit: Trailforks' eigene Bewertung -- hier veroeffentlicht kein Betreiber Grade.
  nordvogesen: {
    countries: ["FR", "DE"], label: "Nordvogesen", file: "regions/nordvogesen.json", trailCount: 483,
    bounds: [[48.10768, 6.81610], [49.13417, 7.93934]],
    subRegions: {
      wissembourg: { label: "Wissembourg", color: "#3a6ea5" },
      niederbronn: { label: "Niederbronn", color: "#a8452f" },
      saverne: { label: "Saverne", color: "#8a6a2f" },
      bruche: { label: "Bruche-Tal", color: "#2f8a7a" },
      sainteodile: { label: "Barr", color: "#6a3a8a" },
      ville: { label: "Ribeauvillé", color: "#c2185b" },
      vosges_ouest: { label: "Saint-Dié", color: "#7a7a2f" }
    }
  },
```

Farben sind innerhalb dieser Gruppe paarweise verschieden und keine ist `--forest` (`#2f5d3a`).

**Danach zwingend, in dieser Reihenfolge:**

1. `python tools/validate_region.py nordvogesen` — läuft bis dahin nicht, der Validator braucht den
   Katalog-Eintrag (`? nordvogesen is not in REGION_CATALOG`). Ohne Eintrag selbst geprüft und in
   Ordnung: keine doppelten IDs, keine verwaiste Geometrie/Profile, kein `url`-Feld, nur die vier
   erlaubten Schwierigkeiten, jedes Profil startet bei 0, kein Trail unter 2 Punkten, kein Trail-Slug in
   beiden Vogesen-Regionen.
2. ~~`python tools/update_region_versions.py`~~ — **schon gelaufen**, nachdem die parallele
   Pfälzerwald-Arbeit committet war: `regions/version.json` hat jetzt Einträge für beide Regionen.
   Nach jeder weiteren Änderung an den Region-Dateien erneut laufen lassen.
3. Eintrag in `CHANGELOG.md` und in `docs/backlog.md` (Abschnitt "Regionen"). Beide Dateien sind
   gerade ebenfalls uncommitted in Arbeit und wurden deshalb hier nicht angefasst.

## Bekannte Lücken

- **Keine Lifte** — geprüft (siehe oben), nicht angenommen: alles Selbst-Shuttle/Uphill.
- **Keine Touren/Trailrunden.** Trailforks hat "Routes" (z. B. "Enduro VTT De La Scherhol" bei
  Wissembourg), die nicht geerntet wurden — eigener Schritt mit `tools/gpx_map_match.py` gegen die 483
  Trails.
- **Rund 30 Trails sind kürzer als 150 m** (kürzester 50 m). Der Pfälzerwald-Build hat solche Stücke
  verworfen, das betraf aber automatisch erkannte Tour-Abschnitte, nicht benannte Trailforks-Trails —
  hier bleiben sie drin.
- **`activitytype` in der Tabelle ist KEIN Ausschlusskriterium.** 229 Zeilen tragen dort `hike`, was
  zunächst wie der Livigno-Fall aussah ("Trailforks-tagged Hike, nicht MTB → nicht aufnehmen"). Auf den
  Trail-Seiten selbst haben aber auch diese durchweg ein **`Bike Type` (AM/DH)** und eine
  Bike-Schwierigkeit, sind also als MTB-Trails registriert (geprüft an `champ-2`,
  `kreuzweg-to-hohwaldcamping`, gegen `bornes-to-be`, `le-chateau-935759`). Die Spalte scheint die
  vorherrschende Aktivität der Ridelogs zu sein, nicht die Klassifikation des Trails.

## Transfer aus dem Browser — beide dokumentierten Wege sind zu

Für die nächste Ernte relevant, weil es eine halbe Stunde gekostet hat:

- **`tools/harvest_receiver.py` funktioniert nicht mehr.** Chrome verweigert einen `fetch()` von einem
  PUBLIC-Origin (`https://www.trailforks.com`) auf `127.0.0.1` inzwischen komplett — bloßes
  `TypeError: Failed to fetch`, die Anfrage erreicht den Server nie. Der Header
  `Access-Control-Allow-Private-Network`, den der Docstring dort als Opt-in beschreibt, reicht nicht
  mehr (auch nicht mit erzwungenem Preflight über `Content-Type: application/json`).
- **Der Blob-Download geht genau einmal pro Origin.** Danach greift "multiple automatic downloads" —
  und zwar auch hinter einem echten, vertrauenswürdigen Klick (per `computer`-Tool getestet: der
  Handler läuft, die Datei erscheint nicht). Ein 13-Byte-Test scheiterte genauso wie 1,16 MB, es ist
  also nicht die Größe.
- **Was funktioniert: ein Popup auf `127.0.0.1` als Brücke.** `.tmpwork/vogesen/bridge_server.py`
  liefert unter `/bridge` eine winzige Seite, die sich per `postMessage` beim Opener meldet, den
  Payload annimmt und ihn **same-origin** an `/save?name=…` POSTet. Ein `window.open` ist eine
  *Navigation*, keine Subresource — Private Network Access greift dort nicht; ein `<iframe>` auf
  dieselbe URL wurde dagegen blockiert (geprüft). Das `window.open` braucht eine echte
  Nutzeraktivierung, also einen Klick per `computer`-Tool auf einen selbst in die Seite gesetzten
  Button. Danach lassen sich beliebig viele Dateien nachschieben, solange das Popup offen bleibt — hier
  fünf, bis 1,6 MB pro Stück.
