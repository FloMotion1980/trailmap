# Changelog

A chronological, skimmable log of notable changes — "what happened and when", newest first. For the
*why* behind any entry (design reasoning, rejected alternatives, exact bugs), check:

- **`CLAUDE.md`** — the living design doc. Every non-trivial decision here has a longer, dated writeup
  there, usually in the section for the feature it touches.
- **`tests/MUTATIONS.md`** — for a bugfix specifically, records the mutation that proves the fix's test
  actually catches the bug.
- **`docs/*.md`** — standalone writeups for bigger features (Tourenbuilder, lifts, Trailrunden, etc).

This file starts 2026-08-13 — it is not a full backfill of the project's history, which lives in
`git log`. Add a line here whenever you'd want to tell a teammate "here's what changed" without them
reading the diff; skip routine one-line data fixes (a single trail's difficulty, a name typo) unless
they're part of a larger entry.

**Any entry that adds/rebuilds trails, Tours or lifts must say where the data came from** — OSM Overpass,
an operator's own GPX/API, Trailforks (and which extraction method — the anonymous-polyline page source,
the `/widgets/trail/` embed, etc.), or sequential map-matching (`tools/gpx_map_match.py`) against an
existing region's trails/lifts. One clause is usually enough ("Trailforks' own encodedpath, harvested via
logged-in Chrome"); the full sourcing method, caveats and edge cases belong in the region's own build
script docstring or `CLAUDE.md`'s `Material/<region>/` bullet, not repeated here.

## 2026-08-25 (Umgebungssuche: „Trails in der Nähe")
- **Gebaut, nach dem Konzept vom Vortag** (`docs/naehe-konzept.md`, Suite `tests/browser/nearby.js`, 9 Fälle
  / 38 Checks, zwei geprüfte Mutationen). Ein **Anker** auf der Karte — langer Druck, am Schreibtisch
  Rechtsklick, oder 📍 in der Ankerzeile für die eigene Position — plus ein **Radius-Regler mit Trefferzahl**.
  Gemessen wird die Luftlinie zur nächsten Stelle eines Trails. Nichts davon wird gespeichert; im RIDE-Modus
  ist alles davon aus.
- **Die Karte dimmt, die Liste filtert — durch EINE gemeinsame Regel** (`nearbyPasses`). Das löst einen
  Widerspruch im Konzept selbst, das beides verlangte: `trailPassesFilters` räumt die Karte, „gedimmt, nicht
  ausgeblendet" will das Gegenteil. Gebaut ist die Fassung, die der Nutzer sichtbar beschrieben hat — dimmen
  auf der Karte (dieselbe Mechanik wie „Nur Highlights", beide Linsen zusammen, Solo gewinnt weiter über
  beide), filtern in der Liste, weil „3 km · 31 Trails" sonst eine Behauptung über eine Liste mit 219
  Einträgen wäre. Beide Mutationen davon sind geprüft: ohne den Filter behauptet die Zeile 31 und die Liste
  zeigt 219, ohne das Dimmen verliert die Karte stillschweigend ihre Linse.
