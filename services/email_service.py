import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


def send_recovery_email(recipient, code):
    username = current_app.config.get('SMTP_USERNAME')
    password = current_app.config.get('SMTP_PASSWORD')
    sender = current_app.config.get('SMTP_FROM_EMAIL') or username
    if not username or not password or not sender:
        return False

    message = EmailMessage()
    message['Subject'] = 'CampusPulse password reset code'
    message['From'] = sender
    message['To'] = recipient
    message.set_content(
        f"Your CampusPulse password reset code is {code}. It expires in 10 minutes. "
        "If you did not request this code, you can ignore this email."
    )

    try:
        with smtplib.SMTP(
            current_app.config.get('SMTP_HOST', 'smtp.gmail.com'),
            current_app.config.get('SMTP_PORT', 587),
            timeout=10
        ) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(username, password)
            smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        return False