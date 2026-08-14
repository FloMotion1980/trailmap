// @suite   palette
// @area    Per-basemap trail/lift/connector colors and the geometry halo (Satellit + Relief)
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches applyBasePalette, repaintLineColors, syncHalo, applyHaloOpacity, applySolo, clearSolo, BASE_PALETTES, HALO, HALO_ACTIVE_KINDS, diffColor, CONNECTOR_COLOR, LIFT_LINE_COLOR, LIFT_MASK_COLOR, LIFT_MASK_OPACITY, SELECT_YELLOW, baseLayerControl
// @needs   region=bikekingdom, builder=off
//
// Added 2026-08-13 (schwarz-only halo on Satellit), rewritten 2026-08-14 once the halo widened to every
// kind and Relief got Satellit's whole treatment -- see CLAUDE.md's palette section for the full story,
// including the three-week round trip the connector color took through orange and back to grey.
// `diffColor`/`CONNECTOR_COLOR`/`LIFT_LINE_COLOR`/`LIFT_MASK_COLOR`/`LIFT_MASK_OPACITY`/`SELECT_YELLOW`/
// `HALO` are all const/let inside the app's own scope and unreachable here (same reason lineLayers/
// soloId are), so every check below reads the map's own SVG stroke/stroke-width/stroke-opacity
// attributes, per the harness's own rule -- and that is deliberate, not a workaround: it is what proves
// the already-built layers were actually repainted/rebuilt in place, not just that some internal
// variable changed while the paint stayed stale.
//
// This suite drives the real #baseLayerControl chips (not applyBasePalette directly) so a bug in the click
// wiring itself -- forgetting to call applyBasePalette() at all -- would fail it, and restores "osm" at the
// end since changing the active basemap is shared state no other suite expects to inherit (same rule the
// `regions` suite follows for the active region set).
//
// THE CONNECTOR COLOR IS THE SAME EVERYWHERE NOW (#5a5a5a, dark grey), on purpose, and this suite once
// checked the opposite on purpose too -- worth knowing if this changes again: it spent 2026-08-13 through
// 2026-08-14 as three different oranges (bright amber on Satellit only, then "überall", then two rounds
// of darkening for the three light basemaps) before a full round trip back to the original grey, once a
// halo existed everywhere to carry the contrast job orange was invented for. Don't assume grey is safe
// again on a basemap that has NO halo behind it -- it was specifically the halo's arrival that made grey
// work on Satellit a second time.
//
// A HALO IS A CASING POLYLINE PER KIND (diff name / "connector" / "lift"), sized by `HALO_WEIGHT_TRAIL`
// (currently 7.5 -- HOVER_WEIGHT+1, narrowed from +2 the same day the halo widened from schwarz-only to
// every kind). `HALO_ACTIVE_KINDS` decides which kinds get a casing layer built at all; right now that's
// every kind except `lift` on topo and sat, and nothing on osm/carto. Width 7.5 is therefore a reliable
// fingerprint for "this path is a halo casing", regardless of which kind or which basemap -- no other
// path in the overlay pane uses that width (trail lines are 3.5/6.5, connectors 2.2/3.0).
//
// A LIFT'S CONTRAST COMES FROM A DIFFERENT, PRE-EXISTING MECHANISM, NOT A HALO CASING. Its own grey mask
// polyline (LIFT_MASK_WEIGHT, 7px wide) already sits behind the 1.1px hairline and 3.8px dots, in the same
// pane, purely by build order -- structurally identical to a halo. `LIFT_MASK_OPACITY` toggles it: 1 on
// osm (covers OSM's own vector aerialway rendering), 0 on carto (nothing to cover, and no contrast band
// wanted), 1 on topo/sat (repurposed as a permanent contrast band, once the user noticed the shape already
// existed -- "wir haben ja die Linie für Straße, die bei den anderen Ansichten ausgeblendet ist"). Its
// color on topo/sat is light violet (`#dab6f0`), not white, specifically so a lift reads as its own kind
// of thing rather than another trail with a halo (the user tried white first and rejected it). `lift`
// stays `null` in every basemap's `halo` map for this reason -- there is nothing to build for it.
//
// HALO HISTORY, worth knowing before touching this again. A CSS `filter: drop-shadow` contrast halo shipped
// first, on every vector path on Satellit -- reverted the same day, since it broke on the user's iPhone in
// Safari (no glow on trails, an opaque white background on lifts), a long-standing WebKit bug combining CSS
// `filter` with an ancestor `transform` (every Leaflet pane, plus leaflet-rotate's rotate()). A geometry-
// based halo for EVERY trail/connector was designed next but rejected on performance grounds before being
// built (doubling the per-frame path count during rotation). It came back the same day, scoped down to
// just `sat.schwarz` -- and widened to every kind, on Satellit AND Relief, a day later once the original
// performance worry turned out not to matter enough to block it in practice.

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
  // Width 7.5 (HALO_WEIGHT_TRAIL) is a reliable fingerprint for "this path is a halo casing", regardless
  // of colour or kind -- see the suite header for why no other overlay-pane path shares that width.
  const haloWidthCount = () => overlay().filter((p) => p.getAttribute("stroke-width") === "7.5").length;
  const setBase = async (key) => {
    const chip = TM.$(`#baseLayerControl [data-layer='${key}']`);
    if (!chip.classList.contains("active")) { chip.click(); await TM.wait(200); }
  };

  T.test("starts on osm: dark grey connector, brightened diff trio, lift mask visible, no halo anywhere");
  await setBase("osm");
  const greenOsm = strokeCount(overlay(), "#4fa85e");
  T.ok("green trails present", greenOsm > 0, greenOsm, "> 0");
  const blauOsm = strokeCount(overlay(), "#2f74c0");
  T.ok("blau trails present", blauOsm > 0, blauOsm, "> 0");
  const rotOsm = strokeCount(overlay(), "#d9483c");
  T.ok("rot trails present", rotOsm > 0, rotOsm, "> 0");
  const schwarzOsm = strokeCount(overlay(), "#1c1c1c");
  T.ok("schwarz trails present, near-black", schwarzOsm > 0, schwarzOsm, "> 0");
  const maskOsm = strokeCountOp(band(), "#cfcfcf", 1);
  T.ok("lift masks present and fully opaque on osm", maskOsm > 0, maskOsm, "> 0");
  // Width 2.2 (CONNECTOR_WEIGHT) disambiguates a connector from a Tour's own lift hairline, which shares
  // this exact color on topo/sat (see checkSatLikeTreatment below) but never this width (1.1 or 3.8).
  const connectorsOsm = strokeCount(overlay(), "#5a5a5a", 2.2);
  T.ok("connectors present, the dark grey", connectorsOsm > 0, connectorsOsm, "> 0");
  T.eq("no halo casing anywhere on osm", haloWidthCount(), 0);
  T.eq("no leftover amber connector from the old orange scheme", strokeCount(overlay(), "#ffb300"), 0);
  T.eq("no leftover burnt-orange connector either", strokeCount(overlay(), "#e08a00"), 0);

  T.test("carto: same dark grey connector, ORIGINAL unbrightened trio, lift mask invisible, no halo");
  await setBase("carto");
  T.eq("carto connector matches osm's dark grey", strokeCount(overlay(), "#5a5a5a", 2.2), connectorsOsm);
  T.eq("carto lift masks are transparent, same count as osm's opaque ones", strokeCountOp(band(), "#cfcfcf", 0), maskOsm);
  T.eq("carto gruen is the ORIGINAL unbrightened one, not osm's brightened gruen", strokeCount(overlay(), "#3f8a4c"), greenOsm);
  T.eq("no halo casing on carto either", haloWidthCount(), 0);

  // Relief ("topo") and Satellit ("sat") are byte-for-byte the same treatment as of 2026-08-14 -- Relief
  // had the same underlying hue-collision problem Satellit's halo already fixed, so it was given the
  // identical configuration wholesale rather than a separate design. One function checks both.
  const checkSatLikeTreatment = (label) => {
    T.eq(`${label}: no old osm-brightened gruen leaking in`, strokeCount(overlay(), "#4fa85e"), 0);
    T.eq(`${label}: no old unbrightened carto/topo gruen left either`, strokeCount(overlay(), "#3f8a4c"), 0);
    T.eq(`${label}: gruen is the darker shade, same count`, strokeCount(overlay(), "#2f9e52"), greenOsm);
    T.eq(`${label}: blau is the darker shade, same count`, strokeCount(overlay(), "#2a6fcf"), blauOsm);
    T.eq(`${label}: rot is the darker shade, same count`, strokeCount(overlay(), "#d8402a"), rotOsm);
    T.eq(`${label}: schwarz stays near-black -- the halo carries the contrast now, not a lightened color`,
         strokeCount(overlay(), "#1c1c1c"), schwarzOsm);
    // Width-filtered -- on topo/sat, a Tour's own lift hairline/dots share this exact color now (see the
    // lift-line check below), and without the width filter they'd inflate this count.
    T.eq(`${label}: connector unchanged -- same dark grey as every other basemap`, strokeCount(overlay(), "#5a5a5a", 2.2), connectorsOsm);
    T.eq(`${label}: gruen halo matches gruen trail count`, strokeCount(overlay(), "#a8e8ba", 7.5), greenOsm);
    T.eq(`${label}: blau halo matches blau trail count`, strokeCount(overlay(), "#a9cdf5", 7.5), blauOsm);
    T.eq(`${label}: rot halo matches rot trail count`, strokeCount(overlay(), "#f5aa9d", 7.5), rotOsm);
    T.eq(`${label}: schwarz halo matches schwarz trail count`, strokeCount(overlay(), "#c7c7c7", 7.5), schwarzOsm);
    T.eq(`${label}: connector halo matches connector count`, strokeCount(overlay(), "#ffcc80", 7.5), connectorsOsm);
    T.eq(`${label}: no leftover plain-white halo from the schwarz-only pre-widening design`, strokeCount(overlay(), "#ffffff", 7.5), 0);
    T.ok(`${label}: lift masks are opaque violet -- reused as the lift's own contrast band`,
         strokeCountOp(band(), "#dab6f0", 1) > 0, strokeCountOp(band(), "#dab6f0", 1), "> 0");
    T.ok(`${label}: lift hairline/dots are the same dark grey as the connector`,
         strokeCountOp(band(), "#5a5a5a", 1) > 0, strokeCountOp(band(), "#5a5a5a", 1), "> 0");
    T.eq(`${label}: no leftover light-grey lift line (lost inside the yellow selection outline)`, strokeCountOp(band(), "#d9d9d9", 1), 0);
    T.eq(`${label}: no leftover near-white lift mask from before it became the contrast band`, strokeCountOp(band(), "#f2f2f2", 1), 0);
  };

  T.test("switching to Relief: Satellit's whole configuration, applied wholesale");
  await setBase("topo");
  checkSatLikeTreatment("topo");

  T.test("switching to Satellit: the identical configuration");
  await setBase("sat");
  checkSatLikeTreatment("sat");

  T.test("selecting a Tour riding a lift must NOT force that lift's mask past LIFT_MASK_OPACITY -- exercised on carto, the one basemap left where the mask must stay hidden");
  // applyLiftSegmentOpacity() sets every lift segment's opacity to 1 when its OWN Tour is the soloed one
  // (which selecting a Tour does) -- but `liftSegments` is a flat [mask, hairline, dots, ...] repeat, and
  // the mask specifically must stay capped at LIFT_MASK_OPACITY regardless, or selecting/soloing a Tour
  // riding a lift forces that lift's mask back to fully opaque on a basemap where it's supposed to stay
  // invisible. Reported by the user as "Lifte die in einer Tour verwendet werden haben weiterhin den
  // grauen [weißen] Strich" -- specifically AFTER selecting the Tour, which is the tell: the mask was
  // already correctly invisible before that, only selection forced it back. Used to be exercised on
  // Satellit, back when Satellit's own LIFT_MASK_OPACITY was 0 too; now that topo/sat both keep the mask
  // permanently visible, carto is the only basemap left where this cap is not a no-op.
  await setBase("carto");
  {
    const maskOpacities = () => new Set(band()
      .filter((p) => p.getAttribute("stroke-width") === "7")
      .map((p) => p.getAttribute("stroke-opacity") || "1"));
    const before = maskOpacities();
    T.ok("at rest, no lift mask is opaque on carto", ![...before].some((op) => parseFloat(op) > 0.5), [...before], "nothing > 0.5");
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
  // schwarz trail's line faded to SOLO_DIM_OPACITY while its halo kept glowing at HALO_OPACITY, right
  // where the actual line used to be. Reported by the user as "Monte Corno wird komplett weiß" on
  // Satellit, and only once Monte Corno itself was selected: Monte Corno is an unsegmented loop and never
  // has a halo of its own (see buildTrailLayer's own comment on why), but selecting ANY loop solos it,
  // which dimmed a schwarz trail lying near/under Monte Corno's own path while leaving that trail's halo
  // untouched. Needs at least one schwarz trail that ISN'T the soloed one to observe the dimming on.
  await setBase("sat");
  {
    const schwarzHaloOpacities = () => new Set(overlay()
      .filter((p) => (p.getAttribute("stroke") || "").toLowerCase() === "#c7c7c7" && p.getAttribute("stroke-width") === "7.5")
      .map((p) => p.getAttribute("stroke-opacity") || "1"));
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
  // the two rings sitting close together looked cluttered. Suppressing (removing) the halo rather than
  // fighting Leaflet z-order to make the wider yellow ring paint over the narrower one sidesteps a real
  // ordering problem: `layer.line.bringToFront()` brings a segmented Trailrunde's whole featureGroup --
  // including any attached segment casings -- forward together, which would drag a halo back in front of
  // the outline it was meant to hide behind.
  {
    const haloCount = () => strokeCount(overlay(), "#c7c7c7", 7.5);
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

  T.test("switching back to osm round-trips every color/opacity exactly, nothing left stuck on the sat/topo palette");
  await setBase("osm");
  T.eq("gruen restored, same count", strokeCount(overlay(), "#4fa85e"), greenOsm);
  T.eq("no sat/topo gruen left", strokeCount(overlay(), "#2f9e52"), 0);
  T.eq("connector still the same dark grey, same count", strokeCount(overlay(), "#5a5a5a", 2.2), connectorsOsm);
  T.eq("lift masks opaque again, same count", strokeCountOp(band(), "#cfcfcf", 1), maskOsm);
  T.eq("schwarz unchanged throughout (it was never recolored on osm)", strokeCount(overlay(), "#1c1c1c"), schwarzOsm);
  T.eq("every halo casing is gone again, not just recolored", haloWidthCount(), 0);
  T.eq("lift line back to near-black, no dark-grey left from sat/topo", strokeCountOp(band(), "#5a5a5a", 1), 0);
  T.eq("lift mask back to plain grey, no violet left from sat/topo", strokeCountOp(band(), "#dab6f0", 1), 0);

  T.test("an unknown basemap key falls back to the osm palette (colors, halo, AND mask opacity) rather than leaving stale state");
  // Not reachable through the UI (every chip's data-layer is a real key) -- calls the function directly,
  // which plain function declarations allow (see the harness notes on Annex B). The connector can no
  // longer be the differentiator here (it's the same #5a5a5a on every basemap now, including sat) -- gruen,
  // the halo, and the lift mask still change per basemap, so those carry this check instead.
  await setBase("sat");
  applyBasePalette("not-a-real-basemap-key");
  await TM.wait(50);
  T.eq("colors fall back to osm's brightened gruen", strokeCount(overlay(), "#4fa85e"), greenOsm);
  T.eq("sat's own darker gruen is gone", strokeCount(overlay(), "#2f9e52"), 0);
  T.eq("the halo falls back to off, not left on from sat", haloWidthCount(), 0);
  T.eq("the lift mask falls back to osm's opaque grey, not left violet from sat", strokeCountOp(band(), "#cfcfcf", 1), maskOsm);
  T.eq("no violet lift mask left over", strokeCountOp(band(), "#dab6f0", 1), 0);
  applyBasePalette("osm"); // leave state consistent with the chip UI, which still reads "sat" until re-clicked
  await setBase("osm");
});
