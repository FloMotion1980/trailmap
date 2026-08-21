# Madeira

**158 trails, 6 sub-regions, no lifts, one source.** Built 2026-08-21 by
`tools/build_trailforks_region.py madeira` from a Trailforks harvest
(`tools/harvest_trailforks.py`), which is also the first region built with either of those two tools.

## The source, and why there is only one

The user has ridden the island themselves, which by the standing rule (see `docs/backlog.md`'s Madeira
entry and the Bike Kingdom precedent) would make their own account the authority for difficulty and for
the sub-region split. Asked before the build, they had nothing to hand: *"Nimm alles von Trailforks. Hab
auch keine andere Quelle da"* (2026-08-21). And the operators here are guiding/shuttle companies
(Freeride Madeira and friends) that publish descriptions and photographs but no per-trail GPX and no
grade — so there is no operator rating for `CLAUDE.md`'s "operator difficulty wins" rule to prefer, and
Trailforks' own rating is the documented fallback rather than a shortcut.

So: **geometry, elevation and difficulty all come from Trailforks**, and every trail's id is
`md_<trailforks-slug>` so any single trail can be traced back to the page it came from.

**No elevation API was needed.** A Trailforks trail page carries the line twice — the `encodedpath`
polyline and an `ElevationChart` whose points hold lat/lng *and* real elevation *and* cumulative
distance. All 158 built trails have both, and the two lengths agreed within 60 m for **every one of
them** (the harvester cross-checks and prints the disagreements; there were none).

## What is in, and what is not

| | |
|---|---|
| in the Trailforks tables | 184 |
| access roads / uplift / no grade | 24 |
| harvested, no line on their own page | 2 (`Antenas`, `Tabaibeiras`) |
| **built** | **158** |

Nothing was dropped as a duplicate or as too far from the region — which is worth stating rather than
leaving implicit, because the same rules dropped 76 duplicates and 30 out-of-range trails in the
Schwarzwald. An island tree curated by one small community simply has neither problem.

Seeds: `madeira-island`, `madeira`, `porto-santo-71311`. **`madeira` is NOT an ancestor of
`madeira-island`** on Trailforks — its 35 rows are a subset of the island's 184, but nothing in the
hierarchy says so, which is exactly why the harvester takes a list of seeds and dedupes by slug instead
of trusting the tree.

## Sub-regions

Decided from where the trails actually fall (the same method as the Schwarzwald's), not from
Trailforks' own `riding area` column — that column is an administrative box: 33 trails carry the
useless area name "Madeira" or "Madeira Island", and they are spread over the whole island. Every trail
goes to the sub-region of its **nearest anchor town** (23 anchors, in
`tools/build_trailforks_region.py`'s `CONFIGS`), with a 15 km ceiling that nothing reached.

| sub-region | label | trails | what it covers |
|---|---|---|---|
| `md_funchal` | Funchal/Arieiro | 52 | Funchal, Monte, Poiso, Pico do Arieiro, Curral das Freiras, Câmara de Lobos |
| `md_east` | Machico | 27 | Machico, Santo da Serra, Caniçal, Porto da Cruz |
| `md_west` | Calheta | 27 | Calheta, Paul da Serra, Prazeres, Ribeira Brava |
| `md_northwest` | Ponta do Pargo | 25 | Ponta do Pargo, Fanal, Porto Moniz |
| `md_north` | São Vicente | 23 | São Vicente, Santana, Faial, Encumeada, Seixal |
| `md_porto_santo` | Porto Santo | 4 | the second island |

**The labels are capped at 15 characters**, for the measured reason written up in `docs/gardasee.md`: at the
first version's average of 22 every one of these six chips sat on its own line. The label doubles as the
region dialog's search haystack, so each keeps one name a rider would type; the rest of each hub's places are
in the right-hand column.

Difficulties come out 10 grün / 75 blau / 55 rot / 18 schwarz.

**Porto Santo is why the catalog bounds cover open sea.** The second island sits 40 km north-east, so
the region's bounding box — which is what the sidebar's 📍 flies to — spans both. Left as one region on
purpose: four trails are too thin for a region group of their own, and as a sub-region they can be
switched off in one tap.

## Two things to know before touching this region

**No `lifts` array, on purpose.** Madeira is a shuttle island: Arieiro, Ruivo, Encumeada, Fanal and
Ponta do Pargo all start from a van drop. There is no bike-carrying lift to leave out, so the absence is
a finding rather than an omission.

**The levadas.** Sixteen entries carry a levada/vereda/caminho name, i.e. they run on irrigation-channel
or old-road infrastructure, and eight of those are literally called "Levada …". They are in the region
because **Trailforks lists them under `activitytype=1` (bike)**, which is the filter the harvest runs
with — the Harz's hike-tagged "Madonon Ridgeline" is the case that filter exists for. Two carried an
official *hiking* route number, and they were looked at individually rather than waved through:
`PR6.2 Levada do Alecrim` is an Access Trail and was excluded by the grade rule anyway, and
`lha Trail PR1` (Severe/Black, 10.5 km) has a plainly MTB description on its own page
("muito técnico, vistas lindas") and stays. What this data cannot tell you is whether riding any given
levada is *legal* — a polyline says nothing about a bike ban — so if the user ever reports one, remove
that trail rather than re-litigating the filter.

## Rebuilding

```bash
python tools/harvest_trailforks.py --dir Material/Madeira --seeds madeira-island,madeira,porto-santo-71311 --tables
python tools/harvest_trailforks.py --dir Material/Madeira --geo
python tools/build_trailforks_region.py madeira
python tools/add_region_places.py madeira      # 7 place labels, from OSM
python tools/validate_region.py madeira && python tools/update_region_versions.py
```

The build reads back the existing file's `places` before writing, so a rebuild does not throw the
labels away.
