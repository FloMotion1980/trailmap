# Gardasee & Trentino

**911 trails, 10 sub-regions, 2 lifts, one source.** Built 2026-08-21 by
`tools/build_trailforks_region.py gardasee` from a Trailforks harvest
(`tools/harvest_trailforks.py`). By trail count this is now the largest region in the app — 289 more
than the Schwarzwald — and its file is 2.9 MB.

## The source, and why there is only one

The user asked for the Garda ("Von Trailforks ziehen") and, when the standing "operator difficulty
wins" rule was put to them against the handful of bikeparks here that do publish a grade, chose
**"Rein Trailforks, keine Betreiber-Recherche"** (2026-08-21). So every grade in this region is
Trailforks' community rating, including for Bike Park Pergine, Lavarone and the Rovereto/Pomarolo
AllSeasons areas. That is a deliberate, recorded exception to `CLAUDE.md`'s standing rule, not an
oversight — and the cheapest thing to revisit later, since ids are `gd_<trailforks-slug>` and every
trail can be traced back to the page its grade came from.

Geometry and elevation come from the same pages and needed **no elevation API**: 990 of the 993
harvested pages carry both the `encodedpath` polyline and an `ElevationChart` with real per-point
elevation, and the two lengths agreed within 60 m for **every one of them**.

## Scope — the widest of the options offered

The user was given three scopes and picked the widest, "bis Trento, Brescia, Valsugana", asking that
the lake stay in the region's name. Hence **"Gardasee & Trentino"**, covering both shores of the lake,
the Sarca and Ledro valleys, Vallagarina, Trento and Monte Bondone, the Valsugana and the Altopiani,
Verona's Lessinia, the Valle Sabbia and Brescia itself.

Deliberately **out**, and each its own future region rather than a hole in this one:

- the Dolomites group north of Trento — Fassa, Val di Sole, Val di Non, Primiero, San Martino,
  Madonna di Campiglio, Passo Tonale. **Dolomiti Paganella is already a built region**, and this build
  must not duplicate it: Andalo, Molveno and Fai sit in that excluded set for exactly that reason.
- **Lago d'Iseo, Franciacorta and the whole Val Camonica** west and north of Brescia. A different lake
  and a different valley, 64 trails at Darfo Boario alone.

Both exclusions are applied twice: `Material/Gardasee/areas_out_of_scope.json` keeps the harvest from
fetching them at all (a cost filter only — 575 rows), and, decisively, the build has **no anchor town**
within 12 km of them, which is the rule that actually decides membership.

## Sub-regions

Trailforks' own `riding area` column is a hint, not the answer — its "Sgreben Zone" (72 trails) sits
near Baselga di Pinè, 30 km from anything called Sgreben on a map, and "Trento" rows turn up 90 km
away. So every trail goes to the sub-region of its **nearest anchor town** (88 anchors in
`tools/build_trailforks_region.py`'s `CONFIGS`), and one further than 12 km from every anchor is not in
the region at all.

**The sidebar label is short on purpose and this table is where the full list lives.** A sub-region label is
capped at 15 characters, measured rather than chosen: the chip row is 279px on a phone, two chips fit a line
only at ~136px each, and the count (" (155)") spends six of those characters. The first version averaged 21
and put **every one of these ten chips on its own line** — ten lines for one region, which is what the user
noticed. At the short labels it is five lines of two, with 13px of headroom on the worst pair.

| sub-region | label | trails | what it covers |
|---|---|---|---|
| `gd_valsugana` | Valsugana | 155 | Pergine, Levico, Caldonazzo, Panarotta, Lavarone, Pinè, the Altopiani |
| `gd_verona` | Verona | 114 | Verona, Valpolicella, Lessinia |
| `gd_garda_west` | Gardawestufer | 114 | Limone, Tremosine, Tignale, Gargnano, Toscolano, Salò |
| `gd_trento` | Trento | 107 | Trento, Monte Bondone, Marzola, Calisio, Terlago |
| `gd_rovereto` | Rovereto | 90 | Rovereto, Pomarolo, Volano, Mori, Brentonico, Folgaria, Vallagarina |
| `gd_brescia` | Brescia | 86 | Brescia, Monte Maddalena, Val Trompia, Lumezzane |
| `gd_garda_trentino` | Riva/Arco | 82 | Riva, Torbole, Arco, Nago, Ledro, Tremalzo |
| `gd_valsabbia` | Valle Sabbia | 72 | Idrosee, Bagolino, Vestone, Gavardo, Serle |
| `gd_sarca` | Valle del Sarca | 49 | Dro, Pietramurata, Sarche, Cavedine, Vezzano, Valle dei Laghi |
| `gd_baldo` | Monte Baldo | 42 | Malcesine, Brenzone, San Zeno, Prada, Garda, Bardolino |

The label is also the region dialog's own **search haystack** (region name + sub-region labels + country, and
nothing else), so each one keeps the name a rider would actually type — Riva and Arco rather than the
tourist-board "Garda Trentino". The names that fell out of it are in the right-hand column above.

248 grün / 374 blau / 183 rot / 106 schwarz.

## The one lift, and the thing about it that is deliberately not stored

**Both sections of the Malcesine–Monte Baldo cable car are in**, as two lifts (`lift_gd_malcesine_i`,
`lift_gd_malcesine_ii`) in `gd_baldo`: Malcesine 98 m → San Michele 545 m (1 423 m of line) and San Michele
550 m → Monte Baldo 1 741 m (2 547 m). Geometry from OSM ways 117463249 and 338522120, elevations from
OpenTopoData, stored bottom-station-first like every other lift.

