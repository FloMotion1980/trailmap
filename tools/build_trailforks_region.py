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
    # Tarentaise & Vanoise, 2026-08-26. Die groesste Kandidatin ueberhaupt (Trailforks: 757 Trails im
    # gescopten Ausschnitt). Bewusst NUR das Isere-Tal: die Maurienne auf der anderen Seite der Vanoise
    # (Val Cenis, Aussois, Modane, Bessans, Valloire) ist ein eigenes Tal mit eigener Identitaet und bleibt
    # draussen, ebenso das Flachland um Albertville und Chambery. Neun Schubladen, weil die Region so gross
    # ist -- jede ist ein Skigebiet oder ein Talabschnitt, den ein Fahrer als Einheit kennt.
    "tarentaise": dict(
        prefix="tv", label="Tarentaise & Vanoise", countries=["FR"], material="Tarentaise",
        max_anchor_km=9.0,
        subregions=[
            ("tv_troisvallees", "Les 3 Vallées", "#be185d"),
            ("tv_tignes",       "Tignes",        "#0f766e"),
            ("tv_valdisere",    "Val d'Isère",   "#0891b2"),
            ("tv_saintefoy",    "Sainte-Foy",    "#4d7c0f"),
            ("tv_bourg",        "Bourg & Séez",  "#b45309"),
            ("tv_lesarcs",      "Les Arcs",      "#1d4ed8"),
            ("tv_laplagne",     "La Plagne",     "#7c3aed"),
            ("tv_valmorel",     "Valmorel",      "#475569"),
            ("tv_vanoise",      "Vanoise",       "#7f1d1d"),
        ],
        anchors=[
            (45.3250, 6.5400, "tv_troisvallees", "Les Menuires"),
            (45.2980, 6.5800, "tv_troisvallees", "Val Thorens"),
            (45.3960, 6.5650, "tv_troisvallees", "Meribel"),
            (45.3700, 6.5750, "tv_troisvallees", "Meribel-Mottaret"),
            (45.4150, 6.6350, "tv_troisvallees", "Courchevel"),
            (45.3770, 6.5060, "tv_troisvallees", "Saint-Martin-de-Belleville"),
            (45.4530, 6.5680, "tv_troisvallees", "Brides-les-Bains"),
            (45.4400, 6.6450, "tv_troisvallees", "Bozel"),
            (45.4700, 6.9050, "tv_tignes", "Tignes le Lac"),
            (45.5100, 6.8900, "tv_tignes", "Tignes les Brevieres"),
            (45.4570, 6.8930, "tv_tignes", "Val Claret"),
            (45.4480, 6.9800, "tv_valdisere", "Val-d'Isere"),
            (45.4390, 7.0130, "tv_valdisere", "Le Fornet"),
            (45.4470, 6.9560, "tv_valdisere", "La Daille"),
            (45.5920, 6.8850, "tv_saintefoy", "Sainte-Foy-Tarentaise"),
            (45.5820, 6.8750, "tv_saintefoy", "Villaroger"),
            (45.6180, 6.7690, "tv_bourg", "Bourg-Saint-Maurice"),
            (45.6220, 6.8000, "tv_bourg", "Seez"),
            (45.6300, 6.8500, "tv_bourg", "La Rosiere"),
            (45.5750, 6.8010, "tv_lesarcs", "Arc 1800"),
            (45.5720, 6.8360, "tv_lesarcs", "Arc 2000"),
            (45.5900, 6.7900, "tv_lesarcs", "Arc 1600"),
            (45.5460, 6.7580, "tv_lesarcs", "Peisey-Nancroix"),
            (45.5680, 6.7350, "tv_lesarcs", "Landry"),
            (45.5060, 6.6800, "tv_laplagne", "La Plagne"),
            (45.5540, 6.6480, "tv_laplagne", "Aime"),
            (45.5400, 6.7300, "tv_laplagne", "Montchavin"),
            (45.4600, 6.7100, "tv_laplagne", "Champagny-en-Vanoise"),
            (45.4850, 6.5320, "tv_valmorel", "Moutiers"),
            (45.4700, 6.4900, "tv_valmorel", "Aigueblanche"),
            (45.4600, 6.4500, "tv_valmorel", "La Lechere"),
            (45.4600, 6.4400, "tv_valmorel", "Valmorel"),
            (45.4700, 6.4700, "tv_valmorel", "Doucy"),
            # Linkes Isere-Ufer gegenueber La Lechere: sechs Trails um 45,55 / 6,44, die sonst knapp
            # herausfielen (9-10 km von Doucy). Beaufortain bleibt bewusst draussen, siehe docs/tarentaise.md.
            (45.5480, 6.4420, "tv_valmorel", "Feissons-sur-Isere"),
            (45.3800, 6.7250, "tv_vanoise", "Pralognan-la-Vanoise"),
        ],
    ),
    # Aostatal, 2026-08-26. ~300 Trails auf ~600 km und ungewoehnlich vollstaendig: Aosta selbst, Courmayeur,
    # Pila, La Thuile, Cervinia, Val d'Ayas, Gressoney. Sieben Taeler, die alle in dasselbe Haupttal muenden
    # -- die Einteilung folgt genau diesen Seitentaelern, nicht Trailforks' 42 Gemeindekaesten.
    # Trailforks fuehrt unter dieser Region auch drei Zeilen, die gar nicht im Aostatal liegen
    # ("Alta Val Trebbia", "Lago di Ridracoli", "Parco Vena del Gesso" -- Ligurien und Emilia-Romagna);
    # die Anker-Regel wirft sie heraus und der Bau-Bericht nennt sie.
    "aostatal": dict(
        prefix="ao", label="Aostatal", countries=["IT"], material="Aostatal",
        # 11 statt 8/9: die Hochuebergaenge (Col de la Seigne, Grand Col Ferret, Col Chavannes, Col
        # Fenetre) liegen 9-11 km vom naechsten Dorf und gehoeren zweifelsfrei ins Tal. Geprueft, dass
        # dabei nichts aus dem Piemont hereinrutscht -- Sorba/Valsesia und die Valle-Cervo-Linien um
        # San Grato bleiben mit 10-14 km weiter draussen.
        max_anchor_km=11.0,
        subregions=[
            ("ao_aosta",        "Aosta",         "#be185d"),
            ("ao_monte_bianco", "Monte Bianco",  "#0f766e"),
            ("ao_paradiso",     "Gran Paradiso", "#4d7c0f"),
            ("ao_cervino",      "Cervino",       "#1d4ed8"),
            ("ao_monterosa",    "Monte Rosa",    "#b45309"),
            ("ao_bassa_valle",  "Bassa Valle",   "#7c3aed"),
            ("ao_valpelline",   "Valpelline",    "#475569"),
        ],
        anchors=[
            (45.7370, 7.3200, "ao_aosta", "Aosta"),
            (45.7150, 7.2900, "ao_aosta", "Gressan"),
            (45.7200, 7.3300, "ao_aosta", "Charvensod"),
            (45.6820, 7.3080, "ao_aosta", "Pila"),
            (45.7200, 7.2600, "ao_aosta", "Sarre"),
            (45.7500, 7.3500, "ao_aosta", "Saint-Christophe"),
            (45.7400, 7.4000, "ao_aosta", "Quart"),
            (45.7080, 7.2280, "ao_aosta", "Saint-Pierre"),
            (45.7450, 7.4550, "ao_aosta", "Nus"),
            (45.7900, 6.9700, "ao_monte_bianco", "Courmayeur"),
            (45.7550, 7.0400, "ao_monte_bianco", "Morgex"),
            (45.7300, 7.0700, "ao_monte_bianco", "La Salle"),
            (45.7130, 6.9500, "ao_monte_bianco", "La Thuile"),
            (45.7550, 7.0000, "ao_monte_bianco", "Pre-Saint-Didier"),
            (45.7000, 7.1600, "ao_monte_bianco", "Arvier"),
            (45.7750, 6.8600, "ao_monte_bianco", "Val Veny"),
            (45.8600, 7.0400, "ao_monte_bianco", "Val Ferret"),
            (45.6900, 7.1800, "ao_paradiso", "Introd"),
            (45.6080, 7.3560, "ao_paradiso", "Cogne"),
            (45.5900, 7.2100, "ao_paradiso", "Valsavarenche"),
            (45.5700, 7.1100, "ao_paradiso", "Rhemes-Notre-Dame"),
            (45.6300, 7.0700, "ao_paradiso", "Valgrisenche"),
            (45.7050, 7.2050, "ao_paradiso", "Villeneuve"),
            (45.9350, 7.6300, "ao_cervino", "Breuil-Cervinia"),
            (45.8750, 7.6250, "ao_cervino", "Valtournenche"),
            (45.8400, 7.5600, "ao_cervino", "Torgnon"),
            (45.8100, 7.5900, "ao_cervino", "Antey-Saint-Andre"),
            (45.8500, 7.6200, "ao_cervino", "Chamois"),
            (45.7500, 7.6150, "ao_cervino", "Chatillon"),
            (45.8300, 7.7250, "ao_monterosa", "Champoluc"),
            (45.7580, 7.7350, "ao_monterosa", "Brusson"),
            (45.7750, 7.8250, "ao_monterosa", "Gressoney-Saint-Jean"),
            (45.8250, 7.8250, "ao_monterosa", "Gressoney-La-Trinite"),
            (45.7100, 7.7100, "ao_monterosa", "Challand-Saint-Anselme"),
            (45.8100, 7.6900, "ao_monterosa", "Ayas"),
            (45.6670, 7.6900, "ao_bassa_valle", "Verres"),
            (45.6600, 7.6800, "ao_bassa_valle", "Issogne"),
            (45.6200, 7.6200, "ao_bassa_valle", "Champorcher"),
            (45.5850, 7.5350, "ao_bassa_valle", "Col Fenetre"),
            (45.7400, 7.5400, "ao_bassa_valle", "Pontey"),
            (45.7350, 7.4800, "ao_bassa_valle", "Fenis"),
            (45.7400, 7.5500, "ao_bassa_valle", "Chambave"),
            (45.6400, 7.7000, "ao_bassa_valle", "Arnad"),
            (45.5980, 7.7950, "ao_bassa_valle", "Pont-Saint-Martin"),
            (45.8300, 7.3150, "ao_valpelline", "Ollomont"),
            (45.8300, 7.3300, "ao_valpelline", "Valpelline"),
            (45.8250, 7.2300, "ao_valpelline", "Etroubles"),
            (45.8300, 7.1800, "ao_valpelline", "Saint-Rhemy"),
            (45.7800, 7.3000, "ao_valpelline", "Gignod"),
        ],
    ),
    # Bayerische Voralpen, 2026-08-26. Die mit Abstand groesste deutsche Luecke (Trailforks: 410 Trails auf
    # 669 km) und die einzige deutsche Kandidatin mit alpinen Laengen. Acht Reviere, die geografisch
    # zusammenhaengen, aber keinen gemeinsamen Namen tragen -- daher die eigene Einteilung.
    # BEWUSST DRAUSSEN: Trailforks' Gebiet "Isartrails" (42 Trails / 19 km) ist die Muenchner Isar, 60 km
    # noerdlich. Es ist mitgeerntet, bekommt aber keinen Anker und faellt damit heraus; die Namen stehen im
    # Bau-Bericht. Ein Anker "Muenchen" wuerde die Region bis in die Stadt ziehen.
    "voralpen": dict(
        prefix="bv", label="Bayerische Voralpen", countries=["DE"], material="Bayerische Voralpen",
        max_anchor_km=8.0,
        subregions=[
            ("bv_garmisch",   "Garmisch",       "#0f766e"),
            ("bv_mittenwald", "Mittenwald",     "#0891b2"),
            ("bv_ammergau",   "Ammergau",       "#4d7c0f"),
            ("bv_fuessen",    "Füssen",         "#b45309"),
            ("bv_kochel",     "Kochel/Walchen", "#1d4ed8"),
            ("bv_lenggries",  "Lenggries/Tölz", "#7c3aed"),
            ("bv_tegernsee",  "Tegernsee",      "#be185d"),
            ("bv_schliersee", "Schliersee",     "#475569"),
        ],
        anchors=[
            (47.4920, 11.0950, "bv_garmisch", "Garmisch-Partenkirchen"),
            (47.4770, 11.0200, "bv_garmisch", "Grainau"),
            (47.5200, 11.1150, "bv_garmisch", "Farchant"),
            (47.4800, 11.0800, "bv_garmisch", "Hausberg"),
            (47.5150, 11.1450, "bv_garmisch", "Wank"),
            (47.4750, 11.1100, "bv_garmisch", "Eckbauer"),
            (47.4180, 10.9850, "bv_garmisch", "Zugspitzplatt"),
            (47.4420, 11.2620, "bv_mittenwald", "Mittenwald"),
            (47.5220, 11.1900, "bv_mittenwald", "Wallgau"),
            (47.5050, 11.2600, "bv_mittenwald", "Kruen"),
            (47.5400, 11.2200, "bv_mittenwald", "Kaltenbrunn"),
            (47.4780, 11.3200, "bv_mittenwald", "Soiernhaus"),
            (47.4600, 11.3350, "bv_mittenwald", "Gumpenkar"),
            (47.5980, 11.0670, "bv_ammergau", "Oberammergau"),
            (47.5700, 11.0930, "bv_ammergau", "Ettal"),
            (47.6650, 11.0450, "bv_ammergau", "Bad Kohlgrub"),
            (47.6100, 11.0250, "bv_ammergau", "Unterammergau"),
            (47.6600, 11.0200, "bv_ammergau", "Saulgrub"),
            (47.5700, 10.9600, "bv_ammergau", "Linderhof"),
            (47.5800, 10.9800, "bv_ammergau", "Graswang"),
            (47.5700, 10.7000, "bv_fuessen", "Fuessen"),
            (47.5750, 10.7400, "bv_fuessen", "Schwangau"),
            (47.5800, 10.5600, "bv_fuessen", "Pfronten"),
            (47.6200, 10.5000, "bv_fuessen", "Nesselwang"),
            (47.6400, 10.8100, "bv_fuessen", "Halblech"),
            (47.6100, 10.7700, "bv_fuessen", "Buching"),
            (47.6600, 11.3700, "bv_kochel", "Kochel am See"),
            (47.5900, 11.3300, "bv_kochel", "Walchensee"),
            (47.5900, 11.4500, "bv_kochel", "Jachenau"),
            (47.7050, 11.4100, "bv_kochel", "Benediktbeuern"),
            (47.5950, 11.1900, "bv_kochel", "Eschenlohe"),
            (47.6300, 11.2400, "bv_kochel", "Ohlstadt"),
            (47.6800, 11.2000, "bv_kochel", "Murnau"),
            (47.6500, 11.3200, "bv_kochel", "Schlehdorf"),
            (47.6100, 11.3200, "bv_kochel", "Herzogstand"),
            (47.6830, 11.5700, "bv_lenggries", "Lenggries"),
            (47.7600, 11.5600, "bv_lenggries", "Bad Toelz"),
            (47.5700, 11.5300, "bv_lenggries", "Sylvenstein"),
            (47.5600, 11.4700, "bv_lenggries", "Fall"),
            (47.7300, 11.5300, "bv_lenggries", "Wackersberg"),
            (47.6600, 11.5500, "bv_lenggries", "Brauneck"),
            (47.6800, 11.4900, "bv_lenggries", "Arzbach"),
            (47.6900, 11.7650, "bv_tegernsee", "Rottach-Egern"),
            (47.7100, 11.7580, "bv_tegernsee", "Tegernsee"),
            (47.6400, 11.7450, "bv_tegernsee", "Kreuth"),
            (47.7500, 11.7350, "bv_tegernsee", "Gmund"),
            (47.7100, 11.7200, "bv_tegernsee", "Bad Wiessee"),
            (47.6000, 11.7300, "bv_tegernsee", "Wildbad Kreuth"),
            (47.5450, 11.7100, "bv_tegernsee", "Schwarzentenn"),
            (47.7350, 11.8600, "bv_schliersee", "Schliersee"),
            (47.6700, 11.8850, "bv_schliersee", "Spitzingsee"),
            (47.6740, 12.0130, "bv_schliersee", "Bayrischzell"),
            (47.7100, 11.9500, "bv_schliersee", "Fischbachau"),
            (47.6700, 12.0300, "bv_schliersee", "Sudelfeld"),
        ],
    ),
    # Bormio & Valtellina, 2026-08-26 -- der ausdrueckliche Wunsch des Nutzers, aus eigener Erfahrung:
    # "Da war ich schon mal im Bikepark und ganz oben ging auch eine epische Tour los... Bormio 3000 nach
    # Sankt Katharina oder so". Das ist die Abfahrt vom Bormio 3000 ueber das Valfurva nach Santa Caterina.
    # Der Zuschnitt geht bewusst ueber das Becken hinaus bis Tirano/Aprica -- ein Tal, eine Region --, hoert
    # aber vor Sondrio auf (60 km talabwaerts, Bassa Valtellina). Livigno ist nicht dabei: eigene Region.
    # Gemessen: der "Stelvio Natural Trail Park" liegt mit 19 Trails im Valfurva, nicht am Stilfserjoch.
    "bormio": dict(
        prefix="bo", label="Bormio & Valtellina", countries=["IT"], material="Bormio",
        max_anchor_km=9.0,
        subregions=[
            ("bo_bormio",      "Bormio",         "#be185d"),
            ("bo_valdidentro", "Valdidentro",    "#0f766e"),
            ("bo_valfurva",    "Valfurva",       "#b45309"),
            ("bo_valdisotto",  "Valdisotto/Oga", "#4d7c0f"),
            ("bo_grosio",      "Grosio/Tirano",  "#1d4ed8"),
            ("bo_aprica",      "Aprica/Teglio",  "#7c3aed"),
        ],
        anchors=[
            (46.4676, 10.3717, "bo_bormio", "Bormio"),
            (46.4650, 10.3450, "bo_bormio", "Bormio 2000"),
            (46.4750, 10.3300, "bo_bormio", "Bormio 3000"),
            (46.4864, 10.2814, "bo_valdidentro", "Isolaccia"),
            (46.4900, 10.2500, "bo_valdidentro", "Semogo"),
            (46.4550, 10.2200, "bo_valdidentro", "Arnoga"),
            (46.5250, 10.3200, "bo_valdidentro", "Cancano"),
            (46.5300, 10.2900, "bo_valdidentro", "Fraele"),
            (46.5350, 10.2600, "bo_valdidentro", "Alpisella"),
            (46.4800, 10.3450, "bo_valdidentro", "Premadio"),
            (46.4133, 10.4900, "bo_valfurva", "Santa Caterina"),
            (46.4520, 10.4380, "bo_valfurva", "San Nicolo"),
            (46.4580, 10.4250, "bo_valfurva", "Sant'Antonio"),
            (46.3450, 10.4930, "bo_valfurva", "Gavia"),
            (46.4000, 10.5800, "bo_valfurva", "Forni"),
            (46.4400, 10.3400, "bo_valdisotto", "Cepina"),
            (46.4600, 10.3600, "bo_valdisotto", "Oga"),
            (46.4300, 10.3800, "bo_valdisotto", "San Colombano"),
            (46.3000, 10.2800, "bo_grosio", "Grosio"),
            (46.3300, 10.2700, "bo_grosio", "Grosotto"),
            (46.3100, 10.3300, "bo_grosio", "Sondalo"),
            (46.2150, 10.1690, "bo_grosio", "Tirano"),
            (46.2100, 10.1300, "bo_grosio", "Villa di Tirano"),
            (46.1550, 10.1500, "bo_aprica", "Aprica"),
            (46.1730, 10.0680, "bo_aprica", "Teglio"),
            (46.1500, 10.0500, "bo_aprica", "Tresenda"),
            (46.1600, 10.2400, "bo_aprica", "Corteno Golgi"),
        ],
    ),
    # Vinschgau & Meran, 2026-08-26. Suedtiroler Nachbar des Kronplatz und die laengsten Linien im ganzen
    # Vergleichsfeld (148 Trails auf 394 km, also 2,7 km je Trail). Sechs Taeler, und die Grenzen sind
    # unsere: Trailforks kennt hier nur die Bezirke "Vinschgau" (Streuung 28 km!) und "Burggrafenamt".
    "vinschgau": dict(
        prefix="vg", label="Vinschgau & Meran", countries=["IT"], material="Vinschgau",
        # 10 statt der ueblichen 8: die Trails hier reichen weit in die Seitentaeler hinein (Stettiner
        # Huette, Eisjoechl, die 36er ueber Sulden), und mit 8 fielen fuenf davon heraus, obwohl sie
        # zweifelsfrei in der Region liegen. Geprueft: bei 10 kommt nichts Fremdes dazu.
        max_anchor_km=10.0,
        subregions=[
            ("vg_obervinschgau", "Obervinschgau",   "#0f766e"),
            ("vg_mitte",         "Vinschgau Mitte", "#b45309"),
            ("vg_naturns",       "Naturns/Schnals", "#4d7c0f"),
            ("vg_meran",         "Meran",           "#1d4ed8"),
            ("vg_ulten",         "Ultental",        "#7c3aed"),
            ("vg_passeier",      "Passeiertal",     "#be185d"),
        ],
        anchors=[
            (46.6880, 10.5430, "vg_obervinschgau", "Mals"),
            (46.6710, 10.5540, "vg_obervinschgau", "Glurns"),
            (46.7130, 10.5230, "vg_obervinschgau", "Burgeis"),
            (46.8290, 10.4990, "vg_obervinschgau", "Reschen"),
            (46.8100, 10.5400, "vg_obervinschgau", "Graun"),
            (46.6400, 10.4600, "vg_obervinschgau", "Taufers"),
            (46.6180, 10.5900, "vg_obervinschgau", "Prad"),
            (46.5700, 10.5500, "vg_obervinschgau", "Stilfs"),
            (46.5300, 10.5100, "vg_obervinschgau", "Trafoi"),
            (46.5200, 10.5800, "vg_obervinschgau", "Sulden"),
            (46.6280, 10.7690, "vg_mitte", "Schlanders"),
            (46.6170, 10.7000, "vg_mitte", "Laas"),
            (46.6180, 10.8600, "vg_mitte", "Latsch"),
            (46.5600, 10.7800, "vg_mitte", "Martell"),
            (46.6250, 10.9100, "vg_mitte", "Kastelbell"),
            (46.6200, 10.8300, "vg_mitte", "Goldrain"),
            (46.6470, 11.0030, "vg_naturns", "Naturns"),
            (46.6830, 11.0570, "vg_naturns", "Partschins"),
            (46.6480, 11.0300, "vg_naturns", "Plaus"),
            (46.7100, 10.9100, "vg_naturns", "Karthaus"),
            (46.7500, 10.8800, "vg_naturns", "Kurzras"),
            (46.6700, 11.1600, "vg_meran", "Meran"),
            (46.6900, 11.1600, "vg_meran", "Dorf Tirol"),
            (46.6900, 11.1800, "vg_meran", "Schenna"),
            (46.6300, 11.2300, "vg_meran", "Hafling"),
            (46.5900, 11.2100, "vg_meran", "Voeran"),
            (46.6150, 11.1500, "vg_meran", "Lana"),
            (46.6800, 11.1300, "vg_meran", "Algund"),
            (46.6500, 11.1400, "vg_meran", "Marling"),
            (46.5500, 10.9500, "vg_ulten", "St. Walburg"),
            (46.5100, 10.8600, "vg_ulten", "St. Nikolaus"),
            (46.5700, 11.0400, "vg_ulten", "St. Pankraz"),
            (46.7830, 11.2280, "vg_passeier", "St. Martin"),
            (46.8120, 11.2470, "vg_passeier", "St. Leonhard"),
            (46.7300, 11.1900, "vg_passeier", "Riffian"),
            (46.7800, 11.0800, "vg_passeier", "Pfelders"),
            (46.7550, 11.1350, "vg_passeier", "Moos in Passeier"),
        ],
    ),
    # Davos Klosters, 2026-08-26. Die groesste einzelne Luecke im Alpenbogen (153 Trails / 279 km bei
    # Trailforks) und direkter Nachbar des gebauten Bike Kingdom. Trailforks fuehrt alles unter EINEM
    # Gebiet "Davos Klosters" -- die Unterteilung ist also ganz unsere, nach den drei Taelern, in denen
    # die Linien tatsaechlich liegen (gemessen, nicht geschaetzt: 90 / 43 / 19 Trails).
    "davos": dict(
        prefix="dk", label="Davos Klosters", countries=["CH"], material="Davos",
        max_anchor_km=9.0,
        subregions=[
            ("dk_davos",      "Davos",      "#0f766e"),
            ("dk_klosters",   "Klosters",   "#b45309"),
            ("dk_landwasser", "Landwasser", "#7c3aed"),
        ],
        anchors=[
            (46.7930, 9.8200, "dk_davos", "Davos Platz"),
            (46.8060, 9.8400, "dk_davos", "Davos Dorf"),
            (46.7700, 9.8400, "dk_davos", "Jakobshorn"),
            (46.8300, 9.7900, "dk_davos", "Parsenn"),
            (46.7480, 9.7900, "dk_davos", "Rinerhorn"),
            (46.8200, 9.8900, "dk_davos", "Pischa"),
            (46.7300, 9.8500, "dk_davos", "Sertig"),
            (46.7700, 9.8800, "dk_davos", "Dischma"),
            (46.8600, 9.7600, "dk_davos", "Wolfgang"),
            (46.7900, 9.9400, "dk_davos", "Fluelapass"),
            (46.8700, 9.8800, "dk_klosters", "Klosters Platz"),
            (46.8850, 9.8700, "dk_klosters", "Klosters Dorf"),
            (46.8950, 9.8300, "dk_klosters", "Madrisa"),
            (46.8900, 9.8950, "dk_klosters", "Serneus"),
            (46.9140, 9.7770, "dk_klosters", "Kuablis"),
            (46.9200, 9.7300, "dk_klosters", "Fideris"),
            (46.9700, 9.8000, "dk_klosters", "St. Antoenien"),
            (46.7100, 9.7700, "dk_landwasser", "Monstein"),
            (46.7100, 9.7100, "dk_landwasser", "Wiesen"),
            (46.6740, 9.6870, "dk_landwasser", "Filisur"),
        ],
    ),
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
