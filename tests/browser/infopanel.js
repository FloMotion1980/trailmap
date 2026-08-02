// @suite   infopanel
// @area    Info panel: trail, lift, Tour segments, reverse, GPX, elevation chart
// @files   Trailmap App/index.html
// @touches showTrailInfo, showLiftInfo, buildInfoPanelHtml, handleInfoPanelClick, applyReversedEndpoints, reversedId, selectedSegmentId, selectTourSegment, openTourRidingLift, downloadTrailGpx, buildElevationSvg, getEleHoverData, handleEleChartHover, hideEleHover, hideEleHoverChart, eleHoverMapMarker, eleHoverTouched, flyToTrailBounds, liftClimb, LIFT_TYPE_LABEL, mapTouchStart
// @needs   region=bikekingdom, builder=off
//
// The panel is a custom div rather than a Leaflet popup so nothing covers the trail, which means every piece
// of its behaviour is hand-wired and testable: which buttons exist for a trail vs a lift, what reversing
// swaps, what a clicked Tour segment adds, and the data attributes the chart's hover-sync reads back out of
// its own SVG. The reverse case checks the MAP too -- an earlier version only mirrored the numbers and the
// profile while leaving the Start/Ziel markers where they were, which read as "nothing happened".

TM.add("infopanel", () => typeof showTrailInfo === "function" && TM.ui.cardNamed("liftCards", /Hörnli/) && TM.ui.cardNamed("tourCards", /Biketicket/), async (T) => {

  const panel = () => TM.$("#infoPanel");
  const content = () => TM.$("#ipContent");
  const openFirstTrail = async () => {
    const card = TM.ui.trailCards().find((c) => !c.querySelector(".badge-uphill")) || TM.ui.trailCards()[0];
    card.click();
    await TM.until(() => panel().classList.contains("visible"));
    return card;
  };

  T.test("a trail's panel carries its numbers and its four controls");
  const card = await openFirstTrail();
  const meta = card.querySelector(".trail-meta").textContent.replace(/\s+/g, " ");
  T.ok("the heading names the trail", content().querySelector("h3").textContent.trim().length > 2, true, true);
  T.ok("length and elevation are shown", /km/.test(content().textContent) && /m ⬆/.test(content().textContent), true, true);
  T.ok("the card and the panel agree on the length",
       content().textContent.indexOf(meta.split(" km")[0].trim()) > -1, true, true);
  for (const sel of [".locate-btn", ".solo-btn", ".reverse-btn", ".gpx-download-btn"]) {
    T.ok("has " + sel, !!content().querySelector(sel), !!content().querySelector(sel), true);
  }
  T.ok("and an elevation chart", !!content().querySelector("svg.ele-chart, svg"), true, true);

  T.test("the reverse button swaps the numbers, mirrors the profile and moves the markers");
  const readUpDown = () => {
    // The stats line reads "<up> m U+2B06 <down> m U+2B07" -- emoji arrows since 2026-08-02, and the dot and
    // slash that used to separate the two figures are now pure space (an empty .ip-gap span, no character at
    // all), so nothing may be required between them. The trailing U+FE0F is optional in both.
    const m = /(\d+)\s*m\s*⬆️?\s*(\d+)\s*m\s*⬇️?/.exec(content().textContent.replace(/\s+/g, " "));
    return m ? [+m[1], +m[2]] : null;
  };
  const before = readUpDown();
  const chartBefore = content().querySelector("svg").getAttribute("data-profile");
  // Start/Ziel markers: green is the start, red the finish, and reversing has to move them to the other end
  // of the SAME line -- an earlier version only mirrored the numbers and the profile, which read as "nothing
  // happened". Compared as a SET of positions, since the DOM order of the markers is not stable across a
  // redraw and there can be more than one green dot on screen (a hovered lift shows its Talstation too).
  const dotSet = (fill) => TM.map.overlay().filter((p) => (p.getAttribute("fill") || "").toLowerCase() === fill)
    .map((p) => (p.getAttribute("d") || "").slice(0, 24)).sort().join("|");
  const greenPos = () => dotSet("#3fbf5e");
  const startBefore = await TM.settle(greenPos);   // the card click flew the map; wait for it to land
  content().querySelector(".reverse-btn").click();
  await TM.wait(400);
  const after = readUpDown();
  T.ok("up and down are swapped", before && after && before[0] === after[1] && before[1] === after[0],
       [before, after], "swapped");
  T.ok("the button shows as active", content().querySelector(".reverse-btn").classList.contains("active"), true, true);
  // The flag is stamped as "1"/"" rather than "true"/"false"; what matters is that it is set at all, since
  // the hover handler only tests for truthiness when converting a chart position back into a map position.
  T.ok("the chart is redrawn as reversed", !!content().querySelector("svg").getAttribute("data-reversed"),
       content().querySelector("svg").getAttribute("data-reversed"), "a truthy value");
  T.ok("the profile itself is mirrored", content().querySelector("svg").getAttribute("data-profile") !== chartBefore,
       true, true);
  const startReversed = await TM.settle(greenPos);
  T.ok("the green start marker moved to the other end", startReversed !== startBefore, startReversed, "!= " + startBefore);
  content().querySelector(".reverse-btn").click();
  await TM.wait(400);
  T.eq("reversing back restores the numbers", readUpDown(), before);
  T.eq("and puts the marker back", await TM.settle(greenPos), startBefore);

  T.test("opening a different trail resets the reversed view");
  content().querySelector(".reverse-btn").click();
  await TM.wait(350);
  T.ok("reversed", content().querySelector(".reverse-btn").classList.contains("active"), true, true);
  const other = TM.ui.trailCards().find((c) => c !== card);
  other.click();
  await TM.until(() => panel().classList.contains("visible"));
  await TM.wait(250);
  T.ok("the new panel is not reversed", !content().querySelector(".reverse-btn").classList.contains("active"),
       content().querySelector(".reverse-btn").className, "not active");

  T.test("a lift's panel is sparser: no reverse, no GPX, no chart");
  const liftCard = TM.ui.liftCards()[0];
  liftCard.click();
  await TM.until(() => /🚡/.test(content().textContent));
  T.ok("names the lift", /🚡/.test(content().querySelector("h3").textContent), true, true);
  T.ok("has a locate button", !!content().querySelector(".locate-btn"), true, true);
  T.ok("has a solo button", !!content().querySelector(".solo-btn"), true, true);
  T.eq("no reverse button", content().querySelectorAll(".reverse-btn").length, 0);
  T.eq("no GPX button", content().querySelectorAll(".gpx-download-btn").length, 0);
  T.eq("no elevation chart", content().querySelectorAll("svg").length, 0);
  T.ok("it states the climb", /\+\d+ m/.test(content().textContent), true, true);
  T.ok("and the type", /bahn|lift|Seil|Gondel|Sessel|Schlepp|Standseil/i.test(content().textContent), true, true);
  T.ok("the locate button addresses a lift", !!content().querySelector(".locate-btn").dataset.liftId, true, true);

  T.test("clicking a Tour keeps the Tour open and its chart is coloured per segment");
  const tourCard = TM.ui.cardNamed("tourCards", /615/) || TM.ui.tourCards()[0];
  tourCard.click();
  await TM.until(() => panel().classList.contains("visible") && content().querySelectorAll("svg").length > 0);
  const svg = content().querySelector("svg");
  T.ok("the Tour badge is in the heading", /🔁/.test(content().querySelector("h3").textContent),
       content().querySelector("h3").textContent.trim(), "contains 🔁");
  T.ok("more than one polyline, i.e. coloured per stretch", svg.querySelectorAll("polyline").length > 1,
       svg.querySelectorAll("polyline").length, "> 1");
  const strokes = [...svg.querySelectorAll("polyline")].map((p) => p.getAttribute("stroke"));
  T.ok("several different colours are used", new Set(strokes).size > 1, [...new Set(strokes)], "> 1 colour");
  T.ok("the connector grey is among them", strokes.indexOf("#5a5a5a") > -1 || strokes.indexOf("#000000") > -1,
       [...new Set(strokes)], "contains a connector or lift colour");

  T.test("clicking one of the Tour's own segments adds a block without losing the Tour");
  const tourName = content().querySelector("h3").textContent.trim();
  const segHit = TM.map.overlay().filter((p) => (p.getAttribute("stroke-opacity") || "1") === "0");
  if (!segHit.length) {
    T.skip("no invisible segment hit-lines found to click");
  } else {
    // Going through the app's own entry point rather than synthesising a Leaflet mouse event on an SVG path.
    const tid = TM.ui.names("tourCards");
    selectTourSegment({ id: "bk_tour_615_blau", name: tourName, loop: true, diff: "blau", len: 1, up: 1, down: 1 },
                      "lift_bk_tgantieni");
    await TM.wait(400);
    T.ok("the panel still shows the Tour", content().querySelector("h3").textContent.indexOf(tourName.split(" 🔁")[0]) > -1,
         content().querySelector("h3").textContent.trim(), tourName);
    const block = content().querySelector(".ip-segment-info");
    T.ok("a segment block appeared", !!block, !!block, true);
    // Guarded: reading .textContent off a null here aborted the whole suite once, turning one failed check
    // into "infopanel: threw" and losing every case after it.
    T.ok("naming the lift that stretch is ridden by", block && /🚡/.test(block.textContent),
         block ? block.textContent.replace(/\s+/g, " ").trim() : null, "a lift");
    T.ok("and the chart highlights that stretch", !!content().querySelector("svg rect"), true, true);
  }

  T.test("the elevation chart stamps everything its map hover-sync needs");
  TM.ui.trailCards()[0].click();
  await TM.until(() => content().querySelectorAll("svg").length > 0);
  const chart = content().querySelector("svg");
  const need = ["data-trail-id", "data-reversed", "data-profile", "data-dist-max", "data-pad-top",
                "data-pad-bottom", "data-h", "data-ele-min", "data-ele-range"];
  T.eq("no attribute is missing", need.filter((a) => !chart.hasAttribute(a)), []);
  T.ok("the profile parses", Array.isArray(JSON.parse(chart.getAttribute("data-profile"))), true, true);
  T.ok("dist-max is positive", +chart.getAttribute("data-dist-max") > 0, +chart.getAttribute("data-dist-max"), "> 0");
  T.ok("ele-range is positive", +chart.getAttribute("data-ele-range") > 0, +chart.getAttribute("data-ele-range"), "> 0");

  T.test("moving the mouse across the chart puts a dot on the chart and one on the map");
  const rect = chart.getBoundingClientRect();
  const dots = () => TM.map.overlay().filter((p) => (p.getAttribute("fill") || "").toLowerCase() === "#1f5f9e").length;
  const before2 = dots();
  chart.dispatchEvent(new MouseEvent("mousemove", {
    bubbles: true, clientX: Math.round(rect.left + rect.width * 0.5), clientY: Math.round(rect.top + rect.height * 0.5),
  }));
  await TM.wait(300);
  T.ok("a marker appeared on the map", dots() > before2, dots(), "> " + before2);
  // An ELLIPSE, not a circle: the chart's viewBox is stretched non-uniformly (preserveAspectRatio="none"), so a
  // true circle would render as an egg on screen -- fixed 2026-08-04 by making the dot an ellipse whose rx/ry
  // are set per position to cancel the stretch out.
  T.ok("and a dot inside the chart", !!chart.querySelector("ellipse"), !!chart.querySelector("ellipse"), true);
  content().dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));
  await TM.wait(350);
  T.eq("both go away when the mouse leaves the panel", dots(), before2);

  T.test("a tap on the chart LEAVES a dot behind, and a tap elsewhere clears it");
  // On a phone the finger covers the very spot you are trying to read, so the reading is only usable once the
  // finger is gone (user, 2026-08-04). There is no touchend handler for that reason -- which also makes a plain
  // tap set a dot, since touchstart already places one. Driven with real Touch/TouchEvent objects rather than the
  // handler, because "no handler on touchend" is exactly the kind of thing a direct call cannot check.
  const chartDot = () => { const d = chart.querySelector(".ele-hover-dot"); return d && d.style.display !== "none"; };
  const tapChart = (frac) => {
    const r = chart.getBoundingClientRect();
    const t = new Touch({ identifier: 1, target: chart,
                          clientX: Math.round(r.left + r.width * frac), clientY: Math.round(r.top + r.height / 2) });
    chart.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, cancelable: true, touches: [t], targetTouches: [t], changedTouches: [t] }));
    chart.dispatchEvent(new TouchEvent("touchend", { bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: [t] }));
  };
  tapChart(0.4);
  await TM.wait(300);
  const setX = chart.querySelector(".ele-hover-dot").getAttribute("cx");
  T.ok("the tap set a dot on the chart", chartDot(), chartDot(), true);
  T.ok("and one on the map", dots() > before2, dots(), "> " + before2);
  await TM.wait(700);
  T.ok("both are still there after the finger is long gone", chartDot() && dots() > before2,
       [chartDot(), dots()], "[true, > " + before2 + "]");
  tapChart(0.75);
  await TM.wait(300);
  T.ok("a second tap moves it rather than adding another",
       chart.querySelector(".ele-hover-dot").getAttribute("cx") !== setX && dots() === before2 + 1,
       [chart.querySelector(".ele-hover-dot").getAttribute("cx"), setX, dots()], "moved, still one");
  TM.$("#map").dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
  await TM.wait(300);
  T.ok("tapping somewhere else clears both", !chartDot() && dots() === before2,
       [chartDot(), dots()], "[false, " + before2 + "]");

  T.test("tapping a trail opens it even when the platform's own click would not have fired");
  // Reported again by the user AFTER the first fix (a positional mismatch retarget) shipped: "ich schaffe es
  // immer noch genauso, nur auf dem Handy wenn weit rausgezoomt". That is the signature of a SECOND, independent
  // cause with the same symptom -- iOS Safari's documented "first tap on a hover-reactive element only applies
  // :hover, the click needs a second tap" quirk. Our hit-lines qualify (mouseover visibly thickens them), and
  // this has nothing to do with WHERE the finger landed, so a mismatch-only check can never catch it: down can
  // equal up and the native click can still just not happen. This case is exactly that -- identical down and up
  // position, which the first version of this fix would have left completely alone (no mismatch, defer to the
  // platform) and could not even measure, since a scripted touch dispatch never produces the browser's own
  // synthetic click at all. It can only pass now because the app stopped depending on that synthesis entirely:
  // setHover(true) already lives INSIDE each layer's own click handler, so one dispatched click reproduces the
  // whole intended effect regardless of what the platform would or would not have done.
  // The sidebar drawer sits on top of the map on a touch layout, so it must be closed first -- the app is not
  // guaranteed to start in that state here (bootFresh cases elsewhere in a run may leave the toggle either way).
  const aside = TM.$("aside");
  if (aside && aside.classList.contains("open")) { TM.$("#sidebarToggle").click(); await TM.wait(400); }
  {
    // Not "the first wide hit-line in the DOM" and not a path's own bounding-box centre either: a bent/zigzag
    // trail's rectangular bbox centre routinely sits in the empty space BETWEEN two arms of the line, off the
    // path entirely (measured -- a candidate with a perfectly real 242x336 box still resolved to something else
    // at its own centre). The only trustworthy way to find a usable point is the same one the mismatch case
    // below already uses: ask the DOM itself, at a grid of real screen points, which element is actually there.
    const mapBoxForPick = TM.$("#map").getBoundingClientRect();
    let cx = null, cy = null, hitEl = null;
    outerPick:
    for (let y = Math.round(mapBoxForPick.top) + 20; y < mapBoxForPick.bottom - 20; y += 6) {
      for (let x = Math.round(mapBoxForPick.left) + 8; x < mapBoxForPick.right - 8; x += 6) {
        const el = document.elementFromPoint(x, y);
        if (el && el.tagName === "path" && el.classList.contains("leaflet-interactive") &&
            parseFloat(el.getAttribute("stroke-width") || 0) >= 14) {
          cx = x; cy = y; hitEl = el;
          break outerPick;
        }
      }
    }
    if (!hitEl) {
      T.skip("no wide hit-line found by scanning the map to probe");
    } else {
      panel().classList.remove("visible");
      const mapEl = TM.$("#map");
      const t1 = new Touch({ identifier: 30, target: hitEl, clientX: cx, clientY: cy });
      mapEl.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, cancelable: true, touches: [t1], targetTouches: [t1], changedTouches: [t1] }));
      await TM.wait(30);
      const t2 = new Touch({ identifier: 30, target: hitEl, clientX: cx, clientY: cy });   // SAME point, on purpose
      const ev2 = new TouchEvent("touchend", { bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: [t2] });
      mapEl.dispatchEvent(ev2);
      await TM.wait(400);
      T.ok("the platform's own click is suppressed unconditionally", ev2.defaultPrevented, ev2.defaultPrevented, true);
      T.ok("the trail's panel opens anyway", panel().classList.contains("visible"), panel().classList.contains("visible"), true);
    }
  }

  T.test("a tap that settles a few pixels away still opens the trail it started on");
  // The first, narrower cause: browsers hit-test a touch's native click at the TOUCHEND position, not the
  // touchstart one, and a normal tap's finger settles a few pixels in between -- ordinary human behaviour, not a
  // drag. On a densely packed map that drift is often enough to move off the intended trail's hit-line entirely,
  // onto a neighbour's start/end dot or onto empty map: measured on Donnersberg's own boot zoom, a realistic 4px
  // settle mismatched 134 of 400 sampled points. Kept as its own case because it is a DIFFERENT reproduction
  // (deliberately mismatched down/up) than the one above (deliberately identical down/up) -- between them they
  // cover both causes the user's report turned out to have.
  // Rather than trusting one hit-line's own bounding-box centre (a curved/angled path's actual drawn pixels are
  // not reliably under that point, and it is exactly as likely to sit over open sidebar space as over the map),
  // scan the map for a point where a real 4px settle genuinely lands on a DIFFERENT element -- the same method
  // used to first find and quantify this bug.
  const mapBox = TM.$("#map").getBoundingClientRect();
  let found = null;
  outer:
  for (let y = Math.round(mapBox.top) + 20; y < mapBox.bottom - 20; y += 6) {
    for (let x = Math.round(mapBox.left) + 8; x < mapBox.right - 8; x += 6) {
      const down = document.elementFromPoint(x, y);
      if (!down || down.tagName !== "path" || !down.classList.contains("leaflet-interactive") ||
          parseFloat(down.getAttribute("stroke-width") || 0) < 14) continue;
      const up = document.elementFromPoint(x + 4, y + 3);
      if (up !== down) { found = { hit: down, x0: x, y0: y, x1: x + 4, y1: y + 3 }; break outer; }
    }
  }
  if (!found) {
    T.skip("no down/up mismatch found on this map to probe");
  } else {
    const { hit, x0, y0, x1, y1 } = found;
    panel().classList.remove("visible");
    const mapEl = TM.$("#map");
    const t1 = new Touch({ identifier: 21, target: hit, clientX: x0, clientY: y0 });
    mapEl.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, cancelable: true, touches: [t1], targetTouches: [t1], changedTouches: [t1] }));
    await TM.wait(30);
    const upEl = document.elementFromPoint(x1, y1);
    const t2 = new Touch({ identifier: 21, target: upEl, clientX: x1, clientY: y1 });
    const ev2 = new TouchEvent("touchend", { bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: [t2] });
    mapEl.dispatchEvent(ev2);
    await TM.wait(400);
    T.ok("the up-position genuinely differs from the down one (otherwise this proves nothing)",
         upEl !== hit, upEl === hit, "a different element");
    T.ok("the native click was suppressed", ev2.defaultPrevented, ev2.defaultPrevented, true);
    T.ok("the trail's panel opened anyway", panel().classList.contains("visible"), panel().classList.contains("visible"), true);

    T.test("a real drag is left completely alone");
    panel().classList.remove("visible");
    const t3 = new Touch({ identifier: 22, target: hit, clientX: x0, clientY: y0 });
    mapEl.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, cancelable: true, touches: [t3], targetTouches: [t3], changedTouches: [t3] }));
    await TM.wait(30);
    const farEl = document.elementFromPoint(x0, y0 + 60);
    const t4 = new Touch({ identifier: 22, target: farEl, clientX: x0, clientY: y0 + 60 });
    const ev4 = new TouchEvent("touchend", { bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: [t4] });
    mapEl.dispatchEvent(ev4);
    await TM.wait(300);
    T.ok("a 60px movement is not treated as a tap", !ev4.defaultPrevented, ev4.defaultPrevented, false);
    T.ok("and nothing gets opened by it", !panel().classList.contains("visible"), panel().classList.contains("visible"), false);
  }

  T.test("the GPX export offers the app's own geometry");
  // Deliberately not clicking it (that downloads a file); the point is that the exporter finds the trail.
  const names = TM.ui.names("trailCards");
  T.ok("downloadTrailGpx exists and is callable", typeof downloadTrailGpx === "function", true, true);
  T.ok("the button carries the trail id it will export",
       !!content().querySelector(".gpx-download-btn").dataset.id,
       content().querySelector(".gpx-download-btn").dataset.id, "an id");

  T.test("the panel has no ✕ of its own and closing it deselects");
  // The ✕ was removed on 2026-08-02 (user), and with it the one behaviour that distinguished it from a map tap:
  // it closed the panel but LEFT the trail selected. So this case asserts the button is gone AND that the
  // remaining way out still works, because "no ✕" without a working map tap would be a panel you cannot close.
  const openCard = TM.ui.trailCards()[0];
  openCard.click();
  await TM.until(() => panel().classList.contains("visible"));
  T.eq("no ✕ in the panel", panel().querySelectorAll("#ipClose, .ip-close").length, 0);
  T.ok("and the heading keeps no room for one", parseFloat(getComputedStyle(content().querySelector("h3")).paddingRight) < 4,
       Math.round(parseFloat(getComputedStyle(content().querySelector("h3")).paddingRight)), "< 4px");
  closeInfoPanelAndDeselect();   // what a tap on empty map space calls
  await TM.wait(300);
  T.ok("panel closed", !panel().classList.contains("visible"), false, false);
  T.ok("the card is deselected too", !openCard.classList.contains("selected"), openCard.className, "not selected");
  T.eq("and the outline left the map", TM.map.selectionOutlines(), 0);

  T.test("all four actions are one unbreakable row of equal-sized buttons");
  // The layout the user asked for: the group sits behind the name when the name's last line leaves room and drops
  // WHOLE onto its own line under it when it does not. Both halves are asserted below by walking every trail in
  // the list -- so a name long enough to force the second line has to exist in the region for this to prove
  // much, and bikecircus has several ("Connection ..." ones).
  let behind = 0, ownLine = 0, worstOverflow = -1e9, sizes = new Set();
  for (const c of TM.ui.trailCards().slice(0, 14)) {
    c.click();
    await TM.until(() => panel().classList.contains("visible") && content().querySelector(".ip-btns"));
    const h3 = content().querySelector("h3"), grp = h3.querySelector(".ip-btns");
    const g = grp.getBoundingClientRect(), p = panel().getBoundingClientRect();
    const first = grp.firstElementChild.getBoundingClientRect();
    const last = grp.lastElementChild.getBoundingClientRect();
    // One row: every button shares the group's own top, and the group's width is the sum of its parts.
    if (Math.abs(first.top - last.top) > 1) worstOverflow = 1e9;
    worstOverflow = Math.max(worstOverflow, g.right - p.right);
    [...grp.children].forEach((b) => sizes.add(Math.round(b.getBoundingClientRect().height)));
    const nameNode = h3.firstChild;
    const r = document.createRange(); r.setStart(nameNode, 0); r.setEnd(nameNode, nameNode.length);
    const lines = [...r.getClientRects()];
    if (lines.length && Math.abs(g.top - lines[lines.length - 1].top) < 12) behind++; else ownLine++;
  }
  T.ok("every button is the same height", sizes.size === 1, [...sizes], "one height");
  T.ok("the group never leaves the panel", worstOverflow <= 0, Math.round(worstOverflow), "<= 0");
  T.ok("it sits behind the name where the name leaves room", behind > 0, behind, "> 0");
  T.ok("and drops to its own line where it does not", ownLine > 0, ownLine, "> 0");

  T.test("the panel's width does not depend on which trail is open");
  // It was sized by its content (width:max-content), so the same panel came out 320, 338 or 360px wide depending
  // on the name -- and since the touch layout centres it, both its edges moved on every tap (user, 2026-08-02).
  const widths = new Set();
  for (const c of TM.ui.trailCards().slice(0, 8)) {
    c.click();
    await TM.until(() => panel().classList.contains("visible"));
    widths.add(Math.round(panel().getBoundingClientRect().width));
  }
  T.ok("one width across eight trails", widths.size === 1, [...widths], "one width");
  // And the rule itself, because the measurement above can only see the layout this run happens to be in: the
  // variable width lived in the touch/coarse-pointer media block, which a desktop-sized run never applies.
  let touchWidth = null;
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
    for (const rule of rules || []) {
      if (!(rule.media && /coarse|max-width/.test(rule.conditionText || ""))) continue;
      for (const inner of rule.cssRules || []) {
        if (inner.selectorText === "#infoPanel" && inner.style.width) touchWidth = inner.style.width;
      }
    }
  }
  T.ok("and the touch layout's own rule is a fixed width, not max-content",
       touchWidth !== null && !/content/.test(touchWidth), touchWidth, "a length");
});
