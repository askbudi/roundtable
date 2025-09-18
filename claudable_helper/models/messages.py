"""Mock message models for claudable_helper.

This module provides mock implementations of the message models
that were originally imported from app.models.messages.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(str, Enum):
    """Message type enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    ERROR = "error"
    CHAT = "chat"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    RESULT = "result"


class MessageStatus(str, Enum):
    """Message status enumeration."""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"


class Message:
    """Mock message model for chat interactions."""
    
    def __init__(
        self,
        content: str = "",
        message_type: MessageType = MessageType.USER,
        session_id: Optional[str] = None,
        project_id: Optional[str] = None,
        model: Optional[str] = None,
        status: MessageStatus = MessageStatus.COMPLETED,
        metadata: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        # Additional parameters for compatibility with CLI adapters
        id: Optional[str] = None,
        role: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ):
        # Handle id parameter (CLI adapters pass 'id', we prefer 'message_id')
        self.id = id or message_id or str(uuid.uuid4())
        self.content = content

        # Handle message_type as either string or enum
        if isinstance(message_type, str):
            self.message_type = MessageType(message_type)
        else:
            self.message_type = message_type

        self.session_id = session_id
        self.project_id = project_id
        self.model = model

        # Handle metadata (merge metadata_json if provided)
        self.metadata = metadata or {}
        if metadata_json:
            self.metadata.update(metadata_json)

        # Handle status as either string or enum
        if isinstance(status, str):
            self.status = MessageStatus(status)
        else:
            self.status = status

        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

        # Store role - use provided role or fallback to message_type value
        self.role = role if role is not None else self.message_type.value
        self.timestamp = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "message_type": self.message_type.value,
            "role": self.role,
            "session_id": self.session_id,
            "project_id": self.project_id,
            "model": self.model,
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            message_id=data.get("id"),
            content=data.get("content", ""),
            message_type=MessageType(data.get("message_type", "user")),
            session_id=data.get("session_id"),
            project_id=data.get("project_id"),
            model=data.get("model"),
            status=MessageStatus(data.get("status", "completed")),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )
    
    def update_content(self, content: str) -> None:
        """Update message content."""
        self.content = content
        self.updated_at = datetime.utcnow()
    
    def update_status(self, status: MessageStatus) -> None:
        """Update message status."""
        self.status = status
        self.updated_at = datetime.utcnow()
    
    def __str__(self) -> str:
        """String representation of the message."""
        return f"Message(id={self.id}, type={self.message_type.value}, content='{self.content[:50]}...')"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Message(id={self.id}, type={self.message_type.value}, "
            f"status={self.status.value}, session_id={self.session_id})"
        )