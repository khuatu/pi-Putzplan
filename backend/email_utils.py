# backend/email_utils.py
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "bella_putzplan@proton.me")   # Deine verifizierte Absenderadresse

def send_email(to_email: str, subject: str, body: str):
    if not SENDGRID_API_KEY:
        print("SendGrid API-Key nicht gesetzt. E-Mail nicht versendet.")
        return
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"E-Mail an {to_email} gesendet. Status: {response.status_code}")
    except Exception as e:
        print(f"Fehler beim Senden an {to_email}: {e}")