# Elba — Quellen, Bau und was offen blieb (2026-08-25)

222 Trails, 5 Sub-Regionen, keine Lifte, 179 Trails mit Trailforks-Bewertung. Gebaut mit dem generischen
Paar `tools/harvest_trailforks.py` → `tools/build_trailforks_region.py`, wie Madeira und der Gardasee.

## Die Quelle, und warum die Insel vorher wie ein Nest aussah

**Trailforks allein.** Der Nutzer hat die Region ausdrücklich „von Trailforks" bestellt, und kein Betreiber
auf der Insel veröffentlicht überhaupt eine Schwierigkeit — damit gilt hier dieselbe **protokollierte
Ausnahme** von der Betreiber-Regel wie bei Madeira und am Gardasee, nicht ein stillschweigendes Abweichen.

**Der Fund, der die Region überhaupt möglich gemacht hat, ist ein Werkzeugfehler, kein Datenfund.** Die
erste Suche über `tools/probe_tf_slugs.py` fand für Elba genau drei Slugs — `capoliveri` (4 Zeilen),
`porto-azzurro` (4), `cavo-65916` (5) — plus eine Zeile im Gebiet „Isola d'elba" unter der Provinz Livorno.
Vierzehn Zeilen, davon vier Zufahrten. Das las sich wie „Trailforks kennt Elba praktisch nicht".

Tatsächlich existiert `isola-d-elba-28064` mit **310 Zeilen**. Erreichbar ist die Region unter dem
naheliegenden Slug `isola-d-elba` — der aber **301 weiterleitet**, und `fetch()` in
`tools/harvest_trailforks.py` lief ohne `curl -L`. Eine Weiterleitung kam als ein paar hundert Byte zurück,
und jeder Aufrufer las das als „gibt es nicht". Beide Proben (`probe_tf_slugs.py`, `find_tf_regions.py`)
gehen durch dieselbe Funktion, also traf es beide.

**`fetch()` folgt jetzt Weiterleitungen** — und musste dabei gleich ein zweites Problem lösen, das erst
durch die Korrektur entsteht: ein Treffer auf einen nicht existierenden Slug landet danach nicht mehr auf
einem kurzen Redirect-Rumpf, sondern auf einer vollwertigen 200-OK-Fehlerseite, und die trägt selbst drei
`/trails/`-Links. Eine Probe, die solche Links zählt, meldete danach für **jeden** erfundenen Slug drei
Treffer. Deshalb hängt `fetch()` per `curl -w` die tatsächliche Ziel-URL an, schneidet sie wieder ab und
gibt `""` zurück, wenn sie auf `/error` endet.

Wer als Nächstes eine Region sucht: eine Probe, die „-- none --" sagt, meint das seit dieser Korrektur auch.
Vorher konnte sie eine 300-Trail-Region übersehen haben.

## Ernte

| Saat | Zeilen | neu |
|---|---:|---:|
| `livorno` (Provinz) | 558 | 558 |
| `isola-d-elba-28064` | 310 | 306 |
| `capoliveri`, `porto-azzurro`, `cavo-65916`, `amandolo-trail-zone-47478`, `isola-d-elba-20515` | 14 | 4 |

Die Provinz Livorno ist mitgeerntet, weil ihre Tabelle die vier Elba-Gebiete `Capoliveri`, `Porto Azzurro`,
`Isola d'elba` und `Amandolo Trail Zone` mitführt. `Material/Elba/areas_out_of_scope.json` hält die 13
Festland-Gebiete davon aus der **Geometrie**-Ernte heraus — das ist ausschließlich ein Kostenfilter, wie in
`build_trailforks_region.py` beschrieben; was am Ende in der Region ist, entscheidet allein die
Ankerregel. `portoferraio` ist als Region vorhanden, führt aber **keine eigene Trail-Tabelle** (0 Zeilen) —
ihre Trails hängen alle unter `isola-d-elba-28064`.

**235 Seiten geholt, 235 mit Polylinie UND Höhenprofil.** Kein einziger Trail ist an der fehlenden
`ElevationChart` gescheitert — anders als bei Kronplatz, siehe `docs/kronplatz.md`.

## Was gebaut wurde und was nicht

222 gebaut. Ausgeschieden:

* **9 zu weit von jedem Anker** (68–76 km) — allesamt Festland-Toskana, die letzten Reste der
  Livorno-Saat. Genau der Zweck der Regel.
* **4 asphaltierte Radwege** über `EXCLUDE_NAME_RE` (drei „Ciclabile Torre Mozza/Pappasole" am Festland,
  „Ciclabile di Pilade" auf der Insel).
* **2 Geometrie-Dubletten**, 1 Namensdublette (`Sentiero 7 #107` = `eb_sentiero_7`).

## Die fünf Sub-Regionen sind Geografie, nicht Trailforks' `riding area`

| Sub-Region | Trails | was drin ist |
|---|---:|---|
| Capoliveri | 63 | Capoliveri, Porto Azzurro, Monte Calamita, Naregno, Morcone, Mola |
| Monte Capanne | 51 | Marciana, Marciana Marina, Poggio, Sant'Ilario, San Piero, Pomonte, Chiessi, Seccheto, Fetovaia |
| Marina di Campo | 41 | Marina di Campo, La Pila, Colle Reciso, Lacona, Cavoli |
| Portoferraio | 34 | Portoferraio, Procchio, Biodola, San Martino, Magazzini, Bagnaia |
| Rio & Cavo | 33 | Rio nell'Elba, Rio Marina, Cavo, Nisporto, Volterraio, Porticciolo |

Trailforks' eigene Gebietsspalte taugt hier nicht als Antwort: ihr Gebiet „Marina di Campo" reicht bis
lon 10,127 — neun Kilometer **westlich** von Marina di Campo, mitten im Monte-Capanne-Massiv. Das ist
derselbe Verwaltungskasten-Effekt wie im Schwarzwald und am Gardasee.

## Keine Lifte

Elba hat genau eine Seilbahn, die **Cabinovia Monte Capanne** ab Marciana, und die ist ein Stehkörbchen —
da passt kein Rad hinein. Damit ist die Frage aus `docs/lifts-feature.md` beantwortet, ohne dass es eine
Betreiberseite braucht: es gibt nichts anderes zu prüfen. Kein `lifts`-Array, wie Madeira.

## Ortslabels

Vier: Portoferraio, Capoliveri, Marciana, Cavo. Marina di Campo und Rio Marina fallen an
`MIN_SEPARATION_KM` (8 km) — Marina di Campo liegt 7,2 km von Marciana. Auf einer 27 km breiten Insel ist
das die bindende Schranke, und sie global zu lockern würde jede andere Region mit ändern. Falls die vier
zu wenig sind, ist der saubere Hebel ein regionsspezifischer Wert, kein neuer globaler.

## Bewertungen

179 von 222 (81 %) tragen `rate`/`votes`/`pop`, **alle 222** den Trailforks-Slug (`tf`) für spätere
Auffrischungen. Bestbewertet: Zucca 2 (4,75 / 34 Stimmen), Cielo Alto 107B (4,67 / 42), Sassi Ritti
(4,64 / 26). Stand `asOf: 2026-08-25`.

## Offen

* **Der Nutzer war selbst auf Elba.** Seine eigene Einschätzung schlägt jede geerntete Bewertung — sowohl
  bei der Schwierigkeit als auch beim Zuschnitt der fünf Sub-Regionen. Beides ist bisher rein aus den
  Daten entschieden.
* 43 Trails ohne Bewertung; das ist normal für die dünn befahrenen Ecken und kein Fehler.
