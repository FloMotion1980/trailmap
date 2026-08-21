# Gardasee & Trentino

**911 trails, 10 sub-regions, no lifts, one source.** Built 2026-08-21 by
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

| sub-region | trails | |
|---|---|---|
| `gd_valsugana` | 155 | Pergine, Levico, Caldonazzo, Panarotta, Lavarone, Pinè |
| `gd_verona` | 114 | Verona, Valpolicella, Lessinia |
| `gd_garda_west` | 114 | Limone, Tremosine, Tignale, Gargnano, Toscolano, Salò |
| `gd_trento` | 107 | Trento, Monte Bondone, Marzola, Calisio, Terlago |
| `gd_rovereto` | 90 | Rovereto, Pomarolo, Volano, Mori, Brentonico, Folgaria |
| `gd_brescia` | 86 | Brescia, Monte Maddalena, Val Trompia, Lumezzane |
| `gd_garda_trentino` | 82 | Riva, Torbole, Arco, Nago, Ledro, Tremalzo |
| `gd_valsabbia` | 72 | Idrosee, Bagolino, Vestone, Gavardo, Serle |
| `gd_sarca` | 49 | Dro, Pietramurata, Sarche, Cavedine, Vezzano |
| `gd_baldo` | 42 | Malcesine, Brenzone, San Zeno, Prada, Garda, Bardolino |

248 grün / 374 blau / 183 rot / 106 schwarz. **No `lifts` array**: the Malcesine–Monte Baldo cable car
is a genuine summer bike lift and belongs here eventually, but a lift's data comes from the operator's
own summer page (see `docs/lifts-feature.md`), and this build was explicitly scoped to Trailforks only.
That is a known gap, listed in `docs/backlog.md`, not an oversight.

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

**Half of that RIDE figure is an empty pane.** This region has no lifts, so `LIFT_BAND_PANE` holds zero
paths and still pays a full 15.2 MB padded surface — the same waste the builder pane paid until 2026-08-20.
It is the top item in `docs/backlog.md`'s memory list, and this region is the clearest evidence for it.

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
