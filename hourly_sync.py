#!/usr/bin/env python3
"""
Hourly data sync script for PythonAnywhere cron job
Fetches latest data from Ultrahuman API and stores in database
"""

import os
import sys
import mysql.connector
import requests
from datetime import datetime, date, timedelta
import json

# Database configuration
def connect_to_db():
    """Connect to production database"""
    return mysql.connector.connect(
        host='bphlite.mysql.pythonanywhere-services.com',
        user='bphlite',
        password='Opeyemi992!',
        database='bphlite$default'
    )

def log_message(level, message, user_id=None):
    """Log message to database and console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {level}: {message}")

    try:
        conn = connect_to_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_logs (user_id, level, source, message, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, level, 'hourly_sync', message, datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to log to database: {e}")

def fetch_ultrahuman_data(user_id, uh_email, target_date):
    """Fetch data from Ultrahuman API for a specific date"""

    api_key = 'eyJhbGciOiJIUzI1NiJ9.eyJzZWNyZXQiOiJlMDg4MjFkMzEyYzNkOTAxYjkxMCIsImV4cCI6MjUwMDkzNjc5Mn0.52ZFNCKV2cm01X-nynjPtyBVunvFGMi4iXIiDmxKIb0'
    base_url = 'https://partner.ultrahuman.com/api/v1'

    headers = {
        'Authorization': api_key,
        'Accept': 'application/json'
    }

    params = {
        'email': uh_email,
        'date': target_date.isoformat()
    }

    try:
        response = requests.get(f'{base_url}/metrics', headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            json_response = response.json()
            # Debug logging to see the actual response format
            log_message('INFO', f'API response type for {uh_email}: {type(json_response)}', user_id)

            # Add detailed debugging
            if isinstance(json_response, dict):
                log_message('DEBUG', f'Dict keys: {list(json_response.keys())}', user_id)
                if 'data' in json_response:
                    data_section = json_response['data']
                    log_message('DEBUG', f'data section type: {type(data_section)}', user_id)
                    if isinstance(data_section, dict):
                        log_message('DEBUG', f'data keys: {list(data_section.keys())}', user_id)
                        if 'metric_data' in data_section:
                            metric_data = data_section['metric_data']
                            log_message('DEBUG', f'metric_data type: {type(metric_data)}, length: {len(metric_data) if hasattr(metric_data, "__len__") else "N/A"}', user_id)
                            if hasattr(metric_data, '__len__') and len(metric_data) > 0:
                                log_message('DEBUG', f'First metric_data item type: {type(metric_data[0])}', user_id)
                        else:
                            log_message('DEBUG', 'No metric_data key in data section', user_id)
                    else:
                        log_message('DEBUG', f'data section is not dict, contains: {str(data_section)[:100]}', user_id)

            # Handle different response formats
            if isinstance(json_response, list):
                # Some emails return list format directly
                log_message('INFO', f'List format response with {len(json_response)} items', user_id)
                return {'data': {'metric_data': json_response}}
            elif isinstance(json_response, dict):
                # Standard format - but check if it has the expected structure
                if 'data' in json_response:
                    return json_response
                else:
                    # Dict but not standard format - might be direct metric data
                    log_message('INFO', f'Dict response without data key: {list(json_response.keys())[:5]}', user_id)
                    return {'data': {'metric_data': [json_response]}}
            else:
                log_message('WARNING', f'Unexpected response format for {uh_email}: {type(json_response)}', user_id)
                return {'data': {'metric_data': []}}
        elif response.status_code == 404:
            return {'data': {'metric_data': []}}  # No data for this date
        else:
            log_message('ERROR', f'API returned {response.status_code}: {response.text[:200]}', user_id)
            return None

    except Exception as e:
        log_message('ERROR', f'API request failed: {str(e)}', user_id)
        return None

def process_and_store_metrics(user_id, api_data):
    """Process API data and store metrics in database"""

    if not api_data or 'data' not in api_data:
        return 0

    metric_data = api_data['data'].get('metric_data', [])
    if not metric_data:
        return 0

    conn = connect_to_db()
    cursor = conn.cursor()

    metrics_inserted = 0

    try:
        for metric_group in metric_data:
            # Handle different response formats
            if isinstance(metric_group, dict):
                metric_type = metric_group.get('type', 'unknown')
                values = metric_group.get('object', {}).get('values', [])
            elif isinstance(metric_group, list):
                # If metric_group is a list, it might contain the values directly
                log_message('DEBUG', f'Got list format metric_group: {len(metric_group)} items', user_id)
                values = metric_group
                metric_type = 'unknown'
            else:
                log_message('WARNING', f'Unexpected metric_group format: {type(metric_group)}', user_id)
                continue

            for value_entry in values:
                if 'value' not in value_entry or 'timestamp' not in value_entry:
                    continue

                # Convert timestamp to datetime
                timestamp = datetime.fromtimestamp(value_entry['timestamp'])
                value = float(value_entry['value'])

                # Map metric types to our internal naming
                internal_metric_type = map_metric_type(metric_type)

                try:
                    # Insert metric with conflict handling
                    cursor.execute("""
                        INSERT IGNORE INTO metrics
                        (user_id, metric_type, value, timestamp, source, meta_data)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        internal_metric_type,
                        value,
                        timestamp,
                        'ultrahuman',
                        json.dumps(value_entry)
                    ))

                    if cursor.rowcount > 0:
                        metrics_inserted += 1

                except mysql.connector.IntegrityError:
                    # Duplicate entry - skip
                    pass

        conn.commit()

    except Exception as e:
        conn.rollback()
        log_message('ERROR', f'Failed to store metrics: {str(e)}', user_id)

    finally:
        cursor.close()
        conn.close()

    return metrics_inserted

