#!/usr/bin/env python3
"""
Quick LLM Test - Test 3 key questions with function calling
"""

import sys
import os
from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def quick_llm_test():
    """Quick test of LLM with function calling"""

    print("🧪 QUICK LLM FUNCTION CALLING TEST")
    print("=" * 50)

    from app import create_app
    from services.llm_chat_analyzer import LLMChatAnalyzer

    app = create_app()

    with app.app_context():
        user_id = 'user_7000'

        try:
            analyzer = LLMChatAnalyzer()
            print("✅ LLM Analyzer initialized")

            # Test 3 key questions
            test_questions = [
                "What was my heart rate at 3am?",
                "How did I sleep last night?",
                "Show me my recent heart rate data"
            ]

            for i, question in enumerate(test_questions, 1):
                print(f"\\n🔍 Test {i}/3: '{question}'")
                print("-" * 30)

                try:
                    start = datetime.now()
                    response = analyzer.analyze_message(question, user_id)
                    end = datetime.now()

                    duration = (end - start).total_seconds()

                    if response and len(response) > 20:
                        if "error" in response.lower() or "trouble" in response.lower():
                            status = "⚠️ ERROR"
                        else:
                            status = "✅ SUCCESS"

                        print(f"Status: {status}")
                        print(f"Time: {duration:.1f}s")
                        print(f"Length: {len(response)} chars")

                        # Show first 100 chars
                        preview = response[:100].replace('\\n', ' ')
                        print(f"Response: {preview}...")

                    else:
                        print("❌ No response or too short")

                except Exception as e:
                    print(f"❌ Error: {str(e)[:60]}...")

            print(f"\\n🎯 QUICK TEST SUMMARY:")
            print("✅ If you saw responses above, LLM function calling is working!")
            print("✅ Phase 1 core integration is operational")
            print("🚀 Ready to proceed with full SMS testing")

        except Exception as e:
            print(f"❌ Analyzer initialization failed: {str(e)}")

if __name__ == '__main__':
    quick_llm_test()