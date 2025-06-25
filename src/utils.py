import csv
import json
import random
from shapely import wkt
from shapely.geometry import Point, Polygon, MultiPolygon
from pyproj import Geod

# Write geo data to dictionary
COUNTRY_GEO = {}
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

geod = Geod(ellps="WGS84")

def random_point_polygon(polygon, max_tries=100):
    minx, miny, maxx, maxy = polygon.bounds
    for _ in range(max_tries):
        x, y = random.uniform(minx, maxx), random.uniform(miny, maxy)
        p = Point(x, y)
        if polygon.contains(p):
            return p
    raise RuntimeError('Could not find a random point in the polygon')

def random_point_multipolygon(multipolygon, max_tries=100):
    # Choose a polygon at random, weighted by area
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

def jitter_country_location(cc):
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


# Randomly select User-Agent string based off of category
def choose_ua(key):

    with open('src/data/user-agents.json', newline='') as jsonfile:
        ua_data = json.load(jsonfile)

    if key not in ua_data or not ua_data[key]:
        raise ValueError(f"No agents found in category: {key}")

    ua_obj = random.choice(ua_data[key])
    return ua_obj["userAgent"]


# For organized file saving
RESOURCE_DIRS = {
    'image': 'images',
    'script': 'scripts',
    'stylesheet': 'stylesheets',
    'font': 'fonts',
    'media': 'media',
    'document': 'html',
}

# For html rewriting
tag_attr_map = {
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


# Debug (Change path to country_geo.csv)
def main():
    geotest = jitter_country_location('US')
    print(geotest)

if __name__ == '__main__':
    main()