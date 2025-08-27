"""
WSGI configuration for PythonAnywhere deployment
"""

import sys
import os
from dotenv import load_dotenv

# Add your project directory to the Python path
project_home = '/home/yourusername/ultrahuman-agent'  # Update with your username
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables
load_dotenv(os.path.join(project_home, '.env'))

from app import create_app

# Create the Flask application
application = create_app()

if __name__ == "__main__":
    application.run()