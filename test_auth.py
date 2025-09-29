#!/usr/bin/env python3
"""
Simple authentication test script
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test if the API is running"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Health check: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_signup():
    """Test user signup"""
    try:
        data = {
            "email": "test@example.com",
            "password": "password123", 
            "name": "Test User"
        }
        response = requests.post(f"{BASE_URL}/api/auth/signup", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Signup successful!")
            print(f"   User ID: {result['user']['user_id']}")
            print(f"   Email: {result['user']['email']}")
            print(f"   Token: {result['access_token'][:20]}...")
            return result['access_token']
        else:
            print(f"❌ Signup failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Signup error: {e}")
        return None

def test_login():
    """Test user login"""
    try:
        data = {
            "email": "test@example.com",
            "password": "password123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Login successful!")
            print(f"   User ID: {result['user']['user_id']}")
            print(f"   Token: {result['access_token'][:20]}...")
            return result['access_token']
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_me(token):
    """Test protected endpoint"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Protected endpoint works!")
            print(f"   User: {result['name']} ({result['email']})")
            return True
        else:
            print(f"❌ Protected endpoint failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Protected endpoint error: {e}")
        return False

def main():
    print("🚀 Testing FastAPI Authentication...")
    print()
    
    # Test health
    if not test_health():
        return
    print()
    
    # Test signup
    print("📝 Testing signup...")
    token = test_signup()
    print()
    
    # Test login
    print("🔐 Testing login...")
    login_token = test_login()
    print()
    
    # Test protected endpoint
    if token:
        print("🔒 Testing protected endpoint...")
        test_me(token)
    
    print("\n🎉 Authentication tests complete!")

if __name__ == "__main__":
    main()