(() => {
  const PC = window.RTCPeerConnection;
  if (!PC) return;
  class PCWrap extends PC {
    constructor(...a) { super(...a); this.addEventListener('icecandidate', scrub); }
  }
  function scrub(e) {
    if (e.candidate && e.candidate.candidate)
      e.candidate.candidate = e.candidate.candidate.replace(/(\d{1,3}\.){3}\d{1,3}/g, '0.0.0.0');
  }
  window.RTCPeerConnection = PCWrap;
})();
