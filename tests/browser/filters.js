// @suite   filters
// @area    Visibility rules and the four summary counts
// @files   Trailmap App/index.html
// @touches trailPassesFilters, liftPassesFilters, liftHiddenBySolo, matchesSearch, searchTerm, trailSearchInput, activeDiffs, activeRegions, showUphill, showLoop, showDownhill, showLifts, render, filterCountLabel, trailCountLabel, tourCountLabel, liftCountLabel, syncSearchFieldLocation, floating-on-map, floating-fixed, sidebar-search-footer, isMobileLayout, openSidebar, closeSidebar
// @needs   region=bikekingdom, builder=off
//
// The search box (added 2026-08-09) is matchesSearch() as one more AND-ed condition inside
// trailPassesFilters()/liftPassesFilters(), so it has to be proven to COMBINE with the others rather than
// override them -- a name match on a difficulty that is switched off must still be hidden. searchTerm itself
// is a `let` inside the app's own try{} block and unreachable from here (same reason lineLayers/soloId are
// unreachable, see the harness notes), so every case below drives the real #trailSearchInput element instead
// of poking the variable.
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

  T.test("the search box matches Trails, Touren and Lifte by name, case/diacritics-insensitive");
  const searchEl = TM.$("#trailSearchInput");
  const setSearch = async (v) => {
    searchEl.value = v;
    searchEl.dispatchEvent(new Event("input", { bubbles: true }));
    await TM.wait(300);
  };
  // FLOWline/FLOWline lower are real ids in this region -- the exact pair the user's own report named
  // (2026-08-09: searching "flowline" left every OTHER trail's name label on the map, see the labels suite
  // for that half of the bug).
  await setSearch("flowline");
  T.eq("only the two FLOWline trails are listed", TM.ui.trailCards().length, 2);
  T.ok("both really carry the term", TM.ui.names("trailCards").every((n) => /flowline/i.test(n)),
       TM.ui.names("trailCards"), "all containing 'flowline'");
  await setSearch("FLOWLINE");
  T.eq("case does not matter", TM.ui.trailCards().length, 2);
  await setSearch("hornli");   // no umlaut, on purpose
  T.ok("diacritics-insensitive: 'hornli' still finds the Hörnli lift", TM.ui.cardNamed("liftCards", /Hörnli/),
       TM.ui.names("liftCards"), "a Hörnli card");
  await setSearch("biketicket");
  T.ok("and it matches a Tour's name too", TM.ui.cardNamed("tourCards", /Biketicket/i),
       TM.ui.names("tourCards"), "a Biketicket card");
  await setSearch("thisnametrailwillneverexist");
  T.eq("a term matching nothing empties all three lists",
       TM.ui.trailCards().length + TM.ui.tourCards().length + TM.ui.liftCards().length, 0);
  await setSearch("");
  T.eq("clearing restores the full trail count", TM.ui.trailCards().length, trails0);
  T.eq("and the full lift count", TM.ui.liftCards().length, lifts0);

  T.test("a search match does not override a filtered-out difficulty, region or category");
  // Both FLOWline trails are blau; both PRIMEline trails are rot. A name match must not resurrect a trail
  // whose difficulty the user has switched off -- the two conditions AND together, neither wins alone.
  await setSearch("flowline");
  await TM.ui.setDiff("blau", false);
  T.eq("the difficulty filter still wins", TM.ui.trailCards().length, 0);
  await TM.ui.setDiff("blau", true);
  await TM.wait(300);
  T.eq("back once blau is on again", TM.ui.trailCards().length, 2);
  await setSearch("primeline");
  await TM.ui.setDiff("rot", false);
  T.eq("same for a different difficulty", TM.ui.trailCards().length, 0);
  await TM.ui.setDiff("rot", true);
  await TM.wait(300);
  T.eq("back once rot is on again", TM.ui.trailCards().length, 2);
  await setSearch("");
  await TM.wait(300);

  T.test("the search box force-opens Touren/Lifte while active and restores what the user had");
  document.getElementById("secTouren").open = false;
  document.getElementById("secLifts").open = false;
  await setSearch("biketicket");
  T.eq("Touren opens so the match is not hidden behind a closed section", document.getElementById("secTouren").open, true);
  await setSearch("");
  T.eq("and closes again on clear, since the user had it closed", document.getElementById("secTouren").open, false);
  T.eq("the persisted section state was not overwritten by the search",
       JSON.parse(localStorage.getItem("trailmap-ui-sections-v1") || "{}").secTouren, false);
  document.getElementById("secTouren").open = true;   // leave sections as later suites expect (all open)
  document.getElementById("secLifts").open = true;

  T.test("Escape clears the search box, same two-step behaviour as the region dialog's own search");
  await setSearch("flowline");
  T.eq("narrowed first", TM.ui.trailCards().length, 2);
  searchEl.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
  await TM.wait(300);
  T.eq("Escape empties the field", searchEl.value, "");
  T.eq("and the full list is back", TM.ui.trailCards().length, trails0);

  T.test("closing the sidebar on mobile floats the live search field onto the map, edited in place");
  // TM.bootFresh()'s iframe is 420px wide on purpose (see its own comment) -- narrow enough that
  // isMobileLayout() is true inside it, which is exactly the layout syncSearchFieldLocation() only acts on.
  // It shares localStorage with this window, so it comes up with the same active region (bikekingdom) already
  // on, and its DOM is real and same-origin -- driving #sidebarToggle/#trailSearchInput/#sidebarBackdrop
  // there exercises the actual reparenting code, not a stand-in for it.
  {
    const boot = await TM.bootFresh();
    try {
      const fdoc = boot.doc;
      T.ok("the iframe is narrow enough to count as mobile", boot.win.innerWidth <= 768, boot.win.innerWidth, "<=768");
      const wrap = fdoc.querySelector(".search-field-wrap");
      const fInput = fdoc.getElementById("trailSearchInput");
      T.ok("the field starts in the sidebar footer, closed sidebar, no search yet",
           wrap.parentElement.classList.contains("sidebar-search-footer") && !wrap.classList.contains("floating-on-map"),
           true, true);
      fdoc.getElementById("sidebarToggle").click();
      fInput.value = "flowline";
      fInput.dispatchEvent(new Event("input", { bubbles: true }));
      await TM.wait(50);
      T.ok("still in the footer while the sidebar (its normal home) is open",
           wrap.parentElement.classList.contains("sidebar-search-footer"), true, true);
      fdoc.getElementById("sidebarBackdrop").click();
      T.ok("closing the sidebar with a search active floats the SAME node onto the map",
           wrap.parentElement.classList.contains("map-wrap") && wrap.classList.contains("floating-on-map"),
           true, true);
      fInput.value = "flowlinex";
      fInput.dispatchEvent(new Event("input", { bubbles: true }));
      await TM.wait(50);
      T.eq("it is genuinely the same input -- typing while floated keeps its own value", fInput.value, "flowlinex");
      fdoc.getElementById("trailSearchClear").click();
      T.ok("the ✕ clears the term and sends the field back to the (now empty, hidden) footer",
           fInput.value === "" && wrap.parentElement.classList.contains("sidebar-search-footer") &&
           !wrap.classList.contains("floating-on-map"),
           true, true);
    } finally {
      boot.done();
    }
  }

  T.test("on desktop the field floats WITHOUT reparenting, so a focused search never loses focus");
  // isMobileLayout() only reads window.innerWidth here (a real mouse pointer never matches (pointer:coarse)),
  // so stubbing it is enough to force the desktop branch deterministically, whatever width this window
  // actually happens to be pasted into. The first version of this feature floated the field on desktop the
  // same way as mobile -- by reparenting it -- and the user hit a real bug doing exactly this: typing the
  // very first character of a search moved the (still focused) node to a new parent and the field lost
  // focus ("es springt einfach hoch und verliert den Fokus", 2026-08-09). Desktop now only ever toggles
  // `position:fixed` on the SAME node (.floating-fixed, not .floating-on-map -- that class stays mobile-only
  // and reparents) via CSS custom properties, so this asserts the node itself never moves AND stays focused
  // through the whole test, not just that it visually ends up in the right place.
  {
    const widthDesc = Object.getOwnPropertyDescriptor(window, "innerWidth");
    Object.defineProperty(window, "innerWidth", { value: 1400, configurable: true });
    try {
      const wrap = TM.$(".search-field-wrap");
      const footer = TM.$(".sidebar-search-footer");
      searchEl.focus();
      await setSearch("flowline");
      T.ok("the node never left the sidebar footer", wrap.parentElement === footer, wrap.parentElement.className, "sidebar-search-footer");
      T.ok("it switched to position:fixed instead", wrap.classList.contains("floating-fixed"), wrap.className, "…floating-fixed…");
      T.ok("and never picked up the mobile (reparenting) class", !wrap.classList.contains("floating-on-map"), wrap.className, "no floating-on-map");
      T.ok("the field kept focus through the whole transition", document.activeElement === searchEl,
           document.activeElement && document.activeElement.id, "trailSearchInput");
      // The un-capped first version stretched to the map's own top-right control cluster, which on a
      // genuinely wide window read as "too wide" (user, 2026-08-09) -- width is an explicit min(), not a
      // left+right stretch, so it must stay compact regardless of how much room the map actually has.
      const w = wrap.getBoundingClientRect().width;
      T.ok("width stays capped rather than stretching with the window", w > 0 && w <= 330, w, "<= 330");
      await setSearch("");
      T.ok("clearing removes the fixed positioning, still the same node in the same place",
           wrap.parentElement === footer && !wrap.classList.contains("floating-fixed"),
           { parent: wrap.parentElement.className, cls: wrap.className }, "back in the footer, no floating-fixed");
    } finally {
      if (widthDesc) Object.defineProperty(window, "innerWidth", widthDesc); else delete window.innerWidth;
      searchEl.blur();
    }
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
