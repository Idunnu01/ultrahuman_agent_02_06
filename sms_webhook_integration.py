#!/usr/bin/env python3
"""
SMS Webhook Integration Code
Copy this into your app/routes.py SMS webhook handler
"""

from services.sms_health_analyzer import SMSHealthAnalyzer
from services.sms_service import SMSService
import logging

def handle_sms_webhook():
    """Enhanced SMS webhook with question-answering for both correlation and trend analysis"""

    try:
        # Get SMS data
        body = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')

        if not body:
            return "Empty message", 400

        # Get user
        user = User.query.filter_by(phone_number=from_number).first()
        if not user:
            # Send error SMS
            sms_service = SMSService()
            sms_service.send_sms(from_number, "❌ User not found. Please register first.")
            return "User not found", 400

        # Initialize health analyzer
        health_analyzer = SMSHealthAnalyzer()

        # Check if this is a health question (both correlation and trend)
        if health_analyzer.is_question_format(body):

            try:
                logging.info(f"Processing health question from user {user.id}: {body[:50]}...")

                # Analyze the question (handles both types automatically)
                response = health_analyzer.analyze_question(body, user.id)

                if not response:
                    response = "❌ Unable to analyze your question. Try: 'What's my heart rate trend?' or 'Did meal timing affect heart rate?'"

                # SMS has character limits, so we may need to truncate for very long responses
                if len(response) > 1600:  # SMS limit
                    # For very long responses, send a summary
                    lines = response.split('\n')
                    summary_lines = []

                    # Include header and key insights
                    for line in lines[:15]:  # First 15 lines usually contain the key info
                        summary_lines.append(line)

                    summary_lines.append("...")
                    summary_lines.append("📱 Full analysis available in app")

                    response = '\n'.join(summary_lines)

                # Send SMS response
                sms_service = SMSService()
                sms_service.send_sms(user.phone_number, response)

                # Log the interaction
                logging.info(f"Health question answered for user {user.id}: {len(response)} chars sent")

                return "Question analyzed and response sent", 200

            except Exception as e:
                logging.error(f"Health question analysis failed: {str(e)}")

                # Send error response
                error_msg = """❌ Analysis failed. Try questions like:
• 'What's my heart rate trend?'
• 'How is my sleep improving?'
• 'Did meal timing affect heart rate?'
• 'Does exercise correlate with recovery?'"""

                sms_service = SMSService()
                sms_service.send_sms(user.phone_number, error_msg)

                return "Error response sent", 200

        # If not a health question, handle with existing conversation logic
        else:
            # Your existing SMS conversation handling code goes here
            # For example:
            # return handle_regular_sms_conversation(body, user)

            # Placeholder response
            response = "Thanks for your message! For health questions, try: 'What's my heart rate trend?' or 'Did meal timing affect heart rate?'"

            sms_service = SMSService()
            sms_service.send_sms(user.phone_number, response)

            return "Regular message handled", 200

    except Exception as e:
        logging.error(f"SMS webhook error: {str(e)}")
        return "Internal error", 500


def update_question_format_detection():
    """
    Enhanced question format detection to include trend analysis
    This updates the is_question_format method to handle more patterns
    """

    # The SMSHealthAnalyzer.is_question_format() method now handles:

    # Correlation Analysis Questions:
    question_indicators = [
        'did', 'does', 'how does', 'what', 'why', 'when',
        'affect', 'impact', 'correlate', 'influence', 'change'
    ]

    # Trend Analysis Questions (NEW):
    trend_indicators = [
        'trend', 'trending', 'average', 'over time', 'weekly', 'monthly',
        'improving', 'getting better', 'getting worse', 'how is my',
        'what\'s my', 'show me my'
    ]

    # Health metrics that work with both types:
    health_terms = [
        'heart rate', 'hrv', 'sleep', 'recovery', 'temperature',
        'steps', 'activity', 'exercise'
    ]

    # Lifestyle factors (for correlation only):
    lifestyle_terms = [
        'meal', 'magnesium', 'supplement', 'exercise', 'activity', 'steps'
    ]


# Example SMS conversations that now work:

examples = [
    # Trend Analysis Examples:
    {
        "sms": "What's my heart rate trend?",
        "response": """📈 Trend Analysis: heart_rate
📊 Data availability:
   heart_rate: 9573 readings
🧪 Trend Analysis:
=========================
💡 Key Insights:
===============
📊 Overall Statistics:
   Total readings: 9573
   Average heart rate: 89.45
   Range: 45.0 - 140.0
   Standard deviation: 12.8
📈 30-Day Comparison:
   Recent 30 days: 87.2
   Previous 30 days: 91.6
   Change: -4.4 (-4.8%)
   💡 Heart Rate is IMPROVING over time
📈 Overall Trend: Downward trend detected
📅 Weekly Analysis:
   First week: 94.2
   Latest week: 86.8
   Week-to-week change: -7.4
   Tracking over 12 weeks
⏱️ Analysis Period: 2025-06-11 to 2025-09-09"""
    },

    # Correlation Analysis Examples:
    {
        "sms": "Did meal timing affect heart rate?",
        "response": """🔍 Analyzing: meal_timing → heart_rate
📊 Data availability:
   meal_timing: 7 readings
   heart_rate: 9573 readings
🧪 Statistical Analysis:
=========================
💡 Key Insights:
===============
📈 Comparison Analysis:
   With meal timing: 85.96
   Without meal timing: 90.19
   Difference: -4.22 (-4.7%)
   Statistical significance: ✅ Yes
   💡 Meal Timing appears to REDUCE heart rate
⏱️ Temporal Analysis:
   Found 4 instances to analyze
   Average heart rate after meal timing: 85.38"""
    }
]