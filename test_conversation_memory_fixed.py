#!/usr/bin/env python3
"""
Test conversation memory and follow-up capabilities - FIXED VERSION
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import uuid

def test_conversation_memory():
    """Test the complete conversation memory system"""

    print("🧠 TESTING CONVERSATION MEMORY SYSTEM")
    print("=" * 50)

    from app import create_app
    from app.models import User, Conversation
    from services.metrics_service import MetricsService
    from utils.database import db

    app = create_app()

    with app.app_context():
        # Create test user
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        test_user = User(
            id=test_user_id,
            ultrahuman_user_id=f"uh_{test_user_id}",
            phone_number="+15551234567",
            timezone='UTC',
            preferences={}
        )

        try:
            db.session.add(test_user)
            db.session.commit()
            print(f"✅ Created test user: {test_user_id}")
        except Exception as e:
            print(f"❌ Failed to create test user: {e}")
            return

        metrics_service = MetricsService()

        print("\n🔄 TEST 1: NEW CONVERSATION")
        print("-" * 30)

        # Test 1: Initial query (should create new conversation)
        query1 = "how is my heart rate today?"
        print(f"Query: '{query1}'")

        try:
            result1 = metrics_service.process_sms_input_with_context(test_user_id, query1)
            print(f"✅ Processed: {result1.get('success', False)}")
            print(f"📊 Response type: {result1.get('response_type', 'unknown')}")

            # Check if conversation was stored - FIXED QUERY
            conversations = db.session.query(Conversation).filter(Conversation.user_id == test_user_id).all()
            print(f"💾 Conversations stored: {len(conversations)}")

            if conversations:
                conv1 = conversations[0]
                print(f"📝 Query stored: '{conv1.query[:50]}...'")
                print(f"🔄 Session ID: {conv1.session_id}")
                print(f"🎯 Query type: {conv1.query_type}")

        except Exception as e:
            print(f"❌ Test 1 failed: {e}")
            import traceback
            traceback.print_exc()
            return

        print("\n🔗 TEST 2: FOLLOW-UP CONVERSATION")
        print("-" * 35)

        # Test 2: Follow-up query (should detect context)
        query2 = "what about yesterday?"
        print(f"Query: '{query2}'")

        try:
            result2 = metrics_service.process_sms_input_with_context(test_user_id, query2)
            print(f"✅ Processed: {result2.get('success', False)}")
            print(f"🔗 Is follow-up: {result2.get('is_follow_up', False)}")
            print(f"📊 Response type: {result2.get('response_type', 'unknown')}")

            # Check conversation history - FIXED QUERY
            conversations = db.session.query(Conversation).filter(Conversation.user_id == test_user_id).order_by(Conversation.created_at).all()
            print(f"💾 Total conversations: {len(conversations)}")

            if len(conversations) >= 2:
                conv2 = conversations[1]
                print(f"📝 Follow-up query: '{conv2.query[:50]}...'")
                print(f"🔗 Is follow-up: {conv2.is_follow_up}")
                print(f"👨‍👩‍👧‍👦 Parent ID: {conv2.parent_conversation_id}")

                # Check if they share the same session
                print(f"🎯 Same session: {conv2.session_id == conversations[0].session_id}")

        except Exception as e:
            print(f"❌ Test 2 failed: {e}")
            import traceback
            traceback.print_exc()

        print("\n🔍 TEST 3: CONTEXT PATTERNS")
        print("-" * 30)

        # Test 3: Different follow-up patterns
        follow_up_queries = [
            "show me more details",
            "what about sleep too?",
            "compared to last week",
            "that looks good",
            "anything else?"
        ]

        for i, query in enumerate(follow_up_queries, 3):
            print(f"Query {i}: '{query}'")
            try:
                result = metrics_service.process_sms_input_with_context(test_user_id, query)
                print(f"  🔗 Detected as follow-up: {result.get('is_follow_up', False)}")

                # Quick pattern check
                is_follow_up = metrics_service._is_follow_up_query(query, [])
                print(f"  🎯 Pattern match: {is_follow_up}")

            except Exception as e:
                print(f"  ❌ Failed: {e}")
            print()

        print("\n📊 TEST 4: SESSION MANAGEMENT")
        print("-" * 30)

        try:
            # Check session expiry logic
            conversations = db.session.query(Conversation).filter(Conversation.user_id == test_user_id).all()
            active_sessions = set(conv.session_id for conv in conversations
                                if conv.session_expires_at > datetime.utcnow())
            print(f"🕐 Active sessions: {len(active_sessions)}")

            # Test session cleanup
            expired_count = len([conv for conv in conversations
                               if conv.session_expires_at <= datetime.utcnow()])
            print(f"⏰ Expired conversations: {expired_count}")

        except Exception as e:
            print(f"❌ Session test failed: {e}")

        print("\n🔍 TEST 5: CONTEXT BUILDING")
        print("-" * 30)

        try:
            # Test context building method
            recent_convs = metrics_service._get_recent_conversations(test_user_id, limit=3)
            print(f"📚 Recent conversations found: {len(recent_convs)}")

            if recent_convs:
                context = metrics_service._build_conversation_context(recent_convs, "test query")
                print(f"📝 Context length: {len(context)} characters")
                print(f"📋 Context preview: {context[:100]}...")

        except Exception as e:
            print(f"❌ Context building failed: {e}")

        print("\n🎯 RESULTS SUMMARY")
        print("-" * 25)

        try:
            # Final statistics - FIXED QUERIES
            total_conversations = db.session.query(Conversation).filter(Conversation.user_id == test_user_id).count()
            follow_up_conversations = db.session.query(Conversation).filter(
                Conversation.user_id == test_user_id,
                Conversation.is_follow_up == True
            ).count()

            print(f"📈 Total conversations: {total_conversations}")
            print(f"🔗 Follow-up conversations: {follow_up_conversations}")
            print(f"💡 Follow-up detection rate: {follow_up_conversations/max(total_conversations-1, 1)*100:.1f}%")

            # Check database integrity
            all_convs = db.session.query(Conversation).filter(Conversation.user_id == test_user_id).all()
            sessions = set(conv.session_id for conv in all_convs)
            print(f"🎭 Unique sessions created: {len(sessions)}")

            # Cleanup test user
            print(f"\n🧹 Cleaning up test user: {test_user_id}")
            db.session.query(Conversation).filter(Conversation.user_id == test_user_id).delete()
            db.session.delete(test_user)
            db.session.commit()
            print("✅ Cleanup completed")

        except Exception as e:
            print(f"❌ Summary failed: {e}")
            # Try cleanup anyway
            try:
                db.session.query(Conversation).filter(Conversation.user_id == test_user_id).delete()
                db.session.query(User).filter(User.id == test_user_id).delete()
                db.session.commit()
            except:
                pass

        print("\n🎉 CONVERSATION MEMORY TESTING COMPLETED!")
        print("=" * 50)

if __name__ == "__main__":
    try:
        test_conversation_memory()
    except Exception as e:
        print(f"\n💥 Testing failed with error: {e}")
        import traceback
        traceback.print_exc()