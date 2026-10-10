"""
GenBuddy WSGI entry point for production deployment.

Usage with waitress (recommended):
    pip install waitress
    waitress-serve --host=0.0.0.0 --port=5000 wsgi:application

Usage with gunicorn (Linux):
    pip install gunicorn
    gunicorn -w 4 -b 0.0.0.0:5000 wsgi:application

Set PUBLIC_DEMO_MODE=1 to enable read-only public mode.
"""

import os
os.environ.setdefault("PUBLIC_DEMO_MODE", "1")

from app import app as application
