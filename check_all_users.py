#!/usr/bin/env python3
"""
Comprehensive user information checker - shows all user details and latest metrics
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta

def format_timestamp(ts_str):
    """Format timestamp string for better readability"""
    if not ts_str:
        return "Never"
    try:
        if 'T' in ts_str:
            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return ts_str

def check_all_users():
    """Check comprehensive information for all users"""

    print("👥 COMPREHENSIVE USER INFORMATION")
    print("=" * 80)

    # Check if the database file exists
    db_path = "instance/ultrahuman_agent.db"
    if not os.path.exists(db_path):
        print(f"❌ Database file not found at: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all users with complete information
        cursor.execute("""
            SELECT id, ultrahuman_user_id, phone_number, timezone,
                   onboarded_at, preferences, is_active
            FROM users
            ORDER BY id
        """)

        users = cursor.fetchall()

        if not users:
            print("❌ No users found in the database")
            conn.close()
            return

        print(f"📊 Found {len(users)} users\n")

        for user in users:
            user_id, uh_user_id, phone, timezone, onboarded_at, preferences, is_active = user

            print(f"👤 USER: {user_id}")
            print("-" * 60)
            print(f"🆔 Ultrahuman User ID: {uh_user_id}")
            print(f"📱 Phone Number: {phone}")
            print(f"🌍 Timezone: {timezone}")
            print(f"📅 Onboarded: {format_timestamp(onboarded_at)}")
            print(f"⚡ Active: {'Yes' if is_active else 'No'}")

            # Parse and display preferences
            if preferences:
                try:
                    prefs = json.loads(preferences) if isinstance(preferences, str) else preferences
                    if prefs:
                        print(f"⚙️  Preferences:")
                        for key, value in prefs.items():
                            print(f"   - {key}: {value}")
                except:
                    print(f"⚙️  Preferences: {preferences}")

            # Get comprehensive metrics summary
            cursor.execute("""
                SELECT
                    metric_type,
                    COUNT(*) as count,
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value
                FROM metrics
                WHERE user_id = ?
                GROUP BY metric_type
                ORDER BY metric_type
            """, (user_id,))

            metrics_summary = cursor.fetchall()

            if metrics_summary:
                print(f"\n📈 METRICS SUMMARY ({len(metrics_summary)} types):")
                print("   Type            | Count | Latest Value | Avg    | Range      | Latest Data")
                print("   " + "-" * 75)

                for metric in metrics_summary:
                    m_type, count, earliest, latest, avg_val, min_val, max_val = metric

                    # Get the latest value for this metric type
                    cursor.execute("""
                        SELECT value, timestamp, unit
                        FROM metrics
                        WHERE user_id = ? AND metric_type = ?
                        ORDER BY timestamp DESC
                        LIMIT 1
                    """, (user_id, m_type))

                    latest_metric = cursor.fetchone()
                    if latest_metric:
                        latest_value, latest_ts, unit = latest_metric
                        unit_str = f" {unit}" if unit else ""
                        latest_date = format_timestamp(latest_ts)[:10]  # Just the date
                    else:
                        latest_value = avg_val
                        unit_str = ""
                        latest_date = "Unknown"

                    print(f"   {m_type:<15} | {count:5} | {latest_value:8.1f}{unit_str:<4} | {avg_val:6.1f} | {min_val:4.1f}-{max_val:<5.1f} | {latest_date}")

                # Show latest 10 metrics across all types
                cursor.execute("""
                    SELECT metric_type, value, unit, timestamp, source
                    FROM metrics
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (user_id,))

                recent_metrics = cursor.fetchall()

                if recent_metrics:
                    print(f"\n🕒 LATEST 10 METRICS:")
                    for rm in recent_metrics:
                        m_type, value, unit, ts, source = rm
                        unit_str = f" {unit}" if unit else ""
                        print(f"   {format_timestamp(ts)} | {m_type:<14} | {value:8.1f}{unit_str} ({source})")

                # Show data freshness
                cursor.execute("""
                    SELECT MAX(timestamp) as most_recent
                    FROM metrics
                    WHERE user_id = ?
                """, (user_id,))

                most_recent = cursor.fetchone()[0]
                if most_recent:
                    try:
                        if 'T' in most_recent:
                            recent_dt = datetime.fromisoformat(most_recent.replace('Z', '+00:00'))
                        else:
                            recent_dt = datetime.strptime(most_recent, '%Y-%m-%d %H:%M:%S')
                        days_ago = (datetime.utcnow() - recent_dt.replace(tzinfo=None)).days
                        print(f"\n📅 Data Freshness: Most recent data from {days_ago} days ago ({format_timestamp(most_recent)})")
                    except:
                        print(f"\n📅 Data Freshness: Most recent data: {most_recent}")

            else:
                print("\n❌ No metrics found for this user")

            # Check for alerts (if table exists)
            try:
                cursor.execute("""
                    SELECT COUNT(*) as total_alerts,
                           SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) as unresolved_alerts,
                           MAX(created_at) as latest_alert
                    FROM alerts
                    WHERE user_id = ?
                """, (user_id,))

                alert_info = cursor.fetchone()
                if alert_info and alert_info[0] > 0:
                    total_alerts, unresolved, latest_alert = alert_info
                    print(f"\n🚨 ALERTS: {total_alerts} total, {unresolved} unresolved")
                    if latest_alert:
                        print(f"   Latest: {format_timestamp(latest_alert)}")
            except sqlite3.OperationalError:
                pass  # Table doesn't exist

            # Check for daily reports (if table exists)
            try:
                cursor.execute("""
                    SELECT COUNT(*) as total_reports,
                           MAX(report_date) as latest_report,
                           SUM(CASE WHEN sms_sent = 1 THEN 1 ELSE 0 END) as reports_sent
                    FROM daily_reports
                    WHERE user_id = ?
                """, (user_id,))

                report_info = cursor.fetchone()
                if report_info and report_info[0] > 0:
                    total_reports, latest_report, reports_sent = report_info
                    print(f"\n📑 DAILY REPORTS: {total_reports} total, {reports_sent} sent via SMS")
                    if latest_report:
                        print(f"   Latest: {latest_report}")
            except sqlite3.OperationalError:
                pass  # Table doesn't exist

            # Check conversations (if table exists)
            try:
                cursor.execute("""
                    SELECT COUNT(*) as total_conversations,
                           MAX(created_at) as latest_conversation
                    FROM conversations
                    WHERE user_id = ?
                """, (user_id,))

                conv_info = cursor.fetchone()
                if conv_info and conv_info[0] > 0:
                    total_conv, latest_conv = conv_info
                    print(f"\n💬 CONVERSATIONS: {total_conv} total")
                    if latest_conv:
                        print(f"   Latest: {format_timestamp(latest_conv)}")
            except sqlite3.OperationalError:
                pass  # Table doesn't exist

            print("\n" + "=" * 80 + "\n")

        # Check if there are any metrics at all
        cursor.execute("SELECT COUNT(*) FROM metrics")
        total_all_metrics = cursor.fetchone()[0]
        print(f"\nTotal metrics in database: {total_all_metrics}")

        if total_all_metrics > 0:
            # Show some sample data
            cursor.execute("""
                SELECT user_id, metric_type, timestamp, value, unit
                FROM metrics
                ORDER BY timestamp DESC
                LIMIT 10
            """)

            sample_data = cursor.fetchall()
            print(f"\nRecent sample data:")
            for user_id, metric_type, timestamp, value, unit in sample_data:
                print(f"  {user_id} - {metric_type}: {value} {unit} at {timestamp}")

        conn.close()

    except Exception as e:
        print(f"Error checking users: {str(e)}")
        import traceback
        traceback.print_exc()

