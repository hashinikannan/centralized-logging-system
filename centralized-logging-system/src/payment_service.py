"""Payment Service module with centralized logging.

Simulates financial transactions, gateway timeouts, processing failures,
and validation errors.
Logs are written to `logs/payment_service.log`.
"""

from __future__ import annotations

import random
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from src.logger_config import get_logger

# Service logger writes to console and logs/payment_service.log
logger = get_logger("payment_service")


def process_payment(amount: Decimal | float | str, currency: str = "USD", user_id: str = "guest_user") -> str | None:
    """Validate and process a simulated payment safely."""
    try:
        val = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        logger.warning("Payment rejected: invalid amount '%s' for user_id=%s", amount, user_id)
        return None

    if not val.is_finite() or val <= 0:
        logger.warning("Payment rejected: non-positive amount %s for user_id=%s", val, user_id)
        return None

    norm_curr = str(currency).strip().upper()
    if len(norm_curr) != 3 or not norm_curr.isalpha():
        logger.warning("Payment rejected: invalid currency '%s' for user_id=%s", currency, user_id)
        return None

    txn_id = f"TXN-{uuid4().hex[:10].upper()}"
    logger.info(
        "Payment processed successfully: txn_id=%s amount=%.2f %s user_id=%s status=SETTLED",
        txn_id,
        float(val),
        norm_curr,
        user_id,
    )
    return txn_id


def simulate_payment_success(
    amount: float = 49.99,
    currency: str = "USD",
    user_id: str = "customer_884",
) -> dict[str, Any]:
    """Simulate a successful checkout transaction."""
    txn_id = f"TXN-{uuid4().hex[:10].upper()}"
    logger.info(
        "Payment processed successfully: txn_id=%s amount=%.2f %s user_id=%s method=CREDIT_CARD status=SETTLED",
        txn_id,
        amount,
        currency,
        user_id,
    )
    return {
        "status": "success",
        "service": "payment_service",
        "severity": "INFO",
        "txn_id": txn_id,
        "message": f"Payment of {amount:.2f} {currency} succeeded (txn: {txn_id})",
    }


def simulate_payment_failure(
    amount: float = 120.00,
    currency: str = "USD",
    user_id: str = "customer_205",
    reason: str = "Insufficient balance in account",
) -> dict[str, Any]:
    """Simulate a declined or failed payment transaction."""
    txn_id = f"TXN-{uuid4().hex[:10].upper()}"
    logger.warning(
        "Payment declined: txn_id=%s amount=%.2f %s user_id=%s reason='%s'",
        txn_id,
        amount,
        currency,
        user_id,
        reason,
    )
    return {
        "status": "declined",
        "service": "payment_service",
        "severity": "WARNING",
        "txn_id": txn_id,
        "message": f"Payment declined: {reason}",
    }


def simulate_gateway_timeout(
    gateway: str = "StripeSimulator",
    timeout_ms: int = 5000,
    user_id: str = "customer_912",
) -> dict[str, Any]:
    """Simulate an external payment gateway timeout error.

    Essential test scenario for hackathon demonstration:
    Severity: ERROR
    Keywords: 'Payment gateway timeout', 'timeout'
    """
    txn_id = f"TXN-{uuid4().hex[:10].upper()}"
    error_msg = (
        f"Payment gateway timeout after {timeout_ms}ms: gateway={gateway} "
        f"user_id={user_id} txn_id={txn_id} error=GatewayTimeoutHTTP504"
    )
    logger.error(error_msg)
    return {
        "status": "error",
        "service": "payment_service",
        "severity": "ERROR",
        "txn_id": txn_id,
        "message": error_msg,
    }


def simulate_processing_error(
    error_code: str = "ERR_LEDGER_ROLLBACK",
    details: str = "Database transaction rolled back during ledger commit",
    user_id: str = "customer_404",
) -> dict[str, Any]:
    """Simulate an internal backend processing failure."""
    txn_id = f"TXN-{uuid4().hex[:10].upper()}"
    error_msg = (
        f"Transaction processing error [{error_code}]: {details} "
        f"txn_id={txn_id} user_id={user_id}"
    )
    logger.error(error_msg)
    return {
        "status": "error",
        "service": "payment_service",
        "severity": "ERROR",
        "txn_id": txn_id,
        "message": error_msg,
    }


def simulate_event(event_type: str, **kwargs: Any) -> dict[str, Any]:
    """Dispatch event simulation based on event type name."""
    event_type = event_type.lower().strip()
    if event_type in ("success", "payment_success"):
        return simulate_payment_success(
            amount=float(kwargs.get("amount", round(random.uniform(10.0, 250.0), 2))),
            currency=kwargs.get("currency", "USD"),
            user_id=kwargs.get("user_id", "customer_884"),
        )
    elif event_type in ("failed", "failure", "decline", "declined"):
        return simulate_payment_failure(
            amount=float(kwargs.get("amount", round(random.uniform(50.0, 500.0), 2))),
            reason=kwargs.get("reason", "Insufficient balance in account"),
            user_id=kwargs.get("user_id", "customer_205"),
        )
    elif event_type in ("timeout", "gateway_timeout"):
        return simulate_gateway_timeout(
            gateway=kwargs.get("gateway", "StripeSimulator"),
            timeout_ms=int(kwargs.get("timeout_ms", 5000)),
            user_id=kwargs.get("user_id", "customer_912"),
        )
    elif event_type in ("error", "processing_error", "ledger_error"):
        return simulate_processing_error(
            error_code=kwargs.get("error_code", "ERR_LEDGER_ROLLBACK"),
            details=kwargs.get("details", "Database transaction rolled back during ledger commit"),
            user_id=kwargs.get("user_id", "customer_404"),
        )
    else:
        return simulate_payment_success()


def main() -> None:
    """Run interactive or CLI demonstration batch."""
    print("Generating Payment Service demo events...")
    simulate_payment_success(85.50, "USD", "pat_smith")
    simulate_payment_failure(499.00, "USD", "alex_client", "Exceeded daily spending limit")
    simulate_gateway_timeout("StripeSimulator", 5000, "elena_r")
    simulate_processing_error("ERR_DATABASE_DEADLOCK", "Acquire lock timeout on account balance table")
    print("Events logged to logs/payment_service.log successfully.")


if __name__ == "__main__":
    main()
