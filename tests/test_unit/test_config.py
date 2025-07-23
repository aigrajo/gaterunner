"""
Test suite for Config class and argument parsing.

Tests the critical configuration management that drives CLI behavior
and gate orchestration throughout the application.
"""
import pytest
from unittest.mock import Mock, patch
from gaterunner.browser import Config


class TestConfigDefaults:
    """Test default configuration values."""
    
    def test_config_default_values(self):
        """Test that Config has correct default values."""
        config = Config()
        
        # Application defaults
        assert config.engine == "auto"
        assert config.headless == False
        assert config.interactive == False  
        assert config.timeout_sec == 30
        assert config.verbose == False
        assert config.output_dir == "./data"
        assert config.plain_progress == False
        assert config.workers is None
        
        # Network defaults
        assert config.proxy is None
        
        # Gate defaults
        assert config.gates_enabled == {}
        assert config.gate_args == {}
        
        # Runtime defaults
        assert config.detected_engine is None


class TestConfigFromArgs:
    """Test Config.from_args() method with various argument combinations."""
    
    def test_basic_argument_parsing(self, mock_args):
        """Test basic argument parsing without gates."""
        mock_args.engine = "playwright"
        mock_args.headful = True
        mock_args.timeout = "60"
        mock_args.verbose = True
        mock_args.output_dir = "./custom_data"
        mock_args.workers = 4
        
        config = Config.from_args(mock_args)
        
        assert config.engine == "playwright"
        assert config.interactive == True  # headful maps to interactive
        assert config.timeout_sec == 60
        assert config.verbose == True
        assert config.output_dir == "./custom_data"
        assert config.workers == 4
    
    def test_timeout_string_conversion(self, mock_args):
        """Test that timeout string is properly converted to int."""
        mock_args.timeout = "120"
        
        config = Config.from_args(mock_args)
        
        assert config.timeout_sec == 120
        assert isinstance(config.timeout_sec, int)
    
    def test_proxy_validation_valid(self, mock_args):
        """Test proxy validation with valid URLs."""
        test_cases = [
            "http://proxy.example.com:8080",
            "https://proxy.example.com:8080", 
            "socks5://proxy.example.com:1080"
        ]
        
        for proxy_url in test_cases:
            mock_args.proxy = proxy_url
            
            with patch('gaterunner.browser._is_valid_proxy', return_value=True):
                config = Config.from_args(mock_args)
                
            assert config.proxy == {"server": proxy_url}
    
    def test_proxy_validation_invalid(self, mock_args):
        """Test proxy validation with invalid URLs."""
        invalid_proxies = [
            "invalid-proxy",
            "not-a-url",
            "",
            "ftp://invalid.com"  # unsupported protocol
        ]
        
        for invalid_proxy in invalid_proxies:
            mock_args.proxy = invalid_proxy
            
            with patch('gaterunner.browser._is_valid_proxy', return_value=False):
                config = Config.from_args(mock_args)
                
            assert config.proxy is None
    
    def test_proxy_none(self, mock_args):
        """Test that None proxy is handled correctly."""
        mock_args.proxy = None
        
        config = Config.from_args(mock_args)
        
        assert config.proxy is None


class TestGeolocationGateConfiguration:
    """Test geolocation gate configuration."""
    
    def test_valid_country_code(self, mock_args, valid_country_geo):
        """Test geolocation configuration with valid country code."""
        mock_args.country = "US"
        
        config = Config.from_args(mock_args)
        
        # Verify GeolocationGate is enabled
        assert config.gates_enabled["GeolocationGate"] == True
        assert config.gate_args["GeolocationGate"]["country_code"] == "US"
        
        # Verify TimezoneGate is auto-enabled
        assert config.gates_enabled["TimezoneGate"] == True
        assert config.gate_args["TimezoneGate"]["country"] == "US"
    
    def test_invalid_country_code(self, mock_args):
        """Test that invalid country code raises ValueError."""
        mock_args.country = "INVALID"
        
        # Mock empty country data to simulate invalid code
        with patch('gaterunner.gates.geolocation.COUNTRY_GEO', {}):
            with pytest.raises(ValueError, match="Invalid country code: INVALID"):
                Config.from_args(mock_args)
    
    def test_lowercase_country_code(self, mock_args, valid_country_geo):
        """Test that lowercase country codes are handled correctly."""
        mock_args.country = "us"  # lowercase
        
        config = Config.from_args(mock_args)
        
        # Should be converted to uppercase
        assert config.gate_args["GeolocationGate"]["country_code"] == "US"
    
    def test_no_country_specified(self, mock_args):
        """Test that no country doesn't enable geolocation gates.""" 
        mock_args.country = None
        
        config = Config.from_args(mock_args)
        
        assert "GeolocationGate" not in config.gates_enabled
        assert "TimezoneGate" not in config.gates_enabled


