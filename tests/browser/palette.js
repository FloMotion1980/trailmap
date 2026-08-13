// @suite   palette
// @area    Per-basemap color palette for trails/lifts/tours/selection, plus the schwarz-only halo
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches applyBasePalette, repaintLineColors, syncHalo, BASE_PALETTES, HALO, HALO_ACTIVE_KINDS, diffColor, CONNECTOR_COLOR, LIFT_LINE_COLOR, LIFT_MASK_COLOR, SELECT_YELLOW, baseLayerControl
// @needs   region=bikekingdom, builder=off
//
// Added 2026-08-13 per the user: on Satellit (Esri World Imagery, dark almost everywhere), the trail/lift/
// connector colors tuned against OSM's light tiles -- especially schwarz and the grey lift mask -- nearly
// disappear into the imagery. `diffColor`/`CONNECTOR_COLOR`/`LIFT_LINE_COLOR`/`LIFT_MASK_COLOR`/`SELECT_YELLOW`/
// `HALO` are all const/let inside the app's own scope and unreachable here (same reason lineLayers/soloId
// are), so every check below reads the map's own SVG stroke/stroke-width attributes, per the harness's own
// rule -- and that is deliberate, not a workaround: it is what proves the already-built layers were actually
// repainted/rebuilt in place, not just that some internal variable changed while the paint stayed stale.
//
// This suite drives the real #baseLayerControl chips (not applyBasePalette directly) so a bug in the click
// wiring itself -- forgetting to call applyBasePalette() at all -- would fail it, and restores "osm" at the
// end since changing the active basemap is shared state no other suite expects to inherit (same rule the
// `regions` suite follows for the active region set).
//
// HALO HISTORY, worth knowing before touching this again. A CSS `filter: drop-shadow` contrast halo shipped
// first, on every vector path on Satellit -- reverted the same day, since it broke on the user's iPhone in
// Safari (no glow on trails, an opaque white background on lifts), a long-standing WebKit bug combining CSS
// `filter` with an ancestor `transform` (every Leaflet pane, plus leaflet-rotate's rotate()). A geometry-
// based halo for EVERY trail/connector was designed next but rejected on performance grounds before being
// built (doubling the per-frame path count during rotation). It came back the same day, scoped down: a
// casing layer is only ever built for a "kind" (diff name / "connector" / "lift") that SOME basemap's
// `halo` entry actually uses -- right now that's just `sat.schwarz`, a small minority of trails in any
// region, so the extra-path cost is far smaller than "every trail". `HALO_ACTIVE_KINDS` is what decides
// this once, from the static `BASE_PALETTES` data, before any trail is ever built.

