(() => {
  if (speechSynthesis && speechSynthesis.getVoices)
    speechSynthesis.getVoices = () => [{ name: 'Default', lang: 'en-US', localService: true, default: true }];
})();
