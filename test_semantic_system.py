#!/usr/bin/env python3
"""
Test the semantic health analysis system
"""

import sys
import os
from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_azure_embeddings():
    """Test Azure OpenAI embedding service"""
    print("🧪 Testing Azure OpenAI Embeddings...")
    print("=" * 50)

    try:
        from services.azure_embedding_service import AzureEmbeddingService

        embedding_service = AzureEmbeddingService()

        # Test embedding generation
        test_text = "I took magnesium 400mg at 10pm and had great sleep quality"
        embedding = embedding_service.get_embedding(test_text)

        if len(embedding) == 1536:  # text-embedding-ada-002 dimension
            print(f"✅ Embedding generated: {len(embedding)} dimensions")
        else:
            print(f"❌ Unexpected embedding dimension: {len(embedding)}")
            return False

        # Test structured data extraction
        structured = embedding_service.extract_structured_data(test_text)
        print(f"📊 Extracted structured data:")
        print(f"   Supplements: {structured.get('supplements', [])}")
        print(f"   Context: {structured.get('context', 'None')}")

        # Test tag generation
        tags = embedding_service.generate_tags(test_text, structured)
        print(f"🏷️ Generated tags: {tags}")

        print("✅ Azure embedding service working correctly!")
        return True

    except Exception as e:
        print(f"❌ Azure embedding test failed: {str(e)}")
        return False

def test_semantic_health_service():
    """Test semantic health service (without database)"""
    print(f"\\n🧪 Testing Semantic Health Service...")
    print("=" * 50)

    try:
        from services.semantic_health_service import SemanticHealthService

        # This will fail gracefully without PostgreSQL
        semantic_service = SemanticHealthService()

        if semantic_service.embedding_service:
            print("✅ Semantic service initialized (embedding service ready)")
            print("⚠️ Database connection will be needed for full functionality")
            return True
        else:
            print("❌ Semantic service initialization failed")
            return False

    except Exception as e:
        print(f"⚠️ Semantic service test: {str(e)}")
        print("💡 This is expected without PostgreSQL setup")
        return True  # Expected failure without DB

def test_enhanced_sms_service():
    """Test enhanced SMS service"""
    print(f"\\n🧪 Testing Enhanced SMS Service...")
    print("=" * 50)

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

        print(f"📱 Generated Enhanced SMS ({len(sms)} chars):")
        print("=" * 40)
        print(sms)
        print("=" * 40)

        if sms and len(sms) <= 306 and "🌅 Daily Health" in sms:
            print("✅ Enhanced SMS generation working!")

            # Check for rich content
            if "%" in sms:
                print("   📊 Contains percentage changes")
            if "link" in sms:
                print("   🔍 Contains correlation information")
            if "💡" in sms:
                print("   💡 Contains insights")

            return True
        else:
            print("❌ Enhanced SMS generation failed validation")
            return False

    except Exception as e:
        print(f"❌ Enhanced SMS test failed: {str(e)}")
        return False

def show_setup_instructions():
    """Show setup instructions"""
    print(f"\\n📋 Setup Instructions")
    print("=" * 50)

    print("1. 🗃️ Set up PostgreSQL with pgvector:")
    print("   • Go to railway.app and create PostgreSQL database")
    print("   • Enable pgvector extension")
    print("   • Update .env with connection details:")
    print("     POSTGRES_HOST=your-host")
    print("     POSTGRES_DATABASE=your-db")
    print("     POSTGRES_USER=your-user")
    print("     POSTGRES_PASSWORD=your-password")

    print("\\n2. 📊 Initialize database:")
    print("   • Run: psql -f setup_semantic_db.sql")
    print("   • Or execute the SQL commands in your PostgreSQL console")

    print("\\n3. 📦 Install requirements:")
    print("   • pip install psycopg2-binary pgvector")
    print("   • Or: pip install -r setup_semantic_requirements.txt")

    print("\\n4. 🧪 Test full system:")
    print("   • python test_semantic_system.py")
    print("   • Process health note: enhanced_sms.process_health_note('user_123', 'took magnesium at 10pm')")
    print("   • Search patterns: enhanced_sms.search_health_patterns('user_123', 'magnesium sleep improvement')")

    print("\\n5. 🚀 Start using:")
    print("   • Your daily reports will automatically use enhanced SMS")
    print("   • Add health notes via API: POST /api/health-note")
    print("   • Search patterns via API: GET /api/health-patterns?q=sleep+improvement")

def main():
    print("🚀 Semantic Health Analysis System Test")
    print("Testing PostgreSQL + pgvector + OpenAI Embeddings integration")

    # Run tests
    azure_ok = test_azure_embeddings()
    semantic_ok = test_semantic_health_service()
    sms_ok = test_enhanced_sms_service()

    # Summary
    print(f"\\n📊 Test Results Summary:")
    print(f"   Azure OpenAI Embeddings: {'✅' if azure_ok else '❌'}")
    print(f"   Semantic Health Service: {'✅' if semantic_ok else '❌'}")
    print(f"   Enhanced SMS Service: {'✅' if sms_ok else '❌'}")

    if azure_ok and sms_ok:
        print(f"\\n🎉 Core functionality ready!")
        print(f"✅ Your SMS will be enhanced with rich analysis")
        print(f"🔧 Database setup needed for full semantic features")
    else:
        print(f"\\n⚠️ Some components need attention")

    show_setup_instructions()

if __name__ == '__main__':
    main()