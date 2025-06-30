(() => {
  if ('connection' in navigator) Object.defineProperty(navigator, 'connection', {
    get: () => ({ type: 'wifi', effectiveType: '4g', downlink: 10, rtt: 50,
                  saveData: false, addEventListener(){}, removeEventListener(){} })
  });
})();
