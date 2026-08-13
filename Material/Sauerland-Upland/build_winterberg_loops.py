# -*- coding: utf-8 -*-
"""Add the four Trailpark Winterberg loops (Bremberg-, Family First-, Poppenberg-, Sürenberg-Loop)
as Trailrunden into the already-built `regions/sauerland.json`, 2026-08-13.

Source: each loop has its own real recorded GPX (Outdooractive-hosted, via winterberg.de's
`poi3.api.eo-heimat.de` widget backend -- `GET https://poi3.api.eo-heimat.de/poi/?apiKey=<key>&slug=<id>`
returns `route.gpx.url`, a real `outdooractive.com/download.tour.gpx?i=<n>` link). The three loops
whose own `/strecke-detail/<id>/` page renders (Family First, Poppenberg-Loop, Sürenberg-Loop) made
this obvious; Bremberg-Loop's own page 404s (a site bug, not a data gap) but the same API endpoint
answers for it too, apiKey and all, so all four were fetched the same way -- see
`winterberg_loops_gpx/*.gpx`. This replaces the original plan of guessing a trail order from the
loops' prose descriptions, which the user correctly pointed out was unnecessary once the per-trail
GPX pattern (already used for the 16 individual Trailpark Winterberg trails) turned out to cover the
loops too.

Sequential map-matching (`tools/gpx_map_match.py`) reconstructs which of Trailpark Winterberg's own
16 trails each loop actually rides, in ride order, against `candidates` restricted to
`region=="trailpark_winterberg"` only (Bikepark Winterberg/"The Mother" is a different, unconnected
hill -- see build_sauerland.py's own module docstring -- and Trailpark Winterberg has no lifts, so
lifts are not candidates here either). Connectors (fireroad/access stretches between trails) are
built from the loop's OWN recorded GPX, not guessed or looked up on OSM, since the actual ridden
connector is sitting right there in the same recording.

Difficulty mapping: the API's own 3-tier field (easy/intermediate/hard) mirrors winterberg.de's
LEICHT/MITTEL/SCHWER, mapped the same way build_sauerland.py already maps that scale for the other
16 Trailpark Winterberg trails: easy->blau, intermediate->rot, hard->schwarz. Length/up/down use the
API's own published `state` numbers (site's own numbers win over GPX-derived, per project
convention), not the resampled profile's gain/loss.
"""
import json
import os
import sys

sys.path.insert(0, r"D:\Trailmap\tools")
from trailmap_pipeline import (parse_gpx, build_profile, cumulative_km, douglas_peucker,
                                dedupe_points, write_region, region_summary, SIMPLIFY_EPS_M)
from gpx_map_match import match_gpx_to_network, resolve_segments

MAT = r"D:\Trailmap\Material\Sauerland-Upland"
GPX_DIR = os.path.join(MAT, "winterberg_loops_gpx")
REGION_PATH = r"D:\Trailmap\Trailmap App\regions\sauerland.json"

DIFF_MAP = {"easy": "blau", "intermediate": "rot", "hard": "schwarz"}

# (loop_id, name, gpx_filename, api difficulty, official (len_km, up_m, down_m))
LOOPS = [
    ("wb_loop_family_first", "Family First", "family_first.gpx", "easy", (9.82, 231, 231)),
    ("wb_loop_poppenberg", "Poppenberg-Loop", "poppenberg_loop.gpx", "easy", (5.99, 201, 191)),
    ("wb_loop_bremberg", "Bremberg-Loop", "bremberg_loop.gpx", "intermediate", (6.68, 218, 218)),
    ("wb_loop_suerenberg", "Sürenberg-Loop", "suerenberg_loop.gpx", "hard", (6.28, 217, 217)),
]


def round_coords(pts):
    return [[round(p[0], 6), round(p[1], 6)] for p in pts]


