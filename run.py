"""Convenient root launcher for the Centralized Logging System.

Allows running `py run.py` or `python run.py` directly from the workspace root.
"""

import os
import sys
from pathlib import Path

# Add project folder to sys.path
PROJECT_DIR = Path(__file__).resolve().parent / "centralized-logging-system"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.chdir(PROJECT_DIR)

from app import main

if __name__ == "__main__":
    main()
