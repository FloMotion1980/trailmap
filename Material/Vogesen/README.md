# Material/Vogesen — Trailforks-Ernte für Nordvogesen und Südvogesen

Eingaben für `tools/build_nordvogesen.py` und `tools/build_suedvogesen.py`. Geerntet 2026-08-19 durch das
eigene eingeloggte Chrome des Nutzers (siehe `trailforks-anonymous-polyline-extraction` und
`docs/nordvogesen.md`). Hier eingecheckt aus demselben Grund wie `Material/Harz/harz_tf_geo.json`: ohne
diese Dateien sind die beiden Build-Skripte auf jedem anderen Klon wirkungslos.

| Datei | Inhalt |
|---|---|
| `vogesen_table_full.json` | Trailliste Nord: Name, Gemeinde, Trailforks-Schwierigkeit, Aktivitätstyp, je Trailforks-Region eine Tabellenseite |
| `vogesen_geo.json` | Geometrie Nord, je Slug `{c: dekodierter encodedpath, p: ElevationChart-Sektionen}` |
| `vogesen_geo_black.json` | dieselbe Struktur für die 38 Trails, die der erste Durchlauf verpasst hatte (fehlender `difficulty`-Code 10 = `Severe / Black`) |
| `sued_table.json` | Trailliste Süd, gleiche Struktur |
| `sued_geo.json` | Geometrie Süd, gleiche Struktur |

Die Geometrie-Dateien tragen **beide** Kopien derselben Linie, die Trailforks ausliefert: die Polyline
(`c`) und die Punkte des Höhenprofils (`p`, mit echter Höhe und kumulierter Distanz). Die Builds bauen aus
`p` und prüfen dessen Länge gegen `c` — das ist der Korruptionsnachweis, der bei Varazze und Finale gefehlt
hat. Und weil `p` die Höhe mitbringt, brauchten diese Regionen keine Elevation-API.
