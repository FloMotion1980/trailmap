// Lift, solo, name-label and count regression cases — paste into the browser console and run.
//
// WHY THIS FILE EXISTS: every case below is a bug the user reported, and several of them were reported
// TWICE for two different causes — "Solo blendet Lifte nicht aus" arrived once for the mask/dim trap and
// again for the Tours' own lift stretches, and the fix for the first made the second more visible, not less.
// That is exactly the shape of bug a prose changelog cannot protect against, so this executes them.
//
// HOW TO RUN
//   1. python3 -m http.server   from inside "Trailmap App/"   (NOT file://)
//   2. open http://localhost:8000/ and activate the region "Bike Kingdom" (bikekingdom). Other regions may
//      stay active — every count below is a before/after delta, not an absolute, apart from the ids listed
//      in T/L, which come from bikekingdom's own data.
//   3. Tourenbuilder mode OFF (one case switches it on and off again itself)
//   4. paste this whole file into the console
//
// It changes filters, solo, "Namen" and "Orte" (each case puts back what it touched), and the last two
// cases boot a second copy of the app in an off-screen iframe. Your saved state is restored at the end, but
// anything you had assembled in the builder is gone.
//
// DOES IT ACTUALLY BITE? Validated by mutation; repeat cheaply with any of these:
//
//   * in applyLiftVisibility, drop the solo term: `if (passes) {`
//     -> 5 tests fail, 6 checks, all of the form "got 20 lifts on the map, want 0/1/5".
//   * in applySolo/clearSolo, remove the applyLiftSegmentOpacity() call
//     -> 3 tests fail, 5 checks: 26 Tour lift stretches still visible, want 0 (or 5 for the soloed Tour).
//        This is the second, independent cause of the same user report, which is why both are checked
//        separately — the mutations fail disjoint sets of checks.
//   * in liftPassesFilters, restore the old exemption: `|| liftIdsInVisibleTours.has(l.id)`
//     -> the ReferenceError aborts the run; re-add the set to see the intended failure, which is
//        "🚡-Schalter aus" reporting 5 lifts left on the map and "5 Lifte" missing from the Filter line.
//   * in applyNameLabels, delete the liftLayers loop
//     -> "Namen an" fails: 0 lift labels, want one per lift.
//   * in setLiftHover's off-branch, go back to an unconditional hitLine.closeTooltip()
//     -> "Hover laesst das Label stehen" fails: the label count drops to 0 on mouseleave.
//   * in render()'s card branch, drop the Tour term: `if (!visible) { … }`
//     -> "Touren stehen in ihrem eigenen Abschnitt" fails: the Tours are back in the trail list.
//   * in renderTourList, sort by difficulty instead of by name
//     -> the same case fails on "nach Namen sortiert, nicht nach Schwierigkeit".
//   * in syncBuilderModeChrome, rename the id back to scrollTopBtn (the crash of 2026-07-29)
//     -> 2 tests fail, 5 checks: the builder case reports the TypeError as its value, and the fresh start
//        comes up as the fatal-error panel with the title still "Trailmap" and its sheet closed. That
//        mutation is also what showed the throw to be SILENT before boot() got its .catch — the app came up
//        half-started with no panel at all, which is why "kein Fehlerpanel" is a meaningful check now.
//
// WHY IT DRIVES THE DOM: same reason as builder_testcases.js — `LIFTS`, `lineLayers`, `liftLayers`,
// `soloId` and friends are const/let inside the app's top-level try{} block and are NOT reachable from a
// separately-evaluated script, while function *declarations* leak to the global scope (sloppy-mode Annex B).
// So applySolo/liftPassesFilters can be called, but nothing they own can be read directly — the map is
// inspected through its own SVG instead, which has the side benefit of testing what is actually painted.
//
// ONE FOOTNOTE TO THAT RULE, worth knowing before you try to call something and get a ReferenceError:
// Annex B hoisting covers plain FunctionDeclarations only. `async function boot()` is an
// AsyncFunctionDeclaration and stays block-scoped, so boot() canNOT be called from here — which is why the
// two boot-order cases at the end load the app afresh in an off-screen same-origin iframe instead. That is
// closer to the real bug anyway: both were bugs about what the app looks like in its first painted frame,
// and an iframe gives a genuine first frame while sharing localStorage with this page.

