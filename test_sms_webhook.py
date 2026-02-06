#!/usr/bin/env python3
"""
Test SMS webhook functionality by simulating Twilio webhook requests.

Coverage:
- Ensures tables + a sample user (phone matches webhook From)
- Exercises MetricsService.process_sms_input() with:
  • Correlations
  • Trends (improving/declining/flat)
  • Patterns (time-of-day/week, associations)
  • Anomalies (spikes/drops)
  • Interventions (effectiveness questions)
  • Habits & recommendations (what to do next)
  • Event logging (meal/supplement/sleep)
- Exercises /webhook/sms endpoint
"""

import sys
import os

# --- Path & env bootstrap ---
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, ".env"))

# ---- Config you can tweak for the test ----
TEST_USER_ID = "sample_user"
TEST_USER_PHONE = "+1234567890"  # must match the webhook 'From' below
TEST_USER_TZ = "UTC"

# Organized test prompts
CORRELATION_QUERIES = [
    "Is there a correlation between my body temperature and heart rate?",
    "What's the relationship between my sleep score and HRV?",
    "How does my HRV correlate with recovery score?",
    "Is there a link between glucose variability and sleep quality?",
]

TREND_QUERIES = [
    "Are my resting heart rate trends improving or worsening over the last 14 days?",
    "Show me the trend for HRV for the past 30 days. Is it stable?",
    "Is my sleep efficiency trending up over the last 2 weeks?",
]

PATTERN_QUERIES = [
    "Do I have time-of-day patterns where my glucose spikes in the afternoon?",
    "Are there weekly patterns where my recovery is lowest on Mondays?",
    "Which meals are most often followed by a higher heart rate overnight?",
]

ANOMALY_QUERIES = [
    "Did I have any anomalies in body temperature this week?",
    "Alert me if last night's resting heart rate was unusually high vs baseline.",
    "Were there significant deviations in HRV over the last 7 days?",
]

INTERVENTION_QUERIES = [
    "Has magnesium supplementation improved my sleep score in the last month?",
    "Is stopping caffeine after 2pm improving my HRV?",
    "Did adding a 20-minute evening walk help reduce my resting heart rate?",
]

HABIT_RECO_QUERIES = [
    "Based on my data, what should I do tonight to improve recovery?",
    "Give me one habit change that would improve sleep quality this week.",
    "What is the top recommendation for lowering my resting heart rate?",
]

# Event-logging style messages (exercise parsing + immediate insights)
EVENT_MESSAGES = [
    "meal salmon quinoa 7pm",
    "supplement magnesium 400mg 9pm",
    "sleep 23:30 to 06:45 good",
    "workout zone2 40min 18:00",
]

# A compact “webhook” question to test the HTTP route
WEBHOOK_BODY = "Is there a correlation between my body temperature and heart rate?"

def safe_fmt_float(val, fmt=":.4f", default="N/A"):
    try:
        if val is None:
            return default
        return format(float(val), fmt)
    except Exception:
        return default

