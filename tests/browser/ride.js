// @suite   ride
// @area    RIDE mode: enter/exit chrome, auto-solo + selection-ring suppression, the focus halo, the
//          look-ahead map offset (portrait AND landscape), and the info panel's own content
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches enterRideMode, exitRideMode, syncRideModeChrome, rideMode, applyRideMapOffset, clearRideMapOffset,
//          rideMapOffsetTop, rideMapOffsetHeight, rideMapOffsetLeft, rideMapOffsetWidth, applyRideFocusHalo,
//          clearRideFocusHalo, rideHaloLayers, rideHaloOriginalConnectorStyles, updateRideInfoPanel,
//          updateSelectionOutlineVisibility, RIDE_OUTER_COLOR, RIDE_OUTER_WEIGHT, RIDE_OUTER_OPACITY,
//          RIDE_MIDDLE_TINT, RIDE_MIDDLE_WEIGHT, RIDE_CONNECTOR_CORE_WEIGHT, RIDE_CONNECTOR_CORE_COLOR,
//          RIDE_GAP_BRIDGE_MIN_M, rideModeBtn, rideInfoPanel, rideInfoSpeed, rideInfoAlt, rideInfoName,
//          rideInfoStats, rideInfoTrail, lastSpeedKmh, lastAltitudeM, startFollowing, stopFollowing,
//          updateUserLocation, //          recoverFromRotationCrash, rotationPadding, syncRideArrows, buildRideArrowLayer, rideArrowLayer,
//          RIDE_ARROW_SPEC, RIDE_ARROW_FILL, RIDE_ARROW_EDGE, ARROW_SPEC, buildChevron,
//          buildDirectionArrowShapes, highlightSelectedTrail, updateStartDotVisibility,
//          eachVectorRenderer, setRendererPadding, BUILDER_PANE, LIFT_BAND_PANE,
//          buildRideArrowShapes, RIDE_ARROW_SPACING_PX, RIDE_ARROW_MAX, rideArrowCumDist, rideArrowCumCache,
//          reversedId, applyReversedEndpoints, reverse-btn, applyEndpointSize, syncEndpointSizes,
//          RIDE_ENDPOINT_RADIUS, RIDE_ENDPOINT_WEIGHT, ENDPOINT_RADIUS, showEndpoints
// @needs   region=bikekingdom, builder=off
//
// Added 2026-08-16, once the RIDE infobox redesign settled (per the user's own phone-tested refinements the
// same day) -- everything here had only been verified live on a phone until now, per docs/backlog.md's own
// "Automated test coverage for RIDE mode is still thin" entry. rideMode/lastSpeedKmh/openTrailId/soloId and
// friends are const/let inside the app's own scope and unreachable here (same reason lineLayers/soloId are
// elsewhere) -- every check below reads the DOM (classes, textContent, computed geometry) or the map's own
// SVG, never an internal variable.
//
// navigator.geolocation.watchPosition is stubbed as a plain no-op subscription (never resolves) for the
// whole suite: enterRideMode() always calls startFollowing() if following isn't already active, and
// startFollowing() sets #liveStatus's own "live" class SYNCHRONOUSLY, before any position ever arrives (see
// its own code) -- so a real fix is never needed just to prove following started. The first version of this
// suite DID resolve a fix (matching tests/browser/bearing.js's own pattern), and that reliably produced a
// real "Maximum call stack size exceeded" in Leaflet's _tryAnimatedZoom: a resolved fix is treated as the
// "first fix" and triggers updateUserLocation's own map.flyTo(..., {duration:0.8}), and something about that
// animation combined with leaflet-rotate recurses. Since the speed/altitude readout is the only thing that
// actually needs a delivered fix, that one test calls updateUserLocation(pos, false) DIRECTLY instead of
// going through the watch at all -- isFirstFix:false skips the flyTo branch entirely while still setting
// lastSpeedKmh/lastAltitudeM and (since rideMode is active) calling updateRideInfoPanel() itself.

