// Offline support. On install, downloads the app shell plus every lesson
// listed in content/index.json. Afterwards everything is served from the
// cache straight away and refreshed in the background when there's signal
// (stale-while-revalidate), so new lessons appear on the next open.

const CACHE = 'study-v1';
const SHELL = [
  './',
  'index.html',
  'styles.css',
  'app.js',
  'manifest.webmanifest',
  'icons/icon.svg',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/apple-touch-icon.png',
  'content/index.json',
];

async function lessonUrls() {
  const res = await fetch('content/index.json', { cache: 'no-cache' });
  const { topics } = await res.json();
  return topics.flatMap((t) => t.lessons.map((l) => `content/${t.id}/${l.file}`));
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const fresh = (urls) => cache.addAll(urls.map((u) => new Request(u, { cache: 'no-cache' })));
    await fresh(SHELL);
    await fresh(await lessonUrls());
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    // All routes are hash-based, so any page navigation is the app shell.
    const key = req.mode === 'navigate' ? 'index.html' : req;
    const cached = await cache.match(key, { ignoreSearch: true });

    // no-cache: revalidate with the server rather than reuse the HTTP cache.
    const refresh = fetch(req.url, { cache: 'no-cache' }).then(async (res) => {
      if (res.ok) {
        await cache.put(key, res.clone());
        // A changed catalogue may list new lessons: fetch them too.
        if (req.url.endsWith('content/index.json')) {
          const urls = await lessonUrls().catch(() => []);
          await Promise.all(urls.map(async (u) => {
            if (!(await cache.match(u))) await cache.add(u).catch(() => {});
          }));
        }
      }
      return res;
    }).catch(() => null);

    if (cached) {
      event.waitUntil(refresh);
      return cached;
    }
    return (await refresh) || new Response('Offline and not cached yet.', { status: 503 });
  })());
});
