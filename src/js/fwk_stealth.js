/* fwk-stealth (deep) */
Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions',
  { value: () => ({ timeZone: '__TZ__' }) });
Object.defineProperty(navigator, 'vendor', { get: () => '' });
Object.defineProperty(navigator, 'oscpu', { get: () => undefined });
Object.defineProperty(navigator, 'buildID', { get: () => undefined });
Object.defineProperty(navigator, 'productSub', { get: () => '20100101' });
try { delete window.navigator.__proto__.mozAddonManager; } catch(_) {}

/* realistic plugin + mimeTypes */
Object.defineProperty(navigator, 'plugins', { get: () => [
  { name: 'Portable Document Format', filename: 'internal-pdf-viewer',
     description: 'Portable Document Format' }
] });
Object.defineProperty(navigator, 'mimeTypes', { get: () => [
  { type: 'application/pdf', description: '', suffixes: 'pdf',
     enabledPlugin: navigator.plugins[0] }
] });

 