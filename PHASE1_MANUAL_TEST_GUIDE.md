
📱 PHASE 1 MANUAL SMS TESTING GUIDE
==================================

After running the automated tests, test your live SMS system:

🔧 SETUP STEPS:
1. Deploy your code to PythonAnywhere
2. Set your Twilio webhook to: https://yourdomain.pythonanywhere.com/webhook/sms
3. Make sure your .env file is uploaded with the correct OpenAI API key

📲 SMS TEST QUESTIONS TO TRY:
Send these messages to your Twilio number:

CONVERSATIONAL TESTS:
• "Hello"
• "Hi, how are you?"
• "What can you help me with?"

HEALTH DATA TESTS:
• "What was my heart rate at 3am last night?"
• "How did I sleep last night?"
• "Show me my HRV trends"
• "What time did I fall asleep yesterday?"
• "How was my activity today?"
• "Compare my weekend sleep to weekdays"

TIME-SPECIFIC TESTS:
• "What was my heart rate at 2pm today?"
• "How was my sleep quality overnight?"
• "Show me my morning activity patterns"

✅ EXPECTED BEHAVIOR:
• Quick responses (under 30 seconds)
• Natural language, ChatGPT-like answers
• Specific health data when available
• Friendly conversational tone
• Fallback to enhanced analyzer if LLM fails

❌ TROUBLESHOOTING:
If you get generic responses or errors:
1. Check PythonAnywhere error logs
2. Verify OpenAI API key is working
3. Ensure database has recent health data
4. The enhanced analyzer will provide fallback responses

🎯 SUCCESS INDICATORS:
• Responses mention specific times, dates, or values
• Natural language explanations of health data
• Personalized insights based on your data
• Conversational, helpful tone
