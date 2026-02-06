"""
API endpoints for semantic health analysis
Add these routes to your Flask app
"""

from flask import request, jsonify
from datetime import datetime
import logging

from services.enhanced_sms_service import EnhancedSMSService

logger = logging.getLogger(__name__)

def add_semantic_routes(app):
    """Add semantic health analysis routes to Flask app"""

    enhanced_sms_service = EnhancedSMSService()

    @app.route('/api/health-note', methods=['POST'])
    def process_health_note():
        """Process natural language health note"""
        try:
            data = request.get_json()

            if not data or 'description' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Description is required'
                }), 400

            user_id = data.get('user_id', 'user_7000')  # Default to your user
            description = data['description']
            event_date = data.get('event_date')

            if event_date:
                try:
                    event_date = datetime.fromisoformat(event_date)
                except:
                    event_date = None

            # Process the health note
            result = enhanced_sms_service.process_health_note(user_id, description)

            if result.get('success'):
                return jsonify({
                    'success': True,
                    'event_id': result['event_id'],
                    'structured_data': result['structured_data'],
                    'tags': result['tags'],
                    'message': 'Health note processed successfully'
                })
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Health note processing failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    @app.route('/api/health-patterns', methods=['GET'])
    def search_health_patterns():
        """Search health patterns using natural language"""
        try:
            query = request.args.get('q')
            user_id = request.args.get('user_id', 'user_7000')
            limit = int(request.args.get('limit', 10))

            if not query:
                return jsonify({
                    'success': False,
                    'error': 'Query parameter "q" is required'
                }), 400

            # Search patterns
            results = enhanced_sms_service.search_health_patterns(user_id, query)

            # Format results for API response
            formatted_results = []
            for result in results[:limit]:
                formatted_results.append({
                    'id': result['id'],
                    'date': result['event_date'].isoformat() if result['event_date'] else None,
                    'description': result['description'],
                    'structured_data': result['structured_data'],
                    'tags': result['tags'],
                    'similarity_score': result.get('similarity_score', 0)
                })

            return jsonify({
                'success': True,
                'query': query,
                'results': formatted_results,
                'count': len(formatted_results)
            })

        except Exception as e:
            logger.error(f"Health pattern search failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Search failed'
            }), 500

    @app.route('/api/health-insights', methods=['GET'])
    def get_health_insights():
        """Get AI-generated insights from health patterns"""
        try:
            user_id = request.args.get('user_id', 'user_7000')
            query = request.args.get('q', 'recent improvements and successful interventions')

            # Search for relevant patterns
            patterns = enhanced_sms_service.search_health_patterns(user_id, query)

            if not patterns:
                return jsonify({
                    'success': True,
                    'insights': ['No similar patterns found in your health history'],
                    'recommendations': ['Continue tracking consistently for better insights']
                })

            # Extract insights from patterns
            insights = []
            recommendations = []

            for pattern in patterns[:5]:  # Top 5 patterns
                structured = pattern.get('structured_data', {})

                # Extract successful interventions
                supplements = structured.get('supplements', [])
                for supp in supplements:
                    if supp.get('name'):
                        recommendations.append(f"Consider {supp['name']} {supp.get('dosage', '')} at {supp.get('time', 'optimal timing')}")

                # Extract insights from descriptions
                description = pattern.get('description', '')
                if 'improved' in description.lower() or 'better' in description.lower():
                    insights.append(f"Similar pattern on {pattern['event_date'].strftime('%B %d')}: {description[:100]}")

            # Remove duplicates and limit
            insights = list(set(insights))[:3]
            recommendations = list(set(recommendations))[:3]

            if not insights:
                insights = ['Your health tracking shows consistent patterns']
            if not recommendations:
                recommendations = ['Continue your current health monitoring routine']

            return jsonify({
                'success': True,
                'insights': insights,
                'recommendations': recommendations,
                'pattern_count': len(patterns)
            })

        except Exception as e:
            logger.error(f"Health insights generation failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Insight generation failed'
            }), 500

    @app.route('/api/enhanced-sms-preview', methods=['POST'])
    def preview_enhanced_sms():
        """Preview what enhanced SMS would look like for given analysis"""
        try:
            data = request.get_json()

            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Analysis data is required'
                }), 400

            user_id = data.get('user_id', 'user_7000')
            analysis_results = data.get('analysis_results', {})
            report_date = data.get('report_date', datetime.now().strftime('%Y-%m-%d'))

            # Generate enhanced SMS
            enhanced_sms = enhanced_sms_service.generate_super_rich_sms(
                analysis_results, user_id, report_date
            )

            return jsonify({
                'success': True,
                'enhanced_sms': enhanced_sms,
                'length': len(enhanced_sms),
                'within_limit': len(enhanced_sms) <= 306
            })

        except Exception as e:
            logger.error(f"Enhanced SMS preview failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Preview generation failed'
            }), 500

# Usage instructions for adding to your app.py:
"""
To add these routes to your existing Flask app:

1. Import at the top of app.py:
   from api_endpoints_semantic import add_semantic_routes

2. After creating your Flask app:
   add_semantic_routes(app)

3. Example usage:
   # Add a health note
   curl -X POST http://localhost:5000/api/health-note \\
        -H "Content-Type: application/json" \\
        -d '{"description": "took magnesium 400mg at 10pm, felt relaxed", "user_id": "user_7000"}'

   # Search health patterns
   curl "http://localhost:5000/api/health-patterns?q=magnesium%20sleep%20improvement&user_id=user_7000"

   # Get health insights
   curl "http://localhost:5000/api/health-insights?user_id=user_7000"

   # Preview enhanced SMS
   curl -X POST http://localhost:5000/api/enhanced-sms-preview \\
        -H "Content-Type: application/json" \\
        -d '{"analysis_results": {"baseline_statistics": {"sleep_score": {"latest_value": 85, "mean": 78}}}}'
"""