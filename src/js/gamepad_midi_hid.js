(() => {
  if (navigator.getGamepads) navigator.getGamepads = () => [];
  if (navigator.requestMIDIAccess) navigator.requestMIDIAccess = () => Promise.reject();
  if (navigator.hid) navigator.hid.getDevices = () => Promise.resolve([]);
})();
