/**
 * worker_spoof_template.js – Template for spoofing navigator properties inside
 * Web Workers and Service Workers.
 * Placeholders like {platform} are filled by Python .format().
 * All non-placeholder braces are doubled to escape them.
 */

(() => {{
    const nav = {nav_ref};
    const spoof = {spoof_json};

    const def = (obj, key, val) =>
        Object.defineProperty(obj, key, {{ get: () => val }});

    def(nav, 'platform', '{platform}');
    def(nav, 'userAgent', '{user_agent}');
    def(nav, 'deviceMemory', {device_memory});
    def(nav, 'hardwareConcurrency', {hardware_concurrency});
    def(nav, 'language', '{language}');
    def(nav, 'languages', {languages_json});

    const uaData = {{
        ...spoof,
        getHighEntropyValues: async (hints) => {{
            const result = {{}};
            for (const k of hints) {{
                if (k in spoof) result[k] = spoof[k];
            }}
            return result;
        }},
        toJSON: () => spoof
    }};
    Object.defineProperty(nav, 'userAgentData', {{ get: () => uaData }});

    const spoofWebGL = (proto) => {{
        const orig = proto.getParameter;
        proto.getParameter = function (p) {{
            if (p === 37445) return '{webgl_vendor}';
            if (p === 37446) return '{webgl_renderer}';
            return orig.call(this, p);
        }};
    }};
    if ({win_ref}.WebGLRenderingContext)
        spoofWebGL({win_ref}.WebGLRenderingContext.prototype);
    if ({win_ref}.WebGL2RenderingContext)
        spoofWebGL({win_ref}.WebGL2RenderingContext.prototype);

    try {{
        const orig = Intl.DateTimeFormat.prototype.resolvedOptions;
        Intl.DateTimeFormat.prototype.resolvedOptions = function () {{
            const o = orig.call(this);
            o.timeZone = '{timezone}';
            return o;
        }};
    }} catch (_e) {{}}
}})(); 