#!/usr/bin/env python3
"""
Fix syntax error in daily report from enhancement
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def fix_daily_report_syntax():
    """Fix syntax error in daily report"""

    daily_report_path = os.path.join(project_dir, 'tasks', 'daily_report.py')
    backup_path = daily_report_path + '.enhanced_backup'

    print("🔧 Fixing Daily Report Syntax Error")
    print("=" * 50)

    try:
        # First, check if we can restore from backup
        if os.path.exists(backup_path):
            print("✅ Found backup file, restoring...")

            with open(backup_path, 'r') as f:
                backup_content = f.read()

            with open(daily_report_path, 'w') as f:
                f.write(backup_content)

            print("✅ Restored from backup")
        else:
            print("❌ No backup found")
            return False

        # Test if the file is now syntactically correct
        try:
            import ast
            with open(daily_report_path, 'r') as f:
                content = f.read()

            ast.parse(content)
            print("✅ Daily report syntax is now correct")
            return True

        except SyntaxError as e:
            print(f"❌ Still has syntax error: {e}")
            return False

    except Exception as e:
        print(f"❌ Fix failed: {str(e)}")
        return False

def create_simple_enhanced_fallback():
    """Create a simple enhancement without complex string formatting"""

    daily_report_path = os.path.join(project_dir, 'tasks', 'daily_report.py')

    try:
        with open(daily_report_path, 'r') as f:
            content = f.read()

        print("📝 Adding simple enhanced fallback...")

        # Simple enhancement function that won't cause syntax errors
        simple_enhancement = '''
def _generate_enhanced_fallback_sms(insights_data, correlations_data, anomalies_data, trends_data, user_id, report_date):
    """Generate enhanced SMS using actual analysis data - simple version"""
    from datetime import datetime

    try:
        message_parts = []

        # Header with date
        if isinstance(report_date, str):
            date_obj = datetime.strptime(report_date, '%Y-%m-%d')
        else:
            date_obj = report_date

        date_str = date_obj.strftime("%b %d")
        message_parts.append("🌅 Daily Health - " + date_str)

        # Add insights if available
        if insights_data and isinstance(insights_data, dict):
            key_insights = insights_data.get('key_insights', [])
            if key_insights and len(key_insights) > 0:
                insight = str(key_insights[0])
                if len(insight) < 50:
                    if 'sleep' in insight.lower():
                        message_parts.append("💤 " + insight)
                    elif 'hrv' in insight.lower():
                        message_parts.append("❤️ " + insight)
                    else:
                        message_parts.append("📊 " + insight)

        # Add top correlation if available
        if correlations_data and isinstance(correlations_data, dict):
            for corr_name, corr_data in correlations_data.items():
                if isinstance(corr_data, dict) and corr_data.get('significant', False):
                    corr_val = corr_data.get('correlation', 0)
                    if abs(corr_val) > 0.3:
                        corr_name_clean = corr_name.replace('_', ' ').title()
                        if corr_val > 0:
                            message_parts.append("🔍 " + corr_name_clean + ": +" + str(int(abs(corr_val)*100)) + "% correlation")
                        break

        # Add recommendation from trends
        if trends_data and isinstance(trends_data, dict):
            for trend_name, trend_info in trends_data.items():
                if isinstance(trend_info, dict):
                    direction = trend_info.get('direction', 'stable')
                    strength = trend_info.get('strength', 0)
                    if strength > 0.5:
                        if 'sleep' in trend_name.lower() and direction == 'improving':
                            message_parts.append("💡 Sleep trending up - maintain routine")
                        break

        # Fallback content if no data
        if len(message_parts) == 1:  # Only header
            message_parts.append("📊 Health metrics analyzed")
            message_parts.append("💪 Keep up the good work")

        # Add ending
        message_parts.append("Open dashboard for details.")

        # Join with newlines
        sms_content = "\\n".join(message_parts)

        # Ensure it fits
        if len(sms_content) > 306:
            # Simple truncation
            sms_content = sms_content[:280] + "...\\nOpen dashboard for details."

        return sms_content

    except Exception as e:
        # Ultimate fallback
        return "🌅 Daily Health Update\\n📊 Analysis complete\\n💪 Keep up the great work!\\nOpen dashboard for details."
'''

        # Find a safe place to add this function
        if 'def _generate_fallback_sms(' in content:
            # Add before existing fallback
            insertion_point = content.find('def _generate_fallback_sms(')
            content = content[:insertion_point] + simple_enhancement + '\n\n' + content[insertion_point:]
            print("✅ Added enhanced fallback function")
        else:
            # Add at end
            content += '\n' + simple_enhancement
            print("✅ Added enhanced fallback function at end")

        # Write the updated content
        with open(daily_report_path, 'w') as f:
            f.write(content)

        # Test syntax
        import ast
        with open(daily_report_path, 'r') as f:
            test_content = f.read()

        ast.parse(test_content)
        print("✅ Enhanced daily report syntax verified")
        return True

    except Exception as e:
        print(f"❌ Enhancement failed: {str(e)}")
        return False

if __name__ == '__main__':
    print("🔧 Fix Daily Report Syntax Error")

    # First restore from backup
    restore_ok = fix_daily_report_syntax()

    if restore_ok:
        # Then add simple enhancement
        enhance_ok = create_simple_enhanced_fallback()

        if enhance_ok:
            print(f"\n✅ Daily Report Fixed and Enhanced!")
            print(f"✅ Syntax error resolved")
            print(f"✅ Simple enhanced SMS added")
            print(f"💡 Now test with: python force_new_report_test.py")
        else:
            print(f"\n⚠️ Fixed syntax but enhancement failed")
            print(f"💡 Basic functionality restored")
    else:
        print(f"\n❌ Could not fix syntax error")
        print(f"💡 May need manual intervention")