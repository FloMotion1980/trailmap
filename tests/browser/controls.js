// @suite   controls
// @area    The map control cluster: the segmented column, the readout chip, and what covers what
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches locateCluster, mapControls, liveStatusChip, liveStatusShort, applyLiveStatusOpen, liveStatusOpen, updateLiveStatus, is-detached, showFollowHint, hideFollowHint, followHint, FOLLOW_HINT_MS
// @needs   region=bikekingdom, builder=off
//
// This suite exists because of a bug that every other kind of check would have missed: the readout's fold handle
// was 56% covered by the locate button, so tapping it did nothing. Nothing errored, no state was wrong, the
// element was in the DOM at the right size — a control simply sat in front of it with a higher z-index. The one
// honest test for that is `document.elementFromPoint` at each control's own centre, which is what this asks. The
// cause was the old cluster's deliberate 9px overlaps (a design decision, since reversed), so the checks are
// written against the PROPERTY the user cares about — every control is hittable, nothing overlaps — rather than
// against the container's current shape.
//
// The cluster is touch-only (`display:flex` only under `(max-width:768px),(pointer:coarse)`), so a desktop-sized
// run cannot see it at all. Rather than skip, the geometry cases force it visible for the duration and put the
// stylesheet back afterwards; the layout rules under test are not in that media query.

