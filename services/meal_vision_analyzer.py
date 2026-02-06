"""
Meal Vision Analyzer - Analyzes food photos using Claude 3 Haiku Vision
Extracts nutrition info and logs meal events from photos
"""

from anthropic import Anthropic
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import re
import base64
import requests
from app.models import Metric
from utils.database import db

logger = logging.getLogger(__name__)


class MealVisionAnalyzer:
    """Analyzes meal photos to extract nutrition info and log meal events"""

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        # Use Claude 3 Haiku - cheapest model with vision (5-10x cheaper than GPT-4o!)
        self.model = "claude-3-haiku-20240307"

        logger.info("MealVisionAnalyzer initialized with Claude 3 Haiku (5-10x cheaper!)")

    def analyze_meal_photo(self, user_id: str, image_url: str,
                          user_message: str = "") -> str:
        """
        Analyze a meal photo and log it as a metric

        Args:
            user_id: User's ID
            image_url: URL to the meal photo (Twilio provides this)
            user_message: Optional text caption from user

        Returns:
            SMS response with meal analysis
        """
        try:
            logger.info(f"Analyzing meal photo for user {user_id}: {image_url[:50]}...")

            # Create prompt for Claude Vision
            prompt = self._create_analysis_prompt(user_message)

            # Download and encode image for Claude
            image_data = self._fetch_and_encode_image(image_url)

            # Call Claude 3 Haiku with Vision
            response = self.client.messages.create(
                model=self.model,
                max_tokens=600,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_data['media_type'],
                                    "data": image_data['data']
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            analysis = response.content[0].text

            # Extract structured nutrition data from the analysis
            nutrition_data = self._extract_nutrition_from_analysis(analysis)

            # Log meal event to database
            self._log_meal_event(
                user_id=user_id,
                analysis=analysis,
                nutrition_data=nutrition_data,
                image_url=image_url,
                user_message=user_message
            )

            # Format SMS response
            sms_response = f"📸 Meal Analysis:\n\n{analysis}\n\n✅ Logged to your nutrition tracker!"

            # Truncate if too long for SMS
            if len(sms_response) > 1400:
                # Keep first part and add truncation notice
                sms_response = sms_response[:1380] + "\n\n📱 (Analysis truncated for SMS)"

            logger.info(f"Meal photo analysis completed for user {user_id}: {len(analysis)} chars")
            return sms_response

        except Exception as e:
            logger.error(f"Meal vision analysis failed for user {user_id}: {str(e)}", exc_info=True)
            return f"🤖 Had trouble analyzing your meal photo. Error: {str(e)[:150]}\n\nPlease try again or send a clearer photo."

    def _fetch_and_encode_image(self, image_url: str) -> Dict[str, str]:
        """
        Fetch image from URL and encode to base64 for Claude API

        Args:
            image_url: URL to the image

        Returns:
            Dictionary with 'media_type' and 'data' (base64 encoded)
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            # Determine media type
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            if 'image/' not in content_type:
                content_type = 'image/jpeg'  # Default

            # Encode to base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')

            return {
                'media_type': content_type,
                'data': image_base64
            }

        except Exception as e:
            logger.error(f"Failed to fetch and encode image: {str(e)}")
            raise

    def _create_analysis_prompt(self, user_message: str) -> str:
        """Create the analysis prompt for Claude Vision"""

        base_prompt = """Analyze this meal photo and provide a concise SMS-friendly response:

📋 **Food Items**: List all visible foods with approximate portions
📊 **Nutrition Estimate**:
   - Calories (total kcal)
   - Protein (g)
   - Carbs (g)
   - Fats (g)

💚 **Health Score**: Rate 1-10 with brief reasoning
⏰ **Timing Insight**: When is this meal optimal? (breakfast/lunch/dinner/snack)
💡 **Quick Tip**: One actionable nutrition insight

Format your response to be concise and encouraging. Use emojis for readability.
Keep total response under 800 characters for SMS delivery."""

        if user_message:
            base_prompt += f"\n\nUser's note: \"{user_message}\""

        return base_prompt

    def _extract_nutrition_from_analysis(self, analysis: str) -> Dict[str, Any]:
        """
        Extract structured nutrition data from GPT's text analysis

        Uses regex to parse calories, macros, and health score from the text
        """
        nutrition = {
            'calories': None,
            'protein_g': None,
            'carbs_g': None,
            'fats_g': None,
            'health_score': None
        }

        try:
            # Extract calories (various formats: "500 calories", "500 kcal", "500cal")
            cal_match = re.search(r'(\d+)\s*(?:calories|cal|kcal)', analysis, re.IGNORECASE)
            if cal_match:
                nutrition['calories'] = int(cal_match.group(1))

            # Extract protein (formats: "30g protein", "30 g protein", "protein: 30g")
            protein_match = re.search(r'(?:protein[:\s]+)?(\d+)\s*g?\s*(?:protein)?', analysis, re.IGNORECASE)
            if protein_match:
                nutrition['protein_g'] = int(protein_match.group(1))

            # Extract carbs
            carbs_match = re.search(r'(?:carbs?[:\s]+)?(\d+)\s*g?\s*(?:carbs?)?', analysis, re.IGNORECASE)
            if carbs_match:
                nutrition['carbs_g'] = int(carbs_match.group(1))

            # Extract fats
            fats_match = re.search(r'(?:fats?[:\s]+)?(\d+)\s*g?\s*(?:fats?)?', analysis, re.IGNORECASE)
            if fats_match:
                nutrition['fats_g'] = int(fats_match.group(1))

            # Extract health score (formats: "8/10", "Score: 8", "Health: 8")
            score_match = re.search(r'(?:score|health)[:\s]+(\d+)(?:/10)?', analysis, re.IGNORECASE)
            if score_match:
                nutrition['health_score'] = int(score_match.group(1))

            logger.debug(f"Extracted nutrition: {nutrition}")

        except Exception as e:
            logger.warning(f"Error extracting nutrition data: {str(e)}")

        return nutrition

    def _log_meal_event(self, user_id: str, analysis: str,
                       nutrition_data: Dict[str, Any], image_url: str,
                       user_message: str = ""):
        """Log meal as a metric in the database"""
        try:
            # Use calories as the primary value (or 0 if not detected)
            calorie_value = nutrition_data.get('calories', 0)

            # Create meal metric
            meal_metric = Metric(
                user_id=user_id,
                metric_type='meal_photo',  # New metric type
                value=float(calorie_value) if calorie_value else 0.0,
                unit='kcal',
                timestamp=datetime.utcnow(),
                source='sms_photo',
                meta_data={
                    'analysis': analysis[:1000],  # Truncate for storage
                    'image_url': image_url,
                    'nutrition': nutrition_data,
                    'user_note': user_message,
                    'logged_via': 'claude_3_haiku_vision',
                    'model': self.model,
                    'timestamp_logged': datetime.utcnow().isoformat()
                }
            )

            db.session.add(meal_metric)
            db.session.commit()

            logger.info(f"Meal photo logged for user {user_id} - {calorie_value} kcal")

        except Exception as e:
            logger.error(f"Failed to log meal event for user {user_id}: {str(e)}", exc_info=True)
            # Don't raise - we still want to send the analysis even if logging fails
            db.session.rollback()

    def analyze_multiple_photos(self, user_id: str, image_urls: list,
                                user_message: str = "") -> str:
        """
        Analyze multiple meal photos (e.g., different angles or dishes)

        Args:
            user_id: User's ID
            image_urls: List of image URLs
            user_message: Optional caption

        Returns:
            Combined SMS response
        """
        if len(image_urls) == 1:
            return self.analyze_meal_photo(user_id, image_urls[0], user_message)

        try:
            logger.info(f"Analyzing {len(image_urls)} meal photos for user {user_id}")

            # Create multi-image prompt
            prompt = f"""Analyze these {len(image_urls)} photos of the same meal (different angles or dishes).
Provide a single combined analysis:

📋 **All Food Items**: Complete list from all photos
📊 **Total Nutrition**: Combined calories and macros
💚 **Health Score**: Overall meal rating (1-10)
💡 **Key Insight**: One actionable tip

Keep response under 900 characters."""

            if user_message:
                prompt += f"\n\nUser's note: \"{user_message}\""

            # Build content array with multiple images + text for Claude
            content = []

            # Add images first (Claude prefers images before text)
            for url in image_urls[:3]:  # Limit to 3 images max (cost control)
                image_data = self._fetch_and_encode_image(url)
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_data['media_type'],
                        "data": image_data['data']
                    }
                })

            # Add text prompt
            content.append({"type": "text", "text": prompt})

            # Call Claude 3 Haiku with multiple images
            response = self.client.messages.create(
                model=self.model,
                max_tokens=700,
                temperature=0.7,
                messages=[{"role": "user", "content": content}]
            )

            analysis = response.content[0].text
            nutrition_data = self._extract_nutrition_from_analysis(analysis)

            # Log as single meal event with all image URLs
            self._log_multi_photo_meal(user_id, analysis, nutrition_data, image_urls, user_message)

            sms_response = f"📸 Multi-Photo Meal Analysis ({len(image_urls)} photos):\n\n{analysis}\n\n✅ Logged!"

            if len(sms_response) > 1400:
                sms_response = sms_response[:1380] + "\n\n📱 (Truncated for SMS)"

            return sms_response

        except Exception as e:
            logger.error(f"Multi-photo analysis failed: {str(e)}")
            # Fallback: analyze first photo only
            return self.analyze_meal_photo(user_id, image_urls[0], user_message)

    def _log_multi_photo_meal(self, user_id: str, analysis: str,
                             nutrition_data: Dict[str, Any],
                             image_urls: list, user_message: str):
        """Log multi-photo meal event"""
        try:
            calorie_value = nutrition_data.get('calories', 0)

            meal_metric = Metric(
                user_id=user_id,
                metric_type='meal_photo',
                value=float(calorie_value) if calorie_value else 0.0,
                unit='kcal',
                timestamp=datetime.utcnow(),
                source='sms_photo_multi',
                meta_data={
                    'analysis': analysis[:1000],
                    'image_urls': image_urls,  # Store all URLs
                    'num_photos': len(image_urls),
                    'nutrition': nutrition_data,
                    'user_note': user_message,
                    'logged_via': 'claude_3_haiku_vision_multi',
                    'model': self.model,
                    'timestamp_logged': datetime.utcnow().isoformat()
                }
            )

            db.session.add(meal_metric)
            db.session.commit()

            logger.info(f"Multi-photo meal logged for user {user_id} - {len(image_urls)} photos")

        except Exception as e:
            logger.error(f"Failed to log multi-photo meal: {str(e)}")
            db.session.rollback()

    def get_recent_meals(self, user_id: str, days_back: int = 7) -> list:
        """
        Get recent meal photos with analysis

        Args:
            user_id: User's ID
            days_back: How many days back to look

        Returns:
            List of meal dictionaries
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_back)

            meal_metrics = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type == 'meal_photo',
                Metric.timestamp >= cutoff_time
            ).order_by(Metric.timestamp.desc()).all()

            meals = []
            for metric in meal_metrics:
                meals.append({
                    'timestamp': metric.timestamp.isoformat(),
                    'calories': metric.value,
                    'analysis': metric.meta_data.get('analysis', ''),
                    'nutrition': metric.meta_data.get('nutrition', {}),
                    'user_note': metric.meta_data.get('user_note', ''),
                    'image_url': metric.meta_data.get('image_url', '')
                })

            return meals

        except Exception as e:
            logger.error(f"Failed to get recent meals: {str(e)}")
            return []

    def get_nutrition_summary(self, user_id: str, days_back: int = 7) -> Dict[str, Any]:
        """
        Get nutrition summary from meal photos

        Args:
            user_id: User's ID
            days_back: How many days to summarize

        Returns:
            Dictionary with nutrition totals and averages
        """
        try:
            from datetime import timedelta

            meals = self.get_recent_meals(user_id, days_back)

            if not meals:
                return {'error': 'No meal data available'}

            total_calories = sum(m['calories'] for m in meals if m['calories'])
            total_protein = sum(m['nutrition'].get('protein_g', 0) for m in meals)
            total_carbs = sum(m['nutrition'].get('carbs_g', 0) for m in meals)
            total_fats = sum(m['nutrition'].get('fats_g', 0) for m in meals)

            num_meals = len(meals)

            return {
                'days_analyzed': days_back,
                'total_meals_logged': num_meals,
                'total_calories': total_calories,
                'avg_calories_per_meal': round(total_calories / num_meals, 1) if num_meals else 0,
                'total_protein_g': total_protein,
                'total_carbs_g': total_carbs,
                'total_fats_g': total_fats,
                'avg_daily_calories': round(total_calories / days_back, 1),
                'meals_per_day': round(num_meals / days_back, 1)
            }

        except Exception as e:
            logger.error(f"Failed to get nutrition summary: {str(e)}")
            return {'error': str(e)}


# Utility function for testing
def test_vision_analyzer():
    """Test the meal vision analyzer with a sample image URL"""
    analyzer = MealVisionAnalyzer()

    # Use a public sample food image for testing
    test_image_url = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400"

    result = analyzer.analyze_meal_photo(
        user_id="test_user",
        image_url=test_image_url,
        user_message="breakfast today"
    )

    print("Test Result:")
    print(result)

    return result


if __name__ == "__main__":
    # Allow testing from command line
    test_vision_analyzer()
