'''
utils.py

Helper functions
'''

import csv
import json
import random
from typing import Union

from shapely import wkt
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
from pyproj import Geod

# ───────────────────────── types ──────────────────────────

CountryGeo = dict[str, Union[float, int, BaseGeometry]]
UserAgentEntry = dict[str, str]

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


def choose_ua(key: str) -> str:
    """Randomly choose a User-Agent string from a JSON file category.

    @param key (str): Category key (e.g. 'desktop', 'mobile') from user-agents.json.

    @return (str): A random User-Agent string.
    @raise ValueError: If the category key is missing or empty.
    """
    with open('src/data/user-agents.json', newline='') as jsonfile:
        ua_data: dict[str, list[UserAgentEntry]] = json.load(jsonfile)

    if key not in ua_data or not ua_data[key]:
        raise ValueError(f"No agents found in category: {key}")

    ua_obj = random.choice(ua_data[key])
    return ua_obj["userAgent"]


def main() -> None:
    """Test function to print jittered geolocation for US.

    @return None
    """
    geotest = jitter_country_location('US')
    print(geotest)


# ───────────────────────── constants ──────────────────────────

RESOURCE_DIRS: dict[str, str] = {
    'image': 'images',
    'script': 'scripts',
    'stylesheet': 'stylesheets',
    'font': 'fonts',
    'media': 'media',
    'document': 'html',
}

tag_attr_map: dict[str, list[str]] = {
    'img': ['src', 'srcset'],
    'script': ['src'],
    'link': ['href'],
    'iframe': ['src'],
    'audio': ['src'],
    'video': ['src', 'poster'],
    'source': ['src', 'srcset'],
    'embed': ['src'],
    'object': ['data'],
}

if __name__ == '__main__':
    main()
