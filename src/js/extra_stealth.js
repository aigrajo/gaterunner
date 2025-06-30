/* extra-stealth (chromium & fwk) */
(() => {
  /* Permissions & Notification */
  if (navigator.permissions?.query) {
    const real = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = p =>
      p && p.name === 'notifications'
        ? Promise.resolve({ state: 'prompt', onchange: null })
        : real(p);
  }
  Object.defineProperty(Notification, 'permission', { get: () => 'default' });
  Notification.requestPermission = async () => 'granted';

  /* Advanced Speech-synthesis spoofing */
  if ('speechSynthesis' in window) {
    const voices = [{
      voiceURI: 'Google US English',
      name:     'Google US English',
      lang:     'en-US',
      localService: true,
      default:  true
    }];
    
    const nativeGetVoices = window.speechSynthesis.getVoices;
    
    // Advanced function cloning
    const spoofedGetVoices = function getVoices() {
      return voices;
    };
    
    Object.setPrototypeOf(spoofedGetVoices, nativeGetVoices);
    Object.defineProperty(spoofedGetVoices, 'toString', {
      value: () => nativeGetVoices.toString(),
      configurable: true
    });
    Object.defineProperty(spoofedGetVoices, 'name', {
      value: 'getVoices',
      configurable: true
    });
    
    window.speechSynthesis.getVoices = spoofedGetVoices;
  }

  /* Advanced AudioContext fingerprinting protection */
  const ctxProto = (window.AudioContext || window.webkitAudioContext)?.prototype;
  if (ctxProto && !ctxProto.__patched) {
    const nativeCreateAnalyser = ctxProto.createAnalyser;
    
    // Advanced function replacement with proper cloning
    const spoofedCreateAnalyser = function createAnalyser() {
      const analyser = nativeCreateAnalyser.apply(this, arguments);
      const nativeFFT = analyser.getFloatFrequencyData;
      
      // Clone the FFT function with minimal detection footprint
      const spoofedFFT = function getFloatFrequencyData(array) {
        nativeFFT.call(this, array);
        // Minimal audio noise injection
        if (array && array.length > 0) {
          for (let i = 0; i < array.length; i += 128) {
            array[i] += (Math.random() - 0.5) * 1e-5; // Even smaller noise
          }
        }
      };
      
      // Advanced function cloning
      Object.setPrototypeOf(spoofedFFT, nativeFFT);
      Object.defineProperty(spoofedFFT, 'toString', {
        value: () => nativeFFT.toString(),
        configurable: true
      });
      Object.defineProperty(spoofedFFT, 'name', {
        value: 'getFloatFrequencyData',
        configurable: true
      });
      
      analyser.getFloatFrequencyData = spoofedFFT;
      return analyser;
    };
    
    // Clone createAnalyser function
    Object.setPrototypeOf(spoofedCreateAnalyser, nativeCreateAnalyser);
    Object.defineProperty(spoofedCreateAnalyser, 'toString', {
      value: () => nativeCreateAnalyser.toString(),
      configurable: true
    });
    Object.defineProperty(spoofedCreateAnalyser, 'name', {
      value: 'createAnalyser',
      configurable: true
    });
    
    ctxProto.createAnalyser = spoofedCreateAnalyser;
    ctxProto.__patched = true;
  }

  /* mediaDevices.getUserMedia stub */
  if (navigator.mediaDevices && !navigator.mediaDevices.__patched) {
    navigator.mediaDevices.getUserMedia = async () => new MediaStream();
    navigator.mediaDevices.__patched = true;
  }

/* ---------- plugin & mimeType tidy-up (five default viewers) ---------- */
/* ---------- final plugin & mimeType patch (native object, 5 plugins) -- */
(() => {
  const navProto   = Navigator.prototype;
  const nativePlug = navigator.plugins;
  const nativeMime = navigator.mimeTypes;

  /* bail if already patched or not present */
  if (!nativePlug || nativePlug.__patched) return;

  /* wipe existing entries ---------------------------------------------------- */
  const clearALike = obj => {
    const n = obj.length >>> 0;
    for (let i = 0; i < n; i++) delete obj[i];
  };
  clearALike(nativePlug);
  clearALike(nativeMime);

  /* helpers ------------------------------------------------------------------ */
  function makeMime(type, plugin) {
    return Object.freeze({
      type, suffixes: 'pdf',
      description: 'Portable Document Format',
      enabledPlugin: plugin
    });
  }
  function makePlugin(name) {
    /* create a blank object whose [[Prototype]] is the native PDF plugin’s proto
       so all internal slots stay valid and instanceof checks pass            */
    const plugin = Object.create(Object.getPrototypeOf(nativePlug[0] || {}));

    Object.assign(plugin, {
      name,
      filename:    'internal-pdf-viewer',
      description: 'Portable Document Format'
    });

    /* two MIME types -------------------------------------------------------- */
    const m0 = makeMime('application/pdf', plugin);
    const m1 = makeMime('text/pdf',        plugin);
    plugin[0] = m0;
    plugin[1] = m1;

    /* expose length as **2** with an accessor to override the old 8 ---------- */
    Object.defineProperty(plugin, 'length', { get: () => 2 });
    plugin.item      = i => (i === 0 ? m0 : i === 1 ? m1 : null);
    plugin.namedItem = t => /pdf/i.test(t) ? m0 : null;

    return { plugin, mimes: [m0, m1] };
  }

  const names = [
    'PDF Viewer',
    'Chrome PDF Viewer',
    'Chromium PDF Viewer',
    'Microsoft Edge PDF Viewer',
    'WebKit built-in PDF'
  ];

  const built   = names.map(makePlugin);
  const plugins = built.map(b => b.plugin);
  const mimes   = built.flatMap(b => b.mimes);

  /* repopulate native PluginArray ------------------------------------------- */
  plugins.forEach((p, i) => { nativePlug[i] = p; });
  Object.defineProperty(nativePlug, 'length', { get: () => plugins.length });
  nativePlug.item      = i => nativePlug[i] || null;
  nativePlug.namedItem = n => plugins.find(p => p.name === n) || null;
  nativePlug.refresh   = () => {};
  /* ensure toString & prototype checks pass */
  nativePlug.toString = () => '[object PluginArray]';

  /* repopulate native MimeTypeArray ----------------------------------------- */
  mimes.forEach((m, i) => { nativeMime[i] = m; });
  Object.defineProperty(nativeMime, 'length', { get: () => mimes.length });
  nativeMime.item      = i => nativeMime[i] || null;
  nativeMime.namedItem = t => mimes.find(m => m.type === t) || null;

  /* flag so we don’t patch twice */
  Object.defineProperty(nativePlug, '__patched', { value: true });
})();


  /* privacy flags */
  Object.defineProperty(navigator, 'doNotTrack', { get: () => 'unspecified' });

  /* remove Battery Status API so Chrome 116+ behaviour matches */
  (() => {
    const wipe = (obj) => {
      if (!obj || !('getBattery' in obj)) return;
      const ok = delete obj.getBattery;
      if (!ok) {            // if property is non-configurable, shadow it
        try {
          Object.defineProperty(obj, 'getBattery', {
            value: undefined,
            writable: false,
            enumerable: false,
            configurable: false
          });
        } catch (_) {}
      }
    };
    wipe(Navigator.prototype);
    wipe(navigator);
  })();
  if ('getBattery' in navigator) {
    Object.defineProperty(Navigator.prototype, 'getBattery',
      { value: undefined, configurable: false });
    Object.defineProperty(navigator, 'getBattery',
      { value: undefined, configurable: false });
  }
})();