def map_metric_type(api_metric_type):
    """Map API metric types to internal naming"""
    mapping = {
        'hr': 'heart_rate',
        'temp': 'temperature',
        'hrv': 'hrv',
        'steps': 'steps',
        'night_rhr': 'night_rhr',
        'sleep_rhr': 'sleep_rhr',
        'Sleep': 'sleep_score',
        'glucose': 'glucose',
        'metabolic_score': 'metabolic_score',
        'recovery_index': 'recovery',
        'movement_index': 'movement_index',
        'active_minutes': 'active_minutes',
        'vo2_max': 'vo2_max'
    }
    return mapping.get(api_metric_type, api_metric_type)

def sync_user_data(user_id, uh_email):
    """Sync data for a single user"""

    log_message('INFO', f'Starting sync for user {user_id}')

    # Sync last 2 days to catch any delayed data
    dates_to_sync = [
        date.today(),
        date.today() - timedelta(days=1)
    ]

    total_inserted = 0

    for target_date in dates_to_sync:
        api_data = fetch_ultrahuman_data(user_id, uh_email, target_date)

        if api_data:
            inserted = process_and_store_metrics(user_id, api_data)
            total_inserted += inserted

            if inserted > 0:
                log_message('INFO', f'Inserted {inserted} metrics for {user_id} on {target_date}')

    if total_inserted == 0:
        log_message('INFO', f'No new metrics for user {user_id}')
    else:
        log_message('INFO', f'Sync completed for {user_id}: {total_inserted} total new metrics')

    return total_inserted

def main():
    """Main sync process"""

    log_message('INFO', '🚀 Starting hourly data sync')

    try:
        # Get active users from database
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, ultrahuman_user_id
            FROM users
            WHERE is_active = 1
        """)

        users = cursor.fetchall()
        cursor.close()
        conn.close()

        if not users:
            log_message('WARNING', 'No active users found')
            return

        log_message('INFO', f'Found {len(users)} active users')

        total_new_metrics = 0
        successful_syncs = 0

        for user in users:
            user_id = user['id']
            uh_email = user['ultrahuman_user_id']

            try:
                metrics_inserted = sync_user_data(user_id, uh_email)
                total_new_metrics += metrics_inserted
                successful_syncs += 1

            except Exception as e:
                log_message('ERROR', f'Sync failed for {user_id}: {str(e)}')

        # Summary
        log_message('INFO', f'✅ Hourly sync completed: {successful_syncs}/{len(users)} users, {total_new_metrics} new metrics')

        # Update statistics if significant new data
        if total_new_metrics > 50:
            log_message('INFO', 'Significant new data detected - statistical baselines will be updated in next analysis cycle')

    except Exception as e:
        log_message('ERROR', f'Hourly sync failed: {str(e)}')

if __name__ == '__main__':
    main()