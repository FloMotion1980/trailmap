// Trailmap — Service Worker
// Caches the app shell (this page + Leaflet library) so the app itself opens offline,
// and caches map tiles as they are viewed (or explicitly preloaded) so the map background
// keeps working without a connection.

// Style changes no longer need a bump: style.css is served network-first as of v16 (see the fetch handler),
// so a new index.html can never be paired with an old stylesheet again. Bump this only to force every
// cached asset to be re-fetched. v6-v15 were all "style.css changed" bumps, back when it was cache-first --
// the last of which did not reach the user's phone and made the pinned builder sheet invisible there,
// which is why the strategy changed (2026-07-27).
const CACHE_NAME = "trailmap-v16";
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

  // Our own stylesheet: network-first, same reasoning as the navigation request it belongs to. It used to
  // be cache-first, which made every CSS change depend on the CACHE_NAME bump actually reaching the
  // device -- and when it did not, the browser paired a NEW index.html with an OLD style.css. That is not
  // a cosmetic problem: an element whose rules are missing entirely loses its `position:absolute` and
  // therefore paints *behind* #map (which is `position:absolute; inset:0`), i.e. it vanishes. Exactly what
  // happened to the user's phone with the pinned builder sheet and the 🧭 button on 2026-07-27, while
  // everything else looked perfectly normal. One small same-origin file; not worth the risk.
  if (new URL(req.url).pathname.endsWith("/style.css")) {
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
