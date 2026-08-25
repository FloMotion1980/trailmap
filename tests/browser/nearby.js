// @suite   nearby
// @area    Umgebungssuche: Anker, Radius, Dimmen auf der Karte, Filtern in der Liste, Entfernungs-Sortierung
// @files   Trailmap App/index.html, Trailmap App/style.css
// @touches nearbyAnchor, nearbyRadiusKm, nearbyDistanceKm, nearbyPasses, nearbyVisibleCount, nearbyDistanceLabel, setNearbyAnchor, clearNearbyAnchor, drawNearbyAnchor, syncNearbyChrome, nearbyBar, nearbyBarText, nearbyRadius, nearbyRadiusValue, nearby-touch-only, nearby-slider-wrap, nearby-available, nearby-chip, trail-meta-dist, baselineLineOpacity, trailPassesFilters, TRAIL_SORT_COMPARE, nearbyPickArmed, armNearbyPick, disarmNearbyPick, syncNearbyPickChrome, nearbyPickBtn, nearbyPickHint, nearby-picking
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
//   * ERST DER KNOPF, DANN TIPPEN -- und waehrend der Modus laeuft, ist keine Trail-Linie klickbar. Genau
//     daran haengt, dass ein Tipp auf eine Linie den Anker setzt statt den Trail zu oeffnen: die CSS-Regel
//     nimmt den Linien ihre pointer-events, also landet jeder Tipp auf der Karte. Das lange Druecken, das
//     hier einen Tag lang stand, war nicht auffindbar und loeste auf iOS das Systemmenue aus.
//
// Anker-Koordinaten sind hier fest verdrahtet, und das ist Absicht: ein Anker aus `map.getCenter()` waere
// von der Kartenlage abhaengig, die jede vorher gelaufene Suite verschoben haben kann. [44.17, 8.35] liegt
// mitten in Finales Hub-Dichte, [44.60, 8.90] ueber 40 km entfernt im Nichts.

