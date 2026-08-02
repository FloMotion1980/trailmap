// @suite   filters
// @area    Visibility rules and the four summary counts
// @files   Trailmap App/index.html
// @touches trailPassesFilters, liftPassesFilters, liftHiddenBySolo, activeDiffs, activeRegions, showUphill, showLoop, showDownhill, showLifts, render, filterCountLabel, trailCountLabel, tourCountLabel, liftCountLabel
// @needs   region=bikekingdom, builder=off
//
// One rule decides what is on the map and what is in a list -- trailPassesFilters -- and it is called from two
// places (the map loop in render() and renderTourList). The suite pins the rule itself AND the numbers it
// produces, because the counts are what a user reads to check the filters did what they asked.
//
// The categories are mutually exclusive on purpose: a trail is a Tour, an uphill or a downhill, never two.
// That is what lets you isolate "only Tours" by turning the other two off, and it is why the check picks
// exactly one switch per trail instead of ANDing three booleans.

TM.add("filters", () => typeof trailPassesFilters === "function" && trailPassesFilters({id:"x", region:"bk_bear_mountains", diff:"rot"}) && TM.ui.cardNamed("liftCards", /Hörnli/) && TM.ui.cardNamed("tourCards", /Biketicket/), async (T) => {
  const bk = (id) => ({ id: id, region: "bk_bear_mountains", diff: "rot" });

  T.test("trailPassesFilters needs region AND difficulty AND the right category");
  const plain = { id: "x", region: "bk_bear_mountains", diff: "rot" };
  T.ok("a plain visible trail passes", trailPassesFilters(plain) === true, trailPassesFilters(plain), true);
  T.ok("an inactive sub-region fails", trailPassesFilters({ id: "x", region: "not_a_region", diff: "rot" }) === false,
       trailPassesFilters({ id: "x", region: "not_a_region", diff: "rot" }), false);
  await TM.ui.setDiff("rot", false);
  T.ok("a filtered-out difficulty fails", trailPassesFilters(plain) === false, trailPassesFilters(plain), false);
  T.ok("another difficulty still passes", trailPassesFilters({ id: "x", region: "bk_bear_mountains", diff: "blau" }) === true,
       true, true);
  await TM.ui.setDiff("rot", true);

  T.test("exactly one category switch applies per trail");
  const dh = { id: "d", region: "bk_bear_mountains", diff: "rot" };
  const up = { id: "u", region: "bk_bear_mountains", diff: "rot", uphill: true };
  const loop = { id: "l", region: "bk_biketickets", diff: "rot", loop: true };
  await TM.ui.setSwitch("showDownhillToggle", false);
  T.ok("downhill off hides a plain trail", trailPassesFilters(dh) === false, trailPassesFilters(dh), false);
  T.ok("but not an uphill", trailPassesFilters(up) === true, trailPassesFilters(up), true);
  T.ok("and not a Tour", trailPassesFilters(loop) === true, trailPassesFilters(loop), true);
  await TM.ui.setSwitch("showDownhillToggle", true);
  await TM.ui.setSwitch("showUphillToggle", false);
  T.ok("uphill off hides only the uphill", trailPassesFilters(up) === false && trailPassesFilters(dh) === true, true, true);
  await TM.ui.setSwitch("showUphillToggle", true);
  await TM.ui.setSwitch("showLoopToggle", false);
  T.ok("Touren off hides only the Tour", trailPassesFilters(loop) === false && trailPassesFilters(dh) === true, true, true);
  await TM.ui.setSwitch("showLoopToggle", true);

  T.test("builder mode hides every Tour whatever the switch says");
  // A Tour lies on top of the very trails you are picking, so its line, its per-segment labels and its wide
  // hit-lines all get in the way -- which is the whole activity in that mode.
  await TM.ui.builderMode(true);
  T.ok("with the switch ON, a Tour is still hidden", trailPassesFilters(loop) === false, trailPassesFilters(loop), false);
  T.ok("ordinary trails are unaffected", trailPassesFilters(dh) === true, trailPassesFilters(dh), true);
  T.eq("the Touren list is empty", TM.ui.tourCards().length, 0);
  T.ok("and its count says so rather than reading 0",
       /Builder/i.test(TM.ui.counts().touren), TM.ui.counts().touren, "mentions the builder");
  await TM.ui.builderMode(false);
  T.ok("leaving the mode brings them back", trailPassesFilters(loop) === true, trailPassesFilters(loop), true);

  T.test("liftPassesFilters is the switch and the sub-region, with no Tour exemption");
  const lift = { id: "lift_bk_hoernli", region: "bk_bear_mountains" };
  T.ok("a lift in an active sub-region passes", liftPassesFilters(lift) === true, liftPassesFilters(lift), true);
  T.ok("an inactive sub-region fails", liftPassesFilters({ id: "l", region: "nope" }) === false, false, false);
  await TM.ui.setSwitch("showLiftsToggle", false);
  T.ok("the switch off hides it", liftPassesFilters(lift) === false, liftPassesFilters(lift), false);
  // The exemption existed from 2026-07-26 to 2026-07-30 and was rejected as inconsistent: a rot trail inside
  // a Tour is equally gone from the map, the list and the counts when rot is off.
  T.ok("even one that a visible Tour rides",
       liftPassesFilters({ id: "lift_bk_chur_kaenzeli", region: "bk_park_chur" }) === false, false, false);
  await TM.ui.setSwitch("showLiftsToggle", true);

  T.test("liftHiddenBySolo keeps the soloed lift and a soloed Tour's own lifts");
  T.ok("nothing soloed: nothing hidden", liftHiddenBySolo("lift_bk_hoernli") === false, false, false);
  applySolo("lift_bk_hoernli");
  await TM.wait(250);
  T.ok("the soloed lift is not hidden", liftHiddenBySolo("lift_bk_hoernli") === false, false, false);
  T.ok("another lift is", liftHiddenBySolo("lift_bk_rothorn1") === true, true, true);
  clearSolo();
  await TM.wait(250);
  applySolo("bk_tour_615_blau");
  await TM.wait(300);
  T.ok("a lift the soloed Tour rides stays", liftHiddenBySolo("lift_bk_chur_kaenzeli") === false, false, false);
  T.ok("a lift it does not ride goes", liftHiddenBySolo("lift_bk_hoernli") === true, true, true);
  clearSolo();
  await TM.wait(250);

  T.test("the four counts split by question, and add up");
  const base = TM.ui.counts();
  T.eq("nothing hidden is said outright", base.filter, "alles sichtbar");
  T.ok("Trails counts trails", /^\d+ Trails?$/.test(base.trails), base.trails, "N Trails");
  T.ok("Touren counts Touren", /^\d+ Touren?$/.test(base.touren), base.touren, "N Touren");
  T.ok("Lifte counts Lifte", /^\d+ Lifte?$/.test(base.lifts), base.lifts, "N Lifte");
  const trails0 = TM.ui.num(base.trails), tours0 = TM.ui.num(base.touren), lifts0 = TM.ui.num(base.lifts);
  T.eq("the Trails list has exactly that many cards", TM.ui.trailCards().length, trails0);
  T.eq("the Touren list too", TM.ui.tourCards().length, tours0);
  T.eq("the Lifte list too", TM.ui.liftCards().length, lifts0);

  T.test("hiding a difficulty is reported per kind and the sums stay right");
  await TM.ui.setDiff("schwarz", false);
  await TM.wait(300);
  const c = TM.ui.counts();
  const hiddenTrails = TM.ui.num(c.filter);
  T.ok("the line starts with the Trails term", /^\d+ Trails?\b/.test(c.filter), c.filter, "N Trails ...");
  T.ok("and ends with ausgeblendet", /ausgeblendet$/.test(c.filter), c.filter, "... ausgeblendet");
  T.eq("shown + hidden = the old total", TM.ui.num(c.trails) + hiddenTrails, trails0);
  // "Tour(en)?", not "Touren?": the app says "1 Tour" in the singular and this pattern demanded at least
  // "Toure", so it only ever passed while the hidden difficulty happened to contain no Tour at all. In
  // bikekingdom exactly one Tour is schwarz, and the line it produced -- "24 Trails · 1 Tour ausgeblendet" --
  // is correct. A check that depends on which region's data it meets is worse than no check.
  T.ok("Touren are named separately when some are hidden",
       tours0 === TM.ui.num(c.touren) || /Tour(en)?\b/.test(c.filter), c.filter, "mentions Tour/Touren");
  T.eq("the lift count is untouched by a difficulty", TM.ui.num(c.lifts), lifts0);
  await TM.ui.setDiff("schwarz", true);
  await TM.wait(300);
  T.eq("and back to nothing hidden", TM.ui.counts().filter, "alles sichtbar");

  T.test("hiding lifts names every loaded lift, and only lifts");
  await TM.ui.setSwitch("showLiftsToggle", false);
  await TM.wait(300);
  const off = TM.ui.counts();
  T.eq("all of them are reported hidden", TM.ui.num(off.filter), lifts0);
  T.ok("only the lift term is present", /^\d+ Lifte? ausgeblendet$/.test(off.filter), off.filter, "N Lifte ausgeblendet");
  T.eq("the trail count did not move", TM.ui.num(off.trails), trails0);
  T.eq("nor the Tour count", TM.ui.num(off.touren), tours0);
  T.eq("the list is empty", TM.ui.liftCards().length, 0);
  T.eq("and none is on the map", TM.map.standaloneLifts(), 0);
  await TM.ui.setSwitch("showLiftsToggle", true);
  await TM.wait(300);
  T.eq("restored", TM.map.standaloneLifts(), lifts0);

  T.test("a sub-region chip's count includes its Tours");
  // Bike Kingdom's "Biketicket 2 Ride" holds nothing but Tours; a chip reading (0) next to four visible ones
  // would be a lie, which is why the chips deliberately count more than the Trails list does.
  const chip = TM.$$("#regionChips .chip").find((b) => /Biketicket/i.test(b.textContent));
  if (!chip) {
    T.skip("no Tours-only sub-region in the active regions");
  } else {
    // Parse the TRAILING (n): "Biketicket 2 Ride (4)" has a digit in its name too, and stripping all
    // non-digits read that as 24 on the first attempt.
    const trailing = (el) => +(/\((\d+)\)\s*$/.exec(el.textContent.trim()) || [0, -1])[1];
    T.ok("the chip carries a non-zero count", trailing(chip) > 0, chip.textContent.trim(), "> 0");
    const hub = TM.$$("#tourList .hub-title").find((h) => /Biketicket/i.test(h.textContent));
    T.eq("and it equals that hub's Tour count in the Touren list", trailing(chip), hub ? trailing(hub) : -1);
  }

  T.test("render() is idempotent: calling it twice changes no number");
  const before = JSON.stringify(TM.ui.counts());
  render();
  await TM.wait(300);
  render();
  await TM.wait(300);
  T.eq("counts unchanged", JSON.stringify(TM.ui.counts()), before);
  T.eq("no duplicated cards", TM.ui.trailCards().length, trails0);
  T.eq("no duplicated lift cards", TM.ui.liftCards().length, lifts0);
});
