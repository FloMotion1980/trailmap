# Backlog

## Bikecircus: 15 Trails ohne belastbare Betreiberzahl (2026-08-25)

34 der 49 Abfahrten in `bikecircus` stehen jetzt auf den Zahlen des Betreibers selbst
(`tools/harvest_oa_official.py`, plus bikepark-leogang.com fuer Hangman I). Diese 15 nicht, und der Grund
steht je Trail dabei -- ohne offizielle Zahl wird hier nicht geraten:

| Trail | wir | Betreiber | Trailforks | Warum offen |
|---|---|---|---|---|
| Blue-Line (SH07) | 2,7 km / 32 / 446 | keine Seite | 3,00 km / -407 | im Tourenverzeichnis des Betreibers nicht vorhanden |
| Pro-Line (SH42) | 2,2 / 74 / 484 | keine Seite | 1,71 / -339 | dito; Trailforks' Laenge weicht zudem um 22 % ab |
| Evil Eye Trail | 0,3 / 9 / 72 | keine Seite | 0,17 / -32 | dito |
| Wurzel-Trail (SH37) | 3,4 / 178 / 104 | 1,52 km / 25 / 0 | 3,40 / -156 | Betreiberseite beschreibt eine 1,5-km-Passage, Trailforks bestaetigt UNSERE Laenge -- zwei Definitionen desselben Namens |
| Hot Shots | 2,1 / 22 / 321 | 3,07 km | 2,82 km | **unsere Linie ist die kuerzeste von drei Quellen** -- hier ist die Geometrie fraglich, nicht die Zahl |
| Antonius Trail | 1,25 / 43 / 203 | 2,82 km | 1,24 km | Betreibertour enthaelt die Zufahrt |
| Matzalm / Forsthof / Schwarzleo / Knappen / AlteSchmiede | | nur `le-NN-...-tour` | Laengen wie unsere | die einzige Betreiberseite ist die RUNDE (auf == ab, bis 16,4 km) |
| Gateway | 0,55 / 7 / 51 | 0 / 2 | 0,55 / -38 | Betreiberzahl gibt den Hoehenunterschied der eigenen Linie nicht her (2 m gegen 44 m netto) |
| Schweinestberg / Streuboeden / Iglmoos | | Fieberbrunn hat kein Outdooractive-Projekt | nicht bei Trailforks | einzige Quelle waere die Bikepark-Seite, die keine Zahlen ausweist |

Wer das aufgreift: `up` ist die anfaellige Zahl. Sie stammt bei den Uebriggebliebenen weiter aus der
Aufzeichnung (GPS-Rauschen), waehrend jede geprueftе Betreiberangabe fuer eine Bikepark-Abfahrt **0** sagt.
Ein pauschales Nullsetzen ist trotzdem falsch: Wurzel-Trail und Asitz-Trail steigen wirklich.

General, cross-topic backlog for Trailmap — ideas, pending features and open decisions that aren't tied to
any single file. It travels with `git clone`/`git pull`, so it is the copy that survives switching device;
the assistant's own local memory notes mirror it, and this file wins if the two ever drift.

**Swept hard on 2026-08-21 at the user's own direction, and the shape of the file changed with it.** Three
things came out because they are finished, not because they were forgotten: all Touren rework (*"Touren
Nacharbeiten gibt es keine. Die sind jetzt alle gut soweit"*), the remaining region items for Gardasee,
Schwarzwald, Sauerland and Vogesen (*"für mich alles abgeschlossen"*), and rebuilding the Saalbach loops in
the Tourenbuilder. Two blocks moved to **Zurückgestellt** rather than out: the RIDE memory/crash work and
the open RIDE feature ideas. What is left at the top is what the user actually wants next.

Every built region has its own `docs/<region>.md` with the full sourcing account, so the per-region build
history is no longer repeated here — the table at the end is a status list, and git has the rest.

---

# Aktiv

## 1. Richtung App: Cloud, Accounts, App Stores

**The user's own priority as of 2026-08-21** (*"in Richtung App gehen ist weiterhin spannend"*). Approved as
a roadmap on 2026-08-02, and until now it lived ONLY in the assistant's local memory — exactly the failure
this file exists to prevent, so it is written down properly here. Full plan:
`C:\Users\flomo\.claude\plans\wie-k-nnen-wir-die-gleaming-peacock.md`.

Turn the Tourenbuilder from a local-only, `localStorage`-based feature into a cloud-backed, multi-user one,
and eventually ship through the real stores rather than only as an installable PWA.

**Decisions already locked in — do not re-open without a reason:**
- **Login via Google/Apple OAuth only**, no custom password system.
- **Supabase** as the backend (Postgres + Auth + Storage + Row Level Security), chosen specifically because
  `supabase-js` loads from a plain CDN `<script>` tag with no bundler — it fits this repo's "no build step,
  ever" architecture the same way the Leaflet tag does.
- Two tables: `routes` (Tourenbuilder exports) and `gpx_tracks` (imported GPX), **both with a nullable
  `share_token` column from day one**, even though the sharing UI ships later.
- Scope covers **both** builder-made routes and imported GPX, not just one.
- **Capacitor** for the store step — this project's first real build step (npm, native Xcode/Android Studio
  projects), planned for an isolated `mobile/` subfolder so day-to-day web dev (open `index.html`, no build)
  stays untouched. Apple mandates "Sign in with Apple" once Google login is offered (Guideline 4.8), which is
  why the auth decision above cannot be revisited cheaply later.

**Milestones**, deliberately incremental: M1 Google login + route sync (web/PWA) → M2 GPX import synced →
M3 link-sharing UI → M4–M6 per the plan file (Apple login, Capacitor, store submission).

