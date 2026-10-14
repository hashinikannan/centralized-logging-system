"""Integration tests for the Flask Web Dashboard and REST API endpoints."""

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from app import create_app


class TestDashboardAPI(TestCase):
    """Test Flask routes, APIs, simulation endpoints, and export."""

    def setUp(self) -> None:
        """Create a test application instance with an isolated temporary log directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temp_dir.name)

        # Seed sample log entries
        login_log = self.log_dir / "login_service.log"
        login_log.write_text(
            "2026-10-14 10:00:01 | INFO    | login_service | User logged in user_id=seed_user\n"
            "2026-10-14 10:00:02 | WARNING | login_service | Invalid credentials attempt user_id=intruder\n",
            encoding="utf-8",
        )

        payment_log = self.log_dir / "payment_service.log"
        payment_log.write_text(
            "2026-10-14 10:00:03 | INFO    | payment_service | Payment processed successfully txn_id=TXN-SEED\n"
            "2026-10-14 10:00:04 | ERROR   | payment_service | Payment gateway timeout after 5000ms: gateway=StripeSimulator\n",
            encoding="utf-8",
        )

        self.app = create_app({"TESTING": True, "LOG_DIR": self.log_dir})
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_index_page(self) -> None:
        """GET / should render the dashboard HTML."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Centralized Logging System", res.data)
        self.assertIn(b"Observability Dashboard", res.data)

    def test_get_stats(self) -> None:
        """GET /api/stats should return aggregated log statistics."""
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["stats"]["total"], 4)
        self.assertEqual(data["stats"]["info"], 2)
        self.assertEqual(data["stats"]["warning"], 1)
        self.assertEqual(data["stats"]["error"], 1)

    def test_get_logs_all(self) -> None:
        """GET /api/logs should return all logs."""
        res = self.client.get("/api/logs")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 4)

    def test_get_logs_filtered_service(self) -> None:
        """GET /api/logs?service=payment_service should filter by service."""
        res = self.client.get("/api/logs?service=payment_service")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], 2)
        self.assertTrue(all(l["service"] == "payment_service" for l in data["logs"]))

    def test_get_logs_filtered_severity(self) -> None:
        """GET /api/logs?severity=ERROR should filter by severity."""
        res = self.client.get("/api/logs?severity=ERROR")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["logs"][0]["severity"], "ERROR")

    def test_get_logs_search(self) -> None:
        """GET /api/logs?search=timeout should return matching logs."""
        res = self.client.get("/api/logs?search=timeout")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], 1)
        self.assertIn("timeout", data["logs"][0]["message"].lower())

    def test_get_logs_invalid_severity(self) -> None:
        """GET /api/logs with an invalid severity should return 400 Bad Request."""
        res = self.client.get("/api/logs?severity=UNKNOWN_LEVEL")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["status"], "error")

    def test_generate_event(self) -> None:
        """POST /api/generate should simulate service events."""
        res = self.client.post(
            "/api/generate",
            data=json.dumps({"service": "login_service", "event_type": "success"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["service"], "login_service")

    def test_generate_invalid_service(self) -> None:
        """POST /api/generate with invalid service should return 400."""
        res = self.client.post(
            "/api/generate",
            data=json.dumps({"service": "non_existent_service"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_clear_logs(self) -> None:
        """POST /api/clear should empty log files."""
        res = self.client.post("/api/clear")
        self.assertEqual(res.status_code, 200)

        # Check stats after clear
        stats_res = self.client.get("/api/stats")
        self.assertEqual(stats_res.get_json()["stats"]["total"], 0)

    def test_export_csv(self) -> None:
        """GET /api/export?format=csv should return a valid CSV file."""
        res = self.client.get("/api/export?format=csv")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/csv")
        self.assertIn(b"Timestamp,Severity,Service,Message,Source File", res.data)

    def test_complete_hackathon_demo_scenario(self) -> None:
        """End-to-end test of the complete hackathon scenario:
        1. Generate a payment gateway timeout.
        2. Open dashboard logs.
        3. Filter for Payment Service.
        4. Select ERROR severity.
        5. Search for 'timeout'.
        6. Identify the matching error and its timestamp.
        """
        # Step 1: Generate Payment Gateway Timeout
        gen_res = self.client.post(
            "/api/generate",
            data=json.dumps({
                "service": "payment_service",
                "event_type": "timeout",
                "gateway": "StripeSimulator",
                "timeout_ms": 5000,
                "user_id": "hackathon_judge_demo",
            }),
            content_type="application/json",
        )
        self.assertEqual(gen_res.status_code, 200)

        # Step 2-5: Query with filters: service=payment_service, severity=ERROR, search=timeout
        query_res = self.client.get("/api/logs?service=payment_service&severity=ERROR&search=timeout")
        self.assertEqual(query_res.status_code, 200)
        query_data = query_res.get_json()

        # Step 6: Identify matching error and timestamp
        self.assertTrue(query_data["count"] >= 1)
        matched_log = query_data["logs"][0]

        self.assertEqual(matched_log["service"], "payment_service")
        self.assertEqual(matched_log["severity"], "ERROR")
        self.assertIn("timeout", matched_log["message"].lower())
        self.assertIsNotNone(matched_log["timestamp"])
        self.assertTrue(len(matched_log["timestamp"]) > 0)
