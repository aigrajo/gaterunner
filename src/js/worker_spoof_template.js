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
    // Fix appVersion leak - this is what CreepJS collects for the second ua entry
    def(nav, 'appVersion', '__USER_AGENT__'.replace('Mozilla/', ''));
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

    // API surface normalization for CreepJS consistency
    try {
        // Ensure consistent API availability between main thread and workers
        const consistentAPIs = [
            'doNotTrack', 'getGamepads', 'requestMIDIAccess', 'geolocation'
        ];
        
        consistentAPIs.forEach(api => {
            if (typeof nav[api] === 'undefined') {
                // Add missing APIs that should be consistent across contexts
                switch (api) {
                    case 'doNotTrack':
                        def(nav, 'doNotTrack', 'unspecified');
                        break;
                    case 'getGamepads':
                        def(nav, 'getGamepads', () => []);
                        break;
                    case 'requestMIDIAccess':
                        def(nav, 'requestMIDIAccess', () => 
                            Promise.reject(new DOMException('', 'NotSupportedError')));
                        break;
                    case 'geolocation':
                        // Geolocation API consistency - workers should have it too
                        if (!nav.geolocation) {
                            def(nav, 'geolocation', {
                                getCurrentPosition: () => {},
                                watchPosition: () => 1,
                                clearWatch: () => {}
                            });
                        }
                        break;
                }
            }
        });
        
        // Ensure consistent window/global object properties in workers
        if (typeof __WIN_REF__ !== 'undefined' && __WIN_REF__) {
            // Make sure workers have consistent global properties  
            const globalAPIs = ['openDatabase'];
            globalAPIs.forEach(api => {
                if (typeof __WIN_REF__[api] === 'undefined') {
                    try {
                        __WIN_REF__[api] = undefined;
                    } catch (e) {
                        // Ignore if we can't set it
                    }
                }
            });
        }
    } catch (e) {
        // Silent error handling to avoid detection
    }

    // Enhanced timezone spoofing for worker consistency with main thread
    const targetTimezone = '__TIMEZONE__';
    
    // Basic Intl.DateTimeFormat spoofing (keep existing)
    try {
        const orig = Intl.DateTimeFormat.prototype.resolvedOptions;
        Intl.DateTimeFormat.prototype.resolvedOptions = function () {
            const o = orig.call(this);
            o.timeZone = targetTimezone;
            return o;
        };
    } catch (_e) {}

    // Enhanced timezone spoofing for CreepJS consistency
    if (targetTimezone !== 'UTC' && targetTimezone) {
        try {
            // Override Date.prototype.getTimezoneOffset for accurate timezone offset
            const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() {
                try {
                    // Calculate timezone offset for this specific date
                    const utcTime = Date.UTC(
                        this.getFullYear(),
                        this.getMonth(),
                        this.getDate(),
                        this.getHours(),
                        this.getMinutes(),
                        this.getSeconds(),
                        this.getMilliseconds()
                    );
                    
                    const tempDate = new Date(utcTime);
                    const targetFormatter = new Intl.DateTimeFormat('en-CA', {
                        timeZone: targetTimezone,
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        hour12: false
                    });
                    
                    const targetParts = targetFormatter.formatToParts(tempDate);
                    const targetYear = parseInt(targetParts.find(p => p.type === 'year').value);
                    const targetMonth = parseInt(targetParts.find(p => p.type === 'month').value) - 1;
                    const targetDay = parseInt(targetParts.find(p => p.type === 'day').value);
                    const targetHour = parseInt(targetParts.find(p => p.type === 'hour').value);
                    const targetMinute = parseInt(targetParts.find(p => p.type === 'minute').value);
                    const targetSecond = parseInt(targetParts.find(p => p.type === 'second').value);
                    
                    const targetLocalTime = Date.UTC(targetYear, targetMonth, targetDay, targetHour, targetMinute, targetSecond);
                    const offsetMs = utcTime - targetLocalTime;
                    const offsetMinutes = Math.round(offsetMs / 60000);
                    
                    return offsetMinutes;
                } catch (e) {
                    return 0; // Fallback to UTC offset
                }
            };

            // Override Date toString methods for consistent timezone display
            const originalToString = Date.prototype.toString;
            Date.prototype.toString = function() {
                try {
                    const formatter = new Intl.DateTimeFormat('en-US', {
                        timeZone: targetTimezone,
                        weekday: 'short',
                        year: 'numeric',
                        month: 'short',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        timeZoneName: 'short',
                        hour12: false
                    });
                    return formatter.format(this);
                } catch (e) {
                    return originalToString.call(this);
                }
            };

            const originalToTimeString = Date.prototype.toTimeString;
            Date.prototype.toTimeString = function() {
                try {
                    const formatter = new Intl.DateTimeFormat('en-US', {
                        timeZone: targetTimezone,
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        timeZoneName: 'short',
                        hour12: false
                    });
                    return formatter.format(this);
                } catch (e) {
                    return originalToTimeString.call(this);
                }
            };

            const originalToLocaleString = Date.prototype.toLocaleString;
            Date.prototype.toLocaleString = function(locales, options) {
                if (!options) {
                    options = { timeZone: targetTimezone };
                } else if (typeof options === 'object' && !options.timeZone) {
                    options = { ...options, timeZone: targetTimezone };
                }
                return originalToLocaleString.call(this, locales, options);
            };

        } catch (_e) {
            // Silent error handling to avoid detection
        }
    }
})(); 