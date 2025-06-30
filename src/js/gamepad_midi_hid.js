(() => {
  /* 1 ── navigator.getGamepads */
  if (navigator.getGamepads) {
    const nativeGP = navigator.getGamepads;          // keep reference
    const spoofedGP = function getGamepads() {       // regular func, not arrow
      const pads = nativeGP.call(navigator) || [];
      /* return empty array but keep same object type */
      return pads.filter(Boolean);                   // -- or do extra mapping if needed
    };
    Object.setPrototypeOf(spoofedGP, nativeGP);      // inherit props
    Object.defineProperty(spoofedGP, 'toString', {   // hide source
      value: () => nativeGP.toString(),
      configurable: true
    });
    navigator.getGamepads = spoofedGP;
  }

  /* 2 ── navigator.requestMIDIAccess */
  const midiReject = function requestMIDIAccess() {  // regular func
    return new Promise((_, rej) => {
      setTimeout(() =>
        rej(new DOMException('', 'NotSupportedError')),
        300 + Math.random() * 300);
    });
  };
  /* mimic a native function’s toString output */
  Object.defineProperty(midiReject, 'toString', {
    value: () => 'function requestMIDIAccess() { [native code] }',
    configurable: true
  });
  navigator.requestMIDIAccess = midiReject;
})();