TM.add("ride", () => typeof enterRideMode === "function" && typeof applyRideFocusHalo === "function" &&
       TM.ui.cardNamed("trailCards", /./) && TM.ui.cardNamed("tourCards", /Biketicket 2 RIDE schwarz/), async (T) => {
  const overlay = () => TM.map.overlay();
  const strokeCount = (layers, color, width) => layers.filter((p) => {
    if ((p.getAttribute("stroke") || "").toLowerCase() !== color) return false;
    return width === undefined || p.getAttribute("stroke-width") === String(width);
  }).length;
  const outerRingCount = () => strokeCount(overlay(), "#ff6a00", "18");
  const middleTintCount = (color) => strokeCount(overlay(), color, "8");
  const connectorCoreCount = () => strokeCount(overlay(), "#3d3d3d", "5");

  // TM.baseline() (run automatically right before this suite, see _harness.js) calls setHeadingUp(false),
  // which starts its own eased bearing transition (500ms) whenever a PRIOR suite (bearing.js runs earlier in
  // this same bundle) left the map rotated. Calling enterRideMode() -- which calls setHeadingUp(true) right
  // back -- before that transition has actually finished is what produced a real "Maximum call stack size
  // exceeded" in leaflet-rotate's patched _tryAnimatedZoom (it shares machinery with plain zoom animation).
  // Letting baseline's own transition fully settle first avoids stacking two bearing tweens on top of each other.
  // Lets TM.baseline()'s own setHeadingUp(false) transition (started right before this suite's body runs,
  // see above) fully settle before this suite starts calling enterRideMode()/exitRideMode() directly --
  // these bypass toggleRideMode()'s cooldown guard (built for the real button, see enterRideMode's own
  // comment and docs/backlog.md), so nothing here protects a test that fires them back-to-back with no wait.
  await TM.wait(700);

  const realWatch = navigator.geolocation.watchPosition;
  const realClear = navigator.geolocation.clearWatch;
  // Never calls back -- see the header comment for why a real fix is deliberately avoided everywhere except
  // the one test that needs it, and why that test bypasses the watch entirely instead of resolving it.
  navigator.geolocation.watchPosition = () => 1;
  navigator.geolocation.clearWatch = () => {};

  T.test("enterRideMode() adds html.ride-mode, syncs both RIDE buttons, and starts following; exitRideMode() reverses all three");
  enterRideMode();
  await TM.until(() => TM.$("#liveStatus").classList.contains("live"), 3000);
  T.ok("html carries ride-mode", document.documentElement.classList.contains("ride-mode"), document.documentElement.className, "ride-mode");
  const rideBtn = TM.$("#rideModeBtn");
  T.ok("the map-control RIDE button is marked active", rideBtn.classList.contains("active"), rideBtn.className, "active");
  T.eq("...with aria-pressed true", rideBtn.getAttribute("aria-pressed"), "true");
  T.eq("...and a title offering to end it", rideBtn.title, "RIDE-Modus beenden");
  exitRideMode();
  await TM.wait(200);
  T.ok("html loses ride-mode", !document.documentElement.classList.contains("ride-mode"), document.documentElement.className, "no ride-mode");
  T.ok("the button is inactive again", !rideBtn.classList.contains("active"), rideBtn.className, "not active");
  T.eq("...with aria-pressed false", rideBtn.getAttribute("aria-pressed"), "false");
  T.ok("following stopped", !TM.$("#liveStatus").classList.contains("live"), TM.$("#liveStatus").className, "not live");

  T.test("a trail already selected before entering RIDE is auto-soloed, and its yellow selection ring is suppressed for as long as RIDE runs");
  const plainCard = TM.ui.trailCards().find(c => !/🔁/.test(c.textContent));
  plainCard.click();
  await TM.until(() => plainCard.classList.contains("selected"));
  T.eq("selecting it normally shows the yellow ring, nothing dimmed yet", TM.map.selectionOutlines(), 1);
  T.eq("(no solo yet)", TM.map.dimmedTrails(), 0);
  enterRideMode();
  await TM.wait(300);
  T.eq("the ring is gone the moment RIDE starts", TM.map.selectionOutlines(), 0);
  T.ok("the already-open trail got auto-soloed", TM.map.dimmedTrails() > 0, TM.map.dimmedTrails(), "> 0");

  T.test("selecting a DIFFERENT trail while RIDE is already running auto-solos it too, still with no yellow ring");
  const otherCard = TM.ui.trailCards().find(c => c !== plainCard && !/🔁/.test(c.textContent));
  otherCard.click();
  await TM.until(() => otherCard.classList.contains("selected"));
  await TM.wait(300);
  T.eq("still no yellow ring while riding", TM.map.selectionOutlines(), 0);
  T.ok("the newly-focused trail is soloed too", TM.map.dimmedTrails() > 0, TM.map.dimmedTrails(), "> 0");
  exitRideMode();
  await TM.wait(200);
  T.eq("leaving RIDE gives the still-open trail its yellow ring back", TM.map.selectionOutlines(), 1);
  clearSolo();
  closeInfoPanelAndDeselect();

  T.test("the focus halo (orange outer ring + per-difficulty middle tint) appears for a plain trail's own colour, and clears on exit");
  T.eq("no stray halo rings before selecting anything", outerRingCount(), 0);
  otherCard.click();
  await TM.until(() => otherCard.classList.contains("selected"));
  enterRideMode();
  await TM.wait(300);
  T.eq("exactly one outer ring for a non-segmented trail", outerRingCount(), 1);
  const otherDiffBadge = otherCard.querySelector(".badge");
  const otherDiff = ["gruen", "blau", "rot", "schwarz"].find(d => otherDiffBadge.classList.contains(d));
  const tint = { gruen: "#a8e8ba", blau: "#a9cdf5", rot: "#f5aa9d", schwarz: "#c7c7c7" }[otherDiff];
  T.eq("...tinted in that trail's own difficulty colour", middleTintCount(tint), 1);
  exitRideMode();
  await TM.wait(200);
  T.eq("exiting RIDE removes the outer ring", outerRingCount(), 0);
  T.eq("...and the middle tint", middleTintCount(tint), 0);
  clearSolo();
  closeInfoPanelAndDeselect();

  T.test("the focus halo covers every segment of a Tour, bridges its gaps, and recolours connector cores -- clears on exit");
  const tourCard = TM.ui.cardNamed("tourCards", /Biketicket 2 RIDE schwarz/);
  tourCard.click();
  await TM.until(() => tourCard.classList.contains("selected"));
  enterRideMode();
  await TM.wait(400);
  T.ok("more than one outer-ring segment for a 53-stretch Tour", outerRingCount() > 1, outerRingCount(), "> 1");
  T.ok("its schwarz component stretches got the schwarz middle tint", middleTintCount("#c7c7c7") > 0, middleTintCount("#c7c7c7"), "> 0");
  T.ok("its connector stretches got the darker/thicker RIDE core colour", connectorCoreCount() > 0, connectorCoreCount(), "> 0");
  exitRideMode();
  await TM.wait(200);
  T.eq("every halo ring is gone after exiting", outerRingCount(), 0);
  T.eq("connector cores go back to the normal CONNECTOR_COLOR (#5a5a5a), not left recoloured", connectorCoreCount(), 0);
  T.ok("...and are visibly grey again, not stuck at the RIDE core colour", strokeCount(overlay(), "#5a5a5a") > 0, strokeCount(overlay(), "#5a5a5a"), "> 0");
  clearSolo();
  closeInfoPanelAndDeselect();

  T.test("applyRideMapOffset resizes/repositions #map to look ahead in PORTRAIT, and clearRideMapOffset restores it exactly");
  document.documentElement.classList.remove("landscape-compact");
  const mapEl = document.getElementById("map");
  const beforeStyle = { top: mapEl.style.top, height: mapEl.style.height, left: mapEl.style.left, width: mapEl.style.width };
  enterRideMode();
  await TM.wait(300);
  T.ok("#map's top moved off its default (an empty string)", mapEl.style.top !== "", mapEl.style.top, "a non-empty offset");
  T.ok("#map grew taller than the plain 100% it starts at", mapEl.style.height !== "", mapEl.style.height, "a non-empty height");
  T.eq("no horizontal shift in portrait (the info panel docks along the bottom there, not a side)", mapEl.style.left, "");
  exitRideMode();
  await TM.wait(200);
  T.eq("top is cleared back to nothing", mapEl.style.top, beforeStyle.top);
  T.eq("height is cleared back to nothing", mapEl.style.height, beforeStyle.height);

  T.test("in landscape-compact, the offset also shifts #map horizontally to centre the space beside the docked panel");
  document.documentElement.classList.add("landscape-compact");
  enterRideMode();
  await TM.wait(300);
  T.eq("a flat -20px left shift, regardless of the panel's own rendered width", mapEl.style.left, "-20px");
  T.ok("#map widened to cover the panel's width plus the shift", parseFloat(mapEl.style.width) > document.querySelector(".map-wrap").getBoundingClientRect().width, mapEl.style.width, "> map-wrap width");
  exitRideMode();
  await TM.wait(200);
  T.eq("left is cleared back to nothing", mapEl.style.left, "");
  T.eq("width is cleared back to nothing", mapEl.style.width, "");
  document.documentElement.classList.remove("landscape-compact");
  clearSolo();
  closeInfoPanelAndDeselect();

  T.test("updateRideInfoPanel shows an honest '–' for speed/altitude with no fix carrying them, and hides the trail row with nothing focused");
  enterRideMode();
  await TM.wait(300);
  T.eq("speed reads as a dash, not 0", TM.$("#rideInfoSpeed").textContent, "–");
  T.eq("altitude reads as a dash too", TM.$("#rideInfoAlt").textContent, "–");
  T.eq("the trail row is hidden outright with nothing open", TM.$("#rideInfoTrail").style.display, "none");

  T.test("...a delivered fix WITH speed/altitude fills in real numbers, and ONE without them falls back to '–' again");
  // isFirstFix:false bypasses updateUserLocation's own map.flyTo branch entirely (see the header comment) --
  // this only needs the speed/altitude side effect, not a real GPS-driven pan.
  updateUserLocation({ coords: { latitude: 46.79, longitude: 9.53, accuracy: 8, speed: 5, altitude: 1234 } }, false);
  await TM.wait(150);
  T.eq("18 km/h from 5 m/s, rounded", TM.$("#rideInfoSpeed").textContent, "18");
  T.eq("1234 m altitude", TM.$("#rideInfoAlt").textContent, "1234");
  updateUserLocation({ coords: { latitude: 46.79, longitude: 9.53, accuracy: 8 } }, false); // no speed/altitude at all
  await TM.wait(150);
  T.eq("back to a dash once a fix carries neither field, not stuck at the old numbers", TM.$("#rideInfoSpeed").textContent, "–");
  T.eq("...same for altitude", TM.$("#rideInfoAlt").textContent, "–");

  T.test("...and fills in the focused trail's own name/length/Hm the moment one is selected during RIDE");
  const namedCard = TM.ui.trailCards().find(c => !/🔁/.test(c.textContent));
  const cardName = namedCard.querySelector(".trail-name").textContent.replace("👁", "").trim();
  namedCard.click();
  await TM.until(() => namedCard.classList.contains("selected"));
  await TM.wait(300);
  T.eq("the trail row is shown again", TM.$("#rideInfoTrail").style.display, "");
  T.eq("its name matches the card that was clicked", TM.$("#rideInfoName").textContent, cardName);
  const statsText = TM.$("#rideInfoStats").textContent;
  T.ok("its stats mention km/climb/descent", /km/.test(statsText) && /⬆️/.test(statsText) && /⬇️/.test(statsText), statsText, "km + ⬆️ + ⬇️");

  T.test("the focused trail swaps its buried offset chevrons for filled triangles inside the ring");
  // The normal chevron sits 9px to the side and the focus ring is 18px wide, i.e. reaches exactly 9px from
  // the centreline -- so it is not partly covered, it is precisely on the ring's outer edge (user,
  // 2026-08-20: "durch die dickere Linie wird der komplett verdeckt"). RIDE therefore replaces that trail's
  // own arrows with filled white triangles ON the centreline, where the ring's own colour is the contrast.
  // Every other trail keeps its normal chevrons, which is why this counts the SHAPES that disappear rather
  // than just looking for triangles: a version that added triangles without suppressing the buried pair
  // would look identical to this test if it only checked for their presence.
  const realFlyTo2 = L.Map.prototype.flyTo;
  L.Map.prototype.flyTo = function (c, z) { return this.setView(c, z, { animate: false }); };
  // The map is a `const` inside the app's own try{} block and unreachable from here (same reason
  // lineLayers/soloId are), but the app hands it over itself: wrap a prototype method it calls, trigger one
  // call, unwrap. getZoom() rather than something rarer -- updateStartDotVisibility asks for it immediately,
  // so the capture is one synchronous call and the patch is off again before anything else can see it. (This
  // used to hook setMinZoom, which enterRideMode called for the RIDE zoom clamp -- that clamp was removed on
  // 2026-08-20, and the case then silently skipped its whole body because nothing called it any more.)
  const realGetZoom = L.Map.prototype.getZoom;
  let m2 = null;
  L.Map.prototype.getZoom = function () { m2 = this; return realGetZoom.apply(this, arguments); };
  try { updateStartDotVisibility(); } finally { L.Map.prototype.getZoom = realGetZoom; }
  const arrowBox = TM.$("#showDirectionArrowsToggle");
  const arrowsWereOn = arrowBox.checked;
  try {
    exitRideMode();
    await TM.wait(400);
    await TM.ui.setSwitch("showDirectionArrowsToggle", true);
    enterRideMode();
    await TM.wait(500);
    T.ok("captured the map instance", !!m2, !!m2, true);
    if (!m2) {
      T.skip("no map instance to drive the zoom with");
    } else {
      const paths = () => TM.map.overlay();
      // A normal chevron is the only 1.6px unfilled stroke on the map; a triangle is the only #ffffff fill.
      const chevronShapes = () => paths().filter((p) => p.getAttribute("fill") === "none" &&
        p.getAttribute("stroke-width") === "1.6" && (p.getAttribute("d") || "").length > 10)
        .reduce((a, p) => a + ((p.getAttribute("d") || "").match(/M/g) || []).length, 0);
      const triNodes = () => paths().filter((p) => p.getAttribute("fill") === "#ffffff");
      TM.ui.trailCards()[0].click();
      await TM.until(() => TM.$("#infoPanel").classList.contains("visible"), 3000);
      m2.setZoom(16, { animate: false });
      await TM.wait(700);
      // Every count below has to be taken at the SAME view: how many chevrons are painted depends on how many
      // trails are on screen, and clicking a card calls flyToTrailBounds. Comparing counts across two clicks
      // without restoring the view is what made the first version of this case report 190 against 74 -- the
      // app was right and the measurement was not.
      const anchorCentre = m2.getCenter();
      const atAnchor = async () => { m2.setView(anchorCentre, 16, { animate: false }); await TM.wait(600); };
      const withFocus = chevronShapes(), tri = triNodes();
      T.eq("exactly one triangle layer, holding several arrows in one node", tri.length, 1);
      T.ok("it is a filled polygon with a dark edge, not a stroke-only chevron",
           tri[0].getAttribute("stroke") === "#2a2a2a" && (tri[0].getAttribute("d") || "").indexOf("z") > -1,
           tri[0].getAttribute("stroke") + " / " + (tri[0].getAttribute("d") || "").slice(-2), "#2a2a2a / closed");
      // Batching, not quantity: every arrow is a sub-path of the SAME node. How MANY there are is a
      // property of the grid and the current view (see the grid case below) -- since RIDE started deriving
      // them from the visible stretch, one is a perfectly correct answer for a short trail, and this check
      // used to demand "more than one" from the old whole-trail sampling and failed on a correct app.
      const triShapes = ((tri[0].getAttribute("d") || "").match(/M/g) || []).length;
      T.ok("every arrow is a sub-path of that one node", triShapes >= 1 && tri.length === 1,
           triShapes + " arrows in " + tri.length + " node(s)", ">= 1 arrow in exactly 1 node");
      // The regression this case exists for as much as the feature: highlightSelectedTrail brings the
      // selected trail's own line to the front AFTER showTrailInfo has built the halo, so without a
      // counter-call the 3.5px line paints a stripe straight through every 16px triangle. Measured at DOM
      // index 643 against the arrows' 642 before the fix.
      const all = paths();
      const focusLine = all.filter((p) => p.getAttribute("stroke-opacity") === "0.9" && p.getAttribute("fill") === "none");
      T.ok("the triangles are painted ON TOP of the focused trail's own line",
           focusLine.every((p) => all.indexOf(p) < all.indexOf(tri[0])),
           focusLine.map((p) => all.indexOf(p)).join(",") + " vs " + all.indexOf(tri[0]), "line index < arrows");
      // Suppression: dropping the focus must hand that trail's own chevrons back, and taking it again must
      // remove them. Same view throughout, so the counts are comparable.
      clearRideFocusHalo();
      await atAnchor();
      const noFocus = chevronShapes();
      T.eq("no triangles once the focus is gone", triNodes().length, 0);
      T.ok("and the trail's own chevrons came back", noFocus > withFocus, noFocus + " vs " + withFocus,
           "more than while focused");
      TM.ui.trailCards()[0].click();
      await TM.wait(400);
      await atAnchor();
      T.eq("re-focusing suppresses them again", chevronShapes(), withFocus);
      T.eq("and the triangles are back", triNodes().length, 1);
      // Below ARROW_MIN_ZOOM nothing is drawn at all, exactly like the normal arrows.
      m2.setZoom(13, { animate: false });
      await TM.wait(700);
      T.eq("below the arrow zoom threshold there are no triangles", triNodes().length, 0);
      T.eq("and no chevrons either", chevronShapes(), 0);
      await atAnchor();
      T.eq("zooming back in brings the triangles back", triNodes().length, 1);
      // This is the check that pins the suppression term in updateStartDotVisibility's own loop, and it has
      // to come AFTER a zoom: applyRideFocusHalo removes the focused trail's chevrons itself, so up to here
      // everything passes even without that term. It is the zoomend re-evaluation that would put the buried
      // pair back on the map alongside the triangles, and only a count taken after one can see it.
      T.eq("and the zoom did not quietly restore the buried chevrons underneath them",
           chevronShapes(), withFocus);
      exitRideMode();
      await TM.wait(700);
      T.eq("leaving RIDE removes them", triNodes().length, 0);
      T.ok("and the trail has its normal chevrons again", chevronShapes() > 0, chevronShapes(), "> 0");
    }
  } finally {
    L.Map.prototype.flyTo = realFlyTo2;
    if (!arrowsWereOn) await TM.ui.setSwitch("showDirectionArrowsToggle", false);
  }

  T.test("the RIDE arrows sit on a grid anchored to the TRAIL, spaced by zoom, only where the line is visible");
  // The normal arrows sample the whole trail every 300 m and cap at 40 -- one every 2.25 km on a 90 km tour,
  // so a screen showing 300 m of it usually shows none (user, 2026-08-20). RIDE derives them from the visible
  // stretch instead. The property that matters is WHICH thing the zoom controls: the SPACING, never the
  // position. Arrows live on a grid anchored at km 0, so each one keeps its place on the ground and glides
  // past like a signpost; deriving the position from the viewport ("one in the middle of what is visible")
  // gives it no fixed home and makes it JUMP on every pan. That is what the pan check below pins, and it is
  // the only check here that can tell the two designs apart -- counts alone cannot.
  if (!m2) {
    T.skip("no map instance captured earlier in this suite");
  } else {
    const realFlyTo3 = L.Map.prototype.flyTo;
    L.Map.prototype.flyTo = function (c, z) { return this.setView(c, z, { animate: false }); };
    try {
      exitRideMode();
      await TM.wait(400);
      await TM.ui.setSwitch("showDirectionArrowsToggle", true);
      enterRideMode();
      await TM.wait(500);
      TM.ui.trailCards()[0].click();
      await TM.until(() => TM.$("#infoPanel").classList.contains("visible"), 3000);
      await TM.wait(700);
      // One polygon node; each arrow is a sub-path of it, so the count is the number of "M" commands.
      const arrowNode = () => TM.map.overlay().filter((p) => p.getAttribute("fill") === "#ffffff")[0] || null;
      const subPaths = () => {
        const n = arrowNode();
        if (!n) return [];
        return (n.getAttribute("d") || "").split("M").filter(Boolean).map((x) => "M" + x.trim());
      };
      const counts = {};
      for (const z of [16, 17, 18]) { m2.setZoom(z, { animate: false }); await TM.wait(650); counts[z] = subPaths().length; }
      const seen = Object.values(counts);
      T.ok("a handful at every zoom, never the whole trail's worth", seen.every((n) => n <= 12),
           JSON.stringify(counts), "each <= 12");
      T.ok("and at least one zoom actually shows some", seen.some((n) => n > 0), JSON.stringify(counts), "some > 0");

      m2.setZoom(16, { animate: false });
      await TM.wait(700);
      const before = subPaths();
      if (!before.length) {
        T.skip("the focused trail is not under the map centre at this zoom");
      } else {
        // A pan at CONSTANT zoom does not change layer-pixel coordinates -- Leaflet translates the pane
        // instead -- so an arrow that keeps its place on the ground must come back byte-identical. A
        // viewport-derived position would be recomputed and differ.
        const c = m2.getCenter();
        m2.panTo([c.lat + 0.0016, c.lng + 0.0016], { animate: false });
        await TM.wait(800);
        const after = subPaths();
        const survived = before.filter((d) => after.indexOf(d) > -1);
        T.ok("panning leaves the surviving arrows exactly where they were",
             survived.length > 0 || after.length === 0,
             before.length + " before, " + after.length + " after, " + survived.length + " unchanged",
             "at least one carried over unchanged");
        T.ok("nothing was silently re-placed", before.length === 0 || survived.length > 0,
             survived.length, "> 0 of " + before.length);
      }
      exitRideMode();
      await TM.wait(400);
    } finally {
      L.Map.prototype.flyTo = realFlyTo3;
    }
  }

  T.test("a trail reversed BEFORE entering RIDE gets its arrows pointing the other way");
  // 🔄 is unreachable during RIDE (the info panel is hidden), so a reversed view can only come from before --
  // exactly the case the user asked to pin (2026-08-20). buildRideArrowShapes samples the angle from
  // latLngAtDistance at targetKm ± 20 m, and that helper measures from the END when `reversed`, so the sign
  // falls out of the same mechanism the normal arrows use. Worth pinning anyway: RIDE builds its own shapes,
  // so nothing else would notice if the flag stopped being threaded through.
  //
  // Two checks, because neither alone is both exact and honest. The FIRST calls buildRideArrowShapes directly
  // on a synthetic straight line laid across the current view: on a straight line the answer is exact, and it
  // needs no trail to be selected, no zoom to cooperate and no guess about how the real trail bends. Three
  // earlier attempts went through the rendered layer instead and skipped themselves every time -- once for no
  // arrows in view, once because the two runs' grids sit a constant 100px apart (they are anchored to km 0 of
  // the line and of the REVERSED line), and once because the visible stretch bent too much to compare
  // directions at all. The SECOND is the integration half the direct call cannot see: that `reversedId`
  // actually reaches the layer.
  if (!m2) {
    T.skip("no map instance captured earlier in this suite");
  } else {
    const b = m2.getBounds(), c = m2.getCenter();
    const lat0 = c.lat - (c.lat - b.getSouth()) * 0.9, lat1 = c.lat + (b.getNorth() - c.lat) * 0.9;
    const straightLine = [];
    for (let i = 0; i <= 60; i++) straightLine.push([lat0 + (lat1 - lat0) * i / 60, c.lng]);
    const dirsOf = (shapes) => shapes.map((sh) => {
      const bl = sh[0], tip = sh[1], br = sh[2];
      const mid = [(bl[0] + br[0]) / 2, (bl[1] + br[1]) / 2];
      const v = [tip[0] - mid[0], tip[1] - mid[1]], len = Math.hypot(v[0], v[1]) || 1;
      return [v[0] / len, v[1] / len];
    });
    const fwd = dirsOf(buildRideArrowShapes("__reversetest__", straightLine, false, m2.getZoom()));
    const rev = dirsOf(buildRideArrowShapes("__reversetest__", straightLine, true, m2.getZoom()));
    T.ok("the straight probe line produces arrows both ways", fwd.length > 0 && rev.length > 0,
         fwd.length + " forward, " + rev.length + " reversed", "both > 0");
    if (fwd.length && rev.length) {
      const dot = fwd[0][0] * rev[0][0] + fwd[0][1] * rev[0][1];
      T.ok("reversed arrows point the exact opposite way", dot < -0.99, dot.toFixed(4), "< -0.99");
      T.ok("and a forward arrow runs along the line, not across it", Math.abs(fwd[0][1]) < 0.02,
           fwd[0][1].toFixed(4), "|east-west component| < 0.02 on a north-south line");
    }
    // rideArrowCumDist caches by trail id and the probe just put a fake one in it.
    clearRideFocusHalo();
    await TM.wait(300);

    // Integration half: reverse a real trail, then enter RIDE, and check the drawn set CHANGED. Deliberately
    // not a geometric claim -- if `reversedId` never reached syncRideArrows the two runs would be built from
    // identical inputs and come out byte-identical, which is what this can see without assuming anything
    // about the trail's shape.
    const realFlyTo4 = L.Map.prototype.flyTo;
    L.Map.prototype.flyTo = function (cc, z) { return this.setView(cc, z, { animate: false }); };
    let reversedHere = false;
    try {
      exitRideMode();
      await TM.wait(400);
      await TM.ui.setSwitch("showDirectionArrowsToggle", true);
      const card = TM.ui.trailCards()[0];
      const subs = () => {
        const p = TM.map.overlay().filter((x) => x.getAttribute("fill") === "#ffffff")[0];
        return p ? (p.getAttribute("d") || "").split("M").filter(Boolean).map((x) => "M" + x.trim()) : [];
      };
      card.click();
      await TM.until(() => TM.$("#infoPanel").classList.contains("visible"), 3000);
      enterRideMode();
      await TM.wait(500);
      // enterRideMode ends by re-centring on the tracked position (an earlier case delivered one), so the
      // trail has to be brought back under the map AFTER that or nothing is in view at all.
      card.click();
      await TM.wait(700);
      const drawnForward = subs();
      exitRideMode();
      await TM.wait(500);
      const revBtn = TM.$("#ipContent .reverse-btn");
      if (!revBtn || !drawnForward.length) {
        T.skip(!revBtn ? "no reverse button on this panel" : "no arrows drawn for the real trail here");
      } else {
        revBtn.click();
        reversedHere = true;
        await TM.wait(500);
        enterRideMode();
        await TM.wait(500);
        card.click();
        await TM.wait(700);
        const drawnReversed = subs();
        T.ok("the reversed trail still draws arrows", drawnReversed.length > 0, drawnReversed.length, "> 0");
        T.ok("and they are not the same shapes as the forward run",
             drawnReversed.some((d) => drawnForward.indexOf(d) === -1),
             drawnForward.length + " forward vs " + drawnReversed.length + " reversed",
             "at least one differs");
      }
      exitRideMode();
      await TM.wait(400);
    } finally {
      L.Map.prototype.flyTo = realFlyTo4;
      if (reversedHere) {
        const back = TM.$("#ipContent .reverse-btn");
        if (back && back.classList.contains("active")) { back.click(); await TM.wait(400); }
      }
    }
  }

  T.test("Start and Ziel are drawn bigger while riding, and go back to normal afterwards");
  // Radius 5 is right on a normal map and far too small at arm's length on a bright phone, inside an 18px
  // focus ring (user, 2026-08-20: "die sieht man fast nicht"). Read off the marker's own path data rather
  // than app state: a Leaflet circleMarker renders as "M<x>,<y>a<r>,<r> ...", so the first number after the
  // arc command IS the radius the browser is drawing.
  {
    const greenDot = () => {
      const p = TM.map.overlay().filter((x) => x.getAttribute("fill") === "#3fbf5e")[0];
      if (!p) return null;
      const m = /a(\d+(?:\.\d+)?),/.exec(p.getAttribute("d") || "");
      return m ? { r: +m[1], w: p.getAttribute("stroke-width") } : null;
    };
    const realFlyTo5 = L.Map.prototype.flyTo;
    L.Map.prototype.flyTo = function (cc, z) { return this.setView(cc, z, { animate: false }); };
    try {
      exitRideMode();
      await TM.wait(400);
      const card = TM.ui.trailCards()[0];
      card.click();
      await TM.until(() => TM.$("#infoPanel").classList.contains("visible"), 3000);
      await TM.wait(400);
      const normal = greenDot();
      if (!normal) {
        T.skip("no Start marker on screen to measure");
      } else {
        T.eq("a selected trail's Start dot is radius 5 on a normal map", normal.r, 5);
        // RIDE always re-centres on the tracked position -- applyRideMapOffset ends with a panTo, and
        // showTrailInfo goes through updateRideInfoPanel, so even clicking the card again cannot keep a
        // faraway trail in view. Clicking it first and THEN reporting a fix at the map centre puts the
        // rider at the trail, which is both what a real ride looks like and the only way this stays
        // measurable: a clipped marker renders as "M0 0" and has no radius to read at all.
        const at = m2.getCenter();
        updateUserLocation({ coords: { latitude: at.lat, longitude: at.lng, accuracy: 8 } }, false);
        await TM.wait(200);
        enterRideMode();
        await TM.wait(800);
        const riding = greenDot();
        T.ok("and grows while riding", riding && riding.r > normal.r,
             riding ? riding.r : null, "> " + normal.r);
        T.ok("with a heavier outline so it still reads inside the ring",
             riding && parseFloat(riding.w) > parseFloat(normal.w),
             riding ? riding.w : null, "> " + normal.w);
        exitRideMode();
        await TM.wait(600);
        const back = greenDot();
        T.eq("leaving RIDE puts the radius back", back ? back.r : null, normal.r);
        T.eq("and the outline too", back ? back.w : null, normal.w);
      }
    } finally {
      L.Map.prototype.flyTo = realFlyTo5;
    }
  }

  T.test("RIDE does not allocate a full-size renderer for the empty builder pane");
  // Each vector pane costs one SVG sized to the padded bounds, and while rotated that is the same surface
  // whether the pane holds 655 paths or none: measured on a phone in RIDE, 3235x3236 = 39.9 MB for a builder
  // pane with zero paths in it, a third of the app's whole vector footprint. It existed only because
  // setRendererPadding asked about the pane, and map.getRenderer() CREATES a renderer for a pane that has
  // none rather than just looking one up. RIDE switches the builder off outright, so during a ride that
  // surface can never be anything but empty. Read from the DOM: L.Renderer.onAdd appends its container to
  // its pane, so a pane with no child element has no renderer.
  const builderPaneEl = () => document.querySelector(".leaflet-builder-pane");
  exitRideMode();
  await TM.wait(400);
  T.ok("the builder pane element exists (it is created at boot)", !!builderPaneEl(), !!builderPaneEl(), true);
  const childrenBefore = builderPaneEl().childElementCount;
  enterRideMode();
  await TM.wait(600);
  // Only a pane that has NOT been used yet can show this. Once the Tourenbuilder has actually drawn a route
  // glow -- which the lifts and lists suites do earlier in a full bundle -- the renderer legitimately exists
  // and legitimately gets padded, which is the documented behaviour, not a regression. Saying so out loud
  // beats a check that quietly means different things depending on which suites ran first.
  if (childrenBefore > 0) {
    T.skip("an earlier suite already used the Tourenbuilder, so its pane legitimately has a renderer");
  } else {
  // Weak on purpose and known to be so: once an earlier suite in the same bundle has used the builder, the
  // renderer already exists and this can only report "unchanged". The check that actually bites is the
  // padded-panes one below -- see tests/MUTATIONS.md, which records which of the two the mutation kills.
  T.eq("entering RIDE adds no renderer to it", builderPaneEl().childElementCount, childrenBefore);
  T.eq("and nothing in RIDE put paths there either", builderPaneEl().querySelectorAll("path").length, 0);
  // The panes that DO hold something are still padded -- this must not have switched the mechanism off.
  // "Is it padded" has to be asked against the CONTAINER, not against a pixel threshold: at bearing 0 the
  // padded box is the plain rectangle (1078px wide on a phone) and only a rotated one comes out square and
  // wide, so a raw width test reports a correctly padded map as unpadded. Area ratio is bearing-independent.
  const mapBox = document.getElementById("map").getBoundingClientRect();
  const containerArea = mapBox.width * mapBox.height;
  const areaOf = (e) => (+e.getAttribute("width") || 0) * (+e.getAttribute("height") || 0);
  const padded = TM.$$(".leaflet-pane svg").filter((e) => areaOf(e) > containerArea * 2);
  T.ok("the panes that hold something are still padded for rotation", padded.length > 0,
       padded.length, "> 0");
  T.ok("none of the padded panes is the builder pane",
       padded.every((e) => !/builder/.test(e.parentElement.className || "")),
       padded.map((e) => (e.parentElement.className || "").replace("leaflet-pane leaflet-", "")).join(","),
       "no builder-pane");
  }
  exitRideMode();
  await TM.wait(400);

  T.test("teardown: leave RIDE mode, restore the real geolocation API");
  exitRideMode();
  clearSolo();
  closeInfoPanelAndDeselect();
  document.documentElement.classList.remove("ride-mode", "landscape-compact");
  navigator.geolocation.watchPosition = realWatch;
  navigator.geolocation.clearWatch = realClear;
  T.ok("cleanup ran", true, "done", "done");
});
