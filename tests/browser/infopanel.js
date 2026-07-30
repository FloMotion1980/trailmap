// @suite   infopanel
// @area    Info panel: trail, lift, Tour segments, reverse, GPX, elevation chart
// @files   Trailmap App/index.html
// @touches showTrailInfo, showLiftInfo, buildInfoPanelHtml, handleInfoPanelClick, applyReversedEndpoints, reversedId, selectedSegmentId, selectTourSegment, openTourRidingLift, downloadTrailGpx, buildElevationSvg, getEleHoverData, handleEleChartHover, hideEleHover, flyToTrailBounds, liftClimb, LIFT_TYPE_LABEL
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
  T.ok("length and elevation are shown", /km/.test(content().textContent) && /m ↑/.test(content().textContent), true, true);
  T.ok("the card and the panel agree on the length",
       content().textContent.indexOf(meta.split(" km")[0].trim()) > -1, true, true);
  for (const sel of [".locate-btn", ".solo-btn", ".reverse-btn", ".gpx-download-btn"]) {
    T.ok("has " + sel, !!content().querySelector(sel), !!content().querySelector(sel), true);
  }
  T.ok("and an elevation chart", !!content().querySelector("svg.ele-chart, svg"), true, true);

  T.test("the reverse button swaps the numbers, mirrors the profile and moves the markers");
  const readUpDown = () => {
    const m = /(\d+)\s*m\s*↑\s*\/\s*(\d+)\s*m\s*↓/.exec(content().textContent.replace(/\s+/g, " "));
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
  T.ok("and a dot inside the chart", !!chart.querySelector("circle"), !!chart.querySelector("circle"), true);
  content().dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));
  await TM.wait(350);
  T.eq("both go away when the mouse leaves the panel", dots(), before2);

  T.test("the GPX export offers the app's own geometry");
  // Deliberately not clicking it (that downloads a file); the point is that the exporter finds the trail.
  const names = TM.ui.names("trailCards");
  T.ok("downloadTrailGpx exists and is callable", typeof downloadTrailGpx === "function", true, true);
  T.ok("the button carries the trail id it will export",
       !!content().querySelector(".gpx-download-btn").dataset.id,
       content().querySelector(".gpx-download-btn").dataset.id, "an id");

  T.test("the × keeps the map selection but closes the panel");
  const openCard = TM.ui.trailCards()[0];
  openCard.click();
  await TM.until(() => panel().classList.contains("visible"));
  TM.$("#ipClose").click();
  await TM.wait(300);
  T.ok("panel closed", !panel().classList.contains("visible"), false, false);
  // Deliberate: a trail keeps its outline, its Start/Ziel dots and its selected card after the ×.
  T.ok("the card is still selected", openCard.classList.contains("selected"), openCard.className, "selected");
  T.ok("and the outline is still on the map", TM.map.selectionOutlines() > 0, TM.map.selectionOutlines(), "> 0");
  closeInfoPanelAndDeselect();
  await TM.wait(200);
  T.eq("the full reset does clear it", TM.map.selectionOutlines(), 0);
});
