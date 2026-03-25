"""
Test script for phone camera backend functionality.
"""

import requests
import json
import base64
import sys

BASE_URL = "http://localhost:8000"


def test_phone_camera_endpoints():
    """Test the phone camera API endpoints."""

    print("=" * 60)
    print("Phone Camera Backend Test")
    print("=" * 60)

    # Test 1: Get phone camera stats
    print("\n1. Testing GET /phone-camera/stats")
    try:
        response = requests.get(f"{BASE_URL}/phone-camera/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Status: {response.status_code}")
            print(f"   ✓ Active sessions: {data.get('active_sessions', 0)}")
            print(f"   ✓ Total scans: {data.get('total_scans', 0)}")
        else:
            print(f"   ✗ Error: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Start a scan session
    print("\n2. Testing POST /phone-camera/scan/start")
    session_id = None
    try:
        payload = {
            "camera_id": "test-camera-001",
            "device_name": "Test Device",
            "location": "Test Location",
            "scan_mode": "realtime"
        }
        response = requests.post(
            f"{BASE_URL}/phone-camera/scan/start",
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            print(f"   ✓ Status: {response.status_code}")
            print(f"   ✓ Session ID: {session_id}")
            print(f"   ✓ WebSocket URL: {data.get('websocket_url')}")
        else:
            print(f"   ✗ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: List active sessions
    print("\n3. Testing GET /phone-camera/sessions")
    try:
        response = requests.get(f"{BASE_URL}/phone-camera/sessions", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Status: {response.status_code}")
            print(f"   ✓ Active sessions count: {data.get('count', 0)}")
            for session in data.get('active_sessions', []):
                print(f"   ✓ Session: {session.get('session_id')} - {session.get('status')}")
        else:
            print(f"   ✗ Error: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 4: Get session details
    if session_id:
        print(f"\n4. Testing GET /phone-camera/sessions/{session_id}")
        try:
            response = requests.get(f"{BASE_URL}/phone-camera/sessions/{session_id}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Status: {response.status_code}")
                print(f"   ✓ Camera ID: {data.get('camera_id')}")
                print(f"   ✓ Device Info: {data.get('device_info')}")
                print(f"   ✓ Location: {data.get('location')}")
            else:
                print(f"   ✗ Error: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

    # Test 5: Stop the scan session
    if session_id:
        print(f"\n5. Testing POST /phone-camera/scan/{session_id}/stop")
        try:
            response = requests.post(f"{BASE_URL}/phone-camera/scan/{session_id}/stop", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Status: {response.status_code}")
                print(f"   ✓ Session stopped: {data.get('session_id')}")
                print(f"   ✓ Total frames: {data.get('summary', {}).get('total_frames', 0)}")
            else:
                print(f"   ✗ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

    # Test 6: Get scan history
    print("\n6. Testing GET /phone-camera/history")
    try:
        response = requests.get(f"{BASE_URL}/phone-camera/history", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Status: {response.status_code}")
            print(f"   ✓ History count: {data.get('count', 0)}")
        else:
            print(f"   ✗ Error: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_phone_camera_endpoints()
