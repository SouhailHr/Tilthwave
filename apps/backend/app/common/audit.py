"""
The audit trail: one line per security-relevant event, on the `audit` logger.

Who signed in (or failed to), who signed out, who changed which password, who gave or took a
role, who deactivated or deleted whom. The request id on every line (common.request_context)
ties an event to the access log of the request that caused it. key=value pairs, one event per
line, so `grep 'audit' | grep event=login.failure` answers the usual questions until a JSON
formatter and a sink exist (docs/BACKLOG.md, observability).
"""

import logging

logger = logging.getLogger("audit")


def audit(event: str, **fields) -> None:
    """
    Record `event` (dotted: login.success, user.role_change, ...) with its context. None values
    are dropped; everything else is rendered as key=value.
    """
    rendered = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    logger.info("event=%s %s", event, rendered)
