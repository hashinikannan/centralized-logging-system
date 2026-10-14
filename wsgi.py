"""WSGI entrypoint for Cloud Deployment (Render, Railway, Heroku, etc.).

Exposes the Flask `app` object at the root level so WSGI servers like Gunicorn
can run `gunicorn wsgi:app`.
"""

import os
import sys
from pathlib import Path

# Add project subdirectory to sys.path
PROJECT_DIR = Path(__file__).resolve().parent / "centralized-logging-system"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Ensure working directory is set to centralized-logging-system
os.chdir(PROJECT_DIR)

from app import app  # noqa: E402

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port)
