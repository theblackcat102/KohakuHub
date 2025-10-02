"""Test authentication system."""

import requests

BASE_URL = "http://127.0.0.1:48888/api"

# 1. Register
print("=== Testing Registration ===")
resp = requests.post(
    f"{BASE_URL}/auth/register",
    json={
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "testpass123",
    },
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}\n")

# 2. Login
print("=== Testing Login ===")
resp = requests.post(
    f"{BASE_URL}/auth/login", json={"username": "testuser2", "password": "testpass123"}
)
print(f"Status: {resp.status_code}")
result = resp.json()
print(f"Response: {result}\n")

# Save session cookie and secret
session = requests.Session()
session.cookies.update(resp.cookies)
session_secret = result.get("session_secret")
print(f"Session secret: {session_secret}\n")

# 3. Get current user
print("=== Testing Get Current User ===")
resp = session.get(f"{BASE_URL}/auth/me")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}\n")

# 4. Create API token
print("=== Testing Create Token ===")
resp = session.post(f"{BASE_URL}/auth/tokens/create", json={"name": "test-token"})
print(f"Status: {resp.status_code}")
result = resp.json()
print(f"Response: {result}\n")

token = result["token"]
print(f"Generated token: {token}\n")
print(f"Session secret for encryption: {result['session_secret']}\n")

# 5-1. List tokens
print("=== Testing List Tokens ===")
resp = session.get(f"{BASE_URL}/auth/tokens")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}\n")

# 6. Test token-based auth
print("=== Testing Token Auth ===")
headers = {"Authorization": f"Bearer {token}"}
resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}\n")

# 5-2. List tokens
print("=== Testing List Tokens ===")
resp = session.get(f"{BASE_URL}/auth/tokens")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}\n")

# 7. Logout
print("=== Testing Logout ===")
resp = session.post(f"{BASE_URL}/auth/logout")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}\n")

# 8. Verify session cleared
print("=== Testing Session Cleared ===")
resp = session.get(f"{BASE_URL}/auth/me")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}\n")

# 9. Verify token still works
print("=== Testing Token Still Works ===")
resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}\n")
