# Tarentaise & Vanoise — gebaut 2026-08-26

710 Trails, 9 Sub-Regionen, 224 mit Trailforks-Bewertung, keine Lifte (siehe „Offen").
Nach dem Gardasee (916) die **zweitgrößte Region der App**.
Verfahren und Quelle: **`docs/sechs-regionen-2026-08.md`**.

## Zuschnitt: das Isère-Tal, und nur das

Die Auswahl der Gebiete ist hier die eigentliche Entscheidung, weil das Département Savoie 1 771 bewertete
Trails führt und man daraus fast jede Region schneiden könnte. Drinnen ist das **Isère-Tal von Moûtiers
aufwärts** samt seiner Seitentäler. Bewusst draußen:

* **Die Maurienne** (Val Cenis 70, Aussois 24, Modane 23, Avrieux 25, Bessans 20, Bonneval 20, Valloire 15,
  Saint-Michel 21) — das Arc-Tal hinter der Vanoise, ein eigenes Tal mit eigener Identität. Gar nicht erst
  geerntet.
* **Das Beaufortain** — geerntet, aber ohne Anker, also von der Regel selbst verworfen: `Berges du
  Roselend`, `Col Du Coin Face Nord`, `Refuge Croix Du Bonhomme`, `La Ville Des Glaciers`,
  `Sentier du Col de l'Oullion` (9–13 km vom nächsten Anker). Ein Massiv nördlich des Tals.
* **Albertville, Chambéry, Aix-les-Bains** — Flachland, und mit 0,9 km je Trail eine andere Art von Revier.

| Sub-Region | Trails | was drin ist |
|---|---:|---|
| Les 3 Vallées | 176 | Les Menuires, Val Thorens, Méribel, Mottaret, Courchevel, Saint-Martin, Brides, Bozel |
| Tignes | 107 | Tignes le Lac, les Brévières, Val Claret |
| Bourg & Séez | 77 | Bourg-Saint-Maurice, Séez, La Rosière/Montvalezan |
| Sainte-Foy | 76 | Sainte-Foy-Tarentaise, Villaroger |
| La Plagne | 76 | La Plagne, Aime, Montchavin, Champagny-en-Vanoise |
| Les Arcs | 58 | Arc 1600/1800/2000, Peisey-Nancroix, Landry |
| Valmorel | 52 | Moûtiers, Aigueblanche, La Léchère, Valmorel, Doucy, Feissons |
| Val d'Isère | 46 | Val-d'Isère, Le Fornet, La Daille |
| Vanoise | 35 | Pralognan-la-Vanoise |

**Ein Anker kam nachträglich dazu**: Feissons-sur-Isère (45,548 / 6,442), für sechs Trails am linken
Isère-Ufer gegenüber La Léchère, die sonst mit 9–10 km knapp herausgefallen wären.

## Ausgeschieden

**21 Namensdubletten** — mit Abstand der höchste Wert aller sechs Regionen, und der Grund ist die Dichte:
in einem Tal mit neun Skigebieten heißen mehrere Trails gleich. Die Regel greift nur innerhalb von
`SAME_NAME_KM` (5 km), zwei gleichnamige Trails 20 km auseinander bleiben also beide. Dazu 8
Geometriedubletten, 8 unter 80 m, 5 ohne Linie auf ihrer Trailforks-Seite und die 5 Beaufortain-Zeilen.

## Offen — und hier am dringendsten

* **Die Schwierigkeit gehört den Betreibern.** Les Arcs Bikepark, Tignes, Méribel Bikepark, Belleville
  Bikepark, La Plagne, Valmorel Bike Park und Bike Park Tignes-Val d'Isère führen alle eigene Trailtabellen
  mit eigenen Graden. Nach `CLAUDE.md`s stehender Regel gewinnen die; gebaut ist bisher Trailforks' Wert.
  Siehe `docs/backlog.md`, Abschnitt 3b — das Werkzeug (`diff_override`) steht bereit.
* **Lifte.** Sieben Bikeparks mit Sommerbetrieb, keiner davon eingetragen.
* **Nur 32 % tragen eine Bewertung** — der niedrigste Wert der sechs. Das liegt an der Menge kleiner,
  wenig befahrener Linien in den Seitentälern, nicht an einem Fehler bei der Zuordnung: alle 710 tragen
  ihren Trailforks-Slug, ein Auffrischungslauf holt neue Werte also jederzeit nach.
