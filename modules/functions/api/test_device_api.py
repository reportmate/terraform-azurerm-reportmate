#!/usr/bin/env python
"""
Test the device API directly without func start
"""
import os
import sys
import json
from datetime import datetime

# Set DATABASE_URL environment variable
os.environ['DATABASE_URL'] = 'postgresql://reportmate:2sSWbVxyqjXp9WUpeMmzRaC@reportmate-database.postgres.database.azure.com:5432/reportmate?sslmode=require'

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the device API directly
from device import handle_post_device

# Mock HTTP request class
class MockHttpRequest:
    def __init__(self, body, method="POST"):
        self.method = method
        self._body = body
        self.url = "http://localhost:7071/api/device"
        self.route_params = {}
    
    def get_body(self):
        return self._body
    
    def get_json(self):
        return json.loads(self._body.decode('utf-8'))

# Sample test data (using the format from the Windows client)
test_data = {
    "source": "osquery",
    "collectionType": "modular",
    "collectionTimestamp": datetime.utcnow().isoformat() + "Z",
    "clientVersion": "1.0.0",
    "device": {
        "serial_number": "TEST-DEVICE-123",
        "hostname": "test-device"
    },
    "applications": [
        {"name": "Test App", "version": "1.0", "publisher": "Test Publisher"}
    ],
    "system": {
        "os_name": "Windows 11",
        "os_version": "22H2",
        "hostname": "test-device"
    },
    "hardware": {
        "manufacturer": "Test Corp",
        "model": "Test Model",
        "cpu": "Intel i7",
        "memory": "16GB"
    },
    "inventory": {
        "hostname": "test-device",
        "serial_number": "TEST-DEVICE-123"
    }
}

def test_device_api():
    print("🧪 Testing device API directly...")
    
    try:
        # Create mock request
        body_json = json.dumps(test_data)
        mock_request = MockHttpRequest(body_json.encode('utf-8'))
        
        print(f"📤 Sending test data: {len(body_json)} bytes")
        
        # Call the device API function directly
        response = handle_post_device(mock_request)
        
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response body: {response.get_body().decode('utf-8')}")
        
        if response.status_code == 200:
            print("✅ API test successful!")
            return True
        else:
            print("❌ API test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_device_api()
