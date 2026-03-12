from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any

import requests

from . import config
from .utils import append_jsonl, iso_utc


class Notifier:
    def __init__(self) -> None:
        self.smtp_host = os.getenv("II_SMTP_HOST", "").strip()
        self.smtp_port = int(os.getenv("II_SMTP_PORT", "465"))
        self.smtp_user = os.getenv("II_SMTP_USER", "").strip()
        self.smtp_pass = os.getenv("II_SMTP_PASS", "").strip()
        self.email_from = os.getenv("II_EMAIL_FROM", "").strip()
        self.email_to = os.getenv("II_EMAIL_TO", "").strip()
        self.webhook_url = os.getenv("II_ALERT_WEBHOOK", "").strip()

    def notify(self, subject: str, body: str, level: str = "info") -> dict[str, Any]:
        payload = {"ts": iso_utc(), "subject": subject, "body": body, "level": level}
        append_jsonl(config.NOTIFICATION_LOG, payload)
        result = {"logged": True, "email": False, "webhook": False}

        if self.email_from and self.email_to and self.smtp_host:
            try:
                msg = EmailMessage()
                msg["From"] = self.email_from
                msg["To"] = self.email_to
                msg["Subject"] = subject
                msg.set_content(body)
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as smtp:
                    if self.smtp_user and self.smtp_pass:
                        smtp.login(self.smtp_user, self.smtp_pass)
                    smtp.send_message(msg)
                result["email"] = True
            except Exception:
                pass

        if self.webhook_url:
            try:
                requests.post(self.webhook_url, json=payload, timeout=4)
                result["webhook"] = True
            except Exception:
                pass

        return result
