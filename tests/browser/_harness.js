// Shared harness for every browser suite. Paste this FIRST, then any number of suite files -- or let
// `python tests/run.py` bundle the harness and the selected suites into one paste.
//
// WHY A HARNESS AT ALL, when the two original suites each carried their own: the suites kept re-deriving the
// same three things, and two of them got it wrong in ways that cost real time.
//   1. THE BASELINE. A suite that assumes "nothing is selected, every filter is on" is wrong the moment
//      another suite ran first. A case in the lift suite failed for exactly this reason -- closing a panel
//      with the × deliberately KEEPS the map selection, so the previous case left a lift selected and
//      "unmarked on mouseleave" failed against a correct app. TM.baseline() is the fix, and every suite
//      calls it.
//   2. WAITING. Leaflet fades tooltips out, so a synchronous read right after a click sees elements that are
//      already logically gone. Fixed sleeps hid that as flakiness; TM.until() polls instead.
//   3. THE MAP PROBES. What is actually painted is the only honest source for "is this lift hidden", and the
//      pane plus stroke colour/width is what tells a standalone lift from a Tour's own lift stretch. Getting
//      that wrong makes a suite pass for the wrong reason.
//
// WHAT IS REACHABLE FROM HERE. The app's data (`lineLayers`, `LIFTS`, `soloId`, `TRAIL_GEO`, …) is const/let
// inside its top-level try{} block and is NOT reachable from a separately-evaluated script. Plain function
// declarations DO leak to the global scope (sloppy-mode Annex B), so applySolo/render/trailPassesFilters and
// friends can be called -- but `async function boot()` cannot, since Annex B covers plain declarations only.
// Suites that need a fresh boot use TM.bootFresh(), which loads a second copy in an off-screen same-origin
// iframe; that shares localStorage and gives a genuine first painted frame.

