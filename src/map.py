import csv

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

RESOURCE_DIRS = {
    'image': 'images',
    'script': 'scripts',
    'stylesheet': 'stylesheets',
    'font': 'fonts',
    'media': 'media',
    'document': 'html',
}

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