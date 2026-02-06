#!/usr/bin/env python3
"""
Debug Ultrahuman API Response - Actual Working Script
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def main():
    print("🔍 DEBUGGING ULTRAHUMAN PARTNER API")
    print("=" * 60)

    try:
        from app import create_app
        from tasks.data_ingestion import sync_ultrahuman_data

        # Create Flask app context
        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            print(f"📊 Running data sync for user: {user_id}")
            print(f"📅 Fetching last 3 days of data")
            print(f"🔧 Debug mode: {os.getenv('ULTRAHUMAN_DEBUG')}")
            print(f"🌐 API Base: {os.getenv('ULTRAHUMAN_API_BASE')}")
            print()
            print("⏳ Fetching data from Ultrahuman Partner API...")
            print("   (Debug logs will show actual API response structure)")
            print()

            # Run the data sync - this will trigger debug logging
            result = sync_ultrahuman_data(user_id, days_back=3)

            print("📋 SYNC RESULT:")
            print("=" * 30)

            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"✅ Success: {result['success']}")
                print(f"📈 Metrics inserted: {result.get('metrics_inserted', 0)}")

                if result.get('processing_stats'):
                    stats = result['processing_stats']
                    print(f"📊 Processing stats:")
                    for key, value in stats.items():
                        print(f"   • {key}: {value}")

            print()
            print("💡 NEXT STEPS:")
            print("   1. Check the debug logs above for actual API response structure")
            print("   2. Look for lines containing 'Partner mapping' to see data breakdown")
            print("   3. Compare API fields with what the code expects in _map_partner_to_internal")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()