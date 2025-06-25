/* webgl_patch.js  –  uses same “clone‐and-swap” formula as spoof_useragent */
(() => {
  const VENDOR   = '__WEBGL_VENDOR__';
  const RENDERER = '__WEBGL_RENDERER__';

  /** clone helper: keep every observable flag from the native method */
  const replace = (Ctx, key, wrapper) => {
    const orig = Ctx.prototype[key];
    if (typeof orig !== 'function') return;                  // nothing to do
    const desc = Object.getOwnPropertyDescriptor(Ctx.prototype, key);

    /* 1. make wrapper NON-constructible & prototype-less */
    const f = wrapper.bind(null);          // bound ⇒ inherits “non-constructor”
    try { delete f.prototype; } catch {}   // built-ins expose no own prototype

    /* 2. mirror visible props */
    Object.setPrototypeOf(f, orig);        // clone [[Prototype]] chain
    Object.defineProperty(f, 'name',   { value: key });
    Object.defineProperty(f, 'length', { value: orig.length });
    Object.defineProperty(f, 'toString', {
      value: () => String(orig)            // native source string
    });

    /* 3. swap on the prototype keeping descriptor flags identical */
    Object.defineProperty(Ctx.prototype, key, { ...desc, value: f });
  };

  const patch = (Ctx) => {
    if (!Ctx) return;

    /* --- getParameter ------------------------------------------------ */
    replace(Ctx, 'getParameter', function (param) {
      if (param === 37445) return VENDOR;
      if (param === 37446) return RENDERER;
      /* same error paths / this-binding as native */
      return arguments.callee.__proto__.apply(this, arguments);
    });

    /* --- getExtension ------------------------------------------------- */
    replace(Ctx, 'getExtension', function (name) {
      if (name === 'WEBGL_debug_renderer_info') {
        return { UNMASKED_VENDOR_WEBGL: 37445,
                 UNMASKED_RENDERER_WEBGL: 37446 };
      }
      return arguments.callee.__proto__.apply(this, arguments);
    });
  };

  patch(self.WebGLRenderingContext);
  patch(self.WebGL2RenderingContext);
})();
