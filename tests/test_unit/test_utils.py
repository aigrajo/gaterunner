"""
Test suite for utility functions, particularly TemplateLoader.

Tests the JavaScript template processing system that is critical
for dynamic fingerprinting patch injection.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from gaterunner.utils import TemplateLoader, safe_filename


class TestTemplateLoader:
    """Test suite for TemplateLoader class."""
    
    def test_template_loader_init_default_dir(self):
        """Test TemplateLoader initialization with default JS directory."""
        loader = TemplateLoader()
        
        # Should default to gaterunner/js directory
        expected_path = Path(__file__).resolve().parent.parent.parent / "gaterunner" / "js"
        assert loader.js_dir == expected_path
        assert loader.js_templates_cache == {}
    
    def test_template_loader_init_custom_dir(self, sample_js_templates_dir):
        """Test TemplateLoader initialization with custom directory."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        assert loader.js_dir == sample_js_templates_dir
        assert loader.js_templates_cache == {}
    
    def test_load_and_render_basic_template(self, sample_js_templates_dir):
        """Test basic template loading and variable replacement."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        template_vars = {
            "__NAV_REF__": "navigator",
            "__USER_AGENT__": "Mozilla/5.0 Chrome Test Agent",
            "__PLATFORM__": "Win32"
        }
        
        rendered = loader.load_and_render_template("spoof_useragent.js", template_vars)
        
        # Check that variables were replaced
        assert "Mozilla/5.0 Chrome Test Agent" in rendered
        assert "Win32" in rendered
        assert "navigator" in rendered
        
        # Check that placeholders were removed
        assert "__USER_AGENT__" not in rendered
        assert "__PLATFORM__" not in rendered
        assert "__NAV_REF__" not in rendered
    
    def test_template_variable_formats(self, sample_js_templates_dir):
        """Test different variable format handling."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        # Test mixed variable formats
        template_vars = {
            "__USER_AGENT__": "Already formatted",  # Already has double underscores
            "platform": "Needs formatting",         # Needs conversion to __PLATFORM__
            "device_memory": "8"                   # Should become __DEVICE_MEMORY__
        }
        
        rendered = loader.load_and_render_template("worker_spoof_template.js", template_vars)
        
        # Check that both formats work
        assert "Already formatted" in rendered
        assert "8" in rendered  # device_memory should be replaced
    
    def test_template_caching_behavior(self, sample_js_templates_dir):
        """Test that templates are cached after first load."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        # Load template first time
        vars1 = {"__USER_AGENT__": "First Load"}
        rendered1 = loader.load_and_render_template("spoof_useragent.js", vars1)
        
        # Verify template is now cached
        assert "spoof_useragent.js" in loader.js_templates_cache
        cached_template = loader.js_templates_cache["spoof_useragent.js"]
        
        # Load template second time with different variables
        vars2 = {"__USER_AGENT__": "Second Load"}
        rendered2 = loader.load_and_render_template("spoof_useragent.js", vars2)
        
        # Verify template content is cached but variables are different
        assert loader.js_templates_cache["spoof_useragent.js"] == cached_template
        assert "First Load" in rendered1
        assert "Second Load" in rendered2
        assert "First Load" not in rendered2
    
    def test_template_not_found_error(self, sample_js_templates_dir):
        """Test handling of missing template files."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        with pytest.raises(FileNotFoundError, match="JS template not found"):
            loader.load_and_render_template("nonexistent_template.js", {})
    
    def test_complex_template_rendering(self, sample_js_templates_dir):
        """Test rendering with complex variable sets."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        # Complex variable set typical of real usage
        template_vars = {
            "__WEBGL_VENDOR__": "NVIDIA Corporation",
            "__WEBGL_RENDERER__": "NVIDIA GeForce RTX 3060/PCIe/SSE2",
            "param_1": "37445",  # Will become __PARAM_1__
            "param_2": "37446"   # Will become __PARAM_2__
        }
        
        rendered = loader.load_and_render_template("webgl_patch.js", template_vars)
        
        # Verify complex replacements
        assert "NVIDIA Corporation" in rendered
        assert "NVIDIA GeForce RTX 3060/PCIe/SSE2" in rendered
        assert "__WEBGL_VENDOR__" not in rendered
        assert "__WEBGL_RENDERER__" not in rendered
    
    def test_empty_template_variables(self, sample_js_templates_dir):
        """Test template rendering with empty variable dict."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        # Should not crash with empty variables
        rendered = loader.load_and_render_template("spoof_useragent.js", {})
        
        # Original placeholders should remain
        assert "__USER_AGENT__" in rendered
        assert "__PLATFORM__" in rendered
    
    def test_special_characters_in_variables(self, sample_js_templates_dir):
        """Test handling of special characters in variable values."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        # Variables with special characters that might break JS
        template_vars = {
            "__USER_AGENT__": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \"Quoted\" Agent",
            "__PLATFORM__": "Win32/WOW64",
        }
        
        rendered = loader.load_and_render_template("spoof_useragent.js", template_vars)
        
        # Should handle special characters correctly
        assert '"Quoted"' in rendered
        assert "Win32/WOW64" in rendered
    
    def test_numeric_variables(self, sample_js_templates_dir):
        """Test handling of numeric variables."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        template_vars = {
            "__DEVICE_MEMORY__": 8,      # Integer
            "timeout": 30.5              # Float - becomes __TIMEOUT__
        }
        
        rendered = loader.load_and_render_template("worker_spoof_template.js", template_vars)
        
        # Numeric values should be converted to strings
        assert "8" in rendered


