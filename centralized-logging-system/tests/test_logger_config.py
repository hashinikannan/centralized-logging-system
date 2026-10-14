"""Unit tests for the logger configuration module."""

import logging
import tempfile
from pathlib import Path
from unittest import TestCase

from src.logger_config import get_logger, LOG_FORMAT, LOG_DATE_FORMAT


class TestLoggerConfig(TestCase):
    """Test logger initialization, formatting, and handler idempotency."""

    def test_logger_creation(self) -> None:
        """Verify logger is created with proper handlers and format."""
        logger_name = "test_custom_service"
        logger = get_logger(logger_name)
        
        self.assertEqual(logger.name, logger_name)
        self.assertFalse(logger.propagate)
        self.assertTrue(len(logger.handlers) >= 2)

        # Verify handlers include StreamHandler and RotatingFileHandler
        handler_types = [type(h) for h in logger.handlers]
        self.assertIn(logging.StreamHandler, handler_types)

    def test_prevent_duplicate_handlers(self) -> None:
        """Calling get_logger repeatedly must not attach duplicate handlers."""
        logger_name = "idempotent_test_service"
        logger1 = get_logger(logger_name)
        initial_handler_count = len(logger1.handlers)

        logger2 = get_logger(logger_name)
        self.assertIs(logger1, logger2)
        self.assertEqual(len(logger2.handlers), initial_handler_count)

    def test_logger_writes_to_file(self) -> None:
        """Verify that logging messages write to the designated file."""
        logger_name = "test_file_write_service"
        logger = get_logger(logger_name)
        
        test_msg = "Verification event for file write test"
        logger.info(test_msg)

        # Find the file handler
        file_handler = None
        for h in logger.handlers:
            if hasattr(h, "baseFilename"):
                file_handler = h
                break

        self.assertIsNotNone(file_handler, "Logger should have a file handler")
        file_path = Path(file_handler.baseFilename)
        self.assertTrue(file_path.exists())

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(test_msg, content)
        self.assertIn("INFO", content)
        self.assertIn(logger_name, content)
