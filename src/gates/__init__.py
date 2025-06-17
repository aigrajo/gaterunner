from . import clienthints
from .geolocation import GeolocationGate
from .referrer import ReferrerGate
from .useragent import UserAgentGate

ALL_GATES = [
    GeolocationGate(),
    ReferrerGate(),
    UserAgentGate(),
]