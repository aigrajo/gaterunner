"""
Test suite for GateBase class and gate interface contracts.

Tests the base interface that all gates must implement and
validates the contract for gate implementations.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from gaterunner.gates.base import GateBase


class TestGateBase:
    """Test the base gate interface."""
    
    def test_gate_base_initialization(self):
        """Test GateBase initialization and default values."""
        gate = GateBase()
        
        assert gate.name == "base"
    
    @pytest.mark.asyncio
    async def test_handle_default_implementation(self):
        """Test that handle() method has default no-op implementation."""
        gate = GateBase()
        
        # Should not crash with any arguments
        await gate.handle(None, None)
        await gate.handle("page", "context", setting="value")
    
    @pytest.mark.asyncio
    async def test_get_headers_default_implementation(self):
        """Test that get_headers() returns empty dict by default."""
        gate = GateBase()
        
        headers = await gate.get_headers()
        assert headers == {}
        
        # Should work with any kwargs
        headers = await gate.get_headers(url="https://example.com", setting="value")
        assert headers == {}
    
    def test_inject_headers_default_implementation(self):
        """Test that inject_headers() returns empty dict by default."""
        gate = GateBase()
        mock_request = Mock()
        
        headers = gate.inject_headers(mock_request)
        assert headers == {}
    
    def test_get_js_patches_default_implementation(self):
        """Test that get_js_patches() returns empty list by default."""
        gate = GateBase()
        
        patches = gate.get_js_patches()
        assert patches == []
        
        # Should work with engine parameter
        patches = gate.get_js_patches(engine="chromium")
        assert patches == []
        
        # Should work with any kwargs
        patches = gate.get_js_patches(engine="firefox", setting="value")
        assert patches == []
    
    def test_get_js_template_vars_default_implementation(self):
        """Test that get_js_template_vars() returns empty dict by default."""
        gate = GateBase()
        
        vars = gate.get_js_template_vars()
        assert vars == {}
        
        # Should work with any kwargs
        vars = gate.get_js_template_vars(setting="value", user_agent="test")
        assert vars == {}


class ConcreteTestGate(GateBase):
    """Concrete gate implementation for testing inheritance."""
    
    name = "TestGate"
    
    async def handle(self, page, context, **kwargs):
        """Test implementation of handle method."""
        self.handle_called = True
        self.handle_kwargs = kwargs
    
    async def get_headers(self, **kwargs):
        """Test implementation of get_headers method."""
        return {"X-Test-Header": "test-value"}
    
    def inject_headers(self, request):
        """Test implementation of inject_headers method."""
        return {"X-Dynamic-Header": "dynamic-value"}
    
    def get_js_patches(self, engine="chromium", **kwargs):
        """Test implementation of get_js_patches method."""
        if engine == "chromium":
            return ["test_patch.js"]
        return []
    
    def get_js_template_vars(self, **kwargs):
        """Test implementation of get_js_template_vars method."""
        return {"__TEST_VAR__": "test_value"}


class TestGateInheritance:
    """Test gate inheritance and interface implementation."""
    
    def test_concrete_gate_inheritance(self):
        """Test that concrete gates inherit properly from GateBase."""
        gate = ConcreteTestGate()
        
        assert isinstance(gate, GateBase)
        assert gate.name == "TestGate"
    
    @pytest.mark.asyncio
    async def test_concrete_gate_handle_implementation(self):
        """Test concrete gate handle method implementation."""
        gate = ConcreteTestGate()
        
        await gate.handle("page", "context", setting="value", enabled=True)
        
        assert hasattr(gate, 'handle_called')
        assert gate.handle_called == True
        assert gate.handle_kwargs == {"setting": "value", "enabled": True}
    
    @pytest.mark.asyncio
    async def test_concrete_gate_get_headers_implementation(self):
        """Test concrete gate get_headers method implementation."""
        gate = ConcreteTestGate()
        
        headers = await gate.get_headers(url="https://example.com")
        
        assert headers == {"X-Test-Header": "test-value"}
    
    def test_concrete_gate_inject_headers_implementation(self):
        """Test concrete gate inject_headers method implementation."""
        gate = ConcreteTestGate()
        mock_request = Mock()
        
        headers = gate.inject_headers(mock_request)
        
        assert headers == {"X-Dynamic-Header": "dynamic-value"}
    
    def test_concrete_gate_get_js_patches_implementation(self):
        """Test concrete gate get_js_patches method implementation."""
        gate = ConcreteTestGate()
        
        # Test chromium engine
        patches = gate.get_js_patches(engine="chromium")
        assert patches == ["test_patch.js"]
        
        # Test other engine
        patches = gate.get_js_patches(engine="firefox")
        assert patches == []
    
    def test_concrete_gate_get_js_template_vars_implementation(self):
        """Test concrete gate get_js_template_vars method implementation."""
        gate = ConcreteTestGate()
        
        vars = gate.get_js_template_vars(user_agent="test-agent")
        
        assert vars == {"__TEST_VAR__": "test_value"}


class TestGateInterfaceContract:
    """Test the interface contract that all gates should follow."""
    
    def test_gate_name_attribute(self):
        """Test that gates have a name attribute."""
        gate = GateBase()
        assert hasattr(gate, 'name')
        assert isinstance(gate.name, str)
        
        concrete_gate = ConcreteTestGate()
        assert hasattr(concrete_gate, 'name')
        assert isinstance(concrete_gate.name, str)
        assert concrete_gate.name != "base"  # Should override default
    
    def test_gate_methods_exist(self):
        """Test that required gate methods exist."""
        gate = GateBase()
        
        # Check all required methods exist
        assert hasattr(gate, 'handle')
        assert callable(gate.handle)
        
        assert hasattr(gate, 'get_headers')
        assert callable(gate.get_headers)
        
        assert hasattr(gate, 'inject_headers')
        assert callable(gate.inject_headers)
        
        assert hasattr(gate, 'get_js_patches')
        assert callable(gate.get_js_patches)
        
        assert hasattr(gate, 'get_js_template_vars')
        assert callable(gate.get_js_template_vars)
    
    @pytest.mark.asyncio
    async def test_gate_handle_signature(self):
        """Test that handle method accepts expected signature."""
        gate = GateBase()
        
        # Should accept page, context, and kwargs
        await gate.handle(None, None)
        await gate.handle("page", "context")
        await gate.handle("page", "context", url="https://example.com")
        await gate.handle("page", "context", setting="value", enabled=True)
    
    @pytest.mark.asyncio
    async def test_gate_get_headers_signature(self):
        """Test that get_headers method accepts expected signature."""
        gate = GateBase()
        
        # Should accept kwargs and return dict
        headers = await gate.get_headers()
        assert isinstance(headers, dict)
        
        headers = await gate.get_headers(url="https://example.com")
        assert isinstance(headers, dict)
        
        headers = await gate.get_headers(user_agent="test", enabled=True)
        assert isinstance(headers, dict)
    
    def test_gate_inject_headers_signature(self):
        """Test that inject_headers method accepts expected signature."""
        gate = GateBase()
        mock_request = Mock()
        
        # Should accept request object and return dict
        headers = gate.inject_headers(mock_request)
        assert isinstance(headers, dict)
    
    def test_gate_get_js_patches_signature(self):
        """Test that get_js_patches method accepts expected signature."""
        gate = GateBase()
        
        # Should accept engine and kwargs, return list
        patches = gate.get_js_patches()
        assert isinstance(patches, list)
        
        patches = gate.get_js_patches(engine="chromium")
        assert isinstance(patches, list)
        
        patches = gate.get_js_patches(engine="firefox", setting="value")
        assert isinstance(patches, list)
    
    def test_gate_get_js_template_vars_signature(self):
        """Test that get_js_template_vars method accepts expected signature."""
        gate = GateBase()
        
        # Should accept kwargs and return dict
        vars = gate.get_js_template_vars()
        assert isinstance(vars, dict)
        
        vars = gate.get_js_template_vars(user_agent="test")
        assert isinstance(vars, dict)
        
        vars = gate.get_js_template_vars(setting="value", enabled=True)
        assert isinstance(vars, dict)


class TestGateDocumentation:
    """Test that gate methods have proper documentation."""
    
    def test_base_gate_method_docstrings(self):
        """Test that base gate methods have docstrings."""
        gate = GateBase()
        
        # Check that methods have docstrings
        assert gate.handle.__doc__ is not None
        assert gate.get_headers.__doc__ is not None
        assert gate.inject_headers.__doc__ is not None
        assert gate.get_js_patches.__doc__ is not None
        assert gate.get_js_template_vars.__doc__ is not None
        
        # Check that docstrings are not empty
        assert len(gate.handle.__doc__.strip()) > 0
        assert len(gate.get_headers.__doc__.strip()) > 0
        assert len(gate.inject_headers.__doc__.strip()) > 0
        assert len(gate.get_js_patches.__doc__.strip()) > 0
        assert len(gate.get_js_template_vars.__doc__.strip()) > 0 