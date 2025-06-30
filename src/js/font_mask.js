// Shrink the visible font set
(() => {
  const safe = ['Arial', 'Courier New', 'Times New Roman'];
  const FontItr = {
    [Symbol.iterator]: function* () { for (const n of safe) yield new FontFace(n, ''); }
  };
  if (document.fonts && document.fonts.values) {
    const orig = document.fonts.values;
    document.fonts.values = function () { return FontItr; };
  }
})();
