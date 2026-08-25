// @suite   nearby
// @area    Umgebungssuche: Anker, Radius, Dimmen auf der Karte, Filtern in der Liste, Entfernungs-Sortierung
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches nearbyAnchor, nearbyRadiusKm, nearbyDistanceKm, nearbyPasses, nearbyVisibleCount, nearbyDistanceLabel, setNearbyAnchor, clearNearbyAnchor, drawNearbyAnchor, syncNearbyChrome, nearbyRow, nearbyBar, nearbyBarText, nearbyRadius, nearbyChip, nearby-available, nearby-chip, trail-meta-dist, baselineLineOpacity, trailPassesFilters, TRAIL_SORT_COMPARE, NEARBY_LONGPRESS_MS, mapTouchStart
// @needs   region=finale, builder=off
//
// **Braucht FINALE**, wie die rating-Suite und aus verwandtem Grund: die Frage "welche guten Trails sind
// hier in der Naehe" stellt sich in einer Region mit 219 Trails, nicht in einer mit zwoelf, und die
// Voreinstellung der Sortierung haengt daran, dass die Region Bewertungen hat.
//
// Drei Eigenschaften sind hier die eigentlichen, weil jede eine Art ist, auf die dieses Feature nicht
// kaputt, sondern UNEHRLICH waere:
//
//   * DIE KARTE DIMMT, DIE LISTE FILTERT -- und beide fragen dieselbe Funktion. Genau daran haengt, dass
//     "3 km · 31 Trails" eine Liste mit 31 Eintraegen bedeutet und nicht eine mit 219.
//   * SOLO GEWINNT, UND DAS SOLO-ENDE FUEHRT ZURUECK IN DEN ANKER-ZUSTAND, nicht auf eine helle Karte.
//     Dieselbe Konstante hat diesen Fehler in diesem Projekt schon zweimal verursacht (Hover-Ende und
//     clearSolo), also ist er hier festgenagelt, bevor er ein drittes Mal auftritt.
//   * EIN LANGER DRUCK AUF EINEN TRAIL SETZT DEN ANKER UND WAEHLT DEN TRAIL NICHT AUS. Der lange Druck
//     haengt bewusst in demselben touchstart/touchend-Paar, das fuer eine Beruehrung auf einer Linie
//     ohnehin einen Klick abschickt -- ohne die Markierung "verbraucht" tut eine Geste zwei Dinge.
//
// Anker-Koordinaten sind hier fest verdrahtet, und das ist Absicht: ein Anker aus `map.getCenter()` waere
// von der Kartenlage abhaengig, die jede vorher gelaufene Suite verschoben haben kann. [44.17, 8.35] liegt
// mitten in Finales Hub-Dichte, [44.60, 8.90] ueber 40 km entfernt im Nichts.

