# Sidebar filter panel: collapsible sections, counts, current-region indicator

Split out of `CLAUDE.md` 2026-07-23 to keep that file lean — this section went through several rapid iteration rounds the same day and will likely keep evolving.

## Collapsible sections (added 2026-07-23)

The filter groups above the trail list are each a plain `<details class="filter-section"><summary>...</summary>...</details>` — no JS needed for the open/close behavior itself, only for persisting which sections are open (`persistFilterSectionsState()`/`initFilterSections()`, keyed by each `<details>`'s own `id` into a separate `trailmap-ui-sections-v1` localStorage key — deliberately *not* folded into the `activeRegions`/`activeDiffs`/etc. state blob persisted by `persistActiveState()`, since open/closed is UI layout state, not a filter value). Done specifically to reclaim vertical space for the trail list, per the user's request to "besser strukturieren und Platz schaffen". The preload button's previously always-visible `.preload-hint` explainer paragraph was folded into a `title` attribute on `#preloadBtn` itself instead (same text, shown on hover/long-press) rather than kept as permanent on-screen real estate for a rarely-used feature.

**Sections and what's in each** (renamed/regrouped 2026-07-23 after the first pass):
- `#secRegion` ("Region", open by default) — the region-group chips, plus (see below) the current-region indicator.
- `#secFilter` ("Filter", open by default — renamed from "Schwierigkeit" once it became clear it holds more than just difficulty) — the difficulty chips plus the `showDownhillToggle`/`showUphillToggle`/`showLoopToggle` category toggles, plus the visible-trail-count text (see below).
- `#secMapOptions` ("Kartenoptionen", closed by default — renamed from "Kartenebene", expanded to be the catch-all for map-*display* options rather than just the base-layer chips) — base layer chips, the `showNamesToggle` toggle (moved here from Filter: showing name labels is a map-display option, not a trail filter), and the preload button.
- `#secTrails` ("Trails", open by default, sibling of `.filters` rather than inside it — `details.filter-section` styling doesn't care about DOM nesting depth, only the class) — wraps `#trailList`.

When adding a new toggle/control, sort it by this test: does it change *which* trails are shown (→ Filter) or *how* the map displays things (→ Kartenoptionen)?

### A margin regression, found and fixed the same day

An initial across-the-board `details.filter-section > *:not(summary){ margin-top:10px; }` rule (added when these sections were first built) had *higher CSS specificity* than `.region-groups-container`'s own `margin-top:14px`, silently shrinking it from 14px to 10px — just enough that the first region-group-block's legend (which overlaps its own box's top border via `transform:translateY(-50%)`) started covering the "Region" heading again, a bug already fixed once before this rewrite. Fixed by moving the spacing onto `summary` itself (`margin:0 0 8px`, mirroring the original `.filters h2` rule these sections replaced) and removing the blanket child rule entirely, so each section's own child elements keep whatever specific margin they already had.

**Lesson**: a "give every child some breathing room" rule is risky to add retroactively onto markup where children already carry their own hand-tuned spacing — specificity, not source order, decides which one wins, and it's easy to not notice which one that is until a visual regression is reported.

### Accordion disclosure arrow

`summary::after{ content:"▸" }` went through two size bumps the same day, both per direct user feedback ("viel zu klein" → 16px, then still "könnte immernoch größer sein" → **22px**, `font-weight:700`) and is colored `var(--forest)` rather than the muted `var(--stone)` label color, so it reads clearly as an interactive affordance rather than blending into the heading text.

### #secTrails indentation bug (found and fixed same day)

Being outside `.filters` meant `#secTrails`'s summary didn't inherit `.filters`' own 16px horizontal padding the way "Region"/"Filter"/"Kartenoptionen" do, so the "Trails" heading sat flush against the sidebar edge while its own content below (`.hub-title`/`.trail-card`, which already carry their *own* left padding/margin independent of any wrapper) stayed correctly indented — found by the user as "Trails ist nicht richtig eingerückt". Fixed with a scoped `#secTrails > summary{ padding: 0 16px; }` — deliberately padding only the summary, not the whole `#secTrails` container, since padding the container too would double up with the content's own indentation and misalign things the other way.

**General lesson**: when a new collapsible section lives *outside* the container that used to supply shared spacing/padding for sibling sections, check specifically whether it silently lost that inherited spacing — this bit twice in the same feature (this one, plus the margin regression above), so treat it as a recurring risk class for this UI pattern, not a one-off.

## Dynamic meta text in a summary heading (added 2026-07-23)

The old standalone always-visible `#countLine` ("X von Y Trails sichtbar") was removed entirely — that text moved *into* `#secFilter`'s own summary line instead (shortened to `${shown}/${total} sichtbar` to fit the tighter space), since it's Filter's settings that determine what counts as visible.

**Split on 2026-07-30, extended 2026-07-31** as Lifte and then Touren each became a list section of their own: each summary answers only the question its own section is about. **Trails**, **Touren** and **Lifte** each state what they are currently listing (`141 Trails`, `6 Touren`, `20 Lifte`); **Filter** — the section you open in order to change that — states what its settings are *costing* you (`27 Trails · 2 Touren · 20 Lifte ausgeblendet`, one term per hidden kind in list order, or `alles sichtbar` when nothing is). No section repeats another's number, and the "nothing is hidden" case is stated outright instead of being left to infer from `141/141`. Every total counts loaded regions only: the trail and Tour tallies come from the region loop, which iterates `REGION_GROUPS` (activated groups only), and `LIFTS` likewise holds only activated groups' lifts — so deactivating a region does not read as "hidden".

## The Region section became the region manager (2026-07-31)

Adding and removing regions used to live entirely in the `#regionDialog`, while the sidebar only *showed* what
was active. Now the section you look at is the section you act in:

- **✕ per region box**, top-right, straddling the border like the legend. Calls `deactivateRegionGroup`
  **immediately, without a confirmation** — the user's explicit choice. It took the slot the 📍 had held since
  2026-07-28, and for the same reason that slot was chosen: it is the one position in the box that does not
  move with the length of the region's name. The 30×28 box and the `-6px` offset are inherited too, because
  they are what puts the *glyph* on the same vertical line as the section carets (x=333, verified).
- **📍 in a right-aligned footer row inside the box.** The first attempt pinned it onto the *bottom* border,
  mirroring the ✕ — and that collides by construction: a 28px button centred on a border reaches 14px past it,
  straight into the next box's legend, whose own height depends on whether a long region name wraps to two
  lines. So the overlap would appear and disappear as regions are added. In normal flow it cannot overlap
  anything, and it is still the box's bottom-right corner. Diagonally opposite the ✕ either way, which is the
  actual requirement: "jump to this region" and "unload this region" must not be adjacent tap targets.
- **`#addRegionBtn` below the boxes**, dashed outline, full width. **Disabled rather than hidden** at
  `MAX_ACTIVE_REGION_GROUPS` — a button that vanishes at three teaches nothing, a greyed one whose label reads
  "＋ Maximal 3 Regionen" does. It opens the same dialog the header button opens; one dialog, two entry points.
- **The header button and the full dialog both stay.** The header doubles as the "what is loaded" readout and
  is reachable without opening the drawer; the dialog still lists every region with active ones marked, so
  deactivating works in either place.

One behaviour worth knowing rather than fixing: **closing a region and re-adding it moves its box to the
bottom**, because `REGION_GROUPS` is keyed in activation order. The `regions` suite compares the active set,
not the order, for exactly this reason.

## Three list sections: Trails, Touren, Lifte (2026-07-31)

Each object kind gets its own list, in that order, because each is chosen by a different question — which trail do I ride next, which whole day out do I pick, which cable gets me up. The **sub-region chip counts stay "everything visible in this region", Tours included**: a sub-region like Bike Kingdom's "Biketicket 2 Ride" holds nothing but Tours, and a chip reading `(0)` next to four visible Tours would be a lie. Only the per-list hub headings count their own list, which is why `render()` keeps `regionTrailCounts`/`regionTourCounts` alongside `regionVisibleCounts`.

Two things are deliberately *not* mirrored from the Trails list:

- **Tours are sorted by name, not by difficulty** (numeric-aware, so `615` precedes `616` and both precede the unnumbered ones). A Tour is picked as a whole outing, and the numbered series a region publishes is the order a rider looks for. The difficulty *badge* stays — unlike a lift, a Tour has one — it just is not the sort key.
- **The 🔁 badge is gone from the cards.** In a section that contains nothing but Tours it would be on every card and on none anywhere else. It stays in the info panel, which is the one place a Tour and a trail still meet.

The visibility rule lives in **one** function, `trailPassesFilters(t)`, used by both the map loop in `render()` and `renderTourList()` — the two must not be able to disagree about what is shown. The card itself comes from one shared `makeTrailCard()`, so solo, hover, the builder route and the click behaviour cannot drift between the two lists. Both switches (🔁 and 🚡) stay up in **Filter** with the other visibility switches, per the user: a list section is a list, not a filter home.

Every new list section also has to be added to the `#secTrails > summary, #secTouren > summary, #secLifts > summary` padding rule in `style.css` — they sit outside `.filters` and do not inherit its 16px indent, which has now been the same regression twice.

A summary that needs this kind of dynamic meta text alongside its static label wraps both in one `.section-title-row` span:
```html
<summary><span class="section-title-row"><span>Filter</span><span class="section-meta" id="…">…</span></span></summary>
```
**Not** two separate direct children of `<summary>` — because `summary{display:flex; justify-content:space-between}` only expects exactly two flex participants (the content, and the generated `::after` arrow); a third real child would get spread apart by `space-between` too, instead of hugging the label. `.section-meta` explicitly resets `text-transform`/`letter-spacing` (inherited as uppercase/spaced from the summary's own heading style, wrong for a lowercase count/region string) and truncates via `text-overflow:ellipsis` if the sidebar is ever narrow enough to need it.

### Current-region-in-heading (added 2026-07-23, moved same day)

`#secRegion`'s summary shows, via the same `.section-title-row`/`.section-meta` pattern, which active region *group* the map's current center is inside (`updateCurrentRegionLabel()`, driven by `map.on("moveend", …)` plus a call from `rebuildRegionChips()` since the active-group set itself can change without the map moving). Deliberately **group-level only** (e.g. "Donnersberg", not "MTB Donnersberger Land") — sub-regions have no bounding box of their own in this data model, only `REGION_CATALOG[group].bounds` exists, so finer granularity isn't available without adding new per-sub-region data. Checks each currently-active group's catalog bounds via `L.latLngBounds(...).contains(map.getCenter())`; shows nothing if the center falls outside every active group's bounds (e.g. panned away to open water or a gap between two regions).

**First placed in `#secTrails`'s summary instead** (a judgment call on an ambiguous instruction, reasoning it read more naturally next to "here's what's currently displayed below") — the user asked for it back on "Region" after all, once they saw both: "Region" already controls region *selection* (a multi-active-group toggle list), so a live "the map is currently in X" readout fits there as "here's which of my selected regions you're looking at right now", rather than being read as agreeing with "Trails" list content specifically. `#secTrails`'s summary is back to plain text `Trails` (no `.section-title-row` wrapper needed there anymore) — only `#secRegion` uses the wrapper now, alongside `#secFilter`.

**Lesson**: when a placement/design choice is made on a genuinely ambiguous instruction, consider surfacing it as a quick question before implementing, rather than picking one and explaining the reasoning after the fact — explaining the reasoning doesn't substitute for asking, since the user can find it sound and still prefer the other option.

## Region-group/sub-region visible-trail counts (added 2026-07-23)

Both the sidebar's region-group label/sub-region chips *and* the trail list's own group/hub headings (`.region-group-title`/`.hub-title`) show a trailing `(n)` — the count of that region's/group's currently *visible* trails, i.e. gated by region-active AND diff AND category filters, the exact same "visible" definition used by the global `${shown}/${total} sichtbar` text. Deliberately shows `(0)` when a sub-region itself is toggled off (rather than "how many you'd see if you turned it on"), to stay literally consistent with what "sichtbar" already means everywhere else in this app. The user first asked for this only in the trail list, then confirmed the sidebar chips (an unplanned first pass) were also welcome to stay — so both locations show it now.

**Sidebar chips**: implemented via two module-level maps populated fresh in `rebuildRegionChips()` (`regionGroupCountEls`/`regionSubCountEls`, mapping group/sub-region key → the `<span class="region-count">` DOM node created alongside that chip's label) and updated by `render()` on every filter change (tallied into local `regionVisibleCounts`/`groupVisibleCounts` objects during the same trail-iteration loop that already computes each trail's `visible` flag) — this avoids rebuilding the whole chip DOM (and re-attaching click handlers) just to refresh a count on every `render()` call, which happens far more often than an actual activate/deactivate.

**Trail-list headings**: trickier because both `.hub-title` (per sub-region) and `.region-group-title` (per group) are created *before* their final visible-trail tally is known — a sub-region's title element is built right as its trail loop starts, and the group title is only created on the *first* sub-region within it that turns out to have any visible trail, i.e. potentially before later sub-regions in the same group are even processed. Fixed by appending the `.region-count` span **after** the relevant loop has fully finished, not at creation time: the hub-title's count span is appended right after that sub-region's own `regionLineTrails.forEach(...)` call ends (`regionVisibleCounts[regionKey]` is final by then), and the group-title's count span is appended after the *whole* `regionKeysInGroup.forEach(...)` call ends, via a `groupTitleEl` reference captured at creation time (initialized to `null` per group, set once when the group-title div is actually created) so there's something to append to even though the div itself was built partway through the sub-region loop.
