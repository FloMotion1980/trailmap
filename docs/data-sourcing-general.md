# Data sourcing: general methodology (GPX, Trailforks, headless browser)

Split out of `CLAUDE.md` 2026-07-23 to keep that file lean — this covers sourcing *methods* that apply across regions, not any one region's specific status. Region-specific sourcing notes (what's confirmed, what's still ambiguous) live in their own `docs/<region>.md` file instead (e.g. `docs/finale-ligure.md`).

## GPX → geometry/elevation pipeline

GPX → geometry/elevation is a well-defined pipeline (regex point extraction — real XML parsers choke on malformed source GPX like unescaped `&` in `<name>`, or CDATA-wrapped `<ele>` values, or `lon` before `lat` in the attribute order, all of which show up across the GPX sets in `Material/` — → Douglas-Peucker line simplification with a small fixed epsilon (~2m; don't simplify harder just to hit a point-count target, that visibly distorts short trails) → elevation resampled to ~100 points by distance with implausible outliers (e.g. GPS glitches reading ~0m) linearly interpolated). This has been scripted more than once (ad hoc, not currently committed to the repo) but not turned into a repo-tracked tool yet — if you rebuild it, that's still the recommended shape.

**Another GPX-format gotcha found 2026-07-23**: a GPX exported from **mtb.waymarkedtrails.org** used self-closing `<trkpt lat=".." lon=".."/>` tags (no separate `</trkpt>` closing tag, no body) — a regex point-extractor written only against the `<trkpt ...>...</trkpt>` form (Outdooractive's own export style) silently returns zero points on this kind of file rather than erroring, which is easy to miss. Match both forms. Also: a route/relation exported *from* waymarkedtrails.org (rather than reconstructed by hand from raw Overpass way/relation data) comes back as a single already-correctly-ordered track — this is the most reliable way to turn an OSM route relation into usable geometry, more so than manually chaining member ways yourself (see `docs/finale-ligure.md`'s "Trincea/Bormida correction" for a case where manual chaining twice produced a wrong-looking result before a waymarkedtrails.org-sourced GPX resolved it cleanly).

Metadata (name/difficulty/length/up/down) is a separate, non-automatable step — it doesn't come from the GPX, it comes from whatever official source exists for that region (tourism site scraping for Paznaun; the `BiketrailsNauders.pdf` brochure's S0–S3 scale for 3-Länder's 21 numbered trails). Where no official length/Hm exists (newer trails not in a brochure), GPX-computed length/elevation-gain-loss is an acceptable fallback — but prefer official published numbers over GPX-derived ones when both exist, to stay consistent with the rest of `lineTrails`.

## Try the resort/park operator's OWN site for GPX first (before OSM)

**Added 2026-07-26, prompted by the user: "Warum probierst du nicht online GPX zu kriegen von den Parks. Bisher gabs die immer."** They were right, and this should now be step 1 for any new bike park / resort region, ahead of OSM+Overpass:

A resort's own bike site is very often built on a tour-CMS (Outdooractive/komoot-backed) that publishes a **direct, unauthenticated GPX asset per trail**. For Serfaus-Fiss-Ladis this was `bike-sfl.at`, with each trail's detail page (`/de/singletrails/<name>-<num>_tour_<id>`) embedding a link to `/var/assets/Touren/<name>-<num>-<assetid>.gpx`. A two-step scrape (listing page → detail pages → regex `(/var/assets/Touren/[^"']+?\.gpx)`) got all of them in one pass. Look for the same shape on any operator site: a per-trail detail page whose HTML contains a `.gpx` (and usually `.kml`) asset URL.

**Why this beats OSM as a first choice:**
- **Real embedded elevation.** This is the big one — it removes the elevation-API step entirely. Open-Meteo's elevation endpoint **rate-limits hard** on a batch build (~10+ trails back-to-back) and starts returning `null`/`0`, which silently produces garbage profiles (Serfaus' first, OSM-based build had trails reading `ele 0 -> 1648`, `up2254/dn270` on what is actually a pure descent). If you ever *do* have to batch-fetch elevation, save incrementally per trail so a mid-loop rate-limit doesn't discard everything.
- **The operator's list is authoritative for which trails still exist.** Serfaus' status page (`/de/info-service/trailstatus-oeffnungszeiten`) enumerated exactly 17 trails; OSM additionally carried Wildbachtrail, Flüstertrail and Almtrail, which the operator no longer lists — i.e. defunct. OSM keeps old trails around long after they're gone, and it also *missed* one that does exist (Scheidtrail). Cross-check both directions.
- Difficulty comes from the same pages, in the operator's own words.

**But don't assume the GPX is automatically the better geometry — verify against the operator's published length/drop.** Park GPX files are often recorded as a *ride*, so they can include the lift/access return leg: Serfaus' "Morning Glory" GPX came back as a loop (1.22 km, up102/dn97) against a published 0.68 km descent, and "Downhill" carried up137. In those cases OSM's clean descent line is the better one. Conversely OSM was badly truncated for "Supernatural 2.0" (0.21 km vs 1.85 km published). The workable rule is **per-trail source selection scored against the operator's own published numbers**, not a blanket "GPX always wins" — and keep the published length as `len` either way, per the existing official-numbers-beat-GPX-derived convention.

## Outdooractive white-label sites: the GPX endpoint works even when the site itself blocks you (2026-07-29)

A lot of resort map portals are white-labelled Outdooractive — the giveaway is a URL of the form
`https://maps.<resort>.<tld>/de/tour/<category>/<slug>/<numericID>/`. **That numeric ID is an Outdooractive
route ID**, so the download endpoint already documented for Finale works directly:

```
https://www.outdooractive.com/en/download.tour.gpx?i=<routeID>&project=outdooractive
```

**Verified for Bike Kingdom / Lenzerheide** (task #17, previously recorded as blocked): id `45019044` from
`maps.arosalenzerheide.swiss/de/tour/mountainbike-trail/urdental-trail/45019044/` returns a valid GPX for
"Urdental Trail" — 242 points, **242 `<ele>` values**, i.e. real elevation, so no DEM backfill needed. It
works with a plain `urllib` request plus a browser `User-Agent`.

Worth knowing because the portal itself does NOT cooperate: `maps.arosalenzerheide.swiss` answers **404** to
the same plain request, for the tour page and for every category-listing URL tried. So the pattern is: get the
ID from a URL the user hands you (or from a search result), then fetch the GPX from outdooractive.com — do not
try to crawl the portal.

**What is still missing for Bike Kingdom**: the ID list. `bikekingdom.ch/en/Tours-and-Trails/Trail-map`
renders its trails client-side — its 284 KB of HTML contains no tour IDs, no links to the maps subdomain, and
only three trail names in prose. So the list needs either the headless Chromium below, or a handful of
per-trail URLs from the user (each one yields its GPX immediately). Difficulties still need the operator's own
grading, as always.

## Checking for a redirect before assuming a name has no match

A site's own detail-page slug can be phrased differently than the name a user gives you and still be the same trail — e.g. an Italian-phrased alternate name 301-redirecting to a canonical English slug on finaleoutdoor.com. Before concluding a user-supplied name has no existing entry, try `curl -I -A "<real UA>" <guessed-slug-url>` and check the `location` header for a redirect target — cheap, and prevents accidentally re-fetching/duplicating a trail that's already built under a different-looking name.

## Trailforks (bot-blocked)

**Trailforks** is a second data source with useful cross-check info (popularity, community rating, IMBA-style green/blue/black/double-black difficulty — apply the same shift as Outdooractive's S-scale: green→`blau`, blue→`rot`, black/double-black→`schwarz`) but is comprehensively bot-blocked: every endpoint tested returns 403 to a plain HTTP client (curl/WebFetch) — trail pages, region pages, embeddable widgets, even the direct `/gpx`/`/kml` download endpoints — except the two standard SEO files (`robots.txt`, `sitemap.xml`, which don't help since the sitemap is global/unfiltered by region). GPX/KML download additionally requires a logged-in account regardless of bot-blocking. A **real headless Chromium does get past the page-level bot-block** (see below for how one got working in this sandboxed environment without root) — but an automated *login* attempt through it gets flagged as suspicious by Trailforks' reCAPTCHA and forces an email-verification step, so don't try to automate the login itself; anonymous page loads (rich metadata, no GPX) work fine unauthenticated though. Net effect: use headless Chromium for anonymous Trailforks metadata scraping if needed, but GPX/KML export still needs the user to log in manually in their own real browser and hand over the file (same as the Outdooractive/manual-download workflow) — don't keep pushing on automating the authenticated path once a provider's anti-bot system explicitly challenges it.

## Getting a real headless browser running in this sandbox (no root)

Playwright's `chromium` package downloads fine via `npx playwright install chromium`, but the binary fails to launch with `error while loading shared libraries: libnspr4.so...` (and libnss3/libnssutil3/libsmime3/libasound2t64) because `playwright install-deps` needs sudo, which isn't available. Fix without root: `apt-get download libnspr4 libnss3 libasound2t64` (plain download, no install, doesn't need sudo — package names are for Ubuntu 24.04/noble, check `apt-cache policy` if on a different base image), `dpkg -x <pkg>.deb <dir>` each one into a scratch directory (extracts without installing), then launch Chrome with `LD_LIBRARY_PATH=<that dir>/usr/lib/x86_64-linux-gnu` set. The binary actually lives at `chrome-linux64/chrome` (not `chrome-linux/chrome` — that's the headless-shell variant's path convention, don't confuse the two). `chrome-headless-shell` specifically was missing libraries even after this fix in testing; the regular `chrome` binary worked fine headless via `--headless --no-sandbox --disable-gpu`.

A working chromium + extracted libs setup has already been produced at least once in this project's sandbox environment (scratchpad-local, not repo-tracked) — check for a `chrome_libs`/`chrome_libs_deb` dir and a Playwright chromium cache under `~/.cache/ms-playwright/` before re-doing this extraction from scratch.