- **Drei Entscheidungen fielen erst beim Bauen**, jede aus einer Messung: der erste Anker **lässt die
  Gruppierung fallen** (nach Region gruppiert wird innerhalb jeder Gruppe sortiert, nach Entfernung standen
  0,76 / 0,76 / 1,7 / 2,1 / 2,4 km — und dann wieder 0,5 km, wo die nächste Hub-Gruppe anfing); er legt die
  **Sortierachse** auf Bewertung, wo es Bewertungen gibt, sonst auf Entfernung; und die Kartenzeile zählt
  **Trails und Touren getrennt** („3 km · 9 Trails · 3 Touren"), weil beide im Radius liegen, aber in
  verschiedenen Abschnitten stehen.
- **Der lange Druck hängt im bestehenden `mapTouchStart`-Paar**, nicht in einem eigenen Handler: dieses Paar
  schickt für eine Berührung auf einer Trail-Linie ohnehin einen Klick ab, ein zweiter Handler hätte also aus
  einer Geste zwei Wirkungen gemacht (Anker setzen **und** Trail auswählen). Live geprüft: langer Druck
  mitten auf eine Linie setzt den Anker, ohne das Info-Panel zu öffnen.
- **Kosten gemessen, bevor sie jemand merkt**: `nearbyDistanceKm` merkt sich je Anker und filtert über die
  Bounding-Box vor — 16 ms für Finales 219 Trails, 147 ms für 1130 mit zugeschaltetem Gardasee, 88 ms für
  einen zweiten Anker. Ring und Ankerpunkt liegen im normalen Overlay-Pane, drehen sich also mit der Karte
  und kosten keine eigene SVG-Fläche (siehe `eachVectorRenderer`, dort waren es gemessen 40 MB).

## 2026-08-25 (Offizielle Zahlen fuer Bikecircus)
- **34 der 49 Bikecircus-Abfahrten stehen jetzt auf den Zahlen des Betreibers**, nicht mehr auf denen einer
  Aufzeichnung. `tools/harvest_oa_official.py` holt sie aus dem Outdooractive-Projekt der Betreiber selbst
  (`api-saalbach`, `api-saalfelden-leogang`) — Projekt und Schlüssel stehen offen im Quelltext ihrer eigenen
  Detailseiten, es braucht keine Anmeldung. Der Anstieg war der auffällige Posten: X-Line 98 → **0**,
  12er Sky-Line 89 → 0, Buchegg 97 → 0, Z-Line 71 → 0, fAIRy Line 121 → 4, Hacklberg 124 → 7. Oft korrigiert
  sich auch der Abstieg (fAIRy Line 381 → 190, Bergstadl 522 → 600, Hochalm 723 → 780) und die Länge.
- **Drei Zuordnungsregeln, jede aus einem echten Fehlgriff:** die **Katalognummer** entscheidet, nicht der
  Name (über den Namen hat „Pro-Line" zwölf Treffer — jede Promenade im Tal —, „Z-Line" einunddreißig; die
  Nummer steht im Trailforks-Namen, „Monti-Trail SH02", und im Betreiber-Slug, `sh-02-…`); **`-runde` und
  `-tour` sind keine Trails** (Leogangs `le-10-matzalm-trail-tour` ist eine 16,4-km-Runde mit 820 m auf und
  820 m ab — in Leogang ist die LE-Nummer die des Touren-Katalogs, nicht die des Trails); und **die Richtung
  kann entgegengesetzt sein** (Vink Link ist bei uns bewusst abwärts gedreht, die Betreibertour läuft
  aufwärts, 90 m auf / 1 m ab). Dazu zwei Plausibilitätsbremsen: eine Angabe mit auf == ab ist eine Runde,
  und eine, die den Höhenunterschied der eigenen Linie nicht hergibt, ist keine Angabe (Gateway: 2 m Abstieg
  für eine Linie, deren Anfang 44 m über ihrem Ende liegt).
- **15 Trails blieben offen und wurden NICHT geraten** — mit Grund je Trail in `docs/backlog.md`. Einer
  davon ist keine Zahlenfrage, sondern eine Geometriefrage: **Hot Shots** ist bei uns 2,10 km, beim Betreiber
  3,07 und bei Trailforks 2,82 — unsere Linie ist die kürzeste von drei Quellen. Fieberbrunn hat überhaupt
  kein Outdooractive-Projekt, seine drei Trails bleiben unverändert.
- **Die Krone sitzt höher** (`vertical-align:0.22em` statt `middle`): `middle` richtet Kästchen aus, nicht
  die Zeichenfläche darin, und die Emoji-Schrift setzt die Krone tief in ihr eigenes Kästchen — sie hing
  weiter unter der Schrift. In em, damit dieselbe Zahl für alle drei Größen gilt (14px Kachel/Panel, 12px
  Abschnittsblock, 11px Kartenlabel).

## 2026-08-25
- **Die Krone steht jetzt vor dem Namen**, in Kachel und Info-Panel, und der Schwierigkeitsbalken ist wieder
  ein reiner Balken. Über ihm war sie zweimal falsch: auf ihm liegend verdeckte sie ihn, und mit genug Luft
  darüber blieben von 52px Kachelhöhe nur 30 für den Strich (im Panel von 21px sogar nur 7). Fünf Varianten
  lagen dem Nutzer als Entwurf vor, bevor eine Zeile App-Code entstand; gewählt wurde die, die Kartenlabel
  und Trailrunden-Abschnittsblock **schon** hatten — eine Form an allen sechs Orten. Gemessen: alle 219
  Finale-Kacheln bleiben 52px hoch, auch die 28 gekrönten, am Schreibtisch wie bei 375px Breite. Die Krone
  ist mittig zur Schrift ausgerichtet (`vertical-align:middle`) statt auf der Grundlinie, weil die
  Emoji-Schrift sie tief in ihr eigenes Kästchen setzt — dieselbe Lösung, die `.badge-uphill` schon nutzt.
- **Der goldene Ring gehört allein dem weißen Startpunkt.** Ist der Trail markiert, stehen Start und Ziel
  wieder in Grün und Rot bei 1,5px: die gelbe Auswahlkontur sagt schon, welcher Trail gemeint ist. Gemessen
  in Bike Kingdom: 12 goldene Ringe (`#e0a326`/2,5) gegen 109 neutrale, genau die 12 gekrönten Kacheln.
- **Monti- und Panorama-Trail: der Anstieg war Aufzeichnungsrauschen, nicht Gelände.** Gespeichert waren
  81 bzw. 78 Höhenmeter Anstieg auf zwei reinen Abfahrten; offiziell sind es **3 bzw. 12** (Zahlen vom
  Nutzer). Beide korrigiert, `down` unangetastet, weil dafür keine offizielle Zahl vorlag (441/476 gegen
  Trailforks' 416/466 — Trailforks führt für beide Trails *keinen* Anstieg, `up: null`). Das ist kein
  Einzelfall: in derselben Region liegt der gespeicherte Anstieg bei **18 weiteren Abfahrten** über dem, den
  unser eigenes Profil hergibt, an der Spitze Hacklberg-Trail (124 gegen 30), X-Line (98/19) und Steinberg
  Line (100/21) — dieselbe Signatur. Noch nicht angefasst, weil jede Korrektur die offizielle Zahl braucht;
  steht im Backlog.
- **Monti-Trail (Saalbach): die GPS-Lasso-Schleife ist weg** (gemeldet vom Nutzer als „komischer Loop").
  Die Linie trug bei Punkt 260–274 eine geschlossene Schleife — Punkt 274 war **bitgleich** mit 260 —, 239 m
  lang und bis 112 m vom Anfangspunkt entfernt, ein Artefakt der Quellaufzeichnung. Gegen die Trailforks-Linie
  desselben Trails geprüft: dort gibt es sie nicht, und unsere Linie liegt sonst im Mittel 5,3 m auf deren
  Linie. Nach dem Schnitt 568 statt 582 Punkte, 3,69 statt 3,93 km, kein Sprung über 60 m, kein doppelter
  Punkt, kein Rückwärtssprung auf der Trailforks-Achse — die eine verbleibende Selbstannäherung (bei 3,08 km)
  hat Trailforks an derselben Stelle, es ist eine echte Kehre. **Beide Touren, die den Trail fahren**
  (THE CHALLENGE, BIG-5), wurden mitgezogen: derselbe Schnitt im Abschnitt, `trailGeo` neu verkettet, alle
  Abschnittsdistanzen neu gerechnet, Profil um dasselbe Fenster gekürzt, Länge 104,55 → 104,31 bzw.
  71,20 → 70,96 km. **up/down blieben unangetastet**, mit Grund: die gespeicherten Werte stammen aus
  dichteren Daten als das 100/200-Punkt-Profil (Monti 81/441 gegen 32/392 aus dem Profil gerechnet), und die
  Schleife trägt dort 14 m Anstieg — eine Korrektur aus der gröberen Quelle würde Herkunft mischen, um
  0,3 % zu gewinnen.

## 2026-08-24 (Die Krone)
- **Aus dem Wort „Highlight" wurde eine Krone** — der Nutzer wollte statt eines ausgeschriebenen Etiketts an
  einer Stelle eine Metapher an allen Stellen zugleich, und die Krone gewann gegen Flamme, Diamant und
  Lorbeer, weil sie nichts bedeutet, was die App schon sagt (die Flamme ist die Beliebtheit, der Stern die
  Bewertung). Sie sitzt jetzt **auf dem Schwierigkeitsbalken** — in der Kachel wie im Info-Panel, denn dort
  ist der Balken seit der Info-Box 2.0 ohnehin das linke, senkrechte Element. Die Kachel bekam dafür
  denselben Balken über die volle Kachelhöhe wie das Panel (`padding-left:14px`, 4px breit, 50 von 52px),
  und der farbige Punkt im Namen ist weg: zwei Anzeigen derselben Sache, von denen eine mitwuchs.
- **Auf der Karte, an den Endpunkten und am Regler dieselbe Krone.** Das Label trägt sie statt des ★; Start-,
  Ziel- und der weiße Startpunkt eines Highlights bekommen einen **goldenen Ring** (`#e0a326`, 2,5px statt
  1,5px) statt einer zweiten Krone, weil ein Emoji auf einem 5px-Punkt nicht lesbar wäre; und der
  **Schieberegler-Knopf ist selbst eine Krone** (Inline-SVG auf `var(--highlight)`) — er IST die Grenze,
  ab der etwas eines ist. **Im RIDE-Modus nichts davon**: dort zählt die Linie, nicht die Auszeichnung.
- **Am Tag danach in drei Punkten nachgezogen, alle aus der Benutzung** (2026-08-25): in der Kachel beginnt
  der Strich jetzt **unter** der Krone statt von ihr verdeckt zu werden (gemessen: Krone 1–12px, Strich 14–51px
  einer 52px-Kachel) — im Panel bleibt sie über der Zeile, weil ein eingerückter Strich dort von 21px nur 7
  übrig lässt; der **goldene Ring gehört allein dem weißen Punkt**, ein markierter Trail zeigt Start und Ziel
  wieder normal (die gelbe Auswahlkontur sagt schon, welcher Trail gemeint ist); und die Krone erscheint auch
  im **Abschnittsblock einer Trailrunde**, wenn der angeklickte Abschnitt ein gekrönter Komponenten-Trail ist.
- **Ein echter Fehler dabei gefunden und behoben**: die Schwelle rastet auf das 0,05-Raster des Reglers ein,
  die Karten-Ebenen und Labels wurden aber mit dem *ungerasteten* Wert gebaut — ein Trail mit 4,32 bei einer
  gerasteten Schwelle von 4,33 trug goldene Ringe, während seine Kachel keine Krone hatte (live an
  „Fürhörnli" gesehen). `lastAppliedHighlightMin` vergleicht jetzt den tatsächlich angewandten Wert und
  zieht Labels und Ringe nach. Die neue Prüfung in `tests/browser/rating.js` vergleicht Kachelwert gegen
  Reglerwert für jede Kachel, statt nur zu zählen.
- **Höhenprofil rückwärts**: die farbige Markierung eines Tourenabschnitts blieb beim Umdrehen stehen, während
  sich das Profil spiegelte. Sie wird jetzt mitgespiegelt (`totalForFlip - distEnd`), und der Hover-Cache
  bekam die Richtung in seinen Schlüssel — sonst antwortete er nach dem Umdrehen mit den alten Distanzen.

## 2026-08-24 (Info-Box 2.0)
- **Der Info-Panel ist umgebaut**, nach vier Beobachtungen des Nutzers und drei Entwürfen (Variante A):
  der **Trailname ist 17px in gemischter Schreibweise** statt 14px Versalien — er war das unauffälligste
  Element im Panel, kleiner als der RIDE-Knopf darunter; die **vier Aktionsknöpfe stehen unter dem
  Höhenprofil** statt in der Überschrift, womit nichts mehr am Namen klebt und der Kopf nie wieder
  zweizeilig wird; die **Punktzeile** („grüner Punkt → Länge → roter Punkt") ist weg, weil sie sich wie ein
  Streckendiagramm las, ohne eines zu sein — jetzt führt die Länge, Auf- und Abstieg stehen daneben, die
  **Bewertung kompakt in derselben Zeile**; das Highlight-Wort sitzt bei den Knöpfen. Die Schwierigkeit ist
  ein Balken statt eines Punkts und **wächst mit einem zweizeiligen Namen mit** (`align-self:stretch`).
- **Im Querformat steht der RIDE-Knopf NEBEN den Aktionsknöpfen**, nicht darunter — der Vorschlag des
  Nutzers, nachdem ein innerer Scrollbereich verworfen wurde ("Scrollen in der Infobox. Bitte nicht."). Das
  spart eine ganze Zeile und behebt den gemeldeten Fehler, dass bei einer Tour mit Abschnitts-Block der
  RIDE-Knopf unter die Bildkante rutschte: gemessen 275px → **229px** bei einem Deckel von 285px. Das Raster
  gehört dabei auf `#ipContent`, nicht auf `#infoPanel` — auf dem Panel gesetzt war es wirkungslos, weil
  alle Inhalte eine Ebene tiefer hängen (zweite Rasterspalte 0px breit).
- **Der Weißraum im Höhenprofil war innen**: `padTop`/`padBottom` von 5 und 9 der 48 viewBox-Einheiten
  dehnen sich mit — bei 72px Höhe also 7,5px oben und 13,5px unten leer. Jetzt 3 und 4; den unteren Wert
  brauchte nur die alte SVG-Beschriftung, die inzwischen HTML ist.
- **Beim Umschalten auf rückwärts folgte der Hover-Punkt dem alten Profil.** `getEleHoverData` hatte seinen
  Zwischenspeicher nur nach der Trail-ID benannt; ⏪ baut das Panel mit gespiegeltem `data-profile` neu auf,
  die ID bleibt aber gleich. Gemessen lag der Punkt bei 25 % der Breite auf cy 11,8, die gezeichnete Kurve
  dort auf 31,9 — bis zu 20 Einheiten daneben. Der Schlüssel enthält jetzt die Richtung; Abweichung ≤0,1.
- **Die Zwischenüberschriften „ohne Bewertung" / „ohne Beliebtheitswert" sind weg** (Nutzer: die fehlende
  Flamme bzw. der fehlende Stern sagt es schon). Die unbewerteten Trails hängen einfach hinten an — die
  Reihenfolge bleibt die Aussage, sonst würden sie mitsortieren, als hätten sie null Sterne.
- Nicht meine Änderungen: drei Testfälle zur Tipp-Erkennung auf der Karte scheitern in der Vorschau-Umgebung,
  weil ein per Skript erzeugtes Touch-Ereignis dort den Abfangmechanismus nicht auslöst — **auf dem alten
  Stand (v202) scheitern sie genauso**, geprüft durch Zurückstellen. Sie stammen aus einem echten
  Handy-Bericht und brauchen ein echtes Touch-Gerät.

## 2026-08-24 (Querformat)
- **Der Info-Panel ist im Querformat breiter: `min(34vw, 230px)` → `min(40vw, 290px)`.** Der Nutzer meldete
  ihn als „einen Tick zu hoch" und schlug zuerst vor, das goldene Highlight-Abzeichen wegzulassen — dann
  seine eigene, bessere Korrektur: breiter machen, dann bricht weniger um. Genau das ist die Ursache, kein
  Platzproblem des Abzeichens: gemessen bei 812×375 nimmt die Bewertungszeile eines Highlight-Trails bei
  230px **zwei Zeilen** (36px statt 18) und die Überschrift trägt ihre Knöpfe auf eine zweite — zusammen ein
  236px hoher Panel. Ab 290px sind beide einzeilig und der Panel ist 200px hoch; darüber ändert sich über 18
  geprüfte Trails und Touren nichts mehr. Das Abzeichen bleibt.

## 2026-08-24 (zwei Kleinigkeiten)
- **Das Höhenprofil war am Handy in beiden Achsen falsch skaliert.** Der viewBox ist fest 240 × 48 mit
  `preserveAspectRatio="none"`, x und y laufen also unabhängig — und am Handy gegenläufig: gemessen bei
  375px ist das Diagramm 313 × 46, x wächst also auf das 1,30-fache, während y auf 0,96 **schrumpft**. Eine
  7px-Beschriftung im SVG kam damit gleichzeitig 6,7px hoch und 36 % zu breit heraus („gequetscht und
  winzig", Nutzer). Zwei Änderungen: die Meter-Angaben sind **HTML statt SVG-Text** (11px, unverzerrt, in
  einem `.ele-wrap` über dem Diagramm, `pointer-events:none`), und das Diagramm ist am Handy **72px statt
  46px** hoch — das war auch der Grund für die gestauchte Kurve, 1 400 Höhenmeter auf 46px. Querformat
  40 → 56px. Der Panel trägt es: gemessen 209px für einen einfachen Trail und 276px für die höchste Tour bei
  einem Deckel von 370px.
- **Der Highlights-Regler kannte nur den Regionsfilter.** `highlightCount()` fragte ausschließlich
  `activeRegions.has(t.region)`, also versprach die Zahl neben dem Regler Trails, die gerade weggefiltert
  waren — in Finale mit nur „schwarz" 28 statt 8. Die Zahl geht jetzt durch `trailPassesFilters(t)`, dieselbe
  Regel, die auch die Kartenschleife und die Tourenliste benutzen. Die **Spanne** folgt den Filtern bewusst
  nicht: sie bliebe sonst nicht stehen, während man Chips umschaltet, und der eingestellte Wert könnte aus
  der neuen Spanne fallen. Skala stabil, Zahl ehrlich — die Entscheidung des Nutzers.
- Nebenbei: die Versionsnummer stand auf **201**, nicht auf der Zahl, die ich erhöhen wollte — die erste
  Erhöhung griff ins Leere, und genau deshalb lieferte der Browser noch die alte CSS aus. Jetzt v202 an allen
  vier Stellen.

## 2026-08-24 (zuletzt)
- **Finale Fall für Fall durchgegangen**: 19 Zuordnungen entschieden, 0 offene Fälle, 134 → 142 bewertete
  Trails (65 %), 154 IDs. Damit hat **keine Region mehr einen Prüfstapel**; gesamt 1 777 bewertete Trails.
- Der lehrreichste Fall ist eine ABLEHNUNG: `Rose di Pietra` gegen `cuore-di-cervo` hat Längenverhältnis
  0,96 und 169 m Endpunktabstand — sieht aus wie 1:1 — aber nur 0,53 Deckung. Genau das Muster zweier
  PARALLELER Trails, vor dem `match_trailforks.py` seit Base Nato / Madre Natura warnt. Länge und Nähe
  ersetzen die Deckung nicht.
- Zwei Fälle, die nur ein Mensch entscheiden konnte: unser `Cava-Green Carpet` ist Trailforks'
  „Cava - Tappeto Verde" (wörtliche Übersetzung, Deckung 1,00, aber unbewertet — ID gemerkt), und
  `Rollercoaster-San Pantaleo` bekommt die 4,52 aus **271 Stimmen** des Rollercoaster, obwohl der nur ein
  Fünftel unseres kombinierten Eintrags ausmacht.

## 2026-08-24 (Nacht darauf)
- **Harz Fall für Fall durchgegangen**: 18 Zuordnungen entschieden, 0 offene Fälle, **21 → 36 bewertete
  Trails (86 %)** und für **alle 42** eine gespeicherte ID. Der Harz ist der reine Bikepark-Fall: Trailforks
  zerlegt jeden Trail in upper/middle/lower, unser Eintrag ist der ganze — vierzehn der achtzehn
  Entscheidungen sind gewichtete Abschnitts-Summen, deren Teillängen jeweils genau unsere Traillänge
  ergeben (Downhill Braunlage: 944 + 469 + 1 343 m gegen unsere 2,75 km).
- **Die Nummer-Regel vergleicht jetzt numerisch und akzeptiert eine Ziffer**: im Bodetal schreibt Trailforks
  unsere Nummern als „#1"/„#2"/„#4", wir schreiben „(01)"/„(02)"/„(04)". Beide Hälften waren nötig — die
  Zwei-Ziffern-Schwelle hat alle drei übersehen, und ein Textvergleich hätte sie wieder übersehen. Eine
  FÜHRENDE Zahl braucht weiter zwei Ziffern, sonst wäre „4-Burgen-Weg" eine Katalognummer.
- **Die ältere Harz-Ernte ist in `trailforks_geo.json` eingeflossen** (23 Linien, die der Abgleich vorher
  gar nicht sah). Das hat den Stapel erst von 15 auf 18 wachsen lassen und dann 24 statt 8 automatische
  Treffer ergeben — mehr Daten heißt hier mehr Arbeit und ein besseres Ergebnis.

## 2026-08-24 (Abend, später)
- **Schwarzwald Fall für Fall durchgegangen**: 26 offene Zuordnungen entschieden, 0 offene Fälle,
  264 → 271 bewertete Trails und 572 gespeicherte IDs. Sechs davon sind reine ID-Merker (das Gegenstück ist
  unbewertet), sechs echte Absagen. Schönster Fund: unser `deadmansfirstride` ist die englische Übersetzung
  von Trailforks' „Toter Mann", und unser „Dr. LTW" die Abkürzung von „Dr. Ludwig Thoma".
- **Ein unbekannter Slug wird jetzt gemeldet, statt still zu scheitern.** Er kam zweimal vor, beide Male
  weil der Prüfbericht seine Slug-Spalte bei 34 Zeichen abgeschnitten hat und ich den gekürzten Namen
  übernommen habe (`flohtrail-2-kinderund-jugendstreck` statt `…strecke`,
  `vierburgenweg-landeckmunding` statt `…mundingen`). Ohne Warnung sieht das aus wie eine erledigte
  Entscheidung: die Tabellensuche liefert nichts, es wird nichts angehängt, und niemand merkt es. Der
  Bericht kappt Slugs jetzt nicht mehr.
- **`review_cases.py --sections`** zeigt für jeden offenen Fall JEDE Trailforks-Linie, die auf unserer
  liegt. Das ist die Sicht, die einen Fall entscheidbar macht — die Kandidatenliste ist es nicht: ein Trail,
  über den unsere Linie führt, kommt auf Deckung 1,00, also füllen sich die oberen Plätze mit Nachbarn,
  während das Stück mit unserem eigenen Namen darunter liegt.

## 2026-08-24 (Abend)
- **Paznaun und Bike Kingdom Fall für Fall durchgegangen**, 39 offene Zuordnungen entschieden: Paznaun
  4 → 7 bewertete Trails, Bike Kingdom 56 → 71 (und 77 gespeicherte IDs). Beide Regionen haben jetzt
  **0 offene Fälle**, jede Entscheidung mit Begründung in `Material/<Region>/tf_manual.json`.
- **Drei Regeln, die der Nutzer dabei vorgegeben hat** (siehe `docs/trail-rating-konzept.md`): zwei
  Trailforks-Abschnitte eines unserer Trails werden stimmen-gewichtet zusammengefasst (Stimmen addiert,
  Beliebtheit als Maximum, weil eine Summe denselben Fahrer doppelt zählt); ein anders benannter Trail wird
  angehängt, wenn er DIE Linie ist, nicht wenn er eines von mehreren Teilstücken ist; eine Zufahrt bekommt
  nichts. `merge_sections()` rechnet den gewichteten Fall.
- **Eine Nummer im Trailforks-Namen kann auch die falsche sein**: „Bike & Hike Berglisee" trägt #7170, nicht
  unser 7190 — die Nummer wurde geprüft, nicht angenommen.

## 2026-08-24 (Nachmittag)
- **Die Trailforks-ID steht jetzt an jedem zugeordneten Trail**, nicht nur an den bewerteten: 3 730 von
  4 555 statt 1 717. Der Schreibschritt hatte eine Zeile ohne Stimmen komplett übersprungen, ID inklusive —
  und damit die teure Hälfte weggeworfen. Die Zuordnung verfällt nicht, die Stimmen kommen später.
- **Nummer-Regel im Abgleich**: Trailforks führt die Trailnummern des Betreibers im eigenen Namen
  („Velilltrail #7134"). Eine geteilte Nummer ist eine Identitätsaussage beider Quellen und löst genau den
  Fall, an dem die vier bisherigen Signale scheitern — ein 2,0-km-Abschnitt von Trailforks liegt in unseren
  8,5 km desselben Trails, während ein Nachbarabschnitt auf reine Deckung höher kommt. Dazu zwei
  Folgeänderungen: bei einem Doppelanspruch gewinnt die Nummer (statt der Deckung), und bei geometrischem
  Gleichstand entscheidet der Name — der auch als dritter Sortierschlüssel nötig war, weil vorher die
  Wörterbuch-Reihenfolge bestimmte, welcher von zwei Kandidaten mit 1,00 „erster" ist. Negativkontrolle
  gegen den Gardasee unverändert bei 0 falschen Treffern. Ergebnis: 1 717 → 1 731 bewertete Trails
  (Finale 131 → 134, Paznaun 4 → 7, Bike Kingdom 56 → 58, Sölden 29 → 30, Bikecircus 32 → 34).
- **Handentscheidungen in `Material/<Region>/tf_manual.json`** (`{id: {slug, why}}`), die beide Regeln
  überstimmen — sonst wirft jeder erneute Lauf einen gemeinsam entschiedenen Fall zurück in den Prüfstapel.
  Erste Einträge: Paznauns Duty Free Laret (Nutzerentscheidung: anhängen) und Schäfersteig (nur ID merken,
  noch unbewertet).

## 2026-08-24 (Nacht)
- **Bewertungen und Beliebtheit für 23 weitere Regionen** — 1 718 von 4 555 Trails (38 %) tragen jetzt
  einen Wert, gegenüber 131 in einer einzigen Region am Vortag. Die Abdeckung je Region steht in
  **`docs/trail-rating-abdeckung.md`** (erzeugt aus den Regionsdateien selbst), das Verfahren in
  `docs/trail-rating-konzept.md`. Höchste Abdeckung: Livigno 93 %, Sölden 85 %, Madeira 78 %; die größten
  Blöcke: Gardasee 387, Schwarzwald 261, Südvogesen 158, Pfälzerwald 156.
- **Zwei Wege statt einem.** Wo die Region AUS Trailforks gebaut wurde, ist die Zuordnung ein Nachschlagen
  (`tools/map_tf_slugs.py`: id → Name → nächste Linie, jeweils gegen die Endpunkte geprüft) — über 1 606
  Zuordnungen kein einziger abweichender Name. Wo unsere Geometrie von einem Betreiber oder aus OSM kommt,
  füllt der unscharfe Abgleich die Lücken (`tools/union_mapping.py`), aber nur mit seinen `match`-Urteilen;
  ein `review` bleibt unbewertet. Das hebt Sölden von 14 auf 29, Livigno von 0 auf 28 und Bike Kingdom von
  4 auf 56.
- **Vier Regionen bekommen nichts, und das ist die Antwort**: Donnersberg, 3-Länder, Serfaus, Waldmeister.
  Trailforks kennt dort 4, 11, 3 und 5 Trails. Der Anteil in der Tabelle misst, wie viel in einer Region
  geloggt wird, nicht wie gut wir sie erfasst haben.
- **Neue Werkzeuge**: `harvest_tf_ratings.py` (nur die Zahlen, für eine Region, deren Geometrie schon da
  ist), `find_tf_regions.py` + `probe_tf_slugs.py` (Trailforks hat keine brauchbare Suche — ein Slug wird
  erraten und probiert), `phase_b_run.py`, `merge_tf_tables.py`, `rate_region.py`, `rating_report.py`.
  Drei Dinge, die mehr wert sind, als sie aussehen: ein **fehlgeschlagener Abruf wird nie als „keine
  Bewertung" verbucht** (sonst markiert eine Drosselung eine ganze Region als unbewertet, und der
  Wiederanlauf überspringt genau diese Zeilen); die Bewertung wird an der **eigenen** Trail-id der Seite
  verankert (die steht in jedem Link der Seite, ein Nachbar einmal — der Modus ist richtig, „erster
  Treffer" ein Münzwurf); und `--areas` begrenzt eine breite Ernte auf die Gebiete, die zur Region gehören
  (Laax liegt unter `graubunden`: 2 416 Zeilen über 70 Gebiete, davon 122 relevant).

## 2026-08-24
- **Die Zeile ragte 14px in den rechten Rand der Seitenleiste** — ein echter Layoutfehler, kein reines
  Textproblem: als gewöhnliches Flex-Item in `.toggle-row-group` nahm sie ihre **Inhaltsbreite** (331px) in
  einem 317px-Container an, ohne `min-width:0` also keine Möglichkeit zu schrumpfen. Behoben mit
  `flex-basis:100%; min-width:0`.
- **Beide Zahlen stehen IN der Bahn** — der Regler gewinnt damit ~65px (170px statt 105px in der
  375px-Schublade, 190px am Schreibtisch). Der Text weicht dem Griff aus, steht also immer auf der Seite,
  auf der der Griff nicht ist, und **kürzt sich selbst, wenn seine Seite zu eng wird**: in der Schublade
  bietet eine Seite einer 170px-Bahn in der Mitte des Wegs 78px, „3,89 ★ · 89 Trails" braucht dort 83 — in
  diesem schmalen Fenster fällt das Wort weg und es liest sich „3,89 ★ · 89". Gemessen an sieben Positionen
  inklusive der Mitte, wo beide Seiten am engsten sind; Luft überall ≥ 5px. Eine feste Schriftgröße, die
  das auch löst, wäre am Schreibtisch unnötig klein gewesen. Die Bahn ist dafür 18px hoch statt der 4px,
  die ein Browser von sich aus zeichnet.
  Zwischenstand, den der Nutzer nach direktem Vergleich verworfen hat: Wert **neben** dem Regler, nur die
  Trailzahl in der Bahn. Rechnerisch bequemer (29px Luft), aber die Zeile las sich schlechter.
- **Schalter, Regler und Trefferzahl stehen in EINER Zeile, und der Regler ist grau, solange der Schalter
  aus ist** (Nutzer). Damit ist auch das Ziehen-schaltet-selbst-ein von heute Morgen wieder weg: es gab zwei
  Wege in denselben Zustand, jetzt gibt es den Schalter. Gemessen in beiden Breiten — eine Zeile, 26px hoch
  (normale Schalterzeile 20px plus eigenes Padding), Label 119px + Regler 105px + Zahl 89px von 331px, die
  Zahl schließt genau am rechten Rand ab; auch in der 375px-Schublade, weshalb „Nur Highlights"
  ausgeschrieben bleiben kann. Der Regler darf dabei **nicht** im `<label>` liegen — sonst schaltet jeder
  Zug am Regler den Schalter um; die Zeile ist ein `div`, das Label nur ihr erstes Kind.
- **Der Highlights-Regler steht da, sobald etwas Angezeigtes bewertet ist** — vorher erschien er erst, wenn
  der Schalter „Nur Highlights" an war, und die erste Rückmeldung des Nutzers war „ich sehe den Regler
  nicht". Ein Bedienelement, das man erst findet, nachdem man ein anderes gefunden hat, findet niemand.
  **Ziehen schaltet Highlights jetzt selbst ein**, der Schalter bleibt das Aus — sonst tut der erste Zug
  nichts Sichtbares. Und der Regler sagt im Tooltip, was ein Highlight überhaupt ist: Bewertung ab dem
  eingestellten Wert, voreingestellt auf das beste Fünftel der bewerteten Trails der
  angezeigten Regionen. `tests/browser/rating.js` prüft beides (sichtbar bei ausgeschaltetem Schalter, ein
  Zug schaltet ein und dimmt die Karte — inzwischen ersetzt, siehe oben). **Doppelklick auf den Regler setzt auf die Vorgabe zurück** —
  zurück heißt dabei der aus den Daten gerechnete Wert, nicht der, mit dem der Regler zuletzt gestartet ist,
  sonst wäre „zurück" davon abhängig, wann man das letzte Mal geschoben hat.
- **Keine Mindest-Stimmenzahl mehr für ein Highlight.** Die Regel war ein Netz gegen „zwei begeisterte
  Stimmen, 4,9 Sterne" — einen Fall, den `rate` nicht erzeugen kann, weil es der bayessche Wert ist:
  Finales bestbewerteter Trail mit unter fünf Stimmen kommt auf 4,11, die Vorgabe lag bei 4,49. Sie hat in
  131 bewerteten Trails nichts abgefangen, aber 21 davon aus der Spanne des Reglers herausgehalten. Jetzt
  zählen 131 statt 110, die Vorgabe wandert von 4,47 auf 4,45 und hält 26 statt 22 Trails; die Spanne
  (2,99–4,77) bleibt gleich. `votes` bleibt in den Daten für ein späteres Update, wird aber nirgends gelesen.
  Nebenbei aufgefallen: `PRELOAD_CACHE_NAME` war bei v193 stehengeblieben, während `sw.js` schon auf v195
  war — `appshell` hätte das sofort gesagt, ich hatte es zwei Commits lang nicht mitlaufen lassen.
- **Kein Dichte-Gate mehr für die Bewertungs-Oberfläche.** Sie erscheint, sobald *irgendetwas* Angezeigtes
  bewertet ist (`ratedTrailCount() > 0`) statt ab 35 % Abdeckung — auf Wunsch des Nutzers („Ist doch
  trotzdem gut zu sehen"), und die alte Regel war ohnehin falsch gebaut: sie poolte die aktiven Regionen,
  also machte das Zuschalten von Madeira (158 Trails, keine Bewertungen) aus Finales 60 % ein 34,7 % und
  ließ das Feature **für Finale** verschwinden. Geblieben ist eine Datenbedingung statt einer Regel: der
  Regler braucht ≥10 bewertete Trails, weil er sonst keine Spanne hat.
- **Weder Quelle noch Stimmenzahl stehen in der Oberfläche.** Die Herkunft bleibt in den Daten (`tf`-Slug je
  Trail plus ein `ratings`-Block je Region), damit eine Bewertung nachprüfbar und später aktualisierbar ist —
  sichtbar ist sie nirgends, auch nicht in `title`-Attributen, wo sie hineingerutscht war. Die Stimmenzahl
  fällt weg, weil `rate` der bayessche Wert ist: er ist schon stimmengewichtet, ein Trail mit drei Stimmen
  kann keine 4,9 zeigen. Beides auf Anweisung des Nutzers, beides durch je einen Testfall festgenagelt.
- **Dem Kartenlabel fehlte das ⬆️ für Uphill-Trails** — Kachel und Info-Panel trugen es immer, das Label
  nicht. Dieselbe Lücke, die 2026-07-28 schon der Schwierigkeitspunkt im Label geschlossen hat.

## 2026-08-21
- **A trail card shows both numbers, always** — `⭐ 4,71 🔥 100`, independent of which axis the list is
  sorted by. It first shipped showing only the active axis, on a SCALED ESTIMATE that both together would
  leave ~8px on a phone; the user asked for both, and the real measurement backs them: at 375px the tightest
  of Finale's 219 cards has **39px of slack** and every card stays 52px tall. Scaling a desktop number down
  was the mistake, not the ambition. `.trail-meta-rating` still pins `line-height: 12px`, because an emoji's
  line box is taller than a text line and without it every card grew 52 → 55px — a card that resizes is what
  the `lists` suite forbids elsewhere. And worth recording how that nearly slipped past: the first check
  counted distinct element top edges to detect a wrap and read the 2px-higher emoji span as a second line.
  It never wrapped; measure the card's height instead.
- **Trail rating and popularity, Stufe 1, live in Finale.** 131 of its 219 trails now carry Trailforks'
  `rating_bayesian`, vote count and popularity score, matched onto our Outdooractive-sourced ids by
  `tools/match_trailforks.py`. Two new sort axes in the Trails list, a **"Nur Highlights"** switch that dims
  everything outside a region's own top fifth, a ★ on a highlight's map label, and a panel row reading
  `4,77 ★ (124 Stimmen · Stand 2026-08-23) Beliebtheit 95`. Three design points are the substance: the
  highlight cut is **per region** and never a fixed number of stars (a 4.3 in Finale and a 4.3 in the
  Pfälzerwald are different communities with sample sizes a factor of thirty apart); unrated trails get their
  **own heading** instead of sorting last as if they scored zero (88 of 219 in Finale, and the best-covered
  region there is); and the whole UI **hides itself** below 35 % coverage, measured as Finale 60 %, Madeira
  34 %, Pfälzerwald 0–3 %. Suite `tests/browser/rating.js`, 8 cases / 32 checks, three verified mutations.
  Building it surfaced three real bugs, all now pinned: `clearSolo()` restored a hardcoded 0.85 (wrong once
  there are two resting states — and the second bug that same constant has caused here); the highlight
  cut-offs were computed AFTER the layers, and a trail label is bound once at build time, so the dimming
  worked while the stars silently did not; and the panel printed the star twice. A fourth was found by the
  suite itself — the switch is persisted, so a session that left it on handed the next suite a map with 197
  dimmed lines, which now resets in `TM.baseline()` like the other map switches.
- **`docs/backlog.md` rebuilt to the user's own priorities (645 -> 324 lines).** Out, because finished
  rather than forgotten: all Touren rework, the remaining region items for Gardasee/Schwarzwald/Sauerland/
  Vogesen, and rebuilding the Saalbach loops. Moved to a new **Zurückgestellt** part, kept in full: the RIDE
  memory/crash work ("wir haben eine einfache Möglichkeit, es zu beheben und im Moment tritt es nicht auf")
  and the undecided RIDE feature ideas. Newly at the top: the **cloud/accounts/App-Store roadmap**, which had
  been living only in the assistant's local memory — the exact failure that file exists to prevent — and
  **Trailforks rating/popularity**. The per-region build history is no longer duplicated there (each region
  has its own doc); a status table replaces it.
- **`docs/trail-rating-konzept.md`**: concept for pulling Trailforks' per-trail rating and popularity in,
  requested for large regions where a difficulty colour alone does not say which twenty trails are worth the
  day. Written on measured data, not assumptions: all of `rating_bayesian`/`votes`/`popularity_score` are
  anonymously readable **on the trail page the harvester already fetches**, so it costs no extra request —
  while the region TABLE serves `data-rating="0"` for every trail and would have led straight to the wrong
  conclusion. The design turns on one measurement: across Madeira's 184 trails, **59 % have two votes or
  fewer** (median 2, max 17), so a raw star average is noise and the Bayesian value plus a visible vote count
  is the only honest presentation. Also fixed in the same pass: nothing colour-codes rating on the map (the
  line colour stays difficulty), and unrated trails get their own group instead of sorting last as if they
  were bad.
- **The Garda Touren's 21 segment gaps are closed.** `close_loop_gaps.py` routed all of them against OSM:
  20 Tier 1 (the bridge is built from the way the trail itself lies on), 1 Tier 3, route factors 1.00-1.73,
  none flagged suspicious. Every joint over 30 m is gone; what remains is at most 25 m, which is the
  threshold's own normal slop. `--no-wrap` was added for this and is the point worth remembering: the tool
  treated LAST->FIRST as a gap unconditionally, which is right for a ring and wrong for the 18 % of the
  app's Touren that are not one — on "Variante Caset Pubregn" (+230/−1080 m, start and finish genuinely
  5 853 m apart) it proposed a 5.9 km bridge across ground nobody rides. Its own default is unchanged.
- **Fixed: the Garda Touren's elevation charts drew one flat colour instead of their trail sections.** The
  segments were written without `distStart`/`distEnd`, and `buildInfoPanelHtml` skips any segment missing
  `distStart` — so the chart fell back to the Tour's own difficulty colour and showed no component trails.
  Invisible to everything automated: the concatenation invariant held, the region validated, the browser
  suites were green (the `infopanel` per-segment-colour case runs against Bike Kingdom, whose Touren have the
  fields). The user's own eye caught it. Ronda Extrema's chart now draws 14 polylines in 4 colours. The
  convention was checked against Donnersberg's stored numbers rather than guessed, `validate_region.py` now
  rejects a Tour whose segments lack the fields, and `regiondata` pins that with a mutation. Running the new
  check over every region also turned up **7 Touren in four other regions whose last segment ends 0,3–1,4 km
  early** — real but cosmetic, and recorded in `docs/backlog.md` rather than enforced, since failing four
  shipped regions would block every commit.
- **Five Garda Trentino Touren, and a measure for which tours are worth building.** Source is the
  destination's own MTB routes (`gardatrentino.it`), whose tracks come from Outdooractive and had to be
  harvested through a real browser again — that API answers 404 to every plain HTTP client. Nine are
  published; five are built. **The obvious measure was wrong and the user said why**: judging a tour by the
  trail share of its whole track made every one look like a fireroad loop, because with 4 200 m of climbing
  most of the distance IS the climb and a climb is a fireroad ("Uphill ist wohl immer Forststrasse" — the
  climbs here measure 30–72 % fireroad). What decides is the DESCENT, split by the track's own smoothed
  elevation and classified against OSM way types: Ronda Extrema 31,8 % of its 33 km descent on singletrail
  (10,5 km), Ronda Grande 27,2 %, against Monte Velo's **0,8 % of 11,8 km** — a gravel descent whose
  "schwer" grade comes from its climbing. Monte Velo, Lago di Ledro, Bio Palafitte and Duvredo Shortcut are
  left out with the reason recorded in the build script, so a rerun cannot add them back.
- **The map-matcher got a spatial prefilter, because 913 candidates broke it.** One 88 km tour against the
  Gardasee's 911 trails plus 2 lifts is ~860 million polyline projections per pass, and produced no output
  in three minutes. `_label_points` now measures a point only against candidates in its own grid
  neighbourhood. It changes no answer — the `gpxmatch` baseline, Livigno's hand-built 20/20 ground truth
  included, is unchanged, and the suite got faster (33 s → 25 s). Two thresholds (12/30 and the module's
  validated 15/35) also produce identical attribution on all five tours, so the validated pair was kept
  rather than an invented one.
- **`tools/oa_harvest_server.py` takes `--proj/--key/--out/--port` now**, instead of being hardcoded to Bike
  Kingdom. Worth knowing what it cost: the first version of that change updated the merge-READ to the new
  path and left the WRITE on the old module global, so a Garda harvest was silently merged into Bike
  Kingdom's own `oa_tours.json` — twice, since a stale server on the default port kept answering after the
  fix. Both times restored from git; the write path and a `--port` flag are the fix, and the comment on that
  line says why.
- **The Gardasee's and Madeira's sub-region labels were too long, measured and fixed.** Every chip sat on its
  own line — ten lines for the Gardasee alone — because the chip row is 279px on a phone, two chips only fit
  at ~136px each, and the count (" (155)") spends six of a label's characters. Labels are capped at 15
  characters now (`Riva/Torbole`, `Valle del Sarca`, `Monte Baldo`, `Funchal/Arieiro` …): five lines of two
  for the Gardasee, three for Madeira, with 13px of headroom on the worst pair — deliberately not tuned to
  the exact shortfall, since the first attempt kept `Verona/Lessinia` + `Trento/Bondone` at 137px each, i.e.
  280 against 279, and they wrapped. The full place list per hub moved into the two region docs, because the
  label is also the region dialog's search haystack and each one now keeps the name a rider would type.
- **The Malcesine–Monte Baldo cable car is in, both sections.** The user researched the summer bike transport
  themselves, which is the operator-side statement `docs/lifts-feature.md` requires (OSM's own
  `aerialway:bicycle=yes` agrees on both ways but never decides). Geometry from OSM, elevations from
  OpenTopoData, stored bottom-station-first: Malcesine 98→545 m and San Michele 550→1741 m, both in
  `gd_baldo`. **The restricted bike window (mornings and afternoons only) is deliberately NOT in the data** —
  the same call the user made when a per-lift `closed`/`note` pair was built and dropped: nothing here
  synchronises lift operating status, so a hardcoded timetable would rot while looking authoritative. It is
  written up in `docs/gardasee.md`.
- **Riva del Garda and Torbole are forced into the Gardasee's place labels** (`FORCE_PLACES` in
  `tools/add_region_places.py`), on the user's own instruction — they are the two best-known shuttle starts,
  and both were being dropped: Riva by `MIN_SEPARATION_KM` against Arco 3 km away, Torbole by its bracket's
  quota. Arco loses its label as a direct consequence of that separation rule; it is still in the region's own
  doc. **The namesake rule was also tightened in the same pass**: it matched any whole WORD inside a
  sub-region label, so shortening the labels to "Monte Baldo" and "Valle Sabbia" promoted the hamlets "Monte"
  and "Valle" (population 0 each) to namesakes — which sort first and are exempt from the separation rule, so
  two empty hamlets took slots from real towns. A namesake now has to match a whole label PART, or be a name
  that starts with one ("Riva" for "Riva del Garda"), which is also a cleaner fix for the bug the word rule
  was itself written for ("Au" matching inside "Bikepark Todtnau").
- **Two new regions, both Trailforks-only: Gardasee & Trentino (911 trails) and Madeira (158).** Source is
  Trailforks end to end — geometry from each trail page's `encodedpath` polyline, elevation from the same
  page's `ElevationChart` (so no elevation API at all; the two lengths cross-check and agreed within 60 m on
  every one of 1 153 pages), and the difficulty from Trailforks' own rating. That last part is a recorded
  exception to the "operator difficulty wins" rule, on the user's own instruction for both regions ("Rein
  Trailforks, keine Betreiber-Recherche"; for Madeira "Nimm alles von Trailforks. Hab auch keine andere Quelle
  da"). Neither region gets a `lifts` array: Madeira is a shuttle island, and the Garda's Malcesine cable car
  needs the operator's own summer page, which this scope excluded. See `docs/gardasee.md` and
  `docs/madeira.md` — including the Garda's scope decision (the widest of three offered, "bis Trento,
  Brescia, Valsugana"), what is deliberately excluded (the Dolomites north of Trento, since Dolomiti
  Paganella is its own region, plus Lago d'Iseo and the Val Camonica), and Madeira's levada question.
- **Two new repo-tracked tools replace ad-hoc harvest scripts.** `tools/harvest_trailforks.py` does both
  halves of a Trailforks harvest — the region trail tables *and* the per-trail pages — where the previous
  script only ever did the second and the first was hand-written and lost. Three source rules that are
  invisible in the HTML are pinned in it: the listing pages at 100 rows via `?page=N` with no pager markup,
  a region's table includes every descendant region's trails (but `madeira` is NOT an ancestor of
  `madeira-island`, so seeds are a list and get deduped), and `difficulty=` must name every code including
  10. `tools/build_trailforks_region.py` turns such a harvest into a region for any Trailforks-only region,
  with everything region-specific — anchors, sub-region labels, id prefix — as data in one `CONFIGS` dict.
- **Two data rules the Garda forced out into the open.** "Easiest / White Circle" is a SIXTH Trailforks
  difficulty tier the project had never met (78 trails here, absent from the Vogesen and the Schwarzwald);
  it maps to `gruen`, and a tier missing from that table is silent, so `tests/python/trailforks.py` now
  checks the mapping against every harvested table rather than a hand-written list. And paved cycle
  INFRASTRUCTURE now gets dropped by name: a municipal cycle path is not graded "Access Trail", it gets a
  real White Circle and sails through — 60 entries here, including Trento's whole urban "Bicipolitana"
  network and the three longest lines in the region (54/51/47 km of the Ciclovia dell'Adige).
- **A region can no longer silently lose its `trailSegments`.** `donnersberg.json` lost that whole key in a
  rebuild in commit `b881699` and nobody noticed for several commits — `validate_region.py` checks segment
  consistency when the key is present and says nothing about one that is gone. `tests/python/regiondata.py`
  now holds a committed per-region count that may only go up, with the reasoning for why the two obvious
  derived rules do not work (15 loops across 6 regions legitimately have no segments, and the geometric
  "this loop retraces its region's own trails" test flags 3 of those 15). Mutation-checked.
- **The fatal-error panel's copy and the vector focus ring are now pinned by tests**, both in
  `tests/python/appshell.py`: no platform-specific advice may appear in the static box (the iPhone tip the
  user had removed on 2026-08-04 would fail it, and on a home-screen PWA that panel cannot be dismissed),
  and `.leaflet-interactive:focus{outline:none}` must stay in `style.css` — without it a clicked trail
  paints a stray black rectangle around its own SVG bounding box.
- **Portugal was missing from the region dialog's country maps**, which Madeira was the first region to need.
  Neither map ever throws — every use falls back to `|| code` / `|| "🏳"` — so the row simply read "🏳 PT" and
  the dialog's search could not find Madeira under "Portugal". Added, with a `regions` case that reads the
  rendered headings and treats a bare two-letter code as the failure, so the next new country cannot ship the
  same way.
- **Two new test suites, and one that existed but could not fail.** `loopgaps` covers the offline half of
  `tools/close_loop_gaps.py` — the gap detection including the wrap-around boundary, all four `close_gap`
  branches plus the degenerate no-intermediate-points case that once left 16 of 29 gaps silently open while
  the report claimed a route factor of 1.00, the bicycle access rules (`vehicle=forestry` blocks, an explicit
  `bicycle=yes` overrides), and the routing graph. `gpxmatch` wires in `tools/test_gpx_map_match.py`, the
  matcher's ten-tour regression harness, which had been in the repo claimed by no suite and **always exited
  0** — it prints a comparison, and reading it was left to a human. It compares against a committed per-case
  baseline now and exits non-zero when a case regresses; its two absolute `D:\Trailmap` paths are derived,
  so it runs on another machine at all. Found by asking the runner which tracked files no suite claims — that
  sweep's leftovers are written up in `docs/backlog.md`.
- **Nine more cases across six existing suites**, each for a documented behaviour nothing was watching: the
  `safeMapStop` reentrancy guard behind the phone-reproduced RIDE crash, the RIDE toggle's cooldown,
  `applyRideMapOffset`'s idempotence, the RIDE speed readout's centring in both orientations, every text
  field being at least 16px (under that, iOS zooms the page on focus and never zooms back), the nine counts'
  non-breaking space, the sidebar's scroll-to-top button, a dimmed trail's arrows being dimmed FILL and all,
  the per-difficulty arrow tint, a connector's smaller hover delta, and the three "Straße" chips being one
  tile layer at three filter levels with dezent the default. All mutation-checked; `tests/MUTATIONS.md` has
  each mutation and the exact failure it produces.
- **`TM.paints()`, and the rule it encodes.** A window that is not being painted runs no animation frames, so
  neither a CSS transition nor Leaflet's animated pan progresses in it — and a case that measures the RESULT
  of one then fails against a correct app. The harness answers that question once now; the `controls` fold
  and `bearing`'s easing case ask it, and the scroll-to-top case asserts the requested scroll rather than its
  arrival.
- **Three `bearing` cases that had been lying were fixed, and with them the "flaky suite" reports.** The
  worst was a real defect rather than flake: the direction-arrow case dereferenced a `find()` result after
  turning the map, threw `Cannot read properties of undefined` on roughly every other run, and that throw
  **aborted the whole suite** — taking six cases with it and leaving the map mid-turn for whichever suite ran
  next, which is what the `controls` and `infopanel` "flakes" actually were. The arrow-size case was
  measuring the wrong quantity entirely (a trail's arrows are sub-rings of ONE polygon, so the element's
  bbox is the extent of the whole trail — 509 px against a 15 px triangle); it parses the first ring out of
  the `d` attribute now and zooms with `setZoomAround` so the arrow it just measured cannot leave the view.
  And the hit-testing case skipped silently whenever an animated fly had not arrived, which is always in an
  environment with no animation frames; it now zooms out until its own probe has a point on screen.
- **A `bearing` case was asserting something that cannot be true.** "centring survives a container whose
  size Leaflet has not noticed yet" fabricated the stale size by writing to `map._size` — and under THAT
  state `invalidateSize`'s compensation moves the pixels while Leaflet's own `getCenter()` stays put, so the
  panTo that follows has nothing left to correct and the dot legitimately ends up off centre. Measured, not
  reasoned about. It asserts the repair now (the size is back, the pill reports it) and leaves "the position
  ends up centred" to the second half of the same case, which changes the container for real.
- **The ⬆️ and 🔁 badges can no longer be separated from the trail's name.** An ordinary space in front of them
  is a break opportunity, so a long name could break right before the badge and leave it starting the next
  line — where the only other thing is the button group, making it read as belonging to the buttons rather
  than the trail (user: they must "nie zu den Buttons in die Zeile rutschen"). Both now use a NON-BREAKING
  space, the same fix the nine counts elsewhere already use. **Reproduced before and after rather than
  reasoned about**, and that took a sweep: at the desktop panel's own 345px NONE of Bike Kingdom's thirteen
  badge-bearing trails showed it, so a check at that width would have passed against the broken build. Swept
  across 220–440px, two do — "Aufstieg Mittelstation Weisshorn" at 310px and "Access Spundis/Lady Patricia"
  at 266px — and with the fix, zero at any width in that range. The new case in `tests/browser/infopanel.js`
  sweeps for the same reason.
- **Two test defects fixed in the same area, both of which had been reporting the wrong thing for a while.**
  "the glyph buttons grow on touch" read the height out of the touch media query, which stopped restating it
  when desktop was pulled up to match — it now reads the base rule and asserts what actually matters, that
  they are a full touch target on every layout. And "it sits behind the name where the name leaves room" took
  `h3.firstChild` as the name, which has been the difficulty DOT since 2026-08-13 — an element, so
  `.length` was undefined, the Range was empty and the check had been reporting 0 ever since, for a reason
  with nothing to do with the layout it is about. It takes the first real text node now, and passes.
- **The info panel's four action buttons are 34px on the desktop too**, not 22 (user: "die grösseren Buttons
  können wir am Desktop nachziehen"). The size was touch-only, where the reason was the touch target; desktop
  does not need a bigger target but does need the two layouts to look like the same panel, and 22px round
  buttons read as an afterthought beside a 345px panel. **The point of the change is that a rule disappeared,
  not that one was added**: the touch block's copy of the sizing is gone, so there is one definition instead
  of two that had to be kept in step. Measured afterwards on the desktop panel: short names keep a one-line
  heading (41px), the fourteen longest push the button group whole onto a second line (57px) — which is
  exactly what `.ip-btns` being an atomic `inline-flex` box was chosen for, and never a name broken mid-way.
  Stylesheet bumped to v183 in all three places.
- **The direction arrows are filled with a light tint of the trail's own difficulty colour**, not one fixed
  white (user). That restores the difficulty cue the previous day's redesign had given up, in the one form
  that keeps the contrast the dark edge provides. The tints are the SAME set already used by the
  Satellit/Relief halo and RIDE's middle ring — one constant, `DIFF_TINT`, three users, because they answer
  the same question. No per-basemap palette entry is needed for the same reason white needed none: a pale
  fill inside a near-black outline reads on every basemap we ship.
- **Fixed: clicking a trail painted its own line straight through its arrows, and it never went away.**
  `highlightSelectedTrail` brings the selected line to the front so it sits above its neighbours, which since
  the arrows moved onto the line also puts it above them — a coloured stripe across every arrow of the trail
  you just tapped, permanent because nothing ever re-ordered them back. Fixed by re-fronting that trail's own
  arrow layer immediately after, the same one-line counter the RIDE arrows already had. **Deliberately not a
  new pane**, which the user also asked about: a pane costs a whole renderer surface — measured at ~40 MB on
  a phone for the empty builder pane — while moving one node inside the pane that already exists costs
  nothing. Mutation-checked in `tests/browser/lists.js`: without the re-front the line lands at DOM index 654
  against the arrows' 653, and nothing about the arrows' own attributes changes, so only the pane order can
  see it.
- **The Schwarzwald's two problem Touren are assembled from the Tourenbuilder now, not matched**
  (`tools/build_schwarzwald_builder_tours.py`, new). Canadian & Borderline is 19,30 km with 84 % of it on
  named trails, Hubbelfuchs · Kammweg · Borderline 40,05 km with 83 % — against 55 % and 79 % when
  matched, and neither has a gap over 30 m left (largest 29 m and 21 m). The ride order comes from the
  app's own builder (`Material/Schwarzwald/builder_*.json`, checked in), each named stretch is that
  trail's own geometry clipped to the points the builder cut it at, and the long connectors are **read out
  of the original recording** rather than routed — 2 770 m, 1 540 m and 3 702 m of it. Two things that
  took a second pass: picking the right PASS of the recording (a loop comes past the same place up to four
  times, and nearest-point-to-nearest-point returned 10,4 km of track for a 2,3 km gap), and orienting a
  stretch's heights together with its geometry instead of separately. What the recording does not cover
  went to `nearby_trail_connector.py` as before — including, as the one exception to the GPX-first rule,
  the 875 m between Fritzis Ende and Baden To The Bone Uphill, where the recording never comes within 60 m
  of the uphill's start as the builder set it.
- **`build_schwarzwald_tours.py` no longer builds those two**, so a rebuild cannot quietly overwrite the
  hand-assembled versions; their recordings are still harvested there, because that is where the
  builder-tour script reads its connectors from. The full order is now four scripts plus the version
  manifest — written out in `docs/schwarzwald.md`.
- Note on the previous entry's commit: `c8f01ad` carries a stray `@` as its subject line, from a
  shell heredoc quoting mistake. Left as is on the user's instruction rather than force-pushed away.
## 2026-08-20
- **The normal-mode direction arrows moved ONTO the line: filled white triangles with a dark edge, the same
  design RIDE uses, one size smaller.** This reverses the 2026-08-05 design knowingly — that one put a thin
  chevron 9 px to the SIDE, at the user's own request, modelled on OSM. What killed it is a case it never
  accounted for: two trails running parallel a dozen pixels apart, which a bike park is full of. A 9 px offset
  then lands the red trail's arrow on the blue trail's line, so it does not just look untidy, it points at the
  wrong trail ("das ist manchmal verwirrend"). Four alternatives were mocked up with `visualize` first —
  including a filled arrow in the trail's own colour and a chevron cut into a locally thickened line — and the
  user picked the RIDE-consistent one. **What it gives up**: arrows are no longer coloured per difficulty. On
  the line that cue is largely redundant (position already says whose arrow it is), and white-with-a-dark-edge
  is the one combination needing no per-basemap palette entry, so `repaintLineColors` lost its arrow branch
  entirely. `buildDirectionArrowLayer` is an `L.polygon` now — the three points close into a triangle once the
  side offset is zero, so the geometry needed no new code, and it is still one node per trail. Two knock-ons
  worth knowing: solo dimming had to learn `fillOpacity` (dimming only the stroke left a soloed-out trail's
  arrows glowing white), and the RIDE arrows took a slightly heavier edge (1.6 against 1.2) — right for a
  bigger shape anyway, and now the only attribute that tells the two apart in the DOM, which three test
  helpers needed. `geometry`'s chevron case asserts the shape STRADDLES its anchor instead of sitting beside
  it; the old check would have passed unchanged for the wrong reason, so it was replaced rather than relaxed.
- **The Schwarzwald's Touren now ride their trails' own geometry, not the recording's.** The Tour segments
  were built with `fill_connectors`, i.e. each named stretch kept the recorded track — so two Tours riding
  Borderline each drew their own slightly different Borderline and none of them matched the trail. The user
  found it by eye; measured, 0 of 35 named segments lay on their trail (mean median offset 4,1 m, 11 over
  5 m). They are built with `build_segments` now and all 35 measure 0,0 m, with the gaps that snapping
  opens closed by `nearby_trail_connector.py` as before. **Note for the next audit of this kind: a
  point-for-point "exact slice" test is the wrong measure** — it reported Bike Kingdom, Laax, Paganella
  and Portes du Soleil as 0 % when in fact the only points off the trail's own list are the two
  interpolated clip endpoints and every line coincides (the user's spot check was right and the metric was
  wrong). Measure the distance.
- **Two of the four Tours are provisional and will be rebuilt in the Tourenbuilder** (the user's call):
  Canadian & Borderline still jumps 582 m and runs 12 % over its recorded track, Hubbelfuchs · Kammweg ·
  Borderline jumps 401 m, both because the matcher extends a stretch to the trail's real end where the
  recording had already turned off. Not tuned and not hand-patched, on instruction.
- **Start and Ziel merge into one two-colour marker exactly when they would overlap on screen.** Where a Tour
  ends on its own start, the red Ziel simply won by draw order and the green Start was gone — worse since the
  markers grew for RIDE, and more common since closing the loop gaps made tours actually end where they begin.
  **Measured across every region first, because the obvious rules are both wrong**: of 97 Touren, **52 % have
  bit-identical first and last coordinates** (they never separate at any zoom), ~25 % more are within 25 m, and
  **18 % are not loops at all** — the Sölden descents and the two Pfälzerwald passages start over a kilometre
  from where they end. So `loop` cannot decide it, and neither can a distance in metres: 25 m is 64 px apart at
  z18 (two clearly separate markers) and invisible at z13 (100 m still overlaps). The rule is the SCREEN
  distance — two circles of radius r collide below 2r — re-evaluated on `zoomend`, since the merged form is a
  property of the view, not of the trail. Merged, the green shrinks and comes to the front, reading as a dot
  inside the red disc, and its tooltip says "Start / Ziel" (or "Talstation / Bergstation", since a short lift
  can collide too). Verified live: the bit-identical Tour stays merged at z13–z19, and a Tour whose ends are
  44 m apart is merged at 4 px and 7 px apart (z13, z14) and separate from 13 px (z15) — the crossover landing
  exactly at the 10 px the rule predicts.
- **Start and Ziel are drawn at radius 9 instead of 5 while riding**, with a heavier outline, after the user
  reported they nearly vanish at arm's length inside the 18px focus ring. `applyEndpointSize` is called by
  `showEndpoints` for the pair being added, and `syncEndpointSizes` resizes whatever is already on the map
  when RIDE is entered or left (including from the crash-recovery path). Applies to a lift's
  Tal-/Bergstation too, since both registries store the same marker pair.
- **A trail reversed before entering RIDE now has a test proving its arrows turn around.** They already did —
  `latLngAtDistance` measures from the end when `reversed`, so the sign falls out of the shared helper — but
  RIDE builds its own shapes, so nothing else would have noticed if the flag stopped being threaded through.
  Measured directly: the direction flips to a dot product of exactly −1.0000. **Three earlier versions of
  this case skipped themselves** rather than failing, each for a different real reason (no trail in view
  because `enterRideMode` re-centres on the tracked position; the forward and reversed grids sit a constant
  100px apart, being anchored to km 0 of the line and of the reversed line; and the visible stretch bending
  too much for any direction comparison). The version that stands calls `buildRideArrowShapes` directly on a
  synthetic straight line laid across the current view, where the answer is exact and needs nothing to
  cooperate, plus one integration check that the reversed run's shapes actually differ from the forward run's
  — which is what proves `reversedId` reaches the layer at all.
- **The focused trail's RIDE arrows are now derived from the visible stretch, so there are always a couple on
  screen instead of usually none.** The normal arrows sample the WHOLE trail every 300 m and cap at 40 — on a
  90 km tour that is one every 2.25 km, so a screen showing 300 m of it shows none at all. That, not the size,
  is why they read as useless while riding (user, 2026-08-20). **What the zoom controls is the SPACING, never
  the position**: arrows sit on a grid anchored at km 0 of the trail, so each keeps its place on the ground and
  glides past like a signpost, and only which grid points fall in view changes as the map pans. The first idea
  — put one in the middle of what is visible — was wrong for exactly that reason and is recorded as such: it
  gives an arrow no fixed home, so it is recomputed and jumps on every pan. `RIDE_ARROW_SPACING_PX` is 400,
  tuned against measured counts (a long Tour gives 5/4/1 at z15/16/17, a single trail 1–2 throughout).
  Bounded work per update: one linear pass over the coords finds which stretch is on screen, the grid is then
  walked over that range only, and the cumulative-distance array is cached per trail. Re-derived on `moveend`
  as well as `zoomend`, since panning is what changes the visible stretch while riding. New mutation-checked
  case in `tests/browser/ride.js` (15 cases now) whose pan check is the only one that can tell the two designs
  apart — the arrow COUNT is identical either way. Out-and-back stretches still show both directions; that
  needs the progress cursor and is deliberately left for later.
- **The Schwarzwald's four Touren have their segment gaps closed**, with `tools/nearby_trail_connector.py`
  — the user's own confirmed procedure, not `close_loop_gaps.py`'s tier system. All 34 gaps over 30 m
  solved (31 "ein Weg erreicht beide Seiten", 2 "Weg folgen und kappen", 1 chain of ways), every applied
  bridge at **weglos 0 m**, i.e. entirely on OSM ways; what remains is the 10–29 m band that procedure
  leaves alone as GPS noise. Two fixes fell out of it. **`nearby_trail_connector.py` left the Tour's own
  `len`/`up`/`down` untouched** while inserting bridges into its line, so the info panel kept stating the
  pre-closure figures (Canadian & Borderline wrote 22,18 km and claimed 21,35); it now updates them from
  the written line. And **`close_loop_gaps.py` was making one Overpass query per gap** — the user spotted
  it from the runtime alone — so it now prefetches once per loop; note that
  `nearby_trail_connector.prefetch_gaps()` had had a better version of this all along (one query, one
  small box per gap), which is exactly what should have been reused instead.
- **The RIDE zoom restriction is gone again, at the user's request**, hours after it went in: the crash it was
  meant to stop came back with the map zoomed far IN, so the guard was treating one route to the cliff rather
  than the cliff. With 40 MB of the real cause removed (the empty builder pane), the user would rather have
  the zoom back and find out whether the remaining 86 MB is enough. If a white screen returns, do NOT simply
  reinstate it — the honest next steps are the lift pane and `rotationPadding()`, both quantified in
  `docs/backlog.md`. **Note for next time: this could not be reverted.** A `git revert` of the guard's commit
  conflicts on all six of its files, because two later commits touched the same regions — and it would also
  have deleted the measurements that commit recorded, which are still valid; only the conclusion drawn from
  them was wrong. A change that might be reversed belongs in its own commit, separate from the findings that
  motivated it.
- **The uphill badge was missing from a Tour's per-segment block in the info panel.** An uphill component trail
  carries the ⬆️ on its sidebar card, its map label and the panel's own heading; `.ip-segment-info` was the one
  place that printed a bare name (user, 2026-08-20). Two new checks in `tests/browser/infopanel.js`, including
  a negative one (a lift stretch must not get a badge) so the positive one cannot pass on a badge printed
  unconditionally.
- **The empty builder pane no longer costs 40 MB in RIDE (126 MB → 86 MB of vector surface, no visual
  change).** Found while diagnosing a SECOND white-screen crash the user hit — this time zoomed far IN, in
  Donnersberg — which disproved part of the earlier diagnosis: the direction of the zoom was never the driver,
  so the `RIDE_MIN_ZOOM` guard had only blocked one route to the same cliff. Re-measured properly at a real
  phone viewport: RIDE + rotation carries **33 Mpx / 126 MB across four renderer panes**, against 3.6 Mpx /
  14 MB north-up — a factor of 9, not the 2.3 reported earlier (that measurement used three panes and a
  container that had not reached full RIDE height). **Tiles are not involved at all**, contrary to the earlier
  entry: 20 tiles without RIDE against 25 with, one level, JS heap 12–14 MB, whichever way you zoom. Leaflet
  prunes correctly. What kills the tab is the baseline surface plus the re-cut every zoom step forces, which
  briefly holds the old and new surfaces at once. The first 40 MB of it came off for free: `eachVectorRenderer`
  named the builder pane in a hardcoded list, and `map.getRenderer()` CREATES a renderer for a pane that has
  none rather than just looking one up — so asking in order to pad it is what allocated a full-size SVG for a
  pane holding nothing. It is now asked about only once it already has a renderer. In Donnersberg the picture
  was worse still: with no lifts in the region, TWO of the three big surfaces were completely empty. New
  mutation-checked case in `tests/browser/ride.js` (14 cases now).
- **The Schwarzwald gets four Touren, and Todtnau's Downhill changes source.**
  `tools/build_schwarzwald_tours.py` (new, runs AFTER the trail build, which would otherwise overwrite
  its `trailSegments`) builds Trailrunden from Trailforks' own recorded **routes** for the Freiburg area:
  Canadian & Borderline (21,4 km), Hubbelfuchs · Kammweg · Borderline (40,0), Schlossberg · Nesselplatz ·
  Rosskopf (29,2) and Freiburger Dreierlei (35,4), matched against the region's own trails and lifts with
  `tools/gpx_map_match.py`. A fifth, "Banden Ride", is deliberately NOT built: its recording jumps 2 593 m
  in one step -- 6,9 % of the Tour, drawn as a straight line across Freiburg -- which is the same reason
  three Paganella marathon routes were left out of that region. **The Tour the user asked for does not exist as a
  Tour**: Trailforks' "Multi Trail" on "Schauinsland Enduro" means multi-USE, not "assembled from several
  trails" — it is a plain 2,8 km descent and the district sweep already built it as one. Three findings
  worth keeping: a **route page renders its ElevationChart config twice**, so every parsed line came out
  at exactly twice its stated distance with every segment list doubled (an exact
  first-half-equals-second-half test cuts it; trail pages do not do this); **snapping named stretches
  onto their trail's own geometry was measured and rejected** here, because it opened joints of up to
  746 m and inflated two Tours past their stated distance, so the segments keep the recording's own
  points and every Tour now matches Trailforks' distance to within 100 m; and **direction settles what
  distance cannot** — on the Rosskopf the club's uphill route runs beside the trail it serves, so the
  matcher alternated between "Borderline" and "Borderline Uphill" down the whole descent, and tightening
  the threshold from 12 m to 8 and 6 m fixed nothing while lowering how much got named. Rejecting an
  attribution to an `uphill: true` trail on a stretch that loses height removed exactly the wrong labels.
- **Todtnau: the OSM-sourced "Downhill" is gone; the Trailforks `bikepark-todtnau-racetrack` carries the
  name** (and keeps the id `sw_todtnau_downhill`), on the user's own call — the sweep had built it as a
  second trail beside the OSM copy. The duplicate check had not caught the pair because the two lines
  trace the same corridor but each covers 100–200 m the other does not, at opposite ends, which the
  "subsumed" shape test is deliberately strict about. The region is 622 trails now.
- **The focused trail's direction arrows during RIDE are filled white triangles on the centreline now, instead
  of the thin chevrons beside it.** The report (user): "durch die dickere Linie wird der komplett verdeckt und
  die Pfeilchen sind eh zu klein und dünn" — and it was not a near miss: `ARROW_OFFSET_PX` is 9 and the RIDE
  focus ring is 18px wide, i.e. reaches exactly 9px from the centreline, so the chevron sat precisely on the
  ring's outer edge. Five variants were mocked up with the `visualize` tool first (per the user's standing
  preference) and the user picked the filled-triangle one: rather than push the arrow further OUT, put it
  INSIDE the ring, where the ring's own orange is the contrast and no space has to be negotiated with
  neighbouring trails. **The geometry needed no new code** — `buildChevron`'s three points (back-left, tip,
  back-right) ARE a triangle once the side offset is zero, so this is the same sampling loop with a second
  size spec (`RIDE_ARROW_SPEC`) and `L.polygon` instead of `L.polyline`. Only the focused trail is affected;
  every other trail keeps its normal chevrons, and the focused trail's own are suppressed while the ring is up
  (measured: 61 → 53 chevron shapes on the map, replaced by 8 triangles). **Performance was measured before
  choosing between the variants**, since RIDE is where this app already hit a memory ceiling: with 15,385
  chevrons force-added — ~10x a realistic load — one renderer pass cost 4.0ms with nothing, 11.7ms as 3.4px
  strokes and 9.9ms as filled polygons, i.e. filling is CHEAPER than a wide stroke at this size. The count is
  what matters, and this layer only ever exists for one trail. Two mutation-checked checks in
  `tests/browser/ride.js` (13 cases now), one of which pins a z-order bug found by measurement:
  `highlightSelectedTrail` fronts the selected line AFTER the halo is built, so without a counter-call the
  trail's own line paints a stripe through every triangle.
- **Schwarzwald, second pass: the Trailforks sweep takes it from 119 trails to 619, and from 7
  sub-regions to 10.** `tools/harvest_schwarzwald_tf.py` (new) harvests the trail table of every
  Schwarzwald district and then one page per trail; `tools/build_schwarzwald.py` integrates them.
  Geometry AND elevation come from the trail page itself — Trailforks embeds an `ElevationChart` whose
  points carry lat/lng, real height and cumulative distance, so the sweep needed **no elevation API at
  all**, and the page's second copy of the line (the `encodedpath` polyline) cross-checks it: all 602
  pairs agree within 60 m. Anonymous curl worked for ~700 pages (urllib gets a 403 with the same
  User-Agent — use curl). Two traps worth carrying forward: the `ElevationChart` points come with
  **quoted** lat/lng, and an unquoted-number regex silently yields no profile at all; and the table URL's
  `difficulty=` list must name code 10 or the whole black tier vanishes (the third region to hit that).
  **A district is not a massif**, so nothing trusts the district it came from: every trail is assigned to
  the sub-region of the nearest of 103 **anchor towns** (`tools/schwarzwald_anchors.py`) and anything
  further than 12 km from all of them is dropped as not-Schwarzwald — one rule that assigns and excludes
  at once, and prints all 30 exclusions (the Kraichgau/Stromberg cluster, two Rhine-plain trails, three
  isolated ones). Duplicates are dropped twice over: by name **within 5 km only** (there are three
  separate "Jägerpfad"s and two "Kammweg"s in these tables — matching on the name alone dropped the far
  ones as duplicates of the near one) and by the project's containment metric; 40 and 36 respectively,
  with the already-built trail always winning. The old "Südschwarzwald" bracket is gone, split into
  `markgraefler` and `hochschwarzwald`, and `ortenau` plus `enztal` are new — each of those is bigger
  than the whole region was before the sweep.
- **Two more lifts, and two rejected on the operator's word.** In: the **Schauinslandbahn** (its own
  Biking page states the bike fare, and it is the uplift for Badish Moon Rising and the Canadian) and the
  **Feldbergbahn** (the Liftverbund's summer page: 8-seat cabins with room for a bike). Out: the
  **Belchen-Seilbahn**, which is exactly what the operator-decides rule is for — OSM tags it
  `aerialway:bicycle=yes` and the operator's price list has no bike fare at all; and Bad Wildbad's
  **Sommerbergbahn**, whose bike days belonged to the bikepark. **Bikepark Bad Wildbad's operator ceased
  on 2025-12-31**: its six runs are in the region (they exist, Trailforks holds the lines) but with
  Trailforks grades and no lift.
- **`tools/add_region_places.py`: the Schwarzwald joins the two Vogesen regions on the 18-label cap** —
  it now spans Lörrach to Pforzheim, where the default 10 left whole brackets anonymous. 18 labels, one
  to three per bracket.
- **RIDE mode no longer lets the map zoom out past z10 (`RIDE_MIN_ZOOM`), because doing so reliably killed the
  app on the user's phone.** Reported as "weiße Seite / lädt sich neu", which is the tell that matters: a
  thrown error shows the fatal panel, so a white page is iOS killing the WebKit content process for memory —
  nothing throws and no stack trace survives. Measured cause, on a 375x812 viewport at a fixed 45° bearing:
  RIDE's look-ahead makes `#map` ~30% taller than the visible window, which makes the container more elongated
  (2.02 → 2.65); `rotationPadding()`'s short-axis rule then grows faster than the container does — padding
  0.646 → 0.938, painted box 1835² → 2786², i.e. **~38 MB → ~89 MB** of vector backing store across the three
  renderer panes, before a tile is loaded. Zooming far out lands a burst on that inflated baseline: several
  tile levels crossed in one gesture, and under rotation the tile bounds are the rotated hull of the container
  (~2.5x its own area at 45°). Sölden was active when it happened — 38 trails, so the DATA volume is not the
  driver, the surfaces are. `setMinZoom` is the lever rather than a guard of our own: leaflet-rotate's pinch
  handler already runs `_limitZoom` on both its branches, as do scrollWheelZoom and every programmatic
  setZoom, so one call covers every way a rider can zoom out — and Leaflet clamps the current zoom too, so
  entering RIDE while already zoomed out corrects itself. Restored on exit AND in `recoverFromRotationCrash`'s
  own RIDE teardown. **The alternative fix — capping `rotationPadding()` — was offered and deliberately not
  taken**: that padding exists because the same user reported the rotation stutter, and capping it would trade
  their own fix back for memory. The 2.3x overhead is recorded in `docs/backlog.md` instead, since it will
  matter again for a bigger region. New mutation-checked case in `tests/browser/ride.js` (12 cases now). **Confirmed by the user on their own
  phone the same day: "Stürzt nicht mehr ab"** — which is the only proof available for this one, since a memory
  kill throws nothing there is no failing test to turn green.
- **New region: Schwarzwald — 119 trails, 1 lift, 7 sub-regions, live.** `regions/schwarzwald.json` plus
  `tools/build_schwarzwald.py` and the `REGION_CATALOG` entry. The data was built first with `index.html`
  deliberately left untouched (another session was editing it) — hence the build script PRINTS its catalog
  entry rather than patching the file, which is worth keeping for the next region built under the same
  condition. Sources: **Mountainbike Freiburg e.V.**'s own per-trail GPX *and*
  its own difficulty colours (a `window.mtb_trails` blob on `mountainbike-freiburg.com`, 23 GPX mirrored
  under `Material/Schwarzwald/`) — operator-wins, which changed six grades away from Trailguide's;
  **Trailguide's own anonymous JSON API** (`/a?query={"action":"trails.get.query","tracks":true,
  "cropTrack":true,...}`, 108 trails with real per-point elevation — `cropTrack` is what stops a trail
  recorded inside a longer ride from arriving with that whole ride's geometry); **Trailforks' anonymous
  `encodedpath`** for the club's association-only trails and for Bikepark Todtnau; and **OSM Overpass**
  for Todtnau's Downhill plus the Hasenhorn chairlift and the place labels. `mtbfr` ("Mountainbike
  Freiburg e.V.") is an organisational bracket among six geographic ones, on the user's own call. Not
  built, deliberately: Todtnau's "Downhill Flow" (no geometry in any source), Trailforks' "Schauinsland
  Enduro" (a multi-trail route — a Tour candidate, and the region has no Touren yet), and four
  same-line-two-names duplicates (Shooter = Schöni, Hirzberg Highway = K-Trail, and two contained
  fragments). Todtnau's two runs are 40 % shorter than the operator's stated distance in every available
  source — the Braunlage-Freeride precedent, recorded rather than papered over. Full account, including
  the three overlapping pairs left in on purpose: `docs/schwarzwald.md`.
- **`tools/add_region_places.py`: a sub-region namesake is now matched as a WHOLE WORD.** "Au" (1 335
  inhabitants) counted as a Schwarzwald namesake because "au" is the tail of "Bikepark Todtnau" — and a
  namesake both sorts first and is exempt from the 8 km separation rule, so it took the Freiburg bracket's
  slot and then knocked out Freiburg itself, a city of 230 000. No shipped region's list changes until one
  is deliberately rebuilt with `--force`.
- **Fixed both open RIDE-era bugs from 2026-08-16, neither of which was actually RIDE-specific.** (1) *A
  selected trail's Start marker read white instead of green.* The white `startDot` and the green `startMarker`
  sit at the EXACT same coordinate with the same radius, so whichever was added to the map last covers the
  other -- and `showEndpoints()` brings the green pair to the front once, while `updateStartDotVisibility()`
  re-adds the white dot on every zoomend. During RIDE the map zooms and pans constantly, which is why it
  looked like a RIDE bug; the Ziel marker has no white counterpart, which is why only the Start was wrong.
  Fixed by removing the overlap rather than re-fighting the z-order: a new `syncStartDot(layer)` is now the one
  place a startDot's visibility is decided, and it suppresses the dot while that trail's own endpoints are
  showing. All three former add/remove sites (`updateStartDotVisibility`, `render()`'s visible branch,
  `showEndpoints`/`hideEndpoints`) go through it, so a call site cannot reintroduce the overlap by forgetting
  the rule -- which is exactly how it got in. (2) *A trail selected from the sidebar list wore the bold hover
  width on top of its yellow selection outline on a touch device.* A tap synthesises a `mouseenter`, and the
  card's hover handler could not tell that from a real one. Both list call sites now go through one
  `wireCardHover()` using `pointerenter`/`pointerleave` and skipping `pointerType === "touch"` -- read off the
  GESTURE rather than from a `(hover: hover)` media query, so a hybrid laptop keeps its real mouse hover and
  loses only the tap-synthesised one. Two new cases in `tests/browser/lists.js`, both mutation-checked (see
  `tests/MUTATIONS.md`); `labels`/`lifts`/`solo` dispatch PointerEvents on cards now, since a MouseEvent
  reaches nothing. Full browser run afterwards: 147/151, the four remaining failures all pre-existing (two in
  `bearing`, one in `infopanel`, plus one `infopanel` marker check that only fails as collateral of the
  `bearing` throw in the same run).
- **RIDE ist in der Infobox jetzt ein eigener, beschrifteter Balken; die Glyph-Buttons wachsen auf dem Handy
  auf 34px.** RIDE war bisher der letzte und kleinste Knopf (22px) in `.ip-btns` — auf genau dem Layout, auf
  dem er der wichtigste ist. Vier Entwuerfe wurden vorab als Mockup gezeigt, der Nutzer hat B gewaehlt:
  `.ip-ride-bar`, volle Panelbreite, 48px hoch (44px in `landscape-compact`), amber, mit Wort statt Glyphe.
  Bleibt touch-only wie der ersetzte Button — **am Desktop aendert sich nichts**. Das touch-`max-height` des
  Panels waechst von `min(38vh,300px)` auf `min(48vh,370px)` (gemessen: normaler Trail 209px, hoechste Tour
  276px auf 375x812, nichts scrollt). Neuer Testfall in `tests/browser/infopanel.js`, per Mutation geprueft.
- **Bremberg-Loop geschlossen: ein paralleler Waldweg ist kein Nachfahren.** Der Nutzer hat den Waldweg auf
  der Karte gesehen; das Verfahren hatte ihn gefunden (254m Bruecke fuer 253m Luecke, Faktor 1,0) und wegen
  angeblich 142m doppelt verworfen. Nachgemessen trennen sich die Faelle am ABSTAND: dort liegt die Bruecke
  zu 10-20+m neben der Trail-Linie und nichts unter 10m, bei einem echten Nachfahren liegen 59 von 73m unter
  5m. Das Doppelt-Mass hat jetzt eine eigene engere Toleranz (DOUBLE_NEAR_M = 10). Nebeneffekt: Kurztour 3
  Schopp braucht eine Lockerung und eine Kappung weniger.
- **"Crest la Siala Tour": ein 381-m-Sporn INNERHALB eines Abschnitts behoben.** Die Naht ist 0,0m, es war
  also keine Luecke -- "Crest la Siala" endet zwischen zwei Stuetzpunkten von "Plaun Larisch", und der
  Abschnitt sprang erst 191m zurueck, bevor er vorwaerts lief. Drei Suchlaeufe fuer denselben Fehler wurden
  gebaut und ALLE verworfen (23, 221 und 80 Treffer, jeder dominiert von legitimer Geometrie wie duenn
  abgetasteten Serpentinen) -- deshalb nur die gemeldete Stelle angefasst, mit vier unbestaetigten Kandidaten
  in Paganella notiert. Siehe docs/nearby-trail-connector.md.
- **Alle uebrigen Regionen geschlossen: 190 von 217 Luecken (88 %)** in Odenwald, Sauerland, Waldmeister,
  Bike Circus, Naheland, Donnersberg, Livigno, Soelden und Bike Kingdom -- ohne Einzelfall-Vorlage, weil das
  Verfahren inzwischen traegt. Im ganzen Stapel gibt es EINE Kappung ueber 15 %. Die beiden
  Tourenbuilder-Touren ("THE CHALLENGE", "BIG-5") waren absichtlich mit offenen Luecken angelegt und sind
  jetzt lueckenlos, mit 1-2 % Kappung. Zwei Sachbefunde: drei Soelden-Touren sind PUNKT-ZU-PUNKT (liftbediente
  Abfahrten, 1,9-6,2 km zwischen Anfang und Ende), korrekt als Strecke gemeldet; und zwei entartete
  Ein-Punkt-Verbinder im Odenwald (MIL1 seg14, GH1 seg8) liessen Fall 0 mit einem TypeError abstuerzen, weil
  `project_onto_way` ueber die Kanten laeuft und bei einem einzigen Punkt None liefert -- jetzt abgefangen.
  `validate_region.py` prueft solche Segmente bisher nicht.
- **Tour 8 Annweiler: eine Stelle per Handeingriff gekappt, weil keine Regel die Gruppen trennt.** Der Nutzer
  wollte an `seg25` gekappt haben; die Zahlen waren 84m Bruecke mit 31m doppelt und ohne Kappung (Fall 1) gegen
  27m Bruecke mit 8m doppelt und 52m Kappung (Fall 2). Drei Verallgemeinerungen sind an echten Zahlen
  gescheitert (Doppelt-Mass vor die Fallnummer: 8 unbeanstandete Stellen kippen; doppelt an der Luecke gemessen:
  13; doppelt als Anteil an der Bruecke: unbrauchbar, weil bei kurzen Bruecken ohnehin fast alles neben der
  Trail-Linie liegt -- 564 von 1023 laegen ueber 20 %). Deshalb `NTC_PREFER`, ein benannter Eingriff fuer eine
  einzelne Luecke, im Report als [HANDEINGRIFF] sichtbar.
- **Die 25 uebrigen Pfaelzerwald-Trailrunden geschlossen: 683 von 705 Luecken, 97 %** (Tour 1-20 plus die
  fuenf Community-Runden). Die 22 verbleibenden sind nach Grund aufgeschluesselt, weil das die Konsequenz
  bestimmt: 10 unverhaeltnismaessig (Kandidaten da, alle zu teuer), 9 weglos ueber Toleranz und 4 ohne jeden
  Kandidaten -- die letzten 13 sind fehlende OSM-Daten, kein Werkzeugfehler. Die "Haardt Runde" ist vermutlich
  gar keine Runde (Anfang 332m vom Ende, dazu eine 976-m-Luecke) und gehoert angesehen statt geschlossen.
- **Neuer Fall: Kappungs-Budget je Segment.** Bei Tour 12 Hauenstein West verlor "Roemerfels" 327m von 512m
  (64 %) -- durch ZWEI benachbarte Luecken, je eine an einem Ende, von denen jede fuer sich die Grenze einhielt
  (42 %, dann 38 % der schon verkuerzten Laenge). `close_gaps()` fuehrt jetzt pro Segment mit, wie viel schon
  gekappt wurde. Zwei Feinheiten, jede aus einem Fehlversuch: die Zuordnung laeuft ueber die Objekt-Identitaet
  der Koordinatenliste (Indizes verschieben sich, wenn ein Segment eingefuegt wird), und der Bruchteil muss dem
  jeweiligen Durchgang folgen -- mit dem strengen Wert sperrte das Budget zwei bestaetigte Loesungen, die genau
  von der Lockerung leben.
- **„Felsenwanderweg Rodalben" umgebaut: die Runde beginnt und endet jetzt an der Jakobsweg-Kreuzung, der
  Bahnhofs-Zubringer wird hin und zurueck gefahren** (Vorgabe des Nutzers). Vorher lag das Ende des
  Rueckweg-Verbinders 379m vom Anfang der Runde weg, und der Connector hatte diese 379m mit einer
  2391-m-Bruecke "geschlossen". Jetzt: Trail 1 -> Verbinder -> Jakobsweg hin -> Kreuzung -> Runde -> Kreuzung
  -> Jakobsweg zurueck -> Verbinder, 20 Segmente, 43,88 km, Anfang gleich Ende, keine Luecke. Der Jakobsweg
  steht zweimal in der Linie, gekappt wird nur der Teil von "Felsenweg Sued" vor der Kreuzung (202m), und die
  beiden 354-m-Luecken des Zubringers schliessen symmetrisch identisch. **Neuer Fall dabei: eine geschlossene
  Teil-Runde wird gedreht, nicht gekappt.** "Trail 1" ist eine geschlossene 308-m-Mini-Runde am Bahnhof, an der
  die Tour mit beiden Enden haengt; der erste Lauf kappte sie von beiden Seiten (148m + 150m von 308m) und
  konnte den zweiten Uebergang dann nicht mehr schliessen. Ihr Anfang gehoert dorthin, wo die Tour sie betritt
  -- gedreht sind beide Luecken exakt 95m und nichts wird gekappt.
- **Neues Mangelkriterium: eine Bruecke darf kein Stueck doppelt fahren lassen.** Der Nutzer meldete drei
  Stellen der Ost-West-Passage, an denen die Tour 87m, 73m und 85m hin und zurueck fuhr -- die Bruecke lief zu
  100 % auf der Linie des Abschnitts, zu dem sie fuehrt. `weglos` ist dafuer blind (alles liegt auf Wegen), die
  Laenge auch (die Bruecke war kaum laenger als die Luftlinie). Der eigentliche Fehler sass in Fall 2: er nahm
  den Weg-Stuetzpunkt, der der anderen Linie am NAECHSTEN liegt, statt den ERSTEN, den man vom Endpunkt aus
  erreicht -- woertlich das Gegenteil der Anweisung des Nutzers. Bei seg9 setzte das den Schnitt 197m in den
  Brunnenwanderweg hinein, was die Segment-Grenze traf; mit "erster Treffer" wird daraus eine 11m-Bruecke mit
  83m Kappung. Das neue Mass `double_ride` ist an den 71 bisher angewendeten Loesungen kalibriert (54 unter
  10m, hoechste unbeanstandete 51,2m, die drei beanstandeten 73/80/106m), Schwelle 60m; es steht in der
  Rangfolge HINTER der Fallnummer, weil es davor ein Dutzend unbeanstandeter Stellen verschob. Zwei Loecher
  kamen dabei heraus: eine absolute Kappungsgrenze fehlte (eine Loesung schnitt 1362m eines 5273m-Abschnitts
  weg, beide relativen Grenzen eingehalten), und eine offene Luecke ist schlimmer als ein doppelt gefahrenes
  Stueck, weshalb der zweite Durchgang eine hoehere Doppelt-Toleranz hat. Alle 15 Touren neu gebaut, keine
  offene innere Luecke, fuenf Uebergaenge brauchten den zweiten Durchgang. Der Regressionstest deckt jetzt
  fuenf Touren (20 Faelle / 75 Pruefungen) -- zwei kamen dazu, jede fuer genau eine Schwelle, die sonst
  ungedeckt blieb.
- **Drei der vier offenen Wahrzeichen-Touren geschlossen: „Felsenwanderweg Rodalben" (16 Luecken, 44,29 km),
  „Ost-West-Passage" (60, 78,32 km) und „Trans Pfaelzerwald" (58, 91,24 km).** Damit haben 17 Pfaelzerwald-
  Trailrunden keine einzige offene innere Luecke mehr. Die vierte, „Dahner Felsenpfad", ist keine Lueckenarbeit:
  sie besteht aus einem einzigen Segment, hat also gar keine Trail-Zuordnung. **Ein Fernweg ist keine Runde** --
  die zwei Passagen beginnen 37 bzw. 38,6 km von ihrem Ende, und wer jede Tour als geschlossene Runde
  durchlaeuft, sieht dort eine 37-km-"Luecke"; `MAX_GAP_M` faengt das ab und meldet es. Fuer lange Touren holt
  `prefetch_gaps()` nur noch die Vereinigung der Lueckenboxen statt einer Box ueber die ganze Tour (534 km2 ->
  46 km2 bei der Trans Pfaelzerwald), weiter in EINEM Abruf und beweisbar mit derselben Wegemenge.
- **Zwei Verfahrensfehler, beide erst von diesen neuen Touren aufgedeckt — und beide haben Trail-Meter
  zurueckgebracht.** (1) Der Freibetrag fuer den Anschluss-Versatz muss dieselbe Zahl sein wie die
  Endpunkt-Toleranz; seit `ON_WAY_M` auf 20 ging, wurde ein bei 16 m akzeptierter Anschluss fuer genau diese
  16 m bestraft. Gefunden an einer 124-m-Bruecke, die durchgehend auf einer Landstrasse laeuft (Kern 0,00 m
  abseits) und trotzdem verworfen wurde. Die Kopplung hob vier erzwungene Kappungen auf: „Lambrecht Trail 7"
  -39 % ist weg, „Felsenweg Nord" +199 m, „Gipfelstuermer" +163 m, „Curvy Up'N'Down" +23 m. (2) Die Kappung
  gehoert in die Rangfolge, aber nur INNERHALB eines Falls: zwei Fall-5-Loesungen standen 654 m Bruecke mit
  1095 m Kappung gegen 698 m mit 62 m, und ohne die Kappung im Schluessel gewann die erste. Vor die Fallnummer
  gesetzt ist es der umgekehrte Fehler, auch gemessen. Alle 15 Touren wurden danach einmal mit dem
  endgueltigen Verfahren neu gebaut; nur noch sieben Abschnitte im ganzen Bestand sind ueberhaupt gekappt.
  Rodalben Felsentrails blieb auf Wunsch unangetastet.
- **`nearbyTrailConnector` erreicht die zwei letzten Rodalben-Felsentrails-Loesungen wieder** (38/38 statt
  36/38), ueber einen zweiten Durchgang mit gelockerter Verhaeltnismaessigkeit — gleiche Bauform wie Fall 5,
  der auch nur anlaeuft, wenn die einfacheren Faelle nichts liefern. Beide Luecken sind vom Nutzer bestaetigt,
  waren aber unerreichbar: `seg0` braucht Bruecke 6,9x und Kappung 6,6x der Luecke, `seg34` kappt 95m eines nur
  150m langen Abschnitts — 63 %, und das war am Hilschberghaus die richtige Antwort, weil nur sie durchgehend
  auf der Strasse bleibt (die kappungsfreie Alternative ist eine 1459m-Kette, Faktor 66). Global lockern war
  messbar falsch: Landstuhl Ost `seg21` waere dann von einer kappungsfreien Schnittpunkt-Loesung mit Faktor
  1,02 auf eine mit 50 % Kappung gewechselt. Die Rangfolge nach Brueckenlaenge-plus-Kappung umzusortieren
  wurde ebenfalls verworfen — sie behob `seg21`, brach aber zwei andere Stellen auf, darunter eine, die von
  Fall 1 auf Fall 3 rutschte. Die Fallhierarchie kodiert Vertrauen, nicht Laenge. Landstuhl Ost und West
  bleiben unveraendert, drei weitere Touren bytegleich nachgerechnet; die ausgelieferte Region wurde NICHT neu
  geschrieben (sie hatte dort schon 0 Luecken). Siehe `docs/nearby-trail-connector.md`.
- **Regressionstest fuer `nearbyTrailConnector` (`tests/python/ntcregression.py`, 12 Faelle / 39 Pruefungen).**
  Das Verfahren war zweimal still schlechter geworden, und beide Male fiel es erst auf, als der Nutzer auf die
  Karte sah: `MAX_TRIM_FACTOR` wurde mit 3.0 eingefuehrt, *nachdem* Rodalben Felsentrails damit geschlossen
  war, wodurch zwei bestaetigte Loesungen (Faktor 6,6) unerreichbar wurden — vier Tage unbemerkt, weil die
  Tour in der Regionsdatei ja schon geschlossen war. Der Test rechnet deshalb jede Tour aus ihrem Stand VOR
  dem Schliessen neu, statt die Datei zu vergleichen. Drei Touren: Felsentrails (Pflicht, auf Wunsch des
  Nutzers), Landstuhl Ost (alle Aenderungen von heute) und Landstuhl West (haengt an genau einer Schwelle).
  Die OSM-Wege liegen gepackt daneben (264 KB) und sind beweisbar dieselbe Menge, die `fetch()` im echten Lauf
  sieht — ein Test, der Overpass braucht, laeuft nie. Elf Mutationen nachgemessen, drei Deckungsluecken
  benannt statt beschoenigt (Fall 4 kommt in keiner reproduzierbaren Tour vor). Der Kern `close_gaps()` steht
  jetzt im Werkzeug und wird von Werkzeug UND Test benutzt, damit der Test die echten Annahmeregeln ausfuehrt
  und nicht eine Kopie.
- **Die restlichen acht Kurztouren des Pfälzerwalds geschlossen — 121 Lücken, keine offen** (Heltersberg,
  Waldfischbach-Burgalben, Schopp, Waldleiningen, Elmstein, Lambrecht, Landstuhl Ost und West). Damit sind
  dreizehn Trailrunden lückenlos, 235 Lücken. 102 der 121 über den einfachsten Fall; nur sechs
  Trailabschnitte überhaupt gekappt. Zwei Kappungen über einem Drittel („Lambrecht Trail 7" −39 %,
  „Westpfalz-Wanderweg Schwarzes W" −36 %) sind innerhalb der Grenzen, aber noch nicht beurteilt.
- **`nearbyTrailConnector`: neuer Fall 0 (Überlappung) und vier Fehler behoben, alle aus einem Befund des
  Nutzers an „Kurztour 6 – Landstuhl (Ost)".** Ein ganzer benannter Trailabschnitt hatte sich aufgelöst
  („Steps Heidenfelsen", 242 m → 0 m): die Verhältnismäßigkeitsgrenze bezog die Kappung nur auf die Lücke,
  nicht auf die eigene Länge des Segments. Dazu überlappten sich zwei Abschnitte schon in der Originaltour —
  „Landstuhl Trail 2" endet 82 m innerhalb von „Pavillonplatz Trail", beide in derselben Richtung, die Tour
  fuhr das Stück also zweimal. Das ist keine Lücke, sondern ein Datenfehler, und er muss **vor** allen
  Brückenfällen geprüft werden, sonst baut Fall 1 eine formal saubere Brücke rückwärts darüber. Außerdem:
  Verschmelzen von OSM-Way-Objekten ist jetzt ein zusätzlicher Kandidat statt eines Ersatzes (1041 m Brücke
  statt 94 m für eine 88-m-Lücke), Fall 1 bricht nicht mehr nach dem ersten Weg ab, der Ablehnungsgrund wird
  an einer Stelle bestimmt statt an zwei auseinanderlaufenden, und Tor/Vorauswahl/Sortierung benutzen
  dieselbe weglos-Schwelle. Nachgerechnet gegen die fünf bestätigten Touren: es ändern sich ausschließlich
  Verbinder um 0–9 m, kein Trailabschnitt. Siehe `docs/nearby-trail-connector.md`.
- **Zwei weitere Kurztouren geschlossen: „Kurztour 3 – Finsterbrunnertal" (25 Lücken, 29,18 km) und
  „Kurztour 5 – Johanniskreuz" (14 Lücken, 10,65 km)** — beide ohne eine einzige Kappung und ohne
  Verhältnismäßigkeits-Ablehnung, 38 von 39 Lücken über den einfachsten Fall. Die beiden größten Lücken
  überhaupt schließen dabei fast maßgenau: 468 m → 483 m Brücke (Faktor 1,03) und 270 m → 271 m (Faktor
  1,00), weil dort jeweils **ein** verketteter OSM-Weg die ganze Lücke spannt. Damit sind fünf Touren fertig,
  114 Lücken, alle mit 0 m abseits gemappter Wege.
- **Latenter Fehler im Wege-Cache behoben**, der beim Wechsel auf eine andere Tour zugeschlagen hätte: die
  vorab geholten OSM-Wege lagen unter **einem** Dateinamen für alle Touren, ein Lauf hätte also stillschweigend
  die Wege der vorigen Tour aus einer anderen Ecke des Waldes benutzt. Bisher nur durch manuelles Löschen
  umgangen; der Cache-Name kommt jetzt aus der Bounding-Box.
- **„Kurztour 1 – Rodalben" vollständig geschlossen: alle 25 Segment-Lücken, 32,98 km**, 0 m abseits
  gemappter Wege. Dritte Tour mit `nearbyTrailConnector`, und die erste, die das Verfahren breiter
  beansprucht: 17× ein verketteter Weg erreicht beide Seiten, 6× Schnittpunkt zweier Wege, 2× Weg folgen +
  Trail kappen, 1× Wegekette. Vier auffällige Stellen wurden gesondert vorgelegt und bestätigt (Brücke mit
  Faktor 3,7; eine Kappung von 164 m gegen 351 m ohne Kappung; eine Kappung von 200 m ohne Alternative; eine
  219-m-Lücke im Hin-und-zurück-Muster). Fall 4 (Projektion) kam auch hier nicht vor — dessen Grenzwerte
  bleiben nur an Rodalben Felsentrails geprüft.

- **Vogesen nachgeschärft, alle drei Punkte aus dem ersten Blick des Nutzers** — (1) **Ortslabels
  ausgedünnt**, 22+22 → **15+12**, über genau die zwei genannten Achsen: Mindestabstand zwischen zwei
  Labels von 4 auf 8 km, plus eine **Quote pro Sub-Region** (`1 + Trails // 45`, max 4), damit eine
  14-Trail-Klammer nicht so viele Namen bekommt wie eine mit 148. Ausnahme: der **Namensgeber einer
  Sub-Region ist vom Abstand befreit** — sonst fällt genau der Name weg, nach dem die Klammer heißt
  (La Bresse war an 150 m Grenzwert gegen Gérardmer gescheitert). (2) **Die drei Bikeparks sind eigene
  Sub-Regionen**: `bp_lacblanc` (8), `bp_labresse` (9), `bp_markstein` (6) — liftbedient,
  betreiberbewertet, als Ziel gefahren, und in der Talklammer ringsum untergegangen (Lac Blanc war ein
  Drittel von `kaysersberg`). Zugehörigkeit aus der eigenen Trailforks-Region des Parks, vor der
  Talklammer geprüft. Die beiden Lifte hängen jetzt an ihrem Park statt am Tal. (3) **Alle
  Sub-Region-Labels auf je einen Namen gekürzt** — aus "Saverne / Dabo / Wangenbourg" wurde "Saverne",
  aus "Épinal / Vallon d'Olima" "Épinal"; ein Seitenleisten-Chip hat ~14 Zeichen, bevor er umbricht.
- **Markstein hat jetzt auch einen Lift: `Tremplin 1`** (Teléski, 762 m, 143 Hm) — der Nutzer nannte
  einen Kandidaten ("Téléski Grenouillère 1"), der auf den richtigen Hang zeigte, aber die Messung gegen
  die sechs Pisten schließt ihn aus: seine Talstation liegt 469 m entfernt und **110 Hm über** den
  Pisten-Zielen, und 40 Hm Förderhöhe bedienen keine 125-Hm-Abfahrt. Tremplin 1 passt an beiden Stationen
  (78 m zum Start, **10 m zum Ziel**), hebt genau die Höhe der Abfahrten und bleibt über die ganze Länge
  10–22 m an allen sechs Pisten. Damit sind alle drei Bikeparks liftbedient.
- Nebenbei geklärt: **Bikepark Markstein ist vollständig**, nicht lückenhaft. Als eigene Sub-Region
  sichtbar sind es genau die 6 Pisten, die kelbikepark nennt (inkl. `Dexter`, das vorher in `guebwiller`
  verborgen war) — eine ist bei Trailforks nur eine Stufe härter eingetragen als beim Betreiber, statt
  wie vermutet zwei Pisten zu fehlen.

## 2026-08-19
- **Zwei neue Regionen: Nordvogesen (483 Trails, 592 km) und Südvogesen (474 Trails, 533 km)** — zusammen
  957 Trails, 44 Orte, 2 Lifte, aus **Trailforks' eigenem `encodedpath` plus dem `ElevationChart`, das
  jede Trail-Seite einbettet**, geerntet durch das eingeloggte Chrome des Nutzers. Dieses Profil bringt
  lat/lng **und echte Höhe und** die kumulierte Distanz pro Punkt mit, deshalb brauchte keine der beiden
  Regionen eine Elevation-API — und weil Trailforks dieselbe Linie damit zweimal ausliefert (Polyline +
  Profil), prüft jeder Build beide Längen gegeneinander: alle 957 stimmen auf 60 m. `build_harz.py`s
  Docstring behauptet noch, Trailforks binde kein Profil ein; das gilt nicht mehr. Quelldaten in
  `Material/Vogesen/`, Details in `docs/nordvogesen.md` und `docs/suedvogesen.md`.
- **Zwei Erntefehler gefunden, die still bleiben würden** — beide gelten für jede künftige
  Trailforks-Region: (1) die `difficulty=`-Liste der Tabellen-URL muss **jeden** Code nennen, denn
  **Code 10 ist `Severe / Black`** — ohne ihn fehlte die komplette schwarze Stufe, 38 Trails, darunter alle
  8 schwarzen in Barr (derselbe Fehler wie bei Finale, zum zweiten Mal; eine ungefilterte URL ist nicht der
  Ausweg, sie liefert *weniger* Zeilen). (2) Die Kind-Regionen-Liste einer Trailforks-Eltern-Region ist
  **nicht vollständig**: neun Gemeinden hatten keinen Link, darunter Gérardmer und der komplette Bikepark
  du Markstein — nur gefunden, indem die abgeschnittene Département-Tabelle gegen die Vereinigung der
  Kinder gediffed wurde.
- **Regionsgrenze aus einer gezeichneten Linie** — der Nutzer hat die Trennung zwischen Nord und Süd auf
  einem Trailforks-Screenshot eingezeichnet; `tools/vogesen_boundary.py` rechnet sie in eine Regel um
  (Pixel-Transformation aus bekannten Orten gefittet, ca. ±4 km genau) und jeder Build prüft jeden Trail
  dagegen. Das hat drei echte Platzierungsfehler gefunden: sechs Trails 65 km neben ihrer Klammer
  (Trailforks' `dambach` ist Dambach-Neunhoffen, nicht Dambach-la-Ville), einen Trail, den der
  Schwerpunkt-Fallback 38 km auf die falsche Seite gezwungen hatte, und einen Trail, dessen zwei Hälften in
  zwei verschiedenen Regionen lagen.
- **Bikepark-Schwierigkeiten von den Betreiberseiten** (Standing Rule) für Lac Blanc und La Bresse: 16
  Trails geprüft, **eine Änderung** (Lac Blancs `La FAT` ist *rouge/noir* → schwarz). Markstein bleibt auf
  Trailforks, weil die als offiziell geführte Betreiberseite heute eine Alterssperre statt eines Bikeparks
  liefert. **2 Lifte**: Montjoie (Lac Blanc) und Vologne Express (La Bresse), über `tools/add_lifts.py`;
  Markstein bekommt bewusst keinen, da OSM dort keinen Sessellift kennt.
- **44 Orte** über `tools/add_region_places.py`, das dafür drei allgemeine Erweiterungen bekam:
  Sub-Region-Labels aus dem Build-Skript, wenn die Region noch nicht im Katalog steht; `MAX_PLACES` pro
  Region überschreibbar (10 passt zu einem Resort, nicht zu einem Massiv); und ein **Mindestabstand von
  4 km zwischen zwei Labels** — ohne den vergab Südvogesen sechs seiner 22 Plätze an die Agglomeration
  Mulhouse, weil ein Vorort mit 10 000 Einwohnern ein Bergdorf mit 4 000 überholt. Dieselbe Suche legte
  einen Datenfehler offen: drei dieser Labels hingen an einem einzigen flachen Trail in Mulhouses
  Stadtwald, 23 km außerhalb des Massivs — der ist jetzt raus.
- **Ein Rebuild löscht `places`/`lifts` nicht mehr** (beide Vogesen-Builds): `add_region_places.py` und
  `add_lifts.py` schreiben nach dem Region-Build, `write_region()` gibt nur aus, was es bekommt. Die beiden
  Builds lesen ein vorhandenes Array jetzt ein und reichen es durch, statt die Reihenfolge zu dokumentieren
  wie bei Bike Kingdom.
- Neu: `tools/region_dupe_check.py` (generisch, ersetzt die region-spezifische Erstfassung) — prüft eine
  Region gegen alle anderen auf gemeinsames Gelände. Fand drei Nordvogesen-Trails, die vier
  Pfälzerwald-Stücke vollständig enthalten (derselbe Waldrücken beidseits der Grenze); nach Entscheidung
  des Nutzers behält der Pfälzerwald seine, die drei sind aus Nordvogesen entfernt.

## 2026-08-17
- **„Kurztour 1 – Leimen" vollständig geschlossen: alle 14 Segment-Lücken, 23,66 km** — erste Anwendung von
  `nearbyTrailConnector` auf eine Tour, mit der das Verfahren nicht entwickelt wurde. 14 von 14 Lücken über
  den einfachsten Fall (ein verketteter OSM-Weg erreicht beide Seiten), 0 m abseits gemappter Wege, kein
  Trail gekappt, kein Grenzwert angepasst. Bestätigt die Vermutung, dass das Zusammenfügen der OSM-Way-Objekte
  der tragende Schritt ist. Siehe `docs/nearby-trail-connector.md`.
- **Reworked the "Orte" map option to default off** (user preference). `showPlaces` now starts `false` in three
  places that all had to move together: the `#showPlacesToggle` checkbox's own `checked` attribute, the
  module-level `let showPlaces` default, and `restoreActiveState()`'s fallback for an old saved state that
  predates the field. A user who already switched it on/off explicitly keeps that choice either way — only the
  brand-new-visitor default changed.
- **Optimized the region picker (`#regionDialog`)** (user feedback, several points at once):
  - Removed the dialog row's own 📍 fly button (`.rd-locate-btn`) — the sidebar's `.region-group-fly-btn`
    already does this once a region is active, and activating one now flies there automatically anyway, so it
    was a second control for a job the flow no longer needs.
  - A region's full name in the dialog no longer clips with an ellipsis (`.rd-label` dropped its
    `white-space:nowrap`/`overflow:hidden`/`text-overflow:ellipsis`) — it wraps instead.
  - **Activating a region now closes the dialog itself once loading actually finishes** (and, on a phone,
    closes the drawer it lives in) — it used to leave the just-finished list sitting open. Only on success: a
    failed fetch keeps the dialog open so the inline error stays visible. The dialog's own "Aktivieren" button
    also got a `.is-loading` sweep animation while pending, on top of the existing "Lädt…" text.
  - `tests/browser/regions.js`: new case "no locate button in the dialog rows any more, and the name is not
    clipped"; the "activating a third region works…" case now also asserts that a successful activation closes
    the dialog on its own. `restoreRegions()`'s own cleanup loop had to learn to reopen the dialog after a click
    that closed it, since it used to assume the dialog stayed open across every click in a pass.
  - Style version bumped (`style.css?v=180`, `CACHE_NAME`/`PRELOAD_CACHE_NAME` → `trailmap-v180`) for the
    `.rd-toggle.is-loading` rule and the `.rd-label` wrap fix.
  - **Tried and reverted the same day: a global "busy bar" indicator** (`#globalBusyBar`, a thin animated bar at
    the top of the viewport) meant to cover region (de)activation and the difficulty/sub-region/
    uphill-loop-downhill/lifts visibility toggles, which can each rebuild hundreds of map layers with no other
    feedback (Pfälzer Wald alone has 805 trails). Removed after the user tested it on phone and desktop: the
    sweep animation barely showed — most of these rebuilds finish faster than its 1.1s animation cycle, so it
    read as one unreliable, barely-visible flash of colour rather than a genuine progress indicator, not worth
    keeping. Worth remembering if this is revisited: a `requestAnimationFrame`-only version of the deferral this
    relied on (to let the browser paint the bar before a long synchronous rebuild blocks the main thread) also
    stalled every filter toggle for as long as the tab was backgrounded/unfocused — rAF callbacks are throttled
    or withheld then, the same effect `tests/README.md` documents for Leaflet's own tooltip-fade timers.

## 2026-08-16
- **„Rodalben Felsentrails" ist vollständig geschlossen: alle 36 Segment-Lücken, 41,81 km, jede Lösung am
  Kartenbild bestätigt.** Das Verfahren heißt **nearbyTrailConnector** (`tools/nearby_trail_connector.py`)
  und wurde fallweise mit dem Nutzer erarbeitet — Methodik, Fallkatalog und die Unterscheidung
  akzeptabel/perfekt in `docs/nearby-trail-connector.md`. Kern sind **zwei Ebenen von Verkettung**: OSM
  zerlegt eine Straße in mehrere Way-Objekte, die zusammengefügt werden müssen (das brachte 27 von 34 Fällen
  auf „einem Weg folgen"), und Ketten über echte Abzweigungen für die schwierigen Fälle. Fünf Fälle:
  ein Weg erreicht beide Seiten (27×), Weg folgen + Trail kappen (3×), Schnittpunkt zweier Wege (2×),
  Projektion des Trailabschnitts auf seinen Weg (2×), Wegekette (2×) — alle mit 0 m abseits gemappter Wege.
  Zwei Regeln, die je einen Fehlversuch gekostet haben: ein Weg, auf dem die Tour ohnehin liegt, darf nie
  wegen Zugangs-Tags ausgeschlossen werden, und die Trail-Geometrie wird nie verschoben, nur gekappt.
  Ein einziger Overpass-Abruf für die ganze Tour statt einer pro Lücke: von 1 min 35 s auf 0,9 s.
- **Verfahren gegen die bestätigten Ergebnisse nachgerechnet — und dabei drei Mängel gefunden.** Nach dem
  Einbau der Wegeketten wurde alles neu von der Original-Geometrie gerechnet und verglichen: es war zunächst
  *nicht* stabil. (1) Die Verhältnismäßigkeitsgrenze verwarf eine bestätigte Lösung um 1,5 m. (2) Die
  verschärfte Weglos-Toleranz zählte den bewusst akzeptierten GPS-Querversatz von 12–13 m als Mangel. (3) Eine
  Regel „weniger Kappung zuerst" zog eine 637-m-Kette einer 406-m-Lösung vor. Das Qualitätsmaß ist jetzt
  **weglos nach Projektion** (Vorschlag des Nutzers): was innen abseits der Wege läuft, plus der Anteil des
  Anschluss-Versatzes über 15 m — damit ist GPS-Rauschen frei, ein echtes Geländestück zählt. Der vierte
  Durchlauf reproduziert den bestätigten Stand (41,81 km, 36 von 38 Segmenten identisch).
- **Trailrunden-Lückenschließen überarbeitet (Zwischenschritt zum Obigen).** Das Verfahren
  arbeitet nicht mehr als Wettbewerb aller Methoden nach kürzester Strecke, sondern in Prioritätsstufen:
  erst beide Lücken-Enden auf echte OSM-Wege mappen (inkl. neuer Variante, die beide Seiten mappt und den
  tatsächlichen Treffpunkt der zwei Wege sucht), dann vorhandene Connector-Geometrie, dann Dijkstra. Dazu
  eine **Befahrbarkeitsprüfung** (`vehicle=forestry`, `bicycle=no`, `access=private/customers` … werden
  verworfen — genau der Fehler, den der Nutzer live auf der Karte gefunden hatte), eine **Wegtyp-Präferenz**
  (Trail schlägt Forstweg bei vergleichbarem Match) und ein **Abbruchkriterium**, wenn ein Abschnitt gar
  nicht auf einem OSM-Weg liegt. Zwei stille Fehler des ersten Durchlaufs mitbehoben: auf den nächsten
  Stützpunkt schnappen statt auf die Wegstrecke zu projizieren (ließ 16 von 29 Lücken faktisch offen, während
  der Report `route_factor 1.00` meldete), und eine leere Brücke, die gar nichts einfügte. Ergebnis nach
  komplettem Neu-Rechnen: 29/29 Lücken allein durch OSM-Weg-Matching, 22 davon auf echten `path`-Wegen,
  **0 verbleibende Lücken über 2 m** (vorher 38). Methodik in `docs/trailrunden-lueckenschliessen.md`.
- **Fixed a real app-crashing bug the user hit repeatedly on their phone: toggling RIDE mode (or "Blickrichtung
  oben") could throw "Maximum call stack size exceeded" and show the fatal panel.** Root cause: a `map.stop()`
  added earlier the same day (to cancel an in-flight pan/zoom animation before rotating) could itself fire
  Leaflet's `"zoomstart"` event, which the app's own pinch/drag-detach listener turned into another
  `map.stop()` call — an infinite loop between our own event handler and Leaflet's `stop()`, not a
  Leaflet/leaflet-rotate internals bug. Fixed with a reentrancy guard (`safeMapStop()`) that every `map.stop()`
  call in the file now goes through. Also added: a 400ms cooldown on the RIDE toggle buttons and a
  `window.onerror`-level recovery hook that resets rotation state gracefully if this class of crash ever
  recurs for a different reason, instead of leaving the app stuck behind the fatal panel. New suite
  `tests/browser/ride.js` (11 cases: enter/exit chrome, auto-solo + selection-ring suppression, the RIDE focus
  halo, the look-ahead map offset in portrait/landscape, the info panel's content) — building it is what
  surfaced this bug in the first place. See `docs/backlog.md`'s RIDE-Modus section for the full investigation.
- **Fixed: a difficulty/category/region/search filter that hid a trail left its halo casing glowing on
  Satellit/Relief** (reported live by the user). `render()`'s filter-driven hide branch only ever touched
  `layer.line`/`hitLine`/`startDot`/etc, never `layer.casing` — fine for a segmented Trailrunde (its
  casings are children of `layer.line` and go with it for free) but not for a plain trail, whose casing
  lives directly on `map` (same reason `destroyTrailLayer` has its own explicit removal for it). Fixed by
  adding the matching `map.removeLayer(layer.casing)` to the hide branch and a `syncHalo()` re-add to the
  show branch. New mutation-checked case in `tests/browser/palette.js`; see `tests/MUTATIONS.md`.
- **Basemap picker restructured: "Straße"/"Straße dezent"/"Straße hell" are now three peer options**
  (same osm tiles, three CSS filter levels — `brightness`/`saturate`/`contrast` on Leaflet's own tile
  pane, no tile-server involvement, works offline), not sub-options of one button as first built the
  same day. The old CARTO/Positron "Straße hell" basemap is kept (the user didn't want it removed after
  all) but renamed to **"Pastell"** so the two don't collide by name — `data-layer="carto"` is
  unchanged, so its own test coverage needed no changes beyond the visible label. **Default basemap on
  a first-ever visit is now "Straße dezent"**, not plain Straße. Persisted like the other filter
  toggles; general setting, not RIDE-only.
- **RIDE button emoji and the info-panel's own RIDE button.** Went 🚵 (mountain biker, "harder to
  recognize at a glance") → 🚴 (plain cyclist) → 🚲 (bicycle alone, no rider/hill) after the user found
  🚴 still rendered with a hill in the background on their phone's emoji font. A record/stop icon
  (⏺️/⏹️) was considered and rejected twice — once for the coloured background chip those render with
  on many platforms, once on principle ("solange wir nix aufnehmen ist das nicht das richtige", since
  nothing is actually being recorded). Also fixed: the info panel's own `.ride-btn` (in `.ip-btns`,
  alongside locate/solo/reverse/GPX) was visible on desktop too — RIDE only makes sense on a phone
  actually being ridden with, so it's now hidden by default and shown again only in the same
  touch-only media query `#locateCluster` already uses.
- **RIDE mode: bigger control buttons, and the halo's orange is now fully opaque.** `#mapControls`'s
  three cells grow 44px→64px (icon 20px→28px) while `html.ride-mode` is active — gloves/vibration on
  the bike, per the user's request — with the readout chip widened to match so the joined-corner
  design still lines up; unaffected outside RIDE. Separately, the focus halo's outer ring dropped its
  0.75 opacity to fully opaque: where a loop's own line runs close beside or crosses itself (a normal
  shape for a Trailrunde), two semi-transparent orange rings stacked and darkened toward red at the
  overlap, reading as an unrelated reddish smudge on the map.
- **RIDE focus halo: thicker orange ring, and gaps between segments now get bridged too.** After
  phone/live-map feedback: `RIDE_OUTER_WEIGHT` bumped 14→18px, and any real gap between two
  consecutive Trailrunde segments (see `tools/close_loop_gaps.py` for why these exist) is now bridged
  with a plain orange line during RIDE, so an un-closed tour still reads as one continuous line instead
  of visibly breaking apart — verified on "Tour 1 - Rodalben" (34 known gaps), which now shows one
  unbroken orange ring end to end.
- **Closed all 29 real segment-boundary gaps on Rodalben Felsentrails** via a new tool,
  `tools/close_loop_gaps.py` — tries reusing an existing connector from another tour, walking the OSM
  way the other side already follows, or Dijkstra shortest-path as a fallback, and keeps whichever
  produces the shortest real route (average factor 1.02, no detours). Added the same day: a
  three-layer RIDE focus halo (orange outer ring, light per-difficulty tint, existing core line) for
  whichever trail/tour is open during RIDE, so it stays legible in bright sun on any basemap. See
  `docs/backlog.md`'s Trailrunden-Lückenschließen section for a known gap in the tool itself (no OSM
  access-tag check yet — one junction's winning route follows a `vehicle=forestry`-restricted track)
  and the plan for the next round (other tours, OSM-mapping prioritised over Dijkstra, a "trim the
  trail" candidate, a two-sided intersection search).
- **Fixed two follow-up bugs from the infobox refinements above.** (1) The km/h number was still not
  exactly centred in portrait — the number+unit sat together in one flex box, and the unit's own width
  shifted that whole box (and the number inside it) off from the panel's true centre. `.ride-speed-stat`
  is now sized to the number alone (`inline-block`), with the unit positioned beside it via
  `position:absolute` so it adds no width to what gets centred; landscape's existing stacked layout
  (already correct, confirmed unaffected) needed an explicit `display:flex`/`position:static` override to
  survive the more specific portrait rule. (2) The RIDE look-ahead offset (position dot at ~1/3 up from
  the visible bottom) was computed against `.map-wrap`'s full height, so once the portrait info panel
  grew taller (bigger fonts/padding, same day) the fraction was measured against a container that's now
  partly covered by the panel — pushing the dot lower than intended. `applyRideMapOffset()` now subtracts
  the panel's own live rendered height from that reference height, and is also re-run whenever the panel's
  content (and therefore its height) changes — i.e. whenever a trail is focused/unfocused mid-ride, not
  just once on entering RIDE.
- **RIDE infobox: phone-tested refinements after the redesign.** Speed number is now genuinely centred
  (`#rideInfoBig` needed an explicit `width:100%`, or the flex column shrinks to its content and sits
  left-aligned even with `align-items:center` set); altitude's portrait badge and the gap above the
  trail row both grew per the user's sizing calls; in landscape the speed number grew, each stat's unit
  moved below its number instead of beside it, and the trail row is now genuinely pinned to the bottom
  of the column instead of trailing after the big numbers. Also fixed: the length/⬆️/⬇️ stats sat at
  visibly different heights on a real phone (iOS's own emoji font has different vertical metrics than
  plain digits) — switched from baseline to centre alignment, which sidesteps the font-metric mismatch
  instead of compensating for one specific emoji font.
- **RIDE infobox redesigned for sunlight readability**, after reviewing mockups (built with the
  `visualize` tool first, before touching app code) instead of iterating live: speed is now a single
  dominant, centred 80px (58px landscape) number in a plain heavy sans (Arial/Helvetica, not the app's
  decorative Copperplate); altitude is a smaller secondary badge (corner in portrait, below a divider in
  landscape) rather than an equal second number. The focused trail's name/length/Hm moved into one row
  and is now hidden outright with nothing focused — no dash placeholder, unlike speed/altitude which
  always show something.
- **RIDE mode: added a big live speed (km/h) and altitude (m) readout**, sitting above the existing
  trail name/length/Hm in `#rideInfoPanel` (not replacing it, per the user's own preference). Pulled
  straight from each GPS fix's own `coords.speed`/`coords.altitude`; shown as "–" rather than a
  misleading 0 whenever the current fix doesn't carry a usable value.

## 2026-08-15
- **Merged `docs/region-backlog.md` into a new general `docs/backlog.md`**, per the user's request for
  one cross-topic backlog instead of a new per-topic file each time. Regions moved in as their own
  section, unchanged; a new "RIDE-Modus" section holds the open follow-up ideas from the same day
  (infobox rework, a manual orientation toggle, a possible record/stop icon, a separate tracking
  concept, and the still-thin test coverage). `CLAUDE.md`'s own pointer updated to match.
- **Fixed: a two-finger pinch never showed the position button, even while visibly moving the tracked
  position off-centre.** A pinch is handled entirely by leaflet-rotate's own `TouchGestures`, a different
  code path from Leaflet core's drag handler, which only fires "dragstart". Confirmed from the vendored
  source that a pinch fires "zoomstart" instead — now also listened for (guarded so the very first GPS fix's
  own zoom-in doesn't falsely trigger it). Also removed the blue/filled highlight on the position button
  while detached, per the user's request — it now just appears, nothing more.
- **Merged the position button (📍) and the old separate re-centre button (◎) into one.** Both ultimately
  meant "put my position back where it belongs" (the user's own observation). `#mapControls` order is now
  RIDE, bearing, position (RIDE leads as the entry point into riding; position is last since it's the only
  conditional cell now — hidden while centred and following, shown otherwise, taking over ◎'s old "tap to
  reattach" job when detached). Traded away: the brief "tap 📍 during RIDE for the true screen centre"
  override added earlier the same day has no reachable button once centred, since the cell hides then —
  an accepted cost of not having two buttons for one job. Fixed two now-stale assumptions in
  `tests/browser/bearing.js` while updating it for the merge: `followMode`/`followDetached` were never
  actually reachable from a test script (a wrong assumption in an earlier edit that would have silently
  no-opped), and a separate, unrelated case had been waiting on a `.active` class that stopped being set on
  the position button back when RIDE took over triggering follow mode — its wait was quietly running out
  its full timeout every run.
- **RIDE mode, round two, after the first phone test: bottom info bar + a look-ahead position placement.**
  `#rideInfoPanel` now docks at the BOTTOM in portrait, flush with the real bottom edge (was top, and
  briefly left a gap above Leaflet's attribution strip before that too got fixed the same day) — modelled
  loosely on the Bosch eBike Flow app's own "Ride" screen (dark background, readouts at the bottom, top
  kept clear for what's ahead). More significantly: while riding, the user's position now sits about a
  third of the map's height up from the bottom (not dead centre), so more of the map ahead is visible,
  since travel direction is "up" once "Blickrichtung oben" is active. First attempt patched two of the
  vendored `leaflet-rotate.js`'s own internals (`_getNewPixelOrigin`/`_getPixelCenter`) — reverted the same
  day after the phone test showed the rotation pivot moving correctly while the position dot stayed at
  true dead centre regardless (the same disagreement the 2026-08-01 "dead centre" fix was originally for,
  just from different internal math). What shipped instead touches none of Leaflet's own centring/rotation
  code: `#map` itself is made taller than the visible window and shifted upward during RIDE
  (`applyRideMapOffset()`/`clearRideMapOffset()`), so Leaflet's own dead-centre placement — provably
  correct, since nothing about it changed — lands lower within the cropped, visible part. The locate
  button (📍) still recentres to the true screen centre on tap, even mid-ride. See `CLAUDE.md`'s RIDE
  section and the plan file referenced there for the full reasoning, including why the first attempt
  failed and how the replacement was verified.
- **RIDE mode, same-day follow-up: the position dot is now horizontally centred in landscape too.**
  `#rideInfoPanel` docks along the left edge in landscape, covering part of the map — the dot sitting at
  the full container's horizontal centre read as visibly off-centre in the space actually left uncovered.
  `applyRideMapOffset()` now also widens/shifts `#map` horizontally by an amount derived from the panel's
  own live-measured width, landing the dot exactly mid-way between the panel and the map's right edge
  (verified: 0px off target). No change in portrait, where the panel is a full-width bottom bar instead.
- **Added a RIDE mode, replacing the old hold-to-follow gesture on the locate button.** A new 🚵 button
  (in the map controls cluster, and in a trail's info panel) starts a full-screen riding view: header,
  sidebar and the info panel hide, GPS follow + auto "Blickrichtung oben" rotation start, and a focused
  trail is shown solo (dimmed rest of the map) with the yellow selection ring always suppressed,
  regardless of how the trail got selected. A focused trail cannot be deselected by tapping empty map
  space while riding, and exiting RIDE always rotates back to north. A new permanent readout
  (`#rideInfoPanel`, top in portrait / left edge in landscape) shows the focused trail's name/length/Hm
  while riding, and stays visible (reduced) with nothing focused as a placeholder for future tracking
  info. Reuses the existing `startFollowing`/`stopFollowing`/solo/rotation machinery wholesale — only the
  trigger and the full-screen chrome are new. See `CLAUDE.md`'s architecture section for the exact
  functions touched.
- **Connector back to plain dark grey everywhere, and the contrast halo widened from schwarz-only to
  every trail/connector/lift on Satellit and Relief.** Both tried live at the user's own initiative,
  neither designed up front. The connector (`#e08a00` at the start of the day) was reported as low-
  contrast in bright sun on Straße/Straße hell; the user asked for the original dark grey (`#5a5a5a`)
  back — and once a halo made every colour's own contrast case for a separate connector hue redundant, it
  went onto Satellit too, closing out a three-week round trip through orange (`CLAUDE.md` keeps the full
  history so nobody reinvents it). The halo itself widened the same day: white behind every diff colour
  first, narrowed a step further once the user found plain white "zu neutral" — gruen/blau/rot now get
  their own light tint, the diff colours themselves went darker to compensate, and the connector's halo
  is a light orange after a grey-with-white-halo connector was rejected outright ("sieht noch nicht gut
  aus", read as a map boundary rather than part of a Tour). The ring itself is narrower too
  (`HALO_WEIGHT_TRAIL` +1 instead of +2), now that it covers every trail instead of a schwarz minority.
- **Lifts get the same contrast band, for free — by turning ON a layer that already existed rather than
  building a new one.** The user's own observation: "wir haben ja die Linie für Straße, die bei den
  anderen Ansichten ausgeblendet ist" — a lift's own grey MASK polyline (7px, sitting behind the 1.1px
  hairline and 3.8px dots in the same pane, by build order) is structurally identical to a halo casing.
  `liftMaskOpacity` flipped from 0 to 1 on Satellit/Relief is the entire change; its colour went white
  first, then light violet (`#dab6f0`) once white was rejected ("weiß ist nicht das richtige für Lifte")
  — a lift needed to read as its own kind of thing, not as another trail with a halo. Lift hairline/dots
  moved to the same dark grey as the connector too, separately: light grey (`#d9d9d9`) nearly vanished
  inside the yellow selection outline once a lift was selected.
- **Relief got Satellit's entire configuration wholesale, closing a gap open since 2026-08-13.** Tried
  directly rather than designed from scratch, since the underlying problem — hue collision with
  OpenTopoMap's own green/orange, not darkness — is exactly what Satellit's halo already fixed for a
  different reason. Verdict after seeing it live: "besser als vorher, aber Relief ist einfach schwierig.
  Wir lassen es so" — an improvement, accepted as the ceiling for this basemap rather than a full fix.
  `tests/browser/palette.js` rewritten for the new final colours/values, mutation-checked (`tests/
  MUTATIONS.md`).
- **A Tour's segment hit areas moved into their own Leaflet pane (`tourSegHitPane`, z-index 405), which
  closes the segment-click bug structurally instead of by ordering discipline.** Clicking a Tour's stretch gave
  the plain trail's panel until the Tour had been selected once — because `lineTrails` order IS the map's
  z-order and any trail built after a Tour lays its invisible 22px hitLine over that Tour's per-segment areas.
  Two rounds of re-raising (at build time, then in `applySolo`) each held only at the moment they ran, and the
  user named why that can never be enough: "wenn man in der App Filter aktiviert und wieder deaktiviert, kann
  man in so einen Zustand ja immer kommen" — `render()` adds and removes layers on every filter change. A pane
  makes the question disappear. Verified live: 92 hit areas in the new pane, zero left in the overlay pane, and
  the pane is **empty while the Tours are hidden**, so the trails underneath stay clickable (the user's own
  follow-up requirement). Lifts were already at the bottom (`liftBandPane`, 350) including a Tour's own lift
  stretches; putting the visible Tour LINES above the trail lines as well is deliberately left for its own
  change, since four suites select trail geometry via `.leaflet-overlay-pane`.
- **The selected stretch of a Tour is now drawn bold, on touch and desktop alike** (user request). Done by
  raising that segment's own `_tmBaseWeight` rather than setting a width, which is what makes the emphasis
  survive hover, solo dimming and a repaint without any of those needing to know about it -- the same
  mechanism that gives a connector its thinner baseline. A lift stretch is never bolded: it is three strokes
  that are exempt from the group's styling on purpose. Also fixes two bugs the user found on the live region:
  a Tour riding the same trail twice always highlighted the FIRST occurrence (`selectedSegmentId` is a trail
  id, so `segs.find()` could not tell them apart -- Felsenwanderweg Rodalben rides "Felsenweg Süd" at km
  0.7-5.9 and again at 27.5-42.8), and a tapped trail stayed bold on a phone because `setHover(true)` lives
  in the click handler and a finger produces no `mouseout` to undo it.

- **Tried, and rejected same-day, a light basemap that also draws forest roads and trails** — the gap
  between "Straße hell" (light, but its paths are hairline-faint and gone above z14) and "Relief" (draws
  everything, at the price of contour clutter and hue collision with our own lines) is real, but no keyless
  candidate closed it well enough to keep. **"Wald"** (the HOT style via OpenStreetMap France — calm sage
  green, cream path dashes, no contour lines) shipped first, with `maxNativeZoom: 16` and `retryFailedTiles()`
  to work around the server answering **404 above z16** everywhere but the densest areas (not the host —
  CyclOSM on the same infrastructure serves z18) and throttling bursts. It looked right, but the user's own
  verdict on the blurry z17+ upscale, after living with it, was to drop it rather than keep it ("Schade, dass
  Wald nicht so weit reinzoomt … Wald kann auch wieder raus"). **`openstreetmap.de`**, tried next specifically
  because it reaches z19, lost on sight ("sehr ähnlich zu Straße"). **Thunderforest Outdoors** ("Outdoor")
  reaches z19 too but needs an API key — keyless tiles carry a diagonal "API Key Required" watermark,
  byte-identical with and without a `Referer` — and was removed hours before "Wald" itself was. CyclOSM
  (contour-heavy, trail-like tracks) and CARTO Voyager (paths as faint as Positron's) were ruled out the same
  way, by comparing real tiles rather than descriptions. All three basemap entries, `retryFailedTiles()` and
  the browser-suite case that covered them are gone again; the comparison and the rejection reasons are kept
  in `CLAUDE.md` so nobody re-tries the same three without a real fix for the zoom ceiling.
- **`tests/browser/palette.js` carried a line that could never go green** — `T.eq(label, <boolean>, <array>)`
  where it meant `T.ok`, ever since the Monte Corno case was written on 2026-08-13 (`ddec83e`). A
  permanently red line is worse than a missing check: it trains everyone to read past red. Same class of
  thing in `tests/browser/solo.js`, a duplicate `const tourCard` in one callback (from `4cc3989`) — a
  SyntaxError that took down the **whole bundle**, i.e. every `--changed` run after an index.html change.
- **Pfälzerwald reworked against Trailforks: 437 → 805 trails, and the Trailrunden now name three times as
  much of their own length.** Source: all 485 Trailforks trails inside the region's box, from Trailforks'
  own `encodedpath` via logged-in Chrome; the Trailrunden's `trailSegments` re-derived with
  `tools/gpx_map_match.py` against the merged trail set. 112 existing entries replaced where a Trailforks
  trail covers them, 273 kept (mostly OSM hiking-route fragments, which the user confirmed may stay), two
  new sub-regions for ground the region never covered (`haardt` 112, `bienwald` 13). The headline number is
  the share of each Tour's length that falls on a *named* trail: **13.3% → 19.7%**, 37 of 42 Tours better,
  3 unchanged, 2 worse. Felsenwanderweg Rodalben went 24.3% → **85.2%** once the user pointed out it simply
  *is* the Rodalber Felsenwanderweg, which Trailforks carries as "Felsenweg Nord/Süd". Tools:
  `pfaelzerwald_{report,containment,integrate,rederive_loops,finalize}.py`.
- **That 13.3% is the corrected baseline, and finding it mattered more than the gain.** The region's 616
  existing attributions turned out bimodal — half exactly on their trail, then a tail reaching 827 m away
  ("König-Albrecht-Wanderweg 1"). About a tenth claimed ground their named trail is nowhere near, inflating
  the old headline to 15.2%. `pfaelzerwald_report.py` now measures both, and raw == clean after the rework:
  the gain is not paid for with new noise.
- **A Tour's segment must carry its component trail's geometry, not a slice of the Tour's own line.** Built
  the wrong way round first, and the user reported all three consequences from the preview: doubled offset
  lines, clicks opening the trail instead of extending the Tour's panel, and the same ground stored twice.
  Donnersberg/Bike Kingdom/Laax have 100% of segments sitting 0.0 m from their trail; the slice version
  managed 56%. Fixed via `resolve_segments()`, and the Tour lines moved at most 5.7 m in the process.
- **`lineTrails` order IS the map's z-order** — appending the 480 harvested trails after the Tours put 483
  hitlines over every Tour's per-segment hit areas, so segment clicks went to the wrong layer. The live
  region has 3 trails after its last Tour and Bike Kingdom 0, which is why it never showed there. Tours are
  sorted last now, and `applySolo` additionally re-raises the soloed layer's own hit areas — dimming a line
  never touched its invisible 22px hitline, so **Donnersberg carries the same bug latently** and is fixed
  by that half too.
- **Harz difficulties now follow the OPERATOR, not Trailforks** — the user's standing rule ("immer die
  Schwierigkeit des Betreibers übernehmen"), which reverses for this region the Trailforks-throughout rule
  it was built to. All six operator pages re-checked: only St. Andreasberg, Trailpark Ilsenburg and Bodetal
  publish a grade at all, so Hahnenklee/Schulenberg/Braunlage necessarily stay on Trailforks. The
  three-step German scale maps onto the app's own labels (leicht → blau, mittel → rot, schwer → schwarz),
  and a two-step grade ("mittel / schwer") rounds **up**. Net effect: **7 St. Andreasberg trails
  re-coloured**, Ilsenburg's and Bodetal's grades already agreed. `OPERATOR_DIFF`/`resolve_diff` in
  `tools/build_harz.py` carry the mapping plus each trail's operator wording; five new cases in
  `tests/python/geomerge.py` (mutation-checked) pin the rule, one of them comparing the shipped
  `harz.json` against it for all 42 trails.
- **Harz's remaining gaps reviewed and closed as accepted, not open**: the four trails with no geometry
  anywhere (Bodetal `05 Schwarze Köhlerliesel`, Schulenberg `OnAir`, St. Andreasberg `7 Super Enduro` and
  `8 Kids Trail Harz`) are dropped for good — the user found no GPX for them either — and the two
  non-park trails (`Spiegelthaler-Trail`, `Bodetrail`) stay in deliberately. See `docs/region-backlog.md`.

## 2026-08-13

- **Per-basemap map colors, several rounds of live iteration.** Trail/connector/lift colors were tuned
  against OSM's own tiles and nearly disappeared on Satellit (schwarz trails, the grey lift mask). Ended
  at: brightened gruen/blau/rot on "Straße"; unchanged on "Straße hell"/"Relief"; brightened gruen/blau/rot
  + near-black schwarz + a white geometry halo behind schwarz specifically on "Satellit". Connector color
  is orange everywhere, but not the same orange (`#e08a00` on Straße/Straße hell/Relief, `#ffb300` bright
  amber on Satellit) after two rounds of "too pale" / "too dull" feedback on the darker basemaps. See
  CLAUDE.md's "Trail/lift/connector/selection colors are per-basemap" section for the full history,
  including a CSS `filter: drop-shadow` halo that shipped, broke on iOS Safari (WebKit transform+filter
  bug), and was fully reverted the same day in favor of the current geometry-based, kind-scoped halo.
- **Fixed: a trail's halo (the white ring behind schwarz trails on Satellit) didn't dim with solo mode or
  disappear on selection.** Selecting any loop solos it, which dims other trails' lines but — until fixed
  — left their halos glowing at full opacity, misread by the user as "Monte Corno wird komplett weiß" (the
  real cause: a *different* Trailrunde sharing Monte Corno's path). `applyHaloOpacity()` now keeps a
  halo's opacity in sync with its own line everywhere opacity changes; selecting a trail now suppresses
  its own halo outright (redundant once the yellow selection ring is showing).
- **Fixed: selecting a Tour riding a lift forced that lift's (supposed to be invisible, on non-Straße
  basemaps) mask back to fully opaque.** `applyLiftSegmentOpacity()` was setting all three of a lift
  stretch's strokes to the same on/off opacity, ignoring `LIFT_MASK_OPACITY`. Read as a white/light band
  appearing specifically once the Tour was selected.
- **The lift mask (a grey band covering OSM's own vector aerialway rendering) is now Straße-only** — the
  other three basemaps didn't need it (Satellit is a photo with no aerialway line to cover at all). The
  lift symbol (hairline+dots) is light grey on Satellit instead of near-black, for the same "too dark to
  see against dark terrain" reason schwarz trails needed fixing.
- **Recovered:** Donnersberg's "Wasser & Holz" Trailrunde had silently lost its entire `trailSegments`
  breakdown several commits earlier (an unrelated region-expansion commit rewrote the file without
  carrying the key forward) — noticed by the user, recovered from git history since the referenced
  component trails' geometry was unchanged.
- Sauerland/Upland: Winterberg split into two sub-regions (Trailpark + MTB Zone Willingen), lifts added
  (`tools/add_lifts.py`'s "sauerland" table). Several individual trails switched from their original
  source to OSM geometry where OSM turned out more accurate (case-by-case, not a blanket rule). MTB Zone
  Willingen's 8 trails sourced from Trailforks (no GPX endpoint exists for this sub-region). The four
  Trailpark Winterberg loops (Bremberg/Family First/Poppenberg/Sürenberg) were built from each loop's own
  recorded GPX (winterberg.de's Outdooractive-hosted API), with `tools/gpx_map_match.py` sequentially
  matching which of the 16 already-built Trailpark trails each loop actually rides, in ride order —
  connectors come from the loop's own recording, not a guess.
- New region: **Harz** (6 bike parks, 42 trails, 6 lifts, 9 places) — geometry from Trailforks' own
  `encodedpath`, harvested through the user's own logged-in Chrome and decoded in-browser (`tools/build_harz.py`);
  names/difficulty from the operator where certain, Trailforks otherwise; elevation backfilled since
  Trailforks embeds none.
- `tools/gpx_map_match.py` (sequential map-matching: reconstructs which trails/lifts a recorded GPX rides,
  in order, including repeats) gained a test harness and a density-sensitivity fix; used to fill a missing
  Tgantieni lift ride and, the day before, to reconstruct Tutti Frutti's real component-trail segments
  from a hand-authored Tourenbuilder export.
- **Added CHANGELOG.md itself** (this file).
- **The info panel heading now shows a trail's/Tour's difficulty** as the same colored dot the sidebar
  card and map label already use, with a hover tooltip (Sehr leicht/Leicht/Mittel/Schwer) — previously
  only implied by the elevation chart's line color.
- **The desktop info panel is wider (340px, up from 280px) and its elevation chart taller (72px, up from
  46px)**, to make the profile easier to read; touch/mobile unchanged. Checked live whether the existing
  profile data (100–200 points per trail, resampled by length) would look blocky stretched into the bigger
  chart — it doesn't, so no pipeline/data change was needed this round.
