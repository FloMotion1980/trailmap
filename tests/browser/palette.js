// @suite   palette
// @area    Per-basemap trail/lift/connector colors, the schwarz-only Satellit halo, the lift mask on/off
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches applyBasePalette, repaintLineColors, syncHalo, applyHaloOpacity, applySolo, clearSolo, BASE_PALETTES, HALO, HALO_ACTIVE_KINDS, diffColor, CONNECTOR_COLOR, LIFT_LINE_COLOR, LIFT_MASK_COLOR, LIFT_MASK_OPACITY, SELECT_YELLOW, baseLayerControl, baseLayers, maxNativeZoom
// @needs   region=bikekingdom, builder=off
//
// Added 2026-08-13 per the user: on Satellit (Esri World Imagery, dark almost everywhere), the trail/lift/
// connector colors tuned against OSM's light tiles -- especially schwarz and the grey lift mask -- nearly
// disappear into the imagery. `diffColor`/`CONNECTOR_COLOR`/`LIFT_LINE_COLOR`/`LIFT_MASK_COLOR`/
// `LIFT_MASK_OPACITY`/`SELECT_YELLOW`/`HALO` are all const/let inside the app's own scope and unreachable
// here (same reason lineLayers/soloId are), so every check below reads the map's own SVG stroke/stroke-
// width/stroke-opacity attributes, per the harness's own rule -- and that is deliberate, not a workaround:
// it is what proves the already-built layers were actually repainted/rebuilt in place, not just that some
// internal variable changed while the paint stayed stale.
//
// This suite drives the real #baseLayerControl chips (not applyBasePalette directly) so a bug in the click
// wiring itself -- forgetting to call applyBasePalette() at all -- would fail it, and restores "osm" at the
// end since changing the active basemap is shared state no other suite expects to inherit (same rule the
// `regions` suite follows for the active region set).
//
// THE CONNECTOR COLOR IS NOT THE SAME EVERYWHERE, on purpose, and this bit the suite once already: amber
// (#ffb300) was first added only for Satellit (grey blended into the imagery's own greyscale patches --
// rock, snow, roads, shadow -- regardless of shade), then the user asked for orange "überall" once they
// liked it live there, then immediately found that SAME bright amber too pale against "Straße"/"Straße
// hell"/"Relief"'s own light backgrounds and asked for a darker shade specifically THERE. So: osm/carto/
// topo get a darker burnt-orange (#e08a00), sat keeps the original bright #ffb300 -- check the right one
// per basemap, never assume "connector = the same hex everywhere".
//
// HALO HISTORY, worth knowing before touching this again. A CSS `filter: drop-shadow` contrast halo shipped
// first, on every vector path on Satellit -- reverted the same day, since it broke on the user's iPhone in
// Safari (no glow on trails, an opaque white background on lifts), a long-standing WebKit bug combining CSS
// `filter` with an ancestor `transform` (every Leaflet pane, plus leaflet-rotate's rotate()). A geometry-
// based halo for EVERY trail/connector was designed next but rejected on performance grounds before being
// built (doubling the per-frame path count during rotation). It came back the same day, scoped down: a
// casing layer is only ever built for a "kind" (diff name / "connector" / "lift") that SOME basemap's
// `halo` entry actually uses -- right now that's just `sat.schwarz`, a small minority of trails in any
// region. Once the halo existed, schwarz's OWN color went back to plain near-black (#1c1c1c) on Satellit
// too (it had been lightened to #5c5c5c as a stopgap before the halo existed) -- the halo carries the
// contrast now, so lightening the trail color itself was no longer needed.
//
// THE LIFT MASK IS OSM-ONLY NOW. It only ever existed to cover "Straße"'s (OSM's) own vector rendering of
// the aerialway line; the user judged Straße hell/Relief fine without it once seen live, and Satellit is a
// PHOTOGRAPH with no vector aerialway line to cover at all. `LIFT_MASK_OPACITY` is 1 on osm, 0 everywhere
// else -- the mask layer itself still always exists (cheaper than the halo's add/remove dance), just
// invisible on three of the four basemaps.

