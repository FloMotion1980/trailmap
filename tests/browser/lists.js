// @suite   lists
// @area    The three sidebar list sections and their cards
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches makeTrailCard, renderTourList, renderLiftList, render, selectTrail, selectLiftCard, selectCardFor, clearSelection, highlightSelectedTrail, trail-card, lift-card, card-solo-btn, hub-title, region-group-title, card-tint, buildTrailListDom, appendTrailGroup, trailGroupMode, trailSortMode, trailSortDir, trailViewGearBtn, trailViewSettings, trailViewResetBtn, syncTrailViewChips, persistTrailListView, TRAIL_SORT_COMPARE, TRAIL_SORT_DEFAULT_DIR, TRAIL_VIEW_DEFAULTS, categoryBadge, badge-uphill, SORT_LABELS, sidebarScroll, sidebar-search-footer, syncSidebarToggleA11y, isMobileLayout, openSidebar, closeSidebar, wireCardHover, syncStartDot, updateStartDotVisibility,
//          buildDirectionArrowLayer, directionArrowLayer, DIFF_TINT, ARROW_SPEC,
//          showEndpoints, hideEndpoints, startDot, startMarker, START_DOT_MIN_ZOOM
// @needs   region=bikekingdom, builder=off
//
// Trails, Touren and Lifte are three lists built by three different code paths that must not drift apart, so
// the shared pieces are what this suite leans on: makeTrailCard() builds every trail and Tour card, and the
// selection lives in ONE `selectedCard` variable because a trail and a lift are never selected at once.
//
// Structure is checked as well as content: both list levels (region group, then sub-region) with their own
// counts, since a heading showing a count for cards it does not contain is exactly what happened when the
// Tours moved out of the trail list.

