"""Gemini CLI provider implementation using ACP over stdio.

This adapter launches `gemini --experimental-acp`, communicates via JSON-RPC
over stdio, and streams session/update notifications. Thought chunks are
surfaced to the UI.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

from claudable_helper.core.terminal_ui import ui
from claudable_helper.models.messages import Message

from ..base import BaseCLI, CLIType, adapter_session
from .qwen_cli import _ACPClient, _mime_for  # Reuse minimal ACP client


class GeminiCLI(BaseCLI):
    """Gemini CLI via ACP. Streams message and thought chunks to UI."""

    # Class-level client storage per event loop (for per-loop mode)
    _LOOP_CLIENTS: Dict[asyncio.AbstractEventLoop, _ACPClient] = {}
    _LOOP_INITIALIZED: Dict[asyncio.AbstractEventLoop, bool] = {}

    def __init__(self):
        super().__init__(CLIType.GEMINI)
        self._session_store: Dict[str, str] = {}  # Simple in-memory session storage
        self._client: Optional[_ACPClient] = None
        self._initialized = False
        self._per_call_mode = os.getenv("GEMINI_PER_CALL", "1") == "1"

    async def check_availability(self) -> Dict[str, Any]:
        try:
            proc = await asyncio.create_subprocess_shell(
                "gemini --help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return {
                    "available": False,
                    "configured": False,
                    "error": "Gemini CLI not found. Install Gemini CLI and ensure it is in PATH.",
                }
            return {
                "available": True,
                "configured": True,
                "models": self.get_supported_models(),
                "default_models": [],
            }
        except Exception as e:
            return {"available": False, "configured": False, "error": str(e)}


    async def _create_client(self) -> _ACPClient:
        """Create a new ACP client instance."""
        cmd = ["gemini", "--experimental-acp"]
        env = os.environ.copy()
        # Prefer device-code-like flow if CLI supports it
        env.setdefault("NO_BROWSER", "1")
        client = _ACPClient(cmd, env=env)

        # Client-side request handlers: auto-approve permissions
        async def _handle_permission(params: Dict[str, Any]) -> Dict[str, Any]:
            options = params.get("options") or []
            chosen = None
            for kind in ("allow_always", "allow_once"):
                chosen = next((o for o in options if o.get("kind") == kind), None)
                if chosen:
                    break
            if not chosen and options:
                chosen = options[0]
            if not chosen:
                return {"outcome": {"outcome": "cancelled"}}
            return {
                "outcome": {"outcome": "selected", "optionId": chosen.get("optionId")}
            }

        async def _fs_read(params: Dict[str, Any]) -> Dict[str, Any]:
            return {"content": ""}

        async def _fs_write(params: Dict[str, Any]) -> Dict[str, Any]:
            return {}

        client.on_request("session/request_permission", _handle_permission)
        client.on_request("fs/read_text_file", _fs_read)
        client.on_request("fs/write_text_file", _fs_write)

        return client

    async def _ensure_client(self) -> _ACPClient:
        """Get or create a client based on mode (per-call or per-loop)."""
        if self._per_call_mode:
            # Per-call mode: always create new client (will be managed by context manager)
            return await self._create_client()

        # Per-loop mode: share client within event loop
        loop = asyncio.get_running_loop()

        if loop not in GeminiCLI._LOOP_CLIENTS:
            client = await self._create_client()
            await client.start()
            GeminiCLI._LOOP_CLIENTS[loop] = client
            GeminiCLI._LOOP_INITIALIZED[loop] = False

        self._client = GeminiCLI._LOOP_CLIENTS[loop]

        if not GeminiCLI._LOOP_INITIALIZED[loop]:
            await self._client.request(
                "initialize",
                {
                    "clientCapabilities": {
                        "fs": {"readTextFile": False, "writeTextFile": False}
                    },
                    "protocolVersion": 1,
                },
            )
            GeminiCLI._LOOP_INITIALIZED[loop] = True

        return self._client

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
        ui.debug(f"execute_with_streaming called with per_call_mode: {self._per_call_mode}", "Gemini")
        # Get client (per-call or per-loop)
        if self._per_call_mode:
            ui.debug("entering per-call mode path", "Gemini")
            # Per-call mode: use context manager for lifecycle
            client = await self._ensure_client()
            ui.debug(f"got client: {client}", "Gemini")
            async with adapter_session(client) as session_client:
                ui.debug("inside adapter_session context", "Gemini")
                await session_client.request(
                    "initialize",
                    {
                        "clientCapabilities": {
                            "fs": {"readTextFile": False, "writeTextFile": False}
                        },
                        "protocolVersion": 1,
                    },
                )
                ui.debug("initialization request completed", "Gemini")
                ui.debug("calling _execute_streaming_impl", "Gemini")
                async for msg in self._execute_streaming_impl(
                    session_client, instruction, project_path, session_id,
                    log_callback, images, model, is_initial_prompt
                ):
                    ui.debug(f"yielding message from execute_with_streaming: {msg.role} - {msg.message_type}", "Gemini")
                    yield msg
                ui.debug("_execute_streaming_impl completed", "Gemini")
        else:
            ui.debug("entering per-loop mode path", "Gemini")
            # Per-loop mode: use shared client
            client = await self._ensure_client()
            async for msg in self._execute_streaming_impl(
                client, instruction, project_path, session_id,
                log_callback, images, model, is_initial_prompt
            ):
                yield msg

    async def _execute_streaming_impl(
        self,
        client: _ACPClient,
        instruction: str,
        project_path: str,
        session_id: Optional[str] = None,
        log_callback: Optional[Callable[[str], Any]] = None,
        images: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        is_initial_prompt: bool = False
    ) -> AsyncGenerator[Message, None]:
        # Skip provider markdown creation - removed for MCP server usage
        turn_id = str(uuid.uuid4())[:8]
        try:
            ui.debug(
                f"[{turn_id}] execute_with_streaming start | model={model or '-'} | images={len(images or [])} | instruction_len={len(instruction or '')}",
                "Gemini",
            )
        except Exception:
            pass

        # Use the provided project path directly
        project_repo_path = project_path

        # Project ID - simplified path handling
        project_id = os.path.basename(project_path)

        # Ensure session
        # In per-call mode, do NOT reuse cached session IDs from previous processes
        # because each call launches a fresh `gemini` process. Using a stale
        # sessionId would cause "Session not found" and dropped updates.
        if self._per_call_mode:
            stored_session_id = None
        else:
            stored_session_id = await self.get_session_id(project_id)
        ui.debug(f"[{turn_id}] resolved project_id={project_id}", "Gemini")
        if not stored_session_id:
            # Try creating a session to reuse cached OAuth credentials if present
            try:
                result = await client.request(
                    "session/new", {"cwd": project_repo_path, "mcpServers": []}
                )
                stored_session_id = result.get("sessionId")
                if stored_session_id:
                    await self.set_session_id(project_id, stored_session_id)
                    ui.info(f"[{turn_id}] session created: {stored_session_id}", "Gemini")
            except Exception as e:
                # Authenticate then retry session/new
                auth_method = os.getenv("GEMINI_AUTH_METHOD", "oauth-personal")
                ui.warning(
                    f"[{turn_id}] session/new failed; authenticating via {auth_method}: {e}",
                    "Gemini",
                )
                try:
                    await client.request("authenticate", {"methodId": auth_method})
                    result = await client.request(
                        "session/new", {"cwd": project_repo_path, "mcpServers": []}
                    )
                    stored_session_id = result.get("sessionId")
                    if stored_session_id:
                        await self.set_session_id(project_id, stored_session_id)
                        ui.info(f"[{turn_id}] session created after auth: {stored_session_id}", "Gemini")
                except Exception as e2:
                    ui.error(f"[{turn_id}] authentication/session failed: {e2}", "Gemini")
                    yield Message(
                        id=str(uuid.uuid4()),
                        project_id=project_path,
                        role="assistant",
                        message_type="error",
                        content=f"Gemini authentication/session failed: {e2}",
                        metadata_json={"cli_type": self.cli_type.value},
                        session_id=session_id,
                        created_at=datetime.utcnow(),
                    )
                    return

        q: asyncio.Queue = asyncio.Queue()
        thought_buffer: List[str] = []
        text_buffer: List[str] = []

        def _on_update(params: Dict[str, Any]) -> None:
            try:
                ui.debug(f"[{turn_id}] _on_update called with params keys: {list(params.keys()) if params else 'None'}", "Gemini")
                if params.get("sessionId") != stored_session_id:
                    ui.debug(f"[{turn_id}] sessionId mismatch: got {params.get('sessionId')}, expected {stored_session_id}", "Gemini")
                    return
                update = params.get("update") or {}
                try:
                    kind = update.get("sessionUpdate") or update.get("type")
                    snippet = ""
                    if isinstance(update.get("text"), str):
                        snippet = update.get("text")[:80]
                    elif isinstance((update.get("content") or {}).get("text"), str):
                        snippet = (update.get("content") or {}).get("text")[:80]
                    ui.debug(
                        f"[{turn_id}] notif session/update kind={kind} snippet={snippet!r}",
                        "Gemini",
                    )
                except Exception as e:
                    ui.debug(f"[{turn_id}] exception in update logging: {e}", "Gemini")
                ui.debug(f"[{turn_id}] putting update in queue: {update}", "Gemini")
                q.put_nowait(update)
                ui.debug(f"[{turn_id}] update queued successfully, queue size now: {q.qsize()}", "Gemini")
            except Exception as e:
                ui.error(f"[{turn_id}] exception in _on_update: {e}", "Gemini")

        ui.debug(f"[{turn_id}] registering notification handler for session/update", "Gemini")
        client.on_notification("session/update", _on_update)
        ui.debug(f"[{turn_id}] notification handler registered", "Gemini")
        try:
            # Main streaming logic
            async for msg in self._stream_prompt_response(
                client, stored_session_id, instruction, images, project_path, session_id,
                project_id, project_repo_path, turn_id, q, thought_buffer, text_buffer
            ):
                yield msg
        finally:
            # Always unregister handler to prevent leaks
            ui.debug(f"[{turn_id}] unregistering notification handler", "Gemini")
            client.off_notification("session/update", _on_update)
            ui.debug(f"[{turn_id}] notification handler unregistered", "Gemini")

    async def _stream_prompt_response(
        self,
        client: _ACPClient,
        stored_session_id: str,
        instruction: str,
        images: Optional[List[Dict[str, Any]]],
        project_path: str,
        session_id: Optional[str],
        project_id: str,
        project_repo_path: str,
        turn_id: str,
        q: asyncio.Queue,
        thought_buffer: List[str],
        text_buffer: List[str]
    ) -> AsyncGenerator[Message, None]:

        # Build prompt parts
        parts: List[Dict[str, Any]] = []
        if instruction:
            parts.append({"type": "text", "text": instruction})
        if images:
            def _iget(obj, key, default=None):
                try:
                    if isinstance(obj, dict):
                        return obj.get(key, default)
                    return getattr(obj, key, default)
                except Exception:
                    return default

            for image in images:
                local_path = _iget(image, "path")
                b64 = _iget(image, "base64_data") or _iget(image, "data")
                if not b64 and _iget(image, "url", "").startswith("data:"):
                    try:
                        b64 = _iget(image, "url").split(",", 1)[1]
                    except Exception:
                        b64 = None
                if local_path and os.path.exists(local_path):
                    try:
                        with open(local_path, "rb") as f:
                            data = f.read()
                        mime = _mime_for(local_path)
                        b64 = base64.b64encode(data).decode("utf-8")
                        parts.append({"type": "image", "mimeType": mime, "data": b64})
                        continue
                    except Exception:
                        pass
                if b64:
                    parts.append({"type": "image", "mimeType": "image/png", "data": b64})

        # Send prompt
        def _make_prompt_task() -> asyncio.Task:
            ui.debug(f"[{turn_id}] sending session/prompt (parts={len(parts)})", "Gemini")
            return asyncio.create_task(
                client.request(
                    "session/prompt", {"sessionId": stored_session_id, "prompt": parts}
                )
            )
        prompt_task = _make_prompt_task()
        q_task = asyncio.create_task(q.get())  # Create once, reuse

        try:
            ui.debug(f"[{turn_id}] entering main streaming loop", "Gemini")
            loop_count = 0
            while True:
                loop_count += 1
                ui.debug(f"[{turn_id}] loop iteration #{loop_count}, queue size: {q.qsize()}", "Gemini")
                done, _ = await asyncio.wait(
                    {prompt_task, q_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                ui.debug(f"[{turn_id}] wait completed, done tasks: {len(done)}", "Gemini")

                if q_task in done:
                    ui.debug(f"[{turn_id}] q_task completed", "Gemini")
                    # Process the update and create a new q_task
                    update = await q_task
                    ui.debug(f"[{turn_id}] got update from queue: {update}", "Gemini")
                    message_count = 0
                    async for m in self._update_to_messages(update, project_path, session_id, thought_buffer, text_buffer):
                        if m:
                            message_count += 1
                            ui.debug(f"[{turn_id}] yielding message #{message_count}: {m.role} - {m.message_type}", "Gemini")
                            yield m
                    ui.debug(f"[{turn_id}] _update_to_messages yielded {message_count} messages", "Gemini")
                    q_task = asyncio.create_task(q.get())  # Create new task for next get
                    ui.debug(f"[{turn_id}] created new q_task", "Gemini")

                if prompt_task in done:
                    ui.debug(f"[{turn_id}] prompt_task completed; draining updates", "Gemini")
                    # Drain remaining
                    drain_count = 0
                    while not q.empty():
                        drain_count += 1
                        update = q.get_nowait()
                        ui.debug(f"[{turn_id}] draining update #{drain_count}: {update}", "Gemini")
                        message_count = 0
                        async for m in self._update_to_messages(update, project_path, session_id, thought_buffer, text_buffer):
                            if m:
                                message_count += 1
                                ui.debug(f"[{turn_id}] yielding drained message #{message_count}: {m.role} - {m.message_type}", "Gemini")
                                yield m
                        ui.debug(f"[{turn_id}] drained update yielded {message_count} messages", "Gemini")
                    ui.debug(f"[{turn_id}] drained {drain_count} updates", "Gemini")
                    exc = prompt_task.exception()
                    if exc:
                        msg = str(exc)
                        if "Session not found" in msg or "session not found" in msg.lower():
                            ui.warning(f"[{turn_id}] session expired; creating a new session and retrying", "Gemini")
                            try:
                                result = await client.request(
                                    "session/new", {"cwd": project_repo_path, "mcpServers": []}
                                )
                                stored_session_id = result.get("sessionId")
                                if stored_session_id:
                                    await self.set_session_id(project_id, stored_session_id)
                                    ui.info(f"[{turn_id}] new session={stored_session_id}; retrying prompt", "Gemini")
                                    prompt_task = _make_prompt_task()
                                    continue
                            except Exception as e2:
                                ui.error(f"[{turn_id}] session recovery failed: {e2}", "Gemini")
                                yield Message(
                                    id=str(uuid.uuid4()),
                                    project_id=project_path,
                                    role="assistant",
                                    message_type="error",
                                    content=f"Gemini session recovery failed: {e2}",
                                    metadata_json={"cli_type": self.cli_type.value},
                                    session_id=session_id,
                                    created_at=datetime.utcnow(),
                                )
                        else:
                            ui.error(f"[{turn_id}] prompt error: {msg}", "Gemini")
                            yield Message(
                                id=str(uuid.uuid4()),
                                project_id=project_path,
                                role="assistant",
                                message_type="error",
                                content=f"Gemini prompt error: {msg}",
                                metadata_json={"cli_type": self.cli_type.value},
                                session_id=session_id,
                                created_at=datetime.utcnow(),
                            )
                    # Final flush of buffered assistant content (with <thinking> block)
                    if thought_buffer or text_buffer:
                        ui.debug(
                            f"[{turn_id}] flushing buffered content thought_len={sum(len(x) for x in thought_buffer)} text_len={sum(len(x) for x in text_buffer)}",
                            "Gemini",
                        )
                        yield Message(
                            id=str(uuid.uuid4()),
                        project_id=project_path,
                        role="assistant",
                        message_type="chat",
                        content=self._compose_content(thought_buffer, text_buffer),
                        metadata_json={"cli_type": self.cli_type.value},
                        session_id=session_id,
                        created_at=datetime.utcnow(),
                    )
                    thought_buffer.clear()
                    text_buffer.clear()
                    # Prompt completed and buffers flushed; exit loop
                    break
        finally:
            # Cancel any pending tasks
            if not q_task.done():
                q_task.cancel()
                try:
                    await q_task
                except asyncio.CancelledError:
                    pass

        ui.info(f"[{turn_id}] turn completed", "Gemini")

    async def _update_to_messages(
        self,
        update: Dict[str, Any],
        project_path: str,
        session_id: Optional[str],
        thought_buffer: List[str],
        text_buffer: List[str],
    ) -> AsyncGenerator[Optional[Message], None]:
        ui.debug(f"_update_to_messages called with update: {update}", "Gemini")
        kind = update.get("sessionUpdate") or update.get("type")
        ui.debug(f"_update_to_messages processing kind: {kind}", "Gemini")
        now = datetime.utcnow()
        if kind in ("agent_message_chunk", "agent_thought_chunk"):
            text = ((update.get("content") or {}).get("text")) or update.get("text") or ""
            try:
                ui.debug(
                    f"update chunk kind={kind} len={len(text or '')}",
                    "Gemini",
                )
            except Exception:
                pass
            if not isinstance(text, str):
                text = str(text)
            if kind == "agent_thought_chunk":
                ui.debug(f"adding thought chunk: {text[:50]}...", "Gemini")
                thought_buffer.append(text)
                # Do not yield thought-only messages to avoid duplicates; we'll
                # render thinking alongside the first assistant text chunk.
            else:
                ui.debug(f"adding text chunk: {text[:50]}...", "Gemini")
                # First assistant message chunk after thinking: render thinking immediately
                if thought_buffer and not text_buffer:
                    ui.debug(f"yielding thinking message, thought_buffer len: {len(thought_buffer)}", "Gemini")
                    yield Message(
                        id=str(uuid.uuid4()),
                        project_id=project_path,
                        role="assistant",
                        message_type="chat",
                        content=self._compose_content(thought_buffer, []),
                        metadata_json={"cli_type": self.cli_type.value, "event_type": "thinking"},
                        session_id=session_id,
                        created_at=now,
                    )
                    thought_buffer.clear()
                text_buffer.append(text)
            ui.debug(f"_update_to_messages returning after processing {kind}", "Gemini")
            return
        elif kind in ("tool_call", "tool_call_update"):
            tool_name = self._parse_tool_name(update)
            tool_input = self._extract_tool_input(update)

            # Process tool events and extract results from updates
            tool_result = None
            if kind == "tool_call_update":
                # Extract result from tool_call_update
                content_list = update.get("content", [])
                for item in content_list:
                    if isinstance(item, dict) and item.get("type") == "content":
                        content = item.get("content", {})
                        if isinstance(content, dict) and content.get("type") == "text":
                            tool_result = content.get("text", "")
                            break
                ui.debug(f"Tool update {tool_name}: has_result={bool(tool_result)}", "Gemini")
            else:
                ui.debug(f"New tool call: {tool_name}", "Gemini")

            # Create concise summary for tool use; emit detailed results as chat below
            if tool_result:
                summary = f"Tool: {tool_name} (completed)"
            else:
                summary = self._create_tool_summary(tool_name, tool_input)
            # Flush buffered chat before tool use
            if thought_buffer or text_buffer:
                yield Message(
                    id=str(uuid.uuid4()),
                    project_id=project_path,
                    role="assistant",
                    message_type="chat",
                    content=self._compose_content(thought_buffer, text_buffer),
                    metadata_json={"cli_type": self.cli_type.value},
                    session_id=session_id,
                    created_at=now,
                )
                thought_buffer.clear()
                text_buffer.clear()
            yield Message(
                id=str(uuid.uuid4()),
                project_id=project_path,
                role="assistant",
                message_type="tool_use",
                content=summary,
                metadata_json={
                    "cli_type": self.cli_type.value,
                    "event_type": kind,
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                },
                session_id=session_id,
                created_at=now,
            )
            # Also surface concrete tool result as assistant chat content for summaries
            if tool_result:
                yield Message(
                    id=str(uuid.uuid4()),
                    project_id=project_path,
                    role="assistant",
                    message_type="chat",
                    content=tool_result,
                    metadata_json={"cli_type": self.cli_type.value, "event_type": "tool_result"},
                    session_id=session_id,
                    created_at=now,
                )
        elif kind == "plan":
            try:
                ui.info("plan event received", "Gemini")
            except Exception:
                pass
            entries = update.get("entries") or []
            lines = []
            for e in entries[:6]:
                title = e.get("title") if isinstance(e, dict) else str(e)
                if title:
                    lines.append(f"• {title}")
            content = "\n".join(lines) if lines else "Planning…"
            if thought_buffer or text_buffer:
                yield Message(
                    id=str(uuid.uuid4()),
                    project_id=project_path,
                    role="assistant",
                    message_type="chat",
                    content=self._compose_content(thought_buffer, text_buffer),
                    metadata_json={"cli_type": self.cli_type.value},
                    session_id=session_id,
                    created_at=now,
                )
            thought_buffer.clear()
            text_buffer.clear()
            yield Message(
                id=str(uuid.uuid4()),
                project_id=project_path,
                role="assistant",
                message_type="chat",
                content=content,
                metadata_json={"cli_type": self.cli_type.value, "event_type": "plan"},
                session_id=session_id,
                created_at=now,
            )

    def _compose_content(self, thought_buffer: List[str], text_buffer: List[str]) -> str:
        parts: List[str] = []
        if thought_buffer:
            thinking = "".join(thought_buffer).strip()
            if thinking:
                parts.append(f"<thinking>\n{thinking}\n</thinking>\n")
        if text_buffer:
            parts.append("".join(text_buffer))
        return "".join(parts)

    def _parse_tool_name(self, update: Dict[str, Any]) -> str:
        raw_id = update.get("toolCallId") or ""
        if isinstance(raw_id, str) and raw_id:
            base = raw_id.split("-", 1)[0]
            return base or (update.get("title") or update.get("kind") or "tool")
        return update.get("title") or update.get("kind") or "tool"

    def _extract_tool_input(self, update: Dict[str, Any]) -> Dict[str, Any]:
        tool_input: Dict[str, Any] = {}
        path: Optional[str] = None
        locs = update.get("locations")
        if isinstance(locs, list) and locs:
            first = locs[0]
            if isinstance(first, dict):
                path = (
                    first.get("path")
                    or first.get("file")
                    or first.get("file_path")
                    or first.get("filePath")
                    or first.get("uri")
                )
                if isinstance(path, str) and path.startswith("file://"):
                    path = path[len("file://"):]
        if not path:
            content = update.get("content")
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict):
                        cand = (
                            c.get("path")
                            or c.get("file")
                            or c.get("file_path")
                            or (c.get("args") or {}).get("path")
                        )
                        if cand:
                            path = cand
                            break
        if path:
            tool_input["path"] = str(path)
        return tool_input

    async def get_session_id(self, project_id: str) -> Optional[str]:
        """Get stored session ID for project"""
        return self._session_store.get(project_id)

    async def set_session_id(self, project_id: str, session_id: str) -> None:
        """Store session ID for project in memory"""
        self._session_store[project_id] = session_id
        ui.debug(f"Gemini session stored for project {project_id}: {session_id}", "Gemini")


__all__ = ["GeminiCLI"]
