# Kronplatz — gebaut 2026-08-25, nachdem die Geometrie ein Jahr lang gefehlt hat

23 Trails, 4 Lifte, 4 Sub-Regionen, 20 Trails mit Trailforks-Bewertung — 18 der 19 offiziellen
plus fünf, die der Betreiber nicht führt.
`docs/kronplatz-recherche.md` bleibt daneben stehen: es hält die **Betreibertabelle** fest, aus der hier
die Schwierigkeiten kommen, und die vier Beschaffungswege, die 2026-07 an der Geometrie gescheitert sind.

## Der fünfte Weg zur Geometrie: Trailforks

Die Recherche hatte OSM, eine Outdooractive-Sammlung, die Betreiberseite und die Trail-Detailseiten
durchprobiert — alle vier ohne brauchbare Linien. Trailforks war nicht darunter und liefert sie:

| Saat | Zeilen |
|---|---:|
| `bike-park-kronplatz` | 28 |
| `brunico` | 32 (4 eigene) |

22 Seiten geholt, **21 mit Polylinie und Höhenprofil**. `san-vigilio-di-marebbe` existiert als Region, hat
aber keine eigene Tabellenzeile.

## Schwierigkeit: der Betreiber gewinnt, und das ist hier nachprüfbar

`kronplatz.com` führt eine dreistufige Skala. Die Übertragung ist dieselbe wie bei Saalbach —
**easy→blau, medium→rot, difficult→schwarz**, `gruen` wird von dieser Skala nie erreicht. Die Tabelle steht
als `diff_override` in `tools/build_trailforks_region.py`, mit der **Betreiber-Formulierung neben der
Farbe**, damit die Zuordnung prüfbar bleibt, ohne die Seiten neu zu holen.

Von 23 gebauten Trails tragen 18 eine Betreiberangabe. **Genau eine widerspricht Trailforks:**

| Trail | Trailforks | Betreiber | gebaut als |
|---|---|---|---|
| Freeride Piz de Plaies | Intermediate / Blue Square | medium | **rot** |

Die übrigen fünf — `Telle & Co. 4b`, `Hühnerspiel 7B`, `Sambock trail`, `Sambock lower` — stehen nicht in der
Betreibertabelle (es sind Nummernwege des Südtiroler MTB-Netzes bzw. Trails außerhalb des Parks) und fallen
regelkonform auf Trailforks zurück.

## Vier Lifte, nicht fünf — und OSM lag in beide Richtungen falsch

Die Betreiberseite
`kronplatz.com/de/der-kronplatz/pisten-anlagen/aufstiegsanlagen-sommer` (Saison 16.05.–08.11.2026) führt
**vier** Kabinenbahnen: Olang 1 (Nr. 301), Olang 2 (302), Piz de Plaies (202), Kronplatz 2000 (102). Es ist
eine Live-Statustabelle, eine geschlossene Bahn stünde also mit „Geschlossen" drin — vier ist die ganze
Sommerliste, nicht die gerade offene Teilmenge.

**Das korrigiert `docs/kronplatz-recherche.md`, das 2026-07 fünf notiert hatte (zusätzlich Ried und Ruis).**
Beide sind exakt der Fall, vor dem `docs/lifts-feature.md` warnt: OSM taggt `Ried` mit
`aerialway:bicycle=yes` und `Ruis` mit `bicycle=summer`, und keine der beiden steht auf der Betreiberliste.
Dasselbe gilt für `Gipfelbahn`, `Kronplatz I` und `Kronplatz II`. Alle stehen mit Begründung in
`add_lifts.py`s `excluded`.

| Lift | Länge | Tal → Berg |
|---|---:|---|
| Kronplatz 2000 | 3 819 m | 951 → 2 252 m |
| Olang 1 | 2 920 m | 1 166 → 2 070 m |
| Olang 2 | 1 076 m | 2 070 → 2 261 m |
| Piz de Plaies | 727 m | 1 327 → 1 604 m |

