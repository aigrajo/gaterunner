// Tiny, deterministic noise for Canvas + WebGL
(() => {
  /* Canvas */
  const getCtx = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type, ...a) {
    const ctx = getCtx.apply(this, [type, ...a]);
    if (type === '2d' && ctx) hook2D(this, ctx);
    return ctx;
  };
  function hook2D(canvas, ctx) {
    const toData = canvas.toDataURL.bind(canvas);
    canvas.toDataURL = (...a) => tweakURI(toData(...a));

    const getImg = ctx.getImageData.bind(ctx);
    ctx.getImageData = (...a) => {
      const img = getImg(...a);
      mutate(img.data);
      return img;
    };
  }
  /* WebGL */
  const gp = WebGLRenderingContext.prototype;
  const read = gp.readPixels;
  gp.readPixels = function (x, y, w, h, fmt, type, arr) {
    const r = read.call(this, x, y, w, h, fmt, type, arr);
    if (arr) mutate(arr);
    return r;
  };

  /* Helpers */
  const seed = crypto.getRandomValues(new Uint32Array(1))[0];
  function rand() {
    let x = seed ^ (seed << 13);
    x ^= x >> 17;
    x ^= x << 5;
    return x & 1;
  }
  function mutate(buf) {
    for (let i = 0; i < buf.length; i += 4) buf[i] ^= rand();
  }
  function tweakURI(u) {
    const idx = 128;
    return u.slice(0, idx) + (u[idx] === 'A' ? 'B' : 'A') + u.slice(idx + 1);
  }
})();
