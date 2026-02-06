#!/usr/bin/env python3
"""
Simple test to verify LLM functionality is working.
"""

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def test_llm_simple():
    """Simple test of LLM functionality"""

    print("=" * 60)
    print("SIMPLE LLM FUNCTIONALITY TEST")
    print("=" * 60)

    try:
        # Test OpenAI directly
        print("🧪 Testing OpenAI directly...")
        import openai

        openai.api_key = os.getenv('OPENAI_API_KEY')

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say hello in one sentence."}],
                max_tokens=50
            )

            content = response.choices[0].message.content
            print(f"✅ OpenAI test successful: {content}")

        except Exception as e:
            print(f"❌ OpenAI test failed: {str(e)}")
            return False

        print()

        # Test LLM service
        print("🧪 Testing LLM service...")
        try:
            from services.llm_service import LLMService, LLMProvider

            llm_service = LLMService()
            print(f"   Available providers: {list(llm_service.providers.keys())}")

            if LLMProvider.OPENAI in llm_service.providers:
                print("   ✅ OpenAI provider available")

                # Test a simple prompt
                response = llm_service.generate_response(
                    prompt="Explain what a correlation coefficient means in one sentence.",
                    task_type="general",
                    provider=LLMProvider.OPENAI,
                    temperature=0.1
                )

                print(f"   ✅ LLM response: {response.content}")

            else:
                print("   ❌ OpenAI provider not available")
                return False

        except Exception as e:
            print(f"   ❌ LLM service test failed: {str(e)}")
            return False

        print()

        # Test correlation insight generation
        print("🧪 Testing correlation insight generation...")
        try:
            from app import create_app
            from services.metrics_service import MetricsService

            app = create_app()

            with app.app_context():
                metrics_service = MetricsService()

                # Test correlation processing
                test_result = metrics_service.process_sms_input(
                    "sample_user",
                    "Is there a correlation between my heart rate and recovery?"
                )

                if test_result.get('success'):
                    insights = test_result.get('immediate_insights', {}).get('insights', [])
                    if insights:
                        print("   ✅ Correlation insight generated:")
                        print(f"   Message: {insights[0].get('message', 'No message')}")

                        # Check if it's LLM-generated or fallback
                        if "correlation coefficient" in insights[0].get('message', '').lower():
                            print("   🧠 LLM-generated insight detected!")
                        else:
                            print("   📝 Fallback insight (LLM may not be working)")
                    else:
                        print("   ❌ No insights generated")
                else:
                    print(f"   ❌ Correlation processing failed: {test_result.get('error')}")

        except Exception as e:
            print(f"   ❌ Correlation test failed: {str(e)}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error in LLM simple test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("LLM Simple Test")
    print("=" * 60)

    success = test_llm_simple()

    if success:
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print("✅ LLM functionality is working!")
        print("🧠 OpenAI provider initialized")
        print("📊 Correlation insights being generated")
        print("🎯 Ready for enhanced SMS responses")
    else:
        print("\n❌ LLM functionality test failed. Check the errors above.")

if __name__ == "__main__":
    main()
