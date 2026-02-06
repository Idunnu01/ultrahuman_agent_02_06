#!/usr/bin/env python3
"""
Isolated test for LLM service to debug initialization issues.
"""

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def test_llm_isolated():
    """Test LLM service in isolation"""

    print("=" * 60)
    print("ISOLATED LLM SERVICE TEST")
    print("=" * 60)

    try:
        # Test imports
        print("🧪 Testing imports...")
        try:
            import openai
            print(f"   ✅ OpenAI version: {openai.__version__}")
        except ImportError as e:
            print(f"   ❌ OpenAI import failed: {e}")
            return False

        try:
            import anthropic
            print(f"   ✅ Anthropic imported")
        except ImportError as e:
            print(f"   ❌ Anthropic import failed: {e}")

        try:
            import together
            print(f"   ✅ Together imported")
        except ImportError as e:
            print(f"   ❌ Together import failed: {e}")

        print()

        # Test OpenAI client creation
        print("🧪 Testing OpenAI client creation...")
        try:
            openai_client = openai.OpenAI(
                api_key=os.getenv('OPENAI_API_KEY')
            )
            print("   ✅ OpenAI client created successfully")
        except Exception as e:
            print(f"   ❌ OpenAI client creation failed: {str(e)}")
            return False

        print()

        # Test LLM service initialization
        print("🧪 Testing LLM service initialization...")
        try:
            from services.llm_service import LLMService, LLMProvider

            llm_service = LLMService()
            print(f"   ✅ LLM service initialized")
            print(f"   Available providers: {list(llm_service.providers.keys())}")

            if LLMProvider.OPENAI in llm_service.providers:
                print("   ✅ OpenAI provider available")

                # Test a simple API call
                print("   🧪 Testing OpenAI API call...")
                try:
                    response = llm_service.generate_response(
                        prompt="Say hello in one sentence.",
                        task_type="general",
                        provider=LLMProvider.OPENAI,
                        temperature=0.1
                    )

                    print(f"   ✅ API call successful: {response.content}")
                    return True

                except Exception as e:
                    print(f"   ❌ API call failed: {str(e)}")
                    return False
            else:
                print("   ❌ OpenAI provider not available")
                return False

        except Exception as e:
            print(f"   ❌ LLM service initialization failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Error in isolated test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("LLM Isolated Test")
    print("=" * 60)

    success = test_llm_isolated()

    if success:
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print("✅ LLM service is working correctly!")
        print("🧠 OpenAI provider initialized and responding")
        print("🎯 Ready for enhanced SMS responses")
    else:
        print("\n❌ LLM service test failed. Check the errors above.")

if __name__ == "__main__":
    main()