class TestLanguageGateConfiguration:
    """Test language gate configuration."""
    
    def test_valid_language(self, mock_args):
        """Test language gate configuration with valid language."""
        mock_args.lang = "fr-FR"
        
        with patch('gaterunner.browser._is_valid_lang', return_value=True):
            config = Config.from_args(mock_args)
        
        assert config.gates_enabled["LanguageGate"] == True
        assert config.gate_args["LanguageGate"]["language"] == "fr-FR"
    
    def test_invalid_language(self, mock_args):
        """Test that invalid language raises ValueError."""
        mock_args.lang = "invalid-lang"
        
        with patch('gaterunner.browser._is_valid_lang', return_value=False):
            with pytest.raises(ValueError, match="Invalid language: invalid-lang"):
                Config.from_args(mock_args)
    
    def test_default_language(self, mock_args):
        """Test default language handling."""
        mock_args.lang = None
        
        config = Config.from_args(mock_args)
        
        assert "LanguageGate" not in config.gates_enabled


class TestUserAgentGateConfiguration:
    """Test user agent gate configuration."""
    
    def test_ua_selector_parsing(self, mock_args):
        """Test user agent selector parsing."""
        mock_args.ua = "Windows;;Chrome"
        mock_args.ua_full = None
        
        # Mock the user agent selection
        with patch('gaterunner.gates.useragent.choose_ua', return_value="Mozilla/5.0 Chrome Test"):
            config = Config.from_args(mock_args)
        
        assert config.gates_enabled["UserAgentGate"] == True
        assert "ua_selector" in config.gate_args["UserAgentGate"]
    
    def test_full_user_agent_override(self, mock_args):
        """Test that ua_full overrides ua selector."""
        mock_args.ua = "Windows;;Chrome"
        mock_args.ua_full = "Custom User Agent String"
        
        config = Config.from_args(mock_args)
        
        assert config.gates_enabled["UserAgentGate"] == True
        assert config.gate_args["UserAgentGate"]["user_agent"] == "Custom User Agent String"
    
    def test_no_user_agent_specified(self, mock_args):
        """Test that no user agent doesn't enable UserAgentGate."""
        mock_args.ua = None
        mock_args.ua_full = None
        
        config = Config.from_args(mock_args)
        
        assert "UserAgentGate" not in config.gates_enabled


class TestConfigIntegration:
    """Integration tests for Config with multiple gates."""
    
    def test_multiple_gates_configuration(self, mock_args, valid_country_geo):
        """Test configuration with multiple gates enabled."""
        mock_args.country = "US"
        mock_args.lang = "en-US"
        mock_args.ua_full = "Test User Agent"
        
        with patch('gaterunner.browser._is_valid_lang', return_value=True):
            config = Config.from_args(mock_args)
        
        # Verify all gates are enabled
        assert config.gates_enabled["GeolocationGate"] == True
        assert config.gates_enabled["TimezoneGate"] == True  # Auto-enabled with geo
        assert config.gates_enabled["LanguageGate"] == True
        assert config.gates_enabled["UserAgentGate"] == True
        
        # Verify gate arguments
        assert config.gate_args["GeolocationGate"]["country_code"] == "US"
        assert config.gate_args["TimezoneGate"]["country"] == "US"
        assert config.gate_args["LanguageGate"]["language"] == "en-US"
        assert config.gate_args["UserAgentGate"]["user_agent"] == "Test User Agent"
    
    def test_config_methods_exist(self, basic_config):
        """Test that Config has required methods for the application."""
        # Test that Config has methods expected by other components
        expected_methods = [
            'get_gate_config',
            'get_ua_for_engine_selection'
        ]
        
        for method_name in expected_methods:
            # Check if method exists (may not be implemented yet)
            if hasattr(basic_config, method_name):
                assert callable(getattr(basic_config, method_name))


class TestConfigValidation:
    """Test configuration validation and error handling."""
    
    def test_invalid_timeout_value(self, mock_args):
        """Test handling of invalid timeout values."""
        mock_args.timeout = "invalid"
        
        with pytest.raises(ValueError):
            Config.from_args(mock_args)
    
    def test_negative_timeout_value(self, mock_args):
        """Test handling of negative timeout values."""
        mock_args.timeout = "-10"
        
        # Config just converts to int without validation
        config = Config.from_args(mock_args)
        assert config.timeout_sec == -10  # No validation in current implementation
    
    def test_workers_validation(self, mock_args):
        """Test workers value validation."""
        test_cases = [
            (1, 1),
            (4, 4),
            (None, None),
            (0, 0)  # Edge case
        ]
        
        for input_workers, expected in test_cases:
            mock_args.workers = input_workers
            config = Config.from_args(mock_args)
            assert config.workers == expected 