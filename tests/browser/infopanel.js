// @suite   infopanel
// @area    Info panel: trail, lift, Tour segments, reverse, GPX, elevation chart
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches showTrailInfo, showLiftInfo, buildInfoPanelHtml, categoryBadge, badge-uphill, badge-loop, ip-segment-info, ip-btns, handleInfoPanelClick, applyReversedEndpoints, reversedId, selectedSegmentId, selectTourSegment, openTourRidingLift, downloadTrailGpx, buildElevationSvg, getEleHoverData, handleEleChartHover, hideEleHover, hideEleHoverChart, eleHoverMapMarker, eleHoverTouched, flyToTrailBounds, liftClimb, LIFT_TYPE_LABEL, mapTouchStart, closeInfoPanelAndDeselect, resetAllHoverStyles, applyLineWeight, DIFF_LABEL, syncRideModeChrome, ip-ride-bar, tm-crown, isHighlight, applyCrownRing, ip-diff-bar
// @needs   region=bikekingdom, builder=off
//
// The panel is a custom div rather than a Leaflet popup so nothing covers the trail, which means every piece
// of its behaviour is hand-wired and testable: which buttons exist for a trail vs a lift, what reversing
// swaps, what a clicked Tour segment adds, and the data attributes the chart's hover-sync reads back out of
// its own SVG. The reverse case checks the MAP too -- an earlier version only mirrored the numbers and the
// profile while leaving the Start/Ziel markers where they were, which read as "nothing happened".