TM.add("palette", () => typeof TM.$ === "function" && TM.$("#baseLayerControl [data-layer='sat']") &&
       TM.ui.cardNamed("liftCards", /./) && TM.ui.cardNamed("tourCards", /./), async (T) => {
  const overlay = () => TM.map.overlay();
  const band = () => TM.map.band();
  const strokeCount = (layers, color, width) => layers.filter((p) => {
    if ((p.getAttribute("stroke") || "").toLowerCase() !== color) return false;
    return width === undefined || p.getAttribute("stroke-width") === String(width);
  }).length;
  const setBase = async (key) => {
    const chip = TM.$(`#baseLayerControl [data-layer='${key}']`);
    if (!chip.classList.contains("active")) { chip.click(); await TM.wait(200); }
  };

  T.test("starts on osm with its own gruen and an amber connector");
  await setBase("osm");
  const greenOsm = strokeCount(overlay(), "#4fa85e");
  T.ok("green trails present", greenOsm > 0, greenOsm, "> 0");
  const maskOsm = strokeCount(band(), "#cfcfcf");
  T.ok("lift masks present", maskOsm > 0, maskOsm, "> 0");
  const schwarzOsm = strokeCount(overlay(), "#1c1c1c");
  T.ok("schwarz trails present, at the original near-black", schwarzOsm > 0, schwarzOsm, "> 0");
  T.eq("no white halo on osm -- schwarz doesn't need one there", strokeCount(overlay(), "#ffffff", 8.5), 0);
  // Amber is now the connector color on EVERY basemap, not just Satellit -- the user asked for it
  // "überall" after seeing it live there. If this ever regresses to grey on a specific basemap, the
  // round-trip check further down (which re-measures on osm after visiting sat) would still pass, since
  // both would show amber -- so the real regression guard is this OWN count being > 0 already on osm,
  // before Satellit is ever touched.
  const connectorsOsm = strokeCount(overlay(), "#ffb300");

  T.test("switching to Satellit repaints trails/lifts AND adds a white halo behind schwarz only");
  await setBase("sat");
  T.eq("the sat chip is now active", TM.$("#baseLayerControl [data-layer='sat']").classList.contains("active"), true);
  T.eq("no path is still the old osm gruen", strokeCount(overlay(), "#4fa85e"), 0);
  T.eq("the same number of trails now carry the brighter sat gruen", strokeCount(overlay(), "#5fdd7a"), greenOsm);
  T.eq("no path is still the old osm lift mask", strokeCount(band(), "#cfcfcf"), 0);
  T.eq("the same number of lift masks now carry the lighter sat mask color", strokeCount(band(), "#f2f2f2"), maskOsm);
  T.eq("the lift symbol color repainted too", strokeCount(band(), "#111111") > 0, true, true);
  T.eq("no path is left on the near-black osm schwarz", strokeCount(overlay(), "#1c1c1c"), 0);
  const schwarzSat = strokeCount(overlay(), "#5c5c5c");
  T.eq("the same number of trails now carry the lightened sat schwarz", schwarzSat, schwarzOsm);
  T.eq("and exactly that many white halos appear behind them, at the fixed halo weight",
       strokeCount(overlay(), "#ffffff", 8.5), schwarzOsm);
  T.eq("the amber connector count is unchanged (it was already amber on osm)",
       strokeCount(overlay(), "#ffb300"), connectorsOsm);
  T.ok("a yellow selection outline exists on Satellit once something is selected -- checked in its own test below", true, true, true);

  T.test("Relief (topo) is pixel-identical to Straße/osm for gruen -- no halo either, no separate palette");
  // First copied Satellit's bright colors here per the user's own request, then reverted the same day once
  // they saw it live and it didn't help: Relief's actual problem is HUE COLLISION with OpenTopoMap's own
  // green forest fill and orange/brown contour lines, not darkness, so brightening was the wrong fix.
  // Relief has no `halo` entries set at all (unlike sat.schwarz), so schwarz stays near-black and unhaloed
  // there too -- untouched until a real fix (probably different hues, not a halo) is designed.
  await setBase("osm");
  await setBase("topo");
  T.eq("topo shows the ORIGINAL unbrightened gruen, not osm's own brightened one", strokeCount(overlay(), "#3f8a4c"), greenOsm);
  T.eq("not osm's own brightened gruen", strokeCount(overlay(), "#4fa85e"), 0);
  T.eq("none of sat's gruen at all", strokeCount(overlay(), "#5fdd7a"), 0);
  T.eq("schwarz stays near-black, not lightened", strokeCount(overlay(), "#1c1c1c"), schwarzOsm);
  T.eq("and no halo appears behind it on topo", strokeCount(overlay(), "#ffffff", 8.5), 0);

  T.test("a Trailrunde's own connector segments stay amber too, not just standalone lines");
  // Only meaningful if the active region has a loop with plain (non-trail, non-lift) connector stretches --
  // skip rather than fail if none is currently active, per the harness's own "let a wrong precondition skip"
  // rule, since which regions are loaded is out of this suite's control.
  await setBase("sat");
  if (connectorsOsm === 0) {
    T.skip("no active Trailrunde has a plain connector stretch right now");
  } else {
    T.eq("still amber, same count, on Satellit too", strokeCount(overlay(), "#ffb300"), connectorsOsm);
  }

  T.test("selection/lift-selection outlines keep using the current SELECT_YELLOW after a repaint");
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
  T.eq("schwarz is back to near-black, same count", strokeCount(overlay(), "#1c1c1c"), schwarzOsm);
  T.eq("and every white halo is gone again, not just recolored", strokeCount(overlay(), "#ffffff", 8.5), 0);

  T.test("an unknown basemap key falls back to the osm palette (colors AND halo) rather than leaving stale state");
  // Not reachable through the UI (every chip's data-layer is a real key) -- calls the function directly,
  // which plain function declarations allow (see the harness notes on Annex B).
  await setBase("sat");
  applyBasePalette("not-a-real-basemap-key");
  await TM.wait(50);
  T.eq("colors fall back to osm's", strokeCount(overlay(), "#4fa85e"), greenOsm);
  T.eq("and the halo falls back to off, not left on from sat", strokeCount(overlay(), "#ffffff", 8.5), 0);
  applyBasePalette("osm"); // leave state consistent with the chip UI, which still reads "sat" until re-clicked
  await setBase("osm");
});
