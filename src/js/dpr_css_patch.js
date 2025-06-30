(() => {
  const DPR = 2;
  Object.defineProperty(window, 'devicePixelRatio', { get: () => DPR });
  const mm = window.matchMedia;
  window.matchMedia = q => /device-pixel-ratio|resolution/.test(q)
    ? { matches: q.includes(`${DPR}`), media: q }      // stubbed MediaQueryList
    : mm.call(window, q);
})();
