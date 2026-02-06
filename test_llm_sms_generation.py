#!/usr/bin/env python3
"""
Test LLM SMS generation to diagnose the 4 AM report issue
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_llm_sms_generation():
    """Test the LLM SMS generation directly"""

    try:
        from services.llm_service import SMSLLMService

        print("🧪 Testing LLM SMS Generation")
        print("=" * 50)

        # Initialize LLM service
        llm_service = SMSLLMService()

        # Test prompt similar to what daily reports use
        test_prompt = """You are composing a concise SMS (<= 306 chars total).
Goal: Rephrase the BASE SMS with clear wording, keep all facts, include 1–2 insights + 1 recommendation, and end with 'Open dashboard for details.'

RULES:
- Do not fabricate metrics or numbers.
- Keep total length <= 306 characters (hard cap).
- Keep tone neutral, professional, no emojis.

DATE: 2025-09-09
BASE SMS:
Daily Health Update - Sep 9
Sleep: 8.2h (Good)
HRV: 45ms (Normal)
Recovery: 78%
"""

        print(f"📝 Test Prompt:")
        print(f"   Length: {len(test_prompt)} characters")
        print(f"   First 100 chars: {test_prompt[:100]}...")

        # Test SMS generation
        print(f"\n🤖 Testing SMS Generation...")
        try:
            response = llm_service.generate_sms_response(test_prompt, max_length=306)

            if response:
                print(f"✅ Response received:")
                print(f"   Type: {type(response)}")
                print(f"   Has content attr: {hasattr(response, 'content')}")

                if hasattr(response, 'content'):
                    content = response.content
                    print(f"   Content length: {len(content)}")
                    print(f"   Content type: {type(content)}")
                    print(f"\n📱 Generated SMS:")
                    print("=" * 60)
                    print(content)
                    print("=" * 60)

                    # Check if it's the prompt being returned
                    if "You are composing a concise SMS" in content:
                        print("❌ ERROR: LLM returned the prompt instead of responding to it!")
                        return False
                    elif len(content) > 306:
                        print(f"⚠️ WARNING: SMS too long ({len(content)} chars)")
                    else:
                        print("✅ SMS generation looks correct!")
                        return True
                else:
                    print("❌ Response has no content attribute")
                    return False
            else:
                print("❌ No response received")
                return False

        except Exception as e:
            print(f"❌ LLM generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_generation():
    """Test fallback SMS generation"""

    try:
        from services.llm_service import SMSLLMService

        print(f"\n🔄 Testing Fallback SMS Generation...")

        llm_service = SMSLLMService()

        # Test fallback directly
        test_context = "Daily health metrics show good sleep (8.2h) and normal HRV (45ms)"

        fallback_response = llm_service._generate_fallback_sms(test_context, 306)

        if fallback_response:
            print(f"✅ Fallback response:")
            print(f"   Type: {type(fallback_response)}")
            if hasattr(fallback_response, 'content'):
                print(f"   Content: {fallback_response.content}")
            else:
                print(f"   Content: {fallback_response}")
        else:
            print("❌ Fallback failed")

        return True

    except Exception as e:
        print(f"❌ Fallback test failed: {str(e)}")
        return False

def check_llm_providers():
    """Check which LLM providers are available"""

    try:
        from services.llm_service import SMSLLMService

        print(f"\n🔍 Checking LLM Providers...")

        llm_service = SMSLLMService()

        print(f"   Available providers: {list(llm_service.providers.keys())}")
        print(f"   Provider errors: {llm_service.provider_errors}")

        # Check optimal provider selection
        optimal = llm_service._select_optimal_provider("sms_response")
        print(f"   Optimal provider for SMS: {optimal}")

        return True

    except Exception as e:
        print(f"❌ Provider check failed: {str(e)}")
        return False

if __name__ == '__main__':
    print(f"🧪 LLM SMS Generation Diagnostic")
    print(f"Identifying why 4 AM reports show prompt instead of response")

    # Run tests
    provider_ok = check_llm_providers()
    fallback_ok = test_fallback_generation()
    sms_ok = test_llm_sms_generation()

    print(f"\n📊 Test Results:")
    print(f"   Provider check: {'✅' if provider_ok else '❌'}")
    print(f"   Fallback SMS: {'✅' if fallback_ok else '❌'}")
    print(f"   Main SMS generation: {'✅' if sms_ok else '❌'}")

    if not sms_ok:
        print(f"\n🔧 Issue Identified:")
        print(f"   The LLM service is returning the prompt instead of generating a response")
        print(f"   This explains why your 4 AM reports contain prompt instructions")
        print(f"   Next: Fix the LLM API call or use fallback generation")
    else:
        print(f"\n✅ LLM generation working correctly!")
        print(f"   Issue may be in daily report generation logic")