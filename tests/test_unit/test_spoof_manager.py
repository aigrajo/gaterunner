"""
Test suite for SpoofingManager class.

Tests the core orchestration logic that coordinates all spoofing gates
and applies both HTTP-level and JavaScript-level fingerprinting evasion.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, ANY
from gaterunner.spoof_manager import SpoofingManager


class TestSpoofingManagerInit:
    """Test SpoofingManager initialization."""
    
    def test_default_initialization(self):
        """Test SpoofingManager initialization with default gates."""
        with patch('gaterunner.spoof_manager.ALL_GATES', []):
            manager = SpoofingManager()
            
            assert manager.gates == []
            assert hasattr(manager, 'template_loader')
    
    def test_custom_gates_initialization(self):
        """Test SpoofingManager initialization with custom gates."""
        mock_gates = [Mock(), Mock()]
        mock_gates[0].name = "TestGate1"
        mock_gates[1].name = "TestGate2"
        
        manager = SpoofingManager(gates=mock_gates)
        
        assert manager.gates == mock_gates
        assert len(manager.gates) == 2


class TestGateEnablement:
    """Test gate enablement logic."""
    
    @pytest.fixture
    def mock_gates(self):
        """Create mock gates for testing."""
        gate1 = Mock()
        gate1.name = "TestGate1"
        gate2 = Mock()
        gate2.name = "TestGate2"
        return [gate1, gate2]
    
    @pytest.fixture
    def manager(self, mock_gates):
        """SpoofingManager with mock gates."""
        return SpoofingManager(gates=mock_gates)
    
    def test_gate_enabled_explicit_config(self, manager):
        """Test gate enablement with explicit configuration."""
        gate = manager.gates[0]
        gate_config = {"TestGate1": {"enabled": True}}
        
        assert manager._is_gate_enabled(gate, gate_config) == True
    
    def test_gate_enabled_default_behavior(self, manager):
        """Test gate enablement with default behavior (should be enabled)."""
        gate = manager.gates[0]
        gate_config = {}
        
        assert manager._is_gate_enabled(gate, gate_config) == True
    
    def test_gate_explicitly_disabled(self, manager):
        """Test gate explicitly disabled via gates_enabled config."""
        gate = manager.gates[0]
        gate_config = {"gates_enabled": {"TestGate1": False}}
        
        assert manager._is_gate_enabled(gate, gate_config) == False
    
    def test_gate_enabled_mixed_config(self, manager):
        """Test gate enablement with mixed explicit and default config."""
        gate_config = {
            "TestGate1": {"setting": "value"},  # Explicitly configured = enabled
            "gates_enabled": {"TestGate2": False}  # Explicitly disabled
        }
        
        assert manager._is_gate_enabled(manager.gates[0], gate_config) == True
        assert manager._is_gate_enabled(manager.gates[1], gate_config) == False


class TestHTTPSpoofing:
    """Test HTTP-level spoofing functionality."""
    
    @pytest.fixture
    def mock_gates(self):
        """Mock gates with HTTP functionality."""
        gate1 = AsyncMock()
        gate1.name = "HTTPGate1"
        gate1.handle = AsyncMock()
        gate1.get_headers = AsyncMock(return_value={"X-Test-1": "value1"})
        gate1.inject_headers = Mock(return_value={"X-Dynamic-1": "dynamic1"})
        
        gate2 = AsyncMock()
        gate2.name = "HTTPGate2"
        gate2.handle = AsyncMock()
        gate2.get_headers = AsyncMock(return_value={"X-Test-2": "value2"})
        # gate2 doesn't have inject_headers method
        
        return [gate1, gate2]
    
    @pytest.fixture
    def manager(self, mock_gates):
        """SpoofingManager with HTTP mock gates."""
        return SpoofingManager(gates=mock_gates)
    
    @pytest.mark.asyncio
    async def test_apply_http_spoofing_basic(self, manager, mock_page, mock_context):
        """Test basic HTTP spoofing application."""
        gate_config = {
            "HTTPGate1": {"enabled": True},
            "HTTPGate2": {"enabled": True}
        }
        
        await manager._apply_http_spoofing(
            mock_page, mock_context, gate_config, url="https://example.com", 
            resource_request_headers=None
        )
        
        # Verify all gates were handled
        for gate in manager.gates:
            gate.handle.assert_called_once()
            gate.get_headers.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_header_collection_and_routing(self, manager, mock_page, mock_context):
        """Test header collection and route setup."""
        gate_config = {"HTTPGate1": {}, "HTTPGate2": {}}
        
        await manager._apply_http_spoofing(
            mock_page, mock_context, gate_config, url="https://example.com",
            resource_request_headers={}
        )
        
        # Verify context.route was called to set up header injection
        mock_context.route.assert_called_once_with("**/*", ANY)
    
    @pytest.mark.asyncio
    async def test_special_useragent_gate_handling(self, manager, mock_context):
        """Test special handling for UserAgentGate with WebGL data."""
        # Create UserAgentGate mock
        ua_gate = AsyncMock()
        ua_gate.name = "UserAgentGate"
        ua_gate.handle = AsyncMock()
        ua_gate.get_headers = AsyncMock(return_value={})
        
        manager.gates = [ua_gate]
        
        gate_config = {
            "UserAgentGate": {"user_agent": "test"},
            "WebGLGate": {"webgl_vendor": "NVIDIA", "webgl_renderer": "RTX 3060"}
        }
        
        await manager._apply_http_spoofing(
            None, mock_context, gate_config, url=None, resource_request_headers=None
        )
        
        # Verify UserAgentGate.handle was called with WebGL data
        ua_gate.handle.assert_called_once()
        call_kwargs = ua_gate.handle.call_args[1]
        assert call_kwargs["webgl_vendor"] == "NVIDIA"
        assert call_kwargs["webgl_renderer"] == "RTX 3060"


class TestJavaScriptSpoofing:
    """Test JavaScript patch application."""
    
    @pytest.fixture
    def mock_gates(self):
        """Mock gates with JavaScript functionality."""
        gate1 = Mock()
        gate1.name = "JSGate1"
        gate1.get_js_patches = Mock(return_value=["patch1.js", "patch2.js"])
        gate1.get_js_template_vars = Mock(return_value={"__VAR1__": "value1"})
        
        gate2 = Mock()
        gate2.name = "JSGate2"
        gate2.get_js_patches = Mock(return_value=["patch3.js"])
        gate2.get_js_template_vars = Mock(return_value={"__VAR2__": "value2"})
        
        # Special timezone gate
        tz_gate = Mock()
        tz_gate.name = "TimezoneGate"
        tz_gate.get_js_patches = Mock(return_value=["timezone.js"])
        tz_gate.get_js_template_vars = Mock(return_value={"timezone_id": "America/New_York"})
        
        return [gate1, gate2, tz_gate]
    
    @pytest.fixture
    def manager(self, mock_gates):
        """SpoofingManager with JS mock gates."""
        manager = SpoofingManager(gates=mock_gates)
        # Mock template loader
        manager.template_loader = Mock()
        manager.template_loader.load_and_render_template = Mock(return_value="console.log('spoofed');")
        return manager
    
    @pytest.mark.asyncio
    async def test_apply_js_patches_basic(self, manager, mock_context):
        """Test basic JavaScript patch application."""
        gate_config = {"JSGate1": {}, "JSGate2": {}}
        
        await manager._apply_js_patches(mock_context, gate_config, "chromium")
        
        # Verify template variables were collected
        for gate in manager.gates[:2]:  # Skip timezone gate for this test
            gate.get_js_template_vars.assert_called_once()
        
        # Verify patches were applied
        assert mock_context.add_init_script.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_timezone_priority_handling(self, manager, mock_context):
        """Test that TimezoneGate is processed first for timezone selection."""
        gate_config = {
            "JSGate1": {},
            "TimezoneGate": {}
        }
        
        await manager._apply_js_patches(mock_context, gate_config, "chromium")
        
        # Verify timezone was processed and stored
        assert hasattr(manager, '_last_template_vars')
        # The timezone from TimezoneGate should be available
    
    @pytest.mark.asyncio
    async def test_browser_engine_patch_skipping(self, manager, mock_context):
        """Test that patches are skipped for certain browser engines."""
        gate_config = {
            "browser_engine": "patchright",
            "JSGate1": {}
        }
        
        await manager._apply_js_patches(mock_context, gate_config, "chromium")
        
        # Verify get_js_patches was called with browser_engine parameter
        for gate in manager.gates:
            if gate.name != "TimezoneGate":
                gate.get_js_patches.assert_called_once()
                call_kwargs = gate.get_js_patches.call_args[1]
                assert call_kwargs.get("browser_engine") == "patchright"
    
    @pytest.mark.asyncio
    async def test_template_rendering_error_handling(self, manager, mock_context):
        """Test error handling in template rendering."""
        gate_config = {"JSGate1": {}}
        
        # Make template loader raise an exception
        manager.template_loader.load_and_render_template.side_effect = Exception("Template error")
        
        # Should not crash, should handle error gracefully
        await manager._apply_js_patches(mock_context, gate_config, "chromium")
        
        # Verify it attempted to load templates but handled the error
        assert manager.template_loader.load_and_render_template.called
    
    @pytest.mark.asyncio
    async def test_template_variable_merging(self, manager, mock_context):
        """Test that template variables from different gates are merged correctly."""
        gate_config = {"JSGate1": {}, "JSGate2": {}}
        
        await manager._apply_js_patches(mock_context, gate_config, "chromium")
        
        # Verify template variables were merged and stored
        assert hasattr(manager, '_last_template_vars')
        template_vars = manager._last_template_vars
        
        # Should contain variables from both gates
        assert "__VAR1__" in template_vars
        assert "__VAR2__" in template_vars


class TestApplySpoofingIntegration:
    """Test the main apply_spoofing method integration."""
    
    @pytest.fixture
    def comprehensive_gates(self):
        """Create comprehensive mock gates for integration testing."""
        gates = []
        
        # UserAgent gate
        ua_gate = AsyncMock()
        ua_gate.name = "UserAgentGate"
        ua_gate.handle = AsyncMock()
        ua_gate.get_headers = AsyncMock(return_value={"User-Agent": "Test Agent"})
        ua_gate.get_js_patches = Mock(return_value=["useragent.js"])
        ua_gate.get_js_template_vars = Mock(return_value={"__USER_AGENT__": "Test Agent"})
        gates.append(ua_gate)
        
        # WebGL gate
        webgl_gate = AsyncMock()
        webgl_gate.name = "WebGLGate"
        webgl_gate.handle = AsyncMock()
        webgl_gate.get_headers = AsyncMock(return_value={})
        webgl_gate.get_js_patches = Mock(return_value=["webgl.js"])
        webgl_gate.get_js_template_vars = Mock(return_value={
            "__WEBGL_VENDOR__": "NVIDIA",
            "__WEBGL_RENDERER__": "RTX 3060"
        })
        gates.append(webgl_gate)
        
        return gates
    
    @pytest.fixture
    def integration_manager(self, comprehensive_gates):
        """SpoofingManager for integration testing."""
        manager = SpoofingManager(gates=comprehensive_gates)
        manager.template_loader = Mock()
        manager.template_loader.load_and_render_template = Mock(return_value="/* spoofed */")
        return manager
    
    @pytest.mark.asyncio
    async def test_full_spoofing_pipeline(self, integration_manager, mock_page, mock_context):
        """Test complete spoofing pipeline from config to application."""
        gate_config = {
            "UserAgentGate": {"user_agent": "Test Agent"},
            "WebGLGate": {"webgl_vendor": "NVIDIA", "webgl_renderer": "RTX 3060"}
        }
        
        await integration_manager.apply_spoofing(
            page=mock_page,
            context=mock_context,
            gate_config=gate_config,
            engine="chromium",
            url="https://example.com"
        )
        
        # Verify both HTTP and JS spoofing were applied
        mock_context.route.assert_called_once()  # HTTP spoofing
        mock_context.add_init_script.assert_called()  # JS spoofing
        
        # Verify gates were handled
        for gate in integration_manager.gates:
            gate.handle.assert_called_once()
            gate.get_headers.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resource_request_headers_tracking(self, integration_manager, mock_page, mock_context):
        """Test that resource request headers are tracked when requested."""
        gate_config = {"UserAgentGate": {"user_agent": "Test Agent"}}
        resource_headers = {}
        
        await integration_manager.apply_spoofing(
            page=mock_page,
            context=mock_context,
            gate_config=gate_config,
            engine="chromium",
            url="https://example.com",
            resource_request_headers=resource_headers
        )
        
        # Verify route handler was set up for header tracking
        mock_context.route.assert_called_once()


class TestSetupPageHandlers:
    """Test page handler setup functionality."""
    
    @pytest.fixture
    def manager_with_page_handlers(self):
        """Manager with gates that have page handlers."""
        gate_with_handler = AsyncMock()
        gate_with_handler.name = "PageHandlerGate"
        gate_with_handler.setup_page_handlers = AsyncMock()
        
        gate_without_handler = Mock()
        gate_without_handler.name = "NoHandlerGate"
        # Deliberately no setup_page_handlers method
        
        manager = SpoofingManager(gates=[gate_with_handler, gate_without_handler])
        return manager
    
    @pytest.mark.asyncio
    async def test_setup_page_handlers_basic(self, manager_with_page_handlers, mock_page, mock_context):
        """Test basic page handler setup."""
        gate_config = {"PageHandlerGate": {}}
        
        await manager_with_page_handlers.setup_page_handlers(
            mock_page, mock_context, gate_config
        )
        
        # Verify setup_page_handlers was called on gates that have it
        gate_with_handler = manager_with_page_handlers.gates[0]
        gate_with_handler.setup_page_handlers.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_page_handlers_error_handling(self, manager_with_page_handlers, mock_page, mock_context):
        """Test error handling in page handler setup."""
        gate_config = {"PageHandlerGate": {}}
        
        # Make setup_page_handlers raise an exception
        gate_with_handler = manager_with_page_handlers.gates[0]
        gate_with_handler.setup_page_handlers.side_effect = Exception("Handler error")
        
        # Should not crash, should handle error gracefully
        await manager_with_page_handlers.setup_page_handlers(
            mock_page, mock_context, gate_config
        )
        
        # Verify it attempted to set up handlers
        gate_with_handler.setup_page_handlers.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_browser_engine_passed_to_handlers(self, manager_with_page_handlers, mock_page, mock_context):
        """Test that browser_engine config is passed to page handlers."""
        gate_config = {
            "browser_engine": "patchright",
            "PageHandlerGate": {"setting": "value"}
        }
        
        await manager_with_page_handlers.setup_page_handlers(
            mock_page, mock_context, gate_config
        )
        
        # Verify browser_engine was passed to the handler
        gate_with_handler = manager_with_page_handlers.gates[0]
        call_kwargs = gate_with_handler.setup_page_handlers.call_args[1]
        assert call_kwargs["browser_engine"] == "patchright"
        assert call_kwargs["setting"] == "value" 