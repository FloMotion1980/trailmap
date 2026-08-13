// @suite   palette
// @area    Per-basemap color palette for trails/lifts/tours/selection
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches applyBasePalette, repaintLineColors, BASE_PALETTES, diffColor, CONNECTOR_COLOR, LIFT_LINE_COLOR, LIFT_MASK_COLOR, SELECT_YELLOW, baseLayerControl
// @needs   region=bikekingdom, builder=off
//
// Added 2026-08-13 per the user: on Satellit (Esri World Imagery, dark almost everywhere), the trail/lift/
// connector colors tuned against OSM's light tiles -- especially schwarz and the grey lift mask -- nearly
// disappear into the imagery. `diffColor`/`CONNECTOR_COLOR`/`LIFT_LINE_COLOR`/`LIFT_MASK_COLOR`/`SELECT_YELLOW`
// are all const/let inside the app's own scope and unreachable here (same reason lineLayers/soloId are), so
// every check below reads the map's own SVG stroke attributes, per the harness's own rule -- and that is
// deliberate, not a workaround: it is what proves the already-built layers were actually repainted in place,
// not just that some internal variable changed while the paint stayed stale.
//
// This suite drives the real #baseLayerControl chips (not applyBasePalette directly) so a bug in the click
// wiring itself -- forgetting to call applyBasePalette() at all -- would fail it, and restores "osm" at the
// end since changing the active basemap is shared state no other suite expects to inherit (same rule the
// `regions` suite follows for the active region set).
//
// NO HALO HERE ON PURPOSE. A CSS `filter: drop-shadow` contrast halo was tried and reverted the same day --
// it broke on the user's iPhone in Safari (no glow on trails, an opaque white background on lifts), a
// long-standing WebKit bug combining CSS `filter` with an ancestor `transform` (every Leaflet pane, plus
// leaflet-rotate's rotate()). A geometry-based halo (a second polyline behind each trail, like
// `selectionOutline`'s own yellow ring) would have rendered correctly everywhere but was rejected on
// performance grounds before being built -- leaflet-rotate repaints every vector path's viewBox per degree
// turned, and a second polyline per trail/connector would double that per-frame cost. So Satellit's contrast
// is carried by COLOR CHOICE ALONE: brighter gruen/blau/rot, an amber connector, and a lightened schwarz
// (#5c5c5c, not near-black) -- there is nothing here to assert about a halo, deliberately.

