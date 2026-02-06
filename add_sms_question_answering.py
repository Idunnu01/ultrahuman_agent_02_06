#!/usr/bin/env python3
"""
Add SMS question-answering capability to your health agent
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def create_sms_health_analyzer():
    """Create SMS-compatible health question analyzer"""

    sms_analyzer_code = '''"""
SMS Health Question Analyzer
Handles analytical questions via SMS with concise responses
"""

import numpy as np
from scipy.stats import pearsonr, ttest_ind
from datetime import datetime, timedelta
import re
from app.models import Metric, db

class SMSHealthAnalyzer:
    """Analyze health questions and provide SMS-friendly responses"""

    def __init__(self):
        self.max_sms_length = 306  # SMS character limit

    def analyze_question(self, question, user_id):
        """Analyze health question and return SMS-friendly response"""

        try:
            # Parse question
            lifestyle_factor, health_metric = self._parse_question(question)

            if not lifestyle_factor or not health_metric:
                return self._help_response()

            # Get data
            lifestyle_data = self._get_metric_data(user_id, lifestyle_factor, days=60)
            health_data = self._get_metric_data(user_id, health_metric, days=60)

            if not lifestyle_data or not health_data:
                return f"❌ Limited data for {lifestyle_factor.replace('_', ' ')} → {health_metric.replace('_', ' ')}. Need more readings for analysis."

            # Analyze relationship
            analysis = self._analyze_relationship(lifestyle_data, health_data)

            # Format SMS response
            return self._format_sms_response(lifestyle_factor, health_metric, analysis)

        except Exception as e:
            return f"❌ Analysis error. Try: 'Did meal timing affect heart rate?' or 'How does magnesium impact HRV?'"

    def _parse_question(self, question):
        """Parse SMS question to extract metrics"""

        question_lower = question.lower()

        # Lifestyle factor mappings
        lifestyle_mappings = {
            'meal timing': 'meal_timing',
            'meal': 'meal_timing',
            'dinner': 'meal_timing',
            'eating': 'meal_timing',
            'magnesium': 'magnesium_intake',
            'supplement': 'supplement_intake',
            'supplements': 'supplement_intake',
            'exercise': 'exercise_duration',
            'workout': 'exercise_duration',
            'activity': 'active_minutes',
            'steps': 'steps'
        }

        # Health metric mappings
        health_mappings = {
            'heart rate': 'heart_rate',
            'hr': 'heart_rate',
            'hrv': 'hrv',
            'heart rate variability': 'hrv',
            'sleep': 'sleep_score',
            'sleep score': 'sleep_score',
            'recovery': 'recovery',
            'temperature': 'temperature',
            'temp': 'temperature'
        }

        lifestyle_factor = None
        health_metric = None

        for term, metric in lifestyle_mappings.items():
            if term in question_lower:
                lifestyle_factor = metric
                break

        for term, metric in health_mappings.items():
            if term in question_lower:
                health_metric = metric
                break

        return lifestyle_factor, health_metric

    def _get_metric_data(self, user_id, metric_type, days=60):
        """Get metric data for analysis"""

        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            data = db.session.query(Metric.value, Metric.timestamp).filter(
                Metric.user_id == user_id,
                Metric.metric_type == metric_type,
                Metric.timestamp >= cutoff_date
            ).order_by(Metric.timestamp).all()

            return [(float(d[0]), d[1]) for d in data]

        except Exception:
            return []

    def _analyze_relationship(self, lifestyle_data, health_data):
        """Analyze relationship between lifestyle and health metrics"""

        # Method 1: Comparison analysis (most reliable for SMS)
        comparison_result = self._analyze_comparison(lifestyle_data, health_data)

        # Method 2: Correlation if enough data
        correlation_result = None
        if len(lifestyle_data) >= 5 and len(health_data) >= 10:
            correlation_result = self._analyze_correlation(lifestyle_data, health_data)

        return {
            'comparison': comparison_result,
            'correlation': correlation_result,
            'lifestyle_count': len(lifestyle_data),
            'health_count': len(health_data)
        }

    def _analyze_comparison(self, lifestyle_data, health_data):
        """Compare health metric on days with/without lifestyle factor"""

        try:
            # Get dates with lifestyle factor
            lifestyle_dates = set([d[1].date() for d in lifestyle_data])

            # Split health data
            with_lifestyle = []
            without_lifestyle = []

            for value, timestamp in health_data:
                if timestamp.date() in lifestyle_dates:
                    with_lifestyle.append(value)
                else:
                    without_lifestyle.append(value)

            if len(with_lifestyle) < 2 or len(without_lifestyle) < 2:
                return None

            with_mean = np.mean(with_lifestyle)
            without_mean = np.mean(without_lifestyle)
            difference = with_mean - without_mean
            percent_change = (difference / without_mean) * 100

            # Statistical test
            try:
                _, p_value = ttest_ind(with_lifestyle, without_lifestyle)
                significant = p_value < 0.05
            except:
                significant = False
                p_value = 1.0

            return {
                'with_mean': with_mean,
                'without_mean': without_mean,
                'difference': difference,
                'percent_change': percent_change,
                'significant': significant,
                'p_value': p_value,
                'with_count': len(with_lifestyle),
                'without_count': len(without_lifestyle)
            }

        except Exception:
            return None

    def _analyze_correlation(self, lifestyle_data, health_data):
        """Analyze correlation between metrics"""

        try:
            # Align by date
            lifestyle_dict = {}
            for value, timestamp in lifestyle_data:
                date_key = timestamp.date()
                lifestyle_dict[date_key] = lifestyle_dict.get(date_key, []) + [value]

            health_dict = {}
            for value, timestamp in health_data:
                date_key = timestamp.date()
                health_dict[date_key] = health_dict.get(date_key, []) + [value]

            common_dates = set(lifestyle_dict.keys()) & set(health_dict.keys())

            if len(common_dates) < 5:
                return None

            lifestyle_values = []
            health_values = []

            for date in common_dates:
                lifestyle_values.append(np.mean(lifestyle_dict[date]))
                health_values.append(np.mean(health_dict[date]))

            correlation, p_value = pearsonr(lifestyle_values, health_values)

            return {
                'correlation': correlation,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'sample_size': len(common_dates)
            }

        except Exception:
            return None

    def _format_sms_response(self, lifestyle_factor, health_metric, analysis):
        """Format analysis into SMS-friendly response"""

        lifestyle_name = lifestyle_factor.replace('_', ' ').title()
        health_name = health_metric.replace('_', ' ').title()

        response_parts = []

        # Header
        response_parts.append(f"🔍 {lifestyle_name} → {health_name}")

        # Data summary
        response_parts.append(f"📊 {analysis['lifestyle_count']} + {analysis['health_count']} readings")

        # Primary analysis
        comparison = analysis.get('comparison')
        correlation = analysis.get('correlation')

        if comparison:
            diff = comparison['difference']
            pct = comparison['percent_change']
            sig = comparison['significant']

            direction = "↗️" if diff > 0 else "↘️"
            effect = f"{direction} {abs(pct):.1f}% change"

            if sig:
                response_parts.append(f"✅ {effect} (significant)")
            else:
                response_parts.append(f"⚠️ {effect} (not significant)")

            # Specific values
            response_parts.append(f"With: {comparison['with_mean']:.1f}")
            response_parts.append(f"Without: {comparison['without_mean']:.1f}")

        elif correlation:
            corr = correlation['correlation']
            sig = correlation['significant']
            strength = self._get_correlation_strength(abs(corr))

            direction = "+" if corr > 0 else "-"

            if sig:
                response_parts.append(f"✅ {strength} correlation: {direction}{abs(corr):.2f}")
            else:
                response_parts.append(f"⚠️ Weak correlation: {direction}{abs(corr):.2f}")

        else:
            response_parts.append("⚠️ Insufficient overlapping data")

        # Insight
        if comparison and comparison['significant']:
            if abs(comparison['percent_change']) > 5:
                if comparison['difference'] > 0:
                    response_parts.append(f"💡 {lifestyle_name} may IMPROVE {health_name}")
                else:
                    response_parts.append(f"💡 {lifestyle_name} may REDUCE {health_name}")

        # Join and truncate to SMS limit
        full_response = "\\n".join(response_parts)

        if len(full_response) > self.max_sms_length:
            # Truncate to fit SMS
            truncated = full_response[:self.max_sms_length-3] + "..."
            return truncated

        return full_response

    def _get_correlation_strength(self, r):
        """Get correlation strength description"""
        if r >= 0.7:
            return "Very Strong"
        elif r >= 0.5:
            return "Strong"
        elif r >= 0.3:
            return "Moderate"
        else:
            return "Weak"

    def _help_response(self):
        """Help response for unclear questions"""
        return """❓ Try questions like:
