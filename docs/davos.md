# Davos Klosters — gebaut 2026-08-26

152 Trails, 275 km, 3 Sub-Regionen, 86 mit Trailforks-Bewertung, keine Lifte (siehe unten).
Verfahren und Quelle: **`docs/sechs-regionen-2026-08.md`**.

## Warum sie gebaut wurde

Die **größte einzelne Lücke im ganzen Alpenbogen** nach der Trailforks-Auswertung: 153 Trails auf 279 km,
und direkter Nachbar des bereits gebauten Bike Kingdom (153 Trails auf 179 km). Wer Lenzerheide in der App
hat, dem fehlte das Tal daneben.

## Zuschnitt: drei Täler, alle drei unsere eigene Entscheidung

Trailforks führt **alle 153 Linien unter einem einzigen Gebiet** „Davos Klosters" — es gibt von dort also
keinerlei Untergliederung zu übernehmen. Die drei Schubladen kommen aus den Koordinaten selbst:

| Sub-Region | Trails | was drin ist |
|---|---:|---|
| Davos | 79 | Parsenn, Jakobshorn, Rinerhorn, Pischa, Schatzalp, Sertig, Dischma, Flüelatal |
| Klosters | 43 | Klosters Platz und Dorf, Madrisa, Gotschna, Serneus — plus das Prättigau bis Küblis/St. Antönien |
| Landwasser | 30 | Monstein, Wiesen, Filisur — das Tal unterhalb von Davos |

`max_anchor_km` ist 9: die hochalpinen Übergänge (Jöriflesspass, Scalettapass, Sertigpass) liegen 5–8 km
vom nächsten Ort, gehören aber zweifelsfrei dazu.

Das Prättigau bekam **keine eigene Schublade**: nur vier Trails, und sie hängen an Klosters.

## Ausgeschieden

Genau einer: `Sertig Dörfli - Clavadel` — seine Trailforks-Seite trägt weder Polylinie noch Höhenprofil.

## Lifte: der Stand ist halb erhoben, bewusst nicht geraten

`davos.ch/aktivitaeten/radsport/mountainbiken/bike-transport` sagt wörtlich: **„Auf insgesamt sechs Stand-
und Luftseilbahnen ist der Transport mit dem Mountainbike möglich"**, dazu die **Schatzalpbahn** als
unabhängiger Betrieb (eigene Tarife, **keine Downhill-Bikes**, und der Sessellift dort nimmt gar keine
Räder). Die sechs werden auf dieser Seite aber **nicht namentlich genannt**, und die Live-Liftliste unter
`davosklostersmountains.ch/de/mountains/sommer/live-info/lifte` wird per JavaScript nachgeladen.

Die Namen aus OSM zu übernehmen wäre genau der Fehler, vor dem `docs/lifts-feature.md` warnt — bei
Kronplatz stand `aerialway:bicycle` tags zuvor bei zwei Bahnen falsch. Also **kein `lifts`-Array**, bis die
sechs benannt sind. Das ist eine halbe Stunde Arbeit, kein offenes Problem.

## Offen

* Die sechs Bahnen benennen und mit `tools/add_lifts.py` eintragen.
* Der **Alps Epic Trail Davos** (Jakobshorn → Sertig) ist als einzelner Trail drin und mit 4,63 aus 65
  Stimmen der meistbewertete der Region — als Trailrunde mit Abschnitten ist er nicht gebaut.
