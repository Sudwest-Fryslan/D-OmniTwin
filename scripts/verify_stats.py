import requests
import json
import os

BASE_URL = "http://localhost:8000/api/admin/dashboard"
# Key matching the one in .env
ADMIN_KEY = "3aa6df22c564ae89056c42436ac1a2e0b3d27f7151fb7f2a56cef696df42a831"

def check_stats():
    print("Checking Dashboard Stats Endpoint...")
    try:
        headers = {"X-Admin-Key": ADMIN_KEY}
        response = requests.get(f"{BASE_URL}/stats", headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Data received:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_stats()
