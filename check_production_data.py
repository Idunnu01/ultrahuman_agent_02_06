#!/usr/bin/env python3
"""
Script to check production data - run this on PythonAnywhere
"""

import mysql.connector
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables (if running locally with .env file)
load_dotenv()

def connect_to_production_db():
    """Connect to the production MySQL database"""

    # Get database connection details from environment or hardcode for PythonAnywhere
    db_config = {
        'host': 'bphlite.mysql.pythonanywhere-services.com',
        'user': 'bphlite',
        'password': 'Opeyemi992!',  # Use environment variable in production
        'database': 'bphlite$default'
    }

    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def check_production_data():
    """Check all data in production database"""

    print("Checking Production Database Data")
    print("=" * 50)

    conn = connect_to_production_db()
    if not conn:
        print("❌ Failed to connect to production database")
        return

    cursor = conn.cursor(dictionary=True)

    try:
        # Check users
        print("\n👥 USERS:")
        cursor.execute("SELECT id, phone_number, ultrahuman_user_id, onboarded_at FROM users")
        users = cursor.fetchall()

        print(f"Total users: {len(users)}")
        for user in users:
            print(f"  - {user['id']}")
            print(f"    Phone: {user['phone_number']}")
            print(f"    UH ID: {user['ultrahuman_user_id']}")
            print(f"    Onboarded: {user['onboarded_at']}")
            print()

        if not users:
            print("❌ No users found")
            return

        # Check total metrics
        print("\n📊 METRICS OVERVIEW:")
        cursor.execute("SELECT COUNT(*) as total_metrics FROM metrics")
        total_metrics = cursor.fetchone()['total_metrics']
        print(f"Total metrics in database: {total_metrics:,}")

        # Check metrics per user
        print("\n📈 METRICS PER USER:")
        for user in users:
            user_id = user['id']

            # Total metrics for this user
            cursor.execute("SELECT COUNT(*) as count FROM metrics WHERE user_id = %s", (user_id,))
            user_total = cursor.fetchone()['count']

            print(f"\n🔹 {user_id}: {user_total:,} total metrics")

            if user_total == 0:
                print("   ❌ No metrics for this user")
                continue

            # Metrics by type
            cursor.execute("""
                SELECT metric_type,
                       COUNT(*) as count,
                       MIN(timestamp) as earliest,
                       MAX(timestamp) as latest,
                       MIN(value) as min_value,
                       MAX(value) as max_value,
                       AVG(value) as avg_value
                FROM metrics
                WHERE user_id = %s
                GROUP BY metric_type
                ORDER BY count DESC
            """, (user_id,))

            metric_types = cursor.fetchall()

            print(f"   Metric types: {len(metric_types)}")
            for metric in metric_types:
                print(f"     {metric['metric_type']}: {metric['count']:,} points")
                print(f"       Range: {metric['earliest']} to {metric['latest']}")
                print(f"       Values: {metric['min_value']:.2f} - {metric['max_value']:.2f} (avg: {metric['avg_value']:.2f})")

            # Recent data (last 7 days)
            seven_days_ago = datetime.now() - timedelta(days=7)
            cursor.execute("""
                SELECT COUNT(*) as recent_count
                FROM metrics
                WHERE user_id = %s AND timestamp >= %s
            """, (user_id, seven_days_ago))

            recent_count = cursor.fetchone()['recent_count']
            print(f"   📅 Recent data (last 7 days): {recent_count:,} metrics")

            # Today's data
            today = datetime.now().date()
            cursor.execute("""
                SELECT COUNT(*) as today_count
                FROM metrics
                WHERE user_id = %s AND DATE(timestamp) = %s
            """, (user_id, today))

            today_count = cursor.fetchone()['today_count']
            print(f"   📅 Today's data: {today_count:,} metrics")

        # Check statistical baselines
        print("\n📊 STATISTICAL BASELINES:")
        cursor.execute("SELECT COUNT(*) as count FROM statistical_baselines")
        baseline_count = cursor.fetchone()['count']
        print(f"Total statistical baselines: {baseline_count}")

        if baseline_count > 0:
            cursor.execute("""
                SELECT user_id, metric_type, sample_size, last_updated
                FROM statistical_baselines
                ORDER BY last_updated DESC
                LIMIT 10
            """)

            baselines = cursor.fetchall()
            print("Recent baselines:")
            for baseline in baselines:
                print(f"  {baseline['user_id']} - {baseline['metric_type']}: {baseline['sample_size']} samples ({baseline['last_updated']})")

        # Check system logs for any errors
        print("\n📋 RECENT SYSTEM LOGS:")
        cursor.execute("""
            SELECT level, source, message, created_at
            FROM system_logs
            WHERE level IN ('ERROR', 'WARNING')
            ORDER BY created_at DESC
            LIMIT 10
        """)

        logs = cursor.fetchall()
        if logs:
            for log in logs:
                print(f"  {log['level']}: {log['source']} - {log['message'][:100]}... ({log['created_at']})")
        else:
            print("  ✅ No recent errors or warnings")

        print("\n" + "=" * 50)
        print("DATA SUMMARY:")
        print(f"✅ Total users: {len(users)}")
        print(f"✅ Total metrics: {total_metrics:,}")
        print(f"✅ Statistical baselines: {baseline_count}")
        print("✅ Production database is operational")

    except mysql.connector.Error as e:
        print(f"❌ Database query error: {e}")

    finally:
        cursor.close()
        conn.close()

