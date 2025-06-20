const spoofedUAData = {{
  brands: [
    {{ brand: "Chromium", version: "{chromium_v}" }},
    {{ brand: "{brand}", version: "{brand_v}" }},
    {{ brand: "NotA.Brand", version: "99" }}
  ],
  getHighEntropyValues: async function(hints) {{
    const values = {{}};
    for (const hint of hints) {{
      values[hint] = "fake-" + hint;
    }}
    return values;
  }}
}};

Object.defineProperty(navigator, 'userAgentData', {{
  get: () => spoofedUAData,
  configurable: true
}});
