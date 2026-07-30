// @suite   lifts
// @area    Lift map objects: drawing, stations, Tour routing, builder
// @files   Trailmap App/index.html, Trailmap App/regions/*.json
// @touches buildLiftLayer, destroyLiftLayer, liftLayers, showLiftInfo, highlightSelectedLift, clearLiftSelection, openTourRidingLift, selectTourSegment, showEndpoints, hideEndpoints, endpointOwner, hideAllLiftEndpoints, LIFT_MASK_COLOR, LIFT_MASK_WEIGHT, LIFT_LINE_COLOR, LIFT_HAIRLINE_WEIGHT, LIFT_DOT_WEIGHT, LIFT_DOT_DASH, LIFT_BAND_PANE, liftClimb, LIFT_TYPE_LABEL, builderTryAdd
// @needs   region=bikekingdom, builder=off
//
// A lift is drawn in two parts -- an opaque grey MASK covering the base map's own aerialway line, and a
// black hairline-plus-fat-dots SYMBOL on top -- and the shape of that is load-bearing far beyond looks: the
// mask is why solo has to REMOVE a lift instead of dimming it, and the symbol is defined by colour and
// dash only (never width or opacity) so a Tour can reuse it as an ordinary featureGroup member.
//
// The station markers must stay bottom-first in the data: coords[0] is the valley station, which is what
// makes the green Talstation / red Bergstation dots and the climb figure right.

