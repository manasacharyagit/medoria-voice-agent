import os
import base64
import logging
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

def get_gmail_service():
    service_account_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    ).with_subject(SENDER_EMAIL)
    service = build("gmail", "v1", credentials=credentials)
    return service

def send_doctor_email(doctor_name: str, doctor_email: str, patient_name: str, patient_phone: str, service_name: str, date_str: str, time_str: str) -> dict:
    """Sends a booking notification email to the doctor only."""
    try:
        service = get_gmail_service()
        body = f"""Dear {doctor_name},

A new appointment has been booked via Medoria AI.

Patient: {patient_name}
Patient Phone: {patient_phone}
Service: {service_name}
Date: {date_str}
Time: {time_str}

Thank you,
Medoria AI Team"""

        msg = MIMEMultipart("mixed")
        msg["From"] = SENDER_EMAIL
        msg["To"] = doctor_email
        msg["Subject"] = f"New Appointment - {patient_name} on {date_str} at {time_str}"
        msg.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

        logging.info(f"Doctor notification email sent to {doctor_email}")
        return {"success": True}

    except Exception as e:
        logging.error(f"Error sending doctor email: {e}")
        return {"success": False, "error": str(e)}