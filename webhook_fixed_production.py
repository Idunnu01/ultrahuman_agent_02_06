# FIXED WEBHOOK ROUTE FOR PRODUCTION - PROPER SMS ERROR HANDLING
# Replace the existing webhook route in your PythonAnywhere app/__init__.py with this:

webhook_route_fixed = '''
    # Twilio SMS webhook - PRODUCTION VERSION WITH PROPER ERROR HANDLING
    @app.route('/webhook/sms', methods=['POST'])
    def sms_webhook():
        try:
            from services.metrics_service import MetricsService
            from app.models import User

            sms_data = {
                'From': request.form.get('From'),
                'Body': request.form.get('Body'),
                'MessageSid': request.form.get('MessageSid'),
                'AccountSid': request.form.get('AccountSid')
            }
            app.logger.info(f"SMS received from {sms_data['From']}: {sms_data['Body'][:50]}...")

            # Find user by phone number
            user = User.query.filter_by(phone_number=sms_data['From']).first()

            if not user:
                app.logger.warning(f"No user found for phone number: {sms_data['From']}")
                return '<Response></Response>', 200, {'Content-Type': 'text/xml'}

            # Process the SMS message
            try:
                metrics_service = MetricsService()
                result = metrics_service.process_sms_input(user.id, sms_data['Body'])

                if result.get('success'):
                    insights = (result.get('immediate_insights') or {}).get('insights') or []
                    if insights:
                        response_text = (insights[0].get('message', '') or '').strip() or "✅ Message processed successfully!"
                    elif result.get('events_processed', 0) > 0:
                        response_text = f"✅ Logged {result['events_processed']} event(s). Thanks!"
                    else:
                        response_text = "📊 Message processed successfully!"
                else:
                    response_text = "👍 Message received, processing..."

            except Exception as e:
                app.logger.error(f"Metrics processing failed: {str(e)}")
                response_text = "📊 Thanks for your message! Data is being processed."

            # CRITICAL FIX: Send SMS with proper error handling
            try:
                from services.sms_service import SMSService
                sms_service = SMSService()

                # Check the SMS service response properly
                sms_result = sms_service.send_immediate_response(user.id, sms_data['From'], response_text)

                if sms_result.get('success'):
                    app.logger.info(f"✅ SMS sent successfully to {sms_data['From']}: {response_text}")
                else:
                    # SMS FAILED - Log the real error
                    error = sms_result.get('error', 'Unknown SMS error')
                    app.logger.error(f"❌ SMS FAILED to {sms_data['From']}: {error}")

                    # Handle different error types
                    if 'rate limit' in error.lower() or 'daily' in error.lower():
                        app.logger.warning(f"⚠️  Rate limit hit for user {user.id} - SMS blocked")
                    elif 'twilio' in error.lower():
                        app.logger.error(f"🚨 Twilio API error: {error}")
                    else:
                        app.logger.error(f"🔧 SMS service error: {error}")

            except Exception as e:
                app.logger.error(f"💥 SMS service exception: {str(e)}")

            return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>', 200, {'Content-Type': 'text/xml'}

        except Exception as e:
            app.logger.error(f"💥 SMS webhook error: {str(e)}")
            return '<Response></Response>', 200, {'Content-Type': 'text/xml'}
'''

print("🔧 FIXED WEBHOOK CODE FOR PRODUCTION")
print("=" * 60)
print("Copy this code to replace your webhook route in PythonAnywhere:")
print(webhook_route_fixed)