• Did meal timing affect heart rate?
• How does magnesium impact HRV?
• Does exercise correlate with recovery?
• Did supplements affect sleep score?"""

    def is_question_format(self, message):
        """Check if message is a health question"""

        question_indicators = [
            'did', 'does', 'how does', 'what', 'why', 'when',
            'affect', 'impact', 'correlate', 'influence', 'change'
        ]

        lifestyle_terms = [
            'meal', 'magnesium', 'supplement', 'exercise', 'activity', 'steps'
        ]

        health_terms = [
            'heart rate', 'hrv', 'sleep', 'recovery', 'temperature'
        ]

        message_lower = message.lower()

        has_question_word = any(indicator in message_lower for indicator in question_indicators)
        has_lifestyle = any(term in message_lower for term in lifestyle_terms)
        has_health = any(term in message_lower for term in health_terms)

        return has_question_word and (has_lifestyle or has_health)
'''

    # Write the SMS health analyzer
    with open('services/sms_health_analyzer.py', 'w') as f:
        f.write(sms_analyzer_code)

    print("✅ Created services/sms_health_analyzer.py")

def integrate_with_sms_webhook():
    """Integration code for SMS webhook"""

    print("🔧 Integration with SMS Webhook")
    print("=" * 35)

    integration_code = '''
# Add this to your SMS webhook handler in app/routes.py

from services.sms_health_analyzer import SMSHealthAnalyzer

def handle_sms_webhook():
    """Enhanced SMS webhook with question-answering"""

    # ... your existing webhook code ...

    body = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')

    # Get user
    user = User.query.filter_by(phone_number=from_number).first()
    if not user:
        return "User not found", 400

    # Initialize health analyzer
    health_analyzer = SMSHealthAnalyzer()

    # Check if this is a health question
    if health_analyzer.is_question_format(body):

        try:
            # Analyze the question
            response = health_analyzer.analyze_question(body, user.id)

            # Send SMS response
            sms_service = SMSService()
            sms_service.send_sms(user.phone_number, response)

            # Log the interaction
            logger.info(f"Health question answered for user {user.id}: {body[:50]}...")

            return "Question analyzed and response sent", 200

        except Exception as e:
            logger.error(f"Health question analysis failed: {str(e)}")

            # Send error response
            error_msg = "❌ Analysis failed. Try simpler questions like 'Did meal timing affect heart rate?'"
            sms_service = SMSService()
            sms_service.send_sms(user.phone_number, error_msg)

            return "Error response sent", 200

    # If not a question, handle with existing conversation logic
    else:
        # ... your existing conversation handling ...
        pass
'''

    print("Copy this code to integrate with your SMS webhook:")
    print(integration_code)

def create_test_script():
    """Create test script for SMS question answering"""

    test_code = '''#!/usr/bin/env python3
"""
Test SMS health question answering
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_sms_questions():
    """Test SMS question answering with your data"""

    print("🧪 Testing SMS Health Question Answering")
    print("=" * 50)

    from app import create_app
    from services.sms_health_analyzer import SMSHealthAnalyzer

    app = create_app()

    with app.app_context():
        analyzer = SMSHealthAnalyzer()

        test_questions = [
            "Did my meal timing affect my heart rate?",
            "How does magnesium impact my HRV?",
            "Does exercise correlate with recovery?",
            "Did supplements affect sleep score?",
            "What about temperature and heart rate?"
        ]

        user_id = 'user_7000'  # Your user ID

        for question in test_questions:
            print(f"\\n❓ Question: {question}")
            print("=" * 60)

            response = analyzer.analyze_question(question, user_id)

            print(f"📱 SMS Response ({len(response)} chars):")
            print("─" * 40)
            print(response)
            print("─" * 40)

            print(f"✅ Fits SMS limit: {'Yes' if len(response) <= 306 else 'No'}")

