import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from .emailer import send_email

logger = logging.getLogger("notification-service")
logging.basicConfig(level=logging.INFO)


def handle_event(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Handle domain events.
    payload examples:
      user.registered: { "email": "...", "verify_url": "..." }
      payment.succeeded: { "email": "...", "order_id": "...", "total": ... }
    """
    if event_type == "user.registered":
        email = payload["email"]
        verify_url = payload["verify_url"]

        send_email(
            to_email=email,
            subject="Verify your MicroShop account",
            html_body=(
                "<h3>Welcome to MicroShop</h3>"
                "<p>Please verify your email:</p>"
                f"<p><a href='{verify_url}'>{verify_url}</a></p>"
            ),
        )
        logger.info("Sent verification email to %s", email)
        return

    if event_type == "payment.succeeded":
        email = payload["email"]
        order_id = payload["order_id"]
        total = payload["total"]

        send_email(
            to_email=email,
            subject="Payment confirmed - MicroShop",
            html_body=(
                "<h3>Payment successful</h3>"
                f"<p>Order <b>#{order_id}</b> is paid.</p>"
                f"<p>Total: <b>${total}</b></p>"
            ),
        )
        logger.info("Sent payment email to %s (order #%s)", email, order_id)
        return

    logger.info("Ignoring event_type=%s payload=%s", event_type, payload)


def _try_parse_json(s: Any) -> Optional[Dict[str, Any]]:
    if isinstance(s, dict):
        return s
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _extract_sqs_records(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = event.get("Records")
    return records if isinstance(records, list) else []


def _parse_message(obj: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Expected message format:
      { "type": "user.registered", "payload": {...} }
    """
    event_type = obj.get("type") or obj.get("event_type")
    payload = obj.get("payload") or {}
    if not isinstance(event_type, str) or not isinstance(payload, dict):
        return None
    return event_type, payload


def _handle_sqs_batch(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    If this is an SQS trigger, we MUST return the partial batch response shape:
      { "batchItemFailures": [ {"itemIdentifier": "<messageId>"} , ...] }

    This ensures only failed messages are retried (instead of the whole batch).
    """
    records = _extract_sqs_records(event)
    if not records:
        return None

    failures: List[Dict[str, str]] = []
    processed = 0

    for r in records:
        message_id = r.get("messageId") or r.get("messageID") or r.get("message_id") or ""
        body = r.get("body")
        obj = _try_parse_json(body)

        if not obj:
            logger.warning("Skipping non-JSON SQS body: %s", body)
            # treat as failure so it can go to DLQ after retries
            if message_id:
                failures.append({"itemIdentifier": message_id})
            continue

        parsed = _parse_message(obj)
        if not parsed:
            logger.warning("Bad message format: %s", obj)
            if message_id:
                failures.append({"itemIdentifier": message_id})
            continue

        event_type, payload = parsed

        try:
            handle_event(event_type, payload)
            processed += 1
        except Exception as e:
            logger.exception("Failed processing message_id=%s error=%s", message_id, repr(e))
            if message_id:
                failures.append({"itemIdentifier": message_id})

    logger.info("SQS batch processed=%s failures=%s", processed, len(failures))
    return {"batchItemFailures": failures}


def _extract_eventbridge(event: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    EventBridge style:
      {
        "detail-type": "user.registered",
        "detail": {...}
      }
    """
    detail_type = event.get("detail-type") or event.get("detailType")
    detail = event.get("detail")
    if isinstance(detail_type, str) and isinstance(detail, dict):
        return detail_type, detail
    return None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info("Received event keys: %s", list(event.keys()) if isinstance(event, dict) else type(event))

    # 1) SQS (recommended)
    sqs_resp = _handle_sqs_batch(event)
    if sqs_resp is not None:
        return sqs_resp

    # 2) EventBridge direct
    eb = _extract_eventbridge(event)
    if eb:
        event_type, payload = eb
        handle_event(event_type, payload)
        return {"ok": True, "source": "eventbridge"}

    # 3) Direct invoke (testing)
    direct = _parse_message(event) if isinstance(event, dict) else None
    if direct:
        event_type, payload = direct
        handle_event(event_type, payload)
        return {"ok": True, "source": "direct"}

    logger.warning("Unsupported event format: %s", event)
    return {"ok": False, "error": "Unsupported event format"}