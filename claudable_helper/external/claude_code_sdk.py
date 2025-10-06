"""Mock implementation of claude_code_sdk for claudable_helper.

This module provides mock implementations of the Claude Code SDK classes
to make the claudable_helper module importable without the actual SDK.

It now includes a minimal `types` module that mirrors the core classes
that adapters expect (SystemMessage, AssistantMessage, UserMessage,
ResultMessage and content blocks like TextBlock, ToolUseBlock,
ToolResultBlock). This allows local, deterministic tests of message
flows without hitting the real Claude Code backend.
"""
from typing import Any, AsyncGenerator, Dict, List, Optional
import asyncio
import uuid
from datetime import datetime
import types as _types


class ClaudeCodeOptions:
    """Mock ClaudeCodeOptions class."""
    
    def __init__(
        self,
        project_path: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ):
        self.project_path = project_path
        self.model = model
        self.system_prompt = system_prompt
        self.session_id = session_id
        self.extra_options = kwargs


class MockMessage:
    """Mock message class for Claude Code SDK."""
    
    def __init__(self, content: str = "", role: str = "assistant", **kwargs):
        self.content = content
        self.role = role
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.extra_data = kwargs


class MockStreamingResponse:
    """Mock streaming response class."""
    
    def __init__(self, content: str = "Mock response from Claude Code"):
        self.content = content
        self.chunks = self._split_into_chunks(content)
        self.index = 0
    
    def _split_into_chunks(self, content: str) -> List[str]:
        """Split content into chunks for streaming simulation."""
        chunk_size = 20
        return [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.chunks):
            raise StopAsyncIteration
        
        chunk = self.chunks[self.index]
        self.index += 1
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        return MockMessage(content=chunk)


class ClaudeSDKClient:
    """Mock ClaudeSDKClient class."""
    
    def __init__(self, options: Optional[ClaudeCodeOptions] = None):
        self.options = options or ClaudeCodeOptions()
        self._is_connected = False
    
    async def __aenter__(self):
        self._is_connected = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._is_connected = False

    async def query(self, instruction: str, **kwargs):
        """Mock query method that the Claude adapter expects."""
        if not self._is_connected:
            raise RuntimeError("Client not connected. Use 'async with' context manager.")

        # Just store the instruction for potential use
        self._last_instruction = instruction
        # Return immediately since this is just sending the query
        return None

    async def receive_messages(self):
        """Mock message receiving method emitting realistic typed events.

        Sequence:
        1) SystemMessage (init + session_id)
        2) AssistantMessage with ToolUseBlock (LS .)
        3) AssistantMessage with TextBlock (natural language result)
        4) ResultMessage (summary metrics)
        """
        if not self._is_connected:
            raise RuntimeError("Client not connected. Use 'async with' context manager.")

        instruction = getattr(self, "_last_instruction", "default task")

        # Import our mock types
        t = sys.modules.get("claude_code_sdk.types")
        SystemMessage = getattr(t, "SystemMessage")
        AssistantMessage = getattr(t, "AssistantMessage")
        TextBlock = getattr(t, "TextBlock")
        ToolUseBlock = getattr(t, "ToolUseBlock")
        ResultMessage = getattr(t, "ResultMessage")

        # 1) System init
        yield SystemMessage(session_id=str(uuid.uuid4()), subtype="init")
        await asyncio.sleep(0.02)

        # If the instruction looks like counting files, use LS
        use_ls = "count files" in instruction.lower()
        if use_ls:
            # 2) Tool use (LS .)
            tool = ToolUseBlock(id=str(uuid.uuid4()), name="LS", input={"path": "."})
            yield AssistantMessage(content=[tool])
            await asyncio.sleep(0.02)

            # Simulate computing a count. We won't actually touch the FS here to
            # keep the mock deterministic; just return a plausible value.
            fake_count = 7
            text = TextBlock(text=f"Found {fake_count} items in .")
            yield AssistantMessage(content=[text])
        else:
            text = TextBlock(
                text=(
                    f"I'll help you with: {instruction[:50]}"
                    f"{'...' if len(instruction) > 50 else ''}"
                )
            )
            yield AssistantMessage(content=[text])

        await asyncio.sleep(0.02)

        # 4) Result
        yield ResultMessage(
            duration_ms=42,
            duration_api_ms=30,
            total_cost_usd=0.0,
            num_turns=1,
            is_error=False,
            subtype="complete",
            session_id=str(uuid.uuid4()),
        )

    async def chat_stream(
        self,
        message: str,
        **kwargs
    ) -> AsyncGenerator[MockMessage, None]:
        """Mock streaming chat method."""
        if not self._is_connected:
            raise RuntimeError("Client not connected. Use 'async with' context manager.")
        
        # Simulate a response
        response_content = f"Mock response to: {message[:50]}{'...' if len(message) > 50 else ''}"
        
        streaming_response = MockStreamingResponse(response_content)
        async for chunk in streaming_response:
            yield chunk
    
    async def chat(self, message: str, **kwargs) -> MockMessage:
        """Mock non-streaming chat method."""
        if not self._is_connected:
            raise RuntimeError("Client not connected. Use 'async with' context manager.")
        
        response_content = f"Mock response to: {message[:50]}{'...' if len(message) > 50 else ''}"
        return MockMessage(content=response_content)


# Mock types module for compatibility
class _TypesModule(_types.ModuleType):
    """Module-like container for mock Claude Code types."""

    class SystemMessage:
        def __init__(self, session_id: Optional[str] = None, subtype: Optional[str] = None):
            self.session_id = session_id
            self.subtype = subtype

    class TextBlock:
        def __init__(self, text: str):
            self.text = text

    class ToolUseBlock:
        def __init__(self, id: str, name: str, input: Dict[str, Any]):
            self.id = id
            self.name = name
            self.input = input

    class ToolResultBlock:
        def __init__(self, tool_use_id: str, content: Any = None, is_error: bool = False):
            self.tool_use_id = tool_use_id
            self.content = content
            self.is_error = is_error

    class AssistantMessage:
        def __init__(self, content: List[Any]):
            # In the real SDK, content is a list of blocks
            self.content = content

    class UserMessage:
        def __init__(self, content: Any):
            self.content = content

    class ResultMessage:
        def __init__(
            self,
            duration_ms: int = 0,
            duration_api_ms: int = 0,
            total_cost_usd: float = 0.0,
            num_turns: int = 0,
            is_error: bool = False,
            subtype: Optional[str] = None,
            session_id: Optional[str] = None,
        ):
            self.duration_ms = duration_ms
            self.duration_api_ms = duration_api_ms
            self.total_cost_usd = total_cost_usd
            self.num_turns = num_turns
            self.is_error = is_error
            self.subtype = subtype
            self.session_id = session_id


# Make the mock module importable as claude_code_sdk
import sys
sys.modules["claude_code_sdk"] = sys.modules[__name__]
_types_mod = _TypesModule("claude_code_sdk.types")
sys.modules["claude_code_sdk.types"] = _types_mod

# Re-export names for convenience
TextBlock = _types_mod.TextBlock
ToolUseBlock = _types_mod.ToolUseBlock
ToolResultBlock = _types_mod.ToolResultBlock
AssistantMessage = _types_mod.AssistantMessage
UserMessage = _types_mod.UserMessage
SystemMessage = _types_mod.SystemMessage
ResultMessage = _types_mod.ResultMessage
