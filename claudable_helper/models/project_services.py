"""Mock project service models for claudable_helper.

This module provides mock implementations of the project service models
that were originally imported from app.models.project_services.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ServiceType(str, Enum):
    """Service type enumeration."""
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    STORAGE = "storage"
    API = "api"
    CDN = "cdn"
    MONITORING = "monitoring"
    DEPLOYMENT = "deployment"
    OTHER = "other"


class ConnectionStatus(str, Enum):
    """Connection status enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


class ProjectServiceConnection:
    """Mock project service connection model."""
    
    def __init__(
        self,
        project_id: str,
        service_name: str,
        service_type: ServiceType,
        connection_id: Optional[str] = None,
        connection_string: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = connection_id or str(uuid.uuid4())
        self.project_id = project_id
        self.service_name = service_name
        self.service_type = service_type
        self.connection_string = connection_string
        self.config = config or {}
        self.credentials = credentials or {}
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Runtime status
        self._status = ConnectionStatus.UNKNOWN
        self._last_check: Optional[datetime] = None
    
    @property
    def status(self) -> ConnectionStatus:
        """Get current connection status."""
        return self._status
    
    @property
    def last_check(self) -> Optional[datetime]:
        """Get timestamp of last status check."""
        return self._last_check
    
    @property
    def is_connected(self) -> bool:
        """Check if service is currently connected."""
        return self._status == ConnectionStatus.CONNECTED
    
    @property
    def masked_connection_string(self) -> Optional[str]:
        """Get masked version of connection string for display."""
        if not self.connection_string:
            return None
        
        # Simple masking - replace passwords and sensitive info
        masked = self.connection_string
        
        # Mask password in connection strings
        if "://" in masked:
            try:
                scheme, rest = masked.split("://", 1)
                if "@" in rest:
                    auth, host_part = rest.split("@", 1)
                    if ":" in auth:
                        user, _ = auth.split(":", 1)
                        masked = f"{scheme}://{user}:***@{host_part}"
            except ValueError:
                pass  # Keep original if parsing fails
        
        return masked
    
    async def test_connection(self) -> bool:
        """Test the service connection (mock implementation)."""
        # In a real implementation, this would actually test the connection
        # For mock, we'll simulate success most of the time
        import random
        
        success = random.random() > 0.1  # 90% success rate
        self._status = ConnectionStatus.CONNECTED if success else ConnectionStatus.ERROR
        self._last_check = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        return success
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update service configuration."""
        self.config.update(config)
        self.updated_at = datetime.utcnow()
    
    def update_credentials(self, credentials: Dict[str, str]) -> None:
        """Update service credentials."""
        self.credentials.update(credentials)
        self.updated_at = datetime.utcnow()
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
        self.updated_at = datetime.utcnow()
    
    def to_dict(self, include_credentials: bool = False, mask_sensitive: bool = True) -> Dict[str, Any]:
        """Convert service connection to dictionary.
        
        Args:
            include_credentials: Whether to include credentials
            mask_sensitive: Whether to mask sensitive information
        """
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "service_name": self.service_name,
            "service_type": self.service_type.value,
            "config": self.config,
            "metadata": self.metadata,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if self.connection_string:
            if mask_sensitive:
                data["connection_string"] = self.masked_connection_string
            else:
                data["connection_string"] = self.connection_string
        
        if include_credentials:
            data["credentials"] = self.credentials
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectServiceConnection":
        """Create service connection from dictionary."""
        return cls(
            connection_id=data.get("id"),
            project_id=data.get("project_id", ""),
            service_name=data.get("service_name", ""),
            service_type=ServiceType(data.get("service_type", "other")),
            connection_string=data.get("connection_string"),
            config=data.get("config", {}),
            credentials=data.get("credentials", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )
    
    def __str__(self) -> str:
        """String representation of the service connection."""
        return f"ProjectServiceConnection(service={self.service_name}, type={self.service_type.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"ProjectServiceConnection(id={self.id}, project_id={self.project_id}, "
            f"service={self.service_name}, type={self.service_type.value}, status={self.status.value})"
        )