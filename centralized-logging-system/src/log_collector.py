"""Centralized log collector and query engine.

Discovers, parses, aggregates, and filters logs from all service log files
in the logs directory.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.logger_config import get_log_dir


@dataclass
class LogEntry:
    """Represents a single parsed log event."""

    id: str
    timestamp: str
    timestamp_raw: str
    severity: str
    service: str
    message: str
    source_file: str

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for JSON serialization."""
        return asdict(self)


class LogCollector:
    """Collects and aggregates log files from the centralized log directory."""

    # Matches: 2026-10-14 10:20:30 | INFO    | login_service | User logged in
    PIPE_REGEX = re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*"
        r"(?P<severity>[A-Z]+)\s*\|\s*"
        r"(?:\[)?(?P<service>[a-zA-Z0-9_\-]+)(?:\])?\s*\|\s*"
        r"(?P<message>.*)$"
    )

    # Matches legacy: 2026-10-14T10:09:49+0530 INFO [login_service] User logged in
    LEGACY_REGEX = re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:[+\-]\d{4})?)\s+"
        r"(?P<severity>[A-Z]+)\s+"
        r"\[(?P<service>[a-zA-Z0-9_\-]+)\]\s+"
        r"(?P<message>.*)$"
    )

    def __init__(self, log_dir: Path | str | None = None) -> None:
        """Initialize with a log directory or use the system default."""
        if log_dir is not None:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = get_log_dir()

    def parse_line(self, line: str, source_file: str, line_index: int) -> LogEntry | None:
        """Parse a single log file line into a structured LogEntry."""
        line = line.strip()
        if not line:
            return None

        # 1. Try JSON parsing (if structured JSON logging is used)
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                ts = str(data.get("timestamp", data.get("time", "")))
                sev = str(data.get("severity", data.get("level", "INFO"))).upper()
                svc = str(data.get("service", data.get("logger", "unknown")))
                msg = str(data.get("message", data.get("msg", line)))
                entry_id = f"{source_file}:{line_index}"
                return LogEntry(
                    id=entry_id,
                    timestamp=ts,
                    timestamp_raw=ts,
                    severity=sev,
                    service=svc,
                    message=msg,
                    source_file=source_file,
                )
            except json.JSONDecodeError:
                pass

        # 2. Try Standard Pipe format: `timestamp | severity | service | message`
        match = self.PIPE_REGEX.match(line)
        if match:
            entry_id = f"{source_file}:{line_index}"
            return LogEntry(
                id=entry_id,
                timestamp=match.group("timestamp").strip(),
                timestamp_raw=match.group("timestamp").strip(),
                severity=match.group("severity").strip().upper(),
                service=match.group("service").strip(),
                message=match.group("message").strip(),
                source_file=source_file,
            )

        # 3. Try Legacy bracket format: `timestamp LEVEL [service] message`
        match_leg = self.LEGACY_REGEX.match(line)
        if match_leg:
            entry_id = f"{source_file}:{line_index}"
            ts_str = match_leg.group("timestamp").strip()
            # Clean ISO timestamp display if it has T
            clean_ts = ts_str.replace("T", " ")[:19]
            return LogEntry(
                id=entry_id,
                timestamp=clean_ts,
                timestamp_raw=ts_str,
                severity=match_leg.group("severity").strip().upper(),
                service=match_leg.group("service").strip(),
                message=match_leg.group("message").strip(),
                source_file=source_file,
            )

        # 4. Fallback for unexpected formats (graceful resilience)
        entry_id = f"{source_file}:{line_index}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return LogEntry(
            id=entry_id,
            timestamp=now_str,
            timestamp_raw=now_str,
            severity="INFO",
            service=Path(source_file).stem,
            message=line,
            source_file=source_file,
        )

    def read_all_logs(self) -> list[LogEntry]:
        """Read and parse all log files in the configured directory.

        Handles missing directory, empty files, and locked files gracefully.
        Returns entries sorted in descending chronological order (newest first).
        """
        if not self.log_dir.exists():
            return []

        entries: list[LogEntry] = []

        try:
            log_files = sorted(self.log_dir.glob("*.log"))
        except Exception:
            return []

        for file_path in log_files:
            source_name = file_path.name
            try:
                # Open with utf-8 and ignore/replace corrupt bytes
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    for idx, line in enumerate(f, start=1):
                        entry = self.parse_line(line, source_name, idx)
                        if entry:
                            entries.append(entry)
            except (OSError, IOError):
                # Silently skip file if inaccessible/locked
                continue

        # Sort newest logs first
        entries.sort(key=lambda x: x.timestamp_raw, reverse=True)
        return entries

    def filter_logs(
        self,
        service: str | None = None,
        severity: str | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LogEntry]:
        """Filter log entries according to service, severity, and search keywords.

        Args:
            service: Filter by exact or partial service name ('all' or None means any)
            severity: Filter by log level ('all' or None means any)
            search: Case-insensitive search string in message, service, or severity
            limit: Maximum number of entries to return (pagination)
            offset: Number of entries to skip

        Returns:
            Filtered list of LogEntry objects.
        """
        all_logs = self.read_all_logs()
        filtered = all_logs

        # 1. Filter by service
        if service and service.strip().lower() not in ("all", ""):
            svc_target = service.strip().lower()
            filtered = [
                log for log in filtered if log.service.lower() == svc_target
            ]

        # 2. Filter by severity
        if severity and severity.strip().lower() not in ("all", ""):
            sev_target = severity.strip().upper()
            filtered = [
                log for log in filtered if log.severity == sev_target
            ]

        # 3. Filter by search query
        if search and search.strip():
            query = search.strip().lower()
            filtered = [
                log
                for log in filtered
                if query in log.message.lower()
                or query in log.service.lower()
                or query in log.severity.lower()
                or query in log.timestamp.lower()
            ]

        # Pagination
        if offset > 0:
            filtered = filtered[offset:]
        if limit is not None and limit > 0:
            filtered = filtered[:limit]

        return filtered

    def get_statistics(self) -> dict[str, Any]:
        """Calculate summary counts: total, INFO, WARNING, ERROR, and per-service.

        Returns:
            Dictionary with aggregated log metrics.
        """
        all_logs = self.read_all_logs()

        stats = {
            "total": len(all_logs),
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0,
            "by_service": {},
            "services": set(),
        }

        for log in all_logs:
            sev = log.severity.upper()
            if sev == "INFO":
                stats["info"] += 1
            elif sev == "WARNING":
                stats["warning"] += 1
            elif sev in ("ERROR", "CRITICAL"):
                stats["error"] += 1
                if sev == "CRITICAL":
                    stats["critical"] += 1

            # Count by service
            svc = log.service
            stats["services"].add(svc)
            stats["by_service"][svc] = stats["by_service"].get(svc, 0) + 1

        # Convert set of services to sorted list
        stats["services"] = sorted(list(stats["services"]))
        return stats

    def clear_logs(self) -> bool:
        """Clear the content of all log files in the directory for testing/resets."""
        if not self.log_dir.exists():
            return True

        for file_path in self.log_dir.glob("*.log"):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.truncate(0)
            except (OSError, IOError):
                pass
        return True
