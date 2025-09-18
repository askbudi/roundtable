"""Roundtable AI MCP Server.

This module provides an MCP server that exposes CLI subagents
(Codex, Claude, Cursor, Gemini) via the MCP protocol.

Developed by Roundtable AI for seamless AI assistant integration.
"""

from .server import main, ServerConfig, parse_config_from_env

__all__ = ["main", "ServerConfig", "parse_config_from_env"]