"""Fill in the `places` (village-label) list for regions that have none, from OSM's own place nodes.

WHY OSM AND NOT A HAND-TYPED LIST: the base map *is* OSM, so its `place` node is exactly where the base map
draws that village's name -- and since 2026-07-28 our label is centred on the same point in order to cover it,
so the name appears once instead of twice. A hand-typed coordinate misses that by design; Samnaun's was 1460 m
out. See the Donnersberg/"match the base map" note in CLAUDE.md.

WHY PROXIMITY TO TRAILS AND NOT THE BOUNDING BOX: the regions differ by two orders of magnitude in area
(Brandnertal 3x4 km, Odenwald 60x50 km). Every place inside the Odenwald's box would be dozens of labels
covering the map. What makes a label useful is that it orients you relative to the trails, so the filter is
the distance from a place to the nearest trail point:

    city/town   <= TOWN_MAX_KM     (bigger settlements stay useful as landmarks from further away)
    village     <= VILLAGE_MAX_KM
    hamlet      <= HAMLET_MAX_KM   (only where the region would otherwise have almost no labels)

then capped at MAX_PLACES per region, ranked by place type and distance. Existing regions were the
calibration: Paznaun carries 4 labels for a 20x26 km area, 3-Länder 3 for 6x14 km.

    python tools/add_region_places.py --dry-run        # report what it would add, change nothing
    python tools/add_region_places.py                  # write the regions that have no places yet
    python tools/add_region_places.py odenwald --force # redo one, replacing its existing list

Writes with the pipeline's own writer, so the files keep their one-line shape. Run
tools/update_region_versions.py afterwards -- the script reminds you.
"""
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trailmap_pipeline import haversine_m, overpass, write_region  # noqa: E402
from validate_region import _block_at, _entries, _strip_comments  # noqa: E402  -- catalog parsing

REGIONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "Trailmap App", "regions")

TOWN_MAX_KM = 5.0
VILLAGE_MAX_KM = 2.5
HAMLET_MAX_KM = 1.2
MAX_PLACES = 10
#: Two kept labels must be at least this far apart. Without it the population ranking hands a whole
#: agglomeration's suburbs a place each -- Suedvogesen gave six of its slots to Mulhouse/Illzach/
#: Kingersheim/Pfastatt/Lutterbach/Richwiller, which on screen is one blob and costs six mountain
#: villages their label. The higher-ranked of a close pair wins, which is why this is applied after the
#: sort rather than during it. Raised from 4 to 8 km on the user's own reading of the result
#: (2026-08-20, "zu viele Orte ... da wo ... viele Orte beieinander liegen").
MIN_SEPARATION_KM = 8.0

#: Labels per sub-region, as `base + trails // per_extra`, capped. The other half of the same request
#: ("ausduennen da wo wenig Trails sind"): a bracket with 14 trails does not need the same number of
#: labels as one with 148, and MAX_PLACES alone cannot express that because it is a region-wide total that
#: the population ranking then spends wherever the biggest towns happen to be. A place is attributed to
#: whichever sub-region owns the trail nearest to it.
SUB_QUOTA_BASE = 1
SUB_QUOTA_PER_EXTRA = 45
SUB_QUOTA_MAX = 4
#: Per-region override of MAX_PLACES. The default suits a resort-sized region (Brandnertal is 3x4 km);
#: it does not suit one that spans a whole massif, where ten labels leave most sub-regions anonymous.
#: Keyed by region, with the reason, so the numbers stay arguable instead of arbitrary.
MAX_PLACES_BY_REGION = {
    # All three span a whole massif, so the default 10 would leave brackets anonymous -- but the
    # per-sub-region quota below is what actually shapes the result now, and all land well under this
    # ceiling. The Schwarzwald joined them on 2026-08-20, when the Trailforks sweep took it from 119
    # trails in 7 brackets to 619 in 10, reaching from Loerrach to Pforzheim.
    "nordvogesen": 18,
    "suedvogesen": 18,
    "schwarzwald": 18,
}
MIN_VILLAGE_POP = 600     # see the note below
KNOWN_MAX_KM = 2.0        # for places that carry a wikidata/wikipedia tag but are small
RANK = {"city": 0, "town": 1, "village": 2, "hamlet": 3}
BBOX_MARGIN_DEG = 0.06          # ~6 km, so a town just outside the trails' box can still qualify


def build_script_labels(key):
    """Sub-region labels from `tools/build_<key>.py`'s own SUBREGIONS table.

    For a region that is fully built but not yet in REGION_CATALOG -- which is the normal state while
    index.html is being worked on elsewhere -- the build script is the authoritative statement of what the
    sub-regions are called. Without this the catalog lookup returns nothing, and every "named after one of
    the region's own sub-regions" qualifier silently stops firing, which is exactly the check that keeps
    the useful villages and drops the farmsteads.
    """
    try:
        mod = __import__("build_" + key)
    except Exception:
        return []
    subs = getattr(mod, "SUBREGIONS", None) or {}
    labels = []
    for entry in subs.values():
        label = entry[0] if isinstance(entry, (list, tuple)) else entry
        # "Barr / Mont Sainte-Odile" and "Kaysersberg / Lac Blanc" name two things each; split them, or
        # the substring test only ever matches the first.
        labels.extend(part.strip() for part in str(label).replace("(", "/").replace(")", "/").split("/")
                      if part.strip())
    return labels


