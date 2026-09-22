"""
Outgoing email, stdlib only (smtplib), for the password-reset link.

Not configured (no SMTP_HOST) is a first-class mode, not an error: the message is written to the
API log instead, so a local stack can complete the forgot-password flow by copying the link out
of `docker logs tilthwave-api`. That log line contains a live reset token, which is exactly why
this mode is only for a stack nobody else can read the logs of.
"""

import logging
import smtplib
from email.message import EmailMessage

from config.settings import settings

logger = logging.getLogger(__name__)


class Mailer:
    def __init__(self, cfg):
        self.cfg = cfg

    @property
    def configured(self) -> bool:
        return bool(self.cfg.HOST)

    def send(self, to: str, subject: str, body: str) -> None:
        if not self.configured:
            logger.warning(
                "SMTP_HOST is not set: email NOT sent, shown here instead.\nTo: %s\nSubject: %s\n%s", to, subject, body
            )
            return
        message = EmailMessage()
        message["From"] = self.cfg.FROM_ADDRESS
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(self.cfg.HOST, self.cfg.PORT, timeout=self.cfg.TIMEOUT_SECONDS) as smtp:
                if self.cfg.USE_TLS:
                    smtp.starttls()
                if self.cfg.USER:
                    smtp.login(self.cfg.USER, self.cfg.PASSWORD or "")
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError):
            # Runs as a background task after the 202 went out; nothing to tell the caller.
            logger.exception("Could not send email to %s via %s:%s", to, self.cfg.HOST, self.cfg.PORT)

    def send_password_reset(self, to: str, username: str, link: str, minutes: int) -> None:
        body = (
            f"Hello {username},\n\n"
            f"Someone asked to reset the password of your Tilthwave account. If that was you, open this "
            f"link within {minutes} minutes:\n\n{link}\n\n"
            "If it was not you, ignore this message: your password has not changed and the link expires on "
            "its own.\n"
        )
        self.send(to=to, subject="Reset your Tilthwave password", body=body)


mailer = Mailer(settings.SMTP)
