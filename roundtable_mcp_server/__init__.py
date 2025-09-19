"""Roundtable AI MCP Server.

This module provides an MCP server that exposes CLI subagents
(Codex, Claude, Cursor, Gemini) via the MCP protocol.

Developed by Roundtable AI for seamless AI assistant integration.
"""

import sys
from pathlib import Path

try:
    from .server import main, ServerConfig, parse_config_from_env
except ImportError:
    # Add current directory to path for direct execution
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    from server import main, ServerConfig, parse_config_from_env

__all__ = ["main", "ServerConfig", "parse_config_from_env"]