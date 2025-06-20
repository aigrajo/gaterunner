from .geolocation import GeolocationGate
from .language import LanguageGate
from .referrer import ReferrerGate
from .useragent import UserAgentGate

# List of all gates to be run
ALL_GATES = [
    GeolocationGate(),
    ReferrerGate(),
    UserAgentGate(),
    LanguageGate(),
]