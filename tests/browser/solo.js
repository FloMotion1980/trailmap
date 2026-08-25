// @suite   solo
// @area    Solo mode for trails, Tours and lifts
// @files   Trailmap App/index.html
// @touches applySolo, clearSolo, selectTourSegment, selectedSegmentIdx, applyLiftVisibility, applyLiftSegmentOpacity, liftHiddenBySolo, baselineLineOpacity, resetAllHoverStyles, applyLineWeight, syncSelectedCardSoloBtn, SOLO_DIM_OPACITY, liftSegments, wireCardHover
// @needs   region=bikekingdom, builder=off
//
// Solo has produced more repeat reports than anything else in the app, and each time for a DIFFERENT reason,
// so the cases here are deliberately split by cause:
//   * trails dim to 15% -- but merely MOVING THE MOUSE over another trail used to cancel that, because the
//     hover-off path reset opacity to a hardcoded 0.85 instead of asking baselineLineOpacity().
//   * lifts cannot be dimmed at all: the grey band is a MASK over the base map's own aerialway line, so
//     fading it just uncovers the tile's line at full strength. They have to be removed.
//   * a Tour's own lift stretches are exempt from the Tour's group styling, so they were the one thing solo
//     never reached and stayed fully opaque after every standalone lift had gone.
// All three are the same user sentence ("Solo blendet Lifte nicht aus" / "das Dimmen ist weg") and all three
// have to fail independently, or one can mask another.
//
// A card's hover is wired to pointerenter/pointerleave, not mouseenter/mouseleave (2026-08-20): a TAP
// synthesises a mouseenter too, which left a trail selected from the list wearing the bold hover width on
// top of its yellow outline on a phone. The handler reads `pointerType` off the event, so a dispatched
// MouseEvent now reaches nothing at all -- which is why the card hovers below are PointerEvents.

