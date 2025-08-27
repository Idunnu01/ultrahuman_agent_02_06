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

if __name__ == '__main__':
    # Development server
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )