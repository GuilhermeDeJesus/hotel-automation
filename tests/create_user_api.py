#!/usr/bin/env python3

import requests
import json

# API endpoint
register_url = "http://localhost:8000/api/auth/register"

# User data
user_data = {
    "email": "teste@hotel.com",
    "password": "123456",
    "hotel_id": "hotel-teste-001"
}

try:
    print("Creating test user via API...")
    response = requests.post(register_url, json=user_data)
    
    if response.status_code == 201:
        print("✅ Test user created successfully!")
        print("📧 Email: teste@hotel.com")
        print("🔑 Password: 123456")
        print("🏨 Hotel ID: hotel-teste-001")
        print("🌐 Login URL: http://localhost:4173/login")
    elif response.status_code == 400 and "already registered" in response.text:
        print("✅ User 'teste@hotel.com' already exists")
        print("📧 Email: teste@hotel.com")
        print("🔑 Password: 123456")
        print("🏨 Hotel ID: hotel-teste-001")
        print("🌐 Login URL: http://localhost:4173/login")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to API. Make sure the backend is running on http://localhost:8000")
except Exception as e:
    print(f"❌ Error: {e}")
