import requests
import json
import os

BASE_URL = "http://localhost:8000/api/admin"
ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")
if not ADMIN_KEY:
    raise SystemExit("Zet ADMIN_API_KEY in de omgeving (zie .env).")

def check_hierarchy():
    print("Checking Hierarchy Tree Endpoint...")
    try:
        # Assuming dev environment has the key in .env or simplified auth
        headers = {"X-Admin-Key": ADMIN_KEY}
        response = requests.get(f"{BASE_URL}/hierarchie/tree", params={"config_id": 1}, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            tree = data.get("tree", [])
            print(f"Success! Root children count: {len(tree)}")
            
            # Verify structure - should have Titels (Quadrants) at top level
            if len(tree) > 0:
                first_node = tree[0]
                print(f"First Node Keys: {list(first_node.keys())}")
                print(f"First Node Content: {first_node}")
                # API now returns 'naam' instead of 'name'
                print(f"First Node: Naam={first_node.get('naam')}, Type={first_node.get('type')}")
                
                if first_node.get('type') == 'titel':
                    print("✅ CONFIRMED: Hierarchy includes 'titel' (Quadrant) level.")
                else:
                    print(f"❌ WARNING: First node type is '{first_node.get('type')}', expected 'titel'")
                    
                # Check children depth
                if 'children' in first_node and len(first_node['children']) > 0:
                    child = first_node['children'][0]
                    print(f"  Child Node: Naam={child.get('naam')}, Type={child.get('type')}")
                    
        else:
            print(f"Error: Status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_hierarchy()
