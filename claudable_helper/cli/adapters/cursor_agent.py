"""Cursor Agent provider implementation.

Moved from unified_manager.py to a dedicated adapter module.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from claudable_helper.models.messages import Message
from claudable_helper.core.terminal_ui import ui

from ..base import BaseCLI, CLIType


class CursorAgentCLI(BaseCLI):
    """Cursor Agent CLI implementation with stream-json support and session continuity"""

    def __init__(self):
        super().__init__(CLIType.CURSOR)
        self._session_store = {}  # Simple in-memory session storage

    async def check_availability(self) -> Dict[str, Any]:
        """Check if Cursor Agent CLI is available"""
        try:
            # Check if cursor-agent is installed and working
            result = await asyncio.create_subprocess_shell(
                "cursor-agent -h",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                return {
                    "available": False,
                    "configured": False,
                    "error": (
                        "Cursor Agent CLI not installed or not working.\n\nTo install:\n"
                        "1. Install Cursor: curl https://cursor.com/install -fsS | bash\n"
                        "2. Login to Cursor: cursor-agent login\n3. Try running your prompt again"
                    ),
                }

            # Check if help output contains expected content
            help_output = stdout.decode() + stderr.decode()
            if "cursor-agent" not in help_output.lower():
                return {
                    "available": False,
                    "configured": False,
                    "error": (
                        "Cursor Agent CLI not responding correctly.\n\nPlease try:\n"
                        "1. Reinstall: curl https://cursor.com/install -fsS | bash\n"
                        "2. Login: cursor-agent login\n3. Check installation: cursor-agent -h"
                    ),
                }

            return {
                "available": True,
                "configured": True,
                "models": self.get_supported_models(),
                "default_models": ["gpt-5", "sonnet-4"],
            }
        except Exception as e:
            return {
                "available": False,
                "configured": False,
                "error": (
                    f"Failed to check Cursor Agent: {str(e)}\n\nTo install:\n"
                    "1. Install Cursor: curl https://cursor.com/install -fsS | bash\n"
                    "2. Login: cursor-agent login"
                ),
            }

    def _handle_cursor_stream_json(
        self, event: Dict[str, Any], project_path: str, session_id: str
    ) -> Optional[Message]:
        """Handle Cursor stream-json format (NDJSON events) to be compatible with Claude Code CLI output"""
        event_type = event.get("type")

        if event_type == "system":
            # System initialization event
            return Message(
                id=str(uuid.uuid4()),
                project_id=project_path,
                role="system",
                message_type="system",
                content=f"🔧 Cursor Agent initialized (Model: {event.get('model', 'unknown')})",
                metadata_json={
                    "cli_type": self.cli_type.value,
                    "event_type": "system",
                    "cwd": event.get("cwd"),
                    "api_key_source": event.get("apiKeySource"),
                    "original_event": event,
                    "hidden_from_ui": True,  # Hide system init messages
                },
                session_id=session_id,
                created_at=datetime.utcnow(),
            )

        elif event_type == "user":
            # Cursor echoes back the user's prompt. Suppress it to avoid duplicates.
            return None

        elif event_type == "assistant":
            # Assistant response event (text delta)
            message_content = event.get("message", {}).get("content", [])
            content = ""

            if message_content and isinstance(message_content, list):
                for part in message_content:
                    if part.get("type") == "text":
                        content += part.get("text", "")

            if content:
                return Message(
                    id=str(uuid.uuid4()),
                    project_id=project_path,
                    role="assistant",
                    message_type="chat",
                    content=content,
                    metadata_json={
                        "cli_type": self.cli_type.value,
                        "event_type": "assistant",
                        "original_event": event,
                    },
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                )

        elif event_type == "tool_call":
            subtype = event.get("subtype")
            tool_call_data = event.get("tool_call", {})
            if not tool_call_data:
                return None

            tool_name_raw = next(iter(tool_call_data), None)
            if not tool_name_raw:
                return None

            # Normalize tool name: lsToolCall -> ls
            tool_name = tool_name_raw.replace("ToolCall", "")

            if subtype == "started":
                tool_input = tool_call_data[tool_name_raw].get("args", {})
                summary = self._create_tool_summary(tool_name, tool_input)

                return Message(
                    id=str(uuid.uuid4()),
                    project_id=project_path,
                    role="assistant",
                    message_type="chat",
                    content=summary,
                    metadata_json={
                        "cli_type": self.cli_type.value,
                        "event_type": "tool_call_started",
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "original_event": event,
                    },
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                )

            elif subtype == "completed":
                result = tool_call_data[tool_name_raw].get("result", {})
                content = ""
                if "success" in result:
                    content = json.dumps(result["success"])
                elif "error" in result:
                    content = json.dumps(result["error"])

                return Message(
                    id=str(uuid.uuid4()),
                    project_id=project_path,
                    role="system",
                    message_type="tool_result",
                    content=content,
                    metadata_json={
                        "cli_type": self.cli_type.value,
                        "original_format": event,
                        "tool_name": tool_name,
                        "hidden_from_ui": True,
                    },
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                )

        elif event_type == "result":
            # Final result event
            duration = event.get("duration_ms", 0)
            result_text = event.get("result", "")

            if result_text:
                return Message(
                    id=str(uuid.uuid4()),
                    project_id=project_path,
                    role="system",
                    message_type="system",
                    content=(
                        f"Execution completed in {duration}ms. Final result: {result_text}"
                    ),
                    metadata_json={
                        "cli_type": self.cli_type.value,
                        "event_type": "result",
                        "duration_ms": duration,
                        "original_event": event,
                        "hidden_from_ui": True,
                    },
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                )

        return None


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
        """Execute Cursor Agent CLI with stream-json format and session continuity"""
        # Skip AGENTS.md creation - removed for MCP server usage

        # Extract project ID - simplified path handling
        project_id = os.path.basename(project_path)

        stored_session_id = await self.get_session_id(project_id)

        cmd = [
            "cursor-agent",
            "--force",
            "-p",
            instruction,
            "--output-format",
            "stream-json",  # Use stream-json format
        ]

        # Add session resume if available (prefer stored session over parameter)
        active_session_id = stored_session_id or session_id
        if active_session_id:
            cmd.extend(["--resume", active_session_id])
            print(f"🔗 [Cursor] Resuming session: {active_session_id}")

        # Add API key if available
        if os.getenv("CURSOR_API_KEY"):
            cmd.extend(["--api-key", os.getenv("CURSOR_API_KEY")])

        # Add model - prioritize parameter over environment variable
        cli_model = self._get_cli_model_name(model) or os.getenv("CURSOR_MODEL")
        if cli_model:
            cmd.extend(["--model", cli_model])
            print(f"🔧 [Cursor] Using model: {cli_model}")

        # Use the provided project path directly
        project_repo_path = project_path

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,  # Explicitly close stdin
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_repo_path,
            )

            # Start stderr reader task
            stderr_task = asyncio.create_task(self._drain_stderr(process.stderr))

            cursor_session_id = None
            assistant_message_buffer = ""
            result_received = False  # Track if we received result event

            async for line in process.stdout:
                line_str = line.decode().strip()
                if not line_str:
                    continue

                try:
                    # Parse NDJSON event
                    event = json.loads(line_str)

                    event_type = event.get("type")

                    # Priority: Extract session ID from type: "result" event (most reliable)
                    if event_type == "result":
                        print(f"🔍 [Cursor] Result event received: {event}")

                        # Extract session ID if not already found
                        if not cursor_session_id:
                            session_id_from_result = event.get("session_id")
                            if session_id_from_result:
                                cursor_session_id = session_id_from_result
                                await self.set_session_id(project_id, cursor_session_id)
                                print(
                                    f"💾 [Cursor] Session ID extracted from result event: {cursor_session_id}"
                                )

                        # Emit result message for MCP server
                        result_text = event.get("result", "")
                        yield Message(
                            id=str(uuid.uuid4()),
                            project_id=project_path,
                            role="assistant",
                            message_type="result",
                            content=result_text,
                            metadata_json={
                                "cli_type": "cursor",
                                "event_type": "result",
                                "session_id": cursor_session_id,
                            },
                            session_id=session_id,
                            created_at=datetime.utcnow(),
                        )

                        # Mark that we received result event
                        result_received = True

                    # Extract session ID from various event types
                    if not cursor_session_id:
                        # Try to extract session ID from any event that contains it
                        potential_session_id = (
                            event.get("sessionId")
                            or event.get("chatId")
                            or event.get("session_id")
                            or event.get("chat_id")
                            or event.get("threadId")
                            or event.get("thread_id")
                        )

                        # Also check in nested structures
                        if not potential_session_id and isinstance(
                            event.get("message"), dict
                        ):
                            potential_session_id = (
                                event["message"].get("sessionId")
                                or event["message"].get("chatId")
                                or event["message"].get("session_id")
                                or event["message"].get("chat_id")
                            )

                        if potential_session_id and potential_session_id != active_session_id:
                            cursor_session_id = potential_session_id
                            await self.set_session_id(project_id, cursor_session_id)
                            print(
                                f"💾 [Cursor] Updated session ID for project {project_id}: {cursor_session_id}"
                            )
                            print(f"   Previous: {active_session_id}")
                            print(f"   New: {cursor_session_id}")

                    # If we receive a non-assistant message, flush the buffer first
                    if event.get("type") != "assistant" and assistant_message_buffer:
                        yield Message(
                            id=str(uuid.uuid4()),
                            project_id=project_path,
                            role="assistant",
                            message_type="chat",
                            content=assistant_message_buffer,
                            metadata_json={
                                "cli_type": "cursor",
                                "event_type": "assistant_aggregated",
                            },
                            session_id=session_id,
                            created_at=datetime.utcnow(),
                        )
                        assistant_message_buffer = ""

                    # Process the event
                    message = self._handle_cursor_stream_json(
                        event, project_path, session_id
                    )

                    if message:
                        if message.role == "assistant" and message.message_type == "chat":
                            assistant_message_buffer += message.content
                        else:
                            if log_callback:
                                await log_callback(f"📝 [Cursor] {message.content}")
                            yield message

                    # ★ CRITICAL: Break after result event to end streaming
                    if result_received:
                        print(
                            f"🏁 [Cursor] Result event received, terminating stream early"
                        )
                        try:
                            process.terminate()
                            print(f"🔪 [Cursor] Process terminated")
                        except Exception as e:
                            print(f"⚠️ [Cursor] Failed to terminate process: {e}")
                        break

                except json.JSONDecodeError as e:
                    # Handle malformed JSON
                    print(f"⚠️ [Cursor] JSON decode error: {e}")
                    print(f"⚠️ [Cursor] Raw line: {line_str}")

                    # Still yield as raw output
                    message = Message(
                        id=str(uuid.uuid4()),
                        project_id=project_path,
                        role="assistant",
                        message_type="chat",
                        content=line_str,
                        metadata_json={
                            "cli_type": "cursor",
                            "raw_output": line_str,
                            "parse_error": str(e),
                        },
                        session_id=session_id,
                        created_at=datetime.utcnow(),
                    )
                    yield message

            # Flush any remaining content in the buffer
            if assistant_message_buffer:
                yield Message(
                    id=str(uuid.uuid4()),
                    project_id=project_path,
                    role="assistant",
                    message_type="chat",
                    content=assistant_message_buffer,
                    metadata_json={
                        "cli_type": "cursor",
                        "event_type": "assistant_aggregated",
                    },
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                )

        except asyncio.CancelledError:
            # Handle cancellation gracefully
            print(f"🔄 [Cursor] Operation cancelled, cleaning up process")
            raise
        except Exception as e:
            print(f"❌ [Cursor] Error during execution: {e}")
            raise
        except FileNotFoundError:
            error_msg = (
                "❌ Cursor Agent CLI not found. Please install with: curl https://cursor.com/install -fsS | bash"
            )
            yield Message(
                id=str(uuid.uuid4()),
                project_id=project_path,
                role="assistant",
                message_type="error",
                content=error_msg,
                metadata_json={"error": "cli_not_found", "cli_type": "cursor"},
                session_id=session_id,
                created_at=datetime.utcnow(),
            )
        except asyncio.CancelledError:
            # Propagate cancellation
            raise
        except Exception as e:
            error_msg = f"❌ Cursor Agent execution failed: {str(e)}"
            yield Message(
                id=str(uuid.uuid4()),
                project_id=project_path,
                role="assistant",
                message_type="error",
                content=error_msg,
                metadata_json={
                    "error": "execution_failed",
                    "cli_type": "cursor",
                    "exception": str(e),
                },
                session_id=session_id,
                created_at=datetime.utcnow(),
            )
        finally:
            # Always clean up process and tasks
            if 'process' in locals():
                stderr_task_var = locals().get('stderr_task')
                await self._cleanup_cursor_process(process, stderr_task_var)

    async def get_session_id(self, project_id: str) -> Optional[str]:
        """Get stored session ID for project"""
        return self._session_store.get(project_id)

    async def set_session_id(self, project_id: str, session_id: str) -> None:
        """Store session ID for project in memory"""
        self._session_store[project_id] = session_id
        print(
            f"💾 [Cursor] Session ID stored for project {project_id}: {session_id}"
        )

    async def _drain_stderr(self, stderr) -> None:
        """Background task to drain stderr to prevent blocking."""
        if not stderr:
            return

        try:
            while True:
                line = await stderr.readline()
                if not line:
                    break
                # Optionally log stderr for debugging
                line_str = line.decode().strip()
                if line_str:
                    print(f"🔍 [Cursor] stderr: {line_str}")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _cleanup_cursor_process(self, process, stderr_task) -> None:
        """Clean up cursor process and associated tasks."""
        try:
            # Cancel stderr task
            if stderr_task and not stderr_task.done():
                stderr_task.cancel()
                try:
                    await stderr_task
                except asyncio.CancelledError:
                    pass

            # Gracefully terminate process
            if process and process.returncode is None:
                print(f"🔄 [Cursor] Terminating process gracefully")
                process.terminate()
                try:
                    # Wait up to 5 seconds for graceful termination
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                    print(f"🔪 [Cursor] Process terminated gracefully")
                except asyncio.TimeoutError:
                    print(f"⚠️ [Cursor] Process didn't terminate gracefully, killing")
                    process.kill()
                    await process.wait()
                    print(f"🔪 [Cursor] Process killed")
        except Exception as e:
            print(f"⚠️ [Cursor] Error during cleanup: {e}")


__all__ = ["CursorAgentCLI"]