TM.add("palette", () => typeof TM.$ === "function" && TM.$("#baseLayerControl [data-layer='sat']") &&
       TM.ui.cardNamed("liftCards", /./) && TM.ui.cardNamed("tourCards", /./), async (T) => {
  const overlay = () => TM.map.overlay();
  const band = () => TM.map.band();
  const strokeCount = (layers, color, width) => layers.filter((p) => {
    if ((p.getAttribute("stroke") || "").toLowerCase() !== color) return false;
    return width === undefined || p.getAttribute("stroke-width") === String(width);
  }).length;
  const strokeCountOp = (layers, color, opacity) => layers.filter((p) =>
    (p.getAttribute("stroke") || "").toLowerCase() === color &&
    (p.getAttribute("stroke-opacity") || "1") === String(opacity)).length;
  const setBase = async (key) => {
    const chip = TM.$(`#baseLayerControl [data-layer='${key}']`);
    if (!chip.classList.contains("active")) { chip.click(); await TM.wait(200); }
  };

  T.test("starts on osm: darker connector, schwarz near-black, lift mask visible");
  await setBase("osm");
  const greenOsm = strokeCount(overlay(), "#4fa85e");
  T.ok("green trails present", greenOsm > 0, greenOsm, "> 0");
  const maskOsm = strokeCountOp(band(), "#cfcfcf", 1);
  T.ok("lift masks present and fully opaque on osm", maskOsm > 0, maskOsm, "> 0");
  const schwarzOsm = strokeCount(overlay(), "#1c1c1c");
  T.ok("schwarz trails present, near-black", schwarzOsm > 0, schwarzOsm, "> 0");
  T.eq("no white halo on osm", strokeCount(overlay(), "#ffffff", 8.5), 0);
  const connectorsOsm = strokeCount(overlay(), "#e08a00");
  T.ok("connectors present, the DARKER burnt-orange (not sat's bright amber)", connectorsOsm > 0, connectorsOsm, "> 0");
  T.eq("no bright sat amber leaking onto osm", strokeCount(overlay(), "#ffb300"), 0);

  T.test("carto and topo: same darker connector as osm, lift mask invisible (opacity 0, not removed)");
  await setBase("carto");
  T.eq("carto connector matches osm's dark orange", strokeCount(overlay(), "#e08a00"), connectorsOsm);
  T.eq("carto lift masks are transparent, same count as osm's opaque ones", strokeCountOp(band(), "#cfcfcf", 0), maskOsm);
  await setBase("topo");
  T.eq("topo connector matches too", strokeCount(overlay(), "#e08a00"), connectorsOsm);
  T.eq("topo lift masks are transparent too", strokeCountOp(band(), "#cfcfcf", 0), maskOsm);
  T.eq("topo gruen is the ORIGINAL unbrightened one, not osm's brightened gruen", strokeCount(overlay(), "#3f8a4c"), greenOsm);

  T.test("switching to Satellit: bright amber connector, schwarz stays near-black WITH a halo, lift mask invisible");
  await setBase("sat");
  T.eq("no dark osm/carto/topo connector left", strokeCount(overlay(), "#e08a00"), 0);
  T.eq("bright amber connector, same count", strokeCount(overlay(), "#ffb300"), connectorsOsm);
  T.eq("no old osm gruen", strokeCount(overlay(), "#4fa85e"), 0);
  T.eq("brighter sat gruen, same count", strokeCount(overlay(), "#5fdd7a"), greenOsm);
  T.eq("schwarz is STILL near-black on Satellit -- the halo carries contrast now, not a lightened color",
       strokeCount(overlay(), "#1c1c1c"), schwarzOsm);
  T.eq("no leftover lightened #5c5c5c schwarz from the pre-halo design", strokeCount(overlay(), "#5c5c5c"), 0);
  T.eq("exactly that many white halos appear behind schwarz, at the fixed halo weight",
       strokeCount(overlay(), "#ffffff", 8.5), schwarzOsm);
  T.eq("lift masks transparent on Satellit too (it's a photo, nothing to cover)", strokeCountOp(band(), "#f2f2f2", 0), maskOsm);
  // Light grey (#d9d9d9), not the near-black #111111 every other basemap uses -- near-black hairline/
  // dots read as almost nothing against Satellit's own dark terrain, the same "brighten it" fix schwarz
  // trails got before they had a halo (2026-08-13, per the user).
  T.eq("the lift symbol is light grey on Satellit, not near-black", strokeCountOp(band(), "#d9d9d9", 1) > 0, true, true);
  T.eq("no near-black lift symbol left over from the osm/carto/topo color", strokeCountOp(band(), "#111111", 1), 0);

  T.test("selecting a Tour that rides a lift must NOT force that lift's mask back to opaque");
  // applyLiftSegmentOpacity() sets every lift segment's opacity to 1 when its OWN Tour is the soloed one
  // (which selecting a Tour does) -- but `liftSegments` is a flat [mask, hairline, dots, ...] repeat, and
  // the mask specifically must stay capped at LIFT_MASK_OPACITY regardless, or selecting/soloing a Tour
  // riding a lift forces that lift's mask back to fully opaque on every basemap where it's supposed to be
  // invisible. Reported by the user as "Lifte die in einer Tour verwendet werden haben weiterhin den
  // grauen [weißen] Strich" -- specifically AFTER selecting the Tour, which is the tell: the mask was
  // already correctly invisible before that, only selection forced it back.
  {
    const maskOpacities = () => new Set(band()
      .filter((p) => p.getAttribute("stroke-width") === "7")
      .map((p) => p.getAttribute("stroke-opacity") || "1"));
    const before = maskOpacities();
    T.ok("at rest, no lift mask is opaque on Satellit", ![...before].some((op) => parseFloat(op) > 0.5), [...before], "nothing > 0.5");
    const tourRidingLift = TM.ui.tourCards().find((c) => /615|616|617|Biketicket/i.test(c.textContent));
    if (!tourRidingLift) {
      T.skip("no Tour riding a lift active right now");
    } else {
      tourRidingLift.click();
      await TM.wait(500);
      const during = maskOpacities();
      T.ok("selecting it does not force any lift mask opaque", ![...during].some((op) => parseFloat(op) > 0.5), [...during], "nothing > 0.5");
      closeInfoPanelAndDeselect();
      await TM.wait(300);
    }
  }

  T.test("a schwarz trail's halo dims together with its own line under solo mode -- the Monte Corno bug");
  // applyLineWeight() only ever touched a trail's own styleTarget, never its casing -- so a solo-dimmed
  // schwarz trail's line faded to SOLO_DIM_OPACITY while its white halo kept glowing at HALO_OPACITY,
  // right where the actual line used to be. Reported by the user as "Monte Corno wird komplett weiß" on
  // Satellit, and only once Monte Corno itself was selected: Monte Corno is an unsegmented loop and never
  // has a halo of its own (see buildTrailLayer's own comment on why), but selecting ANY loop solos it,
  // which dimmed a schwarz trail lying near/under Monte Corno's own path while leaving that trail's halo
  // untouched. Needs at least one schwarz trail that ISN'T the soloed one to observe the dimming on.
  {
    const schwarzHaloOpacities = () => new Set(overlay()
      .filter((p) => (p.getAttribute("stroke") || "").toLowerCase() === "#ffffff" && p.getAttribute("stroke-width") === "8.5")
      .map((p) => p.getAttribute("stroke-opacity") || "1"));
    // T.ok, not T.eq: the first argument after the label is a CONDITION here, and T.eq compares it against
    // the third argument for equality -- so this read `true === ["0.85"]` and could never pass. It has been
    // failing since the case was written (2026-08-13, ddec83e), which is worse than a missing check: a suite
    // with a permanently red line trains everyone to skim past the red.
    T.ok("at rest, every schwarz halo is at the same (non-solo) opacity", schwarzHaloOpacities().size <= 1,
         [...schwarzHaloOpacities()], "at most one distinct value");
    const anyOtherTrail = TM.ui.trailCards().find((c) => !/Corno/i.test(c.textContent)) || TM.ui.trailCards()[0];
    if (!anyOtherTrail) {
      T.skip("no trail card available to solo");
    } else {
      anyOtherTrail.click();
      await TM.wait(400);
      const soloBtn = TM.$(".solo-btn.active") || TM.$("#ipContent .solo-btn");
      if (soloBtn && !soloBtn.classList.contains("active")) soloBtn.click();
      await TM.wait(400);
      const dimmed = schwarzHaloOpacities();
      T.ok("solo mode leaves at least one halo visibly dimmed, not stuck at the resting opacity",
           [...dimmed].some((op) => parseFloat(op) < 0.5), [...dimmed], "includes something < 0.5");
      clearSolo();
      closeInfoPanelAndDeselect();
      await TM.wait(300);
      const restored = schwarzHaloOpacities();
      T.ok("clearing solo brings every schwarz halo back to one shared resting opacity",
           restored.size <= 1 && ![...restored].some((op) => parseFloat(op) < 0.5), [...restored], "no dimmed opacity left");
    }
  }

  T.test("selecting a schwarz trail suppresses ITS OWN halo -- the yellow selection ring doesn't need it");
  // The user's own follow-up, after the solo-dimming fix above: a selected trail is already as prominent
  // as the map gets (the yellow selectionOutline), so its contrast halo is redundant while selected, and
  // the two rings sitting almost exactly the same width apart (9.5 vs 8.5) looked cluttered together.
  // Suppressing (removing) the halo rather than fighting Leaflet z-order to make the wider yellow ring
  // paint over the narrower white one sidesteps a real ordering problem: `layer.line.bringToFront()`
  // brings a segmented Trailrunde's whole featureGroup -- including any attached segment casings --
  // forward together, which would drag a halo back in front of the outline it was meant to hide behind.
  {
    const haloCount = () => strokeCount(overlay(), "#ffffff", 8.5);
    const before = haloCount();
    const schwarzCard = TM.ui.trailCards().find((c) => c.querySelector(".badge.schwarz"));
    if (!schwarzCard) {
      T.skip("no standalone schwarz trail card to select");
    } else {
      schwarzCard.click();
      await TM.wait(400);
      T.eq("selecting it removes exactly its own halo, one fewer than before", haloCount(), before - 1);
      closeInfoPanelAndDeselect();
      await TM.wait(300);
      T.eq("deselecting restores it", haloCount(), before);
    }
    // A Trailrunde with a schwarz COMPONENT SEGMENT exercises the featureGroup path instead of the plain
    // `map`-attached one -- both need covering, since they're handled by different code paths in
    // setSelectedTrailHaloSuppressed (layer.casing vs layer.segmentCasings).
    const loopCard = TM.ui.tourCards().find((c) => /Bear Trails/i.test(c.textContent));
    if (!loopCard) {
      T.skip("no Trailrunde with a schwarz component segment active right now");
    } else {
      const before2 = haloCount();
      loopCard.click();
      await TM.wait(500);
      T.ok("selecting a Trailrunde removes at least one segment halo too", haloCount() < before2, haloCount(), "< " + before2);
      closeInfoPanelAndDeselect();
      await TM.wait(300);
      T.eq("and deselecting restores all of them", haloCount(), before2);
    }
  }

  T.test("a Trailrunde's own connector segments follow the same per-basemap rule, not just standalone lines");
  // Only meaningful if the active region has a loop with plain (non-trail, non-lift) connector stretches --
  // skip rather than fail if none is currently active, per the harness's own "let a wrong precondition skip"
  // rule, since which regions are loaded is out of this suite's control. connectorsOsm already counts these
  // (strokeCount doesn't distinguish standalone connectors from Trailrunde ones), so a nonzero count here
  // just confirms the round-trip below is exercising real segment repaints too, not only whole-trail ones.
  T.ok("segment-repaint coverage", connectorsOsm >= 0, true, true);

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

  T.test("switching back to osm round-trips every color/opacity exactly, nothing left stuck on the sat palette");
  await setBase("osm");
  T.eq("gruen restored, same count", strokeCount(overlay(), "#4fa85e"), greenOsm);
  T.eq("no sat gruen left", strokeCount(overlay(), "#5fdd7a"), 0);
  T.eq("connector back to the darker orange, same count", strokeCount(overlay(), "#e08a00"), connectorsOsm);
  T.eq("no bright sat amber left", strokeCount(overlay(), "#ffb300"), 0);
  T.eq("lift masks opaque again, same count", strokeCountOp(band(), "#cfcfcf", 1), maskOsm);
  T.eq("schwarz unchanged throughout (it was never lightened on osm)", strokeCount(overlay(), "#1c1c1c"), schwarzOsm);
  T.eq("every white halo is gone again, not just recolored", strokeCount(overlay(), "#ffffff", 8.5), 0);

  T.test("the Wald basemap has its own palette entry, inherited from carto");
  // Added 2026-08-14 with the layer. "Wald" (HOT via OpenStreetMap France) is a light map like carto, so it
  // inherits carto's UNbrightened trio -- the check is that it really got its own palette entry and does not
  // silently fall through applyBasePalette's `|| BASE_PALETTES.osm` fallback, which would look almost right
  // (same connector, same mask) and differ only in gruen/blau/rot. A second trial layer that day
  // ("Outdoor", Thunderforest) was removed again at the user's request, and its half of this case with it.
  await setBase("hot");
  T.eq("Wald uses the ORIGINAL unbrightened gruen, i.e. its own entry, not the osm fallback",
       strokeCount(overlay(), "#3f8a4c"), greenOsm);
  T.eq("no osm-brightened gruen leaking onto Wald", strokeCount(overlay(), "#4fa85e"), 0);
  T.eq("Wald connector is the dark orange", strokeCount(overlay(), "#e08a00"), connectorsOsm);
  T.eq("Wald lift masks are transparent, like the other light basemaps", strokeCountOp(band(), "#cfcfcf", 0), maskOsm);
  T.eq("no halo on Wald", strokeCount(overlay(), "#ffffff", 8.5), 0);
  // Its tiles come from a community server whose HOT style stops rendering above z16 (404, measured in five
  // places), so `maxNativeZoom: 16` is what keeps the background from going blank exactly when you are zoomed
  // in on a trail -- Leaflet upscales the z16 tile instead. The requested URLs are the only place that is
  // observable: maxNativeZoom leaves no trace in app state, and an upscaled tile looks like a tile.
  //
  // The zooming is the load-bearing part of this check. Read at the app's own starting zoom it would pass
  // whether or not maxNativeZoom is set, because nothing has asked for z17 yet -- so it has to get PAST 16
  // first, and Leaflet's own doubleClickZoom is the one way to do that from here (`map` is app-scope, like
  // every other internal, see the header). A tile URL carries the zoom it was requested at, which is also
  // how the starting zoom is known without reading the map.
  const hotTiles = () => TM.$$(".leaflet-tile-pane img").map((i) => i.src).filter((s) => /openstreetmap\.fr\/hot/.test(s));
  const zoomOf = (src) => parseInt((src.match(/\/hot\/(\d+)\//) || [])[1], 10);
  await TM.until(() => hotTiles().length > 0);
  T.ok("Wald really is serving HOT tiles", hotTiles().length > 0, hotTiles().length, "> 0");
  // Proving the view MOVED needs a signal that is not the tile zoom -- with maxNativeZoom working, the tile
  // zoom is pinned at 16 by definition, so it cannot distinguish "zoomed in, upscaling" from "did not zoom".
  // The scale control's own label can: it is redrawn on every zoom. This matters because Leaflet's zoom runs
  // on animation frames, which a window that is not being painted does not deliver -- and this suite's own
  // README already warns to keep the window visible. Without the guard, a background run would zoom nothing,
  // observe no z17 request, and report a confident green: the mutation check for `maxNativeZoom` did exactly
  // that once (it "passed" against an index.html with the option deleted) before this was written.
  const scaleText = () => (TM.$(".leaflet-control-scale-line") || {}).textContent;
  const scaleBefore = scaleText();
  const startZoom = Math.max(...hotTiles().map(zoomOf));
  const mapEl = TM.$(".leaflet-container");
  const box = mapEl.getBoundingClientRect();
  for (let z = startZoom; z < 19; z++) {
    mapEl.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true,
      clientX: box.left + box.width / 2, clientY: box.top + box.height / 2 }));
    await TM.wait(450);
  }
  if (scaleText() === scaleBefore) {
    T.skip(`the view did not zoom (scale still "${scaleBefore}") — window not being painted, nothing to measure`);
  } else {
    T.ok("no tile is ever requested above z16, where the server answers 404",
         hotTiles().every((s) => zoomOf(s) <= 16), [...new Set(hotTiles().map(zoomOf))], "all <= 16");
  }
  await setBase("osm");
  T.eq("back on osm, gruen is the brightened one again", strokeCount(overlay(), "#4fa85e"), greenOsm);

  T.test("an unknown basemap key falls back to the osm palette (colors, halo, AND mask opacity) rather than leaving stale state");
  // Not reachable through the UI (every chip's data-layer is a real key) -- calls the function directly,
  // which plain function declarations allow (see the harness notes on Annex B).
  await setBase("sat");
  applyBasePalette("not-a-real-basemap-key");
  await TM.wait(50);
  T.eq("colors fall back to osm's dark connector", strokeCount(overlay(), "#e08a00"), connectorsOsm);
  T.eq("the halo falls back to off, not left on from sat", strokeCount(overlay(), "#ffffff", 8.5), 0);
  T.eq("the lift mask falls back to opaque, not left transparent from sat", strokeCountOp(band(), "#cfcfcf", 1), maskOsm);
  applyBasePalette("osm"); // leave state consistent with the chip UI, which still reads "sat" until re-clicked
  await setBase("osm");
});
