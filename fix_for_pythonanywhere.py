#!/usr/bin/env python3.11
"""
Fix code for PythonAnywhere deployment
Run this after uploading the original code
"""

import os
import re

def fix_celery_imports():
    """Remove Celery imports and decorators from task files"""

    files_to_fix = [
        'tasks/daily_report.py',
        'tasks/data_ingestion.py',
        'tasks/maintenance.py'
    ]

    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            continue

        print(f"Fixing {file_path}...")

        with open(file_path, 'r') as f:
            content = f.read()

        # Remove Celery imports
        content = re.sub(r'from celery import.*\n', '', content)
        content = re.sub(r'from tasks\.celery_app import.*\n', '', content)

        # Remove Celery decorators
        content = re.sub(r'@celery_app\.task.*\n', '', content)
        content = re.sub(r'@log_task_execution\n', '', content)
        content = re.sub(r'@retry_on_failure.*\n', '', content)

        # Fix function signatures (remove 'self' parameter)
        content = re.sub(r'def (\w+)\(self, ', r'def \1(', content)

        # Remove Celery retry logic
        content = re.sub(r'if current_task:.*?\n.*?current_task\.retry.*?\n', '', content, flags=re.DOTALL)

        with open(file_path, 'w') as f:
            f.write(content)

        print(f"✅ Fixed {file_path}")

def add_missing_imports():
    """Add missing imports to files"""

    # Fix metrics_service.py
    metrics_file = 'services/metrics_service.py'
    if os.path.exists(metrics_file):
        with open(metrics_file, 'r') as f:
            content = f.read()

        if 'import os' not in content:
            content = 'import os\n' + content

        with open(metrics_file, 'w') as f:
            f.write(content)

        print("✅ Added missing imports to metrics_service.py")

def fix_app_config():
    """Fix app configuration for PythonAnywhere"""

    app_init_file = 'app/__init__.py'
    if os.path.exists(app_init_file):
        with open(app_init_file, 'r') as f:
            content = f.read()

        # Replace postgres:// with postgresql://
        if 'postgres://' in content and 'postgresql://' not in content:
            content = content.replace(
                "SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL',",
                """# PythonAnywhere-specific database URL handling
        database_url = os.getenv('DATABASE_URL')
        if database_url and database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)

        app.config.update(
            # Database
            SQLALCHEMY_DATABASE_URI=database_url or"""
            )

        with open(app_init_file, 'w') as f:
            f.write(content)

        print("✅ Fixed app configuration")

def create_simple_cache():
    """Create simplified cache for PythonAnywhere"""

    cache_file = 'utils/cache.py'
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            content = f.read()

        # Add fallback cache logic
        fallback_cache = '''
    def _fallback_operation(self, operation, *args, **kwargs):
        """Fallback to in-memory operations when Redis unavailable"""
        if not hasattr(self, '_memory_cache'):
            self._memory_cache = {}

        if operation == 'get':
            return self._memory_cache.get(args[0])
        elif operation == 'set':
            self._memory_cache[args[0]] = args[1]
            return True
        elif operation == 'delete':
            return self._memory_cache.pop(args[0], None) is not None
        return None
'''

        # Insert fallback logic
        if '_fallback_operation' not in content:
            # Find the class definition and add fallback
            class_match = re.search(r'class CacheManager:', content)
            if class_match:
                insert_pos = content.find('\n', class_match.end())
                content = content[:insert_pos] + fallback_cache + content[insert_pos:]

        with open(cache_file, 'w') as f:
            f.write(content)

        print("✅ Added cache fallback logic")

def main():
    """Run all fixes"""
    print("🔧 Fixing code for PythonAnywhere deployment...")

    try:
        fix_celery_imports()
        add_missing_imports()
        fix_app_config()
        create_simple_cache()

        print("\n✅ All fixes applied successfully!")
        print("\n📋 Next steps:")
        print("1. Install dependencies: pip3.11 install --user -r requirements.txt")
        print("2. Run setup: python3.11 setup_pythonanywhere.py")
        print("3. Configure web app to use wsgi.py")
        print("4. Set up scheduled tasks")

    except Exception as e:
        print(f"❌ Error applying fixes: {str(e)}")

if __name__ == "__main__":
    main()