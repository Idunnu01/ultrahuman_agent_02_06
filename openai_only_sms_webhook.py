
@main_bp.route('/webhook/sms', methods=['POST'])
def sms_webhook():
    """SMS webhook - OPENAI ONLY, NO FALLBACKS"""
    try:
        # Get SMS data from Twilio
        body = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')

        if not body:
            return "Empty message", 400

        logger.info(f"Received SMS from {from_number}: {body[:50]}...")

        # Get user by phone number
        user = User.query.filter_by(phone_number=from_number).first()
        if not user:
            sms_service = SMSService()
            sms_service.send_sms(user_id="unknown", phone_number=from_number,
                               message="❌ User not found. Please register first.",
                               message_type='response')
            return "User not found", 400

        # OPENAI-ONLY Processing
        logger.info(f"Processing OpenAI ChatGPT message from user {user.id}: {body[:50]}...")

        try:
            # Initialize OpenAI LLM Analyzer
            from services.llm_chat_analyzer_pa import LLMChatAnalyzer
            llm_analyzer = LLMChatAnalyzer()

            # Get ChatGPT response
            response = llm_analyzer.analyze_message(body, user.id)

            if not response:
                response = "🤖 I'm having trouble processing your request. Please try rephrasing your question."

            # Handle SMS character limits
            if len(response) > 1600:
                lines = response.split('\n')
                summary_lines = lines[:15]
                if len(lines) > 15:
                    summary_lines.append("📱 Response truncated for SMS")
                response = '\n'.join(summary_lines)

            # Send OpenAI ChatGPT response
            sms_service = SMSService()
            sms_service.send_immediate_response(user.id, from_number, response)

            logger.info(f"OpenAI ChatGPT response sent to user {user.id}: {len(response)} chars")
            return "OpenAI ChatGPT response sent", 200

        except Exception as llm_error:
            # OpenAI failed - send error message (NO FALLBACK)
            logger.error(f"OpenAI ChatGPT failed for user {user.id}: {str(llm_error)}")

            error_response = f"""🤖 ChatGPT is temporarily unavailable.

Error: {str(llm_error)[:100]}

Please try again in a moment. Your request: "{body[:50]}..." """

            sms_service = SMSService()
            sms_service.send_immediate_response(user.id, from_number, error_response)

            return f"OpenAI error reported to user", 500

    except Exception as e:
        logger.error(f"SMS webhook critical error: {str(e)}")
        return "Critical SMS error", 500
