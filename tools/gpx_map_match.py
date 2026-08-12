# -*- coding: utf-8 -*-
"""Reconstruct which named trails/lifts a recorded GPX tour actually rode, in ride order,
including repeats -- without a human stating the sequence.

## Why this exists

Building a segmented Trailrunde from a recorded GPX used to mean picking, for each candidate
trail, its single best-matching window against the tour track (see
`trailmap_pipeline`-adjacent ad-hoc scripts from the Naheland tours and the first two Livigno
"Tutti Frutti" attempts). That approach has a structural ceiling: an "epic" tour that rides the
same trail twice (out-and-back, or from two different approaches) or the same lift three times
can *never* be reconstructed by a "one best window per trail" search, no matter how the distance/
gap thresholds are tuned -- two full rounds of tuning on Tutti Frutti proved this empirically, and
the user caught both as wrong by their own riding knowledge even though each looked clean by every
automated check (no overlapping windows, tight avg/max distance).

The fix is a different algorithm shape, not a better threshold: **sequential map-matching**. Walk
every point of the recorded GPX in order and ask "which known trail or lift is closest right now",
the same way GPS-trace map-matching works in general (OSRM/Valhalla-style route reconstruction),
rather than asking "where does this one candidate best fit in the whole track". This lets the same
trail or lift reappear as a separate segment later in the sequence for free -- it falls out of
walking forward through time, not out of a rule that has to know revisits are possible.

## Validated against a known-good answer (2026-08-11)

The user hand-built Livigno's "Tutti Frutti Epic MTB Tour" (54 km, 20 real trail/lift rides,
several repeated) in the app's own Tourenbuilder and exported it as ground truth. Run blind
against the tour's own recorded GPX and Carosello 3000's 16 trails + 5 lifts, this module's
`match_gpx_to_network()` reproduced **20 of 20 elements, in the correct order and identity**
(including both Coast to Coast rides, both H-Dream rides, all three Baite Pel lift rides, and the
Madonon out-and-back) -- the one lift missed by the strict first pass (San Rocco - Baite Pel, whose
stored line the recording never approached closer than 27.5 m) was recovered by the built-in second,
loosened pass over the remaining unexplained gaps, where it was the dominant candidate by a wide
margin. The one *other* leftover big gap correctly resolved to "no match" -- a genuine ~8 km transfer
stretch back to the start with no trail or lift anywhere near it.

**Lifts MUST be included as candidates alongside trails.** Omitting them (the mistake in both
earlier Tutti Frutti attempts) silently turns every real lift ride into an anonymous connector.

**Direction and out-and-back handling (2026-08-11, same session, per the user's own follow-up
points).** `resolve_segments()` turns each raw run into actual clipped-and-oriented geometry:
- **A trail ridden backwards relative to its own stored direction is detected for free.** Project
  every point of a run onto the candidate's own along-line distance; if that trend falls instead
  of rises, the candidate was ridden reversed. No separate heuristic needed -- this is the same
  real case the user flagged from both this tour (Madonon, once each direction) and the Saalbach
  Challenges.
- **An out-and-back ride of the same trail produces one raw run** (contiguous in both id and
  time) but is really two rides. Detected by the same projected-position curve: a real
  out-and-back rises to an interior peak (or falls to an interior trough) instead of trending
  one way end to end; `_split_direction_reversals()` cuts it there.
- **Endpoint-anchored extension** (the user's own suggestion): a confident match can still fall
  short of a trail's true start/end under GPS noise even when the rider truly reached it. If the
  candidate's OWN stored endpoint lies within `endpoint_extend_m` of the recording near the run's
  own time window, the clip extends to that real endpoint instead of reporting a falsely partial
  ride. Needs a surprisingly generous default (60 m, not 20-25 m) for LIFT stations specifically --
  measured on Livigno's Baite Pel-Carosello 3000 gondola, the recording's closest approach to the
  station's own mapped point was 50 m, presumably because a real station platform is physically
  larger than a single lat/lon can represent. A genuinely partial ride (Naheland's Lower Flak,
  ridden only halfway; this tour's own first, deliberately short H-Dream visit) is unaffected,
  since its own true endpoint is never close to the recording in the first place.

**Full validation run, with `resolve_segments()` included (2026-08-11)**: of the 20 real elements
in the user's hand-built Tutti Frutti sequence, this pipeline reproduced **16 with matching length
to within 300 m and exactly correct identity/order/direction**, including the Madonon out-and-back
(one run reversed, one not) resolving to within a few metres of the user's own two lengths. The
remaining 4 are informative rather than wrong: two are the tour's own genuinely-partial rides
(short H-Dream visit, Federia slightly under its full length) where extension correctly declines to
fabricate a full ride; the weakest is San Rocco - Baite Pel, whose stored line the recording never
gets within 27.5 m of at any point (not just at its endpoints) -- a real geometry-precision limit
no amount of matching cleverness fixes, worth a manual nudge (a slightly re-drawn lift line, or a
lower per-lift threshold) rather than more algorithm.

**Ideas raised but not yet implemented (2026-08-11), worth revisiting for a denser network like
Pfälzerwald**, roughly in order of expected value:
1. **Elevation-direction as a lift/trail discriminator.** No extra data needed (elevation is
   already in the GPX): a lift climbs net-upward over its ride, a trail descent doesn't. Cheap and
   useful specifically where a lift's line runs geometrically close to a trail underneath it.
2. **Per-candidate elevation-PROFILE cross-check.** Each trail already has a known elevation
   profile; if a tentative match's recorded elevation trend contradicts it (climbing where the
   trail is known descent-only), that is a same-cost, independent signal that the match is wrong
   -- catches cases pure lat/lon distance cannot.
3. **Replace the stacked heuristics (mode-filter smoothing, gap-merge, min-run-length) with a
   proper Viterbi/HMM decode** -- state = current candidate, emission probability from distance,
   transition cost penalising a label change. Mathematically the right tool for exactly this
   problem and would likely subsume passes 1-2 and the smoothing step into one principled pass.
4. **Use the trail/lift network's own junction graph (shared endpoints within ~15-20 m) to
   route gaps**, not just validate them -- if two matched segments' own endpoints are both near a
   third known trail, that trail may be the honest way to close the gap, rather than a straight
   line or a slice of this one recording (which may not have taken that path at all).
5. **Per-segment confidence output** (coverage fraction, avg/max distance) so a human reviewer
   can jump straight to the shaky segments instead of re-checking everything.

## Usage

    import sys; sys.path.insert(0, r"D:\\Trailmap\\tools")
    from trailmap_pipeline import parse_gpx
    from gpx_map_match import match_gpx_to_network, resolve_segments

    candidates = {}
    candidates.update({t["id"]: TRAIL_GEO[t["id"]] for t in region_trails_of_interest})
    candidates.update({l["id"]: l["coords"] for l in region_lifts_of_interest})

    tour_gpx = parse_gpx(open("tour.gpx", encoding="utf-8").read())
    segments = match_gpx_to_network(tour_gpx, candidates)
    resolved = resolve_segments(tour_gpx, candidates, segments)
    # resolved: [{"id", "coords", "reversed", "gpx_start_idx", "gpx_end_idx"}, ...] in ride order,
    # each already clipped and oriented -- ready to interleave with connector geometry for the
    # gaps between them (straight line, OSM lookup, or a slice of this same GPX IF the gap's own
    # endpoints land close to one contiguous, short stretch of it -- check that before trusting
    # it: the recording's own cumulative position can jump around relative to whatever ride order
    # you actually want, since one recording is one specific day's route, not necessarily in a
    # hand-chosen canonical order -- confirmed on this exact tour, where several gaps' endpoints
    # were 15-22 km apart in the original recording despite being under 250 m apart in reality).

Tune `strict_thresh_m` / `loose_thresh_m` per region: Livigno's Carosello 3000 trails run close
together near lift stations, which is what makes the smoothing window and the min-run-length floor
necessary in the first place -- a denser trail network (more parallel lines close together, e.g.
Finale Ligure or Pfälzerwald) will likely need a smaller `strict_thresh_m` to avoid cross-talk
between adjacent trails, at the cost of needing the loose second pass more often.
"""
import sys

