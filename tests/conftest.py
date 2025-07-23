import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import tempfile
import json

from gaterunner.browser import Config


@pytest.fixture
def mock_context():
    """Mock Playwright browser context."""
    context = AsyncMock()
    context.route = AsyncMock()
    context.on = Mock()
    context.add_init_script = AsyncMock()
    return context


@pytest.fixture
def mock_page():
    """Mock Playwright page."""
    page = AsyncMock()
    page.on = Mock()
    page.goto = AsyncMock()
    page.evaluate = AsyncMock()
    return page


@pytest.fixture
def mock_args():
    """Mock CLI arguments with valid values."""
    args = Mock()
    args.timeout = "30"
    args.proxy = None
    args.country = None  # Set to None to avoid validation errors
    args.lang = "en-US"
    args.user_agent = None
    args.workers = 1
    args.engine = "playwright"
    args.headless = True
    return args


@pytest.fixture
def valid_country_geo():
    """Mock COUNTRY_GEO with valid country data."""
    country_data = {
        "US": {
            "latitude": 45.70562800215178,
            "longitude": -112.5994359115045,
            "accuracy": 100
        },
        "CA": {
            "latitude": 61.46907614534896,
            "longitude": -98.14238137209708,
            "accuracy": 100
        },
        "GB": {
            "latitude": 54.75844,
            "longitude": -2.69531,
            "accuracy": 100
        }
    }
    
    with patch('gaterunner.gates.geolocation.COUNTRY_GEO', country_data):
        yield country_data


@pytest.fixture
def sample_user_agents():
    """Sample user agent data using real categories from user-agents.json."""
    return {
        "Windows;;Chrome": [
            {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "browser": "Chrome",
                "browserVersion": "131.0.0.0",
                "os": "Windows",
                "osVersion": "10"
            },
            {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                "browser": "Chrome", 
                "browserVersion": "130.0.0.0",
                "os": "Windows",
                "osVersion": "10"
            }
        ],
        "Mac OS;;Chrome": [
            {
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "browser": "Chrome",
                "browserVersion": "131.0.0.0", 
                "os": "Mac OS",
                "osVersion": "10.15.7"
            }
        ]
    }


@pytest.fixture 
def sample_country_geo():
    """Sample country geolocation data using real country codes."""
    return {
        "US": {
            "latitude": 45.70562800215178,
            "longitude": -112.5994359115045,
            "accuracy": 100
        },
        "CA": {
            "latitude": 61.46907614534896,
            "longitude": -98.14238137209708,
            "accuracy": 100
        },
        "GB": {
            "latitude": 54.75844,
            "longitude": -2.69531,
            "accuracy": 100
        }
    }


@pytest.fixture
def sample_js_templates_dir():
    """Create temporary directory with JS template files that tests expect."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create all the JS template files that tests expect
        js_files = {
            "spoof_useragent.js": """
            // UserAgent spoofing template
            Object.defineProperty(__NAV_REF__, 'userAgent', {
                get: () => '__USER_AGENT__',
                configurable: true
            });
            Object.defineProperty(__NAV_REF__, 'appVersion', {
                get: () => '__APP_VERSION__',
                configurable: true  
            });
            Object.defineProperty(__NAV_REF__, 'platform', {
                get: () => '__PLATFORM__',
                configurable: true  
            });
            """,
            
            "worker_spoof_template.js": """
            // Worker spoofing template
            const hardwareConcurrency = __HARDWARE_CONCURRENCY__;
            const deviceMemory = __DEVICE_MEMORY__;
            const timeout = __TIMEOUT__;
            const userAgent = '__USER_AGENT__';
            const platform = '__PLATFORM__';
            (function() {
                const originalWorker = window.Worker;
                window.Worker = function(url, options) {
                    return new originalWorker(url, options);
                };
                window.Worker.prototype = originalWorker.prototype;
            })();
            """,
            
            "webgl_patch.js": """
            // WebGL spoofing template  
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return '__WEBGL_VENDOR__';
                if (parameter === 37446) return '__WEBGL_RENDERER__';
                return getParameter.call(this, parameter);
            };
            """,
            
            "timezone_spoof.js": """
            // Timezone spoofing template
            const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() {
                return __TIMEZONE_OFFSET__;
            };
            """,
            
            "test_template.js": """
            // Test template  
            console.log('Test: __TEST_VAR__');
            """,
            
            "complex_template.js": """
            // Complex template
            const config = {
                value: __NUMERIC_VAR__,
                text: '__TEXT_VAR__',
                flag: __BOOLEAN_VAR__
            };
            """
        }
        
        for filename, content in js_files.items():
            (temp_path / filename).write_text(content)
            
        yield temp_path


@pytest.fixture
def basic_config():
    """Basic configuration object for testing."""
    config = Config()
    config.timeout = 30000
    config.engine = "playwright"
    config.headless = True
    return config


@pytest.fixture
def gate():
    """Real UserAgentGate instance for integration tests."""
    from gaterunner.gates.useragent import UserAgentGate
    return UserAgentGate()


@pytest.fixture
def manager():
    """Mock SpoofingManager with basic setup."""
    from gaterunner.spoof_manager import SpoofingManager
    manager = Mock(spec=SpoofingManager)
    manager.gates = {}
    manager.config = Mock()
    manager.config.engine = "playwright"
    return manager


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_template_loader():
    """Mock template loader for testing."""
    from gaterunner.utils import TemplateLoader
    loader = Mock(spec=TemplateLoader)
    loader.load_and_render_template = Mock(return_value="rendered_template")
    return loader 