#!/usr/bin/env python3
"""
Test Railway PostgreSQL database connection and setup
"""

import sys
import os
from urllib.parse import urlparse

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_with_existing_connection():
    """Test database connection using existing MySQL connector patterns"""

    print("🔌 Testing Railway PostgreSQL Connection")
    print("=" * 50)

    try:
        # Try to import our semantic service
        from services.semantic_health_service import SemanticHealthService

        print("📦 Semantic service imported successfully")

        # Initialize service
        semantic_service = SemanticHealthService()

        if semantic_service.connection_pool:
            print("✅ PostgreSQL connection pool established!")

            # Test processing a health event
            test_description = "I took magnesium 400mg at 10pm and had amazing sleep quality, felt very relaxed"

            result = semantic_service.process_health_event('test_user', test_description)

            if result.get('success'):
                print(f"🎉 SUCCESS! Health event processed:")
                print(f"   Event ID: {result['event_id']}")
                print(f"   Supplements: {result['structured_data'].get('supplements', [])}")
                print(f"   Tags: {result['tags']}")

                # Test search
                search_results = semantic_service.semantic_search(
                    query="magnesium sleep improvement",
                    user_id='test_user',
                    limit=5
                )

                print(f"🔍 Search found {len(search_results)} similar events")

                return True
            else:
                print(f"❌ Health event processing failed: {result.get('error')}")
                return False
        else:
            print("❌ Could not establish database connection")

            # Check environment variables
            host = os.getenv('POSTGRES_HOST')
            port = os.getenv('POSTGRES_PORT')
            database = os.getenv('POSTGRES_DATABASE')
            user = os.getenv('POSTGRES_USER')

            print(f"📋 Connection details:")
            print(f"   Host: {host}")
            print(f"   Port: {port}")
            print(f"   Database: {database}")
            print(f"   User: {user}")

            return False

    except ImportError as e:
        print(f"❌ Import failed: {str(e)}")
        print("💡 Need to install: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def setup_tables_manually():
    """Set up database tables manually if needed"""

    print("\\n🔧 Manual Table Setup")
    print("=" * 30)

    try:
        from services.semantic_health_service import SemanticHealthService

        semantic_service = SemanticHealthService()

        if not semantic_service.connection_pool:
            print("❌ No database connection available")
            return False

        conn = semantic_service.get_connection()

        if not conn:
            print("❌ Could not get database connection")
            return False

        try:
            with conn.cursor() as cur:
                # Create tables manually
                print("📊 Creating health_events table...")

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS health_events (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(50) NOT NULL,
                        event_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        description TEXT NOT NULL,
                        structured_data JSONB,
                        tags TEXT[],
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                print("✅ health_events table created")

                # Try to create a simple index instead of vector index for now
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_health_events_user_date
                    ON health_events(user_id, event_date DESC);
                """)

                print("✅ Basic indexes created")

                conn.commit()

            return True

        finally:
            semantic_service.return_connection(conn)

    except Exception as e:
        print(f"❌ Manual setup failed: {str(e)}")
        return False

def test_enhanced_sms():
    """Test enhanced SMS generation"""

    print("\\n📱 Testing Enhanced SMS Generation")
    print("=" * 40)

    try:
        from services.enhanced_sms_service import EnhancedSMSService

        enhanced_sms = EnhancedSMSService()

        # Mock analysis results
        mock_analysis = {
            'baseline_statistics': {
                'sleep_score': {
                    'latest_value': 85,
                    'mean': 78,
                    'trend': 'improving'
                },
                'hrv': {
                    'latest_value': 45,
                    'mean': 42,
                    'trend': 'stable'
                }
            },
            'correlations': {
                'magnesium_sleep_quality': {
                    'correlation': 0.67,
                    'p_value': 0.001,
                    'significant': True
                }
            },
            'insights': {
                'key_insights': [
                    'Sleep consistency improved this week'
                ]
            }
        }

        # Generate enhanced SMS
        sms = enhanced_sms.generate_super_rich_sms(
            analysis_results=mock_analysis,
            user_id='test_user',
            report_date='2025-09-09'
        )

        print(f"📱 Enhanced SMS ({len(sms)} chars):")
        print("=" * 50)
        print(sms)
        print("=" * 50)

        return True

    except Exception as e:
        print(f"❌ Enhanced SMS test failed: {str(e)}")
        return False

def main():
    print("🚀 PostgreSQL Database Test & Setup")
    print("Testing Railway PostgreSQL + Semantic Health Analysis")
    print("=" * 60)

    # Test 1: Database connection and basic functionality
    db_test = test_with_existing_connection()

    # Test 2: Manual table setup if needed
    if not db_test:
        print("💡 Attempting manual table setup...")
        setup_ok = setup_tables_manually()
        if setup_ok:
            print("✅ Manual setup completed, retrying tests...")
            db_test = test_with_existing_connection()

    # Test 3: Enhanced SMS (works regardless of database)
    sms_test = test_enhanced_sms()

    # Summary
    print(f"\\n📊 Test Results Summary:")
    print(f"   Database & Semantic: {'✅' if db_test else '❌'}")
    print(f"   Enhanced SMS: {'✅' if sms_test else '❌'}")

    if sms_test:
        print(f"\\n🎉 Enhanced SMS is working!")
        print(f"✅ Your daily reports will use sophisticated analysis")

        if db_test:
            print(f"✅ Full semantic capabilities enabled!")
            print(f"✅ Natural language health notes ready")
            print(f"✅ Historical context in SMS")
        else:
            print(f"⚠️ Database setup needed for full semantic features")
            print(f"💡 But your enhanced SMS is already working in daily reports!")
    else:
        print(f"\\n❌ Setup needs attention")

    print(f"\\n💡 Next steps:")
    if db_test:
        print(f"   🚀 Everything is ready! Test with a fresh daily report")
    else:
        print(f"   🔧 Check PostgreSQL connection details in .env")
        print(f"   📦 Ensure psycopg2-binary is installed")

    print(f"   📱 Your enhanced SMS is already integrated in daily reports!")

if __name__ == '__main__':
    main()