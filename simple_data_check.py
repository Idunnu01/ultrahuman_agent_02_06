#!/usr/bin/env python3
"""
Simple script to check your data without requiring Flask dependencies
"""

import sqlite3
import os
from datetime import datetime, timedelta

def check_data_simple():
    """Check your data using direct SQLite connection"""

    print("Checking your data using direct database connection...")
    print("=" * 50)

    # Check if the database file exists
    db_path = "instance/ultrahuman_agent.db"
    if not os.path.exists(db_path):
        print(f"Database file not found at: {db_path}")
        print("Make sure the application has been run at least once to create the database.")
        return

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        user_id = "sample_user"

        print(f"User ID: {user_id}")
        print(f"Database: {db_path}")

        # Check if the user exists
        cursor.execute("SELECT id, phone_number, ultrahuman_user_id FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            print(f"\n❌ User '{user_id}' not found in database")
            print("Available users:")
            cursor.execute("SELECT id, phone_number FROM users LIMIT 5")
            users = cursor.fetchall()
            for u in users:
                print(f"  - {u[0]} (phone: {u[1]})")
            return

        print(f"\n✅ User found: {user[0]}")
        print(f"  Phone: {user[1]}")
        print(f"  Ultrahuman ID: {user[2]}")

        # Check total metrics for this user
        cursor.execute("SELECT COUNT(*) FROM metrics WHERE user_id = ?", (user_id,))
        total_metrics = cursor.fetchone()[0]
        print(f"\nTotal metrics for user: {total_metrics}")

        if total_metrics == 0:
            print("❌ No metrics found for this user")
            print("This could mean:")
            print("  - The Ultrahuman device is not syncing data")
            print("  - Data hasn't been fetched from the Ultrahuman API yet")
            print("  - The user ID might be incorrect")
            return

        # Check metrics by type
        cursor.execute("""
            SELECT metric_type, COUNT(*) as count,
                   MAX(timestamp) as latest_timestamp,
                   MAX(value) as max_value, MIN(value) as min_value,
                   AVG(value) as avg_value
            FROM metrics
            WHERE user_id = ?
            GROUP BY metric_type
            ORDER BY count DESC
        """, (user_id,))

        metrics_by_type = cursor.fetchall()

        print(f"\nMetrics by type:")
        for metric_type, count, latest_ts, max_val, min_val, avg_val in metrics_by_type:
            print(f"  {metric_type}:")
            print(f"    Count: {count} data points")
            print(f"    Latest: {latest_ts}")
            print(f"    Range: {min_val:.2f} - {max_val:.2f}")
            print(f"    Average: {avg_val:.2f}")

        # Check recent data (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        seven_days_ago_str = seven_days_ago.strftime("%Y-%m-%d %H:%M:%S")

        print(f"\nRecent data (last 7 days, since {seven_days_ago_str}):")

        cursor.execute("""
            SELECT metric_type, COUNT(*) as count
            FROM metrics
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY metric_type
            ORDER BY count DESC
        """, (user_id, seven_days_ago_str))

        recent_metrics = cursor.fetchall()

        if not recent_metrics:
            print("  ❌ No recent data found in the last 7 days")
        else:
            for metric_type, count in recent_metrics:
                print(f"  {metric_type}: {count} data points")

        # Check specific metrics for correlation
        print(f"\nChecking data for correlation analysis:")

        # Temperature data
        cursor.execute("""
            SELECT timestamp, value, unit
            FROM metrics
            WHERE user_id = ?
              AND metric_type = 'temperature'
              AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (user_id, seven_days_ago_str))

        temp_data = cursor.fetchall()
        print(f"  Temperature data (last 7 days): {len(temp_data)} points")
        if temp_data:
            print("    Recent values:")
            for ts, val, unit in temp_data:
                print(f"      {ts}: {val} {unit}")

        # Sleep data
        cursor.execute("""
            SELECT timestamp, value, unit
            FROM metrics
            WHERE user_id = ?
              AND metric_type = 'sleep_score'
              AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (user_id, seven_days_ago_str))

        sleep_data = cursor.fetchall()
        print(f"  Sleep data (last 7 days): {len(sleep_data)} points")
        if sleep_data:
            print("    Recent values:")
            for ts, val, unit in sleep_data:
                print(f"      {ts}: {val} {unit}")

        # Heart rate data
        cursor.execute("""
            SELECT timestamp, value, unit
            FROM metrics
            WHERE user_id = ?
              AND metric_type = 'heart_rate'
              AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (user_id, seven_days_ago_str))

        hr_data = cursor.fetchall()
        print(f"  Heart rate data (last 7 days): {len(hr_data)} points")
        if hr_data:
            print("    Recent values:")
            for ts, val, unit in hr_data:
                print(f"      {ts}: {val} {unit}")

        # Correlation readiness check
        print(f"\nCorrelation Analysis Readiness:")
        if len(temp_data) >= 3 and len(sleep_data) >= 3:
            print(f"  ✅ Temperature + Sleep: Ready for correlation analysis!")
            print(f"    Temperature: {len(temp_data)} data points")
            print(f"    Sleep: {len(sleep_data)} data points")
        else:
            print(f"  ❌ Temperature + Sleep: Not enough data for correlation")
            print(f"    Temperature: {len(temp_data)} points (need at least 3)")
            print(f"    Sleep: {len(sleep_data)} points (need at least 3)")

        if len(temp_data) >= 3 and len(hr_data) >= 3:
            print(f"  ✅ Temperature + Heart Rate: Ready for correlation analysis!")
            print(f"    Temperature: {len(temp_data)} data points")
            print(f"    Heart Rate: {len(hr_data)} data points")
        else:
            print(f"  ❌ Temperature + Heart Rate: Not enough data for correlation")
            print(f"    Temperature: {len(temp_data)} points (need at least 3)")
            print(f"    Heart Rate: {len(hr_data)} points (need at least 3)")

        conn.close()

    except Exception as e:
        print(f"Error checking data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_data_simple()

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("This shows your ACTUAL data from the database.")
    print("If you have enough data points, correlation analysis will work.")
    print("If not, you'll need to wait for more data or check device sync.")
