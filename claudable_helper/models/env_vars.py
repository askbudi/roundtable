"""Mock environment variable models for claudable_helper.

This module provides mock implementations of the environment variable models
that were originally imported from app.models.env_vars.
"""
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class EnvVarType(str, Enum):
    """Environment variable type enumeration."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SECRET = "secret"
    JSON = "json"


class EnvVarScope(str, Enum):
    """Environment variable scope enumeration."""
    GLOBAL = "global"
    PROJECT = "project"
    SESSION = "session"


class EnvVar:
    """Mock environment variable model for managing configuration."""
    
    def __init__(
        self,
        key: str,
        value: str,
        var_type: EnvVarType = EnvVarType.STRING,
        scope: EnvVarScope = EnvVarScope.PROJECT,
        project_id: Optional[str] = None,
        env_id: Optional[str] = None,
        description: Optional[str] = None,
        is_encrypted: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = env_id or str(uuid.uuid4())
        self.key = key
        self.value = value
        self.var_type = var_type
        self.scope = scope
        self.project_id = project_id
        self.description = description
        self.is_encrypted = is_encrypted
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    @property
    def is_secret(self) -> bool:
        """Check if this is a secret environment variable."""
        return self.var_type == EnvVarType.SECRET or self.is_encrypted
    
    @property
    def masked_value(self) -> str:
        """Get masked version of the value for display."""
        if not self.is_secret:
            return self.value
        
        if len(self.value) <= 8:
            return "*" * len(self.value)
        
        return self.value[:2] + "*" * (len(self.value) - 4) + self.value[-2:]
    
    @property
    def display_value(self) -> str:
        """Get appropriate value for display (masked if secret)."""
        return self.masked_value if self.is_secret else self.value
    
    def get_typed_value(self) -> Any:
        """Get value converted to the appropriate type."""
        if self.var_type == EnvVarType.BOOLEAN:
            return self.value.lower() in ("true", "1", "yes", "on")
        elif self.var_type == EnvVarType.NUMBER:
            try:
                if "." in self.value:
                    return float(self.value)
                return int(self.value)
            except ValueError:
                return self.value
        elif self.var_type == EnvVarType.JSON:
            try:
                import json
                return json.loads(self.value)
            except (json.JSONDecodeError, ImportError):
                return self.value
        else:
            return self.value
    
    def set_value(self, value: str) -> None:
        """Set new value for the environment variable."""
        self.value = value
        self.updated_at = datetime.utcnow()
    
    def apply_to_environment(self) -> None:
        """Apply this environment variable to the current process environment."""
        os.environ[self.key] = self.value
    
    @classmethod
    def from_environment(cls, key: str, **kwargs) -> Optional["EnvVar"]:
        """Create EnvVar from current environment."""
        value = os.environ.get(key)
        if value is None:
            return None
        
        return cls(key=key, value=value, **kwargs)
    
    def to_dict(self, include_value: bool = False, mask_secrets: bool = True) -> Dict[str, Any]:
        """Convert environment variable to dictionary.
        
        Args:
            include_value: Whether to include the actual value
            mask_secrets: Whether to mask secret values
        """
        data = {
            "id": self.id,
            "key": self.key,
            "var_type": self.var_type.value,
            "scope": self.scope.value,
            "project_id": self.project_id,
            "description": self.description,
            "is_encrypted": self.is_encrypted,
            "is_secret": self.is_secret,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_value:
            if mask_secrets and self.is_secret:
                data["value"] = self.masked_value
            else:
                data["value"] = self.value
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvVar":
        """Create environment variable from dictionary."""
        return cls(
            env_id=data.get("id"),
            key=data.get("key", ""),
            value=data.get("value", ""),
            var_type=EnvVarType(data.get("var_type", "string")),
            scope=EnvVarScope(data.get("scope", "project")),
            project_id=data.get("project_id"),
            description=data.get("description"),
            is_encrypted=data.get("is_encrypted", False),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )
    
    def __str__(self) -> str:
        """String representation of the environment variable."""
        return f"EnvVar(key={self.key}, type={self.var_type.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"EnvVar(id={self.id}, key={self.key}, type={self.var_type.value}, "
            f"scope={self.scope.value}, is_secret={self.is_secret})"
        )