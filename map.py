COUNTRY_GEO = {
    "US": {"latitude": 37.0902, "longitude": -95.7129, "accuracy": 100},      # USA
    "UK": {"latitude": 51.509865, "longitude": -0.118092, "accuracy": 100},   # UK
    "FR": {"latitude": 48.864716, "longitude": 2.349014, "accuracy": 100},    # France
    "DE": {"latitude": 51.1657, "longitude": 10.4515, "accuracy": 100},       # Germany
    "JP": {"latitude": 35.652832, "longitude": 139.839478, "accuracy": 100},  # Japan
    # Add more as needed
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