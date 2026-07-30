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
    T.eq("same active regions as before it ran", TM.$("#regionsBtn").textContent, startingLabel);
  }

  async function regionCases(T) {
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
  if (!candidates.length || startGroups >= 3) {
    T.skip("already at the limit or nothing left to activate — run with 2 active regions");
    await closeDialog();
  } else {
    toggle(candidates[0]).click();
    // Region data is fetched, so wait for the group to actually appear rather than guessing.
    const grew = await TM.until(() => activeGroupCount() === startGroups + 1, 15000, 200);
    T.ok("the new group is active", grew, activeGroupCount(), startGroups + 1);
    T.ok("its trails joined the list", TM.ui.num(TM.ui.counts().trails) > startTrails,
         TM.ui.num(TM.ui.counts().trails), "> " + startTrails);
    T.ok("the header label grew with it", TM.$("#regionsBtn").textContent.split("·").length === startGroups + 1,
         TM.$("#regionsBtn").textContent, (startGroups + 1) + " groups");
    await openDialog();
    if (activeGroupCount() >= 3) {
      const still = inactiveRows();
      T.ok("at the limit, the remaining rows are disabled",
           still.every((r) => toggle(r).disabled), still.filter((r) => !toggle(r).disabled).length, 0);
      T.ok("and the dialog says why", getComputedStyle(TM.$("#regionLimitNote")).display !== "none",
           getComputedStyle(TM.$("#regionLimitNote")).display, "shown");
    } else {
      T.skip("fewer than 3 regions in the catalog to reach the limit");
    }
    await closeDialog();

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
