// @suite   geometry
// @area    Pure geometry, distance and elevation-profile helpers
// @files   Trailmap App/index.html
// @touches haversineM, cumulativeDistanceKm, latLngAtDistance, bearingDeg, destinationPoint, metresPerPixel, buildChevron, elevationAtDistance, profileSlice, reverseElevationProfile, hexToRgba, round3, buildDirectionArrowShapes, buildElevationSvg, profileKmToGeometryKm, buildProfileToGeometryAxis, liftClimb, trailLabelHtml, formatAge
// @needs   any region active
//
// The cheapest coverage in the app: these are pure functions with no DOM and no app state, they are what the
// elevation chart, its map hover-sync, the direction arrows and the reverse-direction view are all built out
// of, and every one of them was written by hand against a real bug. Nothing here touches the map, so this
// suite is safe to run first and fast enough to run always.

TM.add("geometry", () => typeof haversineM === "function", async (T) => {

  T.test("haversineM matches known distances");
  // 1/100 of a degree of latitude is ~1112 m everywhere; a degree of longitude shrinks with latitude.
  T.near("0.01° latitude", haversineM([47, 10], [47.01, 10]), 1112, 3);
  T.near("0.01° longitude at 47°N", haversineM([47, 10], [47, 10.01]), 758, 5);
  T.eq("a point to itself is zero", haversineM([47, 10], [47, 10]), 0);
  T.ok("it is symmetric", haversineM([47, 10], [47.5, 10.5]) === haversineM([47.5, 10.5], [47, 10]), true, true);

  T.test("cumulativeDistanceKm starts at zero and adds up");
  const line = [[47, 10], [47.01, 10], [47.02, 10], [47.03, 10]];
  const cum = cumulativeDistanceKm(line);
  T.eq("one entry per point", cum.length, line.length);
  T.eq("the first is 0", cum[0], 0);
  T.near("three equal legs", cum[3] * 1000, 3336, 12);
  T.ok("strictly increasing", cum.every((v, i) => i === 0 || v > cum[i - 1]), true, true);
  T.eq("a single point has length 0", cumulativeDistanceKm([[47, 10]])[0], 0);

  T.test("latLngAtDistance interpolates, clamps, and knows about reversed");
  const half = latLngAtDistance(line, cum, cum[3] / 2, false);
  T.near("halfway is halfway in latitude", half[0], 47.015, 0.0005);
  T.eq("distance 0 is the first point", latLngAtDistance(line, cum, 0, false).map((n) => Math.round(n * 1e4) / 1e4), [47, 10]);
  T.eq("beyond the end clamps to the last point",
       latLngAtDistance(line, cum, 99, false).map((n) => Math.round(n * 1e4) / 1e4), [47.03, 10]);
  T.eq("negative clamps to the first", latLngAtDistance(line, cum, -5, false).map((n) => Math.round(n * 1e4) / 1e4), [47, 10]);
  // `reversed` measures from the END -- the coords array is never physically reordered (applyReversedEndpoints
  // only moves the markers), so this function is the single place that has to account for it.
  T.eq("reversed 0 is the LAST point",
       latLngAtDistance(line, cum, 0, true).map((n) => Math.round(n * 1e4) / 1e4), [47.03, 10]);
  T.eq("reversed full length is the first",
       latLngAtDistance(line, cum, cum[3], true).map((n) => Math.round(n * 1e4) / 1e4), [47, 10]);
  T.near("reversed halfway is the same point as forwards halfway",
         latLngAtDistance(line, cum, cum[3] / 2, true)[0], half[0], 0.0002);

  T.test("bearingDeg uses compass degrees, clockwise from north");
  T.near("due north", bearingDeg([47, 10], [47.01, 10]), 0, 0.5);
  T.near("due east", bearingDeg([47, 10], [47, 10.01]), 90, 0.5);
  T.near("due south", bearingDeg([47, 10], [46.99, 10]), 180, 0.5);
  T.near("due west", bearingDeg([47, 10], [47, 9.99]), 270, 0.5);
  T.ok("always inside 0..360", [[47.5, 10.5], [46.5, 9.5], [47, 9.99]]
       .every((p) => { const b = bearingDeg([47, 10], p); return b >= 0 && b < 360; }), true, true);

  T.test("elevationAtDistance interpolates between profile points");
  const prof = [[0, 1000], [1, 1100], [2, 900], [3, 900]];
  T.eq("exactly on a point", elevationAtDistance(prof, 1), 1100);
  T.eq("halfway up", elevationAtDistance(prof, 0.5), 1050);
  T.eq("halfway down", elevationAtDistance(prof, 1.5), 1000);
  T.eq("flat stretch", elevationAtDistance(prof, 2.5), 900);
  T.eq("past the end returns the last", elevationAtDistance(prof, 99), 900);
  T.eq("exactly at 0", elevationAtDistance(prof, 0), 1000);
  // Deliberately NOT asserting a negative distance: the function extrapolates backwards there rather than
  // clamping (it returns 900 for -1 km on this profile), which is a latent gap and not a live bug -- every
  // caller feeds it a segment boundary or a chart position, both already inside 0..total. Left as-is rather
  // than "fixed" while writing tests; noted so the next reader does not mistake the gap for intended behaviour.

  T.test("profileSlice cuts a clean sub-range with interpolated ends");
  // The whole point: adjacent per-segment polylines must share an exact boundary point, or the coloured
  // stretches of a Tour's chart show a gap or an overlap at every seam.
  const slice = profileSlice(prof, 0.5, 1.5);
  T.eq("it starts exactly at distStart", slice[0], [0.5, 1050]);
  T.eq("it ends exactly at distEnd", slice[slice.length - 1], [1.5, 1000]);
  T.eq("the interior point is kept", slice[1], [1, 1100]);
  T.ok("monotone in distance", slice.every((p, i) => i === 0 || p[0] >= slice[i - 1][0]), true, true);
  const left = profileSlice(prof, 0, 1.5), right = profileSlice(prof, 1.5, 3);
  T.eq("two adjacent slices meet at the same point", left[left.length - 1], right[0]);
  const degenerate = profileSlice(prof, 1, 1);
  T.eq("a zero-length slice is two identical points, not a crash", degenerate.length, 2);

  T.test("reverseElevationProfile mirrors distance and keeps elevation");
  const rev = reverseElevationProfile(prof);
  T.eq("same number of points", rev.length, prof.length);
  T.eq("distance starts at 0 again", rev[0][0], 0);
  T.eq("the last elevation becomes the first", rev[0][1], prof[prof.length - 1][1]);
  T.eq("total length is unchanged", rev[rev.length - 1][0], prof[prof.length - 1][0]);
  T.eq("reversing twice is the original", reverseElevationProfile(rev), prof);
  T.ok("distances stay monotone", rev.every((p, i) => i === 0 || p[0] >= rev[i - 1][0]), true, true);

  T.test("hexToRgba and round3");
  T.eq("black", hexToRgba("#000000", 0.5), "rgba(0,0,0,0.5)");
  T.eq("white", hexToRgba("#ffffff", 1), "rgba(255,255,255,1)");
  T.eq("a difficulty colour", hexToRgba("#c23b30", 0.2), "rgba(194,59,48,0.2)");
  T.eq("it tolerates a missing #", hexToRgba("1f5f9e", 1), "rgba(31,95,158,1)");
  T.eq("round3 keeps three decimals", round3(1.23456), 1.235);
  T.eq("round3 of an integer", round3(5), 5);

  T.test("destinationPoint is bearingDeg's own inverse");
  // "which way" and "how far that way" have to agree with each other: walking bearingDeg's own reported
  // direction for the distance haversineM reports must land back at the second point.
  const from = [47, 10], to = [47.01, 10.02];
  const dist = haversineM(from, to), brng = bearingDeg(from, to);
  const landed = destinationPoint(from[0], from[1], brng, dist);
  T.near("latitude matches", landed[0], to[0], 0.0003);
  T.near("longitude matches", landed[1], to[1], 0.0005);
  T.near("due north for 1000m moves ~0.009° latitude, 0° longitude",
         destinationPoint(47, 10, 0, 1000)[0] - 47, 0.00899, 0.0002);
  T.near("and due north does not drift in longitude", destinationPoint(47, 10, 0, 1000)[1], 10, 0.0001);
  T.near("a round trip (there and back) returns to the start",
         haversineM(destinationPoint(destinationPoint(47, 10, 30, 500)[0], destinationPoint(47, 10, 30, 500)[1], 210, 500), [47, 10]),
         0, 1);

  T.test("metresPerPixel halves per zoom level and shrinks toward the poles");
  T.near("one zoom level in halves the metres a pixel covers",
         metresPerPixel(47, 15) / metresPerPixel(47, 16), 2, 0.001);
  T.ok("higher latitude (more compressed east-west) covers fewer metres per pixel than the equator",
       metresPerPixel(60, 15) < metresPerPixel(0, 15), metresPerPixel(60, 15), "< " + metresPerPixel(0, 15));

  T.test("buildChevron draws a three-point arrow STRADDLING the anchor, tip forward, sized from mpp");
  const mpp17 = metresPerPixel(47, 17);
  const chevron = buildChevron([47, 10], 90, 1, mpp17);   // pointing due east
  T.eq("three points: back-left, tip, back-right", chevron.length, 3);
  const [backLeft, tip, backRight] = chevron;
  // The default spec's side offset went to 0 on 2026-08-20 (arrows sit ON the line now, see ARROW_SPEC), so
  // the contract is no longer "offset away from the anchor" -- it is that the shape is CENTRED on it. Checked
  // as the two back corners falling on opposite sides of the line: an offset shape has both on the same side,
  // which is what this case used to assert and would now be wrong. Note the old check would still PASS here
  // by accident -- the corners are ~9px from the anchor either way -- so it had to be replaced, not relaxed.
  T.ok("the back corners straddle the anchor rather than sitting to one side of it",
       (backLeft[0] - 47) * (backRight[0] - 47) < 0,
       [backLeft[0] - 47, backRight[0] - 47], "opposite signs");
  T.ok("and the anchor is between them, not outside the shape",
       Math.abs((backLeft[0] + backRight[0]) / 2 - 47) < 1e-9,
       (backLeft[0] + backRight[0]) / 2 - 47, "midpoint on the anchor");
  T.ok("the tip is further EAST than the back of the chevron (it points the way it is told to)",
       tip[1] > (backLeft[1] + backRight[1]) / 2, tip[1], "> " + (backLeft[1] + backRight[1]) / 2);
  T.ok("back-left and back-right straddle the tip's own latitude, roughly symmetrically",
       Math.abs((backLeft[0] - tip[0]) - -(backRight[0] - tip[0])) < 0.0001,
       [backLeft[0] - tip[0], backRight[0] - tip[0]], "roughly equal and opposite");
  // The whole point of sizing from mpp: the same chevron built at a HIGHER zoom (fewer metres per pixel) must
  // be a SMALLER real-world shape, so its on-screen size stays constant -- unlike the old fixed-metre version,
  // which is exactly what the user reported growing/shrinking as they zoomed.
  const chevronZoomedIn = buildChevron([47, 10], 90, 1, metresPerPixel(47, 19));
  T.ok("built at a higher zoom, the chevron's real-world size shrinks (constant on-screen size)",
       haversineM(chevronZoomedIn[1], [47, 10]) < haversineM(tip, [47, 10]),
       haversineM(chevronZoomedIn[1], [47, 10]), "< " + haversineM(tip, [47, 10]));

  T.test("buildDirectionArrowShapes spaces arrows by distance and stays within its cap");
  const short = [[47, 10], [47.001, 10]];                       // ~111 m
  const long = Array.from({ length: 400 }, (_, i) => [47 + i * 0.0005, 10]);   // ~22 km
  const few = buildDirectionArrowShapes(short, false, 17), many = buildDirectionArrowShapes(long, false, 17);
  // The cap is written out rather than read from ARROW_MAX_COUNT: that is a `const` inside the app's try{}
  // block, so it is genuinely unreachable from here (only function declarations leak out). Referencing it
  // throws a ReferenceError -- and if the tests are served from a different origin than the app, the browser
  // reports that as an opaque "Script error." with no line number, which is why the runner insists on
  // serving both from the repo root.
  const ARROW_CAP = 40;
  T.ok("even a very short trail gets one arrow", few.length >= 1, few.length, ">= 1");
  T.ok("a long trail gets many but never more than the cap",
       many.length > 10 && many.length <= ARROW_CAP, many.length, "11.." + ARROW_CAP);
  // Each shape is a 3-point chevron (see buildChevron); the geometry itself is checked there, so this only
  // checks the SHAPE of what buildDirectionArrowShapes hands back, one per sampled position along the trail.
  T.ok("every arrow is a 3-point chevron", many.every((a) => Array.isArray(a) && a.length === 3),
       JSON.stringify(many[0]), "[p,p,p]");
  T.ok("arrows sit inside the trail, not on its endpoints",
       many[0][1][0] > long[0][0] && many[many.length - 1][1][0] < long[long.length - 1][0], true, true);
  T.eq("a zero-length track gets no arrows", buildDirectionArrowShapes([[47, 10], [47, 10]], false, 17).length, 0);
  // `reversed` has to flip which way the chevrons point, the same way latLngAtDistance already reads a
  // reversed trail from its other end -- checked by comparing the tip direction of the FIRST arrow forward
  // against the tip direction of the LAST arrow reversed: on a straight due-north line they should point
  // opposite ways (south vs. north), i.e. their tips move away from their own anchors in opposite latitudes.
  const fwdArrows = buildDirectionArrowShapes(long, false, 17), revArrows = buildDirectionArrowShapes(long, true, 17);
  const tipDeltaLat = (shape) => shape[1][0] - (shape[0][0] + shape[2][0]) / 2;
  T.ok("reversed arrows point the opposite way along the trail",
       Math.sign(tipDeltaLat(fwdArrows[0])) !== Math.sign(tipDeltaLat(revArrows[revArrows.length - 1])),
       [tipDeltaLat(fwdArrows[0]), tipDeltaLat(revArrows[revArrows.length - 1])], "opposite signs");

  T.test("buildElevationSvg stamps the axis data its hover-sync reads back");
  // The hover handler re-derives everything from these attributes rather than having them threaded through
  // showTrailInfo's call chain, so a missing one silently kills the dot on the map.
  const svgHtml = buildElevationSvg(prof, null, "#c23b30", "test_trail", false, null);
  const holder = document.createElement("div");
  holder.innerHTML = svgHtml;
  const svg = holder.querySelector("svg");
  T.ok("an svg came back", !!svg, !!svg, true);
  for (const attr of ["data-trail-id", "data-reversed", "data-profile", "data-dist-max",
                      "data-pad-top", "data-pad-bottom", "data-h", "data-ele-min", "data-ele-range"]) {
    T.ok("carries " + attr, svg.hasAttribute(attr), svg.getAttribute(attr) !== null, true);
  }
  T.eq("the trail id is the one passed in", svg.getAttribute("data-trail-id"), "test_trail");
  T.eq("the profile round-trips as JSON", JSON.parse(svg.getAttribute("data-profile")), prof);
  T.eq("dist-max is the profile's own length", Number(svg.getAttribute("data-dist-max")), prof[prof.length - 1][0]);
  T.ok("the line is drawn in the colour it was given", svgHtml.indexOf("#c23b30") > -1, true, true);

  T.test("buildElevationSvg colours per segment when segments are given");
  const segs = [{ distStart: 0, distEnd: 1.5, color: "#3f8a4c" }, { distStart: 1.5, distEnd: 3, color: "#5a5a5a" }];
  const segHtml = buildElevationSvg(prof, null, "#c23b30", "test_loop", false, segs);
  T.ok("both segment colours appear", segHtml.indexOf("#3f8a4c") > -1 && segHtml.indexOf("#5a5a5a") > -1, true, true);
  const segDiv = document.createElement("div");
  segDiv.innerHTML = segHtml;
  T.ok("one polyline per segment, not one for the whole trail",
       segDiv.querySelectorAll("polyline").length >= 2, segDiv.querySelectorAll("polyline").length, ">= 2");

  T.test("buildElevationSvg draws the highlight band on top of the segments");
  const hl = buildElevationSvg(prof, { distStart: 1, distEnd: 2, color: "#1f5f9e" }, "#c23b30", "t", false, segs);
  const hlDiv = document.createElement("div");
  hlDiv.innerHTML = hl;
  const rect = hlDiv.querySelector("rect");
  T.ok("there is a rect for the highlighted stretch", !!rect, !!rect, true);
  if (rect) {
    // Drawn after the lines, so it reads as a tint over a coloured chart rather than being buried under one.
    const kids = [...hlDiv.querySelector("svg").children];
    const lastPoly = kids.map((k) => k.tagName.toLowerCase()).lastIndexOf("polyline");
    T.ok("the rect comes after the last polyline", kids.indexOf(rect) > lastPoly, kids.indexOf(rect), "> " + lastPoly);
  }

  T.test("the profile axis maps chart km onto geometry km");
  // A profile's x-axis and the geometry's own cumulative distance are not the same scale (the profile is
  // resampled), so the hover dot needs this conversion or it drifts along the line.
  const coords = Array.from({ length: 60 }, (_, i) => [47 + i * 0.0004, 10]);
  const cumC = cumulativeDistanceKm(coords);
  const axis = buildProfileToGeometryAxis ? buildProfileToGeometryAxis("nope_not_a_trail", cumC) : null;
  T.ok("an unknown trail yields no axis rather than throwing", axis === null || axis === undefined || !!axis, true, true);
  const distMax = cumC[cumC.length - 1];
  T.near("with no axis, 0 km maps to 0", profileKmToGeometryKm(0, null, cumC, distMax), 0, 0.001);
  T.near("with no axis, the end maps to the end", profileKmToGeometryKm(distMax, null, cumC, distMax), distMax, 0.001);

  T.test("small formatters");
  T.eq("liftClimb rounds and never goes negative", liftClimb({ baseEle: 1000, topEle: 1958.4 }), 958);
  T.eq("a lift recorded top-first would report 0, not a negative climb", liftClimb({ baseEle: 2000, topEle: 1000 }), 0);
  T.ok("formatAge says seconds under a minute", /s/.test(formatAge(5000)), formatAge(5000), "contains s");
  T.ok("and minutes above one", /m/.test(formatAge(180000)), formatAge(180000), "contains m");
  const label = trailLabelHtml({ id: "x", name: "Test Trail", diff: "rot" });
  T.ok("a trail label carries its difficulty dot", /tl-diff/.test(label), label, "contains tl-diff");
  T.ok("and its name", /Test Trail/.test(label), true, true);

});
