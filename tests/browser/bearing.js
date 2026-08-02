// @suite   bearing
// @area    Map orientation: "Norden oben" vs. "Blickrichtung oben"
// @files   Trailmap App/index.html, Trailmap App/style.css, Trailmap App/leaflet-rotate.js
// @touches setHeadingUp, applyMapBearing, currentMapBearing, headingUp, appliedBearing, targetBearing, updateHeadingCone, refreshHeadingCone, uiOffsetVector, getOffsetCenter, paddedBoundsView, flyToTrailBounds, ROTATING_PANE, rotatePane, bearingBtn, rotateWithView, canRotate, BEARING_MIN_DELTA_DEG, compassStillNeeded, stopFollowing, detachOrientationListener, bearingFrameSafety
// @needs   builder=off
//
// Rotation is the one feature here that is bolted on by a third-party file patching Leaflet's core, and its
// failure modes are all silent-and-visual. Four of them are pinned below, each one a thing that WOULD have
// shipped:
//   * OUR OWN PANES. leaflet-rotate rotates tilePane and overlayPane by re-parenting them into its own
//     "rotatePane" -- but it does not override createPane, so liftBandPane and builderPane would have stayed
//     in the unrotated map pane and stood still while the trails inside them turned away. Case 2.
//   * DOUBLE COUNTING THE HEADING. The cone lives in the marker pane, which is deliberately NOT rotated, so
//     drawing it at the raw compass heading while the map is also turned by that heading makes it spin at
//     twice the rate. Case 4 is the arithmetic, in both modes.
//   * THE PADDING VECTORS. getFlyPadding's numbers are screen-axis pixels but get applied to projected
//     points, which is the same thing only while the map is north-up. Cases 5 and 6 assert the invariant that
//     matters -- the target lands on the SAME SCREEN POINT at every bearing -- rather than the arithmetic.
//   * UPRIGHT TEXT. Labels and builder numbers must not turn; direction arrows must. Cases 3 and 7.
//
// The compass itself cannot be driven from here (tests/README: no DeviceOrientationEvent, no watchPosition),
// so handleOrientation and updateUserLocation are called directly with synthetic readings. Both are plain
// function declarations, so Annex B leaks them to global scope -- that is the whole reason this is testable.
//
// A fifth case exists for something invisible until it regresses: rotating must not REPAINT the vector
// renderers. leaflet-rotate re-cuts every renderer's viewBox on each degree, and that repaint of a
// ~900x1800 px SVG is what made the first version stutter on a phone.
//
// All five mutations above were applied, watched fail, and reverted -- see tests/MUTATIONS.md for the exact
// failures. Two of this file's OWN first-draft bugs are worth knowing before editing it: coneAngle() returned
// 0 instead of null when no cone existed (so "points straight up" passed while nothing was drawn), and the
// cleanup used to remove the location marker from the map, which desynchronises the app's own
// `userLocationMarker` reference and broke the suite's second run in a session.

