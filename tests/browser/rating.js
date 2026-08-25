// @suite   rating
// @area    Trail rating and popularity: the two sort axes, the Highlights slider, the crown, the panel row
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches ratingOf, popOf, ratingRowHtml, isHighlight, highlightCut, recomputeHighlightCuts, groupOfSubRegion, syncRatingChrome, showHighlightsOnly, applyHighlightDimming, baselineLineOpacity, clearSolo, HIGHLIGHT_QUANTILE, HIGHLIGHT_MIN_VOTES, RATING_DENSITY_MIN, REGION_RATING_META, rating-chip, rating-chrome, rating-available, tm-crown, card-diff-bar, applyCrownRing, syncCrownRings, ip-rating, rating-unrated-title, trailLabelHtml, appendTrailGroup, TRAIL_SORT_COMPARE
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
  const ratedCards = () => TM.ui.trailCards().filter((c) => /⭐/.test(c.textContent));

  // Put the list into a known state: flat, so ordering is readable in one pass.
  TM.$("#trailViewResetBtn").click();
  await TM.wait(300);
  chip("group", "none").click();
  await TM.wait(300);

  T.test("the rating UI appears as soon as anything is rated -- no coverage threshold");
  // A 35 % coverage gate was built and then removed on the user's call ("Ist doch trotzdem gut zu sehen").
  // What remains is a data requirement, not a policy: with nothing rated there is nothing to sort or dim.
  T.ok("something on screen is rated", ratedTrailCount() > 0, ratedTrailCount(), "> 0");
  T.ok("the Bewertung chip is offered", visible(chip("sort", "rate")), visible(chip("sort", "rate")), true);
  T.ok("the Beliebtheit chip is offered", visible(chip("sort", "pop")), visible(chip("sort", "pop")), true);
  T.ok("and the Highlights switch is offered", visible(TM.$("#highlightsRow")),
       visible(TM.$("#highlightsRow")), true);

  T.test("sorting by rating is best-first, and the unrated simply follow at the end");
  // Die Zwischenueberschrift ("ohne Bewertung" / "ohne Beliebtheitswert") ist am 2026-08-24 entfallen --
  // der Nutzer: "Man sieht ja, dass Flamme bzw. Stern fehlt. Einfach unten an die Liste dranhaengen."
  // Die REIHENFOLGE bleibt damit die einzige Aussage, und genau sie ist hier gepinnt: ohne sie wuerden die
  // unbewerteten Trails mitsortieren, als haetten sie null Sterne (der Vergleicher gibt fuer sie -1 zurueck),
  // also mitten zwischen den bewerteten stehen.
  chip("sort", "rate").click();
  await TM.wait(400);
  T.eq("keine Zwischenueberschrift mehr", TM.$$("#trailList .rating-unrated-title").length, 0);
  const order = TM.ui.names("trailCards");
  const hasStar = TM.ui.trailCards().map((c) => /⭐/.test(c.textContent));
  const lastRated = hasStar.lastIndexOf(true), firstUnrated = hasStar.indexOf(false);
  T.ok("es gibt beide Sorten in dieser Region", lastRated > -1 && firstUnrated > -1,
       [lastRated, firstUnrated], "beide vorhanden");
  T.ok("kein unbewerteter Trail steht zwischen den bewerteten", firstUnrated > lastRated,
       [firstUnrated, lastRated], "erster unbewerteter nach dem letzten bewerteten");
  T.ok("und es sind wirklich viele, kein Rundungsfehler", hasStar.filter((r) => !r).length > 20,
       hasStar.filter((r) => !r).length, "> 20");
  T.eq("the best-rated trail in Finale leads the list", order[0], "Madonna della Guardia");
  T.ok("and the second is one of the other top ones", /Ingegnere|Revenant/.test(order[1] || ""),
       order[1], "Ingegnere/Revenant");

  T.test("sorting by popularity is its own axis, and orders differently from the rating");
  chip("sort", "pop").click();
  await TM.wait(400);
  const popOrder = TM.ui.names("trailCards");
  T.ok("popularity produces a different order than rating", popOrder.join("|") !== order.join("|"),
       popOrder.slice(0, 3), "different from " + order.slice(0, 3).join(","));
  const popRated = TM.ui.trailCards().map((c) => /🔥/.test(c.textContent));
  T.ok("auch hier stehen die ohne Wert hinten", popRated.indexOf(false) > popRated.lastIndexOf(true),
       [popRated.indexOf(false), popRated.lastIndexOf(true)], "ohne Wert zuletzt");
  T.eq("und ebenfalls ohne Zwischenueberschrift", TM.$$("#trailList .rating-unrated-title").length, 0);

  T.test("the slider spans the REAL rating range, not 0..5, and says how many trails it keeps");
  // Finale's Bayesian values run 2.99..4.77, so a 0..5 slider would spend three fifths of its travel doing
  // nothing. The range is the min..max over the displayed regions (the user's design), the default is the
  // pooled top quintile, and the label carries the count because "4,49" alone says nothing.
  await TM.ui.setSwitch("showHighlightsToggle", false);
  await TM.wait(400);
  const sl = TM.$("#highlightSlider");
  const defaultThreshold = sl.value;      // the computed default; put back before leaving the case
  // Visible while the switch is still OFF: it was gated on the switch for a day and the user's first report
  // was that they could not find it. A control that only appears once you have found another control is a
  // control nobody finds.
  T.ok("the slider is there before the switch is touched",
       getComputedStyle(TM.$("#highlightSliderRow")).display !== "none",
       getComputedStyle(TM.$("#highlightSliderRow")).display, "not none");
  T.ok("but it is DISABLED while the switch is off", sl.disabled, sl.disabled, true);
  // Switch, slider and count are ONE row (the user's own layout). Checked by geometry rather than by
  // reading the CSS: the three tops have to sit inside one line box, and the row must be as tall as a
  // normal toggle row plus its own padding -- not twice that. Measured in the 375px drawer as well, which
  // is where "Nur Highlights" + a slider + "4,44 ★ · 26 Trails" is tight (119 + 105 + 89 of 331px).
  const hlRow = TM.$("#highlightsRow").getBoundingClientRect();
  const tops = [".highlight-switch", "#highlightSlider", "#highlightSliderValue"]
      .map(sel => TM.$(sel).getBoundingClientRect().top);
  T.ok("switch, slider and count share one line", Math.max(...tops) - Math.min(...tops) < 8,
       tops.map(Math.round), "within 8px");
  T.ok("so the row stays one line tall", hlRow.height < 34, Math.round(hlRow.height), "< 34");
  // The row must stay inside .toggle-row-group. It did not: as an ordinary flex item it took its CONTENT
  // width (331px) in a 317px container and hung 14px into the sidebar's own right margin, where by design
  // nothing may sit. min-width:0 is what lets it shrink.
  const grp = TM.$("#secMapOptions .toggle-row-group").getBoundingClientRect();
  T.ok("the row does not hang over its container", hlRow.right <= grp.right + 1,
       [Math.round(hlRow.right), Math.round(grp.right)], "inside");
  await TM.ui.setSwitch("showHighlightsToggle", true);
  await TM.wait(600);
  T.ok("the switch enables it", !sl.disabled, sl.disabled, false);
  T.ok("its minimum is a real rating, not 0", parseFloat(sl.min) > 2.5, sl.min, "> 2.5");
  T.ok("its maximum is a real rating, not 5", parseFloat(sl.max) < 5, sl.max, "< 5");
  T.ok("and the range is narrow, as the data is", parseFloat(sl.max) - parseFloat(sl.min) < 2.5,
       (parseFloat(sl.max) - parseFloat(sl.min)).toFixed(2), "< 2.5");
  const label = () => TM.$("#highlightSliderValue").textContent;
  T.ok("the label states the threshold and the count", /\d,\d\d ★ · \d+ Trails?/.test(label()), label(),
       "x,xx ★ · n Trails");
  T.ok("the value shown is the value applied", Math.abs(parseFloat(sl.value) - parseFloat(label().replace(",", "."))) < 0.001,
       [sl.value, label()], "same number");

  T.test("raising the threshold keeps fewer trails, and the map follows");
  const countOf = (s) => TM.ui.num(s.split("·")[1] || "");
  const wide = { n: countOf(label()), dim: TM.map.dimmedTrails() };
  sl.value = (parseFloat(sl.max) - 0.1).toFixed(2);
  sl.dispatchEvent(new Event("input", { bubbles: true }));
  await TM.wait(600);
  const strict = { n: countOf(label()), dim: TM.map.dimmedTrails() };
  T.ok("the count drops", strict.n < wide.n, [wide.n, strict.n], "fewer");
  T.ok("and more of the map is dimmed", strict.dim > wide.dim, [wide.dim, strict.dim], "more");
  // Double-click is the way back to the computed default (the user's own request). The value it restores is
  // highlightRange.def, not "whatever the slider held when the case started" -- otherwise "back" would
  // depend on when you last dragged.
  sl.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
  await TM.wait(500);
  T.eq("a double-click puts the default back", sl.value, defaultThreshold);
  T.ok("and the map follows it", TM.map.dimmedTrails() === wide.dim, [TM.map.dimmedTrails(), wide.dim], "same");
  // Put the threshold back BEFORE switching off, while the slider is still live -- a disabled input fires
  // no events of its own, so a restore after the switch would only work because a test can dispatch what a
  // finger cannot. Toggling the switch deliberately does NOT reset the value (a rider who dialled in 4,6
  // and flicked the switch to glance at the whole map wants 4,6 back), so a strict value left here leaks
  // into every later case. It did: the next case saw 3 bright trails instead of ~22.
  sl.value = defaultThreshold;
  sl.dispatchEvent(new Event("input", { bubbles: true }));
  await TM.wait(400);
  await TM.ui.setSwitch("showHighlightsToggle", false);
  await TM.wait(500);
  T.eq("switching off restores everything", TM.map.dimmedTrails(), 0);
  T.ok("and the slider is greyed out again", sl.disabled, sl.disabled, true);

  T.test("the readout rides INSIDE the track and never hides under the thumb");
  // Both numbers sit in the slide area -- the user compared this against "value beside the slider, count
  // inside the track" and preferred it. It only works because the text SHORTENS itself when its own side
  // gets tight: in the 375px drawer one side of a 170px track offers 78px at half travel while
  // "3,89 ★ · 89 Trails" needs 83, so in that window it drops the word and reads "3,89 ★ · 89".
  // Sampled around the crossover, because that is where both sides are tightest.
  await TM.ui.setSwitch("showHighlightsToggle", true);
  await TM.wait(400);
  const cnt = TM.$("#highlightSliderValue");
  T.ok("the readout sits in the track, not after it",
       cnt.getBoundingClientRect().right <= sl.getBoundingClientRect().right + 1,
       [Math.round(cnt.getBoundingClientRect().right), Math.round(sl.getBoundingClientRect().right)], "inside");
  const lo = parseFloat(sl.min), hi = parseFloat(sl.max);
  let worst = 999, worstAt = null;
  for (const f of [0, 0.25, 0.45, 0.5, 0.55, 0.75, 1]) {
    sl.value = (lo + f * (hi - lo)).toFixed(2);
    sl.dispatchEvent(new Event("input", { bubbles: true }));
    await TM.wait(120);
    const s = sl.getBoundingClientRect(), c = cnt.getBoundingClientRect();
    const frac = (parseFloat(sl.value) - lo) / (hi - lo);
    const thumb = s.left + 7 + frac * (s.width - 14);      // 14px thumb, so its centre travels width-14
    const gap = Math.max(thumb - 7 - c.right, c.left - (thumb + 7));
    if (gap < worst) { worst = gap; worstAt = f; }
  }
  T.ok("clear of the thumb at every position, shortening itself where it must", worst > 0, [Math.round(worst), worstAt], "> 0");
  sl.value = defaultThreshold;
  sl.dispatchEvent(new Event("input", { bubbles: true }));
  await TM.ui.setSwitch("showHighlightsToggle", false);
  await TM.wait(400);

  T.test("the count follows EVERY filter, while the scale stays put");
  // The slider knew only the region filter: recomputeHighlightRange and highlightCount both asked
  // activeRegions.has(t.region) and nothing else, so with only "schwarz" switched on the label still
  // promised 28 trails in Finale while 8 were visible (user, 2026-08-24). The count is a promise about what
  // is about to be seen, so it goes through trailPassesFilters -- the same rule the map loop and the Tour
  // list use, which is what makes the number agree with them by construction.
  // The RANGE deliberately does not follow: it would move under the finger while chips are toggled, and the
  // dialled-in threshold could fall outside the new span. Both halves are checked, because a version that
  // filters everything passes the first half and fails here.
  await TM.ui.setSwitch("showHighlightsToggle", true);
  await TM.wait(500);
  const readCount = () => TM.ui.num(TM.$("#highlightSliderValue").textContent.split("·")[1] || "");
  const before = { n: readCount(), min: sl.min, max: sl.max, value: sl.value };
  for (const d of ["gruen", "blau", "rot"]) await TM.ui.setDiff(d, false);
  await TM.wait(500);
  const after = { n: readCount(), min: sl.min, max: sl.max, value: sl.value };
  T.ok("switching difficulties off lowers the count", after.n < before.n, [before.n, after.n], "fewer");
  T.eq("the scale does not move", [after.min, after.max, after.value], [before.min, before.max, before.value]);
  const listed = TM.ui.trailCards().length;
  T.ok("and the count never exceeds what is actually listed", after.n <= listed, [after.n, listed],
       "count <= listed");
  for (const d of ["gruen", "blau", "rot"]) await TM.ui.setDiff(d, true);
  await TM.wait(400);
  T.eq("switching them back restores the count", readCount(), before.n);
  await TM.ui.setSwitch("showHighlightsToggle", false);
  await TM.wait(300);

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
  const card = TM.ui.cardNamed("trailCards", /Madonna della Guardia/);
  card.click();
  await TM.wait(700);
  // Die Grundlinie erst NACH dem Klick: der Klick fliegt die Karte, und dimmedTrails() zaehlt DOM-Pfade --
  // Leaflet zeichnet nur, was im gepolsterten Ausschnitt liegt. Vor dem Flug gezaehlt haengt die Zahl davon
  // ab, wo die Karte stand, als die Suite anfing, also davon, welche Suite vorher lief: standalone war der
  // Fall gruen, im Bund mit vier anderen las er 382 gegen 191 -- genau das Doppelte, weil im zweiten
  // Ausschnitt doppelt so viele Linien gezeichnet waren. Gemessen und behoben am 2026-08-25; verglichen wird
  // ueber das Solo hinweg, und das ist die Eigenschaft, um die es geht.
  const dimHighlights = TM.map.dimmedTrails();
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

  T.test("a highlight carries the CROWN in its map label, its card and its panel");
  // Aus dem ★ wurde am 2026-08-24 eine Krone -- der Nutzer wollte statt des ausgeschriebenen Worts
  // "Highlight" eine Metapher, und sie gilt jetzt an allen Orten zugleich. Das Label ist weiterhin der
  // strengste Fall, weil es EINMAL beim Bauen gebunden wird: mit den Schwellen nach buildTrailLayer
  // gerechnet kamen alle Labels ungekroent heraus, waehrend das Dimmen laengst funktionierte.
  await TM.ui.setSwitch("showNamesToggle", true);
  await TM.until(() => TM.map.trailLabels().length > 50, 4000);
  const crowned = TM.$$(".trail-label-tooltip .tm-crown");
  T.ok("some labels carry a crown", crowned.length > 5, crowned.length, "> 5");
  T.ok("but far from all of them", crowned.length < TM.map.trailLabels().length / 3,
       crowned.length + " of " + TM.map.trailLabels().length, "a small share");
  const crownNames = crowned.map((s) => s.parentElement.textContent.replace("👑", "").trim());
  T.ok("and the region's best-rated trail is among them", crownNames.includes("Madonna della Guardia"),
       crownNames.slice(0, 5), "includes Madonna della Guardia");
  T.eq("the old ★ is gone from the labels", TM.$$(".trail-label-tooltip .tl-star").length, 0);
  // Dieselbe Krone in der Liste, auf dem Schwierigkeitsbalken der Kachel -- und nur dort, wo sie hingehoert:
  // die Schwelle rastet auf das 0,05-Raster des Reglers ein, und genau daran hing ein Fehler, siehe unten.
  const cardCrowns = TM.ui.trailCards().filter((c) => c.querySelector(".trail-name .tm-crown"));
  T.ok("cards carry it before the name", cardCrowns.length > 3, cardCrowns.length, "> 3");
  // Vor dem Namen, nicht auf dem Schwierigkeitsbalken: die Krone ueber dem Strich war zweimal falsch (auf ihm
  // verdeckte sie ihn, mit Luft darueber blieben von 52px Kachelhoehe nur 30 fuer den Strich), und im
  // Textfluss ist es dieselbe Form, die Kartenlabel und Abschnittsblock schon tragen (Nutzer, 2026-08-25).
  T.eq("and never on the bar itself", TM.$$(".trail-card .card-diff-bar .tm-crown").length, 0);
  const thr = parseFloat(TM.$("#highlightSlider").value);
  const value = (c) => { const m = /⭐\s*([\d,]+)/.exec(c.textContent); return m ? +m[1].replace(",", ".") : null; };
  const wrongCrown = TM.ui.trailCards().filter((c) => {
    const v = value(c), has = !!c.querySelector(".tm-crown");
    return v != null && has !== (v >= thr - 0.001);
  });
  T.eq("and exactly the trails at or above the threshold have it", wrongCrown.length, 0);
  // Karte und Liste muessen DIESELBEN Trails kroenen. Genau das war der Fehler vom 2026-08-24: die Schwelle
  // rastet auf das 0,05-Raster des Reglers ein, Label und Ringe waren aber mit dem ungerasteten Wert gebaut
  // (Bike Kingdom, "Fuerhoernli" 4,32 gegen die gerastete Schwelle 4,33 -- goldene Ringe ohne Krone auf der
  // Kachel). In DIESER Region kann er nicht auftreten, weil die Vorgabe hier zufaellig auf dem Raster liegt;
  // die Zusicherung steht trotzdem hier, weil sie die verletzte Eigenschaft benennt. Siehe MUTATIONS.md.
  const clean = (s) => s.replace(/[👑⬆️🔁👁]/g, "").trim();
  const cardCrownNames = cardCrowns.map((c) => clean(c.querySelector(".trail-name").textContent)).sort();
  const labelCrownNames = crownNames.slice().sort();
  T.eq("map and list crown the same trails",
       labelCrownNames.filter((n) => !cardCrownNames.includes(n)).length, 0);
  // The ⬆️ belongs in the map label too, and did not use to be there (user, 2026-08-24) -- the card and the
  // info panel heading always had it, so an uphill trail's LABEL was the one place that read like a descent.
  // The uphill trail is found through the DOM, not through `lineTrails` -- that is a const inside the app's
  // own try{} and unreachable from here, the same trap RATING_DENSITY_MIN set earlier in this file. The
  // sidebar card already marks uphill trails with .badge-uphill, so it is the honest index.
  const upCard = TM.ui.trailCards().find((c) => c.querySelector(".badge-uphill"));
  if (!upCard) {
    T.skip("no uphill trail in the active regions -- nothing to check");
  } else {
    const upName = upCard.querySelector(".trail-name").textContent.replace(/[👁👑⬆️]/g, "").trim();
    const upLabel = TM.map.trailLabels().find((e) => e.textContent.indexOf(upName) >= 0);
    T.ok("an uphill trail's label is on the map", !!upLabel, upName, "a label for " + upName);
    T.ok("and it carries the ⬆️ badge", /⬆️/.test((upLabel || {}).textContent || ""),
         (upLabel || {}).textContent, "contains ⬆️");
  }
  await TM.ui.setSwitch("showNamesToggle", false);
  await TM.wait(250);

  T.test("no user-visible text names the data source");
  // The user's own rule (2026-08-24): "Auf keinen Fall Trailforks irgendwo erwähnen". The card tooltips
  // said "(Trailforks)" until then. Checked as an ABSENCE across everything the sidebar and the panel
  // actually render, including title attributes, since that is where it had crept in.
  const visibleText = () => {
    const parts = [];
    ["aside", "#infoPanel", "#regionDialog"].forEach((sel) => {
      const root = TM.$(sel);
      if (!root) return;
      parts.push(root.textContent || "");
      root.querySelectorAll("[title]").forEach((e) => parts.push(e.getAttribute("title") || ""));
    });
    return parts.join(" ");
  };
  T.ok("no source named anywhere in the sidebar, panel or region dialog",
       !/trailforks/i.test(visibleText()), (/trailforks/i.exec(visibleText()) || ["none"])[0], "not present");
  T.ok("and no vote count either", !/Stimmen?/.test(visibleText()),
       (/.{0,18}Stimmen?/.exec(visibleText()) || ["none"])[0], "not present");

  T.test("the info panel states the value, the vote count and the popularity -- and NO date");
  TM.ui.cardNamed("trailCards", /Madonna della Guardia/).click();
  await TM.wait(600);
  const row = TM.$("#ipContent .ip-rating");
  T.ok("a rating row is present", !!row, !!row, true);
  const txt = (row || {}).textContent || "";
  // Seit der Info-Box 2.0 steht die Bewertung KOMPAKT in der Metazeile statt in einer eigenen Zeile mit
  // vollem Wortlaut -- auf Wunsch des Nutzers ("Ich bestehe nicht auf dem vollen Text und will lieber alles
  // in einer Zeile"). Zwei Nachkommastellen wie in der Kachel, damit dieselbe Zahl an beiden Orten gleich
  // aussieht; geprueft wird weiter, dass die Zahl da ist und deutsch gesetzt ist.
  T.ok("the value, German style", /⭐ 4,\d\d/.test(txt), txt.slice(0, 40), "⭐ 4,xx");
  // Neither the vote count nor the source appears -- both on the user's instruction, both pinned as an
  // ABSENCE because that is the whole point. `votes` stays in the data; the app itself no longer reads it at all.
  T.ok("no vote count in the panel", !/Stimme/.test(txt), txt, "no Stimmen");
  T.ok("popularity as its own number, never merged into the stars", /🔥 \d+/.test(txt), txt, "🔥 n");
  T.eq("one star glyph and one flame, no doubles",
       [(txt.match(/⭐/g) || []).length, (txt.match(/🔥/g) || []).length], [1, 1]);
  // The harvest date is deliberately absent from the UI (user, 2026-08-23) while staying in the region
  // file's own `ratings` block. Pinned as an ABSENCE, since that is the whole instruction.
  T.ok("and no harvest date in the panel", !/Stand|\d{4}-\d{2}-\d{2}/.test(txt), txt, "no date");
  // Das Highlight steht seit dem 2026-08-24 NICHT mehr als Wort in dieser Zeile, sondern als Krone auf dem
  // Schwierigkeitsbalken der Ueberschrift -- eine Metapher an allen Orten statt eines Worts an einem.
  T.ok("no 'Highlight' wording left in the row", !/Highlight/.test(txt), txt, "kein Wort");
  T.ok("the crown sits before the name in the heading instead",
       !!TM.$("#ipContent h3 .ip-name .tm-crown"), !!TM.$("#ipContent h3 .tm-crown"), true);

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
  T.ok("with no 0 and no stray mark", !/0,00|★|👑/.test(noneTxt), noneTxt, "no zero, no mark");

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
