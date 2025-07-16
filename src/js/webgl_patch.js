/**
 * webgl_patch.js – comprehensive WebGL spoofing for all contexts
 * Handles GPU vendor/renderer spoofing and pixel fingerprint protection
 * across main thread, workers, and service workers
 */

(function () {
  const vendor   = "__WEBGL_VENDOR__";
  const renderer = "__WEBGL_RENDERER__";
  const DBG_EXT  = "WEBGL_debug_renderer_info";

  // ───────────────────────────────────────────────────────── helpers ──

  function mirrorDescriptor(src, tgt) {
    Object.defineProperty(tgt, "name",   { value: src.name });
    Object.defineProperty(tgt, "length", { value: src.length });
    Object.defineProperty(tgt, "toString", {
      value: Function.prototype.toString.bind(src),
      writable: false,
      enumerable: false,
      configurable: true
    });
  }

  // Simple Fowler–Noll–Vo hash (FNV‑1a 32‑bit) → 0‑255 byte
  function hashByte(str) {
    let h = 0x811c9dc5;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = (h * 0x01000193) >>> 0;
    }
    return h & 0xff;
  }

  // Overwrite small pixel buffers in‑place (≤32 px)
  function scrubPixels(pixels, w, h) {
    if (!pixels || pixels.length === 0) return;
    if (w * h > 32) return;                 // real renders stay untouched

    const seed = hashByte(vendor + renderer);
    for (let i = 0; i < pixels.length; i++) {
      pixels[i] = (seed + i) & 0xff;        // deterministic pattern
    }
  }

  // ─────────────────────────────────── per‑context instrumentation ──

  function patchInstance(ctx, originalGetParameter, originalReadPixels) {
    // 1) getParameter spoof (already arrow ⇒ no prototype)
    if (!ctx.getParameter.__isPatched) {
      const spoof = (param) => {
        try {
          const ext = ctx.getExtension && ctx.getExtension(DBG_EXT);
          if (ext) {
            if (param === ext.UNMASKED_VENDOR_WEBGL)   return vendor;
            if (param === ext.UNMASKED_RENDERER_WEBGL) return renderer;
          }
        } catch (_) {/*ignored*/}
        return originalGetParameter.call(ctx, param);
      };
      mirrorDescriptor(originalGetParameter, spoof);
      Object.defineProperty(spoof, "__isPatched", { value: true });
      Object.defineProperty(ctx, "getParameter", {
        value: spoof,
        configurable: true,
        enumerable: false,
        writable: true
      });
    }

    // 2) readPixels hash scrub (includes canvas_webgl_noise functionality)
    if (!ctx.readPixels.__isPatched) {
      const scrubber = (x, y, w, h, format, type, pixels) => {
        const res = originalReadPixels.call(ctx, x, y, w, h, format, type, pixels);
        try { 
          scrubPixels(pixels, w, h);
          
          // Add additional noise for all buffers (canvas_webgl_noise functionality)
          if (pixels && pixels.length > 0) {
            const seed = crypto.getRandomValues ? crypto.getRandomValues(new Uint32Array(1))[0] : Date.now();
            for (let i = 0; i < pixels.length; i += 4) {
              pixels[i] ^= (seed ^ (seed << 13) ^ (seed >> 17) ^ (seed << 5)) & 1;
            }
          }
        } catch (_) {}
        return res;
      };
      mirrorDescriptor(originalReadPixels, scrubber);
      Object.defineProperty(scrubber, "__isPatched", { value: true });
      Object.defineProperty(ctx, "readPixels", {
        value: scrubber,
        configurable: true,
        enumerable: false,
        writable: true
      });
    }
  }

  // ───────────────────────────── prototype hook to capture contexts ──

  function instrument(Context) {
    if (!Context || !Context.prototype) return;

    const getExt  = Context.prototype.getExtension;
    const getParm = Context.prototype.getParameter;
    const rdPix   = Context.prototype.readPixels;

    if (!getExt || getExt.__isPatched) return;

    function getExtensionWrapper(name) {
      const ext = getExt.apply(this, arguments);
      if (name === DBG_EXT && ext) {
        patchInstance(this, getParm, rdPix);
      }
      return ext;
    }

    mirrorDescriptor(getExt, getExtensionWrapper);
    Object.defineProperty(getExtensionWrapper, "__isPatched", { value: true });

    Object.defineProperty(Context.prototype, "getExtension", {
      value: getExtensionWrapper,
      configurable: true,
      enumerable: false,
      writable: true
    });
  }

  // ───────────── comprehensive context coverage (main + workers) ──

  // Main thread WebGL contexts
  if (typeof window !== 'undefined') {
    instrument(window.WebGLRenderingContext);
    instrument(window.WebGL2RenderingContext);
  }

  // Worker contexts (Web Workers, Service Workers)
  if (typeof self !== 'undefined' && typeof window === 'undefined') {
    // We're in a worker context
    instrument(self.WebGLRenderingContext);
    instrument(self.WebGL2RenderingContext);
    
    // For OffscreenCanvas in workers
    if (typeof OffscreenCanvas !== 'undefined') {
      // Override getParameter directly for worker contexts since they may not use getExtension pattern
      ['WebGLRenderingContext', 'WebGL2RenderingContext'].forEach(ctxName => {
        const Context = self[ctxName];
        if (Context && Context.prototype && Context.prototype.getParameter) {
          const originalGetParameter = Context.prototype.getParameter;
          
          if (!originalGetParameter.__isWorkerPatched) {
            const spoofedGetParameter = function getParameter(parameter) {
              switch (parameter) {
                case 37445: // UNMASKED_VENDOR_WEBGL  
                  return vendor;
                case 37446: // UNMASKED_RENDERER_WEBGL
                  return renderer;
                default:
                  return originalGetParameter.call(this, parameter);
              }
            };
            
            mirrorDescriptor(originalGetParameter, spoofedGetParameter);
            Object.defineProperty(spoofedGetParameter, '__isWorkerPatched', { value: true });
            
            Context.prototype.getParameter = spoofedGetParameter;
          }
        }
      });
    }
  }

  // Global scope coverage (covers additional edge cases)
  if (typeof globalThis !== 'undefined') {
    instrument(globalThis.WebGLRenderingContext);
    instrument(globalThis.WebGL2RenderingContext);
  }

})();