TM.add("lists", () => typeof renderTourList === "function" && TM.ui.cardNamed("liftCards", /Hörnli/) && TM.ui.cardNamed("tourCards", /Biketicket/), async (T) => {
  // This suite is the one that mutates trailGroupMode/trailSortMode/trailSortDir (like "regions" is the one
  // that mutates which regions are loaded) -- TM.baseline() deliberately does not touch either, since it is
  // UI-layout state, not a filter. Reset via the real reset button (the variables themselves are `let`s
  // inside the app's own try{} block and unreachable here, like lineLayers/soloId -- see the harness notes)
  // rather than trust whatever a previous run or a bit of manual poking in the same session left behind: a
  // leftover "diff" or "none" groupMode makes the very first case below (which expects #trailList
  // .region-group-title to exist) throw on a null getBoundingClientRect() instead of failing cleanly, which
  // is exactly what happened once already while writing this suite.
  const resetBtn = TM.$("#trailViewResetBtn");
  if (resetBtn) { resetBtn.click(); await TM.wait(250); }

  T.test("the sidebar has exactly three list sections, in order");
  // #sidebarScroll (2026-08-09) wraps everything scrolling, so the list sections are no longer DIRECT
  // children of <aside> -- a plain descendant selector still returns every <details> in DOCUMENT ORDER
  // (querySelectorAll's own guarantee), so filtering that down to just the three list ids still proves the
  // order, unlike a per-id lookup would (that would trivially "pass" regardless of where each one sits).
  const listSectionIds = ["secTrails", "secTouren", "secLifts"];
  const ids = TM.$$("aside details").map((d) => d.id).filter((id) => listSectionIds.includes(id));
  T.eq("order", ids, listSectionIds);
  T.ok("each has its own count label",
       ["#trailCountLabel", "#tourCountLabel", "#liftCountLabel"].every((s) => !!TM.$(s)), true, true);
  // One content column for the whole sidebar (2026-08-01). Checked as the rendered LEFT EDGE, not as a padding
  // value: these three sections sit outside .filters and get their indent from their own margin now, so a
  // padding-based check would fail on a correct layout. Every content edge has to agree -- that was the
  // complaint ("Trails, Lifte und Touren haben einen anderen Abstand als der Rahmen der Bike Regionen"), where
  // the trail cards sat at 12px against the region boxes' 16px.
  const leftOf = (sel) => Math.round(TM.$(sel).getBoundingClientRect().left);
  const column = leftOf("#regionChips .region-group-block");
  [["#secFilter .section-title-row", "the Filter heading"],
   ["#secTrails .section-title-row", "the Trails heading"],
   ["#secTouren .section-title-row", "the Touren heading"],
   ["#secLifts .section-title-row", "the Lifte heading"],
   ["#addRegionBtn", "the add-region button"],
   ["#diffChips .chip", "the difficulty chips"],
   ["#trailList .trail-card", "the trail cards"],
   ["#trailList .hub-title", "the hub headings"],
   ["#trailList .region-group-title", "the region-group headings"]].forEach(([sel, what]) => {
    T.ok(what + " starts on the content column", Math.abs(leftOf(sel) - column) <= 1,
         leftOf(sel) - column, "0 from the region boxes");
  });

  T.test("every separator line in the menu is the same length, and there is only one per boundary");
  // Section lines used to be 349px outside .filters and 317px inside it, and each hub drew a third separator on
  // top of its own coloured heading -- two lines and a title for one boundary before a new region group.
  const seps = [];
  TM.$$("aside *").forEach((e) => {
    // .sidebar-search-footer's own top border (2026-08-09) is deliberately full-bleed edge-to-edge, the
    // same kind of divider the header already draws at the OTHER end of the page -- not inset to the 16px
    // content column like every section separator this case actually checks. Excluded by design, not missed.
    if (e.classList.contains("sidebar-search-footer")) return;
    const cs = getComputedStyle(e), r = e.getBoundingClientRect();
    if (r.width < 40) return;
    // A separator is a line, i.e. a border on the top or bottom ONLY. Anything with a left or right border is a
    // box (a card, a chip, the region pill, a button) and is not part of this question -- the first version of
    // this check listed the region-group pills as 143px and 186px "separators".
    if (parseFloat(cs.borderLeftWidth) > 0 || parseFloat(cs.borderRightWidth) > 0) return;
    ["Top", "Bottom"].forEach((side) => {
      if (parseFloat(cs["border" + side + "Width"]) > 0 && cs["border" + side + "Color"] !== "rgba(0, 0, 0, 0)") {
        seps.push({ el: e.id || e.className.toString().split(" ")[0], w: Math.round(r.width) });
      }
    });
  });
  T.ok("there are separator lines to compare", seps.length >= 4, seps.length, ">= 4");
  T.eq("all of them span the same width", [...new Set(seps.map((s) => s.w))], [Math.round(TM.$("#regionChips .region-group-block").getBoundingClientRect().width)]);
  T.eq("no hub group draws its own line any more",
       TM.$$("#trailList .hub-group").filter((g) => parseFloat(getComputedStyle(g).borderBottomWidth) > 0).length, 0);

  T.test("the trail list is grouped region -> sub-region, each with its own count");
  const groups = TM.$$("#trailList .region-group-title");
  const hubs = TM.$$("#trailList .hub-title");
  T.ok("at least one region group heading", groups.length >= 1, groups.length, ">= 1");
  T.ok("at least one sub-region heading", hubs.length >= 1, hubs.length, ">= 1");
  T.ok("every group heading carries a (n)", groups.every((g) => /\(\d+\)/.test(g.textContent)), true, true);
  T.ok("every hub heading carries a (n)", hubs.every((h) => /\(\d+\)/.test(h.textContent)), true, true);
  // Each hub's own count must equal the cards under it, or the heading is counting something else.
  const wrongHub = TM.$$("#trailList .hub-group").filter((g) => {
    const n = +(g.querySelector(".hub-title").textContent.match(/\((\d+)\)/) || [0, -1])[1];
    return n !== g.querySelectorAll(".trail-card").length;
  }).map((g) => g.querySelector(".hub-title").textContent.trim());
  T.eq("every hub count equals its own cards", wrongHub, []);
  const groupSum = TM.$$("#trailList .region-group-title")
    .map((g) => +(g.textContent.match(/\((\d+)\)/) || [0, 0])[1]).reduce((a, b) => a + b, 0);
  T.eq("the group counts add up to the section count", groupSum, TM.ui.num(TM.ui.counts().trails));

  T.test("no Tour appears in the trail list, and no 🔁 badge is left anywhere in a list");
  T.eq("no loop badge in either list", TM.$$("#trailList .badge-loop").length + TM.$$("#tourList .badge-loop").length, 0);
  const tourNames = TM.ui.names("tourCards");
  const trailNames = TM.ui.names("trailCards");
  T.eq("the two lists share no entry", tourNames.filter((n) => trailNames.indexOf(n) > -1), []);

  T.test("trail cards are sorted by difficulty inside a sub-region");
  const order = { gruen: 0, blau: 1, rot: 2, schwarz: 3 };
  const badOrder = [];
  TM.$$("#trailList .hub-group").forEach((g) => {
    const diffs = [...g.querySelectorAll(".trail-card .badge")]
      .map((b) => [...b.classList].find((c) => c in order)).map((d) => order[d]);
    for (let i = 1; i < diffs.length; i++) if (diffs[i] < diffs[i - 1]) badOrder.push(g.querySelector(".hub-title").textContent.trim());
  });
  T.eq("easiest first, everywhere", [...new Set(badOrder)], []);

  T.test("the Trails list's own gear opens its settings without toggling the section itself");
  // The gear lives inside #secTrails' own <summary>, whose native behaviour is to toggle the whole
  // <details> on any click inside it -- the gear's click handler has to preventDefault/stopPropagation or
  // every tap on it would also collapse the Trails section (2026-08-09).
  const gearBtn = TM.$("#trailViewGearBtn");
  const panel = TM.$("#trailViewSettings");
  T.eq("closed by default", panel.classList.contains("open"), false);
  gearBtn.click();
  T.ok("opens on click", panel.classList.contains("open"), true, true);
  T.ok("the Trails section itself is untouched by the gear", TM.$("#secTrails").open, true, true);

  T.test("grouping by difficulty splits into per-difficulty headings, canonical order, counts add up");
  TM.$('.trail-view-chips[data-target="group"] [data-value="diff"]').click();
  await TM.wait(300);
  T.eq("no region grouping left", TM.$$("#trailList .region-group-title").length, 0);
  const DIFF_ORDER_NAMES = ["Sehr leicht", "Leicht", "Mittel", "Schwer"];
  const diffSeen = TM.$$("#trailList .hub-title").map((e) => e.textContent.replace(/\s*\(\d+\)$/, "").trim());
  T.ok("every heading is one of the four difficulty labels", diffSeen.every((s) => DIFF_ORDER_NAMES.includes(s)), diffSeen, "all in " + DIFF_ORDER_NAMES);
  T.eq("in canonical order, easiest first", diffSeen, DIFF_ORDER_NAMES.filter((d) => diffSeen.includes(d)));
  const diffTotal = TM.$$("#trailList .hub-title").reduce((sum, e) => sum + (+(/\((\d+)\)/.exec(e.textContent) || [0, 0])[1]), 0);
  T.eq("the heading counts add up to the section total", diffTotal, TM.ui.num(TM.ui.counts().trails));
  const DIFF_CLASS_BY_LABEL = { "Sehr leicht": "gruen", "Leicht": "blau", "Mittel": "rot", "Schwer": "schwarz" };
  const mismatched = TM.$$("#trailList .hub-group").filter((g) => {
    const want = DIFF_CLASS_BY_LABEL[g.querySelector(".hub-title").textContent.replace(/\s*\(\d+\)$/, "").trim()];
    return [...g.querySelectorAll(".trail-card .badge")].some((b) => !b.classList.contains(want));
  });
  T.eq("every card under a difficulty heading really has that difficulty", mismatched.length, 0);

  T.test("grouping by category splits into exactly Downhill and Uphill, no Tour ever in either");
  TM.$('.trail-view-chips[data-target="group"] [data-value="category"]').click();
  await TM.wait(300);
  const catSeen = TM.$$("#trailList .hub-title").map((e) => e.textContent.replace(/\s*\(\d+\)$/, "").trim());
  T.eq("exactly Downhill then Uphill", catSeen, ["Downhill", "Uphill"]);
  const uphillGroup = TM.$$("#trailList .hub-group").find((g) => /Uphill/.test(g.querySelector(".hub-title").textContent));
  T.ok("every card in Uphill carries the uphill badge",
       !!uphillGroup && [...uphillGroup.querySelectorAll(".trail-card")].every((c) => /⬆️/.test(c.textContent)), true, true);
  T.eq("no loop badge sneaks into either category (Tours are a separate list)",
       TM.$$("#trailList .badge-loop").length, 0);

  T.test("grouping 'none' is a flat list; sorting by name/length reorders it, not the count");
  TM.$('.trail-view-chips[data-target="group"] [data-value="none"]').click();
  await TM.wait(300);
  T.eq("no headings of either kind", TM.$$("#trailList .hub-title").length + TM.$$("#trailList .region-group-title").length, 0);
  const flatCount = TM.ui.trailCards().length;
  T.eq("but every trail is still listed", flatCount, TM.ui.num(TM.ui.counts().trails));

  TM.$('.trail-view-chips[data-target="sort"] [data-value="name"]').click();
  await TM.wait(300);
  const flatNames = TM.ui.names("trailCards");
  T.eq("name sort is alphabetical, numeric-aware", flatNames,
       flatNames.slice().sort((a, b) => a.localeCompare(b, "de", { numeric: true })));
  T.eq("the count is unaffected by which sort is picked", TM.ui.trailCards().length, flatCount);

  TM.$('.trail-view-chips[data-target="sort"] [data-value="length"]').click();
  await TM.wait(300);
  const lens = TM.ui.trailCards().map((c) => parseFloat(c.querySelector(".trail-meta span").textContent));
  T.ok("length sort is ascending by default -- shortest first", lens.every((v, i) => i === 0 || v >= lens[i - 1] - 1e-9),
       lens.slice(0, 6), "ascending");

  T.test("Bergauf/Bergab are separate sortable axes, each reversible by tapping the already-active chip");
  // The user's own report: a single "Höhenmeter" chip could only ever sort by descent, and there was no way
  // to flip direction at all -- both fixed in the same change, so tested together here.
  const upSortChip = TM.$('.trail-view-chips[data-target="sort"] [data-value="up"]');
  upSortChip.click();
  await TM.wait(300);
  T.eq("newly picked, Bergauf defaults to biggest-climb-first (descending)", upSortChip.textContent, "Bergauf ↓");
  const ups = TM.ui.trailCards().map((c) => +(/(\d+)\s*m\s*↑/.exec(c.querySelector(".trail-meta span:nth-child(2)").textContent) || [0, 0])[1]);
  T.ok("really is descending by climb", ups.every((v, i) => i === 0 || v <= ups[i - 1]), ups.slice(0, 6), "descending");
  upSortChip.click();
  await TM.wait(300);
  T.eq("tapping the already-active chip flips its own label to ↑", upSortChip.textContent, "Bergauf ↑");
  const upsFlipped = TM.ui.trailCards().map((c) => +(/(\d+)\s*m\s*↑/.exec(c.querySelector(".trail-meta span:nth-child(2)").textContent) || [0, 0])[1]);
  T.ok("and really is ascending now", upsFlipped.every((v, i) => i === 0 || v >= upsFlipped[i - 1]), upsFlipped.slice(0, 6), "ascending");

  const downSortChip = TM.$('.trail-view-chips[data-target="sort"] [data-value="down"]');
  downSortChip.click();
  await TM.wait(300);
  T.eq("Bergab is its OWN axis, independent of Bergauf, also defaulting to descending", downSortChip.textContent, "Bergab ↓");
  T.eq("picking a different chip resets its direction rather than carrying Bergauf's flipped one over",
       upSortChip.textContent, "Bergauf");
  const downs = TM.ui.trailCards().map((c) => +(/(\d+)\s*m\s*↓/.exec(c.querySelector(".trail-meta span:nth-child(2)").textContent) || [0, 0])[1]);
  T.ok("really is descending by descent", downs.every((v, i) => i === 0 || v <= downs[i - 1]), downs.slice(0, 6), "descending");

  T.test("only Uphill trails carry a category badge -- a downhill card stays unmarked, on purpose");
  // Tried the symmetric ⬇️ badge on every downhill card the same day and reverted it (user: "In den
  // Traileinträgen im Menü will ich das blaue Emoji nicht bei Downhill Trails") -- the blue-emoji pairing
  // is Filter's own Downhill/Uphill switches (⬇️/⬆️) now, not the cards.
  const uphillBadgeCount = TM.$$("#trailList .badge-uphill").length;
  T.ok("there is at least one uphill-badged card in this region", uphillBadgeCount > 0, uphillBadgeCount, "> 0");
  T.eq("no card anywhere carries a downhill badge -- the class doesn't exist any more",
       TM.$$(".badge-downhill").length, 0);
  const filterLabels = TM.$$("#secFilter .toggle-row").map((l) => l.textContent.trim());
  T.ok("Downhill switch uses the blue ⬇️ emoji, matching Uphill's ⬆️",
       filterLabels.some((t) => t.startsWith("⬇️")), filterLabels, "one starting with ⬇️");
  T.ok("Uphill switch still uses ⬆️", filterLabels.some((t) => t.startsWith("⬆️")), filterLabels, "one starting with ⬆️");

  T.test("the group/sort choice, including direction, is persisted under its own key");
  T.eq("the current choice is saved", JSON.parse(localStorage.getItem("trailmap-list-view-v1") || "{}"),
       { groupMode: "none", sortMode: "down", sortDir: -1 });

  T.test("the reset button restores every default in one tap");
  TM.$("#trailViewResetBtn").click();
  await TM.wait(300);
  T.eq("group back to region", TM.$('.trail-view-chips[data-target="group"] .active').dataset.value, "region");
  T.eq("sort back to Schwierigkeit, ascending", TM.$('.trail-view-chips[data-target="sort"] .active').textContent, "Schwierigkeit ↑");
  T.ok("the list itself is grouped by region again", TM.$$("#trailList .region-group-title").length > 0,
       TM.$$("#trailList .region-group-title").length, "> 0");
  T.eq("and the reset is what's persisted now", JSON.parse(localStorage.getItem("trailmap-list-view-v1") || "{}"),
       { groupMode: "region", sortMode: "diff", sortDir: 1 });

  panel.classList.remove("open");
  await TM.wait(300);

  T.test("Tour cards are sorted by name, numeric-aware, and keep their difficulty badge");
  const sorted = tourNames.slice().sort((a, b) => a.localeCompare(b, "de", { numeric: true }));
  // Compared per sub-region, since the list is grouped: a global sort would not hold across groups.
  const perHub = TM.$$("#tourList .hub-group").map((g) =>
    [...g.querySelectorAll(".trail-card .trail-name")].map((e) => e.textContent.replace("👁", "").trim()));
  const unsorted = perHub.filter((names) =>
    String(names) !== String(names.slice().sort((a, b) => a.localeCompare(b, "de", { numeric: true }))));
  T.eq("every hub's Tours are in name order", unsorted, []);
  T.eq("every Tour card has a difficulty badge", TM.$$("#tourList .trail-card .badge").length, tourNames.length);
  T.ok("a numbered series comes out in numeric order",
       sorted.length < 2 || sorted.join("|").indexOf("615") <= sorted.join("|").indexOf("616"), true, true);

  T.test("lift cards carry the type and the climb, and no difficulty badge");
  const liftCards = TM.ui.liftCards();
  T.ok("there are lift cards", liftCards.length > 0, liftCards.length, "> 0");
  T.eq("none has a difficulty badge", TM.$$("#liftList .trail-card .badge").length, 0);
  T.ok("every one names a lift type", liftCards.every((c) => /bahn|lift|Standseil|Schlepp|Gondel|Sessel|Seil/i.test(c.textContent)),
       liftCards[0].textContent.replace(/\s+/g, " ").trim(), "contains a type");
  T.ok("and a climb in metres", liftCards.every((c) => /\+\d+ m/.test(c.textContent)), true, true);
  T.ok("every lift card is prefixed with the cable icon", liftCards.every((c) => /🚡/.test(c.textContent)), true, true);
  T.ok("they reuse the trail-card class so the shared styles apply",
       liftCards.every((c) => c.classList.contains("trail-card")), true, true);

  T.test("every card is tinted with its own sub-region colour");
  const tinted = TM.ui.trailCards().filter((c) => c.style.getPropertyValue("--card-tint"));
  T.ok("trail cards carry --card-tint", tinted.length === TM.ui.trailCards().length, tinted.length, TM.ui.trailCards().length);
  T.ok("Tour cards too", TM.ui.tourCards().every((c) => !!c.style.getPropertyValue("--card-tint")), true, true);
  T.ok("lift cards too", TM.ui.liftCards().every((c) => !!c.style.getPropertyValue("--card-tint")), true, true);
  T.ok("the tint is a color-mix of the sub-region colour, not a literal",
       /color-mix/.test(tinted[0].style.getPropertyValue("--card-tint")),
       tinted[0].style.getPropertyValue("--card-tint"), "color-mix(...)");

  T.test("clicking a trail card selects it, opens its panel and marks the card");
  const card = TM.ui.trailCards()[0];
  const name = card.querySelector(".trail-name").textContent.replace("👁", "").trim();
  card.click();
  T.ok("the panel opened", await TM.until(() => TM.$("#infoPanel").classList.contains("visible")), true, true);
  T.ok("it shows that trail", TM.$("#ipContent h3").textContent.indexOf(name.split(" (")[0]) > -1,
       TM.$("#ipContent h3").textContent.trim(), name);
  T.ok("the card is marked selected", card.classList.contains("selected"), card.className, "selected");
  T.eq("exactly one card is selected anywhere", TM.$$(".trail-card.selected").length, 1);
  T.ok("a yellow selection outline is on the map", TM.map.selectionOutlines() > 0, TM.map.selectionOutlines(), "> 0");

  T.test("the solo button on a card appears only while that card is selected");
  // It is rendered on every card and revealed by CSS, because selecting a trail does not re-render the list.
  T.ok("visible on the selected card", getComputedStyle(card.querySelector(".card-solo-btn")).display !== "none",
       getComputedStyle(card.querySelector(".card-solo-btn")).display, "not none");
  const other = TM.ui.trailCards().find((c) => c !== card);
  T.eq("hidden on an unselected one", getComputedStyle(other.querySelector(".card-solo-btn")).display, "none");

  T.test("the selection survives a re-render and moves to the new card element");
  render();
  await TM.wait(350);
  const again = TM.ui.trailCards().find((c) => c.querySelector(".trail-name").textContent.indexOf(name.split(" (")[0]) > -1);
  T.ok("the card is a new element", again !== card, again !== card, true);
  T.ok("and it is the selected one", again.classList.contains("selected"), again.className, "selected");
  T.eq("still exactly one selected", TM.$$(".trail-card.selected").length, 1);

  T.test("selecting a card does not resize it or move the cards below it");
  // Selecting used to change a card's geometry three separate ways, all of which showed as the list twitching
  // under your finger (user, 2026-08-02): the selected card's border went to 2px, so its box grew 2px; the solo
  // button it reveals was a 20px inline box in a 19px line, worth another 4px; and on a name long enough to fill
  // the line -- every lift card, measured -- that button pushed a word onto a second line, worth 19px. So this
  // takes the LONGEST name in each list, which is the case that reproduced the worst of it, and asserts that
  // nothing about the card's size or its neighbour's position changes at all.
  // The Lifte and Touren sections start collapsed, and a card inside a closed <details> measures 0 by 0 -- which
  // would make every check below pass without measuring anything.
  ["#secLifts", "#secTouren", "#secTrails"].forEach((id) => { const d = TM.$(id); if (d) d.open = true; });
  await TM.wait(250);
  for (const [listName, cards] of [["Trails", TM.ui.trailCards()], ["Lifte", TM.ui.liftCards()], ["Touren", TM.ui.tourCards()]]) {
    if (!cards || cards.length < 2) { T.ok(listName + ": needs two cards", true, "skipped", "skipped"); continue; }
    const worst = cards.reduce((a, b) =>
      a.querySelector(".trail-name").textContent.length > b.querySelector(".trail-name").textContent.length ? a : b);
    const neighbour = cards[cards.indexOf(worst) + 1] || cards[cards.indexOf(worst) - 1];
    TM.$$(".trail-card.selected").forEach((c) => c.classList.remove("selected"));
    await TM.wait(150);
    // Both measurements are RELATIVE to the card itself, never viewport-relative: selecting a card elsewhere
    // calls scrollIntoView({behavior:"smooth"}), and that scroll is still running when this case starts, so
    // absolute tops drift by hundreds of pixels between two reads for reasons that have nothing to do with the
    // selection. The distance from this card's top to its neighbour's is exactly the quantity in question.
    const h0 = worst.getBoundingClientRect().height;
    const gap0 = neighbour.getBoundingClientRect().top - worst.getBoundingClientRect().top;
    worst.classList.add("selected");
    await TM.wait(200);
    const grew = worst.getBoundingClientRect().height - h0;
    const moved = (neighbour.getBoundingClientRect().top - worst.getBoundingClientRect().top) - gap0;
    const btn = worst.querySelector(".card-solo-btn");
    const cr = worst.getBoundingClientRect(), br = btn ? btn.getBoundingClientRect() : null;
    T.ok(listName + ": the card is actually laid out", h0 > 10, Math.round(h0), "> 10px tall");
    T.ok(listName + ": the card keeps its height", Math.abs(grew) < 0.6, Math.round(grew * 10) / 10, "0px");
    T.ok(listName + ": the card below stays put", Math.abs(moved) < 0.6, Math.round(moved * 10) / 10, "0px");
    T.ok(listName + ": and its solo button is inside the card",
         !!br && br.top >= cr.top - 0.6 && br.bottom <= cr.bottom + 0.6,
         br ? [Math.round(br.top - cr.top), Math.round(cr.bottom - br.bottom)] : "no button", "inside");
    worst.classList.remove("selected");
  }

  T.test("no card's name wraps while its line still has room");
  // The user's own observation, and the counterpart to the case above: reserving the solo button's width on the
  // NAME kept the card's size stable but made two of 117 names wrap with room to spare -- on a phone, "Marienthal
  // - Donnersberg Uphill" needed 254px of the 275 it should have had and broke at 249. The reserve lives on the
  // meta row now, which has 100px+ of slack on its tightest card. A name genuinely wider than the line is fine
  // and expected; a name that FITS and wrapped anyway is the bug, so that is what this measures.
  {
    const probe = document.createElement("div");
    probe.className = "trail-name";
    probe.textContent = "X";
    const host = TM.ui.trailCards()[0];
    host.appendChild(probe);
    const oneLine = probe.getBoundingClientRect().height;
    probe.remove();
    // How wide the name would be if it were NOT allowed to break: an off-screen clone of the real element, in the
    // real card, with white-space:nowrap. Measuring the rendered rects instead cannot work and is worth spelling
    // out, because the first version of this case did exactly that and reported two false positives: once the text
    // has wrapped, the widest of its line rects is by definition no wider than the line, so every genuine wrap
    // looks like it "fitted".
    const unbrokenWidth = (n, card) => {
      const clone = n.cloneNode(true);
      clone.querySelectorAll(".card-solo-btn").forEach((b) => b.remove());
      clone.style.cssText = "position:absolute; visibility:hidden; white-space:nowrap; display:inline-block;" +
                            " width:auto; max-width:none; left:0; top:0; padding-right:0;";
      card.appendChild(clone);
      const w = clone.getBoundingClientRect().width;
      clone.remove();
      return w;
    };
    let earlyWraps = [], metaWraps = 0, tightestMetaSpare = Infinity;
    for (const c of TM.ui.trailCards().concat(TM.ui.liftCards())) {
      const n = c.querySelector(".trail-name"), m = c.querySelector(".trail-meta");
      const lines = Math.max(1, Math.round(n.getBoundingClientRect().height / oneLine));
      if (lines > 1) {
        // Compared against the FULL width, not the width left after the padding: the question this case asks is
        // whether the wrap was caused by a reserved slot rather than by a name that is genuinely too long, so a
        // name that would have fitted without the reserve counts as an early wrap even though the layout, given
        // its reserve, broke it correctly.
        const needs = unbrokenWidth(n, c);
        const full = n.clientWidth;
        const forText = full - parseFloat(getComputedStyle(n).paddingRight);
        if (needs <= full + 0.5) {
          earlyWraps.push(n.textContent.trim() + " (needed " + Math.round(needs) + ", had " + Math.round(forText) +
                          " of the row's " + Math.round(full) + ")");
        }
      }
      if (m) {
        const kids = [...m.children].map((k) => k.getBoundingClientRect());
        if (new Set(kids.map((k) => Math.round(k.top))).size > 1) metaWraps++;
        if (kids.length) {
          const spare = m.getBoundingClientRect().right - parseFloat(getComputedStyle(m).paddingRight) -
                        Math.max.apply(null, kids.map((k) => k.right));
          tightestMetaSpare = Math.min(tightestMetaSpare, spare);
        }
      }
    }
    T.ok("the probe measured a real line height", oneLine > 10, Math.round(oneLine), "> 10px");
    T.ok("no name wrapped with room left on its line", earlyWraps.length === 0, earlyWraps.slice(0, 3), "none");
    T.eq("and no meta row wrapped either", metaWraps, 0);
    // The reserve is only free while this stays comfortable. If a future region's meta row gets long enough to
    // eat it, the button needs a new home rather than a smaller slot.
    T.ok("the meta row still has slack for the button's slot", tightestMetaSpare > 20,
         Math.round(tightestMetaSpare), "> 20px spare");
  }

  T.test("selecting a lift drops the trail selection, and vice versa");
  const liftCard = TM.ui.liftCards()[0];
  liftCard.click();
  await TM.until(() => liftCard.classList.contains("selected"));
  T.ok("the lift card is selected", liftCard.classList.contains("selected"), true, true);
  T.eq("and it is the only selected card", TM.$$(".trail-card.selected").length, 1);
  T.ok("the lift panel is open", /🚡/.test(TM.$("#ipContent h3").textContent), TM.$("#ipContent h3").textContent.trim(), "🚡 …");
  TM.ui.trailCards()[0].click();
  await TM.until(() => TM.ui.trailCards()[0].classList.contains("selected"));
  T.ok("selecting a trail again releases the lift", !TM.$$("#liftList .selected").length, TM.$$("#liftList .selected").length, 0);
  T.eq("still exactly one selected", TM.$$(".trail-card.selected").length, 1);

  T.test("hovering a card highlights its line on the map and lets go again");
  closeInfoPanelAndDeselect();
  await TM.wait(200);
  const hoverCard = TM.ui.trailCards()[1];
  const widths = () => TM.map.overlay().map((p) => +p.getAttribute("stroke-width")).filter((w) => w > 5).length;
  const before = widths();
  // pointerenter/pointerleave, not mouseenter/mouseleave: the handler reads the GESTURE off the event
  // (`pointerType`) rather than asking a media query about the device, so a hybrid laptop keeps its real
  // mouse hover. Dispatching a MouseEvent here reaches nothing at all any more, which is the point.
  const point = (type, kind) => hoverCard.dispatchEvent(new PointerEvent(type, { pointerType: kind }));
  point("pointerenter", "mouse");
  await TM.wait(200);
  T.ok("one line got thicker", widths() > before, widths(), "> " + before);
  point("pointerleave", "mouse");
  await TM.wait(250);
  T.eq("and thin again", widths(), before);
  // A tap on a touch screen synthesises the same enter event, so a trail selected from the list came out
  // wearing BOTH the yellow selection outline (right) and the bold hover width (wrong), with no pointer left
  // to move away again (user, 2026-08-16). Runs on this same desktop harness precisely because the rule is
  // per-gesture, not per-device -- a `(hover: hover)` implementation could not be tested from here at all.
  point("pointerenter", "touch");
  await TM.wait(200);
  T.eq("a touch pointer bolds nothing", widths(), before);
  point("pointerleave", "touch");
  await TM.wait(200);
  T.eq("and leaving with one changes nothing either", widths(), before);

  T.test("a selected trail shows its GREEN start marker, not the white dot underneath it");
  // startDot (white) and startMarker (green) sit at the EXACT same coordinate with the same radius, so
  // whichever was added to the map last covers the other -- and the white one is re-added on every zoomend,
  // long after showEndpoints() brought the green pair to the front once. The Ziel marker has no white
  // counterpart, which is why only the Start ever read wrong (user, 2026-08-16, seen in RIDE mode, where the
  // map zooms and pans constantly). The fix removes the overlap instead of re-fighting the z-order, so what
  // this checks is that ONE white dot disappears while the green marker is up and comes back on deselect.
  //
  // Counted as a DELTA, never as "no white dot at the green position": in a bike park several trails share a
  // trailhead, so other trails' dots legitimately sit on that exact coordinate too (measured: 1 there while
  // selected, 2 after deselecting). An absolute check reads that as the bug and fails a correct app.
  //
  // flyToTrailBounds animates for 0.6 s and lands around z16, well above START_DOT_MIN_ZOOM -- but the whole
  // case is silent below that threshold, since no startDot is painted at all. Swapping flyTo for an
  // unanimated setView removes both the wait and the doubt, and is the same trick used to verify the RIDE
  // look-ahead offset (see CLAUDE.md). Restored in the finally, or every later suite inherits it.
  const realFlyTo = L.Map.prototype.flyTo;
  L.Map.prototype.flyTo = function (c, z) { return this.setView(c, z, { animate: false }); };
  try {
    closeInfoPanelAndDeselect();
    await TM.wait(300);
    const dAt = (fill) => TM.map.overlay()
      .filter((p) => (p.getAttribute("fill") || "").toLowerCase() === fill)
      .map((p) => p.getAttribute("d") || "");
    TM.ui.trailCards()[0].click();
    await TM.until(() => TM.$("#infoPanel").classList.contains("visible"));
    await TM.wait(700);
    const greens = dAt("#3fbf5e");
    T.eq("exactly one green start marker is on the map", greens.length, 1);
    const whiteHere = () => dAt("#fff").filter((d) => d === greens[0]).length;
    if (!dAt("#fff").length) {
      T.skip("the map is below START_DOT_MIN_ZOOM, so no startDot is painted to be covered");
    } else {
      const selectedHere = whiteHere(), selectedAll = dAt("#fff").length;
      // The two paths that re-add a startDot while the endpoints are already showing. Both used to put the
      // white dot straight back on top, and the zoomend one is what made this impossible to get rid of.
      updateStartDotVisibility();
      await TM.wait(200);
      T.eq("a zoomend re-add does not put a dot back on the green marker", whiteHere(), selectedHere);
      render();
      await TM.wait(400);
      T.eq("nor does a full render()", whiteHere(), selectedHere);
      T.eq("and the map still has one green start marker", dAt("#3fbf5e").length, 1);
      // Suppressed, not discarded: deselecting has to hand the neutral dot back, or a trail loses its start
      // cue permanently once it has been looked at.
      closeInfoPanelAndDeselect();
      await TM.wait(500);
      T.eq("the green marker goes with the selection", dAt("#3fbf5e").length, 0);
      T.eq("and exactly one white dot returns to its spot", whiteHere(), selectedHere + 1);
      T.eq("one more white dot on the map overall", dAt("#fff").length, selectedAll + 1);
    }
  } finally {
    L.Map.prototype.flyTo = realFlyTo;
  }

  T.test("selecting a trail does not paint its own line through its direction arrows");
  // highlightSelectedTrail brings the selected trail's line to the front so it sits above its neighbours.
  // Since the arrows became filled triangles ON the line (2026-08-20) that also paints the line straight
  // through every one of them -- a coloured stripe across each arrow that never went away, because nothing
  // put them back on top (user, 2026-08-21). Fixed by re-fronting that trail's arrow layer immediately
  // after, NOT by giving the arrows their own pane: a pane costs a whole renderer surface (~40 MB on a
  // phone, see the builder-pane note in CLAUDE.md), moving one node inside the existing one costs nothing.
  //
  // After the fronting, the last unfilled long path in the pane IS the selected trail's line -- only filled
  // things (its endpoint markers and its arrows) are ordered after it -- so "some arrow sits later than
  // that" is the whole property, and it is what a missing re-front would break.
  {
    const arrowsOn = TM.$("#showDirectionArrowsToggle");
    const wereOn = arrowsOn.checked;
    await TM.ui.setSwitch("showDirectionArrowsToggle", true);
    closeInfoPanelAndDeselect();
    await TM.wait(300);
    TM.ui.trailCards()[0].click();
    await TM.until(() => TM.$("#infoPanel").classList.contains("visible"), 3000);
    await TM.wait(800);
    const all = TM.map.overlay();
    const longD = (p) => (p.getAttribute("d") || "").length > 40;
    const lines = all.filter((p) => p.getAttribute("fill") === "none" && longD(p));
    const arrows = all.filter((p) => p.getAttribute("stroke-width") === "1.2" &&
                                     p.getAttribute("fill") !== "none" && longD(p));
    if (!lines.length || !arrows.length) {
      T.skip("no trail line and arrow pair on screen at this view");
    } else {
      const selectedLine = Math.max.apply(null, lines.map((p) => all.indexOf(p)));
      const lastArrow = Math.max.apply(null, arrows.map((p) => all.indexOf(p)));
      T.ok("the selected trail's arrows are drawn after its own line, not under it",
           lastArrow > selectedLine, lastArrow + " vs line at " + selectedLine, "arrow index > line index");
      // The fill carries the difficulty again since 2026-08-21 -- a light tint of the trail's own colour
      // rather than one fixed white, which is the cue the white-only version had given up.
      const tints = ["#a8e8ba", "#a9cdf5", "#f5aa9d", "#c7c7c7"];
      T.ok("and they are filled with a light difficulty tint, not one fixed colour",
           arrows.every((p) => tints.indexOf(p.getAttribute("fill")) > -1),
           [...new Set(arrows.map((p) => p.getAttribute("fill")))].join(","), tints.join(","));
    }
    if (!wereOn) await TM.ui.setSwitch("showDirectionArrowsToggle", false);
  }

  T.test("the sidebar's own scroll-to-top button appears once the list is scrolled, and works");
  // It exists because on a phone the drawer is `position:fixed; top:0; z-index:2500` and covers the header
  // entirely -- so the title, which used to do this job, is unreachable exactly when a long list needs it.
  // A floating button was REJECTED for this on 2026-07-24 in favour of the title, and the phone measurement
  // is what reversed that; it is `position:sticky` as the scroller's last child rather than fixed, so it
  // positions itself against whichever width the sidebar has with no hardcoded geometry.
  {
    const scroller = TM.$("#sidebarScroll"), aside = TM.$("aside"), btn = TM.$("#sidebarTopBtn");
    T.ok("the button exists", !!btn, !!btn, true);
    if (btn && scroller && scroller.scrollHeight > scroller.clientHeight + 200) {
      const was = scroller.scrollTop;
      scroller.scrollTop = 0;
      scroller.dispatchEvent(new Event("scroll"));
      await TM.wait(120);
      T.ok("at the top of the list it is hidden", !aside.classList.contains("scrolled"),
           aside.className, "not scrolled");
      scroller.scrollTop = 400;
      scroller.dispatchEvent(new Event("scroll"));
      await TM.wait(120);
      T.ok("scrolled down it is shown", aside.classList.contains("scrolled"), aside.className, "scrolled");
      T.eq("and it is sticky, not fixed -- so it follows the sidebar's own width",
           getComputedStyle(btn).position, "sticky");
      // The handler asks for `behavior:"smooth"`, which is driven by animation frames -- so in a window that
      // is not being painted (a background tab, this project's own preview pane) the scroll never ARRIVES
      // however long you poll, and asserting arrival would fail a correct app there. Assert the request,
      // which is the contract, and treat arrival as a bonus that is only checked where it can happen.
      let asked = null;
      const realScrollTo = scroller.scrollTo;
      scroller.scrollTo = function (opts) { asked = opts; return realScrollTo.apply(this, arguments); };
      btn.click();
      const arrived = await TM.until(() => scroller.scrollTop < 40, 1500);
      delete scroller.scrollTo;
      T.ok("clicking it asks the list to scroll back to its top",
           !!asked && asked.top === 0, JSON.stringify(asked), '{"top":0,...}');
      if (arrived) {
        T.ok("and it gets there", scroller.scrollTop < 40, scroller.scrollTop, "< 40");
      } else {
        T.ok("(arrival not checked: smooth scrolling needs animation frames this window is not running)",
             true, "skipped", "skipped");
        scroller.scrollTop = 0;
      }
      scroller.scrollTop = was;
      scroller.dispatchEvent(new Event("scroll"));
      await TM.wait(120);
    } else {
      T.skip("the list is not tall enough to scroll in this region/viewport");
    }
  }

  T.test("a filter that hides the selected trail closes its panel and clears everything");
  // Leaving solo engaged for a trail that is no longer shown left every OTHER trail invisibly stuck dimmed.
  const victim = TM.ui.trailCards().find((c) => c.querySelector(".badge.schwarz"));
  if (!victim) {
    T.skip("no schwarz trail in the active regions");
  } else {
    victim.click();
    await TM.until(() => TM.$("#infoPanel").classList.contains("visible"));
    victim.querySelector(".card-solo-btn").click();
    await TM.wait(300);
    T.ok("solo is on", TM.map.dimmedTrails() > 0, TM.map.dimmedTrails(), "> 0");
    await TM.ui.setDiff("schwarz", false);
    await TM.wait(400);
    T.ok("the panel closed", !TM.$("#infoPanel").classList.contains("visible"), false, false);
    T.eq("no card is selected", TM.$$(".trail-card.selected").length, 0);
    T.eq("nothing is left dimmed", TM.map.dimmedTrails(), 0);
    T.eq("and no stray selection outline", TM.map.selectionOutlines(), 0);
    await TM.ui.setDiff("schwarz", true);
    await TM.wait(300);
  }
});
