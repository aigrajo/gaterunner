from . import clienthints
from .geolocation import GeolocationGate
from .referrer import ReferrerGate
from .useragent import UserAgentGate

# List of all gates to be ran
ALL_GATES = [
    GeolocationGate(),
    ReferrerGate(),
    UserAgentGate(),
]