## Sub-Regionen: die Geometrie, nicht die Hangzuordnung der Recherche

Die Recherche hatte Olang (9), St. Vigil (5), Reischach (5) notiert. Die geernteten Linien sagen etwas
anderes, und sie sind hier die belastbarere Quelle: Sigi, Uschi, Franz, Christian, Hans und der Herrnsteig
liegen alle auf der **Nordflanke** zwischen 46,754 und 46,771 — also über Reischach, nicht über Olang. Die
alte Zuordnung folgt vermutlich der bedienenden Bahn, nicht dem Hang.

| Sub-Region | Trails | Lage |
|---|---:|---|
| Reischach | 10 | Nordflanke, Herrnsteig plus die Bikepark-Linien über Ried/Ruis |
| Olang | 3 | Ostflanke: Telle Line, Telle & Co., Spitzhorn |
| St. Vigil | 2 | Süden: Furcia Trail, Freeride Piz de Plaies |
| Pustertal Nord | 3 | jenseits des Tals: Sambock über Bruneck, Hühnerspiel über Rasen |

„Pustertal Nord" gehört zu keiner der drei Flanken und ist deshalb eine eigene Schublade statt einer
schiefen Einordnung.

## Abgleich mit der offiziellen Trailliste (2026-08-25, vom Nutzer geliefert)

`kronplatz.com/de/der-kronplatz/aktivitaeten/kronplatzbikepark/trails` führt **19 Trails**. Die Tabelle ist
maschinenlesbar im HTML (eine `<table class="ds-listing-table">`, eine Zeile je Trail mit `data-id`, Status,
Name, `ds-slope-difficulty-N`, Länge und HM) — sie muss also nicht abgetippt werden, und sie bestätigt die
2026-07 in `docs/kronplatz-recherche.md` notierten Zahlen Zeile für Zeile.

**18 der 19 sind gebaut.** Fünf davon erst nach diesem Abgleich:

| Trail | vorher | jetzt |
|---|---|---|
| Crazy Bunny Line | als Geometriedublette des Furcia verworfen (78 %) | gebaut, `keep_overlapping` |
| CC Top Line | dito, als `cctop1` + `cctop2` (je 100 %) | beide gebaut, `keep_overlapping` |
| Gassl Trail | übersprungen, kein Höhenprofil bei Trailforks | gebaut, **von Komoot** |
| Dragon Trail | nirgends gefunden | gebaut, **von Komoot** |