(async () => {
  "use strict";
  const T = {                                    // ids, so a rename fails loudly in one place
    tour615: "bk_tour_615_blau",                 // rides exactly 5 lifts (see L.of615)
    trail: "bk_access_langwies",                 // any ordinary non-loop trail
  };
  const L = {
    hoernli: "lift_bk_hoernli",
    rothorn1: "lift_bk_rothorn1",
    of615: ["lift_bk_chur_kaenzeli", "lift_bk_kaenzeli_brambrueesch",
            "lift_bk_tgantieni", "lift_bk_scalottas", "lift_bk_heidbueel"],
  };

  // ---------- harness (same shape as builder_testcases.js) ----------
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const results = [];
  let current = null;
  const test = (name) => { current = { name, checks: [], skipped: null }; results.push(current); };
  const ok = (label, cond, got, want) => current.checks.push({ label, pass: !!cond, got, want });

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  // ---------- map probes ----------
  // The four kinds of stroke that matter here live in two panes, and the pane is what tells a standalone
  // lift from a Tour's own lift stretch: a standalone lift puts all three strokes in LIFT_BAND_PANE, while a
  // Tour puts only its MASK there and its symbol in the overlay pane with the trails.
  const shown = (p) => (p.getAttribute("stroke-opacity") || "1") !== "0";
  const band = () => $$(".leaflet-liftBand-pane path");
  const overlay = () => $$(".leaflet-overlay-pane path");
  const standaloneLifts = () =>                    // one hairline per standalone lift
    band().filter((p) => p.getAttribute("stroke") === "#000000" &&
                         p.getAttribute("stroke-width") === "1.1" && shown(p)).length;
  const tourLiftStretches = () =>                  // one dotted symbol per Tour lift segment
    overlay().filter((p) => (p.getAttribute("stroke-dasharray") || "").startsWith("1,13") && shown(p)).length;
  const masks = () =>
    band().filter((p) => p.getAttribute("stroke") === "#cfcfcf" && shown(p)).length;
  const dimmedTrails = () =>
    overlay().filter((p) => (p.getAttribute("stroke-opacity") || "1") === "0.15").length;
  const placeLabels = () => $$(".place-label-tooltip").length;
  const liftLabels = () => $$(".trail-label-tooltip").filter((e) => /🚡/.test(e.textContent));
  const markedLabels = () => liftLabels().filter((e) => e.classList.contains("tl-hover"));

  // ---------- UI probes ----------
  const liftCards = () => $$("#liftList .lift-card");
  const cardFor = (name) => liftCards().find((c) => c.textContent.includes(name));
  const counts = () => ({
    filter: $("#filterCountLabel").textContent,
    trails: $("#trailCountLabel").textContent,
    touren: $("#tourCountLabel").textContent,
    lifts: $("#liftCountLabel").textContent,
  });
  const num = (s) => { const m = /(\d+)/.exec(s || ""); return m ? +m[1] : null; };
  const setSwitch = async (id, on) => {
    const box = $("#" + id);
    if (box.checked !== on) { box.click(); await wait(220); }
  };
  const setDiff = async (d, on) => {
    const chip = $(`#diffChips [data-diff="${d}"]`);
    if (chip.classList.contains("active") !== on) { chip.click(); await wait(220); }
  };

  // ---------- a genuine fresh boot, without leaving this page ----------
  // Same origin, so the iframe shares localStorage: write the state to be restored, then let a second copy
  // of the app come up from scratch and look at its first painted frame. `mutate` receives the parsed
  // saved state and returns what should be stored instead. Everything is put back by done().
  const STORE = { state: "trailmap-active-state-v1", builder: "trailmap-builder-v1" };
  const bootFresh = async (mutate) => {
    const backup = Object.values(STORE).map((k) => [k, localStorage.getItem(k)]);
    mutate({
      state: JSON.parse(localStorage.getItem(STORE.state) || "null"),
      builder: JSON.parse(localStorage.getItem(STORE.builder) || "null"),
      put: (k, v) => localStorage.setItem(STORE[k], JSON.stringify(v)),
    });
    const frame = document.createElement("iframe");
    frame.style.cssText = "position:fixed;left:-9999px;top:0;width:420px;height:420px;border:0";
    frame.src = location.pathname + "?boottest=" + backup.length;
    document.body.appendChild(frame);
    await new Promise((r) => { frame.onload = r; setTimeout(r, 10000); });
    await wait(2600);                       // boot()'s fetches, then its render
    return {
      doc: frame.contentDocument,
      done: () => {
        frame.remove();                     // remove FIRST: the copy persists its own state while alive
        backup.forEach(([k, v]) => (v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v)));
      },
    };
  };

  // ---------- preconditions ----------
  for (const fn of ["applySolo", "clearSolo", "applyLiftVisibility", "applyLiftSegmentOpacity",
                    "liftPassesFilters", "liftHiddenBySolo", "applyNameLabels",
                    "syncBuilderModeChrome", "closeInfoPanelAndDeselect"]) {
    if (typeof window[fn] !== "function") {
      console.error(`${fn} is not reachable — not the Trailmap app, or the script block failed to run. Aborting.`);
      return;
    }
  }
  if ($("#builderSheet") && $("#builderSheet").classList.contains("visible")) {
    console.error("Tourenbuilder mode is ON — switch it off in the header first (it hides every Tour). Aborting.");
    return;
  }
  if (!liftCards().length) {
    console.error('No lifts listed — activate "Bike Kingdom" and switch 🚡 Lifte on. Aborting.');
    return;
  }
  if (!cardFor("Hörnli-Express")) {
    console.error('Region "bikekingdom" is not active (Hörnli-Express is missing), or ids changed. Aborting.');
    return;
  }

  // Normalise the filters so the deltas below are not measured against a half-filtered map, and remember
  // what was there so it can be handed back at the end.
  const savedState = localStorage.getItem("trailmap-active-state-v1");
  clearSolo();
  for (const d of ["gruen", "blau", "rot", "schwarz"]) await setDiff(d, true);
  for (const s of ["showDownhillToggle", "showUphillToggle", "showLoopToggle", "showLiftsToggle",
                   "showPlacesToggle"]) await setSwitch(s, true);
  await setSwitch("showNamesToggle", false);
  await wait(250);

  const LIFTS_ON_MAP = standaloneLifts();
  const TOUR_STRETCHES = tourLiftStretches();
  const LIFT_CARDS = liftCards().length;

  // =====================================================================================
  // 1. SOLO HIDES LIFTS — reported twice, for two independent causes. Both are checked.
  //    (a) dimming the grey band could never work: it MASKS the base map's own aerialway line, so fading
  //        it just uncovers the tile's line at full strength. Lifts have to be removed.
  //    (b) a Tour's own lift stretches are exempt from the Tour's group styling (a width contrast a
  //        group-wide setStyle would flatten), which made them the one thing solo never reached.
  // =====================================================================================
  test("Solo auf einem Trail: kein einziges Liftsymbol bleibt uebrig");
  {
    ok("Vorbedingung: Lifte sind da", LIFTS_ON_MAP > 0 && TOUR_STRETCHES > 0,
       { standalone: LIFTS_ON_MAP, tour: TOUR_STRETCHES }, "both > 0");
    applySolo(T.trail);
    await wait(300);
    ok("(a) freistehende Lifte weg", standaloneLifts() === 0, standaloneLifts(), 0);
    ok("(b) Liftabschnitte der Touren weg", tourLiftStretches() === 0, tourLiftStretches(), 0);
    ok("keine graue Maske bleibt sichtbar", masks() === 0, masks(), 0);
    ok("die anderen Trails sind gedimmt, nicht entfernt", dimmedTrails() > 0, dimmedTrails(), "> 0");
    clearSolo();
    await wait(300);
    ok("danach alles zurueck", standaloneLifts() === LIFTS_ON_MAP && tourLiftStretches() === TOUR_STRETCHES,
       { standalone: standaloneLifts(), tour: tourLiftStretches() },
       { standalone: LIFTS_ON_MAP, tour: TOUR_STRETCHES });
    ok("nichts bleibt gedimmt", dimmedTrails() === 0, dimmedTrails(), 0);
  }

  test("Solo auf einer Tour behaelt genau die Lifte, die sie faehrt");
  {
    applySolo(T.tour615);
    await wait(300);
    ok("die 5 gefahrenen Lifte bleiben", standaloneLifts() === L.of615.length, standaloneLifts(), L.of615.length);
    for (const id of L.of615) ok(`  ${id} nicht von Solo versteckt`, liftHiddenBySolo(id) === false, liftHiddenBySolo(id), false);
    ok("ein nicht gefahrener Lift ist versteckt", liftHiddenBySolo(L.hoernli) === true, liftHiddenBySolo(L.hoernli), true);
    ok("eigene Liftabschnitte bleiben sichtbar", tourLiftStretches() === L.of615.length,
       tourLiftStretches(), L.of615.length);
    ok("fremde Liftabschnitte sind weg", tourLiftStretches() < TOUR_STRETCHES,
       { now: tourLiftStretches(), before: TOUR_STRETCHES }, "fewer");
    clearSolo();
    await wait(300);
  }

  // =====================================================================================
  // 2. EIN LIFT KANN SELBST DAS SOLO-ZIEL SEIN — one soloId for both object kinds, no second mechanism.
  // =====================================================================================
  test("Solo auf einem Lift: nur dieser bleibt, alle Trails gedimmt");
  {
    applySolo(L.hoernli);
    await wait(300);
    ok("genau ein freistehender Lift", standaloneLifts() === 1, standaloneLifts(), 1);
    ok("er selbst ist nicht versteckt", liftHiddenBySolo(L.hoernli) === false, liftHiddenBySolo(L.hoernli), false);
    ok("ein anderer schon", liftHiddenBySolo(L.rothorn1) === true, liftHiddenBySolo(L.rothorn1), true);
    ok("Trails sind gedimmt", dimmedTrails() > 0, dimmedTrails(), "> 0");
    ok("Liftabschnitte der Touren weg", tourLiftStretches() === 0, tourLiftStretches(), 0);
    clearSolo();
    await wait(300);
  }

  test("Der Solo-Button im Lift-Panel und auf der Karte gehen beide, und bleiben synchron");
  {
    const card = cardFor("Hörnli-Express");
    card.click();
    await wait(350);
    const panelBtn = () => $("#ipContent .solo-btn");
    ok("Panel hat einen Solo-Button", !!panelBtn(), !!panelBtn(), true);
    ok("er traegt data-lift-id", panelBtn().dataset.liftId === L.hoernli, panelBtn().dataset.liftId, L.hoernli);
    ok("die Karte ist ausgewaehlt", card.classList.contains("selected"), card.className, "selected");
    // The card's own button is revealed by CSS only while the card is selected -- a render()-time check
    // would go stale the moment the selection changes, which is why it is a CSS rule.
    const cardBtn = () => card.querySelector(".card-solo-btn");
    ok("Karten-Button ist sichtbar", getComputedStyle(cardBtn()).display !== "none",
       getComputedStyle(cardBtn()).display, "not none");
    panelBtn().click();
    await wait(300);
    ok("Solo greift", standaloneLifts() === 1, standaloneLifts(), 1);
    ok("Panel-Button aktiv", panelBtn().classList.contains("active"), panelBtn().className, "active");
    ok("Karten-Button ebenfalls aktiv", cardFor("Hörnli-Express").querySelector(".card-solo-btn").classList.contains("active"),
       cardFor("Hörnli-Express").querySelector(".card-solo-btn").className, "active");
    $("#ipContent .solo-btn").click();
    await wait(300);
    ok("wieder aus", standaloneLifts() === LIFTS_ON_MAP, standaloneLifts(), LIFTS_ON_MAP);
    $("#ipClose").click();
    await wait(150);
  }

  // =====================================================================================
  // 3. KEINE TOUR-AUSNAHME BEI DEN FILTERN — a lift ridden by a visible Tour used to stay on the map with
  //    the switch off and count as shown. Rejected: a rot trail inside a Tour is equally gone.
  // =====================================================================================
  test("🚡-Schalter aus: ALLE Lifte weg, auch die von sichtbaren Touren gefahrenen");
  {
    await setSwitch("showLiftsToggle", false);
    await wait(300);
    ok("kein freistehender Lift auf der Karte", standaloneLifts() === 0, standaloneLifts(), 0);
    ok("keine Liftkarte in der Liste", liftCards().length === 0, liftCards().length, 0);
    ok("ein von Tour 615 gefahrener Lift faellt durch", liftPassesFilters({ id: L.of615[0], region: "bk_park_chur" }) === false,
       liftPassesFilters({ id: L.of615[0], region: "bk_park_chur" }), false);
    ok("die Filterzeile nennt alle Lifte", num(/(\d+) Lifte/.exec(counts().filter)?.[0]) === LIFT_CARDS,
       counts().filter, `${LIFT_CARDS} Lifte ausgeblendet`);
    ok("die Touren zeichnen ihre Abschnitte weiter", tourLiftStretches() === TOUR_STRETCHES,
       tourLiftStretches(), TOUR_STRETCHES);
    // ...including the grey mask, which used to be borrowed from the lift object the exemption kept alive.
    ok("inklusive eigener Maske", masks() === TOUR_STRETCHES, masks(), TOUR_STRETCHES);
    await setSwitch("showLiftsToggle", true);
    await wait(300);
    ok("zurueck", standaloneLifts() === LIFTS_ON_MAP && liftCards().length === LIFT_CARDS,
       { map: standaloneLifts(), list: liftCards().length }, { map: LIFTS_ON_MAP, list: LIFT_CARDS });
  }

  // =====================================================================================
  // 4. NAMENSLABELS DER LIFTE — "Namen" an nahm einem vorher die einzige Moeglichkeit, einen Liftnamen zu
  //    lesen: das dauerhafte Label wurde nie geoeffnet, und der Hover oeffnete nur bei ausgeschaltetem Schalter.
  // =====================================================================================
  test("Namen an: jeder sichtbare Lift hat ein dauerhaftes Label");
  {
    ok("Namen aus: keine Liftlabels", liftLabels().length === 0, liftLabels().length, 0);
    await setSwitch("showNamesToggle", true);
    await wait(400);
    ok("eins pro Lift", liftLabels().length === LIFTS_ON_MAP, liftLabels().length, LIFTS_ON_MAP);
    ok("mit Namen darin", liftLabels().some((e) => /Hörnli/.test(e.textContent)),
       liftLabels()[0]?.textContent, "a lift name");
  }

  test("Hover laesst das Label stehen und markiert es in der Liftfarbe");
  {
    // Deselect first, or this case measures the wrong thing: closing a panel with the × deliberately KEEPS
    // the map selection (a trail keeps its outline and its card too), and a selected lift keeps its label
    // marked hover or not -- so the previous case leaves Hörnli marked and "unmarked on mouseleave" would
    // fail for a correct app. The suite made exactly that mistake first.
    closeInfoPanelAndDeselect();
    await wait(250);
    ok("Vorbedingung: nichts ist markiert", markedLabels().length === 0,
       markedLabels().map((e) => e.textContent.trim()), 0);
    const card = cardFor("Hörnli-Express");
    card.dispatchEvent(new MouseEvent("mouseenter"));
    await wait(200);
    const marked = markedLabels();
    ok("genau ein Label markiert", marked.length === 1, marked.map((e) => e.textContent.trim()), "1 marked");
    ok("es ist das gehoverte", /Hörnli/.test(marked[0]?.textContent || ""), marked[0]?.textContent, "Hörnli-Express");
    ok("Rand in der Liftfarbe, nicht rostrot", marked[0]?.style.borderColor === "rgb(0, 0, 0)",
       marked[0]?.style.borderColor, "rgb(0, 0, 0)");
    card.dispatchEvent(new MouseEvent("mouseleave"));
    await wait(250);
    ok("das Label bleibt offen", liftLabels().length === LIFTS_ON_MAP, liftLabels().length, LIFTS_ON_MAP);
    ok("nur die Markierung ist weg", markedLabels().length === 0, markedLabels().length, 0);
  }

  test("Ein ausgewaehlter Lift behaelt seine Markierung ohne Hover");
  {
    cardFor("Hörnli-Express").click();
    await wait(350);
    const marked = markedLabels();
    ok("markiert solange ausgewaehlt", marked.length === 1 && /Hörnli/.test(marked[0].textContent),
       marked.map((e) => e.textContent.trim()), "Hörnli-Express");
    $("#ipClose").click();
    await wait(150);
    // Solo re-adds the soloed lift's hit-line, and Leaflet re-opens a permanent tooltip on every re-add --
    // applyLiftVisibility has to decide open/closed itself there, because applySolo deliberately does not
    // call applyNameLabels (that would re-open the trail labels solo has just closed).
    applySolo(L.hoernli);
    await wait(350);
    ok("das Label des solo geschalteten Lifts bleibt", liftLabels().length === 1, liftLabels().length, 1);
    clearSolo();
    await wait(350);
    await setSwitch("showNamesToggle", false);
    await wait(300);
    ok("Namen aus: alle Liftlabels weg", liftLabels().length === 0, liftLabels().length, 0);
  }

  // =====================================================================================
  // 5. DIE DREI ZAEHLUNGEN — Trails/Lifte sagen, was sie listen; Filter sagt, was seine Einstellungen kosten.
  // =====================================================================================
  test("Zaehlungen: jede Zeile beantwortet nur ihre eigene Frage");
  {
    const base = counts();
    ok("Filter meldet nichts verdeckt", base.filter === "alles sichtbar", base.filter, "alles sichtbar");
    ok("Trails zaehlt Trails", /^\d+ Trails?$/.test(base.trails), base.trails, "N Trails");
    ok("Lifte zaehlt Lifte", num(base.lifts) === LIFT_CARDS, base.lifts, `${LIFT_CARDS} Lifte`);
    const trailsBefore = num(base.trails);
    await setDiff("schwarz", false);
    await wait(300);
    const c = counts();
    const hiddenNow = num(c.filter);
    // "schwarz" aus verdeckt Trails UND Touren, also steht der Trail-Posten am Anfang und nicht allein.
    ok("Filter nennt die ausgeblendeten Trails zuerst", /^\d+ Trails?\b/.test(c.filter) && /ausgeblendet$/.test(c.filter),
       c.filter, "N Trails · … ausgeblendet");
    ok("und die Summe stimmt", num(c.trails) + hiddenNow === trailsBefore,
       { shown: num(c.trails), hidden: hiddenNow }, `sum ${trailsBefore}`);
    ok("die Liftzahl bleibt davon unberuehrt", num(c.lifts) === LIFT_CARDS, c.lifts, `${LIFT_CARDS} Lifte`);
    await setSwitch("showLiftsToggle", false);
    await wait(300);
    // Every hidden kind gets its own term, in list order (Trails, Touren, Lifte). Turning "schwarz" off
    // hides Tours too, since a Tour has a difficulty like any trail -- so all three terms can appear.
    ok("jede Art steht als eigener Posten in einer Zeile",
       /^\d+ Trails? · \d+ Touren? · \d+ Lifte? ausgeblendet$/.test(counts().filter),
       counts().filter, "N Trails · M Touren · K Lifte ausgeblendet");
    await setSwitch("showLiftsToggle", true);
    await setDiff("schwarz", true);
    await wait(300);
    ok("zurueck auf alles sichtbar", counts().filter === "alles sichtbar", counts().filter, "alles sichtbar");
  }

  // =====================================================================================
  // 5b. TOUREN HABEN IHREN EIGENEN ABSCHNITT (2026-07-31) — zwischen Trails und Lifte. Eine Tour hat eine
  //     Schwierigkeit, wird aber nicht wie ein Trail danach sortiert: sie wird als ganzer Tag gewaehlt, und
  //     die Nummernserie einer Region ist die Ordnung, in der man sie sucht.
  // =====================================================================================
  test("Touren stehen in ihrem eigenen Abschnitt, nach Namen sortiert");
  {
    const secOrder = $$("aside > details").map((d) => d.id);
    ok("Abschnittsreihenfolge", String(secOrder) === "secTrails,secTouren,secLifts", String(secOrder),
       "secTrails,secTouren,secLifts");
    const tourNames = $$("#tourList .trail-card .trail-name").map((e) => e.textContent.replace("👁", "").trim());
    ok("Touren sind gelistet", tourNames.length > 0, tourNames.length, "> 0");
    ok("keine Tour mehr in der Trailliste", $$("#trailList .trail-card").every((c) => !/Biketicket/i.test(c.textContent)),
       $$("#trailList .trail-card").filter((c) => /Biketicket/i.test(c.textContent)).length, 0);
    // Das 🔁-Abzeichen ist weg: in einem Abschnitt, der nur Touren enthaelt, traegt es jede Karte und sagt nichts.
    ok("kein 🔁-Abzeichen in einer der beiden Listen",
       $$("#trailList .badge-loop").length + $$("#tourList .badge-loop").length === 0,
       $$("#trailList .badge-loop").length + $$("#tourList .badge-loop").length, 0);
    ok("aber das Schwierigkeitsabzeichen ist da", $$("#tourList .trail-card .badge").length === tourNames.length,
       $$("#tourList .trail-card .badge").length, tourNames.length);
    // Nach Namen, numerisch: 615 vor 616 vor den unnummerierten.
    const bk = tourNames.filter((n) => /Biketicket/i.test(n));
    const sorted = bk.slice().sort((a, b) => a.localeCompare(b, "de", { numeric: true }));
    ok("nach Namen sortiert, nicht nach Schwierigkeit", String(bk) === String(sorted), String(bk), String(sorted));
    ok("die Zaehlung nennt Touren", num(counts().touren) === tourNames.length, counts().touren, `${tourNames.length} Touren`);
    // Der Schwierigkeitsfilter greift auch hier -- eine Tour ist kein Lift.
    await setDiff("schwarz", false);
    await wait(350);
    ok("schwarz aus entfernt die schwarze Tour", !$$("#tourList .trail-card").some((c) => /schwarz/i.test(c.textContent)),
       $$("#tourList .trail-card").filter((c) => /schwarz/i.test(c.textContent)).length, 0);
    await setDiff("schwarz", true);
    await wait(350);
    // Eine Tour-Karte tut dasselbe wie eine Trail-Karte: fliegt hin, oeffnet das Panel, wird ausgewaehlt.
    const card = $$("#tourList .trail-card").find((c) => /615/.test(c.textContent));
    card.click();
    await wait(500);
    ok("Klick oeffnet die Tour", /615/.test($("#ipContent h3")?.textContent || ""), $("#ipContent h3")?.textContent.trim(), "615 …");
    ok("und waehlt ihre Karte aus", card.classList.contains("selected"), card.className, "selected");
    // Die Karten werden bei jedem render() neu gebaut -- die Auswahl muss auf die NEUE Karte wandern.
    render();
    await wait(400);
    const again = $$("#tourList .trail-card").find((c) => /615/.test(c.textContent));
    ok("Auswahl ueberlebt ein render()", again.classList.contains("selected"), again.className, "selected");
    $("#ipClose").click();
    await wait(200);
    closeInfoPanelAndDeselect();
    await wait(200);
  }

  // =====================================================================================
  // 6. LIFTE IM BUILDER — aus der Liste, nicht nur von der Karte. Der Hinweistext im Builder hat
  //    "auf der Karte oder in der Liste" immer versprochen, konnte es fuer Lifte aber nicht halten.
  // =====================================================================================
  test("Builder-Modus: eine Liftkarte haengt den Lift an, statt das Panel zu oeffnen");
  {
    $("#builderModeBtn").click();
    await wait(400);
    // The title doubles as the mode indicator. This line threw for a day because the <h1> had lost its id
    // while syncBuilderModeChrome() still wrote to it -- and since boot() calls that function whenever
    // builder mode was left on, the app came up as the fatal-error panel and nothing else.
    ok("Header-Titel zeigt den Modus", $("#appTitle").textContent === "Trailbuilder", $("#appTitle").textContent, "Trailbuilder");
    let threw = null;
    try { syncBuilderModeChrome(); } catch (e) { threw = String(e); }
    ok("syncBuilderModeChrome wirft nicht", threw === null, threw, null);
    $("#builderClearBtn").click();
    await wait(150);
    cardFor("Hörnli-Express").click();
    await wait(300);
    const rows = $$("#builderList .builder-row");
    ok("eine Zeile in der Builder-Liste", rows.length === 1, rows.length, 1);
    ok("und es ist der Lift", /Hörnli/.test(rows[0]?.textContent || ""), rows[0]?.textContent.trim(), "Hörnli-Express");
    ok("das Info-Panel bleibt zu", !$("#infoPanel").classList.contains("visible"),
       $("#infoPanel").className, "not visible");
    $("#builderClearBtn").click();
    await wait(150);
    $("#builderModeBtn").click();
    await wait(400);
    ok("Titel wieder zurueck", $("#appTitle").textContent === "Trailmap", $("#appTitle").textContent, "Trailmap");
  }

  // =====================================================================================
  // 7. BOOT-REIHENFOLGE — beide Fehler dieser Klasse betrafen den ERSTEN gezeichneten Frame, deshalb
  //    laufen sie in einem frischen iframe und nicht auf dieser Seite.
  //    (a) Ein Neuladen zeigte immer Orte, egal was der Schalter sagte: activateRegionGroup ruft
  //        applyPlaceVisibility(), boot() stellte den Zustand aber erst DANACH her -- also sah sie den
  //        Standardwert true, und danach ruft die Funktion nichts mehr auf.
  //    (b) Mit eingeschaltetem Builder-Modus kam die App ueberhaupt nicht mehr hoch: der Header-Titel hatte
  //        seine id verloren, syncBuilderModeChrome() schreibt sie aber weiter, und boot() ruft die Funktion
  //        genau dann. Ergebnis war das Fehlerpanel und sonst nichts -- ein Fall, den nur ein echter Start
  //        zeigt, weil das Umschalten im Betrieb danach trotzdem funktionierte.
  // =====================================================================================
  test("Frischer Start: 'Orte aus' bleibt aus, 'Orte an' kommt wieder");
  {
    ok("Vorbedingung: Orte sind hier sichtbar", placeLabels() > 0, placeLabels(), "> 0");
    const off = await bootFresh(({ state, put }) => put("state", { ...state, showPlaces: false }));
    const offLabels = off.doc.querySelectorAll(".place-label-tooltip").length;
    const offBox = off.doc.getElementById("showPlacesToggle").checked;
    const offTrails = off.doc.querySelectorAll("#trailList .trail-card").length;
    off.done();
    ok("die Kopie ist wirklich hochgekommen", offTrails > 0, offTrails, "> 0 trail cards");
    ok("keine Ortslabels", offLabels === 0, offLabels, 0);
    ok("und der Schalter zeigt es", offBox === false, offBox, false);
    // Gegenprobe, damit dieser Fall nicht auch bei einem iframe "gruen" meldet, das gar nichts zeichnet.
    const on = await bootFresh(({ state, put }) => put("state", { ...state, showPlaces: true }));
    const onLabels = on.doc.querySelectorAll(".place-label-tooltip").length;
    on.done();
    ok("mit 'Orte an' sind sie da", onLabels > 0, onLabels, "> 0");
  }

  test("Frischer Start im Builder-Modus laeuft bis zum Ende durch");
  {
    const b = await bootFresh(({ builder, put }) =>
      put("builder", { ...(builder || {}), builderMode: true, builderItems: [], builderSheetOpen: true }));
    const fatal = b.doc.getElementById("fatalError");
    const fatalShown = fatal ? b.doc.defaultView.getComputedStyle(fatal).display !== "none" : null;
    const title = b.doc.getElementById("appTitle")?.textContent;
    const cards = b.doc.querySelectorAll("#trailList .trail-card").length;
    const sheet = b.doc.getElementById("builderSheet")?.className;
    b.done();
    ok("kein Fehlerpanel", fatalShown === false, fatalShown, false);
    // Die drei Checks unten sind die eigentlichen: eine gefuellte Trailliste beweist NICHT, dass boot()
    // durchgelaufen ist -- activateRegionGroup ruft render() selbst, also stehen die Trails auch dann da,
    // wenn boot() danach abbricht. Genau so sah der #appTitle-Absturz aus, bevor boot() einen .catch bekam:
    // Trails auf der Karte, aber kein Titel, kein Builder-Sheet und keine wiederhergestellten Filter.
    ok("die Trailliste ist gefuellt", cards > 0, cards, "> 0");
    ok("der Titel zeigt den Modus", title === "Trailbuilder", title, "Trailbuilder");
    ok("das Builder-Sheet ist offen", /visible/.test(sheet || ""), sheet, "visible");
  }

  // ---------- restore + report ----------
  if (savedState) localStorage.setItem(STORE.state, savedState);

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
