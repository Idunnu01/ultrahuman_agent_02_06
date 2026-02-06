"""
SMS Health Question Analyzer
Handles analytical questions via SMS with concise responses
"""

import numpy as np
from scipy.stats import pearsonr, ttest_ind
from datetime import datetime, timedelta
from app.models import Metric, db

class SMSHealthAnalyzer:
    """Analyze health questions and provide SMS-friendly responses"""

    def __init__(self):
        self.max_sms_length = 306  # SMS character limit

    def analyze_question(self, question, user_id):
        """Analyze health question and return detailed response"""

        try:
            # Parse question
            lifestyle_factor, health_metric = self._parse_question(question)

            if not lifestyle_factor or not health_metric:
                return self._help_response()

            # Handle different types of analysis
            if lifestyle_factor == 'TREND_ANALYSIS':
                # Handle sleep-specific analysis
                if health_metric.endswith('_analysis'):
                    return self._handle_sleep_analysis(health_metric, user_id)

                header_info = f"📈 Trend Analysis: {health_metric}\n"

                # Get data for trend analysis (longer period)
                health_data = self._get_metric_data(user_id, health_metric, days=90)

                data_info = f"📊 Data availability:\n   {health_metric}: {len(health_data)} readings\n"

                if len(health_data) < 10:
                    return header_info + data_info + f"❌ Limited data for {health_metric.replace('_', ' ')} trend analysis. Need more readings."

                # Analyze trends
                trend_analysis = self._analyze_trends(health_data, health_metric)
                trend_response = self._format_trend_response(health_metric, trend_analysis)

                return header_info + data_info + trend_response

            elif lifestyle_factor == 'TIME_SPECIFIC_ANALYSIS':
                return self._handle_time_specific_analysis(health_metric, user_id)

            elif lifestyle_factor == 'OVERNIGHT_ANALYSIS':
                return self._handle_overnight_analysis(health_metric, user_id)

            elif lifestyle_factor == 'HOURLY_PATTERN_ANALYSIS':
                return self._handle_hourly_pattern_analysis(health_metric, user_id)

            elif lifestyle_factor == 'DATE_SPECIFIC_ANALYSIS':
                return self._handle_date_specific_analysis(health_metric, user_id)

            elif lifestyle_factor == 'WEEKDAY_ANALYSIS':
                return self._handle_weekday_analysis(health_metric, user_id)

            # Regular correlation analysis
            header_info = f"🔍 Analyzing: {lifestyle_factor} → {health_metric}\n"

            # Get data
            lifestyle_data = self._get_metric_data(user_id, lifestyle_factor, days=60)
            health_data = self._get_metric_data(user_id, health_metric, days=60)

            data_info = f"📊 Data availability:\n   {lifestyle_factor}: {len(lifestyle_data)} readings\n   {health_metric}: {len(health_data)} readings\n"

            if not lifestyle_data or not health_data:
                return header_info + data_info + f"❌ Limited data for {lifestyle_factor.replace('_', ' ')} → {health_metric.replace('_', ' ')}. Need more readings for analysis."

            # Analyze relationship
            analysis = self._analyze_relationship(lifestyle_data, health_data)

            # Format detailed response
            detailed_response = self._format_detailed_response(lifestyle_factor, health_metric, analysis)

            return header_info + data_info + detailed_response

        except Exception:
            return f"❌ Couldn't understand the question format\n💡 Try questions like:\n   • 'Did my meal timing affect my heart rate?'\n   • 'How does magnesium intake impact my HRV?'\n   • 'Does supplement intake correlate with sleep score?'"

    def _parse_question(self, question):
        """Parse SMS question to extract metrics and analysis type"""

        question_lower = question.lower()

        # Check for trend/temporal analysis keywords
        trend_keywords = ['trend', 'trending', 'average', 'over time', 'weekly', 'monthly', 'improving', 'getting better', 'getting worse', 'show me my', 'what\'s my', 'how is my', 'is my', 'did i get', 'how does my', 'compare to', 'what nights', 'how many', 'how are my', 'show me', 'how long']

        # Check for sleep-specific time-based questions
        sleep_time_keywords = ['how much', 'what time', 'how long', 'when do', 'bedtime', 'wake up', 'fall asleep', 'sleep time', 'last night', 'yesterday']

        # Check for specific time-based queries
        time_specific_keywords = ['at 3am', '3am', '3 am', 'during sleep', 'overnight', 'night time', 'morning', 'evening', 'afternoon', 'each day', 'time of day', 'hourly', 'daily pattern']

        # Check for date-specific queries
        date_specific_keywords = ['last night', 'yesterday', 'today', 'this week', 'last week', 'this month', 'weekend', 'weekday']

        is_trend_analysis = any(keyword in question_lower for keyword in trend_keywords)
        is_sleep_time_analysis = any(keyword in question_lower for keyword in sleep_time_keywords)
        is_time_specific = any(keyword in question_lower for keyword in time_specific_keywords)
        is_date_specific = any(keyword in question_lower for keyword in date_specific_keywords)

        if is_trend_analysis or is_sleep_time_analysis or is_time_specific or is_date_specific:
            # Enhanced health metric mappings including sleep details
            health_mappings = {
                'heart rate': 'heart_rate',
                'hr': 'heart_rate',
                'hrv': 'hrv',
                'heart rate variability': 'hrv',
                'sleep': 'sleep_score',
                'sleep score': 'sleep_score',
                'sleep quality': 'sleep_score',
                'recovery': 'recovery_score',
                'recovery score': 'recovery_score',
                'temperature': 'temperature',
                'temp': 'temperature',
                'steps': 'steps',
                'activity': 'active_minutes',
                'active minutes': 'active_minutes',
                'exercise': 'exercise_duration',

                # Glucose/Metabolic metrics
                'glucose': 'glucose',
                'blood sugar': 'glucose',
                'blood glucose': 'glucose',
                'metabolic score': 'metabolic_score',
                'metabolism': 'metabolic_score',
                'glucose variability': 'glucose_variability',
                'blood sugar variability': 'glucose_variability',
                'average glucose': 'average_glucose',
                'avg glucose': 'average_glucose',
                'hba1c': 'hba1c',
                'hemoglobin a1c': 'hba1c',
                'time in target': 'time_in_target',
                'glucose target': 'time_in_target',

                # Advanced recovery metrics
                'resting heart rate': 'resting_heart_rate',
                'rhr': 'resting_heart_rate',
                'rest heart rate': 'resting_heart_rate',
                'vo2 max': 'vo2_max',
                'vo2': 'vo2_max',
                'fitness': 'vo2_max',
                'cardio fitness': 'vo2_max',
                'movement index': 'movement_index',
                'movement': 'movement',
                'motion': 'movement',

                # Sleep-specific mappings (check specific sleep terms first)
                'deep sleep': 'deep_sleep_analysis',
                'rem sleep': 'rem_sleep_analysis',
                'rem': 'rem_sleep_analysis',
                'light sleep': 'light_sleep_analysis',
                'sleep efficiency': 'sleep_efficiency_analysis',
                'total sleep': 'total_sleep_analysis',
                'sleep time': 'sleep_timing_analysis',
                'bedtime': 'bedtime_analysis',
                'wake up': 'wake_time_analysis',
                'wake time': 'wake_time_analysis',
                'fall asleep': 'sleep_onset_analysis'
            }

            # Sort by length (descending) to match longer, more specific terms first
            sorted_mappings = sorted(health_mappings.items(), key=lambda x: len(x[0]), reverse=True)

            # Handle time-specific and date-specific queries with special analysis types
            for term, metric in sorted_mappings:
                if term in question_lower:
                    # Detect specific time-based analysis needed
                    if is_time_specific:
                        if any(t in question_lower for t in ['3am', '3 am', 'at 3am']):
                            return 'TIME_SPECIFIC_ANALYSIS', f"{metric}_at_3am"
                        elif any(t in question_lower for t in ['during sleep', 'overnight', 'night time']):
                            return 'OVERNIGHT_ANALYSIS', f"{metric}_overnight"
                        elif any(t in question_lower for t in ['morning']):
                            return 'TIME_SPECIFIC_ANALYSIS', f"{metric}_morning"
                        elif any(t in question_lower for t in ['evening']):
                            return 'TIME_SPECIFIC_ANALYSIS', f"{metric}_evening"
                        elif any(t in question_lower for t in ['each day', 'time of day', 'hourly', 'daily pattern']):
                            return 'HOURLY_PATTERN_ANALYSIS', f"{metric}_daily_pattern"

                    if is_date_specific:
                        if 'last night' in question_lower:
                            return 'DATE_SPECIFIC_ANALYSIS', f"{metric}_last_night"
                        elif 'yesterday' in question_lower:
                            return 'DATE_SPECIFIC_ANALYSIS', f"{metric}_yesterday"
                        elif any(t in question_lower for t in ['weekend', 'weekday']):
                            return 'WEEKDAY_ANALYSIS', f"{metric}_weekday_pattern"

                    # Default to trend analysis
                    return 'TREND_ANALYSIS', metric

        # Regular correlation/comparison analysis
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
            'steps': 'steps',
            'movement': 'movement',
            'motion': 'movement'
        }

        health_mappings = {
            'heart rate': 'heart_rate',
            'hr': 'heart_rate',
            'hrv': 'hrv',
            'heart rate variability': 'hrv',
            'sleep': 'sleep_score',
            'sleep score': 'sleep_score',
            'recovery': 'recovery_score',
            'recovery score': 'recovery_score',
            'temperature': 'temperature',
            'temp': 'temperature',
            # Glucose/Metabolic metrics
            'glucose': 'glucose',
            'blood sugar': 'glucose',
            'blood glucose': 'glucose',
            'metabolic score': 'metabolic_score',
            'metabolism': 'metabolic_score',
            'glucose variability': 'glucose_variability',
            'average glucose': 'average_glucose',
            'hba1c': 'hba1c',
            'time in target': 'time_in_target',
            # Advanced recovery metrics
            'resting heart rate': 'resting_heart_rate',
            'rhr': 'resting_heart_rate',
            'vo2 max': 'vo2_max',
            'vo2': 'vo2_max',
            'fitness': 'vo2_max',
            'movement index': 'movement_index',
            'movement': 'movement'
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

    def _get_sleep_data_with_details(self, user_id, days=60):
        """Get sleep data with detailed information from database"""

        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get full metric records for sleep data to access potential metadata
            sleep_records = db.session.query(Metric).filter(
                Metric.user_id == user_id,
                Metric.metric_type == 'sleep_score',
                Metric.timestamp >= cutoff_date
            ).order_by(Metric.timestamp.desc()).all()

            return sleep_records

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

    def _analyze_trends(self, health_data, _metric_type):
        """Analyze trends in health metric over time"""

        try:
            if len(health_data) < 10:
                return None

            # Sort by date
            health_data.sort(key=lambda x: x[1])

            values = [d[0] for d in health_data]
            dates = [d[1] for d in health_data]

            # Calculate basic statistics
            recent_30_days = [d[0] for d in health_data if (datetime.now() - d[1]).days <= 30]
            previous_30_days = [d[0] for d in health_data if 30 < (datetime.now() - d[1]).days <= 60]

            # Weekly averages
            weekly_averages = self._calculate_weekly_averages(health_data)

            # Calculate trend direction
            if len(values) >= 7:
                x = np.arange(len(values))
                slope = np.polyfit(x, values, 1)[0]
            else:
                slope = 0

            analysis = {
                'total_readings': len(health_data),
                'overall_average': np.mean(values),
                'recent_30_avg': np.mean(recent_30_days) if recent_30_days else None,
                'previous_30_avg': np.mean(previous_30_days) if previous_30_days else None,
                'min_value': np.min(values),
                'max_value': np.max(values),
                'std_dev': np.std(values),
                'slope': slope,
                'weekly_averages': weekly_averages,
                'first_week': weekly_averages[0] if weekly_averages else None,
                'last_week': weekly_averages[-1] if weekly_averages else None,
                'date_range': (dates[0], dates[-1])
            }

            return analysis

        except Exception:
            return None

    def _calculate_weekly_averages(self, health_data):
        """Calculate weekly averages from health data"""

        try:
            weekly_data = {}

            for value, timestamp in health_data:
                # Get week start (Monday)
                days_since_monday = timestamp.weekday()
                week_start = timestamp.date() - timedelta(days=days_since_monday)

                if week_start not in weekly_data:
                    weekly_data[week_start] = []
                weekly_data[week_start].append(value)

            # Calculate averages for each week
            weekly_averages = []
            for week_start in sorted(weekly_data.keys()):
                avg = np.mean(weekly_data[week_start])
                weekly_averages.append((week_start, avg, len(weekly_data[week_start])))

            return weekly_averages

        except Exception:
            return []

    def _format_trend_response(self, metric_type, analysis):
        """Format trend analysis into detailed response"""

        if not analysis:
            return "⚠️ Unable to analyze trends with current data"

        metric_name = metric_type.replace('_', ' ').title()
        response_lines = []

        response_lines.append("🧪 Trend Analysis:")
        response_lines.append("=" * 25)
        response_lines.append("💡 Key Insights:")
        response_lines.append("=" * 15)

        # Overall statistics
        response_lines.append("📊 Overall Statistics:")
        response_lines.append(f"   Total readings: {analysis['total_readings']}")
        response_lines.append(f"   Average {metric_name.lower()}: {analysis['overall_average']:.2f}")
        response_lines.append(f"   Range: {analysis['min_value']:.1f} - {analysis['max_value']:.1f}")
        response_lines.append(f"   Standard deviation: {analysis['std_dev']:.2f}")

        # Recent vs previous comparison
        if analysis['recent_30_avg'] and analysis['previous_30_avg']:
            change = analysis['recent_30_avg'] - analysis['previous_30_avg']
            percent_change = (change / analysis['previous_30_avg']) * 100

            response_lines.append("📈 30-Day Comparison:")
            response_lines.append(f"   Recent 30 days: {analysis['recent_30_avg']:.2f}")
            response_lines.append(f"   Previous 30 days: {analysis['previous_30_avg']:.2f}")
            response_lines.append(f"   Change: {change:+.2f} ({percent_change:+.1f}%)")

            if abs(percent_change) > 5:
                direction = "IMPROVING" if change > 0 else "DECLINING"
                response_lines.append(f"   💡 {metric_name} is {direction} over time")

        # Trend direction
        if abs(analysis['slope']) > 0.01:
            direction = "upward" if analysis['slope'] > 0 else "downward"
            response_lines.append(f"📈 Overall Trend: {direction.title()} trend detected")
        else:
            response_lines.append("📈 Overall Trend: Stable (no significant trend)")

        # Weekly analysis
        if len(analysis['weekly_averages']) >= 2:
            response_lines.append("📅 Weekly Analysis:")
            first_week = analysis['weekly_averages'][0]
            last_week = analysis['weekly_averages'][-1]

            weekly_change = last_week[1] - first_week[1]
            response_lines.append(f"   First week: {first_week[1]:.2f}")
            response_lines.append(f"   Latest week: {last_week[1]:.2f}")
            response_lines.append(f"   Week-to-week change: {weekly_change:+.2f}")

            response_lines.append(f"   Tracking over {len(analysis['weekly_averages'])} weeks")

        # Date range
        start_date = analysis['date_range'][0].strftime('%Y-%m-%d')
        end_date = analysis['date_range'][1].strftime('%Y-%m-%d')
        response_lines.append(f"⏱️ Analysis Period: {start_date} to {end_date}")

        return "\n".join(response_lines)

    def _handle_sleep_analysis(self, analysis_type, user_id):
        """Handle sleep-specific analysis questions"""

        if analysis_type == 'deep_sleep_analysis':
            return self._analyze_deep_sleep(user_id)
        elif analysis_type == 'rem_sleep_analysis':
            return self._analyze_rem_sleep(user_id)
        elif analysis_type == 'light_sleep_analysis':
            return self._analyze_light_sleep(user_id)
        elif analysis_type == 'sleep_efficiency_analysis':
            return self._analyze_sleep_efficiency(user_id)
        elif analysis_type == 'total_sleep_analysis':
            return self._analyze_total_sleep(user_id)
        elif analysis_type == 'sleep_timing_analysis':
            return self._analyze_sleep_timing(user_id)
        elif analysis_type == 'bedtime_analysis':
            return self._analyze_bedtime(user_id)
        elif analysis_type == 'wake_time_analysis':
            return self._analyze_wake_time(user_id)
        elif analysis_type == 'sleep_onset_analysis':
            return self._analyze_sleep_onset(user_id)
        else:
            return "❌ Sleep analysis type not supported yet. Try asking about sleep score trends instead."

    def _analyze_deep_sleep(self, user_id):
        """Analyze deep sleep patterns and trends"""

        # Try to get deep_sleep_minutes data first
        deep_sleep_data = self._get_metric_data(user_id, 'deep_sleep_minutes', days=60)

        if not deep_sleep_data:
            # Fall back to checking sleep_score data and related metrics
            sleep_data = self._get_metric_data(user_id, 'sleep_score', days=60)
            if not sleep_data:
                return "❌ No sleep data found. Make sure your sleep tracking is working."
            return self._analyze_sleep_from_scores(user_id, 'deep sleep', sleep_data)

        # Analyze deep sleep trends
        header = "💤 Deep Sleep Analysis\n"
        data_info = f"📊 Found {len(deep_sleep_data)} deep sleep readings\n"

        if len(deep_sleep_data) < 5:
            return header + data_info + "❌ Need more sleep data for deep sleep analysis."

        # Calculate statistics
        values = [d[0] for d in deep_sleep_data]
        recent_values = [d[0] for d in deep_sleep_data if (datetime.now() - d[1]).days <= 7]

        analysis = {
            'total_readings': len(deep_sleep_data),
            'average_deep_sleep': np.mean(values),
            'recent_average': np.mean(recent_values) if recent_values else None,
            'min_deep_sleep': np.min(values),
            'max_deep_sleep': np.max(values),
            'last_night': values[-1] if values else None
        }

        response_lines = [header, data_info]
        response_lines.append("🧪 Deep Sleep Analysis:")
        response_lines.append("=" * 25)

        # Average deep sleep
        avg_hours = analysis['average_deep_sleep'] / 60 if analysis['average_deep_sleep'] > 10 else analysis['average_deep_sleep']
        unit = "hours" if analysis['average_deep_sleep'] > 10 else "minutes"
        response_lines.append(f"📊 Average deep sleep: {avg_hours:.1f} {unit}")

        # Recent performance
        if analysis['recent_average']:
            recent_hours = analysis['recent_average'] / 60 if analysis['recent_average'] > 10 else analysis['recent_average']
            response_lines.append(f"📅 Recent (7 days): {recent_hours:.1f} {unit}")

            if analysis['recent_average'] > analysis['average_deep_sleep']:
                response_lines.append("✅ Deep sleep has IMPROVED recently")
            elif analysis['recent_average'] < analysis['average_deep_sleep'] * 0.9:
                response_lines.append("⚠️ Deep sleep has DECREASED recently")

        # Last night
        if analysis['last_night']:
            last_hours = analysis['last_night'] / 60 if analysis['last_night'] > 10 else analysis['last_night']
            response_lines.append(f"🌙 Last reading: {last_hours:.1f} {unit}")

        # Range
        min_hours = analysis['min_deep_sleep'] / 60 if analysis['min_deep_sleep'] > 10 else analysis['min_deep_sleep']
        max_hours = analysis['max_deep_sleep'] / 60 if analysis['max_deep_sleep'] > 10 else analysis['max_deep_sleep']
        response_lines.append(f"📈 Range: {min_hours:.1f} - {max_hours:.1f} {unit}")

        # Health insights
        response_lines.append("\n💡 Deep Sleep Insights:")
        if avg_hours >= 1.5 if unit == "hours" else avg_hours >= 90:
            response_lines.append("✅ Good deep sleep duration")
        else:
            response_lines.append("⚠️ Consider optimizing sleep environment for more deep sleep")

        return "\n".join(response_lines)

    def _analyze_rem_sleep(self, user_id):
        """Analyze REM sleep patterns and trends"""

        # Try to get rem_sleep_minutes data first
        rem_sleep_data = self._get_metric_data(user_id, 'rem_sleep_minutes', days=60)

        if not rem_sleep_data:
            # Fall back to checking sleep_score data
            sleep_data = self._get_metric_data(user_id, 'sleep_score', days=60)
            if not sleep_data:
                return "❌ No sleep data found. Make sure your sleep tracking is working."
            return self._analyze_sleep_from_scores(user_id, 'REM sleep', sleep_data)

        # Analyze REM sleep trends
        header = "🌙 REM Sleep Analysis\n"
        data_info = f"📊 Found {len(rem_sleep_data)} REM sleep readings\n"

        if len(rem_sleep_data) < 5:
            return header + data_info + "❌ Need more sleep data for REM sleep analysis."

        # Calculate statistics
        values = [d[0] for d in rem_sleep_data]
        recent_values = [d[0] for d in rem_sleep_data if (datetime.now() - d[1]).days <= 7]

        analysis = {
            'total_readings': len(rem_sleep_data),
            'average_rem_sleep': np.mean(values),
            'recent_average': np.mean(recent_values) if recent_values else None,
            'min_rem_sleep': np.min(values),
            'max_rem_sleep': np.max(values),
            'last_night': values[-1] if values else None
        }

        response_lines = [header, data_info]
        response_lines.append("🧪 REM Sleep Analysis:")
        response_lines.append("=" * 25)

        # Average REM sleep
        avg_hours = analysis['average_rem_sleep'] / 60 if analysis['average_rem_sleep'] > 10 else analysis['average_rem_sleep']
        unit = "hours" if analysis['average_rem_sleep'] > 10 else "minutes"
        response_lines.append(f"📊 Average REM sleep: {avg_hours:.1f} {unit}")

        # Recent performance
        if analysis['recent_average']:
            recent_hours = analysis['recent_average'] / 60 if analysis['recent_average'] > 10 else analysis['recent_average']
            response_lines.append(f"📅 Recent (7 days): {recent_hours:.1f} {unit}")

            if analysis['recent_average'] > analysis['average_rem_sleep']:
                response_lines.append("✅ REM sleep has IMPROVED recently")
            elif analysis['recent_average'] < analysis['average_rem_sleep'] * 0.9:
                response_lines.append("⚠️ REM sleep has DECREASED recently")

        # Last night
        if analysis['last_night']:
            last_hours = analysis['last_night'] / 60 if analysis['last_night'] > 10 else analysis['last_night']
            response_lines.append(f"🌙 Last reading: {last_hours:.1f} {unit}")

        # Range
        min_hours = analysis['min_rem_sleep'] / 60 if analysis['min_rem_sleep'] > 10 else analysis['min_rem_sleep']
        max_hours = analysis['max_rem_sleep'] / 60 if analysis['max_rem_sleep'] > 10 else analysis['max_rem_sleep']
        response_lines.append(f"📈 Range: {min_hours:.1f} - {max_hours:.1f} {unit}")

        # Health insights
        response_lines.append("\n💡 REM Sleep Insights:")
        if avg_hours >= 1.5 if unit == "hours" else avg_hours >= 90:
            response_lines.append("✅ Good REM sleep duration")
        else:
            response_lines.append("⚠️ Consider consistent sleep schedule for better REM sleep")

        return "\n".join(response_lines)

    def _analyze_sleep_efficiency(self, user_id):
        """Analyze sleep efficiency patterns"""

        # Try to get sleep_efficiency data first
        efficiency_data = self._get_metric_data(user_id, 'sleep_efficiency', days=60)

        if not efficiency_data:
            # Fall back to sleep_score data
            sleep_data = self._get_metric_data(user_id, 'sleep_score', days=60)
            if not sleep_data:
                return "❌ No sleep data found. Make sure your sleep tracking is working."
            return self._analyze_sleep_from_scores(user_id, 'sleep efficiency', sleep_data)

        # Analyze sleep efficiency trends
        header = "💤 Sleep Efficiency Analysis\n"
        data_info = f"📊 Found {len(efficiency_data)} sleep efficiency readings\n"

        if len(efficiency_data) < 5:
            return header + data_info + "❌ Need more sleep data for efficiency analysis."

        # Calculate statistics
        values = [d[0] for d in efficiency_data]
        recent_values = [d[0] for d in efficiency_data if (datetime.now() - d[1]).days <= 7]

        analysis = {
            'total_readings': len(efficiency_data),
            'average_efficiency': np.mean(values),
            'recent_average': np.mean(recent_values) if recent_values else None,
            'min_efficiency': np.min(values),
            'max_efficiency': np.max(values),
            'last_night': values[-1] if values else None
        }

        response_lines = [header, data_info]
        response_lines.append("🧪 Sleep Efficiency Analysis:")
        response_lines.append("=" * 25)

        # Average efficiency
        response_lines.append(f"📊 Average efficiency: {analysis['average_efficiency']:.1f}%")

        # Recent performance
        if analysis['recent_average']:
            response_lines.append(f"📅 Recent (7 days): {analysis['recent_average']:.1f}%")

            if analysis['recent_average'] > analysis['average_efficiency']:
                response_lines.append("✅ Sleep efficiency has IMPROVED recently")
            elif analysis['recent_average'] < analysis['average_efficiency'] - 5:
                response_lines.append("⚠️ Sleep efficiency has DECREASED recently")

        # Last night
        if analysis['last_night']:
            response_lines.append(f"🌙 Last night: {analysis['last_night']:.1f}%")

        # Range
        response_lines.append(f"📈 Range: {analysis['min_efficiency']:.1f}% - {analysis['max_efficiency']:.1f}%")

        # Health insights
        response_lines.append("\n💡 Sleep Efficiency Insights:")
        if analysis['average_efficiency'] >= 85:
            response_lines.append("✅ Excellent sleep efficiency")
        elif analysis['average_efficiency'] >= 75:
            response_lines.append("✅ Good sleep efficiency")
        else:
            response_lines.append("⚠️ Consider optimizing bedtime routine for better efficiency")

        return "\n".join(response_lines)

    def _analyze_sleep_timing(self, user_id):
        """Analyze sleep timing patterns (bedtime, wake time, duration)"""

        # Get recent sleep data to analyze timing
        sleep_data = self._get_metric_data(user_id, 'sleep_score', days=30)

        if not sleep_data:
            return "❌ No sleep data found. Make sure your sleep tracking is working."

        header = "⏰ Sleep Timing Analysis\n"
        data_info = f"📊 Found {len(sleep_data)} sleep records\n"

        if len(sleep_data) < 5:
            return header + data_info + "❌ Need more sleep data for timing analysis."

        response_lines = [header, data_info]
        response_lines.append("🧪 Sleep Timing Analysis:")
        response_lines.append("=" * 25)
        response_lines.append("📊 Based on available sleep score data")
        response_lines.append("💡 For detailed timing data, ensure your sleep tracker")
        response_lines.append("   records bedtime and wake time details")

        # Basic analysis from sleep scores
        values = [d[0] for d in sleep_data]
        recent_values = [d[0] for d in sleep_data if (datetime.now() - d[1]).days <= 7]

        response_lines.append(f"\n📈 Sleep consistency over {len(sleep_data)} nights:")
        response_lines.append(f"   Average score: {np.mean(values):.1f}")
        if recent_values:
            response_lines.append(f"   Recent average: {np.mean(recent_values):.1f}")

        # Timing insights
        response_lines.append("\n⏰ Timing Recommendations:")
        response_lines.append("   • Maintain consistent bedtime (±30 min)")
        response_lines.append("   • Aim for 7-9 hours total sleep time")
        response_lines.append("   • Wake up at same time daily")

        return "\n".join(response_lines)

    def _analyze_bedtime(self, user_id):
        """Analyze bedtime patterns"""
        return self._analyze_sleep_timing_specific(user_id, "bedtime")

    def _analyze_wake_time(self, user_id):
        """Analyze wake time patterns"""
        return self._analyze_sleep_timing_specific(user_id, "wake time")

    def _analyze_sleep_onset(self, user_id):
        """Analyze sleep onset (time to fall asleep) patterns"""
        return self._analyze_bedtime_with_actual_data(user_id)

    def _analyze_sleep_timing_specific(self, user_id, timing_type):
        """Analyze specific sleep timing aspect"""

        sleep_data = self._get_metric_data(user_id, 'sleep_score', days=30)

        if not sleep_data:
            return "❌ No sleep data found. Make sure your sleep tracking is working."

        header = f"⏰ {timing_type.title()} Analysis\n"
        data_info = f"📊 Found {len(sleep_data)} sleep records\n"

        response_lines = [header, data_info]
        response_lines.append(f"🧪 {timing_type.title()} Analysis:")
        response_lines.append("=" * 25)

        if timing_type == "bedtime":
            response_lines.append("💤 Bedtime Analysis:")
            response_lines.append("   Based on sleep score consistency")
            response_lines.append("   💡 Consistent bedtime improves sleep quality")
            response_lines.append("   📊 Ideal bedtime: 9-11 PM for most people")
        elif timing_type == "wake time":
            response_lines.append("🌅 Wake Time Analysis:")
            response_lines.append("   Based on sleep score patterns")
            response_lines.append("   💡 Consistent wake time regulates circadian rhythm")
            response_lines.append("   📊 Natural wake time without alarm is healthiest")
        else:  # sleep onset
            response_lines.append("😴 Sleep Onset Analysis:")
            response_lines.append("   Based on sleep quality patterns")
            response_lines.append("   💡 Ideal time to fall asleep: 10-20 minutes")
            response_lines.append("   📊 Longer onset may indicate stress or environment issues")

        # Show recent sleep quality as proxy
        recent_values = [d[0] for d in sleep_data if (datetime.now() - d[1]).days <= 7]
        if recent_values:
            response_lines.append(f"\n📈 Recent sleep quality: {np.mean(recent_values):.1f}/100")
            if np.mean(recent_values) >= 80:
                response_lines.append(f"✅ Your {timing_type} appears to be working well")
            else:
                response_lines.append(f"⚠️ Consider optimizing your {timing_type} routine")

        return "\n".join(response_lines)

    def _analyze_light_sleep(self, user_id):
        """Analyze light sleep patterns"""

        sleep_data = self._get_metric_data(user_id, 'sleep_score', days=30)

        if not sleep_data:
            return "❌ No sleep data found. Make sure your sleep tracking is working."

        return self._analyze_sleep_from_scores(user_id, 'light sleep', sleep_data)

    def _analyze_total_sleep(self, user_id):
        """Analyze total sleep time patterns"""

        sleep_data = self._get_metric_data(user_id, 'sleep_score', days=60)

        if not sleep_data:
            return "❌ No sleep data found. Make sure your sleep tracking is working."

        header = "💤 Total Sleep Time Analysis\n"
        data_info = f"📊 Found {len(sleep_data)} sleep records\n"

        response_lines = [header, data_info]
        response_lines.append("🧪 Total Sleep Analysis:")
        response_lines.append("=" * 25)

        # Analysis based on sleep scores as proxy for sleep duration quality
        values = [d[0] for d in sleep_data]
        recent_values = [d[0] for d in sleep_data if (datetime.now() - d[1]).days <= 7]

        response_lines.append(f"📊 Sleep quality analysis over {len(sleep_data)} nights")
        response_lines.append(f"   Average score: {np.mean(values):.1f}/100")

        if recent_values:
            response_lines.append(f"   Recent average: {np.mean(recent_values):.1f}/100")

            if np.mean(recent_values) > np.mean(values):
                response_lines.append("✅ Sleep quality has improved recently")
            elif np.mean(recent_values) < np.mean(values) - 5:
                response_lines.append("⚠️ Sleep quality has declined recently")

        response_lines.append("\n💡 Total Sleep Insights:")
        response_lines.append("   • Aim for 7-9 hours of total sleep")
        response_lines.append("   • Quality matters as much as quantity")
        response_lines.append("   • Consistent sleep schedule improves efficiency")

        avg_score = np.mean(values)
        if avg_score >= 80:
            response_lines.append("✅ Your sleep duration appears adequate")
        else:
            response_lines.append("⚠️ Consider extending sleep time or improving quality")

        return "\n".join(response_lines)

    def _analyze_sleep_from_scores(self, user_id, sleep_aspect, sleep_data):
        """Fallback analysis using sleep scores when specific metrics unavailable"""

        header = f"💤 {sleep_aspect.title()} Analysis\n"
        data_info = f"📊 Analysis based on {len(sleep_data)} sleep score records\n"

        values = [d[0] for d in sleep_data]
        recent_values = [d[0] for d in sleep_data if (datetime.now() - d[1]).days <= 7]

        response_lines = [header, data_info]
        response_lines.append(f"🧪 {sleep_aspect.title()} Analysis:")
        response_lines.append("=" * 25)
        response_lines.append("⚠️ Detailed sleep stage data not available")
        response_lines.append("📊 Analysis based on overall sleep quality scores")
        response_lines.append(f"   Average sleep score: {np.mean(values):.1f}/100")

        if recent_values:
            response_lines.append(f"   Recent average: {np.mean(recent_values):.1f}/100")

        response_lines.append(f"\n💡 {sleep_aspect.title()} Insights:")
        response_lines.append("   • Sleep stages are tracked by your device")
        response_lines.append("   • Higher sleep scores often correlate with better sleep stages")
        response_lines.append("   • Consider checking your Ultrahuman app for detailed breakdown")

        return "\n".join(response_lines)

    def _handle_time_specific_analysis(self, health_metric, user_id):
        """Handle time-specific analysis like '3am', 'morning', 'evening'"""

        base_metric = health_metric.split('_')[0] if '_' in health_metric else health_metric

        if 'at_3am' in health_metric:
            return self._analyze_3am_values(base_metric, user_id)
        elif 'morning' in health_metric:
            return self._analyze_morning_values(base_metric, user_id)
        elif 'evening' in health_metric:
            return self._analyze_evening_values(base_metric, user_id)
        else:
            return self._analyze_general_time_specific(base_metric, user_id)

    def _handle_overnight_analysis(self, health_metric, user_id):
        """Handle overnight/sleep hours analysis"""

        base_metric = health_metric.replace('_overnight', '')
        return self._analyze_overnight_patterns(base_metric, user_id)

    def _handle_hourly_pattern_analysis(self, health_metric, user_id):
        """Handle daily pattern/hourly analysis"""

        base_metric = health_metric.replace('_daily_pattern', '')
        return self._analyze_daily_patterns(base_metric, user_id)

    def _handle_date_specific_analysis(self, health_metric, user_id):
        """Handle date-specific analysis like 'last night', 'yesterday'"""

        if 'last_night' in health_metric:
            base_metric = health_metric.replace('_last_night', '')

            # Special handling for sleep onset/bedtime queries
            if 'sleep_onset' in base_metric or 'bedtime' in base_metric or 'fall_asleep' in base_metric:
                return self._analyze_bedtime_with_actual_data(user_id)
            else:
                return self._analyze_last_night(base_metric, user_id)

        elif 'yesterday' in health_metric:
            base_metric = health_metric.replace('_yesterday', '')

            # Special handling for sleep onset/bedtime queries
            if 'sleep_onset' in base_metric or 'bedtime' in base_metric or 'fall_asleep' in base_metric:
                return self._analyze_bedtime_with_actual_data(user_id)
            else:
                return self._analyze_yesterday(base_metric, user_id)
        else:
            return self._analyze_general_date_specific(health_metric, user_id)

    def _handle_weekday_analysis(self, health_metric, user_id):
        """Handle weekday vs weekend analysis"""

        base_metric = health_metric.replace('_weekday_pattern', '')
        return self._analyze_weekday_patterns(base_metric, user_id)

    def _analyze_3am_values(self, metric_type, user_id):
        """Analyze specific metric values at 3am"""

        header = f"🌙 3 AM {metric_type.replace('_', ' ').title()} Analysis\n"

        # Get recent data
        all_data = self._get_metric_data(user_id, metric_type, days=30)

        if not all_data:
            return header + f"❌ No {metric_type.replace('_', ' ')} data found."

        # Filter for 3am values (2:30am to 3:30am window)
        threeem_values = []
        for value, timestamp in all_data:
            hour = timestamp.hour
            minute = timestamp.minute
            # 3am window: 2:30am to 3:30am
            if (hour == 2 and minute >= 30) or (hour == 3 and minute <= 30):
                threeem_values.append((value, timestamp))

        data_info = f"📊 Found {len(threeem_values)} readings around 3 AM (last 30 days)\n"

        if not threeem_values:
            return header + data_info + "❌ No readings found around 3 AM. Your device may not track during sleep hours."

        # Analyze 3am values
        values = [v[0] for v in threeem_values]
        recent_value = threeem_values[-1][0] if threeem_values else None
        recent_date = threeem_values[-1][1] if threeem_values else None

        response_lines = [header, data_info]
        response_lines.append("🧪 3 AM Analysis:")
        response_lines.append("=" * 20)

        if recent_value is not None and recent_date:
            response_lines.append(f"🌙 Most recent 3 AM reading: {recent_value}")
            response_lines.append(f"📅 Date: {recent_date.strftime('%Y-%m-%d at %I:%M %p')}")

        if len(values) > 1:
            avg_3am = np.mean(values)
            response_lines.append(f"📊 Average at 3 AM: {avg_3am:.1f}")
            response_lines.append(f"📈 Range: {min(values):.1f} - {max(values):.1f}")

            # Compare to all-day average
            all_values = [v[0] for v in all_data]
            all_day_avg = np.mean(all_values)
            diff = avg_3am - all_day_avg
            pct_diff = (diff / all_day_avg) * 100

            response_lines.append(f"\n💡 Compared to daily average ({all_day_avg:.1f}):")
            if abs(pct_diff) < 5:
                response_lines.append(f"✅ Similar levels at 3 AM ({diff:+.1f}, {pct_diff:+.1f}%)")
            elif diff < 0:
                response_lines.append(f"📉 Lower at 3 AM ({diff:.1f}, {pct_diff:.1f}%) - typical during sleep")
            else:
                response_lines.append(f"📈 Higher at 3 AM ({diff:+.1f}, {pct_diff:+.1f}%) - may indicate sleep disturbance")

        return "\n".join(response_lines)

    def _analyze_overnight_patterns(self, metric_type, user_id):
        """Analyze overnight patterns (10 PM to 6 AM)"""

        header = f"🌙 Overnight {metric_type.replace('_', ' ').title()} Analysis\n"

        # Get recent data
        all_data = self._get_metric_data(user_id, metric_type, days=14)

        if not all_data:
            return header + f"❌ No {metric_type.replace('_', ' ')} data found."

        # Filter for overnight hours (10 PM to 6 AM)
        overnight_values = []
        for value, timestamp in all_data:
            hour = timestamp.hour
            if hour >= 22 or hour <= 6:  # 10 PM to 6 AM
                overnight_values.append((value, timestamp))

        data_info = f"📊 Found {len(overnight_values)} overnight readings (10 PM - 6 AM)\n"

        if not overnight_values:
            return header + data_info + "❌ No overnight readings found."

        # Analyze overnight patterns
        values = [v[0] for v in overnight_values]

        response_lines = [header, data_info]
        response_lines.append("🧪 Overnight Pattern Analysis:")
        response_lines.append("=" * 30)

        # Basic overnight stats
        overnight_avg = np.mean(values)
        response_lines.append(f"🌙 Average overnight: {overnight_avg:.1f}")
        response_lines.append(f"📈 Range: {min(values):.1f} - {max(values):.1f}")

        # Compare to daytime (6 AM to 10 PM)
        daytime_values = []
        for value, timestamp in all_data:
            hour = timestamp.hour
            if 6 < hour < 22:  # 6 AM to 10 PM
                daytime_values.append(value)

        if daytime_values:
            daytime_avg = np.mean(daytime_values)
            diff = overnight_avg - daytime_avg
            pct_diff = (diff / daytime_avg) * 100

            response_lines.append(f"\n💡 Day vs Night Comparison:")
            response_lines.append(f"☀️ Daytime average: {daytime_avg:.1f}")
            response_lines.append(f"🌙 Overnight average: {overnight_avg:.1f}")
            response_lines.append(f"📊 Difference: {diff:+.1f} ({pct_diff:+.1f}%)")

            if metric_type == 'heart_rate':
                if diff < -5:
                    response_lines.append("✅ Good overnight recovery - heart rate drops during sleep")
                elif diff > 5:
                    response_lines.append("⚠️ Elevated overnight heart rate - may indicate stress or poor sleep")
                else:
                    response_lines.append("📊 Stable heart rate overnight")

        return "\n".join(response_lines)

    def _analyze_daily_patterns(self, metric_type, user_id):
        """Analyze when metric is highest/lowest during the day"""

        header = f"⏰ Daily Pattern: {metric_type.replace('_', ' ').title()}\n"

        # Get recent data
        all_data = self._get_metric_data(user_id, metric_type, days=14)

        if not all_data:
            return header + f"❌ No {metric_type.replace('_', ' ')} data found."

        # Group by hour of day
        hourly_data = {}
        for value, timestamp in all_data:
            hour = timestamp.hour
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(value)

        if len(hourly_data) < 3:
            return header + "❌ Not enough hourly data to analyze daily patterns."

        # Calculate hourly averages
        hourly_averages = {}
        for hour, values in hourly_data.items():
            if len(values) >= 2:  # At least 2 readings for that hour
                hourly_averages[hour] = np.mean(values)

        if not hourly_averages:
            return header + "❌ Insufficient data for hourly analysis."

        data_info = f"📊 Analyzed {len(all_data)} readings across {len(hourly_averages)} hours\n"

        # Find peak and low times
        max_hour = max(hourly_averages.items(), key=lambda x: x[1])
        min_hour = min(hourly_averages.items(), key=lambda x: x[1])

        response_lines = [header, data_info]
        response_lines.append("🧪 Daily Pattern Analysis:")
        response_lines.append("=" * 25)

        # Format time strings
        max_time = self._format_hour_to_time(max_hour[0])
        min_time = self._format_hour_to_time(min_hour[0])

        response_lines.append(f"📈 Highest: {max_hour[1]:.1f} at {max_time}")
        response_lines.append(f"📉 Lowest: {min_hour[1]:.1f} at {min_time}")

        # Show key time periods
        response_lines.append(f"\n⏰ Hourly Pattern:")

        # Morning (6-12)
        morning_hours = {h: v for h, v in hourly_averages.items() if 6 <= h <= 12}
        if morning_hours:
            morning_avg = np.mean(list(morning_hours.values()))
            response_lines.append(f"🌅 Morning (6 AM-12 PM): {morning_avg:.1f}")

        # Afternoon (12-18)
        afternoon_hours = {h: v for h, v in hourly_averages.items() if 12 <= h <= 18}
        if afternoon_hours:
            afternoon_avg = np.mean(list(afternoon_hours.values()))
            response_lines.append(f"☀️ Afternoon (12-6 PM): {afternoon_avg:.1f}")

        # Evening (18-22)
        evening_hours = {h: v for h, v in hourly_averages.items() if 18 <= h <= 22}
        if evening_hours:
            evening_avg = np.mean(list(evening_hours.values()))
            response_lines.append(f"🌆 Evening (6-10 PM): {evening_avg:.1f}")

        # Night (22-6)
        night_hours = {h: v for h, v in hourly_averages.items() if h >= 22 or h <= 6}
        if night_hours:
            night_avg = np.mean(list(night_hours.values()))
            response_lines.append(f"🌙 Night (10 PM-6 AM): {night_avg:.1f}")

        return "\n".join(response_lines)

    def _analyze_last_night(self, metric_type, user_id):
        """Analyze metric values from last night specifically"""

        header = f"🌙 Last Night's {metric_type.replace('_', ' ').title()}\n"

        # Calculate last night time range (6 PM yesterday to 6 AM today)
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        # Last night: 6 PM yesterday to 6 AM today
        last_night_start = yesterday.replace(hour=18, minute=0, second=0, microsecond=0)
        last_night_end = now.replace(hour=6, minute=0, second=0, microsecond=0)

        # If it's before 6 AM today, adjust to cover the previous night
        if now.hour < 6:
            last_night_end = now.replace(hour=6, minute=0, second=0, microsecond=0)
            last_night_start = (now - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)

        # Get all data
        all_data = self._get_metric_data(user_id, metric_type, days=7)

        # Filter for last night
        last_night_data = []
        for value, timestamp in all_data:
            if last_night_start <= timestamp <= last_night_end:
                last_night_data.append((value, timestamp))

        data_info = f"📊 Last night data ({last_night_start.strftime('%I %p')} - {last_night_end.strftime('%I %p')}): {len(last_night_data)} readings\n"

        if not last_night_data:
            return header + data_info + "❌ No data found for last night. Your device may not have been tracking."

        values = [v[0] for v in last_night_data]

        response_lines = [header, data_info]
        response_lines.append("🧪 Last Night Analysis:")
        response_lines.append("=" * 25)

        # Basic stats
        night_avg = np.mean(values)
        response_lines.append(f"🌙 Average last night: {night_avg:.1f}")
        response_lines.append(f"📈 Range: {min(values):.1f} - {max(values):.1f}")

        # Show specific time if asked about bedtime metrics
        if metric_type in ['heart_rate', 'hrv', 'temperature']:
            # Find bedtime period values (9 PM - 12 AM)
            bedtime_values = []
            for value, timestamp in last_night_data:
                if 21 <= timestamp.hour <= 23:
                    bedtime_values.append((value, timestamp))

            if bedtime_values:
                bedtime_avg = np.mean([v[0] for v in bedtime_values])
                response_lines.append(f"😴 During bedtime (9-11 PM): {bedtime_avg:.1f}")

        # Compare to typical night average
        night_comparison_data = []
        for value, timestamp in all_data:
            hour = timestamp.hour
            if hour >= 22 or hour <= 6:
                night_comparison_data.append(value)

        if len(night_comparison_data) > len(values):
            typical_night_avg = np.mean(night_comparison_data)
            diff = night_avg - typical_night_avg
            pct_diff = (diff / typical_night_avg) * 100 if typical_night_avg != 0 else 0

            response_lines.append(f"\n💡 Compared to typical nights:")
            response_lines.append(f"📊 Typical night average: {typical_night_avg:.1f}")
            response_lines.append(f"📊 Last night difference: {diff:+.1f} ({pct_diff:+.1f}%)")

            if abs(pct_diff) < 5:
                response_lines.append("✅ Normal night for you")
            elif pct_diff > 5:
                response_lines.append("📈 Higher than typical - possible sleep disturbance")
            else:
                response_lines.append("📉 Lower than typical - good recovery night")

        return "\n".join(response_lines)

    def _analyze_yesterday(self, metric_type, user_id):
        """Analyze metric values from yesterday"""

        header = f"📅 Yesterday's {metric_type.replace('_', ' ').title()}\n"

        # Calculate yesterday's time range
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today - timedelta(days=1)
        yesterday_end = today

        # Get all data
        all_data = self._get_metric_data(user_id, metric_type, days=7)

        # Filter for yesterday
        yesterday_data = []
        for value, timestamp in all_data:
            if yesterday_start <= timestamp < yesterday_end:
                yesterday_data.append((value, timestamp))

        data_info = f"📊 Yesterday ({yesterday_start.strftime('%Y-%m-%d')}): {len(yesterday_data)} readings\n"

        if not yesterday_data:
            return header + data_info + "❌ No data found for yesterday."

        values = [v[0] for v in yesterday_data]

        response_lines = [header, data_info]
        response_lines.append("🧪 Yesterday Analysis:")
        response_lines.append("=" * 22)

        # Basic stats
        yesterday_avg = np.mean(values)
        response_lines.append(f"📊 Yesterday's average: {yesterday_avg:.1f}")
        response_lines.append(f"📈 Range: {min(values):.1f} - {max(values):.1f}")
        response_lines.append(f"📋 Total readings: {len(yesterday_data)}")

        # Compare to recent average (last 7 days excluding yesterday)
        other_days_data = []
        for value, timestamp in all_data:
            if not (yesterday_start <= timestamp < yesterday_end):
                other_days_data.append(value)

        if other_days_data:
            recent_avg = np.mean(other_days_data)
            diff = yesterday_avg - recent_avg
            pct_diff = (diff / recent_avg) * 100 if recent_avg != 0 else 0

            response_lines.append(f"\n💡 Compared to recent average:")
            response_lines.append(f"📊 Recent average: {recent_avg:.1f}")
            response_lines.append(f"📊 Yesterday difference: {diff:+.1f} ({pct_diff:+.1f}%)")

            if abs(pct_diff) < 5:
                response_lines.append("✅ Typical day for you")
            elif pct_diff > 10:
                response_lines.append("📈 Significantly higher than usual")
            elif pct_diff < -10:
                response_lines.append("📉 Significantly lower than usual")

        return "\n".join(response_lines)

    def _format_hour_to_time(self, hour):
        """Convert 24-hour format to readable time"""
        if hour == 0:
            return "12 AM"
        elif hour < 12:
            return f"{hour} AM"
        elif hour == 12:
            return "12 PM"
        else:
            return f"{hour - 12} PM"

    def _analyze_morning_values(self, metric_type, user_id):
        """Analyze morning values (6 AM - 12 PM)"""
        return self._analyze_time_period(metric_type, user_id, "Morning", 6, 12)

    def _analyze_evening_values(self, metric_type, user_id):
        """Analyze evening values (6 PM - 10 PM)"""
        return self._analyze_time_period(metric_type, user_id, "Evening", 18, 22)

    def _analyze_time_period(self, metric_type, user_id, period_name, start_hour, end_hour):
        """Generic time period analysis"""

        header = f"⏰ {period_name} {metric_type.replace('_', ' ').title()} Analysis\n"

        all_data = self._get_metric_data(user_id, metric_type, days=14)

        if not all_data:
            return header + f"❌ No {metric_type.replace('_', ' ')} data found."

        # Filter for time period
        period_values = []
        for value, timestamp in all_data:
            if start_hour <= timestamp.hour < end_hour:
                period_values.append((value, timestamp))

        if not period_values:
            return header + f"❌ No {period_name.lower()} readings found."

        values = [v[0] for v in period_values]

        response_lines = [header]
        response_lines.append(f"📊 Found {len(period_values)} {period_name.lower()} readings")
        response_lines.append(f"🧪 {period_name} Analysis:")
        response_lines.append("=" * (len(period_name) + 10))

        period_avg = np.mean(values)
        response_lines.append(f"⏰ {period_name} average: {period_avg:.1f}")
        response_lines.append(f"📈 Range: {min(values):.1f} - {max(values):.1f}")

        # Compare to all-day average
        all_values = [v[0] for v in all_data]
        all_day_avg = np.mean(all_values)
        diff = period_avg - all_day_avg
        pct_diff = (diff / all_day_avg) * 100

        response_lines.append(f"\n💡 Compared to daily average ({all_day_avg:.1f}):")
        response_lines.append(f"📊 Difference: {diff:+.1f} ({pct_diff:+.1f}%)")

        if abs(pct_diff) < 5:
            response_lines.append(f"✅ {period_name} levels are typical for you")
        elif pct_diff > 5:
            response_lines.append(f"📈 Higher in {period_name.lower()} - normal circadian pattern")
        else:
            response_lines.append(f"📉 Lower in {period_name.lower()} - good recovery period")

        return "\n".join(response_lines)

    def _analyze_weekday_patterns(self, metric_type, user_id):
        """Analyze weekday vs weekend patterns"""

        header = f"📅 Weekday Pattern: {metric_type.replace('_', ' ').title()}\n"

        all_data = self._get_metric_data(user_id, metric_type, days=30)

        if not all_data:
            return header + f"❌ No {metric_type.replace('_', ' ')} data found."

        # Separate weekdays vs weekends
        weekday_values = []
        weekend_values = []

        for value, timestamp in all_data:
            if timestamp.weekday() < 5:  # Monday=0, Sunday=6
                weekday_values.append(value)
            else:
                weekend_values.append(value)

        response_lines = [header]
        response_lines.append(f"📊 Weekdays: {len(weekday_values)} readings | Weekends: {len(weekend_values)} readings")
        response_lines.append("🧪 Weekday vs Weekend Analysis:")
        response_lines.append("=" * 35)

        if weekday_values and weekend_values:
            weekday_avg = np.mean(weekday_values)
            weekend_avg = np.mean(weekend_values)
            diff = weekend_avg - weekday_avg
            pct_diff = (diff / weekday_avg) * 100 if weekday_avg != 0 else 0

            response_lines.append(f"👔 Weekday average: {weekday_avg:.1f}")
            response_lines.append(f"🏖️ Weekend average: {weekend_avg:.1f}")
            response_lines.append(f"📊 Difference: {diff:+.1f} ({pct_diff:+.1f}%)")

            if abs(pct_diff) < 5:
                response_lines.append("✅ Consistent patterns weekdays vs weekends")
            elif pct_diff > 5:
                response_lines.append("📈 Higher on weekends - more relaxed lifestyle")
            else:
                response_lines.append("📉 Lower on weekends - good recovery time")

        elif weekday_values:
            response_lines.append(f"👔 Weekday average: {np.mean(weekday_values):.1f}")
            response_lines.append("⚠️ No weekend data for comparison")

        elif weekend_values:
            response_lines.append(f"🏖️ Weekend average: {np.mean(weekend_values):.1f}")
            response_lines.append("⚠️ No weekday data for comparison")

        else:
            response_lines.append("❌ Insufficient data for weekday analysis")

        return "\n".join(response_lines)

    def _analyze_general_time_specific(self, metric_type, user_id):
        """Fallback for general time-specific analysis"""
        return f"⏰ Time-specific analysis for {metric_type.replace('_', ' ')} is being processed. Please be more specific about the time period you're interested in."

    def _analyze_general_date_specific(self, metric_type, user_id):
        """Fallback for general date-specific analysis"""
        return f"📅 Date-specific analysis for {metric_type.replace('_', ' ')} is being processed. Please specify which date or period you're interested in."

    def _analyze_bedtime_with_actual_data(self, user_id):
        """Analyze actual bedtime data from separate bedtime metric records"""

        # Get bedtime records directly from the bedtime metric type
        bedtime_records = self._get_metric_data(user_id, 'bedtime', days=30)

        if not bedtime_records:
            return "❌ No bedtime data found. Make sure your sleep tracking is working and syncing bedtime information."

        header = "🛌 Enhanced Bedtime Analysis\n"
        data_info = f"📊 Found {len(bedtime_records)} bedtime records\n"

        bedtimes = []
        recent_bedtime = None

        # Process bedtime records - they contain decimal hour values and bedtime_full metadata
        for value, timestamp in bedtime_records[:14]:  # Last 2 weeks

            # Convert decimal hour to time (e.g., 21.55 -> 21:33)
            hour = int(value)
            minute = int((value - hour) * 60)

            try:
                from datetime import time
                bedtime = time(hour, minute)
                bedtimes.append(bedtime)

                if recent_bedtime is None:  # Most recent (first in desc order)
                    recent_bedtime = bedtime

            except ValueError:
                continue  # Skip invalid times

        # Also check for bedtime_full timestamps in metadata for more precise times
        bedtime_metrics = Metric.query.filter(
            Metric.user_id == user_id,
            Metric.metric_type == 'bedtime'
        ).order_by(Metric.timestamp.desc()).limit(7).all()

        precise_bedtimes = []
        for record in bedtime_metrics:
            if record.meta_data and 'bedtime_full' in record.meta_data:
                bedtime_full = record.meta_data['bedtime_full']
                try:
                    from dateutil import parser
                    bedtime_dt = parser.parse(bedtime_full)
                    precise_bedtimes.append(bedtime_dt.time())
                    if len(precise_bedtimes) == 1:  # Most recent
                        recent_bedtime = bedtime_dt.time()
                except Exception:
                    continue

        # Use precise times if available, otherwise decimal conversion
        if precise_bedtimes:
            bedtimes = precise_bedtimes
            data_info += f"✅ Using precise bedtime timestamps\n"
        else:
            data_info += f"📊 Using decimal hour conversion\n"

        response_lines = [header, data_info]
        response_lines.append("🧪 Bedtime Analysis:")
        response_lines.append("=" * 25)

        if recent_bedtime:
            # Format the actual bedtime
            bedtime_str = recent_bedtime.strftime('%I:%M %p')
            response_lines.append(f"🌙 Most recent bedtime: {bedtime_str}")

            if len(bedtimes) >= 3:
                # Calculate average bedtime over recent data
                total_seconds = 0
                for t in bedtimes[:7]:
                    seconds = t.hour * 3600 + t.minute * 60 + t.second
                    # Handle times after midnight (adjust for 24-hour calculation)
                    if t.hour < 12:  # Assume times before noon are actually late night
                        seconds += 24 * 3600
                    total_seconds += seconds

                avg_seconds = total_seconds / len(bedtimes[:7])
                avg_seconds = avg_seconds % (24 * 3600)  # Wrap around 24 hours

                avg_hours = int(avg_seconds // 3600)
                avg_minutes = int((avg_seconds % 3600) // 60)

                # Format average time
                if avg_hours == 0:
                    avg_time_str = f"12:{avg_minutes:02d} AM"
                elif avg_hours < 12:
                    avg_time_str = f"{avg_hours}:{avg_minutes:02d} AM"
                elif avg_hours == 12:
                    avg_time_str = f"12:{avg_minutes:02d} PM"
                else:
                    avg_time_str = f"{avg_hours-12}:{avg_minutes:02d} PM"

                response_lines.append(f"📅 Average bedtime ({len(bedtimes[:7])} nights): {avg_time_str}")

            # Bedtime insights
            hour = recent_bedtime.hour
            if hour < 6:  # After midnight, treat as late night
                hour += 24

            response_lines.append("\n💡 Bedtime Insights:")
            if 21 <= hour <= 23:  # 9 PM - 11 PM
                response_lines.append("✅ Good bedtime window for optimal sleep")
            elif hour < 21:  # Before 9 PM
                response_lines.append("😴 Early bedtime - great for morning energy")
            else:  # After 11 PM
                response_lines.append("⚠️ Consider earlier bedtime for better sleep quality")

        else:
            response_lines.append("⚠️ No bedtime timestamps found in metadata")
            response_lines.append("📊 This may be due to:")
            response_lines.append("   • Sleep data not containing detailed timing")
            response_lines.append("   • Different metadata structure than expected")
            response_lines.append("   • Sleep tracking device limitations")

            # Try alternative approach: Use sleep_score timestamps as proxy
            if sleep_records:
                response_lines.append(f"\n🔄 Alternative Analysis:")
                response_lines.append(f"   Using sleep analysis timestamps as proxy for sleep periods")

                # Analyze when sleep scores were recorded (might indicate sleep periods)
                sleep_times = []
                for record in sleep_records[:7]:
                    sleep_time = record.timestamp.time()
                    sleep_times.append(sleep_time)

                if sleep_times:
                    # Most recent sleep analysis time
                    recent_sleep_time = sleep_times[0]
                    response_lines.append(f"🕐 Recent sleep analysis time: {recent_sleep_time.strftime('%I:%M %p')}")

                    # Check if sleep analyses happen in morning (indicating previous night's sleep)
                    morning_analyses = [t for t in sleep_times if 6 <= t.hour <= 10]
                    if morning_analyses:
                        response_lines.append("💡 Sleep analyses occur in morning - tracking overnight sleep")

            # Fallback to sleep quality analysis
            recent_scores = [r.value for r in sleep_records[:7]]
            if recent_scores:
                avg_score = sum(recent_scores) / len(recent_scores)
                response_lines.append(f"\n📈 Recent sleep quality: {avg_score:.1f}/100")

                if avg_score >= 80:
                    response_lines.append("✅ Your sleep timing appears to be working well")
                else:
                    response_lines.append("⚠️ Consider optimizing your bedtime routine")

        return "\n".join(response_lines)

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
        full_response = "\n".join(response_parts)

        if len(full_response) > self.max_sms_length:
            # Truncate to fit SMS
            truncated = full_response[:self.max_sms_length-3] + "..."
            return truncated

        return full_response

    def _format_detailed_response(self, lifestyle_factor, health_metric, analysis):
        """Format analysis into detailed response like ask_health_questions.py"""

        response_lines = []
        response_lines.append("🧪 Statistical Analysis:")
        response_lines.append("=" * 25)
        response_lines.append("💡 Key Insights:")
        response_lines.append("=" * 15)

        # Primary analysis
        comparison = analysis.get('comparison')
        correlation = analysis.get('correlation')

        if comparison:
            response_lines.append("📈 Comparison Analysis:")
            response_lines.append(f"   With {lifestyle_factor.replace('_', ' ')}: {comparison['with_mean']:.2f}")
            response_lines.append(f"   Without {lifestyle_factor.replace('_', ' ')}: {comparison['without_mean']:.2f}")
            response_lines.append(f"   Difference: {comparison['difference']:.2f} ({comparison['percent_change']:.1f}%)")
            response_lines.append(f"   Statistical significance: {'✅ Yes' if comparison['significant'] else '❌ No'}")

            # Insight
            if comparison['significant']:
                effect = "REDUCE" if comparison['difference'] < 0 else "IMPROVE"
                lifestyle_name = lifestyle_factor.replace('_', ' ').title()
                health_name = health_metric.replace('_', ' ')
                response_lines.append(f"   💡 {lifestyle_name} appears to {effect} {health_name}")

            # Temporal analysis if we have overlapping data
            if comparison['with_count'] > 0:
                response_lines.append("⏱️ Temporal Analysis:")
                response_lines.append(f"   Found {comparison['with_count']} instances to analyze")
                response_lines.append(f"   Average {health_metric.replace('_', ' ')} after {lifestyle_factor.replace('_', ' ')}: {comparison['with_mean']:.2f}")

        elif correlation and correlation['significant']:
            response_lines.append("📊 Correlation Analysis:")
            corr_strength = self._get_correlation_strength(abs(correlation['correlation']))
            sign = "positive" if correlation['correlation'] > 0 else "negative"
            response_lines.append(f"   {corr_strength} {sign} correlation: {correlation['correlation']:.3f}")
            response_lines.append(f"   Statistical significance: {'✅ Yes' if correlation['significant'] else '❌ No'}")
            response_lines.append(f"   Based on {correlation['sample_size']} overlapping days")

        else:
            response_lines.append("⚠️ No significant relationships found with current data")
            response_lines.append("💡 This could be due to:")
            response_lines.append("   • Limited overlapping data points")
            response_lines.append("   • Need longer time period for analysis")
            response_lines.append("   • Relationship may exist but be too subtle to detect")

        return "\n".join(response_lines)

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

        # Correlation question indicators
        correlation_indicators = [
            'did', 'does', 'how does', 'why', 'when', 'what about',
            'affect', 'impact', 'correlate', 'influence', 'change'
        ]

        # Trend question indicators
        trend_indicators = [
            'trend', 'trending', 'average', 'over time', 'weekly', 'monthly',
            'improving', 'getting better', 'getting worse', 'show me my',
            'what\'s my', 'how is my', 'is my', 'what is my', 'show me',
            'how many', 'how are my', 'how long', 'how much', 'what was my',
            'during sleep', 'overnight', 'at 3am', 'pattern overnight'
        ]

        lifestyle_terms = [
            'meal', 'magnesium', 'supplement', 'exercise', 'activity', 'steps'
        ]

        health_terms = [
            'heart rate', 'hrv', 'sleep', 'recovery', 'temperature', 'hr',
            'deep sleep', 'rem sleep', 'rem', 'light sleep', 'sleep efficiency',
            'total sleep', 'sleep time', 'bedtime', 'wake up', 'wake time', 'fall asleep',
            'glucose', 'blood sugar', 'metabolic score', 'metabolism', 'hba1c',
            'resting heart rate', 'rhr', 'vo2 max', 'vo2', 'fitness', 'movement', 'motion',
            'steps', 'active minutes', 'time in target'
        ]

        message_lower = message.lower()

        # Check for correlation questions
        has_correlation_word = any(indicator in message_lower for indicator in correlation_indicators)
        has_lifestyle = any(term in message_lower for term in lifestyle_terms)
        has_health = any(term in message_lower for term in health_terms)

        # Check for trend questions
        has_trend_word = any(indicator in message_lower for indicator in trend_indicators)

        # Return true if it's either type of health question
        is_correlation_question = has_correlation_word and (has_lifestyle or has_health)
        is_trend_question = has_trend_word and has_health

        return is_correlation_question or is_trend_question

    def _extract_bedtime_from_metadata(self, metadata):
        """Extract bedtime from various metadata field formats"""
        if not metadata:
            return None

        # List of possible bedtime field names
        bedtime_fields = [
            'bedtime', 'bedtime_start', 'sleep_start', 'onset_time',
            'start_time', 'sleep_onset', 'bedtime_actual'
        ]

        for field in bedtime_fields:
            if field in metadata:
                try:
                    bedtime_value = metadata[field]

                    # Handle different time formats
                    if isinstance(bedtime_value, str):
                        # Parse time string like "22:30:00" or "10:30 PM"
                        if ':' in bedtime_value:
                            time_parts = bedtime_value.replace(' PM', '').replace(' AM', '').split(':')
                            if len(time_parts) >= 2:
                                hour = int(time_parts[0])
                                minute = int(time_parts[1])

                                # Handle PM times if specified
                                if 'PM' in bedtime_value and hour != 12:
                                    hour += 12
                                elif 'AM' in bedtime_value and hour == 12:
                                    hour = 0

                                from datetime import time
                                return time(hour, minute)

                    elif hasattr(bedtime_value, 'hour'):
                        # Already a time/datetime object
                        return bedtime_value.time() if hasattr(bedtime_value, 'time') else bedtime_value

                except Exception:
                    continue

        return None

    def _extract_deep_sleep_from_metadata(self, metadata):
        """Extract deep sleep minutes from various metadata formats"""
        if not metadata:
            return None

        # List of possible deep sleep field names
        deep_sleep_fields = [
            'deep_sleep_minutes', 'deep_sleep_duration', 'deep_sleep',
            'deep_minutes', 'deep_time'
        ]

        for field in deep_sleep_fields:
            if field in metadata:
                try:
                    value = metadata[field]
                    if isinstance(value, (int, float)):
                        return int(value)
                except Exception:
                    continue

        # Check nested structures like stages
        if 'stages' in metadata and isinstance(metadata['stages'], dict):
            stages = metadata['stages']
            deep_fields = ['deep', 'deep_sleep', 'deep_minutes']

            for field in deep_fields:
                if field in stages:
                    try:
                        value = stages[field]
                        if isinstance(value, (int, float)):
                            return int(value)
                    except Exception:
                        continue

        return None
