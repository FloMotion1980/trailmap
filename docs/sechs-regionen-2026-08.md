# Sechs Regionen aus einem Guss (2026-08-26) — das gemeinsame Verfahren

Davos Klosters, Vinschgau & Meran, Bormio & Valtellina, Bayerische Voralpen, Aostatal und
Tarentaise & Vanoise sind in einem Zug gebaut worden, nach derselben Methode. Diese Datei hält fest, was
für alle sechs gilt; was je Region eigen ist, steht in `docs/<region>.md`.

Ausgewählt wurden sie aus der Trailforks-Recherche über DE/AT/CH/IT/FR (`docs/backlog.md`, Abschnitt 3),
und zwar nach **Kilometern je Trail**, nicht nach Trailzahl — die Begründung steht dort.

## Quelle: Trailforks, und was das hier bedeutet

Alle sechs sind **Trailforks-only**, wie Madeira, der Gardasee und Elba. Das ist die protokollierte
Ausnahme von der Betreiber-Regel (`CLAUDE.md`), nicht ihr Gegenteil — und hier ist sie eine **bewusste
Entscheidung mit einem offenen Ende**, kein Übersehen:

* Der Nutzer hat die sechs aus einer Trailforks-Auswertung heraus bestellt („bau die 6 mal über Nacht").
* Für Davos, Vinschgau, Bormio und die Bayerischen Voralpen ist das auch sachlich richtig: das sind
  gewachsene Trailnetze ohne einen Betreiber, der eine Trailliste mit Schwierigkeiten führt.
* **Für das Aostatal und die Tarentaise ist es das nicht.** Dort sitzen echte Bikeparks mit eigenen
  Trailtabellen — Pila Bikeland, La Thuile Bike World, Cervino, Les Arcs, Tignes, Méribel, Belleville,
  La Plagne, Valmorel. Nach der stehenden Regel gewinnt deren Angabe. Das ist **offen** und in
  `docs/backlog.md` als Nacharbeit vermerkt: es sind zehn Betreiberseiten, und sie einzeln zu prüfen ist
  eine eigene Sitzung, keine Fußnote einer Nacht. Bis dahin trägt jeder dieser Trails Trailforks' Wert.

## Der Zuschnitt ist unserer, und das ist keine Kleinigkeit

Trailforks' `riding area`-Spalte ist ein Verwaltungskasten, kein Revier — das wusste das Projekt schon von
Elba und vom Gardasee, aber hier wird es besonders deutlich:

| Region | was Trailforks kennt | was daraus wurde |
|---|---|---|
| Davos | **ein** Gebiet „Davos Klosters" für alle 153 Linien | 3 Täler (Davos 79, Klosters 43, Landwasser 30) |
| Vinschgau | „Vinschgau" mit **28 km Streuung**, „Burggrafenamt" mit 18 | 6 Täler |
| Bormio | „Stelvio Natural Trail Park" — liegt im **Valfurva**, nicht am Stilfserjoch | 6 Talabschnitte |
| Voralpen | 11 Landkreis-Kästen, darunter die Münchner Isar | 8 Reviere, Isar draußen |

Die Sub-Regionen sind also durchweg **eigene Entscheidungen** (der Nutzer delegiert das ausdrücklich), und
sie sind gegen die tatsächlichen Koordinaten geprüft, nicht geschätzt: für jede Region wurden erst die
Schwerpunkte und Streuungen der geernteten Linien ausgerechnet und dann die Anker gesetzt, danach die
Abfall-Liste des Baus durchgesehen und Anker nachgezogen, wo echte Trails knapp herausgefallen wären.

## Was die Ankerregel bewusst wegwirft

Jeder Bau druckt seine Ausschlüsse. Die drei, die eine Erklärung verdienen:

* **Bayerische Voralpen: 45 Zeilen der „Isartrails"** — die Münchner Isar, 28 bis 52 km nördlich. Sie sind
  mitgeerntet (der Landkreis-Kasten enthält sie) und bekommen bewusst **keinen Anker**; ein Anker
  „München" würde die Region bis in die Stadt ziehen. Die Regel wirft sie selbst heraus.
* **Bormio: 6 Zeilen im Val di Scalve** (Passo Vivione, Venerocolo, Belviso) — Provinz Bergamo, jenseits
  des Passes, 10–29 km vom nächsten Anker.
* **Aostatal: drei Zeilen, die gar nicht im Aostatal liegen** — „Alta Val Trebbia", „Lago di Ridracoli",
  „Parco Vena del Gesso" sind Ligurien und Emilia-Romagna, bei Trailforks falsch einsortiert.

## Was allen sechs noch fehlt

**Lifte.** Keine der sechs hat ein `lifts`-Array, und das ist eine bewusste Auslassung, keine Annahme:
`docs/lifts-feature.md` verlangt die Sommerseite des Betreibers, und OSMs `aerialway:bicycle` ist als
Quelle ausdrücklich ausgeschlossen — bei Kronplatz stand es tags zuvor bei zwei Bahnen falsch. Für Davos
ist der Stand schon halb erhoben und steht in `docs/davos.md`: der Betreiber sagt „auf insgesamt sechs
Stand- und Luftseilbahnen ist der Transport mit dem Mountainbike möglich", nennt die sechs aber auf der
Seite nicht namentlich, und die Live-Liftliste wird per JS nachgeladen. Sechs solche Recherchen sind eine
eigene Aufgabe; `tools/add_lifts.py` macht sie danach billig.

**Touren.** Keine der sechs hat `loop:true`-Einträge. Die Trailforks-Tabellen führen einzelne Trails; eine
Trailrunde entsteht hier über `tools/gpx_map_match.py` oder den Tourenbuilder und braucht eine Aufzeichnung.
Für Bormio ist das konkret: die vom Nutzer erinnerte Abfahrt Bormio 3000 → Santa Caterina, siehe
`docs/bormio.md`.

## Reproduzierbar

Für jede Region liegt unter `Material/<Region>/` die geerntete Tabelle, die Geometrie und ein
`harvest_scope.json`, das festhält, aus welcher Landestabelle sie geschnitten wurde und mit welchem
Gebiets-Muster (`tools/scope_tf_table.py`). Ein Neubau braucht damit kein Netz mehr.
