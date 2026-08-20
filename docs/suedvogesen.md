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

**474 Trails, 533,1 km, 12 Sub-Regionen (davon 3 Bikeparks), 2 Lifte, 12 Orte, 1,21 MB.** Bounds
`[[47.74454, 6.36278], [48.17171, 7.28295]]`. Keine Touren/Trailrunden. Kein einziger Trail-Slug ist in beiden
Vogesen-Regionen (geprüft), und `tools/region_dupe_check.py suedvogesen` findet **keine geometrische
Überlappung** mit irgendeiner bestehenden Region.

| Sub-Region (Key) | Label | Trails | km |
|---|---|---:|---:|
| `thann` | Thann | 118 | 181,1 |
| `labresse` | La Bresse | 82 | 96,7 |
| `epinal` | Épinal | 76 | 37,6 |
| `munstertal` | Münstertal | 66 | 62,4 |
| `guebwiller` | Guebwiller | 34 | 34,4 |
| `colmar` | Colmar | 26 | 28,3 |
| `masevaux` | Masevaux | 18 | 29,6 |
| `kaysersberg` | Kaysersberg | 17 | 15,2 |
| `gerardmer` | Gérardmer | 14 | 20,1 |
| **`bp_labresse`** | **Bikepark La Bresse** | 9 | 11,0 |
| **`bp_lacblanc`** | **Bikepark Lac Blanc** | 8 | 11,9 |
| **`bp_markstein`** | **Bikepark Markstein** | 6 | 4,9 |

**Die drei Bikeparks sind eigene Sub-Regionen** (2026-08-20, *"ich möchte dass die Bikeparks eine eigene
Unterregion werden"*). Sie sind liftbedient, vom Betreiber bewertet und werden als Ziel gefahren — in der
Talklammer ringsum gingen sie unter: Lac Blancs 8 Pisten waren ein Drittel von `kaysersberg`, Marksteins 6
ein Siebtel von `guebwiller`. Zugehörigkeit kommt aus der jeweils **eigenen Trailforks-Region** des Parks,
und die drei Listen kamen genau so heraus, wie die Betreiber sie veröffentlichen. Geprüft **vor** der
Talklammer, damit ein Trail, der Park *und* Gemeinde trägt, nicht über die Listenreihenfolge im Tal landet.

**Die übrigen Labels sind je EIN Name** (gleiche Anfrage): aus "Thann / Saint-Amarin",
"Masevaux / Ballon d'Alsace", "Épinal / Vallon d'Olima" wurde je der Talname. Was drin ist, steht in
`SUBREGIONS` in `tools/build_suedvogesen.py`.

Schwierigkeiten: 74 grün, 235 blau, 110 rot, **56 schwarz** (Norden: 38 — die Hautes-Vosges sind das
steilere Gelände). Höhen 245–1355 m.

Drei Bikeparks, jetzt je eigene Sub-Region: **La Bresse** (9 Trails), **Lac Blanc** (8),
**Markstein** (6).

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
veröffentlichen keine Pistenliste. kelbikepark nennt eine **Verteilung**: 6 Pisten, 2 grün / 2 blau / 1 rot / 1 schwarz.
**Seit der Park eine eigene Sub-Region ist, ist klar, dass wir alle sechs haben** — Manala (grün), Papala
(blau), Spaetzle (blau), Papala rouge (rot), Schloppa (rot), Dexter (schwarz), also 1/2/2/1. Es fehlt
demnach keine Piste; eine ist bei Trailforks nur eine Stufe härter eingetragen als beim Betreiber. Welche,
lässt sich ohne die Betreiberseite nicht sagen — als ungelöst vermerkt, aber deutlich kleiner als zuvor
angenommen. (Die frühere Notiz "es fehlen ein grüner und ein schwarzer Trail" war falsch: `Dexter` war
schon da, nur in `guebwiller` verborgen.)

## Lifte

**Zwei**, beide Sessellifte, beide mit dem dokumentierten Verfahren gebaut (`tools/add_lifts.py`, Eintrag
`suedvogesen`): Betreiber entscheidet die Zugehörigkeit, OSM liefert nur die Geometrie, gespeichert wird
Talstation zuerst.

| Lift | Sub-Region | Länge | Höhe | Beleg |
|---|---|---:|---|---|
| **Montjoie** (Lac Blanc) | `bp_lacblanc` | 1 191 m | 867 → 1 151 m | Station nennt nur "un télésiège débrayable"; es ist der einzige Sessellift dort, Bergstation 22 m vom Start aller 7 DH-Pisten |
| **Vologne Express** (La Bresse) | `bp_labresse` | 1 173 m | 921 → 1 174 m | vom Betreiber namentlich als Lift des Bikeparks genannt; Bergstation 9 m von den Pisten-Startpunkten |

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

Vergeben: Épinal, Guebwiller, Gérardmer, Thann, La Bresse, Masevaux, Saint-Amarin, Remiremont, Munster,
Wintzenheim, Orbey, Giromagny. Die drei Bikepark-Klammern bekommen keins — sie heißen in der Seitenleiste
schon nach ihrem Park, und ihr nächstes Dorf ist jeweils über ein anderes Label abgedeckt.

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
      colmar: { label: "Colmar", color: "#a03a8a" },
      kaysersberg: { label: "Kaysersberg", color: "#a8452f" },
      bp_lacblanc: { label: "Bikepark Lac Blanc", color: "#e07a1f" },
      munstertal: { label: "Münstertal", color: "#3a6ea5" },
      guebwiller: { label: "Guebwiller", color: "#c1440e" },
      bp_markstein: { label: "Bikepark Markstein", color: "#8a2f5a" },
      thann: { label: "Thann", color: "#8a6a2f" },
      masevaux: { label: "Masevaux", color: "#2f8a7a" },
      labresse: { label: "La Bresse", color: "#6a3a8a" },
      bp_labresse: { label: "Bikepark La Bresse", color: "#2f6ea8" },
      gerardmer: { label: "Gérardmer", color: "#4a7d3f" },
      epinal: { label: "Épinal", color: "#7a3a2f" }
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
