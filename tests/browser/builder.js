// @suite   builder
// @area    Tourenbuilder: junctions, direction, clipping, row list
// @standalone
// @files   Trailmap App/index.html
// @touches builderResolve, junctionCandidates, builderTryAdd, renderBuilder, wireBuilderRowDrag, drawBuilderHighlight, builderCoordsOf, builderNameOf, builderCycleConnect, persistBuilder, restoreBuilder, builderTouchLayout, syncBuilderRowFocus, JUNCTION_MAX_GAP_M, categoryBadge
// @needs   region=bikecircus, builder=ON, phone viewport, SELF-CONTAINED (paste alone, it brings its own harness)
//
// Tourenbuilder regression cases — paste into the browser console and run.
//
// WHY THIS FILE EXISTS: the builder's rules were each derived from one concrete ride the user tried, and
// every one of them broke a previous rule when it landed (three separate direction bugs in two days). The
// cases below are those rides. A prose list would drift, so this executes them and checks the numbers.
//
// HOW TO RUN
//   1. python3 -m http.server   from inside "Trailmap App/"   (NOT file://)
//   2. open http://localhost:8000/, activate the region "Bikecircus Saalbach" (bikecircus)
//   3. switch the header button to Tourenbuilder, make sure the sheet is expanded
//   4. paste this whole file into the console
//
// It clears and refills the builder repeatedly, so anything you had assembled is gone afterwards.
//
// DOES IT ACTUALLY BITE? A suite nobody has watched fail proves nothing, so it was validated by mutation.
// Both of these were tried, and the expected failures are listed so the check can be repeated cheaply:
//
//   * in the junction pass, `const somethingAhead = true;`
//     -> 3 tests fail, 12 checks. Also worth knowing: the region-wide case then reports 17 empty stretches,
//        not one, i.e. that rule fixed 16 pairs beyond the one the user reported.
//   * in wireBuilderRowDrag, `slotShift = (from, to) => (to - from) * (rects[idx].height + 4)`
//     -> the drag test fails with "got translateY(-37px), want ≈ translateY(-46px)".
//   * in the drag's auto-scroll ticker, drop the clamp: `scroller.scrollTop = before + step`
//     -> the edge-scroll test fails with "got {held: 1133, max: 275}".
//
// WHY IT DRIVES THE DOM instead of calling the resolver with arguments: `builderItems`, `TRAIL_GEO` and
// `lineTrails` are `let`/`const` inside the app's top-level try{} block, so they are NOT reachable from a
// separately-evaluated script. Function *declarations* do leak to the global scope (sloppy-mode Annex B),
// which is why builderResolve/builderTryAdd/junctionCandidates can be called but their data cannot be
// touched. Adding elements and pressing buttons through the real UI is therefore the only route in — and it
// exercises the click handlers as a side benefit.

