(() => {
  const spoofedUAData = {
    brands: [
      { brand: "Chromium",   version: "__CHROMIUM_V__" },
      { brand: "__BRAND__",    version: "__BRAND_V__"   },
      { brand: "Not.A/Brand", version: "99" }
    ],
    architecture:    "__ARCHITECTURE__",
    bitness:         "__BITNESS__",
    wow64:           __WOW64__,
    model:           "__MODEL__",
    mobile:          __MOBILE__,
    platform:        "__PLATFORM__",
    platformVersion: "__PLATFORM_VERSION__",
    uaFullVersion:   "__UA_FULL_VERSION__",
    fullVersionList: [
      { brand: "Chromium", version: "__UA_FULL_VERSION__" },
      { brand: "__BRAND__",  version: "__UA_FULL_VERSION__" },
      { brand: "Not.A/Brand", version: "99" }

    ],

    getHighEntropyValues(hints) {
      const map = {
        architecture:    this.architecture,
        bitness:         this.bitness,
        wow64:           this.wow64,
        model:           this.model,
        platform:        this.platform,
        platformVersion: this.platformVersion,
        uaFullVersion:   this.uaFullVersion,
        fullVersionList: this.fullVersionList,
      };
      return Promise.resolve(
        Object.fromEntries(hints.map(h => [h, map[h] ?? ""]))
      );
    },
    toJSON() { return this; }
  };

  Object.defineProperty(Navigator.prototype, "userAgentData", {
    get: () => spoofedUAData,
    enumerable: true
  });

  // Fix main thread navigator.userAgent spoofing for CreepJS consistency
  Object.defineProperty(Navigator.prototype, "userAgent", {
    get: () => "__USER_AGENT__",
    enumerable: true,
    configurable: true
  });

  // Fix main thread navigator.appVersion spoofing for CreepJS consistency  
  Object.defineProperty(Navigator.prototype, "appVersion", {
    get: () => "__USER_AGENT__".replace('Mozilla/', ''),
    enumerable: true,
    configurable: true
  });
})();
