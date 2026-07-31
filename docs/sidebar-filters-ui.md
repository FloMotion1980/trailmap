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
- **📍 stacked directly under the ✕**, both inside one `.region-group-corner` group that carries a single
  opaque background. Four positions were tried on 2026-07-31; the three that lost are worth knowing before
  moving it a fifth time:
  - the **bottom** border, mirroring the ✕, *collides by construction* — a 28px button centred on a border
    overhangs it by 14px, straight into the next box's legend, whose own height depends on whether a long
    region name wraps, so the overlap appears and disappears as regions are added;
  - a **footer row in flow** is collision-proof but costs a whole line (~28px) per region for one icon;
  - **side by side on the border line** put the grey border in the 6px gap between the two buttons, which
    reads as a seam.
  Stacked in one group solves all three at once: no extra line (the 📍 hangs into the box's own top padding),
  no collision, and — because the *group* carries the `--card-bg`, not the individual buttons — one clean gap
  in the border with the two buttons touching, so there is nothing left to show through. `translateY(-14px)`
  rather than `-50%`, so the **✕** is the thing centred on the border and its glyph stays on the same vertical
  line as the section carets; centring the 54px group would push it up by 13px.
  Two knock-on rules: `.region-group-chips` gets `padding-right: 34px` (a wrapping flex row cannot dodge the
  button per line), and `.region-group-row` a `max-width: calc(100% - 74px)` — the legend is absolutely
  positioned and a long region name would otherwise run under the group. It wraps rather than truncating; a
  shortened region name is worse than a taller legend.
- **`#addRegionBtn` below the boxes**, dashed outline, full width. **Disabled rather than hidden** at
  `MAX_ACTIVE_REGION_GROUPS` — a button that vanishes at three teaches nothing, a greyed one whose label reads
  "＋ Maximal 3 Regionen" does. It opens the same dialog the header button opens; one dialog, two entry points.
- **The header button and the full dialog both stay.** The header doubles as the "what is loaded" readout and
  is reachable without opening the drawer; the dialog still lists every region with active ones marked, so
  deactivating works in either place.

One behaviour worth knowing rather than fixing: **closing a region and re-adding it moves its box to the
bottom**, because `REGION_GROUPS` is keyed in activation order. The `regions` suite compares the active set,
not the order, for exactly this reason.

## One content column, one kind of separator (2026-08-01)

A measured pass over every inset and every line in the sidebar, after the user asked for one ("Solche Design
Aspekte sind mir wichtig"). Five things were off, all of them for the same structural reason: the three list
sections sit *outside* `.filters` and so never inherited its 16px padding, while everything inside it did.

| | before | after |
|---|---|---|
| Trail/Tour/lift cards | left edge at **12px** | 16px, flush with the region boxes' frame |
| Section lines inside `.filters` | 317px (16…333) | 317px |
| Section lines outside it (Trails/Touren/Lifte) | **349px, full bleed** | 317px |
| `.filters`' own bottom border | **349px, full bleed** | gone; `#secMapOptions` draws that separator now |
| Line under every hub group | present | gone |
| Region → Filter boundary | **31px** | 17px, like every other boundary |

The fix is `margin: 0 16px` on `#secTrails`/`#secTouren`/`#secLifts` — which makes their own `border-bottom`
the same line as the filter sections' — plus removing the 16px that their children were each adding a second
time (`summary`, `.hub-title`, `.region-group-title`, and the cards' `margin`).

**Why the hub line went.** A new sub-region already announces itself with its own coloured uppercase title, and
before a new *region* group there is that group's 2px top border 12px further down as well — so the line was the
third separator for one boundary. What is left inside a list is exactly one line, the 2px region-group rule; a
different weight from the 1px section rules on purpose, because it is a different level of the hierarchy.

**The one gap that is deliberately not uniform** is `.region-groups-container`'s `margin-top: 18px`: the first
region box's legend is lifted onto its own top border and needs the room, or it covers the "Region" heading —
a regression that has been fixed twice already.

The `lists` suite now checks both properties directly: every content edge against the region boxes' own left
edge, and every separator's width against the boxes' width. It discriminates a line from a box by asking
whether the element has a left or right border — the first version reported the region-group pills as 143px and
186px "separators".

## One vertical line for the caret, the ✕ and the 📍 (2026-08-01)

All three are **centred on the line that frames the regions** — the region box's right border, which is also
the sidebar's own content edge. They were aligned with each other before but 10px shy of that line, because the
corner group sat just *inside* the box (`right: -6px`) and the caret ended *at* the summary's edge.

- `.region-group-corner` uses `right: -15px`, i.e. half its own 30px width, so the border runs through the
  middle of both glyphs.
- `summary::after` gets `margin-right: -10px`, half the caret's ~20px glyph box, for the same reason.

The 10px this frees *inside* every box is the reason the two rules below could be relaxed: `.region-group-row`
went from `max-width: calc(100% - 74px)` to `- 34px`, which is what stops **"Bikeland Schladming-Dachstein
(29)" from wrapping to two lines**, and the floated chip spacer went from 26px to 18px. Measured after: caret,
✕ and 📍 all centred on x=333 on desktop and x=313 in the phone drawer, where the group's outer edge still has
3px of clearance to the drawer edge.

`.region-add-btn` took the region boxes' own `border-radius: 10px` instead of a pill, so the column of boxes
and the button under them read as one shape.

One knock-on the reservation made visible: with the slack now *inside* the parens, a count shorter than its
reserved width printed as `( 0 )`. `.region-count` is `text-align: right`, so a short number sits where a table
column would put it rather than leaving a gap before the closing paren.

## Two chip-layout fixes worth not undoing (2026-08-01)

**The 📍's clearance is a floated spacer, not padding on the chip row.** `padding-right: 34px` reserved that
width on *every* wrapped line, not just the one the button occupies — which cost Bike Kingdom's nine
sub-regions their two-per-row layout entirely: nine chips, nine lines. A `float: right` spacer as the row's
first child is reserved only on the lines it actually overlaps. The knock-on is that the row **cannot be
`display: flex`** (flex items ignore floats), so `.region-group-chips` is a block row with `inline-block`
chips, and what was a flex `gap: 6px` is now a margin on the chips themselves. Nine chips went from 9 rows to
5, about 100px back per region.

**Only the DIGITS of a count are width-reserved.** The reservation exists so toggling a sub-region cannot
change a chip's footprint and reflow its wrapped siblings (a real bug from 2026-07-23, "chips jumping"). But
reserving `digits + 3` characters for `" (n)"` reserved three *digit* widths for a space and two parentheses,
all far narrower in Arial — and since the box is left-aligned, the slack piled up at its end, i.e. as visible
dead space on the chip's right edge. The user spotted it as "links weniger Platz als rechts". The parens are
static text nodes beside the span now, the span reserves digits only, and the chip measures 12px of padding on
both sides. ~9px saved per chip, which is often the difference between two chips fitting on a line and not.

## The region dialog: slots, search, country groups (2026-08-01)

Sixteen regions in one flat, catalog-ordered list had stopped scaling, and the backlog is longer still. Three
changes, all inside the existing dialog:

**The three places, as places.** `#regionSlots` shows one slot per allowed region — filled ones carry the
region's name and their own ✕, empty ones read "frei" — with a hint below counting them
(`2 von 3 Plätzen belegt — noch 1 frei`). This replaces a red `Limit erreicht` note that only appeared *after*
you had run into the wall. The limit is now legible before you try, and the dialog is also where you make room.
The slot row publishes the limit as `data-max`, which is how the test suite reads
`MAX_ACTIVE_REGION_GROUPS` (a `const` inside the app's `try{}` block, unreachable from a suite).

**Grouped by country, and the ambiguity is the interesting part.** `countries: ["AT", "CH"]` is an **explicit**
catalog field, never derived from `bounds`. Three of sixteen regions cross a border *in our own sub-region
data*: Silvretta Bike Arena has "Ischgl/Samnaun" (CH) plus a trail ending in Ramosch (CH), 3-Länder has
Schöneben and Haideralm on the Italian side of the Reschenpass, and Portes du Soleil has
Champéry · Les Crosets · Morgins in Switzerland. A bounding-box centre would have silently picked one — absurd
for a region called "3-Länder". The **first** country is the primary and decides the group, so every region
appears exactly once; the others show as extra flags on the row, making the crossing visible rather than tidy.
Countries sort by their German name and regions alphabetically inside each, both stable as the catalog grows,
unlike catalog order or "most regions first". Headings are `position: sticky` — a heading that scrolls away
turns grouping back into a flat list.

**Search covers what grouping cannot.** `#regionSearch` matches the region label, **every sub-region label**,
the country code and the country's German name, all diacritics- and punctuation-insensitive (`galtur` finds
Galtür). Sub-regions are the important part: a rider knows "Samnaun" or "Morzine", not necessarily which of our
region names covers it — and they are printed as a third line on each row, so the search is discoverable
rather than hidden. It is also what keeps grouping-by-primary honest: typing "Schweiz" finds Silvretta Bike
Arena even though it is filed under Austria. Place labels are deliberately *not* searchable — they live in the
region file, which is not loaded until the region is activated. Escape clears the term before it closes the
dialog, so a key aimed at the text field cannot cost you the whole dialog.

Deliberately **not** built, and why: a per-region map preview (16 regions' worth of tiles for a decision you
have not made yet), and a download size per row (it would need re-measuring on every region build, and a stale
size is worse than none). A map *strip* inside the dialog was designed and dropped in favour of these three;
the idea, its tile cost (4–6 tiles at zoom 5) and the option of precaching those into `APP_SHELL` are recorded
here in case it comes back.

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
