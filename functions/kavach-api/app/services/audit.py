"""
Audit logging service for Kavach.

Every API call that touches sensitive data is logged to a local JSONL file.
In production this would be sent to a SIEM or centralised logging service.

Format (one JSON object per line):
{
  "timestamp": "ISO-8601",
  "user_id": "...",
  "role": "...",
  "method": "GET|POST",
  "path": "/api/...",
  "query_text": "...",  # for chat queries
  "ip": "...",
  "status_code": 200
}
"""
from __future__ import annotations
from typing import Optional
import json
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "audit.log")


def log_event(
    method: str,
    path: str,
    user_id: str = "anonymous",
    role: str = "none",
    query_text: str = "",
    ip: str = "",
    status_code: int = 200,
):
    """Append one audit entry to the JSONL log file."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "role": role,
        "method": method,
        "path": path,
        "query_text": query_text[:200] if query_text else "",
        "ip": ip,
        "status_code": status_code,
    }
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception as exc:
        print(f"[audit] Failed to write log: {exc}")


def recent_audit_entries(n: int = 50) -> list:
    """Return the last `n` entries from the audit log (for the supervisor dashboard)."""
    if not os.path.isfile(LOG_PATH):
        return []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
        return list(reversed(entries))
    except Exception:
        return []
