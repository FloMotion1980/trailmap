// @suite   bearing
// @area    Map orientation: "Norden oben" vs. "Blickrichtung oben"
// @files   Trailmap App/index.html, Trailmap App/style.css, Trailmap App/leaflet-rotate.js
// @touches setHeadingUp, applyMapBearing, currentMapBearing, headingUp, appliedBearing, updateHeadingCone, refreshHeadingCone, uiOffsetVector, getOffsetCenter, paddedBoundsView, flyToTrailBounds, ROTATING_PANE, rotatePane, bearingBtn, rotateWithView, canRotate, BEARING_MIN_DELTA_DEG
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
  const grabMap = () => {
    let m = null;
    const orig = L.Map.prototype.getCenter;
    L.Map.prototype.getCenter = function () { m = this; return orig.apply(this, arguments); };
    try { updateCurrentRegionLabel(); } finally { L.Map.prototype.getCenter = orig; }
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
  const cone = TM.$(".geo-cone");
  T.ok("the synthetic fix produced a location marker carrying a cone", !!cone, !!cone, true);
  if (!cone) {
    T.skip("no cone element, nothing to measure");
  } else {
    T.eq("the map followed the heading", currentMapBearing(), 90);
    T.eq("the cone is shown", cone.style.display, "block");
    T.ok("and it points straight up", coneAngle() !== null && Math.abs(coneAngle()) <= 1, coneAngle(), "0 ±1");
    setHeadingUp(false);
    await TM.wait(120);
    T.eq("back to north-up the map is straight", angleOf(".leaflet-rotate-pane"), 0);
    T.ok("and the same cone now points east instead", coneAngle() !== null && Math.abs(coneAngle() - 90) <= 1,
         coneAngle(), "90 ±1");
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
  setHeadingUp(false);
  await TM.wait(150);
  const back = dotScreen();
  T.near("and switching back to north-up does not move it either",
         Math.hypot(back.x - atNorth.x, back.y - atNorth.y), 0, 2);

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
  T.eq("the zoom is bearing-independent", fitE.zoom, fitN.zoom);
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
  setHeadingUp(false);
  await TM.wait(150);
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
  // Pin the view first. Inheriting whatever the previous case left is what made this flaky: at zoom 14 only a
  // handful of points on any line are inside the container at all, and a probe with a sample of four either
  // passes or reports a failure that has nothing to do with rotation.
  map.setView(home.center, 12, { animate: false });
  await TM.wait(400);
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
  setHeadingUp(false);
  await TM.wait(200);
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
  await TM.wait(200);
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
  setHeadingUp(false);
  await TM.wait(150);
  T.ok("back in north-up the renderer is small again",
       +TM.$(".leaflet-overlay-pane svg").getAttribute("viewBox").split(" ")[2] < bigEnough[2],
       TM.$(".leaflet-overlay-pane svg").getAttribute("viewBox"), "narrower than while rotating");

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
  await TM.wait(120);
  T.eq("a second tap goes back to north", currentMapBearing(), 0);
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
