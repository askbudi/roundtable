#!/usr/bin/env python3
"""Demo script showing how to use the Roundtable AI MCP Server.

This script demonstrates basic usage and can be used to test the server manually.
"""

import os
import sys
from pathlib import Path

def print_section(title: str, emoji: str = "🔧"):
    """Print a formatted section header."""
    print(f"\n{emoji} {title}")
    print("-" * (len(title) + 3))

def main():
    """Main demo function."""
    print("🚀 Roundtable AI MCP Server Demo")
    print("=" * 50)

    print_section("Server Information", "ℹ️")
    print("This MCP server exposes CLI subagents via the MCP protocol.")
    print("Available subagents: Codex, Claude Code, Cursor Agent, Gemini")

    print_section("Installation", "📦")
    print("1. Install dependencies:")
    print("   source .venv_juno/bin/activate")
    print("   pip install fastmcp pydantic")

    print_section("Running the Server", "🚀")
    print("1. Start the server:")
    print("   source .venv_juno/bin/activate")
    print("   python -m roundtable_mcp_server")
    print()
    print("2. Or with specific configuration:")
    print("   export CLI_MCP_SUBAGENTS=\"codex,claude\"")
    print("   export CLI_MCP_WORKING_DIR=\"/path/to/project\"")
    print("   python -m roundtable_mcp_server")

    print_section("MCP Client Configuration", "🔧")
    print("For Claude Desktop (~/.config/claude_desktop_config.json):")
    print("""{
  "mcpServers": {
    "roundtable-ai": {
      "command": "python",
      "args": ["-m", "roundtable_mcp_server"],
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}""")

    print_section("Available Tools", "🛠️")
    tools = [
        ("check_codex_availability", "Check if Codex CLI is available"),
        ("codex_subagent", "Execute coding tasks using Codex"),
        ("check_claude_availability", "Check if Claude Code CLI is available"),
        ("claude_subagent", "Execute coding tasks using Claude Code"),
        ("check_cursor_availability", "Check if Cursor Agent CLI is available"),
        ("cursor_subagent", "Execute coding tasks using Cursor Agent"),
        ("check_gemini_availability", "Check if Gemini CLI is available"),
        ("gemini_subagent", "Execute coding tasks using Gemini"),
    ]

    for tool_name, description in tools:
        print(f"  - {tool_name}: {description}")

    print_section("Example Usage", "💡")
    print("Once configured with an MCP client, you can:")
    print("1. Check which subagents are available")
    print("2. Execute coding tasks like:")
    print("   - 'Implement a function to sort a list'")
    print("   - 'Fix bugs in the codebase'")
    print("   - 'Refactor code for better performance'")
    print("   - 'Add tests for existing functions'")

    print_section("Environment Variables", "🌍")
    print("- CLI_MCP_SUBAGENTS: Comma-separated list (default: all)")
    print("- CLI_MCP_WORKING_DIR: Working directory (default: current)")
    print("- CLI_MCP_DEBUG: Enable debug logging (default: true)")

    print_section("Logs and Debugging", "🔍")
    print("- Debug logs are written to: roundtable_mcp_server.log")
    print("- Use the test suite to verify functionality:")
    print("  python -m roundtable_mcp_server.test_server")

    print_section("Current Status", "📊")
    # Show current working directory
    print(f"Working directory: {Path.cwd()}")

    # Check if log file exists
    log_file = Path.cwd() / "roundtable_mcp_server.log"
    if log_file.exists():
        size = log_file.stat().st_size
        print(f"Log file: {log_file} ({size} bytes)")
    else:
        print("Log file: Not created yet")

    print("\n🎉 Ready to use Roundtable AI MCP Server!")
    print("Start the server and configure your MCP client to begin.")

if __name__ == "__main__":
    main()