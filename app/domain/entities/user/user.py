"""
User domain entity for authentication and RBAC.
"""
from datetime import datetime
from typing import Optional

class User:
    def __init__(
        self,
        user_id: str,
        email: str,
        password_hash: str,
        role: str = "user",
        hotel_id: Optional[str] = None,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.hotel_id = hotel_id
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_manager(self) -> bool:
        return self.role == "manager"

    def is_staff(self) -> bool:
        return self.role == "staff"

    def is_active_user(self) -> bool:
        return self.is_active
