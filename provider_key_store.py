"""
Encrypted storage for provider API keys.

Uses Fernet (symmetric encryption) from cryptography library.
Encryption key is derived from Flask SECRET_KEY or API_KEY_ENCRYPTION_SECRET env var.
"""
import os
import json
import base64
import hashlib
from typing import Optional, Dict
from cryptography.fernet import Fernet, InvalidToken


class ProviderKeyStore:
    """Encrypted storage for provider API keys."""
    
    def __init__(self, secret_key: str, storage_path: str = None):
        """
        Initialize key store with encryption.
        
        Args:
            secret_key: Secret key for encryption (from Flask SECRET_KEY or env var)
            storage_path: Path to store encrypted keys (defaults to config/provider_keys.json)
        """
        # Default to local config directory if not specified
        if storage_path is None:
            # Try /app/config for Docker, fall back to ./config for dev
            if os.path.exists("/app"):
                storage_path = "/app/config/provider_keys.json"
            else:
                storage_path = os.path.join(os.getcwd(), "config", "provider_keys.json")
        
        self.storage_path = storage_path
        
        # Derive a Fernet key from the secret_key
        # Fernet requires a 32-byte base64-encoded key
        key_bytes = hashlib.sha256(secret_key.encode()).digest()
        self.fernet_key = base64.urlsafe_b64encode(key_bytes)
        self.cipher = Fernet(self.fernet_key)
        
        # Ensure storage directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Load existing keys
        self._keys = self._load_keys()
    
    def _load_keys(self) -> Dict[str, str]:
        """Load and decrypt keys from storage file."""
        if not os.path.exists(self.storage_path):
            return {}
        
        try:
            with open(self.storage_path, 'r') as f:
                encrypted_data = json.load(f)
            
            # Decrypt each key
            decrypted = {}
            for provider, encrypted_key in encrypted_data.items():
                try:
                    decrypted_key = self.cipher.decrypt(encrypted_key.encode()).decode()
                    decrypted[provider] = decrypted_key
                except InvalidToken:
                    # Skip keys that can't be decrypted (wrong secret key)
                    continue
            
            return decrypted
            
        except Exception as e:
            # If file is corrupted or can't be read, start fresh
            return {}
    
    def _save_keys(self):
        """Encrypt and save keys to storage file."""
        try:
            # Encrypt each key
            encrypted_data = {}
            for provider, key in self._keys.items():
                encrypted_key = self.cipher.encrypt(key.encode()).decode()
                encrypted_data[provider] = encrypted_key
            
            # Write to file atomically (write to temp, then rename)
            temp_path = self.storage_path + ".tmp"
            with open(temp_path, 'w') as f:
                json.dump(encrypted_data, f, indent=2)
            
            # Atomic rename
            os.replace(temp_path, self.storage_path)
            
        except Exception as e:
            raise IOError(f"Failed to save provider keys: {str(e)}")
    
    def get_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider.
        
        Args:
            provider: Provider name (e.g., 'alpha_vantage')
            
        Returns:
            API key or None if not set
        """
        return self._keys.get(provider)
    
    def set_key(self, provider: str, api_key: str):
        """
        Set API key for a provider.
        
        Args:
            provider: Provider name
            api_key: API key to store (will be encrypted)
        """
        self._keys[provider] = api_key
        self._save_keys()
    
    def delete_key(self, provider: str) -> bool:
        """
        Delete API key for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            True if key was deleted, False if it didn't exist
        """
        if provider in self._keys:
            del self._keys[provider]
            self._save_keys()
            return True
        return False
    
    def list_providers_with_keys(self) -> list:
        """
        List all providers that have keys stored.
        
        Returns:
            List of provider names
        """
        return list(self._keys.keys())
    
    def clear_all(self):
        """Delete all stored keys (for testing/reset)."""
        self._keys = {}
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)


def get_encryption_secret() -> str:
    """
    Get the encryption secret from environment.
    
    Priority:
    1. API_KEY_ENCRYPTION_SECRET env var (recommended)
    2. Flask SECRET_KEY env var
    3. Fallback to dev_secret (for development only!)
    
    Returns:
        Encryption secret string
    """
    secret = os.getenv("API_KEY_ENCRYPTION_SECRET") or os.getenv("SECRET_KEY") or "dev_secret"
    
    if secret == "dev_secret":
        # Warn if using default secret
        import sys
        print(
            "WARNING: Using default encryption secret! "
            "Set API_KEY_ENCRYPTION_SECRET or SECRET_KEY environment variable for production!",
            file=sys.stderr
        )
    
    return secret
