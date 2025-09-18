"""Mock token models for claudable_helper.

This module provides mock implementations of the token models
that were originally imported from app.models.tokens.
"""
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional


class TokenType(str, Enum):
    """Token type enumeration."""
    API_KEY = "api_key"
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    SERVICE_TOKEN = "service_token"


class TokenStatus(str, Enum):
    """Token status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"


class ServiceToken:
    """Mock service token model for managing API tokens."""
    
    def __init__(
        self,
        service_name: str,
        token_value: str,
        token_type: TokenType = TokenType.API_KEY,
        token_id: Optional[str] = None,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = token_id or str(uuid.uuid4())
        self.service_name = service_name
        self.token_value = token_value
        self.token_type = token_type
        self.description = description
        self.expires_at = expires_at
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    @property
    def status(self) -> TokenStatus:
        """Get current token status."""
        if self.expires_at and self.expires_at < datetime.utcnow():
            return TokenStatus.EXPIRED
        
        # In a real implementation, you might check if the token is valid
        # by making an API call or checking a database
        return TokenStatus.ACTIVE
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid and not expired."""
        return self.status == TokenStatus.ACTIVE
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return self.status == TokenStatus.EXPIRED
    
    @property
    def masked_token(self) -> str:
        """Get masked version of the token for display."""
        if len(self.token_value) <= 8:
            return "*" * len(self.token_value)
        
        return self.token_value[:4] + "*" * (len(self.token_value) - 8) + self.token_value[-4:]
    
    def set_expiry(self, days: int) -> None:
        """Set token expiry to specified number of days from now."""
        self.expires_at = datetime.utcnow() + timedelta(days=days)
        self.updated_at = datetime.utcnow()
    
    def revoke(self) -> None:
        """Revoke this token."""
        self.metadata["revoked"] = True
        self.metadata["revoked_at"] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow()
    
    @property
    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.metadata.get("revoked", False)
    
    def to_dict(self, include_token: bool = False) -> Dict[str, Any]:
        """Convert token to dictionary.
        
        Args:
            include_token: Whether to include the actual token value (dangerous!)
        """
        data = {
            "id": self.id,
            "service_name": self.service_name,
            "token_type": self.token_type.value,
            "description": self.description,
            "status": self.status.value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_token:
            data["token_value"] = self.token_value
        else:
            data["masked_token"] = self.masked_token
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceToken":
        """Create token from dictionary."""
        return cls(
            token_id=data.get("id"),
            service_name=data.get("service_name", ""),
            token_value=data.get("token_value", ""),
            token_type=TokenType(data.get("token_type", "api_key")),
            description=data.get("description"),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )
    
    def __str__(self) -> str:
        """String representation of the token."""
        return f"ServiceToken(service={self.service_name}, type={self.token_type.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"ServiceToken(id={self.id}, service={self.service_name}, "
            f"type={self.token_type.value}, status={self.status.value})"
        )