sys.path.insert(0, r"D:\Trailmap\tools")
from trailmap_pipeline import haversine_m, cumulative_km

__all__ = ["closest_point_on_polyline", "match_gpx_to_network", "resolve_segments"]


def _to_xy(lat0, p):
    import math
    la = lat0 * math.pi / 180
    return (p[1] * math.cos(la) * 111320, p[0] * 110540)


def closest_point_on_polyline(poly, pt):
    """Nearest point on poly to pt. Returns (dist_m, seg_index, t) -- t in [0,1] along that segment."""
    best = None
    for i in range(len(poly) - 1):
        a, b = poly[i], poly[i + 1]
        lat0 = a[0]
        A = _to_xy(lat0, a)
        B = _to_xy(lat0, b)
        P = _to_xy(lat0, pt)
        ABx, ABy = B[0] - A[0], B[1] - A[1]
        L2 = ABx * ABx + ABy * ABy
        if L2 < 1e-9:
            t = 0.0
        else:
            t = ((P[0] - A[0]) * ABx + (P[1] - A[1]) * ABy) / L2
            t = max(0.0, min(1.0, t))
        proj = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
        d = haversine_m(pt, proj)
        if best is None or d < best[0]:
            best = (d, i, t)
    return best


def _label_points(gpx_points, candidates, thresh_m, only_indices=None):
    """Nearest candidate id (or None if beyond thresh_m) per gpx point. only_indices restricts
    which point indices are (re)labelled -- used for the second, loosened pass over gaps only."""
    n = len(gpx_points)
    labels = [None] * n
    indices = only_indices if only_indices is not None else range(n)
    for i in indices:
        p = gpx_points[i]
        best_id, best_d = None, None
        for cid, cgeo in candidates.items():
            d, _, _ = closest_point_on_polyline(cgeo, p)
            if best_d is None or d < best_d:
                best_d, best_id = d, cid
        labels[i] = best_id if (best_d is not None and best_d <= thresh_m) else None
    return labels


