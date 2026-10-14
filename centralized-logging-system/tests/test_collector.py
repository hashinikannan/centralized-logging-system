"""Unit tests for the centralized LogCollector engine."""

import tempfile
from pathlib import Path
from unittest import TestCase

from src.log_collector import LogCollector, LogEntry


class TestLogCollector(TestCase):
    """Test log line parsing, aggregation, filtering, and stats."""

    def setUp(self) -> None:
        """Create a temporary directory for isolated log testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temp_dir.name)
        self.collector = LogCollector(log_dir=self.log_dir)

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_parse_pipe_format_line(self) -> None:
        """Verify parsing of standard pipe-delimited log lines."""
        raw_line = "2026-10-14 10:30:15 | ERROR   | payment_service | Payment gateway timeout after 5000ms"
        entry = self.collector.parse_line(raw_line, "payment_service.log", 1)

        self.assertIsNotNone(entry)
        self.assertEqual(entry.timestamp, "2026-10-14 10:30:15")
        self.assertEqual(entry.severity, "ERROR")
        self.assertEqual(entry.service, "payment_service")
        self.assertEqual(entry.message, "Payment gateway timeout after 5000ms")
        self.assertEqual(entry.source_file, "payment_service.log")

    def test_parse_legacy_format_line(self) -> None:
        """Verify parsing of bracket format lines."""
        raw_line = "2026-10-14T10:09:49+0530 INFO [login_service] Login succeeded for user_id=demo-user"
        entry = self.collector.parse_line(raw_line, "application.log", 1)

        self.assertIsNotNone(entry)
        self.assertEqual(entry.severity, "INFO")
        self.assertEqual(entry.service, "login_service")
        self.assertIn("Login succeeded", entry.message)

    def test_missing_directory_graceful(self) -> None:
        """Missing log directory should return empty list and zero stats without error."""
        non_existent_dir = self.log_dir / "does_not_exist"
        collector = LogCollector(log_dir=non_existent_dir)

        logs = collector.read_all_logs()
        self.assertEqual(logs, [])

        stats = collector.get_statistics()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["info"], 0)
        self.assertEqual(stats["warning"], 0)
        self.assertEqual(stats["error"], 0)

    def test_filtering_and_search(self) -> None:
        """Test service, severity, and search filtering."""
        # Create a sample log file
        log_file = self.log_dir / "services.log"
        content = (
            "2026-10-14 10:00:01 | INFO    | login_service | User logged in user_id=alex\n"
            "2026-10-14 10:00:02 | WARNING | login_service | Invalid credentials attempt user_id=unknown\n"
            "2026-10-14 10:00:03 | INFO    | payment_service | Payment processed successfully txn_id=TXN-101\n"
            "2026-10-14 10:00:04 | ERROR   | payment_service | Payment gateway timeout after 5000ms: gateway=StripeSimulator\n"
            "2026-10-14 10:00:05 | ERROR   | payment_service | Transaction processing error: ledger rollback\n"
        )
        log_file.write_text(content, encoding="utf-8")

        # 1. Total count
        all_logs = self.collector.read_all_logs()
        self.assertEqual(len(all_logs), 5)

        # 2. Filter by service
        payment_logs = self.collector.filter_logs(service="payment_service")
        self.assertEqual(len(payment_logs), 3)
        self.assertTrue(all(l.service == "payment_service" for l in payment_logs))

        login_logs = self.collector.filter_logs(service="login_service")
        self.assertEqual(len(login_logs), 2)

        # 3. Filter by severity
        error_logs = self.collector.filter_logs(severity="ERROR")
        self.assertEqual(len(error_logs), 2)
        self.assertTrue(all(l.severity == "ERROR" for l in error_logs))

        warning_logs = self.collector.filter_logs(severity="WARNING")
        self.assertEqual(len(warning_logs), 1)

        # 4. Search query
        timeout_logs = self.collector.filter_logs(search="timeout")
        self.assertEqual(len(timeout_logs), 1)
        self.assertEqual(timeout_logs[0].severity, "ERROR")
        self.assertIn("timeout", timeout_logs[0].message)

        # 5. Combined filter: Payment Service + ERROR + search "timeout"
        combined = self.collector.filter_logs(
            service="payment_service",
            severity="ERROR",
            search="timeout",
        )
        self.assertEqual(len(combined), 1)
        self.assertEqual(combined[0].service, "payment_service")
        self.assertEqual(combined[0].severity, "ERROR")
        self.assertIn("Payment gateway timeout", combined[0].message)

    def test_statistics_calculation(self) -> None:
        """Verify summary statistics counts."""
        log_file = self.log_dir / "stats_test.log"
        content = (
            "2026-10-14 10:00:01 | INFO    | login_service | Info 1\n"
            "2026-10-14 10:00:02 | INFO    | login_service | Info 2\n"
            "2026-10-14 10:00:03 | WARNING | login_service | Warn 1\n"
            "2026-10-14 10:00:04 | ERROR   | payment_service | Err 1\n"
        )
        log_file.write_text(content, encoding="utf-8")

        stats = self.collector.get_statistics()
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["info"], 2)
        self.assertEqual(stats["warning"], 1)
        self.assertEqual(stats["error"], 1)
        self.assertEqual(stats["by_service"]["login_service"], 3)
        self.assertEqual(stats["by_service"]["payment_service"], 1)

    def test_clear_logs(self) -> None:
        """Verify clear_logs truncates all log files."""
        log_file = self.log_dir / "sample.log"
        log_file.write_text("2026-10-14 10:00:00 | INFO | login_service | Sample", encoding="utf-8")
        self.assertEqual(len(self.collector.read_all_logs()), 1)

        self.collector.clear_logs()
        self.assertEqual(len(self.collector.read_all_logs()), 0)
