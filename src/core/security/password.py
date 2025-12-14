"""
Password Hashing & Verification

Uses bcrypt for secure password hashing with configurable cost factor.
"""
import re
from typing import Optional
from passlib.context import CryptContext
from src.core.configs import settings
from src.core.exceptions import ValidationException


# Initialize password context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,  # Cost factor (10-15)
)


class PasswordHasher:
    """Password hashing and verification utility"""
    
    @staticmethod
    def hash(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
        
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database
        
        Returns:
            True if password matches
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    
    @staticmethod
    def needs_update(hashed_password: str) -> bool:
        """
        Check if password hash needs to be updated.
        
        Args:
            hashed_password: Current password hash
        
        Returns:
            True if hash uses deprecated scheme or cost factor
        """
        return pwd_context.needs_update(hashed_password)
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength.
        
        Requirements:
        - Minimum length (from settings)
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        
        Args:
            password: Password to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        min_length = settings.PASSWORD_MIN_LENGTH
        
        if len(password) < min_length:
            return False, f"Password must be at least {min_length} characters"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
        
        # Check for common weak passwords
        weak_passwords = {
            "password", "password123", "12345678", "qwerty", "abc123",
            "password1", "admin123", "letmein", "welcome", "monkey123"
        }
        if password.lower() in weak_passwords:
            return False, "Password is too common"
        
        return True, None


# Convenience functions
def hash_password(password: str) -> str:
    """Hash a password"""
    return PasswordHasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return PasswordHasher.verify(plain_password, hashed_password)


def validate_and_hash_password(password: str) -> str:
    """
    Validate password strength and hash it.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    
    Raises:
        ValidationException: If password is too weak
    """
    is_valid, error = PasswordHasher.validate_password_strength(password)
    if not is_valid:
        raise ValidationException(message=error or "Password is too weak")
    
    return PasswordHasher.hash(password)