def check_specific_user(user_id):
    """Check data for a specific user"""

    print(f"Checking data for user: {user_id}")
    print("=" * 40)

    conn = connect_to_production_db()
    if not conn:
        return

    cursor = conn.cursor(dictionary=True)

    try:
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            print(f"❌ User {user_id} not found")
            return

        print(f"✅ User found: {user['id']}")
        print(f"   Phone: {user['phone_number']}")
        print(f"   UH ID: {user['ultrahuman_user_id']}")
        print(f"   Onboarded: {user['onboarded_at']}")

        # Get detailed metrics
        cursor.execute("""
            SELECT metric_type, COUNT(*) as count,
                   MIN(timestamp) as earliest,
                   MAX(timestamp) as latest,
                   AVG(value) as avg_value
            FROM metrics
            WHERE user_id = %s
            GROUP BY metric_type
            ORDER BY latest DESC
        """, (user_id,))

        metrics = cursor.fetchall()

        print(f"\n📊 Metrics for {user_id}:")
        print(f"Total metric types: {len(metrics)}")

        for metric in metrics:
            print(f"\n  {metric['metric_type']}:")
            print(f"    Count: {metric['count']:,}")
            print(f"    Period: {metric['earliest']} to {metric['latest']}")
            print(f"    Average: {metric['avg_value']:.2f}")

            # Get recent sample
            cursor.execute("""
                SELECT value, timestamp
                FROM metrics
                WHERE user_id = %s AND metric_type = %s
                ORDER BY timestamp DESC
                LIMIT 3
            """, (user_id, metric['metric_type']))

            samples = cursor.fetchall()
            recent_values = [f"{s['value']:.1f} ({s['timestamp']})" for s in samples]
            print(f"    Recent values: {recent_values}")

    except mysql.connector.Error as e:
        print(f"❌ Error: {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Check specific user
        user_id = sys.argv[1]
        check_specific_user(user_id)
    else:
        # Check all data
        check_production_data()

    print("\n" + "=" * 50)
    print("USAGE:")
    print("  python check_production_data.py                    # Check all data")
    print("  python check_production_data.py adewusiemmanuel@gmail.com  # Check specific user")
    print("")
    print("RUN THIS ON PYTHONANYWHERE:")
    print("1. Upload this file to your PythonAnywhere account")
    print("2. Open a console on PythonAnywhere")
    print("3. Run: python3.10 check_production_data.py")
    print("4. Or check specific user: python3.10 check_production_data.py adewusiemmanuel@gmail.com")