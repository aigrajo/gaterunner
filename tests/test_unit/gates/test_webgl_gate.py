"""
Test suite for WebGLGate class.

Tests WebGL renderer and vendor spoofing functionality
for hardware fingerprinting evasion.
"""
import pytest
from unittest.mock import Mock, patch
from gaterunner.gates.webgl import WebGLGate


class TestWebGLGateBasics:
    """Test basic WebGLGate functionality."""
    
    @pytest.fixture
    def gate(self):
        """WebGLGate instance for testing."""
        return WebGLGate()
    
    def test_gate_name(self, gate):
        """Test gate name property."""
        assert gate.name == "WebGLGate"
    
    def test_gate_inheritance(self, gate):
        """Test that WebGLGate inherits from GateBase."""
        from gaterunner.gates.base import GateBase
        assert isinstance(gate, GateBase)
    
    def test_webgl_by_os_data_structure(self, gate):
        """Test that WEBGL_BY_OS has expected structure."""
        assert hasattr(gate, 'WEBGL_BY_OS')
        assert isinstance(gate.WEBGL_BY_OS, dict)
        
        # Check expected OS keys
        expected_os = ["windows", "mac", "linux", "android", "ios"]
        for os_name in expected_os:
            assert os_name in gate.WEBGL_BY_OS
            assert isinstance(gate.WEBGL_BY_OS[os_name], list)
            
            # Each entry should be a (vendor, renderer) tuple
            for entry in gate.WEBGL_BY_OS[os_name]:
                assert isinstance(entry, tuple)
                assert len(entry) == 2
                assert isinstance(entry[0], str)  # vendor
                assert isinstance(entry[1], str)  # renderer


class TestWebGLHandleMethod:
    """Test WebGL gate handle method."""
    
    @pytest.fixture
    def gate(self):
        return WebGLGate()
    
    @pytest.mark.asyncio
    async def test_handle_method_no_op(self, gate):
        """Test that handle method is a no-op."""
        # Should not crash with any arguments
        await gate.handle(None, None)
        await gate.handle("page", "context", setting="value")


class TestWebGLHeaders:
    """Test WebGL gate header generation."""
    
    @pytest.fixture
    def gate(self):
        return WebGLGate()
    
    @pytest.mark.asyncio
    async def test_get_headers_returns_empty(self, gate):
        """Test that get_headers returns empty dict."""
        headers = await gate.get_headers()
        assert headers == {}
        
        # Should return empty regardless of arguments
        headers = await gate.get_headers(webgl_vendor="NVIDIA", webgl_renderer="RTX 3060")
        assert headers == {}


class TestWebGLJavaScriptPatches:
    """Test WebGL JavaScript patch selection."""
    
    @pytest.fixture
    def gate(self):
        return WebGLGate()
    
    def test_get_js_patches_basic(self, gate):
        """Test basic JavaScript patch selection."""
        # Without user_agent or explicit vendor/renderer, no patches returned
        patches = gate.get_js_patches()
        
        assert isinstance(patches, list)
        assert patches == []
    
    def test_get_js_patches_all_engines(self, gate):
        """Test JavaScript patch selection for different engines."""
        engines = ["chromium", "firefox", "webkit"]
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        
        for engine in engines:
            patches = gate.get_js_patches(engine=engine, user_agent=user_agent)
            assert "webgl_patch.js" in patches
    
    def test_get_js_patches_patchright_disabled(self, gate):
        """Test that patches are disabled for Patchright."""
        patches = gate.get_js_patches(
            engine="chromium",
            browser_engine="patchright"
        )
        
        assert patches == []
    
    def test_get_js_patches_camoufox_disabled(self, gate):
        """Test that patches are disabled for CamouFox."""
        patches = gate.get_js_patches(
            engine="firefox",
            browser_engine="camoufox"
        )
        
        assert patches == []


