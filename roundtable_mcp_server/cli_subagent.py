"""CLI Subagent Tools for TinyAgent.

This module integrates CLI adapters as TinyAgent tools, allowing TinyAgent
to execute tasks through various CLI providers like Codex, Cursor, Claude, etc.
Each CLI adapter becomes a specialized tool that TinyAgent can use.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any, AsyncGenerator
from pathlib import Path

from tinyagent import tool, TinyCodeAgent
from claudable_helper.cli.adapters.codex_cli import CodexCLI
from claudable_helper.cli.adapters.claude_code import ClaudeCodeCLI
from claudable_helper.cli.adapters.cursor_agent import CursorAgentCLI
from claudable_helper.cli.adapters.gemini_cli import GeminiCLI
from claudable_helper.core.terminal_ui import ui
from claudable_helper.models.messages import Message


# Global CLI adapter instances
_codex_cli = None
_claude_cli = None
_cursor_cli = None
_gemini_cli = None


def _check_claude_code_sdk() -> tuple[bool, str]:
    """Check if claude_code_sdk is available.

    Returns:
        Tuple of (is_available, error_message)
    """
    try:
        import claude_code_sdk
        ui.debug("claude_code_sdk is available", "ClaudeSetup")
        return True, ""
    except ImportError:
        error_msg = (
            "claude_code_sdk is required but not installed. "
            "Please install it using: pip install claude_code_sdk"
        )
        ui.warning(error_msg, "ClaudeSetup")
        return False, error_msg


async def get_codex_cli() -> CodexCLI:
    """Get or create a CodexCLI instance."""
    global _codex_cli
    if _codex_cli is None:
        _codex_cli = CodexCLI()
    return _codex_cli


async def get_claude_cli() -> ClaudeCodeCLI:
    """Get or create a ClaudeCodeCLI instance."""
    global _claude_cli
    if _claude_cli is None:
        # Check if claude_code_sdk is available before creating CLI instance
        is_available, error_msg = _check_claude_code_sdk()
        if not is_available:
            raise RuntimeError(error_msg)
        _claude_cli = ClaudeCodeCLI()
    return _claude_cli


async def get_cursor_cli() -> CursorAgentCLI:
    """Get or create a CursorAgentCLI instance."""
    global _cursor_cli
    if _cursor_cli is None:
        _cursor_cli = CursorAgentCLI()
    return _cursor_cli


async def get_gemini_cli() -> GeminiCLI:
    """Get or create a GeminiCLI instance."""
    global _gemini_cli
    if _gemini_cli is None:
        _gemini_cli = GeminiCLI()
    return _gemini_cli


@tool(
    name="codex_subagent",
    description="""Execute a coding task using Codex CLI agent.

    This tool runs a Codex instance to perform complex coding tasks autonomously.
    Codex has access to file operations, shell commands, web search, and can make
    code changes directly. It's ideal for implementing features, fixing bugs,
    refactoring code, and other development tasks.

    The tool will stream back the agent's progress and any code changes made.
    """
)
async def codex_subagent(
    instruction: str,
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    images: Optional[List[Dict[str, Any]]] = None,
    is_initial_prompt: bool = False
) -> str:
    """Execute a coding task using Codex CLI agent.

    Args:
        instruction: The coding task or instruction to execute
        project_path: Path to the project directory where work should be done
        session_id: Optional session ID for conversation continuity
        model: Optional model to use (e.g., 'gpt-5', 'claude-3.5-sonnet')
        images: Optional list of image data for visual tasks
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Codex agent accomplished
    """
    try:
        # Get Codex CLI instance
        codex_cli = await get_codex_cli()

        # Check if Codex is available
        availability = await codex_cli.check_availability()
        if not availability.get("available", False):
            error_msg = availability.get("error", "Codex CLI not available")
            ui.error(f"Codex unavailable: {error_msg}", "CodexSubagent")
            return f"❌ Codex CLI not available: {error_msg}"

        # Robust path validation and fallback
        if not project_path or project_path.strip() == "":
            project_path = str(Path.cwd().absolute())
            ui.debug(f"Using fallback directory: {project_path}", "CodexSubagent")
        else:
            # Ensure we have an absolute path
            project_path = str(Path(project_path).absolute())
            ui.debug(f"Using provided project path: {project_path}", "CodexSubagent")

        # Validate the directory exists
        if not Path(project_path).exists():
            error_msg = f"Project directory does not exist: {project_path}"
            ui.error(error_msg, "CodexSubagent")
            return f"❌ {error_msg}"

        ui.info(f"Starting Codex subagent task: {instruction[:50]}...", "CodexSubagent")

        # Collect all messages from streaming execution
        messages = []
        agent_responses = []
        tool_uses = []

        async for message in codex_cli.execute_with_streaming(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=images,
            is_initial_prompt=is_initial_prompt
        ):
            messages.append(message)

            # Debug: Print all message details to understand structure
            ui.debug(f"Message received - Type: {message.message_type}, Role: {getattr(message, 'role', 'N/A')}, Content preview: {str(message.content)[:100]}...", "CodexSubagent")

            # Categorize messages for summary - be more permissive
            msg_type = getattr(message, "message_type", None)
            msg_type_str = getattr(msg_type, "value", msg_type)

            if hasattr(message, 'role') and message.role == "assistant":
                if message.content and message.content.strip():
                    agent_responses.append(message.content.strip())
                    ui.debug(f"Captured assistant response: {len(message.content)} chars", "CodexSubagent")
            elif msg_type_str == "tool_use":
                tool_uses.append(message.content)
                ui.debug(f"Captured tool use: {message.content}", "CodexSubagent")
            elif msg_type_str == "tool_result":
                tool_uses.append(f"Tool result: {message.content}")
                ui.debug(f"Captured tool result: {str(message.content)[:50]}...", "CodexSubagent")
            elif msg_type_str == "error":
                ui.error(f"Codex error: {message.content}", "CodexSubagent")
                return f"❌ Codex execution failed: {message.content}"
            else:
                # Capture any other message types that might contain useful content
                if message.content and str(message.content).strip():
                    agent_responses.append(str(message.content).strip())
                    ui.debug(f"Captured other message type '{msg_type_str}': {str(message.content)[:50]}...", "CodexSubagent")

        # Create comprehensive summary
        summary_parts = []

        ui.debug(f"Processing summary - Agent responses: {len(agent_responses)}, Tool uses: {len(tool_uses)}", "CodexSubagent")

        if agent_responses:
            # Combine all responses, not just the longest one
            if len(agent_responses) == 1:
                summary_parts.append(f"🤖 **Codex Agent Response:**\n{agent_responses[0]}")
            else:
                # If multiple responses, combine them intelligently
                combined_response = "\n\n".join(agent_responses)
                summary_parts.append(f"🤖 **Codex Agent Response:**\n{combined_response}")
            ui.debug(f"Added agent response to summary: {len(agent_responses)} responses", "CodexSubagent")

        if tool_uses:
            summary_parts.append(f"🔧 **Tools Used ({len(tool_uses)}):**")
            for tool_use in tool_uses:
                summary_parts.append(f"• {tool_use}")
            ui.debug(f"Added tool uses to summary: {len(tool_uses)} tools", "CodexSubagent")

        if not summary_parts:
            ui.warning("No responses or tool uses captured - this might indicate an issue", "CodexSubagent")
            summary_parts.append("✅ Codex task completed successfully (no detailed output captured)")

        summary = "\n\n".join(summary_parts)
        ui.debug(f"Final summary length: {len(summary)} characters", "CodexSubagent")

        ui.success(f"Codex subagent completed task", "CodexSubagent")
        return summary

    except Exception as e:
        error_msg = f"Codex subagent execution failed: {str(e)}"
        ui.error(error_msg, "CodexSubagent")
        return f"❌ {error_msg}"


@tool(
    name="claude_subagent",
    description="""Execute a coding task using Claude Code CLI agent.

    This tool runs a Claude Code instance to perform complex coding tasks autonomously.
    Claude Code has access to file operations, shell commands, web search, and can make
    code changes directly. It's ideal for implementing features, fixing bugs,
    refactoring code, and other development tasks.

    The tool will stream back the agent's progress and any code changes made.
    """
)
async def claude_subagent(
    instruction: str,
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    images: Optional[List[Dict[str, Any]]] = None,
    is_initial_prompt: bool = False
) -> str:
    """Execute a coding task using Claude Code CLI agent.

    Args:
        instruction: The coding task or instruction to execute
        project_path: Path to the project directory where work should be done
        session_id: Optional session ID for conversation continuity
        model: Optional model to use (e.g., 'sonnet-4', 'opus-4.1', 'haiku-3.5')
        images: Optional list of image data for visual tasks
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Claude Code agent accomplished
    """
    try:
        # Get Claude CLI instance (this will check for claude_code_sdk)
        try:
            claude_cli = await get_claude_cli()
        except RuntimeError as e:
            error_msg = str(e)
            ui.error(f"Claude Code setup failed: {error_msg}", "ClaudeSubagent")
            return f"❌ Claude Code setup failed: {error_msg}"

        # Check if Claude Code is available
        availability = await claude_cli.check_availability()
        if not availability.get("available", False):
            error_msg = availability.get("error", "Claude Code CLI not available")
            ui.error(f"Claude Code unavailable: {error_msg}", "ClaudeSubagent")
            return f"❌ Claude Code CLI not available: {error_msg}"

        # Robust path validation and fallback
        if not project_path or project_path.strip() == "":
            project_path = str(Path.cwd().absolute())
            ui.debug(f"Using fallback directory: {project_path}", "ClaudeSubagent")
        else:
            # Ensure we have an absolute path
            project_path = str(Path(project_path).absolute())
            ui.debug(f"Using provided project path: {project_path}", "ClaudeSubagent")

        # Validate the directory exists
        if not Path(project_path).exists():
            error_msg = f"Project directory does not exist: {project_path}"
            ui.error(error_msg, "ClaudeSubagent")
            return f"❌ {error_msg}"

        ui.info(f"Starting Claude Code subagent task: {instruction[:50]}...", "ClaudeSubagent")

        # Collect all messages from streaming execution
        messages = []
        agent_responses = []
        tool_uses = []

        async for message in claude_cli.execute_with_streaming(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=images,
            is_initial_prompt=is_initial_prompt
        ):
            messages.append(message)

            # Debug: Print all message details to understand structure
            ui.debug(f"Message received - Type: {message.message_type}, Role: {getattr(message, 'role', 'N/A')}, Content preview: {str(message.content)[:100]}...", "ClaudeSubagent")

            # Categorize messages for summary - be more permissive
            msg_type = getattr(message, "message_type", None)
            msg_type_str = getattr(msg_type, "value", msg_type)

            if hasattr(message, 'role') and message.role == "assistant":
                if message.content and message.content.strip():
                    agent_responses.append(message.content.strip())
                    ui.debug(f"Captured assistant response: {len(message.content)} chars", "ClaudeSubagent")
            elif msg_type_str == "tool_use":
                tool_uses.append(message.content)
                ui.debug(f"Captured tool use: {message.content}", "ClaudeSubagent")
            elif msg_type_str == "tool_result":
                tool_uses.append(f"Tool result: {message.content}")
                ui.debug(f"Captured tool result: {str(message.content)[:50]}...", "ClaudeSubagent")
            elif msg_type_str == "error":
                ui.error(f"Claude Code error: {message.content}", "ClaudeSubagent")
                return f"❌ Claude Code execution failed: {message.content}"
            else:
                # Capture any other message types that might contain useful content
                if message.content and str(message.content).strip():
                    agent_responses.append(str(message.content).strip())
                    ui.debug(f"Captured other message type '{msg_type_str}': {str(message.content)[:50]}...", "ClaudeSubagent")

        # Create comprehensive summary
        summary_parts = []

        ui.debug(f"Processing summary - Agent responses: {len(agent_responses)}, Tool uses: {len(tool_uses)}", "ClaudeSubagent")

        if agent_responses:
            # Combine all responses, not just the longest one
            if len(agent_responses) == 1:
                summary_parts.append(f"🤖 **Claude Code Agent Response:**\n{agent_responses[0]}")
            else:
                # If multiple responses, combine them intelligently
                combined_response = "\n\n".join(agent_responses)
                summary_parts.append(f"🤖 **Claude Code Agent Response:**\n{combined_response}")
            ui.debug(f"Added agent response to summary: {len(agent_responses)} responses", "ClaudeSubagent")

        if tool_uses:
            summary_parts.append(f"🔧 **Tools Used ({len(tool_uses)}):**")
            for tool_use in tool_uses:
                summary_parts.append(f"• {tool_use}")
            ui.debug(f"Added tool uses to summary: {len(tool_uses)} tools", "ClaudeSubagent")

        if not summary_parts:
            ui.warning("No responses or tool uses captured - this might indicate an issue", "ClaudeSubagent")
            summary_parts.append("✅ Claude Code task completed successfully (no detailed output captured)")

        summary = "\n\n".join(summary_parts)
        ui.debug(f"Final summary length: {len(summary)} characters", "ClaudeSubagent")

        ui.success(f"Claude Code subagent completed task", "ClaudeSubagent")
        return summary

    except Exception as e:
        error_msg = f"Claude Code subagent execution failed: {str(e)}"
        ui.error(error_msg, "ClaudeSubagent")
        return f"❌ {error_msg}"


@tool(
    name="check_codex_availability",
    description="Check if Codex CLI is available and configured properly"
)
async def check_codex_availability() -> str:
    """Check if Codex CLI is available and configured.

    Returns:
        Status message about Codex availability
    """
    try:
        codex_cli = await get_codex_cli()
        availability = await codex_cli.check_availability()

        if availability.get("available", False):
            models = availability.get("models", [])
            default_models = availability.get("default_models", [])

            status_parts = ["✅ **Codex CLI Available**"]
            if default_models:
                status_parts.append(f"📋 **Default Models:** {', '.join(default_models)}")
            if models:
                status_parts.append(f"🔧 **All Models:** {len(models)} available")

            return "\n".join(status_parts)
        else:
            error = availability.get("error", "Unknown error")
            return f"❌ **Codex CLI Unavailable:** {error}"

    except Exception as e:
        return f"❌ **Error checking Codex:** {str(e)}"


@tool(
    name="check_claude_availability",
    description="Check if Claude Code CLI is available and configured properly"
)
async def check_claude_availability() -> str:
    """Check if Claude Code CLI is available and configured.

    Returns:
        Status message about Claude Code availability
    """
    try:
        # This will check for claude_code_sdk availability
        try:
            claude_cli = await get_claude_cli()
        except RuntimeError as e:
            return f"❌ **Claude Code Setup Failed:** {str(e)}"

        availability = await claude_cli.check_availability()

        if availability.get("available", False):
            models = availability.get("models", [])
            default_models = availability.get("default_models", [])

            status_parts = ["✅ **Claude Code CLI Available**"]
            if default_models:
                status_parts.append(f"📋 **Default Models:** {', '.join(default_models)}")
            if models:
                status_parts.append(f"🔧 **All Models:** {len(models)} available")

            return "\n".join(status_parts)
        else:
            error = availability.get("error", "Unknown error")
            return f"❌ **Claude Code CLI Unavailable:** {error}"

    except Exception as e:
        return f"❌ **Error checking Claude Code:** {str(e)}"


@tool(
    name="cursor_subagent",
    description="""Execute a coding task using Cursor Agent CLI.

    This tool runs a Cursor Agent instance to perform complex coding tasks autonomously.
    Cursor Agent has access to file operations, shell commands, web search, and can make
    code changes directly. It's ideal for implementing features, fixing bugs,
    refactoring code, and other development tasks.

    The tool will stream back the agent's progress and any code changes made.
    """
)
async def cursor_subagent(
    instruction: str,
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    images: Optional[List[Dict[str, Any]]] = None,
    is_initial_prompt: bool = False
) -> str:
    """Execute a coding task using Cursor Agent CLI.

    Args:
        instruction: The coding task or instruction to execute
        project_path: Path to the project directory where work should be done
        session_id: Optional session ID for conversation continuity
        model: Optional model to use (e.g., 'gpt-5', 'sonnet-4', 'opus-4.1')
        images: Optional list of image data for visual tasks
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Cursor Agent accomplished
    """
    try:
        # Get Cursor CLI instance
        cursor_cli = await get_cursor_cli()

        # Check if Cursor Agent is available
        availability = await cursor_cli.check_availability()
        if not availability.get("available", False):
            error_msg = availability.get("error", "Cursor Agent CLI not available")
            ui.error(f"Cursor Agent unavailable: {error_msg}", "CursorSubagent")
            return f"❌ Cursor Agent CLI not available: {error_msg}"

        # Robust path validation and fallback
        if not project_path or project_path.strip() == "":
            project_path = str(Path.cwd().absolute())
            ui.debug(f"Using fallback directory: {project_path}", "CursorSubagent")
        else:
            # Ensure we have an absolute path
            project_path = str(Path(project_path).absolute())
            ui.debug(f"Using provided project path: {project_path}", "CursorSubagent")

        # Validate the directory exists
        if not Path(project_path).exists():
            error_msg = f"Project directory does not exist: {project_path}"
            ui.error(error_msg, "CursorSubagent")
            return f"❌ {error_msg}"

        ui.info(f"Starting Cursor Agent subagent task: {instruction[:50]}...", "CursorSubagent")

        # Collect all messages from streaming execution
        messages = []
        agent_responses = []
        tool_uses = []

        async for message in cursor_cli.execute_with_streaming(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=images,
            is_initial_prompt=is_initial_prompt
        ):
            messages.append(message)

            # Debug: Print all message details to understand structure
            ui.debug(f"Message received - Type: {message.message_type}, Role: {getattr(message, 'role', 'N/A')}, Content preview: {str(message.content)[:100]}...", "CursorSubagent")

            # Categorize messages for summary - be more permissive
            msg_type = getattr(message, "message_type", None)
            msg_type_str = getattr(msg_type, "value", msg_type)

            if hasattr(message, 'role') and message.role == "assistant":
                if message.content and message.content.strip():
                    agent_responses.append(message.content.strip())
                    ui.debug(f"Captured assistant response: {len(message.content)} chars", "CursorSubagent")
            elif msg_type_str == "tool_use":
                tool_uses.append(message.content)
                ui.debug(f"Captured tool use: {message.content}", "CursorSubagent")
            elif msg_type_str == "tool_result":
                tool_uses.append(f"Tool result: {message.content}")
                ui.debug(f"Captured tool result: {str(message.content)[:50]}...", "CursorSubagent")
            elif msg_type_str == "error":
                ui.error(f"Cursor Agent error: {message.content}", "CursorSubagent")
                return f"❌ Cursor Agent execution failed: {message.content}"
            else:
                # Capture any other message types that might contain useful content
                if message.content and str(message.content).strip():
                    agent_responses.append(str(message.content).strip())
                    ui.debug(f"Captured other message type '{msg_type_str}': {str(message.content)[:50]}...", "CursorSubagent")

        # Create comprehensive summary
        summary_parts = []

        ui.debug(f"Processing summary - Agent responses: {len(agent_responses)}, Tool uses: {len(tool_uses)}", "CursorSubagent")

        if agent_responses:
            # Combine all responses, not just the longest one
            if len(agent_responses) == 1:
                summary_parts.append(f"🤖 **Cursor Agent Response:**\n{agent_responses[0]}")
            else:
                # If multiple responses, combine them intelligently
                combined_response = "\n\n".join(agent_responses)
                summary_parts.append(f"🤖 **Cursor Agent Response:**\n{combined_response}")
            ui.debug(f"Added agent response to summary: {len(agent_responses)} responses", "CursorSubagent")

        if tool_uses:
            summary_parts.append(f"🔧 **Tools Used ({len(tool_uses)}):**")
            for tool_use in tool_uses:
                summary_parts.append(f"• {tool_use}")
            ui.debug(f"Added tool uses to summary: {len(tool_uses)} tools", "CursorSubagent")

        if not summary_parts:
            ui.warning("No responses or tool uses captured - this might indicate an issue", "CursorSubagent")
            summary_parts.append("✅ Cursor Agent task completed successfully (no detailed output captured)")

        summary = "\n\n".join(summary_parts)
        ui.debug(f"Final summary length: {len(summary)} characters", "CursorSubagent")

        ui.success(f"Cursor Agent subagent completed task", "CursorSubagent")
        return summary

    except Exception as e:
        error_msg = f"Cursor Agent subagent execution failed: {str(e)}"
        ui.error(error_msg, "CursorSubagent")
        return f"❌ {error_msg}"


@tool(
    name="check_cursor_availability",
    description="Check if Cursor Agent CLI is available and configured properly"
)
async def check_cursor_availability() -> str:
    """Check if Cursor Agent CLI is available and configured.

    Returns:
        Status message about Cursor Agent availability
    """
    try:
        cursor_cli = await get_cursor_cli()
        availability = await cursor_cli.check_availability()

        if availability.get("available", False):
            models = availability.get("models", [])
            default_models = availability.get("default_models", [])

            status_parts = ["✅ **Cursor Agent CLI Available**"]
            if default_models:
                status_parts.append(f"📋 **Default Models:** {', '.join(default_models)}")
            if models:
                status_parts.append(f"🔧 **All Models:** {len(models)} available")

            return "\n".join(status_parts)
        else:
            error = availability.get("error", "Unknown error")
            return f"❌ **Cursor Agent CLI Unavailable:** {error}"

    except Exception as e:
        return f"❌ **Error checking Cursor Agent:** {str(e)}"


@tool(
    name="gemini_subagent",
    description="""Execute a coding task using Gemini CLI agent.

    This tool runs a Gemini CLI instance to perform complex coding tasks autonomously.
    Gemini has access to file operations, shell commands, web search, and can make
    code changes directly. It's ideal for implementing features, fixing bugs,
    refactoring code, and other development tasks.

    The tool will stream back the agent's progress and any code changes made.
    """
)
async def gemini_subagent(
    instruction: str,
    project_path: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    images: Optional[List[Dict[str, Any]]] = None,
    is_initial_prompt: bool = False
) -> str:
    """Execute a coding task using Gemini CLI agent.

    Args:
        instruction: The coding task or instruction to execute
        project_path: Path to the project directory where work should be done
        session_id: Optional session ID for conversation continuity
        model: Optional model to use (e.g., 'gemini-2.5-pro', 'gemini-2.5-flash')
        images: Optional list of image data for visual tasks
        is_initial_prompt: Whether this is the first prompt in a new session

    Returns:
        Summary of what the Gemini agent accomplished
    """
    try:
        # Get Gemini CLI instance
        gemini_cli = await get_gemini_cli()

        # Check if Gemini is available
        availability = await gemini_cli.check_availability()
        if not availability.get("available", False):
            error_msg = availability.get("error", "Gemini CLI not available")
            ui.error(f"Gemini unavailable: {error_msg}", "GeminiSubagent")
            return f"❌ Gemini CLI not available: {error_msg}"

        # Robust path validation and fallback
        if not project_path or project_path.strip() == "":
            project_path = str(Path.cwd().absolute())
            ui.debug(f"Using fallback directory: {project_path}", "GeminiSubagent")
        else:
            # Ensure we have an absolute path
            project_path = str(Path(project_path).absolute())
            ui.debug(f"Using provided project path: {project_path}", "GeminiSubagent")

        # Validate the directory exists
        if not Path(project_path).exists():
            error_msg = f"Project directory does not exist: {project_path}"
            ui.error(error_msg, "GeminiSubagent")
            return f"❌ {error_msg}"

        ui.info(f"Starting Gemini subagent task: {instruction[:50]}...", "GeminiSubagent")

        # Collect all messages from streaming execution
        messages = []
        agent_responses = []
        tool_uses = []

        async for message in gemini_cli.execute_with_streaming(
            instruction=instruction,
            project_path=project_path,
            session_id=session_id,
            model=model,
            images=images,
            is_initial_prompt=is_initial_prompt
        ):
            messages.append(message)

            # Debug: Print all message details to understand structure
            ui.debug(f"Message received - Type: {message.message_type}, Role: {getattr(message, 'role', 'N/A')}, Content preview: {str(message.content)[:100]}...", "GeminiSubagent")

            # Categorize messages for summary - be more permissive
            msg_type = getattr(message, "message_type", None)
            msg_type_str = getattr(msg_type, "value", msg_type)

            if hasattr(message, 'role') and message.role == "assistant":
                if message.content and message.content.strip():
                    agent_responses.append(message.content.strip())
                    ui.debug(f"Captured assistant response: {len(message.content)} chars", "GeminiSubagent")
            elif msg_type_str == "tool_use":
                tool_uses.append(message.content)
                ui.debug(f"Captured tool use: {message.content}", "GeminiSubagent")
            elif msg_type_str == "tool_result":
                tool_uses.append(f"Tool result: {message.content}")
                ui.debug(f"Captured tool result: {str(message.content)[:50]}...", "GeminiSubagent")
            elif msg_type_str == "error":
                ui.error(f"Gemini error: {message.content}", "GeminiSubagent")
                return f"❌ Gemini execution failed: {message.content}"
            else:
                # Capture any other message types that might contain useful content
                if message.content and str(message.content).strip():
                    agent_responses.append(str(message.content).strip())
                    ui.debug(f"Captured other message type '{msg_type_str}': {str(message.content)[:50]}...", "GeminiSubagent")

        # Create comprehensive summary
        summary_parts = []

        ui.debug(f"Processing summary - Agent responses: {len(agent_responses)}, Tool uses: {len(tool_uses)}", "GeminiSubagent")

        if agent_responses:
            # Combine all responses, not just the longest one
            if len(agent_responses) == 1:
                summary_parts.append(f"🤖 **Gemini Agent Response:**\n{agent_responses[0]}")
            else:
                # If multiple responses, combine them intelligently
                combined_response = "\n\n".join(agent_responses)
                summary_parts.append(f"🤖 **Gemini Agent Response:**\n{combined_response}")
            ui.debug(f"Added agent response to summary: {len(agent_responses)} responses", "GeminiSubagent")

        if tool_uses:
            summary_parts.append(f"🔧 **Tools Used ({len(tool_uses)}):**")
            for tool_use in tool_uses:
                summary_parts.append(f"• {tool_use}")
            ui.debug(f"Added tool uses to summary: {len(tool_uses)} tools", "GeminiSubagent")

        if not summary_parts:
            ui.warning("No responses or tool uses captured - this might indicate an issue", "GeminiSubagent")
            summary_parts.append("✅ Gemini task completed successfully (no detailed output captured)")

        summary = "\n\n".join(summary_parts)
        ui.debug(f"Final summary length: {len(summary)} characters", "GeminiSubagent")

        ui.success(f"Gemini subagent completed task", "GeminiSubagent")
        return summary

    except Exception as e:
        error_msg = f"Gemini subagent execution failed: {str(e)}"
        ui.error(error_msg, "GeminiSubagent")
        return f"❌ {error_msg}"


@tool(
    name="check_gemini_availability",
    description="Check if Gemini CLI is available and configured properly"
)
async def check_gemini_availability() -> str:
    """Check if Gemini CLI is available and configured.

    Returns:
        Status message about Gemini availability
    """
    try:
        gemini_cli = await get_gemini_cli()
        availability = await gemini_cli.check_availability()

        if availability.get("available", False):
            models = availability.get("models", [])
            default_models = availability.get("default_models", [])

            status_parts = ["✅ **Gemini CLI Available**"]
            if default_models:
                status_parts.append(f"📋 **Default Models:** {', '.join(default_models)}")
            if models:
                status_parts.append(f"🔧 **All Models:** {len(models)} available")

            return "\n".join(status_parts)
        else:
            error = availability.get("error", "Unknown error")
            return f"❌ **Gemini CLI Unavailable:** {error}"

    except Exception as e:
        return f"❌ **Error checking Gemini:** {str(e)}"


class CLISubagentManager:
    """Manager for CLI subagent tools and TinyAgent integration."""

    def __init__(self):
        self.available_tools = {
            "codex_subagent": codex_subagent,
            "check_codex_availability": check_codex_availability,
            "claude_subagent": claude_subagent,
            "check_claude_availability": check_claude_availability,
            "cursor_subagent": cursor_subagent,
            "check_cursor_availability": check_cursor_availability,
            "gemini_subagent": gemini_subagent,
            "check_gemini_availability": check_gemini_availability,
        }

    async def create_code_agent(
        self,
        model: str = "gpt-4o",
        system_prompt: Optional[str] = None,
        additional_tools: Optional[List] = None
    ) -> TinyCodeAgent:
        """Create a TinyCodeAgent with CLI subagent tools.

        Args:
            model: Model to use for the agent
            system_prompt: Optional custom system prompt
            additional_tools: Additional tools to include

        Returns:
            Configured TinyCodeAgent instance
        """
        # Default system prompt for CLI subagent
        if system_prompt is None:
            system_prompt = """You are a coding assistant with access to powerful CLI subagents.

