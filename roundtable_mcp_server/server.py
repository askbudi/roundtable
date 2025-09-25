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
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import anyio

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field

# Handle imports for both package and direct execution
def _import_module_item(module_name: str, item_name: str):
    """Import an item from a module, handling both package and direct execution."""
    try:
        # Try relative import first (package execution)
        import importlib
        package = __package__ or "roundtable_mcp_server"
        module = importlib.import_module(f".{module_name}", package=package)
        return getattr(module, item_name)
    except (ImportError, ValueError, TypeError):
        # Fall back to absolute import (direct execution)
        current_dir = Path(__file__).parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        import importlib
        module = importlib.import_module(module_name)
        return getattr(module, item_name)

# Import required classes and functions


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

CLIAvailabilityChecker = _import_module_item("availability_checker", "CLIAvailabilityChecker")

# Import CLI adapters directly for MCP streaming with progress
try:
    from claudable_helper.cli.adapters.codex_cli import CodexCLI
    from claudable_helper.cli.adapters.claude_code import ClaudeCodeCLI
    from claudable_helper.cli.adapters.cursor_agent import CursorAgentCLI
    from claudable_helper.cli.adapters.gemini_cli import GeminiCLI
    CLI_ADAPTERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"CLI adapters not available for direct import: {e}")
    CLI_ADAPTERS_AVAILABLE = False



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
    verbose: bool = Field(
        default=False,
        description="Enable verbose output for subagents, showing tool calls and everystep of the execution. "
    )

# Parse configuration from environment and availability cache
def parse_config_from_env() -> ServerConfig:
    """Parse server configuration from environment variables and availability cache.

    Environment variables:
    - CLI_MCP_SUBAGENTS: Comma-separated list of subagents to enable (overrides availability cache)
    - CLI_MCP_WORKING_DIR: Default working directory for subagents
    - CLI_MCP_DEBUG: Enable debug logging (true/false)
    - CLI_MCP_IGNORE_AVAILABILITY: Ignore availability cache and enable all subagents (true/false)

    Returns:
        ServerConfig instance
    """
    config = ServerConfig()

    # Check if we should ignore availability cache
    ignore_availability = os.getenv("CLI_MCP_IGNORE_AVAILABILITY", "true").lower() in ("true", "1", "yes", "on")

    # Parse enabled subagents
    subagents_env = os.getenv("CLI_MCP_SUBAGENTS")
    if subagents_env:
        # Environment variable override - use specified subagents
        subagents = [s.strip().lower() for s in subagents_env.split(",") if s.strip()]
        valid_subagents = {"codex", "claude", "cursor", "gemini"}
        config.subagents = [s for s in subagents if s in valid_subagents]
        config.verbose = os.getenv("CLI_MCP_VERBOSE", "false").lower() in ("true", "1", "yes", "on")
        logger.info(f"Verbose: {config.verbose}")
        invalid = set(subagents) - valid_subagents
        if invalid:
            logger.warning(f"Invalid subagent names ignored: {', '.join(invalid)}")

        logger.info(f"Using subagents from environment variable: {config.subagents}")
    elif ignore_availability:
        # Ignore availability cache and enable all subagents
        config.subagents = ["codex", "claude", "cursor", "gemini"]
        logger.info("Ignoring availability cache - enabling all subagents")
    else:
        # Use availability cache to determine enabled subagents
        checker = CLIAvailabilityChecker()
        available_clis = checker.get_available_clis()

        if available_clis:
            config.subagents = available_clis
            logger.info(f"Using available subagents from cache: {config.subagents}")
        else:
            # Fallback to default if no availability data
            logger.warning("No availability data found, falling back to default subagents")
            logger.warning("Run 'python -m roundtable_mcp_server.availability_checker --check' to check CLI availability")
            config.subagents = ["codex", "claude", "cursor", "gemini"]

    # Parse working directory
    working_dir = os.getenv("CLI_MCP_WORKING_DIR")
    if working_dir:
        config.working_dir = working_dir

    # Parse debug flag
    debug_env = os.getenv("CLI_MCP_DEBUG", "true").lower()
    config.debug = debug_env in ("true", "1", "yes", "on")

    return config


