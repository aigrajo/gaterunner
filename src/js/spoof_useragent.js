(() => {{
  const spoofedUAData = {{
    brands: [
      {{ brand: "Chromium",   version: "{chromium_v}" }},
      {{ brand: "{brand}",    version: "{brand_v}"   }},
      {{ brand: "Not.A/Brand", version: "99" }}
    ],
    architecture:    "{architecture}",
    bitness:         "{bitness}",
    wow64:           {wow64},
    model:           "{model}",
    mobile:          {mobile},
    platform:        "{platform}",
    platformVersion: "{platformVersion}",
    uaFullVersion:   "{uaFullVersion}",
    fullVersionList: [
      {{ brand: "Chromium", version: "{uaFullVersion}" }},
      {{ brand: "{brand}",  version: "{uaFullVersion}" }}
    ],

    getHighEntropyValues(hints) {{
      const map = {{
        architecture:    this.architecture,
        bitness:         this.bitness,
        wow64:           this.wow64,
        model:           this.model,
        platform:        this.platform,
        platformVersion: this.platformVersion,
        uaFullVersion:   this.uaFullVersion,
        fullVersionList: this.fullVersionList,
      }};
      return Promise.resolve(
        Object.fromEntries(hints.map(h => [h, map[h] ?? ""]))
      );
    }},
    toJSON() {{ return this; }}
  }};

  Object.defineProperty(Navigator.prototype, "userAgentData", {{
    get: () => spoofedUAData,
    enumerable: true
  }});
}})();
