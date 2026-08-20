import os
import smtplib

from email.message import EmailMessage


SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_otp_email(
    recipient_email: str,
    otp: str,
    purpose: str
):
    if not SMTP_HOST or not SMTP_USERNAME or not SMTP_PASSWORD:
        raise RuntimeError("Email service is not configured")

    purpose_messages = {
        "change_username": "change your EVENTORA username",
        "change_password": "change your EVENTORA password",
        "change_email": "change your EVENTORA email address",
        "change_phone": "verify your EVENTORA phone number",
    }

    action = purpose_messages.get(
        purpose,
        "verify your EVENTORA account"
    )

    message = EmailMessage()

    message["Subject"] = "EVENTORA Security Verification Code"
    message["From"] = SMTP_USERNAME
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

You requested to {action}.

Your EVENTORA verification code is:

{otp}

This code will expire in 5 minutes.

If you did not request this change, please ignore this email.

For your security, do not share this verification code with anyone.

Regards,
EVENTORA Team
"""
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)