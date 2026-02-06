
To use the PythonAnywhere-optimized LLM analyzer:

1. In your app/routes.py, change the import:
   FROM: from services.llm_chat_analyzer import LLMChatAnalyzer
   TO:   from services.llm_chat_analyzer_pa import LLMChatAnalyzer

2. Or create a hybrid approach in routes.py:

   try:
       from services.llm_chat_analyzer import LLMChatAnalyzer
       llm_analyzer = LLMChatAnalyzer()
       response = llm_analyzer.analyze_message(body, user.id)

       if "Connection error" in response:
           raise Exception("LLM failed")

   except Exception:
       # Fallback to enhanced analyzer
       from services.sms_health_analyzer import SMSHealthAnalyzer
       health_analyzer = SMSHealthAnalyzer()
       response = health_analyzer.analyze_question(body, user.id)

This ensures your SMS system always works, even if LLM has issues!