TM.add("bearing", () => typeof setHeadingUp === "function" && typeof applyMapBearing === "function" &&
                        TM.ui.trailCards().length > 0, async (T) => {

  // The app's `map` is a const inside its top-level try{} and genuinely unreachable from a separately
  // evaluated script. Borrow the instance by capturing `this` from a prototype method that one of the app's
  // globally-reachable functions calls. Used only to read screen positions and to clean up afterwards --
  // every assertion about behaviour goes through the app's own functions or the painted DOM.
  // Any app function that calls a map method will do; updateStartDotVisibility is the smallest one that reads
  // getZoom() and changes nothing. (It used to borrow updateCurrentRegionLabel, which was removed on
  // 2026-08-02 along with the label it wrote.)
  const grabMap = () => {
    let m = null;
    const orig = L.Map.prototype.getZoom;
    L.Map.prototype.getZoom = function () { m = this; return orig.apply(this, arguments); };
    try { updateStartDotVisibility(); } finally { L.Map.prototype.getZoom = orig; }
    return m;
  };
  const map = grabMap();
  const home = map ? { center: map.getCenter(), zoom: map.getZoom() } : null;

  // Rotation angle of an element, in degrees, read off the painted matrix. "none" counts as 0.
  const angleOf = (sel) => {
    const el = TM.$(sel);
    if (!el) return null;
    const m = /matrix\(([^)]+)\)/.exec(getComputedStyle(el).transform);
    if (!m) return 0;
    const n = m[1].split(",").map(Number);
    return Math.round(((Math.atan2(n[1], n[0]) * 180 / Math.PI) + 360) % 360);
  };
  const parentClassOf = (sel) => { const el = TM.$(sel); return el && el.parentElement ? el.parentElement.className : "(missing)"; };
  // Switching the mode EASES the map round over BEARING_TRANSITION_MS, so "off" is not instantly north any
  // more. Every case that switches off and then measures has to wait for the value, not for a guessed delay --
  // a fixed sleep here would either be flaky or hide a transition that got slower.
  const northAgain = async () => {
    setHeadingUp(false);
    await TM.until(() => Math.round(currentMapBearing()) % 360 === 0, 2500);
    await TM.wait(80);
  };
  // Null on purpose when there is no cone at all, and every caller has to check: an earlier version returned
  // 0 in that case, which sailed through "points straight up" while nothing was drawn.
  const coneAngle = () => {
    const wrap = TM.$(".geo-wrap");
    if (!wrap) return null;
    const m = /rotate\((-?[\d.]+)deg\)/.exec(wrap.style.transform || "");
    return m ? ((+m[1] % 360) + 360) % 360 : null;
  };
  // Where does `latlng` end up on screen, measured from the centre of the map container? Any assertion about
  // the padding maths has to be in screen space -- that is the space the numbers are written in.
  const screenOffsetOf = (latlng, zoom, center) => {
    map.setView(center, zoom, { animate: false });
    const p = map.latLngToContainerPoint(latlng), s = map.getSize();
    return { x: Math.round(p.x - s.x / 2), y: Math.round(p.y - s.y / 2) };
  };

  T.test("the rotation plugin is loaded and the map starts north-up");
  T.ok("leaflet-rotate patched L.Map", typeof L.Map.prototype.setBearing === "function", typeof L.Map.prototype.setBearing, "function");
  T.ok("it built its two wrapper panes", !!TM.$(".leaflet-rotate-pane") && !!TM.$(".leaflet-norotate-pane"), true, true);
  T.eq("bearing is 0", currentMapBearing(), 0);
  T.eq("so the rotating pane is not turned", angleOf(".leaflet-rotate-pane"), 0);
  // rotateControl and shiftKeyRotate default to TRUE upstream: loading the file without passing them would
  // have put a rotate widget on the map and bound shift+wheel, on desktop too.
  T.eq("and no rotate widget was added to the map", TM.$$(".leaflet-control-rotate").length, 0);

  T.test("our own panes rotate with the trails, the label panes do not");
  T.eq("tiles rotate", parentClassOf(".leaflet-tile-pane"), "leaflet-pane leaflet-rotate-pane");
  T.eq("trail lines rotate", parentClassOf(".leaflet-overlay-pane"), "leaflet-pane leaflet-rotate-pane");
  T.eq("the lift band rotates with the lines it sits under", parentClassOf(".leaflet-liftBand-pane"), "leaflet-pane leaflet-rotate-pane");
  T.eq("the builder glow rotates with the lines it marks", parentClassOf(".leaflet-builder-pane"), "leaflet-pane leaflet-rotate-pane");
  T.eq("markers stay upright", parentClassOf(".leaflet-marker-pane"), "leaflet-pane leaflet-norotate-pane");
  T.eq("labels stay upright", parentClassOf(".leaflet-tooltip-pane"), "leaflet-pane leaflet-norotate-pane");

  T.test("heading up turns the map and leaves every label upright");
  await TM.ui.setSwitch("showNamesToggle", true);
  await TM.until(() => TM.map.trailLabels().length > 0, 3000);
  setHeadingUp(true);
  applyMapBearing(90, true);
  await TM.wait(200);
  T.eq("the app reports the bearing it was given", currentMapBearing(), 90);
  T.eq("the rotating pane is turned by it", angleOf(".leaflet-rotate-pane"), 90);
  T.eq("the unrotated wrapper is not", angleOf(".leaflet-norotate-pane"), 0);
  const turnedLabels = TM.$$(".leaflet-tooltip").filter((e) => {
    const m = /matrix\(([^)]+)\)/.exec(getComputedStyle(e).transform);
    if (!m) return false;
    const n = m[1].split(",").map(Number);
    return Math.abs(n[1]) > 0.01 || Math.abs(n[0] - 1) > 0.01;      // any rotation or skew at all
  });
  T.ok("there are labels to check", TM.$$(".leaflet-tooltip").length > 0, TM.$$(".leaflet-tooltip").length, "> 0");
  T.eq("not one of them is turned", turnedLabels.length, 0);

  T.test("the cone points up the screen in heading-up, and at the real heading in north-up");
  // A synthetic fix so the location marker (and therefore the cone) exists at all. isFirstFix false and
  // follow mode off, so this moves the map by exactly nothing.
  setHeadingUp(true);
  updateUserLocation({ coords: { latitude: map.getCenter().lat, longitude: map.getCenter().lng, accuracy: 12, heading: null } }, false);
  handleOrientation({ absolute: true, alpha: 270 });     // Android absolute: 360-270 => heading 90, due east
  await TM.until(() => TM.$(".geo-cone"), 2000);
  // Switching the mode EASES the map round over half a second now, so the bearing arrives a few frames after
  // the reading does. Waiting for the value is the point; a fixed sleep would only hide a slow transition.
  // 270, not 90: the map bearing that puts a heading of 90° at the top of the screen is -90 (see targetBearing).
  // This case asserted 90 until 2026-08-04 and passed the whole time the map was turning the wrong way, because
  // the only other thing it checked was the cone -- which subtracts the bearing and so cancelled the error out.
  // The case below ("the direction the rider faces...") is the one that pins the sign to something observable.
  await TM.until(() => Math.round(currentMapBearing()) === 270, 2500);
  const cone = TM.$(".geo-cone");
  T.ok("the synthetic fix produced a location marker carrying a cone", !!cone, !!cone, true);
  if (!cone) {
    T.skip("no cone element, nothing to measure");
  } else {
    T.eq("the map turned to put that heading up", Math.round(currentMapBearing()), 270);
    T.eq("the cone is shown", cone.style.display, "block");
    T.ok("and it points straight up", coneAngle() !== null && Math.abs(coneAngle()) <= 1, coneAngle(), "0 ±1");
    await northAgain();
    T.eq("back to north-up the map is straight", angleOf(".leaflet-rotate-pane"), 0);
    T.ok("and the same cone now points east instead", coneAngle() !== null && Math.abs(coneAngle() - 90) <= 1,
         coneAngle(), "90 ±1");
  }

  T.test("the direction the rider faces is the direction at the top of the screen");
  // The sign of the bearing, stated as the property that actually matters and measured where the user sees it.
  // It was inverted for two days: the map was turned by +heading instead of -heading, so facing east put WEST at
  // the top, while the cone -- which subtracts the same value -- still pointed up and looked perfectly right.
  // That combination is why no existing case caught it and why the user found it outdoors instead.
  // The probe is a point due north of the centre: whatever heading is being followed, north has to appear at
  // minus that heading. latLngToContainerPoint is rotation-aware (the plugin patches the layer->container step),
  // so this is the same mapping that decides where the trails are drawn.
  {
    const northOf = L.latLng(map.getCenter().lat + 0.02, map.getCenter().lng);
    const screenAngleOfNorth = () => {
      const c = map.latLngToContainerPoint(map.getCenter());
      const p = map.latLngToContainerPoint(northOf);
      return ((Math.atan2(p.x - c.x, -(p.y - c.y)) * 180 / Math.PI) + 360) % 360;
    };
    const off = (got, want) => Math.abs(((got - want + 540) % 360) - 180);
    await northAgain();
    T.ok("north-up: north is at the top", off(screenAngleOfNorth(), 0) <= 1,
         Math.round(screenAngleOfNorth()), "0 ±1");
    setHeadingUp(true);
    // Fed repeatedly: handleOrientation runs an EMA with factor 0.2, so one reading only moves a fifth of the way.
    for (let i = 0; i < 60; i++) handleOrientation({ absolute: true, alpha: 270 });   // 360-270 => heading 90, east
    await TM.until(() => off(360 - currentMapBearing(), 90) < 3, 3000);
    T.ok("facing east, the map reports east at the top", off(360 - currentMapBearing(), 90) < 3,
         Math.round(360 - currentMapBearing()), "90 ±3");
    // ...and the map really is turned that way, which is the half the old case could not see.
    T.ok("and north has moved to the left of the screen", off(screenAngleOfNorth(), 270) <= 3,
         Math.round(screenAngleOfNorth()), "270 ±3 (i.e. north on the LEFT, not the right)");
    T.ok("the cone still points up, as it must in this mode", coneAngle() !== null && off(coneAngle(), 0) <= 2,
         coneAngle(), "0 ±2");
    await northAgain();
  }

  T.test("the compass outlives the follow mode, in both map orientations");
  // Reported 2026-08-04: ending the follow killed the rotation and the turning cone in BOTH modes, and took the
  // readout with them. stopFollowing() detached the orientation listener unconditionally, which also reset the
  // smoothed heading -- so "Blickrichtung oben", documented from the start as independent of following, was in
  // fact tied to it. The sensor is released only when neither consumer (this mode, or a position on the map)
  // is left.
  {
    const off = (got, want) => Math.abs(((got - want + 540) % 360) - 180);
    const topOfScreen = () => (360 - currentMapBearing()) % 360;
    // REAL events on the window, not a direct handleOrientation() call. That distinction is the whole test: the
    // bug was that the listener had been removed from the window, and a direct call bypasses exactly that -- the
    // first version of this case called the handler and passed happily against the broken code. Dispatching both
    // event names covers either branch of attachOrientationListener.
    const fire = (heading) => {
      for (const type of ["deviceorientationabsolute", "deviceorientation"]) {
        const ev = new Event(type);
        ev.absolute = true;
        ev.alpha = (360 - heading) % 360;       // the app converts Android's counter-clockwise alpha back
        window.dispatchEvent(ev);
      }
    };
    attachOrientationListener();               // the app's own attach path; no permission gate on this platform
    setHeadingUp(true);
    for (let i = 0; i < 40; i++) fire(90);     // facing east
    await TM.until(() => off(topOfScreen(), 90) < 3, 3000);
    T.ok("with the mode on and no follow, the map already turns", off(topOfScreen(), 90) < 3,
         Math.round(topOfScreen()), "90 ±3");
    TM.$("#liveStatus").classList.add("visible", "live");
    stopFollowing();
    await TM.wait(400);
    T.ok("the compass is still wanted after the follow ends", compassStillNeeded(), compassStillNeeded(), true);
    T.ok("the readout stays on screen for its compass fields",
         TM.$("#liveStatus").classList.contains("visible"), TM.$("#liveStatus").className, "visible");
    T.ok("but its dot stops blinking, because no fixes arrive any more",
         !TM.$("#liveStatus").classList.contains("live"), TM.$("#liveStatus").className, "not live");
    // The half that was actually broken: a real reading arriving AFTER the follow ended still has to turn the map,
    // which it only can if the window listener is still there.
    for (let i = 0; i < 40; i++) fire(270);    // facing west now
    await TM.until(() => off(topOfScreen(), 270) < 3, 3000);
    T.ok("and a reading that arrives afterwards still turns the map", off(topOfScreen(), 270) < 3,
         Math.round(topOfScreen()), "270 ±3");
    await northAgain();
    detachOrientationListener();               // leave the sensor as the baseline expects it
    T.ok("with the mode off and nothing else using it, the sensor is not wanted",
         !compassStillNeeded() || !!TM.$(".geo-wrap"),
         [compassStillNeeded(), !!TM.$(".geo-wrap")], "released, or a position marker still wants it");
  }

  T.test("the followed position sits on the rotation pivot and stays put through a turn");
  // The user reported this twice, from opposite ends: the blue dot ORBITED the middle of the screen as the map
  // turned, and it jumped ~110 px the moment the mode was switched. Both were one cause -- the pans to the
  // position used to offset it by the UI-avoidance padding, while leaflet-rotate pivots around the container
  // centre, so the dot sat on a radius-84 circle around the pivot. Same point, no orbit; this case is the
  // requirement itself, in screen pixels, which is the only space it can be stated in.
  const dotScreen = () => {
    const el = TM.$(".geo-wrap");
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
  };
  const mapCentreScreen = () => {
    const b = TM.$("#map").getBoundingClientRect();
    return { x: Math.round(b.left + b.width / 2), y: Math.round(b.top + b.height / 2) };
  };
  setHeadingUp(false);
  updateUserLocation({ coords: { latitude: home.center.lat, longitude: home.center.lng, accuracy: 12, heading: null } }, false);
  // Centre through the app's OWN path rather than a hand-written panTo: the re-centre button is what a rider
  // taps, and its handler is the code under test. Its CSS makes it click-through only while detached, but the
  // listener does not care.
  TM.$("#recenterBtn").click();
  await TM.settle(dotScreen, 3000);
  const atNorth = dotScreen(), centre = mapCentreScreen();
  T.ok("there is a dot to measure", !!atNorth, atNorth, "a position");
  T.near("it is on the container centre, x", atNorth.x, centre.x, 2);
  T.near("it is on the container centre, y", atNorth.y, centre.y, 2);
  setHeadingUp(true);
  const wander = [];
  for (const deg of [45, 90, 180, 270, 315]) {
    applyMapBearing(deg, true);
    await TM.wait(120);
    const d = dotScreen();
    wander.push(Math.round(Math.hypot(d.x - atNorth.x, d.y - atNorth.y)));
  }
  T.eq("turning the map does not move it off that point", wander.filter((px) => px > 2), []);
  await northAgain();
  const back = dotScreen();
  T.near("and switching back to north-up does not move it either",
         Math.hypot(back.x - atNorth.x, back.y - atNorth.y), 0, 2);

  T.test("centring survives a container whose size Leaflet has not noticed yet");
  // The landscape half of the same report: after a portrait/landscape flip iOS settles the layout later than
  // Leaflet's own debounced resize handler runs, so map.getSize() can still hold the previous orientation.
  // Reproduced exactly here by putting a stale size back: with 375x757 cached against a real 768x320 container,
  // panTo placed the position 58 px BELOW the bottom edge of the screen. The iOS timing is not reproducible;
  // the stale size is, and it is the actual cause.
  const realSize = L.point(TM.$("#map").clientWidth, TM.$("#map").clientHeight);
  map._size = L.point(Math.round(realSize.y / 2), Math.round(realSize.x * 1.5));   // plausibly "the other orientation"
  T.ok("the map is now holding a size that is not its container's",
       map.getSize().y !== realSize.y, JSON.stringify(map.getSize()), "different from " + JSON.stringify(realSize));
  TM.$("#recenterBtn").click();
  // Wait out the settle BURST before measuring, not just for the pixels to stop moving. onViewportSettled is
  // deliberately re-run at 150/400/900/1500 ms after a size change (iOS settles a flip in steps), so a reading
  // taken between two of those checks can catch the view mid-repair — which is exactly what happened when this
  // case was measured 96 px low in a combined run while passing on its own. The property under test is where the
  // position ends up, so the measurement has to be after the last scheduled check.
  await TM.wait(1700);
  await TM.settle(dotScreen, 3000);
  const healed = dotScreen(), c2 = mapCentreScreen();
  T.near("the position still lands on the container centre, x", healed.x, c2.x, 2);
  T.near("the position still lands on the container centre, y", healed.y, c2.y, 2);
  T.eq("and Leaflet is holding the real size again", JSON.stringify(map.getSize()), JSON.stringify(realSize));
  T.ok("the pill can report that it happened", /⇲/.test(TM.$("#liveStatusText").textContent),
       TM.$("#liveStatusText").textContent, "contains ⇲");

  // And the same thing from the user's own three steps, with a REAL container change rather than a fabricated
  // cached size: position centred, compass on, container flipped to landscape shape while Leaflet still holds
  // the portrait one and never got to pan. That is the state that put the position at dy +210, below the bottom
  // edge. Note this asserts the position, not "whatever was in the middle": an earlier version of this case
  // wrote to map._size while the view was correctly laid out, which nothing but a test can produce, and it
  // happily passed the implementation that shipped the bug.
  const el = TM.$("#map");
  const startBox = { w: el.style.width, h: el.style.height };
  setHeadingUp(true);
  applyMapBearing(45, true);
  map.setView(L.latLng(home.center.lat, home.center.lng), 15, { animate: false });
  await TM.wait(250);
  T.near("centred before the flip", Math.hypot(dotScreen().x - mapCentreScreen().x,
         dotScreen().y - mapCentreScreen().y), 0, 2);
  el.style.width = Math.round(realSize.y * 0.9) + "px";      // landscape-shaped, and Leaflet is told nothing
  el.style.height = Math.round(realSize.x * 0.9) + "px";
  const displaced = Math.hypot(dotScreen().x - mapCentreScreen().x, dotScreen().y - mapCentreScreen().y);
  T.ok("the bare flip does displace it, so there is something to fix", displaced > 20, Math.round(displaced), "> 20 px");
  ensureMapSizeCurrent();
  await TM.wait(250);
  T.near("and after the heal the position is back on the centre", Math.hypot(
         dotScreen().x - mapCentreScreen().x, dotScreen().y - mapCentreScreen().y), 0, 3);
  T.eq("with the bearing unchanged", Math.round(currentMapBearing()) % 360, 45);
  el.style.width = startBox.w; el.style.height = startBox.h;
  ensureMapSizeCurrent();
  await TM.wait(200);
  await northAgain();

  T.test("while following, a container that changes in steps leaves the position centred");
  // The landscape flip, as the user actually hit it: the terrain stayed put but the blue dot ended up off
  // centre. iOS settles a flip in SEVERAL steps, so a single check at a guessed moment centres against a
  // container that then changes again. Reproduced here by moving the container twice and letting Leaflet see
  // only the first step -- which is exactly the state that used to leave the dot behind.
  //
  // Follow mode needs a live watchPosition, so it gets a stubbed one. Both stubs and the container's height are
  // put back at the end; leaving either behind would poison every later suite.
  const realWatch = navigator.geolocation.watchPosition;
  const realClear = navigator.geolocation.clearWatch;
  const fixed = { latitude: home.center.lat, longitude: home.center.lng, accuracy: 12, heading: null };
  navigator.geolocation.watchPosition = (ok) => { setTimeout(() => ok({ coords: fixed }), 30); return 1; };
  navigator.geolocation.clearWatch = () => {};
  const mapEl = TM.$("#map");
  const startHeight = mapEl.style.height;
  try {
    startFollowing();
    await TM.until(() => TM.$("#locateBtn").classList.contains("active"), 3000);
    map.setView(L.latLng(fixed.latitude, fixed.longitude), 15, { animate: false });
    await TM.wait(250);
    T.near("following starts with the position on the centre", dotScreen() ? Math.hypot(
      dotScreen().x - mapCentreScreen().x, dotScreen().y - mapCentreScreen().y) : -1, 0, 2);
    // step one, seen by Leaflet; step two, not seen -- then the event a real flip fires
    mapEl.style.height = (mapEl.clientHeight - 60) + "px";
    map.invalidateSize({ debounceMoveend: true });
    mapEl.style.height = (mapEl.clientHeight - 40) + "px";
    window.dispatchEvent(new Event("resize"));
    await TM.wait(2000);                     // the settle burst runs to 1.5 s
    T.eq("Leaflet ends up holding the container's real size",
         JSON.stringify(map.getSize()), JSON.stringify(L.point(mapEl.clientWidth, mapEl.clientHeight)));
    T.near("and the position is still on the centre afterwards", Math.hypot(
      dotScreen().x - mapCentreScreen().x, dotScreen().y - mapCentreScreen().y), 0, 2);
  } finally {
    if (typeof stopFollowing === "function") stopFollowing();
    mapEl.style.height = startHeight;
    window.dispatchEvent(new Event("resize"));
    navigator.geolocation.watchPosition = realWatch;
    navigator.geolocation.clearWatch = realClear;
    await TM.wait(1800);
  }

  T.test("a padded bounds fit puts the target in the uncovered part of the map, at every bearing");
  const c = home.center;
  const bounds = L.latLngBounds([[c.lat - 0.015, c.lng - 0.045], [c.lat + 0.015, c.lng + 0.045]]);
  const fitAt = (deg) => {
    setHeadingUp(deg !== 0);
    applyMapBearing(deg, true);
    const v = paddedBoundsView(bounds);
    return { zoom: v.zoom, off: screenOffsetOf(bounds.getCenter(), v.zoom, v.center) };
  };
  const fitN = fitAt(0), fitE = fitAt(90);
  // The zoom is allowed to differ, and must: a wide, short bounds turned 90° lies across the container's short
  // axis and genuinely needs a step less. Demanding equality was this case's own bug -- it passed only while
  // the container happened to be tall. What must NOT change is the screen position, below.
  T.ok("the zoom differs by at most one step", Math.abs(fitE.zoom - fitN.zoom) <= 1,
       [fitN.zoom, fitE.zoom], "within one step");
  T.near("and so is the screen position (x)", fitE.off.x, fitN.off.x, 2);
  T.near("and so is the screen position (y)", fitE.off.y, fitN.off.y, 2);
  // Leaflet's own padding convention: the target is pushed AWAY from whichever side reserves more room. Per
  // AXIS, not summed -- on desktop the info panel reserves 340px on the right (so the fit moves left) while
  // the header reserves 80px against the bottom bar's 40 (so it moves DOWN). Asserting one combined
  // direction was this test's own first bug, and the app was right.
  const pad = getFlyPadding();
  // Per axis, and with a tolerance on the "no difference" case: when a layout reserves the same room on both
  // sides the offset is zero and lands within a pixel of the centre, so demanding an exact sign of 0 fails on
  // rounding alone. That is how this assertion first broke -- on a rounding artefact, not on the app.
  const axis = (name, off, tl, br) => {
    if (tl === br) T.near("the " + name + " offset is zero when both sides reserve the same", off, 0, 2);
    else T.eq("the " + name + " offset moves away from the side that reserves more",
              Math.sign(off), Math.sign(tl - br));
  };
  axis("x", fitN.off.x, pad.paddingTopLeft.x, pad.paddingBottomRight.x);
  axis("y", fitN.off.y, pad.paddingTopLeft.y, pad.paddingBottomRight.y);

  T.test("direction arrows turn with the map, the name labels do not");
  map.setView(home.center, 14, { animate: false });      // arrows only exist above START_DOT_MIN_ZOOM (13)
  await TM.ui.setSwitch("showDirectionArrowsToggle", true);
  await TM.until(() => TM.$$(".direction-arrow-icon").length > 0, 3000);
  await northAgain();
  const iconNorth = TM.$(".direction-arrow-icon").style.transform;
  const glyphNorth = TM.$(".direction-arrow-icon .direction-arrow").style.transform;
  setHeadingUp(true);
  applyMapBearing(45, true);
  await TM.wait(150);
  const iconEast = TM.$(".direction-arrow-icon").style.transform;
  const glyphEast = TM.$(".direction-arrow-icon .direction-arrow").style.transform;
  T.ok("north-up: the icon carries no rotation at all", !/rotate/.test(iconNorth), iconNorth, "translate only");
  T.ok("rotated: the icon picks up the bearing", /rotate\(([\d.]+)rad\)/.test(iconEast), iconEast, "with a rotate()");
  const rad = /rotate\(([\d.]+)rad\)/.exec(iconEast);
  T.near("and it is exactly the bearing", rad ? +rad[1] * 180 / Math.PI : -1, 45, 1);
  T.eq("while the glyph keeps its own geographic angle", glyphEast, glyphNorth);
  T.eq("and the labels are still upright", angleOf(".leaflet-norotate-pane"), 0);
  await TM.ui.setSwitch("showDirectionArrowsToggle", false);

  T.test("a trail can still be picked by the browser while the map is turned");
  // Hit-testing is what a rotation layer breaks quietest, and firing events at layer OBJECTS would pass for
  // the wrong reason -- that is exactly how the Trailrunde hit-line bug got through once. So: take points
  // that provably lie ON a trail line (SVG user units through the live screen matrix) and ask the browser
  // itself what is painted there. Several points per line, and only points that land inside the map's own
  // rectangle, because a midpoint can fall off-screen or behind the sidebar, and a label or a crossing
  // trail's hit line may legitimately be on top. Names off for the same reason: a label is SUPPOSED to cover
  // its line.
  await TM.ui.setSwitch("showNamesToggle", false);
  // Put a trail on screen through the app's own "fly to this card" path rather than picking a view by hand.
  // Both earlier attempts at this were flaky for the same reason: a hand-picked centre and zoom may leave few
  // or no points of any line inside the container -- and Leaflet empties a fully clipped polyline's `d`, so
  // "no candidates" looks exactly like "no trail lines exist".
  TM.ui.trailCards()[0].click();
  await TM.settle(() => TM.map.overlay().filter((p) => p.getAttribute("stroke-width") === "3.5").length, 4000);
  await TM.wait(300);
  const probeHit = () => {
    const box = TM.$("#map").getBoundingClientRect();
    let probed = 0;
    for (const line of TM.map.overlay().filter((p) => p.getAttribute("stroke-width") === "3.5")) {
      const len = line.getTotalLength();
      if (!len) continue;
      const ctm = line.getScreenCTM();
      if (!ctm) continue;
      for (const frac of [0.5, 0.25, 0.75, 0.1, 0.9]) {
        const pt = line.getPointAtLength(len * frac);
        const cx = Math.round(ctm.a * pt.x + ctm.c * pt.y + ctm.e);
        const cy = Math.round(ctm.b * pt.x + ctm.d * pt.y + ctm.f);
        if (cx < box.left + 2 || cx > box.right - 2 || cy < box.top + 2 || cy > box.bottom - 2) continue;
        probed++;
        const hit = document.elementFromPoint(cx, cy);
        const same = !!hit && hit.getAttribute && hit.getAttribute("d") === line.getAttribute("d");
        if (same) return { ok: true, probed: probed, at: [cx, cy], width: +hit.getAttribute("stroke-width") };
      }
    }
    // Reported separately from a failure: another trail's hit line legitimately covering every sampled point
    // is not a rotation bug, and a case that cannot tell those apart is not evidence.
    return { ok: false, probed: probed };
  };
  await northAgain();
  const hitNorth = probeHit();
  setHeadingUp(true);
  applyMapBearing(90, true);
  await TM.wait(250);
  const hitEast = probeHit();
  if (!hitNorth.probed || !hitEast.probed) {
    T.skip("no point of any trail line fell inside the map container at this view");
  } else {
    T.ok("north-up: a point on a trail line resolves to that trail", hitNorth.ok, hitNorth, "resolved");
    T.ok("turned 90°: it still does", hitEast.ok, hitEast, "resolved");
    T.ok("and what answers is the wide invisible hit line, not the thin visible one",
         hitEast.ok && hitEast.width > 3.5, hitEast.width, "> 3.5");
  }

  T.test("turning the map does not repaint the vector renderers");
  // This is the performance fix, and it is invisible until it regresses. leaflet-rotate makes every renderer
  // re-cut its SVG viewBox on every degree of rotation, which repaints a ~900x1800 px SVG holding a hundred
  // paths -- measured as 61 repaints in a 90-step sweep, and the reason the first version stuttered badly on
  // the user's phone. A sweep must now produce exactly ONE viewBox, and the box must still cover the whole
  // visible area, since "no repaints" is worthless if the lines get clipped instead.
  const viewBoxNow = () => TM.$(".leaflet-overlay-pane svg").getAttribute("viewBox");
  setHeadingUp(true);
  applyMapBearing(0, true);
  // Settle the map first, and for two separate reasons -- both of which re-cut the box for honest reasons that
  // would read here as the suppression having broken. An earlier case resizes the container on purpose, and the
  // one before this flies to a trail, whose 0.6 s animation would still be moving the view mid-sweep.
  map.stop();
  ensureMapSizeCurrent();
  await TM.wait(500);
  const seen = new Set();
  for (let a = 5; a <= 360; a += 5) { applyMapBearing(a, true); seen.add(viewBoxNow()); }
  T.eq("a full turn re-cuts the viewBox exactly once", seen.size, 1);
  const bigEnough = viewBoxNow().split(" ").map(Number);
  T.ok("and that one box is padded out well beyond the viewport",
       bigEnough[2] > TM.$("#map").clientWidth * 1.5, bigEnough[2], "> 1.5x the map width");
  // The renderer's own bounds must still contain all four corners of the container, at every angle -- that is
  // what the skip is allowed to assume, so it is what gets checked.
  const covers = () => {
    const r = map.getRenderer(L.polyline([]));
    const s = map.getSize();
    const need = L.bounds([[0, 0], [s.x, 0], [0, s.y], [s.x, s.y]].map((p) => map.containerPointToLayerPoint(p)));
    return !!r._bounds && r._bounds.contains(need);
  };
  const uncovered = [];
  for (let a = 0; a < 360; a += 15) { applyMapBearing(a, true); if (!covers()) uncovered.push(a); }
  T.eq("no angle leaves the visible area outside the painted box", uncovered, []);
  await northAgain();
  T.ok("back in north-up the renderer is small again",
       +TM.$(".leaflet-overlay-pane svg").getAttribute("viewBox").split(" ")[2] < bigEnough[2],
       TM.$(".leaflet-overlay-pane svg").getAttribute("viewBox"), "narrower than while rotating");

  T.test("switching the mode eases the map round instead of snapping it");
  // The user asked for this after riding with the first version: a mode switch is a jump of up to 180°, and
  // done in one frame it is jarring. Sampled per animation frame, so it fails both if the animation is gone
  // (one angle) and if it never finishes (never reaches the target).
  await northAgain();
  // Fed repeatedly on purpose: handleOrientation runs an EMA with factor 0.2, so ONE reading of 180° only
  // moves the smoothed heading a fifth of the way there. Assuming otherwise was this case's own first bug --
  // it demanded the map arrive at 180° while the pipeline was still saying 108°, and the app was right.
  for (let i = 0; i < 30; i++) handleOrientation({ absolute: true, alpha: 180 });
  await TM.until(() => Math.round(currentMapBearing()) % 360 === 0, 1500);
  // An animation can only be observed if the page is being painted, and this harness sometimes runs in a
  // window that is not (animation frames stop entirely then). Skipping beats failing: a case that cannot see
  // frames has nothing to say about the easing. The safety timer in startBearingTransition is what makes the
  // app itself survive that state -- and the last two checks below still hold either way.
  let frames = 0;
  await new Promise((done) => {
    const t0 = performance.now();
    const tick = () => { frames++; if (performance.now() - t0 < 250) requestAnimationFrame(tick); else done(); };
    requestAnimationFrame(tick);
    setTimeout(done, 1200);
  });
  const canSeeFrames = frames >= 5;
  const seenAngles = new Set();
  let sampling = true;
  const sampler = () => { seenAngles.add(angleOf(".leaflet-rotate-pane")); if (sampling) requestAnimationFrame(sampler); };
  requestAnimationFrame(sampler);
  setHeadingUp(true);
  // targetBearing() is mode-dependent by design -- it answers "north" while the mode is off -- so it can only
  // be read once the mode is on. Reading it a line earlier made this case demand a turn to 0°.
  const aim = Math.round(targetBearing());
  T.ok("the heading pipeline is pointing somewhere worth turning to", Math.abs(aim - 180) <= 2, aim, "180 ±2");
  await TM.until(() => Math.round(currentMapBearing()) === aim, 2500);
  sampling = false;
  const between = [...seenAngles].filter((a) => a !== 0 && a !== 360 && a !== aim);
  if (!canSeeFrames) {
    T.skip("this window is not being painted (" + frames + " animation frames in 250 ms), so the easing itself " +
           "cannot be observed here; the arrival checks below still ran");
  } else {
    T.ok("the map was painted at many angles on the way", seenAngles.size >= 5, seenAngles.size, ">= 5 distinct");
    T.ok("including angles that are neither the start nor the target", between.length >= 3,
         between.length, ">= 3 intermediate angles");
  }
  T.eq("and it arrives exactly where the heading pipeline points", Math.round(currentMapBearing()), aim);
  await northAgain();
  T.eq("switching off eases back to exactly north", angleOf(".leaflet-rotate-pane"), 0);

  T.test("the 🧭 button switches the mode and persists it");
  setHeadingUp(false);
  const btn = TM.$("#bearingBtn");
  T.ok("the button exists on this layout or is display:none on desktop", !!btn, !!btn, true);
  btn.click();
  await TM.wait(120);
  T.ok("one tap arms heading-up", btn.classList.contains("active"), btn.className, "active");
  T.eq("and says so to assistive tech", btn.getAttribute("aria-pressed"), "true");
  T.eq("and it is written to the saved state",
       JSON.parse(localStorage.getItem("trailmap-active-state-v1") || "{}").headingUp, true);
  btn.click();
  await TM.until(() => Math.round(currentMapBearing()) % 360 === 0, 2500);
  // % 360, because the tween can land a hair below zero and round to 360 -- the same angle, and the app is
  // right to keep it in [0,360). Asserting a bare 0 failed on exactly that.
  T.eq("a second tap goes back to north", Math.round(currentMapBearing()) % 360, 0);
  T.eq("the button is no longer marked", btn.classList.contains("active"), false);
  T.eq("and that is persisted too",
       JSON.parse(localStorage.getItem("trailmap-active-state-v1") || "{}").headingUp, false);

  T.test("a fresh boot with heading-up saved comes up armed, but north-up");
  // Nothing attaches the orientation listener until the user taps, so a restored mode has no heading to turn
  // to yet. Coming up rotated to a stale angle would be worse than coming up straight.
  const f = await TM.bootFresh(({ state, put }) => {
    put("state", Object.assign({}, state || {}, { headingUp: true }));
  });
  const fBtn = f.doc.getElementById("bearingBtn");
  const fPane = f.doc.querySelector(".leaflet-rotate-pane");
  T.ok("it booted", f.shows("#trailList .trail-card") > 0, f.shows("#trailList .trail-card"), "> 0");
  T.ok("the button comes up marked", fBtn && fBtn.classList.contains("active"), fBtn && fBtn.className, "active");
  T.ok("but the map is not turned", !fPane || !/matrix\(-?[\d.]+, [^0]/.test(f.win.getComputedStyle(fPane).transform),
       fPane && f.win.getComputedStyle(fPane).transform, "no rotation");
  f.done();

  // ---- put the map back the way we found it -------------------------------------------------------
  setHeadingUp(false);
  // The synthetic fix's marker and accuracy ring are left ON the map on purpose. Removing the layer was
  // tried and is a trap: the app keeps its own `userLocationMarker` reference, so a removed layer makes the
  // next updateUserLocation take the "already exists" branch and never re-add it -- after which the marker
  // has no element, the cone silently cannot be drawn, and this suite fails on its second run in the same
  // session for a reason that has nothing to do with the app. What a real GPS fix leaves behind is exactly
  // this, and no TM.map probe counts it (they all filter by stroke colour and pane). Only the cone is put
  // away, which is the app's own way of saying "no trustworthy heading".
  if (typeof hideHeadingCone === "function") hideHeadingCone();
  if (map) map.setView(home.center, home.zoom, { animate: false });
});