(async () => {
  "use strict";
  const REGION = "bikecircus";
  const T = { // ids used below, so a rename fails loudly in one place
    hacklberg: "ow_sh_hacklberg", x: "ow_sh_x", backtoblack: "ow_sh_backtoblack",
    z: "ow_sh_z", sky12: "ow_sh_12er_sky", asitz: "ow_sh_asitz",
    scheeleitn: "ow_sh_scheeleitn", wurzel: "ow_sh_wurzel",
  };
  const L = { sprinter: "lift_bc_a6", steinberg1: "lift_bc_l3", steinberg2: "lift_bc_l4" };

  // ---------- harness ----------
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const results = [];
  let current = null;
  const test = (name) => { current = { name, checks: [], skipped: null }; results.push(current); };
  const ok = (label, cond, got, want) =>
    current.checks.push({ label, pass: !!cond, got, want });
  const eqNum = (label, got, want, tol) =>
    ok(label, Math.abs(got - want) <= tol, round(got), `${want} ±${tol}`);
  const round = (n) => (typeof n === "number" ? Math.round(n * 1000) / 1000 : n);

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];
  const btnByText = (re) => $$("#builderSheet button").find((b) => re.test(b.textContent));

  const clearBuilder = async () => { btnByText(/Leeren/).click(); await wait(30); };
  const add = async (kind, id) => { builderTryAdd(kind, id); await wait(40); };
  const build = async (seq) => { await clearBuilder(); for (const [k, id] of seq) await add(k, id); };
  const flip = async (i) => { $$(".builder-row")[i].querySelector('[data-act="flip"]').click(); await wait(50); };
  const tapConnector = async (i) => { $$(".builder-connector")[i].click(); await wait(50); };

  // Where a resolved stretch starts/ends within its own full geometry. Used to pin down *which* part of a
  // trail is ridden, which is what every direction bug was actually about -- a length alone would not have
  // caught "same 2.38 km, but measured from the wrong end".
  const idxRange = (r) => {
    const full = builderCoordsOf(r.item) || [];
    const c = r.coords || [];
    if (!full.length || !c.length) return [null, null];
    const nearest = (p) => {
      let bi = 0, bd = Infinity;
      for (let k = 0; k < full.length; k++) {
        const d = haversineM(full[k], p);
        if (d < bd) { bd = d; bi = k; }
      }
      return bi;
    };
    return [nearest(c[0]), nearest(c[c.length - 1])];
  };
  const slope = (r) => (r.up > r.down ? "bergauf" : r.down > r.up ? "bergab" : "flach");
  const rowText = (i) => ($$(".bi-main")[i] || {}).textContent?.replace(/\s+/g, " ").trim() || "";
  const pill = (i) => {
    const c = $$(".builder-connector")[i];
    return c ? { text: c.textContent.replace(/\s+/g, " ").trim(), dashed: c.classList.contains("is-off") } : null;
  };
  const glowPaths = () => $$(".leaflet-builder-pane path").length;

  // ---------- preconditions ----------
  if (typeof builderResolve !== "function" || typeof builderTryAdd !== "function") {
    console.error("Not the Trailmap app, or the script block failed to run. Aborting.");
    return;
  }
  if (!$("#builderSheet") || !$("#builderSheet").classList.contains("visible")) {
    console.error("Tourenbuilder mode is off — switch it on in the header first. Aborting.");
    return;
  }
  {   // Are this region's trails actually loaded? builderNameOf falls back to the raw id when they are not,
      // which is how a whole run of these cases once passed against ids that did not exist.
    await build([["trail", T.hacklberg]]);
    const name = builderNameOf({ kind: "trail", id: T.hacklberg });
    if (name === T.hacklberg) {
      console.error(`Region "${REGION}" is not active (or ids changed): ${T.hacklberg} has no name. Aborting.`);
      await clearBuilder();
      return;
    }
  }

  // =====================================================================================
  // 1. DIRECTION FIRST — the clip follows the ride direction; a junction behind you is skipped.
  //    (2026-07-28. Reported twice: "dann fährt er die xline hoch".)
  // =====================================================================================
  test("Back-to-Black → X-Line → Sprinter: X-Line keeps its direction, exit junction skipped");
  {
    await build([["trail", T.backtoblack], ["trail", T.x], ["lift", L.sprinter]]);
    const r = builderResolve();
    eqNum("X-Line ridden km", r[1].len, 2.38, 0.02);
    ok("X-Line runs downhill", slope(r[1]) === "bergab", slope(r[1]), "bergab");
    ok("X-Line index range 311→617", String(idxRange(r[1])) === "311,617", String(idxRange(r[1])), "311,617");
    ok("gap reported as skipped exit", r[1].gapReason === "exit", r[1].gapReason, "exit");
    ok("⤳ shown in row 2", /⤳/.test(rowText(1)), rowText(1), "contains ⤳");
    ok("no empty stretch", !r.some((x) => x.empty), r.map((x) => !!x.empty), "all false");
  }

  test("…same chain, arrow pressed on the X-Line: uphill is allowed, and it CLOSES the gap");
  {
    await build([["trail", T.backtoblack], ["trail", T.x], ["lift", L.sprinter]]);
    await flip(1);
    const r = builderResolve();
    eqNum("X-Line ridden km", r[1].len, 2.95, 0.02);
    ok("X-Line runs uphill", slope(r[1]) === "bergauf", slope(r[1]), "bergauf");
    ok("index range 311→118", String(idxRange(r[1])) === "311,118", String(idxRange(r[1])), "311,118");
    ok("no gap any more", !r[1].gapReason, r[1].gapReason, null);
  }

  test("X-Line → Sprinter: open end follows the trail's own direction (not 'the longer ride')");
  {
    await build([["trail", T.x], ["lift", L.sprinter]]);
    const r = builderResolve();
    eqNum("X-Line ridden km", r[0].len, 1.31, 0.02);
    ok("index range 0→118", String(idxRange(r[0])) === "0,118", String(idxRange(r[0])), "0,118");
    ok("runs downhill", slope(r[0]) === "bergab", slope(r[0]), "bergab");
    eqNum("Sprinter km", r[1].len, 0.63, 0.02);
  }

  test("X-Line → Sprinter → Hacklberg: three elements, unchanged by later rule changes");
  {
    await build([["trail", T.x], ["lift", L.sprinter], ["trail", T.hacklberg]]);
    const r = builderResolve();
    eqNum("X-Line", r[0].len, 1.31, 0.02);
    eqNum("Sprinter", r[1].len, 0.63, 0.02);
    eqNum("Hacklberg", r[2].len, 5.44, 0.02);
    ok("no gaps anywhere", r.every((x) => !x.gapReason), r.map((x) => x.gapReason), "all null");
  }

  test("ScheeLeitn → Wurzel: exit lies behind, so ScheeLeitn rides whole and says so");
  {
    await build([["trail", T.scheeleitn], ["trail", T.wurzel]]);
    const r = builderResolve();
    eqNum("ScheeLeitn km (whole)", r[0].len, 1.70, 0.02);
    ok("ScheeLeitn flags the gap", r[0].gapReason === "exit", r[0].gapReason, "exit");
    eqNum("Wurzel clipped km", r[1].len, 0.11, 0.02);
    ok("Wurzel index range 114→117", String(idxRange(r[1])) === "114,117", String(idxRange(r[1])), "114,117");
  }

  // =====================================================================================
  // 2. TOO FAR APART IS OFF BY DEFAULT
  //    (2026-07-28, user: "zu weit weg, iconnect aus". The fallback in junctionCandidates can never
  //     answer "no junction", so without this every non-touching pair invented one.)
  // =====================================================================================
  test("Hacklberg → Z-Line (1657 m apart): junction off by default, both trails whole");
  {
    await build([["trail", T.hacklberg], ["trail", T.z]]);
    const r = builderResolve();
    eqNum("Hacklberg whole", r[0].len, 5.44, 0.02);
    eqNum("Z-Line whole", r[1].len, 3.68, 0.02);
    ok("junction reported off", r[0].junction.off === true, r[0].junction.off, true);
    ok("…because it is too far", r[0].junction.tooFar === true, r[0].junction.tooFar, true);
    ok("pill is dashed", pill(0).dashed, pill(0), "dashed");
    ok('pill says "aus"', /aus/.test(pill(0).text), pill(0).text, "contains aus");
    // The off pill must show the REAL gap (end of A → start of B), not the candidate's closest approach.
    eqNum("gapOff ≈ end-to-start distance", r[0].junction.gapOff, 1664, 40);
    ok("neither trail clipped", !r[0].clipped && !r[1].clipped, [r[0].clipped, r[1].clipped], "both false");
  }

  test("…one tap forces that junction on: the old clipping behaviour is still reachable");
  {
    await build([["trail", T.hacklberg], ["trail", T.z]]);
    await tapConnector(0);
    const r = builderResolve();
    ok("junction now on", r[0].junction.off === false, r[0].junction.off, false);
    eqNum("Z-Line clipped km", r[1].len, 1.53, 0.02);
    ok("pill shows candidate n/m", /1\/1/.test(pill(0).text), pill(0).text, "contains 1/1");
    eqNum("on pill shows the approach", r[0].junction.dist, 1657, 40);
  }

  test("Hacklberg → 12er Sky-Line (1632 m apart): off by default");
  {
    await build([["trail", T.hacklberg], ["trail", T.sky12]]);
    const r = builderResolve();
    eqNum("Hacklberg whole", r[0].len, 5.44, 0.02);
    eqNum("12er whole", r[1].len, 5.61, 0.02);
    ok("junction off", r[0].junction.off === true, r[0].junction.off, true);
    eqNum("real gap, not the 1632 m approach", r[0].junction.gapOff, 2602, 60);
  }

  test("Steinbergbahn I → II → Asitz-Trail (300 m): off by default, Asitz rides whole");
  {
    await build([["lift", L.steinberg1], ["lift", L.steinberg2], ["trail", T.asitz]]);
    const r = builderResolve();
    eqNum("Asitz whole", r[2].len, 1.53, 0.02);
    ok("not empty any more", !r[2].empty, r[2].empty, false);
    ok("Asitz junction off", r[1].junction.off === true, r[1].junction.off, true);
    // A lift→lift junction clips nothing, so it must not offer a control at all.
    ok("lift→lift junction has no control", r[0].junction.clips === false, r[0].junction.clips, false);
    ok("exactly one pill for three elements", $$(".builder-connector").length === 1,
       $$(".builder-connector").length, 1);
    // 300 m at the closest approach, but the station is near the trail's END: the real gap is ~1.6 km.
    eqNum("real gap ≈ 1609 m", r[1].junction.gapOff, 1600, 60);
    eqNum("closest approach ≈ 300 m", r[1].junction.dist, 300, 30);
  }

  test("…Asitz with the junction forced on: still whole, NOT an empty stretch");
  {
    await build([["lift", L.steinberg1], ["lift", L.steinberg2], ["trail", T.asitz]]);
    await tapConnector(0);
    const r = builderResolve();
    eqNum("Asitz still whole", r[2].len, 1.53, 0.02);
    ok("not empty", !r[2].empty, r[2].empty, false);
    ok("junction marked unusable", r[1].junction.unmade === true, r[1].junction.unmade, true);
  }

  // =====================================================================================
  // 3. A JUNCTION IS ONLY USED IF BOTH SIDES CAN HONOUR IT
  //    (2026-07-28. Z-Line → 12er: a genuine 108 m junction, but it joins the Z-Line's START to the
  //     12er's END, i.e. it describes the ride in the other order.)
  // =====================================================================================
  test("Z-Line → 12er Sky-Line: real 108 m junction, unusable in this order");
  {
    await build([["trail", T.z], ["trail", T.sky12]]);
    const r = builderResolve();
    const c = junctionCandidates(builderCoordsOf(r[0].item), builderCoordsOf(r[1].item));
    eqNum("candidate really is close", c[0].dist, 108, 15);
    ok("…and it is NOT filtered as too far", r[0].junction.tooFar !== true, r[0].junction.tooFar, "not true");
    ok("candidate joins Z-Line start to 12er end", c[0].ia === 0 && c[0].ib === 199,
       [c[0].ia, c[0].ib], [0, 199]);
    eqNum("Z-Line whole", r[0].len, 3.68, 0.02);
    eqNum("12er whole", r[1].len, 5.61, 0.02);
    ok("no empty stretch (was ∅ before)", !r[1].empty, r[1].empty, false);
    ok("gap reason is the next element", r[0].gapReason === "next", r[0].gapReason, "next");
    ok("junction marked unmade", r[0].junction.unmade === true, r[0].junction.unmade, true);
    ok("pill dashed but keeps its numbers", pill(0).dashed && /108 m/.test(pill(0).text),
       pill(0), "dashed + 108 m");
    ok("both stretches drawn (2 × 3 glow lines)", glowPaths() === 6, glowPaths(), 6);
  }

  test("12er Sky-Line → Z-Line: the same junction IS used in the right order, and needs no clip");
  {
    await build([["trail", T.sky12], ["trail", T.z]]);
    const r = builderResolve();
    eqNum("12er whole", r[0].len, 5.61, 0.02);
    eqNum("Z-Line whole", r[1].len, 3.68, 0.02);
    ok("junction is on", r[0].junction.off === false, r[0].junction.off, false);
    ok("and usable", !r[0].junction.unmade, r[0].junction.unmade, "falsy");
    ok("no gap reported", !r[0].gapReason, r[0].gapReason, null);
  }

  // =====================================================================================
  // 4. REGION-WIDE INVARIANT: no pair may produce an empty stretch.
  //    `empty`/∅ became unreachable once the entry check landed; this is what proves it, and what would
  //    catch a future rule change reintroducing it.
  // =====================================================================================
  test("all ordered trail pairs in the region: not one empty stretch");
  {
    const resp = await fetch(`regions/${REGION}.json`);
    const data = await resp.json();
    const ids = data.lineTrails.filter((t) => !t.loop).map((t) => t.id);
    const clear = btnByText(/Leeren/);
    let empty = 0, unmade = 0, skippedExit = 0, pairs = 0;
    const examples = [];
    const t0 = performance.now();
    for (const a of ids) for (const b of ids) {
      if (a === b) continue;
      clear.click(); builderTryAdd("trail", a); builderTryAdd("trail", b);
      pairs++;
      for (const x of builderResolve()) {
        if (x.empty) { empty++; if (examples.length < 6) examples.push(`${a} → ${b}`); }
        if (x.gapReason === "next") unmade++;
        if (x.gapReason === "exit") skippedExit++;
      }
      if (performance.now() - t0 > 60000) break;
    }
    clear.click();
    ok(`${pairs} pairs checked, none empty`, empty === 0, { empty, examples }, { empty: 0 });
    ok("unmade junctions occur (rule 3 is live)", unmade > 0, unmade, "> 0");
    ok("skipped exits occur (rule 1 is live)", skippedExit > 0, skippedExit, "> 0");
  }

  // =====================================================================================
  // 5. ROW LIST MECHANICS — drag, and the geometry bug it hid.
  // =====================================================================================
  test("drag reorders, and a displaced row travels the real slot distance");
  {
    await build([["trail", T.backtoblack], ["trail", T.x], ["lift", L.sprinter]]);
    const rows = () => $$("#builderList .builder-row");
    const mids = () => rows().map((r) => { const b = r.getBoundingClientRect(); return b.top + b.height / 2; });
    const names = () => rows().map((r) => r.querySelector(".bi-name").textContent.trim());
    const m = mids();
    const slot = m[1] - m[0];
    const rowH = rows()[0].getBoundingClientRect().height;
    // The bug: `rowHeight + 4` under-measures, because an iConnect pill sits between two rows and still
    // contributes layout on its negative margins. Desktop 46 vs 37, mobile 71 vs 56.
    ok("slot distance is NOT rowHeight+4", Math.abs(slot - (rowH + 4)) > 2,
       { slot: Math.round(slot), naive: rowH + 4 }, "must differ");

    const before = names();
    const h = rows()[0].querySelector(".bi-drag"), hb = h.getBoundingClientRect();
    const dy = slot + 4;   // strictly past the next row's centre
    h.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, clientX: hb.left + 5, clientY: hb.top + 5, pointerId: 99, isPrimary: true }));
    window.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: hb.left + 5, clientY: hb.top + 5 + dy, pointerId: 99, isPrimary: true }));
    await wait(160);
    const displaced = rows()[1].style.transform;
    const connOpacity = $$(".builder-connector").map((c) => getComputedStyle(c).opacity);
    ok("row 2 steps aside by one slot",
       Math.abs(parseFloat(displaced.replace(/[^-\d.]/g, "")) + slot) < 1.5,
       displaced, `≈ translateY(-${Math.round(slot)}px)`);
    ok("iConnect pills hidden while dragging", connOpacity.every((o) => parseFloat(o) < 0.05),
       connOpacity, "all ≈ 0");
    window.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, clientX: hb.left + 5, clientY: hb.top + 5 + dy, pointerId: 99, isPrimary: true }));
    await wait(200);
    const after = names();
    ok("order actually changed on drop", after[0] === before[1] && after[1] === before[0],
       after, [before[1], before[0], before[2]]);
    ok("pills visible again", $$(".builder-connector").every((c) => parseFloat(getComputedStyle(c).opacity) > 0.9),
       $$(".builder-connector").map((c) => getComputedStyle(c).opacity), "all 1");
    ok("numbers renumbered", $$(".bi-num").map((n) => n.textContent.trim()).join("") === "123",
       $$(".bi-num").map((n) => n.textContent.trim()), ["1", "2", "3"]);
  }

  // =====================================================================================
  // 6. TOUCH BEHAVIOUR — the drag handle's own axis split is delegated to the browser via touch-action, so
  //    these values ARE the behaviour. `manipulation` on the sheet is what stops a double-tap from zooming
  //    the map. .bi-body itself used to carry pan-y for the row's own swipe-to-delete gesture; that gesture
  //    is gone (2026-08-09, replaced by the ❌ button staying visible on every layout instead), and with it
  //    the reason .bi-body needed anything other than the browser's own default touch-action.
  test("touch-action values that the gestures depend on");
  {
    await build([["trail", T.x], ["lift", L.sprinter]]);
    const v = (sel, prop) => getComputedStyle($(sel))[prop];
    ok("#builderSheet manipulation (no double-tap zoom)", v("#builderSheet", "touchAction") === "manipulation",
       v("#builderSheet", "touchAction"), "manipulation");
    ok(".bi-drag none (vertical drag is not stolen by scrolling)", v(".bi-drag", "touchAction") === "none",
       v(".bi-drag", "touchAction"), "none");
  }

  // =====================================================================================
  // 7. EXPORT — deliberately not a finished Tour. What it MUST carry is every unmade connection, because
  //    the offline assembler has to close those rather than assume the stretches meet.
  // =====================================================================================
  test("export states each gap");
  {
    await build([["trail", T.backtoblack], ["trail", T.x], ["lift", L.sprinter]]);
    btnByText(/JSON/).click();
    await wait(80);
    const out = JSON.parse($("#builderExport").value);
    const xline = out.elements[1];
    ok("skipped exit exported as unconnected", xline.unconnected === true, xline.unconnected, true);
    ok("from/to pin the ridden stretch", Array.isArray(xline.from) && Array.isArray(xline.to),
       [xline.from, xline.to], "two coordinates");
    ok("no fabricated profile fields", !("distStart" in xline) && !("profile" in xline),
       Object.keys(xline), "no distStart/profile");

    await build([["trail", T.hacklberg], ["trail", T.z]]);
    btnByText(/JSON/).click();
    await wait(80);
    const off = JSON.parse($("#builderExport").value).elements[0].iConnect;
    ok("off junction exported with off:true", off.off === true, off.off, true);
    ok("…carries the real gap to bridge", Math.abs(off.gapM - 1664) <= 40, off.gapM, "1664 ±40");
    ok("…and the closest approach separately", Math.abs(off.nearestM - 1657) <= 40, off.nearestM, "1657 ±40");
    ok("…flagged as distance-driven", off.tooFar === true, off.tooFar, true);
  }

  // =====================================================================================
  // 8. LONG LISTS ON A PHONE (2026-07-28). All three need a list taller than the sheet, so they build
  //    8 elements first. Run the browser at a phone viewport for the touch-only parts.
  // =====================================================================================
  const LONG = [T.hacklberg, T.z, T.sky12, T.x, T.backtoblack, T.asitz, T.wurzel, T.scheeleitn];
  const sheetBody = () => $("#builderSheetBody");

  test("adding an element scrolls the list to it and flashes the new row");
  {
    await build(LONG.map((id) => ["trail", id]));
    const body = sheetBody();
    const max = Math.round(body.scrollHeight - body.clientHeight);
    ok("list is actually scrollable", max > 0, max, "> 0");
    // The smooth scroll has to finish, and each add restarts it -- 500ms was not enough and looked like a
    // failure while checking this by hand.
    await wait(1600);
    ok("scrolled to the bottom", Math.round(body.scrollTop) >= Math.round(body.scrollHeight - body.clientHeight) - 2,
       Math.round(body.scrollTop), `≈ ${Math.round(body.scrollHeight - body.clientHeight)}`);
    // One more add, to see the flash class on the row it created.
    await add("trail", T.asitz);
    const flashed = $$("#builderList .builder-row.is-new");
    ok("exactly one row carries is-new", flashed.length === 1, flashed.length, 1);
    ok("…and it is the last one", flashed[0] === $$("#builderList .builder-row").pop(),
       true, "last row");
    ok("row animation is running", getComputedStyle(flashed[0]).animationName === "builderRowIn",
       getComputedStyle(flashed[0]).animationName, "builderRowIn");
    ok("body flash is running", getComputedStyle(flashed[0].querySelector(".bi-body")).animationName === "builderRowFlash",
       getComputedStyle(flashed[0].querySelector(".bi-body")).animationName, "builderRowFlash");
    renderBuilder();
    ok("flash does not replay on a later render", $$(".builder-row.is-new").length === 0,
       $$(".builder-row.is-new").length, 0);
  }

  test("dragging to the list edge auto-scrolls, and stops at the real end");
  {
    await build(LONG.map((id) => ["trail", id]));
    const body = sheetBody();
    await wait(1200);
    body.scrollTop = 0;
    await wait(60);
    const max = Math.round(body.scrollHeight - body.clientHeight);
    const rows = () => $$("#builderList .builder-row");
    const names = () => rows().map((r) => r.querySelector(".bi-name").textContent.trim());
    const b = body.getBoundingClientRect();
    const before = names();

    // Hold at the bottom edge and fire NO further pointer events: the ticker has to keep scrolling on its
    // own, which is the whole point -- a stationary finger produces no pointermove.
    const h = rows()[0].querySelector(".bi-drag"), hb = h.getBoundingClientRect();
    const edgeY = b.bottom - 8;
    h.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, clientX: hb.left + 5, clientY: hb.top + 5, pointerId: 98, isPrimary: true }));
    window.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: hb.left + 5, clientY: edgeY, pointerId: 98, isPrimary: true }));
    await wait(300);
    const mid = Math.round(body.scrollTop);
    await wait(1400);
    const held = Math.round(body.scrollTop);
    ok("it scrolls while the finger just rests at the edge", mid > 0, mid, "> 0");
    // A transform extends its scroll container's scrollable overflow, so without clamping this runs away:
    // scrolling grows the drag offset, which pushes the row further down, which allows more scrolling.
    // Measured before the clamp: 825 on a list whose maximum is 275.
    ok("clamped to the list's real maximum", held <= max + 1, { held, max }, `≤ ${max}`);
    window.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, clientX: hb.left + 5, clientY: edgeY, pointerId: 98, isPrimary: true }));
    await wait(250);
    ok("the dragged element ended up last", names().indexOf(before[0]) === before.length - 1,
       names().indexOf(before[0]), before.length - 1);
    const after = Math.round(body.scrollTop);
    await wait(400);
    ok("the ticker stopped on release", Math.round(body.scrollTop) === after,
       [after, Math.round(body.scrollTop)], "unchanged");
  }

  test("the scrollbar is only visible while the list is moving (touch layouts)");
  {
    await build(LONG.map((id) => ["trail", id]));
    const body = sheetBody();
    await wait(1200);
    const colour = () => getComputedStyle(body).scrollbarColor;
    if (!builderTouchLayout()) {
      current.skipped = "desktop layout — the scrollbar stays visible here on purpose";
      ok("skipped on desktop", true, "skipped", "skipped");
    } else {
      const idleWidth = body.clientWidth;
      ok("invisible at rest", /rgba\(0, 0, 0, 0\)/.test(colour()), colour(), "transparent thumb");
      body.scrollTop = Math.max(0, body.scrollTop - 40);
      await wait(90);
      ok("visible while scrolling", body.classList.contains("is-scrolling"), colour(), "has is-scrolling");
      ok("no reflow when it appears", body.clientWidth === idleWidth,
         [idleWidth, body.clientWidth], "equal");
      await wait(900);
      ok("invisible again once idle", !body.classList.contains("is-scrolling"), colour(), "transparent again");
    }
  }

  // ---------- report ----------
  await clearBuilder();
  let passed = 0, failed = 0;
  const lines = [];
  for (const t of results) {
    const bad = t.checks.filter((c) => !c.pass);
    if (bad.length) { failed++; lines.push(`FAIL  ${t.name}`); for (const c of bad) lines.push(`        ${c.label}: got ${JSON.stringify(c.got)}, want ${JSON.stringify(c.want)}`); }
    else if (t.skipped) { passed++; lines.push(`skip  ${t.name}\n        ${t.skipped}`); }
    else { passed++; lines.push(`ok    ${t.name}`); }
  }
  console.log(lines.join("\n"));
  console.log(`\n${passed} passed, ${failed} failed, ${results.reduce((n, t) => n + t.checks.length, 0)} checks total`);
  return { passed, failed };
})();