TM.add("nearby", () => typeof setNearbyAnchor === "function" && TM.ui.trailCards().length > 50, async (T) => {

  const ANCHOR = { lat: 44.17, lng: 8.35 };
  const FAR = { lat: 44.6, lng: 8.9 };
  const bar = () => TM.$("#nearbyBar");
  const barText = () => TM.$("#nearbyBarText").textContent;
  const radiusText = () => TM.$("#nearbyRadiusValue").textContent;
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
  // Und im Menue steht ueberhaupt nichts davon (Nutzer, 2026-08-25: "Generell nix im Menue. Das spielt sich
  // alles auf der Karte ab") -- die Ankerzeile in den Filtern gab es einen Tag lang, sie ist ersatzlos weg.
  T.eq("keine Bedienelemente in der Seitenleiste", TM.$$("aside #nearbyRadius, aside #nearbyBar, #nearbyRow").length, 0);
  T.ok("die Zeile auf der Karte ist weg", !shown(bar()), getComputedStyle(bar()).display, "none");
  T.ok("und der Entfernungs-Chip", !shown(TM.$(".nearby-chip")), getComputedStyle(TM.$(".nearby-chip")).display, "none");
  T.eq("kein Ring auf der Karte", ring(), 0);
  T.eq("nichts ist gedimmt", TM.map.dimmedTrails(), 0);
  T.eq("keine Entfernung auf einer Kachel", TM.$$("#trailList .trail-meta-dist").length, 0);

  T.test("ein Anker zeigt Zeile, Ring und Zahl -- und die Liste sind genau die Treffer");
  setNearbyAnchor(ANCHOR);
  await TM.wait(500);
  await setRadius(3);
  T.ok("die Zeile auf der Karte ist da", shown(bar()), getComputedStyle(bar()).display, "flex");
  T.ok("und sie liegt auf der Karte, nicht in der Seitenleiste",
       !TM.$("aside").contains(bar()) && TM.$(".map-wrap").contains(bar()), true, true);
  T.ok("und der Entfernungs-Chip", shown(TM.$(".nearby-chip")), getComputedStyle(TM.$(".nearby-chip")).display, "block");
  T.eq("ein Ring liegt auf der Karte", ring(), 1);
  // Der Radius steht im Regler, die Treffer in der Zeile -- jede Zahl an genau einer Stelle.
  T.ok("der Regler nennt den Radius", /^3 km$/.test(radiusText()), radiusText(), "3 km");
  T.ok("die Zeile nennt die Treffer", /^\d+ Trails?/.test(barText()), barText(), "n Trails");
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
  const n1 = TM.ui.trailCards().length, b1 = radiusText();
  await setRadius(8);
  const n8 = TM.ui.trailCards().length;
  T.ok("groesserer Radius, mehr Treffer", n8 > n1, n1 + " bei 1 km, " + n8 + " bei 8 km", "8 km > 1 km");
  T.ok("und der Regler nennt den eingestellten Radius", /^1 km$/.test(b1), b1, "1 km");
  setNearbyAnchor(FAR);
  await TM.wait(500);
  await setRadius(3);
  T.eq("weit draussen ist die Liste leer", TM.ui.trailCards().length, 0);
  // Kein Fehlertext, keine Ursache -- nur, dass es gerade keine gibt.
  T.ok("und die Zeile sagt es als Ergebnis", /keine Treffer/.test(barText()), barText(), "keine Treffer");

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

  T.test("erst der Knopf, dann tippen -- und waehrenddessen ist keine Linie klickbar");
  // Das lange Druecken gab es einen Tag lang und ist weg (Nutzer, 2026-08-25): es war nicht auffindbar
  // ("aktuell fehlt noch eine Art Hinweis, dass das ueberhaupt geht") und loeste auf iOS zusaetzlich das
  // Systemmenue aus. Ein Knopf ist sichtbar, und die Geste danach ist auf beiden Plattformen dieselbe.
  clearNearbyAnchor();
  await TM.wait(350);
  const pickBtn = TM.$("#nearbyPickBtn");
  T.ok("der Knopf steht im Bedienstapel", !!pickBtn && pickBtn.parentElement.id === "mapControls",
       pickBtn ? pickBtn.parentElement.id : null, "mapControls");
  pickBtn.click();
  await TM.wait(400);
  T.ok("der Hinweis sagt, was zu tun ist", shown(TM.$("#nearbyPickHint")),
       getComputedStyle(TM.$("#nearbyPickHint")).display, "flex");
  T.ok("und der Knopf zeigt sich als aktiv", pickBtn.classList.contains("on"), pickBtn.className, "on");
  // DAS ist der Mechanismus: ohne pointer-events auf den Linien landet jeder Tipp auf der Karte, also
  // braucht der Klick-Handler keinen Sonderfall -- und unsere eigene Tipp-Abfangung findet per
  // elementFromPoint keine interaktive Linie und laesst die Beruehrung in Ruhe.
  const aLine = TM.$$(".leaflet-overlay-pane path.leaflet-interactive")[0];
  T.eq("keine Trail-Linie ist waehrend des Modus klickbar",
       aLine ? getComputedStyle(aLine).pointerEvents : null, "none");
  const el = TM.$("#map"), r = el.getBoundingClientRect();
  const at = (fx, fy) => ["mousedown", "mouseup", "click"].forEach((t) => el.dispatchEvent(
    new MouseEvent(t, { bubbles: true, cancelable: true,
                        clientX: Math.round(r.left + r.width * fx), clientY: Math.round(r.top + r.height * fy) })));
  at(0.4, 0.5);
  await TM.wait(900);
  T.ok("der Tipp setzt den Anker", shown(bar()), getComputedStyle(bar()).display, "flex");
  T.ok("der Modus ist danach aus", !pickBtn.classList.contains("on") && !shown(TM.$("#nearbyPickHint")),
       [pickBtn.className, getComputedStyle(TM.$("#nearbyPickHint")).display], "aus");
  // FRISCH abfragen, nicht `aLine` von vorher: der Anker loest ein render() aus, und ein Trail ausserhalb
  // des Radius verliert dabei seine Elemente. Ein abgemeldeter Knoten liefert "none" und haette den Fall
  // gruen gemeldet, obwohl er nichts geprueft hat (gemessen).
  // ...und eine wirklich INTERAKTIVE Linie: der erste Pfad im Pane ist der Ring der Umgebungssuche selbst
  // (interactive:false, per bringToBack ganz nach hinten), und der traegt "none" voellig zu Recht. Auch das
  // gemessen, nicht ueberlegt -- die erste Fassung dieses Vergleichs meldete den Ring als Fehler.
  const freshLine = TM.$$(".leaflet-overlay-pane path.leaflet-interactive")[0];
  // "klickbar wieder" heisst: NICHT none. Der genaue Wert gehoert Leaflet und ist je Version "auto" oder
   // "visiblePainted" -- gemessen kam hier "auto", und ein fester Vergleich haette nur die Version gepruefft.
  T.ok("und die Karte ist nicht mehr im Punkt-Modus",
       !TM.$(".leaflet-container").classList.contains("nearby-picking") &&
       !!freshLine && getComputedStyle(freshLine).pointerEvents !== "none",
       [TM.$(".leaflet-container").className.indexOf("nearby-picking") > -1,
        freshLine ? getComputedStyle(freshLine).pointerEvents : null], "kein Modus, Linien klickbar");
  T.eq("und kein Info-Panel ist dabei aufgegangen", TM.$$("#infoPanel.visible").length, 0);

  T.test("ein Tipp OHNE armierten Modus setzt keinen Anker");
  clearNearbyAnchor();
  await TM.wait(350);
  at(0.45, 0.45);
  await TM.wait(600);
  T.ok("die Zeile bleibt weg", !shown(bar()), getComputedStyle(bar()).display, "none");

  T.test("nach dem Aufraeumen stehen Sortierung und Gruppierung wieder auf den URSPRUNGSWERTEN");
  // Nicht auf den Vorgaben der App (Nutzer, 2026-08-25): wer vorher nach Laenge sortiert und nach
  // Schwierigkeit gruppiert hatte, will das danach wieder haben. Bis dahin ging nur die Gruppierung zurueck,
  // weil die Sortierung nur im Fall "dist" zurueckgesetzt wurde -- vom Nutzer gemeldet: "Passiert momentan
  // nur bei Gruppieren nicht bei Sortieren".
  const chip = (target, val) => TM.$(".trail-view-chips[data-target='" + target + "'] .chip[data-value='" + val + "']");
  const viewState = () => [TM.$(".trail-view-chips[data-target='sort'] .chip.active").textContent,
                           TM.$(".trail-view-chips[data-target='group'] .chip.active").textContent];
  clearNearbyAnchor();
  await TM.wait(300);
  chip("sort", "length").click();
  await TM.wait(300);
  chip("group", "diff").click();
  await TM.wait(400);
  const ownView = viewState();
  setNearbyAnchor(ANCHOR);
  await TM.wait(700);
  const anchoredView = viewState();
  T.ok("der Anker stellt beides um", anchoredView[0] !== ownView[0] && anchoredView[1] !== ownView[1],
       anchoredView, "anders als " + ownView);
  TM.$("#nearbyClearBtn").click();
  await TM.wait(700);
  T.eq("und danach steht beides wieder wie vorher", viewState(), ownView);

  // Die Gegenprobe, damit das Zuruecksetzen nicht zur Bevormundung wird: was der Nutzer WAEHREND des
  // Ankers selbst umstellt, ist seine Wahl und bleibt stehen.
  setNearbyAnchor(ANCHOR);
  await TM.wait(700);
  chip("sort", "name").click();
  await TM.wait(400);
  const chosen = viewState()[0];
  TM.$("#nearbyClearBtn").click();
  await TM.wait(700);
  T.eq("eine eigene Wahl waehrend des Ankers bleibt", viewState()[0], chosen);
  T.eq("und die unangetastete Achse geht trotzdem zurueck", viewState()[1], ownView[1]);
  TM.$("#trailViewResetBtn").click();
  await TM.wait(300);

  T.test("was am Schreibtisch nichts tut, ist dort auch nicht zu sehen");
  // "Liste" oeffnet die Schublade -- am Schreibtisch steht sie ohnehin dauerhaft daneben; 📍 setzt den Anker
  // auf die eigene Position, die es am Laptop meist nicht gibt. Beides hat der Nutzer nach dem ersten
  // Versuch gemeldet ("Ich kann auf Liste klicken und nix passiert", "Das Positionslocator wird nicht
  // benoetigt am Desktop"). Geprueft wird die REGEL, nicht die Breite: auf einem Touch-Layout muessen beide
  // da sein, und diese Suite laeuft am Schreibtisch.
  setNearbyAnchor(ANCHOR);
  await TM.wait(450);
  const touchLayout = window.matchMedia("(max-width: 768px), (pointer: coarse)").matches;
  T.eq("Liste und Positionsknopf folgen dem Layout",
       [shown(TM.$("#nearbyBarList")), shown(TM.$("#nearbyLocateBtn"))], [touchLayout, touchLayout]);
  T.ok("das ✕ ist immer da", shown(TM.$("#nearbyClearBtn")), getComputedStyle(TM.$("#nearbyClearBtn")).display, "sichtbar");

  T.test("das Aufraeumen stellt alles wieder her");
  setNearbyAnchor(ANCHOR);
  await TM.wait(450);
  TM.$("#nearbyClearBtn").click();
  await TM.wait(500);
  T.eq("wieder alle Kacheln", TM.ui.trailCards().length, allCards);
  T.eq("nichts gedimmt", TM.map.dimmedTrails(), 0);
  T.eq("kein Ring", ring(), 0);
  T.ok("keine Zeile auf der Karte", !shown(bar()), getComputedStyle(bar()).display, "none");
  T.eq("keine Entfernung auf den Kacheln", TM.$$("#trailList .trail-meta-dist").length, 0);
  // Die Entfernungsachse verschwindet mit ihrem Anker: eine Sortierung nach einer Zahl, die es nicht mehr
  // gibt, waere eine Reihenfolge ohne Bedeutung.
  const sortAfter = TM.$(".trail-view-chips[data-target='sort'] .chip.active").textContent;
  T.ok("und die Sortierung steht nicht mehr auf Entfernung", !/Entfernung/.test(sortAfter), sortAfter, "nicht Entfernung");
});