def sub_region_labels(key):
    """The group's own label plus its sub-regions' labels, e.g. ["Serfaus-Fiss-Ladis", "Serfaus", "Fiss/Ladis"].

    LABELS, not the sub-region keys: the keys are internal slugs and matching against them lost Ladis in
    Serfaus while keeping valley villages like Prutz that have nothing to do with the region. The region's own
    names are the most reliable statement of which settlements it is about.
    """
    src = _strip_comments(io.open(os.path.join(os.path.dirname(REGIONS), "index.html"),
                                 encoding="utf-8").read())
    block, _ = _block_at(src, src.index("{", src.index("const REGION_CATALOG")))
    for gkey, body in _entries(block):
        if gkey != key:
            continue
        labels = re.findall(r'label\s*:\s*"([^"]*)"', body)
        return labels
    return []


def region_files():
    return sorted(f[:-5] for f in os.listdir(REGIONS)
                  if f.endswith(".json") and f != "version.json")


def load(key):
    return json.load(io.open(os.path.join(REGIONS, key + ".json"), encoding="utf-8"))


def trail_points(data, stride):
    """Every stride-th coordinate of every trail -- enough to measure distance-to-region against."""
    pts = []
    for g in data["trailGeo"].values():
        pts.extend(g[::stride] or g[:1])
    return pts


def fetch_places(data):
    lats = [c[0] for g in data["trailGeo"].values() for c in g]
    lons = [c[1] for g in data["trailGeo"].values() for c in g]
    box = (min(lats) - BBOX_MARGIN_DEG, min(lons) - BBOX_MARGIN_DEG,
           max(lats) + BBOX_MARGIN_DEG, max(lons) + BBOX_MARGIN_DEG)
    query = ('[out:json][timeout:180];\n'
             'node["place"~"^(city|town|village|hamlet)$"]["name"]'
             '(%.5f,%.5f,%.5f,%.5f);\nout body;' % box)
    return overpass(query)["elements"]


