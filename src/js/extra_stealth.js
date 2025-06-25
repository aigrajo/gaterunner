/* extra-stealth (chromium & fwk) */
(() => {
  /* Permissions & Notification */
  if (navigator.permissions?.query) {
    const real = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = p =>
      p && p.name === 'notifications'
        ? Promise.resolve({ state: 'prompt', onchange: null })
        : real(p);
  }
  Object.defineProperty(Notification, 'permission', { get: () => 'default' });
  Notification.requestPermission = async () => 'granted';

  /* Advanced Speech-synthesis spoofing */
  if ('speechSynthesis' in window) {
    const voices = [{
      voiceURI: 'Google US English',
      name:     'Google US English',
      lang:     'en-US',
      localService: true,
      default:  true
    }];
    
    const nativeGetVoices = window.speechSynthesis.getVoices;
    
    // Advanced function cloning
    const spoofedGetVoices = function getVoices() {
      return voices;
    };
    
    Object.setPrototypeOf(spoofedGetVoices, nativeGetVoices);
    Object.defineProperty(spoofedGetVoices, 'toString', {
      value: () => nativeGetVoices.toString(),
      configurable: true
    });
    Object.defineProperty(spoofedGetVoices, 'name', {
      value: 'getVoices',
      configurable: true
    });
    
    window.speechSynthesis.getVoices = spoofedGetVoices;
  }

  /* Advanced AudioContext fingerprinting protection */
  const ctxProto = (window.AudioContext || window.webkitAudioContext)?.prototype;
  if (ctxProto && !ctxProto.__patched) {
    const nativeCreateAnalyser = ctxProto.createAnalyser;
    
    // Advanced function replacement with proper cloning
    const spoofedCreateAnalyser = function createAnalyser() {
      const analyser = nativeCreateAnalyser.apply(this, arguments);
      const nativeFFT = analyser.getFloatFrequencyData;
      
      // Clone the FFT function with minimal detection footprint
      const spoofedFFT = function getFloatFrequencyData(array) {
        nativeFFT.call(this, array);
        // Minimal audio noise injection
        if (array && array.length > 0) {
          for (let i = 0; i < array.length; i += 128) {
            array[i] += (Math.random() - 0.5) * 1e-5; // Even smaller noise
          }
        }
      };
      
      // Advanced function cloning
      Object.setPrototypeOf(spoofedFFT, nativeFFT);
      Object.defineProperty(spoofedFFT, 'toString', {
        value: () => nativeFFT.toString(),
        configurable: true
      });
      Object.defineProperty(spoofedFFT, 'name', {
        value: 'getFloatFrequencyData',
        configurable: true
      });
      
      analyser.getFloatFrequencyData = spoofedFFT;
      return analyser;
    };
    
    // Clone createAnalyser function
    Object.setPrototypeOf(spoofedCreateAnalyser, nativeCreateAnalyser);
    Object.defineProperty(spoofedCreateAnalyser, 'toString', {
      value: () => nativeCreateAnalyser.toString(),
      configurable: true
    });
    Object.defineProperty(spoofedCreateAnalyser, 'name', {
      value: 'createAnalyser',
      configurable: true
    });
    
    ctxProto.createAnalyser = spoofedCreateAnalyser;
    ctxProto.__patched = true;
  }

  /* mediaDevices.getUserMedia stub */
  if (navigator.mediaDevices && !navigator.mediaDevices.__patched) {
    navigator.mediaDevices.getUserMedia = async () => new MediaStream();
    navigator.mediaDevices.__patched = true;
  }

  /* ----------------------------------------------------------------------------
   * realistic plugins + mimeTypes
   * --------------------------------------------------------------------------*/
  (function () {
    /* use the real empty arrays to keep correct [[Class]] */
    const nativePlugins = navigator.plugins;
    if (nativePlugins.length === 0) {
      const pdfPlugin = Object.freeze({
        description: 'Portable Document Format',
        filename:    'internal-pdf-viewer',
        name:        'PDF Viewer',
        length:      0
        });
      Object.defineProperty(nativePlugins, '0', { value: pdfPlugin, writable: false });
      Object.defineProperty(nativePlugins, 'length', { value: 1, writable: false });
    }

    const nativeMimes = navigator.mimeTypes;
    if (nativeMimes.length === 0) {
      const pdfMime = Object.freeze({
        type:          'application/pdf',
        suffixes:      'pdf',
        description:   '',
        enabledPlugin: nativePlugins[0]
        });
      Object.defineProperty(nativeMimes, '0', { value: pdfMime, writable: false });
      Object.defineProperty(nativeMimes, 'length', { value: 1, writable: false });
    }
  })();

  /* privacy flags */
  Object.defineProperty(navigator, 'doNotTrack', { get: () => 'unspecified' });

  /* remove Battery Status API so Chrome 116+ behaviour matches */
  (() => {
    const wipe = (obj) => {
      if (!obj || !('getBattery' in obj)) return;
      const ok = delete obj.getBattery;
      if (!ok) {            // if property is non-configurable, shadow it
        try {
          Object.defineProperty(obj, 'getBattery', {
            value: undefined,
            writable: false,
            enumerable: false,
            configurable: false
          });
        } catch (_) {}
      }
    };
    wipe(Navigator.prototype);
    wipe(navigator);
  })();
  if ('getBattery' in navigator) {
    Object.defineProperty(Navigator.prototype, 'getBattery',
      { value: undefined, configurable: false });
    Object.defineProperty(navigator, 'getBattery',
      { value: undefined, configurable: false });
  }
})(); 