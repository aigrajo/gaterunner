import csv
import json
import random

# Write geo data to dictionary
COUNTRY_GEO = {}
with open('src/country_geo.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)
    for row in reader:
        COUNTRY_GEO[row[0]] = {
            'latitude': float(row[1]),
            'longitude': float(row[2]),
            'accuracy': int(row[3]),
        }

# Randomly select User-Agent string based off of category
def choose_ua(key):

    with open('src/user-agents.json', newline='') as jsonfile:
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
    print(COUNTRY_GEO)

if __name__ == '__main__':
    main()