(() => {
  const fp = window.__fp;
  if (!fp) return;

  /* 1. navigator.userAgentData */
  Object.defineProperty(navigator, 'userAgentData', {
    get() {
      return {
        brands: [
          { brand: fp.brand || 'Chromium', version: fp.brand_v || fp.chromium_v },
          { brand: 'Chromium',             version: fp.chromium_v },
          { brand: 'Not)A;Brand',          version: '99' }
        ],
        mobile: fp.mobile || false,
        getHighEntropyValues: keys =>
          Promise.resolve(keys.reduce((o, k) => {
            const map = {
              architecture:     fp.arch,
              bitness:          fp.bitness,
              model:            fp.model,
              platform:         fp.platform,
              platformVersion:  fp.platform_version,
              uaFullVersion:    fp.ua_full_version
            };
            if (k in map) o[k] = map[k];
            return o;
          }, {}))
      };
    },
    configurable: true
  });

  /* 2. WebGPU adapter spoof */
  if ('gpu' in navigator && navigator.gpu?.requestAdapter) {
    const fakeAdapter = {
      name:        fp.webgl_renderer,
      vendor:      fp.webgl_vendor,
      architecture: fp.arch,
      driver:      '0',
      isSoftware:  false,
      limits:      {},
      features:    new Set()
    };
    navigator.gpu.requestAdapter = () => Promise.resolve(fakeAdapter);
  }

  /* 3. Remove storageBuckets / credentials */
  delete Navigator.prototype.storageBuckets;
  delete Navigator.prototype.credentials;

  /* 4. Remove HID / USB / Serial if not ChromeOS */
  if (!fp.os_chrome_os) {
    delete Navigator.prototype.hid;
    delete Navigator.prototype.usb;
    delete Navigator.prototype.serial;
  }

  /* 5. Slow-reject timing for MIDI & getUserMedia */
  const slowReject = () =>
    new Promise((_, rej) =>
      setTimeout(() => rej(new DOMException('', 'NotSupportedError')),
                 300 + Math.random() * 300));

  navigator.requestMIDIAccess = slowReject;
  if (navigator.mediaDevices?.getUserMedia) {
    navigator.mediaDevices.getUserMedia = slowReject;
  }

  /* 6. Clean minor surfaces */
  [
    'devicePosture', 'ink', 'wakeLock',
    'adAuctionComponents', 'runAdAuction',
    'joinAdInterestGroup', 'updateAdInterestGroups',
    'leaveAdInterestGroup', 'clearAppBadge',
    'canLoadAdAuctionFencedFrame', 'createAuctionNonce'
  ].forEach(key => delete Navigator.prototype[key]);
})();


