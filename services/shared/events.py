import os
import json
from typing import Any, Dict

EVENT_BACKEND = os.getenv("EVENT_BACKEND", "rabbitmq")  # rabbitmq | sqs
EXCHANGE = "microshop.events"


def publish(event_type: str, payload: Dict[str, Any]) -> None:
    if EVENT_BACKEND == "rabbitmq":
        _publish_rabbitmq(event_type, payload)
        return

    if EVENT_BACKEND == "sqs":
        _publish_sqs(event_type, payload)
        return

    raise RuntimeError(f"Unsupported EVENT_BACKEND={EVENT_BACKEND}")


def _publish_rabbitmq(event_type: str, payload: Dict[str, Any]) -> None:
    import pika

    rabbitmq_url = os.environ["RABBITMQ_URL"]

    conn = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    body = json.dumps({"type": event_type, "payload": payload}).encode("utf-8")
    ch.basic_publish(
        exchange=EXCHANGE,
        routing_key=event_type,
        body=body,
        properties=pika.BasicProperties(delivery_mode=2),
    )
    conn.close()


def _publish_sqs(event_type: str, payload: Dict[str, Any]) -> None:
    import boto3

    queue_url = os.environ["SQS_QUEUE_URL"]
    sqs = boto3.client("sqs")

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({"type": event_type, "payload": payload}),
        MessageAttributes={
            "type": {"DataType": "String", "StringValue": event_type}
        },
    )