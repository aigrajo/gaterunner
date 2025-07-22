import csv
import random
from typing import Union, Dict

from shapely import wkt
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
from pyproj import Geod

from .base import GateBase
from urllib.parse import urlparse

# ───────────────────────── types ──────────────────────────

CountryGeo = dict[str, Union[float, int, BaseGeometry]]

# ───────────────────────── data ──────────────────────────

COUNTRY_GEO: dict[str, CountryGeo] = {}

with open('src/data/country_geo.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)
    for row in reader:
        COUNTRY_GEO[row[0]] = {
            'latitude': float(row[1]),
            'longitude': float(row[2]),
            'accuracy': int(row[3]),
            'polygon_wkt': wkt.loads(row[4]),
        }

geod: Geod = Geod(ellps="WGS84")

# ───────────────────────── functions ──────────────────────────

def random_point_polygon(polygon: Polygon, max_tries: int = 100) -> Point:
    """Return a random point contained within a polygon.

    @param polygon (shapely.Polygon): The polygon to sample within.
    @param max_tries (int): Number of attempts before giving up.

    @return (shapely.geometry.Point): A random point inside the polygon.
    @raise RuntimeError: If no valid point found after max_tries.
    """
    minx, miny, maxx, maxy = polygon.bounds
    for _ in range(max_tries):
        x, y = random.uniform(minx, maxx), random.uniform(miny, maxy)
        p = Point(x, y)
        if polygon.contains(p):
            return p
    raise RuntimeError('Could not find a random point in the polygon')


def random_point_multipolygon(multipolygon: MultiPolygon, max_tries: int = 100) -> Point:
    """Return a random point from a multipolygon, weighted by area.

    @param multipolygon (shapely.MultiPolygon): The multipolygon to sample from.
    @param max_tries (int): Total attempts across all polygons.

    @return (shapely.geometry.Point): A random point within one of the sub-polygons.
    @raise RuntimeError: If no valid point found after max_tries.
    """
    polygons = list(multipolygon.geoms)
    areas = [poly.area for poly in polygons]
    total_area = sum(areas)
    weights = [area / total_area for area in areas]
    for _ in range(max_tries):
        poly = random.choices(polygons, weights=weights, k=1)[0]
        try:
            return random_point_polygon(poly, max_tries=10)
        except RuntimeError:
            continue
    raise RuntimeError('Could not find a random point in the multipolygon')


def jitter_country_location(cc: str) -> dict[str, float]:
    """Return a random geolocation within the polygon of a given country.

    @param cc (str): Country code used to look up polygon data.

    @return (dict): A dictionary with random 'latitude', 'longitude', and 'accuracy'.
    @raise ValueError: If the geometry is not Polygon or MultiPolygon.
    """
    geom = COUNTRY_GEO[cc].get('polygon_wkt')
    if isinstance(geom, Polygon):
        point = random_point_polygon(geom)
    elif isinstance(geom, MultiPolygon):
        point = random_point_multipolygon(geom)
    else:
        raise ValueError(f"Unknown geometry type for country {cc}")
    accuracy = round(random.uniform(100, 200))
    geo = {
        'latitude': point.y,
        'longitude': point.x,
        'accuracy': accuracy,
    }
    return geo

# Sends browser geolocation data
class GeolocationGate(GateBase):
    name = 'GeolocationGate'

    async def handle(self, page, context, geolocation=None, **kwargs):
        """
        Set up geolocation spoofing via JavaScript API replacement.
        No longer grants browser permissions - uses JS spoofing to avoid TDS detection.
        """
        if geolocation:
            lat = geolocation['latitude']
            lng = geolocation['longitude'] 
            acc = geolocation['accuracy']
            print(f"[GATE] Will spoof geolocation to: {lat}, {lng} (±{acc}m)")
            return True
        return False

    async def get_headers(self, **kwargs):
        """
        Geolocation gate doesn't add HTTP headers.
        """
        return {}

    def get_js_patches(self, engine="chromium", geolocation=None, browser_engine=None, **kwargs):
        """
        Return JavaScript patches for geolocation API spoofing.
        """
        # Disable patches for patchright and camoufox (they have built-in stealth)
        if browser_engine in ["patchright", "camoufox"]:
            return []
        
        # Apply geolocation spoofing if coordinates are provided
        if geolocation:
            return ["geolocation_spoof.js"]
        return []

    def get_js_template_vars(self, geolocation=None, **kwargs):
        """
        Return template variables for geolocation JavaScript spoofing.
        
        @param geolocation: Dict with latitude, longitude, accuracy from jitter_country_location()
        @return: Dict of template variables for geolocation_spoof.js
        """
        if not geolocation:
            return {}
        
        return {
            "__LATITUDE__": geolocation['latitude'],
            "__LONGITUDE__": geolocation['longitude'], 
            "__ACCURACY__": geolocation['accuracy'],
        }