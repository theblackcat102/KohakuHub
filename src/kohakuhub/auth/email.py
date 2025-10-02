"""Email utilities for authentication."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..config import cfg


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """Send email verification email."""
    if not cfg.smtp.enabled:
        print(
            f"[EMAIL] SMTP disabled. Verification link: {cfg.app.base_url}/auth/verify?token={token}"
        )
        return True

    subject = "Verify your Kohaku Hub account"
    verify_link = f"{cfg.app.base_url}/auth/verify?token={token}"

    body = f"""
Hello {username},

Please verify your email address by clicking the link below:

{verify_link}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
Kohaku Hub
"""

    try:
        msg = MIMEMultipart()
        msg["From"] = cfg.smtp.from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(cfg.smtp.host, cfg.smtp.port) as server:
            if cfg.smtp.use_tls:
                server.starttls()
            if cfg.smtp.username and cfg.smtp.password:
                server.login(cfg.smtp.username, cfg.smtp.password)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send verification email: {e}")
        return False