def pick(data, elements, sub_labels, allow_hamlets, cap=None):
    """Which OSM place nodes deserve a label on this region's map.

    Distance alone is not enough. Austria in particular tags a lot of tiny hamlet-sized settlements as
    `village`, and Bikecircus filled its whole quota with Pirzbichl (67 inhabitants), Grießen (79) and Madreit
    (91) while Saalbach, Leogang and Fieberbrunn competed for the leftovers. `population` turns out to be
    well-tagged and separates them cleanly -- 4300/3582/1947 against 67/79/91 -- so a village qualifies if it
    is either big enough, or named after one of the region's own sub-regions (those ARE the relevant
    villages, by construction), or close enough to the trails that its size does not matter.
    """
    # Coarse pass over a subsampled track first, then an exact one only for the survivors: the full product
    # would be millions of pairs for Pfälzerwald's 437 trails.
    coarse = trail_points(data, 25)
    fine = trail_points(data, 3)
    haystack = " ".join(sub_labels).lower()
    out = []
    for el in elements:
        tags = el["tags"]
        kind = tags["place"]
        name = tags["name"]
        if kind == "hamlet" and not allow_hamlets:
            continue
        limit = (TOWN_MAX_KM if kind in ("city", "town")
                 else VILLAGE_MAX_KM if kind == "village"
                 else HAMLET_MAX_KM)
        here = (el["lat"], el["lon"])
        rough = min(haversine_m(here, p) for p in coarse) / 1000.0
        if rough > limit + 1.5:
            continue
        exact = min(haversine_m(here, p) for p in fine) / 1000.0
        if exact > limit:
            continue
        try:
            pop = int(str(tags.get("population", "0")).replace(" ", ""))
        except ValueError:
            pop = 0
        # A WHOLE WORD, not a substring. "Au" (1 335 inhabitants, in the Hexental) counted as a namesake
        # of the Schwarzwald because "au" is the tail of "Bikepark Todtnau" -- and being a namesake both
        # sorts first and is exempt from MIN_SEPARATION_KM, so it took the Freiburg bracket's first slot
        # and then knocked out Freiburg itself, a city of 230 000, for sitting within 8 km of it. Found
        # 2026-08-20 while building the Schwarzwald; a region only re-picks its places under --force, so
        # this changes no shipped list until one is deliberately rebuilt.
        named = re.search(r"\b%s\b" % re.escape(name.lower()), haystack) is not None
        # Three ways for a small settlement to qualify, and proximity is deliberately NOT one of them: in a
        # bike park the trails run past everything, so distance alone gave Bikecircus three slots to Grießen
        # (79 inhabitants), Berg (130) and Rain (229), and gave Sölden nine unnamed hamlets (Wildmoos, Platte,
        # Im Brand ...) while dropping Zwieselstein, which is a real village people navigate by.
        #   - named after one of the region's own sub-regions
        #   - big enough by population
        #   - carries a wikidata/wikipedia tag, i.e. somebody wrote an article about it: that is what separates
        #     Zwieselstein and Hochsölden from a cluster of farmsteads, where population alone cannot.
        known = bool(tags.get("wikidata") or tags.get("wikipedia"))
        if kind in ("village", "hamlet") and not named:
            if pop >= MIN_VILLAGE_POP:
                pass
            elif known and exact <= KNOWN_MAX_KM:
                pass
            else:
                continue
        out.append({"name": name, "lat": round(el["lat"], 5), "lng": round(el["lon"], 5),
                    "_kind": kind, "_km": round(exact, 2), "_pop": pop, "_named": named,
                    "_known": known})
    # Sub-region namesakes first, then bigger before smaller, then nearer before further: what survives the
    # cap should be what a rider would use to orient themselves.
    out.sort(key=lambda p: (not p["_named"], RANK[p["_kind"]], -p["_pop"], p["_km"]))

    # Which sub-region each candidate belongs to, and how many labels that sub-region may have.
    per_sub = {}
    for t in data["lineTrails"]:
        per_sub[t["region"]] = per_sub.get(t["region"], 0) + 1
    quota = dict((sub, min(SUB_QUOTA_MAX, SUB_QUOTA_BASE + n // SUB_QUOTA_PER_EXTRA))
                 for sub, n in per_sub.items())
    owner = {}
    for t in data["lineTrails"]:
        for c in data["trailGeo"][t["id"]][::4] or data["trailGeo"][t["id"]][:1]:
            owner.setdefault(t["region"], []).append(c)

    used = {}
    kept = []
    for cand in out:
        if len(kept) >= (cap or MAX_PLACES):
            break
        here = (cand["lat"], cand["lng"])
        # A sub-region's OWN namesake is exempt from the separation rule: it is the name that bracket is
        # called by, so losing it to a merely-bigger neighbour defeats the point of having labels at all.
        # La Bresse (4 041, and the name of an 82-trail bracket plus a bike park) was dropped for sitting
        # 8.15 km from Gerardmer, i.e. by 150 m of threshold.
        if not cand["_named"] and any(
                haversine_m(here, (k["lat"], k["lng"])) / 1000.0 < MIN_SEPARATION_KM for k in kept):
            continue
        sub = min(owner, key=lambda sr: min(haversine_m(here, c) for c in owner[sr]))
        if used.get(sub, 0) >= quota.get(sub, SUB_QUOTA_MAX):
            continue
        used[sub] = used.get(sub, 0) + 1
        cand["_sub"] = sub
        kept.append(cand)
    return kept


def main(argv):
    dry = "--dry-run" in argv
    force = "--force" in argv
    wanted = [a for a in argv if not a.startswith("--")] or region_files()
    touched = []
    for key in wanted:
        data = load(key)
        existing = data.get("places") or []
        if existing and not force:
            print("%-16s skipped, already has %d place(s)" % (key, len(existing)))
            continue
        try:
            elements = fetch_places(data)
        except Exception as err:
            print("%-16s OVERPASS FAILED: %s" % (key, err))
            continue
        labels = sub_region_labels(key) or build_script_labels(key) or [key]
        cap = MAX_PLACES_BY_REGION.get(key, MAX_PLACES)
        picked = pick(data, elements, labels, allow_hamlets=False, cap=cap)
        if len(picked) < 2:      # a park whose valley village is tagged as a hamlet would end up empty
            picked = pick(data, elements, labels, allow_hamlets=True, cap=cap)
        print("%-16s %2d von %3d Kandidaten: %s" % (
            key, len(picked), len(elements),
            ", ".join("%s (%s, %.1f km, pop %d%s%s)" % (
                p["name"], p.get("_sub", p["_kind"]), p["_km"], p["_pop"],
                ", Namensgeber" if p["_named"] else "",
                ", bekannt" if p["_known"] and not p["_named"] else "")
                      for p in picked)))
        if dry or not picked:
            continue
        data["places"] = [{"name": p["name"], "lat": p["lat"], "lng": p["lng"]} for p in picked]
        write_region(os.path.join(REGIONS, key + ".json"), data["lineTrails"], data["trailGeo"],
                     data["elevationProfiles"], places=data["places"],
                     lifts=data.get("lifts"), trail_segments=data.get("trailSegments"))
        touched.append(key)
        time.sleep(2)            # be a good Overpass citizen between regions
    if touched:
        print("\ngeschrieben: %s\n-> jetzt tools/update_region_versions.py laufen lassen" % ", ".join(touched))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
