#!/usr/bin/env python3
"""
Fix for natural conversational responses - handles greetings and thanks properly
"""

import re

def add_conversational_handling_to_metrics_service():
    """Add conversational message detection to MetricsService"""

    # This is the code that needs to be added to services/metrics_service.py
    conversational_code = '''
    def _is_conversational_message(self, text: str) -> tuple[bool, str]:
        """Detect conversational messages and return appropriate response"""
        text_lower = text.lower().strip()

        # Greeting patterns
        greeting_patterns = [
            r'^(hi|hello|hey|good morning|good afternoon|good evening)!?$',
            r'^(hi|hello|hey) there!?$',
            r'^how are you\??$'
        ]

        for pattern in greeting_patterns:
            if re.match(pattern, text_lower):
                return True, self._get_greeting_response()

        # Thank you patterns
        thanks_patterns = [
            r'^(thank you|thanks|thx)!?$',
            r'^(thank you|thanks) so much!?$',
            r'^(appreciate it|thanks a lot)!?$',
            r'^ok thank you$',
            r'^got it,? thanks?$'
        ]

        for pattern in thanks_patterns:
            if re.match(pattern, text_lower):
                return True, self._get_thanks_response()

        # Goodbye patterns
        goodbye_patterns = [
            r'^(bye|goodbye|see you|talk later)!?$',
            r'^have a good (day|night|evening)!?$'
        ]

        for pattern in goodbye_patterns:
            if re.match(pattern, text_lower):
                return True, self._get_goodbye_response()

        return False, ""

    def _get_greeting_response(self) -> str:
        """Generate appropriate greeting response"""
        responses = [
            "Hello! I'm Ava, your health coach. How can I help you today?",
            "Hi there! Ready to explore your health data? Ask me anything!",
            "Hello! I can help you track metrics, find correlations, or answer health questions. What would you like to know?"
        ]
        import random
        return random.choice(responses)

    def _get_thanks_response(self) -> str:
        """Generate appropriate thank you response"""
        responses = [
            "You're welcome! Happy to help anytime. 😊",
            "My pleasure! Feel free to ask if you need anything else.",
            "Glad I could help! I'm here whenever you need health insights.",
            "You're very welcome! Keep up the great work with your health tracking! 💪"
        ]
        import random
        return random.choice(responses)

    def _get_goodbye_response(self) -> str:
        """Generate appropriate goodbye response"""
        responses = [
            "Goodbye! Take care and keep tracking your health! 🌟",
            "See you later! Remember to stay hydrated and get good sleep!",
            "Have a great day! I'll be here when you need me. 👋"
        ]
        import random
        return random.choice(responses)
    '''

    return conversational_code

def show_integration_instructions():
    """Show how to integrate the conversational handling"""

    print("🔧 CONVERSATIONAL RESPONSE FIX")
    print("=" * 50)
    print()
    print("To fix the conversational responses, you need to:")
    print()
    print("1. Add the conversational detection methods to MetricsService")
    print("2. Modify process_sms_input to check for conversational messages FIRST")
    print()
    print("Here's what needs to be added to services/metrics_service.py:")
    print()
    print(add_conversational_handling_to_metrics_service())
    print()
    print("3. Then modify the process_sms_input method to add this check:")
    print()
    integration_code = '''
    def process_sms_input(self, user_id: str, message: str) -> Dict:
        """Process SMS input and return appropriate response"""
        try:
            text = (message or "").strip()
            if not text:
                return {"success": False, "error": "Empty message"}

            # NEW: Check for conversational messages FIRST
            is_conversational, response = self._is_conversational_message(text)
            if is_conversational:
                return {
                    "success": True,
                    "conversational_response": True,
                    "immediate_insights": {
                        "insights": [{
                            "type": "conversational",
                            "message": response
                        }]
                    }
                }

            msg_lc = text.lower()

            # Continue with existing logic...
            # (rest of the existing method remains unchanged)
    '''
    print(integration_code)
    print()
    print("🎯 BENEFITS:")
    print("- Natural greeting responses")
    print("- Appropriate thank you acknowledgments")
    print("- Context-aware conversation flow")
    print("- No more generic health tips for simple greetings")
    print()
    print("📝 EXAMPLE RESPONSES:")
    print("User: 'Hello' → 'Hi there! I'm Ava, your health coach. How can I help you today?'")
    print("User: 'Thank you' → 'You're welcome! Happy to help anytime. 😊'")
    print("User: 'Bye' → 'Goodbye! Take care and keep tracking your health! 🌟'")

if __name__ == "__main__":
    show_integration_instructions()