"""Mock session models for claudable_helper.

This module provides mock implementations of the session models
that were originally imported from app.models.sessions.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .messages import Message


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SessionType(str, Enum):
    """Session type enumeration."""
    CHAT = "chat"
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    ANALYSIS = "analysis"


class Session:
    """Mock session model for managing chat sessions."""
    
    def __init__(
        self,
        project_id: str,
        session_id: Optional[str] = None,
        name: Optional[str] = None,
        session_type: SessionType = SessionType.CHAT,
        status: SessionStatus = SessionStatus.ACTIVE,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = session_id or str(uuid.uuid4())
        self.project_id = project_id
        self.name = name or f"Session {self.id[:8]}"
        self.session_type = session_type
        self.status = status
        self.model = model
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Message storage
        self._messages: List[Message] = []
    
    @property
    def messages(self) -> List[Message]:
        """Get all messages in this session."""
        return self._messages[:]  # Return copy
    
    @property
    def message_count(self) -> int:
        """Get number of messages in this session."""
        return len(self._messages)
    
    @property
    def last_message(self) -> Optional[Message]:
        """Get the last message in this session."""
        return self._messages[-1] if self._messages else None
    
    def add_message(self, message: Message) -> None:
        """Add a message to this session."""
        message.session_id = self.id
        self._messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def get_messages(self, limit: Optional[int] = None, offset: int = 0) -> List[Message]:
        """Get messages with optional pagination."""
        messages = self._messages[offset:]
        if limit:
            messages = messages[:limit]
        return messages
    
    def get_user_messages(self) -> List[Message]:
        """Get only user messages."""
        return [msg for msg in self._messages if msg.message_type.value == "user"]
    
    def get_assistant_messages(self) -> List[Message]:
        """Get only assistant messages."""
        return [msg for msg in self._messages if msg.message_type.value == "assistant"]
    
    def clear_messages(self) -> None:
        """Clear all messages from this session."""
        self._messages.clear()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "session_type": self.session_type.value,
            "status": self.status.value,
            "model": self.model,
            "metadata": self.metadata,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create session from dictionary."""
        return cls(
            session_id=data.get("id"),
            project_id=data.get("project_id", ""),
            name=data.get("name"),
            session_type=SessionType(data.get("session_type", "chat")),
            status=SessionStatus(data.get("status", "active")),
            model=data.get("model"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update session metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get session metadata value."""
        return self.metadata.get(key, default)
    
    def archive(self) -> None:
        """Archive this session."""
        self.status = SessionStatus.ARCHIVED
        self.updated_at = datetime.utcnow()
    
    def activate(self) -> None:
        """Activate this session."""
        self.status = SessionStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def __str__(self) -> str:
        """String representation of the session."""
        return f"Session(name={self.name}, messages={self.message_count})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Session(id={self.id}, project_id={self.project_id}, "
            f"type={self.session_type.value}, status={self.status.value})"
        )