"""
Token storage service for local development
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from ..models.tokens import ServiceToken

def save_service_token(
    db: Session, 
    provider: str, 
    token: str, 
    name: str
) -> ServiceToken:
    """Save a service token to database"""
    # Delete existing token for this provider (enforce one token per provider)
    existing = db.query(ServiceToken).filter_by(provider=provider).first()
    if existing:
        db.delete(existing)
    
    # Create new token (plain text for local development)
    service_token = ServiceToken(
        id=str(uuid.uuid4()),
        provider=provider,
        name=name,
        token=token,
        created_at=datetime.utcnow()
    )
    
    db.add(service_token)
    db.commit()
    db.refresh(service_token)
    
    return service_token

def get_service_token(db: Session, provider: str) -> Optional[ServiceToken]:
    """Get service token by provider"""
    return db.query(ServiceToken).filter_by(provider=provider).first()

def get_token(db: Session, provider: str) -> Optional[str]:
    """Get plain text token by provider"""
    service_token = get_service_token(db, provider)
    if service_token:
        return service_token.token
    return None

def delete_service_token(db: Session, token_id: str) -> bool:
    """Delete a service token"""
    token = db.query(ServiceToken).filter_by(id=token_id).first()
    if token:
        db.delete(token)
        db.commit()
        return True
    return False

def update_last_used(db: Session, provider: str):
    """Update last used timestamp for a token"""
    db.query(ServiceToken).filter_by(provider=provider).update({
        "last_used": datetime.utcnow()
    })
    db.commit()

# Legacy function for backward compatibility
def get_decrypted_token(db: Session, provider: str) -> Optional[str]:
    """Legacy function - use get_token instead"""
    return get_token(db, provider)

class TokenService:
    """Token service class for compatibility"""
    
    def save_service_token(self, db: Session, provider: str, token: str, name: str) -> ServiceToken:
        return save_service_token(db, provider, token, name)
    
    def get_service_token(self, db: Session, provider: str) -> Optional[ServiceToken]:
        return get_service_token(db, provider)
    
    def get_token(self, db: Session, provider: str) -> Optional[str]:
        return get_token(db, provider)
    
    def get_decrypted_token(self, db: Session, provider: str) -> Optional[str]:
        """Legacy method - use get_token instead"""
        return get_token(db, provider)
    
    def delete_service_token(self, db: Session, token_id: str) -> bool:
        return delete_service_token(db, token_id)
    
    def update_last_used(self, db: Session, provider: str):
        return update_last_used(db, provider)
    
    async def get_token_async(self, provider: str, db: Session = None) -> Optional[dict]:
        """Get token for a provider - async version for compatibility"""
        if db is None:
            return None
        
        token = self.get_token(db, provider)
        if token:
            return {"token": token, "provider": provider}
        return None