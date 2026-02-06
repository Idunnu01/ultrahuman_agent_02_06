#!/usr/bin/env python3
"""
Direct backfill script that bypasses Flask app context issues.
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from pathlib import Path
import os
import sys
import time

# Load environment variables first
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# Import the backfill function and Flask app
from tasks.data_ingestion import backfill_user_data
from app import create_app

def main():
    # Configuration
    user_id = "adewusiemmanuel@gmail.com"
    start_date = date(2025, 8, 1)   # August 1, 2025 (more recent)
    end_date = date(2025, 8, 28)    # August 28, 2025 (today)

    print("=" * 60)
    print("DIRECT BACKFILL - OCTOBER TO DECEMBER 2024")
    print("=" * 60)
    print(f"User ID: {user_id}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Total Days: {(end_date - start_date).days}")
    print("=" * 60)

    # Check environment
    print("Environment check:")
    print(f"  ULTRAHUMAN_API_BASE: {os.getenv('ULTRAHUMAN_API_BASE')}")
    print(f"  UH_AUTH_KEY: {'*' * 10 if os.getenv('UH_AUTH_KEY') else 'NOT SET'}")
    print(f"  UH_EMAIL: {os.getenv('UH_EMAIL')}")
    print()

    # Initialize Flask app
    app = create_app()

    # Break into 90-day windows (API limit)
    current_start = start_date
    window_count = 0
    total_metrics = 0
    total_chunks = 0
    all_errors = []

    with app.app_context():
        while current_start < end_date:
            window_end = min(current_start + timedelta(days=90), end_date)
            window_count += 1

            print(f"Processing window {window_count}: {current_start} to {window_end}")

            try:
                result = backfill_user_data(
                    user_id,
                    current_start.isoformat(),
                    window_end.isoformat()
                )

                if result.get("success"):
                    metrics_in_window = int(result.get("total_metrics_processed", 0))
                    chunks_in_window = int(result.get("chunks_processed", 0))

                    total_metrics += metrics_in_window
                    total_chunks += chunks_in_window

                    print(f"  ✅ Success: {metrics_in_window} metrics, {chunks_in_window} chunks")

                    if result.get("errors"):
                        print(f"  ⚠️  Warnings: {len(result['errors'])} errors in this window")
                        all_errors.extend(result["errors"])
                else:
                    error_msg = result.get("error", "Unknown error")
                    print(f"  ❌ Failed: {error_msg}")
                    all_errors.append({
                        "date_range": f"{current_start}..{window_end}",
                        "error": error_msg
                    })

            except Exception as e:
                print(f"  ❌ Exception: {str(e)}")
                all_errors.append({
                    "date_range": f"{current_start}..{window_end}",
                    "error": str(e)
                })

            # Move to next window
            current_start = window_end

            # Sleep between windows to respect rate limits
            if current_start < end_date:
                print("  Sleeping 2 seconds...")
                time.sleep(2)

    # Final summary
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"User ID: {user_id}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Windows Processed: {window_count}")
    print(f"Total Metrics: {total_metrics}")
    print(f"Total Chunks: {total_chunks}")
    print(f"Errors: {len(all_errors)}")

    if all_errors:
        print("\nErrors encountered:")
        for error in all_errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(all_errors) > 5:
            print(f"  ... and {len(all_errors) - 5} more errors")

    print("\nNext steps:")
    print("1. Check your data: python simple_data_check.py")
    print("2. Test correlation analysis with your real data")

    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
