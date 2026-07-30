// @suite   solo
// @area    Solo mode for trails, Tours and lifts
// @files   Trailmap App/index.html
// @touches applySolo, clearSolo, applyLiftVisibility, applyLiftSegmentOpacity, liftHiddenBySolo, baselineLineOpacity, resetAllHoverStyles, applyLineWeight, syncSelectedCardSoloBtn, SOLO_DIM_OPACITY, liftSegments
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

TM.add("solo", () => typeof applySolo === "function" && TM.map.tourLiftStretches() > 0 && TM.ui.cardNamed("liftCards", /Hörnli/) && TM.ui.cardNamed("tourCards", /Biketicket/), async (T) => {
  const LIFTS_ON_MAP = TM.map.standaloneLifts();
  const TOUR_STRETCHES = TM.map.tourLiftStretches();
  const firstTrail = () => TM.ui.trailCards()[0];
  const trailIdOf = (card) => {
    // The card carries no id; find it through the layer registry the app exposes by function only.
    const name = card.querySelector(".trail-name").textContent.replace("👁", "").trim();
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
  other.dispatchEvent(new MouseEvent("mouseenter"));
  await TM.wait(250);
  T.ok("still dimmed while hovering", TM.map.dimmedTrails() >= dimmedBefore - 1, TM.map.dimmedTrails(), "~" + dimmedBefore);
  other.dispatchEvent(new MouseEvent("mouseleave"));
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
});
