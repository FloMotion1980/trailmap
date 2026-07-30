// @suite   labels
// @area    Map name labels for trails, Tour segments and lifts
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches applyNameLabels, setLabelHovered, showNames, trailLabelHtml, tl-hover, tl-diff, segmentNameLabels, buildLiftLayer, setLiftHover, applyPlaceVisibility, buildPlaceMarkers
// @needs   region=bikekingdom, builder=off
//
// Labels are where "it looks fine" hides the most. Two shipped bugs behind these cases:
//   * turning "Namen" ON used to REMOVE the only way to read a lift's name -- nothing opened the permanent
//     tooltip, and the hover handler only opened one while the switch was off.
//   * a permanent tooltip re-opens itself every time Leaflet re-adds its layer, so every add path has to
//     decide open-or-closed again; missing one made labels pop open with no hover involved.
// Note the harness waits by polling: Leaflet FADES tooltips out, so a synchronous read right after a toggle
// still sees elements that are logically gone. That produced a false "still there" reading once already.

TM.add("labels", () => typeof applyNameLabels === "function" && TM.ui.cardNamed("liftCards", /Hörnli/) && TM.ui.cardNamed("tourCards", /Biketicket/), async (T) => {

  T.test("with Namen off, no permanent label is on the map");
  T.eq("no trail labels", TM.map.trailLabels().length, 0);
  T.eq("no lift labels", TM.map.liftLabels().length, 0);

  T.test("Namen on shows one label per visible trail and per visible lift");
  const trailsShown = TM.ui.num(TM.ui.counts().trails);
  const liftsShown = TM.map.standaloneLifts();
  await TM.ui.setSwitch("showNamesToggle", true);
  await TM.until(() => TM.map.liftLabels().length > 0, 3000);
  await TM.wait(400);
  T.eq("one per lift", TM.map.liftLabels().length, liftsShown);
  T.ok("and plenty of trail labels", TM.map.trailLabels().length >= trailsShown,
       TM.map.trailLabels().length, ">= " + trailsShown);
  T.ok("a lift label names a lift", TM.map.liftLabels().some((e) => /bahn|Express|Shuttle|Seil|lift/i.test(e.textContent)),
       TM.map.liftLabels()[0].textContent.trim(), "a lift name");

  T.test("a trail label carries its difficulty as a coloured dot");
  // The label often covers the very line whose colour would have told you how hard it is.
  const withDot = TM.map.trailLabels().filter((e) => e.querySelector(".tl-diff"));
  T.ok("labels carry .tl-diff", withDot.length > 0, withDot.length, "> 0");
  const dot = withDot[0].querySelector(".tl-diff");
  T.ok("the dot has a colour", !!getComputedStyle(dot).backgroundColor && getComputedStyle(dot).backgroundColor !== "rgba(0, 0, 0, 0)",
       getComputedStyle(dot).backgroundColor, "a colour");
  T.ok("a lift label starts with the cable icon instead", TM.map.liftLabels().every((e) => /🚡/.test(e.textContent)), true, true);

  T.test("hovering a trail card marks its label in the trail's own colour");
  const card = TM.ui.trailCards().find((c) => c.querySelector(".badge.schwarz")) || TM.ui.trailCards()[0];
  const wantColour = getComputedStyle(card.querySelector(".badge")).backgroundColor;
  card.dispatchEvent(new MouseEvent("mouseenter"));
  await TM.until(() => TM.map.markedLabels().length > 0, 2000);
  T.eq("exactly one label is marked", TM.map.markedLabels().length, 1);
  const marked = TM.map.markedLabels()[0];
  T.ok("its border is the trail's difficulty colour, not a fixed rust",
       marked.style.borderColor.replace(/\s/g, "") === wantColour.replace(/\s/g, ""),
       marked.style.borderColor, wantColour);
  card.dispatchEvent(new MouseEvent("mouseleave"));
  await TM.until(() => TM.map.markedLabels().length === 0, 2000);
  T.eq("the mark is dropped again", TM.map.markedLabels().length, 0);
  T.ok("but the label itself stays open", TM.map.trailLabels().length > 0, TM.map.trailLabels().length, "> 0");

  T.test("the selected trail keeps its label marked without hover");
  card.click();
  await TM.until(() => card.classList.contains("selected"));
  await TM.wait(300);
  T.eq("one marked label", TM.map.markedLabels().length, 1);
  // Hovering something else and leaving must not steal the mark from the selection.
  const other = TM.ui.trailCards().find((c) => c !== card);
  other.dispatchEvent(new MouseEvent("mouseenter"));
  await TM.wait(250);
  other.dispatchEvent(new MouseEvent("mouseleave"));
  await TM.wait(350);
  T.eq("the selected trail is still the marked one", TM.map.markedLabels().length, 1);
  closeInfoPanelAndDeselect();
  await TM.wait(300);
  T.eq("deselecting clears it", TM.map.markedLabels().length, 0);

  T.test("hovering a lift keeps its permanent label and marks it in the lift colour");
  const liftCard = TM.ui.liftCards()[0];
  const liftLabelCount = TM.map.liftLabels().length;
  liftCard.dispatchEvent(new MouseEvent("mouseenter"));
  await TM.until(() => TM.map.markedLabels().length > 0, 2000);
  const m = TM.map.markedLabels()[0];
  T.ok("the marked label is the lift's", /🚡/.test(m.textContent), m.textContent.trim(), "a lift label");
  T.eq("bordered in the lift's own symbol colour", m.style.borderColor, "rgb(0, 0, 0)");
  liftCard.dispatchEvent(new MouseEvent("mouseleave"));
  await TM.wait(400);
  // The old code closed the tooltip unconditionally here, which blanked the very label the switch is for.
  T.eq("the label is still open after the mouse leaves", TM.map.liftLabels().length, liftLabelCount);
  T.eq("only the mark went", TM.map.markedLabels().length, 0);

  T.test("a filter re-add does not pop labels open on its own");
  // Leaflet re-opens a permanent tooltip on every (re-)add; every add path has to close it again when the
  // switch is off, or a hidden-then-shown trail shows its name with no hover.
  await TM.ui.setSwitch("showNamesToggle", false);
  await TM.until(() => TM.map.trailLabels().length === 0, 3000);
  await TM.ui.setDiff("rot", false);
  await TM.wait(300);
  await TM.ui.setDiff("rot", true);
  await TM.wait(400);
  T.eq("no trail label appeared", TM.map.trailLabels().length, 0);
  T.eq("no lift label appeared", TM.map.liftLabels().length, 0);
  await TM.ui.setSwitch("showLiftsToggle", false);
  await TM.wait(300);
  await TM.ui.setSwitch("showLiftsToggle", true);
  await TM.wait(400);
  T.eq("still none after the lifts came back", TM.map.liftLabels().length, 0);

  T.test("solo hides the other trails' labels and keeps the soloed one's");
  await TM.ui.setSwitch("showNamesToggle", true);
  await TM.until(() => TM.map.trailLabels().length > 0, 3000);
  const allLabels = TM.map.trailLabels().length;
  const soloCard = TM.ui.trailCards()[0];
  soloCard.click();
  await TM.until(() => soloCard.classList.contains("selected"));
  soloCard.querySelector(".card-solo-btn").click();
  await TM.wait(500);
  T.ok("far fewer trail labels", TM.map.trailLabels().length < allLabels, TM.map.trailLabels().length, "< " + allLabels);
  T.eq("and no lift labels at all, since the lifts are gone", TM.map.liftLabels().length, 0);
  soloCard.querySelector(".card-solo-btn").click();
  await TM.wait(600);
  T.eq("all trail labels return", TM.map.trailLabels().length, allLabels);
  T.ok("lift labels return with their lifts", TM.map.liftLabels().length > 0, TM.map.liftLabels().length, "> 0");
  closeInfoPanelAndDeselect();
  await TM.ui.setSwitch("showNamesToggle", false);
  await TM.wait(300);

  T.test("place labels are their own switch, independent of Namen");
  const places = TM.map.placeLabels();
  T.ok("places are shown by default", places > 0, places, "> 0");
  await TM.ui.setSwitch("showNamesToggle", true);
  await TM.wait(400);
  T.eq("turning Namen on does not change them", TM.map.placeLabels(), places);
  await TM.ui.setSwitch("showNamesToggle", false);
  await TM.ui.setSwitch("showPlacesToggle", false);
  await TM.until(() => TM.map.placeLabels() === 0, 3000);
  T.eq("their own switch hides them", TM.map.placeLabels(), 0);
  await TM.ui.setSwitch("showPlacesToggle", true);
  await TM.until(() => TM.map.placeLabels() === places, 3000);
  T.eq("and brings them back", TM.map.placeLabels(), places);
});
