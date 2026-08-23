// @suite   rating
// @area    Trail rating and popularity: the two sort axes, the Highlights switch, the ★, the panel row
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches ratingOf, popOf, ratingRowHtml, isHighlight, highlightCut, recomputeHighlightCuts, groupOfSubRegion, ratingDensity, syncRatingChrome, showHighlightsOnly, applyHighlightDimming, baselineLineOpacity, clearSolo, HIGHLIGHT_QUANTILE, HIGHLIGHT_MIN_VOTES, RATING_DENSITY_MIN, REGION_RATING_META, rating-chip, rating-chrome, rating-available, tl-star, ip-rating, rating-unrated-title, trailLabelHtml, appendTrailGroup, TRAIL_SORT_COMPARE
// @needs   region=finale, builder=off
//
// **Needs FINALE, not Bike Kingdom like most suites.** Finale is the only region carrying ratings so far,
// and deliberately so: it is a big destination region (219 trails), which is where the feature is meant to
// help, and Trailforks' coverage there is the best there is -- 80 % of its trails have three votes or more,
// against 34 % on Madeira and 0-3 % in the Pfälzerwald.
//
// Three properties here are the ones worth defending, because each is a way the feature could be quietly
// dishonest rather than broken:
//
//   * AN UNRATED TRAIL IS NOT A BAD TRAIL. 88 of Finale's 219 have no rating, and sorting by rating puts
//     them under their own heading instead of last-as-zero. The comparator really does return -1 for them,
//     so the split in appendTrailGroup is the only thing standing between that and a lie.
//   * THE HIGHLIGHT CUT IS PER REGION, never a fixed number of stars. A 4.3 in Finale and a 4.3 in the
//     Pfälzerwald are different communities with sample sizes a factor of thirty apart.
//   * LEAVING SOLO MUST RETURN TO THE HIGHLIGHT STATE, not to "everything bright". clearSolo() used to
//     restore a hardcoded 0.85 -- the same constant that had already caused one real bug in solo mode.
//
// The ★ case exists because of a real half-working state found while building this: a trail's permanent
// label is bound ONCE at buildTrailLayer time, so with the highlight cut-offs computed after the layers the
// dimming worked and the stars silently did not.

