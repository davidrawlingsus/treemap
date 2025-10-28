"""
Script to upload the sample Intercom JSON data to the database via API.
Run this after the server is running to test the end-to-end flow.
"""
import requests
import json
import sys

API_URL = "http://localhost:8000"

def main():
    try:
        # Check if API is running
        print("🔌 Checking API connection...")
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ API is running")
        else:
            print("❌ API is not responding correctly")
            sys.exit(1)
        
        # Upload JSON file
        json_file_path = "../rows_MRT - Intercom chats - Topics in order.json"
        print(f"\n📤 Uploading {json_file_path}...")
        
        with open(json_file_path, 'rb') as f:
            files = {'file': ('intercom_data.json', f, 'application/json')}
            data = {'name': 'Sample Intercom Data - Q4 2024'}
            response = requests.post(f"{API_URL}/api/data-sources/upload", files=files, data=data)
        
        if response.status_code == 200:
            data_source = response.json()
            print(f"✅ Data source uploaded successfully!")
            print(f"   ID: {data_source['id']}")
            print(f"   Name: {data_source['name']}")
            print(f"\n🎉 You can now open index.html in your browser to see the visualization!")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   {response.text}")
            sys.exit(1)
            
    except FileNotFoundError:
        print(f"❌ Could not find JSON file at {json_file_path}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to API at {API_URL}")
        print(f"   Make sure the server is running: uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


