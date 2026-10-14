"""Login Service module with centralized logging.

Simulates authentication flows including successful logins, failed attempts,
invalid credentials, and security warnings.
Logs are written to `logs/login_service.log`.
"""

from __future__ import annotations

import random
from typing import Any

from src.logger_config import get_logger

# Service logger writes to console and logs/login_service.log
logger = get_logger("login_service")


def record_login(user_id: str, authenticated: bool, ip_address: str = "192.168.1.100") -> bool:
    """Record an authentication outcome with safety precautions.

    Never pass raw passwords or sensitive credentials to this function.
    """
    if not user_id or not user_id.strip():
        logger.warning("Login attempt rejected: missing user identifier from IP %s", ip_address)
        return False

    user_clean = user_id.strip()
    if authenticated:
        logger.info(
            "Login succeeded for user_id=%s via WebPortal from IP %s",
            user_clean,
            ip_address,
        )
        return True
    else:
        logger.warning(
            "Login failed for user_id=%s: authentication mismatch from IP %s",
            user_clean,
            ip_address,
        )
        return False


def simulate_login_success(user_id: str = "alex_dev", ip_address: str = "192.168.1.45") -> dict[str, Any]:
    """Simulate a successful user authentication event."""
    logger.info(
        "Login succeeded: user_id=%s auth_method=OAuth2/MFA ip=%s session_id=sess-%06d",
        user_id,
        ip_address,
        random.randint(100000, 999999),
    )
    return {
        "status": "success",
        "service": "login_service",
        "severity": "INFO",
        "message": f"Login succeeded for user {user_id}",
    }


def simulate_login_failure(
    user_id: str = "jordan_m",
    reason: str = "Account temporarily locked due to policy",
    ip_address: str = "10.0.0.12",
) -> dict[str, Any]:
    """Simulate a failed login attempt."""
    logger.warning(
        "Login failed: user_id=%s reason='%s' ip=%s",
        user_id,
        reason,
        ip_address,
    )
    return {
        "status": "failure",
        "service": "login_service",
        "severity": "WARNING",
        "message": f"Login failed for {user_id}: {reason}",
    }


def simulate_invalid_credentials(
    user_id: str = "sam_ops",
    ip_address: str = "198.51.100.23",
) -> dict[str, Any]:
    """Simulate an invalid credentials warning event."""
    logger.warning(
        "Invalid credentials attempt: user_id=%s from IP %s - invalid hash mismatch",
        user_id,
        ip_address,
    )
    return {
        "status": "warning",
        "service": "login_service",
        "severity": "WARNING",
        "message": f"Invalid credentials attempt for user {user_id}",
    }


def simulate_suspicious_warning(
    user_id: str = "admin_root",
    attempts: int = 5,
    ip_address: str = "203.0.113.89",
) -> dict[str, Any]:
    """Simulate security warning for brute-force or anomalous login attempts."""
    logger.warning(
        "Security Alert: %d consecutive failed login attempts detected for user_id=%s from IP %s",
        attempts,
        user_id,
        ip_address,
    )
    return {
        "status": "warning",
        "service": "login_service",
        "severity": "WARNING",
        "message": f"Security alert: {attempts} consecutive failed attempts for {user_id}",
    }


def simulate_auth_service_error(
    user_id: str = "service_account",
    error_detail: str = "LDAP authentication provider unreachable",
) -> dict[str, Any]:
    """Simulate an internal error in the authentication service."""
    logger.error(
        "Authentication service error: user_id=%s detail='%s'",
        user_id,
        error_detail,
    )
    return {
        "status": "error",
        "service": "login_service",
        "severity": "ERROR",
        "message": f"Authentication service error: {error_detail}",
    }


def simulate_event(event_type: str, **kwargs: Any) -> dict[str, Any]:
    """Dispatch event simulation based on event type name."""
    event_type = event_type.lower().strip()
    if event_type in ("success", "login_success"):
        return simulate_login_success(
            user_id=kwargs.get("user_id", "alex_dev"),
            ip_address=kwargs.get("ip_address", "192.168.1.45"),
        )
    elif event_type in ("failed", "failure", "login_failure"):
        return simulate_login_failure(
            user_id=kwargs.get("user_id", "jordan_m"),
            reason=kwargs.get("reason", "Account temporarily locked due to policy"),
        )
    elif event_type in ("invalid_credentials", "credentials"):
        return simulate_invalid_credentials(
            user_id=kwargs.get("user_id", "sam_ops"),
            ip_address=kwargs.get("ip_address", "198.51.100.23"),
        )
    elif event_type in ("warning", "suspicious", "brute_force"):
        return simulate_suspicious_warning(
            user_id=kwargs.get("user_id", "admin_root"),
            attempts=int(kwargs.get("attempts", 5)),
        )
    elif event_type in ("error", "auth_error"):
        return simulate_auth_service_error(
            user_id=kwargs.get("user_id", "service_account"),
            error_detail=kwargs.get("detail", "LDAP authentication provider unreachable"),
        )
    else:
        # Default fallback: general login event
        return simulate_login_success()


def main() -> None:
    """Run interactive or CLI demonstration batch."""
    print("Generating Login Service demo events...")
    simulate_login_success("maya_admin", "192.168.1.15")
    simulate_invalid_credentials("guest_user", "198.51.100.10")
    simulate_suspicious_warning("maya_admin", 4, "203.0.113.50")
    simulate_login_failure("unknown_id", "User profile not found")
    print("Events logged to logs/login_service.log successfully.")


if __name__ == "__main__":
    main()