def _smooth_mode(labels, window=11):
    """Majority-vote filter to remove flicker where candidates run close together."""
    from collections import Counter
    n = len(labels)
    half = window // 2
    out = []
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        out.append(Counter(labels[lo:hi]).most_common(1)[0][0])
    return out


def _run_length_encode(labels):
    runs = []
    i, n = 0, len(labels)
    while i < n:
        j = i
        while j + 1 < n and labels[j + 1] == labels[i]:
            j += 1
        runs.append([labels[i], i, j])
        i = j + 1
    return runs


def _split_direction_reversals(gpx_points, candidates, runs, min_segment_pts=15, min_segment_km=0.1):
    """A trail ridden out-and-back (Livigno's Madonon: down one way, then back up the same line)
    produces ONE consolidated run, since id and time are both contiguous -- but it is really two
    separate rides. Detect this: project every point of the run onto the candidate's own
    along-line distance; a real out-and-back shows up as that position rising to an interior
    extreme then falling back (or vice versa), not monotonic start-to-end. Split at that extreme
    when both halves are substantial, so an "epic" tour that revisits a trail immediately gets two
    segments, matching how a human (or the Tourenbuilder) would describe the ride."""
    out = []
    for cid, a, b in runs:
        cgeo = candidates[cid]
        ccum = cumulative_km(cgeo)
        positions = []
        for k in range(a, b + 1):
            _, seg_i, t = closest_point_on_polyline(cgeo, gpx_points[k])
            nxt = min(seg_i + 1, len(ccum) - 1)
            positions.append(ccum[seg_i] + t * (ccum[nxt] - ccum[seg_i]))

        n = len(positions)
        split_idx = None
        for extreme_fn in (max, min):
            m = positions.index(extreme_fn(positions))
            if m < min_segment_pts or (n - m) < min_segment_pts:
                continue
            span1 = abs(positions[m] - positions[0])
            span2 = abs(positions[m] - positions[-1])
            if span1 >= min_segment_km and span2 >= min_segment_km:
                split_idx = m
                break

        if split_idx is None:
            out.append((cid, a, b))
        else:
            out.append((cid, a, a + split_idx))
            out.append((cid, a + split_idx + 1, b))
    return out


def _consolidate(runs, gap_merge_pts, min_run_pts):
    """Merge same-id runs separated by a short gap (noise/brief GPS wobble, not a real
    revisit), then drop whatever is still too short to be a real ride."""
    named = [r for r in runs if r[0] is not None]
    consolidated = []
    for cid, a, b in named:
        if consolidated and consolidated[-1][0] == cid and (a - consolidated[-1][2]) <= gap_merge_pts:
            consolidated[-1][2] = b
        else:
            consolidated.append([cid, a, b])
    return [c for c in consolidated if (c[2] - c[1] + 1) >= min_run_pts]


