"""
timezone.py - Timezone spoofing gate

Handles dynamic timezone selection based on country code, replacing hardcoded UTC
with realistic timezones that match the user's geographic selection.
"""

import random
from pathlib import Path
from .base import GateBase


class TimezoneGate(GateBase):
    name = "TimezoneGate"
    
    def __init__(self):
        self._timezones_cache = None
    
    def _load_timezones(self):
        """Load timezone mappings from IANA zone.tab file (cached)"""
        if self._timezones_cache is None:
            zone_tab_file = Path(__file__).resolve().parent.parent / "data" / "zone.tab"
            timezones_by_country = {}
            
            with open(zone_tab_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse tab-delimited format: country_code \t coordinates \t timezone \t comments
                    parts = line.split('\t', 3)  # Split into max 4 parts
                    if len(parts) < 3:
                        continue
                    
                    country_code = parts[0].upper()
                    timezone = parts[2]
                    
                    if country_code not in timezones_by_country:
                        timezones_by_country[country_code] = []
                    
                    timezones_by_country[country_code].append(timezone)
            
            self._timezones_cache = timezones_by_country
            print(f"[{self.name}] Loaded timezones for {len(timezones_by_country)} countries from zone.tab")
        
        return self._timezones_cache
    
    def select_timezone_for_country(self, country_code):
        """
        Randomly pick timezone from country's pool.
        
        @param country_code: 2-letter country code (e.g., "US", "GB", "DE")
        @return: IANA timezone string (e.g., "America/New_York")
        """
        if not country_code:
            return "UTC"
            
        timezones_by_country = self._load_timezones()
        country_code = country_code.upper()
        
        if country_code in timezones_by_country:
            timezones = timezones_by_country[country_code]
            selected = random.choice(timezones)
            print(f"[{self.name}] Selected timezone for {country_code}: {selected} (from {len(timezones)} options)")
            return selected
        else:
            print(f"[{self.name}] No timezones found for {country_code}, using UTC")
            return "UTC"
    
    async def handle(self, page, context, **kwargs):
        """
        Timezone gate doesn't need special page/context handling.
        """
        pass
    
    async def get_headers(self, **kwargs):
        """
        Timezone gate doesn't add HTTP headers.
        """
        return {}
    
    def get_js_patches(self, engine="chromium", country=None, **kwargs):
        """
        Return JavaScript patches for timezone spoofing.
        Only apply if we have a country (otherwise keep system timezone).
        """
        if country:
            return ["timezone_spoof.js"]
        return []
    
    def get_js_template_vars(self, country=None, **kwargs):
        """
        Return template variables for timezone spoofing.
        
        @param country: Country code from GeolocationGate or --country flag
        @return: Dict with __TIMEZONE__ variable
        """
        selected_timezone = self.select_timezone_for_country(country)
        
        return {
            "__TIMEZONE__": selected_timezone,
            "timezone_id": selected_timezone,  # For compatibility with existing code
        } 