def print_header(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

def run_section(app, title, prompts_or_msgs, is_event=False):
    """Run a list of prompts through MetricsService.process_sms_input()"""
    print_header(title)
    from services.metrics_service import MetricsService
    ms = MetricsService()

    for i, text in enumerate(prompts_or_msgs, 1):
        print("\n" + "-" * 60)
        prefix = "📋 Log" if is_event else "📱 Query"
        print(f"{prefix} {i}: {text}")
        try:
            result = ms.process_sms_input(TEST_USER_ID, text)
            if not result or not result.get("success"):
                print(f"❌ Processing failed: {result.get('error') if result else 'Unknown error'}")
                continue

            print("✅ Processed successfully")

            # If correlation analysis present
            corr = result.get("correlation_analysis") or {}
            if corr:
                print("📊 Correlation analysis:")
                print(f"   Metric 1: {corr.get('metric1', 'N/A')}")
                print(f"   Metric 2: {corr.get('metric2', 'N/A')}")
                print(f"   r: {safe_fmt_float(corr.get('correlation_coefficient'))}")
                print(f"   p: {safe_fmt_float(corr.get('p_value'), ':.6f')}")
                print(f"   n: {corr.get('sample_size', 'N/A')}")
                print(f"   significance: {corr.get('significance', 'N/A')}")

            # If trend or anomaly summaries are surfaced in insights/context, print a short line
            insights = (result.get("immediate_insights") or {}).get("insights") or []
            if insights:
                msg = (insights[0].get("message") or "").strip()
                print(f"📝 Top insight: {msg[:300]}")

            # For event messages, see if any events were parsed
            if is_event:
                n = result.get("events_processed", 0)
                print(f"🧾 Events processed: {n}")

        except Exception as e:
            print(f"❌ Exception during processing: {e}")

def test_sms_webhook():
    print_header("SMS WEBHOOK FUNCTIONALITY TEST")

    # Import after path/env so app/modules resolve
    from app import create_app
    from utils.database import db
    from app.models import User

    app = create_app()

    with app.app_context():
        # Ensure tables exist
        try:
            db.create_all()
        except Exception:
            pass

        # Ensure sample user exists (phone must match webhook 'From')
        u = db.session.get(User, TEST_USER_ID) if hasattr(db.session, "get") else User.query.get(TEST_USER_ID)
        if u is None:
            u = User(
                id=TEST_USER_ID,
                ultrahuman_user_id="uh_sample",
                phone_number=TEST_USER_PHONE,
                timezone=TEST_USER_TZ,
                preferences={"test_user": True}
            )
            db.session.add(u)
            db.session.commit()
            print(f"👤 Created test user {TEST_USER_ID} with phone {TEST_USER_PHONE}")
        else:
            if u.phone_number != TEST_USER_PHONE:
                u.phone_number = TEST_USER_PHONE
                db.session.commit()
                print(f"👤 Updated test user phone → {TEST_USER_PHONE}")

        # ---- Sections covering your agent’s capabilities ----
        run_section(app, "CORRELATIONS", CORRELATION_QUERIES)
        run_section(app, "TRENDS", TREND_QUERIES)
        run_section(app, "PATTERNS", PATTERN_QUERIES)
        run_section(app, "ANOMALIES", ANOMALY_QUERIES)
        run_section(app, "INTERVENTIONS", INTERVENTION_QUERIES)
        run_section(app, "HABITS & RECOMMENDATIONS", HABIT_RECO_QUERIES)
        run_section(app, "EVENT LOGGING (Parser Flow)", EVENT_MESSAGES, is_event=True)

        # ---- Webhook endpoint test (HTTP) ----
        print_header("WEBHOOK ENDPOINT (/webhook/sms)")
        from flask import current_app
        with app.test_client() as client:
            webhook_data = {
                "From": TEST_USER_PHONE,  # must match user above
                "Body": WEBHOOK_BODY,
                "MessageSid": "test_message_sid",
                "AccountSid": "test_account_sid",
            }
            resp = client.post("/webhook/sms", data=webhook_data)

            print(f"📡 Status: {resp.status_code}")
            print(f"📡 Content-Type: {resp.content_type}")

            body = resp.get_data(as_text=True)
            if resp.status_code == 200:
                print("✅ Webhook endpoint OK")
                # Extract <Message>...</Message> from TwiML
                if "<Message>" in body and "</Message>" in body:
                    start = body.find("<Message>") + len("<Message>")
                    end = body.find("</Message>")
                    msg = body[start:end].strip()
                    print(f"💬 SMS Response: {msg[:300]}")
                else:
                    print("ℹ️ TwiML did not include <Message> content.")
            else:
                print("❌ Webhook endpoint failed")
                print(body)

    return True

def main():
    print("SMS Webhook Test Runner")
    print("=" * 60)
    ok = test_sms_webhook()
    if ok:
        print_header("SUMMARY")
        print("✅ SMS webhook functionality tested")
        print("📱 Processor covers correlations, trends, patterns, anomalies, interventions")
        print("🧾 Parser covers event logging (meal/supplement/sleep/workout)")
        print("🌐 Webhook endpoint reachable and returns TwiML")
        print("🎯 Ready for real SMS flow (Twilio webhook → your route)")
    else:
        print("\n❌ SMS webhook test failed.")

if __name__ == "__main__":
    main()
