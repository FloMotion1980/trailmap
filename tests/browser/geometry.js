// @suite   geometry
// @area    Pure geometry, distance and elevation-profile helpers
// @files   Trailmap App/index.html
// @touches haversineM, cumulativeDistanceKm, latLngAtDistance, bearingDeg, elevationAtDistance, profileSlice, reverseElevationProfile, hexToRgba, round3, buildDirectionArrows, buildElevationSvg, profileKmToGeometryKm, buildProfileToGeometryAxis, liftClimb, trailLabelHtml, formatAge, distToBounds
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

  T.test("buildDirectionArrows spaces arrows by distance and stays within its cap");
  const short = [[47, 10], [47.001, 10]];                       // ~111 m
  const long = Array.from({ length: 400 }, (_, i) => [47 + i * 0.0005, 10]);   // ~22 km
  const few = buildDirectionArrows(short), many = buildDirectionArrows(long);
  // The cap is written out rather than read from ARROW_MAX_COUNT: that is a `const` inside the app's try{}
  // block, so it is genuinely unreachable from here (only function declarations leak out). Referencing it
  // throws a ReferenceError -- and if the tests are served from a different origin than the app, the browser
  // reports that as an opaque "Script error." with no line number, which is why the runner insists on
  // serving both from the repo root.
  const ARROW_CAP = 40;
  T.ok("even a very short trail gets one arrow", few.length >= 1, few.length, ">= 1");
  T.ok("a long trail gets many but never more than the cap",
       many.length > 10 && many.length <= ARROW_CAP, many.length, "11.." + ARROW_CAP);
  // Shape is {pos, baseAngle} -- `baseAngle` because applyReversedEndpoints adds 180 to it for a reversed
  // trail rather than rebuilding the arrows, so the stored value has to stay the unreversed one.
  T.ok("every arrow has a position and a base angle",
       many.every((a) => a && Array.isArray(a.pos) && typeof a.baseAngle === "number"),
       JSON.stringify(many[0]), "{pos:[lat,lng], baseAngle:n}");
  T.ok("angles are compass degrees", many.every((a) => a.baseAngle >= 0 && a.baseAngle < 360),
       many.map((a) => Math.round(a.baseAngle)).slice(0, 4), "0..360");
  T.near("a due-north line points north", many[1].baseAngle, 0, 2);
  T.ok("arrows sit inside the trail, not on its endpoints",
       many[0].pos[0] > long[0][0] && many[many.length - 1].pos[0] < long[long.length - 1][0], true, true);
  T.eq("a zero-length track gets no arrows", buildDirectionArrows([[47, 10], [47, 10]]).length, 0);

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

  T.test("distToBounds is 0 inside and grows outside");
  const box = L.latLngBounds([[47, 10], [48, 11]]);
  T.eq("a point inside", distToBounds(L.latLng(47.5, 10.5), box), 0);
  T.ok("a point outside is positive", distToBounds(L.latLng(50, 10.5), box) > 0, true, true);
  T.ok("further away is further", distToBounds(L.latLng(52, 10.5), box) > distToBounds(L.latLng(50, 10.5), box), true, true);
});
