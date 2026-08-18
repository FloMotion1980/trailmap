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
  // Each row's only clickable control is now the .rd-toggle (the row's own 📍 fly button was removed
  // 2026-08-17 -- see the "no locate button in the dialog rows any more" case below).
  const rows = () => TM.$$("#regionDialogList > *").filter((r) => r.querySelector(".rd-toggle"));
  const toggle = (row) => row.querySelector(".rd-toggle");
  const inactiveRows = () => rows().filter((r) => !toggle(r).classList.contains("active"));
  const activeRows = () => rows().filter((r) => toggle(r).classList.contains("active"));
  const activeGroupCount = () => TM.$$("#regionChips .region-group-block").length;
  // The dialog publishes the limit as a data attribute on its slot row (the old #regionLimitText span went
  // when the red "Limit erreicht" note became a row of slots). MAX_ACTIVE_REGION_GROUPS itself is a const
  // inside the app's try{} block and unreachable from here.
  const MAX_GROUPS = +(TM.$("#regionSlots") || {}).dataset?.max || 3;

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
          // A successful activation now closes the dialog on its own (2026-08-17) -- reopen it so the NEXT
          // pass's `rows()` reads a freshly rebuilt list instead of the stale one left behind by a click that
          // skipped renderRegionDialog() on the way out. The already-clicked nodes in `current` stay usable for
          // the rest of THIS pass regardless (their handlers close over groupKey/state, not DOM attachment).
          if (!dialog().classList.contains("visible")) { TM.$("#regionsBtn").click(); await TM.wait(200); }
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
  T.test("every active region has its own box, framed except where its controls sit on the line");
  // A fieldset, and that is the whole idea: the frame is drawn all the way round, and each control that sits ON
   // the line carries the sidebar's background so it cuts its own gap (user, 2026-08-02: "da wo oben
  // Schaltflächen sind, ist er nicht zu sehen"). Between those two dates the controls briefly moved INSIDE a
  // closed box, and this case asserted that instead -- worth knowing, because it is why the checks read the way
  // they do now: the ✕'s glyph has to land on the same vertical line as the section carets, and losing that by
  // 10px is exactly what the inside-the-box version got wrong.
  const boxes = TM.$$("#regionChips .region-group-block");
  T.eq("one box per active region", boxes.length, activeGroupCount());
  T.ok("each has a close button", boxes.every((b) => !!b.querySelector(".region-group-close-btn")), true, true);
  T.ok("each has a fly button", boxes.every((b) => !!b.querySelector(".region-group-fly-btn")), true, true);
  T.ok("the frame is drawn on all four sides", ["borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth"]
       .every((p) => parseFloat(getComputedStyle(boxes[0])[p]) > 0), true, true);
  // Geometry only means something once the sidebar is really laid out. It is 1px wide when the browser pane is
  // not compositing, and every position then reads as nonsense -- better an honest skip than checks that pass
  // or fail at random.
  const laidOut = TM.$("aside").getBoundingClientRect().width > 120;
  if (!laidOut) {
    T.skip("sidebar not laid out (width " + Math.round(TM.$("aside").getBoundingClientRect().width) +
           "px) — open the drawer or use a wider viewport for the geometry checks");
  } else {
    const box = boxes[0].getBoundingClientRect();
    const row = boxes[0].querySelector(".region-group-row");
    const rowRect = row.getBoundingClientRect();
    const label = boxes[0].querySelector(".region-group-label").getBoundingClientRect();
    const pin = boxes[0].querySelector(".region-group-fly-btn").getBoundingClientRect();
    const x = boxes[0].querySelector(".region-group-close-btn").getBoundingClientRect();
    const chip = boxes[0].querySelector(".region-group-chips .chip").getBoundingClientRect();
    T.ok("the legend straddles the top border", Math.abs((rowRect.top + rowRect.bottom) / 2 - box.top) < 4,
         Math.round((rowRect.top + rowRect.bottom) / 2 - box.top), "≈ 0 from the top edge");
    // The gap in the border is cut by the background, nothing else. If it ever goes transparent the line runs
    // straight through the name and nothing else notices.
    T.ok("and cuts its gap with an opaque background",
         !/rgba\(0, 0, 0, 0\)|transparent/.test(getComputedStyle(row).backgroundColor),
         getComputedStyle(row).backgroundColor, "an opaque colour");
    T.ok("the name sits close to the box's left edge", label.left - box.left <= 12,
         Math.round(label.left - box.left), "<= 12px in");
    T.ok("the 📍 is beside the name, on the same line", pin.left >= label.right - 1 &&
         Math.abs((pin.top + pin.bottom) / 2 - (label.top + label.bottom) / 2) < 4,
         [Math.round(pin.left - label.right), Math.round((pin.top + pin.bottom) / 2 - (label.top + label.bottom) / 2)],
         "to the right, same centre line");
    // Both of these are what the user checks by eye: the ✕ on the box's corner, and its glyph on the same
    // vertical line as the carets of every section heading.
    T.ok("the ✕ is centred on the box's top-right corner",
         Math.abs((x.left + x.right) / 2 - box.right) < 3 && Math.abs((x.top + x.bottom) / 2 - box.top) < 4,
         [Math.round((x.left + x.right) / 2 - box.right), Math.round((x.top + x.bottom) / 2 - box.top)], "≈ 0, ≈ 0");
    const caretAfter = getComputedStyle(TM.$("#secRegion > summary"), "::after");
    const caretMid = TM.$("#secRegion > summary").getBoundingClientRect().right +
                     Math.abs(parseFloat(caretAfter.marginRight)) - parseFloat(caretAfter.width) / 2;
    T.ok("and its glyph lands on the section carets' line", Math.abs((x.left + x.right) / 2 - caretMid) < 3,
         Math.round((x.left + x.right) / 2 - caretMid), "≈ 0 from the caret centre");
    // The straddling legend hangs INTO the box, so the first chip row has to clear it. At 14px of box padding
    // they were 1px apart and read as overlapping, which is what the padding is now 20px for.
    T.ok("the chips clear the legend", chip.top >= rowRect.bottom - 1,
         Math.round(chip.top - rowRect.bottom), ">= 0");
    T.ok("the chips get the box's full width, with no reserved corner",
         !boxes[0].querySelector(".region-group-chip-spacer"), true, true);
    const chips = TM.$$(".region-group-chips .chip", boxes[0]);
    T.ok("and run to the box's inner right edge when there are enough of them",
         chips.length < 3 || Math.max(...chips.map((c) => c.getBoundingClientRect().right)) > box.right - 60,
         [chips.length, Math.round(Math.max(...chips.map((c) => c.getBoundingClientRect().right)))],
         "not held back by a reserved corner");
    // Greedy line-filling has to be OPTIMAL: whenever a chip starts a new line, the previous line must genuinely
    // have had no room for it. It did not, for a whole day -- as inline-blocks the last chip on a line still
    // contributed its own margin-right, so a pair needing 274.9px of 275px wrapped anyway and every region box
    // was a line taller than it had to be (user, 2026-08-02: "müssten nicht mehr in eine Zeile passen"). The
    // check is arithmetic on the rendered boxes, so it holds for any region and any name lengths.
    {
      const GAP = 6;   // must match .region-group-chips' gap
      const inner = chips.length ? chips[0].parentNode.clientWidth : 0;
      let worstWasted = 0, culprit = null;
      for (let i = 1; i < chips.length; i++) {
        const prev = chips[i - 1].getBoundingClientRect(), cur = chips[i].getBoundingClientRect();
        if (Math.abs(cur.top - prev.top) < 2) continue;      // same line, nothing to prove
        const usedOnPrevLine = prev.right - chips[0].parentNode.getBoundingClientRect().left;
        const spare = inner - usedOnPrevLine - GAP - cur.width;
        if (spare >= 0 && spare > worstWasted) { worstWasted = spare; culprit = chips[i].textContent.trim(); }
      }
      T.ok("every chip that wrapped had to wrap", worstWasted < 0.5,
           culprit ? culprit + " had " + Math.round(worstWasted) + "px to spare on the line above" : "none",
           "no wasted line");
    }
    if (boxes.length > 1) {
      T.ok("nothing hangs into the box below", box.bottom <= boxes[1].getBoundingClientRect().top,
           [Math.round(box.bottom), Math.round(boxes[1].getBoundingClientRect().top)], "boxes clear");
    }
    T.ok("a long name stays off the ✕", rowRect.right <= x.left + 1,
         [Math.round(rowRect.right), Math.round(x.left)], "legend ends before the ✕");
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

  T.test("the dialog groups by country and can be searched");
  await openDialog();
  {
    const heads = TM.$$("#regionDialogList .rd-country");
    T.ok("there are country headings", heads.length >= 2, heads.length, ">= 2");
    T.ok("each names a country and counts its regions",
         heads.every((h) => /\(\d+\)/.test(h.textContent) && h.textContent.trim().length > 4),
         heads.map((h) => h.textContent.trim()).slice(0, 3), "flag + name + (n)");
    // Sorted by the country's German name, and stable as the catalog grows -- catalog order or
    // "most regions first" would reshuffle the list whenever a region is added.
    const names = heads.map((h) => h.textContent.replace(/[^A-Za-zÄÖÜäöüß ]/g, "").trim());
    T.eq("countries in alphabetical order", names, names.slice().sort((a, b) => a.localeCompare(b, "de")));
    // Every region appears exactly once: grouping by the PRIMARY country, with the others shown as flags.
    T.eq("no region is listed twice", rows().length, new Set(rows().map((r) => r.textContent)).size);
    const crossBorder = rows().filter((r) => r.querySelector(".rd-flags"));
    T.ok("the cross-border regions say so with extra flags", crossBorder.length >= 3,
         crossBorder.map((r) => r.querySelector(".rd-label").textContent.trim()), ">= 3 of them");
  }

  T.test("search matches the name, a sub-region and a country");
  {
    const all = rows().length;
    const type = async (v) => {
      TM.$("#regionSearch").value = v;
      TM.$("#regionSearch").dispatchEvent(new Event("input", { bubbles: true }));
      await TM.wait(120);
      return rows().map((r) => r.querySelector(".rd-label").textContent.trim());
    };
    T.ok("by region name", (await type("finale")).some((n) => /Finale/i.test(n)), await type("finale"), "Finale Ligure");
    // The point of searching sub-regions: a rider knows the village, not our region name.
    const bySub = await type("samnaun");
    T.ok("by sub-region — Samnaun finds Silvretta Bike Arena", bySub.some((n) => /Silvretta/i.test(n)), bySub, "Silvretta");
    const byCountry = await type("schweiz");
    T.ok("by country name", byCountry.length >= 2, byCountry, ">= 2 Swiss regions");
    // The one that makes grouping-by-primary honest: Silvretta is filed under Austria but reaches into CH.
    T.ok("...including the cross-border ones filed elsewhere", byCountry.some((n) => /Silvretta/i.test(n)),
         byCountry, "contains Silvretta");
    T.ok("by country code", (await type("ch")).length >= 2, (await type("ch")).length, ">= 2");
    // Diacritics: a phone keyboard will not produce "ü".
    const noUmlaut = await type("galtur");
    T.ok("umlauts are ignored — 'galtur' finds Galtür", noUmlaut.some((n) => /Silvretta/i.test(n)), noUmlaut, "Silvretta");
    T.eq("a term nobody matches empties the list", (await type("zzzznope")).length, 0);
    T.ok("and says so instead of showing nothing", TM.$("#regionDialogEmpty").classList.contains("visible"),
         TM.$("#regionDialogEmpty").className, "visible");
    await type("");
    T.eq("clearing it brings every region back", rows().length, all);
    T.ok("and the empty note is gone", !TM.$("#regionDialogEmpty").classList.contains("visible"), false, false);
  }
  await closeDialog();

  T.test("the dialog lists every catalogued region and marks the active ones");
  await openDialog();
  T.ok("more rows than are active", rows().length > activeGroupCount(), rows().length, "> " + activeGroupCount());
  T.eq("there is one slot per allowed region", TM.$$("#regionSlots .rd-slot").length, MAX_GROUPS);
  T.eq("filled slots match the active regions", TM.$$("#regionSlots .rd-slot.filled").length, activeGroupCount());
  T.eq("the rest are empty", TM.$$("#regionSlots .rd-slot.empty").length, MAX_GROUPS - activeGroupCount());
  T.ok("and the hint counts them", /\d von \d/.test(TM.$("#regionDialogHint").textContent) ||
       /Alle \d/.test(TM.$("#regionDialogHint").textContent),
       TM.$("#regionDialogHint").textContent.trim(), "N von M Plätzen");
  T.eq("the limit it publishes is the real one", MAX_GROUPS, 3);
  await closeDialog();

  T.test("no locate button in the dialog rows any more, and the name is not clipped");
  await openDialog();
  {
    const r = rows()[0];
    T.ok("no .rd-locate-btn left in a row", !r.querySelector(".rd-locate-btn"), false, false);
    const label = r.querySelector(".rd-label");
    const cs = getComputedStyle(label);
    T.ok("the label can wrap instead of being clipped",
         cs.whiteSpace !== "nowrap" && cs.textOverflow !== "ellipsis",
         [cs.whiteSpace, cs.textOverflow], "not nowrap/ellipsis");
  }
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
    T.ok("a successful activation closes the dialog on its own (2026-08-17)",
         !dialog().classList.contains("visible"), dialog().classList.contains("visible"), false);
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
    T.eq("every slot is filled", TM.$$("#regionSlots .rd-slot.filled").length, MAX_GROUPS);
    T.eq("no empty slot is left", TM.$$("#regionSlots .rd-slot.empty").length, 0);
    T.ok("and the hint says the dialog is full", /Alle/.test(TM.$("#regionDialogHint").textContent),
         TM.$("#regionDialogHint").textContent.trim(), "Alle N Plätze belegt");
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

  T.test("a saved state missing activeRegions/activeDiffs cannot crash boot()");
  // Found 2026-08-04 by accident while testing an unrelated fix: boot() reads `saved.activeRegions.filter(...)`
  // with no guard, so a state that is otherwise a valid object but happens to be missing that one key -- written
  // by an older build, hand-edited, or truncated -- threw "Cannot read properties of undefined (reading
  // 'filter')" out of boot() and put up the fatal panel on EVERY load, which on a home-screen PWA a rider cannot
  // dismiss or work around themselves. restoreActiveState() now normalises both arrays the same way it already
  // normalised the boolean switches below.
  // activeRegionGroups is set explicitly rather than trusting whatever the live page currently has: by this
  // point in the suite other cases have activated and deactivated regions, so the real, current saved value is
  // not something this case should depend on -- only the two keys actually under test matter here.
  const maimed = await TM.bootFresh(({ state, put }) => {
    const s = Object.assign({}, state, { activeRegionGroups: ["bikekingdom"] });
    delete s.activeRegions;
    delete s.activeDiffs;
    put("state", s);
  });
  const maimedFatal = maimed.doc.getElementById("fatalError");
  const maimedShown = maimed.doc.defaultView.getComputedStyle(maimedFatal).display !== "none";
  const maimedTrails = maimed.doc.querySelectorAll("#trailList .trail-card").length;
  maimed.done();
  T.eq("no fatal panel", maimedShown, false);
  T.ok("the region still loaded, just with everything visible by default", maimedTrails > 0, maimedTrails, "> 0");

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
  const bBtnOn = b.doc.getElementById("builderModeBtn").classList.contains("on");
  const bSheet = b.doc.getElementById("builderSheet").className;
  const bCards = b.doc.querySelectorAll("#trailList .trail-card").length;
  b.done();
  T.eq("no fatal panel", bFatal, false);
  T.ok("the list is filled", bCards > 0, bCards, "> 0");
  // The title used to become the mode indicator ("Trailbuilder") -- dropped 2026-08-09 (user) once it became
  // permanently visible on desktop too, where a name that changes under you reads as a different app. The
  // builder button's own fill is the only mode indicator now.
  T.eq("the title stays \"Trailmap\", builder mode or not", bTitle, "Trailmap");
  T.ok("the builder button itself shows the mode instead", bBtnOn, bBtnOn, true);
  T.ok("and the builder sheet is open", /visible/.test(bSheet || ""), bSheet, "visible");

  T.test("a first-ever visit asks which regions, with NOTHING preselected");
  // Used to land on Paznaun behind the dialog, which contradicted the dialog's own point: it cannot ask the
  // user to "consciously pick" while one is already picked for them. The old case even asserted that as
  // correct ("and the default region is loaded behind it"). What made the user notice was the catalog label --
  // Paznaun's own display name is "Silvretta Bike Arena" (2026-08-04), so the dialog showed that region marked
  // Aktiv on a session that had never chosen anything, which is the report verbatim, just not the region it
  // sounded like.
  const first = await TM.bootFresh(({ put }) => { put("state", null); put("builder", null); });
  const dlgShown = first.doc.getElementById("regionDialog").classList.contains("visible");
  const firstCards = first.doc.querySelectorAll("#trailList .trail-card").length;
  const activeToggleCount = [...first.doc.querySelectorAll(".region-dialog-row .rd-toggle.active")].length;
  const headerText = first.doc.getElementById("regionsLabel").textContent;
  first.done();
  T.ok("the region dialog is open", dlgShown, dlgShown, true);
  T.eq("no region is loaded behind it", firstCards, 0);
  T.eq("none of the dialog's own rows shows Aktiv", activeToggleCount, 0);
  T.ok("and the header says so too", /wählen/.test(headerText), headerText, "mentions wählen");

  T.test("a returning visitor who deliberately cleared every region stays cleared");
  // The same fallback used to override THIS case back to Paznaun too, on the reasoning that an empty array is
  // indistinguishable from "nothing saved" -- but a returning visitor (saved !== null) who emptied their
  // regions on purpose gets their choice respected, and does NOT see the dialog auto-open a second time.
  const returning = await TM.bootFresh(({ state, put }) => {
    put("state", Object.assign({}, state || {}, { activeRegionGroups: [], activeRegions: [] }));
  });
  const returningDlgShown = returning.doc.getElementById("regionDialog").classList.contains("visible");
  const returningCards = returning.doc.querySelectorAll("#trailList .trail-card").length;
  returning.done();
  T.eq("no region is loaded", returningCards, 0);
  T.ok("and the dialog does not auto-open for a returning visitor", !returningDlgShown, returningDlgShown, false);
  }
});