TM.add("infopanel", () => typeof showTrailInfo === "function" && TM.ui.cardNamed("liftCards", /Hörnli/) && TM.ui.cardNamed("tourCards", /Biketicket/), async (T) => {

  const panel = () => TM.$("#infoPanel");
  const content = () => TM.$("#ipContent");
  const openFirstTrail = async () => {
    const card = TM.ui.trailCards().find((c) => !c.querySelector(".badge-uphill")) || TM.ui.trailCards()[0];
    card.click();
    await TM.until(() => panel().classList.contains("visible"));
    return card;
  };

  T.test("a trail's panel carries its numbers and its four controls");
  const card = await openFirstTrail();
  const meta = card.querySelector(".trail-meta").textContent.replace(/\s+/g, " ");
  T.ok("the heading names the trail", content().querySelector("h3").textContent.trim().length > 2, true, true);
  T.ok("length and elevation are shown", /km/.test(content().textContent) && /m ⬆/.test(content().textContent), true, true);
  T.ok("the card and the panel agree on the length",
       content().textContent.indexOf(meta.split(" km")[0].trim()) > -1, true, true);
  for (const sel of [".locate-btn", ".solo-btn", ".reverse-btn", ".gpx-download-btn"]) {
    T.ok("has " + sel, !!content().querySelector(sel), !!content().querySelector(sel), true);
  }
  T.ok("and an elevation chart", !!content().querySelector("svg.ele-chart, svg"), true, true);
  // Added 2026-08-13, per the user: the heading carries the same difficulty dot the sidebar card and the
  // map label already use (`.badge <diff>`, see makeTrailCard/trailLabelHtml), so the difficulty is
  // visible without having to already know the trail or read the elevation chart's own line color.
  const cardDiffClass = [...card.querySelector(".badge").classList].find((c) => c !== "badge");
  const panelBadge = content().querySelector("h3 .badge");
  T.ok("the heading has a difficulty badge", !!panelBadge, !!panelBadge, true);
  T.ok("matching the card's own difficulty", panelBadge && panelBadge.classList.contains(cardDiffClass),
       panelBadge && [...panelBadge.classList], "contains " + cardDiffClass);
  T.ok("with a readable title (Sehr leicht/Leicht/Mittel/Schwer)",
       panelBadge && /^(Sehr leicht|Leicht|Mittel|Schwer)$/.test(panelBadge.getAttribute("title")),
       panelBadge && panelBadge.getAttribute("title"), "one of the four German difficulty labels");

  T.test("the reverse button swaps the numbers, mirrors the profile and moves the markers");
  const readUpDown = () => {
    // The stats line reads "<up> m U+2B06 <down> m U+2B07" -- emoji arrows since 2026-08-02, and the dot and
    // slash that used to separate the two figures are now pure space (an empty .ip-gap span, no character at
    // all), so nothing may be required between them. The trailing U+FE0F is optional in both.
    const m = /(\d+)\s*m\s*⬆️?\s*(\d+)\s*m\s*⬇️?/.exec(content().textContent.replace(/\s+/g, " "));
    return m ? [+m[1], +m[2]] : null;
  };
  const before = readUpDown();
  const chartBefore = content().querySelector("svg").getAttribute("data-profile");
  // Start/Ziel markers: green is the start, red the finish, and reversing has to move them to the other end
  // of the SAME line -- an earlier version only mirrored the numbers and the profile, which read as "nothing
  // happened". Compared as a SET of positions, since the DOM order of the markers is not stable across a
  // redraw and there can be more than one green dot on screen (a hovered lift shows its Talstation too).
  const dotSet = (fill) => TM.map.overlay().filter((p) => (p.getAttribute("fill") || "").toLowerCase() === fill)
    .map((p) => (p.getAttribute("d") || "").slice(0, 24)).sort().join("|");
  const greenPos = () => dotSet("#3fbf5e");
  const startBefore = await TM.settle(greenPos);   // the card click flew the map; wait for it to land
  content().querySelector(".reverse-btn").click();
  await TM.wait(400);
  const after = readUpDown();
  T.ok("up and down are swapped", before && after && before[0] === after[1] && before[1] === after[0],
       [before, after], "swapped");
  T.ok("the button shows as active", content().querySelector(".reverse-btn").classList.contains("active"), true, true);
  // The flag is stamped as "1"/"" rather than "true"/"false"; what matters is that it is set at all, since
  // the hover handler only tests for truthiness when converting a chart position back into a map position.
  T.ok("the chart is redrawn as reversed", !!content().querySelector("svg").getAttribute("data-reversed"),
       content().querySelector("svg").getAttribute("data-reversed"), "a truthy value");
  T.ok("the profile itself is mirrored", content().querySelector("svg").getAttribute("data-profile") !== chartBefore,
       true, true);
  const startReversed = await TM.settle(greenPos);
  T.ok("the green start marker moved to the other end", startReversed !== startBefore, startReversed, "!= " + startBefore);
  content().querySelector(".reverse-btn").click();
  await TM.wait(400);
  T.eq("reversing back restores the numbers", readUpDown(), before);
  T.eq("and puts the marker back", await TM.settle(greenPos), startBefore);

  T.test("opening a different trail resets the reversed view");
  content().querySelector(".reverse-btn").click();
  await TM.wait(350);
  T.ok("reversed", content().querySelector(".reverse-btn").classList.contains("active"), true, true);
  const other = TM.ui.trailCards().find((c) => c !== card);
  other.click();
  await TM.until(() => panel().classList.contains("visible"));
  await TM.wait(250);
  T.ok("the new panel is not reversed", !content().querySelector(".reverse-btn").classList.contains("active"),
       content().querySelector(".reverse-btn").className, "not active");

  T.test("the ⬆️ and 🔁 badges never start a line, however the heading wraps");
  // They belong to the NAME, and an ordinary space in front of them is a break opportunity: a long name can
  // then break right before the badge and leave it starting the next line, where the only other thing is the
  // .ip-btns group -- so it reads as belonging to the buttons rather than to the trail (user, 2026-08-21:
  // they must "nie zu den Buttons in die Zeile rutschen"). categoryBadge and the loop badge use a
  // NON-BREAKING space now, the same fix the nine counts elsewhere already use.
  //
  // Swept across panel widths rather than measured at the one the layout happens to use: the failure needs a
  // name that fills the line almost exactly, so it appears only at particular widths. At the desktop's own
  // 345px NONE of Bike Kingdom's badge-bearing trails reproduced it, and a check taken there would have
  // passed against the broken build. Two do reproduce it in 220-440px (measured: 310px and 266px).
  {
    const panelEl = TM.$("#infoPanel");
    const badgeCards = [...TM.ui.trailCards(), ...TM.ui.tourCards()]
      .filter((c) => c.querySelector(".badge-uphill") || /🔁/.test(c.textContent));
    if (!badgeCards.length) {
      T.skip("no uphill or Tour badge in the active regions");
    } else {
      const offenders = [];
      let widthsProbed = 0;
      badgeCards.forEach((c) => {
        c.click();
        const h3 = TM.$("#ipContent h3");
        const badge = h3 && h3.querySelector(".badge-uphill, .badge-loop");
        if (!badge) return;
        for (let w = 220; w <= 440; w++) {
          panelEl.style.width = w + "px";
          widthsProbed++;
          const left = h3.getBoundingClientRect().left + parseFloat(getComputedStyle(h3).paddingLeft || 0);
          if (badge.getBoundingClientRect().left <= left + 3) {
            offenders.push(c.querySelector(".trail-name").textContent.replace(/[👁👑]/g, "").trim().slice(0, 24) + " @" + w + "px");
            break;
          }
        }
        panelEl.style.width = "";
      });
      T.ok("the sweep actually exercised a range of widths", widthsProbed > 200, widthsProbed, "> 200");
      T.eq("no badge ever begins a line", offenders, []);
    }
    panelEl.style.width = "";
    closeInfoPanelAndDeselect();
    await TM.wait(200);
  }

  T.test("a lift's panel is sparser: no reverse, no GPX, no chart");
  const liftCard = TM.ui.liftCards()[0];
  liftCard.click();
  await TM.until(() => /🚡/.test(content().textContent));
  T.ok("names the lift", /🚡/.test(content().querySelector("h3").textContent), true, true);
  T.ok("has a locate button", !!content().querySelector(".locate-btn"), true, true);
  T.ok("has a solo button", !!content().querySelector(".solo-btn"), true, true);
  T.eq("no reverse button", content().querySelectorAll(".reverse-btn").length, 0);
  T.eq("no GPX button", content().querySelectorAll(".gpx-download-btn").length, 0);
  T.eq("no elevation chart", content().querySelectorAll("svg").length, 0);
  T.ok("it states the climb", /\+\d+ m/.test(content().textContent), true, true);
  T.ok("and the type", /bahn|lift|Seil|Gondel|Sessel|Schlepp|Standseil/i.test(content().textContent), true, true);
  T.ok("the locate button addresses a lift", !!content().querySelector(".locate-btn").dataset.liftId, true, true);

  T.test("clicking a Tour keeps the Tour open and its chart is coloured per segment");
  const tourCard = TM.ui.cardNamed("tourCards", /615/) || TM.ui.tourCards()[0];
  tourCard.click();
  await TM.until(() => panel().classList.contains("visible") && content().querySelectorAll("svg").length > 0);
  const svg = content().querySelector("svg");
  T.ok("the Tour badge is in the heading", /🔁/.test(content().querySelector("h3").textContent),
       content().querySelector("h3").textContent.trim(), "contains 🔁");
  T.ok("more than one polyline, i.e. coloured per stretch", svg.querySelectorAll("polyline").length > 1,
       svg.querySelectorAll("polyline").length, "> 1");
  const strokes = [...svg.querySelectorAll("polyline")].map((p) => p.getAttribute("stroke"));
  T.ok("several different colours are used", new Set(strokes).size > 1, [...new Set(strokes)], "> 1 colour");
  T.ok("the connector grey is among them", strokes.indexOf("#5a5a5a") > -1 || strokes.indexOf("#000000") > -1,
       [...new Set(strokes)], "contains a connector or lift colour");

  T.test("clicking one of the Tour's own segments adds a block without losing the Tour");
  const tourName = content().querySelector("h3").textContent.trim();
  const segHit = TM.map.overlay().filter((p) => (p.getAttribute("stroke-opacity") || "1") === "0");
  if (!segHit.length) {
    T.skip("no invisible segment hit-lines found to click");
  } else {
    // Going through the app's own entry point rather than synthesising a Leaflet mouse event on an SVG path.
    const tid = TM.ui.names("tourCards");
    selectTourSegment({ id: "bk_tour_615_blau", name: tourName, loop: true, diff: "blau", len: 1, up: 1, down: 1 },
                      "lift_bk_tgantieni");
    await TM.wait(400);
    T.ok("the panel still shows the Tour", content().querySelector("h3").textContent.indexOf(tourName.split(" 🔁")[0]) > -1,
         content().querySelector("h3").textContent.trim(), tourName);
    const block = content().querySelector(".ip-segment-info");
    T.ok("a segment block appeared", !!block, !!block, true);
    // Guarded: reading .textContent off a null here aborted the whole suite once, turning one failed check
    // into "infopanel: threw" and losing every case after it.
    T.ok("naming the lift that stretch is ridden by", block && /🚡/.test(block.textContent),
         block ? block.textContent.replace(/\s+/g, " ").trim() : null, "a lift");
    T.ok("and the chart highlights that stretch", !!content().querySelector("svg rect"), true, true);

    // ...und die Markierung muss beim Umschalten auf rueckwaerts MITWANDERN (2026-08-24, Nutzer: "Wenn man
    // auf rueckwaerts stellt bleibt die farbige Markierung im Hoehenprofil fuer den Trailabschnitt dort wo
    // sie ist"). Die Segmentfaerbung darunter hat diese Spiegelung immer gemacht, das Rechteck nicht: es
    // wird aus denselben Segmentdaten gebaut, die auf der UNGESPIEGELTEN Achse aufgezeichnet sind.
    // Gemessen wird gegen die Spiegelformel, nicht gegen einen festen Wert -- x' = W - x - Breite.
    const hlRect = () => {
      const r = content().querySelector(".ele-chart rect");
      return r ? { x: +r.getAttribute("x"), w: +r.getAttribute("width") } : null;
    };
    const beforeFlip = hlRect();
    if (beforeFlip) {
      content().querySelector(".reverse-btn").click();
      await TM.wait(500);
      const after = hlRect();
      const wantX = 240 - beforeFlip.x - beforeFlip.w;   // 240 = buildElevationSvg's fixed viewBox width
      T.ok("the highlight moves to the mirrored position", !!after && Math.abs(after.x - wantX) < 1.5,
           after ? [after.x, +wantX.toFixed(1)] : null, "mirrored");
      T.ok("and keeps its width", !!after && Math.abs(after.w - beforeFlip.w) < 1.5,
           after ? [after.w, beforeFlip.w] : null, "same width");
      content().querySelector(".reverse-btn").click();
      await TM.wait(400);
    }

    // An UPHILL component trail has to carry the ⬆️ here too. It is named in four places -- the sidebar
    // card, the map label, the panel's own heading and this block -- and this was the one that dropped it
    // (user, 2026-08-20). Checked against a real uphill segment of a real Tour rather than a synthetic one,
    // since the badge comes from that trail's own `uphill` flag via categoryBadge().
    selectTourSegment({ id: "bk_tour_b2r_schwarz", name: "Biketicket 2 RIDE schwarz", loop: true,
                        diff: "schwarz", len: 1, up: 1, down: 1 }, "bk_aufstieg_praetschli");
    await TM.wait(400);
    const upBlock = content().querySelector(".ip-segment-info");
    T.ok("an uphill segment block appeared", !!upBlock, !!upBlock, true);
    if (upBlock) {
      T.ok("it carries the uphill badge after the trail's name",
           !!upBlock.querySelector(".badge-uphill"),
           upBlock.innerHTML.replace(/\s+/g, " ").slice(0, 120), "a .badge-uphill");
      // After the name, not before it and not inside the <b> -- same order the heading uses.
      const b = upBlock.querySelector("b"), badge = upBlock.querySelector(".badge-uphill");
      T.ok("and it comes after the name, outside the bold",
           !!(b && badge) && (b.compareDocumentPosition(badge) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0 &&
           !b.contains(badge),
           b ? b.textContent.trim() + " | badge inside <b>: " + b.contains(badge) : null, "after, outside");
    }
    // A non-uphill segment must NOT get one, or the check above would pass on a badge printed unconditionally.
    selectTourSegment({ id: "bk_tour_615_blau", name: tourName, loop: true, diff: "blau", len: 1, up: 1, down: 1 },
                      "lift_bk_tgantieni");
    await TM.wait(400);
    const liftBlock = content().querySelector(".ip-segment-info");
    T.eq("a lift stretch gets no uphill badge", liftBlock ? liftBlock.querySelectorAll(".badge-uphill").length : -1, 0);

    // Und die Krone, aus demselben Grund: ein Highlight ist an fuenf Stellen gekroent, und dieser Block war
    // die sechste, an der es fehlte (Nutzer, 2026-08-25). Hier steht sie im Textfluss vor dem Namen statt
    // ueber dem Streifen -- das Hoehenprofil endet direkt darueber. Geprueft wird gegen den Reglerwert und
    // nicht gegen eine feste Zahl, damit der Fall eine Neuernte der Bewertungen uebersteht.
    const segCrown = (tourId, segId) => {
      selectTourSegment({ id: tourId, name: "x", loop: true, diff: "rot", len: 1, up: 1, down: 1 }, segId);
      const b = content().querySelector(".ip-segment-info");
      const m = b ? /⭐\s*([\d,]+)/.exec(b.textContent) : null;
      return { crown: !!(b && b.querySelector(".tm-crown")), rate: m ? +m[1].replace(",", ".") : null };
    };
    const thr = parseFloat(TM.$("#highlightSlider").value);
    const hi = segCrown("bk_tour_616_rot", "bk_alp_staetz");
    await TM.wait(300);
    const lo = segCrown("bk_tour_616_rot", "bk_scalottas_june_huette");
    await TM.wait(300);
    T.ok("a crowned component trail wears its crown in the segment block too",
         hi.rate != null && hi.crown === (hi.rate >= thr - 0.001), [hi, thr], "crown iff at/above the threshold");
    T.ok("and one below the threshold does not", lo.rate != null && !lo.crown, [lo, thr], "no crown");
  }

  T.test("the elevation chart stamps everything its map hover-sync needs");
  TM.ui.trailCards()[0].click();
  await TM.until(() => content().querySelectorAll("svg").length > 0);
  const chart = content().querySelector("svg");
  const need = ["data-trail-id", "data-reversed", "data-profile", "data-dist-max", "data-pad-top",
                "data-pad-bottom", "data-h", "data-ele-min", "data-ele-range"];
  T.eq("no attribute is missing", need.filter((a) => !chart.hasAttribute(a)), []);
  T.ok("the profile parses", Array.isArray(JSON.parse(chart.getAttribute("data-profile"))), true, true);
  T.ok("dist-max is positive", +chart.getAttribute("data-dist-max") > 0, +chart.getAttribute("data-dist-max"), "> 0");
  T.ok("ele-range is positive", +chart.getAttribute("data-ele-range") > 0, +chart.getAttribute("data-ele-range"), "> 0");

  T.test("moving the mouse across the chart puts a dot on the chart and one on the map");
  const rect = chart.getBoundingClientRect();
  const dots = () => TM.map.overlay().filter((p) => (p.getAttribute("fill") || "").toLowerCase() === "#1f5f9e").length;
  const before2 = dots();
  chart.dispatchEvent(new MouseEvent("mousemove", {
    bubbles: true, clientX: Math.round(rect.left + rect.width * 0.5), clientY: Math.round(rect.top + rect.height * 0.5),
  }));
  await TM.wait(300);
  T.ok("a marker appeared on the map", dots() > before2, dots(), "> " + before2);
  // An ELLIPSE, not a circle: the chart's viewBox is stretched non-uniformly (preserveAspectRatio="none"), so a
  // true circle would render as an egg on screen -- fixed 2026-08-04 by making the dot an ellipse whose rx/ry
  // are set per position to cancel the stretch out.
  T.ok("and a dot inside the chart", !!chart.querySelector("ellipse"), !!chart.querySelector("ellipse"), true);
  content().dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));
  await TM.wait(350);
  T.eq("both go away when the mouse leaves the panel", dots(), before2);

  T.test("a tap on the chart LEAVES a dot behind, and a tap elsewhere clears it");
  // On a phone the finger covers the very spot you are trying to read, so the reading is only usable once the
  // finger is gone (user, 2026-08-04). There is no touchend handler for that reason -- which also makes a plain
  // tap set a dot, since touchstart already places one. Driven with real Touch/TouchEvent objects rather than the
  // handler, because "no handler on touchend" is exactly the kind of thing a direct call cannot check.
  const chartDot = () => { const d = chart.querySelector(".ele-hover-dot"); return d && d.style.display !== "none"; };
  const tapChart = (frac) => {
    const r = chart.getBoundingClientRect();
    const t = new Touch({ identifier: 1, target: chart,
                          clientX: Math.round(r.left + r.width * frac), clientY: Math.round(r.top + r.height / 2) });
    chart.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, cancelable: true, touches: [t], targetTouches: [t], changedTouches: [t] }));
    chart.dispatchEvent(new TouchEvent("touchend", { bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: [t] }));
  };
  tapChart(0.4);
  await TM.wait(300);
  const setX = chart.querySelector(".ele-hover-dot").getAttribute("cx");
  T.ok("the tap set a dot on the chart", chartDot(), chartDot(), true);
  T.ok("and one on the map", dots() > before2, dots(), "> " + before2);
  await TM.wait(700);
  T.ok("both are still there after the finger is long gone", chartDot() && dots() > before2,
       [chartDot(), dots()], "[true, > " + before2 + "]");
  tapChart(0.75);
  await TM.wait(300);
  T.ok("a second tap moves it rather than adding another",
       chart.querySelector(".ele-hover-dot").getAttribute("cx") !== setX && dots() === before2 + 1,
       [chart.querySelector(".ele-hover-dot").getAttribute("cx"), setX, dots()], "moved, still one");
  TM.$("#map").dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
  await TM.wait(300);
  T.ok("tapping somewhere else clears both", !chartDot() && dots() === before2,
       [chartDot(), dots()], "[false, " + before2 + "]");

  T.test("tapping a trail opens it even when the platform's own click would not have fired");
  // Reported again by the user AFTER the first fix (a positional mismatch retarget) shipped: "ich schaffe es
  // immer noch genauso, nur auf dem Handy wenn weit rausgezoomt". That is the signature of a SECOND, independent
  // cause with the same symptom -- iOS Safari's documented "first tap on a hover-reactive element only applies
  // :hover, the click needs a second tap" quirk. Our hit-lines qualify (mouseover visibly thickens them), and
  // this has nothing to do with WHERE the finger landed, so a mismatch-only check can never catch it: down can
  // equal up and the native click can still just not happen. This case is exactly that -- identical down and up
  // position, which the first version of this fix would have left completely alone (no mismatch, defer to the
  // platform) and could not even measure, since a scripted touch dispatch never produces the browser's own
  // synthetic click at all. It can only pass now because the app stopped depending on that synthesis entirely:
  // setHover(true) already lives INSIDE each layer's own click handler, so one dispatched click reproduces the
  // whole intended effect regardless of what the platform would or would not have done.
  // The sidebar drawer sits on top of the map on a touch layout, so it must be closed first -- the app is not
  // guaranteed to start in that state here (bootFresh cases elsewhere in a run may leave the toggle either way).
  const aside = TM.$("aside");
  if (aside && aside.classList.contains("open")) { TM.$("#sidebarToggle").click(); await TM.wait(400); }
  {
    // Not "the first wide hit-line in the DOM" and not a path's own bounding-box centre either: a bent/zigzag
    // trail's rectangular bbox centre routinely sits in the empty space BETWEEN two arms of the line, off the
    // path entirely (measured -- a candidate with a perfectly real 242x336 box still resolved to something else
    // at its own centre). The only trustworthy way to find a usable point is the same one the mismatch case
    // below already uses: ask the DOM itself, at a grid of real screen points, which element is actually there.
    const mapBoxForPick = TM.$("#map").getBoundingClientRect();
    let cx = null, cy = null, hitEl = null;
    outerPick:
    for (let y = Math.round(mapBoxForPick.top) + 20; y < mapBoxForPick.bottom - 20; y += 6) {
      for (let x = Math.round(mapBoxForPick.left) + 8; x < mapBoxForPick.right - 8; x += 6) {
        const el = document.elementFromPoint(x, y);
        if (el && el.tagName === "path" && el.classList.contains("leaflet-interactive") &&
            parseFloat(el.getAttribute("stroke-width") || 0) >= 14) {
          cx = x; cy = y; hitEl = el;
          break outerPick;
        }
      }
    }
    if (!hitEl) {
      T.skip("no wide hit-line found by scanning the map to probe");
    } else {
      panel().classList.remove("visible");
      const mapEl = TM.$("#map");
      const t1 = new Touch({ identifier: 30, target: hitEl, clientX: cx, clientY: cy });
      mapEl.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, cancelable: true, touches: [t1], targetTouches: [t1], changedTouches: [t1] }));
      await TM.wait(30);
      const t2 = new Touch({ identifier: 30, target: hitEl, clientX: cx, clientY: cy });   // SAME point, on purpose
      const ev2 = new TouchEvent("touchend", { bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: [t2] });
      mapEl.dispatchEvent(ev2);
      await TM.wait(400);
      T.ok("the platform's own click is suppressed unconditionally", ev2.defaultPrevented, ev2.defaultPrevented, true);
      T.ok("the trail's panel opens anyway", panel().classList.contains("visible"), panel().classList.contains("visible"), true);
    }
  }

  T.test("a tap that settles a few pixels away still opens the trail it started on");
  // The first, narrower cause: browsers hit-test a touch's native click at the TOUCHEND position, not the
  // touchstart one, and a normal tap's finger settles a few pixels in between -- ordinary human behaviour, not a
  // drag. On a densely packed map that drift is often enough to move off the intended trail's hit-line entirely,
  // onto a neighbour's start/end dot or onto empty map: measured on Donnersberg's own boot zoom, a realistic 4px
  // settle mismatched 134 of 400 sampled points. Kept as its own case because it is a DIFFERENT reproduction
  // (deliberately mismatched down/up) than the one above (deliberately identical down/up) -- between them they
  // cover both causes the user's report turned out to have.
  // Rather than trusting one hit-line's own bounding-box centre (a curved/angled path's actual drawn pixels are
  // not reliably under that point, and it is exactly as likely to sit over open sidebar space as over the map),
  // scan the map for a point where a real 4px settle genuinely lands on a DIFFERENT element -- the same method
  // used to first find and quantify this bug.
  const mapBox = TM.$("#map").getBoundingClientRect();
  let found = null;
  outer:
  for (let y = Math.round(mapBox.top) + 20; y < mapBox.bottom - 20; y += 6) {
    for (let x = Math.round(mapBox.left) + 8; x < mapBox.right - 8; x += 6) {
      const down = document.elementFromPoint(x, y);
      if (!down || down.tagName !== "path" || !down.classList.contains("leaflet-interactive") ||
          parseFloat(down.getAttribute("stroke-width") || 0) < 14) continue;
      const up = document.elementFromPoint(x + 4, y + 3);
      if (up !== down) { found = { hit: down, x0: x, y0: y, x1: x + 4, y1: y + 3 }; break outer; }
    }
  }
  if (!found) {
    T.skip("no down/up mismatch found on this map to probe");
  } else {
    const { hit, x0, y0, x1, y1 } = found;
    panel().classList.remove("visible");
    const mapEl = TM.$("#map");
    const t1 = new Touch({ identifier: 21, target: hit, clientX: x0, clientY: y0 });
    mapEl.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, cancelable: true, touches: [t1], targetTouches: [t1], changedTouches: [t1] }));
    await TM.wait(30);
    const upEl = document.elementFromPoint(x1, y1);
    const t2 = new Touch({ identifier: 21, target: upEl, clientX: x1, clientY: y1 });
    const ev2 = new TouchEvent("touchend", { bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: [t2] });
    mapEl.dispatchEvent(ev2);
    await TM.wait(400);
    T.ok("the up-position genuinely differs from the down one (otherwise this proves nothing)",
         upEl !== hit, upEl === hit, "a different element");
    T.ok("the native click was suppressed", ev2.defaultPrevented, ev2.defaultPrevented, true);
    T.ok("the trail's panel opened anyway", panel().classList.contains("visible"), panel().classList.contains("visible"), true);

    T.test("a real drag is left completely alone");
    panel().classList.remove("visible");
    const t3 = new Touch({ identifier: 22, target: hit, clientX: x0, clientY: y0 });
    mapEl.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, cancelable: true, touches: [t3], targetTouches: [t3], changedTouches: [t3] }));
    await TM.wait(30);
    const farEl = document.elementFromPoint(x0, y0 + 60);
    const t4 = new Touch({ identifier: 22, target: farEl, clientX: x0, clientY: y0 + 60 });
    const ev4 = new TouchEvent("touchend", { bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: [t4] });
    mapEl.dispatchEvent(ev4);
    await TM.wait(300);
    T.ok("a 60px movement is not treated as a tap", !ev4.defaultPrevented, ev4.defaultPrevented, false);
    T.ok("and nothing gets opened by it", !panel().classList.contains("visible"), panel().classList.contains("visible"), false);
  }

  T.test("the GPX export offers the app's own geometry");
  // Deliberately not clicking it (that downloads a file); the point is that the exporter finds the trail.
  const names = TM.ui.names("trailCards");
  T.ok("downloadTrailGpx exists and is callable", typeof downloadTrailGpx === "function", true, true);
  T.ok("the button carries the trail id it will export",
       !!content().querySelector(".gpx-download-btn").dataset.id,
       content().querySelector(".gpx-download-btn").dataset.id, "an id");

  T.test("the panel has no ✕ of its own and closing it deselects");
  // The ✕ was removed on 2026-08-02 (user), and with it the one behaviour that distinguished it from a map tap:
  // it closed the panel but LEFT the trail selected. So this case asserts the button is gone AND that the
  // remaining way out still works, because "no ✕" without a working map tap would be a panel you cannot close.
  const openCard = TM.ui.trailCards()[0];
  openCard.click();
  await TM.until(() => panel().classList.contains("visible"));
  T.eq("no ✕ in the panel", panel().querySelectorAll("#ipClose, .ip-close").length, 0);
  T.ok("and the heading keeps no room for one", parseFloat(getComputedStyle(content().querySelector("h3")).paddingRight) < 4,
       Math.round(parseFloat(getComputedStyle(content().querySelector("h3")).paddingRight)), "< 4px");
  closeInfoPanelAndDeselect();   // what a tap on empty map space calls
  await TM.wait(300);
  T.ok("panel closed", !panel().classList.contains("visible"), false, false);
  T.ok("the card is deselected too", !openCard.classList.contains("selected"), openCard.className, "not selected");
  T.eq("and the outline left the map", TM.map.selectionOutlines(), 0);

  T.test("deselecting on a TOUCH tap (no mouseout) also resets a bold line back to normal width");
  // Reported 2026-08-10, on a phone only: tapping a trail bolds its line (setHover(true), fired from inside
  // the hit-line's own click handler -- see the "drive a tap ourselves" note above). Tapping empty map space
  // afterwards dropped the yellow selection outline but left the line fat. Root cause: touch has no mouseout,
  // so setHover(false) -- the thing that would otherwise shrink the line back down -- never ran, and
  // closeInfoPanelAndDeselect's clearSelection() only ever removed the yellow outline, never the width. Not
  // reproducible with a real mouse: a desktop click always physically passes over other map area first,
  // firing a genuine mouseout on the way -- which is exactly why the user saw this only on a phone. Needs a
  // scripted, no-movement touch tap to reproduce at all, same technique as the down/up-mismatch case above.
  const overlayWeights = () => TM.map.overlay()
    .filter((p) => parseFloat(p.getAttribute("stroke-width") || 0) < 14)   // exclude every invisible hit-line
    .map((p) => parseFloat(p.getAttribute("stroke-width") || 0));
  const mapBox2 = TM.$("#map").getBoundingClientRect();
  let hitEl = null, hx = 0, hy = 0;
  outer2:
  for (let y = Math.round(mapBox2.top) + 20; y < mapBox2.bottom - 20; y += 6) {
    for (let x = Math.round(mapBox2.left) + 8; x < mapBox2.right - 8; x += 6) {
      const el = document.elementFromPoint(x, y);
      // stroke-width 22 is specifically a trail/Tour hit-line (buildTrailLayer) -- a lift's is 20, a Tour
      // segment's own per-stretch hit-line is 18 (see docs/trailrunde-feature.md), neither of which this
      // case is about.
      if (el && el.tagName === "path" && el.classList.contains("leaflet-interactive") &&
          el.getAttribute("stroke-width") === "22") { hitEl = el; hx = x; hy = y; break outer2; }
    }
  }
  if (!hitEl) {
    T.skip("no trail/Tour hit-line found on screen to tap");
  } else {
    panel().classList.remove("visible");
    const mapEl2 = TM.$("#map");
    const tt1 = new Touch({ identifier: 30, target: hitEl, clientX: hx, clientY: hy });
    mapEl2.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, cancelable: true, touches: [tt1], targetTouches: [tt1], changedTouches: [tt1] }));
    await TM.wait(30);
    const tt2 = new Touch({ identifier: 30, target: hitEl, clientX: hx, clientY: hy });   // same point: a tap, not a drag
    mapEl2.dispatchEvent(new TouchEvent("touchend", { bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: [tt2] }));
    await TM.wait(300);
    T.eq("the tap selected something", TM.map.selectionOutlines(), 1);
    T.ok("and bolded its line", overlayWeights().some((w) => w > 4), overlayWeights(), "some weight > 4");

    closeInfoPanelAndDeselect();   // what a tap on EMPTY map space calls next
    await TM.wait(300);
    T.eq("the outline is gone", TM.map.selectionOutlines(), 0);
    T.ok("and no line is left stuck bold", !overlayWeights().some((w) => w > 4), overlayWeights(), "none > 4");
  }

  T.test("the four actions are one row UNDER the chart, and the heading is always one line");
  // Rewritten for the Info Box 2.0 (2026-08-24). The old property -- the group sits behind the name and
  // drops WHOLE onto its own line when the name is long -- is deliberately gone: the user's report was that
  // "die Ueberschrift klebt etwas zu sehr an den Buttons", so the group moved out of the heading entirely
  // and sits between the elevation chart and the RIDE bar. What is worth pinning is what that bought: the
  // heading can no longer be two lines (16px in landscape), and the gap above RIDE is carried by the
  // buttons instead of by whitespace.
  let sizes = new Set(), worstOverflow = -1e9, twoLineHeads = 0, wrongOrder = 0, barTooShort = 0;
  for (const c of TM.ui.trailCards().slice(0, 14)) {
    c.click();
    await TM.until(() => panel().classList.contains("visible") && content().querySelector(".ip-btns"));
    const h3 = content().querySelector("h3");
    const grp = content().querySelector(".ip-btns");
    if (h3.querySelector(".ip-btns")) wrongOrder++;          // must no longer live in the heading
    const g = grp.getBoundingClientRect(), p = panel().getBoundingClientRect();
    // Nur die BUTTONS messen: in der Gruppe steht seit dem 2026-08-24 auch das Highlight-Abzeichen, ein
    // 14px hoher Text -- als "Knopf" mitgezaehlt hat es die Hoehen-Gleichheit sofort widerlegt.
    const btns = [...grp.querySelectorAll("button")];
    const first = btns[0].getBoundingClientRect();
    const last = btns[btns.length - 1].getBoundingClientRect();
    if (Math.abs(first.top - last.top) > 1) worstOverflow = 1e9;   // one row, or the overflow check is moot
    worstOverflow = Math.max(worstOverflow, g.right - p.right);
    btns.forEach((b) => sizes.add(Math.round(b.getBoundingClientRect().height)));
    // Ein langer Name DARF umbrechen -- was nicht passieren darf, ist dass der farbige Balken links dabei
    // auf seiner Zeilenhoehe stehen bleibt (Nutzer, 2026-08-24: "Wenn der Trailname zweizeilig wird, waechst
    // der farbige Balken links nicht mit in der Hoehe"). Also wird das Verhaeltnis geprueft, nicht das
    // Umbrechen: der Balken traegt die volle Hoehe der Ueberschrift.
    const name = h3.querySelector(".ip-name");
    const bar = h3.querySelector(".ip-diff-bar");
    if (name && bar && bar.getBoundingClientRect().height + 1 < name.getBoundingClientRect().height) barTooShort++;
    if (name && name.getClientRects().length > 1) twoLineHeads++;
    const chart = content().querySelector(".ele-chart");
    const ride = content().querySelector(".ip-ride-bar");
    if (chart && g.top < chart.getBoundingClientRect().bottom - 1) wrongOrder++;
    if (ride && getComputedStyle(ride).display !== "none" && g.top > ride.getBoundingClientRect().top + 1) wrongOrder++;
  }
  T.ok("every button is the same height", sizes.size === 1, [...sizes], "one height");
  T.ok("the group never leaves the panel", worstOverflow <= 0, Math.round(worstOverflow), "<= 0");
  T.eq("it is out of the heading and sits between chart and RIDE", wrongOrder, 0);
  T.eq("the difficulty bar is as tall as the name, wrapped or not", barTooShort, 0);
  // Nur zur Information -- ein Umbruch ist erlaubt, seit die Knoepfe die Zeile nicht mehr teilen.
  T.ok("headings measured", true, twoLineHeads + " davon zweizeilig", "kein Kriterium");

  T.test("the panel's width does not depend on which trail is open");
  // It was sized by its content (width:max-content), so the same panel came out 320, 338 or 360px wide depending
  // on the name -- and since the touch layout centres it, both its edges moved on every tap (user, 2026-08-02).
  const widths = new Set();
  for (const c of TM.ui.trailCards().slice(0, 8)) {
    c.click();
    await TM.until(() => panel().classList.contains("visible"));
    widths.add(Math.round(panel().getBoundingClientRect().width));
  }
  T.ok("one width across eight trails", widths.size === 1, [...widths], "one width");
  // And the rule itself, because the measurement above can only see the layout this run happens to be in: the
  // variable width lived in the touch/coarse-pointer media block, which a desktop-sized run never applies.
  let touchWidth = null;
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
    for (const rule of rules || []) {
      if (!(rule.media && /coarse|max-width/.test(rule.conditionText || ""))) continue;
      for (const inner of rule.cssRules || []) {
        if (inner.selectorText === "#infoPanel" && inner.style.width) touchWidth = inner.style.width;
      }
    }
  }
  T.ok("and the touch layout's own rule is a fixed width, not max-content",
       touchWidth !== null && !/content/.test(touchWidth), touchWidth, "a length");

  T.test("RIDE is a labelled bar under the chart, and the touch layout's buttons are finger-sized");
  // 2026-08-20: RIDE used to be the LAST and smallest thing in .ip-btns, at 22px, on the layout it is the
  // most important control of. It is a full-width bar under the elevation chart now, and the four glyph
  // buttons grow to 34px on touch. Both are touch-only, so this case cannot measure geometry -- a desktop
  // run has the bar in the DOM and never painted, reporting zeroes -- and reads the rules out of the CSSOM
  // instead, the same technique (and the same reason) as the panel-width check above.
  const ruleValue = (selector, prop, inMedia) => {
    let found = null;
    for (const sheet of document.styleSheets) {
      let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
      for (const rule of rules || []) {
        const isMedia = !!(rule.media && /coarse|max-width/.test(rule.conditionText || ""));
        if (isMedia !== inMedia) continue;
        for (const r of (isMedia ? (rule.cssRules || []) : [rule])) {
          if (r.selectorText === selector && r.style && r.style[prop]) found = r.style[prop];
        }
      }
    }
    return found;
  };
  await openFirstTrail();
  const bar = content().querySelector(".ip-ride-bar");
  T.ok("the panel has a RIDE bar", !!bar, !!bar, true);
  T.ok("it is not in the glyph group any more", !!bar && !bar.closest(".ip-btns"), true, true);
  // Seit der Info-Box 2.0 steht die Knopfzeile zwischen Diagramm und RIDE-Balken -- der Balken folgt also
  // nicht mehr direkt auf .ip-trail, sondern auf .ip-btns. Beides zusammen ist die Reihenfolge, die den
  // Abstand ueber dem Balken traegt (frueher Luft).
  T.ok("it follows the button row, which follows the chart block",
       !!bar && bar.previousElementSibling.classList.contains("ip-btns")
             && bar.previousElementSibling.previousElementSibling.classList.contains("ip-trail"),
       bar ? [bar.previousElementSibling.className, bar.previousElementSibling.previousElementSibling.className] : null,
       "ip-btns after ip-trail");
  T.ok("it says what it does", !!bar && /RIDE/.test(bar.textContent), bar ? bar.textContent.trim() : null, "names RIDE");
  // handleInfoPanelClick and syncRideModeChrome both find this button by .ride-btn, nothing else -- moving it
  // in the DOM must not move it out of their reach.
  T.ok("and still answers to .ride-btn", !!bar && bar.classList.contains("ride-btn"), true, true);
  T.eq("hidden on desktop, exactly as the button it replaced was", ruleValue("#infoPanel .ip-ride-bar", "display", false), "none");
  T.eq("shown on touch", ruleValue("#infoPanel .ip-ride-bar", "display", true), "flex");
  const barH = parseFloat(ruleValue("#infoPanel .ip-ride-bar", "height", false) || "0");
  T.ok("and it is a full touch target tall", barH >= 44, barH, ">= 44");
  // Read from the BASE rule, not the touch block: the 34px sizing moved out of the media query on 2026-08-21
  // when desktop was pulled up to match ("die grösseren Buttons können wir am Desktop nachziehen"), so the
  // touch block no longer restates it and this returned 0. The property worth pinning was never "the touch
  // block makes them bigger" but "they are a full touch target" -- which is now true on both layouts, and is
  // what a regression to 22px would break.
  // Die Knopfzeile haengt seit der Info-Box 2.0 nicht mehr in der Ueberschrift, sondern steht unter dem
  // Hoehenprofil -- der Selektor ist entsprechend ohne h3.
  const btnH = parseFloat(ruleValue("#infoPanel .ip-btns > button", "height", false) || "0");
  T.ok("the glyph buttons are a full touch target, on every layout", btnH >= 34, btnH, ">= 34");
  // The heading's own group must stay ONE row of EQUAL buttons after the move (the case above measures that
  // where it can be painted); here it is only the count that changed, and a stray fifth child would mean the
  // bar was rendered in both places.
  T.eq("the group is four buttons again", content().querySelectorAll(".ip-btns > button").length, 4);

  T.test("the hover dot sits ON the drawn curve, forwards AND reversed");
  // Der Zwischenspeicher fuer die Hover-Daten war nur nach der Trail-ID benannt. ⏪ baut das Panel mit einem
  // gespiegelten `data-profile` neu auf, die ID bleibt aber gleich -- also lieferte er weiter das ALTE
  // Profil, und die Hoehe kam aus der ungespiegelten Kurve (Nutzer, 2026-08-24: "Aber wenn man drueber
  // hovert ... verlaeuft der blaue Punkt nicht wie wenn der Trail vorwaerts gefahren werden wuerde").
  // Gemessen war der Punkt bei 25 % der Breite auf cy 11,8, die gezeichnete Kurve dort auf 31,9.
  // Geprueft wird deshalb der ABSTAND zwischen Punkt und Kurve, nicht der Wert selbst -- der Punkt darf
  // ueberall stehen, solange er auf der Linie liegt, die man gerade sieht.
  await openFirstTrail();
  const curveY = (cx) => {
    const pl = content().querySelector(".ele-chart polyline");
    if (!pl) return null;
    const pts = pl.getAttribute("points").trim().split(/\s+/).map((t) => t.split(",").map(Number));
    let best = pts[0];
    for (const q of pts) if (Math.abs(q[0] - cx) < Math.abs(best[0] - cx)) best = q;
    return best[1];
  };
  const hoverAt = (f) => {
    const svg = content().querySelector(".ele-chart"), r = svg.getBoundingClientRect();
    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true,
      clientX: r.left + r.width * f, clientY: r.top + r.height / 2 }));
    const d = svg.querySelector(".ele-hover-dot");
    return Math.abs(+d.getAttribute("cy") - curveY(+d.getAttribute("cx")));
  };
  const fwd = [0.25, 0.75].map(hoverAt);
  T.ok("forwards the dot is on the curve", Math.max(...fwd) < 2, fwd.map((v) => +v.toFixed(1)), "< 2");
  content().querySelector(".reverse-btn").click();
  await TM.wait(500);
  const rev = [0.25, 0.75].map(hoverAt);
  T.ok("and reversed it is too", Math.max(...rev) < 2, rev.map((v) => +v.toFixed(1)), "< 2");
  content().querySelector(".reverse-btn").click();
  await TM.wait(350);

  T.test("the chart's metre figures are HTML, so the viewBox cannot squash them");
  // The viewBox is a fixed 240 x 48 with preserveAspectRatio="none", so x and y scale by DIFFERENT factors
  // -- and on a phone they scaled in opposite directions: the chart measured 313 x 46, so x grew 1.30x while
  // y SHRANK to 0.96x, and a 7px SVG glyph came out 6.7px tall and 36 % too wide at the same time (user,
  // 2026-08-24: "gequetscht und winzig"). Nothing inside that viewBox can be typeset honestly, so the two
  // figures moved out of it. Checked as an ABSENCE plus a real font size, because either half alone passes
  // against the broken build: SVG text with a bigger font is still stretched, and HTML labels in a 46px box
  // still sit on a squashed curve.
  await openFirstTrail();
  const eleSvg = content().querySelector("svg.ele-chart");
  T.eq("no <text> left inside the stretched viewBox", eleSvg.querySelectorAll("text").length, 0);
  const labels = [...content().querySelectorAll(".ele-wrap .ele-label")];
  T.eq("both figures are there as HTML", labels.length, 2);
  T.ok("and they read as metres", labels.every((l) => /^\d+ m$/.test(l.textContent.trim())),
       labels.map((l) => l.textContent.trim()), "n m");
  const fs = labels.length ? parseFloat(getComputedStyle(labels[0]).fontSize) : 0;
  T.ok("at a real font size, not 7px", fs >= 10, fs, ">= 10");
  T.ok("they do not swallow a tap meant for the chart",
       labels.every((l) => getComputedStyle(l).pointerEvents === "none"),
       labels.map((l) => getComputedStyle(l).pointerEvents), "none");
  // The height is what stops the curve itself being squashed: 46px against a 48-unit viewBox is a y scale
  // BELOW 1, i.e. 1 400 metres of descent compressed into 46 pixels.
  const touchH = parseFloat(ruleValue(".ele-chart", "height", true) || ruleValue(".ele-chart", "height", false) || "0");
  T.ok("and the touch chart is not shorter than the viewBox it draws", touchH >= 48, touchH, ">= 48");

  T.test("in landscape the panel is wide enough that the rating row stays one line");
  // The landscape panel was min(34vw, 230px) and the user's report was that it sat "einen Tick zu hoch".
  // The cause is a WRAP, not the content: measured at 812x375, the rating row of a highlighted trail took
  // two lines at 230px (36px instead of 18) and the heading carried its buttons onto a second line, adding
  // up to a 236px panel; from 290px both are single lines and the panel is 200px. Their own correction was
  // to widen rather than drop the Highlight badge, so the badge is what this measures with.
  // Checked by LAYOUT rather than by reading the rule: a width that is nominally wider still fails if
  // something inside it grew, and the wrap is the thing that costs the height.
  const html = document.documentElement;
  const wasLandscape = html.classList.contains("landscape-compact");
  html.classList.add("landscape-compact");
  await TM.wait(200);
  let rated = null;
  for (const c of TM.ui.trailCards()) {
    c.click();
    await TM.until(() => panel().classList.contains("visible"), 1200);
    await TM.wait(150);
    if (content().querySelector(".ip-rating-badge")) { rated = c; break; }
  }
  if (!rated) {
    TM.skip("no highlighted trail in this region -- nothing to measure");
  } else {
    const row = content().querySelector(".ip-rating");
    T.eq("the rating row is a single line", row.getClientRects().length, 1);
    T.ok("so it stays at one line's height", row.getBoundingClientRect().height < 28,
         Math.round(row.getBoundingClientRect().height), "< 28");
    const w = panel().getBoundingClientRect().width;
    T.ok("and the panel is wider than the 230px that wrapped it", w >= 270, Math.round(w), ">= 270");
  }
  if (!wasLandscape) html.classList.remove("landscape-compact");
});
