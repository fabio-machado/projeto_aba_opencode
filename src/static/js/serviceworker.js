// Service Worker — Autismo em Foco PWA
// Strategy: Cache-First for static assets, Network-Only for dynamic data
var CACHE_NAME = 'aef-static-v1';

var PRECACHE_ASSETS = [
  '/static/css/theme.css',
  '/static/js/app-shell.js',
  '/static/js/bottom-sheet.js',
  '/static/js/pwa-session-manager.js',
  '/static/js/pwa-install-banner.js',
  '/static/images/pwa/icon-192x192.png',
  '/static/images/pwa/icon-512x512.png'
];

var STATIC_EXTENSIONS = ['css', 'js', 'png', 'svg', 'jpg', 'jpeg', 'gif', 'webp', 'woff2', 'woff', 'ico'];

function isStaticAsset(url) {
  var extension = url.split('.').pop().split('?')[0];
  return STATIC_EXTENSIONS.indexOf(extension) !== -1;
}

// T026: Pre-cache critical assets on install
self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(PRECACHE_ASSETS);
    })
  );
});

// T028+T029: Delete old caches and claim clients on activate
self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (cacheNames) {
      return Promise.all(
        cacheNames.map(function (cacheName) {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

// T027: Cache-First for static assets; pass-through for dynamic (HTMX, API)
self.addEventListener('fetch', function (event) {
  var url = new URL(event.request.url);

  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  // Only handle same-origin requests
  if (url.origin !== self.location.origin) return;

  // Only cache static assets — pass everything else through to network
  if (!isStaticAsset(url.pathname)) return;

  event.respondWith(
    caches.match(event.request).then(function (cachedResponse) {
      if (cachedResponse) return cachedResponse;

      return fetch(event.request).then(function (networkResponse) {
        var responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then(function (cache) {
          cache.put(event.request, responseToCache);
        });
        return networkResponse;
      });
    })
  );
});
