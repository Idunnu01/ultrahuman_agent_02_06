#!/usr/bin/env python3
"""
Fix .env file OpenAI key - Remove embedded newlines
"""

import os
import re

def fix_env_file():
    """Fix the OpenAI key in the .env file"""

    print("🔧 FIXING .ENV FILE")
    print("=" * 40)

    env_path = ".env"

    # Read the current file
    with open(env_path, 'r') as f:
        content = f.read()

    print("📝 Current .env file read")

    # Find the OpenAI key line(s)
    openai_key_match = re.search(r'OPENAI_API_KEY=([^\n]*(?:\n[^\n=]*)*)', content)

    if openai_key_match:
        full_match = openai_key_match.group(0)
        key_value = openai_key_match.group(1)

        print(f"🔍 Found OpenAI key entry:")
        print(f"   Full match: {repr(full_match)}")
        print(f"   Key value: {repr(key_value)}")

        # Clean the key value - remove all whitespace and newlines
        cleaned_key = re.sub(r'\s+', '', key_value)

        print(f"🧹 Cleaned key: {cleaned_key[:20]}...{cleaned_key[-20:]}")
        print(f"   Length: {len(cleaned_key)} characters")

        # Create the new line
        new_line = f"OPENAI_API_KEY={cleaned_key}"

        # Replace in content
        new_content = content.replace(full_match, new_line)

        # Write back to file
        with open(env_path, 'w') as f:
            f.write(new_content)

        print("✅ .env file updated")

        # Test the fixed key
        print("\n🧪 Testing fixed key...")

        # Reload environment
        from dotenv import load_dotenv
        load_dotenv(override=True)  # Override to reload

        test_key = os.getenv('OPENAI_API_KEY')
        print(f"📋 Loaded key: {test_key[:20]}...{test_key[-20:]}")
        print(f"   Length: {len(test_key)}")
        print(f"   Has newlines: {'\\n' in repr(test_key)}")

        # Test with OpenAI
        try:
            from openai import OpenAI

            client = OpenAI(api_key=test_key)

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Say 'Fixed!' if this works"}
                ],
                max_tokens=5,
                timeout=30
            )

            result = response.choices[0].message.content
            print(f"🎉 SUCCESS! OpenAI response: {result}")

            return True

        except Exception as e:
            print(f"❌ Still not working: {str(e)}")

            # If still failing, maybe the key itself is wrong
            if "api key" in str(e).lower() or "authentication" in str(e).lower():
                print("💡 The API key might be invalid. Check your OpenAI dashboard.")

            return False

    else:
        print("❌ Could not find OPENAI_API_KEY in .env file")
        return False

if __name__ == '__main__':
    success = fix_env_file()

    if success:
        print("\n✅ .env file fixed! OpenAI integration should work now.")
        print("🚀 You can now run your LLM tests successfully.")
    else:
        print("\n⚠️ Issue persists. You may need to get a fresh API key from OpenAI.")
        print("   Visit: https://platform.openai.com/api-keys")