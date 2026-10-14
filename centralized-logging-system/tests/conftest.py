"""Pytest configuration and test isolation fixtures."""

import os
import shutil
import tempfile
from pathlib import Path
import pytest

# Set LOG_DIR immediately before test modules are collected or imported
_TEMP_TEST_LOG_DIR = tempfile.mkdtemp(prefix="centralized_logs_test_")
os.environ["LOG_DIR"] = _TEMP_TEST_LOG_DIR


def pytest_sessionfinish(session, exitstatus):
    """Clean up temporary test logs directory after pytest completes."""
    shutil.rmtree(_TEMP_TEST_LOG_DIR, ignore_errors=True)
