"""
User Module

This module handles user management functionality including:
- User CRUD operations
- User profile management
- User search and filtering
"""

from .models import User
from .repository import UserRepository
from .service import UserService

__all__ = ["User", "UserRepository", "UserService"]
