import os
import logging
import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_ses = None


def send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Send email via Amazon SES.

    Required env:
      SES_FROM_EMAIL

    Optional env:
      AWS_REGION / AWS_DEFAULT_REGION (default us-east-1)
    """
    global _ses

    from_email = os.getenv("SES_FROM_EMAIL")
    if not from_email:
        raise RuntimeError("SES_FROM_EMAIL is not set")

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

    if _ses is None:
        _ses = boto3.client("ses", region_name=region)

    resp = _ses.send_email(
        Source=from_email,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
        },
    )

    logger.info("SES sent email to=%s message_id=%s", to_email, resp.get("MessageId"))