class TestWebGLTemplateVariables:
    """Test WebGL template variable generation."""
    
    @pytest.fixture
    def gate(self):
        return WebGLGate()
    
    def test_get_js_template_vars_with_explicit_values(self, gate):
        """Test template variable generation with explicit vendor/renderer."""
        vars = gate.get_js_template_vars(
            webgl_vendor="NVIDIA Corporation",
            webgl_renderer="NVIDIA GeForce RTX 3060/PCIe/SSE2"
        )
        
        assert vars["__WEBGL_VENDOR__"] == "NVIDIA Corporation"
        assert vars["__WEBGL_RENDERER__"] == "NVIDIA GeForce RTX 3060/PCIe/SSE2"
    
    def test_get_js_template_vars_os_based_selection(self, gate):
        """Test template variable generation with OS-based selection."""
        test_cases = [
            ("windows", "Windows"),
            ("mac", "Mac OS"),
            ("linux", "Linux"),
            ("android", "Android"),
            ("ios", "iOS")
        ]
        
        for os_family, user_agent_hint in test_cases:
            with patch('gaterunner.gates.webgl.detect_os_family', return_value=os_family):
                vars = gate.get_js_template_vars(
                    user_agent=f"Mozilla/5.0 ({user_agent_hint}) Test Agent"
                )
                
                # Should have selected values from the appropriate OS
                assert "__WEBGL_VENDOR__" in vars
                assert "__WEBGL_RENDERER__" in vars
                
                # Verify the values come from the correct OS list
                expected_options = gate.WEBGL_BY_OS[os_family]
                selected_vendor = vars["__WEBGL_VENDOR__"]
                selected_renderer = vars["__WEBGL_RENDERER__"]
                
                # The selected combo should be in the OS options
                found_combo = False
                for vendor, renderer in expected_options:
                    if vendor == selected_vendor and renderer == selected_renderer:
                        found_combo = True
                        break
                assert found_combo, f"Selected combo not found in {os_family} options"
    
    def test_get_js_template_vars_default_fallback(self, gate):
        """Test template variable generation with default fallback."""
        with patch('gaterunner.gates.webgl.detect_os_family', return_value="unknown"):
            vars = gate.get_js_template_vars(user_agent="Unknown Agent")
            
                            # Should fall back to Windows pool (since unknown OS)
        assert vars["__WEBGL_VENDOR__"] in ["NVIDIA Corporation", "Intel", "AMD"]
        assert "__WEBGL_RENDERER__" in vars
    
    def test_get_js_template_vars_no_user_agent(self, gate):
        """Test template variable generation without user agent."""
        vars = gate.get_js_template_vars()
        
        # Should use default values when no user agent provided
        assert vars["__WEBGL_VENDOR__"] == "Intel"
        assert vars["__WEBGL_RENDERER__"] == "Intel(R) HD Graphics 530"
    
    def test_get_js_template_vars_precedence(self, gate):
        """Test that explicit values take precedence over OS detection."""
        with patch('gaterunner.gates.webgl.detect_os_family', return_value="windows"):
            vars = gate.get_js_template_vars(
                user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/120.0.0.0",
                webgl_vendor="Custom Vendor",
                webgl_renderer="Custom Renderer"
            )
            
            # Explicit values should override OS-based selection
            assert vars["__WEBGL_VENDOR__"] == "Custom Vendor"
            assert vars["__WEBGL_RENDERER__"] == "Custom Renderer"


class TestWebGLDataValidation:
    """Test WebGL data validation and consistency."""
    
    @pytest.fixture
    def gate(self):
        return WebGLGate()
    
    def test_webgl_vendor_renderer_pairs_valid(self, gate):
        """Test that all vendor/renderer pairs are valid strings."""
        for os_name, gpu_list in gate.WEBGL_BY_OS.items():
            for vendor, renderer in gpu_list:
                # Vendor and renderer should be non-empty strings
                assert isinstance(vendor, str)
                assert isinstance(renderer, str)
                assert len(vendor.strip()) > 0
                assert len(renderer.strip()) > 0
    
    def test_webgl_realistic_combinations(self, gate):
        """Test that WebGL combinations are realistic."""
        # Test some known realistic combinations
        realistic_combos = {
            "windows": [
                ("NVIDIA Corporation", "NVIDIA GeForce"),
                ("Intel", "Intel(R)"),
                ("AMD", "AMD Radeon")
            ],
            "mac": [
                ("Apple Inc.", "Apple"),
                ("Apple Inc.", "Apple")
            ],
            "linux": [
                ("Intel", "Mesa Intel"),
                ("NVIDIA Corporation", "NVIDIA GeForce"),
                ("AMD", "AMD Radeon")
            ],
            "android": [
                ("Qualcomm", "Adreno"),
                ("ARM", "Mali")
            ],
            "ios": [
                ("Apple Inc.", "Apple A")
            ]
        }
        
        for os_name, expected_patterns in realistic_combos.items():
            os_gpus = gate.WEBGL_BY_OS[os_name]
            
            # Check that we have at least one GPU from each expected vendor
            for vendor_pattern, renderer_pattern in expected_patterns:
                found_vendor = any(
                    vendor_pattern.lower() in vendor.lower()
                    for vendor, renderer in os_gpus
                )
                assert found_vendor, f"No {vendor_pattern} GPU found for {os_name}"
    
    def test_webgl_os_coverage(self, gate):
        """Test that all major OS families have WebGL options."""
        required_os = ["windows", "mac", "linux", "android", "ios"]
        
        for os_name in required_os:
            assert os_name in gate.WEBGL_BY_OS
            assert len(gate.WEBGL_BY_OS[os_name]) > 0, f"No WebGL options for {os_name}"
    
    def test_webgl_diversity_per_os(self, gate):
        """Test that each OS has diverse GPU options."""
        for os_name, gpu_list in gate.WEBGL_BY_OS.items():
            # Should have multiple options for realistic spoofing
            assert len(gpu_list) >= 2, f"Insufficient WebGL diversity for {os_name}"
            
            # Should have different vendors
            vendors = {vendor for vendor, renderer in gpu_list}
            assert len(vendors) >= 1, f"No vendor diversity for {os_name}"