TM.add("nearby", () => typeof setNearbyAnchor === "function" && TM.ui.trailCards().length > 50, async (T) => {

  const ANCHOR = { lat: 44.17, lng: 8.35 };
  const FAR = { lat: 44.6, lng: 8.9 };
  const row = () => TM.$("#nearbyRow");
  const bar = () => TM.$("#nearbyBar");
  const barText = () => TM.$("#nearbyBarText").textContent;
  const shown = (el) => getComputedStyle(el).display !== "none";
  const ring = () => TM.map.overlay().filter((p) => (p.getAttribute("stroke") || "").toLowerCase() === "#b3520a").length;
  const setRadius = async (km) => {
    const input = TM.$("#nearbyRadius");
    input.value = String(km);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await TM.wait(350);
  };

  clearNearbyAnchor();
  await TM.wait(250);

  T.test("ohne Anker ist von der Umgebungssuche nichts zu sehen");
  // Im Ruhezustand kostet das Feature keine Flaeche -- dieselbe Regel wie beim Highlights-Regler.
  const allCards = TM.ui.trailCards().length;
  T.ok("die Ankerzeile ist weg", !shown(row()), getComputedStyle(row()).display, "none");
  T.ok("die Zeile auf der Karte auch", !shown(bar()), getComputedStyle(bar()).display, "none");
  T.ok("und der Entfernungs-Chip", !shown(TM.$(".nearby-chip")), getComputedStyle(TM.$(".nearby-chip")).display, "none");
  T.eq("kein Ring auf der Karte", ring(), 0);
  T.eq("nichts ist gedimmt", TM.map.dimmedTrails(), 0);
  T.eq("keine Entfernung auf einer Kachel", TM.$$("#trailList .trail-meta-dist").length, 0);

  T.test("ein Anker zeigt Zeile, Ring und Zahl -- und die Liste sind genau die Treffer");
  setNearbyAnchor(ANCHOR);
  await TM.wait(500);
  await setRadius(3);
  T.ok("die Ankerzeile ist da", shown(row()), getComputedStyle(row()).display, "flex");
  T.ok("die Zeile auf der Karte auch", shown(bar()), getComputedStyle(bar()).display, "flex");
  T.ok("und der Entfernungs-Chip", shown(TM.$(".nearby-chip")), getComputedStyle(TM.$(".nearby-chip")).display, "block");
  T.eq("ein Ring liegt auf der Karte", ring(), 1);
  T.ok("die Zeile nennt Radius und Zahl", /^3 km · \d+ Trail/.test(barText()), barText(), "3 km · n Trails");
  const nearCards = TM.ui.trailCards().length;
  T.ok("die Liste ist kuerzer als ohne Anker", nearCards > 0 && nearCards < allCards,
       nearCards + " von " + allCards, "> 0 und < " + allCards);
  // DIE Eigenschaft: die Zahl in der Zeile ist die Liste, nicht eine Behauptung daneben. Die Zeile zaehlt
  // Trails und Touren getrennt, weil Touren in ihrem eigenen Abschnitt stehen.
  const parts = barText().match(/(\d+) Trail/);
  T.eq("und die genannte Trailzahl IST die Laenge der Liste", parts ? +parts[1] : -1, nearCards);
  T.ok("jede Kachel traegt ihre Entfernung", TM.$$("#trailList .trail-meta-dist").length === nearCards,
       TM.$$("#trailList .trail-meta-dist").length, nearCards);
  T.ok("die Karte raeumt NICHT, sie dimmt", TM.map.dimmedTrails() > 0, TM.map.dimmedTrails(), "> 0");

  T.test("der erste Anker legt die Sortierachse auf die Frage, die er stellt");
  // In einer Region MIT Bewertungen ist das die Bewertung ("sonst steht der mittelmaessige Trail vor der
  // Haustuer ueber dem Highlight zwei Kilometer weiter"); ohne Bewertungen waere es die Entfernung.
  const activeSort = TM.$(".trail-view-chips[data-target='sort'] .chip.active").textContent;
  T.ok("nach Bewertung sortiert", /Bewertung/.test(activeSort), activeSort, "Bewertung");

  T.test("der Radius ist der Filter, und ein leerer Radius ist ein Ergebnis");
  await setRadius(1);
  const n1 = TM.ui.trailCards().length, b1 = barText();
  await setRadius(8);
  const n8 = TM.ui.trailCards().length;
  T.ok("groesserer Radius, mehr Treffer", n8 > n1, n1 + " bei 1 km, " + n8 + " bei 8 km", "8 km > 1 km");
  T.ok("und die Zeile nennt den eingestellten Radius", /^1 km/.test(b1), b1, "beginnt mit 1 km");
  setNearbyAnchor(FAR);
  await TM.wait(500);
  await setRadius(3);
  T.eq("weit draussen ist die Liste leer", TM.ui.trailCards().length, 0);
  // Kein Fehlertext, keine Ursache -- nur die Zahl, die gerade null ist.
  T.ok("und die Zeile sagt es als Ergebnis", /keiner in 3 km/.test(barText()), barText(), "keiner in 3 km");

  T.test("nach Entfernung sortiert steht der naechste oben");
  setNearbyAnchor(ANCHOR);
  await TM.wait(500);
  await setRadius(3);
  TM.$(".trail-view-chips[data-target='sort'] .chip[data-value='dist']").click();
  await TM.wait(400);
  const chipText = TM.$(".trail-view-chips[data-target='sort'] .chip.active").textContent;
  T.ok("der Chip zeigt die Richtung", /Entfernung ↑/.test(chipText), chipText, "Entfernung ↑");
  // Der Anker legt die Gruppierung ab, und daran haengt die Reihenfolge: nach Region gruppiert wird
  // INNERHALB jeder Gruppe sortiert, der naechste Trail stand dann in der Mitte der Liste. Gemessen:
  // 0,76 / 0,76 / 1,7 / 2,1 / 2,4 -- und dann wieder 0,5 km, weil dort die naechste Hub-Gruppe anfing.
  T.eq("und die Liste ist flach, nicht nach Region gruppiert", TM.$$("#trailList .hub-title").length, 0);
  const km = TM.$$("#trailList .trail-meta-dist").map((e) => {
    const m = /([\d,]+) km/.exec(e.textContent);
    return m ? +m[1].replace(",", ".") : +/(\d+) m/.exec(e.textContent)[1] / 1000;
  });
  const sorted = km.every((v, i) => i === 0 || km[i - 1] <= v + 0.001);
  T.ok("die Entfernungen steigen von oben nach unten", sorted, km.slice(0, 6), "aufsteigend");
  T.ok("und keine liegt ueber dem Radius", km.every((v) => v <= 3.05), Math.max.apply(null, km), "<= 3 km");

  T.test("Solo gewinnt, und das Solo-Ende fuehrt in den ANKER-Zustand zurueck");
  const card = TM.ui.trailCards()[0];
  card.click();
  await TM.wait(900);
  // Die Grundlinie erst JETZT: der Klick fliegt die Karte, und dimmedTrails() zaehlt DOM-Pfade -- Leaflet
  // zeichnet nur, was im gepolsterten Ausschnitt liegt, also zaehlt eine Zahl von vor dem Flug andere
  // Pfade. Verglichen wird ueber das Solo hinweg, und genau das ist die Eigenschaft.
  const dimNearby = TM.map.dimmedTrails();
  const soloBtn = TM.$("#trailList .trail-card.selected .card-solo-btn");
  T.ok("die ausgewaehlte Kachel hat ihren Solo-Knopf", !!soloBtn, !!soloBtn, true);
  if (soloBtn) {
    soloBtn.click();
    await TM.wait(500);
    T.ok("waehrend Solo ist mehr gedimmt als durch den Radius", TM.map.dimmedTrails() >= dimNearby,
         TM.map.dimmedTrails(), ">= " + dimNearby);
    soloBtn.click();
    await TM.wait(500);
    // Genau hier lag der Fehler zweimal: ein fest verdrahtetes 0.85 macht die ganze Karte hell.
    T.eq("und danach wieder genau der Anker-Zustand", TM.map.dimmedTrails(), dimNearby);
  }
  if (typeof closeInfoPanelAndDeselect === "function") closeInfoPanelAndDeselect();
  await TM.wait(250);

  T.test("ein langer Druck setzt den Anker -- auch auf einem Trail, ohne ihn auszuwaehlen");
  clearNearbyAnchor();
  await TM.wait(350);
  // Die unsichtbare Trefferlinie eines Trails: genau das Element, fuer das touchend sonst einen Klick
  // abschickt. Ein scriptbarer TouchEvent erreicht unsere eigenen Handler; was er nicht erzeugt, ist der
  // synthetische Klick der Plattform -- und den brauchen wir hier gerade nicht.
  // Der Punkt muss AUF der Linie liegen und nicht in der Mitte ihres Rechtecks: der Handler entscheidet
  // ueber `document.elementFromPoint`, und bei einer krummen Linie liegt die Rechteckmitte daneben -- dann
  // ist start.target null, touchend steigt sowieso aus, und der Fall prueft nichts. Also die Linie selbst
  // abtasten (getPointAtLength + Screen-CTM), bis elementFromPoint wirklich eine Leaflet-Linie liefert.
  const onLine = (() => {
    for (const p of TM.map.overlay().filter((q) => (q.getAttribute("stroke-opacity") || "1") === "0")) {
      const len = p.getTotalLength ? p.getTotalLength() : 0;
      const m = p.getScreenCTM && p.getScreenCTM();
      if (!len || !m) continue;
      for (let f = 0.2; f <= 0.8; f += 0.1) {
        const pt = p.getPointAtLength(len * f);
        const x = Math.round(pt.x * m.a + pt.y * m.c + m.e), y = Math.round(pt.x * m.b + pt.y * m.d + m.f);
        const el = document.elementFromPoint(x, y);
        if (el && el.tagName === "path" && el.classList.contains("leaflet-interactive")) return { x, y, el };
      }
    }
    return null;
  })();
  if (!onLine || typeof TouchEvent !== "function" || typeof Touch !== "function") {
    T.skip("kein Punkt auf einer Trefferlinie oder keine Touch-Konstruktoren in diesem Browser");
  } else {
    const el = TM.$("#map");
    const touch = new Touch({ identifier: 71, target: onLine.el, clientX: onLine.x, clientY: onLine.y });
    // touchend traegt die Beruehrung in changedTouches und NICHT in touches -- so sieht ein echtes
    // touchend aus, und daran haengt hier alles: der Klick-Zweig des Handlers verlangt genau
    // `changedTouches.length === 1`. Mit einer leeren Liste laeuft er nie, und dann besteht dieser Fall
    // auch gegen eine Fassung, die den langen Druck NICHT als verbraucht markiert (gemessen).
    const fire = (type, touches, changed) => el.dispatchEvent(new TouchEvent(type, {
      bubbles: true, cancelable: true, touches: touches, targetTouches: touches,
      changedTouches: changed || touches }));
    fire("touchstart", [touch]);
    await TM.wait(650);                       // laenger als NEARBY_LONGPRESS_MS
    const setDuringPress = shown(bar());
    fire("touchend", [], [touch]);
    await TM.wait(500);
    T.ok("der Anker steht, sobald die Zeit um ist", setDuringPress, setDuringPress, true);
    // `.visible`, nicht `.open`: das ist die Klasse, die das Panel wirklich traegt. Mit `.open` war die
    // Zusicherung leer -- sie konnte nie fehlschlagen und bestand auch gegen eine Fassung, die den langen
    // Druck nicht als verbraucht markiert (gemessen, siehe MUTATIONS.md).
    T.eq("und kein Info-Panel ist aufgegangen", TM.$$("#infoPanel.visible").length, 0);
    T.eq("und keine Kachel ist ausgewaehlt", TM.$$("#trailList .trail-card.selected").length, 0);

    T.test("ein kurzer Tipp setzt keinen Anker");
    clearNearbyAnchor();
    await TM.wait(350);
    fire("touchstart", [touch]);
    await TM.wait(120);
    fire("touchend", [], [touch]);
    await TM.wait(400);
    T.ok("die Zeile bleibt weg", !shown(bar()), getComputedStyle(bar()).display, "none");
  }

  T.test("das Aufraeumen stellt alles wieder her");
  setNearbyAnchor(ANCHOR);
  await TM.wait(450);
  TM.$("#nearbyClearBtn").click();
  await TM.wait(500);
  T.eq("wieder alle Kacheln", TM.ui.trailCards().length, allCards);
  T.eq("nichts gedimmt", TM.map.dimmedTrails(), 0);
  T.eq("kein Ring", ring(), 0);
  T.ok("keine Ankerzeile", !shown(row()), getComputedStyle(row()).display, "none");
  T.ok("keine Zeile auf der Karte", !shown(bar()), getComputedStyle(bar()).display, "none");
  T.eq("keine Entfernung auf den Kacheln", TM.$$("#trailList .trail-meta-dist").length, 0);
  // Die Entfernungsachse verschwindet mit ihrem Anker: eine Sortierung nach einer Zahl, die es nicht mehr
  // gibt, waere eine Reihenfolge ohne Bedeutung.
  const sortAfter = TM.$(".trail-view-chips[data-target='sort'] .chip.active").textContent;
  T.ok("und die Sortierung steht nicht mehr auf Entfernung", !/Entfernung/.test(sortAfter), sortAfter, "nicht Entfernung");
});
