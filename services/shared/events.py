import os
import json
from typing import Any, Dict, Optional

EXCHANGE = os.getenv("EVENT_EXCHANGE", "microshop.events")

# Reuse AWS client across invocations (Lambda-friendly)
_sqs_client = None


def publish(event_type: str, payload: Dict[str, Any], *, safe: bool = False) -> None:
    """
    Publish an event to the configured backend.

    safe=True: swallow exceptions (log only). Useful for request paths like /register.
    """
    backend = os.getenv("EVENT_BACKEND", "rabbitmq").strip().lower()  # rabbitmq | sqs

    try:
        if backend == "rabbitmq":
            _publish_rabbitmq(event_type, payload)
            return

        if backend == "sqs":
            _publish_sqs(event_type, payload)
            return

        raise RuntimeError(f"Unsupported EVENT_BACKEND={backend}")

    except Exception as e:
        if safe:
            print("event publish failed:", repr(e))
            return
        raise


def _publish_rabbitmq(event_type: str, payload: Dict[str, Any]) -> None:
    # Import here so Lambda zip can omit pika if you only use SQS
    import pika

    rabbitmq_url = os.getenv("RABBITMQ_URL")
    if not rabbitmq_url:
        raise RuntimeError("RABBITMQ_URL is not set")

    params = pika.URLParameters(rabbitmq_url)

    # Prevent Lambda from hanging too long on network issues
    params.heartbeat = int(os.getenv("RABBITMQ_HEARTBEAT", "30"))
    params.blocked_connection_timeout = float(os.getenv("RABBITMQ_BLOCKED_TIMEOUT", "5"))

    # Some pika versions support socket_timeout directly
    socket_timeout = os.getenv("RABBITMQ_SOCKET_TIMEOUT")
    if socket_timeout is not None:
        try:
            params.socket_timeout = float(socket_timeout)
        except Exception:
            pass

    conn = pika.BlockingConnection(params)
    try:
        ch = conn.channel()
        ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

        body = json.dumps({"type": event_type, "payload": payload}).encode("utf-8")
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=event_type,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _publish_sqs(event_type: str, payload: Dict[str, Any]) -> None:
    global _sqs_client
    import boto3

    queue_url = os.getenv("SQS_QUEUE_URL")
    if not queue_url:
        raise RuntimeError("SQS_QUEUE_URL is not set")

    if _sqs_client is None:
        _sqs_client = boto3.client("sqs")

    _sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({"type": event_type, "payload": payload}),
        MessageAttributes={
            "type": {"DataType": "String", "StringValue": event_type}
        },
    )