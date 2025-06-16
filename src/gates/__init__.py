from .geolocation import GeolocationGate
from .referrer import ReferrerGate

ALL_GATES = [
    GeolocationGate(),
    ReferrerGate()
]