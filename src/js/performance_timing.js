(() => {
  const q = v => Math.round(v / 50) * 50;
  const now = performance.now.bind(performance);
  performance.now = () => q(now());
  const get = performance.getEntriesByType.bind(performance);
  performance.getEntriesByType = t => get(t).map(e => (e.startTime = q(e.startTime), e.duration = q(e.duration), e));
})();