TM.add("palette", () => typeof TM.$ === "function" && TM.$("#baseLayerControl [data-layer='sat']") &&
       TM.ui.cardNamed("liftCards", /./) && TM.ui.cardNamed("tourCards", /./), async (T) => {
  const overlay = () => TM.map.overlay();
  const band = () => TM.map.band();
  const strokeCount = (layers, color) => layers.filter((p) => (p.getAttribute("stroke") || "").toLowerCase() === color).length;
  const setBase = async (key) => {
    const chip = TM.$(`#baseLayerControl [data-layer='${key}']`);
    if (!chip.classList.contains("active")) { chip.click(); await TM.wait(200); }
  };

  T.test("starts on osm with its own (slightly brightened) gruen");
  await setBase("osm");
  const greenOsm = strokeCount(overlay(), "#4fa85e");
  T.ok("at least one gruen trail is on the map to repaint", greenOsm > 0, greenOsm, "> 0");
  const maskOsm = strokeCount(band(), "#cfcfcf");
  T.ok("at least one lift mask is on the map to repaint", maskOsm > 0, maskOsm, "> 0");

  T.test("switching to Satellit repaints every already-built trail/lift line");
  await setBase("sat");
  T.eq("the sat chip is now active", TM.$("#baseLayerControl [data-layer='sat']").classList.contains("active"), true);
  T.eq("no path is still the old osm gruen", strokeCount(overlay(), "#4fa85e"), 0);
  T.eq("the same number of trails now carry the brighter sat gruen", strokeCount(overlay(), "#5fdd7a"), greenOsm);
  T.eq("no path is still the old osm lift mask", strokeCount(band(), "#cfcfcf"), 0);
  T.eq("the same number of lift masks now carry the lighter sat mask color", strokeCount(band(), "#f2f2f2"), maskOsm);
  T.eq("the lift symbol color repainted too", strokeCount(band(), "#111111") > 0, true, true);

  T.test("schwarz is lightened on Satellit, not left as near-black");
  // #5c5c5c is a plain hex the app can genuinely paint, unlike #1c1c1c which the old design relied on a
  // (now-removed) halo to make visible -- if a future edit brings the halo idea back without also
  // reverting schwarz, this is the check that would catch schwarz quietly going invisible again.
  T.ok("no path is left on the near-black osm schwarz while on Satellit",
       strokeCount(overlay(), "#1c1c1c") === 0, strokeCount(overlay(), "#1c1c1c"), 0);

  T.test("a Trailrunde's own connector segments repaint too, not just standalone lines");
  // Only meaningful if the active region has a loop with plain (non-trail, non-lift) connector stretches --
  // skip rather than fail if none is currently active, per the harness's own "let a wrong precondition skip"
  // rule, since which regions are loaded is out of this suite's control.
  await setBase("osm");
  const connectorsOnOsm = strokeCount(overlay(), "#5a5a5a");
  await setBase("sat");
  if (connectorsOnOsm === 0) {
    T.skip("no active Trailrunde has a plain connector stretch right now");
  } else {
    T.eq("no connector is still the old grey", strokeCount(overlay(), "#5a5a5a"), 0);
    T.eq("the same number now carry the sat amber connector color", strokeCount(overlay(), "#ffb300"), connectorsOnOsm);
  }

  T.test("Relief (topo) keeps the ORIGINAL, pre-brightening gruen -- same as Straße hell/carto");
  // First copied Satellit's bright colors here per the user's own request, then reverted the same day once
  // they saw it live and it didn't help: Relief's actual problem is HUE COLLISION with OpenTopoMap's own
  // green forest fill and orange/brown contour lines, not darkness, so brightening was the wrong fix. A
  // real halo (which contour-line clutter would actually benefit from) was rejected on performance grounds.
  // Relief is therefore untouched -- NOT the same as "osm" (which got brightened separately, per the user,
  // for "Straße" specifically) but the original #3f8a4c shared with carto -- until a real fix is designed.
  await setBase("osm");
  await setBase("topo");
  T.eq("topo shows the original unbrightened gruen", strokeCount(overlay(), "#3f8a4c"), greenOsm);
  T.eq("not osm's own brightened gruen", strokeCount(overlay(), "#4fa85e"), 0);
  T.eq("and none of sat's gruen at all", strokeCount(overlay(), "#5fdd7a"), 0);

  T.test("selection/lift-selection outlines keep using the current SELECT_YELLOW after a repaint");
  await setBase("sat");
  // Both palettes currently share #fff200, so this is a regression guard for repaintLineColors() actually
  // calling setStyle on the two outlines, not a color-change assertion -- a future palette that changes
  // selectYellow would need a real color-difference check here instead.
  const card = TM.ui.trailCards()[0] || TM.ui.tourCards()[0];
  card.click();
  await TM.wait(300);
  T.ok("a yellow selection outline exists on Satellit", TM.map.selectionOutlines() > 0, TM.map.selectionOutlines(), "> 0");
  closeInfoPanelAndDeselect();
  await TM.wait(150);

  T.test("switching back to osm round-trips every color exactly, nothing left stuck on the sat palette");
  await setBase("osm");
  T.eq("gruen trails are back to the original osm color, same count", strokeCount(overlay(), "#4fa85e"), greenOsm);
  T.eq("no trail is left on the sat gruen", strokeCount(overlay(), "#5fdd7a"), 0);
  T.eq("lift masks are back to the original osm color, same count", strokeCount(band(), "#cfcfcf"), maskOsm);
  T.eq("no lift mask is left on the sat color", strokeCount(band(), "#f2f2f2"), 0);

  T.test("an unknown basemap key falls back to the osm palette rather than leaving stale colors");
  // Not reachable through the UI (every chip's data-layer is a real key) -- calls the function directly,
  // which plain function declarations allow (see the harness notes on Annex B).
  await setBase("sat");
  applyBasePalette("not-a-real-basemap-key");
  await TM.wait(50);
  T.eq("colors fall back to osm's", strokeCount(overlay(), "#4fa85e"), greenOsm);
  applyBasePalette("osm"); // leave state consistent with the chip UI, which still reads "sat" until re-clicked
  await setBase("osm");
});
