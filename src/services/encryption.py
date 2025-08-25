"""
Data encryption service for secure storage of sensitive information
"""
import os
import base64
import hashlib
from cryptography.fernet import Fernet

class DataEncryption:
    """Handle encryption and decryption of sensitive data"""
    
    def __init__(self):
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_or_create_key(self):
        """Get encryption key from environment or create new one"""
        # Get key from environment variable
        key_env = os.getenv('ENCRYPTION_KEY')
        if key_env:
            try:
                # Decode base64 key from environment
                return base64.urlsafe_b64decode(key_env.encode())
            except Exception as e:
                print(f"Invalid ENCRYPTION_KEY format: {e}")
        
        # Generate new key and warn user
        new_key = Fernet.generate_key()
        print("WARNING: No valid ENCRYPTION_KEY found. Generated new key.")
        print(f"Add this to your environment: ENCRYPTION_KEY={base64.urlsafe_b64encode(new_key).decode()}")
        print("Without this key, encrypted data will be unreadable after restart!")
        return new_key
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not data:
            return None
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            print(f"Encryption failed: {e}")
            return data  # Return original data if encryption fails
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return None
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            print(f"Decryption failed: {e}")
            return encrypted_data  # Return original data if decryption fails
    
    def hash_for_search(self, data: str) -> str:
        """Create searchable hash of sensitive data"""
        if not data:
            return None
        return hashlib.sha256(data.encode()).hexdigest()

# Global encryption service instance
encryption_service = DataEncryption()