def match_gpx_to_network(gpx_points, candidates, strict_thresh_m=15.0, loose_thresh_m=35.0,
                          smooth_window=11, gap_merge_pts=50, min_run_pts=20, min_gap_pts_for_pass2=60):
    """Reconstruct the ride order of a recorded tour against a network of known trails/lifts.

    `candidates`: {id: [[lat,lon], ...]} -- MUST include lifts, not just trails, or every real
    lift ride in the tour silently becomes an unattributed connector.

    Two passes:
    1. Strict-threshold sequential labelling + majority-vote smoothing + run consolidation. Finds
       the confident majority of real rides, including repeats, in the correct order.
    2. Within whatever large stretches pass 1 left completely unlabelled, re-label with a looser
       threshold. This recovers a real element whose stored geometry the recording never quite
       reached under the strict threshold (confirmed cause on Livigno: a lift's line, missed by
       12.5 m) -- without loosening the threshold globally, which would reintroduce cross-talk
       between trails that run close together elsewhere in the network.

    Returns an ordered list of {"id", "start_idx", "end_idx"} for confidently-matched stretches
    only. Gaps between them (including possibly a large final gap back to the tour's own start)
    are the caller's responsibility -- see module docstring.
    """
    n = len(gpx_points)

    pass1_labels = _smooth_mode(_label_points(gpx_points, candidates, strict_thresh_m), smooth_window)
    pass1_runs = _consolidate(_run_length_encode(pass1_labels), gap_merge_pts, min_run_pts)

    covered = [False] * n
    for _, a, b in pass1_runs:
        for k in range(a, b + 1):
            covered[k] = True
    big_gaps = []
    i = 0
    while i < n:
        if not covered[i]:
            j = i
            while j + 1 < n and not covered[j + 1]:
                j += 1
            if (j - i + 1) >= min_gap_pts_for_pass2:
                big_gaps.append((i, j))
            i = j + 1
        else:
            i += 1

    pass2_labels = list(pass1_labels)
    for a, b in big_gaps:
        loose = _label_points(gpx_points, candidates, loose_thresh_m, only_indices=range(a, b + 1))
        for k in range(a, b + 1):
            pass2_labels[k] = loose[k]

    pass2_smoothed = _smooth_mode(pass2_labels, smooth_window)
    final_runs = _consolidate(_run_length_encode(pass2_smoothed), gap_merge_pts, min_run_pts)
    final_runs = _split_direction_reversals(gpx_points, candidates, final_runs)

    return [{"id": cid, "start_idx": a, "end_idx": b} for cid, a, b in final_runs]


def resolve_segments(gpx_points, candidates, segments, endpoint_extend_m=60.0):
    """Turn match_gpx_to_network()'s GPX-point-index runs into ready-to-build segments: each
    candidate's OWN geometry, clipped to the ridden range and oriented the way it was actually
    ridden -- including a trail ridden backwards relative to its stored direction (real case:
    Livigno's Madonon, ridden once each way; also seen in the Saalbach Challenges).

    Direction and clip range both fall out of the same projection already used for the
    out-and-back split: project every point of the segment onto the candidate's own along-line
    distance. If it trends downward instead of up, the candidate was ridden reversed -- no
    separate direction detection needed, the position trend already says so.

    **Endpoint-anchored extension** (per the user's own suggestion, 2026-08-11): a real GPS
    imprecision or a wooded/steep stretch can leave the confident match short of a trail's actual
    start or end even when the rider truly reached it. If the candidate's own stored endpoint
    (not just the matched sub-range) lies within `endpoint_extend_m` of the recorded track
    somewhere near the segment's own time window, extend the clip to that real endpoint rather
    than reporting a falsely partial ride. This must stay conservative: it only fires when the
    endpoint itself is close to the track, not merely because "it would be nice if the whole
    trail counted" -- a genuinely partial ride (Naheland's Lower Flak, ridden only halfway) must
    still come out partial.
    """
    out = []
    for seg in segments:
        cid, a, b = seg["id"], seg["start_idx"], seg["end_idx"]
        cgeo = candidates[cid]
        ccum = cumulative_km(cgeo)

        def project(k):
            _, seg_i, t = closest_point_on_polyline(cgeo, gpx_points[k])
            nxt = min(seg_i + 1, len(ccum) - 1)
            return ccum[seg_i] + t * (ccum[nxt] - ccum[seg_i])

        pos_start, pos_end = project(a), project(b)
        reversed_ = pos_end < pos_start
        lo_pos, hi_pos = (pos_end, pos_start) if reversed_ else (pos_start, pos_end)

        # Endpoint-anchored extension: does the recording pass close to this candidate's own
        # geometric start (km 0) or end (km ccum[-1]) near this segment's own time window?
        window_lo, window_hi = max(0, a - 40), min(len(gpx_points) - 1, b + 40)
        d_to_geo_start = min(haversine_m(cgeo[0], gpx_points[k]) for k in range(window_lo, window_hi + 1))
        d_to_geo_end = min(haversine_m(cgeo[-1], gpx_points[k]) for k in range(window_lo, window_hi + 1))
        if d_to_geo_start <= endpoint_extend_m:
            lo_pos = 0.0
        if d_to_geo_end <= endpoint_extend_m:
            hi_pos = ccum[-1]

        lo_idx = next(i for i, c in enumerate(ccum) if c >= lo_pos)
        hi_idx = len(ccum) - 1 - next(i for i, c in enumerate(reversed(ccum)) if c <= hi_pos)
        coords = cgeo[lo_idx:hi_idx + 1]
        if reversed_:
            coords = coords[::-1]

        out.append({"id": cid, "coords": coords, "reversed": reversed_,
                    "gpx_start_idx": a, "gpx_end_idx": b})
    return out
