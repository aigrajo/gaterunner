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
const EXPECTED_HIGH_ENTROPY = ${JSON.stringify(EXPECTED_HIGH_ENTROPY)};
const EXPECTED_LANG = EXPECTED_LANGS[0] || 'en-US';
const EXPECTED_TIMEZONE = '__TZ__';
const EXPECTED_WEBGL_VENDOR = '__WEBGL_VENDOR__';
const EXPECTED_WEBGL_RENDERER = '__WEBGL_RENDERER__';

console.log('STEALTH: Service Worker preamble executing...');

// Override ALL navigator properties in service worker context
try {
  if (typeof WorkerNavigator !== 'undefined' && WorkerNavigator.prototype) {
    console.log('STEALTH: Overriding WorkerNavigator.prototype...');
    Object.defineProperty(WorkerNavigator.prototype, 'userAgent', {
      get: function() { console.log('STEALTH: WorkerNavigator.userAgent called'); return EXPECTED_UA; },
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
} catch(e) { console.log('STEALTH: WorkerNavigator.prototype failed:', e); }

try {
  if (typeof navigator !== 'undefined') {
    console.log('STEALTH: Overriding navigator...');
    Object.defineProperty(navigator, 'userAgent', {
      get: function() { console.log('STEALTH: navigator.userAgent called'); return EXPECTED_UA; },
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
    
    // Override userAgentData if it exists
    if (navigator.userAgentData) {
      Object.defineProperty(navigator.userAgentData, 'brands', { 
        get: function() { return EXPECTED_BRANDS; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(navigator.userAgentData, 'mobile', { 
        get: function() { return EXPECTED_MOBILE; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(navigator.userAgentData, 'platform', { 
        get: function() { return EXPECTED_PLATFORM; },
        enumerable: true,
        configurable: true
      });
      
      const originalGetHighEntropyValues = navigator.userAgentData.getHighEntropyValues;
      navigator.userAgentData.getHighEntropyValues = async function(hints) {
        const result = {};
        for (const hint of hints || []) {
          if (EXPECTED_HIGH_ENTROPY.hasOwnProperty(hint)) {
            result[hint] = EXPECTED_HIGH_ENTROPY[hint];
          }
        }
        return result;
      };
    }
  }
} catch(e) { console.log('STEALTH: navigator failed:', e); }

try {
  if (typeof self !== 'undefined' && self.navigator) {
    console.log('STEALTH: Overriding self.navigator...');
    Object.defineProperty(self.navigator, 'userAgent', {
      get: function() { console.log('STEALTH: self.navigator.userAgent called'); return EXPECTED_UA; },
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
    
    // Override userAgentData if it exists in worker
    if (self.navigator.userAgentData) {
      Object.defineProperty(self.navigator.userAgentData, 'brands', { 
        get: function() { return EXPECTED_BRANDS; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(self.navigator.userAgentData, 'mobile', { 
        get: function() { return EXPECTED_MOBILE; },
        enumerable: true,
        configurable: true
      });
      Object.defineProperty(self.navigator.userAgentData, 'platform', { 
        get: function() { return EXPECTED_PLATFORM; },
        enumerable: true,
        configurable: true
      });
    }
  }
} catch(e) { console.log('STEALTH: self.navigator failed:', e); }

try {
  if (typeof globalThis !== 'undefined' && globalThis.navigator) {
    console.log('STEALTH: Overriding globalThis.navigator...');
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
} catch(e) { console.log('STEALTH: globalThis.navigator failed:', e); }

// Override all possible navigator objects in ServiceWorkerGlobalScope
if (typeof ServiceWorkerGlobalScope !== 'undefined' && self instanceof ServiceWorkerGlobalScope) {
  try {
    console.log('STEALTH: In ServiceWorkerGlobalScope, overriding...');
    Object.defineProperty(self.navigator, 'userAgent', {
      get: function() { console.log('STEALTH: ServiceWorker userAgent called'); return EXPECTED_UA; },
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
  } catch(e) { console.log('STEALTH: ServiceWorkerGlobalScope failed:', e); }
}

// CRITICAL: Override WebGL APIs in worker context
try {
  console.log('STEALTH: Setting up WebGL overrides...');
  
  // Check if WebGL is available in worker (it might not be)
  if (typeof OffscreenCanvas !== 'undefined') {
    console.log('STEALTH: OffscreenCanvas available, setting up WebGL...');
    
    // Try to get WebGL context and override getParameter
    const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
    const originalGetParameterGL2 = typeof WebGL2RenderingContext !== 'undefined' ? 
      WebGL2RenderingContext.prototype.getParameter : null;
    
    const spoofedGetParameter = function getParameter(parameter) {
      switch (parameter) {
        case 37445: // UNMASKED_VENDOR_WEBGL
          console.log('STEALTH: WebGL vendor requested, returning:', EXPECTED_WEBGL_VENDOR);
          return EXPECTED_WEBGL_VENDOR;
        case 37446: // UNMASKED_RENDERER_WEBGL
          console.log('STEALTH: WebGL renderer requested, returning:', EXPECTED_WEBGL_RENDERER);
          return EXPECTED_WEBGL_RENDERER;
        default:
          return originalGetParameter.call(this, parameter);
      }
    };
    
    WebGLRenderingContext.prototype.getParameter = spoofedGetParameter;
    if (originalGetParameterGL2) {
      WebGL2RenderingContext.prototype.getParameter = spoofedGetParameter;
    }
    
    console.log('STEALTH: WebGL overrides installed');
  } else {
    console.log('STEALTH: OffscreenCanvas not available in worker');
  }
} catch(e) { console.log('STEALTH: WebGL override failed:', e); }

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
  
  console.log('STEALTH: Intl overrides installed');
} catch(e) { console.log('STEALTH: Intl override failed:', e); }

console.log('STEALTH: Service Worker preamble completed');

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
        console.warn('ServiceWorker patching failed:', error);
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
  const WEBGL_VENDOR = '__WEBGL_VENDOR__';
  const WEBGL_RENDERER = '__WEBGL_RENDERER__';
  
  console.log('STEALTH: Worker preamble executing...', { UA, LANGS, MEM, CORES, PLATFORM });
  
  // Method 1: WorkerNavigator prototype override
  try {
    if (typeof WorkerNavigator !== 'undefined') {
      console.log('STEALTH: Overriding WorkerNavigator.prototype...');
      Object.defineProperty(WorkerNavigator.prototype, 'userAgent', {
        get: function() { console.log('STEALTH: WorkerNavigator.userAgent called'); return UA; },
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
      console.log('STEALTH: WorkerNavigator.prototype overrides complete');
    }
  } catch(e) { console.log('STEALTH: WorkerNavigator.prototype failed:', e); }
  
  // Method 2: Direct navigator override
  try {
    if (typeof navigator !== 'undefined') {
      console.log('STEALTH: Overriding navigator...');
      Object.defineProperty(navigator, 'userAgent', {
        get: function() { console.log('STEALTH: navigator.userAgent called'); return UA; },
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
      console.log('STEALTH: navigator overrides complete');
    }
  } catch(e) { console.log('STEALTH: navigator failed:', e); }
  
  // Method 3: Self navigator override (for service workers)
  try {
    if (typeof self !== 'undefined' && self.navigator) {
      console.log('STEALTH: Overriding self.navigator...');
      Object.defineProperty(self.navigator, 'userAgent', {
        get: function() { console.log('STEALTH: self.navigator.userAgent called'); return UA; },
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
      console.log('STEALTH: self.navigator overrides complete');
    }
  } catch(e) { console.log('STEALTH: self.navigator failed:', e); }
  
  // Method 4: Global scope injection
  try {
    if (typeof globalThis !== 'undefined' && globalThis.navigator) {
      console.log('STEALTH: Overriding globalThis.navigator...');
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
      console.log('STEALTH: globalThis.navigator overrides complete');
    }
  } catch(e) { console.log('STEALTH: globalThis.navigator failed:', e); }
  
  // CRITICAL: Override WebGL APIs in worker context
  try {
    console.log('STEALTH: Setting up WebGL overrides...');
    
    // Check if WebGL is available in worker (it might not be)
    if (typeof OffscreenCanvas !== 'undefined') {
      console.log('STEALTH: OffscreenCanvas available, setting up WebGL...');
      
      // Try to get WebGL context and override getParameter
      const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
      const originalGetParameterGL2 = typeof WebGL2RenderingContext !== 'undefined' ? 
        WebGL2RenderingContext.prototype.getParameter : null;
      
      const spoofedGetParameter = function getParameter(parameter) {
        switch (parameter) {
          case 37445: // UNMASKED_VENDOR_WEBGL
            console.log('STEALTH: WebGL vendor requested, returning:', WEBGL_VENDOR);
            return WEBGL_VENDOR;
          case 37446: // UNMASKED_RENDERER_WEBGL
            console.log('STEALTH: WebGL renderer requested, returning:', WEBGL_RENDERER);
            return WEBGL_RENDERER;
          default:
            return originalGetParameter.call(this, parameter);
        }
      };
      
      WebGLRenderingContext.prototype.getParameter = spoofedGetParameter;
      if (originalGetParameterGL2) {
        WebGL2RenderingContext.prototype.getParameter = spoofedGetParameter;
      }
      
      console.log('STEALTH: WebGL overrides installed');
    } else {
      console.log('STEALTH: OffscreenCanvas not available in worker');
    }
  } catch(e) { console.log('STEALTH: WebGL override failed:', e); }
  
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
    
    console.log('STEALTH: Intl overrides installed');
  } catch(e) { console.log('STEALTH: Intl override failed:', e); }
  
  console.log('STEALTH: Worker preamble completed');
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
        console.warn('Worker patching failed:', error);
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
        console.warn('SharedWorker patching failed:', error);
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

/* Navigator.userAgentData */
if (navigator.userAgentData) {
  const brands = [{brand: '__BRAND__', version: '__BRAND_V__'}];
  Object.defineProperty(navigator.userAgentData, 'brands', { get: () => brands });
  Object.defineProperty(navigator.userAgentData, 'mobile', { get: () => __MOBILE__ });
  Object.defineProperty(navigator.userAgentData, 'platform', { get: () => '__PLATFORM__' });
  
  const highEntropyHints = {
    architecture: '__ARCH__',
    bitness: '__BITNESS__',
    brands: brands,
    mobile: __MOBILE__,
    model: '__MODEL__',
    platform: '__PLATFORM__',
    platformVersion: '__PLATFORM_VERSION__',
    uaFullVersion: '__UA_FULL_VERSION__',
    wow64: __WOW64__
  };
  
  const originalGetHighEntropyValues = navigator.userAgentData.getHighEntropyValues;
  navigator.userAgentData.getHighEntropyValues = async function(hints) {
    const result = {};
    for (const hint of hints || []) {
      if (highEntropyHints.hasOwnProperty(hint)) {
        result[hint] = highEntropyHints[hint];
      }
    }
    return result;
  };
}

/* WebGL vendor + renderer → more realistic pairs */
(() => {
  try {
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    const getParameterWGL2 = WebGL2RenderingContext.prototype.getParameter;
    
    const spoofedGetParameter = function getParameter(parameter) {
      switch (parameter) {
        case 37445: // UNMASKED_VENDOR_WEBGL
          return '__WEBGL_VENDOR__';
        case 37446: // UNMASKED_RENDERER_WEBGL
          return '__WEBGL_RENDERER__';
        default:
          return getParameter.call(this, parameter);
      }
    };
    
    // Apply to both contexts
    WebGLRenderingContext.prototype.getParameter = spoofedGetParameter;
    if (typeof WebGL2RenderingContext !== 'undefined') {
      WebGL2RenderingContext.prototype.getParameter = spoofedGetParameter;
    }
  } catch (err) {
    console.warn('[Stealth] WebGL patching failed:', err);
  }
})();



/* deep-stealth (chromium) – final */
(() => {
  try {
    /* 1 – remove webdriver */
    delete Navigator.prototype.webdriver;
    delete navigator.webdriver;

    /* 2 – userAgentData */
    const uaData = {
      brands: [{ brand: '__BRAND__', version: '__BRAND_V__' }],
      platform: '__PLATFORM__',
      mobile: __MOBILE__,
      getHighEntropyValues: async (hints) => {
        const src = {
          architecture: '__ARCH__',
          bitness: '__BITNESS__',
          model: '__MODEL__',
          platformVersion: '__PLATFORM_VERSION__',
          uaFullVersion: '__UA_FULL_VERSION__',
          wow64: __WOW64__
        };
        const out = {};
        for (const h of hints) if (src[h] !== undefined) out[h] = src[h];
        return out;
      }
    };
    Object.defineProperty(navigator, 'userAgentData', { get: () => uaData });

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
                
    /* 4 – WebGL spoof */
    const SPOOF_VENDOR   = '__WEBGL_VENDOR__';
    const SPOOF_RENDERER = '__WEBGL_RENDERER__';
    const CONSTS = {
      VENDOR:            0x1F00,
      RENDERER:          0x1F01,
      UNMASKED_VENDOR:   0x9245,
      UNMASKED_RENDERER: 0x9246,
    };

    ['WebGLRenderingContext','WebGL2RenderingContext'].forEach((ctxName) => {
      const proto = window[ctxName]?.prototype;
      if (!proto) return;

      /* Advanced WebGL spoofing - avoid Proxy detection */
      const nativeGet = proto.getParameter;
      
      // Method: Function replacement with native toString preservation
      const spoofedGetParameter = function getParameter(parameter) {
        switch (parameter) {
          case CONSTS.VENDOR:
          case CONSTS.UNMASKED_VENDOR:
            return SPOOF_VENDOR;
          case CONSTS.RENDERER:
          case CONSTS.UNMASKED_RENDERER:
            return SPOOF_RENDERER;
          default:
            return nativeGet.call(this, parameter);
        }
      };

      // Copy all properties from original function to avoid detection
      Object.setPrototypeOf(spoofedGetParameter, nativeGet);
      Object.defineProperty(spoofedGetParameter, 'toString', {
        value: () => nativeGet.toString(),
        configurable: true
      });
      Object.defineProperty(spoofedGetParameter, 'name', {
        value: 'getParameter',
        configurable: true
      });
      
      proto.getParameter = spoofedGetParameter;


    });



    /* 5 – Advanced canvas fingerprinting protection */
    const nativeToDataURL = HTMLCanvasElement.prototype.toDataURL;
    
    // Method: Minimal noise injection with function cloning
    const spoofedToDataURL = function toDataURL() {
      // Add minimal noise before export
      try {
        const ctx = this.getContext('2d');
        if (ctx) {
          const imageData = ctx.getImageData(0, 0, Math.min(10, this.width), Math.min(10, this.height));
          const data = imageData.data;
          
          // Minimal pixel manipulation - less detectable than fillRect
          for (let i = 0; i < data.length; i += 4) {
            if (Math.random() < 0.1) { // Only modify 10% of pixels
              data[i] = (data[i] + Math.floor(Math.random() * 3) - 1) & 255;
            }
          }
          ctx.putImageData(imageData, 0, 0);
        }
      } catch (_) {}
      
      return nativeToDataURL.apply(this, arguments);
    };
    
    // Advanced function cloning to avoid detection
    Object.setPrototypeOf(spoofedToDataURL, nativeToDataURL);
    Object.defineProperty(spoofedToDataURL, 'toString', {
      value: () => nativeToDataURL.toString(),
      configurable: true
    });
    Object.defineProperty(spoofedToDataURL, 'name', {
      value: 'toDataURL',
      configurable: true
    });
    
    HTMLCanvasElement.prototype.toDataURL = spoofedToDataURL;

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
  } catch (_err) {}
})();

