# Vinschgau & Meran — gebaut 2026-08-26

146 Trails, 392 km, 6 Sub-Regionen, 116 mit Trailforks-Bewertung, keine Lifte (noch nicht recherchiert).
Verfahren und Quelle: **`docs/sechs-regionen-2026-08.md`**.

## Warum sie gebaut wurde

**Die längsten Linien im ganzen Vergleichsfeld**: 2,7 km je Trail, gegen 1,2 bei Bike Kingdom und 0,5 bei
den deutschen Stadtwald-Kandidaten. Dazu direkter Südtiroler Nachbar des tags zuvor gebauten Kronplatz.

## Zuschnitt: sechs Täler statt zweier Bezirke

Trailforks kennt hier nur `Vinschgau` (**28 km Streuung** um seinen Schwerpunkt — von Reschen bis Latsch)
und `Burggrafenamt` (18 km). Beides sind Bezirke, keine Reviere.

| Sub-Region | Trails | was drin ist |
|---|---:|---|
| Obervinschgau | 47 | Mals, Glurns, Burgeis, Reschen, Graun, Prad, Stilfs, Trafoi, Sulden |
| Vinschgau Mitte | 36 | Schlanders, Laas, Latsch, Martell, Kastelbell, Goldrain |
| Meran | 35 | Meran, Dorf Tirol, Schenna, Hafling, Vöran, Lana, Algund, Marling |
| Naturns/Schnals | 12 | Naturns, Partschins, Plaus, Karthaus, Kurzras |
| Ultental | 11 | St. Walburg, St. Nikolaus, St. Pankraz |
| Passeiertal | 5 | St. Martin, St. Leonhard, Riffian, Pfelders, Moos |

**`max_anchor_km` ist 10 statt der üblichen 8**, und das ist gemessen entschieden: bei 8 fielen fünf Trails
heraus, die zweifelsfrei dazugehören (Stettiner Hütte, Eisjöchl, die 36er über Sulden, Gleck) — allesamt
hochalpin und entsprechend weit vom nächsten Ort. Bei 10 kommt nichts Fremdes dazu, nachgeprüft.

## Ortslabels: Südtirol taggt mehrsprachig

Sieben Ortslabels, und sechs davon mussten gekürzt werden — OSM führt hier jede Ortschaft mit allen
amtlichen Namen zugleich, „St. Leonhard in Passeier - San Leonardo in Passiria" sind 48 Zeichen auf einer
Karte, die großteils Berg ist. Die Kürzungen stehen namentlich in `PLACE_RENAME` in
`tools/add_region_places.py`, gekürzt wird nur über ~20 Zeichen: **„Merano - Meran" bleibt**, weil kurz und
nützlich, genau wie „Bruneck - Brunico" bei Kronplatz.

## Ausgeschieden

Zwei Namensdubletten (`Höfeweg`, `Roatbrunn trail`). Sonst nichts — alle 148 geernteten Zeilen trugen
Polylinie und Höhenprofil.

## Offen

* **Lifte.** Sulden, Schnalstal, Meran 2000, Hafling und die Vinschgauer Bahnen fahren im Sommer teils mit
  Biketransport — die Liste muss aber vom Betreiber kommen (`docs/lifts-feature.md`).
* 30 Trails ohne Bewertung.
