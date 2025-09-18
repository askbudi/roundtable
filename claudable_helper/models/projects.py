"""Mock project models for claudable_helper.

This module provides mock implementations of the project models
that were originally imported from app.models.projects.
"""
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ProjectStatus(str, Enum):
    """Project status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ProjectType(str, Enum):
    """Project type enumeration."""
    WEB = "web"
    API = "api"
    CLI = "cli"
    LIBRARY = "library"
    OTHER = "other"


class Project:
    """Mock project model for managing project metadata."""
    
    def __init__(
        self,
        name: str,
        path: str,
        project_id: Optional[str] = None,
        description: Optional[str] = None,
        project_type: ProjectType = ProjectType.OTHER,
        status: ProjectStatus = ProjectStatus.ACTIVE,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = project_id or str(uuid.uuid4())
        self.name = name
        self.path = os.path.abspath(path) if path else ""
        self.description = description
        self.project_type = project_type
        self.status = status
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Additional computed properties
        self._validate_path()
    
    def _validate_path(self) -> None:
        """Validate that the project path exists."""
        if self.path and not os.path.exists(self.path):
            print(f"Warning: Project path does not exist: {self.path}")
    
    @property
    def exists(self) -> bool:
        """Check if the project directory exists."""
        return bool(self.path) and os.path.exists(self.path)
    
    @property
    def is_git_repo(self) -> bool:
        """Check if the project is a git repository."""
        if not self.exists:
            return False
        return os.path.exists(os.path.join(self.path, ".git"))
    
    def get_relative_path(self, file_path: str) -> str:
        """Get relative path from project root."""
        if not self.path:
            return file_path
        
        try:
            return os.path.relpath(file_path, self.path)
        except ValueError:
            return file_path
    
    def get_absolute_path(self, relative_path: str) -> str:
        """Get absolute path from project-relative path."""
        if not self.path:
            return relative_path
        
        return os.path.join(self.path, relative_path)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "project_type": self.project_type.value,
            "status": self.status.value,
            "metadata": self.metadata,
            "exists": self.exists,
            "is_git_repo": self.is_git_repo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Create project from dictionary."""
        return cls(
            project_id=data.get("id"),
            name=data.get("name", ""),
            path=data.get("path", ""),
            description=data.get("description"),
            project_type=ProjectType(data.get("project_type", "other")),
            status=ProjectStatus(data.get("status", "active")),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )
    
    @classmethod
    def from_path(cls, path: str) -> "Project":
        """Create project from path, inferring name and type."""
        path = os.path.abspath(path)
        name = os.path.basename(path)
        
        # Infer project type based on files present
        project_type = ProjectType.OTHER
        if os.path.exists(os.path.join(path, "package.json")):
            project_type = ProjectType.WEB
        elif os.path.exists(os.path.join(path, "requirements.txt")) or os.path.exists(os.path.join(path, "pyproject.toml")):
            project_type = ProjectType.API
        elif os.path.exists(os.path.join(path, "setup.py")):
            project_type = ProjectType.LIBRARY
        
        return cls(
            name=name,
            path=path,
            project_type=project_type,
        )
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update project metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get project metadata value."""
        return self.metadata.get(key, default)
    
    def __str__(self) -> str:
        """String representation of the project."""
        return f"Project(name={self.name}, path={self.path})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Project(id={self.id}, name={self.name}, type={self.project_type.value}, status={self.status.value})"