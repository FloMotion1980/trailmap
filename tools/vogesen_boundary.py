# -*- coding: utf-8 -*-
"""The Nordvogesen / Südvogesen boundary — the red line the user drew on a Trailforks map.

2026-08-19, the user's third and final word on the split: *"Ich würde alles unter der eingezeichneten
roten Linie zu der Region Südvogesen zählen"*, on a screenshot of the Trailforks map with a hand-drawn
red line running WNW→ESE, passing north of Le Bonhomme and Munster and south of Saint-Dié and
Ribeauvillé. It supersedes the earlier bracket-by-name cut ("ohne colmar und vosges_ouest"), and it
moves two brackets in opposite directions -- see the module note at the bottom.

HOW THE LINE WAS TURNED INTO NUMBERS, and how far to trust it. The screenshot carries no coordinates, so
the transform was fitted from labelled places whose real positions are known: Saint-Dié-des-Vosges,
Épinal, Gérardmer, Munster, Thann and Mulhouse. Latitude came out as
`lat = 48.284 - 0.001056 * (y - 70)` and longitude as `lon = 6.451 + 0.001453 * (x - 110)`; Gérardmer
reproduces to 0.003° with that, the worst check (Munster, whose label sits well above its dot) to 0.05°.
Reading the drawn line at its two ends gives **(48.260 N, 6.567 E) in the west and (48.124 N, 7.352 E)
in the east**, i.e. a straight line dropping 0.173° of latitude per degree of longitude.

**Accuracy is about ±0.04° (±4 km)**, and that is deliberately good enough: the user's own instruction
on the subject (2026-08-19) was "Ich gebe die Unterteilung Im Detail und damit die genauen Grenzen der
Trailregion an dich. So genau brauche ich das da nicht." So the line decides which SUB-REGION goes
where, via each bracket's own centroid, and a trail sitting within the error band stays with its bracket
-- decided, not escalated. What the audit is still for is catching a bracket or a trail that is on the
plainly wrong side, which it did three times on its first run.
Every bracket's centroid clears the line by at least 7 km, so the split itself does not depend on the
measurement error at all:

    kaysersberg  (Lac Blanc, Labaroche, Trois Épis, Turckheim, Le Bonhomme)  7 km SOUTH  -> Südvogesen
    ville        (Ribeauvillé, Lièpvre, Neubois, Breitenau)                 12 km NORTH  -> Nordvogesen
    vosges_ouest (Saint-Dié, Raon-l'Étape, Lac de la Maix, Donon)           18 km NORTH  -> Nordvogesen

The first and third are both CHANGES against what was built before this line arrived: `kaysersberg`
(with the Lac Blanc bike park, which the user had named as a southern park all along) moves south, and
`vosges_ouest` moves back north -- the earlier "ohne vosges_ouest" had put Saint-Dié in the south, but
the drawn line clearly runs south of it.
"""
import math

#: The drawn line's two ends, (lat, lon), read off the screenshot via the transform in the docstring.
WEST_END = (48.260, 6.567)
EAST_END = (48.124, 7.352)

#: Report any trail whose distance to the line is under this, in km -- inside the reading error, so a
#: build must not claim to have placed it correctly on the strength of the line alone.
NEAR_KM = 5.0

_SLOPE = (EAST_END[0] - WEST_END[0]) / (EAST_END[1] - WEST_END[1])


#: Trails whose Trailforks region membership contradicts where they physically are, so neither
#: bracket-by-centroid nor a nearest-centroid fallback can place them. Keyed by trail slug ->
#: (side, sub-region key). Add to this only with a measured distance in the comment, never a hunch.
#:
#: `kiosque`: filed under Trailforks' `gerardmer` region, but its line is at 48.2804, 6.9281 -- at
#: Saint-Die, 20 km north of Gerardmer and 9.2 km NORTH of the line. Its own upper half
#: (`kiosque-upper`, filed under a Saint-Die slug) was already in Nordvogesen 950 m away, so without
#: this the two halves of one trail sat in two different regions.
SLUG_OVERRIDE = {
    "kiosque": ("nord", "vosges_ouest"),
}


def override(slug):
    """(side, sub-region) for a slug the region maps cannot place, else None."""
    return SLUG_OVERRIDE.get(slug)


def boundary_lat(lon):
    """Latitude of the line at this longitude (extrapolated beyond the drawn ends, which is safe: the
    line only ever has to separate clusters that sit far from it)."""
    return WEST_END[0] + _SLOPE * (lon - WEST_END[1])


def side(lat, lon):
    """"nord" if this point is above the line, "sued" if below."""
    return "nord" if lat > boundary_lat(lon) else "sued"


def distance_km(lat, lon):
    """Rough north-south distance from the line in km (signed: positive = north of it).

    Measured along the meridian rather than perpendicular to the line. The line is nearly horizontal
    (10° from due east), so the difference is under 2 % -- irrelevant at a 5 km reporting threshold, and
    a meridian offset is the quantity that is actually easy to check against a map by eye.
    """
    return (lat - boundary_lat(lon)) * 110.574


def centroid(points):
    """Plain mean of [[lat, lon], ...] -- fine over an extent this small."""
    return [sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)]


def audit(trails, geo, expect):
    """Report trails that fall on the other side of the line, or close enough to it to be unclear.

    `trails` is a list of lineTrails entries, `geo` the region's trailGeo, `expect` "nord" or "sued".
    Returns (wrong_side, near_line), each a list of (name, sub-region, signed km).
    """
    wrong, near = [], []
    for t in trails:
        pts = geo[t["id"]]
        lat, lon = centroid(pts)
        km = distance_km(lat, lon)
        # Distance first, side second: a trail 2 km on the "wrong" side is inside this line's own
        # reading error and is genuinely unclear, not misplaced. Only a clear crossing is an error.
        if abs(km) < NEAR_KM:
            near.append((t["name"], t["region"], round(km, 1)))
        elif side(lat, lon) != expect:
            wrong.append((t["name"], t["region"], round(km, 1)))
    wrong.sort(key=lambda x: abs(x[2]), reverse=True)
    near.sort(key=lambda x: abs(x[2]))
    return wrong, near


def report(trails, geo, expect):
    wrong, near = audit(trails, geo, expect)
    if wrong:
        print("  ON THE WRONG SIDE of the red line (expected %s) -- %d:" % (expect, len(wrong)))
        for name, sub, km in wrong[:20]:
            print("    %-38s %-13s %+6.1f km" % (name[:38], sub, km))
    else:
        print("  red line: every trail is on the %s side" % expect)
    if near:
        # A count, not a list. These sit inside the line's own reading error and stay with their own
        # sub-region by decision (splitting a bracket across two regions would be the bigger wart), so
        # naming them every build is noise. The wrong-side check above is the part that earns its keep.
        print("  %d trail(s) within %.0f km of the line -- kept with their sub-region"
              % (len(near), NEAR_KM))
    return wrong, near