**Ordering insight (2026-08-21, from the user's own question): shipping the CURRENT app to the stores first,
before accounts exist, is cheaper than the milestone order implies — and partly inverts its premise.** Apple's
"Sign in with Apple" obligation is triggered by offering Google login (Guideline 4.8); an app with **no**
accounts does not trigger it at all, so a first submission without auth is the simplest one this project will
ever make, not the hardest. It also has no server: nothing to run, nothing to pay monthly, nothing to break.
And store review is the big unknown in this whole plan, so meeting it once before auth is bolted on removes
risk from the sequence rather than adding it. Google Play first (25 $ once, milder review, buildable on
Windows), and its 14-day / 12-tester requirement for new personal accounts then runs down in the background
instead of blocking later. The one review risk to design for is Apple's Guideline 4.2 ("Minimum
Functionality"), which regularly catches apps that are a WebView pointed at a website — this app is not that
in substance (offline, GPS, real local computation), but the FORM has to match: Capacitor must bundle the
files into the app, never load `github.io`. That is what the `mobile/` plan already says.

**Three prerequisites that are NOT technical, found 2026-08-21 and verified in the repo. None of them is
about the stores' own rules — the stores do not care that something is also free on GitHub, and with no
`LICENSE` file the code is the user's own by default copyright. These are what actually blocks a release:**
- **`leaflet-rotate.js` is GPL-3** — the licence is in the file's own header, and the app ships it. GPL-3
  requires the whole combined work to be distributed under GPL-3 with source available, and GPL terms are
  a known conflict with App Store distribution terms (VLC was pulled over exactly this). **This applies
  whether or not the app costs anything**, so it is the first thing to settle before any Apple submission.
  The ways out are to replace the plugin or to solve map rotation without it — see `CLAUDE.md`'s rotation
  section for how deeply it is wired in (it patches Leaflet's core and every pane parent depends on it).
- **The tile servers are not licensed for this.** The app calls `tile.openstreetmap.org` directly, plus
  OpenTopoMap and Esri's World Imagery. OSM's Tile Usage Policy covers small, non-commercial use and rules
  out heavy or commercial traffic; a store app pointing a growing user base at donated infrastructure is
  what that policy exists to prevent. A store release realistically needs a paid tile provider, which is an
  ongoing cost the plan does not currently budget for.
- **Provenance of the trail data.** A large share of the geometry comes from Trailforks harvesting (see the
  region docs). That is one thing for private use and a materially different one when redistributed in a
  store app, and worse again in a paid one. Not a question the assistant can settle — flagged so it is a
  deliberate decision rather than an oversight.

**Consequence for pricing:** the honest reading is stores yes, **money not at first**. Shipping free defuses
the data question considerably and makes the tile question less pressing; GPL-3 has to be solved either way.

**Prerequisites the user has not started yet, and which gate M1**: a Supabase project and the OAuth app
registrations. Confirm those exist before writing code. The user also wants to revisit hosting options when
this resumes — specifically whether a backend could replace GitHub Pages entirely.

**Still open on the Tourenbuilder itself:**
- **Reuse the gap-closing logic in the builder.** The user's own point (*"das hilft uns auch für den
  Tourenbuilder später noch"*): way-matching, the rideability check and the connection logic are the same
  building blocks when two chosen elements have to be joined. It all sits in `tools/close_loop_gaps.py`
  (Python, build time) while the builder runs in the browser, so whether the logic gets ported or
  precomputed is undecided.

## 2. Trail-Rating und Beliebtheit aus Trailforks

**Requested 2026-08-21.** Pull Trailforks' own per-trail rating and popularity into the app. The user's
reasoning is the part that should drive the design: *"gerade in größeren Regionen mit vielen Trails kann das
ein echter Mehrwert sein"*. That is a real problem statement — the Gardasee holds 916 trails and the
Pfälzerwald 805, and a difficulty colour alone does not tell a visitor which twenty are worth the day.

Concept: **`docs/trail-rating-konzept.md`**. Read it before building.

**Stufe 1 ist gebaut und in 24 Regionen ausgerollt (2026-08-23/24).** Zwei Sortierachsen, der
Highlights-Regler, das ★ im Kartenlabel, die Info-Panel-Zeile. **1 777 von 4 555 Trails tragen eine
Bewertung, 3 800 eine gespeicherte Trailforks-ID** (auch die noch unbewerteten — die Zuordnung ist die teure
Hälfte und verfällt nicht). Abdeckung je Region: `docs/trail-rating-abdeckung.md`, erzeugt von
`tools/rating_report.py`. Verfahren und Regeln: `docs/trail-rating-konzept.md`. Suite:
`tests/browser/rating.js` (13 Fälle / 67 Checks).

Erledigt gegenüber der ursprünglichen Liste: das Datendichte-Gate ist auf Wunsch des Nutzers **entfernt**
(es poolte die aktiven Regionen und ließ das Feature ausgerechnet für Finale verschwinden); der
An-/Aus-Schalter wurde ein **Regler** über die echte Spanne der angezeigten Regionen; **alle vier
Prüfstapel sind auf null** (101 Fälle einzeln mit dem Nutzer entschieden, Begründungen in
`Material/<Region>/tf_manual.json`); die weiteren **Regionen sind ausgerollt**.

**Offen, in der Reihenfolge, in der es der Nutzer priorisiert hat:**
- **Die zwei Presets statt Zahlenschieber:** *"Muss man fahren"* (hoch bewertet UND viel gefahren — für den
  Erstbesucher) und *"Versteckte Perlen"* (hoch bewertet, wenig gefahren — für den, der die Region kennt).
  Der zweite Fall existiert nur, weil Bewertung und Beliebtheit zwei getrennte Zahlen sind; genau deshalb
  dürfen sie nie zu einem Score verrechnet werden. **Der Regler ersetzt das nicht** — er filtert auf einer
  Achse, die Presets kombinieren zwei.
- **Stern-Endpunkte auf der Karte**, Idee des Nutzers und von ihm gleich in die richtige Form gebracht: bei
  Highlight-Trails den Start-/Endpunkt-Kreis **mit einem Sternmuster umranden** — den Kreis also NICHT
  ersetzen. Das ist der Unterschied zwischen billig und riskant. Der erste Vorschlag (Layer-Typ tauschen)
  hätte die am stärksten verdrahteten Objekte der Karte angefasst: `syncStartDot` (vier Aufrufstellen),
  `showEndpoints`/`hideEndpoints`, `applyEndpointSize`, `endpointsCollide`, `applyReversedEndpoints` und die
  Solo-/Highlight-Deckkraft — `L.circleMarker` → divIcon bricht `setStyle`/`setRadius` an jeder davon. Als
  Umrandung fällt das weg: der Kreis bleibt das tragende Objekt, der Stern ist eine Schicht darüber, so wie
  der RIDE-Fokus-Halo eine ist. **Im RIDE-Modus ausdrücklich KEIN Stern.**
  Offene Frage fürs Bauen: Zacken als echte Geometrie (`L.polygon`, in Bildschirm-Pixeln nachskaliert wie
  die Richtungspfeile) oder als `dashArray` auf einem etwas größeren Kreis — Letzteres wäre eine Zeile,
  sieht aber eher nach Strichelung als nach Stern aus. Erst mit `visualize` ansehen, bevor Code entsteht.
- ~~**"In der Nähe"**~~ — **gebaut am 2026-08-25** (`docs/naehe-konzept.md`, Suite
  `tests/browser/nearby.js`). Was davon offen BLEIBT, mit Grund: die **erreichbare Stelle statt der
  Luftlinie** (braucht Routing über OSM-Daten — ein Trail, dessen Mitte 200 m entfernt vorbeiführt, dessen
  Einstieg aber drei Kilometer bergauf liegt, ist nicht „in der Nähe" in einem Sinn, der hilft), und die
  **zwei Presets** („Muss man fahren" / „Versteckte Perlen"), die auf derselben Mechanik aufsetzen würden.
- **Vom Lift erreichbare Trail-Einstiege** — beim Antippen eines Lifts zeigen, welche Trails man von dort
  aus anfahren kann, nach Bewertung sortiert. **Eigenes Feature, kein Teil der Umgebungssuche** (Nutzer,
  2026-08-24: "Das mit dem Lift würde ich nicht machen. Dann eher wenn man einen Lift anklickt, welche
  Startpunkte von Trails von dort aus erreichbar sind"). Der Unterschied ist inhaltlich, nicht technisch:
  die Umgebungssuche fragt "was liegt um diesen Punkt herum" und misst zur nächsten Stelle einer Linie,
  hier geht es um **Einstiege** und um die Fahrtrichtung — was man von der Bergstation aus hinunterfahren
  kann. Datenbasis ist da: Bike Kingdom (71 bewertete Trails, 12 Lifte), Harz (36/6), Livigno (28/7),
  Sölden, Paganella.
- **Tourenbuilder-Kandidaten ranken** — `junctionCandidates` liefert die Anschlüsse schon, sie nach
  Bewertung zu ordnen ist ein Zweizeiler mit echtem Effekt.
- **Touren erben die Bewertung ihrer Komponenten** (längengewichtet aus `trailSegments`), damit der
  Touren-Abschnitt überhaupt sortierbar wird. **`merge_sections()` rechnet den verwandten Fall schon** —
  mehrere Trailforks-Abschnitte auf einen unserer Trails, stimmen-gewichtet; für Touren wäre es dieselbe
  Rechnung eine Ebene höher, nur längen- statt stimmen-gewichtet.

**Neu aufgekommen beim Durchgehen der Fälle (2026-08-24):**
- **Werte auffrischen**: die Zahlen sind auf `asOf` datiert und altern. Mit dem gespeicherten `tf`-Slug ist
  ein Update ein Ernte-Lauf plus ein Wörterbuch-Zugriff — `tools/harvest_tf_ratings.py` kann das schon,
  gebraucht wird nur ein Auslöser (z. B. halbjährlich) und ein Blick darauf, was sich verschoben hat.
- **Trailforks-Linien ohne Gegenstück bei uns** sind die Kandidatenliste für fehlende Trails — in Finale 55,
  und in jeder anderen Region gibt es dieselbe Liste. `review_cases.py` zeigt sie noch nicht; die Zahl steht
  im Lauf von `match_trailforks.py` als "none".
- **Zwei mögliche Duplikate in unseren EIGENEN Daten**, aufgedeckt durch Mehrfachansprüche: `Cava-Green
  Carpet` ↔ `Cava - Tappeto Verde` (wörtlich derselbe Name in zwei Sprachen) und `Bondi` ↔ `Bondi Traverse`.
  Beide sind als Zuordnung entschieden, aber die Frage, ob wir denselben Trail zweimal führen, ist offen.
- **Sehr wenige Stimmen sagen fast nichts**: `tiejer-wald` und `medregen-langwies` tragen beide exakt 4,23
  bei je 3 Stimmen, weil der bayessche Wert dort fast auf dem Regionsmittel liegt. Der Nutzer hat
  entschieden, das vorerst so zu lassen — eine sichtbare Unterscheidung (ausgegrauter Stern o. ä.) wäre die
  Ausbaustufe, falls es je stört.

## 3. Regionen, die noch offen sind

**Elba und Kronplatz sind am 2026-08-25 gebaut** (222 bzw. 23 Trails, siehe `docs/elba.md` und
`docs/kronplatz.md`) und stehen deshalb nicht mehr hier. Kronplatz war seit 2026-07 an der Geometrie
hängengeblieben — der fünfte Beschaffungsweg, Trailforks, trägt sie; die vier gescheiterten stehen weiter
in `docs/kronplatz-recherche.md`, damit sie niemand wiederholt. **Offen bei Kronplatz bleibt genau einer der 19 offiziellen Trails**, der Mini Furcia Trail (210 m): weder bei Trailforks noch in OSM noch bei bike-holidays gibt es eine Linie. Nächster Ansatz wäre eine eigene Aufzeichnung. Dragon und Gassl kamen über Komoot dazu — siehe `docs/kronplatz.md`, das Verfahren taugt für jede Region, in der ein Betreiber auf Komoot verlinkt.

Offen sind jetzt **Geißkopf** und **Bormio**, plus die Vorschlagsliste aus der Trailforks-Recherche
weiter unten.

**Bormio und Umland** — vom Nutzer am 2026-08-25 gewünscht, aus eigener Erfahrung: *"Da war ich schon mal im
Bikepark und ganz oben ging auch eine epische Tour los… Bormio 3000 nach Sankt Katharina oder so"*. Das ist
die **Bormio 3000 → Santa Caterina Valfurva**-Abfahrt über das Valfurva, und sie ist der eigentliche Grund
für die Region: eine Tour, nicht nur ein Park. Was vor dem Bauen zu klären ist:
- **Zuschnitt.** Bormio, Valdidentro, Valdisotto, Valfurva und Santa Caterina sind ein zusammenhängendes
  Becken; Livigno ist bereits eine eigene Region und liegt nur den Foscagno-Pass entfernt, Aprica und
  Teglio/Valtellina hängen talabwärts an. Ob Bormio allein steht oder als „Alta Valtellina" mit Aprica und
  dem Valtellina-Sonnenhang zusammengeht, ist eine Entscheidung wie damals Livigno gegen Waldmeister.
- **Lifte.** Bormio 2000/3000, Bormio-Talstation und die Bahnen in Santa Caterina — nach der Regel aus
  `docs/lifts-feature.md` von der Sommerseite des Betreibers, nicht aus OSM-Tags.
- **Quelle.** Trailforks hat die Ecke unter `lombardia`; ob der Bikepark eigene GPX mit eigener
  Schwierigkeit veröffentlicht, ist ungeprüft — Betreiber zuerst, Trailforks als Rückfall.
- **Die epische Tour selbst** ist am ehesten ein Fall für `tools/gpx_map_match.py` oder den Tourenbuilder,
  nicht für den Trailforks-Bau: sie besteht aus mehreren Abschnitten plus Verbindern.

**Geißkopf** (Bodenmais, Bayerischer Wald) ist geografisch von Freiburg/Todtnau (beide Schwarzwald)
getrennt — NICHT annehmen, dass die drei eine Regionsgruppe bilden wie Sauerland/Upland; die Gruppierung
beim Aufgreifen nach echter Entfernung entscheiden, dieselbe Abwägung wie bei Livigno/Waldmeister. Quellen:
- https://mtbzone-bikepark.com/geisskopf/strecken — Trail-Übersicht (dieselbe Seite wie Willingens; prüfen,
  ob sie für diesen Park direkte GPX hat, für Willingen hatte sie keine).
- Trailforks führt `mtb-zone-bikepark-geisskopf` als eigene Region, und der Landkreis-Blick auf Bayern
  (unten) zeigt „Lamer Winkel" mit 28 Trails / 54 km gleich daneben.

### Trailforks-Recherche DE/AT/CH/IT/FR (2026-08-25, auf Wunsch des Nutzers)

**Methode, damit die Zahlen einzuordnen sind:** je Bundesland/Kanton/Region die komplette
Trailforks-Trailtabelle geholt (`tools/harvest_trailforks.py --tables`) und nach der eigenen
`riding area`-Spalte gruppiert; Zufahrten, Forststraßen und Lifte (`ACCESS_DIFF`) sind rausgerechnet.
Die Zahl ist also **bewertete Trails**, und die Kilometer sind Trailforks' eigene Längen. Gemessen:
Österreich, Bayern, Baden-Württemberg, NRW, Sachsen, Hessen, Niedersachsen, Thüringen, Graubünden, Wallis,
Tessin, Aostatal, Trentino-Südtirol, Lombardei, Savoie, Haute-Savoie, Hautes-Alpes.

Zwei Vorbehalte, bevor jemand eine Zahl für bare Münze nimmt: die Gebietsspalte ist ein
**Verwaltungskasten**, kein Revier (siehe Elba und Gardasee), und eine hohe Trailzahl bei kleiner
Kilometersumme heißt „viele kurze Linien" — 163 Trails auf 79 km im Landkreis Regensburg sind ein
Stadtwald, keine Enduro-Region. **Die Kilometer je Trail sind das bessere Signal als die reine Anzahl.**

#### Deutschland — die große Lücke sind die Bayerischen Voralpen

| Kandidat | Trails | km | Gebiete |
|---|---:|---:|---|
| **Bayerische Voralpen** | ~360 | ~640 | Garmisch (84/167), Tegernsee-Kreuth (63/109), Kochelsee-Walchensee-Jachenau (54/95), Schliersee-Spitzingsee (41/51), Bad Tölz/Lenggries (34/70), Ammergauer Alpen (23/44), Mittenwald/Wallgau (21/37), Füssen (19/39) |
| **Heidelberg / Bergstraße** | ~350 | ~200 | Königstuhl (162/71), Weißer Stein (56/45), Neckargemünd (39), Neckarsteinach (38), Kleiner Odenwald (29), Heidelberg (23) — grenzt direkt an den gebauten Odenwald |
| **Bergisches Land / Rheinland** | ~400 | ~230 | Düsseldorf (98), Aaper & Grafenberger Wald (87), Ratingen (62), Burscheid (52), Erkrath (50), Lindlar (37), Bergisch Gladbach (31) |
| **Chiemgau / Berchtesgaden** | ~210 | ~150 | Bad Reichenhall (63/38), Berchtesgadener Land (39/32), Südl. Rupertiwinkel (35), Samerberg (25), Kampenwand (24), Lkr. Rosenheim (23) |
| **Schwäbische Alb** | ~200 | ~160 | Bad Urach (42/44), Balingen (32/40), Schönbuch (27), Tübingen (25), Geislingen (24), Lkr. Esslingen (24) |
| **Thüringer Wald** | ~150 | ~110 | Ilmenau (58/35), Ilm-Kreis (36), Suhl (31), Inselsberg (11), Bike Park Oberhof (11) |
| **Erzgebirge** | ~120 | ~90 | Aue-Bad Schlema (36), Trailcenter Rabenberg (25), Stollberg (20), Zwönitz (13), Lauter-Bernsbach (11) |
| Bayerischer Wald (= Geißkopf, oben) | ~90 | ~120 | Regen (39/37), Lamer Winkel (28/54) plus die Bikepark-Region selbst |
| Siegerland | ~85 | ~50 | Siegen (58/29), Kreuztal (27/15) |

Nicht empfohlen, obwohl die Zahlen groß sind: **Landkreis Regensburg (163/79) und Naabdelta (120/81)** —
das sind ~0,5–0,7 km je Trail, also Stadt- und Flussauenwege. Dieselbe Rechnung sortiert Leipzig (87/56)
und Düsseldorfs Aaper Wald (87/26) aus, falls jemand nach Trailzahl statt nach Kilometern sucht.

#### Österreich — nichts Großes mehr, aber mehrere gute mittlere

Acht österreichische Regionen sind gebaut. Was in der Landestabelle noch heraussticht:

| Kandidat | Trails | km | Gebiete |
|---|---:|---:|---|
| **Innsbruck** | 145 | — | eigene Trailforks-Region (`innsbruck`); Nordkette, Mutterer Alm, Arzler Alm, Bike-Republic-Umfeld |
| **Vorarlberger Rheintal** | ~130 | ~120 | Dornbirn (37/40), Rankweil (27), Bregenz (20/23), Götzis (16), Feldkirch (15), Bludenz (12/24) — ergänzt das gebaute Brandnertal |
| **Wagrain-Kleinarl** | 62 | — | eigene Region (`wagrain`), Pongau |
| **Kärntner Seen** | ~85 | ~60 | Trailcenter Faaker See (26/19), Turracher Höhe (22/11), Ossiacher See (17/15), Simonhöhe (16/7) |
| **Wienerwald & Wiener Alpen** | ~100 | ~110 | Trail-Area Wien Nord (20/27), Wexl Trails (16/28), Trailarea Göttweig (14), Anninger (11), Trailcenter Wien (11), Semmering (11/9), Alpen Bikepark Schneeberg (9) |
| **Steiermark Süd/Ost** | ~110 | ~80 | Bad Gleichenberg (28/25), Kapfenberg (28/26), Lannach (12), Graz (10), Schöckl (8), Judenburg (9) |
| Osttirol/Lienz | ~36 | — | `osttirol` (28) + `lienz` (8) |
| Bad Gastein / Lungau | ~46 | — | `bad-gastein` (23), `lungau` (23) |

#### Schweiz — Davos ist der offensichtlichste Kandidat des ganzen Alpenbogens

| Kandidat | Trails | km | Anmerkung |
|---|---:|---:|---|
| **Davos Klosters** | 153 | 279 | größte unerschlossene Einzelregion in GR; direkt neben dem gebauten Bike Kingdom (153/179) |
| **Zermatt – Matterhorn** | 152 | 128 | eigene Trailforks-Region, dazu Saas-Fee/Saastal (35/46) und Grächen (39/40) |
| **Val Surses** | 130 | 131 | Savognin/Bivio, hängt an Bike Kingdom und Albula |
| **Scuol – Pure Alpine Trails** | 111 | 121 | Unterengadin, plus Val Müstair (88/104) direkt daneben |
| **Verbier / Val de Bagnes** | ~105 | ~85 | Verbier (67/46), Bruson (37/34) |
| **Surselva / Rheinquelle** | ~150 | ~160 | Rheinquelle (94/85), Obersaxen Mundaun (27), Sumvitg (26), Breil/Brigels (23) — nördlich von Laax |
| **Oberengadin** | ~140 | ~170 | Engadin (62/80), Bergün Filisur (38/70), Pontresina (22/31), S-chanf (20/35) |
| **Wallis Mittelland** | ~280 | ~230 | Moosalp (100/82), Ovronnaz (76/41), Fully (68/41), Chamoson (64/40), Visperterminen (58/65), Leuk (57/39) |
| **Goms / Obergoms** | ~140 | ~140 | Goms (91/95), Obergoms (48/55), Fiesch (33/41), Blatten-Belalp (36/27) |
| **Crans-Montana + Val d'Anniviers** | ~160 | ~150 | Crans-Montana (72/77), St-Luc (51/54), Grimentz (35/39) |
| **Tessin** | ~350 | ~400 | Cardada Cimetta (59/60), Bellinzona (54/77), Monte San Giorgio (50/50), Valle di Muggio (47/62), Valle di Blenio (46/58), Monte Bar (44/66), Airolo (31/39), Monte Tamaro (22/42) |
| **Valposchiavo** | 79 | 109 | eigenes Tal südlich des Berninapasses, grenzt an Livigno |

#### Italien — Bormio steht oben, weil der Nutzer es bestellt hat

| Kandidat | Trails | km | Gebiete |
|---|---:|---:|---|
| **Alta Valtellina / Bormio** | ~113 | ~275 | Valdidentro (40/164), Stelvio Natural Trail Park (26/98), Bormio (24/61), Oga Natural Trails (10/16), Valdisotto (9/26), Valfurva (4/4) |
| … talabwärts erweiterbar | +114 | +290 | Sondrio (41/170), Aprica (27/71), Teglio (26/51), Tirano (11/19), Grosio (9/40) |
| **Aostatal** | ~300 | ~600 | Aosta (70/132), Introd (36/73), Courmayeur (36/65), Val d'Ayas (34/71), Pila Bikeland (27/47 plus Pila 18/23), Brusson (25/46), Cervino (19/49), La Thuile Bike World (18/44) |
| **Vinschgau / Meran** | ~134 | ~345 | Vinschgau (63/198), Burggrafenamt (50/111), Latsch (21/36) — Südtiroler Nachbar von Kronplatz |
| **Primiero / San Martino** | ~135 | ~254 | Comunità di Primiero (84/134), Vanoi (29/63), San Martino di Castrozza (22/57) |
| **Val di Sole** | 50 | 148 | eigene Region (`val-di-sole-bike-land`), Weltcup-Bikepark Commezzadura |
| **Bergamasker Alpen** | ~240 | ~430 | Castione della Presolana (50/108), Monte Resegone (49/84), Zogno (48/80), Bergamo (45/90), Grigna Meridionale (44/48) |
| Dolomiten-Rest | ~45 | ~75 | Fassa Bike District (30/40), Selva Val Gardena (13/24) — ergänzt Paganella und Kronplatz |
| Bozen / Eisacktal | ~115 | ~390 | Bolzano (45/163), Tramin (38/74), Brixen (18/138), Eppan (14/13) |

#### Frankreich — drei sehr große Blöcke, alle unangetastet

Portes du Soleil ist gebaut (80 Trails). Daneben liegt sehr viel mehr, als diese eine Region hergibt:

| Kandidat | Trails | km | Gebiete |
|---|---:|---:|---|
| **Tarentaise / Vanoise** | ~450 | ~800 | Belleville Bikepark (95/198), Tignes (92/97, dazu Bike Park Tignes-Val d'Isère 25/50), Sainte-Foy-Tarentaise (79/101), Val Cenis (70/125), Méribel Bikepark (51/86), Les Arcs Bikepark (44/78), Val-d'Isère (43/91), Bourg St. Maurice (37/59) |
| **Annecy / Aravis** | ~450 | ~360 | Talloires (88/71), Le Semnoz (84/42), Thônes (65/62), Faverges-Seythenex (46/40), Mont Salève (45/47), Le Grand Bornand (43/50), Doussard (42/34), La Clusaz Bike Park (40/39) |
| **Mont-Blanc / Chamonix** | ~220 | ~250 | Chamonix (71/98), Les Houches (49/47), Passy (36/43), Saint-Gervais (34/68), Vallorcine (28/23), Megève (28/26) |
| **Briançonnais** | ~190 | ~290 | Névache (48/83), Serre Chevalier Bike Park (46/69), Briançon (30/44), Puy-Saint-André (25/27), Le Monêtier-les-Bains (21/46), La Grave (17/30) |
| **Queyras** | ~140 | ~250 | Arvieux (45/90), Château-Ville-Vieille (23/52), Abriès-Ristolas (22/51 plus Abries Bike Park 16/23), Ceillac (16/40), Aiguilles (15/42) |
| **Embrunais / Ubaye** | ~105 | ~180 | Embrun (44/56), Vars (27/64), Orcières (17/44), Les Orres Bike Park (16/30), Risoul (15/26) |
| Dévoluy / Gap | ~105 | ~130 | Devoluy (47/68), Tallard (33/31), Gap (24/19) |

**Gebaut in der Nacht auf 2026-08-26: die ersten sechs dieser Liste.** Davos Klosters, Vinschgau & Meran,
Bormio & Valtellina, Bayerische Voralpen, Aostatal und Tarentaise & Vanoise stehen in der App. Das
gemeinsame Verfahren und was allen sechs noch fehlt: **`docs/sechs-regionen-2026-08.md`**, je Region
`docs/<region>.md`. **Zwei Nacharbeiten sind ausdrücklich offen und stehen weiter unten im Abschnitt
„Nacharbeit an den sechs Regionen".** Was aus den Tabellen unten noch NICHT gebaut ist, bleibt gültig:
Zermatt, Val Surses, Scuol, Tessin, Surselva, Wallis, Primiero, Bergamasker Alpen, Annecy/Aravis,
Mont-Blanc, Briançonnais, Queyras — und auf deutscher Seite Heidelberg, Schwäbische Alb, Thüringer Wald,
Erzgebirge, Geißkopf.

**Eine Reihenfolge, falls eine gebraucht wird** — nach „viel Trail je Aufwand", und mit dem, was die App
schon kann: **1. Bormio** (Nutzerwunsch, ~113 Trails, Lifte vorhanden), **2. Davos Klosters** (153 Trails /
279 km, die größte einzelne Lücke im Alpenbogen), **3. Bayerische Voralpen** (die größte deutsche Lücke,
~360/640), **4. Tarentaise** (~450/800, aber lauter Bikeparks mit eigenen Betreiberangaben, also die
meiste Zusatzrecherche), **5. Aostatal** (~300/600).

Die Rohtabellen der Recherche sind nicht eingecheckt — sie sind mit einem `--tables`-Lauf je Region in
Minuten reproduzierbar, und eingefroren würden sie nur veralten.

**Pfälzerwald note (for whenever Trailforks trails are added there)**: this region already has 437
trails and is far denser than any region `tools/gpx_map_match.py` has been validated against so far
(Livigno: 21 candidates, Bike Kingdom: ~130). Expect `strict_thresh_m` to need lowering and the loose
second pass to fire more often — see the tool's own "Tune per region" docstring note, and
`tools/test_gpx_map_match.py` for the regression-testing pattern to extend before trusting any new
segmented tour built there.

## 3b. Nacharbeit an den sechs Regionen vom 2026-08-26

Die sechs sind gebaut und fahrbar; zwei Dinge fehlen ihnen allen, und eines davon ist eine echte Schuld
gegenüber der stehenden Regel.

**1. Die Betreiber-Schwierigkeit für Aostatal und Tarentaise.** Alle sechs tragen Trailforks' Wertung. Für
Davos, Vinschgau, Bormio und die Voralpen ist das sachlich richtig — gewachsene Trailnetze ohne Betreiber,
der eine Trailliste führt. Für die anderen beiden ist es das **nicht**: Pila Bikeland, La Thuile Bike World,
Cervino und Champoluc im Aostatal, Les Arcs, Tignes, Méribel, Belleville, La Plagne und Valmorel in der
Tarentaise führen eigene Trailtabellen mit eigenen Graden, und nach `CLAUDE.md`s stehender Regel gewinnen
die. Das Werkzeug dafür steht: `diff_override` in `tools/build_trailforks_region.py` nimmt je Trail die
Farbe UND die Formulierung des Betreibers, so wie es bei Kronplatz gemacht ist. Es sind zehn
Betreiberseiten — eine eigene Sitzung, keine Fußnote.

**2. Lifte für alle sechs.** Kein `lifts`-Array, und das ist eine bewusste Auslassung: `docs/lifts-feature.md`
verlangt die Sommerseite des Betreibers und schließt OSMs `aerialway:bicycle` ausdrücklich aus — bei
Kronplatz stand das Tag am Vortag bei zwei Bahnen falsch. **Für Davos ist die halbe Arbeit schon getan**
(siehe `docs/davos.md`): der Betreiber sagt „auf insgesamt sechs Stand- und Luftseilbahnen ist der Transport
mit dem Mountainbike möglich", nennt sie aber nicht namentlich, und die Live-Liste kommt per JavaScript.

**Stand 2026-08-26 nach dem ersten Blick des Nutzers auf die live gegangene Region:** Bormio hat seine
**drei Lifte** (Betreibertabelle, siehe unten), die anderen fünf noch nicht.

**Bormio: der Bikepark ist eine eigene Sub-Region (2026-08-26, Wunsch des Nutzers), die Grade stehen auf
den Betreiberangaben.** Fünf der sieben Pisten sind gebaut, `Viper` von rot auf blau korrigiert. Neu dafür:
`sub_override` in `tools/build_trailforks_region.py` — der Bikepark ist durch die Betreiberliste definiert,
nicht durch Geografie, und seine Linien fielen nach Nachbarschaft in zwei Täler. Es bleiben **zwei offene
Punkte**, beide ohne Quelle und deshalb nicht geraten:

* **Panther fehlt** (blu, 300 m / 40 Hm) — nicht bei Trailforks, nicht in OSM, nicht bei bike-holidays.
* **Autobahn und Zombie sind eine Linie.** Vier Quellen geprüft und keine trennt sie: beide Betreiberseiten
  nennen dieselben Zahlen (und Autobahns 548 Hm auf 800 m widersprechen der eigenen Angabe „max 19°"), die
  Summen passen nicht (2 200 gegen 2 593 m, 801 gegen 496 Hm), unser Profil läuft mit 14–25 % ohne
  Bruchstelle durch, OSM kennt keine der sieben Pisten namentlich, und die Bikepark-Karte des Betreibers ist
  ein Rasterbild mit den Namen nur in der Legende. Lösen würde es eine Aufzeichnung einer der beiden.

**3. ~~Die Tour Bormio 3000 → Santa Caterina~~ — gebaut am 2026-08-26.** Der Nutzer lieferte die
bergfex-URL (Tour 2861858); deren GPX-Download braucht kein Konto, nur einen `Referer`. Gegen die
Betreiberzahlen geprüft (12,29 gegen 12,3 km, beide Endhöhen auf 20 m), als Trailrunde mit
`tools/gpx_map_match.py` zerlegt: 91 % der Linie auf benannten Trails, sechs Abschnitte. **Dabei fiel die
Vermutung vom Vortag:** die Tour fährt `Panoramico Le Cune`, nicht `Le Cune` — von dem berührt sie nur die
letzten 750 m. Details in `docs/bormio.md`.

## 4. Test-Abdeckung: was noch keine Suite beansprucht

Swept 2026-08-21 by asking the runner itself which tracked files no suite's `@files` claims — that list IS
the to-do list for the library (`tests/README.md` says as much). Closed that night: the Trailforks
harvest/build pair (new `trailforks` suite), `close_loop_gaps.py`'s offline half (new `loopgaps` suite), and
`gpx_map_match.py`, whose own regression harness existed but **always exited 0** and was claimed by nothing
— it compares against a committed per-case baseline now and is wired in as the `gpxmatch` suite (SLOW,
~2–4 min, selected only when the matcher changes).

Still unclaimed, in rough order of what a silent regression would cost:

- **`tools/add_region_places.py`** — real logic nobody tests: the per-sub-region quota,
  `MIN_SEPARATION_KM`, the population/type ranking. A bad change here quietly makes a region's labels
  useless (it already needed a per-region cap for the Gardasee, see `docs/gardasee.md`). Offline-testable
  apart from the Overpass call.
- **`tools/region_dupe_check.py`** — the duplicate metric every new region's build leans on. The metric's
  own primitives in `pfaelzerwald_containment.py` are claimed; the wrapper is not.
- **`tools/harvest_schwarzwald_tf.py`** — superseded by `harvest_trailforks.py` for anything new. Worth
  DELETING rather than testing, once someone confirms nothing still runs it.
- One-off region scripts (`pfaelzerwald_*.py`, `vogesen_boundary.py`, `add_lifts.py`,
  `add_harz_lifts_places.py`, `gap_variants.py`) and the two harvest servers (`harvest_receiver.py`,
  `oa_harvest_server.py`). These ran once and produced committed data that IS checked (`regiondata`,
  `validate_region.py`), so testing them now buys little — leave them.


---

# Zurückgestellt

Both blocks were pushed back by the user on 2026-08-21. Kept in full: the measurements and the rejected
options are worth as much as the open questions.

## RIDE-Modus: Speicher und der weiße Bildschirm

*"Der Ride Absturz ist mir erstmal nicht so wichtig. Wir haben eine einfache Möglichkeit, es zu beheben und
im Moment tritt es nicht auf."* The "simple way" is the first bullet below — gating the empty lift pane, the
same move that saved 40 MB on the builder pane. It is ready when the crash comes back.

- **Open, measured, partly fixed: RIDE mode carries ~9x the vector-renderer memory of the normal map — the
  single most likely cause of the white-screen crashes, and the biggest remaining lever in the app.**
  **Superseded numbers below**: the table further down said 2.3x/89 MB across three panes; a re-measurement at
  a real 375x812 phone viewport with RIDE fully applied gives **33 Mpx / ~126 MB across FOUR panes**, against
  3.6 Mpx / ~14 MB north-up. Also corrected: **tiles play no part**, in either zoom direction (20 tiles vs 25,
  one level, JS heap 12–14 MB) — the earlier "tile burst" explanation was wrong, which is why `RIDE_MIN_ZOOM`
  did not close the crash. It blocked one route to the cliff; the user found the other by zooming far IN
  (2026-08-20, Donnersberg).
  Per-pane, RIDE + rotation on that viewport:

  | pane | surface | paths |
  |---|---|---|
  | overlay | 3235x3236 = 39.9 MB | 655 |
  | liftBand | 3235x3236 = 39.9 MB | 63 |
  | builder | 3235x3236 = 39.9 MB | **0** |
  | tourSegHit | 1245x1244 = 5.9 MB | 92 |

  **Done (2026-08-20): the builder pane is gone**, −40 MB, no visual change — `eachVectorRenderer` was
  materialising it by asking `map.getRenderer()` about a pane nothing used. 126 → 86 MB. **Still open, in
  order of appeal:**
  - **`LIFT_BAND_PANE` pays a full 39.9 MB for 63 short lift paths, and is a wholly empty surface in every
    region that has no lifts** — Donnersberg, Pfälzerwald, Odenwald, Finale, and now the Gardasee and
    Madeira. **Measured again 2026-08-21 with only the Gardasee active** (911 trails, 1 822 paths, no lifts)
    at a 375x812 viewport: RIDE costs 30.4 MB across two panes and **15.2 MB of that is the empty lift
    pane** — half the region's entire vector footprint for zero paths. That is the same waste the builder
    pane paid until it was removed, in a region that cannot ever use the pane at all, which makes this the
    clearest case yet for gating it on whether the active regions have any lifts. Two questions worth separating:
    whether it needs the rotation padding at all (re-rasterising 63 short lines per degree is far cheaper than
    doing it for 655), and whether it should exist when the active regions have no lifts. The pane itself
    cannot simply be dropped: the lift's grey mask must sit UNDER the trails and OVER the tiles, and Leaflet
    offers no z-index between its own tilePane (200) and overlayPane (400), which is the entire reason for a
    third pane at 350.
  - **Cap `rotationPadding()`** — declined twice (see below) and worth re-raising now that the zoom guard has
    demonstrably not closed the crash. 0.938 → 0.65 takes roughly a third off every remaining surface.
  - **The original entry's own options (a)–(d) still stand** for the elongation itself.
- **Original entry, kept for the reasoning (its numbers are superseded above): RIDE mode more than doubles the
  vector-renderer memory, and that is why zooming far out could kill the app.** **The crash is NOT closed, and "it did not happen today" is not evidence that it is.** A `RIDE_MIN_ZOOM`
  of 10 was tried and removed the same day: it stopped the user's zoom-OUT reproduction — confirmed on
  their phone, recorded as fixed — and then the crash returned zoomed far IN. After the empty builder pane
  came out (126 → 86 MB) the user tested again, zooming freely with no clamp, and reported no crash so far
  (2026-08-20). Treat that as encouraging and nothing more: a memory kill needs enough to accumulate, so a
  short session proves less than it feels like, and the same wording was already wrong once today, but the underlying overhead is untouched and will matter again for a bigger
  region or an older phone. Measured on a 375x812 viewport at a fixed 45° bearing:

  | | container | ratio | `rotationPadding()` | painted box | 3 renderer panes |
  |---|---|---|---|---|---|
  | rotation, RIDE off | 375x757 | 2.02 | 0.646 | 1835x1835 | ~38 MB |
  | rotation, RIDE on | 375x995 | 2.65 | **0.938** | **2786x2786** | **~89 MB** |

  Two individually-correct mechanisms colliding: RIDE's look-ahead inflates `#map` to place the position dot a
  third up from the bottom, and `rotationPadding()` must cover the circle the container sweeps, with the SHORT
  axis deciding — so a more elongated container costs quadratically. **The obvious fix, capping the padding, was
  offered to the user and declined** in favour of the zoom limit, and rightly: that padding exists because the
  user reported the rotation stutter, so capping it trades their own fix back. Options if this is ever picked up
  again, in rough order of appeal: (a) derive the padding from the radius needed to cover the VISIBLE crop
  rather than the whole inflated container — correct, but measured at only ~18% saving, since the crop reaches
  almost the full height anyway; (b) cap the padding only while RIDE is on and accept some stutter there; (c)
  shrink `RIDE_LOOKAHEAD_FRACTION`, which attacks the elongation itself but changes a placement the user chose
  deliberately; (d) drop the whole SVG-under-rotation approach for a GL/vector-tile map, which is the only one
  that removes the class of problem rather than the instance.
  **A second, unexplained observation from the same session, worth knowing before assuming memory is the whole
  story:** with the zoom guard mutated away, one of three `ride` suite runs threw `Invalid LatLng object: (NaN,
  NaN)` out of Leaflet. It did not reproduce and it is NOT the reported crash (a throw shows the fatal panel;
  the report is a white page) — but a far-zoomed-out rotated RIDE map may be a broken state and not just an
  expensive one. Nobody has chased this down.

## RIDE-Modus: offene Feature-Ideen

*"Ob wir den Ride Modus erweitern auf einen Aufnahmemodus oder die Strecken hintendran grau machen weiß ich
noch nicht. Kann auch mal hinter."*

- **A toggle button for map orientation, instead of driving it from the phone's own sensors.**
  Currently "Blickrichtung oben" is compass-driven (`setHeadingUp`/`handleOrientation`) and is
  auto-enabled when RIDE starts. The user wants a manual toggle instead — unclear yet whether this
  means replacing the compass entirely (e.g. a button that flips between a couple of fixed
  orientations) or just adding a manual on/off toggle *for* the existing compass-driven rotation
  (which already sort of exists as `#bearingBtn`) — needs clarifying next time, don't assume.

- **A separate "Tracking" concept in addition to RIDE mode** — the user explicitly said they don't yet
  know whether this is its own mode or connected to RIDE ("Ob das ein eigener Modus ist oder
  zusammenhängt weiß ich noch nicht"). Sounds like it could be about recording/saving a ridden track
  (GPX-style), distinct from RIDE's existing live GPS-follow display — but this is a guess, not
  confirmed. Needs a real discussion before any design/implementation, not just an assumption from the
  name.

  - **The outer ring's colour is NOT a placeholder — the user corrected this explicitly (2026-08-16):
    orange and grey are both permanent, meaning RIDE PROGRESS, not a temporary stand-in for one another.**
    When a RIDE session on a tour starts, the entire tour's outer ring is orange (nothing ridden yet); as
    the rider progresses, the outer ring behind the live position turns grey, ahead of it stays orange —
    exactly the Komoot-style already-ridden-vs-still-to-come split from the earlier bullet, just
    implemented as the SAME outer-ring layer rather than a separate feature. This needs live
    progress-along-the-line tracking (nearest point reached on the open tour's `TRAIL_GEO`) feeding a
    split point into the per-point outer-ring colour — real RIDE-mode work, not just a CSS/style change,
    so still backlog rather than something to build alongside the mockup styling. Outside of an active
    RIDE session (or before the rider has moved), the ring is presumably all-orange by default (nothing
    ridden yet) — not yet confirmed with the user what it should look like when a tour is merely selected
    without RIDE running.

- **Switch to "Straße dezent" automatically while `html.ride-mode` is on**, and back afterwards — the one
  half of the 2026-08-16 contrast request that was never done. What shipped instead was "Straße / Straße
  dezent / Straße hell" as three peer basemaps with "dezent" the first-visit default; the automatic switch
  during RIDE stayed open.

  - **Compass appears to freeze for a few seconds repeatedly while riding** — traced to intended
    behaviour, not a bug: `handleOrientation`'s bearing deliberately FREEZES (rather than resetting)
    when magnetometer readings go stale, and a bike's own metal frame/phone-mount magnets/vibration are
    the likely real-world cause of those brief dropouts — the user's own instinct that GPS reception is
    unrelated is correct. Komoot likely avoids this by driving its direction indicator mainly from GPS
    course-over-ground while moving rather than the magnetometer; this app currently prioritises the
    compass and only falls back to GPS course when there is no compass reading at all. A speed-gated
    hybrid (GPS course above some km/h, compass at a standstill) was floated as a possible fix but is a
    real design change, not implemented, not yet decided.

---

# Gebaute Regionen (Stand 2026-08-26)

36 Regionen, **6872 Trails, 140 Lifte, 102 Touren**. Jede hat ihr eigenes `docs/<region>.md` bzw. ihr
Build-Skript in `tools/` mit der vollen Quellen-Herkunft; `python tools/validate_region.py` prüft alle.
Die sechs vom 2026-08-26 teilen sich `docs/sechs-regionen-2026-08.md` für das gemeinsame Verfahren.

| Region | Label | Trails | Lifte | Touren | Sub-Regionen |
|---|---|---:|---:|---:|---:|
| `gardasee` | Gardasee & Trentino | 916 | 2 | 5 | 10 |
| `pfaelzerwald` | Mountainbikepark Pfälzerwald | 805 | 0 | 42 | 9 |
| `tarentaise` | Tarentaise & Vanoise | 710 | 0 | 0 | 9 |
| `schwarzwald` | Schwarzwald | 622 | 3 | 4 | 10 |
| `nordvogesen` | Nordvogesen | 483 | 0 | 0 | 7 |
| `suedvogesen` | Südvogesen | 474 | 3 | 0 | 12 |
| `aostatal` | Aostatal | 425 | 0 | 0 | 7 |
| `voralpen` | Bayerische Voralpen | 358 | 0 | 0 | 8 |
| `elba` | Elba | 222 | 0 | 0 | 5 |
| `finale` | Finale Ligure | 219 | 0 | 0 | 12 |
| `varazze` | Varazze | 195 | 0 | 0 | 7 |
| `bormio` | Bormio & Valtellina | 179 | 0 | 0 | 6 |
| `madeira` | Madeira | 158 | 0 | 0 | 6 |
| `davos` | Davos Klosters | 152 | 0 | 0 | 3 |
| `vinschgau` | Vinschgau & Meran | 146 | 0 | 0 | 6 |
| `bikekingdom` | Bike Kingdom | 121 | 12 | 4 | 9 |
| `portesdusoleil` | Portes du Soleil | 80 | 24 | 1 | 6 |
| `sauerland` | Sauerland/Upland | 73 | 7 | 6 | 5 |
| `odenwald` | Geo-Naturpark Odenwald | 66 | 0 | 14 | 9 |
| `bikecircus` | Saalfelden Leogang | 51 | 16 | 2 | 4 |
| `harz` | Harz | 42 | 6 | 0 | 6 |
| `donnersberg` | Donnersberger Land | 41 | 0 | 1 | 4 |
| `soelden` | Bike Republic Sölden | 38 | 5 | 4 | 4 |
| `livigno` | Livigno | 31 | 7 | 1 | 3 |
| `dreilaender` | 3-Länder Enduro Trails | 29 | 5 | 0 | 4 |
| `schladming` | Bikeland Schladming-Dachstein | 29 | 3 | 0 | 3 |
| `paganella` | Dolomiti Paganella | 28 | 10 | 5 | 4 |
| `paznaun` | Silvretta Bike Arena | 26 | 8 | 2 | 3 |
| `laax` | Flims Laax Falera | 24 | 6 | 5 | 2 |
| `kronplatz` | Kronplatz | 23 | 4 | 0 | 4 |
| `saarland` | Saarland | 22 | 0 | 2 | 2 |
| `waldmeister` | RadLust Waldmeister | 21 | 0 | 1 | 1 |
| `naheland` | Bad Kreuznach | 17 | 0 | 3 | 2 |
| `serfaus` | Serfaus-Fiss-Ladis | 17 | 8 | 0 | 2 |
| `zugspitzarena` | Tiroler Zugspitz Arena | 17 | 8 | 0 | 3 |
| `brandnertal` | Bikepark Brandnertal | 12 | 3 | 0 | 2 |