def build_loop(loop_id, name, gpx_filename, api_diff, official, candidates):
    raw = parse_gpx(open(os.path.join(GPX_DIR, gpx_filename), encoding="utf-8").read())

    segs = match_gpx_to_network(raw, candidates)
    resolved = resolve_segments(raw, candidates, segs)
    if not resolved:
        raise SystemExit("%s: matched nothing against Trailpark Winterberg's own trails" % loop_id)

    # Interleave the resolved trail runs with connector stretches built from THIS loop's own GPX
    # (the actual ridden connector, not a guess) -- one connector for every gap, including a
    # possible leading stretch before the first match and a trailing one closing the loop.
    trail_segments = []
    prev_end = 0
    for r in resolved:
        if r["gpx_start_idx"] > prev_end:
            raw_slice = raw[prev_end:r["gpx_start_idx"] + 1]
            if len(raw_slice) >= 2:
                coords = round_coords(douglas_peucker(dedupe_points(raw_slice), SIMPLIFY_EPS_M))
                if len(coords) >= 2:
                    trail_segments.append({"coords": coords, "trailId": None})
        trail_segments.append({"coords": r["coords"], "trailId": r["id"]})
        prev_end = r["gpx_end_idx"]
    if prev_end < len(raw) - 1:
        raw_slice = raw[prev_end:]
        coords = round_coords(douglas_peucker(dedupe_points(raw_slice), SIMPLIFY_EPS_M))
        if len(coords) >= 2:
            trail_segments.append({"coords": coords, "trailId": None})

    # Critical invariant (docs/trailrunde-feature.md): TRAIL_GEO[loopId] must be the exact
    # concatenation of TRAIL_SEGMENTS' own coords, in order -- never re-derived independently.
    geo = [pt for seg in trail_segments for pt in seg["coords"]]
    geo_total_km = cumulative_km(geo)[-1]

    # Elevation profile comes from the loop's OWN raw recording (build_profile's usual pipeline:
    # simplify, then resample by distance) -- independent of the segment-concatenated geometry,
    # exactly like build_trail() does for any ordinary trail.
    simplified = douglas_peucker(dedupe_points(raw), SIMPLIFY_EPS_M)
    prof_coords = round_coords(simplified)
    prof_ele = [p[2] if len(p) > 2 else None for p in simplified]
    profile, _gain, _loss = build_profile(prof_coords, prof_ele)
    profile_total_km = profile[-1][0]
    scale = profile_total_km / geo_total_km if geo_total_km else 1.0

    cum = cumulative_km(geo)
    idx = 0
    for seg in trail_segments:
        n = len(seg["coords"])
        seg["distStart"] = round(cum[idx] * scale, 4)
        seg["distEnd"] = round(cum[idx + n - 1] * scale, 4)
        idx += n
    del idx

    length_km, up, down = official
    entry = {"id": loop_id, "name": name, "region": "trailpark_winterberg",
             "diff": DIFF_MAP[api_diff], "len": length_km, "up": up, "down": down, "loop": True}

    matched_ids = [r["id"] for r in resolved]
    print("  %-22s %2d segments (%d matched trails: %s), geo %.2f km, profile %.2f km"
          % (loop_id, len(trail_segments), len(matched_ids), ", ".join(matched_ids),
             geo_total_km, profile_total_km))
    return entry, geo, profile, trail_segments


def main():
    d = json.load(open(REGION_PATH, encoding="utf-8"))
    candidates = {t["id"]: d["trailGeo"][t["id"]] for t in d["lineTrails"]
                  if t["region"] == "trailpark_winterberg" and not t.get("loop")}
    print("candidates: %d Trailpark Winterberg trails" % len(candidates))

    trail_segments_all = dict(d.get("trailSegments") or {})
    for loop_id, name, gpx_filename, api_diff, official in LOOPS:
        entry, geo, profile, segs = build_loop(loop_id, name, gpx_filename, api_diff, official,
                                                candidates)
        d["lineTrails"] = [t for t in d["lineTrails"] if t["id"] != loop_id] + [entry]
        d["trailGeo"][loop_id] = geo
        d["elevationProfiles"][loop_id] = profile
        trail_segments_all[loop_id] = segs

    data = write_region(REGION_PATH, d["lineTrails"], d["trailGeo"], d["elevationProfiles"],
                         places=d.get("places"), lifts=d.get("lifts"),
                         trail_segments=trail_segments_all)
    print(region_summary(data))


if __name__ == "__main__":
    main()
