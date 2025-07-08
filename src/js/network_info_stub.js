(() => {
  if (!('connection' in navigator)) {
    Object.defineProperty(navigator, 'connection', {
      get: () => ({
        type: '__CONN_TYPE__',          // wifi, cellular, etc.
        effectiveType: '__EFFECTIVE_TYPE__',  // 4g, 3g, 5g
        downlink: __DOWNLINK__,         // float Mbps
        rtt: __RTT__,                   // ms
        saveData: __SAVE_DATA__,        // boolean
        addEventListener() {},
        removeEventListener() {}
      }),
      configurable: true
    });
  }
})();
