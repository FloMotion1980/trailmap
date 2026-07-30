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

## Not yet mutation-checked

`geometry`, `infopanel`, `lifts` and `builder`'s newer cases have not had a mutation applied. They pass, and
`geometry` did surface two latent gaps while being written, but that is weaker evidence than the table above.
Worth doing, in this order:

1. `geometry` — flip a sign in `latLngAtDistance`'s `reversed` branch; the reversed-endpoint checks must fail.
2. `infopanel` — make `applyReversedEndpoints` a no-op; "the green start marker moved to the other end" must
   fail while the numbers still swap, which is exactly the bug that version of the feature had.
3. `lifts` — give the Tour's lift segments the mask's width; "the hairline stayed a hairline" must fail.
