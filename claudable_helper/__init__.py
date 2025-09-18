"""
Claudable Helper - Integration of Claudable services.

Provides easy access to Claudable's CLI adapters and services.
"""

# Import main CLI adapters for convenience
try:
    from .cli.adapters import (
        ClaudeCodeCLI,
        CursorAgentCLI,
        CodexCLI,
        QwenCLI,
        GeminiCLI,
    )
    __all__ = [
        "ClaudeCodeCLI",
        "CursorAgentCLI", 
        "CodexCLI",
        "QwenCLI",
        "GeminiCLI",
    ]
except ImportError as e:
    print(f"Warning: Could not import CLI adapters: {e}")
    __all__ = []

# Version info
__version__ = "extracted-from-claudable"
