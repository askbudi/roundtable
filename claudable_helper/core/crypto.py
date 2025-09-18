"""Mock crypto module for claudable_helper.

This module provides a mock implementation of the crypto interface
that was originally imported from app.core.crypto.
"""
import base64
import os
from typing import Union


class MockSecretBox:
    """Mock secret box for encryption/decryption."""
    
    def __init__(self):
        # In a real implementation, this would use proper encryption
        # For this mock, we'll just use base64 encoding as a placeholder
        pass
    
    def encrypt(self, plaintext: Union[str, bytes]) -> bytes:
        """Mock encrypt function - just base64 encode for demo."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        # Add a simple prefix to distinguish encrypted data
        prefixed = b"MOCK_ENCRYPTED:" + plaintext
        return base64.b64encode(prefixed)
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Mock decrypt function - just base64 decode for demo."""
        try:
            decoded = base64.b64decode(ciphertext)
            if decoded.startswith(b"MOCK_ENCRYPTED:"):
                return decoded[15:]  # Remove prefix
            return decoded
        except Exception:
            # If decryption fails, return empty bytes
            return b""
    
    def decrypt_str(self, ciphertext: bytes) -> str:
        """Decrypt and return as string."""
        decrypted = self.decrypt(ciphertext)
        try:
            return decrypted.decode('utf-8')
        except UnicodeDecodeError:
            return ""


# Create singleton instance
secret_box = MockSecretBox()