TM.add("controls", () => typeof updateLiveStatus === "function" && TM.$("#mapControls"), async (T) => {

  const $ = TM.$;
  const box = (el) => el.getBoundingClientRect();
  const cellIds = ["locateBtn", "bearingBtn", "recenterBtn"];

  // Everything below needs the cluster laid out. `visible` on the readout is what tracking would set; nothing
  // here starts the real GPS, which a test cannot do.
  let forced = null;
  const showCluster = async () => {
    forced = document.createElement("style");
    forced.textContent = "#locateCluster{ display:flex !important; }";
    document.head.appendChild(forced);
    $("#liveStatus").classList.add("visible");
    $("#liveStatusShort").textContent = "12m";     // the compact form the segment really renders
    $("#liveStatusText").textContent = "3s 🧭247° 41/38";
    await TM.wait(300);
  };
  const restore = async () => {
    if (forced) { forced.remove(); forced = null; }
    $("#liveStatus").classList.remove("visible");
    $("#locateCluster").classList.remove("is-detached");
    $("#locateBtn").classList.remove("active");
    await TM.wait(150);
  };
  // What is actually on top, which is the whole question. FIVE points, not just the centre: a 20px overlap on a
  // 34px chip leaves the centre exposed and would pass a centre-only check while the top third of the target is
  // dead — verified, that is exactly what a trial mutation did. Returns true, or an identifier for whatever is in
  // the way, so a failure names the culprit instead of just saying "false".
  const hitTest = (el) => {
    const r = box(el);
    const pts = [[0.5, 0.5], [0.3, 0.25], [0.7, 0.25], [0.3, 0.75], [0.7, 0.75]];
    for (const [fx, fy] of pts) {
      const hit = document.elementFromPoint(Math.round(r.left + r.width * fx), Math.round(r.top + r.height * fy));
      if (hit === el || el.contains(hit)) continue;
      const who = hit ? (hit.id || (typeof hit.className === "string" && hit.className) || hit.tagName) : "nothing";
      return who + " at " + Math.round(fx * 100) + "/" + Math.round(fy * 100) + "%";
    }
    return true;
  };

  await showCluster();

  T.test("every control in the cluster can actually be tapped");
  // The regression this suite was written for. It must hold in the detached state too, which is the only one
  // where all three cells exist at once.
  $("#locateCluster").classList.add("is-detached");
  await TM.wait(250);
  for (const id of cellIds.concat(["liveStatusChip"])) {
    const el = $("#" + id);
    T.ok(id + " is on top at its own centre", hitTest(el) === true, hitTest(el), true);
  }
  T.ok("and the chip is not overlapped by the control column",
       box($("#liveStatusChip")).top >= box($("#mapControls")).bottom - 0.5 ||
       box($("#liveStatusChip")).right <= box($("#mapControls")).left + 0.5,
       [Math.round(box($("#liveStatusChip")).top), Math.round(box($("#mapControls")).bottom)],
       "chip clears the column");

  T.test("the cells are one size and share one container, with no overlaps");
  const rects = cellIds.map((id) => box($("#" + id)));
  const sizes = new Set(rects.map((r) => Math.round(r.width) + "x" + Math.round(r.height)));
  T.ok("all three cells are the same size", sizes.size === 1, [...sizes], "one size");
  T.ok("they sit inside the container", rects.every((r) => {
    const c = box($("#mapControls"));
    return r.left >= c.left - 0.5 && r.right <= c.right + 0.5 && r.top >= c.top - 0.5 && r.bottom <= c.bottom + 0.5;
  }), true, true);
  // Three 44px cells in a 134px row/column means they meet, not overlap. Checked pairwise on whichever axis the
  // container stacks on, so this holds in portrait and in the landscape row alike.
  const vertical = rects[0].top < rects[1].top - 1;
  let worstOverlap = 0;
  for (let i = 1; i < rects.length; i++) {
    const gap = vertical ? rects[i].top - rects[i - 1].bottom : rects[i].left - rects[i - 1].right;
    worstOverlap = Math.min(worstOverlap, gap);
  }
  T.ok("no cell overlaps its neighbour", worstOverlap >= -0.5, Math.round(worstOverlap), ">= 0");
  T.ok("the container draws the frame, not the cells",
       cellIds.every((id) => parseFloat(getComputedStyle($("#" + id)).borderTopWidth || 0) <= 1),
       cellIds.map((id) => getComputedStyle($("#" + id)).borderTopWidth), "hairlines at most");

  T.test("the re-centre cell is the last one and only exists while detached");
  // Last on purpose: it is the only conditional cell, so its appearing must not displace a cell you were
  // reaching for. The check is that the cells ABOVE it do not move when it comes and goes.
  $("#locateCluster").classList.remove("is-detached");
  await TM.wait(250);
  const beforeShown = getComputedStyle($("#recenterBtn")).display;
  const anchors = ["locateBtn", "bearingBtn"].map((id) => box($("#" + id)));
  $("#locateCluster").classList.add("is-detached");
  await TM.wait(250);
  const afterShown = getComputedStyle($("#recenterBtn")).display;
  const moved = ["locateBtn", "bearingBtn"].map((id, i) =>
    Math.max(Math.abs(box($("#" + id)).top - anchors[i].top), Math.abs(box($("#" + id)).left - anchors[i].left)));
  T.eq("hidden while attached", beforeShown, "none");
  T.ok("shown while detached", afterShown !== "none", afterShown, "not none");
  T.ok("and the other cells did not move", Math.max(...moved) < 0.6, Math.round(Math.max(...moved)), "0px");
  const r = box($("#recenterBtn")), l = box($("#locateBtn"));
  T.ok("it is last in the stack", vertical ? r.top > l.top : r.left > l.left,
       [Math.round(r.top), Math.round(l.top)], "after the locate cell");
  $("#locateCluster").classList.remove("is-detached");
  await TM.wait(200);

  T.test("the chip folds the details away and stays readable itself");
  const chip = $("#liveStatusChip");
  const wasOpen = !$("#liveStatus").classList.contains("collapsed");
  if (!wasOpen) { chip.click(); await TM.wait(350); }
  const openWidth = box($("#liveStatus")).width;
  chip.click();
  await TM.wait(400);
  const shutWidth = box($("#liveStatus")).width;
  T.ok("folding makes the readout narrower", shutWidth < openWidth - 20,
       [Math.round(shutWidth), Math.round(openWidth)], "narrower");
  // Folded, the readout is exactly as wide as the control column above it -- that is what makes the stack one
  // silhouette rather than a column with a pill hanging off it. Compared against the column and not against the
  // chip's own box: the segment carries a 1px border the chip does not, so "equal to the chip" was off by 2.
  T.ok("and it is exactly as wide as the control column", Math.abs(shutWidth - box($("#mapControls")).width) <= 1,
       [Math.round(shutWidth), Math.round(box($("#mapControls")).width)], "same width");
  T.ok("with no seam between them", Math.abs(box($("#liveStatus")).top - box($("#mapControls")).bottom) <= 1,
       Math.round(box($("#liveStatus")).top - box($("#mapControls")).bottom), "0px");
  T.ok("and their edges flush", Math.abs(box($("#liveStatus")).right - box($("#mapControls")).right) <= 1,
       [Math.round(box($("#liveStatus")).right), Math.round(box($("#mapControls")).right)], "flush");
  T.ok("the accuracy is still on screen", $("#liveStatusShort").textContent.trim().length > 0 &&
       box($("#liveStatusShort")).width > 10, $("#liveStatusShort").textContent, "still shown");
  T.ok("and the chip is still hittable while folded", hitTest(chip) === true, hitTest(chip), true);
  chip.click();
  await TM.wait(400);
  T.ok("tapping again brings the details back", box($("#liveStatus")).width > shutWidth + 20,
       Math.round(box($("#liveStatus")).width), "> " + Math.round(shutWidth + 20));
  if (!wasOpen) { chip.click(); await TM.wait(300); }

  T.test("the accuracy is shown once, not in both halves");
  // It read as a stutter when both carried it: "±12 m 3s 🧭247° 41/38   ±12 m". updateLiveStatus owns this, so
  // drive the real function rather than the DOM — with no fix it says "kein Fix", which is the same contract.
  updateLiveStatus();
  await TM.wait(200);
  const line = $("#liveStatusText").textContent;
  const short = $("#liveStatusShort").textContent;
  // The compact form, because that segment is one control cell wide: "12m", or "–" when there is no fix. The long
  // words ("±12 m", "kein Fix") would need 48px and would widen the stack's silhouette.
  T.ok("the readout segment carries an accuracy field", /^\d+m$|^–$/.test(short.trim()), short, "Nm or –");
  T.ok("and the detail line does not repeat it", !/±|\d+m\b/.test(line), line, "no accuracy in the line");
  T.ok("the compact form fits the cell without widening it",
       $("#liveStatusShort").scrollWidth <= 44, $("#liveStatusShort").scrollWidth, "<= 44px");

  T.test("the hold hint comes with every tap, and never gets in the way");
  // It teaches the one gesture that has no visible control of its own. The rule is deliberately unconditional --
  // an earlier version showed it three times and then never again, which the user rejected: on a gesture you may
  // go weeks without using, this is a reminder, not an onboarding step. So the check is that repetition does NOT
  // wear off, which is the property that regressed once already.
  {
    const hint = $("#followHint");
    const opacity = () => getComputedStyle(hint).opacity;
    hideFollowHint();
    await TM.wait(300);
    T.eq("it is not on screen to begin with", opacity(), "0");
    const shownTimes = [];
    for (let i = 0; i < 4; i++) {
      hideFollowHint();
      await TM.wait(280);
      showFollowHint();
      await TM.wait(280);
      shownTimes.push(opacity());
    }
    T.ok("four taps in a row all show it", shownTimes.every((o) => o === "1"), shownTimes, "all 1");
    T.ok("it says what the gesture does", /[Hh]alten/.test(hint.textContent), hint.textContent.trim(), "mentions Halten");
    T.ok("the locate cell shows the matching fill", $("#locateBtn").classList.contains("hinting"),
         $("#locateBtn").className, "hinting");
    // It sits over the map, so it must not be able to swallow anything -- neither a tap for the map nor one for
    // the button it is pointing at.
    T.eq("it cannot take a tap", getComputedStyle(hint).pointerEvents, "none");
    const r = box(hint);
    const under = document.elementFromPoint(Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2));
    T.ok("so a tap on it reaches what is underneath", under !== hint && !hint.contains(under),
         under ? (under.id || under.className || under.tagName) : "nothing", "not the hint");
    T.ok("it clears the control column", r.right <= box($("#mapControls")).left + 1,
         [Math.round(r.right), Math.round(box($("#mapControls")).left)], "left of the column");
    T.ok("and it fits on one line", r.height < 36, Math.round(r.height), "< 36px");
    hideFollowHint();
    await TM.wait(300);
    T.eq("hiding it works", opacity(), "0");
  }

  await restore();
});
