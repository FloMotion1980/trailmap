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

## 2026-08-20
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
