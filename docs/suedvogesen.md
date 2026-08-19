# Südvogesen — vorbereitete Region (noch nicht im Katalog)

Angefragt 2026-08-19, direkt nach dem Nordvogesen-Build: *"Für Colmar und weiter Südlich machen wir eine
eigene Region. Da sind ja auch die Bikeparks Lac Blanc und La Bresse. Das könntest du auch schon
vorbereiten"* — weiterhin **ohne Änderung an `index.html`**.

`Trailmap App/regions/suedvogesen.json` ist gebaut und vollständig; der `REGION_CATALOG`-Eintrag steht
unten zum Einfügen. Schwesterdokument: [nordvogesen.md](nordvogesen.md) — dort steht die Methode im
Detail, hier nur die Abweichungen.

## Die Grenze ist die rote Linie

Die Nordgrenze ist die **rote Linie, die du auf einem Trailforks-Screenshot eingezeichnet hast** (*"Ich
würde alles unter der eingezeichneten roten Linie zu der Region Südvogesen zählen"*) — als nachprüfbare
Regel in `tools/vogesen_boundary.py`, siehe [nordvogesen.md](nordvogesen.md) für die Herleitung aus dem
Screenshot und die Genauigkeit (±4 km). Sie läuft von 48.260 N / 6.567 E im Westen nach
48.124 N / 7.352 E im Osten.

**Lac Blanc ist damit hier** — die Klammer `kaysersberg` (Lac Blanc Bike Park, Labaroche, Trois Épis,
Turckheim, Le Bonhomme) liegt 7 km südlich der Linie. Das war genau das, was du mit der Nennung von Lac
Blanc gemeint hattest; die Linie hat es bestätigt statt es zu überstimmen. Umgekehrt ist
**`vosges_ouest` (Saint-Dié, Raon-l'Étape, Lac de la Maix, Donon) zurück nach Nordvogesen gegangen** —
das frühere *"ohne vosges_ouest"* hatte es hierher gelegt, aber die Linie läuft klar südlich von
Saint-Dié.

Jeder Build prüft **jeden Trail** gegen die Linie. Aktuell: alle 474 auf der Südseite, 10 im
±5-km-Unsicherheitsband (8 davon die Lac-Blanc-Parkstrecken selbst, bei −3,0 bis −3,8 km).

## Stand

**474 Trails, 533,1 km, 9 Sub-Regionen, 2 Lifte, 22 Orte, 1,21 MB.** Bounds
`[[47.74454, 6.36278], [48.17171, 7.28295]]`. Keine Touren/Trailrunden. Kein einziger Trail-Slug ist in beiden
Vogesen-Regionen (geprüft), und `tools/region_dupe_check.py suedvogesen` findet **keine geometrische
Überlappung** mit irgendeiner bestehenden Region.

| Sub-Region (Key) | Label | Trails | km | Ausdehnung |
|---|---|---:|---:|---|
| `thann` | Thann / Saint-Amarin | 118 | 181,1 | 47.758–48.007 N, 6.864–7.290 E |
| `labresse` | La Bresse / Hautes-Vosges | 91 | 107,7 | 47.832–48.065 N, 6.552–7.025 E |
| `epinal` | Épinal / Vallon d'Olima | 76 | 37,6 | 48.133–48.172 N, 6.363–6.467 E |
| `munstertal` | Münstertal | 66 | 62,4 | 47.956–48.109 N, 6.775–7.179 E |
| `guebwiller` | Guebwiller / Markstein | 40 | 39,2 | 47.846–47.944 N, 7.030–7.226 E |
| `colmar` | Colmar / Hohlandsbourg | 26 | 28,3 | 47.963–48.076 N, 6.915–7.283 E |
| `kaysersberg` | Kaysersberg / Lac Blanc | 25 | 27,1 | 48.061–48.147 N, 7.045–7.271 E |
| `masevaux` | Masevaux / Ballon d'Alsace | 18 | 29,6 | 47.745–47.875 N, 6.764–7.025 E |
| `gerardmer` | Gérardmer | 14 | 20,1 | 48.056–48.160 N, 6.866–6.954 E |

Schwierigkeiten: 74 grün, 235 blau, 110 rot, **56 schwarz** (Norden: 38 — die Hautes-Vosges sind das
steilere Gelände). Höhen 245–1355 m.

Drei Bikeparks: **La Bresse** (9 Trails), **Markstein** (6), **Lac Blanc** (8).

Gebaut von `tools/build_suedvogesen.py`. Rohdaten in `.tmpwork/vogesen/`: `sued_table.json` +
`sued_geo.json`, plus die Nord-Dateien für die übernommenen Klammern.

## Bikepark-Schwierigkeiten: mit den Betreiberseiten abgeglichen

Die Standing Rule ist "die Schwierigkeit des Betreibers gewinnt, Trailforks nur als Fallback". Für ~96 %
dieser Region gibt es keinen Betreiber (Club-Vosgien-/Community-Trails im Naturpark), aber für die drei
Bikeparks schon — die waren beim ersten Bau **nicht** geprüft. Jetzt sind sie es. Tabelle mit dem
Original-Wortlaut je Trail: `OPERATOR_DIFF` in `tools/build_suedvogesen.py`.

**Bike Park du Lac Blanc** (Quelle: die Station selbst,
`lac-blanc.com/ete/velo-vtt-vosges/bike-park-dh/`, geprüft 2026-08-19 — die **französische** Seite, die
englische Übersetzung verfälscht zwei Farben). Alle 7 DH-Pisten sind bei uns vorhanden und alle 7
zugeordnet:

| Piste | Betreiber | vorher (Trailforks) | jetzt |
|---|---|---|---|
| La SMOOTH | verte | grün | grün |
| La EASY | verte | grün | grün |
| La COOL | bleue | blau | blau |
| La FLOW | rouge | rot | rot |
| La ROOTS | rouge | rot | rot |
| **La FAT** | **rouge/noir** | rot | **schwarz** |
| La NUTS | noire | schwarz | schwarz |

La FAT ist die einzige Änderung: bei einer zweistufigen Angabe gilt die **härtere** Stufe — dieselbe
Richtung, in die auch der `max()` über die Teilabschnitte eines zusammengesetzten Trails rundet. Das
4X-Track (400 m) führt der Betreiber ohne Farbe, dort bleibt Trailforks stehen.

**Bike Park La Bresse-Hohneck** (Quelle: `labresse.labellemontagne.com/fr/ete/vtt-et-bikepark/bike-park/`):
6 Pisten techniques + 4 freeride. 9 der 10 sind bei uns — und **alle 9 stimmten bereits mit Trailforks
überein**. Sie stehen trotzdem in der Tabelle, weil "geprüft und identisch" und "nie geprüft" nicht
gleich aussehen dürfen. Nicht gefunden: "Schuss Line" (rouge) — nicht geraten.

**Bikepark du Markstein: nicht überprüfbar, bleibt auf Trailforks.** Die Seite, die kelbikepark.fr als
offiziell führt (`alsacefreerideacademy.fr/bikepark-markstein`), liefert heute eine
**"18+ ONLY"-Alterssperre** statt eines Bikeparks; `lemarkstein.net` und die Tourismusseite des Tals
veröffentlichen keine Pistenliste. kelbikepark nennt eine **Verteilung** (6 Pisten: 2 grün, 2 blau, 1 rot,
1 schwarz), die nicht zu unserem Bestand passt (Manala grün, Papala blau, Spaetzle blau, Schloppa rot,
Papala rouge rot) — es fehlen also eher ein grüner und ein schwarzer Trail, als dass die Bewertungen
falsch wären. Als ungelöst vermerkt.

## Lifte

**Zwei**, beide Sessellifte, beide mit dem dokumentierten Verfahren gebaut (`tools/add_lifts.py`, Eintrag
`suedvogesen`): Betreiber entscheidet die Zugehörigkeit, OSM liefert nur die Geometrie, gespeichert wird
Talstation zuerst.

| Lift | Sub-Region | Länge | Höhe | Beleg |
|---|---|---:|---|---|
| **Montjoie** (Lac Blanc) | `kaysersberg` | 1 191 m | 867 → 1 151 m | Station nennt nur "un télésiège débrayable"; es ist der einzige Sessellift dort, Bergstation 22 m vom Start aller 7 DH-Pisten |
| **Vologne Express** (La Bresse) | `labresse` | 1 173 m | 921 → 1 174 m | vom Betreiber namentlich als Lift des Bikeparks genannt; Bergstation 9 m von den Pisten-Startpunkten |

**Markstein bekommt bewusst keinen Lift.** kelbikepark sagt "1" für Biker geöffnete Bahn und ein
France-3-Artikel erwähnt einen im Sommer laufenden Sessellift — aber **OSM hat am Markstein überhaupt
keinen `chair_lift`**, nur Teleskis und Seillifte (nächster: `Tremplin 1`, 78 m von den Pisten-Startpunkten).
Zusammen mit der toten Betreiberseite heißt das: welcher Lift Bikes mitnimmt, ist unbekannt, und
Zugehörigkeit wird nie geraten (`docs/lifts-feature.md`). Ebenfalls ausgeschlossen und im Skript
begründet: Gérardmer/La Mauselaine, Ballon d'Alsace, sowie `Le Chitelet` neben dem Vologne Express.

**Ein Rebuild löscht die Lifte nicht mehr.** `add_lifts.py` schreibt sie *nach* dem Region-Build in die
Datei, und `write_region()` gibt nur aus, was es bekommt — `build_suedvogesen.py` liest ein vorhandenes
`lifts`-Array jetzt ein und reicht es durch. Damit entfällt die Reihenfolge-Regel, die es bei Bike Kingdom
noch braucht.

## Entschieden (nicht mehr offen)

Die Feinaufteilung liegt bei mir (*"So genau brauche ich das da nicht"*), also:

- **`epinal` (76 Trails) bleibt drin**, als eigene, klar benannte Klammer. Es ist eine Ansammlung um
  Épinal — alle vier Trailforks-Regionen (`epinal`, `vallon-d-olima`, `vallon-d-olima-33741`,
  `la-40-semaine-42294`) zentrieren innerhalb von 3 km um 48.160 N / 6.42 E, also ~65 km westlich von
  Colmar in der lothringischen Ebene statt im Massiv. Unter der roten Linie liegt sie aber (−11,7 km),
  und 76 Trails wegzuwerfen wäre teurer als ein etwas weit gefasster Regionsname. Wer sie nicht will,
  schaltet die Sub-Region in der Seitenleiste ab.
- **Trails im ±5-km-Band der Linie bleiben bei ihrer Sub-Region** (hier 10, davon 8 die
  Lac-Blanc-Parkstrecken selbst bei −3,0 bis −3,8 km).
- **`glaserberg-25360` bleibt draußen** (3 Trails, Jura über Leymen bei Basel, 60 km südlich von
  Guebwiller). Geerntet und in `sued_geo.json` vorhanden, falls daraus mal eine Jura-Region wird.
- **Name**: "Südvogesen", passend zu "Nordvogesen".

## Was hier anders lief als im Norden

Alles Übrige (Geometrie **und** Höhe aus dem `ElevationChart` der Trail-Seite, vollständige
`difficulty=`-Codeliste inkl. Code 10 = `Severe / Black`, Trailforks als Schwierigkeitsquelle weil kein
Betreiber Grade veröffentlicht, Sub-Region aus dem Region-Slug statt aus der „riding area"-Spalte) ist
identisch — siehe [nordvogesen.md](nordvogesen.md). Zwei Dinge kamen dazu:

**Die Kinderliste einer Eltern-Region ist NICHT vollständig.** Die zwei Département-Tabellen
(`haut-rhin-27353`, `vosges`) sind bei ~100 Zeilen hart abgeschnitten. Ihre Zeilen gegen die Vereinigung
aller auf ihrer Seite verlinkten Kind-Regionen zu vergleichen, brachte **neun Gemeinden ohne
Kind-Region-Link** zum Vorschein: **Gérardmer (13 Trails)**, **Bikepark du Markstein (6)**, Buhl (9),
Dolleren (6), Cornimont (4), Orbey (2), Ventron (2), Whir-au-Val (2), Donon (1). Ihre Slugs waren nicht
zu erraten (`bikepark-du-markstein-39293`, `whirauval`) — sie kamen aus dem Breadcrumb je eines ihrer
eigenen Trails. **Diesen Abgleich bei jeder künftigen Region machen**, sonst fehlt lautlos ein ganzer
Bikepark.

**Ausgeschlossen, aber geerntet:** `glaserberg-25360` (3 Trails: Blauenberg Trail, Glaserberg Flow,
Largwald Trail) liegt bei 47.442 N, 7.310 E — im **Jura** über Leymen bei Basel, 60 km südlich von
Guebwiller. Steht als `EXCLUDED_REGS` im Skript, damit es sichtbar fehlt statt einfach zu fehlen.
Falls du irgendwann eine Jura/Basel-Region willst, sind sie in `sued_geo.json` schon da.

**Zwei Trails ohne Geometrie:** `dahus` und `mansuy` haben auf Trailforks weder `encodedpath` noch
Profil — nicht gebaut, gemeldet.

**Verifikation:** alle 474 Trails stimmen zwischen Profil-Linie und Polyline auf 60 m überein.

## Orte

**22 pro Region**, aus OSMs eigenen `place`-Knoten über `tools/add_region_places.py` — also genau auf dem
Punkt, an dem die Basemap den Namen selbst zeichnet, damit unser Label ihn überdeckt statt zu verdoppeln
(dieselbe "match the base map"-Regel wie bei Donnersberg). Gefiltert nach Abstand zum nächsten Trail
(Stadt ≤ 5 km, Dorf ≤ 2,5 km) und nach Einwohnerzahl bzw. Namensgleichheit mit einer Sub-Region.

Das Werkzeug brauchte dafür drei Erweiterungen, alle drei allgemein nützlich:

1. **Labels aus dem Build-Skript, wenn die Region noch nicht im Katalog steht.** Die Funktion las die
   Sub-Region-Namen aus `REGION_CATALOG` in `index.html` — die hier fehlt. Ohne sie feuert der Test
   "heißt wie eine Sub-Region" nie, und genau der hält die Orte, nach denen man wirklich navigiert
   (Wissembourg, Saverne, Barr, Thann, La Bresse …), gegen beliebige Nachbardörfer. Fällt jetzt auf
   `SUBREGIONS` im jeweiligen `build_*.py` zurück.
2. **`MAX_PLACES` pro Region überschreibbar.** Der Default 10 passt zu einer Resort-Region (Brandnertal
   3×4 km); für ein ganzes Massiv mit 7–9 Sub-Regionen bleiben damit die Hälfte der Klammern namenlos.
   Beide Vogesen-Regionen stehen auf 22 — der Pfälzerwald daneben hat 27 bei ähnlicher Trailzahl.
3. **Mindestabstand zwischen zwei Labels (`MIN_SEPARATION_KM` = 4 km).** Ohne den vergab Südvogesen
   **sechs** seiner 22 Plätze an eine einzige Agglomeration (Mulhouse 106 341, Illzach 14 829,
   Kingersheim 13 178, Pfastatt 10 237, Lutterbach 6 261, Richwiller 3 704), weil ein Vorort mit 10 000
   Einwohnern ein Bergdorf mit 4 000 in der Rangfolge schlägt. Auf dem Bildschirm ist das ein Klumpen,
   und er kostete sechs Bergdörfer ihr Label.

**Jede Sub-Region beider Regionen hat mindestens 2 Labels innerhalb von 6 km**, das nächste jeweils
höchstens 2,6 km entfernt — keine Klammer bleibt namenlos.

Vergeben: Épinal, Guebwiller, Gérardmer, Thann, La Bresse, Masevaux, Saint-Amarin, Cernay, Remiremont,
Munster, Wintzenheim, Vagney, Orbey, Cornimont, Giromagny, Saulxures-sur-Moselotte, Soultzmatt,
Les Forges, Willer-sur-Thur, Fellering, Corcieux, Lautenbach.

## Ein Trail dabei rausgeflogen

Die Ortssuche hat einen Datenfehler aufgedeckt, den sonst niemand gefunden hätte: **drei der
Mulhouse-Labels hingen an einem einzigen Trail.** "Nonnenbruch Pfastatt side" (1,33 km) liegt bei
47.7676 / 7.2880 im **Stadtwald von Mulhouse**, flach, 23 km vom Saint-Amarin-Tal entfernt, in dessen
Klammer er gelandet war — der einzige Trail der Region in der Rheinebene. Dass ein Ausreißer die Labels
einer ganzen Region bestimmt, ist das Zeichen dafür, dass der Trail unpassend ist, nicht die Label-Regel.
Also raus, mit derselben Begründung wie bei `glaserberg-25360`: nicht im Massiv. Steht als
`EXCLUDED_SLUGS` in `tools/build_suedvogesen.py`, ist eine Zeile rückgängig zu machen.

## Katalog-Eintrag (einfügen, sobald `index.html` frei ist)

```js
  // Trailforks, geerntet 2026-08-19 -- siehe docs/suedvogesen.md (Methode: docs/nordvogesen.md).
  // Nordgrenze ist die vom Nutzer gezeichnete rote Linie, als Regel in tools/vogesen_boundary.py.
  // Schwierigkeit: Trailforks' eigene Bewertung, hier veroeffentlicht kein Betreiber Grade.
  // Drei Bikeparks drin: La Bresse, Markstein, Lac Blanc; 2 Lifte (Montjoie, Vologne Express).
  // Bikepark-Schwierigkeiten gegen die Betreiberseiten abgeglichen (Markstein: Seite tot).
  suedvogesen: {
    countries: ["FR"], label: "Südvogesen", file: "regions/suedvogesen.json", trailCount: 474,
    bounds: [[47.74454, 6.36278], [48.17171, 7.28295]],
    subRegions: {
      colmar: { label: "Colmar / Hohlandsbourg", color: "#a03a8a" },
      kaysersberg: { label: "Kaysersberg / Lac Blanc", color: "#a8452f" },
      munstertal: { label: "Münstertal", color: "#3a6ea5" },
      guebwiller: { label: "Guebwiller / Markstein", color: "#c1440e" },
      thann: { label: "Thann / Saint-Amarin", color: "#8a6a2f" },
      masevaux: { label: "Masevaux / Ballon d'Alsace", color: "#2f8a7a" },
      labresse: { label: "La Bresse / Hautes-Vosges", color: "#6a3a8a" },
      gerardmer: { label: "Gérardmer", color: "#4a7d3f" },
      epinal: { label: "Épinal / Vallon d'Olima", color: "#7a3a2f" }
    }
  },
```

Farben sind innerhalb dieser Gruppe paarweise verschieden und keine ist `--forest` (`#2f5d3a`).
Wiederholungen gegenüber Nordvogesen sind bewusst in Ordnung (siehe `CLAUDE.md`: Farben müssen nur
innerhalb einer Gruppe unterscheidbar sein).

**Danach zwingend:** `python tools/validate_region.py suedvogesen` (läuft erst mit Katalog-Eintrag).
`python tools/update_region_versions.py` ist bereits gelaufen — `regions/version.json` kennt beide
Regionen. Fehlt noch: je ein Eintrag in `CHANGELOG.md` und `docs/backlog.md`.

## Bekannte Lücken

- **Markstein hat keinen Lift in den Daten** — siehe oben; braucht eine Betreiberauskunft, welche der
  Teleskis Bikes mitnehmen.
- **Markstein-Schwierigkeiten unbestätigt** und vermutlich zwei Pisten unvollständig — siehe oben.
- **Keine Touren/Trailrunden.** Trailforks hat für mehrere dieser Regionen „Routes" (u. a. „Enduro
  Bressaud", das hier als eigene Trailforks-Region mit 27 Trails auftaucht und vermutlich ein
  Rennstrecken-Verbund ist) — Segmentierung wäre ein eigener Schritt mit `tools/gpx_map_match.py` gegen
  die 474 Trails.
