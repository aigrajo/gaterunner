// Jitter channel data so the hash drifts
(() => {
  const get = AudioBuffer.prototype.getChannelData;
  const noise = (1e-5) * (crypto.getRandomValues(new Uint32Array(1))[0] / 2 ** 32 - 0.5);
  AudioBuffer.prototype.getChannelData = function (...a) {
    const data = get.apply(this, a);
    for (let i = 0; i < data.length; i += 256) data[i] += noise;
    return data;
  };
})();
