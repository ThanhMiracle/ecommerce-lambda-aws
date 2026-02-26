import os
import smtplib
import logging
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _get_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() == "true"


def send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Send email via SMTP.

    Required env:
      SMTP_HOST

    Optional env:
      SMTP_PORT (default 587)
      SMTP_USER
      SMTP_PASS
      FROM_EMAIL
      SMTP_USE_TLS (true/false)
      SMTP_USE_SSL (true/false)
      SMTP_USE_AUTH (true/false)
      SMTP_TIMEOUT (seconds, default 10)
    """

    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        raise RuntimeError("SMTP_HOST is not set")

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_email = os.getenv("FROM_EMAIL") or smtp_user or "noreply@local"

    use_tls = _get_bool("SMTP_USE_TLS")
    use_ssl = _get_bool("SMTP_USE_SSL")
    use_auth = _get_bool("SMTP_USE_AUTH")
    timeout = float(os.getenv("SMTP_TIMEOUT", "10"))

    msg = MIMEText(html_body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout)

        with server as s:
            s.ehlo()

            if use_tls and not use_ssl:
                s.starttls()
                s.ehlo()

            if use_auth:
                if not smtp_user or not smtp_pass:
                    raise RuntimeError("SMTP_USE_AUTH=true but SMTP_USER/SMTP_PASS not set")
                s.login(smtp_user, smtp_pass)

            s.sendmail(from_email, [to_email], msg.as_string())

        logger.info("Email sent to=%s subject=%s", to_email, subject)

    except Exception as e:
        logger.exception("Email send failed to=%s error=%s", to_email, repr(e))
        raise