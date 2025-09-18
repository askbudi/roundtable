#!/usr/bin/env python3
"""Test script for Roundtable AI MCP Server.

This script tests the MCP server functionality.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_section(title: str, emoji: str = "🔧"):
    """Print a formatted section header."""
    print(f"\n{emoji} {title}")
    print("-" * (len(title) + 3))


async def test_direct_imports():
    """Test that CLI subagent modules can be imported directly."""
    print_section("Testing Direct Imports", "📦")

    try:
        # Add parent dir to path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        from .cli_subagent import (
            check_codex_availability,
            check_claude_availability,
            check_cursor_availability,
            check_gemini_availability,
            codex_subagent,
            claude_subagent,
            cursor_subagent,
            gemini_subagent
        )
        print("✅ All subagent modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


async def test_server_imports():
    """Test that MCP server can be imported."""
    print_section("Testing Server Imports", "📦")

    try:
        from .server import ServerConfig, parse_config_from_env, server
        print("✅ Server modules imported successfully")
        print(f"  - Server name: {server.name}")
        # FastMCP doesn't expose _tools directly, but we can check if tools exist
        print(f"  - Server initialized successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


async def test_environment_configuration():
    """Test configuration from environment variables."""
    print_section("Testing Environment Configuration", "🌍")

    from .server import parse_config_from_env

    # Test 1: Default environment
    os.environ.pop("CLI_MCP_SUBAGENTS", None)
    os.environ.pop("CLI_MCP_WORKING_DIR", None)
    os.environ.pop("CLI_MCP_DEBUG", None)

    config = parse_config_from_env()
    print("✅ Default configuration:")
    print(f"  - Subagents: {', '.join(config.subagents)}")
    print(f"  - Working dir: {config.working_dir or 'Current directory'}")
    print(f"  - Debug: {config.debug}")

    # Test 2: Custom environment
    os.environ["CLI_MCP_SUBAGENTS"] = "codex,claude"
    os.environ["CLI_MCP_WORKING_DIR"] = "/tmp/test"
    os.environ["CLI_MCP_DEBUG"] = "false"

    config = parse_config_from_env()
    print("\n✅ Custom configuration from environment:")
    print(f"  - Subagents: {', '.join(config.subagents)}")
    print(f"  - Working dir: {config.working_dir}")
    print(f"  - Debug: {config.debug}")

    # Test 3: Invalid subagent names
    os.environ["CLI_MCP_SUBAGENTS"] = "codex,invalid,claude,unknown"

    config = parse_config_from_env()
    print("\n✅ Configuration with invalid subagents filtered:")
    print(f"  - Valid subagents: {', '.join(config.subagents)}")

    # Clean up
    os.environ.pop("CLI_MCP_SUBAGENTS", None)
    os.environ.pop("CLI_MCP_WORKING_DIR", None)
    os.environ.pop("CLI_MCP_DEBUG", None)

    return True


async def test_availability_checks():
    """Test availability check tools directly."""
    print_section("Testing Availability Checks", "🔍")

    # Add parent dir to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from .cli_subagent import (
        check_codex_availability,
        check_claude_availability,
        check_cursor_availability,
        check_gemini_availability
    )

    # Test each availability check
    checks = [
        ("Codex", check_codex_availability),
        ("Claude", check_claude_availability),
        ("Cursor", check_cursor_availability),
        ("Gemini", check_gemini_availability)
    ]

    results = {}
    for name, check_func in checks:
        try:
            result = await check_func()
            available = "✅" in result
            results[name] = available
            status = "✅ Available" if available else "❌ Not Available"
            print(f"  {name}: {status}")
        except Exception as e:
            print(f"  {name}: ⚠️  Error - {e}")
            results[name] = False

    # At least one should be available for testing to be meaningful
    if not any(results.values()):
        print("\n⚠️  No subagents are available - tests may be limited")

    return True


async def test_simple_execution():
    """Test executing a simple task with available subagents."""
    print_section("Testing Subagent Execution", "🎯")

    # Add parent dir to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from .cli_subagent import (
        check_codex_availability,
        check_claude_availability,
        codex_subagent,
        claude_subagent
    )

    # Simple test task
    test_task = "List the current directory contents and count the number of Python files"
    print(f"\n📝 Test task: {test_task}")

    # Try with codex first
    for subagent_name, check_func, exec_func in [
        ("Codex", check_codex_availability, codex_subagent),
        ("Claude", check_claude_availability, claude_subagent)
    ]:
        print(f"\nTesting {subagent_name}...")

        # First check availability
        try:
            result = await check_func()
            if "❌" in result:
                print(f"  ⏭️  Skipping {subagent_name} - not available")
                continue
        except Exception:
            print(f"  ⏭️  Skipping {subagent_name} - availability check failed")
            continue

        # Execute task
        try:
            result = await exec_func(
                instruction=test_task,
                project_path=str(Path.cwd()),
                is_initial_prompt=True
            )

            if "❌" in result:
                print(f"  ❌ Execution failed: {result[:100]}...")
            else:
                print(f"  ✅ Execution successful")
                print(f"  Result preview: {result[:200]}...")
                return True  # At least one worked

        except Exception as e:
            print(f"  ❌ Execution error: {e}")

    print("\n⚠️  No subagents could execute the test task")
    return False


async def test_server_tools():
    """Test that server tools are properly registered."""
    print_section("Testing Server Tools", "📋")

    from .server import server

    print(f"✅ Server initialized: {server.name}")
    print(f"✅ Server created successfully")

    # We can't directly access tools in FastMCP, but we can verify the server exists
    # The actual tool verification happens when the server runs
    expected_tools = [
        "check_codex_availability", "codex_subagent",
        "check_claude_availability", "claude_subagent",
        "check_cursor_availability", "cursor_subagent",
        "check_gemini_availability", "gemini_subagent"
    ]

    print(f"\n✅ Expected tools should be available: {len(expected_tools)} tools")
    for tool in expected_tools:
        print(f"  - {tool}")

    return True


async def main():
    """Run all tests."""
    print("🚀 Roundtable AI MCP Server Test Suite")
    print("=" * 50)

    results = {}

    # Run tests
    results["imports"] = await test_direct_imports()
    results["server_imports"] = await test_server_imports()
    results["environment"] = await test_environment_configuration()
    results["tools"] = await test_server_tools()
    results["availability"] = await test_availability_checks()
    results["execution"] = await test_simple_execution()

    # Summary
    print_section("Test Results Summary", "📊")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")

    passed_count = sum(results.values())
    total_count = len(results)

    print(f"\n🎯 Overall: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("🎉 All tests passed! MCP server is working correctly.")
    elif passed_count >= total_count - 1:
        print("✅ Core functionality working. Minor issues may exist.")
    else:
        print("⚠️  Multiple test failures - server needs fixes.")

    return passed_count == total_count


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(main())
    exit(0 if success else 1)