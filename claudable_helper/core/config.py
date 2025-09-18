"""Mock configuration module for claudable_helper.

This module provides a mock implementation of the configuration interface
that was originally imported from app.core.config.
"""
import os
from typing import Any, Optional


class MockSettings:
    """Mock settings object for configuration."""
    
    def __init__(self):
        self._values = {}
    
    def __getattr__(self, name: str) -> Any:
        """Get setting value with fallback to environment variables."""
        # First check if we have it stored
        if name in self._values:
            return self._values[name]
        
        # Try environment variable (uppercase)
        env_name = name.upper()
        env_value = os.environ.get(env_name)
        if env_value is not None:
            return env_value
        
        # Common defaults for known settings
        defaults = {
            "debug": False,
            "environment": "development",
            "base_url": "http://localhost:8000",
            "project_root": os.getcwd(),
        }
        
        return defaults.get(name, None)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Set setting value."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            if not hasattr(self, '_values'):
                super().__setattr__('_values', {})
            self._values[name] = value
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get setting with default value."""
        try:
            return getattr(self, name)
        except AttributeError:
            return default


# Create singleton instance
settings = MockSettings()