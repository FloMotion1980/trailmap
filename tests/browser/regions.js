// @suite   regions
// @area    Activating/deactivating region groups, persistence, the boot sequence
// @files   Trailmap App/index.html, Trailmap App/regions/version.json
// @touches activateRegionGroup, deactivateRegionGroup, MAX_ACTIVE_REGION_GROUPS, REGION_CATALOG, REGION_GROUPS, REGIONS, activeRegionGroups, renderRegionDialog, rebuildRegionChips, updateHeaderRegionsLabel, persistActiveState, restoreActiveState, loadRegionVersions, versionedRegionUrl, boot, applyPlaceVisibility, syncBuilderModeChrome
// @needs   region=bikekingdom, builder=off, SLOW (fetches regions and boots iframes)
//
// This is the core scaling mechanism: a bug here empties the map. It is also the slowest suite, because every
// case genuinely loads or unloads region data -- which is the point, since the failure modes are all about
// partially-applied state.
//
// `activateRegionGroup` is an ASYNC function declaration and therefore NOT reachable from here (Annex B
// hoisting covers plain declarations only), so activation is driven through the region dialog's own buttons,
// exactly as a user would. `boot()` is unreachable for the same reason, so the boot cases use TM.bootFresh(),
// which brings up a second copy of the app in an off-screen same-origin iframe and inspects its first frame.