class TestSafeFilename:
    """Test suite for safe_filename utility function."""
    
    def test_basic_filename_generation(self):
        """Test basic safe filename generation."""
        result = safe_filename("test_file", ".txt", "salt123")
        
        # Should have stem + underscore + hash + extension
        assert result.endswith(".txt")
        assert "test_file_" in result
        assert len(result.split("_")[-1].split(".")[0]) == 8  # 8-char MD5 prefix
    
    def test_filename_with_special_characters(self):
        """Test filename generation with special characters."""
        unsafe_stem = "file with spaces & special chars!@#"
        result = safe_filename(unsafe_stem, ".js", "salt")
        
        # Should handle safely
        assert result.endswith(".js")
        assert "_" in result  # Should have underscore separator
    
    def test_long_filename_truncation(self):
        """Test that long filenames are truncated appropriately."""
        long_stem = "a" * 300  # Very long filename
        result = safe_filename(long_stem, ".txt", "salt")
        
        # Should be under maximum length
        assert len(result) <= 255  # Typical filesystem limit
        assert result.endswith(".txt")
    
    def test_consistent_hash_generation(self):
        """Test that same input produces same hash."""
        stem = "consistent_test"
        ext = ".js"
        salt = "same_salt"
        
        result1 = safe_filename(stem, ext, salt)
        result2 = safe_filename(stem, ext, salt)
        
        assert result1 == result2
    
    def test_different_salt_different_hash(self):
        """Test that different salts produce different hashes."""
        stem = "test_file"
        ext = ".txt"
        
        result1 = safe_filename(stem, ext, "salt1")
        result2 = safe_filename(stem, ext, "salt2")
        
        assert result1 != result2
        # But both should have same structure
        assert result1.endswith(".txt")
        assert result2.endswith(".txt")


class TestUtilityIntegration:
    """Integration tests for utility functions working together."""
    
    def test_template_loader_with_safe_filenames(self, sample_js_templates_dir):
        """Test TemplateLoader working with safe filename generation."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        # Generate a safe filename for a template
        template_name = safe_filename("dynamic_template", ".js", "test_salt")
        
        # This would be used in practice for dynamically generated templates
        # For now, just verify the filename is safe
        assert template_name.endswith(".js")
        assert "_" in template_name
    
    def test_template_variable_edge_cases(self, sample_js_templates_dir):
        """Test edge cases in template variable handling."""
        loader = TemplateLoader(js_dir=sample_js_templates_dir)
        
        edge_case_vars = {
            "__EMPTY__": "",
            "__NULL__": None,
            "__BOOL__": True,
            "__ZERO__": 0,
            "spaces in name": "should_work"  # Becomes __SPACES IN NAME__
        }
        
        # Should not crash with edge case variables
        rendered = loader.load_and_render_template("spoof_useragent.js", edge_case_vars)
        
        # Basic validation that it didn't crash
        assert isinstance(rendered, str)
        assert len(rendered) > 0 