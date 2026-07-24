# Finale Ligure — Master Trail Reconciliation List

Merged from 3 sources: this app's built `finale.json` (35 trails), `trailforks_trails_parsed.json` (125 entries), and the finaleoutdoor.com trail-finder export (172 entries, `Finale Outdoor Trails (parsed).md`). Names matched whitespace/accent/punctuation-insensitively (e.g. "Roller Coaster" == "Rollercoaster"). **219 unique trail names** total, of which **184 are not yet built** into the app.

## Hub-mapping findings (read before using the columns below)

`Infos Finale.md` was re-read in full for this pass. **Its current content does not match what CLAUDE.md previously documented** as the "9 remaining hubs" (Verezzi, Orco-Vezzi, Pietra Ligure/Val Maremola, Feglino, Mallare, Quiliano do not appear in it at all) — that list was stale/wrong and has been corrected in CLAUDE.md. The actual 11 named riding areas described in `Infos Finale.md` are: Le Manie (built), San Bernardino (built), **Nato Base, Melogno Din, Forte Melogno, Isallo, Monte Carmo, Backcountry (Bardineto–Castelvecchio di Rocca Barbena), Spotorno, Caprazoppa, Madonna della Guardia** (9 not yet built).

finaleoutdoor.com's own trail-finder only exposes a **coarser 6-zone** grouping (`fo_region_zone` column), which does **not** map 1:1 onto those 11 areas — confirmed by cross-checking trail names Infos Finale.md explicitly names per area (`direct_name_match_hub` column, the highest-confidence signal available since it's literal text evidence from the guide): e.g. "Madre Natura", "115", "H", "Ingegnere" are named under **Nato Base** in the prose, but finaleoutdoor.com buckets them under the **"Melogno and Alta Val Pora"** zone (not a separate Base-Nato zone) — while "Cravarezza", also named under Nato Base, falls under **"Alta Val Bormida"** instead. Base Nato's own trails are themselves geographically split across 2+ of finaleoutdoor.com's zones (plausible — enduro descents commonly start in one area and finish in a neighboring one). **Two of the 6 finaleoutdoor.com zones don't correspond to any single Infos-Finale.md area at all**: "Pietrese and Val Maremola" (42 unbuilt trails) and "Alta Val Bormida" (13 unbuilt trails) look like genuinely distinct riding clusters the prose guide doesn't describe in detail — these may deserve their own new `REGION_CATALOG` sub-regions rather than being folded into an existing hub name.

**Data-quality note**: for the already-built "Roller Coaster" trail, finaleoutdoor.com's own published stats (5.31 km, 17 m up / 449 m down) differ noticeably from what's currently in `finale.json` (6.45 km, 245 m up / 886 m down, from a user-supplied GPX file) — there's also a distinct "Rollercoaster-San Pantaleo" entry in the finaleoutdoor.com list, so this may be two different route variants rather than a simple correction; flagged here, not changed.

**Net effect**: `fo_region_zone`/`hub_guess` are a best-effort first pass, not a final assignment. Reliable per-trail hub assignment for the ~45 trails in the ambiguous "Finalese and its plateaus" bucket (covers Le Manie/San Bernardino/Base Nato/Caprazoppa/Madonna della Guardia/Isallo all at once) needs each trail's own descriptive text checked individually — not done in this pass, flagged as `AMBIGUOUS` below. Where `direct_name_match_hub` is filled in, trust that over the zone guess.

## Full list

