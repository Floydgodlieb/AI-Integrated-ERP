"""
Append-only audit log: one JSON line per event, so we can always answer
"who asked for what, who approved it, and what was created in Odoo?".

Events written today:
  approval_requested  - the AI proposed a create; the user is asked to approve
  approval_answered   - the user clicked approve or decline
  approval_expired    - nobody answered in time, or the browser went away
  created             - a record was created in Odoo (with its Odoo id)
  create_blocked      - the backend refused a create (not allowed / invalid)
  create_failed       - Odoo refused the create
  read_blocked        - the AI tried to read something that is not allowed

The file is never rewritten, only appended to. It is git-ignored (logs/).
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone

log = logging.getLogger(__name__)


class AuditLog:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)

    def write(self, event: str, **data) -> None:
        record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event, **data}
        line = json.dumps(record, default=str, ensure_ascii=False)
        try:
            with self._lock, open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as e:                         # the audit log must never crash the app
            log.warning("Could not write audit log %s: %s", self.path, e)

    def read_all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