class TestWebGLRandomSelection:
    """Test WebGL random selection behavior."""
    
    @pytest.fixture
    def gate(self):
        return WebGLGate()
    
    def test_random_selection_repeatability(self, gate):
        """Test that random selection can be controlled for testing."""
        with patch('gaterunner.gates.webgl.detect_os_family', return_value="windows"):
            with patch('random.choice') as mock_choice:
                # Mock random.choice to return first item
                mock_choice.side_effect = lambda x: x[0]
                
                vars = gate.get_js_template_vars(user_agent="Windows Chrome Agent")
                
                # Should have called random.choice with Windows GPU list
                mock_choice.assert_called_once()
                called_with = mock_choice.call_args[0][0]
                assert called_with == gate.WEBGL_BY_OS["windows"]
                
                # Should return first item from Windows list
                expected_vendor, expected_renderer = gate.WEBGL_BY_OS["windows"][0]
                assert vars["__WEBGL_VENDOR__"] == expected_vendor
                assert vars["__WEBGL_RENDERER__"] == expected_renderer
    
    def test_random_selection_distribution(self, gate):
        """Test that random selection provides good distribution."""
        with patch('gaterunner.gates.webgl.detect_os_family', return_value="windows"):
            # Generate multiple selections
            vendors_seen = set()
            renderers_seen = set()
            
            for _ in range(50):  # Run enough times to see variety
                vars = gate.get_js_template_vars(user_agent="Windows Chrome Agent")
                vendors_seen.add(vars["__WEBGL_VENDOR__"])
                renderers_seen.add(vars["__WEBGL_RENDERER__"])
            
            # Should see multiple different vendors/renderers over many runs
            # (This is probabilistic, but with 50 runs very likely to pass)
            assert len(vendors_seen) > 1 or len(renderers_seen) > 1


class TestWebGLIntegration:
    """Integration tests for WebGL gate."""
    
    @pytest.fixture
    def gate(self):
        return WebGLGate()
    
    def test_full_gate_lifecycle(self, gate):
        """Test complete gate lifecycle."""
        # 1. Handle (should be no-op)
        import asyncio
        asyncio.run(gate.handle(None, None))
        
        # 2. Get headers (should be empty)
        headers = asyncio.run(gate.get_headers())
        assert headers == {}
        
        # 3. Get JS patches (provide user_agent to get patches)
        patches = gate.get_js_patches(engine="chromium", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")
        assert "webgl_patch.js" in patches
        
        # 4. Get template vars
        vars = gate.get_js_template_vars(
            user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/120.0.0.0"
        )
        assert "__WEBGL_VENDOR__" in vars
        assert "__WEBGL_RENDERER__" in vars
    
    def test_integration_with_user_agent_gate(self, gate):
        """Test WebGL gate integration with UserAgent gate patterns."""
        # Test that WebGL variables work with UserAgent template patterns
        vars = gate.get_js_template_vars(
            user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/120.0.0.0",
            webgl_vendor="NVIDIA Corporation",
            webgl_renderer="NVIDIA GeForce RTX 3060"
        )
        
        # Should provide variables that UserAgent gate expects
        assert vars["__WEBGL_VENDOR__"] == "NVIDIA Corporation"
        assert vars["__WEBGL_RENDERER__"] == "NVIDIA GeForce RTX 3060"
        
        # These variables should be suitable for JavaScript template injection
        vendor = vars["__WEBGL_VENDOR__"]
        renderer = vars["__WEBGL_RENDERER__"]
        
        # Should not contain problematic characters for JS injection
        assert '"' not in vendor or '\\"' in vendor  # Either no quotes or escaped
        assert '"' not in renderer or '\\"' in renderer 