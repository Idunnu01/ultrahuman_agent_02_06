"""
Debug fix for webhook - add logging to SMS webhook to see what's failing
"""

def add_debug_logging():
    """Adds debug logging to the webhook to diagnose the exact failure point"""

    webhook_debug_code = '''
# In your SMS webhook in app/__init__.py around line 216, replace the processing line with:

try:
    app.logger.info(f"Processing SMS for user {user.id} with message: {sms_data['Body']}")
    result = metrics_service.process_sms_input_with_context(user.id, sms_data['Body'])
    app.logger.info(f"SMS processing result: {result}")

    if result.get('success'):
        app.logger.info("SMS processing was successful")
        # ... rest of success logic
    else:
        app.logger.error(f"SMS processing failed: {result.get('error', 'Unknown error')}")
        # ... rest of error logic

except Exception as e:
    app.logger.error(f"Exception in SMS processing: {str(e)}")
    app.logger.error(f"Exception type: {type(e)}")
    import traceback
    app.logger.error(f"Traceback: {traceback.format_exc()}")
    # Return error response
'''

    print("🔧 WEBHOOK DEBUG FIX")
    print("="*50)
    print("Add this enhanced error logging to your SMS webhook:")
    print(webhook_debug_code)
    print("\nAfter adding this logging:")
    print("1. Deploy to PythonAnywhere")
    print("2. Send 'supplement magnesium 400mg at 10pm' via SMS")
    print("3. Check the error log in PythonAnywhere console")
    print("4. You'll see exactly where it's failing!")

if __name__ == '__main__':
    add_debug_logging()