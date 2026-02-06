#!/usr/bin/env python3
"""
Ultrahuman Lifestyle Agent - Flask Entry Point
"""

import os
from dotenv import load_dotenv
from app import create_app
from tasks.celery_app import make_celery

# Load environment variables
load_dotenv()

# Create Flask app
app = create_app()

# Initialize Celery
celery = make_celery(app)

# Health check endpoint for Railway
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'service': 'ultrahuman-chatgpt-sms'}, 200

if __name__ == '__main__':
    # Railway-compatible server
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)