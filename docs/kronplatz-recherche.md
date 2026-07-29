# Kronplatz — Recherchestand, noch nicht gebaut (2026-07-30)

Die Region ist **nicht** in `REGION_CATALOG` und hat keine `regions/kronplatz.json`. Alles außer der
Geometrie ist beisammen; die Geometrie ist der Grund, warum sie nicht gebaut wurde. Dieses Dokument existiert,
damit die nächste Sitzung nicht dieselben vier Wege noch einmal geht.

## Was fehlt: die Geometrie

Vier Wege probiert, keiner tragfähig:

1. **OSM** — unbrauchbar. Die Trails liegen in Fragmenten mit inkonsistenten Namen: „Herrnsteig MTB Freeride",
   „Herrnsteig MTB Freeride Trail" und „Herrnsteig MTB freeride trail" sind drei verschiedene `name`-Werte
   für denselben Trail, und `chain_ways` bekommt daraus 1130 m von 4435 m zusammen. Von den 19 Trails der
   offiziellen Liste fehlen in OSM u. a. Telle, Sigi, Franz, Christian, Hans, Korer, Andreas, Alex,
   Spitzhorn, Piz de Plaies, Richard-Anton und Mini Furcia komplett.
2. **Outdooractive-Sammlung** — existiert nicht. Es gibt Einzelrouten (Furcia `58390529`, „Herrensteig MTB
   Trail" `801132985`), aber keine Raccolta/Collection, die den Park abdeckt, wie sie für Flims Laax
   (`2522082`) existiert. Pro Trail eine Suche wäre 19 Suchen.
3. **kronplatz.com/…/kronplatzbikepark/trails** — trägt die vollständige Tabelle (siehe unten), aber
   **keine** eingebettete Outdooractive-ID: das `conf.id='…'`-Muster, das bei finaleoutdoor.com funktioniert
   (siehe `docs/finale-ligure.md`), kommt im HTML nicht vor, ebenso keine GPX- oder Koordinatenspur.
4. **Die Detailseiten pro Trail** (`bruneck.com/en/activity/alex-trail_26587`,
   `olang.com/en/activity/gassl-trail_29724` — jeder Trail hat eine) enthalten ebenfalls keine Koordinaten
   und keinen GPX-Link; ihre Karten werden per JS nachgeladen.

**Nächster Schritt, wenn es weitergeht:** eine dieser Detailseiten im Browser öffnen und mit
`read_network_requests` beobachten, welche API die Karte füttert — das ist der Weg, mit dem Bike Kingdoms
Outdooractive-Projekt-API gefunden wurde (`tools/oa_harvest_server.py`). Alternativ die 19 Einzelsuchen auf
Outdooractive, oder den Nutzer nach GPX fragen — laut `docs/finale-ligure.md` ist genau das der zuverlässigste
Unblock, wenn entferntes Beschaffen mehrfach scheitert.

## Was steht: Trails, Schwierigkeiten, Gebiete

Quelle: kronplatz.com's eigene Trail-Tabelle (19 Trails, drei Hänge). Die Skala des Betreibers ist dreistufig,
also **easy→blau, medium→rot, difficult→schwarz, kein grün** — dieselbe Übertragung wie bei Saalbach, wo der
Betreiber ebenfalls nur drei Stufen führt.

| Trail | Betreiber | → diff | Länge | Abfahrt | Gebiet |
|---|---|---|---|---|---|
| Herrnsteig Trail | medium | rot | 7 446 m | 1 255 m | Olang |
| Gassl Trail | medium | rot | 6 400 m | 907 m | Olang |
| Telle Line | medium | rot | 617 m | 81 m | Olang |
| Sigi Line | medium | rot | 776 m | 140 m | Olang |
| Uschi Trail | medium | rot | 604 m | 89 m | Olang |
| Spitzhorn Trail | medium | rot | 1 000 m | 182 m | Olang |
| Franz Trail | difficult | schwarz | 1 021 m | 189 m | Olang |
| Christian Trail | difficult | schwarz | 637 m | 90 m | Olang |
| Hans Trail | difficult | schwarz | 718 m | 183 m | Olang |
| Furcia Trail | medium | rot | 4 900 m | 528 m | St. Vigil |
| Crazy Bunny Line | medium | rot | 491 m | 76 m | St. Vigil |
| CC Top Line | medium | rot | 687 m | 342 m | St. Vigil |
| Richard-Anton-Trail | medium | rot | 1 092 m | 98 m | St. Vigil |
| Mini Furcia Trail | easy | blau | 210 m | 14 m | St. Vigil |
| Piz de Plaies Trail | medium | rot | 2 774 m | 388 m | Reischach |
| Dragon Trail | easy | blau | 2 043 m | 197 m | Reischach |
| Korer Trail | difficult | schwarz | 911 m | 167 m | Reischach |
| Andreas Trail | difficult | schwarz | 906 m | 171 m | Reischach |
| Alex Trail | difficult | schwarz | 980 m | 181 m | Reischach |

Sub-Regionen also **Olang (9), St. Vigil (5), Reischach (5)** — die drei Hänge, die der Betreiber selbst
unterscheidet (Riscone/Reischach, San Vigilio/St. Vigil, Valdaora/Olang).

Zwei Zahlen aus anderen Quellen weichen ab und sind nicht übernommen: mountainbiker.it nennt „27 Trails" und
für Gassl 8,4 km, kronplatz.com selbst 19 Trails und 6 400 m. Die Betreiber-Tabelle gilt.

## Was steht: Lifte

Fünf Bahnen laufen im Sommer mit Biketransport (kronplatz.com, olang.com): **Kronplatz 2000, Olang 1+2,
Ried, Ruis, Piz de Plaies**. Die Saison ist 16.5.–8.11.2026. Beim Bauen in `tools/add_lifts.py` eintragen,
Geometrie per anker-genauem Namensmuster aus OSM, bbox etwa `46.65,11.85,46.82,12.05`.

## Orte

Naheliegend, Koordinaten wie immer aus OSM-`node[place]`: Bruneck/Brunico, Reischach/Riscone,
Percha/Perca, Olang/Valdaora, St. Vigil/San Vigilio, Furkelpass/Passo Furcia, Geiselsberg/Sorafurcia.
Für die zweisprachige Region ist zu klären, welche Namensform aufs Label soll — das ist eine Nutzerfrage.
