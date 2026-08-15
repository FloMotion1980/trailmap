// Trailmap — Service Worker
// Caches the app shell (this page + Leaflet library) so the app itself opens offline,
// and caches map tiles as they are viewed (or explicitly preloaded) so the map background
// keeps working without a connection.

// Style changes no longer need a bump HERE: the stylesheet carries a ?v= in its own URL (STYLE_URL below,
// and the <link> in index.html must match it), so a new index.html always asks for a URL the old cache
// cannot answer. Bump CACHE_NAME only to force every cached asset to be re-fetched. v6-v15 were all
// "style.css changed" bumps, back when the URL was constant -- and the last of those did not reach the
// user's phone, which left the pinned builder sheet invisible there (2026-07-27).
const CACHE_NAME = "trailmap-v176";
// Must stay identical to the href of the <link rel="stylesheet"> in index.html.
const STYLE_URL = "./style.css?v=176";
// Same deal as STYLE_URL, for the vendored map-rotation plugin: cache-first with a version in the URL, and
// precached below so it is there on a first-ever offline visit. Must match the <script> src in index.html.
const ROTATE_URL = "./leaflet-rotate.js?v=1";
const APP_SHELL = [
  "./",
  "./index.html",
  STYLE_URL,
  ROTATE_URL,
  "./regions/paznaun.json" // default region on a first-ever visit — precached so it works offline
                            // immediately; other regions are cached opportunistically (cache-first
                            // fetch handler below) once the user activates them via the region dialog.
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  // Region version manifest: network-first (it's tiny), so the per-file content versions are always
  // fresh online and the app re-fetches only the region files whose hash changed. Falls back to the
  // cached manifest when offline. This is what drives cache invalidation, independent of SW updates.
  if (new URL(req.url).pathname.endsWith("/regions/version.json")) {
    event.respondWith(
      fetch(req)
        .then((resp) => {
          const clone = resp.clone();
          event.waitUntil(caches.open(CACHE_NAME).then((c) => c.put(req, clone)));
          return resp;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Our own stylesheet stays CACHE-FIRST on purpose (the user, 2026-07-27: "mach das css nicht network
  // first") -- this app is used offline and on one bar of signal, where network-first would stall the page
  // behind a request timeout before falling back to the cache.
  //
  // What keeps it fresh instead is the ?v= query on the <link> in index.html: index.html is network-first,
  // so a new deploy brings a new stylesheet URL, which cannot hit the old cache entry. That fixes the same
  // bug a CACHE_NAME bump was supposed to fix without depending on the bump reaching the device -- and it
  // is not a cosmetic bug: an element whose rules are missing loses its `position:absolute` and paints
  // *behind* #map (`position:absolute; inset:0`), i.e. vanishes. That is what happened to the user's phone
  // with the pinned builder sheet and the mode button, while everything else looked perfectly normal.
  //
  // The fallback covers the one gap the query opens: an index.html cached from an older deploy asks for a
  // ?v= this cache never held, so offline it would get nothing at all. Any stylesheet beats none.
  if (new URL(req.url).pathname.endsWith("/style.css")) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req)
        .then((resp) => {
          const clone = resp.clone();
          event.waitUntil(caches.open(CACHE_NAME).then((c) => c.put(req, clone)));
          return resp;
        })
        .catch(() => caches.open(CACHE_NAME).then((c) => c.keys().then((keys) => {
          const other = keys.find((k) => new URL(k.url).pathname.endsWith("/style.css"));
          return other ? c.match(other) : undefined;
        })))
      )
    );
    return;
  }

  // App shell / navigation: network-first, so updates (new trails etc.) are picked up
  // when online, but it still opens from cache when there's no connection at all.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((resp) => {
          const clone = resp.clone();
          event.waitUntil(caches.open(CACHE_NAME).then((c) => c.put(req, clone)));
          return resp;
        })
        .catch(() => caches.match(req).then((cached) => cached || caches.match("./index.html")))
    );
    return;
  }

  // Everything else (Leaflet JS/CSS, map tiles from OSM/CARTO/OpenTopoMap/Esri):
  // cache-first, and fill the cache in the background for next time.
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req)
        .then((resp) => {
          if (resp && (resp.ok || resp.type === "opaque")) {
            const clone = resp.clone();
            // IMPORTANT: event.waitUntil keeps this fetch event (and the worker) alive
            // until the cache write actually finishes. Without it, the browser can
            // recycle the service worker right after resp is returned, silently
            // killing the cache.put() before it completes — especially likely when
            // many tiles are being fetched concurrently (like during preload).
            event.waitUntil(caches.open(CACHE_NAME).then((c) => c.put(req, clone)));
          }
          return resp;
        })
        .catch(() => cached);
    })
  );
});
