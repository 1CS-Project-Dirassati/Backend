# madrassati/auth/utils.py
import random
from datetime import datetime, timezone, timedelta
import jwt
from mailjet_rest import Client # Import Mailjet client
from flask import current_app, render_template # Import Flask app context and render_template

from madrassati.config import Config
from madrassati.extensions import redis_client

# --- Constants ---
OTP_EXPIRATION_MINUTES = 10
APP_NAME = "Madrassati" # Or load from config

# --- JWT Functions ---
# ... (generate_token function remains the same) ...

# --- OTP Functions ---
# ... (generate_and_store_otp function remains the same for now) ...
# ... (verify_stored_otp function remains the same) ...


# --- Email Sending Function ---
def send_email(to_email: str, subject: str, template_prefix: str, context: dict):
    """
    Sends an email using Mailjet with HTML and optional Text parts from templates.

    Args:
        to_email (str): Recipient's email address.
        subject (str): Email subject line.
        template_prefix (str): Base name of the template (e.g., 'email/otp_email').
                                Expects '.html' and optionally '.txt' versions.
        context (dict): Dictionary with variables for the template.

    Returns:
        bool: True if email sending was apparently successful (status 200), False otherwise.
    """
    api_key = current_app.config.get('MAILJET_API_KEY')
    secret_key = current_app.config.get('MAILJET_SECRET_KEY')
    sender_email = current_app.config.get('MAIL_SENDER')
    sender_name = current_app.config.get('MAIL_SENDER_NAME', APP_NAME) # Use configured name

    # Ensure configuration is present
    if not all([api_key, secret_key, sender_email]):
        current_app.logger.error("Mailjet configuration missing (API Key, Secret Key, or Sender Email).")
        return False

    mailjet = Client(auth=(api_key, secret_key), version='v3.1')

    # Add common context variables
    context.setdefault('app_name', APP_NAME)
    context.setdefault('subject', subject)

    # Render email bodies
    try:
        html_body = render_template(f"{template_prefix}.html", **context)
    except Exception as e:
        current_app.logger.error(f"Error rendering HTML template {template_prefix}.html: {e}")
        return False

    try:
        # Attempt to render text part, optional
        text_body = render_template(f"{template_prefix}.txt", **context)
    except Exception:
        # If text template doesn't exist, create a basic fallback
        text_body = f"Please view this email in an HTML-compatible client. Subject: {subject}. OTP: {context.get('otp_code', 'N/A')}"
        current_app.logger.info(f"Text template {template_prefix}.txt not found, using fallback.")


    message_data = {
        'Messages': [
            {
                "From": {
                    "Email": sender_email,
                    "Name": sender_name
                },
                "To": [
                    {"Email": to_email}
                    # Optionally add "Name": "Recipient Name" if available
                ],
                "Subject": subject,
                "TextPart": text_body,
                "HTMLPart": html_body
                # Can add CustomID, Attachments, Headers etc. here if needed
            }
        ]
    }

    try:
        result = mailjet.send.create(data=message_data)
        if result.status_code == 200:
            current_app.logger.info(f"Email sent successfully via Mailjet to {to_email}. Subject: '{subject}'.")
            return True
        else:
            # Log detailed error from Mailjet if possible
            error_info = result.json()
            current_app.logger.error(f"Mailjet API error sending email to {to_email}. Status: {result.status_code}. Response: {error_info}")
            return False
    except Exception as e:
        # Catch potential network errors or other issues with the request
        current_app.logger.error(f"Exception occurred sending email via Mailjet to {to_email}: {e}", exc_info=True)
        return False

