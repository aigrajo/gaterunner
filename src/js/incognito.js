// incognito.js – Incognito‑mode camouflage (2025‑06)
// ==================================================
// Inject with Playwright `context.addInitScript` BEFORE any site JS.
//
// Scope: ONLY quirks that differ between a normal and a private window.
// No bot‑stealth, no extra spoofing. Designed to fool probes used by
// detectIncognito.js, Fingerprint Pro, CreepyJS, etc.
//
// Tested on: Chrome 125, Edge 125, Firefox 128, Safari 17.5, Brave 1.67.
// Works on desktop & mobile variants (Android/WebView, iOS Safari).
// -------------------------------------------------------------
(() => {
  /*──────── helpers ────────*/
  const rand = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
  const asyncNoop = () => {};

  /*──────── 1. navigator.storage.* (Chromium) ────────*/
  try {
    if (navigator.storage && navigator.storage.estimate) {
      const origEstimate = navigator.storage.estimate.bind(navigator.storage);
      navigator.storage.estimate = async () => {
        try {
          const orig = await origEstimate();
          if (orig.quota && orig.quota >= 1610612736) return orig; // ≥1.5 GiB → normal
        } catch (_) {}
        const heap = (performance?.memory?.jsHeapSizeLimit) || 1073741824; // 1 GiB fallback
        const fakeQuota = heap * 2 + 314_572_800; // heap×2 + 300 MiB
        return {
          quota: fakeQuota,
          usage: rand(10_485_760, Math.floor(fakeQuota * 0.4)), // 10 MiB – 40 %
        };
      };
    }
    if (navigator.storage?.persist)   navigator.storage.persist   = async () => false;
    if (navigator.storage?.persisted) navigator.storage.persisted = async () => false;
  } catch (_) {}

  /*──────── 2. FileSystem API timing (Chromium) ────────*/
  try {
    if (!('webkitRequestFileSystem' in window)) {
      window.webkitRequestFileSystem =
      window.RequestFileSystem = function (_type, _size, successCb, _errorCb) {
        setTimeout(() => { if (typeof successCb === 'function') successCb(); },
                   rand(30, 70)); // pretend disk latency
      };
    }
  } catch (_) {}

  /*──────── 3. navigator.languages length (Chromium) ────────*/
  try {
    if (navigator.languages?.length === 1) {
      const base = navigator.languages[0];
      const langs = [base, base.split('-')[0]];
      Object.defineProperty(navigator, 'languages', { get: () => langs });
    }
  } catch (_) {}

  /*──────── 4. IndexedDB presence (Firefox / Safari) ────────*/
  try {
    const needStub = (() => {
      if (!window.indexedDB) return true;
      try {
        const req = window.indexedDB.open('__incognito_test__');
        return req.readyState === 'done' && req.error;
      } catch (_) {
        return true;
      }
    })();

    if (needStub) {
      const fakeIndexedDB = {
        open: () => ({ onsuccess: asyncNoop, onerror: asyncNoop }),
        deleteDatabase: () => ({ onsuccess: asyncNoop, onerror: asyncNoop }),
      };
      Object.defineProperty(window, 'indexedDB', { get: () => fakeIndexedDB });
    }
  } catch (_) {}

  /*──────── 5. WebKit localStorage / openDatabase fallbacks ────────*/
  try {
    if (!('openDatabase' in window)) {
      window.openDatabase = () => {
        throw new DOMException('openDatabase disabled', 'InvalidStateError');
      };
    }

    const testKey = '__incognito_ls_test';
    try {
      localStorage.setItem(testKey, '1');
      localStorage.removeItem(testKey);
    } catch (_) {
      const mem = new Map();
      Object.defineProperty(window, 'localStorage', {
        get: () => ({
          getItem: k => mem.get(k) ?? null,
          setItem: (k, v) => { mem.set(k, String(v)); },
          removeItem: k => { mem.delete(k); },
          clear: () => { mem.clear(); },
          key: i => Array.from(mem.keys())[i] ?? null,
          get length() { return mem.size; },
        }),
      });
    }
  } catch (_) {}

  /*──────── 6. CacheStorage timing (Camoufox‑style) ────────*/
  try {
    if ('caches' in window && caches.open) {
      const origCacheOpen = caches.open.bind(caches);
      caches.open = async function (cacheName) {
        await new Promise(r => setTimeout(r, rand(15, 45))); // add disk‑like delay
        return origCacheOpen(cacheName);
      };
    }
  } catch (_) {}
})();
