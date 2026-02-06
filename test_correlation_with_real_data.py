#!/usr/bin/env python3
"""
Test correlation analysis with real data and show the actual values being measured.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def test_correlation_with_real_data():
    """Test correlation analysis with real data and show actual values"""

    print("=" * 60)
    print("TESTING CORRELATION ANALYSIS WITH REAL DATA")
    print("=" * 60)

    try:
        # Import after setting up path
        from app import create_app
        from app.models import User, Metric
        from services.metrics_service import MetricsService
        from services.statistical_analyzer import StatisticalAnalyzer
        from utils.database import db
        from sqlalchemy import func

        # Create app context
        app = create_app()

        with app.app_context():
            user_id = "sample_user"

            print(f"User ID: {user_id}")
            print()

            # Get user
            user = User.query.filter_by(id=user_id).first()
            if not user:
                print(f"❌ User '{user_id}' not found")
                return False

            print(f"✅ Found user: {user.id}")
            print()

            # Test different correlation queries
            test_queries = [
                "Is there a correlation between my body temperature and heart rate?",
                "What's the relationship between my sleep score and heart rate?",
                "How does my HRV correlate with recovery?",
                "Is there a correlation between temperature and sleep score?",
                "What's the relationship between my heart rate and recovery?"
            ]

            for i, query in enumerate(test_queries, 1):
                print(f"🧪 TEST {i}: {query}")
                print("-" * 60)

                # Process the query
                metrics_service = MetricsService()
                result = metrics_service.process_sms_input(query, user_id)

                if result.get("success"):
                    print("✅ Query processed successfully")

                    # Get the correlation analysis
                    correlation_data = result.get("correlation_analysis", {})

                    if correlation_data:
                        print("\n📊 CORRELATION RESULTS:")
                        print(f"   Metric 1: {correlation_data.get('metric1', 'Unknown')}")
                        print(f"   Metric 2: {correlation_data.get('metric2', 'Unknown')}")
                        print(f"   Correlation coefficient: {correlation_data.get('correlation_coefficient', 'N/A'):.4f}")
                        print(f"   P-value: {correlation_data.get('p_value', 'N/A'):.6f}")
                        print(f"   Sample size: {correlation_data.get('sample_size', 'N/A')}")
                        print(f"   Date range: {correlation_data.get('date_range', 'N/A')}")

                        # Show the actual data points used
                        print("\n📈 RAW DATA POINTS USED:")
                        data_points = correlation_data.get('data_points', [])
                        if data_points:
                            print(f"   Total data points: {len(data_points)}")
                            print("   First 10 data points:")
                            for j, point in enumerate(data_points[:10]):
                                print(f"     {j+1}. {point}")
                            if len(data_points) > 10:
                                print(f"     ... and {len(data_points) - 10} more points")
                        else:
                            print("   No raw data points available")

                        # Show insights
                        insights = result.get("insights", "")
                        if insights:
                            print(f"\n💡 INSIGHTS:")
                            print(f"   {insights}")

                    else:
                        print("❌ No correlation analysis found in result")

                else:
                    print(f"❌ Query processing failed: {result.get('error', 'Unknown error')}")

                print("\n" + "=" * 60)
                print()

            # Test direct statistical analysis
            print("🔬 DIRECT STATISTICAL ANALYSIS TEST")
            print("-" * 60)

            # Get recent data for temperature and heart rate
            seven_days_ago = datetime.utcnow() - timedelta(days=7)

            # Get temperature data
            temp_data = db.session.query(
                Metric.timestamp,
                Metric.value
            ).filter(
                Metric.user_id == user_id,
                Metric.metric_type == 'temperature',
                Metric.timestamp >= seven_days_ago
            ).order_by(Metric.timestamp).all()

            # Get heart rate data
            hr_data = db.session.query(
                Metric.timestamp,
                Metric.value
            ).filter(
                Metric.user_id == user_id,
                Metric.metric_type == 'heart_rate',
                Metric.timestamp >= seven_days_ago
            ).order_by(Metric.timestamp).all()

            print(f"📊 Temperature data points: {len(temp_data)}")
            print(f"📊 Heart rate data points: {len(hr_data)}")

            if temp_data and hr_data:
                # Convert to pandas for analysis
                temp_df = pd.DataFrame(temp_data, columns=['timestamp', 'temperature'])
                hr_df = pd.DataFrame(hr_data, columns=['timestamp', 'heart_rate'])

                # Merge on timestamp (closest match)
                temp_df['date'] = temp_df['timestamp'].dt.date
                hr_df['date'] = hr_df['timestamp'].dt.date

                merged_df = pd.merge(temp_df, hr_df, on='date', how='inner')

                print(f"\n📈 MERGED DATA FOR CORRELATION:")
                print(f"   Total paired data points: {len(merged_df)}")

                if len(merged_df) >= 3:
                    # Calculate correlation
                    correlation = merged_df['temperature'].corr(merged_df['heart_rate'])

                    print(f"\n🔍 CORRELATION CALCULATION:")
                    print(f"   Temperature values: {merged_df['temperature'].tolist()}")
                    print(f"   Heart rate values: {merged_df['heart_rate'].tolist()}")
                    print(f"   Correlation coefficient: {correlation:.4f}")

                    # Show the actual paired values
                    print(f"\n📋 PAIRED VALUES:")
                    for i, row in merged_df.iterrows():
                        print(f"   {i+1}. Date: {row['date']}, Temp: {row['temperature']:.2f}, HR: {row['heart_rate']:.1f}")
                else:
                    print("❌ Not enough paired data points for correlation analysis")
            else:
                print("❌ No data available for direct analysis")

            return True

    except Exception as e:
        print(f"❌ Error testing correlation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Correlation Analysis Test with Real Data")
    print("=" * 60)

    success = test_correlation_with_real_data()

    if success:
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print("✅ Correlation analysis test complete")
        print("📊 You can see the actual values being measured")
        print("🧪 Ready to test SMS correlation queries")
    else:
        print("\n❌ Correlation test failed. Check the errors above.")

if __name__ == "__main__":
    main()
