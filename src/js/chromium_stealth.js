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
    hardwareConcurrency: _hc_map[_mem] || 4,
    platform: '__PLATFORM__'
  };
  
  // Method 1: Prototype-level spoofing (harder to detect)
  const originalGetters = {};
  
  ['languages', 'deviceMemory', 'hardwareConcurrency', 'platform'].forEach(prop => {
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

// COMPREHENSIVE WORKER USERAGENT SYNCHRONIZATION
(() => {
  const EXPECTED_UA = '__USER_AGENT__';
  const EXPECTED_LANGS = __LANG_JS__;
  const EXPECTED_MEM = _mem;
  const EXPECTED_CORES = _hc_map[_mem] || 4;
  const EXPECTED_BRANDS = [{brand: '__BRAND__', version: '__BRAND_V__'}];
  const EXPECTED_MOBILE = __MOBILE__;
  const EXPECTED_PLATFORM = '__PLATFORM__';
  const EXPECTED_HIGH_ENTROPY = {
    architecture: '__ARCH__',
    bitness: '__BITNESS__',
    brands: EXPECTED_BRANDS,
    mobile: EXPECTED_MOBILE,
    model: '__MODEL__',
    platform: '__PLATFORM__',
    platformVersion: '__PLATFORM_VERSION__',
    uaFullVersion: '__UA_FULL_VERSION__',
    wow64: __WOW64__
  };
  
  // 1. Override userAgent at Navigator prototype level (affects all contexts)
  try {
    const originalDesc = Object.getOwnPropertyDescriptor(Navigator.prototype, 'userAgent');
    if (originalDesc && originalDesc.configurable) {
      Object.defineProperty(Navigator.prototype, 'userAgent', {
        get: function() { return EXPECTED_UA; },
        set: originalDesc.set,
        enumerable: originalDesc.enumerable,
        configurable: originalDesc.configurable
      });
    }
  } catch (_) {}
  
  // 1b. CRITICAL: Override platform at Navigator prototype level (main thread fix)
  try {
    const originalPlatformDesc = Object.getOwnPropertyDescriptor(Navigator.prototype, 'platform');
    if (originalPlatformDesc && originalPlatformDesc.configurable) {
      Object.defineProperty(Navigator.prototype, 'platform', {
        get: function() { return EXPECTED_PLATFORM; },
        set: originalPlatformDesc.set,
        enumerable: originalPlatformDesc.enumerable,
        configurable: originalPlatformDesc.configurable
      });
    }
  } catch (_) {}
  
  // CREEPJS FIX: Propagate spoofed UA to Web Workers
  // Report: "Navigator.userAgent: does not match worker scope" 
  // Solution: Intercept Worker creation and inject UA override
  if (typeof Worker !== 'undefined') {
    const OriginalWorker = Worker;
    
    Worker = function(scriptURL, options) {
      // Create a blob URL that sets the UA then loads the original script
      const workerScript = `
        // Set navigator properties in worker scope to match main thread
        Object.defineProperty(navigator, 'userAgent', { 
          get: function() { return '${EXPECTED_UA}'; },
          configurable: true,
          enumerable: true
        });
        Object.defineProperty(navigator, 'platform', { 
          get: function() { return '${EXPECTED_PLATFORM}'; },
          configurable: true,
          enumerable: true
        });
        
        // Import the original script
        importScripts('${scriptURL}');
      `;
      
      const blob = new Blob([workerScript], { type: 'application/javascript' });
      const blobURL = URL.createObjectURL(blob);
      
      // Create worker with our modified script
      const worker = new OriginalWorker(blobURL, options);
      
      // Clean up blob URL after worker starts
      setTimeout(() => URL.revokeObjectURL(blobURL), 100);
      
      return worker;
    };
    
    // Preserve original Worker properties
    Object.setPrototypeOf(Worker, OriginalWorker);
    Worker.prototype = OriginalWorker.prototype;
  }
  
  // 2. Override userAgent at navigator instance level (main thread)
  try {
    const instanceDesc = Object.getOwnPropertyDescriptor(navigator, 'userAgent');
    if (!instanceDesc || instanceDesc.configurable) {
      Object.defineProperty(navigator, 'userAgent', {
        get: function() { return EXPECTED_UA; },
        enumerable: true,
        configurable: true
      });
    }
  } catch (_) {}
  
  // 2b. Override platform at navigator instance level (main thread)
  try {
    const platformInstanceDesc = Object.getOwnPropertyDescriptor(navigator, 'platform');
    if (!platformInstanceDesc || platformInstanceDesc.configurable) {
      Object.defineProperty(navigator, 'platform', {
        get: function() { return EXPECTED_PLATFORM; },
        enumerable: true,
        configurable: true
      });
    } else {
      // CREEPJS FIX: If platform is non-configurable, try alternative approaches
      // Platform mismatch detected - non-configurable
    }
  } catch (_) {}
  
  // 3. SERVICE WORKER SPECIFIC PATCHING
  if ('serviceWorker' in navigator && navigator.serviceWorker) {
    const originalRegister = navigator.serviceWorker.register;
    
    navigator.serviceWorker.register = function(scriptURL, options) {
      try {
        // Create a service worker script that includes ALL navigator property overrides
        const serviceWorkerPreamble = `
// SERVICE WORKER NAVIGATOR SYNC - Execute immediately
const EXPECTED_UA = '${EXPECTED_UA}';
const EXPECTED_LANGS = ${JSON.stringify(EXPECTED_LANGS)};
const EXPECTED_MEM = ${EXPECTED_MEM};
const EXPECTED_CORES = ${EXPECTED_CORES};
const EXPECTED_BRANDS = ${JSON.stringify(EXPECTED_BRANDS)};
const EXPECTED_MOBILE = ${EXPECTED_MOBILE};
const EXPECTED_PLATFORM = '${EXPECTED_PLATFORM}';
const EXPECTED_HIGH_ENTROPY = ${JSON.stringify(EXPECTED_HIGH_ENTROPY)}
const EXPECTED_LANG = EXPECTED_LANGS[0] || 'en-US';
const EXPECTED_TIMEZONE = '__TZ__';

// Override ALL navigator properties in service worker context
  try {
    if (typeof WorkerNavigator !== 'undefined' && WorkerNavigator.prototype) {
      Object.defineProperty(WorkerNavigator.prototype, 'userAgent', {
              get: function() { return EXPECTED_UA; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(WorkerNavigator.prototype, 'language', {
      get: function() { return EXPECTED_LANG; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(WorkerNavigator.prototype, 'languages', {
      get: function() { return EXPECTED_LANGS; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(WorkerNavigator.prototype, 'deviceMemory', {
      get: function() { return EXPECTED_MEM; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(WorkerNavigator.prototype, 'hardwareConcurrency', {
      get: function() { return EXPECTED_CORES; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(WorkerNavigator.prototype, 'platform', {
      get: function() { return EXPECTED_PLATFORM; },
      enumerable: true,
      configurable: true
    });
  }
} catch(e) { }

try {
  if (typeof navigator !== 'undefined') {
    Object.defineProperty(navigator, 'userAgent', {
      get: function() { return EXPECTED_UA; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(navigator, 'language', {
      get: function() { return EXPECTED_LANG; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(navigator, 'languages', {
      get: function() { return EXPECTED_LANGS; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(navigator, 'deviceMemory', {
      get: function() { return EXPECTED_MEM; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(navigator, 'hardwareConcurrency', {
      get: function() { return EXPECTED_CORES; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(navigator, 'platform', {
      get: function() { return EXPECTED_PLATFORM; },
      enumerable: true,
      configurable: true
    });
    
    /* REMOVED: userAgentData handled by spoof_useragent.js */
    // userAgentData spoofing moved to dedicated spoof_useragent.js to avoid conflicts
  }
} catch(e) { }

try {
  if (typeof self !== 'undefined' && self.navigator) {
    Object.defineProperty(self.navigator, 'userAgent', {
      get: function() { return EXPECTED_UA; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'language', {
      get: function() { return EXPECTED_LANG; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'languages', {
      get: function() { return EXPECTED_LANGS; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'deviceMemory', {
      get: function() { return EXPECTED_MEM; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'hardwareConcurrency', {
      get: function() { return EXPECTED_CORES; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'platform', {
      get: function() { return EXPECTED_PLATFORM; },
      enumerable: true,
      configurable: true
    });
    
    /* REMOVED: userAgentData handled by spoof_useragent.js */
    // userAgentData spoofing moved to dedicated spoof_useragent.js to avoid conflicts
  }
} catch(e) { }

try {
  if (typeof globalThis !== 'undefined' && globalThis.navigator) {
    Object.defineProperty(globalThis.navigator, 'userAgent', {
      get: function() { return EXPECTED_UA; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(globalThis.navigator, 'language', {
      get: function() { return EXPECTED_LANG; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(globalThis.navigator, 'languages', {
      get: function() { return EXPECTED_LANGS; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(globalThis.navigator, 'deviceMemory', {
      get: function() { return EXPECTED_MEM; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(globalThis.navigator, 'hardwareConcurrency', {
      get: function() { return EXPECTED_CORES; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(globalThis.navigator, 'platform', {
      get: function() { return EXPECTED_PLATFORM; },
      enumerable: true,
      configurable: true
    });
  }
} catch(e) { }

// Override all possible navigator objects in ServiceWorkerGlobalScope
if (typeof ServiceWorkerGlobalScope !== 'undefined' && self instanceof ServiceWorkerGlobalScope) {
  try {
    Object.defineProperty(self.navigator, 'userAgent', {
      get: function() { return EXPECTED_UA; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'language', {
      get: function() { return EXPECTED_LANG; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'languages', {
      get: function() { return EXPECTED_LANGS; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'deviceMemory', {
      get: function() { return EXPECTED_MEM; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'hardwareConcurrency', {
      get: function() { return EXPECTED_CORES; },
      enumerable: true,
      configurable: true
    });
    Object.defineProperty(self.navigator, 'platform', {
      get: function() { return EXPECTED_PLATFORM; },
      enumerable: true,
      configurable: true
    });
  } catch(e) { }
}

// CRITICAL: Override Intl APIs to match main thread
try {
  // Override Intl.DateTimeFormat.prototype.resolvedOptions
  const originalDateTimeResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
  Intl.DateTimeFormat.prototype.resolvedOptions = function() {
    const result = originalDateTimeResolvedOptions.call(this);
    result.timeZone = EXPECTED_TIMEZONE;
    result.locale = EXPECTED_LANG;
    return result;
  };
  
  // Override other Intl resolvedOptions methods
  const intlConstructors = [
    'Collator', 'DisplayNames', 'ListFormat', 'NumberFormat', 
    'PluralRules', 'RelativeTimeFormat'
  ];
  
  intlConstructors.forEach(constructor => {
    if (typeof Intl[constructor] !== 'undefined' && Intl[constructor].prototype.resolvedOptions) {
      const originalResolvedOptions = Intl[constructor].prototype.resolvedOptions;
      Intl[constructor].prototype.resolvedOptions = function() {
        const result = originalResolvedOptions.call(this);
        result.locale = EXPECTED_LANG;
        return result;
      };
    }
  });
  
  // Override Number.prototype.toLocaleString
  const originalNumberToLocaleString = Number.prototype.toLocaleString;
  Number.prototype.toLocaleString = function(locales, options) {
    return originalNumberToLocaleString.call(this, EXPECTED_LANG, options);
  };
  
  } catch(e) { }

`;
        
        // Handle different script URL types
        if (typeof scriptURL === 'string') {
          if (scriptURL.startsWith('data:')) {
            // For data URLs, decode and prepend our code
            const dataMatch = scriptURL.match(/^data:[^,]*,(.*)$/);
            if (dataMatch) {
              const originalScript = decodeURIComponent(dataMatch[1]);
              const modifiedScript = serviceWorkerPreamble + '\n' + originalScript;
              const blob = new Blob([modifiedScript], { type: 'application/javascript' });
              const newScriptURL = URL.createObjectURL(blob);
              
              const result = originalRegister.call(this, newScriptURL, options);
              
              // Clean up blob URL after registration
              setTimeout(() => {
                try {
                  URL.revokeObjectURL(newScriptURL);
                } catch (_) {}
              }, 5000);
              
              return result;
            }
          } else if (!scriptURL.startsWith('blob:')) {
            // For regular URLs, create a wrapper script
            const wrapperScript = serviceWorkerPreamble + `\nimportScripts('${scriptURL}');`;
            const blob = new Blob([wrapperScript], { type: 'application/javascript' });
            const wrapperURL = URL.createObjectURL(blob);
            
            const result = originalRegister.call(this, wrapperURL, options);
            
            // Clean up blob URL after registration
            setTimeout(() => {
              try {
                URL.revokeObjectURL(wrapperURL);
              } catch (_) {}
            }, 5000);
            
            return result;
          }
        }
        
        // Fallback to original registration
        return originalRegister.call(this, scriptURL, options);
        
      } catch (error) {
        return originalRegister.call(this, scriptURL, options);
      }
    };
    
    // Preserve original function properties
    Object.defineProperty(navigator.serviceWorker.register, 'toString', {
      value: () => originalRegister.toString(),
      configurable: true
    });
    Object.defineProperty(navigator.serviceWorker.register, 'name', {
      value: 'register',
      configurable: true
    });
  }
  
  // 4. COMPREHENSIVE WORKER CONSTRUCTOR PATCHING
  const workerPreamble = `
// AGGRESSIVE WORKER NAVIGATOR SYNC - Execute immediately
(function() {
  const UA = '${EXPECTED_UA}';
  const LANGS = ${JSON.stringify(EXPECTED_LANGS)};
  const MEM = ${EXPECTED_MEM};
  const CORES = ${EXPECTED_CORES};
  const LANG = LANGS[0] || 'en-US';
  const PLATFORM = '${EXPECTED_PLATFORM}';
  const TIMEZONE = '__TZ__';
  
  // Method 1: WorkerNavigator prototype override
  try {
    if (typeof WorkerNavigator !== 'undefined') {
      Object.defineProperty(WorkerNavigator.prototype, 'userAgent', {
        get: function() { return UA; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(WorkerNavigator.prototype, 'language', {
        get: function() { return LANG; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(WorkerNavigator.prototype, 'languages', {
        get: function() { return LANGS; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(WorkerNavigator.prototype, 'deviceMemory', {
        get: function() { return MEM; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(WorkerNavigator.prototype, 'hardwareConcurrency', {
        get: function() { return CORES; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(WorkerNavigator.prototype, 'platform', {
        get: function() { return PLATFORM; },
        enumerable: true,
        configurable: true
      });
      }
  } catch(e) { }
  
  // Method 2: Direct navigator override
  try {
    if (typeof navigator !== 'undefined') {
      Object.defineProperty(navigator, 'userAgent', {
        get: function() { return UA; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(navigator, 'language', {
        get: function() { return LANG; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(navigator, 'languages', {
        get: function() { return LANGS; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(navigator, 'deviceMemory', {
        get: function() { return MEM; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: function() { return CORES; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(navigator, 'platform', {
        get: function() { return PLATFORM; },
        enumerable: true,
        configurable: true
      });
      }
  } catch(e) { }
  
  // Method 3: Self navigator override (for service workers)
  try {
    if (typeof self !== 'undefined' && self.navigator) {
      Object.defineProperty(self.navigator, 'userAgent', {
        get: function() { return UA; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(self.navigator, 'language', {
        get: function() { return LANG; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(self.navigator, 'languages', {
        get: function() { return LANGS; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(self.navigator, 'deviceMemory', {
        get: function() { return MEM; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(self.navigator, 'hardwareConcurrency', {
        get: function() { return CORES; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(self.navigator, 'platform', {
        get: function() { return PLATFORM; },
        enumerable: true,
        configurable: true
      });
      }
  } catch(e) { }
  
  // Method 4: Global scope injection
  try {
    if (typeof globalThis !== 'undefined' && globalThis.navigator) {
      Object.defineProperty(globalThis.navigator, 'userAgent', {
        get: function() { return UA; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(globalThis.navigator, 'language', {
        get: function() { return LANG; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(globalThis.navigator, 'languages', {
        get: function() { return LANGS; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(globalThis.navigator, 'deviceMemory', {
        get: function() { return MEM; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(globalThis.navigator, 'hardwareConcurrency', {
        get: function() { return CORES; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(globalThis.navigator, 'platform', {
        get: function() { return PLATFORM; },
        enumerable: true,
        configurable: true
      });
      }
  } catch(e) { }
  
  // CRITICAL: Override Intl APIs to match main thread
  try {
    // Override Intl.DateTimeFormat.prototype.resolvedOptions
    const originalDateTimeResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
    Intl.DateTimeFormat.prototype.resolvedOptions = function() {
      const result = originalDateTimeResolvedOptions.call(this);
      result.timeZone = TIMEZONE;
      result.locale = LANG;
      return result;
    };
    
    // Override other Intl resolvedOptions methods
    const intlConstructors = [
      'Collator', 'DisplayNames', 'ListFormat', 'NumberFormat', 
      'PluralRules', 'RelativeTimeFormat'
    ];
    
    intlConstructors.forEach(constructor => {
      if (typeof Intl[constructor] !== 'undefined' && Intl[constructor].prototype.resolvedOptions) {
        const originalResolvedOptions = Intl[constructor].prototype.resolvedOptions;
        Intl[constructor].prototype.resolvedOptions = function() {
          const result = originalResolvedOptions.call(this);
          result.locale = LANG;
          return result;
        };
      }
    });
    
    // Override Number.prototype.toLocaleString
    const originalNumberToLocaleString = Number.prototype.toLocaleString;
    Number.prototype.toLocaleString = function(locales, options) {
      return originalNumberToLocaleString.call(this, LANG, options);
    };
    
    } catch(e) { }
  
  })();
`;

  // Patch regular Worker
  if (typeof Worker !== 'undefined') {
    const OriginalWorker = Worker;
    
    window.Worker = function(scriptURL, options) {
      try {
        let modifiedScript = workerPreamble;
        
        if (typeof scriptURL === 'string') {
          if (scriptURL.startsWith('data:')) {
            const dataMatch = scriptURL.match(/^data:[^,]*,(.*)$/);
            if (dataMatch) {
              modifiedScript += '\n' + decodeURIComponent(dataMatch[1]);
            }
          } else if (scriptURL.startsWith('blob:')) {
            // For blob URLs, we'll try to modify via message passing
            const worker = new OriginalWorker(scriptURL, options);
            setTimeout(() => {
              try {
                worker.postMessage({ __STEALTH_INIT__: workerPreamble });
              } catch (_) {}
            }, 0);
            return worker;
          } else {
            modifiedScript += `\nimportScripts('${scriptURL}');`;
          }
        }
        
        const blob = new Blob([modifiedScript], { type: 'application/javascript' });
        const blobURL = URL.createObjectURL(blob);
        
        const worker = new OriginalWorker(blobURL, options);
        
        setTimeout(() => {
          try {
            URL.revokeObjectURL(blobURL);
          } catch (_) {}
        }, 1000);
        
        return worker;
        
      } catch (error) {
        return new OriginalWorker(scriptURL, options);
      }
    };
    
    // Preserve Worker properties
    Object.setPrototypeOf(window.Worker, OriginalWorker);
    Object.defineProperty(window.Worker, 'name', {value: 'Worker', configurable: true});
    Object.defineProperty(window.Worker, 'toString', {
      value: () => 'function Worker() { [native code] }',
      configurable: true
    });
  }
  
  // Patch SharedWorker
  if (typeof SharedWorker !== 'undefined') {
    const OriginalSharedWorker = SharedWorker;
    
    window.SharedWorker = function(scriptURL, options) {
      try {
        let modifiedScript = workerPreamble;
        
        if (typeof scriptURL === 'string') {
          if (scriptURL.startsWith('data:')) {
            const dataMatch = scriptURL.match(/^data:[^,]*,(.*)$/);
            if (dataMatch) {
              modifiedScript += '\n' + decodeURIComponent(dataMatch[1]);
            }
          } else if (!scriptURL.startsWith('blob:')) {
            modifiedScript += `\nimportScripts('${scriptURL}');`;
          }
        }
        
        const blob = new Blob([modifiedScript], { type: 'application/javascript' });
        const blobURL = URL.createObjectURL(blob);
        
        const sharedWorker = new OriginalSharedWorker(blobURL, options);
        
        setTimeout(() => {
          try {
            URL.revokeObjectURL(blobURL);
          } catch (_) {}
        }, 1000);
        
        return sharedWorker;
        
      } catch (error) {
        return new OriginalSharedWorker(scriptURL, options);
      }
    };
    
    Object.setPrototypeOf(window.SharedWorker, OriginalSharedWorker);
    Object.defineProperty(window.SharedWorker, 'name', {value: 'SharedWorker', configurable: true});
    Object.defineProperty(window.SharedWorker, 'toString', {
      value: () => 'function SharedWorker() { [native code] }',
      configurable: true
    });
  }
  
  // 5. MESSAGE-BASED FALLBACK for existing workers
  window.addEventListener('message', function(event) {
    if (event.data && event.data.__STEALTH_INIT__) {
      try {
        eval(event.data.__STEALTH_INIT__);
      } catch (_) {}
    }
  });
})();

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

