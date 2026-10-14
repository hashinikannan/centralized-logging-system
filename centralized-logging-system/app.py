"""Centralized Logging System - Flask Web Application & API.

Provides:
- Web dashboard interface for hackathon demonstration
- Real-time log filtering by service, severity, and text search
- Summary metrics (Total, INFO, WARNING, ERROR)
- Interactive event generator endpoints for live demonstrations
- Export capabilities (JSON & CSV)
"""

from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.log_collector import LogCollector
from src.login_service import simulate_event as simulate_login_event
from src.payment_service import simulate_event as simulate_payment_event


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Application factory for the Centralized Logging Dashboard."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Configure app
    app.config["JSON_SORT_KEYS"] = False
    if test_config:
        app.config.update(test_config)

    # Log collector instance
    collector_log_dir = app.config.get("LOG_DIR", None)
    collector = LogCollector(log_dir=collector_log_dir)

    # -------------------------------------------------------------
    # HTML Views
    # -------------------------------------------------------------
    @app.route("/")
    def index() -> str:
        """Render the centralized log dashboard."""
        return render_template("index.html")

    # -------------------------------------------------------------
    # REST API Endpoints
    # -------------------------------------------------------------
    @app.route("/api/logs", methods=["GET"])
    def get_logs() -> Response:
        """Fetch filtered log entries.

        Query Parameters:
            - service: filter by service name (e.g., 'login_service', 'payment_service', 'all')
            - severity: filter by level ('INFO', 'WARNING', 'ERROR', 'CRITICAL', 'all')
            - search: search text in message, service, or severity
            - limit: maximum logs to return (default: 200, max: 1000)
            - offset: number of logs to skip (default: 0)
        """
        service = request.args.get("service", "all").strip()
        severity = request.args.get("severity", "all").strip()
        search = request.args.get("search", "").strip()

        try:
            limit = min(int(request.args.get("limit", 200)), 1000)
            offset = max(int(request.args.get("offset", 0)), 0)
        except ValueError:
            limit = 200
            offset = 0

        # Validate severity
        valid_severities = {"ALL", "INFO", "WARNING", "ERROR", "CRITICAL", ""}
        if severity.upper() not in valid_severities:
            return jsonify({
                "status": "error",
                "message": f"Invalid severity '{severity}'. Must be one of {sorted(list(valid_severities))}",
            }), 400

        logs = collector.filter_logs(
            service=service,
            severity=severity,
            search=search,
            limit=limit,
            offset=offset,
        )

        return jsonify({
            "status": "success",
            "count": len(logs),
            "filters": {
                "service": service,
                "severity": severity,
                "search": search,
            },
            "logs": [entry.to_dict() for entry in logs],
        })

    @app.route("/api/stats", methods=["GET"])
    def get_stats() -> Response:
        """Get summary metric counts and service list."""
        stats = collector.get_statistics()
        return jsonify({
            "status": "success",
            "stats": stats,
        })

    @app.route("/api/generate", methods=["POST"])
    def generate_log_event() -> Response:
        """Trigger an on-demand simulated event from login or payment service.

        JSON Body:
            {
                "service": "payment_service" | "login_service",
                "event_type": "timeout" | "success" | "failure" | "invalid_credentials" | ...
            }
        """
        data = request.get_json(silent=True) or {}
        service = data.get("service", "").strip().lower()
        event_type = data.get("event_type", "success").strip().lower()

        if service in ("login", "login_service"):
            result = simulate_login_event(
                event_type,
                user_id=data.get("user_id", "demo_user"),
                ip_address=data.get("ip_address", "192.168.1.100"),
                reason=data.get("reason", "Simulated demo event"),
            )
            return jsonify({
                "status": "success",
                "service": "login_service",
                "event_type": event_type,
                "result": result,
                "message": f"Generated login event: {event_type}",
            })

        elif service in ("payment", "payment_service"):
            result = simulate_payment_event(
                event_type,
                user_id=data.get("user_id", "demo_customer"),
                amount=data.get("amount", 99.95),
                gateway=data.get("gateway", "StripeSimulator"),
                timeout_ms=data.get("timeout_ms", 5000),
                reason=data.get("reason", "Simulated card decline"),
            )
            return jsonify({
                "status": "success",
                "service": "payment_service",
                "event_type": event_type,
                "result": result,
                "message": f"Generated payment event: {event_type}",
            })

        else:
            return jsonify({
                "status": "error",
                "message": "Invalid service specified. Choose 'login_service' or 'payment_service'.",
            }), 400

    @app.route("/api/clear", methods=["POST"])
    def clear_logs() -> Response:
        """Clear all active log files for demonstration resets."""
        collector.clear_logs()
        return jsonify({
            "status": "success",
            "message": "All log files have been reset and emptied.",
        })

    @app.route("/api/export", methods=["GET"])
    def export_logs() -> Response:
        """Export current filtered logs as CSV or JSON format."""
        export_format = request.args.get("format", "json").strip().lower()
        service = request.args.get("service", "all").strip()
        severity = request.args.get("severity", "all").strip()
        search = request.args.get("search", "").strip()

        logs = collector.filter_logs(
            service=service,
            severity=severity,
            search=search,
            limit=2000,
        )

        if export_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Timestamp", "Severity", "Service", "Message", "Source File"])
            for entry in logs:
                writer.writerow([
                    entry.timestamp,
                    entry.severity,
                    entry.service,
                    entry.message,
                    entry.source_file,
                ])
            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment;filename=centralized_logs.csv"},
            )
        else:
            return jsonify({
                "status": "success",
                "exported_count": len(logs),
                "logs": [entry.to_dict() for entry in logs],
            })

    # Error Handlers
    @app.errorhandler(404)
    def handle_not_found(e: Any) -> Response:
        return jsonify({"status": "error", "message": "Resource not found"}), 404

    @app.errorhandler(500)
    def handle_internal_error(e: Any) -> Response:
        return jsonify({"status": "error", "message": "Internal server error"}), 500

    return app


app = create_app()


def main() -> None:
    """Run Flask development server."""
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "0.0.0.0")
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1")
    print(f"\n=======================================================")
    print(f"  Centralized Logging System - Web Dashboard")
    print(f"  Server listening on: http://{host}:{port}")
    print(f"=======================================================\n")
    app.run(host=host, port=port, debug=debug_mode)


if __name__ == "__main__":
    main()
