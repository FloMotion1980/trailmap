// @suite   lists
// @area    The three sidebar list sections and their cards
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches makeTrailCard, renderTourList, renderLiftList, render, selectTrail, selectLiftCard, selectCardFor, clearSelection, highlightSelectedTrail, trail-card, lift-card, card-solo-btn, hub-title, region-group-title, card-tint
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

  T.test("the sidebar has exactly three list sections, in order");
  const ids = TM.$$("aside > details").map((d) => d.id);
  T.eq("order", ids, ["secTrails", "secTouren", "secLifts"]);
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
  hoverCard.dispatchEvent(new MouseEvent("mouseenter"));
  await TM.wait(200);
  T.ok("one line got thicker", widths() > before, widths(), "> " + before);
  hoverCard.dispatchEvent(new MouseEvent("mouseleave"));
  await TM.wait(250);
  T.eq("and thin again", widths(), before);

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
