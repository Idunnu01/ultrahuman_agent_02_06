#!/usr/bin/env python3
"""
Test Ultrahuman API directly without Flask dependencies.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

def test_ultrahuman_api():
    """Test Ultrahuman API directly"""

    print("=" * 60)
    print("TESTING ULTRAHUMAN API DIRECTLY")
    print("=" * 60)

    # Get API credentials
    api_key = os.getenv('ULTRAHUMAN_API_KEY')  # Use ULTRAHUMAN_API_KEY instead of UH_AUTH_KEY
    api_base = os.getenv('ULTRAHUMAN_API_BASE')
    user_email = os.getenv('UH_EMAIL')

    print(f"API Base: {api_base}")
    print(f"API Key: {'*' * 10 if api_key else 'NOT SET'}")
    print(f"User Email: {user_email}")
    print()

    if not api_key or not api_base or not user_email:
        print("❌ Missing API credentials!")
        return False

    # Test API endpoints
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # Test 1: Get user info
    print("1. Testing user info endpoint...")
    try:
        user_url = f"{api_base}/user"
        response = requests.get(user_url, headers=headers)

        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ User info retrieved successfully")
            print(f"   User ID: {user_data.get('id', 'N/A')}")
            print(f"   Email: {user_data.get('email', 'N/A')}")
            print(f"   Name: {user_data.get('name', 'N/A')}")
        else:
            print(f"❌ User info failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ User info error: {str(e)}")

    print()

    # Test 2: Get metrics for recent dates
    print("2. Testing metrics endpoint...")

    # Try different date ranges
    date_ranges = [
        ("Last 7 days", datetime.now() - timedelta(days=7), datetime.now()),
        ("Last 30 days", datetime.now() - timedelta(days=30), datetime.now()),
        ("August 2025", datetime(2025, 8, 1), datetime(2025, 8, 28)),
        ("July 2025", datetime(2025, 7, 1), datetime(2025, 7, 31)),
    ]

    for range_name, start_date, end_date in date_ranges:
        print(f"\n   Testing {range_name}...")

        try:
            metrics_url = f"{api_base}/metrics"
            params = {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'metrics': 'temperature,heart_rate,sleep_score,hrv,recovery'
            }

            response = requests.get(metrics_url, headers=headers, params=params)

            if response.status_code == 200:
                metrics_data = response.json()
                print(f"   ✅ {range_name}: {len(metrics_data)} data points")

                # Show sample data
                if metrics_data:
                    sample = metrics_data[0] if isinstance(metrics_data, list) else metrics_data
                    print(f"      Sample: {sample}")
            else:
                print(f"   ❌ {range_name}: {response.status_code}")
                print(f"      Response: {response.text[:200]}...")

        except Exception as e:
            print(f"   ❌ {range_name} error: {str(e)}")

    print()

    # Test 3: Check available metrics
    print("3. Testing available metrics...")
    try:
        available_url = f"{api_base}/metrics/available"
        response = requests.get(available_url, headers=headers)

        if response.status_code == 200:
            available_data = response.json()
            print(f"✅ Available metrics retrieved")
            print(f"   Metrics: {available_data}")
        else:
            print(f"❌ Available metrics failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Available metrics error: {str(e)}")

    print("\n" + "=" * 60)
    print("API TEST COMPLETE")
    print("=" * 60)

    return True

def show_next_steps():
    """Show next steps based on API test results"""

    print("\nNEXT STEPS:")
    print("1. If API tests pass, the issue is with the database/user lookup")
    print("2. If API tests fail, check your credentials and network")
    print("3. Try different date ranges to find when you have data")
    print("4. Check if your Ultrahuman device is syncing properly")

if __name__ == "__main__":
    test_ultrahuman_api()
    show_next_steps()