It is in the data because **the user researched the summer bike transport themselves** (2026-08-21) — which
is the operator-side statement `docs/lifts-feature.md` demands. OSM happens to carry
`aerialway:bicycle=yes` on both ways and agrees, but per that doc the tag is information only and never the
decision.

**Bikes only go up in a restricted window — mornings and afternoons — and that is NOT in the data**, on
purpose. A per-lift `closed`/`note` pair was built once and dropped the same day on the user's own call:
nothing in this app synchronises lift operating status, so a hardcoded timetable would silently rot while
looking authoritative. The data therefore states only the stable property, "this lift carries bikes in
summer", and the window lives here. If it ever belongs in the app, it belongs as something that is fetched,
not as a string in a region file.

## What was dropped, and why it is worth knowing

| | |
|---|---|
| in the three province tables (Trento, Brescia, Verona) | 2 096 |
| access roads / uplift / no grade | 531 |
| never harvested (out-of-scope riding area) | 575 |
| **paved cycle infrastructure, by name** | **60** |
| too far from every anchor | 20 |
| duplicates (5 by name, 5 by geometry) | 10 |
| no line on their own Trailforks page | 3 |
| under 80 m | 1 |
| **built** | **911** |

**The paved-cycleway exclusion is new, and it is the one rule this region needed that no earlier
region did.** Trailforks' `Access Trail, Road or Doubletrack` grade is what normally keeps fireroads
and uplift out — but a municipal cycle path is not graded that way. It gets a real
**"Easiest / White Circle"** and sails straight through. Here that was Trento's entire urban
"Bicipolitana" network, the Ciclovia dell'Adige (54 km, 51 km and 47 km of paved valley floor — the
three longest lines in the region by a factor of three), and a dozen "Ciclabile …" valley paths: real
riding, but not trails, and on the map long straight lines through towns that bury whatever they cross.
`EXCLUDE_NAME_RE` drops them by name, matching the Italian words for the infrastructure itself rather
than a difficulty or a length — so the **Ponale**, a famous gravel climb that carries no such word,
stays in.

**"Easiest / White Circle" is also a difficulty tier the project had never met**, absent from both
Vogesen builds and the Schwarzwald. It maps to `gruen` like Green does (the app has four steps and
nothing below "Sehr leicht"). A tier missing from that table is silent — the trails simply are not
built — which is why `tests/python/trailforks.py` now checks the mapping against every harvested table
rather than against a hand-written list.

The 20 anchor drops are all honest: the Argai/Frerone/Tita Secchi cluster is Adamello, 19–20 km beyond
Bagolino; "Soave enduro 1/2" are 15 km east of Verona's hills; and "Torretta's Trail" sits **45 km**
from Verona, which is bad source data rather than a boundary question.

## Coverage gaps worth naming

Trailforks does not hold everything the Garda is famous for. **Pernici, Tremalzo and Busatte are not in
this region** — the first two exist on Trailforks mainly as *routes* rather than trails (the harvester
reads trail pages only), and several classic descents are recorded under local names instead. The
601 is present in pieces ("601toCoast", "Altissimo - 601"). If the user misses a specific line, the fix
is a per-trail addition, not a re-harvest.

## Two things to weigh before extending it

**It is one region group on purpose, and the cost was measured rather than guessed.** At a 375x812 phone
viewport with only this region active: 1 822 vector paths in a 450x908 renderer surface, **3.2 MB** across
two panes; in RIDE, where rotation and the look-ahead pad that surface to 1 170x3 405, **30.4 MB**. Both are
well under the 86 MB the RIDE memory work measured on Bike Kingdom's 655 paths, because what costs the
memory is the SURFACE and not the path count — so a region three times as dense is not three times as
expensive. No fatal panel and no white screen in either state here. With Madeira active as well the map
paints 2 138 paths.

**Half of that RIDE figure was an empty pane** when the region had no lifts at all: `LIFT_BAND_PANE` held
zero paths and still paid a full 15.2 MB padded surface, the same waste the builder pane paid until
2026-08-20. The two Malcesine sections put six paths in it, which does not change the arithmetic — the cost
is the SURFACE — so this is still the clearest evidence for the top item in `docs/backlog.md`'s memory list,
just no longer the pure zero-path case. Madeira is that now.

**Place labels needed their own cap.** At the default `MAX_PLACES` of 10 the population ranking spent
every label on Verona, Brescia, Trento and Rovereto and left the lake anonymous — no Salò, no
Peschiera, no Gargnano, on a region named after that lake. `MAX_PLACES_BY_REGION["gardasee"] = 20`
gives each of the ten brackets its own two. Riva del Garda still loses to Arco, 3 km away, because of
`MIN_SEPARATION_KM`; that rule is deliberate and was left alone.

## Rebuilding

```bash
python tools/harvest_trailforks.py --dir Material/Gardasee --seeds trento,brescia,verona --tables
python tools/harvest_trailforks.py --dir Material/Gardasee --geo --sleep 0.8 --skip-areas Material/Gardasee/areas_out_of_scope.json
python tools/build_trailforks_region.py gardasee
python tools/add_region_places.py gardasee
python tools/validate_region.py gardasee && python tools/update_region_versions.py
```
