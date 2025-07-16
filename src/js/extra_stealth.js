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

  /* REMOVED: Early getUserMedia override conflicts with later slow rejection */
  // getUserMedia handling consolidated into single slow rejection implementation below

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


/* REMOVED: UserAgentData handled by spoof_useragent.js */
// UserAgentData spoofing moved to dedicated spoof_useragent.js to avoid conflicts

(() => {
  const fp = window.__fp;
  if (!fp) return;

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