You have access to specialized subagents:

The subagents will handle file operations, code changes, testing, and execution.
Focus on task planning and coordination rather than direct implementation."""

        # Prepare tools list
        tools = list(self.available_tools.values())
        if additional_tools:
            tools.extend(additional_tools)

        # Create TinyCodeAgent with CLI tools and debug mode
        agent = TinyCodeAgent(
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            local_execution=True,
            tool_call_timeout=180,
            debug_mode=True,  # Enable debug mode for detailed execution logging
            model_kwargs={
                "reasoning":{"effort": "minimal"},
                "llm_api": "responses"
            }
        )

        return agent

    def list_available_tools(self) -> List[str]:
        """List names of available CLI subagent tools."""
        return list(self.available_tools.keys())

    async def check_all_cli_availability(self) -> Dict[str, Any]:
        """Check availability of all CLI providers.

        Returns:
            Dictionary with availability status for each CLI
        """
        status = {}

        # Check Codex
        try:
            codex_status = await check_codex_availability()
            status["codex"] = {
                "available": "✅" in codex_status,
                "status": codex_status
            }
        except Exception as e:
            status["codex"] = {
                "available": False,
                "status": f"❌ Error: {str(e)}"
            }

        # Check Claude Code
        try:
            claude_status = await check_claude_availability()
            status["claude"] = {
                "available": "✅" in claude_status,
                "status": claude_status
            }
        except Exception as e:
            status["claude"] = {
                "available": False,
                "status": f"❌ Error: {str(e)}"
            }

        # Check Cursor Agent
        try:
            cursor_status = await check_cursor_availability()
            status["cursor"] = {
                "available": "✅" in cursor_status,
                "status": cursor_status
            }
        except Exception as e:
            status["cursor"] = {
                "available": False,
                "status": f"❌ Error: {str(e)}"
            }

        # Check Gemini
        try:
            gemini_status = await check_gemini_availability()
            status["gemini"] = {
                "available": "✅" in gemini_status,
                "status": gemini_status
            }
        except Exception as e:
            status["gemini"] = {
                "available": False,
                "status": f"❌ Error: {str(e)}"
            }

        return status


# Global manager instance
cli_manager = CLISubagentManager()


async def create_cli_code_agent(
    model: str = "groq/moonshotai/kimi-k2-instruct",
    system_prompt: Optional[str] = None,
    additional_tools: Optional[List] = None
) -> TinyCodeAgent:
    """Convenience function to create a TinyCodeAgent with CLI subagent tools.

    Args:
        model: Model to use for the agent
        system_prompt: Optional custom system prompt
        additional_tools: Additional tools to include

    Returns:
        Configured TinyCodeAgent instance
    """
    agent = await cli_manager.create_code_agent(
        model=model,
        system_prompt=system_prompt,
        
        additional_tools=additional_tools
    )
    from tinyagent.hooks import MessageCleanupHook
    agent.callbacks.append(MessageCleanupHook())
    return agent


__all__ = [
    "codex_subagent",
    "check_codex_availability",
    "claude_subagent",
    "check_claude_availability",
    "cursor_subagent",
    "check_cursor_availability",
    "gemini_subagent",
    "check_gemini_availability",
    "CLISubagentManager",
    "cli_manager",
    "create_cli_code_agent"
]