# Global configuration variables (will be set in main())
config = None
enabled_subagents = set()
working_dir = Path.cwd()

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Initialize FastMCP server
server = FastMCP("roundtable-ai")

def initialize_config():
    """Initialize configuration - called from main()."""
    global config, enabled_subagents, working_dir

    config = parse_config_from_env()
    enabled_subagents = set(config.subagents)
    verbose = config.verbose
    working_dir = Path(config.working_dir) if config.working_dir else Path.cwd()

    logger.info(f"Initializing Roundtable AI MCP Server")
    logger.info(f"Enabled subagents: {', '.join(enabled_subagents)}")
    logger.info(f"Working directory: {working_dir}")
    logger.info(f"Verbose: {verbose}")


# Tool definitions
@server.tool()
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
        check_codex = _import_module_item("cli_subagent", "check_codex_availability")
        result = await check_codex()
        logger.debug(f"Codex availability result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error checking Codex availability: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool()
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
        check_claude = _import_module_item("cli_subagent", "check_claude_availability")
        result = await check_claude()
        logger.debug(f"Claude availability result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error checking Claude Code availability: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool()
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
        check_cursor = _import_module_item("cli_subagent", "check_cursor_availability")
        result = await check_cursor()
        logger.debug(f"Cursor availability result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error checking Cursor Agent availability: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool()
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
        check_gemini = _import_module_item("cli_subagent", "check_gemini_availability")
        result = await check_gemini()
        logger.debug(f"Gemini availability result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error checking Gemini availability: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool()
async def codex_subagent(
    instruction: str,
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = 'gpt-5',
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
        model: Optional model to use ( 'gpt-5' is the only supported model)
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Codex agent accomplished
    """

    if "codex" not in enabled_subagents:
        return "❌ Codex subagent is not enabled in this server instance"

    if not CLI_ADAPTERS_AVAILABLE:
        # Fallback to old method if CLI adapters not available
        try:
            codex_exec = _import_module_item("cli_subagent", "codex_subagent")
            result = await codex_exec(
                instruction=instruction,
                project_path=project_path,
                session_id=session_id,
                model=model,
                images=None,
                is_initial_prompt=is_initial_prompt
            )
            return result
        except Exception as e:
            error_msg = f"Error executing Codex subagent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"❌ {error_msg}"

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
    logger.debug(f"[MCP-TOOL] codex_subagent started - project_path: {project_path}, model: {model}, session_id: {session_id}")
    

    try:
        # Initialize CodexCLI directly
        codex_cli = CodexCLI()

        # Check if Codex is available
        availability = await codex_cli.check_availability()
        if not availability.get("available", False):
            error_msg = availability.get("error", "Codex CLI not available")
            logger.error(f"Codex unavailable: {error_msg}")
            return f"❌ Codex CLI not available: {error_msg}"

        # Collect all messages from streaming execution with progress reporting
        messages = []
        agent_responses = []
        tool_uses = []
        message_count = 0
        logger.info(f"Codex subagent execution started :verbose={config.verbose}")
        logger.debug(f"[MCP-TOOL] Codex CLI streaming started - will process messages and report progress")

        async for message in codex_cli.execute_with_streaming(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=None,
            is_initial_prompt=is_initial_prompt
        ):
            message_count += 1
            messages.append(message)

            # Get message type as string
            msg_type = getattr(message, "message_type", None)
            msg_type_str = getattr(msg_type, "value", str(msg_type))

            # Get content with fallback
            content = getattr(message, "content", "")
            content_preview = str(content)[:100] if content else ""

            # Progress reporting with debug logging
            progress_message = f"Codex #{message_count}: {msg_type_str} => {content}"
            logger.debug(f"[PROGRESS] {progress_message}")
            await ctx.report_progress(
                progress=message_count,
                total=None,
                message=progress_message
            )

            # Categorize messages for summary (same logic as cli_subagent.py)
            if hasattr(message, 'role') and message.role == "assistant":
                if message.content and message.content.strip():
                    agent_responses.append(message.content.strip())
            elif msg_type_str == "tool_use":
                tool_uses.append(message.content)
            elif msg_type_str == "tool_result":
                tool_uses.append(f"Tool result: {message.content}")
            elif msg_type_str == "error":
                logger.error(f"Codex error: {message.content}")
                return f"❌ Codex execution failed: {message.content}"
            else:
                # Capture any other message types that might contain useful content
                if message.content and str(message.content).strip():
                    agent_responses.append(str(message.content).strip())

        # Create comprehensive summary (same logic as cli_subagent.py)
        summary_parts = []

        if agent_responses:
            if len(agent_responses) == 1:
                summary_parts.append(f"**Codex Response:**\n{agent_responses[0]}")
            else:
                combined_response = "\n\n".join(agent_responses)
                summary_parts.append(f"**Codex Response:**\n{combined_response}")

        if tool_uses:
            summary_parts.append(f"🔧 **Tools Used ({len(tool_uses)}):**")
            for tool_use in tool_uses:
                summary_parts.append(f"• {tool_use}")

        if not summary_parts:
            summary_parts.append("✅ Codex task completed successfully (no detailed output captured)")

        summary = "\n\n".join(summary_parts)

        logger.info("Codex subagent execution completed")
        logger.debug(f"[MCP-TOOL] Codex execution completed - total messages: {message_count}, agent_responses: {len(agent_responses)}, tool_uses: {len(tool_uses)}")
        logger.debug(f"Result summary: {summary[:200]}..." if len(summary) > 200 else f"Result: {summary}")
        if config.verbose:
            return summary  
        return agent_responses[-1]


    except Exception as e:
        error_msg = f"Error executing Codex subagent: {str(e)}"
        await ctx.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool()
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
    use sonnet-4 model by default unless the task is very complex and need more powerful model. opus-4.1 costs 10X more than sonnet-4. And sonnet-4 is smart enough to handle most tasks.


    Args:
        instruction: The coding task or instruction to execute
        project_path: ABSOLUTE path to the project directory (e.g., '/home/user/myproject'). If not provided, uses current working directory.
        session_id: Optional session ID for conversation continuity
        model: Optional model to use (e.g., 'sonnet-4', 'opus-4.1')
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Claude Code agent accomplished
    """
    if "claude" not in enabled_subagents:
        return "❌ Claude subagent is not enabled in this server instance"

    if not CLI_ADAPTERS_AVAILABLE:
        # Fallback to old method if CLI adapters not available
        try:
            claude_exec = _import_module_item("cli_subagent", "claude_subagent")
            result = await claude_exec(
                instruction=instruction,
                project_path=project_path,
                session_id=session_id,
                model=model,
                images=None,
                is_initial_prompt=is_initial_prompt
            )
            return result
        except Exception as e:
            error_msg = f"Error executing Claude subagent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"❌ {error_msg}"

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
    logger.debug(f"[MCP-TOOL] claude_subagent started - project_path: {project_path}, model: {model}, session_id: {session_id}")

    try:
        # Initialize ClaudeCodeCLI directly
        claude_cli = ClaudeCodeCLI()

        # Check if Claude Code is available
        availability = await claude_cli.check_availability()
        if not availability.get("available", False):
            error_msg = availability.get("error", "Claude Code CLI not available")
            logger.error(f"Claude Code unavailable: {error_msg}")
            return f"❌ Claude Code CLI not available: {error_msg}"

        # Collect all messages from streaming execution with progress reporting
        messages = []
        agent_responses = []
        tool_uses = []
        message_count = 0
        logger.info(f"Claude subagent execution started :verbose={config.verbose}")
        logger.debug(f"[MCP-TOOL] Claude CLI streaming started - will process messages and report progress")

        async for message in claude_cli.execute_with_streaming(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=None,
            is_initial_prompt=is_initial_prompt
        ):
            message_count += 1
            messages.append(message)

            # Get message type as string
            msg_type = getattr(message, "message_type", None)
            msg_type_str = getattr(msg_type, "value", str(msg_type))

            # Get content with fallback
            content = getattr(message, "content", "")
            content_preview = str(content)[:100] if content else ""

            # Progress reporting with debug logging
            progress_message = f"Claude #{message_count}: {msg_type_str} => {content}"
            logger.debug(f"[PROGRESS] {progress_message}")
            await ctx.report_progress(
                progress=message_count,
                total=None,
                message=progress_message
            )

            # Categorize messages for summary (same logic as codex_subagent)
            if hasattr(message, 'role') and message.role == "assistant":
                if message.content and message.content.strip():
                    agent_responses.append(message.content.strip())
            elif msg_type_str == "tool_use":
                tool_uses.append(message.content)
            elif msg_type_str == "tool_result":
                tool_uses.append(f"Tool result: {message.content}")
            elif msg_type_str == "error":
                logger.error(f"Claude Code error: {message.content}")
                return f"❌ Claude Code execution failed: {message.content}"
            elif msg_type_str == "result":
                logger.debug(f"Claude Code result: {message.content}, not adding to agent_responses")
            else:
                # Capture any other message types that might contain useful content
                if message.content and str(message.content).strip():
                    agent_responses.append(str(message.content).strip())

        # Create comprehensive summary (same logic as codex_subagent)
        summary_parts = []

        if agent_responses:
            if len(agent_responses) == 1:
                summary_parts.append(f"**Claude Code Response:**\n{agent_responses[0]}")
            else:
                combined_response = "\n\n".join(agent_responses)
                summary_parts.append(f"**Claude Code Response:**\n{combined_response}")

        if tool_uses:
            summary_parts.append(f"🔧 **Tools Used ({len(tool_uses)}):**")
            for tool_use in tool_uses:
                summary_parts.append(f"• {tool_use}")

        if not summary_parts:
            summary_parts.append("✅ Claude Code task completed successfully (no detailed output captured)")

        summary = "\n\n".join(summary_parts)

        logger.info("Claude subagent execution completed")
        logger.debug(f"[MCP-TOOL] Claude execution completed - total messages: {message_count}, agent_responses: {len(agent_responses)}, tool_uses: {len(tool_uses)}")
        logger.debug(f"Result summary: {summary[:200]}..." if len(summary) > 200 else f"Result: {summary}")
        if config.verbose:
            return summary
        return agent_responses[-1] if agent_responses else "✅ Claude Code task completed successfully"

    except Exception as e:
        error_msg = f"Error executing Claude subagent: {str(e)}"
        await ctx.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool()
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
        model: Optional model to use (e.g., 'gpt-5', 'sonnet-4', 'sonnet-4-thinking')
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
    logger.debug(f"[MCP-TOOL] cursor_subagent started - project_path: {project_path}, model: {model}, session_id: {session_id}")

    # Prefer streaming via adapter (to emit MCP progress), with safe fallback
    try:
        # Try to import adapter class via relative import (works in-package)
        try:
            CursorCLIClass = _import_module_item(
                "claudable_helper.cli.adapters.cursor_agent", "CursorAgentCLI"
            )
            cursor_cli = CursorCLIClass()
            use_adapter = True
        except Exception as imp_err:
            logger.debug(f"Cursor adapter import failed, falling back: {imp_err}")
            use_adapter = False

        if not use_adapter:
            # Fallback to legacy tool wrapper (no streaming)
            cursor_exec = _import_module_item("cli_subagent", "cursor_subagent")
            result = await cursor_exec(
                instruction=instruction,
                project_path=project_path,
                session_id=session_id,
                model=model,
                images=None,
                is_initial_prompt=is_initial_prompt,
            )
            logger.info("Cursor subagent execution completed (fallback mode)")
            logger.debug(
                f"Result summary: {result[:200]}..." if len(result) > 200 else f"Result: {result}"
            )
            return result

        # Adapter path with streaming and progress reporting
        availability = await cursor_cli.check_availability()
        if not availability.get("available", False):
            error_msg = availability.get("error", "Cursor Agent CLI not available")
            logger.error(f"Cursor Agent unavailable: {error_msg}")
            return f"❌ Cursor Agent CLI not available: {error_msg}"

        messages: List[Any] = []
        agent_responses: List[str] = []
        tool_uses: List[str] = []
        message_count = 0
        logger.info(f"Cursor subagent execution started :verbose={config.verbose}")
        logger.debug(f"[MCP-TOOL] Cursor CLI streaming started - will process messages and report progress")

        async for message in cursor_cli.execute_with_streaming(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=None,
            is_initial_prompt=is_initial_prompt,
        ):
            message_count += 1
            messages.append(message)

            # Normalize type and content
            msg_type = getattr(message, "message_type", None)
            msg_type_str = getattr(msg_type, "value", str(msg_type))
            content = getattr(message, "content", "")
            content_preview = str(content)[:100] if content else ""

            # Progress reporting with debug logging
            progress_message = f"Cursor #{message_count}: {msg_type_str} => {content}"
            logger.debug(f"[PROGRESS] {progress_message}")
            try:
                await ctx.report_progress(
                    progress=message_count,
                    total=None,
                    message=progress_message,
                )
            except Exception as e:
                logger.debug(f"Progress reporting failed (non-critical): {e}")

            # Accumulate for summary
            if hasattr(message, "role") and message.role == "assistant":
                if content and str(content).strip():
                    agent_responses.append(str(content).strip())
            elif msg_type_str == "tool_use":
                tool_uses.append(content)
            elif msg_type_str == "tool_result":
                tool_uses.append(f"Tool result: {content}")
            elif msg_type_str == "error":
                logger.error(f"Cursor Agent error: {content}")
                return f"❌ Cursor Agent execution failed: {content}"
            elif msg_type_str == "result":
                logger.debug(f"Cursor final result received: {content[:100]}...")
                # Store the result content for the final response
                if content and str(content).strip():
                    agent_responses.append(str(content).strip())
                # Break the loop as cursor execution is complete
                logger.info("Cursor result received, ending stream")
                break
            else:
                if content and str(content).strip():
                    agent_responses.append(str(content).strip())

        # Build summary
        summary_parts: List[str] = []
        if agent_responses:
            if len(agent_responses) == 1:
                summary_parts.append(f"**Cursor Agent Response:**\n{agent_responses[0]}")
            else:
                combined = "\n\n".join(agent_responses)
                summary_parts.append(f"**Cursor Agent Response:**\n{combined}")
        if tool_uses:
            summary_parts.append(f"🔧 **Tools Used ({len(tool_uses)}):**")
            for t in tool_uses:
                summary_parts.append(f"• {t}")
        if not summary_parts:
            summary_parts.append(
                "✅ Cursor Agent task completed successfully (no detailed output captured)"
            )
        summary = "\n\n".join(summary_parts)

        logger.info("Cursor subagent execution completed")
        logger.debug(f"[MCP-TOOL] Cursor execution completed - total messages: {message_count}, agent_responses: {len(agent_responses)}, tool_uses: {len(tool_uses)}")
        logger.debug(
            f"Result summary: {summary[:200]}..." if len(summary) > 200 else f"Result: {summary}"
        )
        if config.verbose:
            return summary
        return agent_responses[-1] if agent_responses else summary

    except Exception as e:
        error_msg = f"Error executing Cursor subagent: {str(e)}"
        await ctx.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool()
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
        model: Optional model to use ( 'gemini-2.5-pro', 'gemini-2.5-flash' are the only supported models)
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Gemini agent accomplished
    """
    if "gemini" not in enabled_subagents:
        return "❌ Gemini subagent is not enabled in this server instance"

    if not CLI_ADAPTERS_AVAILABLE:
        # Fallback to old method if CLI adapters not available
        try:
            gemini_exec = _import_module_item("cli_subagent", "gemini_subagent")
            result = await gemini_exec(
                instruction=instruction,
                project_path=project_path,
                session_id=session_id,
                model=model,
                images=None,
                is_initial_prompt=is_initial_prompt
            )
            return result
        except Exception as e:
            error_msg = f"Error executing Gemini subagent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"❌ {error_msg}"

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
    logger.debug(f"[MCP-TOOL] gemini_subagent started - project_path: {project_path}, model: {model}, session_id: {session_id}")

    try:
        # Initialize GeminiCLI directly
        gemini_cli = GeminiCLI()

        # Check if Gemini is available
        availability = await gemini_cli.check_availability()
        if not availability.get("available", False):
            error_msg = availability.get("error", "Gemini CLI not available")
            logger.error(f"Gemini unavailable: {error_msg}")
            return f"❌ Gemini CLI not available: {error_msg}"

        # Collect all messages from streaming execution with progress reporting
        messages = []
        agent_responses = []
        tool_uses = []
        message_count = 0
        logger.info(f"Gemini subagent execution started :verbose={config.verbose}")
        logger.debug(f"[MCP-TOOL] Gemini CLI streaming started - will process messages and report progress")

        async for message in gemini_cli.execute_with_streaming(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=None,
            is_initial_prompt=is_initial_prompt
        ):
            message_count += 1
            messages.append(message)

            # Get message type as string
            msg_type = getattr(message, "message_type", None)
            msg_type_str = getattr(msg_type, "value", str(msg_type))

            # Get content with fallback
            content = getattr(message, "content", "")
            content_preview = str(content)[:100] if content else ""

            # Progress reporting with debug logging
            progress_message = f"Gemini #{message_count}: {msg_type_str} => {content}"
            logger.debug(f"[PROGRESS] {progress_message}")
            await ctx.report_progress(
                progress=message_count,
                total=None,
                message=progress_message
            )

            # Categorize messages for summary (same logic as codex_subagent)
            if hasattr(message, 'role') and message.role == "assistant":
                if message.content and message.content.strip():
                    agent_responses.append(message.content.strip())
            elif msg_type_str == "tool_use":
                tool_uses.append(message.content)
            elif msg_type_str == "tool_result":
                tool_uses.append(f"Tool result: {message.content}")
            elif msg_type_str == "error":
                logger.error(f"Gemini error: {message.content}")
                return f"❌ Gemini execution failed: {message.content}"
            elif msg_type_str == "result":
                logger.debug(f"Gemini result: {message.content}, not adding to agent_responses")
            else:
                # Capture any other message types that might contain useful content
                if message.content and str(message.content).strip():
                    agent_responses.append(str(message.content).strip())

        # Create comprehensive summary (same logic as codex_subagent)
        summary_parts = []

        if agent_responses:
            if len(agent_responses) == 1:
                summary_parts.append(f"**Gemini Response:**\n{agent_responses[0]}")
            else:
                combined_response = "\n\n".join(agent_responses)
                summary_parts.append(f"**Gemini Response:**\n{combined_response}")

        if tool_uses:
            summary_parts.append(f"🔧 **Tools Used ({len(tool_uses)}):**")
            for tool_use in tool_uses:
                summary_parts.append(f"• {tool_use}")

        if not summary_parts:
            summary_parts.append("✅ Gemini task completed successfully (no detailed output captured)")

        summary = "\n\n".join(summary_parts)

        logger.info("Gemini subagent execution completed")
        logger.debug(f"[MCP-TOOL] Gemini execution completed - total messages: {message_count}, agent_responses: {len(agent_responses)}, tool_uses: {len(tool_uses)}")
        logger.debug(f"Result summary: {summary[:200]}..." if len(summary) > 200 else f"Result: {summary}")
        if config.verbose:
            return summary
        return agent_responses[-1] if agent_responses else "✅ Gemini task completed successfully"

    except Exception as e:
        error_msg = f"Error executing Gemini subagent: {str(e)}"
        await ctx.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


@server.tool()
async def test_tool(context: Context,signal: bool = True) -> Any:
    """
    Test the tool.
    """
    #await anyio.sleep(15)
    #print("15 seconds passed")
    #await anyio.sleep(18)

    if signal is False:
        await anyio.sleep(40)
        return " Tool tested successfully with signal False (No Progress Update)"
    total_items = 50
    for i in range(total_items):
        # Do work
        await anyio.sleep(1)
        progress_message = f"Processing step {i+1} of {total_items}"
        logger.debug(f"[PROGRESS] {progress_message}")
        await context.debug(progress_message)
        await context.report_progress(
                  progress=i + 1,
                  total=total_items,
                  message=progress_message
              )
    

    return "✅ Tool tested successfully"


async def run_availability_check():
    """Run CLI availability check and save results."""
    availability_main = _import_module_item("availability_checker", "main")
    await availability_main()


def get_version() -> str:
    """Read version from pyproject.toml."""
    try:
        # Get the path to pyproject.toml relative to this file
        current_dir = Path(__file__).parent
        pyproject_path = current_dir.parent / "pyproject.toml"

        if not pyproject_path.exists():
            return "unknown"

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        return pyproject_data.get("project", {}).get("version", "unknown")
    except Exception as e:
        logger.warning(f"Could not read version from pyproject.toml: {e}")
        return "unknown"


def main():
    """Main entry point for the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Roundtable AI MCP Server - CLI Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m roundtable_mcp_server                    # Start MCP server with auto-detected agents
  python -m roundtable_mcp_server --check            # Check CLI availability
  python -m roundtable_mcp_server --agents codex,gemini  # Start with specific agents

Environment Variables:
  CLI_MCP_SUBAGENTS          Comma-separated list of subagents (codex,claude,cursor,gemini)
  CLI_MCP_WORKING_DIR        Default working directory
  CLI_MCP_DEBUG             Enable debug logging (true/false)
  CLI_MCP_IGNORE_AVAILABILITY  Ignore availability cache (true/false)

Priority Order:
  1. Command line --agents flag (highest priority)
  2. Environment variable CLI_MCP_SUBAGENTS
  3. Availability cache from ~/.roundtable/availability_check.json
  4. Default to all agents (lowest priority)
        """
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check CLI availability and save results to ~/.roundtable/availability_check.json"
    )
    parser.add_argument(
        "--agents",
        type=str,
        help="Comma-separated list of agents to enable (codex,claude,cursor,gemini)"
    )

    args = parser.parse_args()

    if args.check:
        # Run availability check
        print("🔍 Checking CLI availability...")
        try:
            asyncio.run(run_availability_check())
        except Exception as e:
            logger.error(f"Availability check failed: {e}")
            sys.exit(1)
        return

    # If --agents flag is provided, set it as environment variable (highest priority)
    if args.agents:
        os.environ["CLI_MCP_SUBAGENTS"] = args.agents
        print(f"📋 Using agents from command line: {args.agents}")

    # Initialize configuration after processing command line arguments
    initialize_config()

    # Normal server startup
    version = get_version()
    logger.info("=" * 60)
    logger.info(f"Roundtable AI MCP Server v{version} starting at {datetime.now()}")
    logger.info("=" * 60)

    try:
        # Note: FastMCP handles tool filtering via the @server.tool() decorators
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
