/**
 * worker_spoof_template.js – Template for spoofing navigator properties inside
 * Web Workers and Service Workers.
 * Placeholders like __PLATFORM__ are filled by the SpoofingManager.
 */

(() => {
    const nav = __NAV_REF__;
    const spoof = __SPOOF_JSON__;

    const def = (obj, key, val) =>
        Object.defineProperty(obj, key, { get: () => val });

    def(nav, 'platform', '__PLATFORM__');
    def(nav, 'userAgent', '__USER_AGENT__');
    def(nav, 'deviceMemory', __DEVICE_MEMORY__);
    def(nav, 'hardwareConcurrency', __HARDWARE_CONCURRENCY__);
    def(nav, 'language', '__LANGUAGE__');
    def(nav, 'languages', __LANGUAGES_JSON__);

    const uaData = {
        ...spoof,
        getHighEntropyValues: async (hints) => {
            const result = {};
            for (const k of hints) {
                if (k in spoof) result[k] = spoof[k];
            }
            return result;
        },
        toJSON: () => spoof
    };
    Object.defineProperty(nav, 'userAgentData', { get: () => uaData });

    const spoofWebGL = (proto) => {
        const orig = proto.getParameter;
        proto.getParameter = function (p) {
            if (p === 37445) return '__WEBGL_VENDOR__';
            if (p === 37446) return '__WEBGL_RENDERER__';
            return orig.call(this, p);
        };
    };
    if (__WIN_REF__.WebGLRenderingContext)
        spoofWebGL(__WIN_REF__.WebGLRenderingContext.prototype);
    if (__WIN_REF__.WebGL2RenderingContext)
        spoofWebGL(__WIN_REF__.WebGL2RenderingContext.prototype);

    try {
        const orig = Intl.DateTimeFormat.prototype.resolvedOptions;
        Intl.DateTimeFormat.prototype.resolvedOptions = function () {
            const o = orig.call(this);
            o.timeZone = '__TIMEZONE__';
            return o;
        };
    } catch (_e) {}
})(); 