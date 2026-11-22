// Network-first: always try fresh data; fall back to the last copy when offline.
const CACHE = "job-radar-v1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  const key = e.request.url.split("?")[0];
  e.respondWith(
    fetch(e.request)
      .then((r) => { const c = r.clone(); caches.open(CACHE).then((x) => x.put(key, c)); return r; })
      .catch(() => caches.match(key))
  );
});
