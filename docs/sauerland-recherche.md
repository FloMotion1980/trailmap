# Sauerland/Upland — Recherchestand, noch nicht gebaut (2026-07-30)

Eine Region mit drei Sub-Regionen, so 2026-07-26 vom Nutzer entschieden: **Winterberg**, **Willingen**
(Ettelsberg) und **Green Hill**. Die Bündelung ist ausdrücklich nur geografisch — kein gemeinsames Ticket,
keine Touren, die über zwei der drei laufen, anders als bei Portes du Soleil.

Nicht gebaut, weil pro Trail die Schwierigkeit fehlt — und die darf nicht geraten werden.

## Was steht

- **Green Hill ist lokalisiert**: Schmallenberg-Gellinghausen, Sauerland; eröffnet Juli 2022. Das war im
  Backlog noch offen.
- **Winterberg**: 18 Trails, ~20 km, dazu ein kostenloser Beginner- & Kids-Bereich. Saison 2026:
  24.4.–8.11. Bekannte Namen: SRAM Flow Country Line (1 650 m), Conti Track, Slopestyle-Area, und neu 2026
  „Fly by" (Anfänger, kleine Jumps/Sidehits) und „Jolly Jumper" (blaue Linienführung mit roten und blauen
  Sprüngen).
- **Willingen**: 10 Trails, 15,6 km. Zwei Liftsysteme: **Ettelsberg-Seilbahn** und die **K1 8er-Sesselbahn**
  für die leichteren Trails auf der rechten Bergseite.

## Was fehlt und warum

**Die Schwierigkeit pro Trail.** Für Winterberg ist nur die Verteilung bekannt („3 sehr leicht, 4 leicht,
6 mittel, 2 schwer" — was sich zu 15 statt 18 addiert, also selbst schon unsauber), nicht die Zuordnung
Trail → Stufe. Eine Verteilung ohne Zuordnung ist keine Quelle: daraus 18 Difficulties zu bilden wäre genau
das Erfinden, das `docs/adding-a-region.md` ausschließt.

**`bikepark-winterberg.de` ist bot-geschützt** — die Seite antwortet mit einer Proof-of-Work-Challenge von
zitro® Hosting, nicht mit Inhalt. Das ist derselbe Fall wie Trailforks; der Weg dahin steht in
`docs/data-sourcing-general.md` („Getting a real headless browser running"). Vorher prüfen, ob unter
`~/.cache/ms-playwright/` schon ein Chromium liegt.

## Nächste Schritte, in dieser Reihenfolge

1. Winterbergs Streckenseite mit dem Headless-Chromium holen (oder die Trailmap-PDF, falls es eine gibt) —
   daraus die Namen mit ihren Farben.
2. Willingen: `willingen.de/mtb-zone-bikepark` prüfen, ist nicht bot-geschützt.
3. Green Hill: eigene Seite suchen; der Park ist klein und jung, die Trailliste dürfte kurz sein.
4. Geometrie: für deutsche Bikeparks zuerst OSM prüfen — Winterberg ist stark befahren und dürfte gemappt
   sein. Sonst GPX beim Nutzer erfragen, das ist laut `docs/finale-ligure.md` der zuverlässigste Unblock.
5. Lifte über `tools/add_lifts.py`: Ettelsberg-Seilbahn und K1 sind namentlich bekannt; für Winterberg die
   Betreiberliste prüfen (der Park nutzt Schlepplifte und eine Sesselbahn).