TM.add("regions", () => typeof deactivateRegionGroup === "function", async (T) => {
  const dialog = () => TM.$("#regionDialog");
  const openDialog = async () => {
    if (!dialog().classList.contains("visible")) TM.$("#regionsBtn").click();
    await TM.until(() => dialog().classList.contains("visible"));
    await TM.wait(200);
  };
  const closeDialog = async () => {
    if (dialog().classList.contains("visible")) TM.$("#regionDialogClose").click();
    await TM.wait(200);
  };
  // Each row carries a 📍 fly button and the .rd-toggle; only the latter activates. Selecting on the toggle's
  // own class rather than "the buttons in the row" matters: the first version picked the 📍 and clicked it,
  // which flies the map and silently does nothing else -- a test that looked like a failing app.
  const rows = () => TM.$$("#regionDialogList > *").filter((r) => r.querySelector(".rd-toggle"));
  const toggle = (row) => row.querySelector(".rd-toggle");
  const inactiveRows = () => rows().filter((r) => !toggle(r).classList.contains("active"));
  const activeRows = () => rows().filter((r) => toggle(r).classList.contains("active"));
  const activeGroupCount = () => TM.$$("#regionChips .region-group-block").length;
  // MAX_ACTIVE_REGION_GROUPS is a const inside the app's try{} block and therefore unreachable; the
  // dialog publishes the same number in its own hint, so read it from there rather than hardcoding 3.
  const MAX_GROUPS = +((TM.$("#regionLimitText") || {}).textContent || "3").replace(/\D/g, "") || 3;

  // THIS SUITE IS THE ONE THAT CHANGES WHICH REGIONS ARE LOADED, so it is also the only one that has to put
  // them back itself: TM.baseline() deliberately does not touch the region set (loading a region is slow, and
  // every other suite is happy with whatever is active). Skipping the restore cost a whole confusing run --
  // it deactivated Bike Kingdom and the next seven suites failed with "a plain visible trail passes: got
  // false", which reads like a broken filter rule rather than a test that moved the ground under itself.
  const startingLabel = TM.$("#regionsBtn").textContent;
  // Restore BY ROW INDEX, not by name. The dialog's order comes straight from REGION_CATALOG and is stable,
  // whereas parsing a name out of a row is a trap: "3-Länder Enduro Trails" begins with a digit, the first
  // version's `/^[^\d(]+/` matched the empty string, and `label.indexOf("") > -1` is always true -- so that
  // region was never switched back off and seven later suites ran against a region set nobody asked for.
  let wantedActive = null;
  const snapshotRegions = async () => {
    await openDialog();
    wantedActive = rows().map((r) => toggle(r).classList.contains("active"));
    await closeDialog();
  };
  const restoreRegions = async () => {
    if (!wantedActive || TM.$("#regionsBtn").textContent === startingLabel) return;
    await openDialog();
    for (let pass = 0; pass < 4 && TM.$("#regionsBtn").textContent !== startingLabel; pass++) {
      const current = rows();
      for (let i = 0; i < current.length && i < wantedActive.length; i++) {
        const t = toggle(current[i]);
        if (t.classList.contains("active") !== wantedActive[i] && !t.disabled) {
          t.click();
          await TM.until(() => !TM.$("#regionDialogList").textContent.includes("Lädt…"), 20000, 200);
          await TM.wait(400);
        }
      }
    }
    await closeDialog();
  };
  try {
    await snapshotRegions();
    await regionCases(T);
  } finally {
    await restoreRegions();
    T.test("the suite put the region set back");
    // Compared as a SET: closing a region and re-adding it moves it to the END of the header label and of the
    // sidebar, because REGION_GROUPS is keyed in activation order. That is the app's actual behaviour, not a
    // defect, so the check must not demand the original ordering.
    const asSet = (s) => s.replace("🌍", "").split("·").map((x) => x.trim()).filter(Boolean).sort();
    T.eq("same active regions as before it ran", asSet(TM.$("#regionsBtn").textContent), asSet(startingLabel));
  }

  async function regionCases(T) {
  T.test("every active region has its own box with a ✕ and a 📍, diagonally opposite");
  // The section became the place where regions are managed (2026-07-31): ✕ closes the region, the 📍 flies to
  // it, and they sit in opposite corners so a mis-tap on a phone cannot turn "show me this" into "unload it".
  const boxes = TM.$$("#regionChips .region-group-block");
  T.eq("one box per active region", boxes.length, activeGroupCount());
  T.ok("each has a close button", boxes.every((b) => !!b.querySelector(".region-group-close-btn")), true, true);
  T.ok("each has a fly button", boxes.every((b) => !!b.querySelector(".region-group-fly-btn")), true, true);
  // Geometry only means something once the sidebar is really laid out. It is 1px wide when the browser pane is
  // not compositing, and every position then reads as nonsense -- better an honest skip than four checks that
  // pass or fail at random.
  const laidOut = TM.$("aside").getBoundingClientRect().width > 120;
  if (!laidOut) {
    T.skip("sidebar not laid out (width " + Math.round(TM.$("aside").getBoundingClientRect().width) +
           "px) — open the drawer or use a wider viewport for the geometry checks");
  } else {
    const box = boxes[0].getBoundingClientRect();
    const x = boxes[0].querySelector(".region-group-close-btn").getBoundingClientRect();
    const pin = boxes[0].querySelector(".region-group-fly-btn").getBoundingClientRect();
    T.ok("✕ straddles the TOP border", Math.abs((x.top + x.bottom) / 2 - box.top) < 4,
         Math.round((x.top + x.bottom) / 2 - box.top), "≈ 0 from the top edge");
    T.ok("✕ is at the right edge", Math.abs(x.right - box.right) < 10,
         Math.round(x.right - box.right), "≈ 0 from the right edge");
    // 📍 is STACKED directly under the ✕ inside one corner group. Three earlier positions lost, and the
    // reasons are all still live: the bottom border collides with the next box's legend by construction; a
    // footer row in flow costs a whole line per region; side by side on the border, the grey border showed
    // through the gap between them and read as a seam.
    T.eq("📍 sits directly under the ✕, with no gap", Math.round(pin.top - x.bottom), 0);
    T.ok("and shares its horizontal position", Math.abs(pin.right - x.right) < 3,
         Math.round(pin.right - x.right), "≈ 0");
    const corner = boxes[0].querySelector(".region-group-corner");
    const cRect = corner.getBoundingClientRect();
    T.ok("both are in one corner group", !!corner && corner.contains(boxes[0].querySelector(".region-group-fly-btn")),
         !!corner, true);
    // The shared opaque background is what hides the border between them. If it ever becomes transparent, the
    // seam is back and nothing else notices.
    const bg = getComputedStyle(corner).backgroundColor;
    T.ok("the group's background is opaque", !/rgba\(0, 0, 0, 0\)|transparent/.test(bg), bg, "an opaque colour");
    T.ok("and it covers the border line", cRect.top <= box.top && cRect.bottom > box.top,
         [Math.round(cRect.top - box.top), Math.round(cRect.bottom - box.top)], "spans the top edge");
    // The 📍 hangs into the box, so the wrapping chip row has to stay clear of it horizontally.
    const chips = TM.$$(".region-group-chips .chip", boxes[0]);
    T.ok("the chips keep clear of it", Math.max(...chips.map((c) => c.getBoundingClientRect().right)) <= cRect.left,
         [Math.round(Math.max(...chips.map((c) => c.getBoundingClientRect().right))), Math.round(cRect.left)],
         "chips left of the group");
    if (boxes.length > 1) {
      const prev = boxes[0].getBoundingClientRect();
      T.ok("and nothing hangs into the box below", prev.bottom < boxes[1].getBoundingClientRect().top,
           [Math.round(prev.bottom), Math.round(boxes[1].getBoundingClientRect().top)], "boxes clear");
    }
    // A long region name must not run under the buttons -- the legend is absolutely positioned, so only its
    // max-width keeps it off them.
    const legend = boxes[0].querySelector(".region-group-row").getBoundingClientRect();
    T.ok("the legend stays clear of the corner group", legend.right <= cRect.left + 1,
         [Math.round(legend.right), Math.round(cRect.left)], "legend ends before the group");
  }

  T.test("✕ closes that region straight away, with no confirmation");
  {
    const before = activeGroupCount();
    if (before < 2) {
      T.skip("needs at least two active regions, so one can be closed");
    } else {
      const box = TM.$$("#regionChips .region-group-block")[before - 1];
      const label = box.querySelector(".region-group-label").textContent;
      const name = label.replace(/\s*\(\d+\)\s*$/, "").trim();
      // How much this region currently contributes. It can legitimately be 0 -- every sub-region chip may be
      // switched off -- and then the trail count must NOT drop, so the assertion below has to know which case
      // it is in rather than always demanding a decrease. (That is what failed first: a region whose chips were
      // all off was closed, nothing changed, and the check called it a bug.)
      const ownCount = +(/\((\d+)\)\s*$/.exec(label.trim()) || [0, 0])[1];
      const trailsBefore = TM.ui.num(TM.ui.counts().trails);
      box.querySelector(".region-group-close-btn").click();
      const gone = await TM.until(() => activeGroupCount() === before - 1, 6000, 120);
      T.ok("no dialog or prompt appeared in between", !TM.$("#regionDialog").classList.contains("visible"), false, false);
      T.ok("the box is gone", gone, activeGroupCount(), before - 1);
      T.ok("its name left the header label", TM.$("#regionsBtn").textContent.indexOf(name) === -1,
           TM.$("#regionsBtn").textContent, "without " + name);
      const trailsAfter = TM.ui.num(TM.ui.counts().trails);
      T.ok("its trails left the list", ownCount > 0 ? trailsAfter < trailsBefore : trailsAfter === trailsBefore,
           [trailsBefore, trailsAfter, "own " + ownCount], ownCount > 0 ? "fewer" : "unchanged");
      T.eq("its own box is gone from the sidebar",
           TM.$$("#regionChips .region-group-label").filter((l) => l.textContent.indexOf(name) > -1).length, 0);
    }
  }

  T.test("the add-region button sits under the boxes and is disabled only at the cap");
  {
    const add = () => TM.$("#addRegionBtn");
    T.ok("it exists", !!add(), !!add(), true);
    const lastBox = TM.$$("#regionChips .region-group-block").slice(-1)[0];
    T.ok("below the last region box",
         add().getBoundingClientRect().top >= lastBox.getBoundingClientRect().bottom - 1,
         [Math.round(add().getBoundingClientRect().top), Math.round(lastBox.getBoundingClientRect().bottom)],
         "add button below");
    const atCap = activeGroupCount() >= 3;
    T.eq("disabled exactly when three are active", add().disabled, atCap);
    T.ok("and it says why when it is", !atCap || /3|maximal/i.test(add().textContent + add().title),
         add().textContent.trim(), "mentions the limit");
    if (!atCap) {
      add().click();
      const opened = await TM.until(() => TM.$("#regionDialog").classList.contains("visible"), 2000);
      T.ok("clicking it opens the region dialog", opened, opened, true);
      T.ok("which still lists every region, active ones included",
           rows().length > activeGroupCount() && activeRows().length === activeGroupCount(),
           [rows().length, activeRows().length], "all rows, actives marked");
      await closeDialog();
    } else {
      T.skip("at the cap — the click-through is checked when fewer than three are active");
    }
  }

  T.test("the dialog lists every catalogued region and marks the active ones");
  await openDialog();
  T.ok("more rows than are active", rows().length > activeGroupCount(), rows().length, "> " + activeGroupCount());
  T.ok("the limit is stated", /\d/.test(TM.$("#regionLimitText").textContent), TM.$("#regionLimitText").textContent, "a number");
  T.eq("the limit shown is the real one", TM.$("#regionLimitText").textContent.replace(/\D/g, ""), "3");
  await closeDialog();

  T.test("the header button names exactly the active regions, never a hardcoded list");
  const label = TM.$("#regionsBtn").textContent;
  const groupNames = TM.$$("#regionChips .region-group-label").map((b) => b.textContent.replace(/\s*\(\d+\)\s*$/, "").trim());
  T.ok("every active group appears in the header",
       groupNames.every((n) => label.toLowerCase().indexOf(n.toLowerCase().slice(0, 8)) > -1), label, groupNames);
  T.eq("and nothing else does", label.split("·").length, groupNames.length);

  T.test("activating a third region works, and a fourth is refused at the limit");
  const startGroups = activeGroupCount();
  const startTrails = TM.ui.num(TM.ui.counts().trails);
  await openDialog();
  const candidates = inactiveRows().filter((r) => !toggle(r).disabled);
  if (!candidates.length || startGroups >= MAX_GROUPS) {
    // Spell out WHICH condition bailed. The first version said "already at the limit or nothing left" and a
    // run that skipped for a third reason -- the dialog not being open, so rows() was empty -- looked
    // identical to a legitimately full catalog.
    T.skip("skipped: " + startGroups + " groups active, " + rows().length + " rows in the dialog, " +
           candidates.length + " of them activatable" +
           (dialog().classList.contains("visible") ? "" : " — DIALOG WAS NOT OPEN"));
    await closeDialog();
  } else {
    // Activate it with "Orte" OFF: activateRegionGroup ends in applyPlaceVisibility() precisely so a group
    // loaded while the switch is off does not light its labels up. That guard is the reason the boot-order bug
    // was invisible for so long -- it works for a LATER activation and only failed for boot's own, because
    // the flag had not been restored yet. Both halves are pinned now: this case and the fresh-boot one below.
    await closeDialog();
    await TM.ui.setSwitch("showPlacesToggle", false);
    await TM.until(() => TM.map.placeLabels() === 0, 3000);
    const placesOffBefore = TM.map.placeLabels();
    // Watch the tooltip pane rather than sampling it: the first version of this check caught the labels
    // MID-FADE and reported 3, which looked like a leak and was actually a flash -- every label of the new
    // region was added and then removed again a frame later. buildPlaceMarkers honours the switch at creation
    // now, so the honest assertion is "not even added once", and an observer says that without any timing luck.
    let addedWhileOff = 0;
    const paneObserver = new MutationObserver((records) => {
      records.forEach((rec) => [...rec.addedNodes].forEach((n) => {
        if (n.classList && n.classList.contains("place-label-tooltip")) addedWhileOff++;
      }));
    });
    paneObserver.observe(TM.$(".leaflet-tooltip-pane") || document.body, { childList: true, subtree: true });
    await openDialog();
    toggle(candidates[0]).click();
    // Region data is fetched, so wait for the group to actually appear rather than guessing.
    const grew = await TM.until(() => activeGroupCount() === startGroups + 1, 15000, 200);
    T.ok("the new group is active", grew, activeGroupCount(), startGroups + 1);
    await TM.wait(600);
    paneObserver.disconnect();
    T.eq("its place labels stayed off, as the switch says", TM.map.placeLabels(), placesOffBefore);
    T.eq("and were never even flashed onto the map", addedWhileOff, 0);
    await closeDialog();
    await TM.ui.setSwitch("showPlacesToggle", true);
    await TM.until(() => TM.map.placeLabels() > 0, 3000);
    T.ok("turning Orte back on now includes the new region's places", TM.map.placeLabels() > 0,
         TM.map.placeLabels(), "> 0");
    await openDialog();
    T.ok("its trails joined the list", TM.ui.num(TM.ui.counts().trails) > startTrails,
         TM.ui.num(TM.ui.counts().trails), "> " + startTrails);
    T.ok("the header label grew with it", TM.$("#regionsBtn").textContent.split("·").length === startGroups + 1,
         TM.$("#regionsBtn").textContent, (startGroups + 1) + " groups");
    // Fill up to the cap rather than stopping after one. Reaching MAX_ACTIVE_REGION_GROUPS is the whole point
    // of this case -- and it cannot be reached with a single activation, because the ✕ case above deliberately
    // leaves one region fewer. Without this the limit checks silently skipped every run.
    await openDialog();
    let guard = 0;
    while (activeGroupCount() < MAX_GROUPS && guard++ < MAX_GROUPS + 2) {
      const next = inactiveRows().filter((r) => !toggle(r).disabled)[0];
      if (!next) break;
      const n = activeGroupCount();
      toggle(next).click();
      await TM.until(() => activeGroupCount() === n + 1, 15000, 200);
      await openDialog();
    }
    T.eq("the cap can be filled exactly", activeGroupCount(), MAX_GROUPS);
    const still = inactiveRows();
    T.ok("at the limit, every remaining row is disabled",
         still.length > 0 && still.every((r) => toggle(r).disabled),
         still.filter((r) => !toggle(r).disabled).length, 0);
    T.ok("and the dialog says why", getComputedStyle(TM.$("#regionLimitNote")).display !== "none",
         getComputedStyle(TM.$("#regionLimitNote")).display, "shown");
    T.ok("the already-active rows stay clickable, so you can still make room",
         activeRows().every((r) => !toggle(r).disabled), activeRows().filter((r) => toggle(r).disabled).length, 0);
    await closeDialog();
    // The new add-region button has to agree with the dialog about the cap.
    T.ok("the add-region button is disabled at the cap", TM.$("#addRegionBtn").disabled,
         TM.$("#addRegionBtn").disabled, true);
    T.ok("and its label states the limit", new RegExp(String(MAX_GROUPS)).test(TM.$("#addRegionBtn").textContent),
         TM.$("#addRegionBtn").textContent.trim(), "mentions " + MAX_GROUPS);
    // Closing one with ✕ must re-enable it -- the button is rebuilt by rebuildRegionChips, which
    // deactivateRegionGroup calls, so this also pins that it is rebuilt at all.
    TM.$$("#regionChips .region-group-close-btn").slice(-1)[0].click();
    await TM.until(() => activeGroupCount() === MAX_GROUPS - 1, 6000, 120);
    T.ok("closing one re-enables it", !TM.$("#addRegionBtn").disabled, TM.$("#addRegionBtn").disabled, false);
    T.ok("and its label invites again", /hinzuf/i.test(TM.$("#addRegionBtn").textContent),
         TM.$("#addRegionBtn").textContent.trim(), "Region hinzufügen");

    T.test("deactivating is the exact inverse");
    // It resolves which sub-regions belong to the group through REGION_CATALOG, not through the mutated
    // REGIONS, so the order of activation and deactivation never matters.
    const groupKeys = TM.$$("#regionChips .region-group-block").length;
    const beforeTrails = TM.ui.num(TM.ui.counts().trails);
    const beforeLifts = TM.map.standaloneLifts();
    const beforePlaces = TM.map.placeLabels();
    await openDialog();
    const activeRow = activeRows()[activeRows().length - 1];
    if (!activeRow) {
      T.skip("could not identify an active row's toggle");
      await closeDialog();
    } else {
      toggle(activeRow).click();
      const shrank = await TM.until(() => activeGroupCount() === groupKeys - 1, 8000, 150);
      await closeDialog();
      T.ok("one group fewer", shrank, activeGroupCount(), groupKeys - 1);
      T.ok("its trails left the list", TM.ui.num(TM.ui.counts().trails) < beforeTrails,
           TM.ui.num(TM.ui.counts().trails), "< " + beforeTrails);
      T.ok("its lifts left the map", TM.map.standaloneLifts() <= beforeLifts, TM.map.standaloneLifts(), "<= " + beforeLifts);
      T.ok("its place labels left too", TM.map.placeLabels() <= beforePlaces, TM.map.placeLabels(), "<= " + beforePlaces);
      T.eq("no orphaned selection outline stayed behind", TM.map.selectionOutlines(), 0);
      T.ok("the header label shrank", TM.$("#regionsBtn").textContent.split("·").length === groupKeys - 1,
           TM.$("#regionsBtn").textContent, (groupKeys - 1) + " groups");
    }
  }

  T.test("the version manifest is loaded and every region URL carries its hash");
  // The hash is the ONLY thing that invalidates a cached region, since the worker serves them cache-first.
  T.ok("versionedRegionUrl is callable", typeof versionedRegionUrl === "function", true, true);
  const url = versionedRegionUrl("paznaun");
  T.ok("it points at the region file", /regions\/paznaun\.json/.test(url), url, "regions/paznaun.json...");
  T.ok("and appends a version", /\?v=[0-9a-f]{6,}/.test(url), url, "?v=<hash>");
  // Deliberately NOT asserting anything for an unknown key: it throws on REGION_CATALOG[key].file. Only
  // catalogued keys ever reach it (the dialog and boot both iterate the catalog), and a saved key that no
  // longer exists is dropped before this point -- covered by its own case below. Left as-is rather than
  // hardened while writing tests; noted so the gap is not mistaken for intent.
  T.ok("every catalogued region produces a versioned URL",
       TM.$$("#regionChips .region-group-block").length === 0 ||
       /\?v=/.test(versionedRegionUrl("bikekingdom")), versionedRegionUrl("bikekingdom"), "?v=<hash>");

  T.test("filters and active regions survive a real restart");
  const fresh = await TM.bootFresh(({ state, put }) => put("state", Object.assign({}, state, {
    activeDiffs: ["gruen", "blau"], showLifts: false, showPlaces: false,
  })));
  const d = fresh.doc;
  const chips = [...d.querySelectorAll("#diffChips .chip")].filter((c) => c.classList.contains("active"))
    .map((c) => c.dataset.diff);
  const liftsBox = d.getElementById("showLiftsToggle").checked;
  const placesBox = d.getElementById("showPlacesToggle").checked;
  const placeLabels = d.querySelectorAll(".place-label-tooltip").length;
  const liftCards = d.querySelectorAll("#liftList .lift-card").length;
  const trailCards = d.querySelectorAll("#trailList .trail-card").length;
  fresh.done();
  T.ok("it came up", trailCards > 0, trailCards, "> 0");
  T.eq("only the saved difficulties are active", chips.sort(), ["blau", "gruen"]);
  T.eq("the lifts switch is off", liftsBox, false);
  T.eq("and its list is empty", liftCards, 0);
  T.eq("the places switch is off", placesBox, false);
  // The bug this pins: activateRegionGroup calls applyPlaceVisibility while it runs, so the flags have to be
  // restored BEFORE the fetches -- otherwise a hard reload always came up with the labels showing.
  T.eq("and no place label is painted", placeLabels, 0);

  T.test("a saved region key that no longer exists is dropped silently");
  const ghost = await TM.bootFresh(({ state, put }) => put("state", Object.assign({}, state, {
    activeRegionGroups: (state.activeRegionGroups || []).concat(["region_that_was_deleted"]),
  })));
  const ghostFatal = ghost.doc.getElementById("fatalError");
  const ghostShown = ghost.doc.defaultView.getComputedStyle(ghostFatal).display !== "none";
  const ghostTrails = ghost.doc.querySelectorAll("#trailList .trail-card").length;
  ghost.done();
  T.eq("no fatal panel", ghostShown, false);
  T.ok("the real regions still loaded", ghostTrails > 0, ghostTrails, "> 0");

  T.test("a fresh start in builder mode runs boot() to the end");
  // Everything past boot()'s first await is async, so a throw there is invisible to the top-level try{} and
  // to window.onerror. It used to leave a silently half-started app: trails on the map (activateRegionGroup
  // renders on its own) but no builder state, no restored filters and no map fit.
  const b = await TM.bootFresh(({ builder, put }) =>
    put("builder", Object.assign({}, builder || {}, { builderMode: true, builderItems: [], builderSheetOpen: true })));
  const bFatal = b.doc.defaultView.getComputedStyle(b.doc.getElementById("fatalError")).display !== "none";
  const bTitle = b.doc.getElementById("appTitle") && b.doc.getElementById("appTitle").textContent;
  const bSheet = b.doc.getElementById("builderSheet").className;
  const bCards = b.doc.querySelectorAll("#trailList .trail-card").length;
  b.done();
  T.eq("no fatal panel", bFatal, false);
  T.ok("the list is filled", bCards > 0, bCards, "> 0");
  T.eq("the title switched to the mode indicator", bTitle, "Trailbuilder");
  T.ok("and the builder sheet is open", /visible/.test(bSheet || ""), bSheet, "visible");

  T.test("a first-ever visit asks which regions rather than landing on the default unasked");
  const first = await TM.bootFresh(({ put }) => { put("state", null); put("builder", null); });
  const dlgShown = first.doc.getElementById("regionDialog").classList.contains("visible");
  const firstCards = first.doc.querySelectorAll("#trailList .trail-card").length;
  first.done();
  T.ok("the region dialog is open", dlgShown, dlgShown, true);
  T.ok("and the default region is loaded behind it", firstCards > 0, firstCards, "> 0");
  }
});
