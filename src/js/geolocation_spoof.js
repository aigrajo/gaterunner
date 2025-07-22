/**
 * geolocation_spoof.js - Country-aware geolocation spoofing
 * 
 * Replaces navigator.geolocation API with country-randomized coordinates
 * without requiring browser permissions (avoiding TDS detection)
 */

(() => {
  'use strict';
  
  const fakeCoords = {
    latitude: __LATITUDE__,
    longitude: __LONGITUDE__, 
    accuracy: __ACCURACY__,
    altitude: null,
    altitudeAccuracy: null,
    heading: null,
    speed: null
  };

  const fakePosition = {
    coords: fakeCoords,
    timestamp: Date.now()
  };

  // Helper to generate realistic timing delays
  const getRealisticDelay = () => 100 + Math.random() * 200;

  // Replace the entire geolocation API
  Object.defineProperty(navigator, 'geolocation', {
    value: {
      getCurrentPosition(successCallback, errorCallback, options) {
        // Simulate realistic timing delay like real GPS
        setTimeout(() => {
          if (typeof successCallback === 'function') {
            // Update timestamp for each call
            const currentPosition = {
              coords: fakeCoords,
              timestamp: Date.now()
            };
            successCallback(currentPosition);
          }
        }, getRealisticDelay());
      },
      
      watchPosition(successCallback, errorCallback, options) {
        // Return fake watch ID and call success after delay
        const watchId = Math.floor(Math.random() * 1000000) + 1;
        setTimeout(() => {
          if (typeof successCallback === 'function') {
            const currentPosition = {
              coords: fakeCoords,
              timestamp: Date.now()
            };
            successCallback(currentPosition);
          }
        }, getRealisticDelay());
        return watchId;
      },
      
      clearWatch(watchId) {
        // No-op for fake watch - behaves like real clearWatch
      }
    },
    writable: false,
    enumerable: true,
    configurable: false
  });

  // Also ensure the API is available in workers
  if (typeof self !== 'undefined' && self.navigator && !self.navigator.geolocation) {
    Object.defineProperty(self.navigator, 'geolocation', {
      value: navigator.geolocation,
      writable: false,
      enumerable: true,
      configurable: false
    });
  }

  // Silent operation - no console logging to avoid detection
})(); 