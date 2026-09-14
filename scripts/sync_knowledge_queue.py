#!/usr/bin/env python3
"""Synchronize resolved tickets and create pending Altitude knowledge drafts.

This script is safe to run repeatedly. It never publishes knowledge automatically;
resolved-ticket drafts remain Pending until an administrator approves them in the
Knowledge Queue.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from core.analytics_db import (  # noqa: E402
    apply_ticket_status_updates,
    get_tickets_for_status_sync,
    initialize_database,
    record_ticket_status_sync_error,
)
from core.knowledge_queue import sync_resolved_tickets_to_knowledge_queue  # noqa: E402
from core.ticketing_client import TicketingClientError, fetch_ticket_statuses  # noqa: E402


def main() -> int:
    initialize_database()
    local_tickets = get_tickets_for_status_sync(limit=1_000)

    if not local_tickets:
        print("No Altitude-created tickets are available for synchronization.")
        return 0

    try:
        remote_matches = fetch_ticket_statuses(local_tickets)
    except (TicketingClientError, ValueError) as error:
        record_ticket_status_sync_error(str(error))
        print(f"Ticket synchronization failed: {error}")
        return 1

    updates = [
        {
            "local_ticket_id": match.local_ticket_id,
            "status": match.status,
            "external_ticket_id": match.external_ticket_id,
            "remote_ticket_url": match.remote_ticket_url,
            "resolution_comment": match.resolution_comment,
        }
        for match in remote_matches
    ]
    updated_count = apply_ticket_status_updates(updates)
    queue_result = sync_resolved_tickets_to_knowledge_queue(limit=1_000)

    print(
        "Knowledge queue synchronization complete: "
        f"checked={len(local_tickets)}, matched={len(remote_matches)}, "
        f"updated={updated_count}, drafts_created={queue_result['created']}, "
        f"drafts_skipped={queue_result['skipped']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
