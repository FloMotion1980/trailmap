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
//          updateUserLocation, RIDE_MIN_ZOOM, preRideMinZoom, preRideMinZoomSaved,
//          recoverFromRotationCrash, rotationPadding, syncRideArrows, buildRideArrowLayer, rideArrowLayer,
//          RIDE_ARROW_SPEC, RIDE_ARROW_FILL, RIDE_ARROW_EDGE, ARROW_SPEC, buildChevron,
//          buildDirectionArrowShapes, highlightSelectedTrail, updateStartDotVisibility
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

  T.test("RIDE clamps how far out the map may zoom, and exiting gives the old limit back");
  // A memory guard, not a UX preference: RIDE's look-ahead makes #map ~30% taller, the container more
  // elongated, and rotationPadding()'s short-axis rule then roughly doubles the painted vector surface
  // (measured on a 375x812 viewport at bearing 45: ~38 MB -> ~89 MB across the three renderer panes).
  // Zooming far out lands a multi-tile-level burst on top of that, and on iOS the WebKit content process
  // gets killed -- a WHITE PAGE, not the fatal panel, so nothing throws and no suite could ever catch it
  // after the fact. What IS checkable is the guard itself. See enterRideMode's own comment.
  //
  // The map instance is a `const` inside the app's own try{} block and unreachable from here (same reason
  // lineLayers/soloId are) -- but the app hands it to us itself: setMinZoom is called on it by
  // enterRideMode, so wrapping the prototype captures the very instance the app uses. Restored immediately;
  // leaving a prototype patched would follow every later suite in the bundle.
  exitRideMode();
  await TM.wait(400);
  const realSetMinZoom = L.Map.prototype.setMinZoom;
  let theMap = null;
  L.Map.prototype.setMinZoom = function (z) { theMap = this; return realSetMinZoom.apply(this, arguments); };
  let beforeMin;
  try {
    enterRideMode();
    await TM.wait(500);
    T.ok("entering RIDE set a minimum zoom on the map", !!theMap, !!theMap, true);
    if (theMap) {
      beforeMin = theMap.getMinZoom();
      T.ok("the limit is a real one, not the world view", beforeMin >= 8, beforeMin, ">= 8");
      // Through the map's own public API, so this covers every route a rider can take: leaflet-rotate's
      // pinch handler runs the same _limitZoom on both its move and end branches (bounceAtZoomLimits is
      // false), and scrollWheelZoom does too.
      theMap.setZoom(2, { animate: false });
      await TM.wait(400);
      T.eq("asking for zoom 2 while riding lands on the limit instead", theMap.getZoom(), beforeMin);
    }
    exitRideMode();
    await TM.wait(500);
    if (theMap) {
      T.ok("leaving RIDE lifts the limit again", theMap.getMinZoom() < beforeMin,
           theMap.getMinZoom(), "< " + beforeMin);
      theMap.setZoom(4, { animate: false });
      await TM.wait(400);
      T.eq("and zoom 4 is reachable once more", theMap.getZoom(), 4);
      theMap.setZoom(13, { animate: false });
      await TM.wait(300);
    }
  } finally {
    L.Map.prototype.setMinZoom = realSetMinZoom;
  }

  T.test("the focused trail swaps its buried offset chevrons for filled triangles inside the ring");
  // The normal chevron sits 9px to the side and the focus ring is 18px wide, i.e. reaches exactly 9px from
  // the centreline -- so it is not partly covered, it is precisely on the ring's outer edge (user,
  // 2026-08-20: "durch die dickere Linie wird der komplett verdeckt"). RIDE therefore replaces that trail's
  // own arrows with filled white triangles ON the centreline, where the ring's own colour is the contrast.
  // Every other trail keeps its normal chevrons, which is why this counts the SHAPES that disappear rather
  // than just looking for triangles: a version that added triangles without suppressing the buried pair
  // would look identical to this test if it only checked for their presence.
  const realFlyTo2 = L.Map.prototype.flyTo;
  const realSetMinZoom2 = L.Map.prototype.setMinZoom;
  let m2 = null;
  L.Map.prototype.flyTo = function (c, z) { return this.setView(c, z, { animate: false }); };
  L.Map.prototype.setMinZoom = function (z) { m2 = this; return realSetMinZoom2.apply(this, arguments); };
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
      const withFocus = chevronShapes(), tri = triNodes();
      T.eq("exactly one triangle layer, holding several arrows in one node", tri.length, 1);
      T.ok("it is a filled polygon with a dark edge, not a stroke-only chevron",
           tri[0].getAttribute("stroke") === "#2a2a2a" && (tri[0].getAttribute("d") || "").indexOf("z") > -1,
           tri[0].getAttribute("stroke") + " / " + (tri[0].getAttribute("d") || "").slice(-2), "#2a2a2a / closed");
      const triShapes = ((tri[0].getAttribute("d") || "").match(/M/g) || []).length;
      T.ok("it carries more than one arrow", triShapes > 1, triShapes, "> 1");
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
      await TM.wait(600);
      const noFocus = chevronShapes();
      T.eq("no triangles once the focus is gone", triNodes().length, 0);
      T.ok("and the trail's own chevrons came back", noFocus > withFocus, noFocus + " vs " + withFocus,
           "more than while focused");
      TM.ui.trailCards()[0].click();
      await TM.wait(800);
      T.eq("re-focusing suppresses them again", chevronShapes(), withFocus);
      T.eq("and the triangles are back", triNodes().length, 1);
      // Below ARROW_MIN_ZOOM nothing is drawn at all, exactly like the normal arrows.
      m2.setZoom(13, { animate: false });
      await TM.wait(700);
      T.eq("below the arrow zoom threshold there are no triangles", triNodes().length, 0);
      T.eq("and no chevrons either", chevronShapes(), 0);
      m2.setZoom(16, { animate: false });
      await TM.wait(700);
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
    L.Map.prototype.setMinZoom = realSetMinZoom2;
    if (!arrowsWereOn) await TM.ui.setSwitch("showDirectionArrowsToggle", false);
  }

  T.test("teardown: leave RIDE mode, restore the real geolocation API");
  exitRideMode();
  clearSolo();
  closeInfoPanelAndDeselect();
  document.documentElement.classList.remove("ride-mode", "landscape-compact");
  navigator.geolocation.watchPosition = realWatch;
  navigator.geolocation.clearWatch = realClear;
  T.ok("cleanup ran", true, "done", "done");
});
