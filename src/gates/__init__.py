from .geolocation import GeolocationGate
from .language import LanguageGate
from .referrer import ReferrerGate
from .useragent import UserAgentGate
from .network import NetworkGate
from .webgl import WebGLGate
from .stealth import StealthGate
from .timezone import TimezoneGate

# List of all gates to be run
ALL_GATES = [
    GeolocationGate(),
    ReferrerGate(),
    UserAgentGate(),
    LanguageGate(),
    NetworkGate(),
    WebGLGate(),
    StealthGate(),
    TimezoneGate(),
]