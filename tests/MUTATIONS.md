# Does it actually bite?

A suite nobody has watched fail proves nothing. This file records, per suite, **what has been verified** — a
mutation that was applied and reverted, or better, a real bug the suite caught on its first run. It also says
plainly which suites have *not* been mutation-checked yet, so nobody mistakes an untested test for a tested
one.

To verify a mutation: apply it, run the suite, confirm the listed failure, revert. Keep the counts here
current; a stale count is worse than none, because it looks like evidence.

## Verified by catching a real bug (the strongest evidence there is)

| suite | what it found, unprompted |
|---|---|
| `lists` | **A group heading in the trail list claimed 147 above hub headings adding up to 141.** The per-list hub counts had been split off when Tours moved to their own section, but the per-list *group* count still used the trails-and-Tours tally. Check: "the group counts add up to the section count". |
| `lists` | **The selected card lost its highlight on every re-render.** `render()` rebuilds every card, and only the Tour and lift lists re-marked the selected one — the trail list never did. So toggling any filter with a trail selected left the map showing a selection the sidebar denied. Fixed by one shared `reattachSelectedCard()`. Check: "the selection survives a re-render". |
| `pipeline` | **`build_profile` ignored implausible `0 m` elevations** although its own comment claimed to fill them, so a single `<ele>0</ele>` mid-track produced a full-depth dip plus a phantom climb back out. Fixed; the golden Laax rebuild in the same suite proved it changes no committed region. Check: "build_profile interpolates missing and implausible elevations". |
| `appshell` | Corrected a false belief rather than a bug: the `no-cors` rule for tiles lives in `index.html`'s preload, **not** in `sw.js`, where CLAUDE.md's wording had put it. |
| `filters` | Corrected a check that could only pass by luck: "Touren are named separately when some are hidden" matched `/Touren?/`, which demands at least "Toure", while the app correctly writes the singular "1 Tour". It had passed only because the hidden difficulty happened to contain no Tour; in bikekingdom one Tour is schwarz and the case failed against a correct app. A check whose outcome depends on which region's data it meets is worse than no check. |
| `regions` | **A region activated while "Orte" was off flashed all 17 of its place labels onto the map** before `applyPlaceVisibility()` took them away again a frame later. The count was 0 by the time anything looked, which is why it had never been noticed; the check that caught it sampled mid-fade and read 3. `buildPlaceMarkers` honours the switch at creation now, and the case watches the tooltip pane with a MutationObserver instead of sampling, so it asserts "never added" rather than "gone by now". |

## Verified by mutation

