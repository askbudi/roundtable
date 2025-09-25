"""Claude Code provider implementation.

Moved from unified_manager.py to a dedicated adapter module.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from claudable_helper.core.terminal_ui import ui
from claudable_helper.models.messages import Message
try:
    from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
except ImportError:
    # Fall back to mock implementation
    from claudable_helper.external.claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..base import BaseCLI, CLIType


class ClaudeCodeCLI(BaseCLI):
    """Claude Code Python SDK implementation"""

    def __init__(self):
        super().__init__(CLIType.CLAUDE)
        self.session_mapping: Dict[str, str] = {}  # Simple in-memory session storage

    async def check_availability(self) -> Dict[str, Any]:
        """Check if Claude Code CLI is available"""
        try:
            # First try to check if claude CLI is installed and working
            result = await asyncio.create_subprocess_shell(
                "claude -h",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                return {
                    "available": False,
                    "configured": False,
                    "error": (
                        "Claude Code CLI not installed or not working.\n\nTo install:\n"
                        "1. Install Claude Code: npm install -g @anthropic-ai/claude-code\n"
                        "2. Login to Claude: claude login\n3. Try running your prompt again"
                    ),
                }

            # Check if help output contains expected content
            help_output = stdout.decode() + stderr.decode()
            if "claude" not in help_output.lower():
                return {
                    "available": False,
                    "configured": False,
                    "error": (
                        "Claude Code CLI not responding correctly.\n\nPlease try:\n"
                        "1. Reinstall: npm install -g @anthropic-ai/claude-code\n"
                        "2. Login: claude login\n3. Check installation: claude -h"
                    ),
                }

            return {
                "available": True,
                "configured": True,
                "mode": "CLI",
                "models": self.get_supported_models(),
                "default_models": [
                    "claude-sonnet-4-20250514",
                    "claude-opus-4-1-20250805",
                ],
            }
        except Exception as e:
            return {
                "available": False,
                "configured": False,
                "error": (
                    f"Failed to check Claude Code CLI: {str(e)}\n\nTo install:\n"
                    "1. Install Claude Code: npm install -g @anthropic-ai/claude-code\n"
                    "2. Login to Claude: claude login"
                ),
            }

    async def execute_with_streaming(
        self,
        instruction: str,
        project_path: str,
        session_id: Optional[str] = None,
        log_callback: Optional[Callable[[str], Any]] = None,
        images: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        is_initial_prompt: bool = False,
    ) -> AsyncGenerator[Message, None]:
        """Execute instruction using Claude Code Python SDK"""

        ui.info("Starting Claude SDK execution", "Claude SDK")
        ui.debug(f"Instruction: {instruction[:100]}...", "Claude SDK")
        ui.debug(f"Project path: {project_path}", "Claude SDK")
        ui.debug(f"Session ID: {session_id}", "Claude SDK")

        if log_callback:
            await log_callback("Starting execution...")

        # Use simple default system prompt
        system_prompt = "You are Claude Code, an AI coding assistant."

        # Get CLI-specific model name
        cli_model = self._get_cli_model_name(model) or "claude-sonnet-4-20250514"

        # Use instruction as-is without project-specific context
        # Removed hardcoded project structure assumptions

        # Configure standard tools without project-specific restrictions
        allowed_tools = [
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Bash",
            "Glob",
            "Grep",
            "LS",
            "WebFetch",
            "WebSearch",
            "TodoWrite",
        ]

        ui.debug(f"Allowed tools: {allowed_tools}", "Claude SDK")

        # Configure Claude Code options
        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            permission_mode="bypassPermissions",
            model=cli_model,
            continue_conversation=True,
        )

        ui.info(f"Using model: {cli_model}", "Claude SDK")
        ui.debug(f"Project path: {project_path}", "Claude SDK")
        ui.debug(f"Instruction: {instruction[:100]}...", "Claude SDK")

        try:
            # Change to project directory
            original_cwd = os.getcwd()
            os.chdir(project_path)

            # Get project ID for session management
            project_id = (
                project_path.split("/")[-1] if "/" in project_path else project_path
            )
            existing_session_id = await self.get_session_id(project_id)

            # Update options with resume session if available
            if existing_session_id:
                options.resumeSessionId = existing_session_id
                ui.info(f"Resuming session: {existing_session_id}", "Claude SDK")

            try:
                async with ClaudeSDKClient(options=options) as client:
                    # Send initial query
                    await client.query(instruction)

                    # Stream responses and extract session_id
                    claude_session_id = None

                    async for message_obj in client.receive_messages():
                        # Import SDK types for isinstance checks
                        try:
                            from anthropic.claude_code.types import (
                                SystemMessage,
                                AssistantMessage,
                                UserMessage,
                                ResultMessage,
                            )
                        except ImportError:
                            try:
                                from claude_code_sdk.types import (
                                    SystemMessage,
                                    AssistantMessage,
                                    UserMessage,
                                    ResultMessage,
                                )
                            except ImportError:
                                # Fallback - check type name strings
                                SystemMessage = type(None)
                                AssistantMessage = type(None)
                                UserMessage = type(None)
                                ResultMessage = type(None)

                        # Handle SystemMessage for session_id extraction
                        if (
                            isinstance(message_obj, SystemMessage)
                            or "SystemMessage" in str(type(message_obj))
                        ):
                            # Extract session_id if available
                            if (
                                hasattr(message_obj, "session_id")
                                and message_obj.session_id
                            ):
                                claude_session_id = message_obj.session_id
                                await self.set_session_id(
                                    project_id, claude_session_id
                                )

                            # Send init message (hidden from UI)
                            init_message = Message(
                                id=str(uuid.uuid4()),
                                project_id=project_path,
                                role="system",
                                message_type="system",
                                content=f"Claude Code SDK initialized (Model: {cli_model})",
                                metadata_json={
                                    "cli_type": self.cli_type.value,
                                    "mode": "SDK",
                                    "model": cli_model,
                                    "session_id": getattr(
                                        message_obj, "session_id", None
                                    ),
                                    "hidden_from_ui": True,
                                },
                                session_id=session_id,
                                created_at=datetime.utcnow(),
                            )
                            yield init_message

                        # Handle AssistantMessage (complete messages)
                        elif (
                            isinstance(message_obj, AssistantMessage)
                            or "AssistantMessage" in str(type(message_obj))
                        ):
                            content = ""

                            # Process content - AssistantMessage has content: list[ContentBlock]
                            if hasattr(message_obj, "content") and isinstance(
                                message_obj.content, list
                            ):
                                for block in message_obj.content:
                                    # Import block types for comparison
                                    from claude_code_sdk.types import (
                                        TextBlock,
                                        ToolUseBlock,
                                        ToolResultBlock,
                                    )

                                    if isinstance(block, TextBlock):
                                        # TextBlock has 'text' attribute
                                        content += block.text
                                    elif isinstance(block, ToolUseBlock):
                                        # ToolUseBlock has 'id', 'name', 'input' attributes
                                        tool_name = block.name
                                        tool_input = block.input
                                        tool_id = block.id
                                        summary = self._create_tool_summary(
                                            tool_name, tool_input
                                        )

                                        # Yield tool use message immediately
                                        tool_message = Message(
                                            id=str(uuid.uuid4()),
                                            project_id=project_path,
                                            role="assistant",
                                            message_type="tool_use",
                                            content=summary,
                                            metadata_json={
                                                "cli_type": self.cli_type.value,
                                                "mode": "SDK",
                                                "tool_name": tool_name,
                                                "tool_input": tool_input,
                                                "tool_id": tool_id,
                                            },
                                            session_id=session_id,
                                            created_at=datetime.utcnow(),
                                        )
                                        # Display clean tool usage like Claude Code
                                        tool_display = self._get_clean_tool_display(
                                            tool_name, tool_input
                                        )
                                        ui.info(tool_display, "")
                                        yield tool_message
                                    elif isinstance(block, ToolResultBlock):
                                        # Handle tool result blocks if needed
                                        pass

                            # Yield complete assistant text message if there's text content
                            if content and content.strip():
                                text_message = Message(
                                    id=str(uuid.uuid4()),
                                    project_id=project_path,
                                    role="assistant",
                                    message_type="chat",
                                    content=content.strip(),
                                    metadata_json={
                                        "cli_type": self.cli_type.value,
                                        "mode": "SDK",
                                    },
                                    session_id=session_id,
                                    created_at=datetime.utcnow(),
                                )
                                yield text_message

                        # Handle UserMessage (tool results, etc.)
                        elif (
                            isinstance(message_obj, UserMessage)
                            or "UserMessage" in str(type(message_obj))
                        ):
                            # UserMessage has content: str according to types.py
                            # UserMessages are typically tool results - we don't need to show them
                            pass

                        # Handle ResultMessage (final session completion)
                        elif (
                            isinstance(message_obj, ResultMessage)
                            or "ResultMessage" in str(type(message_obj))
                            or (
                                hasattr(message_obj, "type")
                                and getattr(message_obj, "type", None) == "result"
                            )
                        ):
                            ui.success(
                                f"Session completed in {getattr(message_obj, 'duration_ms', 0)}ms",
                                "Claude SDK",
                            )

                            # Create internal result message (hidden from UI)
                            result_message = Message(
                                id=str(uuid.uuid4()),
                                project_id=project_path,
                                role="system",
                                message_type="result",
                                content=(
                                    f"Session completed in {getattr(message_obj, 'duration_ms', 0)}ms"
                                ),
                                metadata_json={
                                    "cli_type": self.cli_type.value,
                                    "mode": "SDK",
                                    "duration_ms": getattr(
                                        message_obj, "duration_ms", 0
                                    ),
                                    "duration_api_ms": getattr(
                                        message_obj, "duration_api_ms", 0
                                    ),
                                    "total_cost_usd": getattr(
                                        message_obj, "total_cost_usd", 0
                                    ),
                                    "num_turns": getattr(message_obj, "num_turns", 0),
                                    "is_error": getattr(message_obj, "is_error", False),
                                    "subtype": getattr(message_obj, "subtype", None),
                                    "session_id": getattr(
                                        message_obj, "session_id", None
                                    ),
                                    "hidden_from_ui": True,  # Don't show to user
                                },
                                session_id=session_id,
                                created_at=datetime.utcnow(),
                            )
                            yield result_message
                            break

                        # Handle unknown message types
                        else:
                            ui.debug(
                                f"Unknown message type: {type(message_obj)}",
                                "Claude SDK",
                            )

            finally:
                # Restore original working directory
                os.chdir(original_cwd)

        except Exception as e:
            ui.error(f"Exception occurred: {str(e)}", "Claude SDK")
            if log_callback:
                await log_callback(f"Claude SDK Exception: {str(e)}")
            raise

    async def get_session_id(self, project_id: str) -> Optional[str]:
        """Get current session ID for project"""
        return self.session_mapping.get(project_id)

    async def set_session_id(self, project_id: str, session_id: str) -> None:
        """Set session ID for project in memory"""
        self.session_mapping[project_id] = session_id
        ui.debug(
            f"Session ID stored for project {project_id}", "Claude SDK"
        )


__all__ = ["ClaudeCodeCLI"]
