#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(PROJECT_ROOT))

from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.models import UserModel
from passlib.hash import bcrypt
import uuid
from datetime import datetime

def create_test_user():
    """Create a test user for login testing"""
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(UserModel).filter_by(email="teste@hotel.com").first()
        if existing_user:
            print("✅ User 'teste@hotel.com' already exists")
            print(f"   Email: {existing_user.email}")
            print(f"   Role: {existing_user.role}")
            print(f"   Hotel ID: {existing_user.hotel_id}")
            print(f"   Active: {existing_user.is_active}")
            return
        
        # Create new test user
        test_user = UserModel(
            id=str(uuid.uuid4()),
            email="teste@hotel.com",
            password_hash=bcrypt.hash("123456"),
            role="user",
            hotel_id="hotel-teste-001",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        db.add(test_user)
        db.commit()
        
        print("✅ Test user created successfully!")
        print("📧 Email: teste@hotel.com")
        print("🔑 Password: 123456")
        print("🏨 Hotel ID: hotel-teste-001")
        print("🌐 Login URL: http://localhost:4173/login")
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