| suite | mutation | expected failure |
|---|---|---|
| `solo` | in `applyLiftVisibility`, drop the solo term: `if (passes) {` | 5 cases / 6 checks, all "got 20 lifts on the map, want 0/1/5" |
| `solo` | remove the `applyLiftSegmentOpacity()` call from `applySolo`/`clearSolo` | 3 cases / 5 checks: 26 Tour lift stretches still visible, want 0 (or 5 for the soloed Tour). Disjoint from the mutation above — the two causes of the same user report cannot mask each other |
| `filters` | in `liftPassesFilters`, restore the old Tour exemption | "🚡 off" reports 5 lifts still on the map and the Filter line missing its lift term |
| `labels` | delete the `liftLayers` loop in `applyNameLabels` | "Namen on" fails: 0 lift labels, want one per lift |
| `labels` | make `setLiftHover`'s off-branch close the tooltip unconditionally again | "hovering a lift keeps its permanent label" fails: the count drops to 0 on mouseleave |
| `lists` | drop the Tour term in `render()`'s card branch: `if (!visible) {` | "Touren in their own section" fails: the Tours are back in the trail list |
| `lists` | sort `renderTourList` by difficulty instead of by name | the same case fails on "every hub's Tours are in name order" |
| `regions` | rename the id back to `scrollTopBtn` in `syncBuilderModeChrome` | 2 cases / 5 checks: the fresh start comes up as the fatal panel with the title still "Trailmap" and its sheet closed. This mutation is also what proved a throw in the async half of `boot()` used to be **silent**, which is why `boot()` now has a `.catch` |
| `regiondata` | (built in) the suite mutates a region file itself, confirms `validate_region.py` exits non-zero, and restores it | "validate_region still bites" |
| `bearing` | drop the pane parent: `map.createPane(LIFT_BAND_PANE)` | "our own panes rotate with the trails" fails with `leaflet-map-pane`, want `leaflet-rotate-pane` — i.e. the lift bands would have stood still while their own lines turned away |
| `bearing` | in `updateHeadingCone`, drop the correction: `rotate(${headingDeg}deg)` | "the cone points up the screen" fails with got 90, want 0 ±1 — the heading counted twice, cone spinning at double rate |
| `bearing` | in `uiOffsetVector`, return `v` unrotated | 2 cases / 6 checks: the offset flips from (150, −20) to (20, 150) at bearing 90, i.e. the room reserved for the info panel is kept along map-north instead of down the screen |
| `bearing` | heal by capturing the point at the real element's centre and restoring it (`pan:false` + `setView`) instead of letting `invalidateSize` compensate | "and after the heal the position is back on the centre" fails with **259 px**, want 0 ±3 — this is the bug the user reported, and this mutation is the implementation that shipped for an hour. Worth knowing why it got that far: the case then in place fabricated the state by writing to `map._size` while the view was correctly laid out, which nothing but a test can do, and it passed the broken code. Test the container, never the cached size |
| `bearing` | make `startBearingTransition` always apply the bearing directly (`if (true \|\| delta < 1 …)`) | "switching the mode eases the map round instead of snapping it" fails: 0 distinct angles sampled, want ≥5 — the map jumps up to 180° in one frame again |
| `bearing` | drop the `ensureMapSizeCurrent()` call from `#recenterBtn`'s handler | "centring survives a container whose size Leaflet has not noticed yet" fails 4 checks: the position lands at (80,631) in a 768x320 container, i.e. off the screen, which is the landscape report verbatim. The sweep case then fails too as a cascade — with a stale size its coverage check cannot hold — so read the two together |
| `bearing` | put the old UI-avoidance offset back into `#recenterBtn`'s pan (`subtract(uiOffsetVector())`) | "the followed position sits on the rotation pivot" fails with got 518, want 434 ±2, and the orbit check reports `[65,120,169,120,65]` px — the dot circling the pivot at radius 84, which is the bug the user reported |
| `bearing` | neuter the `L.Renderer._update` sweep guard (`if (false && bearingSweeping …)`) | "turning the map does not repaint the vector renderers" fails with got 19, want 1 — 19 viewBox re-cuts in a 72-step turn, which is the stutter the user reported |
| `appshell` | set `ROTATE_URL` to a different `?v=` than index.html's `<script>` | "the rotation plugin's version is the same in both places" fails with got '1', want '2' |
| `bearing` | remove `rotateWithView: true` from the direction-arrow markers | "direction arrows turn with the map" fails: the icon carries a bare `translate3d(...)` and no `rotate()`, so every arrow points the wrong way while turned |
| `regions` | put the sub-region chips back to `display:inline-block` with `margin:0 6px 6px 0` instead of a flex row with a `gap` | "every chip that wrapped had to wrap" fails with *"Western Summits (20) had 5px to spare on the line above"* — the trailing margin of the last chip on a line counts towards that line, so pairs that fit wrapped anyway and every region box was a line too tall. Only bites at a width where some pair is a near miss, which is why the case reports the culprit and its spare pixels rather than a line count |
| `infopanel` | put `width:max-content` back in the touch layout's `#infoPanel` rule | "the panel's width does not depend on which trail is open" fails twice: the measured widths come back `[265,281,282,321,283,270]` and the CSSOM check reports `"max-content"`. The second check is the one that bites on a desktop-sized run, where that media block never applies |
| `lists` | take the card's solo button back into the text flow (`position:static; margin-left:6px`) | "selecting a card does not resize it or move the cards below it" fails 6 checks: every list reports the card growing 2.2px and its neighbour moving. Note the two causes are separable — the `.selected` border going to 2px is worth 2px on its own, and on a lift card the inline button pushed the name onto a second line, worth 19px |

## Not yet mutation-checked

`geometry`, `infopanel`, `lifts` and `builder`'s newer cases have not had a mutation applied. They pass, and
`geometry` did surface two latent gaps while being written, but that is weaker evidence than the table above.
Worth doing, in this order:

1. `geometry` — flip a sign in `latLngAtDistance`'s `reversed` branch; the reversed-endpoint checks must fail.
2. `infopanel` — make `applyReversedEndpoints` a no-op; "the green start marker moved to the other end" must
   fail while the numbers still swap, which is exactly the bug that version of the feature had.
3. `lifts` — give the Tour's lift segments the mask's width; "the hairline stayed a hairline" must fail.
