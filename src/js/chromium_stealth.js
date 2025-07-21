/*
This script provides deep stealth patches for Chromium-based browsers.
Placeholders in the form of __PLACEHOLDER__ will be replaced by Python.
*/

// RESTORE essential spoofing with advanced stealth techniques
const _mem = __RAND_MEM__;
const _hc_map = {4:4,6:4,8:4,12:8,16:8,24:12,32:16};

// Advanced stealth: Use prototype pollution to avoid direct property modification detection
(() => {
  const spoofedValues = {
    languages: __LANG_JS__,
    deviceMemory: _mem,
    hardwareConcurrency: _hc_map[_mem] || 4
    // NOTE: platform spoofing moved to platform_sync.js for simplicity
  };
  
  // Method 1: Prototype-level spoofing (harder to detect)
  const originalGetters = {};
  
  ['languages', 'deviceMemory', 'hardwareConcurrency'].forEach(prop => {
    const descriptor = Object.getOwnPropertyDescriptor(Navigator.prototype, prop) ||
                      Object.getOwnPropertyDescriptor(navigator, prop);
    
    if (descriptor && descriptor.get) {
      originalGetters[prop] = descriptor.get;
      
      // Replace at prototype level
      Object.defineProperty(Navigator.prototype, prop, {
        get: function() {
          // Return spoofed value but make it look like original getter
          return spoofedValues[prop];
        },
        enumerable: descriptor.enumerable,
        configurable: descriptor.configurable
      });
    }
  });
})();

// NOTE: Worker synchronization moved to UserAgentGate for better reliability

const touchEvents = __TOUCH_JS__;

/* deep-stealth (chromium) – final */
(() => {
  try {
    /* 1 – remove webdriver */
    delete Navigator.prototype.webdriver;
    delete navigator.webdriver;

    /* 2 – REMOVED: userAgentData handled by spoof_useragent.js */
    // userAgentData spoofing moved to dedicated spoof_useragent.js to avoid conflicts

    /* 3 – chrome.runtime stub */
    if (!('chrome' in window)) window.chrome = { runtime: {} };
    else if (!('runtime' in window.chrome)) window.chrome.runtime = {};
    /* 3b – chrome.loadTimes and chrome.csi stubs */
    if (!('loadTimes' in window.chrome)) {
      window.chrome.loadTimes = function() {
        return {
          requestTime: Date.now() / 1000,
          startLoadTime: Date.now() / 1000,
          commitLoadTime: Date.now() / 1000,
          finishDocumentLoadTime: Date.now() / 1000,
          finishLoadTime: Date.now() / 1000,
          firstPaintTime: Date.now() / 1000,
          firstPaintAfterLoadTime: 0,
          navigationType: 'Other',
          wasFetchedViaSpdy: false,
          wasNpnNegotiated: false,
          npnNegotiatedProtocol: '',
          wasAlternateProtocolAvailable: false,
          connectionInfo: 'h2'
        };
      };
    }
    if (!('csi' in window.chrome)) {
      window.chrome.csi = function() {
        return {
          startE: Date.now(),
          onloadT: Date.now() - performance.timing.navigationStart,
          pageT: Date.now() - performance.timing.navigationStart,
          tran: 15
        };
      };
    }

    /* 5 – REMOVED: Canvas fingerprinting handled by canvas_webgl_noise.js */
    // Canvas spoofing moved to dedicated canvas_webgl_noise.js to avoid conflicts

    /* 6 – mediaDevices fallback */
    if (navigator.mediaDevices?.enumerateDevices) {
      const realEnum = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
      navigator.mediaDevices.enumerateDevices = async () => {
        const list = await realEnum();
        if (list.length) return list;
        return [
          { kind: 'audioinput', label: 'Microphone', deviceId: 'default', groupId: 'default' },
          { kind: 'videoinput', label: 'Camera', deviceId: 'default', groupId: 'default' }
        ];
      };
    }
  } catch (err) {
    }
})();

