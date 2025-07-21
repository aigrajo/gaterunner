/**
 * timezone_spoof.js - Comprehensive timezone spoofing with dynamic historical date support
 * 
 * Handles CreepJS detection methods by calculating accurate timezone offsets
 * for any date, including historical ones (e.g., year 1113).
 */

(() => {
  'use strict';
  
  const targetTimezone = '__TIMEZONE__';
  
  if (targetTimezone === 'UTC' || !targetTimezone) {
    // No spoofing needed for UTC or if no timezone specified
    return;
  }
  
  console.log(`[TIMEZONE] Spoofing timezone to: ${targetTimezone} (with dynamic historical date support)`);
  
  // ─────────────────────────────────────────────────────────────────
  // 1. Override Intl.DateTimeFormat APIs
  // ─────────────────────────────────────────────────────────────────
  
  const originalResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
  Intl.DateTimeFormat.prototype.resolvedOptions = function() {
    const result = originalResolvedOptions.call(this);
    result.timeZone = targetTimezone;
    return result;
  };
  
  // Override other Intl constructors that have resolvedOptions
  const intlConstructors = ['Collator', 'DisplayNames', 'ListFormat', 'NumberFormat', 'PluralRules', 'RelativeTimeFormat'];
  
  intlConstructors.forEach(constructor => {
    if (typeof Intl[constructor] !== 'undefined' && Intl[constructor].prototype.resolvedOptions) {
      const originalMethod = Intl[constructor].prototype.resolvedOptions;
      Intl[constructor].prototype.resolvedOptions = function() {
        const result = originalMethod.call(this);
        // Only override timeZone if it exists in the result
        if ('timeZone' in result) {
          result.timeZone = targetTimezone;
        }
        return result;
      };
    }
  });
  
  // ─────────────────────────────────────────────────────────────────
  // 2. Dynamic timezone offset calculation for any date
  // ─────────────────────────────────────────────────────────────────
  
  function calculateTimezoneOffset(date, timezone) {
    try {
      // Get UTC time for this specific date
      const utcTime = Date.UTC(
        date.getFullYear(),
        date.getMonth(),
        date.getDate(),
        date.getHours(),
        date.getMinutes(),
        date.getSeconds(),
        date.getMilliseconds()
      );
      
      // Create a temporary date in the target timezone for the same moment
      const tempDate = new Date(utcTime);
      
      // Use Intl.DateTimeFormat to get how this date appears in the target timezone
      const targetFormatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: timezone,
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
      
      // Calculate what the local time would be in the target timezone
      const targetLocalTime = Date.UTC(targetYear, targetMonth, targetDay, targetHour, targetMinute, targetSecond);
      
      // The offset is the difference between UTC time and what the local time shows
      const offsetMs = utcTime - targetLocalTime;
      const offsetMinutes = Math.round(offsetMs / 60000);
      
      return offsetMinutes;
    } catch (e) {
      console.warn('[TIMEZONE] Failed to calculate offset for date', date, 'in timezone', timezone, e);
      return 0; // Fallback to UTC offset
    }
  }
  
  // ─────────────────────────────────────────────────────────────────
  // 3. Override Date.prototype.getTimezoneOffset with dynamic calculation
  // ─────────────────────────────────────────────────────────────────
  
  const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
  Date.prototype.getTimezoneOffset = function() {
    // Calculate the correct offset for THIS specific date (including historical dates)
    return calculateTimezoneOffset(this, targetTimezone);
  };
  
  // ─────────────────────────────────────────────────────────────────
  // 4. Override Date toString methods to show correct timezone
  // ─────────────────────────────────────────────────────────────────
  
  const originalToString = Date.prototype.toString;
  Date.prototype.toString = function() {
    try {
      // Format this specific date in target timezone
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
    // If no options provided, add our timezone
    if (!options) {
      options = { timeZone: targetTimezone };
    } else if (typeof options === 'object' && !options.timeZone) {
      options = { ...options, timeZone: targetTimezone };
    }
    
    return originalToLocaleString.call(this, locales, options);
  };
  
  // ─────────────────────────────────────────────────────────────────
  // 5. Override Temporal API if available (future-proofing)
  // ─────────────────────────────────────────────────────────────────
  
  if (typeof Temporal !== 'undefined' && Temporal.Now) {
    const originalTimeZone = Temporal.Now.timeZone;
    Temporal.Now.timeZone = function() {
      return new Temporal.TimeZone(targetTimezone);
    };
  }
  
  // ─────────────────────────────────────────────────────────────────
  // 6. Additional CreepJS-specific protections
  // ─────────────────────────────────────────────────────────────────
  
  // Override Date constructor to ensure consistent timezone handling
  const OriginalDate = Date;
  window.Date = function Date(...args) {
    const date = args.length === 0 ? new OriginalDate() : new OriginalDate(...args);
    return date;
  };
  
  // Preserve all Date static methods and prototype
  Object.setPrototypeOf(window.Date, OriginalDate);
  Object.setPrototypeOf(window.Date.prototype, OriginalDate.prototype);
  window.Date.prototype.constructor = window.Date;
  
  // Copy all static methods
  ['now', 'parse', 'UTC'].forEach(method => {
    window.Date[method] = OriginalDate[method];
  });
  
  console.log(`[TIMEZONE] Dynamic timezone spoofing applied successfully to: ${targetTimezone}`);
  
})(); 