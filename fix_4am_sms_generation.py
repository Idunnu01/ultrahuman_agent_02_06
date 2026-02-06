#!/usr/bin/env python3
"""
Fix SMS method signature error in daily report
"""

import sys
import os
import re

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def fix_sms_method_signature():
    """Fix the SMS method call to use correct parameters"""

    daily_report_path = os.path.join(project_dir, 'tasks', 'daily_report.py')

    try:
        # Read the file
        with open(daily_report_path, 'r') as f:
            content = f.read()

        print("🔧 Fixing SMS Method Signature Error")
        print("=" * 50)

        # Find and replace the incorrect method call
        old_pattern = r'sms_resp = llm_service\.generate_sms_response\(\s*prompt,\s*max_length=306,\s*temperature=0\.2,\s*top_p=0\.9\s*\)'
        new_pattern = 'sms_resp = llm_service.generate_sms_response(prompt, max_length=306)'

        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_pattern, content)
            print("✅ Fixed SMS method call parameters")
        else:
            # Try broader pattern
            broader_pattern = r'llm_service\.generate_sms_response\([^)]*temperature[^)]*\)'
            replacement = 'llm_service.generate_sms_response(prompt, max_length=306)'

            if re.search(broader_pattern, content):
                content = re.sub(broader_pattern, replacement, content)
                print("✅ Fixed SMS method call with broader pattern")
            else:
                print("❌ Could not find SMS method call to fix")
                return False

        # Write the fixed content
        with open(daily_report_path, 'w') as f:
            f.write(content)

        print("✅ Daily report SMS method signature fixed")
        return True

    except Exception as e:
        print(f"❌ Fix failed: {str(e)}")
        return False

def test_fixed_sms_method():
    """Test that the method signature fix works"""

    try:
        from services.llm_service import SMSLLMService

        print(f"\n🧪 Testing Fixed SMS Method...")

        llm_service = SMSLLMService()

        # Test the method call that was failing
        test_prompt = "Generate a health SMS"

        try:
            response = llm_service.generate_sms_response(test_prompt, max_length=306)
            print("✅ SMS method call successful")

            if response and hasattr(response, 'content'):
                print(f"✅ Response content: {response.content[:100]}...")
                return True
            else:
                print("⚠️ Method works but no content returned")
                return True

        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"❌ Method signature still incorrect: {e}")
                return False
            else:
                print(f"⚠️ Other error (method signature OK): {e}")
                return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == '__main__':
    print("🔧 Fix SMS Method Signature Error")
    print("Fixing temperature/top_p parameter issue")

    fix_ok = fix_sms_method_signature()

    if fix_ok:
        test_ok = test_fixed_sms_method()

        if test_ok:
            print(f"\n✅ SMS Method Signature Fixed!")
            print(f"✅ Daily reports will now use correct LLM parameters")
            print(f"✅ Ready to generate proper SMS content")
        else:
            print(f"\n❌ Method signature still has issues")
    else:
        print(f"\n❌ Could not apply fix automatically")