(function () {
  "use strict";
  if (window.TM && window.TM.version === 1) return;   // harness pasted twice: keep the first, keep the results

  const TM = {
    version: 1,
    cases: [],
    current: null,
    queue: [],
    _running: false,
    _timer: null,
    _savedState: null,
  };

  // ---------------------------------------------------------------- assertions
  TM.test = function (name) {
    TM.current = { suite: TM._suite, name: name, checks: [], skipped: null };
    TM.cases.push(TM.current);
  };
  TM.ok = function (label, cond, got, want) {
    if (!TM.current) TM.test("(no test declared)");
    TM.current.checks.push({ label: label, pass: !!cond, got: got, want: want });
  };
  TM.eq = function (label, got, want) {
    const same = JSON.stringify(got) === JSON.stringify(want);
    TM.ok(label, same, got, want);
  };
  TM.near = function (label, got, want, tol) {
    TM.ok(label, Math.abs(got - want) <= tol, Math.round(got * 1000) / 1000, want + " ±" + tol);
  };
  TM.skip = function (reason) { if (TM.current) TM.current.skipped = reason; TM.ok("skipped", true, reason, reason); };

  // ---------------------------------------------------------------- waiting
  TM.wait = (ms) => new Promise((r) => setTimeout(r, ms));
  // Poll for a condition instead of guessing a delay. Returns true if it became true, false on timeout --
  // the caller decides whether a timeout is a failure, so a "must NOT happen" check can use it too.
  TM.until = async function (fn, timeout, step) {
    const deadline = Date.now() + (timeout || 2500);
    for (;;) {
      let v = false;
      try { v = fn(); } catch (e) { v = false; }
      if (v) return true;
      if (Date.now() > deadline) return false;
      await TM.wait(step || 40);
    }
  };
  // Wait until a probe stops changing. Any pixel-based reading has to go through this: clicking a card calls
  // flyToTrailBounds, and Leaflet keeps re-projecting every marker for the whole 0.6 s flight -- so a value
  // captured "right after the panel opened" is mid-animation and will not match the same reading later. That
  // is a false failure with a very convincing 11-pixel difference, which is exactly how it first showed up.
  // Requires THREE identical samples and waits out the flight first: flyToTrailBounds runs for 0.6 s, and
  // during it two consecutive samples can match by accident on a slow frame -- which produced a very
  // convincing 11-pixel "the marker did not go back" failure that was purely the map still moving.
  TM.settle = async function (fn, timeout) {
    await TM.wait(700);
    const deadline = Date.now() + (timeout || 4000);
    let last = null, same = 0;
    for (;;) {
      const now = JSON.stringify(fn());
      same = now === last ? same + 1 : 0;
      if (same >= 2) return fn();
      last = now;
      if (Date.now() > deadline) return fn();
      await TM.wait(140);
    }
  };
  // Does this window actually RUN animation frames? A hidden or background tab does not -- and this
  // project's own preview pane measures zero even when fronted. Neither a CSS transition nor Leaflet's
  // animated pan/zoom progresses there, so any case that measures the RESULT of one has to ask first or it
  // reports a correct app as broken: that is what the `controls` fold "flake" and the `bearing` hit-testing
  // skip both were. Measured once per session and cached (the answer cannot change without the window being
  // fronted, and each probe costs 250 ms); TM.paintFrames keeps the count, for a skip message that says how
  // it was decided rather than just asserting it.
  TM.paintFrames = null;
  TM.paints = async function () {
    if (TM.paintFrames !== null) return TM.paintFrames >= 5;
    let frames = 0;
    await new Promise((done) => {
      const t0 = performance.now();
      const tick = () => { frames++; if (performance.now() - t0 < 250) requestAnimationFrame(tick); else done(); };
      requestAnimationFrame(tick);
      setTimeout(done, 1200);          // a window with no frames at all would never call back
    });
    TM.paintFrames = frames;
    return frames >= 5;
  };
  TM.$ = (sel, root) => (root || document).querySelector(sel);
  TM.$$ = (sel, root) => [...(root || document).querySelectorAll(sel)];

  // ---------------------------------------------------------------- map probes
  // A standalone lift puts all three of its strokes in LIFT_BAND_PANE; a Tour puts only its MASK there and
  // its symbol in the overlay pane with the trails. That is what makes the two countable apart.
  const visible = (p) => (p.getAttribute("stroke-opacity") || "1") !== "0";
  TM.map = {
    band: () => TM.$$(".leaflet-liftBand-pane path"),
    overlay: () => TM.$$(".leaflet-overlay-pane path"),
    // one hairline per standalone lift currently on the map
    standaloneLifts: () => TM.map.band().filter((p) => p.getAttribute("stroke") === "#000000" &&
                                                       p.getAttribute("stroke-width") === "1.1" && visible(p)).length,
    // one dotted symbol per lift segment of a Tour
    tourLiftStretches: () => TM.map.overlay().filter((p) => (p.getAttribute("stroke-dasharray") || "").startsWith("1,13") && visible(p)).length,
    liftMasks: () => TM.map.band().filter((p) => p.getAttribute("stroke") === "#cfcfcf" && visible(p)).length,
    dimmedTrails: () => TM.map.overlay().filter((p) => (p.getAttribute("stroke-opacity") || "1") === "0.15").length,
    selectionOutlines: () => TM.map.overlay().filter((p) => (p.getAttribute("stroke") || "").toLowerCase() === "#fff200").length,
    placeLabels: () => TM.$$(".place-label-tooltip").length,
    trailLabels: () => TM.$$(".trail-label-tooltip").filter((e) => !/🚡/.test(e.textContent)),
    liftLabels: () => TM.$$(".trail-label-tooltip").filter((e) => /🚡/.test(e.textContent)),
    markedLabels: () => TM.$$(".trail-label-tooltip.tl-hover"),
    startDots: () => TM.$$(".leaflet-overlay-pane path[stroke='#ffffff'], .leaflet-overlay-pane circle").length,
  };

  // ---------------------------------------------------------------- UI probes
  TM.ui = {
    counts: () => ({
      filter: TM.$("#filterCountLabel").textContent,
      trails: TM.$("#trailCountLabel").textContent,
      touren: TM.$("#tourCountLabel").textContent,
      lifts: TM.$("#liftCountLabel").textContent,
    }),
    num: (s) => { const m = /(\d+)/.exec(s || ""); return m ? +m[1] : null; },
    trailCards: () => TM.$$("#trailList .trail-card"),
    tourCards: () => TM.$$("#tourList .trail-card"),
    liftCards: () => TM.$$("#liftList .lift-card"),
    cardNamed: (list, re) => TM.ui[list]().find((c) => re.test(c.textContent)),
    names: (list) => TM.ui[list]().map((c) => c.querySelector(".trail-name").textContent.replace("👁", "").trim()),
    hubTitles: (sel) => TM.$$(sel + " .hub-title").map((e) => e.textContent.trim()),
    setSwitch: async function (id, on) {
      const box = TM.$("#" + id);
      if (box.checked !== on) { box.click(); await TM.until(() => box.checked === on, 1500); await TM.wait(180); }
    },
    setDiff: async function (d, on) {
      const chip = TM.$('#diffChips [data-diff="' + d + '"]');
      if (chip.classList.contains("active") !== on) { chip.click(); await TM.wait(200); }
    },
    builderMode: async function (on) {
      const isOn = TM.$("#builderSheet").classList.contains("visible");
      if (isOn !== on) { TM.$("#builderModeBtn").click(); await TM.wait(420); }
    },
  };

  // ---------------------------------------------------------------- the baseline
  // Every suite starts from here, so no suite can be broken by what another one left behind. It does NOT
  // touch which regions are active -- loading regions is slow and the region suite owns that.
  TM.baseline = async function () {
    if (TM._savedState === null) TM._savedState = localStorage.getItem("trailmap-active-state-v1");
    if (typeof closeInfoPanelAndDeselect === "function") closeInfoPanelAndDeselect();
    if (typeof clearSolo === "function") clearSolo();
    if (typeof hideEleHover === "function") hideEleHover();
    // Back to north up. Any suite that reads pixels would otherwise inherit a rotated map from whoever ran
    // before it -- and "bearing" sorts first in the bundle, so that is not hypothetical.
    if (typeof setHeadingUp === "function") setHeadingUp(false);
    await TM.ui.builderMode(false);
    for (const d of ["gruen", "blau", "rot", "schwarz"]) await TM.ui.setDiff(d, true);
    await TM.ui.setSwitch("showDownhillToggle", true);
    await TM.ui.setSwitch("showUphillToggle", true);
    await TM.ui.setSwitch("showLoopToggle", true);
    await TM.ui.setSwitch("showLiftsToggle", true);
    await TM.ui.setSwitch("showPlacesToggle", true);
    await TM.ui.setSwitch("showNamesToggle", false);
    await TM.ui.setSwitch("showDirectionArrowsToggle", false);
    await TM.wait(250);
  };

  // ---------------------------------------------------------------- a genuine fresh boot
  // Same origin, so the iframe shares localStorage: write the state to restore, let a second copy of the app
  // come up from nothing, and look at its first painted frame. `mutate` gets {state, builder, put}.
  const STORE = { state: "trailmap-active-state-v1", builder: "trailmap-builder-v1", sections: "trailmap-ui-sections-v1" };
  TM.bootFresh = async function (mutate) {
    const backup = Object.values(STORE).map((k) => [k, localStorage.getItem(k)]);
    if (mutate) {
      mutate({
        state: JSON.parse(localStorage.getItem(STORE.state) || "null"),
        builder: JSON.parse(localStorage.getItem(STORE.builder) || "null"),
        put: (k, v) => (v === null ? localStorage.removeItem(STORE[k]) : localStorage.setItem(STORE[k], JSON.stringify(v))),
      });
    }
    const frame = document.createElement("iframe");
    frame.style.cssText = "position:fixed;left:-9999px;top:0;width:420px;height:420px;border:0";
    frame.src = location.pathname + "?tmboot=" + Date.now();
    document.body.appendChild(frame);
    await new Promise((r) => { frame.onload = r; setTimeout(r, 12000); });
    const doc = () => frame.contentDocument;
    // "Booted" means its own render() has run, not merely that the document loaded.
    await TM.until(() => doc() && (doc().querySelectorAll("#trailList .trail-card").length > 0 ||
                                  doc().getElementById("fatalError").classList.contains("visible")), 12000, 150);
    await TM.wait(500);
    return {
      doc: doc(),
      win: frame.contentWindow,
      shows: (sel) => doc().querySelectorAll(sel).length,
      done: function () {
        frame.remove();       // remove FIRST: the live copy keeps persisting its own state
        backup.forEach(([k, v]) => (v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v)));
      },
    };
  };

  // ---------------------------------------------------------------- suite queue
  TM.add = function (name, needs, fn) {
    // Re-pasting a suite REPLACES its results rather than adding a second copy -- the normal fix-and-re-run
    // loop otherwise reports a growing pile in which the stale failures look current.
    TM.cases = TM.cases.filter((c) => c.suite !== name);
    TM.queue.push({ name: name, needs: needs, fn: fn });
    clearTimeout(TM._timer);
    TM._timer = setTimeout(TM._drain, 80);      // let a whole bundle register before starting
  };
  TM._drain = async function () {
    if (TM._running) return;
    TM._running = true;
    while (TM.queue.length) {
      const s = TM.queue.shift();
      TM._suite = s.name;
      try {
        if (s.needs && !s.needs()) {
          TM.test(s.name + ": preconditions not met");
          TM.ok("suite skipped", true, "skipped", "skipped");
          continue;
        }
        await TM.baseline();
        await s.fn(TM);
      } catch (err) {
        TM.test(s.name + ": threw");
        TM.ok(String(err && err.message || err), false, String(err && err.stack || err).split("\n")[1] || "", "no exception");
      }
    }
    TM._suite = null;
    TM._running = false;
    try { await TM.baseline(); } catch (e) { /* leave the app usable, but never fail on the way out */ }
    TM.report();
  };

  TM.report = function () {
    let passed = 0, failed = 0, checks = 0;
    const bySuite = {};
    const lines = [];
    for (const c of TM.cases) {
      checks += c.checks.length;
      const bad = c.checks.filter((x) => !x.pass);
      bySuite[c.suite] = bySuite[c.suite] || { pass: 0, fail: 0 };
      if (bad.length) {
        failed++; bySuite[c.suite].fail++;
        lines.push("FAIL  [" + c.suite + "] " + c.name);
        for (const b of bad) lines.push("        " + b.label + ": got " + JSON.stringify(b.got) + ", want " + JSON.stringify(b.want));
      } else {
        passed++; bySuite[c.suite].pass++;
        lines.push((c.skipped ? "skip  [" : "ok    [") + c.suite + "] " + c.name + (c.skipped ? "\n        " + c.skipped : ""));
      }
    }
    console.log(lines.join("\n"));
    console.log("\n" + Object.keys(bySuite).map((s) => s + ": " + bySuite[s].pass + "/" + (bySuite[s].pass + bySuite[s].fail)).join("   "));
    console.log(passed + " passed, " + failed + " failed, " + checks + " checks total");
    return { passed: passed, failed: failed, checks: checks };
  };

  window.TM = TM;
  console.log("TM harness ready — paste one or more suites, they run automatically.");
})();
