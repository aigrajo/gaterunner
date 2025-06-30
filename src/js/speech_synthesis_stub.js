(() => {
  const voices = [
    { voiceURI: 'Google Deutsch',              name: 'Google Deutsch',              lang: 'de-DE',    localService: true, default: false },
    { voiceURI: 'Google US English',           name: 'Google US English',           lang: 'en-US',    localService: true, default: true  },
    { voiceURI: 'Google UK English Female',    name: 'Google UK English Female',    lang: 'en-GB',    localService: true, default: false },
    { voiceURI: 'Google UK English Male',      name: 'Google UK English Male',      lang: 'en-GB',    localService: true, default: false },
    { voiceURI: 'Google español',              name: 'Google español',              lang: 'es-ES',    localService: true, default: false },
    { voiceURI: 'Google español de Estados Unidos', name: 'Google español de Estados Unidos', lang: 'es-US', localService: true, default: false },
    { voiceURI: 'Google français',             name: 'Google français',             lang: 'fr-FR',    localService: true, default: false },
    { voiceURI: 'Google हिन्दी',               name: 'Google हिन्दी',               lang: 'hi-IN',    localService: true, default: false },
    { voiceURI: 'Google Bahasa Indonesia',     name: 'Google Bahasa Indonesia',     lang: 'id-ID',    localService: true, default: false },
    { voiceURI: 'Google italiano',             name: 'Google italiano',             lang: 'it-IT',    localService: true, default: false },
    { voiceURI: 'Google 日本語',                 name: 'Google 日本語',                 lang: 'ja-JP',    localService: true, default: false },
    { voiceURI: 'Google 한국의',                name: 'Google 한국의',                lang: 'ko-KR',    localService: true, default: false },
    { voiceURI: 'Google Nederlands',           name: 'Google Nederlands',           lang: 'nl-NL',    localService: true, default: false },
    { voiceURI: 'Google polski',               name: 'Google polski',               lang: 'pl-PL',    localService: true, default: false },
    { voiceURI: 'Google português do Brasil',  name: 'Google português do Brasil',  lang: 'pt-BR',    localService: true, default: false },
    { voiceURI: 'Google русский',              name: 'Google русский',              lang: 'ru-RU',    localService: true, default: false },
    { voiceURI: 'Google 普通话（中国大陆）',        name: 'Google 普通话（中国大陆）',        lang: 'zh-CN',   localService: true, default: false },
    { voiceURI: 'Google 粤語（香港）',             name: 'Google 粤語（香港）',             lang: 'zh-HK',   localService: true, default: false },
    { voiceURI: 'Google 國語（臺灣）',             name: 'Google 國語（臺灣）',             lang: 'zh-TW',   localService: true, default: false }
  ];

  /* clone the native getVoices so .toString() still looks native */
  const nativeGetVoices = window.speechSynthesis?.getVoices;
  if (!nativeGetVoices) return;              // API missing (Firefox / WebKit)

  function getVoices() { return voices; }

  Object.setPrototypeOf(getVoices, nativeGetVoices);
  Object.defineProperty(getVoices, 'name',      { value: 'getVoices', configurable: true });
  Object.defineProperty(getVoices, 'toString',  { value: () => nativeGetVoices.toString(), configurable: true });

  window.speechSynthesis.getVoices = getVoices;
})();