def suggest_next_steps():
    """Suggest next steps based on the data situation"""

    print("\n" + "=" * 50)
    print("NEXT STEPS:")
    print("=" * 50)

    print("\nBased on the database check:")
    print("1. If you see 'sample_user' with data:")
    print("   - This is test data, not your real data")
    print("   - You need to register your actual user account")
    print("   - Use your real email/phone number")

    print("\n2. If no users found:")
    print("   - You need to register a user first")
    print("   - Use the registration endpoint or create a user")

    print("\n3. If user exists but no metrics:")
    print("   - Check if Ultrahuman API is configured")
    print("   - Verify API keys are set correctly")
    print("   - Run data sync to fetch your metrics")

    print("\n4. To register your user:")
    print("   POST /users")
    print("   {")
    print('     "user_id": "adewusiemmanuel@gmail.com",')
    print('     "ultrahuman_user_id": "your_ultrahuman_id",')
    print('     "phone_number": "+your_phone_number"')
    print("   }")

    print("\n5. To sync your data:")
    print("   - Make sure your Ultrahuman device is connected")
    print("   - Run the data sync process")
    print("   - Check that API keys are valid")

if __name__ == "__main__":
    check_all_users()
    suggest_next_steps()

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("The database shows what users and data are available.")
    print("You need to either:")
    print("1. Use the existing user (if it has your data)")
    print("2. Register your own user account")
    print("3. Sync your Ultrahuman data to the system")
