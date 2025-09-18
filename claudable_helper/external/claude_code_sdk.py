"""Mock implementation of claude_code_sdk for claudable_helper.

This module provides mock implementations of the Claude Code SDK classes
to make the claudable_helper module importable without the actual SDK.
"""
from typing import Any, AsyncGenerator, Dict, List, Optional
import asyncio
import uuid
from datetime import datetime


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
        """Mock message receiving method."""
        if not self._is_connected:
            raise RuntimeError("Client not connected. Use 'async with' context manager.")

        # Simulate receiving messages after a query
        instruction = getattr(self, '_last_instruction', 'default task')
        response_content = f"I'll help you with: {instruction[:50]}{'...' if len(instruction) > 50 else ''}"

        # Yield a mock message
        yield MockMessage(content=response_content, role="assistant")

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
class MockTypes:
    """Mock types namespace."""
    
    class MessageContent:
        def __init__(self, text: str = ""):
            self.text = text
    
    class Message:
        def __init__(self, content: str = "", role: str = "assistant"):
            self.content = MockTypes.MessageContent(content)
            self.role = role
    
    class StreamingMessage:
        def __init__(self, content: str = "", role: str = "assistant"):
            self.content = MockTypes.MessageContent(content)
            self.role = role


# Create a mock types module structure
types = MockTypes()


# Make the mock module importable as claude_code_sdk
import sys
sys.modules['claude_code_sdk'] = sys.modules[__name__]
sys.modules['claude_code_sdk.types'] = types