Für Crazy Bunny und CC Top ist die Begründung: **der Betreiber entscheidet, was ein Trail ist.**
`duplicate_of` hat recht, dass ihre Linien im Korridor des Furcia liegen (OSM benennt Teilstücke sogar
„MTB Furcia Trail - CC Top"), aber kronplatz.com führt sie mit eigener Länge und Schwierigkeit, also sucht
ein Fahrer sie in der Liste.

### Trailforks' „GASSL trail" waren zwei Trails, und das war der ganze Fehler

Der Nutzer lieferte `bike-holidays.com/mountainbike-singletrail/detail/dragon-trail`, wo der Trail als
**Komoot-Tour** eingebettet ist. Komoots eigene API antwortet anonym und liefert die Linie MIT echter Höhe
je Punkt:

    https://www.komoot.de/api/v007/tours/<id>?_embedded=coordinates

Damit ließ sich zeigen, dass Trailforks' `gassl-trail` (8 364 m) gar nicht der Gassl Trail ist, sondern
**Dragon Trail und Gassl Trail als eine Linie** — gemessen, nicht vermutet:

* Dragon-Ende und Gassl-Anfang liegen **0 m** auseinander;
* 98 % der Dragon-Punkte und 99 % der Gassl-Punkte liegen näher als 25 m an der Trailforks-Linie;
* 99 % der Trailforks-Punkte liegen näher als 25 m an der Vereinigung der beiden (max. 43 m);
* 2 009 + 6 300 = 8 309 m gegen Trailforks' 8 364 m, und 167 + 883 = 1 050 gegen dessen 1 115 Hm.

Das erklärt auch die 30 %, um die Trailforks' Länge die Betreiberangabe verfehlte. Beide stehen jetzt
einzeln in der Region, jeder trifft seine Betreiberzahl fast genau:

| Trail | gebaut | Betreiber |
|---|---|---|
| Gassl Trail | 6,30 km / 879 Hm | 6 400 m / 907 Hm |
| Dragon Trail | 2,00 km / 167 Hm | 2 043 m / 197 Hm |

`gassl-trail` steht dafür in `exclude`, und beide kommen über `extra_trails` aus
`Material/Kronplatz/komoot/` — die Rohantwort samt Tour-ID und Herkunfts-URL liegt dort, ein Neubau braucht
also kein Netz. **Die DEM-Nachreichung, die es kurzzeitig für Gassl gab, ist wieder raus**: Komoot trägt
echte Höhen, also gilt die ursprüngliche Regel „keine Höhen-API" wieder unverändert.

**Dragon liegt in `kp_olang`, nicht in Reischach.** Die Linie startet am Gipfel (46,7394/11,9593, 2 252 m)
und endet ostwärts auf 46,745/11,972 — Komoot nennt die Tour selbst „Dragon Trail / Olang / Südtirol".
Die Hangzuordnung der alten Recherche liegt hier zum wiederholten Mal daneben.

**Herrnsteig blieb bei Trailforks**, obwohl bike-holidays auch dafür eine Komoot-Tour hat: die ist 9 744 m
lang, die Betreiberangabe 7 446 m, unsere Trailforks-Linie 7 190 m. Gemessen entschieden, nicht nach Quelle.

### Was weiterhin fehlt

**Mini Furcia Trail** (leicht, 210 m / 14 Hm, St. Vigil) — der kürzeste der 19. Nicht bei Trailforks, nicht
in OSM (Overpass über alle `highway`-Wege im Kronplatz-Kasten, deren Name einen der 19 Trailnamen enthält:
101 Treffer, keiner davon), und bike-holidays führt nur drei Kronplatz-Trails. Bleibt offen statt geraten.

**Gassl und Dragon tragen keine Bewertung.** Trailforks' 3,52 aus 28 Stimmen hängt an der zusammengesetzten
Linie und gilt damit für beide zusammen; sie einem der zwei zuzuschlagen wäre eine Behauptung, die die
Daten nicht hergeben. `docs/trail-rating-konzept.md` kennt „noch nicht bewertet" als ehrlichen dritten
Zustand. Falls das stören sollte, ist die Zuordnung eine Zeile in der Mapping-Datei.

**Fünf gebaute Trails stehen NICHT auf der Betreiberliste** und fallen regelkonform auf Trailforks'
Schwierigkeit zurück: `Telle & Co. 4b` und `Hühnerspiel 7B` (Nummernwege des Südtiroler MTB-Netzes),
`Sambock trail` und `Sambock lower` (eigener Berg nördlich von Bruneck) — also 23 Trails insgesamt.

## Nebenbefund am Bau-Werkzeug

`build_trailforks_region.py` lief die Tabelle bis dahin **alphabetisch nach Slug** durch, und weil
`duplicate_of` immer die gerade gebaute Linie als Dublette meldet, entschied allein diese Reihenfolge, wer
von einem überlappenden Paar überlebt. Hier hätte das den 4,8-km-Furcia zugunsten des 329-m-Fragments
`cctop1` verworfen. Die Schleife läuft jetzt **längste Linie zuerst**. Madeira ändert sich dadurch nicht;
für den Gardasee würde ein Neubau zwei IDs tauschen — siehe den Hinweis im Code, dessen Datei wurde
bewusst nicht neu gebaut.
