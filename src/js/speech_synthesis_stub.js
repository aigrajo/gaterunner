// Speech Synthesis API stub with proper error handling per CreepJS research
(() => {
  'use strict';

  /* speechSynthesis stub with native-like behavior */
  if ('speechSynthesis' in window && window.speechSynthesis) {
    if (window.speechSynthesis.getVoices && !window.speechSynthesis.getVoices.__isPatched) {
      const originalGetVoices = window.speechSynthesis.getVoices;
      
      const newImpl = function getVoices() {
        // Per report: handle context checking like native function
        // Native getVoices should throw on wrong context
        if (this !== window.speechSynthesis && this !== speechSynthesis) {
          throw new TypeError("Illegal invocation");
        }
        
        // Return realistic voice list (Windows-style voices for consistency)
        return [
          {
            default: true,
            lang: 'en-US',
            localService: true,
            name: 'Microsoft David Desktop - English (United States)',
            voiceURI: 'Microsoft David Desktop - English (United States)'
          },
          {
            default: false,
            lang: 'en-GB', 
            localService: true,
            name: 'Microsoft Hazel Desktop - English (Great Britain)',
            voiceURI: 'Microsoft Hazel Desktop - English (Great Britain)'
          },
          {
            default: false,
            lang: 'en-US',
            localService: true,
            name: 'Microsoft Zira Desktop - English (United States)',
            voiceURI: 'Microsoft Zira Desktop - English (United States)'
          }
        ];
      };
      
      // Preserve native function characteristics
      Object.setPrototypeOf(newImpl, Object.getPrototypeOf(originalGetVoices));
      Object.defineProperty(newImpl, 'name', { 
        value: originalGetVoices.name, 
        configurable: true 
      });
      Object.defineProperty(newImpl, 'length', { 
        value: originalGetVoices.length, 
        configurable: true 
      });
      Object.defineProperty(newImpl, 'toString', { 
        value: function() { return originalGetVoices.toString(); },
        configurable: true 
      });
      
      // Make function not constructable (like native)
      Object.defineProperty(newImpl, 'prototype', {
        value: undefined,
        writable: false
      });
      
      Object.defineProperty(newImpl, '__isPatched', {
        value: true,
        writable: false,
        enumerable: false,
        configurable: false
      });
      
      // Replace the original function
      Object.defineProperty(window.speechSynthesis, 'getVoices', {
        value: newImpl,
        writable: true,
        enumerable: false,
        configurable: true
      });
      
      console.log('[SPEECH] speechSynthesis.getVoices patched with proper error handling');
    }
  }
})();