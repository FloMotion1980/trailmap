// Trailmap — Service Worker
// Caches the app shell (this page + Leaflet library) so the app itself opens offline,
// and caches map tiles as they are viewed (or explicitly preloaded) so the map background
// keeps working without a connection.

// Bump whenever style.css changes: it is in APP_SHELL and served cache-first (only the navigate request
// is network-first), so without a bump a returning user pairs the new index.html with the previously
// cached stylesheet. v6 = bike-lift info panel rules, v7 = Tourenbuilder panel rules (both 2026-07-26),
// v8 = builder glow + numbered start dots (2026-07-27).
const CACHE_NAME = "trailmap-v8";
const APP_SHELL = [
  "./",
  "./index.html",
  "./style.css",
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
