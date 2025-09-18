#!/usr/bin/env python3
"""Roundtable AI MCP Server.

This MCP server exposes CLI subagents (Codex, Claude, Cursor, Gemini) via the MCP protocol.
It supports stdio transport for integration with any MCP-compatible client.

Developed by Roundtable AI for seamless AI assistant integration.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field

# Configure logging with debug traces
log_file = Path.cwd() / "roundtable_mcp_server.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class SubagentConfig(BaseModel):
    """Configuration for a subagent."""
    name: str
    enabled: bool = True
    working_dir: Optional[str] = None
    model: Optional[str] = None


class ServerConfig(BaseModel):
    """Configuration for the MCP server."""
    subagents: List[str] = Field(
        default_factory=lambda: ["codex", "claude", "cursor", "gemini"],
        description="List of subagents to enable"
    )
    working_dir: Optional[str] = Field(
        default=None,
        description="Default working directory for all subagents"
    )
    debug: bool = Field(
        default=True,
        description="Enable debug logging"
    )


# Parse configuration from environment
def parse_config_from_env() -> ServerConfig:
    """Parse server configuration from environment variables.

    Environment variables:
    - CLI_MCP_SUBAGENTS: Comma-separated list of subagents to enable
    - CLI_MCP_WORKING_DIR: Default working directory for subagents
    - CLI_MCP_DEBUG: Enable debug logging (true/false)

    Returns:
        ServerConfig instance
    """
    config = ServerConfig()

    # Parse enabled subagents
    subagents_env = os.getenv("CLI_MCP_SUBAGENTS")
    if subagents_env:
        subagents = [s.strip().lower() for s in subagents_env.split(",") if s.strip()]
        valid_subagents = {"codex", "claude", "cursor", "gemini"}
        config.subagents = [s for s in subagents if s in valid_subagents]

        invalid = set(subagents) - valid_subagents
        if invalid:
            logger.warning(f"Invalid subagent names ignored: {', '.join(invalid)}")

    # Parse working directory
    working_dir = os.getenv("CLI_MCP_WORKING_DIR")
    if working_dir:
        config.working_dir = working_dir

    # Parse debug flag
    debug_env = os.getenv("CLI_MCP_DEBUG", "true").lower()
    config.debug = debug_env in ("true", "1", "yes", "on")

    return config


# Get configuration
config = parse_config_from_env()
enabled_subagents = set(config.subagents)
working_dir = Path(config.working_dir) if config.working_dir else Path.cwd()

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger.info(f"Initializing Roundtable AI MCP Server")
logger.info(f"Enabled subagents: {', '.join(enabled_subagents)}")
logger.info(f"Working directory: {working_dir}")

# Initialize FastMCP server
server = FastMCP("roundtable-ai")


# Tool definitions
@server.tool
async def check_codex_availability(ctx: Context = None) -> str:
    """
    Check if Codex CLI is available and configured properly.

    Returns:
        Status message about Codex availability
    """
    if "codex" not in enabled_subagents:
        return "❌ Codex subagent is not enabled in this server instance"

    logger.info("Checking Codex availability")

    try:
        from .cli_subagent import check_codex_availability as check_codex
        result = await check_codex()
        logger.debug(f"Codex availability result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error checking Codex availability: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool
async def check_claude_availability(ctx: Context = None) -> str:
    """
    Check if Claude Code CLI is available and configured properly.

    Returns:
        Status message about Claude Code availability
    """
    if "claude" not in enabled_subagents:
        return "❌ Claude subagent is not enabled in this server instance"

    logger.info("Checking Claude Code availability")

    try:
        from .cli_subagent import check_claude_availability as check_claude
        result = await check_claude()
        logger.debug(f"Claude availability result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error checking Claude Code availability: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool
async def check_cursor_availability(ctx: Context = None) -> str:
    """
    Check if Cursor Agent CLI is available and configured properly.

    Returns:
        Status message about Cursor Agent availability
    """
    if "cursor" not in enabled_subagents:
        return "❌ Cursor subagent is not enabled in this server instance"

    logger.info("Checking Cursor Agent availability")

    try:
        from .cli_subagent import check_cursor_availability as check_cursor
        result = await check_cursor()
        logger.debug(f"Cursor availability result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error checking Cursor Agent availability: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool
async def check_gemini_availability(ctx: Context = None) -> str:
    """
    Check if Gemini CLI is available and configured properly.

    Returns:
        Status message about Gemini availability
    """
    if "gemini" not in enabled_subagents:
        return "❌ Gemini subagent is not enabled in this server instance"

    logger.info("Checking Gemini availability")

    try:
        from .cli_subagent import check_gemini_availability as check_gemini
        result = await check_gemini()
        logger.debug(f"Gemini availability result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error checking Gemini availability: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool
async def codex_subagent(
    instruction: str,
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    is_initial_prompt: bool = False,
    ctx: Context = None
) -> str:
    """
    Execute a coding task using Codex CLI agent.

    Codex has access to file operations, shell commands, web search,
    and can make code changes directly. It's ideal for implementing features,
    fixing bugs, refactoring code, and other development tasks.

    IMPORTANT: Always provide an absolute path for project_path to ensure proper execution.
    If you don't provide project_path, the current working directory will be used.

    Args:
        instruction: The coding task or instruction to execute
        project_path: ABSOLUTE path to the project directory (e.g., '/home/user/myproject'). If not provided, uses current working directory.
        session_id: Optional session ID for conversation continuity
        model: Optional model to use (e.g., 'gpt-5', 'claude-3.5-sonnet')
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Codex agent accomplished
    """
    if "codex" not in enabled_subagents:
        return "❌ Codex subagent is not enabled in this server instance"

    # Robust path validation and fallback
    if not project_path or project_path.strip() == "":
        project_path = str(working_dir.absolute()) if working_dir else str(Path.cwd().absolute())
        logger.debug(f"Using fallback directory: {project_path}")
    else:
        # Ensure we have an absolute path
        project_path = str(Path(project_path).absolute())
        logger.debug(f"Using provided project path: {project_path}")

    # Validate the directory exists
    if not Path(project_path).exists():
        error_msg = f"Project directory does not exist: {project_path}"
        logger.error(error_msg)
        return f"❌ {error_msg}"

    logger.info(f"Executing Codex subagent with instruction: {instruction[:100]}...")

    try:
        from .cli_subagent import codex_subagent as codex_exec

        result = await codex_exec(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=None,
            is_initial_prompt=is_initial_prompt
        )

        logger.info("Codex subagent execution completed")
        logger.debug(f"Result summary: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        return result

    except Exception as e:
        error_msg = f"Error executing Codex subagent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool
async def claude_subagent(
    instruction: str,
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    is_initial_prompt: bool = False,
    ctx: Context = None
) -> str:
    """
    Execute a coding task using Claude Code CLI agent.

    Claude Code has access to file operations, shell commands, web search,
    and can make code changes directly. It's ideal for implementing features,
    fixing bugs, refactoring code, and other development tasks.

    IMPORTANT: Always provide an absolute path for project_path to ensure proper execution.
    If you don't provide project_path, the current working directory will be used.

    Args:
        instruction: The coding task or instruction to execute
        project_path: ABSOLUTE path to the project directory (e.g., '/home/user/myproject'). If not provided, uses current working directory.
        session_id: Optional session ID for conversation continuity
        model: Optional model to use (e.g., 'sonnet-4', 'opus-4.1', 'haiku-3.5')
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Claude Code agent accomplished
    """
    if "claude" not in enabled_subagents:
        return "❌ Claude subagent is not enabled in this server instance"

    # Robust path validation and fallback
    if not project_path or project_path.strip() == "":
        project_path = str(working_dir.absolute()) if working_dir else str(Path.cwd().absolute())
        logger.debug(f"Using fallback directory: {project_path}")
    else:
        # Ensure we have an absolute path
        project_path = str(Path(project_path).absolute())
        logger.debug(f"Using provided project path: {project_path}")

    # Validate the directory exists
    if not Path(project_path).exists():
        error_msg = f"Project directory does not exist: {project_path}"
        logger.error(error_msg)
        return f"❌ {error_msg}"

    logger.info(f"Executing Claude subagent with instruction: {instruction[:100]}...")

    try:
        from .cli_subagent import claude_subagent as claude_exec

        result = await claude_exec(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=None,
            is_initial_prompt=is_initial_prompt
        )

        logger.info("Claude subagent execution completed")
        logger.debug(f"Result summary: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        return result

    except Exception as e:
        error_msg = f"Error executing Claude subagent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool
async def cursor_subagent(
    instruction: str,
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    is_initial_prompt: bool = False,
    ctx: Context = None
) -> str:
    """
    Execute a coding task using Cursor Agent CLI.

    Cursor Agent has access to file operations, shell commands, web search,
    and can make code changes directly. It's ideal for implementing features,
    fixing bugs, refactoring code, and other development tasks.

    IMPORTANT: Always provide an absolute path for project_path to ensure proper execution.
    If you don't provide project_path, the current working directory will be used.

    Args:
        instruction: The coding task or instruction to execute
        project_path: ABSOLUTE path to the project directory (e.g., '/home/user/myproject'). If not provided, uses current working directory.
        session_id: Optional session ID for conversation continuity
        model: Optional model to use (e.g., 'gpt-5', 'sonnet-4', 'opus-4.1')
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Cursor Agent accomplished
    """
    if "cursor" not in enabled_subagents:
        return "❌ Cursor subagent is not enabled in this server instance"

    # Robust path validation and fallback
    if not project_path or project_path.strip() == "":
        project_path = str(working_dir.absolute()) if working_dir else str(Path.cwd().absolute())
        logger.debug(f"Using fallback directory: {project_path}")
    else:
        # Ensure we have an absolute path
        project_path = str(Path(project_path).absolute())
        logger.debug(f"Using provided project path: {project_path}")

    # Validate the directory exists
    if not Path(project_path).exists():
        error_msg = f"Project directory does not exist: {project_path}"
        logger.error(error_msg)
        return f"❌ {error_msg}"

    logger.info(f"Executing Cursor subagent with instruction: {instruction[:100]}...")

    try:
        from .cli_subagent import cursor_subagent as cursor_exec

        result = await cursor_exec(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=None,
            is_initial_prompt=is_initial_prompt
        )

        logger.info("Cursor subagent execution completed")
        logger.debug(f"Result summary: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        return result

    except Exception as e:
        error_msg = f"Error executing Cursor subagent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool
async def gemini_subagent(
    instruction: str,
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    is_initial_prompt: bool = False,
    ctx: Context = None
) -> str:
    """
    Execute a coding task using Gemini CLI agent.

    Gemini has access to file operations, shell commands, web search,
    and can make code changes directly. It's ideal for implementing features,
    fixing bugs, refactoring code, and other development tasks.

    IMPORTANT: Always provide an absolute path for project_path to ensure proper execution.
    If you don't provide project_path, the current working directory will be used.

    Args:
        instruction: The coding task or instruction to execute
        project_path: ABSOLUTE path to the project directory (e.g., '/home/user/myproject'). If not provided, uses current working directory.
        session_id: Optional session ID for conversation continuity
        model: Optional model to use (e.g., 'gemini-2.5-pro', 'gemini-2.5-flash')
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Gemini agent accomplished
    """
    if "gemini" not in enabled_subagents:
        return "❌ Gemini subagent is not enabled in this server instance"

    # Robust path validation and fallback
    if not project_path or project_path.strip() == "":
        project_path = str(working_dir.absolute()) if working_dir else str(Path.cwd().absolute())
        logger.debug(f"Using fallback directory: {project_path}")
    else:
        # Ensure we have an absolute path
        project_path = str(Path(project_path).absolute())
        logger.debug(f"Using provided project path: {project_path}")

    # Validate the directory exists
    if not Path(project_path).exists():
        error_msg = f"Project directory does not exist: {project_path}"
        logger.error(error_msg)
        return f"❌ {error_msg}"

    logger.info(f"Executing Gemini subagent with instruction: {instruction[:100]}...")

    try:
        from .cli_subagent import gemini_subagent as gemini_exec

        result = await gemini_exec(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=None,
            is_initial_prompt=is_initial_prompt
        )

        logger.info("Gemini subagent execution completed")
        logger.debug(f"Result summary: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        return result

    except Exception as e:
        error_msg = f"Error executing Gemini subagent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


def main():
    """Main entry point for the MCP server."""
    logger.info("=" * 60)
    logger.info(f"Roundtable AI MCP Server starting at {datetime.now()}")
    logger.info("=" * 60)

    try:
        # Note: FastMCP handles tool filtering via the @server.tool decorators
        # The enabled_subagents check is done in each tool function
        logger.info(f"Enabled subagents: {', '.join(enabled_subagents)}")

        # Run the server
        server.run()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()