| Name | Built? | Built hub | Direct text match | fo zone | Hub guess | In Trailforks | In finaleoutdoor | Category | Length | Up/Down | Link |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 115 |  |  | Nato Base | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) |  | ✓ | Enduro | 1.40 km | 0 m238 m | [View](https://www.finaleoutdoor.com/en/trails-walls/115) |
| A Carbonera |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 6 |  |
| Acquedotto |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | Enduro | 0.71 km | 1 m186 m | [View](https://www.finaleoutdoor.com/en/trails-walls/acquedotto) |
| Ale &amp; Ale |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Aleluia |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 6 |  |
| Aleluya |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | Enduro | 0.93 km | 2 m127 m | [View](https://www.finaleoutdoor.com/en/trails-walls/aleluya) |
| Andrassa |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Andrassa pt.2 |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 1.28 km | 8 m94 m | [View](https://www.finaleoutdoor.com/en/trails-walls/andrassa-pt-2) |
| Anello di Pianarella |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 0.99 km | 38 m48 m | [View](https://www.finaleoutdoor.com/en/trails-walls/anello-di-pianarella) |
| Appendaun |  |  | Forte Melogno | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry | ✓ | ✓ | Enduro | 2.50 km | 0 m373 m | [View](https://www.finaleoutdoor.com/en/trails-walls/appendaun) |
| Armuin |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | eMTB | 1.51 km | 16 m131 m | [View](https://www.finaleoutdoor.com/en/trails-walls/armuin) |
| Asinolla Uphill |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 0.76 km | 88 m1 m | [View](https://www.finaleoutdoor.com/en/trails-walls/asinolla-uphill) |
| Avioai |  |  |  | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry |  | ✓ | Enduro | 1.61 km | 0 m266 m | [View](https://www.finaleoutdoor.com/en/trails-walls/avioai) |
| Bardineto BeActive |  |  |  | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry |  | ✓ | eMTB | 32.63 km | 1111 m1111 m | [View](https://www.finaleoutdoor.com/en/trails-walls/dineto-beactive) |
| Base Nato |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) | ✓ | ✓ | Enduro | 2.65 km | 19 m379 m | [View](https://www.finaleoutdoor.com/en/trails-walls/base-nato) |
| Benevento Beeches |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent | ✓ | ✓ | Enduro | 1.54 km | 0 m260 m | [View](https://www.finaleoutdoor.com/en/trails-walls/benevento-beeches) |
| Bianca Alternative |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Black &amp; White |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 9 |  |
| Black Mamba |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent | ✓ | ✓ | Enduro | 2.09 km | 0 m405 m | [View](https://www.finaleoutdoor.com/en/trails-walls/black-mamba) |
| Black and White |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 1.27 km | 18 m97 m | [View](https://www.finaleoutdoor.com/en/trails-walls/black-and-white) |
| Blu Pervinca |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | All Mountain - Cross Country - Enduro | 1.25 km | 2 m76 m | [View](https://www.finaleoutdoor.com/en/trails-walls/blu-pervinca) |
| Bondi |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 3.61 km | 1 m253 m | [View](https://www.finaleoutdoor.com/en/trails-walls/bondi) |
| Bondi Traverse |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 23 |  |
| Bric Berba |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | Enduro | 1.62 km | 65 m163 m | [View](https://www.finaleoutdoor.com/en/trails-walls/bric-berba) |
| Bric Merizzo |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) |  | ✓ | Enduro | 0.73 km | 2 m96 m | [View](https://www.finaleoutdoor.com/en/trails-walls/bric-merizzo) |
| CNC |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | eMTB | 0.85 km | 84 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cnc) |
| Cacciatore |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 2.34 km | 0 m453 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cacciatore) |
| Calvisio |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 5 |  |
| Caprazoppa |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 16 |  |
| Carbonera |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent |  | ✓ | Enduro | 2.25 km | 0 m337 m | [View](https://www.finaleoutdoor.com/en/trails-walls/carbonera) |
| Carbuta |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Carcere duro |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Carmo double loop |  |  |  | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry |  | ✓ | eMTB | 23.03 km | 805 m805 m | [View](https://www.finaleoutdoor.com/en/trails-walls/carmo-double-loop) |
| Carmo per Sempre |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | Enduro | 7.51 km | 12 m1121 m | [View](https://www.finaleoutdoor.com/en/trails-walls/carmo-per-sempre) |
| Castel Gavone second part |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 7 |  |
| Cava - Tappeto Verde |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 37 |  |
| Cava-Green Carpet |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | All Mountain | 2.23 km | 27 m275 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cava-green-carpet) |
| Cavatappi |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 1 |  |
| Cavatappi Lower |  |  |  | -- | unknown |  | ✓ | Enduro | 0.65 km | 1 m220 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cavatappi-lower) |
| Cavatappi Upper |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 1.24 km | 0 m243 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cavatappi-upper) |
| Ciapin Lodge |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 6 |  |
| Ciottolato |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Collegamento Gorillaz |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 0.86 km | 19 m23 m | [View](https://www.finaleoutdoor.com/en/trails-walls/collegamento-gorillaz) |
| Collegamento Vilmar |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 37 |  |
| Cormore |  |  |  | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry |  | ✓ | Enduro | 3.32 km | 14 m463 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cormore) |
| Cravarezza |  |  | Nato Base | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent | ✓ | ✓ | Enduro | 0.78 km | 0 m152 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cravarezza-1) |
| Crestino Pt. 1 |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent | ✓ | ✓ | All Mountain | 3.41 km | 40 m238 m | [View](https://www.finaleoutdoor.com/en/trails-walls/crestino-pt-1) |
| Crestino Pt.2 |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) | ✓ | ✓ | Enduro | 3.32 km | 0 m546 m | [View](https://www.finaleoutdoor.com/en/trails-walls/crestino-pt-2) |
| Cromagnon |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 0.93 km | 2 m129 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cromagnon) |
| Cucco |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | All Mountain | 4.28 km | 102 m94 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cucco) |
| Cucco Uphill |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | eMTB | 0.58 km | 57 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cucco-uphill) |
| Cuore di Cervo |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | Enduro | 1.08 km | 0 m225 m | [View](https://www.finaleoutdoor.com/en/trails-walls/cuore-di-cervo) |
| Cà Bianca |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 2.03 km | 3 m275 m | [View](https://www.finaleoutdoor.com/en/trails-walls/ca-bianca) |
| DH Donne |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Dh Uomini |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 1.34 km | 0 m263 m | [View](https://www.finaleoutdoor.com/en/trails-walls/dh-uomini) |
| Din |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) |  | ✓ | Enduro | 2.31 km | 0 m393 m | [View](https://www.finaleoutdoor.com/en/trails-walls/din) |
| Dog Eat Dog |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | Enduro | 1.00 km | 0 m192 m | [View](https://www.finaleoutdoor.com/en/trails-walls/dog-eat-dog) |
| Dolcenera |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | All Mountain - Cross Country - Enduro | 1.05 km | 0 m270 m | [View](https://www.finaleoutdoor.com/en/trails-walls/dolcenera) |
| Dondella |  |  |  | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry |  | ✓ | Enduro | 2.44 km | 0 m435 m | [View](https://www.finaleoutdoor.com/en/trails-walls/dondella) |
| Eggplant |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | eMTB | 0.84 km | 115 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/eggplant) |
| Fast and Furious |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) | ✓ | ✓ | Enduro | 3.88 km | 5 m566 m | [View](https://www.finaleoutdoor.com/en/trails-walls/fast-and-furious) |
| Final-Borgo |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 0.94 km | 0 m138 m | [View](https://www.finaleoutdoor.com/en/trails-walls/final-borgo) |
| Finale Oltre |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 0.63 km | 83 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/finale-oltre) |
| Foresto |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | All Mountain - Cross Country - Enduro | 1.81 km | 0 m293 m | [View](https://www.finaleoutdoor.com/en/trails-walls/foresto) |
| Friendly Trail |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | All Mountain | 1.17 km | 1 m203 m | [View](https://www.finaleoutdoor.com/en/trails-walls/friendly-trail) |
| Gabry |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | All Mountain | 0.56 km | 1 m60 m | [View](https://www.finaleoutdoor.com/en/trails-walls/gabri) |
| Geologico |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | All Mountain | 0.98 km | 0 m119 m | [View](https://www.finaleoutdoor.com/en/trails-walls/geologico) |
| Gorillaz |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 1.02 km | 38 m117 m | [View](https://www.finaleoutdoor.com/en/trails-walls/gorillaz) |
| Gorra |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 102 |  |
| Gorra Uphill |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | eMTB | 0.83 km | 114 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/gorra-uphill) |
| Green River |  |  |  | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry |  | ✓ | Enduro | 2.69 km | 4 m354 m | [View](https://www.finaleoutdoor.com/en/trails-walls/green-river) |
| Grollon |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent |  | ✓ | Enduro | 2.05 km | 0 m217 m | [View](https://www.finaleoutdoor.com/en/trails-walls/grollon) |
| Grollon 2°pt |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 5 |  |
| Guidone |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | Enduro | 1.13 km | 18 m107 m | [View](https://www.finaleoutdoor.com/en/trails-walls/guidone) |
| Guidone Pt. 2 |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | Enduro | 0.70 km | 0 m104 m | [View](https://www.finaleoutdoor.com/en/trails-walls/guidone-pt-2) |
| Gump |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 0.43 km | 44 m6 m | [View](https://www.finaleoutdoor.com/en/trails-walls/gump) |
| H |  |  | Nato Base | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) |  | ✓ | Enduro | 1.35 km | 0 m247 m | [View](https://www.finaleoutdoor.com/en/trails-walls/h) |
| H Veloce |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) | ✓ | ✓ | Enduro | 2.80 km | 0 m297 m | [View](https://www.finaleoutdoor.com/en/trails-walls/h-veloce) |
| H trail |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Hay Trail (Sentiero del Fieno) |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 1.15 km | 211 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/hay-trail-sentiero-del-fieno) |
| Hell Boy part 1 |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | All Mountain | 1.97 km | 0 m247 m | [View](https://www.finaleoutdoor.com/en/trails-walls/hell-boy-part-1) |
| Hell Boy part 2 |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | All Mountain | 1.50 km | 6 m220 m | [View](https://www.finaleoutdoor.com/en/trails-walls/hell-boy-part-2) |
| Hiroshima Mon Amour |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | Enduro | 2.17 km | 0 m375 m | [View](https://www.finaleoutdoor.com/en/trails-walls/hiroshima-mon-amour) |
| Ingegnere |  |  | Nato Base | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) | ✓ | ✓ | Enduro | 3.77 km | 0 m547 m | [View](https://www.finaleoutdoor.com/en/trails-walls/ingegnere) |
| Isallo Extasi |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) |  | ✓ | Enduro | 5.00 km | 2 m813 m | [View](https://www.finaleoutdoor.com/en/trails-walls/isallo-extasi) |
| Justanice Trail |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 37 |  |
| Karma Trail |  |  | Monte Carmo | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | Enduro | 6.51 km | 0 m1095 m | [View](https://www.finaleoutdoor.com/en/trails-walls/karma-trail) |
| Kill Bill 1 |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 0.95 km | 0 m193 m | [View](https://www.finaleoutdoor.com/en/trails-walls/kill-bill-1) |
| Kill Bill 2 |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 1.03 km | 0 m220 m | [View](https://www.finaleoutdoor.com/en/trails-walls/kill-bill-2) |
| L'Estremo |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 0.29 km | 12 m21 m | [View](https://www.finaleoutdoor.com/en/trails-walls/l-estremo) |
| La Folia |  |  |  | The Island Bay and Levante Area | Spotorno | ✓ | ✓ | Enduro | 2.82 km | 9 m333 m | [View](https://www.finaleoutdoor.com/en/trails-walls/la-folia) |
| La Rete |  |  |  | The Island Bay and Levante Area | Spotorno | ✓ | ✓ | Enduro | 1.17 km | 0 m214 m | [View](https://www.finaleoutdoor.com/en/trails-walls/la-rete) |
| Link |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent |  | ✓ | Enduro | 1.38 km | 29 m114 m | [View](https://www.finaleoutdoor.com/en/trails-walls/link) |
| Little Champery |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 1.65 km | 1 m269 m | [View](https://www.finaleoutdoor.com/en/trails-walls/little-champery) |
| Little Dog |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent | ✓ | ✓ | Enduro | 1.65 km | 16 m314 m | [View](https://www.finaleoutdoor.com/en/trails-walls/little-dog) |
| Ludi Trail |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 1 |  |
| Lupin Feglino |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Madonna della Guardia |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 1.07 km | 0 m194 m | [View](https://www.finaleoutdoor.com/en/trails-walls/madonna-della-guardia) |
| Madonnina |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | eMTB | 0.42 km | 63 m9 m | [View](https://www.finaleoutdoor.com/en/trails-walls/madonnina) |
| Madre Natura |  |  | Nato Base | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) | ✓ | ✓ | Enduro | 2.03 km | 0 m336 m | [View](https://www.finaleoutdoor.com/en/trails-walls/madre-natura) |
| Mao Crest |  |  |  | The Island Bay and Levante Area | Spotorno | ✓ | ✓ | Enduro | 2.51 km | 0 m363 m | [View](https://www.finaleoutdoor.com/en/trails-walls/mao-crest) |
| Margot |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 0.69 km | 9 m126 m | [View](https://www.finaleoutdoor.com/en/trails-walls/margot) |
| Martina |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Monte Alto |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | All Mountain | 2.57 km | 156 m69 m | [View](https://www.finaleoutdoor.com/en/trails-walls/monte-alto) |
| Monte Grosso Trail |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Monte Grosso Uphill |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | eMTB | 0.43 km | 85 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/monte-grosso-uphill) |
| Monte Sant'Elena-Decolli |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | All Mountain | 2.70 km | 50 m54 m | [View](https://www.finaleoutdoor.com/en/trails-walls/monte-sant-elena-decolli) |
| Mulino |  |  |  | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry |  | ✓ | Enduro | 1.33 km | 0 m179 m | [View](https://www.finaleoutdoor.com/en/trails-walls/mulino) |
| Muro Nero |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | eMTB | 0.27 km | 30 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/muro-nero) |
| Neanderthal |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 1.50 km | 0 m182 m | [View](https://www.finaleoutdoor.com/en/trails-walls/neanderthal) |
| Neverland |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent | ✓ | ✓ | Enduro | 1.41 km | 3 m222 m | [View](https://www.finaleoutdoor.com/en/trails-walls/neverland) |
| North Shore |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent |  | ✓ | Enduro | 1.96 km | 0 m209 m | [View](https://www.finaleoutdoor.com/en/trails-walls/north-shore) |
| Oltrefinale |  |  | Monte Carmo | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | All Mountain | 4.13 km | 13 m573 m | [View](https://www.finaleoutdoor.com/en/trails-walls/oltrefinale) |
| One Shot |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | All Mountain - Cross Country - Enduro | 0.66 km | 14 m53 m | [View](https://www.finaleoutdoor.com/en/trails-walls/one-shot) |
| Orera Trail |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | eMTB | 1.37 km | 85 m87 m | [View](https://www.finaleoutdoor.com/en/trails-walls/orera-trail) |
| Oribago |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 0.80 km | 0 m124 m | [View](https://www.finaleoutdoor.com/en/trails-walls/oribago) |
| Oribago 2 |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 0.48 km | 7 m64 m | [View](https://www.finaleoutdoor.com/en/trails-walls/oribago-2) |
| Orto Botanico |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | All Mountain | 2.02 km | 109 m44 m | [View](https://www.finaleoutdoor.com/en/trails-walls/orto-botanico) |
| Pagliarina |  |  |  | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry |  | ✓ | Enduro | 2.25 km | 0 m303 m | [View](https://www.finaleoutdoor.com/en/trails-walls/pagliarina) |
| Parsifal |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | All Mountain | 1.35 km | 27 m36 m | [View](https://www.finaleoutdoor.com/en/trails-walls/parsifal) |
| Partigiano |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) | ✓ | ✓ | Enduro | 2.44 km | 147 m5 m | [View](https://www.finaleoutdoor.com/en/trails-walls/partigiano) |
| Pernice Rossa |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 1 |  |
| Pian Marino Top |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 0.75 km | 5 m59 m | [View](https://www.finaleoutdoor.com/en/trails-walls/pian-marino-top) |
| Pian Marino-Cia |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | All Mountain | 2.64 km | 26 m104 m | [View](https://www.finaleoutdoor.com/en/trails-walls/pian-marino-cia) |
| Pianfieno |  |  | Forte Melogno | Bardineto and north of Monte Carmo | Monte Carmo / Backcountry |  | ✓ | Enduro | 3.33 km | 0 m395 m | [View](https://www.finaleoutdoor.com/en/trails-walls/pianfieno) |
| Pino Morto |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 0.81 km | 2 m157 m | [View](https://www.finaleoutdoor.com/en/trails-walls/pino-morto) |
| Pollaio Felice |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 2.92 km | 101 m93 m | [View](https://www.finaleoutdoor.com/en/trails-walls/pollaio-felice) |
| Poste |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 2 |  |
| Revenant |  |  | Isallo | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) | ✓ | ✓ | Enduro | 0.92 km | 2 m153 m | [View](https://www.finaleoutdoor.com/en/trails-walls/revenant) |
| River |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent |  | ✓ | Enduro | 1.90 km | 7 m200 m | [View](https://www.finaleoutdoor.com/en/trails-walls/river) |
| Rocche Gianche |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 2.04 km | 22 m240 m | [View](https://www.finaleoutdoor.com/en/trails-walls/rocche-gianche) |
| Rocche Sposate |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | Enduro | 1.40 km | 45 m80 m | [View](https://www.finaleoutdoor.com/en/trails-walls/rocche-sposate) |
| RocknRolla |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | Enduro | 0.56 km | 0 m113 m | [View](https://www.finaleoutdoor.com/en/trails-walls/rocknrolla) |
| Roll Up |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) |  | ✓ | eMTB | 4.92 km | 436 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/roll-up) |
| Rollercoaster-San Pantaleo |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) |  | ✓ | Enduro | 1.21 km | 0 m194 m | [View](https://www.finaleoutdoor.com/en/trails-walls/rollercoaster-san-pantaleo) |
| Rose di Pietra |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 1.29 km | 180 m3 m | [View](https://www.finaleoutdoor.com/en/trails-walls/rose-di-pietra) |
| Route Bella |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | eMTB | 1.49 km | 153 m27 m | [View](https://www.finaleoutdoor.com/en/trails-walls/route-bella) |
| Ruote di Pietra |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| S. Stefano DH |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | Enduro | 1.13 km | 0 m176 m | [View](https://www.finaleoutdoor.com/en/trails-walls/s-stefano-dh) |
| Salite di Livello Pt.1 |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 1.15 km | 168 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/salite-di-livello-pt-1) |
| Salite di Livello Pt.2 |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 0.29 km | 41 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/salite-di-livello-pt-2) |
| Scala Santa |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | Enduro | 0.66 km | 0 m194 m | [View](https://www.finaleoutdoor.com/en/trails-walls/scala-santa) |
| Scoglio di Venso |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | All Mountain - Cross Country - Enduro | 0.40 km | 3 m32 m | [View](https://www.finaleoutdoor.com/en/trails-walls/scoglio-di-venso) |
| Sentiero del Fieno |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 209 |  |
| Sentiero delle Neviere |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 1 |  |
| Sentiero indiano |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Simona |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent |  | ✓ | Enduro | 2.37 km | 9 m224 m | [View](https://www.finaleoutdoor.com/en/trails-walls/simona) |
| Stai Carmo |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | Enduro | 0.48 km | 1 m83 m | [View](https://www.finaleoutdoor.com/en/trails-walls/stai-carmo) |
| Stalitto Trail |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 1.17 km | 42 m56 m | [View](https://www.finaleoutdoor.com/en/trails-walls/stalitto-trail) |
| Strinate |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 0.68 km | 0 m144 m | [View](https://www.finaleoutdoor.com/en/trails-walls/strinate) |
| Sugheri |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | eMTB | 1.69 km | 259 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/sugheri) |
| Supergroppo |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 6.02 km | 0 m592 m | [View](https://www.finaleoutdoor.com/en/trails-walls/supergroppo) |
| Tagliate |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | All Mountain | 3.53 km | 3 m144 m | [View](https://www.finaleoutdoor.com/en/trails-walls/tagliate) |
| Tampa |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 10 |  |
| Tecci |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | eMTB | 0.69 km | 2 m124 m | [View](https://www.finaleoutdoor.com/en/trails-walls/tecci) |
| Terra di Mezzo |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 1.10 km | 12 m62 m | [View](https://www.finaleoutdoor.com/en/trails-walls/terra-di-mezzo) |
| Tino |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 0.64 km | 101 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/tino) |
| Titalana |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | All Mountain | 1.69 km | 2 m325 m | [View](https://www.finaleoutdoor.com/en/trails-walls/titalana) |
| Toboga Canova New |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Toboga di Canova |  |  | Melogno Din |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Toboga di Canova Lower |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) |  | ✓ | Enduro | 3.12 km | 0 m403 m | [View](https://www.finaleoutdoor.com/en/trails-walls/toboga-di-canova-lower-1) |
| Toboga di Canova Upper |  |  |  | Melogno and Alta Val Pora | Melogno (Din+Forte) or Base Nato (zone covers both, see findings) |  | ✓ | Enduro | 2.41 km | 0 m264 m | [View](https://www.finaleoutdoor.com/en/trails-walls/toboga-di-canova-upper) |
| Trail del Boccion |  |  |  | Alta Val Bormida | NEW hub candidate (not in Infos-Finale.md's 11 areas) -- maybe Backcountry/Base-Nato-adjacent |  | ✓ | Enduro | 4.97 km | 6 m503 m | [View](https://www.finaleoutdoor.com/en/trails-walls/trail-del-boccion) |
| Trail of Thorns |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | Enduro | 0.99 km | 20 m59 m | [View](https://www.finaleoutdoor.com/en/trails-walls/trail-of-thorns) |
| Traliccio |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 3 |  |
| Trincea |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | eMTB | 0.53 km | 49 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/trincea-1) |
| True to the Line |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | Enduro | 0.53 km | 13 m56 m | [View](https://www.finaleoutdoor.com/en/trails-walls/true-to-the-line) |
| U maxin de pippe |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| UCIENDUROWORLDCUP2025:PietraLigure(E / ENDURO WORLD CUP 2025: Pietra Ligure (E-EDR) |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | eMTB | 30.78 km | 1387 m1402 m | [View](https://www.finaleoutdoor.com/en/trails-walls/uci-enduro-world-cup-2025-pietra-ligure-e-edr) |
| Vaixella |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) | ✓ | ✓ | eMTB | 0.77 km | 111 m6 m | [View](https://www.finaleoutdoor.com/en/trails-walls/vaixella) |
| Val Nava |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 2.28 km | 15 m168 m | [View](https://www.finaleoutdoor.com/en/trails-walls/val-nava) |
| Vallunga Uphill |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo |  | ✓ | eMTB | 0.81 km | 152 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/vallunga-uphill) |
| Variante Rian da Colla |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | eMTB | 1.50 km | 40 m123 m | [View](https://www.finaleoutdoor.com/en/trails-walls/variante-rian-da-colla) |
| Variante Rocche Gianche |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 0.77 km | 0 m39 m | [View](https://www.finaleoutdoor.com/en/trails-walls/variante-rocche-gianche) |
| Via Antica Romana |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 16 |  |
| Via Caffaro |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Via Laiolo |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 0 |  |
| Via alla Rocca |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | All Mountain | 2.53 km | 219 m18 m | [View](https://www.finaleoutdoor.com/en/trails-walls/via-alla-rocca) |
| Via degli Alpini |  |  |  |  | unknown -- no region signal | ✓ |  |  |  | 9 |  |
| Vilmar |  |  |  | The Island Bay and Levante Area | Spotorno |  | ✓ | All Mountain | 1.50 km | 13 m123 m | [View](https://www.finaleoutdoor.com/en/trails-walls/vilmar) |
| Wheels of Pietra |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | Enduro | 1.93 km | 0 m290 m | [View](https://www.finaleoutdoor.com/en/trails-walls/wheels-of-pietra) |
| X-Men |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 2.25 km | 9 m227 m | [View](https://www.finaleoutdoor.com/en/trails-walls/x-men) |
| XC Giustenice |  |  |  | Pietrese and Val Maremola | NEW hub candidate (not in Infos-Finale.md's 11 areas) |  | ✓ | All Mountain - Enduro | 2.13 km | 5 m117 m | [View](https://www.finaleoutdoor.com/en/trails-walls/355-xc-giustenice) |
| Ötzi |  |  |  | Finalese and its plateaus | AMBIGUOUS: Le Manie / San Bernardino / Base Nato / Caprazoppa / Madonna della Guardia / Isallo | ✓ | ✓ | Enduro | 2.02 km | 70 m189 m | [View](https://www.finaleoutdoor.com/en/trails-walls/otzi) |
| 24H | ✅ | le_manie |  |  | le_manie |  |  |  |  |  |  |
| A.N.A. | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | eMTB | 1.22 km | 215 m2 m | [View](https://www.finaleoutdoor.com/en/trails-walls/a-n-a) |
| Acquaviva | ✅ | le_manie |  |  | le_manie |  |  |  |  |  |  |
| Andrassa pt.1 | ✅ | le_manie |  | Finalese and its plateaus | le_manie |  | ✓ | Enduro | 1.49 km | 0 m134 m | [View](https://www.finaleoutdoor.com/en/trails-walls/andrassa-pt-1) |
| Anello dell'Arma | ✅ | le_manie |  | Finalese and its plateaus | le_manie | ✓ | ✓ | All Mountain | 2.42 km | 91 m44 m | [View](https://www.finaleoutdoor.com/en/trails-walls/anello-dell-arma) |
| Borderline | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | Enduro | 1.79 km | 1 m186 m | [View](https://www.finaleoutdoor.com/en/trails-walls/borderline) |
| Borgata Costa | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | All Mountain | 0.88 km | 35 m69 m | [View](https://www.finaleoutdoor.com/en/trails-walls/borgata-costa) |
| Briga Destra | ✅ | le_manie |  | Finalese and its plateaus | le_manie | ✓ | ✓ | Enduro | 2.96 km | 0 m255 m | [View](https://www.finaleoutdoor.com/en/trails-walls/briga-destra) |
| Briga Sinistra | ✅ | le_manie |  | Finalese and its plateaus | le_manie | ✓ | ✓ | Enduro | 2.46 km | 0 m252 m | [View](https://www.finaleoutdoor.com/en/trails-walls/briga-sinistra) |
| Brighella | ✅ | le_manie |  | Finalese and its plateaus | le_manie | ✓ | ✓ | Enduro | 0.83 km | 1 m141 m | [View](https://www.finaleoutdoor.com/en/trails-walls/brighella) |
| Cave | ✅ | le_manie |  | Finalese and its plateaus | le_manie | ✓ | ✓ | All Mountain | 1.16 km | 1 m156 m | [View](https://www.finaleoutdoor.com/en/trails-walls/-cave) |
| Ciappi | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | All Mountain | 2.00 km | 68 m94 m | [View](https://www.finaleoutdoor.com/en/trails-walls/ciappi) |
| Cà del Vacchè | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | Enduro | 3.07 km | 0 m287 m | [View](https://www.finaleoutdoor.com/en/trails-walls/ca-del-vacche) |
| Cà du Puncin | ✅ | le_manie |  | Finalese and its plateaus | le_manie | ✓ | ✓ | All Mountain | 1.72 km | 2 m145 m | [View](https://www.finaleoutdoor.com/en/trails-walls/ca-du-puncin) |
| DH Men | ✅ | le_manie |  |  | le_manie |  |  |  |  |  |  |
| DH Women | ✅ | le_manie |  | Finalese and its plateaus | le_manie |  | ✓ | Enduro | 1.29 km | 0 m183 m | [View](https://www.finaleoutdoor.com/en/trails-walls/dh-women) |
| Diamante | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino |  | ✓ | eMTB | 0.84 km | 34 m6 m | [View](https://www.finaleoutdoor.com/en/trails-walls/diamante) |
| Dolmen | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | Enduro | 1.87 km | 0 m211 m | [View](https://www.finaleoutdoor.com/en/trails-walls/dolmen) |
| Fornaci | ✅ | le_manie |  | Finalese and its plateaus | le_manie |  | ✓ | Enduro | 0.95 km | 7 m88 m | [View](https://www.finaleoutdoor.com/en/trails-walls/fornaci) |
| Legnino | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | eMTB | 0.55 km | 69 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/legnino) |
| Manie Uphill | ✅ | le_manie |  | Finalese and its plateaus | le_manie |  | ✓ | eMTB | 1.29 km | 108 m1 m | [View](https://www.finaleoutdoor.com/en/trails-walls/manie-uphill) |
| Megalithic | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | Enduro | 1.54 km | 12 m110 m | [View](https://www.finaleoutdoor.com/en/trails-walls/megalithic) |
| Pianarella | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | Enduro | 2.06 km | 32 m269 m | [View](https://www.finaleoutdoor.com/en/trails-walls/pianarella) |
| Polveriera | ✅ | le_manie |  |  | le_manie |  |  |  |  |  |  |
| Ponti Romani | ✅ | le_manie |  |  | le_manie | ✓ |  |  |  | 174 |  |
| Radici | ✅ | le_manie |  | Finalese and its plateaus | le_manie |  | ✓ | eMTB | 1.36 km | 99 m1 m | [View](https://www.finaleoutdoor.com/en/trails-walls/radici) |
| Roller Coaster | ✅ | melogno | Melogno Din | Melogno and Alta Val Pora | melogno | ✓ | ✓ | Enduro | 5.31 km | 17 m449 m | [View](https://www.finaleoutdoor.com/en/trails-walls/rollercoaster) |
| Ruggetta | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | Enduro | 1.98 km | 0 m187 m | [View](https://www.finaleoutdoor.com/en/trails-walls/ruggetta) |
| San Michele | ✅ | le_manie |  | Finalese and its plateaus | le_manie | ✓ | ✓ | Enduro | 1.50 km | 5 m277 m | [View](https://www.finaleoutdoor.com/en/trails-walls/san-michele) |
| Semaforo | ✅ | le_manie |  | Finalese and its plateaus | le_manie | ✓ | ✓ | All Mountain | 2.82 km | 0 m244 m | [View](https://www.finaleoutdoor.com/en/trails-walls/semaforo) |
| Sentiero Amico | ✅ | le_manie |  |  | le_manie | ✓ |  |  |  | 0 |  |
| Sentiero dei Ciechi | ✅ | le_manie |  | Finalese and its plateaus | le_manie |  | ✓ | All Mountain | 2.29 km | 181 m58 m | [View](https://www.finaleoutdoor.com/en/trails-walls/sentiero-dei-ciechi) |
| Sporting | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino | ✓ | ✓ | eMTB | 1.22 km | 144 m0 m | [View](https://www.finaleoutdoor.com/en/trails-walls/sporting) |
| Voltage | ✅ | le_manie |  | Finalese and its plateaus | le_manie | ✓ | ✓ | eMTB | 1.57 km | 81 m104 m | [View](https://www.finaleoutdoor.com/en/trails-walls/voltage) |
| X-Ray | ✅ | san_bernardino |  | Finalese and its plateaus | san_bernardino |  | ✓ | Enduro | 0.68 km | 0 m83 m | [View](https://www.finaleoutdoor.com/en/trails-walls/x-ray) |
