"""
Environment Variables Manager

Handles synchronization between database and .env files in Next.js projects.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from ..models.env_vars import EnvVar
from ..core.crypto import secret_box
from ..core.config import settings


def get_project_env_path(project_id: str) -> Path:
    """Get the path to project's .env file"""
    return Path(settings.projects_root) / project_id / "repo" / ".env"


def parse_env_file(env_path: Path) -> Dict[str, str]:
    """Parse .env file and return key-value pairs"""
    env_vars = {}
    
    if not env_path.exists():
        return env_vars
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Match KEY=VALUE pattern
                match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
                if match:
                    key, value = match.groups()
                    
                    # Handle quoted values
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
                
    except Exception as e:
        print(f"Error parsing .env file {env_path}: {e}")
    
    return env_vars


def write_env_file(env_path: Path, env_vars: Dict[str, str]) -> None:
    """Write environment variables to .env file"""
    try:
        # Ensure directory exists
        env_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write .env file
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write("# Environment Variables\n")
            f.write("# This file is automatically synchronized with Project Settings\n\n")
            
            # Sort keys for consistent output
            for key in sorted(env_vars.keys()):
                value = env_vars[key]
                
                # Quote values that contain spaces or special characters
                if ' ' in value or any(c in value for c in ['#', '$', '`', '"', "'"]):
                    value = f'"{value}"'
                
                f.write(f"{key}={value}\n")
                
        from ..core.terminal_ui import ui
        ui.success(f"Updated .env file: {env_path}", "EnvManager")
        
    except Exception as e:
        ui.error(f"Error writing .env file {env_path}: {e}", "EnvManager")
        raise


def load_env_vars_from_db(db: Session, project_id: str) -> Dict[str, str]:
    """Load environment variables from database for a project"""
    env_vars = {}
    
    try:
        db_env_vars = db.query(EnvVar).filter(
            EnvVar.project_id == project_id
        ).all()
        
        for env_var in db_env_vars:
            try:
                # Decrypt the value
                decrypted_value = secret_box.decrypt(env_var.value_encrypted)
                env_vars[env_var.key] = decrypted_value
            except Exception as e:
                print(f"⚠️  Failed to decrypt env var {env_var.key}: {e}")
                
    except Exception as e:
        from ..core.terminal_ui import ui
        ui.error(f"Error loading env vars from DB for project {project_id}: {e}", "EnvManager")
    
    return env_vars


def sync_env_file_to_db(db: Session, project_id: str) -> int:
    """
    Sync .env file contents to database (file -> DB)
    Returns number of variables synced
    """
    env_path = get_project_env_path(project_id)
    file_env_vars = parse_env_file(env_path)
    
    synced_count = 0
    
    try:
        # Get existing env vars from DB
        existing_vars = {
            env_var.key: env_var 
            for env_var in db.query(EnvVar).filter(EnvVar.project_id == project_id).all()
        }
        
        # Update or create env vars from file
        for key, value in file_env_vars.items():
            if key in existing_vars:
                # Update existing
                existing_var = existing_vars[key]
                try:
                    # Only update if value changed
                    current_value = secret_box.decrypt(existing_var.value_encrypted)
                    if current_value != value:
                        existing_var.value_encrypted = secret_box.encrypt(value)
                        synced_count += 1
                except Exception as e:
                    print(f"⚠️  Failed to decrypt existing value for {key}: {e}")
                    existing_var.value_encrypted = secret_box.encrypt(value)
                    synced_count += 1
            else:
                # Create new
                import uuid
                new_env_var = EnvVar(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    key=key,
                    value_encrypted=secret_box.encrypt(value),
                    scope="runtime",
                    var_type="string",
                    is_secret=True
                )
                db.add(new_env_var)
                synced_count += 1
        
        # Remove env vars from DB that are not in file
        file_keys = set(file_env_vars.keys())
        for key, existing_var in existing_vars.items():
            if key not in file_keys:
                db.delete(existing_var)
                synced_count += 1
        
        db.commit()
        from ..core.terminal_ui import ui
        ui.success(f"Synced {synced_count} env vars from file to DB", "EnvManager")
        
    except Exception as e:
        ui.error(f"Error syncing env file to DB: {e}", "EnvManager")
        db.rollback()
        raise
    
    return synced_count


def sync_db_to_env_file(db: Session, project_id: str) -> int:
    """
    Sync database contents to .env file (DB -> file)
    Returns number of variables synced
    """
    try:
        # Load from database
        env_vars = load_env_vars_from_db(db, project_id)
        
        # Write to file
        env_path = get_project_env_path(project_id)
        write_env_file(env_path, env_vars)
        
        print(f"✅ Synced {len(env_vars)} env vars from DB to file")
        return len(env_vars)
        
    except Exception as e:
        print(f"❌ Error syncing DB to env file: {e}")
        raise


def get_env_var_conflicts(db: Session, project_id: str) -> List[Dict]:
    """
    Check for conflicts between DB and .env file
    Returns list of conflicts with details
    """
    conflicts = []
    
    try:
        env_path = get_project_env_path(project_id)
        file_env_vars = parse_env_file(env_path)
        db_env_vars = load_env_vars_from_db(db, project_id)
        
        # Check for differences
        all_keys = set(file_env_vars.keys()) | set(db_env_vars.keys())
        
        for key in all_keys:
            file_value = file_env_vars.get(key)
            db_value = db_env_vars.get(key)
            
            if file_value != db_value:
                conflicts.append({
                    "key": key,
                    "file_value": file_value,
                    "db_value": db_value,
                    "conflict_type": (
                        "file_only" if file_value and not db_value else
                        "db_only" if db_value and not file_value else
                        "value_mismatch"
                    )
                })
    
    except Exception as e:
        print(f"❌ Error checking env var conflicts: {e}")
    
    return conflicts


def create_env_var(db: Session, project_id: str, key: str, value: str, 
                   scope: str = "runtime", var_type: str = "string", 
                   is_secret: bool = True, description: Optional[str] = None) -> EnvVar:
    """Create a new environment variable and sync to file"""
    import uuid
    
    # Create in database
    env_var = EnvVar(
        id=str(uuid.uuid4()),
        project_id=project_id,
        key=key,
        value_encrypted=secret_box.encrypt(value),
        scope=scope,
        var_type=var_type,
        is_secret=is_secret,
        description=description
    )
    
    db.add(env_var)
    db.commit()
    
    # Sync to file
    sync_db_to_env_file(db, project_id)
    
    return env_var


def update_env_var(db: Session, project_id: str, key: str, value: str) -> bool:
    """Update an environment variable and sync to file"""
    env_var = db.query(EnvVar).filter(
        EnvVar.project_id == project_id,
        EnvVar.key == key
    ).first()
    
    if not env_var:
        return False
    
    # Update in database
    env_var.value_encrypted = secret_box.encrypt(value)
    db.commit()
    
    # Sync to file
    sync_db_to_env_file(db, project_id)
    
    return True


def delete_env_var(db: Session, project_id: str, key: str) -> bool:
    """Delete an environment variable and sync to file"""
    env_var = db.query(EnvVar).filter(
        EnvVar.project_id == project_id,
        EnvVar.key == key
    ).first()
    
    if not env_var:
        return False
    
    # Delete from database
    db.delete(env_var)
    db.commit()
    
    # Sync to file
    sync_db_to_env_file(db, project_id)
    
    return True