TM.add("solo", () => typeof applySolo === "function" && TM.map.tourLiftStretches() > 0 && TM.ui.cardNamed("liftCards", /Hörnli/) && TM.ui.cardNamed("tourCards", /Biketicket/), async (T) => {
  const LIFTS_ON_MAP = TM.map.standaloneLifts();
  const TOUR_STRETCHES = TM.map.tourLiftStretches();
  const firstTrail = () => TM.ui.trailCards()[0];
  const trailIdOf = (card) => {
    // The card carries no id; find it through the layer registry the app exposes by function only.
    const name = card.querySelector(".trail-name").textContent.replace(/[👁👑]/g, "").trim();
    return name;
  };

  T.test("preconditions: there is something to hide");
  T.ok("standalone lifts on the map", LIFTS_ON_MAP > 0, LIFTS_ON_MAP, "> 0");
  T.ok("Tour lift stretches on the map", TOUR_STRETCHES > 0, TOUR_STRETCHES, "> 0");
  T.eq("nothing dimmed to start with", TM.map.dimmedTrails(), 0);

  T.test("solo on a trail dims the other trails to 15% and removes every lift symbol");
  const card = firstTrail();
  card.click();
  await TM.until(() => card.classList.contains("selected"));
  card.querySelector(".card-solo-btn").click();
  await TM.wait(400);
  T.ok("other trails are dimmed, not removed", TM.map.dimmedTrails() > 0, TM.map.dimmedTrails(), "> 0");
  T.eq("(a) no standalone lift is left", TM.map.standaloneLifts(), 0);
  T.eq("(b) no Tour lift stretch is left", TM.map.tourLiftStretches(), 0);
  T.eq("no grey mask is left either", TM.map.liftMasks(), 0);
  T.eq("no lift card vanished from the list", TM.ui.liftCards().length, TM.ui.num(TM.ui.counts().lifts));

  T.test("hovering another trail does NOT cancel the dimming");
  // No click needed to trigger the old bug: every mouseover runs resetAllHoverStyles over every other layer.
  const dimmedBefore = TM.map.dimmedTrails();
  const other = TM.ui.trailCards()[3] || TM.ui.trailCards()[1];
  other.dispatchEvent(new PointerEvent("pointerenter", { pointerType: "mouse" }));
  await TM.wait(250);
  T.ok("still dimmed while hovering", TM.map.dimmedTrails() >= dimmedBefore - 1, TM.map.dimmedTrails(), "~" + dimmedBefore);
  other.dispatchEvent(new PointerEvent("pointerleave", { pointerType: "mouse" }));
  await TM.wait(250);
  T.eq("and after the mouse leaves again", TM.map.dimmedTrails(), dimmedBefore);

  T.test("turning solo off restores everything exactly");
  card.querySelector(".card-solo-btn").click();
  await TM.wait(400);
  T.eq("nothing dimmed", TM.map.dimmedTrails(), 0);
  T.eq("lifts back", TM.map.standaloneLifts(), LIFTS_ON_MAP);
  T.eq("Tour stretches back", TM.map.tourLiftStretches(), TOUR_STRETCHES);
  T.eq("masks back", TM.map.liftMasks(), LIFTS_ON_MAP + TOUR_STRETCHES);
  closeInfoPanelAndDeselect();
  await TM.wait(200);

  T.test("solo on a Tour keeps exactly the lifts it rides");
  const tourCard = TM.ui.cardNamed("tourCards", /615/) || TM.ui.tourCards()[0];
  tourCard.click();
  await TM.until(() => TM.$("#infoPanel").classList.contains("visible"));
  // A Tour auto-solos when opened, so the button should already be active.
  const soloBtn = () => TM.$("#ipContent .solo-btn");
  T.ok("opening a Tour solos it", soloBtn().classList.contains("active"), soloBtn().className, "active");
  const keptLifts = TM.map.standaloneLifts(), keptStretches = TM.map.tourLiftStretches();
  T.ok("some lifts stay", keptLifts > 0, keptLifts, "> 0");
  T.ok("but not all of them", keptLifts < LIFTS_ON_MAP, keptLifts, "< " + LIFTS_ON_MAP);
  T.eq("its own lift stretches are exactly as many as the lifts it rides", keptStretches, keptLifts);
  T.ok("other Tours' stretches are gone", keptStretches < TOUR_STRETCHES, keptStretches, "< " + TOUR_STRETCHES);

  T.test("solo off from the panel restores it");
  soloBtn().click();
  await TM.wait(400);
  T.eq("lifts back", TM.map.standaloneLifts(), LIFTS_ON_MAP);
  T.eq("stretches back", TM.map.tourLiftStretches(), TOUR_STRETCHES);
  T.ok("the button is no longer active", !soloBtn().classList.contains("active"), soloBtn().className, "not active");
  closeInfoPanelAndDeselect();
  await TM.wait(250);

  T.test("a lift can be the solo target itself");
  const liftCard = TM.ui.cardNamed("liftCards", /Hörnli/) || TM.ui.liftCards()[0];
  liftCard.click();
  await TM.until(() => TM.$("#infoPanel").classList.contains("visible"));
  T.ok("the lift panel has a solo button", !!TM.$("#ipContent .solo-btn"), true, true);
  T.ok("it is addressed by data-lift-id", !!TM.$("#ipContent .solo-btn").dataset.liftId,
       TM.$("#ipContent .solo-btn").dataset.liftId, "a lift id");
  TM.$("#ipContent .solo-btn").click();
  await TM.wait(400);
  T.eq("exactly one standalone lift is left", TM.map.standaloneLifts(), 1);
  T.eq("no Tour lift stretch survives", TM.map.tourLiftStretches(), 0);
  T.ok("every trail is dimmed", TM.map.dimmedTrails() > 0, TM.map.dimmedTrails(), "> 0");

  T.test("the panel button and the card button stay in sync");
  T.ok("panel button active", TM.$("#ipContent .solo-btn").classList.contains("active"), true, true);
  const liftCardNow = TM.ui.cardNamed("liftCards", /Hörnli/) || TM.ui.liftCards()[0];
  T.ok("card button active too", liftCardNow.querySelector(".card-solo-btn").classList.contains("active"),
       liftCardNow.querySelector(".card-solo-btn").className, "active");
  // Toggling from the CARD has to update the panel as well, since neither goes through a full render.
  liftCardNow.querySelector(".card-solo-btn").click();
  await TM.wait(400);
  T.ok("card off turns the panel button off", !TM.$("#ipContent .solo-btn").classList.contains("active"),
       TM.$("#ipContent .solo-btn").className, "not active");
  T.eq("and every lift is back", TM.map.standaloneLifts(), LIFTS_ON_MAP);

  T.test("opening a different object drops the previous solo, opening the same one keeps it");
  liftCardNow.click();
  await TM.wait(300);
  TM.$("#ipContent .solo-btn").click();
  await TM.wait(350);
  T.eq("soloed again", TM.map.standaloneLifts(), 1);
  // Its own panel button re-opens the same panel; that must not clear the solo it just applied.
  TM.$("#ipContent .solo-btn").click();
  await TM.wait(300);
  TM.$("#ipContent .solo-btn").click();
  await TM.wait(350);
  T.eq("still soloed after a re-render of its own panel", TM.map.standaloneLifts(), 1);
  TM.ui.trailCards()[0].click();
  await TM.wait(400);
  T.eq("opening a trail released it", TM.map.standaloneLifts(), LIFTS_ON_MAP);
  T.eq("nothing dimmed", TM.map.dimmedTrails(), 0);

  T.test("clicking empty map space is a full reset");
  const c2 = TM.ui.trailCards()[0];
  c2.click();
  await TM.until(() => c2.classList.contains("selected"));
  c2.querySelector(".card-solo-btn").click();
  await TM.wait(350);
  closeInfoPanelAndDeselect();   // what map.on("click") calls
  await TM.wait(350);
  T.ok("panel closed", !TM.$("#infoPanel").classList.contains("visible"), false, false);
  T.eq("solo released", TM.map.dimmedTrails(), 0);
  T.eq("selection cleared", TM.$$(".trail-card.selected").length, 0);
  T.eq("lifts back", TM.map.standaloneLifts(), LIFTS_ON_MAP);
  T.eq("Tour stretches back", TM.map.tourLiftStretches(), TOUR_STRETCHES);
  T.test("a Tour's segment hit areas sit in their own pane, above every trail's hit area");
  // The bug this closes: lineTrails order is the map's z-order, so a trail built after a Tour lays its own
  // invisible 22px hitLine over that Tour's per-segment areas and swallows their clicks -- the stretch then
  // opens the plain trail's panel instead of keeping the Tour selected. Two rounds of re-raising
  // (buildTrailLayer at build time, applySolo on selection) each held only at the moment they ran, which the
  // user diagnosed exactly: clicks worked only AFTER a Tour had been selected once, and "wenn man in der App
  // Filter aktiviert und wieder deaktiviert, kann man in so einen Zustand ja immer kommen" -- render() adds
  // and removes layers on every filter change. TOUR_SEG_HIT_PANE settles it structurally, so this asserts the
  // structure rather than an order that would only be true right now.
  const segPane = TM.$(".leaflet-tourSegHit-pane");
  T.ok("the pane exists", !!segPane, !!segPane, true);
  T.ok("and sits above the overlay pane", parseInt(getComputedStyle(segPane).zIndex, 10) >
       parseInt(getComputedStyle(TM.$(".leaflet-overlay-pane")).zIndex, 10),
       [getComputedStyle(segPane).zIndex, getComputedStyle(TM.$(".leaflet-overlay-pane")).zIndex],
       "segment pane higher");
  const inPane = [...segPane.querySelectorAll("path")];
  T.ok("the Tours' segment hit areas are in it", inPane.length > 0, inPane.length, "> 0");
  T.eq("and nothing else is", [...new Set(inPane.map(p => p.getAttribute("stroke-width")))], ["18"]);
  T.eq("none is left behind in the overlay pane",
       TM.$$(".leaflet-overlay-pane path").filter(p => p.getAttribute("stroke-width") === "18").length, 0);

  T.test("hiding the Tours empties that pane, so the trails underneath stay clickable");
  // The user's own requirement once the pane went in: "Hauptsache ich kann auch die Trails treffen, wenn die
  // Touren ausgeblendet sind". A higher pane that kept its areas while its Tours were hidden would block
  // every trail under them. render() already removes them; this pins it, because the pane makes the cost of
  // getting it wrong much higher than it was.
  const tourSwitch = TM.$$("input[type=checkbox]").find(i =>
    /Touren/.test((i.closest("label") || i.parentElement).textContent));
  if (!tourSwitch) {
    T.skip("no Touren switch in this build");
  } else {
    const was = tourSwitch.checked;
    if (was) { tourSwitch.click(); await TM.wait(500); }
    T.eq("pane is empty with the Tours hidden", segPane.querySelectorAll("path").length, 0);
    tourSwitch.click();
    await TM.wait(500);
    T.ok("and refilled when they come back", segPane.querySelectorAll("path").length > 0,
         segPane.querySelectorAll("path").length, "> 0");
    if (!was) { tourSwitch.click(); await TM.wait(300); }
  }

  T.test("solo dims a trail's direction arrows, FILL and all -- and a connector grows less on hover than a trail");
  // Two rules that live one function apart and were each a real bug. (1) setArrowOpacity has to set
  // fillOpacity as well as opacity: since 2026-08-20 an arrow is a FILLED triangle, so dimming only the
  // stroke left every dimmed trail's arrows glowing at full white. (2) applyLineWeight adds a SMALLER
  // hover delta to a connector (0.8) than to a trail (3.0): at the full delta a marked Trailrunde's
  // connectors reached 5.8px and their 6,6 dash pattern read as a solid grey line, which is the whole
  // visual signal for "this is a connector, not a trail" (user, 2026-08-04, "dann verschwinden die Lücken
  // fast"). Both are read off the painted SVG, since the constants themselves are unreachable from here.
  await TM.ui.setSwitch("showDirectionArrowsToggle", true);
  const arrowPolys = () => TM.map.overlay().filter((p) => p.getAttribute("stroke-width") === "1.2" &&
                                                          p.getAttribute("fill") !== "none");
  const card0 = TM.ui.trailCards()[0];
  card0.click();
  await TM.until(() => card0.classList.contains("selected"), 3000);
  // Arrows only exist above ARROW_MIN_ZOOM (15) and only for trails in view, and the card click's own
  // flyToTrailBounds is animated -- so in a window with no animation frames it never arrives and the view
  // stays wherever the previous case left it. Borrow the map (the same getZoom trampoline bearing.js uses,
  // since `map` is a const in the app's own scope) and put it at 15 with the whole region in view, which
  // makes "are there arrows" a property of the app rather than of the last case's leftovers.
  const grabMap = () => {
    let m = null;
    const orig = L.Map.prototype.getZoom;
    L.Map.prototype.getZoom = function () { m = this; return orig.apply(this, arguments); };
    try { updateStartDotVisibility(); } finally { L.Map.prototype.getZoom = orig; }
    return m;
  };
  const map0 = grabMap();
  if (map0) { map0.setZoom(15, { animate: false }); }
  await TM.until(() => arrowPolys().length > 0, 3000);
  if (!arrowPolys().length) {
    T.skip("no direction arrows painted at this view -- nothing to read");
  } else {
    // Every arrow of the trail that is NOT soloed has to be dimmed on both channels. Reading the minimum
    // over the whole set is what makes this independent of which trail happens to be soloed.
    const soloBtn = TM.$("#infoPanel .solo-btn") || TM.$("#infoPanel .ip-btns button[title*='ur dies']");
    if (!soloBtn) {
      T.skip("no solo button in the open panel");
    } else {
      soloBtn.click();
      await TM.wait(500);
      // Leaflet's SVG renderer writes the `opacity` option as **stroke-opacity** and `fillOpacity` as
      // **fill-opacity**; there is no plain `opacity` attribute to read, and looking for one reports every
      // arrow as undimmed on a correct app.
      const dimmed = arrowPolys().filter((p) => +(p.getAttribute("stroke-opacity") || 1) < 0.5);
      T.ok("some arrows are dimmed by the solo", dimmed.length > 0, dimmed.length, "> 0");
      const fillsMatch = dimmed.every((p) => {
        const o = p.getAttribute("stroke-opacity"), f = p.getAttribute("fill-opacity");
        return f !== null && Math.abs(+f - +o) < 0.001;
      });
      T.ok("and every dimmed arrow's FILL is dimmed by the same amount, not left opaque",
           fillsMatch, dimmed.slice(0, 3).map((p) => p.getAttribute("stroke-opacity") + "/" +
                                                     p.getAttribute("fill-opacity")), "fill == stroke");
      soloBtn.click();
      await TM.wait(400);
    }
    // The arrows are also the one place the trail's own difficulty is repeated as a light TINT (2026-08-21,
    // replacing one fixed white); at least two different tints must be on the map, or the fill is not being
    // taken from the trail at all. Inside the guard, because on an empty set it would report "no tints" as a
    // failure -- which is what it did on the run that verified the mutation above, hiding it.
    const tints = new Set(arrowPolys().map((p) => (p.getAttribute("fill") || "").toLowerCase()));
    const known = ["#a8e8ba", "#a9cdf5", "#f5aa9d", "#c7c7c7"];
    T.ok("arrow fills come from the per-difficulty tint set, not one fixed colour",
         [...tints].every((c) => known.indexOf(c) > -1) && tints.size >= 2,
         [...tints], ">= 2 of " + known.join("/"));
  }
  closeInfoPanelAndDeselect();
  await TM.wait(200);

  T.test("hovering a Trailrunde grows its connectors by less than a trail's own delta");
  const hoverTourCard = TM.ui.tourCards()[0];
  if (!hoverTourCard) {
    T.skip("no Tour in this region");
  } else {
    const widths = () => TM.map.overlay().map((p) => p.getAttribute("stroke-width"));
    const restWidths = widths();
    T.ok("at rest a connector is the thin 2.2", restWidths.indexOf("2.2") > -1,
         restWidths.filter((w) => w === "2.2").length + " at 2.2", ">= 1");
    hoverTourCard.dispatchEvent(new PointerEvent("pointerenter", { bubbles: true, pointerType: "mouse" }));
    await TM.wait(300);
    const hovered = widths();
    T.ok("hovered, its connectors are 3.0 -- not the trail delta's 5.2",
         hovered.indexOf("3") > -1 && hovered.indexOf("5.2") === -1,
         hovered.filter((w) => w === "3" || w === "5.2"), "3 present, 5.2 absent");
    hoverTourCard.dispatchEvent(new PointerEvent("pointerleave", { bubbles: true, pointerType: "mouse" }));
    await TM.wait(300);
    T.ok("and it goes back to 2.2", widths().indexOf("2.2") > -1, "restored", "restored");
  }

  // NOT covered here, deliberately: the sibling fix from the same report -- a Tour riding the same trail
  // twice highlighting the clicked occurrence rather than always the first (selectedSegmentIdx) -- cannot be
  // reached from a pasted suite. It needs `lineTrails` and `TRAIL_SEGMENTS` to find a Tour that repeats a
  // component and to call selectTourSegment(t, id, idx), and both are top-level `const` in the app's own
  // script block, so an injected script cannot see them (functions hoist, consts do not).
});