TM.add("rating", () => typeof isHighlight === "function" && TM.ui.cardNamed("trailCards", /Madonna della Guardia/),
       async (T) => {
  const chip = (target, value) => TM.$(`.trail-view-chips[data-target="${target}"] [data-value="${value}"]`);
  const visible = (el) => !!el && getComputedStyle(el).display !== "none";
  const ratedCards = () => TM.ui.trailCards().filter((c) => !/ohne Bewertung/.test(c.textContent));

  // Put the list into a known state: flat, so ordering is readable in one pass.
  TM.$("#trailViewResetBtn").click();
  await TM.wait(300);
  chip("group", "none").click();
  await TM.wait(300);

  T.test("the rating UI only appears where the region actually carries the data");
  // 0.35 spelled out, not read from the app: RATING_DENSITY_MIN is a `const` inside the app's own
  // top-level try{} and genuinely unreachable here (only plain function declarations leak -- same reason
  // the palette suite reads SVG attributes instead of diffColor). Stating the number here is also the
  // stronger test: it is an independent claim about what the threshold should be, not an echo of it.
  T.ok("Finale is dense enough", ratingDensity() >= 0.35, ratingDensity().toFixed(2), ">= 0.35");
  T.ok("the Bewertung chip is offered", visible(chip("sort", "rate")), visible(chip("sort", "rate")), true);
  T.ok("the Beliebtheit chip is offered", visible(chip("sort", "pop")), visible(chip("sort", "pop")), true);
  T.ok("and the Highlights switch is offered", visible(TM.$("#highlightsRow")),
       visible(TM.$("#highlightsRow")), true);

  T.test("sorting by rating is best-first, and unrated trails get their OWN heading, not the bottom");
  chip("sort", "rate").click();
  await TM.wait(400);
  const heads = TM.$$("#trailList .rating-unrated-title").map((e) => e.textContent.trim());
  T.eq("exactly one unrated heading in a flat list", heads.length, 1);
  T.ok("it says so and counts them", /ohne Bewertung \(\d+\)/.test(heads[0] || ""), heads[0], "ohne Bewertung (n)");
  const unratedCount = TM.ui.num(heads[0]);
  T.ok("and that is a real share of the region, not a rounding error", unratedCount > 20,
       unratedCount, "> 20");
  // The rated ones lead, in descending order. Read from the cards' own DOM order.
  const order = TM.ui.names("trailCards");
  const headIdx = TM.$$("#trailList > .hub-group > *").findIndex((e) =>
      e.classList && e.classList.contains("rating-unrated-title"));
  T.ok("the unrated heading sits after the rated cards, not at the top", headIdx > 20, headIdx, "> 20");
  T.eq("the best-rated trail in Finale leads the list", order[0], "Madonna della Guardia");
  T.ok("and the second is one of the other top ones", /Ingegnere|Revenant/.test(order[1] || ""),
       order[1], "Ingegnere/Revenant");

  T.test("sorting by popularity is its own axis, and orders differently from the rating");
  chip("sort", "pop").click();
  await TM.wait(400);
  const popOrder = TM.ui.names("trailCards");
  T.ok("popularity produces a different order than rating", popOrder.join("|") !== order.join("|"),
       popOrder.slice(0, 3), "different from " + order.slice(0, 3).join(","));
  T.ok("its unrated bucket is named for popularity, not rating",
       /ohne Beliebtheitswert/.test((TM.$("#trailList .rating-unrated-title") || {}).textContent || ""),
       (TM.$("#trailList .rating-unrated-title") || {}).textContent, "ohne Beliebtheitswert");

  T.test("the Highlights switch dims everything outside the region's own top fifth");
  chip("sort", "rate").click();
  await TM.wait(300);
  const dimBefore = TM.map.dimmedTrails();
  T.eq("nothing is dimmed to start with", dimBefore, 0);
  await TM.ui.setSwitch("showHighlightsToggle", true);
  await TM.wait(500);
  const dimmed = TM.map.dimmedTrails();
  T.ok("most of the map is dimmed", dimmed > 100, dimmed, "> 100");
  // The bright remainder has to be a small, plausible set -- a fifth of the RATED trails, not of all of
  // them, and not everything with any rating at all.
  const bright = TM.map.overlay().filter((p) => p.getAttribute("stroke-opacity") === "0.9").length;
  T.ok("and a small set stays bright", bright > 5 && bright < 60, bright, "between 5 and 60");
  await TM.ui.setSwitch("showHighlightsToggle", false);
  await TM.wait(500);
  T.eq("switching it off restores every line", TM.map.dimmedTrails(), 0);

  T.test("solo wins over Highlights, and leaving solo returns to the HIGHLIGHT state, not to bright");
  // clearSolo() used to restore a hardcoded 0.85 for every line. With Highlights on that is wrong: the map
  // has two resting states now, and the hardcoded one had already caused a real bug in solo mode itself.
  await TM.ui.setSwitch("showHighlightsToggle", true);
  await TM.wait(400);
  const dimHighlights = TM.map.dimmedTrails();
  const card = TM.ui.cardNamed("trailCards", /Madonna della Guardia/);
  card.click();
  await TM.wait(500);
  applySolo(card.dataset.id || "");
  await TM.wait(400);
  T.ok("during solo almost everything is dimmed", TM.map.dimmedTrails() >= dimHighlights,
       TM.map.dimmedTrails(), ">= " + dimHighlights);
  clearSolo();
  await TM.wait(500);
  T.eq("and leaving solo lands back on the Highlights view, not on an undimmed map",
       TM.map.dimmedTrails(), dimHighlights);
  await TM.ui.setSwitch("showHighlightsToggle", false);
  await TM.wait(400);
  T.eq("finally nothing is dimmed", TM.map.dimmedTrails(), 0);

  T.test("a highlight carries a ★ in its own map label, an ordinary trail does not");
  // The label is bound ONCE at build time, so this also pins the ordering bug it exposed: with the cut-offs
  // computed after buildTrailLayer, every label came out starless while the dimming worked.
  await TM.ui.setSwitch("showNamesToggle", true);
  await TM.until(() => TM.map.trailLabels().length > 50, 4000);
  const starred = TM.$$(".trail-label-tooltip .tl-star");
  T.ok("some labels carry a star", starred.length > 5, starred.length, "> 5");
  T.ok("but far from all of them", starred.length < TM.map.trailLabels().length / 3,
       starred.length + " of " + TM.map.trailLabels().length, "a small share");
  const starNames = starred.map((s) => s.parentElement.textContent.replace("★", "").trim());
  T.ok("and the region's best-rated trail is among them", starNames.includes("Madonna della Guardia"),
       starNames.slice(0, 5), "includes Madonna della Guardia");
  await TM.ui.setSwitch("showNamesToggle", false);
  await TM.wait(250);

  T.test("the info panel states the value, how thin the basis is, and when it was harvested");
  TM.ui.cardNamed("trailCards", /Madonna della Guardia/).click();
  await TM.wait(600);
  const row = TM.$("#ipContent .ip-rating");
  T.ok("a rating row is present", !!row, !!row, true);
  const txt = (row || {}).textContent || "";
  T.ok("it shows the value with a comma, German style", /4,\d\d/.test(txt), txt.slice(0, 40), "4,xx");
  T.ok("exactly ONE star glyph, not two", (txt.match(/★/g) || []).length, 1);
  T.ok("it names the vote count", /\d+ Stimmen/.test(txt), txt, "n Stimmen");
  T.ok("and dates the figure", /Stand \d{4}-\d{2}-\d{2}/.test(txt), txt, "Stand YYYY-MM-DD");
  T.ok("popularity is stated separately, not merged into the stars", /Beliebtheit \d+/.test(txt), txt,
       "Beliebtheit n");

  T.test("an unrated trail says so, and is never shown as a zero");
  chip("sort", "rate").click();
  await TM.wait(400);
  const cards = TM.ui.trailCards();
  const last = cards[cards.length - 1];
  T.ok("there is a trail at the unrated end of the list", !!last, !!last, true);
  last.click();
  await TM.wait(600);
  const noneRow = TM.$("#ipContent .ip-rating");
  T.ok("its panel carries the row", !!noneRow, !!noneRow, true);
  const noneTxt = (noneRow || {}).textContent || "";
  T.ok("and it reads 'noch nicht bewertet'", /noch nicht bewertet/.test(noneTxt), noneTxt, "noch nicht bewertet");
  T.ok("with no 0 and no stray star", !/0,00|★/.test(noneTxt), noneTxt, "no zero, no star");

  T.test("a card shows BOTH numbers whenever it has them, on one line, without resizing");
  // Both, always, independent of the sort axis (the user's call). Two things are pinned here because both
  // were got wrong once: the card must not change height when the sort changes -- an emoji's line box is
  // taller than a text line, which grew every card 52 -> 55px until .trail-meta-rating pinned its
  // line-height -- and the row must stay ONE line, which an earlier version of this check misread by
  // counting element top edges (the emoji span sits 2px higher without wrapping). Measure the CARD, not
  // the tops.
  const cardNamed = () => TM.ui.cardNamed("trailCards", /Ingegnere/);
  const shape = () => {
    const c = cardNamed();
    const m = c.querySelector(".trail-meta");
    return { card: Math.round(c.getBoundingClientRect().height),
             row: Math.round(m.getBoundingClientRect().height),
             items: m.children.length,
             text: [...m.children].map((e) => e.textContent).join(" ") };
  };
  chip("sort", "diff").click();
  await TM.wait(400);
  const rated = shape();
  T.eq("length, elevation, rating and popularity -- four items", rated.items, 4);
  T.ok("the star value is there", /⭐ \d,\d\d/.test(rated.text), rated.text, "⭐ x,xx");
  T.ok("and the flame value too, without sorting by either", /🔥 \d+/.test(rated.text), rated.text, "🔥 n");

  // An unrated trail is the height reference: its card carries two items and must be exactly as tall.
  const unratedCard = TM.ui.trailCards().find((c) => !/⭐/.test(c.textContent));
  T.ok("there is an unrated card to compare against", !!unratedCard, !!unratedCard, true);
  T.eq("a rated card is exactly as tall as an unrated one",
       rated.card, Math.round(unratedCard.getBoundingClientRect().height));

  for (const mode of ["rate", "pop"]) {
    chip("sort", mode).click();
    await TM.wait(400);
    const s2 = shape();
    T.eq(`sorting by ${mode} changes no card height`, s2.card, rated.card);
    T.eq(`and the row is still one line under ${mode}`, s2.row, rated.row);
    T.eq(`and both values are still shown under ${mode}`, s2.items, 4);
  }

  TM.$("#trailViewResetBtn").click();
  await TM.wait(300);
});