if __name__ == '__main__':
    test_sms_questions()
'''

    with open('test_sms_questions.py', 'w') as f:
        f.write(test_code)

    print("✅ Created test_sms_questions.py")

def main():
    print("🚀 Adding SMS Question-Answering to Your Health Agent")
    print("=" * 60)

    # Create the SMS health analyzer
    create_sms_health_analyzer()

    # Show integration instructions
    integrate_with_sms_webhook()

    # Create test script
    create_test_script()

    print("\\n🎯 What You Can Now Do:")
    print("✅ Text questions to your agent")
    print("✅ Get statistical analysis via SMS")
    print("✅ Ask about correlations in your 175K+ metrics")
    print("✅ Receive insights within SMS character limits")

    print("\\n📱 Example SMS Interactions:")
    print("You: 'Did meal timing affect heart rate?'")
    print("Agent: '🔍 Meal Timing → Heart Rate\\n📊 7 + 47,893 readings\\n✅ ↗️ 3.6% change (significant)\\nWith: 89.2\\nWithout: 86.1\\n💡 Meal Timing may IMPROVE Heart Rate'")

    print("\\n🔧 Next Steps:")
    print("1. Copy services/sms_health_analyzer.py to production")
    print("2. Integrate the webhook code with your SMS handler")
    print("3. Test with: python test_sms_questions.py")
    print("4. Start texting analytical questions to your agent!")

    print("\\n🎉 Your agent can now answer health questions via SMS!")

if __name__ == '__main__':
    main()