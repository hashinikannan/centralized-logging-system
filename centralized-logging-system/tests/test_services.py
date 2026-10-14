"""Unit tests for Login Service and Payment Service log emission."""

from decimal import Decimal
from unittest import TestCase

from src.login_service import (
    record_login,
    simulate_auth_service_error,
    simulate_event as simulate_login_event,
    simulate_invalid_credentials,
    simulate_login_failure,
    simulate_login_success,
    simulate_suspicious_warning,
)
from src.payment_service import (
    process_payment,
    simulate_event as simulate_payment_event,
    simulate_gateway_timeout,
    simulate_payment_failure,
    simulate_payment_success,
    simulate_processing_error,
)


class TestLoginService(TestCase):
    """Test login service behaviors and log generation."""

    def test_record_login_success(self) -> None:
        """Successful login returns True."""
        result = record_login("test_user_ok", authenticated=True)
        self.assertTrue(result)

    def test_record_login_failure(self) -> None:
        """Failed login returns False."""
        result = record_login("test_user_fail", authenticated=False)
        self.assertFalse(result)

    def test_record_login_missing_user(self) -> None:
        """Missing user ID triggers warning and returns False."""
        result = record_login("   ", authenticated=True)
        self.assertFalse(result)

    def test_simulate_login_events(self) -> None:
        """Test structured event generators for login service."""
        success_res = simulate_login_success("alice")
        self.assertEqual(success_res["status"], "success")
        self.assertEqual(success_res["severity"], "INFO")

        fail_res = simulate_login_failure("bob", "Incorrect password")
        self.assertEqual(fail_res["status"], "failure")
        self.assertEqual(fail_res["severity"], "WARNING")

        creds_res = simulate_invalid_credentials("charlie")
        self.assertEqual(creds_res["status"], "warning")
        self.assertEqual(creds_res["severity"], "WARNING")

        warn_res = simulate_suspicious_warning("dave", attempts=6)
        self.assertEqual(warn_res["status"], "warning")
        self.assertEqual(warn_res["severity"], "WARNING")

        err_res = simulate_auth_service_error("eve", "Directory timeout")
        self.assertEqual(err_res["status"], "error")
        self.assertEqual(err_res["severity"], "ERROR")

    def test_simulate_login_dispatch(self) -> None:
        """Test generic event dispatcher for login service."""
        res = simulate_login_event("invalid_credentials", user_id="tester")
        self.assertEqual(res["severity"], "WARNING")


class TestPaymentService(TestCase):
    """Test payment service behaviors and log generation."""

    def test_process_payment_valid(self) -> None:
        """Valid payment returns a transaction ID."""
        txn = process_payment("49.99", "USD", "user_1")
        self.assertIsNotNone(txn)
        self.assertTrue(txn.startswith("TXN-"))

    def test_process_payment_invalid_amount(self) -> None:
        """Negative or non-numeric amount is rejected."""
        self.assertIsNone(process_payment("-10.00", "USD"))
        self.assertIsNone(process_payment("not-a-number", "USD"))

    def test_process_payment_invalid_currency(self) -> None:
        """Non-3-letter currency is rejected."""
        self.assertIsNone(process_payment("10.00", "USDD"))

    def test_simulate_gateway_timeout(self) -> None:
        """Gateway timeout must generate an ERROR severity event with 'timeout'."""
        res = simulate_gateway_timeout(gateway="StripeSimulator", timeout_ms=5000, user_id="cust_test")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["severity"], "ERROR")
        self.assertEqual(res["service"], "payment_service")
        self.assertIn("timeout", res["message"].lower())
        self.assertIn("StripeSimulator", res["message"])

    def test_simulate_processing_error(self) -> None:
        """Processing error must generate an ERROR severity event."""
        res = simulate_processing_error("ERR_ROLLBACK", "DB Rollback")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["severity"], "ERROR")
        self.assertIn("ERR_ROLLBACK", res["message"])

    def test_simulate_payment_dispatch(self) -> None:
        """Test generic event dispatcher for payment service."""
        res = simulate_payment_event("timeout", gateway="PayPalMock", timeout_ms=4500)
        self.assertEqual(res["severity"], "ERROR")
        self.assertIn("timeout", res["message"].lower())