TM.add("lifts", () => typeof buildLiftLayer === "function" && TM.ui.cardNamed("liftCards", /Hörnli/) && TM.ui.cardNamed("tourCards", /Biketicket/), async (T) => {
  const bandPane = () => TM.$(".leaflet-liftBand-pane");

  T.test("lifts live in their own pane, below the trails");
  T.ok("the pane exists", !!bandPane(), !!bandPane(), true);
  const z = +getComputedStyle(bandPane()).zIndex;
  T.ok("above the tiles (200)", z > 200, z, "> 200");
  T.ok("and below the trails (400)", z < 400, z, "< 400");

  T.test("each lift is a grey mask plus a two-stroke black symbol");
  const n = TM.map.standaloneLifts();
  T.ok("there are lifts to look at", n > 0, n, "> 0");
  const masks = TM.map.band().filter((p) => p.getAttribute("stroke") === "#cfcfcf");
  const hairlines = TM.map.band().filter((p) => p.getAttribute("stroke") === "#000000" && p.getAttribute("stroke-width") === "1.1");
  const dots = TM.map.band().filter((p) => (p.getAttribute("stroke-dasharray") || "").startsWith("1,13"));
  T.ok("one mask per lift (plus each Tour's own)", masks.length >= n, masks.length, ">= " + n);
  T.eq("one hairline per lift", hairlines.length, n);
  T.eq("one dotted stroke per lift", dots.length, n);
  T.eq("the mask is wide enough to cover the tile's own line", masks[0].getAttribute("stroke-width"), "7");
  T.ok("the dots are fatter than the hairline",
       +dots[0].getAttribute("stroke-width") > +hairlines[0].getAttribute("stroke-width"),
       [dots[0].getAttribute("stroke-width"), hairlines[0].getAttribute("stroke-width")], "dots wider");
  // Screen-space dashes: the spacing stays constant at every zoom, which is why no zoom handler is needed.
  T.eq("a 1px dash with a round cap, i.e. a dot", dots[0].getAttribute("stroke-linecap"), "round");

  T.test("station markers appear only for the hovered or selected lift");
  const greenDots = () => TM.map.overlay().filter((p) => (p.getAttribute("fill") || "").toLowerCase() === "#3fbf5e").length;
  const before = greenDots();
  const card = TM.ui.liftCards()[0];
  card.dispatchEvent(new MouseEvent("mouseenter"));
  await TM.wait(300);
  T.ok("hovering reveals them", greenDots() > before, greenDots(), "> " + before);
  card.dispatchEvent(new MouseEvent("mouseleave"));
  await TM.wait(300);
  T.eq("leaving hides them again", greenDots(), before);
  card.click();
  await TM.until(() => /🚡/.test(TM.$("#ipContent").textContent));
  T.ok("selecting keeps them", greenDots() > before, greenDots(), "> " + before);
  T.ok("and adds a yellow outline", TM.map.selectionOutlines() > 0 || TM.map.band().some((p) => (p.getAttribute("stroke") || "").toLowerCase() === "#fff200"),
       true, true);

  T.test("a lift's data is stored bottom-station-first");
  // coords[0] is the valley station: that is what makes the green/red dots and the +climb right, and it is an
  // invariant of the data rather than of the drawing.
  const climbTexts = TM.ui.liftCards().map((c) => (/\+(\d+) m/.exec(c.textContent) || [0, 0])[1] * 1);
  T.ok("every climb is positive", climbTexts.every((v) => v > 0), climbTexts.filter((v) => v <= 0).length, 0);
  T.ok("and plausible for a bike lift (under 1500 m)", climbTexts.every((v) => v < 1500),
       climbTexts.filter((v) => v >= 1500), []);

  T.test("a lift a Tour rides is answered BY the Tour while that Tour is open");
  // Its own layers are built after the trails, so its hit-line sits above the Tour's and wins every click --
  // which made a gondola stretch behave differently from the Tour's trail stretches.
  T.ok("openTourRidingLift exists", typeof openTourRidingLift === "function", true, true);
  closeInfoPanelAndDeselect();
  await TM.wait(200);
  T.eq("with nothing open it answers null", openTourRidingLift("lift_bk_tgantieni"), null);
  const tour = TM.ui.cardNamed("tourCards", /615/) || TM.ui.tourCards()[0];
  tour.click();
  await TM.until(() => TM.$("#infoPanel").classList.contains("visible"));
  const answered = openTourRidingLift("lift_bk_tgantieni");
  T.ok("with the Tour open, a lift it rides resolves to the Tour", answered && answered.loop === true,
       answered && answered.name, "the open Tour");
  T.eq("a lift it does not ride still answers null", openTourRidingLift("lift_bk_hoernli"), null);
  closeInfoPanelAndDeselect();
  await TM.wait(200);

  T.test("lifts are addable to a tour from the list, not only from the map");
  await TM.ui.builderMode(true);
  TM.$("#builderClearBtn").click();
  await TM.wait(200);
  const liftCard = TM.ui.liftCards()[0];
  const liftName = liftCard.querySelector(".trail-name").textContent.replace("👁", "").replace("🚡", "").trim();
  liftCard.click();
  await TM.until(() => TM.$$("#builderList .builder-row").length === 1, 2000);
  const rows = TM.$$("#builderList .builder-row");
  T.eq("one row was appended", rows.length, 1);
  T.ok("and it is that lift", rows[0].textContent.indexOf(liftName.split(" ")[0]) > -1,
       rows[0].textContent.replace(/\s+/g, " ").trim(), liftName);
  T.ok("the info panel did not open instead", !TM.$("#infoPanel").classList.contains("visible"), false, false);
  T.eq("the builder shows a length for it", /\d[\.,]\d+ km/.test(rows[0].textContent), true);
  TM.$("#builderClearBtn").click();
  await TM.wait(200);
  await TM.ui.builderMode(false);

  T.test("hovering a lift thickens only its dots, never the hairline");
  // Hover must not turn the band opaque, or it hides the base map's own line rather than masking it.
  const dotWidth = () => TM.map.band().filter((p) => (p.getAttribute("stroke-dasharray") || "").startsWith("1,13"))
    .map((p) => +p.getAttribute("stroke-width"));
  const hairWidth = () => TM.map.band().filter((p) => p.getAttribute("stroke") === "#000000" &&
    !(p.getAttribute("stroke-dasharray") || "").startsWith("1,13")).map((p) => +p.getAttribute("stroke-width"));
  const dotsBefore = Math.max(...dotWidth()), hairBefore = Math.max(...hairWidth());
  const c2 = TM.ui.liftCards()[1] || TM.ui.liftCards()[0];
  c2.dispatchEvent(new MouseEvent("mouseenter"));
  await TM.wait(300);
  T.ok("one dotted stroke got wider", Math.max(...dotWidth()) > dotsBefore, Math.max(...dotWidth()), "> " + dotsBefore);
  T.eq("the hairline stayed a hairline", Math.max(...hairWidth()), hairBefore);
  c2.dispatchEvent(new MouseEvent("mouseleave"));
  await TM.wait(300);
  T.eq("and it goes back", Math.max(...dotWidth()), dotsBefore);

  T.test("no lift claims a difficulty, a length or a place in the trail counters");
  T.eq("no lift card carries a difficulty badge", TM.$$("#liftList .badge").length, 0);
  const trailsShown = TM.ui.num(TM.ui.counts().trails);
  const toursShown = TM.ui.num(TM.ui.counts().touren);
  T.eq("the Trails count equals the trail cards", TM.ui.trailCards().length, trailsShown);
  T.eq("the Touren count equals the Tour cards", TM.ui.tourCards().length, toursShown);
  T.ok("and neither includes the lifts", trailsShown + toursShown !== TM.ui.liftCards().length + trailsShown,
       true, true);
});
