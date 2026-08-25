# -*- coding: utf-8 -*-
"""Build a whole region out of a Trailforks harvest, for regions where Trailforks is the only source.

    python tools/build_trailforks_region.py madeira
    python tools/build_trailforks_region.py gardasee --dry-run

Reads `trailforks_table.json` + `trailforks_geo.json` from the region's `Material/` directory (produced
by `tools/harvest_trailforks.py`) and writes `Trailmap App/regions/<key>.json`, then PRINTS its
`REGION_CATALOG` entry rather than patching `index.html` -- same convention `tools/build_schwarzwald.py`
established, and for the same reason: that file is edited by hand.

**Why this is generic and the Schwarzwald's is not.** The Schwarzwald build has four sources (the club's
own GPX, Trailguide, OSM, Trailforks) and the sweep is one branch of it. Madeira and the Gardasee have
exactly one source, so everything that differs between them is DATA -- the anchor towns, the sub-region
labels, the id prefix -- and lives in `CONFIGS` below. Nothing about a region should need code here.

The rules it applies are the project's existing ones, not new ones:

* **Difficulty is Trailforks' own rating**, which is the documented fallback for trails whose operator
  publishes no grade (`CLAUDE.md`'s standing rule). Both regions built with this script were explicitly
  cleared by the user as Trailforks-only, Madeira included ("Nimm alles von Trailforks. Hab auch keine
  andere Quelle da", 2026-08-21).
* **A trail goes to the sub-region of its NEAREST ANCHOR TOWN**, and one further than `max_anchor_km`
  from every anchor is not in the region at all. Trailforks' own `riding area` column is a hint, not the
  answer: it is an administrative box the same way a Schwarzwald district was (a "Trento" row can sit
  90 km from Trento). One rule doing the assigning and the excluding at once is what makes the
  exclusions reviewable -- every one of them is printed.
* **Duplicates are caught by name AND by geometry**, name only within `SAME_NAME_KM` (two trails of the
  same name are the same trail only if they are also in the same place) and geometry by the project's own
  containment metric.
* **No elevation API.** A Trailforks trail page carries the line twice -- the `encodedpath` polyline and
  an `ElevationChart` whose points hold lat/lng AND real elevation -- so the profile is the preferred
  source and a DEM lookup is never needed. A trail that has only the polyline is REPORTED AND SKIPPED
  rather than given invented elevation.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import (build_trail, haversine_m, region_summary,  # noqa: E402
                               write_region)
from pfaelzerwald_containment import bbox, line_len_m  # noqa: E402
from build_schwarzwald import duplicate_of, looks_uphill, norm  # noqa: E402
from harvest_trailforks import ACCESS_DIFF  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS_DIR = os.path.join(ROOT, "Trailmap App", "regions")

#: Trailforks' own difficulty titles, exactly as its region table renders them, onto our four colours.
#: The same table `build_nordvogesen.py`/`build_schwarzwald.py` use -- a project-wide convention -- plus
#: **"Easiest / White Circle"**, a SIXTH tier neither of those regions happened to contain and which is
#: worth 78 trails at the Gardasee alone. It maps to `gruen` like Green does: our scale has four steps and
#: nothing below "Sehr leicht", so white and green share the bottom one. Leaving a tier out of this table
#: is the same class of bug as leaving a code out of the harvester's `difficulty=` list -- see the Finale
#: realignment, where a missing tier silently hid trails.
TF_DIFF = {
    "Easiest / White Circle": "gruen",
    "Easy / Green Circle": "gruen",
    "Intermediate / Blue Square": "blau",
    "Difficult / Red": "rot",
    "Severe / Black": "schwarz",
    "Very Difficult / Black Diamond": "schwarz",
    "Extremely Difficult & dangerous, pros only!": "schwarz",
}
SAME_NAME_KM = 5.0
MIN_TRAIL_M = 80.0

#: Two further per-region escape hatches, both DATA and both deliberately narrow. Neither may be reached for
#: to make a number look better -- each one needs an OPERATOR statement behind it, named in the region's doc.
#:
#: * `keep_overlapping`: Trailforks slugs exempt from the geometry-duplicate drop. `duplicate_of` is right
#:   that these lines share ground with a longer one; the operator is right that they are separate trails
#:   with their own name, grade and length. Kronplatz has three (Crazy Bunny, CCTop1, CCTop2, all inside the
#:   Furcia Trail's corridor) and its own trail table names each of them.
#: * `exclude`: Trailforks slugs to drop outright, with the reason in the comment beside them. For a line
#:   that is WRONG, not merely redundant -- Kronplatz's `gassl-trail` is the Dragon Trail and the Gassl
#:   Trail recorded as one 8.4 km line, which is why its length disagreed with the operator by 30 %.
#: * `extra_trails`: trails the OPERATOR publishes that Trailforks does not have, or has wrong. Each names
#:   a points file under the region's `Material/` directory (`{points: [[lat, lng, ele], ...]}` plus its own
#:   provenance fields), so the source travels with the data and a rebuild needs no network. Real per-point
#:   elevation is required -- this is not a way round the "no elevation API" rule at the top of the file,
#:   it is a second source that has its own heights.
#:
#: Per-region, per-trail difficulty overrides: `{tf_slug: (our_diff, "operator's own wording")}`.
#: This is the standing rule, not an exception to it -- `CLAUDE.md`: the OPERATOR's own published grade
#: always wins, and Trailforks' rating is the fallback for trails whose operator publishes none. Madeira
#: and the Gardasee needed no such table because neither has an operator publishing grades at all;
#: Kronplatz does, so its 19 published trails are graded from `kronplatz.com`'s own table and only the
#: rest fall back to Trailforks. The operator's wording is stored next to the colour so the mapping
#: stays auditable without re-fetching the pages -- also `CLAUDE.md`'s own requirement.

#: Paved cycle INFRASTRUCTURE, dropped by name. Trailforks' `Access Trail, Road or Doubletrack` grade is
#: what normally keeps fireroads and uplift out, but a municipal cycle path is not graded that way -- it
#: gets a real "Easiest / White Circle" and sails through. At the Gardasee that is 48 entries: Trento's
#: whole urban "Bicipolitana" network, the Ciclovia dell'Adige (54 km, 51 km and 47 km of paved valley
#: floor, the three longest lines in the region by a factor of three), and a dozen "Ciclabile ..." valley
#: paths. They are real riding, but they are not trails, and on the map they are long straight lines
#: through towns that bury the trails they cross. Kept deliberately narrow -- it matches the Italian words
#: for the infrastructure itself, not a difficulty and not a length -- so the Ponale, a famous gravel
#: climb that carries no such word, stays in. Nothing in Madeira's table matches it.
EXCLUDE_NAME_RE = re.compile(r"\b(ciclabile|ciclovia|ciclopedonale|bicipolitana|lungolago)\b", re.I)


def sid(prefix, tf_slug):
    return "%s_%s" % (prefix, re.sub(r"[^a-z0-9]+", "_", tf_slug.lower()).strip("_"))


# --------------------------------------------------------------------------------------------------
# The per-region data. An anchor is (lat, lon, sub-region key, name shown in the drop report).
# --------------------------------------------------------------------------------------------------
#: A sub-region label is capped at 15 characters, measured rather than chosen: the sidebar's chip row is
#: 299px, two chips fit a line only at ~146px each, and the count (" (155)") spends six of those characters.
#: Both of these regions shipped at an average of 21 and put every chip on its own line -- ten lines for the
#: Gardasee alone. Keep the name a rider would type (it is also the region dialog's search haystack) and put
#: the full place list in the region's doc instead.
CONFIGS = {
    # Elba, 2026-08-25. The user has ridden there, so their own account of the island beats anything
    # scraped -- but they asked for it "von Trailforks", and no operator publishes grades for the island's
    # trails at all, so Trailforks' own rating stands, the same recorded exception Madeira and the
    # Gardasee were built under. Like Madeira it is a shuttle island: no `lifts` array -- the island's one
    # cable car, the Monte Capanne cabinovia from Marciana, is a standing open basket a rider cannot take a
    # bike into. That is the ONLY lift on Elba, so there is nothing else to check; see `docs/elba.md`.
    #
    # The five sub-regions follow the island's own geography rather than Trailforks' `riding area` column,
    # which is an administrative box here as everywhere: its "Marina di Campo" area reaches to lon 10.127,
    # 9 km WEST of Marina di Campo itself and well inside the Monte Capanne massif.
    "elba": dict(
        prefix="eb", label="Elba", countries=["IT"], material="Elba",
        max_anchor_km=6.0,
        subregions=[
            ("eb_capanne",     "Monte Capanne",   "#0f766e"),
            ("eb_campo",       "Marina di Campo", "#b45309"),
            ("eb_portoferraio", "Portoferraio",   "#1d4ed8"),
            ("eb_rio",         "Rio & Cavo",      "#7c3aed"),
            ("eb_calamita",    "Capoliveri",      "#be185d"),
        ],
        anchors=[
            (42.7930, 10.1740, "eb_capanne", "Marciana"),
            (42.8060, 10.1950, "eb_capanne", "Marciana Marina"),
            (42.7860, 10.1830, "eb_capanne", "Poggio"),
            (42.7660, 10.1750, "eb_capanne", "Monte Capanne"),
            (42.7690, 10.2130, "eb_capanne", "Sant'Ilario"),
            (42.7620, 10.2140, "eb_capanne", "San Piero"),
            (42.7420, 10.1250, "eb_capanne", "Pomonte"),
            (42.7500, 10.1130, "eb_capanne", "Chiessi"),
            (42.7380, 10.1610, "eb_capanne", "Seccheto"),
            (42.7350, 10.1450, "eb_capanne", "Fetovaia"),
            (42.7770, 10.1300, "eb_capanne", "Colle d'Orano"),
            (42.7440, 10.2320, "eb_campo", "Marina di Campo"),
            (42.7530, 10.2440, "eb_campo", "La Pila"),
            (42.7750, 10.2650, "eb_campo", "Colle Reciso"),
            (42.7590, 10.3010, "eb_campo", "Lacona"),
            (42.7400, 10.1830, "eb_campo", "Cavoli"),
            (42.8130, 10.3260, "eb_portoferraio", "Portoferraio"),
            (42.7930, 10.2440, "eb_portoferraio", "Procchio"),
            (42.8000, 10.2790, "eb_portoferraio", "Biodola"),
            (42.7940, 10.3170, "eb_portoferraio", "San Martino"),
            (42.8080, 10.3560, "eb_portoferraio", "Magazzini"),
            (42.8250, 10.3700, "eb_portoferraio", "Bagnaia"),
            (42.8060, 10.4110, "eb_rio", "Rio nell'Elba"),
            (42.8140, 10.4270, "eb_rio", "Rio Marina"),
            (42.8620, 10.4230, "eb_rio", "Cavo"),
            (42.8290, 10.3810, "eb_rio", "Nisporto"),
            (42.8080, 10.3830, "eb_rio", "Volterraio"),
            (42.8420, 10.4130, "eb_rio", "Porticciolo"),
            (42.7440, 10.3960, "eb_calamita", "Capoliveri"),
            (42.7640, 10.3970, "eb_calamita", "Porto Azzurro"),
            (42.7250, 10.4090, "eb_calamita", "Monte Calamita"),
            (42.7460, 10.4150, "eb_calamita", "Naregno"),
            (42.7360, 10.4020, "eb_calamita", "Morcone"),
            (42.7580, 10.3800, "eb_calamita", "Mola"),
        ],
    ),
    # Kronplatz / Plan de Corones, 2026-08-25. Researched in 2026-07 and shelved for want of geometry
    # (`docs/kronplatz-recherche.md` lists the four sourcing routes that failed) -- Trailforks is the fifth
    # and it works. Difficulty is the OPERATOR's, from that same research doc's table, wherever the operator
    # publishes one; the four trails it does not name fall back to Trailforks. See `diff_override` below.
    # Sub-regions are the three flanks the operator itself distinguishes, plus the trails on the NORTH side
    # of the Pustertal (Sambock above Bruneck, Huehnerspiel above Rasen), which belong to no flank at all.
    "kronplatz": dict(
        prefix="kp", label="Kronplatz", countries=["IT"], material="Kronplatz",
        max_anchor_km=8.0,
        subregions=[
            ("kp_reischach",  "Reischach",      "#0f766e"),
            ("kp_olang",      "Olang",          "#b45309"),
            ("kp_stvigil",    "St. Vigil",      "#7c3aed"),
            ("kp_pustertal",  "Pustertal Nord", "#1d4ed8"),
        ],
        anchors=[
            (46.7794, 11.9542, "kp_reischach", "Reischach"),
            (46.7970, 11.9370, "kp_reischach", "Bruneck"),
            (46.7660, 11.9450, "kp_reischach", "Ried/Ruis"),
            (46.7570, 11.9560, "kp_reischach", "Herrnsteig-Nordflanke"),
            (46.7570, 12.0000, "kp_olang", "Geiselsberg"),
            (46.7480, 12.0270, "kp_olang", "Olang"),
            (46.7495, 11.9700, "kp_olang", "Kronplatz Ostflanke"),
            (46.7378, 11.9553, "kp_stvigil", "Kronplatz Gipfel"),
            (46.7250, 11.9600, "kp_stvigil", "Furkelpass"),
            (46.6900, 11.9200, "kp_stvigil", "St. Vigil"),
            (46.8400, 11.9050, "kp_pustertal", "Sambock"),
            (46.8250, 11.9200, "kp_pustertal", "Sambock unten"),
            (46.8280, 12.0050, "kp_pustertal", "Huehnerspiel"),
        ],
        #: kronplatz.com's own three-step scale (easy/medium/difficult) onto our four colours, the same
        #: mapping Saalbach's three-step scale uses: easy->blau, medium->rot, difficult->schwarz, and
        #: `gruen` simply never reached. Only ONE of these disagrees with Trailforks -- Piz de Plaies,
        #: which Trailforks rates Blue and the operator calls medium -- but all of them are listed, so the
        #: table can be checked against the operator's page without guessing which ones mattered.
        diff_override={
            "freeride-trail-herrnsteig": ("rot", "medium"),
            "gassl-trail": ("rot", "medium"),
            "telle-line": ("rot", "medium"),
            "sigi": ("rot", "medium"),
            "uschi": ("rot", "medium"),
            "spitzhorn-672806": ("rot", "medium"),
            "franz": ("schwarz", "difficult"),
            "christian": ("schwarz", "difficult"),
            "hans-trail": ("schwarz", "difficult"),
            "furcia-trail": ("rot", "medium"),
            "crazy-bunny": ("rot", "medium"),
            "cctop1": ("rot", "medium"),
            "cctop2": ("rot", "medium"),
            "richardanton": ("rot", "medium"),
            "freeride-piz-de-plaies": ("rot", "medium"),
            "korer-trail": ("schwarz", "difficult"),
            "andreas-trail": ("schwarz", "difficult"),
            "alex-trail": ("schwarz", "difficult"),
        },
        #: Alle drei fuehrt kronplatz.com als eigene Trails mit eigener Laenge und Schwierigkeit; ihre
        #: Trailforks-Linien liegen im Korridor des 4,8 km langen Furcia Trails (100 %, 100 %, 78 %).
        #: Der Betreiber entscheidet, was ein Trail IST -- also gebaut, nicht verworfen.
        keep_overlapping=("crazy-bunny", "cctop1", "cctop2"),
        #: `gassl-trail` bei Trailforks ist NICHT der Gassl Trail des Betreibers, sondern Dragon Trail und
        #: Gassl Trail als eine 8,4-km-Linie -- gemessen, nicht vermutet: das Ende des Komoot-Dragon und der
        #: Anfang des Komoot-Gassl liegen 0 m auseinander, und 99 % der Punkte der Trailforks-Linie liegen
        #: naeher als 25 m an der Vereinigung der beiden. Daher raus und durch `extra_trails` ersetzt.
        exclude=("gassl-trail",),
        #: Beide von Komoot, verlinkt auf bike-holidays.com (Quelle vom Nutzer). Sie tragen echte Hoehen je
        #: Punkt, und ihre Laengen treffen die Betreiberangabe fast genau (Gassl 6 376 gegen 6 400 m,
        #: Dragon 2 016 gegen 2 043 m) -- die Trailforks-Linie tat das um 30 % nicht. Die Rohdaten liegen
        #: in Material/Kronplatz/komoot/, ein Neubau braucht also kein Netz.
        extra_trails=[
            dict(id="gassl_trail", name="Gassl Trail", sub="kp_olang", diff="rot",
                 file="komoot/gassl-trail.json", source="Komoot 780771680 via bike-holidays.com"),
            dict(id="dragon_trail", name="Dragon Trail", sub="kp_olang", diff="blau",
                 file="komoot/dragon-trail.json", source="Komoot 1068195473 via bike-holidays.com"),
        ],
    ),
    # Madeira: a shuttle island, not a lift island -- every classic descent starts from a van drop, so
    # there is deliberately NO `lifts` array, the same as Odenwald/Pfälzerwald/Donnersberg.
    "madeira": dict(
        prefix="md", label="Madeira", countries=["PT"], material="Madeira",
        max_anchor_km=15.0,
        subregions=[
            ("md_east",        "Machico",         "#3a7a4a"),
            ("md_funchal",     "Funchal/Arieiro", "#3a6b8a"),
            ("md_north",       "São Vicente",     "#8a3a63"),
            ("md_west",        "Calheta",         "#8a6a2a"),
            ("md_northwest",   "Ponta do Pargo",  "#2a7a7a"),
            ("md_porto_santo", "Porto Santo",     "#6b4a8a"),
        ],
        anchors=[
            (32.7186, -16.7674, "md_east", "Machico"),
            (32.7259, -16.8261, "md_east", "Santo da Serra"),
            (32.7398, -16.7379, "md_east", "Caniçal"),
            (32.7727, -16.8281, "md_east", "Porto da Cruz"),
            (32.6669, -16.9241, "md_funchal", "Funchal"),
            (32.6810, -16.9000, "md_funchal", "Monte"),
            (32.7086, -16.8834, "md_funchal", "Poiso"),
            (32.7351, -16.9153, "md_funchal", "Pico do Arieiro"),
            (32.6503, -17.0000, "md_funchal", "Câmara de Lobos"),
            (32.7233, -16.9686, "md_funchal", "Curral das Freiras"),
            (32.8058, -16.8869, "md_north", "Santana"),
            (32.7935, -16.8534, "md_north", "Faial"),
            (32.7987, -17.0442, "md_north", "São Vicente"),
            (32.7554, -17.0175, "md_north", "Encumeada"),
            (32.8210, -17.1050, "md_north", "Seixal"),
            (32.6742, -17.0631, "md_west", "Ribeira Brava"),
            (32.7167, -17.1786, "md_west", "Calheta"),
            (32.7580, -17.1000, "md_west", "Paul da Serra"),
            (32.7550, -17.2000, "md_west", "Prazeres"),
            (32.8663, -17.1697, "md_northwest", "Porto Moniz"),
            (32.8137, -17.1364, "md_northwest", "Fanal"),
            (32.8103, -17.2617, "md_northwest", "Ponta do Pargo"),
            (33.0667, -16.3333, "md_porto_santo", "Vila Baleira"),
        ],
    ),
    # Gardasee & Trentino, 2026-08-21: the user asked for the Garda explicitly and, given the choice, for the
    # WIDER of two scopes -- "bis Trento, Brescia, Valsugana" -- with the lake in the region's own name. So the
    # borders here are deliberately generous: the whole Garda basin, both shores, the Sarca and Ledro valleys,
    # Vallagarina, the Trento hills, the Valsugana and the Altopiani, Verona's Lessinia, the Valle Sabbia and
    # Brescia itself. What is deliberately OUT is the Dolomites/Val di Sole/Val di Non/Primiero group north of
    # Trento (each its own region one day, and Dolomiti Paganella is already built), and Lago d'Iseo plus the
    # whole Val Camonica west of Brescia -- a different lake and a different valley. Those are excluded twice
    # over: by `Material/Gardasee/areas_out_of_scope.json` at harvest time (cost only) and, decisively, by
    # having no anchor within `max_anchor_km` here.
    "gardasee": dict(
        prefix="gd", label="Gardasee & Trentino", countries=["IT"], material="Gardasee",
        max_anchor_km=12.0,
        subregions=[
            ("gd_garda_trentino", "Riva/Torbole",    "#0f766e"),
            ("gd_sarca",          "Valle del Sarca", "#0891b2"),
            ("gd_baldo",          "Monte Baldo",     "#be185d"),
            ("gd_garda_west",     "Gardawestufer",   "#c2410c"),
            ("gd_valsabbia",      "Valle Sabbia",    "#7c3aed"),
            ("gd_brescia",        "Brescia",         "#475569"),
            ("gd_verona",         "Verona",          "#7f1d1d"),
            ("gd_trento",         "Trento",          "#1d4ed8"),
            ("gd_rovereto",       "Rovereto",        "#b45309"),
            ("gd_valsugana",      "Valsugana",       "#4d7c0f"),
        ],
        anchors=[
            (45.8856, 10.8434, "gd_garda_trentino", "Riva del Garda"),
            (45.8706, 10.8722, "gd_garda_trentino", "Torbole"),
            (45.9186, 10.8850, "gd_garda_trentino", "Arco"),
            (45.8770, 10.8886, "gd_garda_trentino", "Nago"),
            (45.9231, 10.8383, "gd_garda_trentino", "Tenno"),
            (45.8827, 10.7326, "gd_garda_trentino", "Pieve di Ledro"),
            (45.8500, 10.6800, "gd_garda_trentino", "Tremalzo"),
            (45.8600, 10.8200, "gd_garda_trentino", "Pregasina"),
            (45.9686, 10.9203, "gd_sarca", "Dro"),
            (45.9930, 10.9333, "gd_sarca", "Pietramurata"),
            (46.0450, 10.9080, "gd_sarca", "Sarche"),
            (45.9940, 10.9700, "gd_sarca", "Cavedine"),
            (46.0700, 10.9760, "gd_sarca", "Vezzano"),
            (46.0450, 10.8720, "gd_sarca", "Comano Terme"),
            (46.0620, 10.9510, "gd_sarca", "Ranzo"),
            (45.8906, 11.0400, "gd_rovereto", "Rovereto"),
            (45.9350, 11.0460, "gd_rovereto", "Pomarolo"),
            (45.9100, 11.0900, "gd_rovereto", "Volano"),
            (45.8544, 10.9333, "gd_rovereto", "Mori"),
            (45.8147, 10.9581, "gd_rovereto", "Brentonico"),
            (45.8890, 11.0000, "gd_rovereto", "Isera"),
            (45.9153, 11.1706, "gd_rovereto", "Folgaria"),
            (45.8760, 11.1400, "gd_rovereto", "Terragnolo"),
            (45.7550, 11.0000, "gd_rovereto", "Ala"),
            (46.0679, 11.1211, "gd_trento", "Trento"),
            (46.0250, 11.0480, "gd_trento", "Monte Bondone"),
            (46.0819, 11.0603, "gd_trento", "Terlago"),
            (46.0400, 11.1600, "gd_trento", "Marzola"),
            (46.1300, 11.1700, "gd_trento", "Santa Colomba"),
            (46.1100, 11.1400, "gd_trento", "Calisio"),
            (46.1700, 11.1400, "gd_trento", "Monte Corona"),
            (46.0980, 11.0770, "gd_trento", "Sorasass"),
            (46.0800, 11.0700, "gd_trento", "Cadine"),
            (46.0631, 11.2372, "gd_valsugana", "Pergine Valsugana"),
            (46.0117, 11.3000, "gd_valsugana", "Levico Terme"),
            (45.9950, 11.2650, "gd_valsugana", "Caldonazzo"),
            (46.1300, 11.2500, "gd_valsugana", "Baselga di Pinè"),
            (46.1600, 11.2800, "gd_valsugana", "Sgreben"),
            (46.0500, 11.3000, "gd_valsugana", "Panarotta"),
            (45.9350, 11.2750, "gd_valsugana", "Lavarone"),
            (46.0100, 11.1900, "gd_valsugana", "Vigolo Vattaro"),
            (46.0100, 11.2600, "gd_valsugana", "Tenna"),
            (46.1200, 11.3000, "gd_valsugana", "Sant'Orsola"),
            (45.7639, 10.8100, "gd_baldo", "Malcesine"),
            (45.7100, 10.7800, "gd_baldo", "Brenzone"),
            (45.6431, 10.7169, "gd_baldo", "San Zeno di Montagna"),
            (45.6500, 10.7800, "gd_baldo", "Prada"),
            (45.6060, 10.7940, "gd_baldo", "Caprino Veronese"),
            (45.5750, 10.7000, "gd_baldo", "Garda"),
            (45.5500, 10.7200, "gd_baldo", "Bardolino"),
            (45.4400, 10.6900, "gd_baldo", "Peschiera del Garda"),
            (45.5450, 10.7800, "gd_baldo", "Cavaion Veronese"),
            (45.4384, 10.9916, "gd_verona", "Verona"),
            (45.5100, 11.0000, "gd_verona", "Grezzana"),
            (45.5750, 11.0200, "gd_verona", "Lugo di Grezzana"),
            (45.5050, 11.0980, "gd_verona", "Trezzolano"),
            (45.6250, 11.0400, "gd_verona", "Bosco Chiesanuova"),
            (45.6400, 10.9400, "gd_verona", "Sant'Anna d'Alfaedo"),
            (45.5400, 10.8800, "gd_verona", "Fumane"),
            (45.5100, 10.8400, "gd_verona", "Sant'Ambrogio di Valpolicella"),
            (45.5300, 10.9400, "gd_verona", "Negrar"),
            (45.8100, 10.7900, "gd_garda_west", "Limone sul Garda"),
            (45.7800, 10.7500, "gd_garda_west", "Tremosine"),
            (45.7400, 10.7200, "gd_garda_west", "Tignale"),
            (45.6900, 10.6600, "gd_garda_west", "Gargnano"),
            (45.6400, 10.6100, "gd_garda_west", "Toscolano-Maderno"),
            (45.6200, 10.5700, "gd_garda_west", "Gardone Riviera"),
            (45.6100, 10.5200, "gd_garda_west", "Salò"),
            (45.6450, 10.4980, "gd_garda_west", "Vobarno"),
            (45.7500, 10.4900, "gd_valsabbia", "Idro"),
            (45.8200, 10.4700, "gd_valsabbia", "Bagolino"),
            (45.7050, 10.4000, "gd_valsabbia", "Vestone"),
            (45.5850, 10.4400, "gd_valsabbia", "Gavardo"),
            (45.5600, 10.3500, "gd_valsabbia", "Serle"),
            (45.5700, 10.4000, "gd_valsabbia", "Paitone"),
            (45.5450, 10.3400, "gd_valsabbia", "Nuvolento"),
            (45.5100, 10.4200, "gd_valsabbia", "Bedizzole"),
            (45.4600, 10.4800, "gd_valsabbia", "Lonato"),
            (45.6200, 10.4450, "gd_valsabbia", "Selvapiana"),
            (45.5416, 10.2118, "gd_brescia", "Brescia"),
            (45.5500, 10.2700, "gd_brescia", "Monte Maddalena"),
            (45.5800, 10.2000, "gd_brescia", "Campiani"),
            (45.6900, 10.1900, "gd_brescia", "Gardone Val Trompia"),
            (45.6500, 10.2600, "gd_brescia", "Lumezzane"),
            (45.5150, 10.2900, "gd_brescia", "Rezzato"),
            (45.6700, 10.2000, "gd_brescia", "Sarezzo"),
            (45.5850, 10.2800, "gd_brescia", "Nave"),
        ],
    ),
}


def build(key, dry_run=False):
    cfg = CONFIGS[key]
    material = os.path.join(ROOT, "Material", cfg["material"])
    table = json.load(io.open(os.path.join(material, "trailforks_table.json"), encoding="utf-8"))
    tf_geo = json.load(io.open(os.path.join(material, "trailforks_geo.json"), encoding="utf-8"))
    anchors = cfg["anchors"]

    def nearest_anchor(point):
        a = min(anchors, key=lambda x: haversine_m(point, (x[0], x[1])))
        return a[2], haversine_m(point, (a[0], a[1])) / 1000.0, a[3]

    trails, geo, profs = [], {}, {}
    by_norm, index = {}, {}
    stats = {"built": 0, "far": [], "nogeo": [], "notharvested": [], "noprofile": [], "tiny": [],
             "unknown_diff": [], "dupe_name": [], "dupe_geo": [], "hidden": [], "cyclepath": [],
             "operator_diff": [], "kept_overlapping": [], "excluded": [], "extra": []}
    def harvested_len(tf_slug):
        """Metres of the harvested line, 0 if there is none -- only used to ORDER the loop."""
        g = tf_geo.get(tf_slug) or {}
        if g.get("p") and len(g["p"]) >= 2:
            return line_len_m([[q[2], q[3]] for q in g["p"]])
        if g.get("c") and len(g["c"]) >= 2:
            return line_len_m(g["c"])
        return 0.0

    # NOTE for a REBUILD of an already-shipped region: this ordering changed on 2026-08-25 and it decides
    # which member of an overlapping pair survives. Madeira is byte-identical either way (no geometry
    # duplicates at all); the GARDASEE is not -- `gd_bike_park_pergine_1_719942` becomes
    # `gd_bike_park_pergine_2_719941` and `gd_strada_forestale_malghetta` becomes
    # `..._80595719`, the longer line of each pair. Its shipped file was NOT rebuilt, because a trail id
    # is what its ratings and its Touren' `trailSegments` point at. Rebuild it only deliberately.
    #
    # LONGEST FIRST, not alphabetically. `duplicate_of` reports the line being built as the duplicate of
    # whatever was built before it, so build order alone decides which of an overlapping pair survives --
    # and by slug that is arbitrary. At Kronplatz it dropped the 4.9 km Furcia Trail because the 329 m
    # `cctop1`, a fragment lying inside it, happened to sort first. Longest-first makes the surviving line
    # the one that contains the other, which is the only reading that is right in general.
    for tf_slug, row in sorted(table.items(), key=lambda kv: (-harvested_len(kv[0]), kv[0])):
        diff = row.get("diff")
        if not diff or diff in ACCESS_DIFF:
            continue
        name = row.get("name") or tf_slug
        if tf_slug in cfg.get("exclude", ()):
            stats["excluded"].append(name)
            continue
        if EXCLUDE_NAME_RE.search(name):
            stats["cyclepath"].append(name)
            continue
        override = cfg.get("diff_override", {}).get(tf_slug)
        if not override and diff not in TF_DIFF:
            stats["unknown_diff"].append("%s (%s)" % (name, diff))
            continue
        if tf_slug not in tf_geo:
            # Never fetched, which is a completely different statement from "its page carries no line" --
            # reporting the two together made 575 rows the harvest deliberately skipped (an out-of-scope
            # riding area, see --skip-areas) read as 575 Trailforks pages with no geometry.
            stats["notharvested"].append(name)
            continue
        g = tf_geo.get(tf_slug) or {}
        if g.get("p") and len(g["p"]) >= 2:
            pts = [[q[2], q[3], q[1]] for q in g["p"]]
        elif g.get("c") and len(g["c"]) >= 2:
            # Skipped, not built: without the ElevationChart there is no elevation for this line and
            # inventing one from a DEM would put a different source's numbers next to Trailforks' own.
            # If the trail matters, give it a real second source through `extra_trails`.
            stats["noprofile"].append(name)
            continue
        else:
            stats["nogeo"].append(name)
            continue
        mid = pts[len(pts) // 2][:2]
        sub, km, anchor = nearest_anchor(mid)
        if km > cfg["max_anchor_km"]:
            stats["far"].append("%s (%.0f km from %s)" % (name, km, anchor))
            continue
        coords_only = [[q[0], q[1]] for q in pts]
        if line_len_m(coords_only) < MIN_TRAIL_M:
            stats["tiny"].append(name)
            continue
        near_same_name = [tid for tid, other_mid in by_norm.get(norm(name), [])
                          if haversine_m(mid, other_mid) / 1000.0 <= SAME_NAME_KM]
        if near_same_name:
            stats["dupe_name"].append("%s = %s" % (name, near_same_name[0]))
            continue
        dup = duplicate_of(coords_only, geo, index)
        if dup and tf_slug not in cfg.get("keep_overlapping", ()):
            stats["dupe_geo"].append("%s = %s (%.0f%%)" % (name, dup[0], dup[1] * 100))
            continue
        if dup:
            stats["kept_overlapping"].append("%s liegt zu %.0f%% auf %s" % (name, dup[1] * 100, dup[0]))
        up = looks_uphill(pts)
        our_diff = override[0] if override else TF_DIFF[diff]
        if override and TF_DIFF.get(diff) != our_diff:
            stats["operator_diff"].append("%s: %s -> %s (Betreiber: %s)"
                                          % (name, TF_DIFF.get(diff, diff), our_diff, override[1]))
        entry, coords, prof = build_trail(sid(cfg["prefix"], tf_slug), name, sub, our_diff, pts,
                                          uphill=up, descend=not up)
        trails.append(entry)
        geo[entry["id"]] = coords
        profs[entry["id"]] = prof
        by_norm.setdefault(norm(name), []).append((entry["id"], coords[len(coords) // 2]))
        index[entry["id"]] = bbox(coords, pad=0.0005)
        stats["built"] += 1
        if row.get("hidden"):
            stats["hidden"].append(name)

    for ex in cfg.get("extra_trails", ()):
        raw = json.load(io.open(os.path.join(material, ex["file"]), encoding="utf-8"))
        pts = [[p[0], p[1], p[2]] for p in raw["points"]]
        tid = "%s_%s" % (cfg["prefix"], ex["id"])
        entry, coords, prof = build_trail(tid, ex["name"], ex["sub"], ex["diff"], pts,
                                          uphill=ex.get("uphill", False),
                                          descend=not ex.get("uphill", False))
        trails.append(entry)
        geo[tid] = coords
        profs[tid] = prof
        stats["extra"].append("%s (%s)" % (ex["name"], ex.get("source", ex["file"])))
        # counted with the rest, or the report's "N built" disagrees with the summary's own trail count
        stats["built"] += 1

    out = os.path.join(REGIONS_DIR, "%s.json" % key)
    # A rebuild must not throw away the place labels tools/add_region_places.py wrote last time.
    # `places`, `lifts`, `trailSegments` and `ratings` are NOT passed on purpose: write_region carries every
    # side key forward from the file it overwrites (see its docstring -- dropping them silently was a
    # recurring bug, not a one-off). The dry run has no file to carry from, so it reads the old one itself.
    if dry_run:
        prev = json.load(io.open(out, encoding="utf-8")) if os.path.exists(out) else {}
        data = {"lineTrails": trails, "trailGeo": geo, "elevationProfiles": profs,
                "places": prev.get("places") or []}
    else:
        data = write_region(out, trails, geo, profs)
    summary = region_summary(data)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("\n%d built, %d name duplicates, %d geometry duplicates, %d outside the region, "
          "%d polyline-only (skipped), %d with no line on their own page, %d never harvested, "
          "%d under %d m, %d unknown difficulty, %d paved cycle paths"
          % (stats["built"], len(stats["dupe_name"]), len(stats["dupe_geo"]), len(stats["far"]),
             len(stats["noprofile"]), len(stats["nogeo"]), len(stats["notharvested"]),
             len(stats["tiny"]), MIN_TRAIL_M, len(stats["unknown_diff"]), len(stats["cyclepath"])))
    for k, label in (("dupe_name", "same name as"), ("dupe_geo", "same ground as"),
                     ("far", "dropped, too far from any anchor"),
                     ("noprofile", "dropped, polyline but no elevation profile"),
                     ("nogeo", "no geometry on its Trailforks page"),
                     ("notharvested", "never harvested (riding area out of scope, see --skip-areas)"),
                     ("tiny", "dropped, too short"),
                     ("unknown_diff", "dropped, difficulty title not in TF_DIFF"),
                     ("cyclepath", "dropped, paved cycle infrastructure by name"),
                     ("operator_diff", "difficulty taken from the operator, not Trailforks"),
                     ("kept_overlapping", "built although it shares ground -- the operator lists it separately"),
                     ("extra", "built from a second source (see `extra_trails`)"),
                     ("excluded", "dropped by `exclude` -- see the reason in CONFIGS"),
                     ("hidden", "built, but Trailforks marks it a hidden trail")):
        if stats[k]:
            # Truncated, because one of these lists runs to 575 names and a report nobody reads is not a
            # report. The COUNT is the claim; the sample is what makes it checkable by hand.
            names = sorted(stats[k])
            more = " ... (+%d more)" % (len(names) - 40) if len(names) > 40 else ""
            print("  %s (%d): %s%s" % (label, len(names), "; ".join(names[:40]), more))
    print("\nREGION_CATALOG entry (paste into index.html):\n")
    print(catalog_entry(key, cfg, data))
    print("\nnext: python tools/add_region_places.py %s"
          "  /  python tools/validate_region.py %s"
          "  /  python tools/update_region_versions.py" % (key, key))
    return data


def catalog_entry(key, cfg, data):
    b = region_summary(data)["bounds"]
    subs = "\n".join('      %-14s { label: "%s", color: "%s" },' % (k + ":", label, color)
                     for k, label, color in cfg["subregions"]
                     if any(t["region"] == k for t in data["lineTrails"]))
    return ('  %s: {\n'
            '    countries: %s, label: "%s", file: "regions/%s.json", trailCount: %d,\n'
            '    bounds: [[%s, %s], [%s, %s]],\n'
            '    subRegions: {\n%s\n    }\n'
            '  },' % (key, json.dumps(cfg["countries"]).replace('"', '"'), cfg["label"], key,
                      len(data["lineTrails"]), b[0][0], b[0][1], b[1][0], b[1][1], subs))


def main(argv):
    if not argv or argv[0] not in CONFIGS:
        print("usage: build_trailforks_region.py <%s> [--dry-run]" % "|".join(sorted(CONFIGS)))
        return 2
    build(argv[0], "--dry-run" in argv)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
