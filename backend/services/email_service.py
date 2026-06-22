"""
Email service for sending application emails with optional attachments.
Supports SSL (port 465) and STARTTLS (port 587).
Falls back to DRY_RUN mode when SMTP credentials are not configured.
"""

import logging
import os
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Send emails with optional HTML body and file attachments."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.host = host if host is not None else settings.SMTP_HOST
        self.port = port if port is not None else settings.SMTP_PORT
        self.username = username if username is not None else settings.SMTP_USERNAME
        self.password = password if password is not None else settings.SMTP_PASSWORD

    @property
    def is_configured(self) -> bool:
        """Return True if SMTP credentials are present and not placeholders."""
        is_placeholder_username = "your-email" in self.username or "your_email" in self.username if self.username else True
        is_placeholder_password = "your-app-password" in self.password if self.password else True
        return bool(
            self.host and
            self.username and
            self.password and
            not is_placeholder_username and
            not is_placeholder_password
        )

    def _send_email_sync(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[list[str]] = None,
    ) -> bool:
        if not self.is_configured:
            return self._dry_run(to, subject, body, attachments)

        try:
            msg = self._build_message(to, subject, body, html_body, attachments)
            self._send(msg, to)
            logger.info("Email sent successfully to %s (subject: %s)", to, subject)
            return True
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to, exc)
            return False

    async def send_email(
        self,
        to: str = "",
        subject: str = "",
        body: str = "",
        html_body: Optional[str] = None,
        attachments: Optional[list[str]] = None,
        to_email: Optional[str] = None,
    ) -> bool:
        """Send an email message asynchronously.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Plain-text body.
            html_body: Optional HTML body.
            attachments: Optional list of file paths to attach.
            to_email: Alias for to, used by some agents.

        Returns:
            True if the email was sent (or dry-run logged) successfully.
        """
        import asyncio
        recipient = to_email or to
        if not recipient:
            raise ValueError("Recipient address 'to' or 'to_email' must be provided.")

        return await asyncio.to_thread(
            self._send_email_sync,
            to=recipient,
            subject=subject,
            body=body,
            html_body=html_body,
            attachments=attachments,
        )

    async def send_email_with_attachments(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_paths: list[str],
        html_body: Optional[str] = None,
    ) -> bool:
        """Send an email message with attachments asynchronously."""
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            html_body=html_body,
            attachments=attachment_paths,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_message(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str],
        attachments: Optional[list[str]],
    ) -> MIMEMultipart:
        """Construct the MIME message."""
        msg = MIMEMultipart("mixed")
        msg["From"] = self.username
        msg["To"] = to
        msg["Subject"] = subject

        # Text / HTML alternative part
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        # Attachments
        for file_path in attachments or []:
            self._attach_file(msg, file_path)

        return msg

    @staticmethod
    def _attach_file(msg: MIMEMultipart, file_path: str) -> None:
        """Attach a file to the message."""
        path = Path(file_path)
        if not path.exists():
            logger.warning("Attachment not found, skipping: %s", file_path)
            return

        try:
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{path.name}"',
            )
            msg.attach(part)
            logger.info("Attached file: %s", path.name)
        except Exception as exc:
            logger.warning("Could not attach file %s: %s", file_path, exc)

    def _send(self, msg: MIMEMultipart, to: str) -> None:
        """Dispatch the message via SMTP."""
        context = ssl.create_default_context()

        if self.port == 465:
            # SSL
            with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                server.login(self.username, self.password)
                server.send_message(msg)
        else:
            # STARTTLS (typically port 587)
            with smtplib.SMTP(self.host, self.port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.username, self.password)
                server.send_message(msg)

    def _dry_run(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[list[str]],
    ) -> bool:
        """Log the email instead of sending it (credentials not configured)."""
        logger.warning("DRY_RUN mode – SMTP credentials not configured.")
        logger.info("=" * 60)
        logger.info("DRY-RUN EMAIL")
        logger.info("-" * 60)
        logger.info("  To:      %s", to)
        logger.info("  Subject: %s", subject)
        logger.info("  Body:    %s...", body[:200])
        if attachments:
            logger.info("  Attachments: %s", ", ".join(attachments))
        logger.info("=" * 60)
        return True
